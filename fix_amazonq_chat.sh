#!/bin/bash

# Fix Amazon Q chat loading issues by clearing history

HISTORY_DIR="$HOME/.aws/amazonq/history"
BACKUP_DIR="$HOME/.aws/amazonq/history_backup_$(date +%Y%m%d_%H%M%S)"

echo "Amazon Q Chat Fix Script"
echo "========================"

# Check if history directory exists
if [ ! -d "$HISTORY_DIR" ]; then
    echo "No history directory found. Nothing to fix."
    exit 0
fi

# Show current size
CURRENT_SIZE=$(du -sh "$HISTORY_DIR" 2>/dev/null | cut -f1)
echo "Current history size: $CURRENT_SIZE"

# Ask for backup
read -p "Create backup before clearing? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating backup at: $BACKUP_DIR"
    cp -r "$HISTORY_DIR" "$BACKUP_DIR"
    echo "Backup created successfully"
fi

# Clear history
echo "Clearing history..."
rm -rf "$HISTORY_DIR"/*
echo "History cleared"

echo ""
echo "Done! Now reload VS Code window:"
echo "  Cmd+Shift+P → 'Developer: Reload Window'"
