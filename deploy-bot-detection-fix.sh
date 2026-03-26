#!/bin/bash

# Deploy bot detection fix to usage tracker Lambda functions

AWS="/opt/homebrew/bin/aws"
LAMBDA_DIR="/Users/ddewit/VSCODE/stockiq/lambda-sync"

echo "🤖 Deploying bot detection fix to Lambda functions..."
echo ""

# Function to deploy a Lambda
deploy_lambda() {
    local FUNCTION_NAME=$1
    local SOURCE_DIR="$LAMBDA_DIR/$FUNCTION_NAME"
    
    if [ ! -d "$SOURCE_DIR" ]; then
        echo "❌ Directory not found: $SOURCE_DIR"
        return 1
    fi
    
    echo "📦 Packaging $FUNCTION_NAME..."
    cd "$SOURCE_DIR"
    
    # Create deployment package
    zip -q -r /tmp/${FUNCTION_NAME}.zip . -x "*.pyc" -x "__pycache__/*" -x ".DS_Store"
    
    if [ ! -f "/tmp/${FUNCTION_NAME}.zip" ]; then
        echo "❌ Failed to create zip for $FUNCTION_NAME"
        return 1
    fi
    
    echo "🚀 Deploying $FUNCTION_NAME to AWS..."
    $AWS lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb:///tmp/${FUNCTION_NAME}.zip" \
        --region us-east-1 \
        > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ $FUNCTION_NAME deployed successfully"
        rm "/tmp/${FUNCTION_NAME}.zip"
        return 0
    else
        echo "❌ Failed to deploy $FUNCTION_NAME"
        rm "/tmp/${FUNCTION_NAME}.zip"
        return 1
    fi
}

# Deploy both Lambda functions
deploy_lambda "stockiq-daily-usage-tracker-anonymous"
echo ""
deploy_lambda "stockiq-daily-usage-tracker"

echo ""
echo "🎉 Bot detection deployment complete!"
echo ""
echo "The following bot patterns are now blocked:"
echo "  • Googlebot (User-Agent + IP 66.249.*)"
echo "  • Bingbot"
echo "  • Yahoo Slurp"
echo "  • Other common crawlers"
echo ""
echo "Bot requests will return usage: 0 without incrementing counters."
