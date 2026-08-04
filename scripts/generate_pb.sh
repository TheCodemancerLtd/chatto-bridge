#!/usr/bin/env bash
# Fetch Chatto's core-event proto sources and generate Python bindings.
#
# Chatto publishes `chatto.core.v1.Event` messages onto the NATS `evt.>`
# (durable) and `live.evt.>` (republish) subjects. The bridge needs the
# core/v1 tree to decode room events; the api/v1 / realtime/v1 trees are
# already available in `chattolib._pb`.
#
# Requires `protoc`, `curl`, and `jq` on PATH. Idempotent — safe to re-run.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="${REPO_ROOT}/proto"
OUT_DIR="${REPO_ROOT}/chatto_bridge/_pb"
CHATTO_REF="${CHATTO_REF:-main}"
BASE_URL="https://raw.githubusercontent.com/chattocorp/chatto/${CHATTO_REF}"

# Fetch the directory listing from GitHub to get all .proto files in core/v1.
# This avoids maintaining a fragile manual file list.
CORE_V1_PATH="proto/chatto/core/v1"
echo "Fetching .proto files from chattocorp/chatto@${CHATTO_REF}:${CORE_V1_PATH}"

FILES_JSON=$(curl -fsSL "https://api.github.com/repos/chattocorp/chatto/contents/${CORE_V1_PATH}?ref=${CHATTO_REF}")
FILE_PATHS=$(echo "${FILES_JSON}" | jq -r '.[] | select(.type == "file") | .path')

if [ -z "${FILE_PATHS}" ]; then
    echo "ERROR: No .proto files found in ${CORE_V1_PATH}. Chatto repo structure may have changed." >&2
    exit 1
fi

mkdir -p "${PROTO_DIR}"
while IFS= read -r path; do
    # Strip the leading "proto/" so files land under ${PROTO_DIR}/chatto/...
    # and protoc's --proto_path=${PROTO_DIR} resolves imports correctly.
    rel_path="${path#proto/}"
    dest="${PROTO_DIR}/${rel_path}"
    mkdir -p "$(dirname "${dest}")"
    curl -fsSL "${BASE_URL}/${path}" -o "${dest}"
    echo "  ${dest}"
done <<< "${FILE_PATHS}"

echo "Generating Python bindings into ${OUT_DIR}"
mkdir -p "${OUT_DIR}"
protoc \
    --proto_path="${PROTO_DIR}" \
    --python_out="${OUT_DIR}" \
    $(find "${PROTO_DIR}" -name '*.proto')

# Ensure every generated directory is an importable package.
find "${OUT_DIR}" -type d -exec touch {}/__init__.py \;

echo "Done."