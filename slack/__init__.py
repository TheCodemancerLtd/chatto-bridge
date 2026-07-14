"""Slack-side integration for chatto-bridge (placeholder).

This directory is reserved for the Slack bridge implementation. Setuptools
maps it to the import path `chatto_bridge.slack` so it does not shadow the
pypi `slack_sdk` package.

Nothing is wired up yet — the console script `chatto-bridge` currently only
launches the Discord side (`chatto_bridge.discord.__main__:main`). When the
Slack integration lands, extract shared config/mapping abstractions from
`chatto_bridge.discord` up into `chatto_bridge` (see the README).
"""
