#!/bin/bash

SCRIPT_DIR="/Users/ddewit/VSCODE/stockiq"
WEBSITE_DIR="/Users/ddewit/VSCODE/website"
cd "$WEBSITE_DIR"

echo "Update refresh intervals for index.html and dashboard.html"
echo ""
echo "1. Ticker sections (Trending, Gainers, Losers, Active)"
echo "2. Market indices (S&P 500, Dow, Nasdaq)"
echo "3. Both"
echo "4. Show current settings"
echo ""
read -p "Select option (1-4): " option

if [[ ! $option =~ ^[1-4]$ ]]; then
    echo "Invalid option. Use 1, 2, 3, or 4"
    exit 1
fi

if [[ $option == "4" ]]; then
    echo ""
    echo "Current Settings:"
    echo "================="
    echo ""
    
    # index.html
    echo "index.html:"
    index_ticker=$(grep -o "(now - parseInt(lastFetch)) >= [0-9]* \* 1000" index.html | head -1 | grep -o "[0-9]*" | head -1)
    index_delay=$(grep -o "const randomDelay = ([0-9]* + Math.random() \* [0-9]*) \* 1000;" index.html | head -1 | sed -E 's/const randomDelay = \(([0-9]*) \+ Math\.random\(\) \* ([0-9]*)\) \* 1000;/\1-\2/')
    if [[ $index_delay =~ ^([0-9]+)-([0-9]+)$ ]]; then
        min_d=${BASH_REMATCH[1]}
        max_d=${BASH_REMATCH[2]}
        total_max=$((max_d + min_d))
        index_delay="${min_d}-${total_max}"
    fi
    index_market=$(grep -A8 "Refresh market data every" index.html | grep -o "}, [0-9]* \* [0-9]* \* 1000);" | head -1 | sed -E 's/}, ([0-9]+) \* ([0-9]+) \* 1000\);/\1*\2/' | bc)
    if [[ -z "$index_market" ]]; then
        index_market=$(grep -A8 "Refresh market data every" index.html | grep -o "}, [0-9]* \* 1000);" | head -1 | grep -o "[0-9]*" | head -1)
    fi
    echo "  Fetch interval: ${index_ticker:-Not found}s"
    echo "  Display delays: ${index_delay:-Not found}s"
    echo "  Total update time: ${index_ticker:-0}-$((index_ticker + total_max))s"
    echo "  Market indices: ${index_market:-Not found}s"
    echo ""
    
    # dashboard.html
    echo "dashboard.html:"
    dash_ticker=$(grep -o "(now - parseInt(lastFetch)) >= [0-9]* \* 1000" dashboard.html | head -1 | grep -o "[0-9]*" | head -1)
    dash_delay=$(grep -o "const randomDelay = ([0-9]* + Math.random() \* [0-9]*) \* 1000;" dashboard.html | head -1 | sed -E 's/const randomDelay = \(([0-9]*) \+ Math\.random\(\) \* ([0-9]*)\) \* 1000;/\1-\2/')
    if [[ $dash_delay =~ ^([0-9]+)-([0-9]+)$ ]]; then
        min_d=${BASH_REMATCH[1]}
        max_d=${BASH_REMATCH[2]}
        total_max=$((max_d + min_d))
        dash_delay="${min_d}-${total_max}"
    fi
    dash_market=$(grep -B2 -A1 "fetchSidebarTickers(false)" dashboard.html | grep -o "}, [0-9]* \* [0-9]* \* 1000);" | head -1 | sed -E 's/}, ([0-9]+) \* ([0-9]+) \* 1000\);/\1*\2/' | bc)
    if [[ -z "$dash_market" ]]; then
        dash_market=$(grep -B2 -A1 "fetchSidebarTickers(false)" dashboard.html | grep -o "}, [0-9]* \* 1000);" | head -1 | grep -o "[0-9]*" | head -1)
    fi
    echo "  Fetch interval: ${dash_ticker:-Not found}s"
    echo "  Display delays: ${dash_delay:-Not found}s"
    echo "  Total update time: ${dash_ticker:-0}-$((dash_ticker + total_max))s"
    echo "  Market indices: ${dash_market:-Not found}s"
    echo ""
    exit 0
fi

if [[ $option == "1" ]]; then
    read -p "Enter ticker interval in seconds (e.g., '10' or '300'): " ticker_seconds
    if [[ ! $ticker_seconds =~ ^[0-9]+$ ]]; then
        echo "Invalid format. Use seconds only"
        exit 1
    fi
    if [ $ticker_seconds -lt 5 ]; then
        echo "Error: Minimum interval is 5 seconds to prevent API overload"
        exit 1
    fi
    read -p "Enter min delay in seconds (e.g., '0'): " min_delay
    if [[ ! $min_delay =~ ^[0-9]+$ ]]; then
        echo "Invalid format. Use seconds only"
        exit 1
    fi
    read -p "Enter max delay in seconds (e.g., '10'): " max_delay
    if [[ ! $max_delay =~ ^[0-9]+$ ]]; then
        echo "Invalid format. Use seconds only"
        exit 1
    fi
    if [ $max_delay -lt $min_delay ]; then
        echo "Error: Max delay must be >= min delay"
        exit 1
    fi
elif [[ $option == "2" ]]; then
    read -p "Enter market indices interval in seconds (e.g., '300'): " market_seconds
    if [[ ! $market_seconds =~ ^[0-9]+$ ]]; then
        echo "Invalid format. Use seconds only"
        exit 1
    fi
    if [ $market_seconds -lt 5 ]; then
        echo "Error: Minimum interval is 5 seconds to prevent API overload"
        exit 1
    fi
elif [[ $option == "3" ]]; then
    read -p "Enter ticker and market interval in seconds (e.g., '10' or '300'): " both_seconds
    if [[ ! $both_seconds =~ ^[0-9]+$ ]]; then
        echo "Invalid format. Use seconds only"
        exit 1
    fi
    if [ $both_seconds -lt 5 ]; then
        echo "Error: Minimum interval is 5 seconds to prevent API overload"
        exit 1
    fi
    ticker_seconds=$both_seconds
    market_seconds=$both_seconds
    read -p "Enter min delay in seconds (e.g., '0'): " min_delay
    if [[ ! $min_delay =~ ^[0-9]+$ ]]; then
        echo "Invalid format. Use seconds only"
        exit 1
    fi
    read -p "Enter max delay in seconds (e.g., '10'): " max_delay
    if [[ ! $max_delay =~ ^[0-9]+$ ]]; then
        echo "Invalid format. Use seconds only"
        exit 1
    fi
    if [ $max_delay -lt $min_delay ]; then
        echo "Error: Max delay must be >= min delay"
        exit 1
    fi
fi

echo ""

# Update ticker sections
if [[ $option == "1" ]] || [[ $option == "3" ]]; then
    echo "Setting ticker interval: ${ticker_seconds} seconds"
    
    # Section stagger: spread across full interval
    section_stagger_ms=$(($ticker_seconds * 1000))
    
    # Update shouldFetch checks
    sed -i '' -E "s/\(now - parseInt\(lastFetch\)\) >= [0-9]+ \* 1000/(now - parseInt(lastFetch)) >= $ticker_seconds * 1000/g" index.html
    sed -i '' -E "s/\(now - parseInt\(lastFetch\)\) >= [0-9]+ \* 1000/(now - parseInt(lastFetch)) >= $ticker_seconds * 1000/g" dashboard.html
    
    # Update setInterval timer
    sed -i '' -E "s/}, [0-9]+ \* 1000\);/}, $ticker_seconds * 1000);/g" index.html
    sed -i '' -E "s/}, [0-9]+ \* 1000\);/}, $ticker_seconds * 1000);/g" dashboard.html
    
    # Update per-ticker random delay formula
    max_range=$((max_delay - min_delay))
    sed -i '' -E "s/\([0-9]+ \+ Math\.random\(\) \* [0-9]+\) \* 1000/($min_delay + Math.random() * $max_range) * 1000/g" index.html
    sed -i '' -E "s/\([0-9]+ \+ Math\.random\(\) \* [0-9]+\) \* 1000/($min_delay + Math.random() * $max_range) * 1000/g" dashboard.html
    
    # Update section-level stagger (spread across full interval)
    sed -i '' -E "s/}, Math\.random\(\) \* [0-9]+\)/}, Math.random() * $section_stagger_ms)/g" index.html
    sed -i '' -E "s/}, Math\.random\(\) \* [0-9]+\)/}, Math.random() * $section_stagger_ms)/g" dashboard.html
    
    echo "✅ Ticker sections updated"
    echo "   - Refresh interval: ${ticker_seconds}s"
    echo "   - Display delays: ${min_delay}-${max_delay}s"
fi

# Update market indices
if [[ $option == "2" ]] || [[ $option == "3" ]]; then
    echo "Setting market indices interval: ${market_seconds} seconds"
    
    # Update market indices refresh interval in index.html
    sed -i '' -E "/Refresh market data every.*minutes/,/^\}, [0-9]+ \* 1000\);/ s/\}, ([0-9]+) \* 1000\);/}, $market_seconds * 1000);/" index.html
    
    # Update market indices refresh interval in dashboard.html
    sed -i '' -E "s/(fetchSidebarTickers\(false\);[[:space:]]*}, )[0-9]+ \* 1000\);/\1$market_seconds * 1000);/g" dashboard.html
    
    # Update market indices random delay (only in index.html for the 4 cards)
    if [[ $option == "3" ]]; then
        max_range=$((max_delay - min_delay))
        sed -i '' -E "s/const randomDelay = \(0 \+ Math\.random\(\) \* [0-9]+\) \* 1000;/const randomDelay = ($min_delay + Math.random() * $max_range) * 1000;/g" index.html
        echo "✅ Market indices updated"
        echo "   - Refresh interval: ${market_seconds}s"
        echo "   - Display delays: ${min_delay}-${max_delay}s"
    else
        echo "✅ Market indices updated"
        echo "   - Refresh interval: ${market_seconds}s"
    fi
fi

echo ""
echo "✅ All updates completed successfully!"
echo ""
echo "Update behavior:"
echo "  - Fetch interval: ${ticker_seconds}s"
echo "  - Display delays: ${min_delay}-${max_delay}s"
echo "  - Total update time: $((ticker_seconds + min_delay))-$((ticker_seconds + max_delay))s"
