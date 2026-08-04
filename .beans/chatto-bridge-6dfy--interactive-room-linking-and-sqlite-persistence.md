---
# chatto-bridge-6dfy
title: Interactive room linking and SQLite persistence
status: completed
type: feature
priority: normal
created_at: 2026-08-04T12:16:42Z
updated_at: 2026-08-04T12:51:09Z
---

Two parts: (1) Replace JSON file persistence with SQLite for the bridge map, adding a Persistence class that wraps sqlite3 with a bridges table. Database is reusable for future features like message caching. (2) Add interactive /bridge link — when called without arguments, fetches Chatto rooms via chattolib.list_rooms(), shows numbered list, user replies with number. Supports fuzzy search (/bridge link <term>), raw ULID, and Chatto room URL parsing. Discord-side only.

## Design\n\nSpec at docs/superpowers/specs/2025-08-04-interactive-linking-design.md
