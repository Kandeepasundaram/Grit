"""Shim — re-exports from grit_pro.cloud.sync when the pro package is installed."""

try:
    from grit_pro.cloud.sync import *  # noqa: F401, F403
    from grit_pro.cloud.sync import (  # noqa: F401
        SyncEngine as SyncEngine,
    )
    from grit_pro.cloud.sync import (
        get_team_profiles as get_team_profiles,
    )
except ImportError:
    pass
