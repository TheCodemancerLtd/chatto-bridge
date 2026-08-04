"""Room ID resolution: plain ULID, Chatto URL, or None."""

from __future__ import annotations

import re
from urllib.parse import urlparse

_ROOM_URL_RE = re.compile(r"/room/([A-Za-z0-9]+)")


def resolve_room_id(raw: str) -> str | None:
    """Return a Chatto room ULID from various input formats.

    Handles:
    - Plain ULID (26 Crockford Base32 chars)
    - Chatto room URL (https://.../room/<ulid>)
    - Empty string returns None
    - Unrecognized strings are returned as-is (caller decides)
    """
    if not raw:
        return None

    # Try URL extraction first
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https"):
        m = _ROOM_URL_RE.search(parsed.path)
        if m:
            return m.group(1)
        return None

    # Plain ULID or arbitrary string — pass through
    return raw
