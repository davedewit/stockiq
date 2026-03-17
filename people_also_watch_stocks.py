#!/usr/bin/env python3
"""
One-time script to add/update the 'People also watch' section on all stock pages.
Creates static internal links to sector peers (good for SEO — funnels link equity to flagship pages).

Selection logic: hybrid — 3 from PRIORITY_STOCKS (well-known sector anchors) + 2 random same-sector peers.
See future-work.md Fix 1 to replace with pure anchor logic.

Usage:
    python3 people_also_watch_stocks.py              # Interactive menu
    python3 people_also_watch_stocks.py --all        # Update all pages
    python3 people_also_watch_stocks.py --missing    # Only pages missing the section
    python3 people_also_watch_stocks.py AAPL MSFT    # Specific symbols
"""

import random
import re

# Top stocks by sector (S&P 500 / NASDAQ 100 large caps)
PRIORITY_STOCKS = {
    'Technology': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META', 'AVGO', 'ORCL', 'ADBE', 'CRM', 'CSCO', 'ACN', 'AMD', 'INTC', 'IBM', 'NOW', 'QCOM', 'AMAT', 'MU', 'LRCX', 'KLAC'],
    'Healthcare': ['UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'BMY', 'AMGN', 'GILD', 'CVS', 'CI', 'ISRG', 'REGN', 'VRTX', 'ZTS', 'ELV', 'MCK'],
    'Financial Services': ['BRK.B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'SPGI', 'BLK', 'C', 'AXP', 'SCHW', 'CB', 'PGR', 'MMC', 'AON', 'USB', 'TFC', 'PNC'],
    'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'TJX', 'LOW', 'BKNG', 'CMG', 'MAR', 'GM', 'F', 'ABNB', 'ORLY', 'AZO', 'YUM', 'DRI', 'ROST', 'DHI'],
    'Communication Services': ['GOOGL', 'META', 'NFLX', 'DIS', 'CMCSA', 'T', 'VZ', 'TMUS', 'EA', 'TTWO', 'CHTR', 'OMC', 'PARA', 'FOXA', 'MTCH', 'NWSA', 'IPG', 'LYV', 'WBD', 'PINS'],
    'Consumer Defensive': ['PG', 'KO', 'PEP', 'COST', 'WMT', 'PM', 'MO', 'MDLZ', 'CL', 'KMB', 'GIS', 'K', 'HSY', 'SYY', 'KHC', 'TSN', 'CAG', 'CPB', 'HRL', 'SJM'],
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'WMB', 'KMI', 'HAL', 'BKR', 'FANG', 'DVN', 'HES', 'MRO', 'APA', 'CTRA', 'OKE'],
    'Industrials': ['UNP', 'HON', 'UPS', 'RTX', 'BA', 'CAT', 'GE', 'LMT', 'DE', 'MMM', 'GD', 'NOC', 'ETN', 'ITW', 'EMR', 'PH', 'FDX', 'CSX', 'NSC', 'WM'],
    'Basic Materials': ['LIN', 'APD', 'SHW', 'ECL', 'DD', 'NEM', 'FCX', 'NUE', 'DOW', 'ALB', 'VMC', 'MLM', 'PPG', 'CTVA', 'IFF', 'CE', 'EMN', 'FMC', 'MOS', 'CF'],
    'Real Estate': ['PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'SPG', 'O', 'WELL', 'DLR', 'AVB', 'EQR', 'VTR', 'ARE', 'INVH', 'MAA', 'ESS', 'UDR', 'CPT', 'HST', 'PEAK'],
    'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'ED', 'WEC', 'ES', 'PEG', 'FE', 'ETR', 'AWK', 'DTE', 'PPL', 'CMS', 'AEE', 'LNT'],
}

def load_stocks():
    """Load all stocks from stocks.txt using csv.reader (handles quoted company names with commas)."""
    import csv
    stocks = []
    with open('/Users/ddewit/VSCODE/website/stocks.txt', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3:
                stocks.append({
                    'symbol': row[0].strip(),
                    'name': row[1].strip(),
                    'sector': row[2].strip()
                })
    return stocks

def get_country_from_symbol(symbol):
    """Extract country code from symbol suffix (e.g. .HK=Hong Kong, .AX=Australia, .T=Japan)."""
    if '.HK' in symbol:
        return 'HK'
    elif '.AX' in symbol:
        return 'AU'
    elif '.TO' in symbol:
        return 'CA'
    elif '.T' in symbol:
        return 'JP'
    elif '.L' in symbol:
        return 'UK'
    elif '.PA' in symbol:
        return 'FR'
    elif '.DE' in symbol:
        return 'DE'
    else:
        return 'US'

def get_related_stocks(symbol, stocks_data, count=5):
    """Get up to 5 related stocks from the same country and sector using hybrid selection (3 priority anchors + 2 random)."""
    current = next((s for s in stocks_data if s['symbol'] == symbol), None)
    if not current:
        return []
    
    country = get_country_from_symbol(symbol)
    sector = current['sector']
    
    # Filter by country and sector
    related = [s for s in stocks_data 
               if s['symbol'] != symbol 
               and get_country_from_symbol(s['symbol']) == country
               and s['sector'] == sector]
    
    # Fallback: if not enough country peers, fill with same-sector global stocks
    if len(related) < count:
        global_peers = [s for s in stocks_data
                        if s['symbol'] != symbol
                        and s['sector'] == sector
                        and s not in related]
        related = related + global_peers

    if len(related) <= count:
        return related
    
    # Get priority stocks for this sector
    priority = PRIORITY_STOCKS.get(sector, [])
    top_related = [s for s in related if s['symbol'] in priority]
    other_related = [s for s in related if s['symbol'] not in priority]
    
    # Hybrid selection: 60% priority, 40% random
    result = []
    
    # Add 3 from priority stocks (if available)
    if top_related:
        result.extend(random.sample(top_related, min(3, len(top_related))))
    
    # Fill remaining with random stocks
    remaining = count - len(result)
    if remaining > 0 and other_related:
        result.extend(random.sample(other_related, min(remaining, len(other_related))))
    
    # If still not enough, fill from any related
    if len(result) < count and related:
        remaining_stocks = [s for s in related if s not in result]
        if remaining_stocks:
            result.extend(random.sample(remaining_stocks, min(count - len(result), len(remaining_stocks))))
    
    return result[:count]

def generate_related_section(related_stocks):
    """Generate the HTML for the 'People also watch' cards section."""
    if not related_stocks:
        return ""
    
    cards_html = ""
    for stock in related_stocks:
        cards_html += f'''
            <a href="{stock['symbol']}.html" style="text-decoration: none; color: inherit;">
                <div style="background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px; min-width: 160px; cursor: pointer; transition: box-shadow 0.2s;">
                    <div style="font-size: 1.1em; font-weight: bold; color: #007bff; margin-bottom: 4px;">{stock['symbol']}</div>
                    <div style="font-size: 0.75em; color: var(--text-secondary); margin-bottom: 4px;">{stock['name']}</div>
                    <div class="stock-price" data-symbol="{stock['symbol']}" style="font-size: 0.75em; color: var(--text-secondary);">--</div>
                </div>
            </a>'''
    
    return f'''<!-- RELATED_SECTION_START -->
        <div style="margin: 40px 0; padding: 20px; background: var(--bg-primary); border-radius: 8px;">
            <h2 style="margin-top: 0; color: var(--text-primary);">People also watch</h2>
            <div style="display: flex; gap: 12px; overflow-x: auto; padding: 10px 0;">
                {cards_html}
            </div>
        </div>
        <!-- RELATED_SECTION_END -->'''

def add_related_to_page(symbol, stocks_data):
    """Insert or replace the related stocks section in a single stock page HTML file."""
    filepath = f'/Users/ddewit/VSCODE/website/stocks/{symbol}.html'
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return False
    
    # Remove existing related stocks section if present
    if '<!-- RELATED_SECTION_START -->' in content:
        content = re.sub(r'<!-- RELATED_SECTION_START -->.*?<!-- RELATED_SECTION_END -->', '<!-- RELATED_SECTION_START -->\n        <!-- RELATED_SECTION_END -->', content, flags=re.DOTALL)
    
    # Get related stocks
    related = get_related_stocks(symbol, stocks_data, count=5)
    if not related:
        print(f"⚠️  {symbol} has no related stocks")
        return True
    
    # Generate related section HTML
    related_html = generate_related_section(related)
    
    # Insert into markers (preferred) or before </main> (legacy pages)
    if '<!-- RELATED_SECTION_START -->' in content:
        new_content = content.replace(
            '<!-- RELATED_SECTION_START -->\n        <!-- RELATED_SECTION_END -->',
            related_html
        )
    else:
        main_pattern = r'(\s*</main>)'
        match = re.search(main_pattern, content)
        if not match:
            print(f"❌ {symbol}: Could not find </main> tag")
            return False
        new_content = content[:match.start()] + '\n' + related_html + '\n' + content[match.start():]
    
    # Write back to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    related_symbols = [s['symbol'] for s in related]
    print(f"✅ {symbol} → {', '.join(related_symbols)}")
    return True

def main():
    import sys

    # Load all stocks
    print("Loading stocks from stocks.txt...")
    stocks_data = load_stocks()
    print(f"Loaded {len(stocks_data)} stocks")

    # Count missing
    missing = []
    for s in stocks_data:
        filepath = f'/Users/ddewit/VSCODE/website/stocks/{s["symbol"]}.html'
        try:
            with open(filepath, 'r') as f:
                if 'People also watch' not in f.read():
                    missing.append(s)
        except FileNotFoundError:
            pass
    print(f"With 'People also watch': {len(stocks_data) - len(missing)} | Missing: {len(missing)}\n")

    # Handle command-line args (non-interactive)
    if len(sys.argv) > 1:
        if sys.argv[1] == '--missing':
            stocks_to_process = missing
            print(f"MISSING MODE: {len(stocks_to_process)} pages\n")
        elif sys.argv[1] == '--all':
            stocks_to_process = stocks_data
            print(f"FULL MODE: {len(stocks_to_process)} pages\n")
        else:
            test_symbols = sys.argv[1:]
            stocks_to_process = [s for s in stocks_data if s['symbol'] in test_symbols]
            print(f"SYMBOL MODE: {len(stocks_to_process)} pages\n")
    else:
        # Interactive menu
        print("What would you like to do?")
        print("  1. Update ALL pages (re-randomises related stocks)")
        print("  2. Update only MISSING pages (no 'People also watch' yet)")
        print("  3. Update specific symbols")
        print("  q. Quit")
        choice = input("\nChoice: ").strip().lower()

        if choice == '1':
            stocks_to_process = stocks_data
            print(f"\nFULL MODE: {len(stocks_to_process)} pages\n")
        elif choice == '2':
            stocks_to_process = missing
            print(f"\nMISSING MODE: {len(stocks_to_process)} pages\n")
        elif choice == '3':
            symbols_input = input("Enter symbols (space or comma separated): ").strip()
            symbols = [s.strip().upper() for s in symbols_input.replace(',', ' ').split()]
            stocks_to_process = [s for s in stocks_data if s['symbol'] in symbols]
            print(f"\nSYMBOL MODE: {len(stocks_to_process)} pages\n")
        else:
            print("Quit.")
            return

    # Process
    success_count = 0
    for stock in stocks_to_process:
        if add_related_to_page(stock['symbol'], stocks_data):
            success_count += 1

    print(f"\n✅ Completed: {success_count}/{len(stocks_to_process)} stocks updated")

if __name__ == "__main__":
    main()
