"""Statistics domain operations for Piazza SDK.

Provides standalone functions for statistics retrieval.
"""

from __future__ import annotations

__all__ = ["get_statistics"]

from typing import TYPE_CHECKING

from piazza_sdk.exceptions import PiazzaSDKError, StatisticsError
from piazza_sdk.models.network import Statistics

if TYPE_CHECKING:
    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager


async def get_statistics(rpc: RPC, *, session: SessionStateManager | None = None) -> Statistics:
    """Get network statistics.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.

    Returns:
        Statistics model with course metrics.

    Raises:
        StatisticsError: If statistics retrieval or parsing fails.
        PiazzaSDKError: On unexpected errors.

        Example:
            ```python
            # Example for get_statistics
            res = await get_statistics()
            ```
    """
    try:
        raw = await rpc.get_stats()
        return Statistics.model_validate(raw, extra="ignore")
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise StatisticsError(f"Failed to get statistics: {exc}") from exc
