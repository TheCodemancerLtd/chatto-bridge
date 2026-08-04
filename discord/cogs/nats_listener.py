"""Subscribes to Chatto's `live.evt.room.>` republish subject on NATS.

Uses the plain NATS Core republish stream (mirror of the JetStream `EVT`
stream) rather than a durable JetStream consumer: the bridge is a
best-effort live tail, and every accepted `evt.room.…` publish is mirrored
once to `live.evt.room.…` for exactly this kind of external fanout. That
avoids having to persist a consumer cursor.

Decoded `RoomEvent`s are dispatched via `bot.dispatch("chatto_room_event",
event)` so any cog can subscribe with `@commands.Cog.listener(...)` — the
`ChattoToDiscord` cog is the primary consumer.
"""

from __future__ import annotations

import logging

import nats
from chatto_bridge.discord.bot import ChattoBridgeBot
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg
from nats.aio.subscription import Subscription

from chatto_bridge.events import decode_event
from discord.ext import commands

log = logging.getLogger(__name__)

ROOM_EVENTS_SUBJECT = "live.evt.room.>"


class NatsListener(commands.Cog):
    def __init__(self, bot: ChattoBridgeBot) -> None:
        self.bot = bot
        self.nc: NATSClient | None = None
        self.subscription: Subscription | None = None

    async def cog_load(self) -> None:
        opts: dict[str, object] = {"servers": [self.bot.engine.config.nats_url]}
        if self.bot.engine.config.nats_auth_token:
            opts["token"] = self.bot.engine.config.nats_auth_token
        self.nc = await nats.connect(**opts)  # type: ignore[arg-type]
        self.subscription = await self.nc.subscribe(
            ROOM_EVENTS_SUBJECT,
            cb=self._on_message,
        )
        log.info("subscribed to NATS subject %s", ROOM_EVENTS_SUBJECT)

    async def cog_unload(self) -> None:
        if self.subscription is not None:
            await self.subscription.unsubscribe()
            self.subscription = None
        if self.nc is not None:
            await self.nc.drain()
            self.nc = None

    async def _on_message(self, msg: Msg) -> None:
        try:
            event = decode_event(msg.subject, msg.data)
        except Exception:
            log.exception("failed to decode NATS message on %s", msg.subject)
            return
        if event is None:
            return
        self.bot.dispatch("chatto_room_event", event)


async def setup(bot: ChattoBridgeBot) -> None:
    await bot.add_cog(NatsListener(bot))
