"""Shared (chatto-side) code for the chatto-bridge project.

Anything in this package is platform-agnostic and speaks only to Chatto:
NATS subject parsing, the protobuf-decoded `RoomEvent` shape, and (later)
the generated `chatto.core.v1` bindings under `_pb/`.

Platform integrations live in sibling top-level directories that setuptools
remaps into subpackages of this one:

- `chatto_bridge.discord` — sources under `/discord/`
- `chatto_bridge.slack` — sources under `/slack/` (placeholder)
"""

__version__ = "0.1.0"
