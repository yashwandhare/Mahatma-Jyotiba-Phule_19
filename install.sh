#!/usr/bin/env bash

set -euo pipefail
IFS=$'\n\t'

# Color codes matching CLI style
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
DIM="\033[2m"
BOLD="\033[1m"
RESET="\033[0m"

LOG_PREFIX="${CYAN}${BOLD}RAGex${RESET}"
DEFAULT_INSTALL_DIR="${RAGEX_INSTALL_DIR:-$HOME/ragex}"
DEFAULT_REPO_URL="${RAGEX_REPO_URL:-https://github.com/ragex-labs/RAGex.git}"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)"
OLLAMA_STATUS=""
LINUX_DESKTOP_INSTALLED=0
LINUX_NAUTILUS_INSTALLED=0
MAC_SERVICE_INSTALLED=0

if git -C "$SCRIPT_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    repo_guess=$(git -C "$SCRIPT_PATH" config --get remote.origin.url || true)
    if [[ -n "$repo_guess" ]]; then
        DEFAULT_REPO_URL="$repo_guess"
    fi
fi

trap 'echo -e "\n$LOG_PREFIX ${YELLOW}Installation failed. Please review the messages above.${RESET}" >&2' ERR

print_header() {
    printf "\n${CYAN}${BOLD}"
    cat << 'EOF'
██████   █████   ██████  ███████ ██   ██ 
██   ██ ██   ██ ██       ██       ██ ██  
██████  ███████ ██   ███ █████     ███   
██   ██ ██   ██ ██    ██ ██       ██ ██  
██   ██ ██   ██  ██████  ███████ ██   ██
EOF
    printf "${RESET}\n"
    printf "${DIM}Installer v1.0.0${RESET}\n\n"
}

log_step() {
    printf "\n${CYAN}▶${RESET} ${BOLD}%s${RESET}\n" "$1"
}

log_info() {
    printf "${DIM}  %s${RESET}\n" "$1"
}

log_success() {
    printf "${GREEN}  ✔${RESET} %s\n" "$1"
}

log_warn() {
    printf "${YELLOW}  ⚠${RESET} %s\n" "$1"
}

replace_token_in_file() {
    local file_path=$1
    local token=$2
    local value=$3
    "$PYTHON_CMD" - <<'PY' "$file_path" "$token" "$value"
import sys
from pathlib import Path
path, token, value = sys.argv[1:4]
text = Path(path).read_text()
Path(path).write_text(text.replace(token, value))
PY
}

detect_os() {
    log_step "Detecting operating system"
    case "$(uname -s)" in
        Linux*)
            OS_NAME="linux"
            OS_LABEL="Linux"
            ;;
        Darwin*)
            OS_NAME="macos"
            OS_LABEL="macOS"
            ;;
        *)
            printf "%s Unsupported operating system. This installer supports Linux and macOS.\n" "$LOG_PREFIX" >&2
            exit 1
            ;;
    esac
    log_success "Detected $OS_LABEL"
}

require_command() {
    local cmd=$1
    local help_msg=${2:-""}
    if ! command -v "$cmd" >/dev/null 2>&1; then
        if [[ -n "$help_msg" ]]; then
            log_warn "$help_msg"
        fi
        printf "%s Missing required command: %s\n" "$LOG_PREFIX" "$cmd" >&2
        exit 1
    fi
}

expand_path() {
    local raw_path=$1
    "$PYTHON_CMD" - <<'PY'
import os, sys
raw = sys.argv[1]
print(os.path.abspath(os.path.expanduser(raw)))
PY
}

prompt_with_default() {
    local prompt_text=$1
    local default_value=$2
    local response
    read -r -p "$prompt_text [$default_value]: " response || true
    if [[ -z "$response" ]]; then
        response="$default_value"
    fi
    printf "%s" "$response"
}

confirm_yes() {
    local prompt_text=$1
    local default_choice=${2:-"n"}
    local response
    local hint="y/N"
    if [[ "$default_choice" == "y" || "$default_choice" == "Y" ]]; then
        hint="Y/n"
    fi
    while true; do
        read -r -p "$prompt_text ($hint): " response || true
        if [[ -z "$response" ]]; then
            response="$default_choice"
        fi
        case ${response,,} in
            y|yes)
                return 0
                ;;
            n|no)
                return 1
                ;;
            *)
                log_warn "Please answer with y or n."
                ;;
        esac
    done
}

select_model_mode() {
    printf "\nChoose how you want RAGex to run:\n"
    printf "  [1] Local (Ollama on this machine)\n"
    printf "  [2] Remote (Groq cloud inference)\n"
    local choice
    while true; do
        read -r -p "Mode [1]: " choice || true
        if [[ -z "$choice" ]]; then
            choice="1"
        fi
        case "$choice" in
            1|local|Local)
                MODEL_MODE="local"
                RAG_PROVIDER="ollama"
                DEFAULT_MODEL="mistral"
                break
                ;;
            2|remote|Remote)
                MODEL_MODE="remote"
                RAG_PROVIDER="groq"
                DEFAULT_MODEL="llama-3.3-70b-versatile"
                break
                ;;
            *)
                log_warn "Please enter 1 for local or 2 for remote."
                ;;
        esac
    done
}

collect_remote_details() {
    while true; do
        read -rsp "Enter your Groq API key (input hidden): " GROQ_API_KEY || true
        printf "\n"
        if [[ -n "$GROQ_API_KEY" ]]; then
            break
        fi
        log_warn "API key cannot be empty."
    done
}

collect_local_details() {
    if ! command -v ollama >/dev/null 2>&1; then
        log_warn "Ollama is not installed. Install it from https://ollama.com/download and run \"ollama serve\" separately."
        OLLAMA_STATUS="missing"
    else
        OLLAMA_STATUS="present"
        log_info "Detected Ollama ($(ollama --version 2>/dev/null || printf 'version unknown'))."
    fi
    GROQ_API_KEY=""
}

ask_model_name() {
    local prompt_text="Model name"
    read -r -p "$prompt_text [$DEFAULT_MODEL]: " MODEL_NAME || true
    if [[ -z "$MODEL_NAME" ]]; then
        MODEL_NAME="$DEFAULT_MODEL"
    fi
}

ask_offline_mode() {
    while true; do
        read -r -p "Enable offline mode by default? (y/N): " OFFLINE_CHOICE || true
        if [[ -z "$OFFLINE_CHOICE" ]]; then
            OFFLINE_CHOICE="n"
        fi
        case ${OFFLINE_CHOICE,,} in
            y|yes)
                RAG_OFFLINE=1
                if [[ "$MODEL_MODE" == "remote" ]]; then
                    log_warn "Offline mode only works with Ollama. Keeping remote mode but RAG_OFFLINE will be disabled."
                    RAG_OFFLINE=0
                fi
                break
                ;;
            n|no)
                RAG_OFFLINE=0
                break
                ;;
            *)
                log_warn "Please answer with y or n."
                ;;
        esac
    done
}

ensure_raw_dependencies() {
    log_step "Checking prerequisites"
    require_command git "Git is required to download RAGex."

    PYTHON_CMD=""
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
                PYTHON_CMD="$candidate"
                break
            fi
        fi
    done

    if [[ -z "$PYTHON_CMD" ]]; then
        printf "%s Python 3.10 or newer is required. Install it and rerun the installer.\n" "$LOG_PREFIX" >&2
        exit 1
    fi

    PYTHON_VERSION=$("$PYTHON_CMD" -c 'import platform; print(platform.python_version())')
    log_info "Using $PYTHON_CMD ($PYTHON_VERSION)."
}

clone_or_update_repo() {
    log_step "Preparing installation directory"
    INSTALL_DIR_RAW=$(prompt_with_default "Install RAGex to" "$DEFAULT_INSTALL_DIR")
    INSTALL_DIR=$(expand_path "$INSTALL_DIR_RAW")

    REPO_URL="$DEFAULT_REPO_URL"
    log_info "Target directory: $INSTALL_DIR"

    mkdir -p "$INSTALL_DIR"

    if [[ -d "$INSTALL_DIR/.git" ]]; then
        log_info "Existing repository detected; pulling latest changes."
        git -C "$INSTALL_DIR" fetch --all
        git -C "$INSTALL_DIR" pull --ff-only
    else
        if [[ -n $(ls -A "$INSTALL_DIR" 2>/dev/null) ]]; then
            if ! confirm_yes "Directory is not empty. Use it anyway?" "n"; then
                printf "%s Installation aborted. Choose an empty directory next time.\n" "$LOG_PREFIX"
                exit 1
            fi
        fi
        log_info "Cloning RAGex from $REPO_URL"
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi

    cd "$INSTALL_DIR"
}

setup_virtualenv() {
    log_step "Creating virtual environment"
    VENV_PATH="$INSTALL_DIR/.venv"
    if [[ -d "$VENV_PATH" ]]; then
        log_info "Reusing existing virtual environment."
    else
        "$PYTHON_CMD" -m venv "$VENV_PATH"
    fi
    VENV_PYTHON="$VENV_PATH/bin/python"
    "$VENV_PYTHON" -m pip install --upgrade pip >/dev/null
    log_step "Installing Python dependencies"
    "$VENV_PYTHON" -m pip install -r backend/requirements.txt
}

write_env_file() {
    log_step "Writing .env configuration"
    ENV_FILE="$INSTALL_DIR/.env"
    local vector_dir="$INSTALL_DIR/data/vectordb"
    mkdir -p "$vector_dir"

    if [[ -f "$ENV_FILE" ]]; then
        if ! confirm_yes ".env already exists. Overwrite with the new answers?" "y"; then
            log_warn "Keeping existing .env file."
            return
        fi
    fi

    cat > "$ENV_FILE" <<EOF
# Auto-generated by install.sh on $(date)
RAG_PROVIDER=$RAG_PROVIDER
RAG_MODEL_NAME=$MODEL_NAME
RAG_OFFLINE=$RAG_OFFLINE
GROQ_API_KEY=$GROQ_API_KEY
OLLAMA_BASE_URL=http://localhost:11434
VECTOR_DB_PATH=$vector_dir
COLLECTION_NAME=ragex_chunks
EOF
    chmod 600 "$ENV_FILE" || true
}

install_cli_shim() {
    log_step "Installing ragex launcher"
    local bin_dir="$HOME/.local/bin"
    local shim_path="$bin_dir/ragex"
    mkdir -p "$bin_dir"
    cat > "$shim_path" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$INSTALL_DIR"
exec "$INSTALL_DIR/.venv/bin/python" ragcli.py "\$@"
EOF
    chmod +x "$shim_path"
    if [[ ":$PATH:" != *":$bin_dir:"* ]]; then
        log_warn "$bin_dir is not in your PATH. Add it to PATH to run 'ragex' globally."
    fi
    CLI_SHIM_PATH="$shim_path"
}

install_linux_desktop_entry() {
    local desktop_src="$INSTALL_DIR/integrations/linux/ragex.desktop"
    if [[ ! -f "$desktop_src" ]]; then
        log_warn "Desktop entry template missing at $desktop_src"
        return
    fi
    local desktop_target="$HOME/.local/share/applications/ragex.desktop"
    mkdir -p "$(dirname "$desktop_target")"
    cp "$desktop_src" "$desktop_target"
    replace_token_in_file "$desktop_target" "__INSTALL_DIR__" "$INSTALL_DIR"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$(dirname "$desktop_target")" >/dev/null 2>&1 || true
    fi
    log_success "Installed desktop entry at $desktop_target"
    LINUX_DESKTOP_INSTALLED=1
}

install_nautilus_script() {
    local script_src="$INSTALL_DIR/integrations/linux/nautilus-open-with-ragex.sh"
    if [[ ! -f "$script_src" ]]; then
        log_warn "Nautilus script template missing at $script_src"
        return
    fi
    local nautilus_dir="$HOME/.local/share/nautilus/scripts"
    local script_target="$nautilus_dir/Open with RAGex"
    mkdir -p "$nautilus_dir"
    cp "$script_src" "$script_target"
    replace_token_in_file "$script_target" "__CLI_SHIM_PATH__" "$CLI_SHIM_PATH"
    chmod +x "$script_target"
    log_success "Installed Nautilus script at $script_target"
    LINUX_NAUTILUS_INSTALLED=1
}

setup_linux_integrations() {
    if confirm_yes "Install right-click launchers (desktop entry + Nautilus script)?" "n"; then
        install_linux_desktop_entry
        install_nautilus_script
        if command -v nautilus >/dev/null 2>&1; then
            log_info "Restart Nautilus (nautilus -q) to load the new script."
        fi
    else
        log_info "Skipping Linux desktop integration."
    fi
}

install_macos_service() {
    local workflow_src="$INSTALL_DIR/integrations/macos/Open with RAGex.workflow"
    if [[ ! -d "$workflow_src" ]]; then
        log_warn "Finder workflow template missing at $workflow_src"
        return
    fi
    local services_dir="$HOME/Library/Services"
    local workflow_target="$services_dir/Open with RAGex.workflow"
    mkdir -p "$services_dir"
    rm -rf "$workflow_target"
    cp -R "$workflow_src" "$workflow_target"
    replace_token_in_file "$workflow_target/Contents/document.wflow" "__CLI_SHIM_PATH__" "$CLI_SHIM_PATH"
    log_success "Installed Finder Quick Action at $workflow_target"
    MAC_SERVICE_INSTALLED=1
}

setup_macos_integrations() {
    if confirm_yes "Install the Finder 'Open with RAGex' Quick Action?" "n"; then
        install_macos_service
        log_info "Enable it via System Settings → Privacy & Security if macOS prompts for permissions."
    else
        log_info "Skipping macOS Finder integration."
    fi
}

print_summary() {
    printf "\n${CYAN}${BOLD}╭─────────────────────────────────────────────────────────────╮${RESET}\n"
    printf "${CYAN}${BOLD}│${RESET}                 ${GREEN}✔${RESET} ${BOLD}Installation Complete${RESET}                  ${CYAN}${BOLD}│${RESET}\n"
    printf "${CYAN}${BOLD}╰─────────────────────────────────────────────────────────────╯${RESET}\n\n"
    printf "${DIM}Location${RESET}      %s\n" "$INSTALL_DIR"
    printf "${DIM}Provider${RESET}      %s\n" "$RAG_PROVIDER"
    printf "${DIM}Model${RESET}         %s\n" "$MODEL_NAME"
    printf "${DIM}Offline mode${RESET}  %s\n" "$([[ "$RAG_OFFLINE" -eq 1 ]] && echo "enabled" || echo "disabled")"
    printf "${DIM}Command${RESET}       ${CYAN}%s${RESET}\n" "$CLI_SHIM_PATH"

    if [[ "$MODEL_MODE" == "local" && "$OLLAMA_STATUS" == "missing" ]]; then
        printf "\n${YELLOW}⚠ Ollama not detected${RESET}\n"
        printf "${DIM}  Install from https://ollama.com/download and start with 'ollama serve'${RESET}\n"
    fi

    if [[ "$LINUX_DESKTOP_INSTALLED" -eq 1 ]]; then
        printf "\n${GREEN}✔${RESET} ${BOLD}Linux Integration${RESET}\n"
        printf "${DIM}  Desktop entry: ~/.local/share/applications/ragex.desktop${RESET}\n"
        printf "${DIM}  Nautilus script: ~/.local/share/nautilus/scripts/Open with RAGex${RESET}\n"
        printf "${DIM}  Remove those files to disable right-click launchers.${RESET}\n"
    fi

    if [[ "$MAC_SERVICE_INSTALLED" -eq 1 ]]; then
        printf "\n${GREEN}✔${RESET} ${BOLD}macOS Integration${RESET}\n"
        printf "${DIM}  Quick Action: ~/Library/Services/Open with RAGex.workflow${RESET}\n"
        printf "${DIM}  Enable in System Settings → Privacy & Security if prompted.${RESET}\n"
        printf "${DIM}  Delete the workflow to remove it.${RESET}\n"
    fi

    printf "\n${BOLD}Usage${RESET}\n"
    printf "${CYAN}  ragex${RESET}\n"
    printf "${CYAN}  ragex <path>${RESET}\n"
    printf "${CYAN}  ragex --ask \"question\"${RESET}\n"
    printf "\n"
}

print_header
detect_os
ensure_raw_dependencies
select_model_mode
if [[ "$MODEL_MODE" == "remote" ]]; then
    collect_remote_details
else
    collect_local_details
fi
ask_model_name
ask_offline_mode
clone_or_update_repo
setup_virtualenv
write_env_file
install_cli_shim
if [[ "$OS_NAME" == "linux" ]]; then
    setup_linux_integrations
elif [[ "$OS_NAME" == "macos" ]]; then
    setup_macos_integrations
fi
print_summary
