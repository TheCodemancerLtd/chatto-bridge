"""Environment-driven configuration for the bridge."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when a required env var is missing or malformed."""


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"missing required env var: {name}")
    return value


def _optional(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class BridgeConfig:
    discord_bot_token: str
    discord_guild_id: int

    chatto_base_url: str
    chatto_login: str
    chatto_password: str

    nats_url: str
    nats_auth_token: str | None

    # chatto_room_id (str) -> discord_channel_id (int)
    room_to_channel: dict[str, int]

    log_level: str

    @property
    def channel_to_room(self) -> dict[int, str]:
        return {channel: room for room, channel in self.room_to_channel.items()}

    @classmethod
    def from_env(cls) -> BridgeConfig:
        raw_map = _optional("BRIDGE_MAP", "{}") or "{}"
        try:
            parsed = json.loads(raw_map)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"BRIDGE_MAP is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ConfigError("BRIDGE_MAP must be a JSON object")
        room_to_channel: dict[str, int] = {}
        for key, value in parsed.items():
            if not isinstance(key, str) or not isinstance(value, int):
                raise ConfigError(
                    "BRIDGE_MAP must map string room IDs to integer channel IDs"
                )
            room_to_channel[key] = value

        return cls(
            discord_bot_token=_required("DISCORD_BOT_TOKEN"),
            discord_guild_id=int(_required("DISCORD_GUILD_ID")),
            chatto_base_url=_required("CHATTO_BASE_URL"),
            chatto_login=_required("CHATTO_LOGIN"),
            chatto_password=_required("CHATTO_PASSWORD"),
            nats_url=_required("NATS_URL"),
            nats_auth_token=_optional("NATS_AUTH_TOKEN") or None,
            room_to_channel=room_to_channel,
            log_level=_optional("LOG_LEVEL", "INFO") or "INFO",
        )
