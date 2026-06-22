"""Shim — re-exports from grit_pro.enterprise.audit when the pro package is installed."""

try:
    from grit_pro.enterprise.audit import (  # noqa: F401
        log_profile_switch,
        log_session_create,
        log_git_config_write,
        export_entries,
    )
    from grit_pro.enterprise.audit import *  # noqa: F401, F403
except ImportError:
    pass
