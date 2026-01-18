#!/bin/bash
# Atomik Installer - https://github.com/aToom13/Atomik
# 
# Install:   curl -fsSL https://raw.githubusercontent.com/aToom13/Atomik/main/install.sh | bash
# Uninstall: curl -fsSL https://raw.githubusercontent.com/aToom13/Atomik/main/install.sh | bash -s -- --uninstall

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Symbols
CHECK="✓"
CROSS="✗"
ARROW="→"

# Installation directory
INSTALL_DIR="${ATOMIK_INSTALL_DIR:-$HOME/.local/share/atomik}"
BIN_DIR="${HOME}/.local/bin"
CONFIG_DIR="${ATOMIK_CONFIG_DIR:-$HOME/.atomik}"

# Banner
print_banner() {
    echo ""
    echo -e "${MAGENTA}"
    echo "     █████╗ ████████╗ ██████╗ ███╗   ███╗██╗██╗  ██╗"
    echo "    ██╔══██╗╚══██╔══╝██╔═══██╗████╗ ████║██║██║ ██╔╝"
    echo "    ███████║   ██║   ██║   ██║██╔████╔██║██║█████╔╝ "
    echo "    ██╔══██║   ██║   ██║   ██║██║╚██╔╝██║██║██╔═██╗ "
    echo "    ██║  ██║   ██║   ╚██████╔╝██║ ╚═╝ ██║██║██║  ██╗"
    echo "    ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "${DIM}    🎙️ Dijital Yoldaşın - Sesli AI Asistan${NC}"
    echo ""
}

# Print step
step() {
    echo -e "${BLUE}${ARROW}${NC} $1"
}

# Print success
success() {
    echo -e "${GREEN}${CHECK}${NC} $1"
}

# Print error
error() {
    echo -e "${RED}${CROSS}${NC} $1"
}

# Print warning
warn() {
    echo -e "${YELLOW}!${NC} $1"
}

# Print info
info() {
    echo -e "${DIM}  $1${NC}"
}

# Detect OS
detect_os() {
    OS="$(uname -s)"
    ARCH="$(uname -m)"
    
    case "$OS" in
        Linux*)     OS_TYPE="linux" ;;
        Darwin*)    OS_TYPE="darwin" ;;
        *)          OS_TYPE="unknown" ;;
    esac
}

# Check if command exists
has() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
check_dependencies() {
    echo ""
    echo -e "${BOLD}Checking dependencies...${NC}"
    echo ""
    
    local deps_ok=true
    local missing_deps=""
    
    # Check Python 3.10+
    if has python3; then
        local py_version=$(python3 --version | cut -d' ' -f2)
        local py_major=$(echo $py_version | cut -d. -f1)
        local py_minor=$(echo $py_version | cut -d. -f2)
        if [ "$py_major" -ge 3 ] && [ "$py_minor" -ge 10 ]; then
            success "python ${py_version}"
        else
            error "python ${py_version} (3.10+ required)"
            deps_ok=false
        fi
    else
        error "python3 not found"
        deps_ok=false
        missing_deps="$missing_deps python3"
    fi
    
    # Check pip
    if has pip3 || has pip; then
        local pip_cmd=$(has pip3 && echo "pip3" || echo "pip")
        success "$pip_cmd $($pip_cmd --version | cut -d' ' -f2)"
    else
        error "pip not found"
        deps_ok=false
    fi
    
    # Check git
    if has git; then
        success "git $(git --version | cut -d' ' -f3)"
    else
        error "git not found"
        deps_ok=false
        missing_deps="$missing_deps git"
    fi
    
    # Check PortAudio (for PyAudio)
    if [ "$OS_TYPE" = "linux" ]; then
        if pkg-config --exists portaudio-2.0 2>/dev/null || [ -f /usr/include/portaudio.h ]; then
            success "portaudio (for audio support)"
        else
            warn "portaudio not found (required for audio)"
            info "Install with: sudo apt install portaudio19-dev"
        fi
    fi
    
    # Check Ollama (optional, for offline mode)
    if has ollama; then
        success "ollama $(ollama --version 2>/dev/null | grep -oP 'version \K[\d.]+' || echo 'installed')"
        OLLAMA_INSTALLED=true
    else
        warn "ollama not found (optional, for offline mode)"
        OLLAMA_INSTALLED=false
    fi
    
    echo ""
    
    if [ "$deps_ok" = false ]; then
        error "Missing required dependencies."
        echo ""
        echo -e "${YELLOW}On Ubuntu/Debian:${NC}"
        echo -e "  sudo apt install python3 python3-pip python3-venv git portaudio19-dev"
        echo ""
        echo -e "${YELLOW}On Fedora:${NC}"
        echo -e "  sudo dnf install python3 python3-pip git portaudio-devel"
        echo ""
        echo -e "${YELLOW}On macOS:${NC}"
        echo -e "  brew install python portaudio"
        echo ""
        exit 1
    fi
}

# Clone or update repository
install_atomik() {
    step "Installing Atomik..."
    
    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    mkdir -p "$CONFIG_DIR"
    
    if [ -d "$INSTALL_DIR/.git" ]; then
        step "Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull origin main >/dev/null 2>&1 || {
            warn "Could not update, reinstalling..."
            cd /
            rm -rf "$INSTALL_DIR"
            git clone --depth 1 https://github.com/aToom13/Atomik.git "$INSTALL_DIR" >/dev/null 2>&1
        }
        success "Updated Atomik"
    else
        step "Cloning repository..."
        rm -rf "$INSTALL_DIR" 2>/dev/null || true
        git clone --depth 1 https://github.com/aToom13/Atomik.git "$INSTALL_DIR" >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            error "Failed to clone repository"
            exit 1
        fi
        success "Cloned Atomik"
    fi
    
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    step "Creating virtual environment..."
    python3 -m venv venv >/dev/null 2>&1
    success "Created virtual environment"
    
    # Install dependencies
    step "Installing Python dependencies..."
    echo -e "${DIM}    (This may take 5-10 minutes on first install)${NC}"
    echo -e "${DIM}    Heavy packages: chromadb, PyGObject may take a while to compile${NC}"
    echo ""
    
    local deps_log="/tmp/atomik_deps_$$.log"
    
    # Run pip install with progress output
    (source venv/bin/activate && pip install --upgrade pip >/dev/null 2>&1 && pip install -r requirements.txt 2>&1 | tee "$deps_log") &
    local pid=$!
    local elapsed=0
    local last_pkg=""
    
    while kill -0 $pid 2>/dev/null; do
        elapsed=$((elapsed + 1))
        
        # Try to get current package from log
        if [ -f "$deps_log" ]; then
            local current_pkg=$(grep -oP "(Collecting|Installing|Building) \K[^ ]+" "$deps_log" 2>/dev/null | tail -1)
            if [ -n "$current_pkg" ] && [ "$current_pkg" != "$last_pkg" ]; then
                last_pkg="$current_pkg"
                printf "\r${BLUE}◐${NC} Installing: ${CYAN}%s${NC} ${DIM}(${elapsed}s)${NC}            " "$current_pkg"
            elif [ $((elapsed % 10)) -eq 0 ]; then
                printf "\r${BLUE}◐${NC} Installing dependencies... ${DIM}(${elapsed}s)${NC}  "
            fi
        fi
        sleep 1
    done
    
    wait $pid
    local exit_code=$?
    printf "\r"
    
    if [ $exit_code -ne 0 ]; then
        error "Failed to install dependencies"
        echo -e "${DIM}Last 20 lines of log:${NC}"
        tail -20 "$deps_log" 2>/dev/null || echo "(no log)"
        exit 1
    fi
    success "Installed Python dependencies"
    
    # Create launcher script
    step "Creating launcher script..."
    cat > "$BIN_DIR/atomik" << 'LAUNCHER'
#!/bin/bash
INSTALL_DIR="${ATOMIK_INSTALL_DIR:-$HOME/.local/share/atomik}"
cd "$INSTALL_DIR"
source venv/bin/activate
exec python main.py "$@" 2>&1 | grep -v -E "(ALSA lib|Cannot connect to server|jack server|JackShm|Expression '.*' failed|paInvalidSampleRate)"
LAUNCHER
    chmod +x "$BIN_DIR/atomik"
    success "Created launcher script"
}

# Setup PATH
setup_path() {
    local shell_rc=""
    local path_line="export PATH=\"$BIN_DIR:\$PATH\""
    
    case "$SHELL" in
        */zsh)  shell_rc="$HOME/.zshrc" ;;
        */bash) 
            if [ -f "$HOME/.bashrc" ]; then
                shell_rc="$HOME/.bashrc"
            else
                shell_rc="$HOME/.bash_profile"
            fi
            ;;
        */fish) shell_rc="$HOME/.config/fish/config.fish" ;;
        *)      shell_rc="$HOME/.profile" ;;
    esac
    
    # Check if already in PATH
    if echo "$PATH" | grep -q "$BIN_DIR"; then
        info "PATH already configured"
        return 0
    fi
    
    # Add to shell config
    if [ -n "$shell_rc" ]; then
        if ! grep -q "# Atomik" "$shell_rc" 2>/dev/null; then
            echo "" >> "$shell_rc"
            echo "# Atomik" >> "$shell_rc"
            echo "$path_line" >> "$shell_rc"
            success "Added to PATH in $shell_rc"
        fi
    fi
    
    export PATH="$BIN_DIR:$PATH"
}

# Setup Ollama (optional)
setup_ollama() {
    if [ "$OLLAMA_INSTALLED" = true ]; then
        echo ""
        echo -e "${CYAN}┌─────────────────────────────────────────────────┐${NC}"
        echo -e "${CYAN}│${NC}  ${BOLD}🦙 Offline Mode Setup${NC}                         ${CYAN}│${NC}"
        echo -e "${CYAN}├─────────────────────────────────────────────────┤${NC}"
        echo -e "${CYAN}│${NC}  ${DIM}Download Gemma 3 model for offline use.${NC}       ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}  ${DIM}This allows Atomik to work without internet.${NC}  ${CYAN}│${NC}"
        echo -e "${CYAN}└─────────────────────────────────────────────────┘${NC}"
        echo ""
        
        if [ -e /dev/tty ]; then
            read -p "Download Gemma 3 model? (~2.5GB) [y/N] " -n 1 -r REPLY < /dev/tty
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                step "Downloading Gemma 3 model..."
                ollama pull gemma3:4b
                success "Downloaded Gemma 3 model"
            else
                info "Skipping Gemma 3 download"
                info "Run 'ollama pull gemma3:4b' later for offline mode"
            fi
        fi
    fi
}

# Verify installation
verify_installation() {
    echo ""
    step "Verifying installation..."
    
    if [ -x "$BIN_DIR/atomik" ]; then
        success "Atomik installed successfully!"
    else
        error "Installation verification failed"
        exit 1
    fi
}

# Print completion message
print_complete() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}${CHECK}${NC} ${BOLD}Atomik installed successfully!${NC}"
    echo ""
    echo -e "  ${DIM}Start with:${NC}"
    echo ""
    echo -e "    ${CYAN}atomik${NC}            ${DIM}# Online mode (Gemini API)${NC}"
    echo -e "    ${CYAN}atomik --offline${NC}  ${DIM}# Offline mode (Ollama)${NC}"
    echo ""
    echo -e "  ${DIM}Configuration:${NC}"
    echo -e "    ${DIM}Create .env file in $INSTALL_DIR with GEMINI_API_KEY${NC}"
    echo ""
    if ! echo "$PATH" | grep -q "$BIN_DIR"; then
        echo -e "  ${YELLOW}!${NC} ${DIM}Restart your terminal or run:${NC}"
        echo -e "    ${CYAN}source ~/.bashrc${NC}  ${DIM}(or ~/.zshrc)${NC}"
        echo ""
    fi
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Main installation flow
main_install() {
    print_banner
    detect_os
    
    echo -e "${DIM}  OS: ${OS_TYPE} | Arch: ${ARCH}${NC}"
    
    check_dependencies
    install_atomik
    setup_path
    setup_ollama
    verify_installation
    print_complete
}

# Uninstall function
uninstall() {
    print_banner
    
    echo -e "${YELLOW}${BOLD}Uninstalling Atomik...${NC}"
    echo ""
    
    local removed=false
    
    # Remove launcher
    if [ -f "$BIN_DIR/atomik" ]; then
        step "Removing launcher..."
        rm -f "$BIN_DIR/atomik"
        success "Removed $BIN_DIR/atomik"
        removed=true
    fi
    
    # Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        step "Removing installation..."
        rm -rf "$INSTALL_DIR"
        success "Removed $INSTALL_DIR"
        removed=true
    fi
    
    # Ask about config
    echo ""
    if [ -d "$CONFIG_DIR" ]; then
        echo -e "${YELLOW}Do you want to remove configuration?${NC}"
        echo -e "${DIM}  This will delete: $CONFIG_DIR${NC}"
        echo ""
        
        if [ -t 0 ]; then
            read -p "Remove config? [y/N] " -n 1 -r REPLY < /dev/tty
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$CONFIG_DIR"
                success "Removed $CONFIG_DIR"
                removed=true
            else
                info "Keeping configuration"
            fi
        fi
    fi
    
    echo ""
    if [ "$removed" = true ]; then
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "  ${GREEN}${CHECK}${NC} ${BOLD}Atomik uninstalled successfully!${NC}"
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    else
        warn "Atomik was not installed."
    fi
    echo ""
}

# Update function
update() {
    print_banner
    
    echo -e "${CYAN}${BOLD}Updating Atomik...${NC}"
    echo ""
    
    if [ ! -d "$INSTALL_DIR" ]; then
        warn "Atomik not found. Running fresh install."
        main_install
        return
    fi
    
    detect_os
    check_dependencies
    install_atomik
    verify_installation
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}${CHECK}${NC} ${BOLD}Atomik updated successfully!${NC}"
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Show help
show_help() {
    echo "Atomik Installer"
    echo ""
    echo "Usage:"
    echo "  install.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --update       Update Atomik to the latest version"
    echo "  --uninstall    Remove Atomik from the system"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  curl -fsSL .../install.sh | bash                      # Install"
    echo "  curl -fsSL .../install.sh | bash -s -- --update       # Update"
    echo "  curl -fsSL .../install.sh | bash -s -- --uninstall    # Uninstall"
}

# Parse arguments and run
case "${1:-}" in
    --update)
        update
        ;;
    --uninstall|-u)
        uninstall
        ;;
    --help|-h)
        show_help
        ;;
    *)
        main_install
        ;;
esac
