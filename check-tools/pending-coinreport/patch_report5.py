"""Fifth step for the single-stock report function: it reports on a coin too, so that the "single coin" button can use it
(the button had a function of its own: a third copy of the old crypto worker with its own scoring and its own RSI).
    python3 patch_report5.py <live lambda_function2.py> <out lambda_function2.py> <orchestrator.py> <analysis-functions.js>
A request with "asset": "crypto" names coins by their symbols (BTC, SUI): each is priced by the ticker the crypto
screener uses for it (SUI is SUI20947-USD: the map is taken from the orchestrator's COINS and must equal the page's).
For a coin the report leaves out what belongs to a company (figures, dividends, the stock market's mood, the stock
page's news), says "since 00:00 UTC" where it said "today", and a background run is saved as "<SYMBOL> Coin Analysis",
which is how the dashboard knows a single-coin entry. A share's report does not change by a character."""
import sys, re, ast, json
src = open(sys.argv[1]).read(); orch = open(sys.argv[3]).read(); page = open(sys.argv[4]).read()
def swap(text, old, new, count=1):
    assert text.count(old) == count, (text.count(old), old[:90])
    return text.replace(old, new)

# the coin tickers: the screener's own list, checked against the page's map
m = re.search(r"COINS = \[(.*?)\n    \]", orch, re.S); assert m
pairs = ast.literal_eval('[' + m.group(1) + ']')
tickers = {display: ticker for display, ticker in pairs if display != ticker}
page_map = json.loads(re.search(r"const CRYPTO_TICKER_MAP = (\{.*?\});", page).group(1))
assert tickers == page_map, sorted(set(tickers.items()) ^ set(page_map.items()))[:6]
wrong = json.loads(re.search(r"const mismatchedCoinSymbols = (\[.*?\]);", page).group(1))
def wrapped(items, width=118, indent='    '):
    lines, line = [], indent
    for item in items:
        if len(line) + len(item) + 2 > width: lines.append(line.rstrip()); line = indent
        line += item + ', '
    return '\n'.join(lines + [line.rstrip()])
COIN_BLOCK = ('''# Coins: the ticker the price source knows each one by, where the plain symbol is a different coin (SUI is SUI20947-USD).
# The crypto screener's own list (COINS in stockiq-option-7-1-orchestrator; the page's CRYPTO_TICKER_MAP is the same):
# keep the three in step (check-tools/report/report_test.py compares this one with the orchestrator's).
COIN_TICKERS = {
''' + wrapped([f"{d!r}: {t!r}" for d, t in sorted(tickers.items())]) + '''
}
# Symbols the price source is known to list a different coin under (checked against CoinGecko, 9 Oct 2026)
COIN_WRONG_MATCH = {
''' + wrapped([repr(s) for s in sorted(wrong)]) + '''
}

def coin_ticker(symbol):
    """(the symbol shown, the price source's ticker) for a coin named by its symbol: 'sui' -> ('SUI', 'SUI20947-USD')"""
    label = str(symbol).upper().strip()
    if label.endswith('-USD'):
        label = label[:-4]
    return label, COIN_TICKERS.get(label, label) + '-USD'

def without_section(lines, starts, ends):
    """The report's lines without the section whose heading holds `starts`, up to the heading that holds `ends`
    (each heading is preceded by a line of ====, which goes or stays with it)"""
    first = next((i for i, line in enumerate(lines) if starts in line), None)
    last = next((i for i, line in enumerate(lines) if ends in line), None)
    if first is None or last is None or last <= first:
        return lines
    return lines[:first - 1] + lines[last - 1:]

''')
src = swap(src, "FIGURE_KEYS = ('pe_ratio',", COIN_BLOCK + "FIGURE_KEYS = ('pe_ratio',")

# the request
src = swap(src, "        symbols = body.get('symbols', [])\n", "        symbols = body.get('symbols', [])\n        asset = str(body.get('asset') or '').lower()   # 'crypto': the symbols are coins (the single-coin button)\n        labels = {}\n")
src = swap(src, """                clean_symbol = str(symbol).upper().strip()
                if len(clean_symbol) >= 1:
                    clean_symbols.append(clean_symbol)
""", """                clean_symbol = str(symbol).upper().strip()
                if len(clean_symbol) >= 1:
                    if asset == 'crypto':
                        label, clean_symbol = coin_ticker(clean_symbol)
                        labels[clean_symbol] = label
                    clean_symbols.append(clean_symbol)
""")
src = swap(src, "analysis = analyze_stock_comprehensive_enhanced(symbol, timezone_offset, is_background)", "analysis = analyze_stock_comprehensive_enhanced(symbol, timezone_offset, is_background, labels.get(symbol))")
src = swap(src, "save_analysis_history(save_user_id, symbol, symbol, analysis.get('comprehensive_analysis'),", "save_analysis_history(save_user_id, analysis.get('label') or symbol, analysis.get('history_name') or symbol, analysis.get('comprehensive_analysis'),")
src = swap(src, "            'companyName': f'Analysis {symbol.upper()}' if is_background else (company_name or ''),\n",
           "            # a coin is saved as \"<SYMBOL> Coin Analysis\": that name is how the dashboard knows a single-coin entry\n            'companyName': company_name if str(company_name or '').endswith(' Coin Analysis') else (f'Analysis {symbol.upper()}' if is_background else (company_name or '')),\n")
src = swap(src, "            'isRead': False if is_background else True\n        }\n", "            'isRead': False if is_background else True\n        }\n        if str(company_name or '').endswith(' Coin Analysis'):\n            item['analysisType'] = 'crypto_single'\n")

# putting a report together
src = swap(src, "def analyze_stock_comprehensive_enhanced(symbol, timezone_offset=None, is_background=False):", "def analyze_stock_comprehensive_enhanced(symbol, timezone_offset=None, is_background=False, label=None):")
src = swap(src, '''        print(f"Got {len(stock_data)} data points for {symbol}")\n''', '''        print(f"Got {len(stock_data)} data points for {symbol}")
        
        # A coin: the single-coin button sends its symbols as coins; a ticker like BTC-USD typed as a stock is one too
        is_coin = _report_ctx.get('instrument') == 'CRYPTOCURRENCY'
        _report_ctx['coin'] = is_coin
        _report_ctx['label'] = (label or re.sub(r'-USD$', '', symbol)) if is_coin else None
''')
src = swap(src, "        fundamentals = fetch_enhanced_fundamentals(symbol)\n        fill_missing_figures(symbol, fundamentals)\n",
           "        # a coin has no company figures and pays no dividend: nothing is asked for\n        fundamentals = {} if is_coin else fetch_enhanced_fundamentals(symbol)\n        if not is_coin:\n            fill_missing_figures(symbol, fundamentals)\n")
src = swap(src, """        market_sentiment = fetch_market_sentiment()
        recent_news = fetch_recent_news_from_stock_page(symbol)
        news_sentiment = fetch_news_sentiment_enhanced(symbol)
""", """        # (not for a coin: the VIX is the stock market's mood, and the news comes from the share's own stock page)
        market_sentiment = None if is_coin else fetch_market_sentiment()
        recent_news = None if is_coin else fetch_recent_news_from_stock_page(symbol)
        news_sentiment = None if is_coin else fetch_news_sentiment_enhanced(symbol)
""")
src = swap(src, "            'symbol': symbol,\n            'current_price': current,", "            'symbol': symbol,\n            'label': _report_ctx.get('label') or symbol,\n            'asset': 'crypto' if is_coin else 'share',\n            'history_name': f\"{_report_ctx.get('label')} Coin Analysis\" if is_coin else None,\n            'current_price': current,")
src = swap(src, "            'symbol': symbol,\n            'return_type': 'url'", "            'symbol': _report_ctx.get('label') or symbol,          # the chart's title; a coin's familiar symbol, not its ticker\n            'return_type': 'url'")

# the text
src = swap(src, '''    analysis.append(f"📊 CUSTOM STOCK ANALYSIS RESULTS (REAL-TIME DATA)")\n''', '''    coin = bool(_report_ctx.get('coin'))
    shown = _report_ctx.get('label') or symbol
    day_words = 'since 00:00 UTC' if coin else 'today'      # a coin's day runs from midnight UTC, and never closes
    analysis.append(f"🔍 SINGLE COIN ANALYSIS: {shown}" if coin else f"📊 CUSTOM STOCK ANALYSIS RESULTS (REAL-TIME DATA)")\n''')
src = swap(src, """    company_name = get_company_name(symbol) or _report_ctx.get('name')
    symbol_display = f"{symbol} - {company_name}" if company_name else symbol
""", """    if coin:
        company_name = re.sub(r'\\s+USD$', '', _report_ctx.get('name') or '')
    else:
        company_name = get_company_name(symbol) or _report_ctx.get('name')
    symbol_display = f"{shown} - {company_name}" if company_name else shown
""")
src = swap(src, "% today)\")", "% {day_words})\")", 2)
src = swap(src, "    if currency_note(current):\n        analysis.append(currency_note(current))\n", """    if currency_note(current):
        analysis.append(currency_note(current))
    if coin:
        analysis.append(f"ℹ️ Priced as {symbol} on Yahoo Finance, in US dollars. Some symbols are shared by more than one coin: check the price matches the coin you mean")
        if shown in COIN_WRONG_MATCH:
            analysis.append(f"⚠️ {shown}: the price source lists a different coin under this symbol, so this analysis is probably not for the coin you mean")
""")
src = swap(src, '''        analysis.append(f"• No company figures were available for this share, so this score is from price and volume only")''',
           '''        analysis.append(f"• A coin has no company figures: this score is from price and volume only" if coin else f"• No company figures were available for this share, so this score is from price and volume only")''')
src = swap(src, '''        analysis.append(f"• Today's session is still open: the price is the latest, and today's part-day volume is left out")''',
           '''        analysis.append(f"• Coins trade around the clock: the price is the latest, and volume is measured on the last full day (UTC)" if coin else f"• Today's session is still open: the price is the latest, and today's part-day volume is left out")''')
src = swap(src, '    return "\\n".join(analysis)\n', '''    if coin:
        # What belongs to a company or to the stock market has no place in a coin's report
        analysis = without_section(analysis, '💰 FUNDAMENTAL ANALYSIS', '⚠️ RISK ASSESSMENT')
        drop = ('🌍 MARKET CONTEXT:', '• Company figures:', '• Dividends:', '• Market sentiment:')
        analysis = [line for line in analysis if not any(word in line for word in drop)]
        analysis = [line.replace('Fundamental metrics', 'Company figures') for line in analysis]
    return "\\n".join(analysis)\n''')
compile(src, 'lambda_function2.py', 'exec'); open(sys.argv[2], 'w').write(src); print('written:', len(src.split('\n')), 'lines;', len(tickers), 'coin tickers,', len(wrong), 'known wrong matches')
