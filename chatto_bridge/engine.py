"""Bridge engine — manages plugin lifecycle and message routing.

Owns the Chatto client and bridge map. Plugins register inbound messages
through `register_inbound()` and receive outbound dispatch through
`send_outbound()` on the plugin.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from typing import TYPE_CHECKING

from chattolib import ChattoClient

from chatto_bridge.config import CoreConfig
from chatto_bridge.mapping import BridgeMap
from chatto_bridge.plugin import BridgePlugin

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


class BridgeEngine:
    """Central orchestrator: Chatto client, bridge map, plugin lifecycle."""

    def __init__(self, config: CoreConfig) -> None:
        self.config = config
        self._plugins: dict[str, BridgePlugin] = {}
        self._chatto: ChattoClient | None = None
        self._chatto_ready = False
        self._bridge_map = BridgeMap(config.bridge_map, path="chatto-bridge.db")

    @property
    def chatto(self) -> ChattoClient:
        if self._chatto is None:
            raise RuntimeError("Chatto client not initialized. Call start() first.")
        return self._chatto

    @property
    def chatto_ready(self) -> bool:
        return self._chatto_ready

    @property
    def bridge_map(self) -> BridgeMap:
        return self._bridge_map

    @property
    def plugins(self) -> dict[str, BridgePlugin]:
        return self._plugins

    async def start(self) -> None:
        """Initialize Chatto client and start all plugins."""
        self._chatto = await ChattoClient.login(
            self.config.chatto_login,
            self.config.chatto_password,
            base_url=self.config.chatto_base_url,
        )
        self._chatto_ready = True
        log.info("logged into chatto at %s", self.config.chatto_base_url)

        for plugin_name in self.config.plugins:
            plugin = self._load_plugin(plugin_name)
            if plugin is not None:
                await plugin.start(self)
                self._plugins[plugin.name] = plugin
                log.info("started plugin: %s", plugin.name)

    async def stop(self) -> None:
        """Stop all plugins and close Chatto client."""
        for name, plugin in list(self._plugins.items()):
            try:
                await plugin.stop()
                log.info("stopped plugin: %s", name)
            except Exception:
                log.exception("error stopping plugin %s", name)
        self._plugins.clear()

        if self._chatto is not None:
            try:
                await self._chatto.close()
            except Exception:
                log.exception("error closing chatto client")
            self._chatto = None
            self._chatto_ready = False

        self._bridge_map.close()

    def _load_plugin(self, name: str) -> BridgePlugin | None:
        """Load a plugin by name using entry points or direct import."""
        try:
            entry_point = importlib.metadata.entry_points(group="chatto_bridge.plugins").get(name)
            if entry_point is not None:
                factory = entry_point.load()
                return factory()
        except Exception:
            log.exception("failed to load plugin %s via entry point", name)

        # Fallback: try direct import from chatto_bridge.{name}.plugin
        try:
            module = importlib.import_module(f"chatto_bridge.{name}.plugin")
            cls_name = f"{name.capitalize()}Plugin"
            if hasattr(module, cls_name):
                return getattr(module, cls_name)()
        except ImportError:
            pass
        except Exception:
            log.exception("failed to load plugin %s via direct import", name)

        log.error("could not load plugin: %s", name)
        return None

    def register_inbound(
        self,
        platform: str,
        channel_id: str | int,
        content: str,
        author: str,
    ) -> None:
        """Register an inbound message from a platform for processing."""
        room_id = self._bridge_map.room_for_channel(platform, channel_id)
        if room_id is None:
            log.debug("no room mapping for %s channel %s", platform, channel_id)
            return

        body = f"**{author}**: {content}"
        asyncio.create_task(self._post_to_chatto(room_id, body))

    async def _post_to_chatto(self, room_id: str, body: str) -> None:
        """Post a message to Chatto."""
        try:
            await self.chatto.post_message(room_id=room_id, body=body)
        except Exception:
            log.exception("failed to post to chatto room %s", room_id)

    async def send_outbound(
        self,
        room_id: str,
        content: str,
        author: str,
    ) -> None:
        """Dispatch a message to all platforms linked to a room."""
        targets = self._bridge_map.channels_for_room(room_id)
        for platform, channel_id in targets:
            plugin = self._plugins.get(platform)
            if plugin is None:
                log.warning("no plugin for platform %s", platform)
                continue
            try:
                await plugin.send_outbound(room_id, channel_id, content, author)
            except Exception:
                log.exception("failed to send outbound to %s channel %s", platform, channel_id)

    async def run(self) -> None:
        """Start the engine and block on the first plugin's bot run loop.

        This is the main entry point for the application. It starts the engine,
        then blocks on the Discord bot's run loop (or whichever plugin provides
        a blocking run method).
        """
        await self.start()

        # Find the discord plugin and run its bot
        discord_plugin = self._plugins.get("discord")
        if discord_plugin is None:
            log.error("no discord plugin loaded")
            await self.stop()
            return

        # Access the bot through a public property on the plugin
        bot = getattr(discord_plugin, "bot", None)
        if bot is None:
            log.error("discord plugin has no bot")
            await self.stop()
            return

        # Get the token from the plugin's config through public API
        plugin_config = getattr(discord_plugin, "config", None)
        if plugin_config is None:
            log.error("discord plugin has no config")
            await self.stop()
            return

        token = getattr(plugin_config, "bot_token", None)
        if token is None:
            log.error("discord plugin config has no bot_token")
            await self.stop()
            return

        await bot.start(token)

        await self.stop()
