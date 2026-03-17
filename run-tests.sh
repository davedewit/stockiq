#!/bin/bash

# StockIQ Test Runner
# Automated testing script for the website

set -e  # Exit on any error

echo "🚀 StockIQ Test Runner"
echo "====================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Get script directory
SCRIPT_DIR="/Users/ddewit/VSCODE/stockiq"
WEBSITE_DIR="/Users/ddewit/VSCODE/website"

# Change to testing directory for dependencies
cd "$SCRIPT_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing test dependencies..."
    npm install
fi

# Change to website directory for server
cd "$WEBSITE_DIR"

# Function to check if server is running
check_server() {
    curl -s http://localhost:8000 > /dev/null 2>&1
}

# Start local server if not running
if ! check_server; then
    echo "🌐 Starting local server..."
    python3 -m http.server 8000 &
    SERVER_PID=$!
    
    # Wait for server to start
    echo "⏳ Waiting for server to start..."
    for i in {1..10}; do
        if check_server; then
            echo "✅ Server is running on http://localhost:8000"
            break
        fi
        sleep 1
    done
    
    if ! check_server; then
        echo "❌ Failed to start server"
        exit 1
    fi
else
    echo "✅ Server already running on http://localhost:8000"
    SERVER_PID=""
fi

# Function to cleanup
cleanup() {
    if [ ! -z "$SERVER_PID" ]; then
        echo "🛑 Stopping server..."
        kill $SERVER_PID 2>/dev/null || true
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Ask user which test to run
echo ""
echo "Select test type:"
echo "1) Quick Test (essential functionality)"
echo "2) UI/Functionality Test (navigation, search, responsive)"
echo "3) Lambda Endpoint Test (homepage widgets)"
echo "4) Standard Test Suite (1+2+3)"
echo "5) Comprehensive Lambda Test (ALL 600+ endpoints)"
echo "6) Retry Failed Lambda Endpoints"
echo "7) Test Single Lambda Endpoint (custom URL)"
echo "8) Generate Lambda Name to URL Mapping (update mapping file)"
read -p "Enter choice (1-8): " choice

case $choice in
    1)
        echo "⚡ Running Quick Test..."
        node "$SCRIPT_DIR/quick-test.js"
        ;;
    2)
        echo "🧪 Running Full Test Suite..."
        echo "Note: This will open a browser window and may require manual interaction"
        read -p "Press Enter to continue..."
        node "$SCRIPT_DIR/test-suite.js"
        ;;
    3)
        echo "🔬 Running Lambda Endpoint Test..."
        node "$SCRIPT_DIR/lambda-test.js"
        ;;
    4)
        echo "🧪 Running Standard Test Suite (1+2+3)..."
        echo "⚡ Quick Test..."
        node "$SCRIPT_DIR/quick-test.js"
        echo ""
        echo "🧪 UI/Functionality Test..."
        echo "Note: This will open a browser window and may require manual interaction"
        read -p "Press Enter to continue..."
        node "$SCRIPT_DIR/test-suite.js"
        echo ""
        echo "🔬 Lambda Endpoint Test..."
        node "$SCRIPT_DIR/lambda-test.js"
        ;;
    5)
        echo "🔬 Running Comprehensive Lambda Test..."
        echo "Note: This will test ALL 600+ Lambda endpoints (may take 10-15 minutes)"
        read -p "Press Enter to continue..."
        
        # Only generate mapping if it doesn't exist
        if [ ! -f "$SCRIPT_DIR/lambda-url-mapping.json" ]; then
            echo "📊 Generating Lambda URL mapping (first time)..."
            bash "$SCRIPT_DIR/generate-lambda-mapping.sh"
            echo ""
        else
            echo "✅ Using existing Lambda URL mapping"
            echo "   (Run option 8 to regenerate if needed)"
            echo ""
        fi
        
        node "$SCRIPT_DIR/comprehensive-lambda-test.js"
        ;;
    6)
        echo "🔁 Retrying Failed Lambda Endpoints..."
        node "$SCRIPT_DIR/comprehensive-lambda-test.js" --retry
        ;;
    7)
        echo "🎯 Test Single Lambda Endpoint"
        read -p "Enter Lambda URL: " lambda_url
        node "$SCRIPT_DIR/test-single-lambda.js" "$lambda_url"
        ;;
    8)
        echo "📊 Generating Lambda URL Mapping..."
        bash "$SCRIPT_DIR/generate-lambda-mapping.sh"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Testing completed!"
echo "💡 Tip: Run 'npm run test:quick' for quick tests anytime"