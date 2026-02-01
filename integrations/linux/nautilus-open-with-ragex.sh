#!/usr/bin/env bash
set -euo pipefail

CLI_SHIM="__CLI_SHIM_PATH__"
if [[ ! -x "$CLI_SHIM" ]]; then
    CLI_SHIM="$(command -v ragex 2>/dev/null || true)"
fi

if [[ -z "$CLI_SHIM" ]]; then
    zenity --error --title="RAGex" --text="Could not find the ragex command. Make sure it is on your PATH." 2>/dev/null || \
        notify-send "RAGex" "Could not find the ragex launcher" 2>/dev/null || \
        echo "[RAGex] ragex command not found" >&2
    exit 1
fi

# Create a temporary script that properly handles all arguments
TEMP_SCRIPT=$(mktemp)
trap 'rm -f "$TEMP_SCRIPT"' EXIT

{
    echo '#!/usr/bin/env bash'
    echo 'set -euo pipefail'
    echo ''
    # Export the CLI_SHIM and arguments
    printf 'CLI_SHIM=%q\n' "$CLI_SHIM"
    echo 'ARGS=('
    for arg in "$@"; do
        printf '  %q\n' "$arg"
    done
    echo ')'
    echo ''
    echo '"$CLI_SHIM" "${ARGS[@]}"'
    echo 'echo ""'
    echo 'echo "Press Enter to close..."'
    echo 'read'
} > "$TEMP_SCRIPT"

chmod +x "$TEMP_SCRIPT"

# Launch terminal executing the script
if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal -- bash "$TEMP_SCRIPT"
elif command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -e bash "$TEMP_SCRIPT"
else
    bash "$TEMP_SCRIPT"
fi
