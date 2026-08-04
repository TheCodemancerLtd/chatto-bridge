"""Backward compatibility — re-exports from chatto_bridge.mapping."""

from __future__ import annotations

from chatto_bridge.mapping import BridgeMap, Persistence  # noqa: F401

__all__ = ["BridgeMap", "Persistence"]
