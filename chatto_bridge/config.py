"""Core (platform-agnostic) configuration for the bridge.

Holds Chatto credentials, NATS settings, bridge map, and plugin selection.
Platform-specific config (DiscordConfig, SlackConfig, etc.) lives in each
plugin's own config module.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when a required env var is missing or malformed."""


def _required(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise ConfigError(f"missing required env var: {name}")
    return value


def _optional(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class CoreConfig:
    """Platform-agnostic bridge configuration."""

    chatto_base_url: str
    chatto_bot_key: str

    nats_url: str
    nats_auth_token: str | None

    # chatto_room_id (str) -> {platform: [channel_ids]}
    bridge_map: dict[tuple[str, str], str | int]

    log_level: str

    plugins: list[str]

    @classmethod
    def from_env(cls) -> CoreConfig:
        raw_map = _optional("BRIDGE_MAP", "{}") or "{}"
        try:
            parsed = json.loads(raw_map)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"BRIDGE_MAP is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ConfigError("BRIDGE_MAP must be a JSON object")

        bridge_map: dict[tuple[str, str], str | int] = {}
        for room, platforms in parsed.items():
            if not isinstance(room, str):
                raise ConfigError("BRIDGE_MAP keys must be string room IDs")
            if isinstance(platforms, int):
                # Legacy format: {"room": 123} -> {"room": {"discord": [123]}}
                bridge_map[(room, "discord")] = platforms
            elif isinstance(platforms, dict):
                for platform, channels in platforms.items():
                    if not isinstance(channels, list):
                        raise ConfigError(
                            f"BRIDGE_MAP platform values must be lists, "
                            f"got {type(channels).__name__}"
                        )
                    for ch in channels:
                        bridge_map[(room, platform)] = ch
            else:
                raise ConfigError(
                    f"BRIDGE_MAP values must be int or dict, got {type(platforms).__name__}"
                )

        plugins_env = _optional("BRIDGE_PLUGINS", "discord") or "discord"
        plugins = [p.strip() for p in plugins_env.split(",") if p.strip()]

        return cls(
            chatto_base_url=_required("CHATTO_BASE_URL"),
            chatto_bot_key=_required("CHATTO_BOT_KEY"),
            nats_url=_required("NATS_URL"),
            nats_auth_token=_optional("NATS_AUTH_TOKEN") or None,
            bridge_map=bridge_map,
            log_level=_optional("LOG_LEVEL", "INFO") or "INFO",
            plugins=plugins,
        )
