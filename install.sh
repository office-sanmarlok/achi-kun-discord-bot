#!/bin/bash
#
# Claude-Discord Bridge Installer
# This script sets up the Claude-Discord Bridge environment
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TOOLKIT_ROOT="$SCRIPT_DIR"

echo -e "${BLUE}🚀 Claude-Discord Bridge Installer${NC}"
echo "=================================="
echo ""

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check OS
check_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    else
        print_error "Unsupported OS: $OSTYPE"
        echo "This toolkit currently supports macOS and Linux only."
        exit 1
    fi
    print_success "Detected OS: $OS"
}

# Check Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo "Please install Python 3.8 or higher"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.8"
    
    # Use Python to compare versions instead of bc
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_error "Python $PYTHON_VERSION is too old (requires $REQUIRED_VERSION+)"
        exit 1
    fi
    
    print_success "Python $PYTHON_VERSION found"
}

# Check tmux
check_tmux() {
    if ! command -v tmux &> /dev/null; then
        print_error "tmux is not installed"
        echo ""
        echo "Please install tmux:"
        if [[ "$OS" == "macos" ]]; then
            echo "  brew install tmux"
        else
            echo "  sudo apt-get install tmux    # Debian/Ubuntu"
            echo "  sudo yum install tmux        # CentOS/RHEL"
        fi
        exit 1
    fi
    print_success "tmux found"
}

# Install Python dependencies
install_python_deps() {
    echo ""
    print_info "Installing Python dependencies..."
    
    # Create requirements file if not exists
    cat > "$TOOLKIT_ROOT/requirements.txt" << EOF
discord.py>=2.0.0
flask>=2.0.0
requests>=2.20.0
python-dotenv>=0.19.0
psutil>=5.8.0
EOF
    
    # Install dependencies
    if pip3 install -r "$TOOLKIT_ROOT/requirements.txt" > /dev/null 2>&1; then
        print_success "Python dependencies installed"
    else
        print_warning "Some dependencies failed to install"
        echo "You may need to install them manually:"
        echo "  pip3 install -r $TOOLKIT_ROOT/requirements.txt"
    fi
}

# Setup configuration
setup_config() {
    echo ""
    print_info "Setting up configuration..."
    
    # Migration from old config directory name
    OLD_CONFIG_DIR="$HOME/.claude-cli-toolkit"
    CONFIG_DIR="$HOME/.claude-discord-bridge"
    
    # Migrate if old exists and new doesn't
    if [ -d "$OLD_CONFIG_DIR" ] && [ ! -d "$CONFIG_DIR" ]; then
        mv "$OLD_CONFIG_DIR" "$CONFIG_DIR"
        print_success "Migrated config directory: $OLD_CONFIG_DIR → $CONFIG_DIR"
    fi
    
    mkdir -p "$CONFIG_DIR"
    
    # Check if already configured
    if [[ -f "$CONFIG_DIR/.env" ]]; then
        echo ""
        read -p "Configuration already exists. Overwrite? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing configuration"
            return
        fi
    fi
    
    # Get Discord bot token
    echo ""
    echo "Enter your Discord bot token:"
    echo "(Get one from https://discord.com/developers/applications)"
    read -s DISCORD_TOKEN
    echo ""
    
    if [[ -z "$DISCORD_TOKEN" ]]; then
        print_error "Discord token cannot be empty"
        exit 1
    fi
    
    # Get Discord channel IDs for sessions
    echo ""
    echo "Now let's set up your Discord sessions."
    echo "You can add up to 3 sessions (channels) initially."
    echo ""
    
    SESSIONS=()
    for i in 1 2 3; do
        echo "Session $i - Enter channel ID (or press Enter to skip):"
        read CHANNEL_ID
        
        if [[ -n "$CHANNEL_ID" ]]; then
            if [[ ! "$CHANNEL_ID" =~ ^[0-9]{15,20}$ ]]; then
                print_warning "Invalid channel ID format, skipping"
            else
                SESSIONS+=("$i:$CHANNEL_ID")
            fi
        fi
    done
    
    if [[ ${#SESSIONS[@]} -eq 0 ]]; then
        print_error "At least one session must be configured"
        exit 1
    fi
    
    # Get Claude Code configuration
    echo ""
    echo "Claude Code Configuration:"
    echo "Enter working directory for Claude Code sessions (default: current directory):"
    read CLAUDE_WORK_DIR
    CLAUDE_WORK_DIR=${CLAUDE_WORK_DIR:-$(pwd)}
    
    echo ""
    echo "Use --dangerously-skip-permissions option? (y/N):"
    read -n 1 -r SKIP_PERMS
    echo ""
    if [[ $SKIP_PERMS =~ ^[Yy]$ ]]; then
        CLAUDE_OPTIONS="--dangerously-skip-permissions"
    else
        CLAUDE_OPTIONS=""
    fi
    
    # Create .env file
    cat > "$CONFIG_DIR/.env" << EOF
# Claude-Discord Bridge Configuration
# This file contains sensitive information. Do not share!

DISCORD_BOT_TOKEN=$DISCORD_TOKEN
DEFAULT_SESSION=1
FLASK_PORT=5001
CLAUDE_WORK_DIR=$CLAUDE_WORK_DIR
CLAUDE_OPTIONS=$CLAUDE_OPTIONS
EOF
    
    chmod 600 "$CONFIG_DIR/.env"
    
    # Create sessions.json
    echo "{" > "$CONFIG_DIR/sessions.json"
    for i in "${!SESSIONS[@]}"; do
        IFS=':' read -r num channel <<< "${SESSIONS[$i]}"
        echo "  \"$num\": \"$channel\"" >> "$CONFIG_DIR/sessions.json"
        if [[ $i -lt $((${#SESSIONS[@]} - 1)) ]]; then
            echo "," >> "$CONFIG_DIR/sessions.json"
        fi
    done
    echo "}" >> "$CONFIG_DIR/sessions.json"
    
    print_success "Configuration saved"
}

# Add to PATH
setup_path() {
    echo ""
    print_info "Setting up PATH..."
    
    BIN_DIR="$TOOLKIT_ROOT/bin"
    
    # Detect shell
    SHELL_NAME=$(basename "$SHELL")
    RC_FILE=""
    
    case "$SHELL_NAME" in
        zsh)
            RC_FILE="$HOME/.zshrc"
            ;;
        bash)
            RC_FILE="$HOME/.bashrc"
            ;;
        *)
            print_warning "Unknown shell: $SHELL_NAME"
            echo "Please add the following to your shell configuration manually:"
            echo "  export PATH=\"$BIN_DIR:\$PATH\""
            return
            ;;
    esac
    
    # Check if already in PATH
    if grep -q "$BIN_DIR" "$RC_FILE" 2>/dev/null; then
        print_info "PATH already configured"
        return
    fi
    
    # Add to RC file
    echo "" >> "$RC_FILE"
    echo "# Claude-Discord Bridge" >> "$RC_FILE"
    echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$RC_FILE"
    
    print_success "Added to PATH in $RC_FILE"
    echo ""
    print_info "Please run: source $RC_FILE"
    print_info "Or open a new terminal for PATH changes to take effect"
}

# Create .gitignore
create_gitignore() {
    cat > "$TOOLKIT_ROOT/.gitignore" << EOF
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/

# Configuration
.env
sessions.json

# Runtime
*.pid
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
EOF
}

# Main installation flow
main() {
    echo "This installer will:"
    echo "  1. Check system requirements"
    echo "  2. Install Python dependencies"
    echo "  3. Configure Discord integration"
    echo "  4. Add commands to your PATH"
    echo ""
    
    read -p "Continue? (Y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    
    echo ""
    print_info "Checking system requirements..."
    check_os
    check_python
    check_tmux
    
    install_python_deps
    setup_config
    setup_path
    create_gitignore
    
    echo ""
    echo "=================================="
    print_success "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Open a new terminal or run: source ~/.${SHELL_NAME}rc"
    echo "  2. Run 'vai doctor' to verify installation"
    echo "  3. Run 'vai' to start the toolkit"
    echo ""
    echo "Commands available:"
    echo "  vai              - Start services"
    echo "  vai status       - Check status"
    echo "  vai doctor       - Run diagnostics"
    echo "  vexit            - Stop services"
    echo "  dp 'message'     - Send to Discord"
    echo ""
    print_info "Happy coding with Claude! 🤖"
}

# Run main function
main