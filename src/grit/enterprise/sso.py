"""Shim — re-exports from grit_pro.enterprise.sso when the pro package is installed."""

try:
    from grit_pro.enterprise.sso import (  # noqa: F401
        EnterpriseConfig,
        SSOSession,
        IdpType,
        load_enterprise_config,
        save_enterprise_config,
        load_sso_session,
        save_sso_session,
        clear_sso_session,
        start_oidc_login,
        poll_oidc_token,
        get_saml_login_url,
        process_saml_response,
        resolve_profile_for_sso,
    )
    from grit_pro.enterprise.sso import *  # noqa: F401, F403
except ImportError:
    pass
