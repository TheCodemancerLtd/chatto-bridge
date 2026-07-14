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
python -m chatto_bridge.discord
```

## Chatto NATS subjects consumed

The bridge subscribes to Chatto's **plain NATS republish subject**
`live.evt.room.>` (mirror of the JetStream `EVT` stream), so no durable
JetStream consumer state has to be maintained. Payloads are the same
`chatto.core.v1.Event` protobuf envelope Chatto uses internally.

See [`docs/nats.md`](docs/nats.md) for the current list of relevant
event tokens (`message_posted`, `message_edited`, `reaction_added`, …).

## Layout

Sources are organised by chat platform, with shared (chatto-side) code at
the repo root. Setuptools remaps the on-disk `discord/` and `slack/`
directories into subpackages of `chatto_bridge` so that the `discord/`
folder does not shadow the pypi `discord.py` package at import time —
see `[tool.setuptools.package-dir]` in `pyproject.toml`.

```
/
├── chatto_bridge/            # shared, imported as `chatto_bridge`
│   ├── events.py             # RoomEvent, subject parser, protobuf decoder
│   └── _pb/                  # generated chatto.core.v1 bindings (gitignored)
├── discord/                  # imported as `chatto_bridge.discord`
│   ├── __main__.py           # entrypoint (also the `chatto-bridge` script)
│   ├── bot.py                # commands.Bot subclass; loads cogs
│   ├── config.py             # env → typed config
│   ├── mapping.py            # room ↔ discord channel map
│   └── cogs/
│       ├── nats_listener.py       # subscribe live.evt.room.>, dispatch to bot
│       ├── chatto_to_discord.py   # forward chatto events to discord webhooks
│       ├── discord_to_chatto.py   # forward discord messages via chattolib
│       └── admin.py               # /bridge link|unlink|list slash commands
├── slack/                    # imported as `chatto_bridge.slack` (placeholder)
├── proto/                    # vendored chatto.core.v1 protos (gitignored)
├── scripts/generate_pb.sh    # fetches protos + runs protoc
├── docs/nats.md              # subjects consumed + write-path rationale
├── tests/
└── pyproject.toml
```

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
