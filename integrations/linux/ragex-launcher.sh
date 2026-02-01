#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

VENV_PATH="${RAGEX_VENV:-$REPO_ROOT/.venv}"
PYTHON_BIN="${RAGEX_PYTHON:-python3}"
CLI_ENTRY="${RAGEX_CLI:-$REPO_ROOT/ragcli.py}"

if [[ ! -f "$CLI_ENTRY" ]]; then
    echo "[ragex] CLI entry not found at $CLI_ENTRY" >&2
    exit 1
fi

if [[ -d "$VENV_PATH" ]]; then
    # shellcheck source=/dev/null
    source "$VENV_PATH/bin/activate"
elif command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    :
else
    echo "[ragex] Neither virtualenv ($VENV_PATH) nor python command ($PYTHON_BIN) is available" >&2
    exit 1
fi

PY_CMD="${VIRTUAL_ENV:+python}"
if [[ -z "$PY_CMD" ]]; then
    PY_CMD="$PYTHON_BIN"
fi

exec "$PY_CMD" "$CLI_ENTRY" "$@"
