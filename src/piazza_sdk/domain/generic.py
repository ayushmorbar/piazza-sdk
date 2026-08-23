"""Generic endpoints logic."""

from typing import Any

from piazza_sdk.api.rpc import RPC
from piazza_sdk.auth import SessionStateManager


async def page_event(
    rpc: RPC, *, session: SessionStateManager | None = None, type: str, **kwargs: Any
) -> bool:
    await rpc.generic_page_event(type=type, **kwargs)
    return True


async def sanitize_html(rpc: RPC, **kwargs: Any) -> dict[str, Any]:
    return await rpc.generic_sanitize_html(**kwargs)
