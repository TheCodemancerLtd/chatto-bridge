"""Slack plugin stub."""

from __future__ import annotations

from typing import Any

from chatto_bridge.plugin import BridgePlugin


class SlackPlugin(BridgePlugin):
    name = "slack"

    async def start(self, engine: Any) -> None:
        raise NotImplementedError("Slack plugin not yet implemented")

    async def stop(self) -> None:
        pass

    async def send_outbound(
        self,
        room_id: str,
        channel_id: str | int,
        content: str,
        author: str,
    ) -> None:
        raise NotImplementedError

    async def on_inbound_message(
        self,
        channel_id: str | int,
        content: str,
        author: str,
    ) -> None:
        raise NotImplementedError

    async def list_channels(self) -> list[tuple[str | int, str]]:
        return []

    async def link_channel(self, room_id: str, channel_id: str | int) -> None:
        raise NotImplementedError

    async def unlink_channel(self, channel_id: str | int) -> bool:
        return False
