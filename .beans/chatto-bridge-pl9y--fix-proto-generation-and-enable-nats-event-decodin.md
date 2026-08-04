---
# chatto-bridge-pl9y
title: Fix proto generation and enable NATS event decoding
status: completed
type: task
priority: normal
created_at: 2026-08-04T10:55:22Z
updated_at: 2026-08-04T10:55:26Z
---

The generate_pb.sh script was incomplete — it only fetched 2 of 20 .proto files, missing transitive imports. Fixed by fetching the entire core/v1 directory via GitHub API. Updated events.py to add chatto_bridge/_pb to sys.path so protoc-generated imports resolve correctly. Verified: all 8 tests pass, proto bindings import successfully.
