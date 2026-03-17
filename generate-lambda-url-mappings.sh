#!/bin/bash

# Generate Lambda URL to Function Name Mapping
# This script queries AWS to map all Lambda Function URLs to their function names

set -u  # Exit on undefined variable

echo "🔍 Generating Lambda URL to Function Name mapping..."
echo ""

# Get script directory to save file in testing folder
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OUTPUT_FILE="$SCRIPT_DIR/lambda-url-mapping.json"
TEMP_FILE="$SCRIPT_DIR/.lambda-mapping.tmp"

# Cleanup on exit
trap 'rm -f "$TEMP_FILE"' EXIT

# Get all Lambda functions with URLs
echo "📡 Querying AWS Lambda functions..."

# Get list of all Lambda functions
FUNCTIONS=$(aws lambda list-functions --region us-east-1 --query 'Functions[*].FunctionName' --output text 2>&1)

if [ -z "$FUNCTIONS" ]; then
    echo "❌ Failed to get Lambda functions from AWS"
    echo "Error: $FUNCTIONS"
    exit 1
fi

# Count total functions
TOTAL=$(echo $FUNCTIONS | wc -w | tr -d ' ')
echo "📊 Discovered $TOTAL Lambda functions"
echo ""

# Write directly to output file
echo "{" > "$OUTPUT_FILE"

FIRST=true
COUNT=0
WITH_URL=0
WITHOUT_URL=0

for FUNC in $FUNCTIONS; do
    # Get function URL config
    URL=$(aws lambda get-function-url-config --function-name "$FUNC" --region us-east-1 2>/dev/null | jq -r '.FunctionUrl' 2>/dev/null || echo "null")
    
    COUNT=$((COUNT + 1))
    
    # Add comma if not first entry
    if [ "$FIRST" = false ]; then
        echo "," >> "$OUTPUT_FILE"
    fi
    FIRST=false
    
    # Use function name as key, URL or "NO_URL" as value
    if [ "$URL" != "null" ] && [ ! -z "$URL" ]; then
        echo -n "  \"$FUNC\": \"$URL\"" >> "$OUTPUT_FILE"
        echo "✅ $FUNC -> $URL"
        WITH_URL=$((WITH_URL + 1))
    else
        echo -n "  \"$FUNC\": \"NO_URL\"" >> "$OUTPUT_FILE"
        echo "⚠️  $FUNC -> NO_URL"
        WITHOUT_URL=$((WITHOUT_URL + 1))
    fi
done

echo "" >> "$OUTPUT_FILE"
echo "}" >> "$OUTPUT_FILE"

echo ""
echo "✅ Mapping complete! Discovered $TOTAL functions, displaying $COUNT functions"
echo "   - $WITH_URL with URLs"
echo "   - $WITHOUT_URL without URLs"
echo "📄 Saved to: $OUTPUT_FILE"
