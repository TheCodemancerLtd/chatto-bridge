"""discord.py-specific bits of chatto-bridge.

Setuptools maps this on-disk `discord/` directory to the import path
`chatto_bridge.discord` (see `package-dir` in `pyproject.toml`), so it does
not shadow the pypi `discord.py` package at import time. Code inside this
package is free to `import discord` normally.
"""
