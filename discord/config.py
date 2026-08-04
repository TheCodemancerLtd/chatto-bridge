"""Discord plugin configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from chatto_bridge.config import ConfigError


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"missing required env var: {name}")
    return value


def _optional(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class DiscordConfig:
    bot_token: str
    guild_id: int

    @classmethod
    def from_env(cls) -> DiscordConfig:
        return cls(
            bot_token=_required("DISCORD_BOT_TOKEN"),
            guild_id=int(_required("DISCORD_GUILD_ID")),
        )
