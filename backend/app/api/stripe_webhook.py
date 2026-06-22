"""Stripe webhook handler for subscription lifecycle events."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request) -> dict:
    """Handle Stripe webhook events (subscription created, updated, deleted)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        import stripe
        stripe.api_key = settings.stripe_secret_key
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except Exception as exc:
        log.warning("Stripe webhook verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook verification failed: {exc}",
        )

    event_type = event["type"]
    log.info("Stripe event: %s", event_type)

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        await _handle_subscription_upsert(event["data"]["object"])
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(event["data"]["object"])

    return {"received": True}


async def _handle_subscription_upsert(subscription_obj: dict) -> None:
    """Create or update a Subscription record when Stripe confirms payment."""
    from app.database import AsyncSessionLocal
    from app.models.user import Subscription, User
    from sqlalchemy import select
    from datetime import datetime, timezone

    stripe_customer_id = subscription_obj.get("customer")
    stripe_sub_id = subscription_obj["id"]
    status_str = subscription_obj.get("status", "")
    plan_id = (subscription_obj.get("items", {}).get("data", [{}])[0]
               .get("price", {}).get("lookup_key", ""))

    tier = "pro" if "pro" in plan_id else ("enterprise" if "enterprise" in plan_id else "free")
    profile_limit = -1 if tier in ("pro", "enterprise") else 5

    period_end = subscription_obj.get("current_period_end")
    expires_at = (
        datetime.fromtimestamp(period_end, tz=timezone.utc) if period_end else None
    )

    async with AsyncSessionLocal() as db:
        # Find user by Stripe customer ID
        stmt = select(User).where(User.id.in_(
            # Simplified: look up by stripe_customer_id stored in Subscription
            db.query(Subscription.user_id).where(
                Subscription.stripe_customer_id == stripe_customer_id
            ).scalar_subquery()
        ))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            log.warning("No user found for Stripe customer %s", stripe_customer_id)
            return

        stmt2 = select(Subscription).where(Subscription.user_id == user.id)
        result2 = await db.execute(stmt2)
        sub = result2.scalar_one_or_none()

        if sub is None:
            sub = Subscription(user_id=user.id)
            db.add(sub)

        sub.tier = tier
        sub.profile_limit = profile_limit
        sub.stripe_subscription_id = stripe_sub_id
        sub.stripe_customer_id = stripe_customer_id
        sub.expires_at = expires_at
        await db.commit()

    log.info("Updated subscription for user %s: tier=%s", user.id if user else "?", tier)


async def _handle_subscription_deleted(subscription_obj: dict) -> None:
    """Downgrade user to free tier when subscription is cancelled."""
    from app.database import AsyncSessionLocal
    from app.models.user import Subscription
    from sqlalchemy import select
    from app.config import settings

    stripe_sub_id = subscription_obj["id"]

    async with AsyncSessionLocal() as db:
        stmt = select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub_id
        )
        result = await db.execute(stmt)
        sub = result.scalar_one_or_none()
        if sub:
            sub.tier = "free"
            sub.profile_limit = settings.free_profile_limit
            sub.expires_at = None
            await db.commit()
            log.info("Downgraded subscription %s to free", stripe_sub_id)
