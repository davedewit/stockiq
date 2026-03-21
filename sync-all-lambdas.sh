#!/bin/bash

# Script to download unique StockIQ Lambda functions (skip duplicate workers)

AWS="/opt/homebrew/bin/aws"
OUTPUT_DIR="/Users/ddewit/VSCODE/stockiq/lambda-sync"
mkdir -p "$OUTPUT_DIR"

echo "📦 Syncing unique StockIQ Lambda functions to $OUTPUT_DIR"
echo ""

# Get all Lambda functions
FUNCTIONS=$($AWS lambda list-functions --query 'Functions[].FunctionName' --output text)

TOTAL=$(echo "$FUNCTIONS" | wc -w)
CURRENT=0
DOWNLOADED=0
SKIPPED=0
DUPLICATE_WORKERS=0

# Track which function types we've already downloaded
SEEN_TYPES=""

for FUNCTION in $FUNCTIONS; do
    CURRENT=$((CURRENT + 1))
    
    # Extract the base type (remove -worker-NUMBER)
    FUNC_TYPE=$(echo "$FUNCTION" | sed 's/-worker-[0-9]*$//')
    
    # Check if we've already downloaded this type
    if echo "$SEEN_TYPES" | grep -q "^$FUNC_TYPE$"; then
        echo "[$CURRENT/$TOTAL] ⏭️  $FUNCTION (duplicate worker, skipped)"
        DUPLICATE_WORKERS=$((DUPLICATE_WORKERS + 1))
        continue
    fi
    
    # Mark this type as seen
    SEEN_TYPES="$SEEN_TYPES
$FUNC_TYPE"
    
    # Get the function code location and last modified time
    FUNC_INFO=$($AWS lambda get-function --function-name "$FUNCTION" --query '{Location: Code.Location, LastModified: Configuration.LastModified}' --output json 2>/dev/null)
    CODE_URL=$(echo "$FUNC_INFO" | jq -r '.Location' 2>/dev/null)
    
    if [ -z "$CODE_URL" ] || [ "$CODE_URL" = "null" ]; then
        echo "[$CURRENT/$TOTAL] ❌ $FUNCTION (failed - no code location)"
        continue
    fi
    
    FUNC_DIR="$OUTPUT_DIR/$FUNCTION"
    
    # Check if already exists and compare timestamps
    if [ -d "$FUNC_DIR" ]; then
        AWS_MODIFIED=$(echo "$FUNC_INFO" | jq -r '.LastModified')
        LOCAL_MODIFIED=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%S" "$FUNC_DIR" 2>/dev/null || echo "")
        
        # Convert AWS timestamp to comparable format and check if AWS is newer
        if [ ! -z "$LOCAL_MODIFIED" ] && [ "$AWS_MODIFIED" \> "$LOCAL_MODIFIED" ]; then
            echo "[$CURRENT/$TOTAL] 🔄 $FUNCTION (updating)"
            rm -rf "$FUNC_DIR"
            mkdir -p "$FUNC_DIR"
            if curl -s -f "$CODE_URL" -o "$FUNC_DIR/function.zip" 2>/dev/null && [ -f "$FUNC_DIR/function.zip" ]; then
                unzip -qo "$FUNC_DIR/function.zip" -d "$FUNC_DIR"
                rm "$FUNC_DIR/function.zip"
                DOWNLOADED=$((DOWNLOADED + 1))
            else
                echo "[$CURRENT/$TOTAL] ⚠️  $FUNCTION (download failed, skipping)"
                rm -rf "$FUNC_DIR"
            fi
        else
            echo "[$CURRENT/$TOTAL] ⏭️  $FUNCTION (up-to-date)"
            SKIPPED=$((SKIPPED + 1))
        fi
    else
        echo "[$CURRENT/$TOTAL] ⬇️  $FUNCTION"
        mkdir -p "$FUNC_DIR"
        if curl -s -f "$CODE_URL" -o "$FUNC_DIR/function.zip" 2>/dev/null && [ -f "$FUNC_DIR/function.zip" ]; then
            unzip -qo "$FUNC_DIR/function.zip" -d "$FUNC_DIR"
            rm "$FUNC_DIR/function.zip"
            DOWNLOADED=$((DOWNLOADED + 1))
        else
            echo "[$CURRENT/$TOTAL] ⚠️  $FUNCTION (download failed, skipping)"
            rm -rf "$FUNC_DIR"
        fi
    fi
done

echo ""
echo "✅ Sync complete: $DOWNLOADED downloaded, $SKIPPED cached"
echo "⏭️  Skipped $DUPLICATE_WORKERS duplicate workers"
echo "Total size: $(du -sh $OUTPUT_DIR | cut -f1)"
