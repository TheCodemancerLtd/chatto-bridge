#!/usr/bin/env bash
# Fetch Chatto's core-event proto sources and generate Python bindings.
#
# Chatto publishes `chatto.core.v1.Event` messages onto the NATS `evt.>`
# (durable) and `live.evt.>` (republish) subjects. The bridge only needs the
# core/v1 tree to decode room events; the api/v1 / realtime/v1 trees are
# already available in `chattolib._pb`.
#
# Requires `protoc` and `curl` on PATH. Idempotent — safe to re-run.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="${REPO_ROOT}/proto"
OUT_DIR="${REPO_ROOT}/src/chatto_bridge/_pb"
CHATTO_REF="${CHATTO_REF:-main}"
BASE_URL="https://raw.githubusercontent.com/chattocorp/chatto/${CHATTO_REF}"

# Add to this list as new core/v1 protos are introduced upstream.
FILES=(
    "proto/chatto/core/v1/event.proto"
    "proto/chatto/core/v1/live_events.proto"
)

echo "Fetching ${#FILES[@]} .proto file(s) from chattocorp/chatto@${CHATTO_REF}"
mkdir -p "${PROTO_DIR}"
for path in "${FILES[@]}"; do
    dest="${PROTO_DIR}/${path#proto/}"
    mkdir -p "$(dirname "${dest}")"
    curl -fsSL "${BASE_URL}/${path}" -o "${dest}"
    echo "  ${dest}"
done

echo "Generating Python bindings into ${OUT_DIR}"
mkdir -p "${OUT_DIR}"
protoc \
    --proto_path="${PROTO_DIR}" \
    --python_out="${OUT_DIR}" \
    $(find "${PROTO_DIR}" -name '*.proto')

# Ensure every generated directory is an importable package.
find "${OUT_DIR}" -type d -exec touch {}/__init__.py \;

echo "Done."
