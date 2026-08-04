"""Plugin protocol — the interface each platform plugin must implement."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BridgePlugin(Protocol):
    """Protocol that every platform plugin must satisfy."""

    name: str

    async def start(self, engine: Any) -> None: ...

    async def stop(self) -> None: ...

    async def send_outbound(
        self,
        room_id: str,
        channel_id: str | int,
        content: str,
        author: str,
    ) -> None: ...

    async def on_inbound_message(
        self,
        channel_id: str | int,
        content: str,
        author: str,
    ) -> None: ...

    async def list_channels(self) -> list[tuple[str | int, str]]: ...

    async def link_channel(self, room_id: str, channel_id: str | int) -> None: ...

    async def unlink_channel(self, channel_id: str | int) -> bool: ...
