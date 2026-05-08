#!/bin/bash
# Install ComfyGram LaunchAgent on macOS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_SRC="$SCRIPT_DIR/com.github.comfygram.bot.plist.template"
PLIST_DEST="$HOME/Library/LaunchAgents/com.github.comfygram.bot.plist"

echo "Installing ComfyGram LaunchAgent..."

# Create LaunchAgents directory if not exists
mkdir -p "$HOME/Library/LaunchAgents"

# Copy template
cp "$PLIST_SRC" "$PLIST_DEST"

# Unload existing service if present
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load service
launchctl load "$PLIST_DEST"

echo "✓ LaunchAgent installed"
echo "Start with: launchctl start com.github.comfygram.bot"
echo "Logs: $HOME/comfygram/workspace/tmp/comfygram-bot.log"
