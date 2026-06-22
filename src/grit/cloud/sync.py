"""Shim — re-exports from grit_pro.cloud.sync when the pro package is installed."""

try:
    from grit_pro.cloud.sync import (  # noqa: F401
        SyncEngine,
        get_team_profiles,
    )
    from grit_pro.cloud.sync import *  # noqa: F401, F403
except ImportError:
    pass
