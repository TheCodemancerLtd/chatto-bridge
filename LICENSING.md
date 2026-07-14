# Licensing

chatto-bridge uses per-file SPDX license metadata following the
[REUSE](https://reuse.software/) specification. The canonical
machine-readable licence boundary is in [REUSE.toml](REUSE.toml).

## Default: MPL-2.0

The bridge's own code — `chatto_bridge/*.py`, `discord/**`, `slack/**`
(except any `_pb/` subtree), `tests/`, `scripts/`, and repository
documentation — is licensed under the
**Mozilla Public License 2.0** (`MPL-2.0`). See [LICENSE](LICENSE) for the
full text.

MPL-2.0 is a **weak, file-level copyleft**:

- You can freely use, distribute, and embed chatto-bridge in commercial or
  proprietary software.
- If you modify a file of chatto-bridge itself and distribute the modified
  version, the modified file must be released under MPL-2.0.
- New files you add alongside chatto-bridge (adapters, plugins, your own
  application code) can be under any licence you like.

MPL-2.0 explicitly permits combination with GPL/LGPL/AGPL code via its
[§3.3 Secondary License](https://www.mozilla.org/en-US/MPL/2.0/#L342)
mechanism.

## Apache-2.0 carve-outs

If and when this repo vendors Chatto's core-event protobuf sources
(`chatto.core.v1.Event`, the NATS payload envelope) or their generated
Python bindings, those paths ship under **Apache License 2.0**:

- `proto/chatto/**` — mirrors of `chattocorp/chatto`'s `.proto` sources.
- `chatto_bridge/_pb/chatto/**` — the generated Python bindings derived
  from those sources.

Chatto's own [`REUSE.toml`](https://github.com/chattocorp/chatto/blob/main/REUSE.toml)
places these files under Apache-2.0 precisely so that downstream integrations
like chatto-bridge can be built with a licence of their own choice.

Full licence texts live in [`LICENSES/`](LICENSES/).
