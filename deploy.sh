#!/bin/bash

# Prevent concurrent runs
LOCK_FILE="/tmp/stockiq-deploy.lock"
if [ -f "$LOCK_FILE" ]; then
    echo "❌ Deployment already running. Exiting."
    exit 1
fi
touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

# Clear log and kill any lingering osascript dialogs
rm -f ~/stockiq-daily.log
pkill -f "osascript" 2>/dev/null

echo "📈 StockIQ Deployment Started" >> ~/stockiq-daily.log
echo "To stop this task, run:" >> ~/stockiq-daily.log
echo "  pkill -9 -f \"aws s3 sync\"" >> ~/stockiq-daily.log
echo "  pkill -9 -f \"deploy-to-s3.sh\"" >> ~/stockiq-daily.log
echo "  pkill -9 -f \"update_stock_news.py\"" >> ~/stockiq-daily.log
echo "" >> ~/stockiq-daily.log
echo "To pause scheduled task:" >> ~/stockiq-daily.log
echo "  launchctl bootout gui/\$(id -u) ~/Library/LaunchAgents/com.stockiq.reminder.plist" >> ~/stockiq-daily.log
echo "To resume scheduled task:" >> ~/stockiq-daily.log
echo "  launchctl bootstrap gui/\$(id -u) ~/Library/LaunchAgents/com.stockiq.reminder.plist" >> ~/stockiq-daily.log
echo "To delete scheduled task permanently:" >> ~/stockiq-daily.log
echo "  launchctl bootout gui/\$(id -u) ~/Library/LaunchAgents/com.stockiq.reminder.plist" >> ~/stockiq-daily.log
echo "  rm ~/Library/LaunchAgents/com.stockiq.reminder.plist" >> ~/stockiq-daily.log
echo "  rm ~/stockiq-reminder.scpt" >> ~/stockiq-daily.log
echo "" >> ~/stockiq-daily.log
echo "To manually run this task:" >> ~/stockiq-daily.log
echo "  cd /Users/ddewit/VSCODE/stockiq && yes | ./deploy.sh >> ~/stockiq-daily.log 2>&1 &" >> ~/stockiq-daily.log
echo "" >> ~/stockiq-daily.log

SCRIPTS_DIR="/Users/ddewit/VSCODE/stockiq"

# Check if running interactively (from terminal) or non-interactively (from launchd)
if [ -t 0 ]; then
    # Interactive mode - ask user
    echo "🔍 Checking news sync status..."
    echo
    python3 "$SCRIPTS_DIR/check_news_sync.py"
    echo
    
    read -p "Continue with deployment? [Y/n]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "❌ Deployment cancelled"
        exit 0
    fi
    echo
    
    read -p "Update stock market news? [Y/n]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        export UPDATE_STOCK_NEWS=false
    else
        export UPDATE_STOCK_NEWS=true
    fi
    
    "$SCRIPTS_DIR/deploy-to-s3.sh" 2>&1 | tee -a ~/stockiq-daily.log
else
    # Non-interactive mode (launchd) - always update stock news
    export UPDATE_STOCK_NEWS=true
    "$SCRIPTS_DIR/deploy-to-s3.sh" >> ~/stockiq-daily.log 2>&1
fi

# Verify news sync after deployment
echo ""
echo "🔍 Verifying news sync status..."
python3 "$SCRIPTS_DIR/check_news_sync.py"