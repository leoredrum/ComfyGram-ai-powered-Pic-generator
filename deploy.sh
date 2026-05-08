#!/bot/bash

# ComfyGram Deployment Script
# Deploy ComfyGram Telegram Bot for ComfyUI

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PROJECT_NAME="comfygram"
WORKSPACE_DIR="$HOME/$PROJECT_NAME/workspace"
HERMES_DIR="$HOME/.hermes"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}🚀 ComfyGram Deployment${NC}"
echo -e "${YELLOW}📁 Repository: $REPO_DIR${NC}"

# Check if Hermes is installed
if [ ! -d "$HERMES_DIR" ]; then
    echo -e "${RED}❌ Hermes not installed. Please install Hermes Agent first${NC}"
    exit 1
fi

# Create workspace directories
echo -e "${GREEN}📂 Creating workspace directories...${NC}"
mkdir -p "$WORKSPACE_DIR"
mkdir -p "$WORKSPACE_DIR/inbox"
mkdir -p "$WORKSPACE_DIR/outbox"
mkdir -p "$WORKSPACE_DIR/tmp"

# Copy files
echo -e "${GREEN}📋 Copying configuration files...${NC}"

# Hermes configuration
if [ -f "$REPO_DIR/hermes-config/config.yaml" ]; then
    cp "$REPO_DIR/hermes-config/config.yaml" "$HERMES_DIR/config.yaml"
    echo "✓ Updated Hermes main configuration"
fi

# ComfyGram profile
mkdir -p "$HERMES_DIR/profiles/$PROJECT_NAME"
cp -r "$REPO_DIR/hermes-config/profiles/$PROJECT_NAME/"* "$HERMES_DIR/profiles/$PROJECT_NAME/"
echo "✓ Copied $PROJECT_NAME profile"

# Workspace files
if [ -d "$REPO_DIR/workspace/bin" ]; then
    cp -r "$REPO_DIR/workspace/bin" "$WORKSPACE_DIR/"
fi
if [ -d "$REPO_DIR/workspace/workflows" ]; then
    cp -r "$REPO_DIR/workspace/workflows" "$WORKSPACE_DIR/"
fi
if [ -f "$REPO_DIR/workspace"/*.json ]; then
    cp "$REPO_DIR/workspace"/*.json "$WORKSPACE_DIR/"
fi
if [ -f "$REPO_DIR/workspace"/*.md ]; then
    cp "$REPO_DIR/workspace"/*.md "$WORKSPACE_DIR/"
fi
echo "✓ Copied workspace files"

# Environment variables configuration
if [ ! -f "$HERMES_DIR/profiles/$PROJECT_NAME/.env" ]; then
    if [ -f "$REPO_DIR/hermes-config/profiles/$PROJECT_NAME/.env.template" ]; then
        cp "$REPO_DIR/hermes-config/profiles/$PROJECT_NAME/.env.template" "$HERMES_DIR/profiles/$PROJECT_NAME/.env"
        echo -e "${YELLOW}⚠️  Please edit .env file with correct configuration${NC}"
    fi
fi

# LaunchAgent installation (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${GREEN}🔧 Installing LaunchAgent...${NC}"

    # Update plist file paths
    PLIST_FILE="$HOME/Library/LaunchAgents/com.github.$PROJECT_NAME.bot.plist"

    if [ -f "$REPO_DIR/scripts/com.github.$PROJECT_NAME.bot.plist" ]; then
        # Copy plist file (paths should already use $HOME or be template-based)
        cp "$REPO_DIR/scripts/com.github.$PROJECT_NAME.bot.plist" "$PLIST_FILE"

        # Update Python path (requires user verification)
        echo -e "${YELLOW}⚠️  Please verify Python path in LaunchAgent: $PLIST_FILE${NC}"
        echo -e "Default path: $HOME/Documents/ComfyUI/.venv/bot/python3"

        # Unload old service (if exists)
        launchctl unload "$PLIST_FILE" 2>/dev/null || true

        # Load new service
        launchctl load "$PLIST_FILE"

        echo -e "${GREEN}✓ LaunchAgent installed${NC}"
    fi
fi

# Set script executable permissions
chmod +x "$WORKSPACE_DIR/bin"/*.sh 2>/dev/null || true
chmod +x "$WORKSPACE_DIR/bin"/*.py 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Edit $HERMES_DIR/profiles/$PROJECT_NAME/.env with correct configuration"
echo "2. Ensure ComfyUI is installed and running at http://127.0.0.1:8000"
echo "3. Update Python path in LaunchAgent if needed"
echo "4. Start service: launchctl start com.github.$PROJECT_NAME.bot"
echo ""
echo -e "${YELLOW}📚 References:${NC}"
echo "- Hermes config: $HERMES_DIR"
echo "- Workspace: $WORKSPACE_DIR"
echo "- Logs: $WORKSPACE_DIR/tmp/"
