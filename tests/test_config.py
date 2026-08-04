"""Tests for environment-driven configuration."""

from __future__ import annotations

import json
import os
from unittest import mock

from chatto_bridge.discord.config import DiscordConfig

from chatto_bridge.config import ConfigError


def _env(**overrides: str) -> dict[str, str]:
    return {
        "DISCORD_BOT_TOKEN": "dtok",
        "DISCORD_GUILD_ID": "123",
        **overrides,
    }


def _core_env(**overrides: str) -> dict[str, str]:
    return {
        "DISCORD_BOT_TOKEN": "dtok",
        "DISCORD_GUILD_ID": "123",
        "CHATTO_BASE_URL": "https://chat.example.com",
        "CHATTO_LOGIN": "bot",
        "CHATTO_PASSWORD": "pass",
        "NATS_URL": "nats://localhost:4222",
        "BRIDGE_MAP": "{}",
        "LOG_LEVEL": "INFO",
        "BRIDGE_PLUGINS": "discord",
        **overrides,
    }


def _patch_env(env: dict[str, str]) -> mock._patch:
    return mock.patch.dict(os.environ, env, clear=True)


# -- DiscordConfig tests ----------------------------------------------------


def test_discord_config_from_env() -> None:
    env = _env()
    with _patch_env(env):
        cfg = DiscordConfig.from_env()
    assert cfg.bot_token == "dtok"
    assert cfg.guild_id == 123


def test_discord_config_missing_token() -> None:
    env = _env()
    del env["DISCORD_BOT_TOKEN"]
    with _patch_env(env):
        try:
            DiscordConfig.from_env()
        except ConfigError as exc:
            assert "DISCORD_BOT_TOKEN" in str(exc)
        else:
            raise AssertionError("expected ConfigError")


def test_discord_config_missing_guild_id() -> None:
    env = _env()
    del env["DISCORD_GUILD_ID"]
    with _patch_env(env):
        try:
            DiscordConfig.from_env()
        except ConfigError as exc:
            assert "DISCORD_GUILD_ID" in str(exc)
        else:
            raise AssertionError("expected ConfigError")


# -- CoreConfig tests -------------------------------------------------------


def test_core_config_from_env() -> None:
    env = _core_env(BRIDGE_MAP=json.dumps({"room-a": 10}))
    with _patch_env(env):
        from chatto_bridge.config import CoreConfig

        cfg = CoreConfig.from_env()
    assert cfg.chatto_base_url == "https://chat.example.com"
    assert cfg.nats_url == "nats://localhost:4222"
    assert cfg.nats_auth_token is None
    assert cfg.bridge_map == {("room-a", "discord"): 10}
    assert cfg.log_level == "INFO"
    assert cfg.plugins == ["discord"]


def test_core_config_legacy_bridge_map() -> None:
    """Legacy format {"room": 123} should map to discord platform."""
    env = _core_env(BRIDGE_MAP=json.dumps({"room-a": 10}))
    with _patch_env(env):
        from chatto_bridge.config import CoreConfig

        cfg = CoreConfig.from_env()
    assert ("room-a", "discord") in cfg.bridge_map
    assert cfg.bridge_map[("room-a", "discord")] == 10


def test_core_config_new_bridge_map_format() -> None:
    """New format {"room": {"discord": [123]}} should parse correctly."""
    env = _core_env(BRIDGE_MAP=json.dumps({"room-a": {"discord": [10], "slack": ["C01"]}}))
    with _patch_env(env):
        from chatto_bridge.config import CoreConfig

        cfg = CoreConfig.from_env()
    assert cfg.bridge_map[("room-a", "discord")] == 10
    assert cfg.bridge_map[("room-a", "slack")] == "C01"


def test_core_config_missing_required_var() -> None:
    env = _core_env()
    del env["CHATTO_BASE_URL"]
    with _patch_env(env):
        try:
            from chatto_bridge.config import CoreConfig

            CoreConfig.from_env()
        except ConfigError as exc:
            assert "CHATTO_BASE_URL" in str(exc)
        else:
            raise AssertionError("expected ConfigError")


def test_core_config_invalid_json() -> None:
    env = _core_env(BRIDGE_MAP="not-json")
    with _patch_env(env):
        try:
            from chatto_bridge.config import CoreConfig

            CoreConfig.from_env()
        except ConfigError as exc:
            assert "JSON" in str(exc)
        else:
            raise AssertionError("expected ConfigError")


def test_core_config_plugins_env() -> None:
    env = _core_env(BRIDGE_PLUGINS="discord,slack")
    with _patch_env(env):
        from chatto_bridge.config import CoreConfig

        cfg = CoreConfig.from_env()
    assert cfg.plugins == ["discord", "slack"]


def test_core_config_nats_auth_token() -> None:
    env = _core_env(NATS_AUTH_TOKEN="secret")
    with _patch_env(env):
        from chatto_bridge.config import CoreConfig

        cfg = CoreConfig.from_env()
    assert cfg.nats_auth_token == "secret"
