#!/bin/bash

# Deploy stockiq.tech website to S3/CloudFront
#
# What this script does:
#   1. Updates market news (update_news.py) - 2 hour cooldown
#   2. Updates stock pages with critical news (update_stock_news.py) - 23 hour cooldown per stock
#   3. Creates backups (website, stockiq, prod_scripts)
#   4. Adds "People also watch" section to stock pages (people_also_watch_stocks.py)
#   5. Updates sitemap.xml with current dates (update_sitemap.py)
#   6. Cleans up broken links (cleanup_broken_links.py)
#   7. Removes duplicate articles (remove_news_duplicates.py)
#   8. Syncs to S3 (only changed files)
#   9. Invalidates CloudFront cache
#   10. Notifies Google/Bing about sitemap updates (notify_search_engines.py)
#   11. Syncs Lambda functions (every 15 min)
#
# Usage:
#   ./deploy-to-s3.sh                    # Quick deploy (no news update)
#   UPDATE_STOCK_NEWS=true ./deploy-to-s3.sh  # Full deploy with news
#   ./deploy.sh                          # Interactive wrapper (asks about news)
#
# When to use:
#   - deploy-to-s3.sh: Just push HTML changes (no API calls, free, fast)
#   - deploy.sh: Update news + deploy (API calls, ~$1-2, 15-20 min)

# Load OpenAI API key if available
if [ -f "$HOME/.openai_key" ]; then
    export OPENAI_API_KEY=$(tr -d '\n' < "$HOME/.openai_key")
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "⚠️  Warning: OpenAI API key file is empty"
    else
        echo "✅ OpenAI API key loaded"
    fi
else
    echo "⚠️  Warning: OpenAI API key file not found at $HOME/.openai_key"
fi

BUCKET="stockiq-final-websitebucket-vqekic7enf9h"
DISTRIBUTION_ID="EHXV50CPHY07R"
AWS="/opt/homebrew/bin/aws"

# Function to check internet connection
check_internet() {
    local attempts=3
    local delay=2
    
    for i in $(seq 1 $attempts); do
        if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
            return 0
        fi
        if [ $i -lt $attempts ]; then
            echo "⚠️  Internet check failed (attempt $i/$attempts), retrying in ${delay}s..."
            sleep $delay
        fi
    done
    
    echo "❌ No internet connection after $attempts attempts. Aborting deployment."
    exit 1
}

# Function to retry AWS commands
retry_aws() {
    local max_attempts=3
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if "$@"; then
            return 0
        fi
        if [ $attempt -lt $max_attempts ]; then
            echo "⚠️  Command failed. Retrying ($attempt/$max_attempts)..."
            sleep 5
        fi
        attempt=$((attempt + 1))
    done
    echo "❌ Command failed after $max_attempts attempts. Aborting."
    exit 1
}

# Change to website root directory
WEBSITE_DIR="/Users/ddewit/VSCODE/website"
cd "$WEBSITE_DIR"
BACKUP_DIR_BASE="/Users/ddewit/VSCODE/backup"
mkdir -p "$BACKUP_DIR_BASE"
BACKUP_MARKER="$BACKUP_DIR_BASE/.last_backup"

# Check internet before starting news updates
if [ "$UPDATE_STOCK_NEWS" = "true" ]; then
    echo "🌐 Checking internet connection..."
    check_internet
    echo "✅ Internet connection OK"
fi

# Update news from Yahoo Finance (only if user opted in)
if [ "$UPDATE_STOCK_NEWS" = "true" ]; then
    NEWS_UPDATE_MARKER="$WEBSITE_DIR/.last_news_update"
    if [ -f "$NEWS_UPDATE_MARKER" ]; then
        LAST_UPDATE=$(cat "$NEWS_UPDATE_MARKER")
        CURRENT_TIME=$(date +%s)
        TIME_DIFF=$((CURRENT_TIME - LAST_UPDATE))
        if [ $TIME_DIFF -lt 7200 ]; then
            echo "⏭️  Skipping news update (last update was $((TIME_DIFF / 60)) minutes ago)"
        else
            echo "📰 Updating market news..."
            python3 "/Users/ddewit/VSCODE/stockiq/update_news.py"
            date +%s > "$NEWS_UPDATE_MARKER"
        fi
    else
        echo "📰 Updating market news..."
        python3 "/Users/ddewit/VSCODE/stockiq/update_news.py"
        date +%s > "$NEWS_UPDATE_MARKER"
    fi
else
    echo "⏭️  Skipping market news update"
fi

# Update individual stock pages with critical news (only if user opted in)
if [ "$UPDATE_STOCK_NEWS" = "true" ]; then
    echo "📊 Checking for critical stock news..."
    python3 "/Users/ddewit/VSCODE/stockiq/update_stock_news.py"
else
    echo "⏭️  Skipping stock news update"
fi

# Remove backups older than 30 days (for both website and stockiq)
echo "🧹 Removing backups older than 30 days..."
find "$BACKUP_DIR_BASE" -maxdepth 1 -type d -name "*_backup_*" -mtime +30 -exec rm -rf {} +

if true; then
    echo "💾 Creating backup..."
    TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
    # Website backup
    BACKUP_DIR="$BACKUP_DIR_BASE/website_backup_$TIMESTAMP"
    rsync -r --exclude='.DS_Store' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git*' --exclude='testing' --exclude='lambda-sync' "$WEBSITE_DIR/" "$BACKUP_DIR/"
    if [ -d "$BACKUP_DIR/.amazonq" ]; then mv "$BACKUP_DIR/.amazonq" "$BACKUP_DIR/amazonq"; fi
    WEBSITE_SIZE=$(du -sh "$BACKUP_DIR" | awk '{print $1}')
    echo "✅ Backup created: website_backup_$TIMESTAMP ($WEBSITE_SIZE)"

    # Stockiq backup
    STOCKIQ_DIR="/Users/ddewit/VSCODE/stockiq"
    STOCKIQ_BACKUP_DIR="$BACKUP_DIR_BASE/stockiq_backup_$TIMESTAMP"
    rsync -r --exclude='.DS_Store' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git*' --exclude='testing' --exclude='lambda-sync' "$STOCKIQ_DIR/" "$STOCKIQ_BACKUP_DIR/"
    if [ -d "$STOCKIQ_BACKUP_DIR/.amazonq" ]; then mv "$STOCKIQ_BACKUP_DIR/.amazonq" "$STOCKIQ_BACKUP_DIR/amazonq"; fi
    STOCKIQ_SIZE=$(du -sh "$STOCKIQ_BACKUP_DIR" | awk '{print $1}')
    echo "✅ Backup created: stockiq_backup_$TIMESTAMP ($STOCKIQ_SIZE)"
    date +%s > "$BACKUP_MARKER"

    # Backup prod_scripts once every 23 hours
    PROD_SCRIPTS_MARKER="$BACKUP_DIR_BASE/.last_prod_scripts_backup"
    PROD_BACKUP_NEEDED=true
    if [ -f "$PROD_SCRIPTS_MARKER" ]; then
        LAST_PROD=$(cat "$PROD_SCRIPTS_MARKER")
        CURRENT_TIME=$(date +%s)
        if [ $((CURRENT_TIME - LAST_PROD)) -lt 82800 ]; then
            PROD_BACKUP_NEEDED=false
            echo "⏭️  Skipping prod_scripts backup (less than 23 hours ago)"
        fi
    fi
    if [ "$PROD_BACKUP_NEEDED" = true ]; then
        PROD_SCRIPTS_DIR="/Users/ddewit/VSCODE/prod_scripts"
        PROD_SCRIPTS_BACKUP_DIR="$BACKUP_DIR_BASE/prod_scripts_backup_$TIMESTAMP"
        rsync -r --exclude='.DS_Store' --exclude='__pycache__' --exclude='*.pyc' "$PROD_SCRIPTS_DIR/" "$PROD_SCRIPTS_BACKUP_DIR/"
        echo "✅ Backup created: backups/prod_scripts_backup_$TIMESTAMP"
        date +%s > "$PROD_SCRIPTS_MARKER"
    fi
fi

# Add related stocks section to any pages missing it
echo "🔗 Adding internal links to pages..."
python3 "/Users/ddewit/VSCODE/stockiq/people_also_watch_stocks.py" --missing

# Update sitemap with current date
echo "📅 Updating sitemap dates..."
python3 "/Users/ddewit/VSCODE/stockiq/update_sitemap.py"

# Clean up broken article links in news.html
echo "🧹 Cleaning up broken links..."
python3 "/Users/ddewit/VSCODE/stockiq/cleanup_broken_links.py"

# Remove duplicate articles from news.html
echo "🗑️ Removing duplicate articles..."
python3 "/Users/ddewit/VSCODE/stockiq/remove_news_duplicates.py"

# Update news article dates
echo "📅 Updating news article dates..."
TODAY=$(date -u +"%Y-%m-%dT00:00:00Z")
sed -i '' "s/<meta property=\"article:modified_time\" content=\"[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}T[0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}Z\">/<meta property=\"article:modified_time\" content=\"$TODAY\">/" "$WEBSITE_DIR/news.html"

# Check internet before S3 sync
echo "🌐 Checking internet connection before S3 sync..."
check_internet
echo "✅ Internet connection OK"

echo "🚀 Deploying to S3..."
echo "📦 Bucket: $BUCKET"
echo "📊 CloudFront: $DISTRIBUTION_ID"

# Sync all files efficiently (only uploads changed files)
echo "📁 Syncing files to S3 (only changed files)..."

# Sync stocks/ folder - HTML files with 24 hour cache (exclude testing)
if [ -d "$WEBSITE_DIR/stocks" ]; then
  echo "  📊 Syncing stock pages..."
  retry_aws $AWS s3 sync "$WEBSITE_DIR/stocks/" s3://$BUCKET/stocks/ \
    --delete \
    --size-only \
    --exclude "testing/*" \
    --cache-control "public, max-age=86400" \
    --content-type "text/html; charset=utf-8"
fi

# Sync js/ folder - 24 hour cache (exclude testing)
if [ -d "$WEBSITE_DIR/js" ]; then
  echo "  📜 Syncing JavaScript files..."
  retry_aws $AWS s3 sync "$WEBSITE_DIR/js/" s3://$BUCKET/js/ \
    --delete \
    --exclude "testing/*" \
    --cache-control "public, max-age=86400"
fi

# Sync root HTML files - 1 hour cache
echo "  📄 Syncing HTML files..."
for filepath in "$WEBSITE_DIR"/*.html; do
  file=$(basename "$filepath")
  LOCAL_SIZE=$(wc -c < "$filepath")
  S3_SIZE=$($AWS s3 ls s3://$BUCKET/"$file" 2>/dev/null | awk '{print $3}')
  if [ "$LOCAL_SIZE" != "$S3_SIZE" ]; then
    $AWS s3 cp "$filepath" s3://$BUCKET/"$file" \
      --cache-control "public, max-age=3600" \
      --content-type "text/html; charset=utf-8"
  fi
done

# Sync CSS files - 24 hour cache
echo "  🎨 Syncing CSS files..."
for filepath in "$WEBSITE_DIR"/*.css; do
  file=$(basename "$filepath")
  LOCAL_SIZE=$(wc -c < "$filepath")
  S3_SIZE=$($AWS s3 ls s3://$BUCKET/"$file" 2>/dev/null | awk '{print $3}')
  if [ "$LOCAL_SIZE" != "$S3_SIZE" ]; then
    $AWS s3 cp "$filepath" s3://$BUCKET/"$file" \
      --cache-control "public, max-age=86400"
  fi
done

# Sync images - 7 day cache
echo "  🖼️  Syncing images..."
retry_aws $AWS s3 sync "$WEBSITE_DIR" s3://$BUCKET/ \
  --exclude "backups/*" \
  --exclude "build-dev/*" \
  --exclude "lambda-sync/*" \
  --exclude "testing/*" \
  --exclude "docs/*" \
  --exclude "dev/*" \
  --exclude "_unused_files/*" \
  --exclude "*copy*" \
  --exclude "*Copy*" \
  --exclude "*old*" \
  --exclude "*Old*" \
  --exclude "*backup*" \
  --exclude "*Backup*" \
  --include "*.svg" \
  --include "*.png" \
  --include "*.jpg" \
  --include "*.ico" \
  --exclude "*" \
  --cache-control "public, max-age=604800"

# Sync special files
echo "  📋 Syncing special files..."
retry_aws $AWS s3 sync "$WEBSITE_DIR" s3://$BUCKET/ \
  --exclude "*" \
  --include "stocks.txt" \
  --include "robots.txt" \
  --include "sitemap.xml" \
  --include "news.js" \
  --include "stock-prices.js"

echo "✅ Sync complete! Only changed files were uploaded."

echo "🔄 Invalidating CloudFront cache..."
INVALIDATION_ID=$(retry_aws $AWS cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo "✓ Invalidation created: $INVALIDATION_ID"
echo "⏳ Waiting for invalidation to complete..."

retry_aws $AWS cloudfront wait invalidation-completed \
  --distribution-id $DISTRIBUTION_ID \
  --id $INVALIDATION_ID

echo "✅ Invalidation complete!"
echo "✅ Website deployment complete!"
echo ""
echo "🌐 Site: https://stockiq.tech"
echo "📊 CloudFront: $DISTRIBUTION_ID"
echo "🔄 Invalidation: $INVALIDATION_ID"
echo ""

# Notify search engines about sitemap update
echo "🔔 Notifying search engines..."
python3 "/Users/ddewit/VSCODE/stockiq/notify_search_engines.py"

# Show content statistics
echo ""
echo "📊 Content Statistics:"
NEWS_COUNT=$(grep -c '<article class="blog-post"' "$WEBSITE_DIR/news.html" 2>/dev/null || echo "0")
STOCK_WITH_NEWS=$(grep -l '<strong>' "$WEBSITE_DIR/stocks/"*.html 2>/dev/null | wc -l | tr -d ' ')
TOTAL_STOCKS=$(find "$WEBSITE_DIR/stocks/" -maxdepth 1 -name "*.html" | wc -l)
echo "  📰 News articles: $NEWS_COUNT"
echo "  📊 Stock pages with news: $STOCK_WITH_NEWS / $TOTAL_STOCKS"
echo ""

# Check if Lambda sync should run (only every 15 minutes)
LAMBDA_SYNC_MARKER="$WEBSITE_DIR/.last_lambda_sync"
if [ -f "$LAMBDA_SYNC_MARKER" ]; then
    LAST_SYNC=$(cat "$LAMBDA_SYNC_MARKER")
    CURRENT_TIME=$(date +%s)
    TIME_DIFF=$((CURRENT_TIME - LAST_SYNC))
    if [ $TIME_DIFF -lt 3600 ]; then
        echo "⏭️  Skipping Lambda sync (last sync was $((TIME_DIFF / 60)) minutes ago)"
    else
        echo "📥 Syncing Lambda functions..."
        "/Users/ddewit/VSCODE/stockiq/sync-all-lambdas.sh"
        date +%s > "$LAMBDA_SYNC_MARKER"
    fi
else
    echo "📥 Syncing Lambda functions..."
    "/Users/ddewit/VSCODE/stockiq/sync-all-lambdas.sh"
    date +%s > "$LAMBDA_SYNC_MARKER"
fi

# Auto-commit and push to GitHub (once per day)
GIT_PUSH_MARKER="$WEBSITE_DIR/.last_git_push"
GIT_PUSH_NEEDED=true
if [ -f "$GIT_PUSH_MARKER" ]; then
    LAST_PUSH=$(cat "$GIT_PUSH_MARKER")
    CURRENT_TIME=$(date +%s)
    if [ $((CURRENT_TIME - LAST_PUSH)) -lt 82800 ]; then
        GIT_PUSH_NEEDED=false
        echo "⏭️  Skipping git push (less than 23 hours ago)"
    fi
fi

if [ "$GIT_PUSH_NEEDED" = true ]; then
    echo "📤 Pushing changes to GitHub..."
    cd /Users/ddewit/VSCODE/stockiq
    if git diff --quiet && git diff --cached --quiet; then
        echo "  ℹ️  No changes to commit"
    else
        git add -A >/dev/null 2>&1
        TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
        git commit -m "Auto-update: $TIMESTAMP" >/dev/null 2>&1
        if git push >/dev/null 2>&1; then
            echo "  ✅ Pushed to GitHub"
            date +%s > "$GIT_PUSH_MARKER"
        else
            echo "  ⚠️  Git push failed (will retry next deploy)"
        fi
    fi
    cd "$WEBSITE_DIR"
fi

echo ""
echo "✅ All done!"
