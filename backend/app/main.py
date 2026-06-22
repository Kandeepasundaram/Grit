"""Grit Cloud API — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, license, sync, account, stripe_webhook, enterprise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    from app.database import init_db
    await init_db()
    yield
    # Shutdown — nothing to clean up for now


app = FastAPI(
    title="Grit Cloud API",
    description="Backend for Grit Pro/Enterprise — sync, licensing, team profiles",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://grit.dev", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/oauth", tags=["auth"])
app.include_router(license.router, prefix="/v1/license", tags=["license"])
app.include_router(sync.router, prefix="/v1/sync", tags=["sync"])
app.include_router(account.router, prefix="/v1/account", tags=["account"])
app.include_router(stripe_webhook.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(enterprise.router, prefix="/v1/enterprise", tags=["enterprise"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "grit-cloud"}
