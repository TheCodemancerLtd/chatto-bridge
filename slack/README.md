# slack/

Placeholder for the future Slack ↔ Chatto side of the bridge.

Setuptools maps this directory to `chatto_bridge.slack`. When implemented,
mirror the shape of `discord/`:

```
slack/
├── __init__.py
├── __main__.py         # entrypoint: chatto-bridge-slack
├── bot.py              # slack_bolt AsyncApp wiring
├── config.py           # SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_TEAM_ID, …
├── mapping.py          # room ↔ slack channel ID
└── handlers/           # slack_bolt equivalent of discord cogs
```

The shared `chatto_bridge.events.RoomEvent` + NATS subscription code is
platform-agnostic and can be reused as-is; only the fan-out to Slack and
the reverse (Slack → Chatto via `chattolib.ChattoClient`) are Slack-
specific.
