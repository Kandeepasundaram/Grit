"""Shim — re-exports from grit_pro.cloud.client when the pro package is installed."""

try:
    from grit_pro.cloud.client import *  # noqa: F401, F403
    from grit_pro.cloud.client import (  # noqa: F401
        AuthRequiredError as AuthRequiredError,
    )
    from grit_pro.cloud.client import (
        GritCloudClient as GritCloudClient,
    )
    from grit_pro.cloud.client import (
        OfflineError as OfflineError,
    )
except ImportError:
    pass
