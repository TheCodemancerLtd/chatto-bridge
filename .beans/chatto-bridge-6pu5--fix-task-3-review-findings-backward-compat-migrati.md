---
# chatto-bridge-6pu5
title: 'Fix Task 3 review findings: backward compat, migration, call sites'
status: completed
type: bug
priority: critical
created_at: 2026-08-04T14:25:29Z
updated_at: 2026-08-04T14:29:42Z
---

Fix critical review findings from Task 3: broken backward compat shim, no SQLite migration, old API call sites, persistence outside lock, incomplete test.


## Summary of Changes

All 5 review findings addressed:

1. **Backward compatibility shim:** Replaced broken re-export with simple shim in `discord/mapping.py`. Updated all production call sites in `discord/bot.py`, `discord/cogs/admin.py`, `discord/cogs/chatto_to_discord.py`, `discord/cogs/discord_to_chatto.py` to use new API signatures.

2. **SQLite migration:** Added `_ensure_schema()` in `Persistence` that detects old schema (missing `platform` column), adds the column with default `'discord'`, and rebuilds the table with proper constraints.

3. **Constructor dict conversion:** Updated `discord/bot.py` to convert `config.room_to_channel` (`dict[str, int]`) to `dict[tuple[str, str], int]` with `'discord'` platform.

4. **Persistence inside lock:** Moved `_persist_link()` and `_persist_delete()` calls inside the `with self._lock:` blocks in `link()` and `unlink()` methods.

5. **Test fix:** Added assertion that old value is gone in `test_env_var_overrides_persisted`.

Added migration test (`test_migration_adds_platform_column`) verifying old schema migrates correctly.

**Results:** 19/19 mapping tests pass, 52/52 total tests pass, ruff clean.
