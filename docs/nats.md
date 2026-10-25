# Chatto NATS subjects consumed by chatto-bridge

Reference: `chattocorp/chatto` — `cli/internal/events/subjects.go`,
`docs/adr/ADR-034-single-event-stream.md`,
`docs/adr/ADR-012-two-tier-realtime-events.md`.

## Overview

Chatto runs a single JetStream stream named `EVT` for durable events, and a
plain NATS Core republish subject tree at `live.evt.>` mirrors every accepted
`evt.>` publish exactly once. The bridge subscribes to the republish tree —
it doesn't need durable delivery guarantees, and it avoids having to track a
JetStream consumer cursor.

## Subscription

```
live.evt.room.>
```

Subject shape: `[live.]evt.room.{room_id}.{event_type}` — snake_case tokens.
Payload: protobuf-serialised `chatto.core.evt.v1.Event` (source of truth:
`proto/chatto/core/evt/v1/event.proto` in the Chatto repo).

## Event types the bridge cares about

The `Event` message has an `event` oneof; the token in the subject matches
the oneof case. Room-scoped cases include:

- `message_posted`
- `message_edited`
- `message_retracted`
- `message_body`
- `reaction_added`
- `reaction_removed`
- `user_joined`, `user_left`
- `room_member_added`, `room_member_removed`, `room_member_banned`,
  `room_member_unbanned`
- `room_created`, `room_updated`, `room_archived`, `room_deleted`
- `thread_created`, `thread_followed`, `thread_unfollowed`
- `call_started`, `call_joined`, `call_left`, `call_ended`

MVP `ChattoToDiscord` only handles `message_posted`; extending the switch is
the intended way to bridge more.

## Not used (yet)

- `live.sync.>` — transient `chatto.core.evt.v1.LiveEvent` payloads: typing
  indicators, presence, voice-call presence, notification sync, config
  invalidations. Cheap to add if the bridge needs presence propagation.
- Direct `evt.>` (JetStream) subscription — only needed for
  event-sourced replay / backfill, which is out of scope for a live bridge.

## Write path

**There is no NATS-side write path.** Publishing directly to `evt.>` would
bypass Chatto's authorization, RBAC, projection readiness, mentions, link
previews, and asset binding. The bridge posts via Chatto's ConnectRPC
`MessageService.PostMessage` (through `chattolib.ChattoClient.post_message`)
authenticated as a bot account.
