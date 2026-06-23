"""Ports layer for hexagonal architecture.

Re-exports all Protocol definitions so consumers can import from
``piazza_sdk.ports`` directly::

    from piazza_sdk.ports import AuthProtocol, RPCProtocol, SessionManagerProtocol
"""

from __future__ import annotations

from piazza_sdk.ports.auth import AuthProtocol, SessionConfigProtocol, TokenStorageProtocol
from piazza_sdk.ports.http import HTTPClientProtocol, RPCProtocol
from piazza_sdk.ports.session import SessionManagerProtocol

__all__ = [
    "AuthProtocol",
    "HTTPClientProtocol",
    "RPCProtocol",
    "SessionConfigProtocol",
    "SessionManagerProtocol",
    "TokenStorageProtocol",
]
