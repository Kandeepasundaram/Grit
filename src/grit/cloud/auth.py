"""Shim — re-exports from grit_pro.cloud.auth when the pro package is installed."""

try:
    from grit_pro.cloud.auth import (  # noqa: F401
        start_device_flow,
        poll_device_flow,
        get_access_token,
        save_tokens,
        load_tokens,
        clear_tokens,
    )
    from grit_pro.cloud.auth import *  # noqa: F401, F403
except ImportError:
    pass
