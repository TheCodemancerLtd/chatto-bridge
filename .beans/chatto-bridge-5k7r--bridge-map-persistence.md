---
# chatto-bridge-5k7r
title: Bridge map persistence
status: completed
type: feature
priority: normal
created_at: 2026-08-04T10:56:05Z
updated_at: 2026-08-04T10:57:39Z
---

Add JSON file-based persistence to BridgeMap so /bridge link survives restart. File stored at chatto-bridge.json in the working directory. Load on startup, merge with BRIDGE_MAP env var (env takes precedence). Save on every link/unlink.
