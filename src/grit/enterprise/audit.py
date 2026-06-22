"""Shim — re-exports from grit_pro.enterprise.audit when the pro package is installed."""

try:
    from grit_pro.enterprise.audit import *  # noqa: F401, F403
    from grit_pro.enterprise.audit import (  # noqa: F401
        export_entries as export_entries,
    )
    from grit_pro.enterprise.audit import (
        log_git_config_write as log_git_config_write,
    )
    from grit_pro.enterprise.audit import (
        log_profile_switch as log_profile_switch,
    )
    from grit_pro.enterprise.audit import (
        log_session_create as log_session_create,
    )
except ImportError:
    pass
