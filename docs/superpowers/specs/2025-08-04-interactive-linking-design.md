# Interactive Room Linking & SQLite Persistence

## Overview

Replace the JSON-file bridge map persistence with SQLite, and add an
interactive `/bridge link` command on the Discord side that lets users
discover and select Chatto rooms without knowing their ULIDs.

## Part 1 — SQLite Persistence

### Motivation

The current JSON-file approach works for the bridge map but is not
composable — it cannot hold additional tables for future features such as
message caching during network issues. SQLite (via Python's stdlib `sqlite3`)
gives us a single durable store that can grow.

### Architecture

A new `Persistence` class wraps `sqlite3` and owns the connection.
`BridgeMap` takes a `Persistence` instance (or a path string, which creates
one) instead of a file path.

**Table schema:**

```sql
CREATE TABLE bridges (
    room_id    TEXT    PRIMARY KEY,
    channel_id INTEGER UNIQUE NOT NULL
);
```

- `room_id` is the Chatto room ULID (primary key — one-to-one mapping).
- `channel_id` has a `UNIQUE` constraint (a Discord channel cannot bridge
  two rooms).
- `BRIDGE_MAP` env var entries are merged on top of persisted state on
  startup (env takes precedence).

**Class interface:**

```python
class Persistence:
    def __init__(self, path: str) -> None: ...  # ":memory:" for tests
    def load_bridges(self) -> dict[str, int]: ...
    def upsert_bridge(self, room_id: str, channel_id: int) -> None: ...
    def delete_by_room(self, room_id: str) -> bool: ...
    def delete_by_channel(self, channel_id: int) -> bool: ...
    def close(self) -> None: ...
```

`BridgeMap` calls these instead of JSON read/write. The existing `RLock`
guards all mutations; SQLite is accessed single-threaded so no additional
locking is needed.

### Migration

- `discord/mapping.py` — new `Persistence` class; `BridgeMap` uses it
- `discord/bot.py` — change `path="chatto-bridge.json"` to
  `path="chatto-bridge.db"`
- `tests/test_mapping.py` — switch to `Persistence(":memory:")`
- `README.md` — update persistence file reference
- `.gitignore` — already has `chatto-bridge.db`; remove `.json` entry

## Part 2 — Interactive `/bridge link`

### User flows

**Discovery (no argument):**

1. Admin runs `/bridge link` in a Discord channel.
2. Bot calls `chattolib.ChattoClient.list_rooms()` and builds a numbered
   list of room names (excluding archived rooms).
3. Bot sends a follow-up message:
   ```
   Available Chatto rooms:
   1. General
   2. Engineering
   3. Random
   Reply with a number (1-3) to link this channel.
   ```
4. Admin replies with a number. Bot links the room and confirms.
5. If no reply within 30 s, the prompt times out and is deleted.

**Fuzzy search:**

1. Admin runs `/bridge link engineering`.
2. Bot filters rooms whose name contains `"engineering"` (case-insensitive).
3. If matches found, shows numbered list as above.
4. If no matches, replies "No rooms matching 'engineering'."

**Direct ULID:**

1. Admin runs `/bridge link r3m5t7...`.
2. Bot links directly (existing behavior).

**Chatto room URL:**

1. Admin runs `/bridge link https://chat.chatto.run/room/r3m5t7...`.
2. Bot extracts the ULID from the URL path and links.

### Implementation

- Extend the `Admin` cog's `link` command to make `room_id` optional
  (`default=None`).
- When `room_id` is `None`, trigger the discovery flow.
- When `room_id` starts with `http`, parse the URL for the room ULID.
- Room list is fetched via `self.bot.chatto.list_rooms()`.
- Selection uses `self.bot.wait_for("message", timeout=30)` with a filter
  that checks author and channel. Invalid replies get up to 3 retries.

### Error handling

- `list_rooms()` failure → ephemeral error message, no prompt.
- Timeout → delete the prompt message, no link created.
- Invalid reply → "Please reply with a number (1-N)." (up to 3 retries).
- URL parsing failure → "Could not extract room ID from URL."

### Constraints

- Requires the bot to already be logged into Chatto (`setup_hook` has run).
  If `/bridge link` is called before login, show "Bot is still starting up."
- Archived rooms are excluded from the room list.
- Discord channel listing is available via `bot.get_guild(guild_id).channels`
  but is not needed for the current scope (Discord-side only).

## Testing

- `Persistence` unit tests with `:memory:` database (CRUD, constraint
  violations, concurrent access).
- `BridgeMap` tests updated to use `Persistence(":memory:")`.
- Admin cog tests for discovery flow with mocked `list_rooms()` and
  `wait_for()`.
- URL parsing unit tests.