---
# chatto-bridge-rsaw
title: Migrate BridgeMap from JSON to SQLite persistence
status: completed
type: task
priority: normal
created_at: 2026-08-04T12:33:04Z
updated_at: 2026-08-04T12:34:51Z
---

Task 2: Replace JSON _load/_save in BridgeMap with Persistence class calls, update tests, update bot.py.

\n\n## Checklist\n\n- [x] Step 1: Rewrite BridgeMap to use Persistence\n- [x] Step 2: Update BridgeMap tests\n- [x] Step 3: Update bot.py\n- [x] Step 4: Run all tests\n- [x] Step 5: Run ruff on changed files\n- [x] Step 6: Commit

## Summary of Changes

Replaced JSON-based _load/_save methods in BridgeMap with Persistence class calls. Updated tests to use :memory: SQLite instead of JSON files. Changed bot.py to use .db extension and added bridge_map.close() to shutdown.
