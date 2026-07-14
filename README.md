# chatto-bridge

**Unofficial** Discord ↔ [Chatto](https://chat.chatto.run) bridge bot. Built on
[discord.py](https://discordpy.readthedocs.io/) (cog system) and
[chattolib](https://pypi.org/project/chattolib/).

The bridge is intended to run co-located with the Chatto server so it can
speak directly to Chatto's NATS event bus for the Chatto → Discord direction.
The Discord → Chatto direction goes through Chatto's public ConnectRPC API
using a bot user account (chattolib's `ChattoClient`) — publishing raw
protobuf into NATS is not supported by Chatto and would bypass RBAC,
mentions, link previews, and asset binding.

## Data flow

```
                     ┌──────────────────────────┐
                     │        Chatto server     │
                     │   ┌────────────────────┐ │
                     │   │  NATS  (EVT + live)│ │
                     │   └─────────┬──────────┘ │
                     │             │ live.evt.room.>
                     │             ▼
                     │       ConnectRPC API ───────┐
                     └──────────────────────────┘  │
                                                   │
              live.evt.room.>  (protobuf Event)    │  POST /api/connect/…
                          │                        ▲
                          ▼                        │
                     ┌──────────────────────────┐  │
                     │        chatto-bridge     │──┘
                     │  ┌────────────────────┐  │
                     │  │ NatsListener  cog  │  │
                     │  │ ChattoToDiscord    │  │
                     │  │ DiscordToChatto    │  │
                     │  │ Admin              │  │
                     │  └────────────────────┘  │
                     └──────────────┬───────────┘
                                    │ discord.py gateway
                                    ▼
                            ┌─────────────┐
                            │   Discord   │
                            └─────────────┘
```

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Configure

Copy `.env.example` to `.env` and fill in credentials:

```bash
cp .env.example .env
```

Required env vars:

| Var | What |
|---|---|
| `DISCORD_BOT_TOKEN` | Bot token from the Discord developer portal |
| `DISCORD_GUILD_ID` | The guild (server) this bridge attaches to |
| `CHATTO_BASE_URL` | e.g. `https://chat.chatto.run` |
| `CHATTO_LOGIN` | Login for the Chatto bot account |
| `CHATTO_PASSWORD` | Password for the Chatto bot account |
| `NATS_URL` | e.g. `nats://localhost:4222` (Chatto's `CHATTO_NATS_CLIENT_URL`) |
| `NATS_AUTH_TOKEN` | optional; matches `CHATTO_NATS_EMBEDDED_AUTH_TOKEN` |
| `BRIDGE_MAP` | JSON: `{"<chatto_room_id>": <discord_channel_id>, ...}` |

## Run

```bash
chatto-bridge
# or
python -m chatto_bridge
```

## Chatto NATS subjects consumed

The bridge subscribes to Chatto's **plain NATS republish subject**
`live.evt.room.>` (mirror of the JetStream `EVT` stream), so no durable
JetStream consumer state has to be maintained. Payloads are the same
`chatto.core.v1.Event` protobuf envelope Chatto uses internally.

See [`docs/nats.md`](docs/nats.md) for the current list of relevant
event tokens (`message_posted`, `message_edited`, `reaction_added`, …).

## Layout

- `src/chatto_bridge/bot.py` — `commands.Bot` subclass; loads cogs.
- `src/chatto_bridge/cogs/nats_listener.py` — subscribes to `live.evt.room.>`
  and dispatches decoded events onto the bot's event loop.
- `src/chatto_bridge/cogs/chatto_to_discord.py` — turns Chatto events into
  Discord messages via webhooks (to preserve author display).
- `src/chatto_bridge/cogs/discord_to_chatto.py` — listens to Discord
  `on_message` and posts to Chatto via `chattolib.ChattoClient`.
- `src/chatto_bridge/cogs/admin.py` — `/bridge` slash commands for linking
  and unlinking rooms.
- `src/chatto_bridge/config.py` — env → typed config.
- `src/chatto_bridge/mapping.py` — Chatto room ↔ Discord channel mapping.
- `src/chatto_bridge/_pb/` — generated `chatto.core.v1` protobuf bindings.
  Regenerate with `scripts/generate_pb.sh`.

## License

- chatto-bridge's own code is licensed under **MPL-2.0** (Mozilla Public
  License 2.0) — a weak, file-level copyleft. You can use, distribute, and
  embed chatto-bridge in commercial or proprietary software; modifications
  to the bridge's own files must be released under MPL-2.0.
- Any vendored Chatto protobuf sources under `proto/chatto/**` and their
  generated bindings under `src/chatto_bridge/_pb/chatto/**` are
  **Apache-2.0**, matching upstream
  [`chattocorp/chatto`](https://github.com/chattocorp/chatto).

See [LICENSING.md](LICENSING.md) for the full picture and
[REUSE.toml](REUSE.toml) for the machine-readable licence map.
