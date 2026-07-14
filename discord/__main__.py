"""Entrypoint: `python -m chatto_bridge.discord` or the `chatto-bridge` script."""

from __future__ import annotations

import asyncio
import logging
import sys

from dotenv import load_dotenv

from chatto_bridge.discord.bot import ChattoBridgeBot
from chatto_bridge.discord.config import BridgeConfig, ConfigError


async def _run() -> None:
    config = BridgeConfig.from_env()
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bot = ChattoBridgeBot(config)
    async with bot:
        await bot.start(config.discord_bot_token)


def main() -> None:
    load_dotenv()
    try:
        asyncio.run(_run())
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
