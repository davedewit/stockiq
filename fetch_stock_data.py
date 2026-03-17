#!/usr/bin/env python3
"""
Fetch company names and sectors from Yahoo Finance and update stocks.txt.

Only processes stocks where sector == 'Stock' (placeholder for unfetched entries).
Stocks that return no data from Yahoo Finance are removed from stocks.txt.
Also auto-updates NUMERIC_COMPANY_NAMES in update_stock_news.py for non-US
numeric symbols (e.g. 0700.HK, 7203.T) so news matching stays in sync.

Usage:
    python3 fetch_stock_data.py

Input/Output: /Users/ddewit/VSCODE/website/stocks.txt

Note: To re-fetch ALL stocks (not just 'Stock' placeholders), change:
    to_fetch = [s for s in all_stocks if s[2] == 'Stock']
to:
    to_fetch = all_stocks
"""

import yfinance as yf
import time
import os
import csv
import re
import sys

def update_numeric_company_names(stocks):
    """Extract numeric symbols from stocks list and update NUMERIC_COMPANY_NAMES dict in update_stock_news.py."""
    
    print("   Extracting numeric symbols...", flush=True)
    
    # Extract numeric symbols and their company names
    numeric_stocks = {}
    for symbol, name, sector in stocks:
        # Check if symbol is numeric (e.g., 0700.HK, 0005.HK, 7203.T)
        base_symbol = symbol.split('.')[0]
        if base_symbol.isdigit():
            # Extract key words from company name (remove common suffixes)
            words = re.findall(r'\b[A-Z][A-Za-z]*\b', name)
            skip_words = {'INC', 'CORP', 'LTD', 'LIMITED', 'PLC', 'CO', 'COMPANY', 'GROUP', 'HOLDINGS', 'THE', 'AND', '&', 'SA', 'AG', 'SE', 'NV', 'N.V.'}
            key_words = [w.upper() for w in words if w.upper() not in skip_words]
            
            if key_words:
                numeric_stocks[symbol] = key_words[0] if len(key_words) == 1 else ' '.join(key_words[:2])
    
    if not numeric_stocks:
        print("   No numeric symbols found to update")
        return
    
    print(f"   Found {len(numeric_stocks)} numeric symbols", flush=True)
    print("   Reading update_stock_news.py...", flush=True)
    
    # Read update_stock_news.py
    update_script = '/Users/ddewit/VSCODE/stockiq/update_stock_news.py'
    with open(update_script, 'r') as f:
        content = f.read()
    
    # Find and replace NUMERIC_COMPANY_NAMES dictionary
    # Use a more robust pattern that handles multiple lines
    pattern = r'NUMERIC_COMPANY_NAMES = \{[\s\S]*?\n\}'
    
    print("   Building new dictionary...", flush=True)
    
    # Build new dictionary
    dict_lines = ['NUMERIC_COMPANY_NAMES = {']
    for symbol in sorted(numeric_stocks.keys()):
        name = numeric_stocks[symbol]
        dict_lines.append(f"    '{symbol}': '{name}',")
    dict_lines.append('}')
    new_dict = '\n'.join(dict_lines)
    
    print("   Replacing in file...", flush=True)
    
    # Replace in content
    new_content = re.sub(pattern, new_dict, content)
    
    # Write back
    with open(update_script, 'w') as f:
        f.write(new_content)
    
    print(f"   ✅ Updated NUMERIC_COMPANY_NAMES with {len(numeric_stocks)} numeric symbols", flush=True)

# Read all stocks
all_stocks = []
stocks_file = '/Users/ddewit/VSCODE/website/stocks.txt'

# Try to read existing stocks.txt, or start fresh
if os.path.exists(stocks_file):
    with open(stocks_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3:
                symbol = row[0]
                name = row[1]
                sector = row[2]
                all_stocks.append([symbol, name, sector])
else:
    print("stocks.txt not found, starting fresh")
    all_stocks = []

# Find stocks with placeholder names (all of them)
to_fetch = [s for s in all_stocks if s[2] == 'Stock']

print(f"Fetching info for {len(to_fetch)} stocks...\n")

# Track symbols to remove
to_remove = []

# Fetch info
import sys
for i, (symbol, _, _) in enumerate(to_fetch, 1):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        name = info.get('longName') or info.get('shortName', symbol)
        sector = info.get('sector', 'Stock')
        
        # Only update if we got real data (not just the symbol back)
        if name != symbol or sector != 'Stock':
            for j, s in enumerate(all_stocks):
                if s[0] == symbol:
                    all_stocks[j] = [symbol, name, sector]
                    break
            print(f"{i}/{len(to_fetch)}: {symbol} - {name}", flush=True)
            sys.stdout.flush()
        else:
            to_remove.append(symbol)
            print(f"{i}/{len(to_fetch)}: {symbol} - Not found, removing", flush=True)
            sys.stdout.flush()
        
        time.sleep(0.3)
    except:
        to_remove.append(symbol)
        print(f"{i}/{len(to_fetch)}: {symbol} - Error, removing", flush=True)
        sys.stdout.flush()

# Write once at the end
current_stocks = [s for s in all_stocks if s[0] not in to_remove]
with open('/Users/ddewit/VSCODE/website/stocks.txt', 'w', newline='') as f:
    writer = csv.writer(f)
    for s in current_stocks:
        writer.writerow([s[0], s[1], s[2]])

print(f"\n✅ Done! Updated stocks.txt")
print(f"Removed {len(to_remove)} stocks that weren't found")
print(f"Final count: {len([s for s in all_stocks if s[0] not in to_remove])} stocks")

# Update NUMERIC_COMPANY_NAMES in update_stock_news.py
print("\n🔄 Updating NUMERIC_COMPANY_NAMES in update_stock_news.py...")
update_numeric_company_names(current_stocks)
