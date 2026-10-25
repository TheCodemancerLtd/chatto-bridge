"""Forwards decoded Chatto room events into their linked Discord channel.

The `NatsListener` cog owns the NATS subscription and dispatches
`chatto_room_event` (a `chatto_bridge.events.RoomEvent`). This cog's
listener does the routing:

    RoomEvent.room_id  ── BridgeMap ──▶  Discord channel

For MVP, only `message_posted` is bridged as a webhook-authored message so
that the Chatto author's display name and avatar carry over. Edits and
reactions are logged but not yet mirrored — the switch statement is the
place to add them.
"""

from __future__ import annotations

import logging

from chatto_bridge.discord.bot import ChattoBridgeBot

import discord
from chatto_bridge.events import RoomEvent
from discord.ext import commands

log = logging.getLogger(__name__)

WEBHOOK_NAME = "chatto-bridge"


class ChattoToDiscord(commands.Cog):
    def __init__(self, bot: ChattoBridgeBot) -> None:
        self.bot = bot
        # Cache one webhook per Discord channel so we don't hit the API on
        # every forwarded message.
        self._webhooks: dict[int, discord.Webhook] = {}
        # Cache Chatto user_id -> display name lookups.
        self._authors: dict[str, str] = {}

    @commands.Cog.listener()
    async def on_chatto_room_event(self, event: RoomEvent) -> None:
        entries = self.bot.bridge_map.channels_for_room(event.room_id)
        channel_id: int | None = None
        for platform, cid in entries:
            if platform == "discord" and isinstance(cid, int):
                channel_id = cid
                break
        if channel_id is None:
            return

        if event.event_type == "message_posted":
            await self._forward_message_posted(channel_id, event)
        else:
            log.debug("unhandled event_type=%s room=%s", event.event_type, event.room_id)

    async def _forward_message_posted(self, channel_id: int, event: RoomEvent) -> None:
        # Since Chatto 0.5.0 (event-sourcing cutover, ADR-034) the NATS
        # `message_posted` payload is a thin hint: the message body lives in a
        # separate encrypted `MessageBodyEvent` and is NOT on the wire here.
        # Hydrate the full message (body included, decrypted server-side for
        # us) through the ConnectRPC API — same strategy chattolib's Bot uses.
        envelope_id = getattr(event.raw, "id", "") or ""
        if not envelope_id:
            return
        try:
            msg = await self.bot.chatto.get_message(event.room_id, envelope_id)
        except Exception:
            log.exception("failed to hydrate message %s in room %s", envelope_id, event.room_id)
            return
        if msg is None or not msg.body:
            return

        body = msg.body
        author_display = await self._author_display(msg.actor_id)
        if not author_display:
            author_display = "chatto"

        webhook = await self._get_webhook(channel_id)
        if webhook is None:
            log.warning("no webhook available for channel %s", channel_id)
            return

        try:
            await webhook.send(content=body, username=str(author_display))
        except discord.HTTPException:
            log.exception("failed to forward chatto message to discord")

    async def _author_display(self, user_id: str) -> str | None:
        """Resolve an author's display name via the Chatto directory API.

        The NATS event payloads never carried display names reliably after
        the 0.5.0 cutover, so we look the author up (cached per user).
        """
        if not user_id:
            return None
        cached = self._authors.get(user_id)
        if cached is not None:
            return cached
        try:
            members = await self.bot.chatto.batch_get_users([user_id])
        except Exception:
            log.warning("failed to resolve chatto user %s", user_id)
            return None
        for member in members:
            if member.user is not None and member.user.id == user_id:
                name = member.user.display_name or member.user.login or None
                if name:
                    self._authors[user_id] = name
                return name
        return None

    async def _get_webhook(self, channel_id: int) -> discord.Webhook | None:
        cached = self._webhooks.get(channel_id)
        if cached is not None:
            return cached
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return None
        for existing in await channel.webhooks():
            if existing.name == WEBHOOK_NAME:
                self._webhooks[channel_id] = existing
                return existing
        created = await channel.create_webhook(name=WEBHOOK_NAME)
        self._webhooks[channel_id] = created
        return created


async def setup(bot: ChattoBridgeBot) -> None:
    await bot.add_cog(ChattoToDiscord(bot))
