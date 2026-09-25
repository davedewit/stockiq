#!/bin/bash

# Deploy stockiq.tech website to S3/CloudFront
#
# What this script does:
#   1. Updates market news (update_news.py) - 2 hour cooldown
#   2. Updates stock pages with critical news (update_stock_news.py) - 23 hour cooldown per stock
#      and data snapshots on large-cap stock pages (update_stock_analysis.py)
#   3. Creates backups (website, stockiq, prod_scripts)
#   4. Adds "People also watch" section to stock pages (people_also_watch_stocks.py)
#   5. Updates sitemap.xml with current dates (update_sitemap.py)
#   6. Cleans up broken links (cleanup_broken_links.py)
#   7. Removes duplicate articles (remove_news_duplicates.py), trims news.html (finalize_news_html.py)
#   8. Syncs to S3 (only changed files)
#   9. Invalidates CloudFront cache
#   10. Notifies Google/Bing about sitemap updates (notify_search_engines.py)
#   11. Syncs Lambda functions (every 15 min)
#   12. Commits and pushes both git repos (stockiq and website) once a day
#
# DRY_RUN=true ./deploy-to-s3.sh lists what would be uploaded/pushed without doing it
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

# DRY_RUN=true: run the local steps, then only list what would be uploaded and pushed
# (no S3 writes, no CloudFront invalidation, no search engine ping, no Lambda sync, no git push)
DRYRUN_FLAG=""
if [ "$DRY_RUN" = "true" ]; then
    DRYRUN_FLAG="--dryrun"
    echo "🧪 DRY RUN - nothing will be uploaded or pushed"
fi

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

# Refresh the data snapshot on large-cap stock pages and the indexable list (daily run only)
if [ "$UPDATE_STOCK_NEWS" = "true" ]; then
    echo "📈 Updating stock data snapshots..."
    python3 "/Users/ddewit/VSCODE/stockiq/update_stock_analysis.py"
else
    echo "⏭️  Skipping stock data snapshots"
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
    WEBSITE_SIZE=$(du -sh "$BACKUP_DIR" | awk '{print $1}')
    echo "✅ Backup created: website_backup_$TIMESTAMP ($WEBSITE_SIZE)"

    # Stockiq backup
    STOCKIQ_DIR="/Users/ddewit/VSCODE/stockiq"
    STOCKIQ_BACKUP_DIR="$BACKUP_DIR_BASE/stockiq_backup_$TIMESTAMP"
    rsync -r --exclude='.DS_Store' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git*' --exclude='testing' --exclude='lambda-sync' "$STOCKIQ_DIR/" "$STOCKIQ_BACKUP_DIR/"
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

# Trim news.html to the newest articles and keep it noindex
echo "✂️  Finalizing news.html..."
python3 "/Users/ddewit/VSCODE/stockiq/finalize_news_html.py"

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
# Compares size and modification time (not --size-only, which skipped same-size edits)
if [ -d "$WEBSITE_DIR/stocks" ]; then
  echo "  📊 Syncing stock pages..."
  retry_aws $AWS s3 sync "$WEBSITE_DIR/stocks/" s3://$BUCKET/stocks/ \
    $DRYRUN_FLAG \
    --delete \
    --exclude "testing/*" \
    --exclude ".DS_Store" \
    --cache-control "public, max-age=86400" \
    --content-type "text/html; charset=utf-8"
fi

# Sync js/ folder - 24 hour cache (exclude testing)
if [ -d "$WEBSITE_DIR/js" ]; then
  echo "  📜 Syncing js/ folder..."
  retry_aws $AWS s3 sync "$WEBSITE_DIR/js/" s3://$BUCKET/js/ \
    $DRYRUN_FLAG \
    --delete \
    --exclude "testing/*" \
    --exclude ".DS_Store" \
    --cache-control "public, max-age=86400"
fi

# Root files are compared by content: local MD5 vs the S3 ETag from one listing call
# (multipart uploads have ETags containing "-", which never match, so those always upload)
S3_ETAGS=$(mktemp)
retry_aws $AWS s3api list-objects-v2 --bucket $BUCKET --delimiter / \
  --query 'Contents[].[Key,ETag]' --output text > "$S3_ETAGS"

upload_if_changed() {
  local filepath=$1 cache=$2 ctype=$3
  local file=$(basename "$filepath")
  local local_md5=$(md5 -q "$filepath")
  local s3_etag=$(awk -F'\t' -v k="$file" '$1==k {gsub(/"/,"",$2); print $2}' "$S3_ETAGS")
  if [ "$local_md5" != "$s3_etag" ]; then
    if [ "$DRY_RUN" = "true" ]; then
      echo "    (dry run) upload: $file"
    else
      $AWS s3 cp "$filepath" s3://$BUCKET/"$file" \
        --cache-control "$cache" \
        --content-type "$ctype"
    fi
  fi
}

# Root HTML files - 1 hour cache
echo "  📄 Syncing HTML files..."
for filepath in "$WEBSITE_DIR"/*.html; do
  upload_if_changed "$filepath" "public, max-age=3600" "text/html; charset=utf-8"
done

# Root CSS files - 24 hour cache
echo "  🎨 Syncing CSS files..."
for filepath in "$WEBSITE_DIR"/*.css; do
  upload_if_changed "$filepath" "public, max-age=86400" "text/css"
done

# Root JS files (auth.js, sidebar.js, analysis-functions.js, news.js...) - 24 hour cache
echo "  📜 Syncing root JavaScript files..."
for filepath in "$WEBSITE_DIR"/*.js; do
  case "$(basename "$filepath")" in
    test-*|analysis-functions-*|*copy*|*Copy*|*old*|*Old*|*backup*|*Backup*) continue ;;
  esac
  if [ "$(basename "$filepath")" = "news.js" ]; then
    upload_if_changed "$filepath" "public, max-age=3600" "application/javascript"   # changes daily
  else
    upload_if_changed "$filepath" "public, max-age=86400" "application/javascript"
  fi
done
rm -f "$S3_ETAGS"

# Sync images - 7 day cache
echo "  🖼️  Syncing images..."
retry_aws $AWS s3 sync "$WEBSITE_DIR" s3://$BUCKET/ \
  $DRYRUN_FLAG \
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
  $DRYRUN_FLAG \
  --exclude "*" \
  --include "stocks.txt" \
  --include "robots.txt" \
  --include "sitemap.xml"

if [ "$DRY_RUN" = "true" ]; then
    echo "🧪 Dry run: the (dryrun) lines above are what would be uploaded or deleted"
else
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
    python3 "/Users/ddewit/VSCODE/website/notify_search_engines.py"
fi

# Show content statistics
echo ""
echo "📊 Content Statistics:"
NEWS_COUNT=$(grep -c '<article class="blog-post"' "$WEBSITE_DIR/news.html" 2>/dev/null || echo "0")
STOCK_WITH_NEWS=$(grep -l '<strong>' "$WEBSITE_DIR/stocks/"*.html 2>/dev/null | wc -l | tr -d ' ')
TOTAL_STOCKS=$(find "$WEBSITE_DIR/stocks/" -maxdepth 1 -name "*.html" | wc -l)
INDEXED_STOCKS=$(grep -l '<meta name="robots" content="index, follow">' "$WEBSITE_DIR/stocks/"*.html 2>/dev/null | wc -l | tr -d ' ')
echo "  📰 News articles: $NEWS_COUNT"
echo "  📊 Stock pages with news: $STOCK_WITH_NEWS / $TOTAL_STOCKS"
echo "  🔎 Stock pages indexable: $INDEXED_STOCKS / $TOTAL_STOCKS"
echo ""

# Check if Lambda sync should run (only every 15 minutes)
LAMBDA_SYNC_MARKER="$WEBSITE_DIR/.last_lambda_sync"
if [ "$DRY_RUN" = "true" ]; then
    echo "⏭️  Skipping Lambda sync (dry run)"
elif [ -f "$LAMBDA_SYNC_MARKER" ]; then
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

# Auto-commit and push both repos to GitHub (once per day):
#   stockiq/ -> davedewit/stockiq (scripts)
#   website/ -> davedewit/stockiq-website (site files; stocks/ is gitignored)
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
    TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
    ALL_PUSHED=true
    for REPO in /Users/ddewit/VSCODE/stockiq "$WEBSITE_DIR"; do
        cd "$REPO"
        NAME=$(basename "$REPO")
        CHANGES=$(git status --porcelain | wc -l | tr -d ' ')
        if [ "$DRY_RUN" = "true" ]; then
            UNPUSHED=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "?")
            echo "  (dry run) $NAME: $CHANGES changed files to commit, $UNPUSHED local commits to push"
            continue
        fi
        if [ "$CHANGES" != "0" ]; then
            git add -A >/dev/null 2>&1
            git commit -m "Auto-update: $TIMESTAMP" >/dev/null 2>&1
        fi
        # Bring in commits made elsewhere (e.g. on GitHub) before pushing
        if ! git pull --rebase >/dev/null 2>&1; then
            git rebase --abort >/dev/null 2>&1
            echo "  ⚠️  $NAME: could not rebase onto GitHub (conflict) - not pushed, needs a manual look"
            ALL_PUSHED=false
            continue
        fi
        if [ -z "$(git rev-list @{u}..HEAD 2>/dev/null)" ]; then
            echo "  ℹ️  $NAME: already up to date on GitHub"
        elif git push >/dev/null 2>&1; then
            echo "  ✅ $NAME: pushed to GitHub"
        else
            echo "  ⚠️  $NAME: git push failed (will retry next deploy)"
            ALL_PUSHED=false
        fi
    done
    cd "$WEBSITE_DIR"
    if [ "$ALL_PUSHED" = true ] && [ "$DRY_RUN" != "true" ]; then
        date +%s > "$GIT_PUSH_MARKER"
    fi
fi

echo ""
echo "✅ All done!"
