"""Tests for environment-driven configuration."""

from __future__ import annotations

import json
import os
from unittest import mock

from chatto_bridge.discord.config import BridgeConfig, ConfigError


def _env(**overrides: str) -> dict[str, str]:
    return {
        "DISCORD_BOT_TOKEN": "dtok",
        "DISCORD_GUILD_ID": "123",
        "CHATTO_BASE_URL": "https://chat.example.com",
        "CHATTO_LOGIN": "bot",
        "CHATTO_PASSWORD": "pass",
        "NATS_URL": "nats://localhost:4222",
        "BRIDGE_MAP": "{}",
        "LOG_LEVEL": "INFO",
        **overrides,
    }


def _patch_env(env: dict[str, str]) -> mock._patch:
    return mock.patch.dict(os.environ, env, clear=True)


def test_from_env_valid() -> None:
    env = _env(BRIDGE_MAP=json.dumps({"room-a": 10}))
    with _patch_env(env):
        cfg = BridgeConfig.from_env()
    assert cfg.discord_bot_token == "dtok"
    assert cfg.discord_guild_id == 123
    assert cfg.chatto_base_url == "https://chat.example.com"
    assert cfg.nats_url == "nats://localhost:4222"
    assert cfg.nats_auth_token is None
    assert cfg.room_to_channel == {"room-a": 10}
    assert cfg.log_level == "INFO"


def test_from_env_missing_required_var() -> None:
    env = _env()
    del env["DISCORD_BOT_TOKEN"]
    with _patch_env(env):
        try:
            BridgeConfig.from_env()
        except ConfigError as exc:
            assert "DISCORD_BOT_TOKEN" in str(exc)
        else:
            raise AssertionError("expected ConfigError")


def test_from_env_invalid_json() -> None:
    env = _env(BRIDGE_MAP="not-json")
    with _patch_env(env):
        try:
            BridgeConfig.from_env()
        except ConfigError as exc:
            assert "JSON" in str(exc)
        else:
            raise AssertionError("expected ConfigError")


def test_from_env_json_not_object() -> None:
    env = _env(BRIDGE_MAP=json.dumps(["room-a", 1]))
    with _patch_env(env):
        try:
            BridgeConfig.from_env()
        except ConfigError as exc:
            assert "object" in str(exc)
        else:
            raise AssertionError("expected ConfigError")


def test_from_env_wrong_value_types() -> None:
    env = _env(BRIDGE_MAP=json.dumps({"room-a": "not-an-int"}))
    with _patch_env(env):
        try:
            BridgeConfig.from_env()
        except ConfigError as exc:
            assert "integer" in str(exc)
        else:
            raise AssertionError("expected ConfigError")


def test_from_env_optional_fields() -> None:
    env = _env(NATS_AUTH_TOKEN="secret")
    del env["LOG_LEVEL"]
    with _patch_env(env):
        cfg = BridgeConfig.from_env()
    assert cfg.nats_auth_token == "secret"
    assert cfg.log_level == "INFO"


def test_channel_to_room_reverse() -> None:
    env = _env(BRIDGE_MAP=json.dumps({"r1": 10, "r2": 20}))
    with _patch_env(env):
        cfg = BridgeConfig.from_env()
    assert cfg.channel_to_room == {10: "r1", 20: "r2"}
