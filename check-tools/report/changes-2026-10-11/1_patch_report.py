"""Builds the new single-stock report function from the live copy, by exact, asserted replacements.
    python3 patch_report.py <live lambda_function2.py> <out lambda_function2.py>
Everything not named here stays byte for byte as it is live."""
import sys, re

src = open(sys.argv[1]).read()

def swap(text, old, new, count=1):
    assert text.count(old) == count, (text.count(old), old[:90])
    return text.replace(old, new)

def cut(text, start, end):
    """(before, the part from start up to end, after)"""
    a = text.index(start); b = text.index(end, a + len(start))
    assert text.count(start) == 1, start[:60]
    return text[:a], text[a:b], text[b:]

# ---------------------------------------------------------------------------------------------------------------
# 1. Prices: one bar a day, the latest session from the quote when its bar arrives empty, and what Yahoo says about
#    the symbol (currency, name, whether today's session is still open)
before, _old, after = cut(src, 'def fetch_stock_data(symbol):', 'def calculate_rsi(closes, period=14):')
NEW_FETCH = r'''# What Yahoo said about the symbol of the report being written: its currency ('USD', 'AUD', 'GBp' = pence ...), its
# name, what kind of thing it is ('EQUITY', 'ETF' ...) and whether today's session is still open
_report_ctx = {}

MONEY_SIGNS = {'USD': '$', 'AUD': 'A$', 'CAD': 'C$', 'NZD': 'NZ$', 'HKD': 'HK$', 'SGD': 'S$', 'GBP': '£', 'EUR': '€',
               'JPY': '¥', 'CNY': 'CN¥', 'INR': '₹', 'KRW': '₩'}
MINOR_UNITS = {'GBp': ('p', 'GBP', 'pence'), 'GBX': ('p', 'GBP', 'pence'), 'ZAc': ('c', 'ZAR', 'cents'), 'ZAC': ('c', 'ZAR', 'cents'),
               'ILA': (' agorot', 'ILS', 'agorot')}

def money(value, places=2):
    """A price in the currency the share trades in (until Oct 2026 every share was printed with a dollar sign)"""
    if value is None:
        return 'N/A'
    cur = _report_ctx.get('currency') or ''
    if cur in MINOR_UNITS:
        return f"{value:,.{places}f}{MINOR_UNITS[cur][0]}"
    if cur in MONEY_SIGNS or not cur:
        return f"{MONEY_SIGNS.get(cur, '$')}{value:,.{places}f}"
    return f"{cur} {value:,.{places}f}"

def currency_note(price):
    """One line saying what the prices are in, when it is not US dollars ('' for a US share)"""
    cur = _report_ctx.get('currency') or ''
    if cur in MINOR_UNITS:
        unit, major, word = MINOR_UNITS[cur]
        return f"ℹ️ Prices for this share are in {word}: {money(price)} is {MONEY_SIGNS.get(major, major + ' ')}{price / 100:,.2f}"
    if cur and cur != 'USD':
        return f"ℹ️ Prices for this share are in {cur} ({MONEY_SIGNS.get(cur, cur).strip()})"
    return ''

def bars_from_chart(result, now=None):
    """Daily bars from one Yahoo chart answer, oldest first, one bar per trading day: the same rules as the screener
    workers (workers/stock_worker.py). Returns (bars, facts about the symbol)."""
    timestamps = result.get('timestamp') or []
    quotes = (result.get('indicators') or {}).get('quote') or []
    meta = result.get('meta') or {}
    offset = meta.get('gmtoffset') or 0

    def day(timestamp):
        # The trading day a time belongs to, on the exchange's own clock
        return (int(timestamp) + offset) // 86400

    bars = []
    prices = quotes[0] if quotes else {}
    for i, ts in enumerate(timestamps):
        try:
            close, high, low = prices['close'][i], prices['high'][i], prices['low'][i]
            if close is None or high is None or low is None:
                continue
            bar = {'date': datetime.fromtimestamp(ts), 'timestamp': ts, 'open': prices['open'][i] or close,
                   'high': high, 'low': low, 'close': close, 'volume': prices['volume'][i] or 0}
        except (KeyError, IndexError, TypeError):
            continue
        # Once a market has closed Yahoo can send its last session twice (seen on the ASX): two bars for one day made
        # "today's change" 0.00%. One bar a day, the later one.
        if bars and day(bars[-1]['timestamp']) == day(ts):
            bars[-1] = bar
        else:
            bars.append(bar)

    # The latest session can arrive with empty figures (seen for London shares), which left the price a day old.
    # The quote that comes with the chart has that session: use it as the last bar.
    price = meta.get('regularMarketPrice')
    quoted = meta.get('regularMarketTime')
    if (bars and isinstance(price, (int, float)) and price > 0 and isinstance(quoted, (int, float))
            and day(quoted) > day(bars[-1]['timestamp'])):
        high, low, volume = meta.get('regularMarketDayHigh'), meta.get('regularMarketDayLow'), meta.get('regularMarketVolume')
        bars.append({'date': datetime.fromtimestamp(quoted), 'timestamp': int(quoted), 'open': bars[-1]['close'],
                     'high': max(high, price) if isinstance(high, (int, float)) else price,
                     'low': min(low, price) if isinstance(low, (int, float)) and low > 0 else price,
                     'close': price, 'volume': volume if isinstance(volume, (int, float)) else 0})

    # Is today's session still open? Then the last bar is a part of a day, and its volume is not a day's volume.
    now = time.time() if now is None else now
    session = ((meta.get('currentTradingPeriod') or {}).get('regular') or {})
    partial = bool(bars and isinstance(session.get('start'), (int, float)) and isinstance(session.get('end'), (int, float))
                   and session['start'] <= now < session['end'] and day(bars[-1]['timestamp']) == day(now))
    facts = {'currency': meta.get('currency') or '', 'name': meta.get('longName') or meta.get('shortName') or '',
             'instrument': meta.get('instrumentType') or '', 'partial_day': partial, 'offset': offset}
    return bars, facts

def fetch_stock_data(symbol):
    """Fetch a year of daily prices from Yahoo Finance"""
    try:
        print(f"⚡ Yahoo Finance: Basic price data for {symbol}")
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=365)).timestamp())

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {'period1': start_time, 'period2': end_time, 'interval': '1d'}
        full_url = f"{url}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(full_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        # Track Yahoo Finance call
        track_data_source('yahoo', 'call', success=True)

        if not data or 'chart' not in data or not data['chart']['result']:
            print(f"No chart data for {symbol}")
            return None

        result = data['chart']['result'][0]
        if 'error' in result and result['error']:
            print(f"Yahoo Finance error for {symbol}: {result['error']}")
            return None

        stock_data, facts = bars_from_chart(result)
        if not stock_data:
            print(f"No price data for {symbol}")
            return None
        _report_ctx.clear()
        _report_ctx.update(facts)

        # Track data points
        track_data_source('yahoo', 'data', len(stock_data))
        print(f"Successfully fetched {len(stock_data)} data points for {symbol}")
        return stock_data

    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return None

'''
src = before + NEW_FETCH + after

# ---------------------------------------------------------------------------------------------------------------
# 2. RSI the standard way, the same as the chart and the screeners
before, _old, after = cut(src, 'def calculate_rsi(closes, period=14):', 'def calculate_macd(closes, fast=12, slow=26, signal=9):')
NEW_RSI = r'''def calculate_rsi(closes, period=14):
    """RSI the standard way (Wilder's smoothing): the figure the chart and the screeners show. Until Oct 2026 this was
    a plain average of the last 14 days, so the report said 47 under a chart that said 56."""
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

'''
src = before + NEW_RSI + after

# ---------------------------------------------------------------------------------------------------------------
# 3. The score: a trend factor that grows with the distance, and the one-year change called what it is
before, score_fn, after = cut(src, 'def calculate_unified_investment_score(', '# Display wording for the internal recommendation codes.')
a = score_fn.index('    # Trend Analysis\n'); b = score_fn.index('    # MACD Signal\n')
score_fn = score_fn[:a] + r'''    # Trend: graded, not all-or-nothing (see trend_points)
    trend, trend_name, trend_words = trend_points(current, ma20, ma50)
    score += trend
    score_breakdown.append(f"{trend_name}: {trend:+d} ({trend_words})")

''' + score_fn[b:]
score_fn = swap(score_fn, '% YTD)', '% over 1 year)', 6)
score_fn = swap(score_fn, 'f"Positive YTD ({ytd_change:+.1f}%): +3"', 'f"Up Over 1 Year ({ytd_change:+.1f}%): +3"')
score_fn = swap(score_fn, 'Liquidity Crisis (', 'Low Liquidity (')
TREND = r'''TREND_FULL_AT = 2.0      # percent apart at which each half of the trend factor counts in full

def trend_points(current, ma20, ma50):
    """The trend factor of the score: up to 6 points for where the price is against its 20-day average, and up to 6 for
    where the 20-day average is against the 50-day, each in full at 2% apart. Returns (points, name, words).
    Until Oct 2026 this was +12 or -12 on the sign alone, so a share 0.03% under its 20-day average, up 45% in a year,
    read "Strong Downtrend: -12", and a move of a few cents swung the score by 24 points."""
    if not ma20 or not ma50:
        return 0, 'Flat Trend', 'not enough history for the averages'
    price_gap = (current / ma20 - 1) * 100
    average_gap = (ma20 / ma50 - 1) * 100
    part = lambda gap: max(-1.0, min(1.0, gap / TREND_FULL_AT))
    short, longer = 6 * part(price_gap), 6 * part(average_gap)
    points = int(round(short + longer))
    # Little either way is "flat"; two clear halves that point opposite ways are "mixed" (a bounce inside a decline)
    middle = 'Mixed Trend' if abs(short) >= 3 and abs(longer) >= 3 and short * longer < 0 else 'Flat Trend'
    name = ('Strong Uptrend' if points >= 9 else 'Uptrend' if points >= 3 else 'Strong Downtrend' if points <= -9
            else 'Downtrend' if points <= -3 else middle)
    side = lambda gap: f"{abs(gap):.1f}% {'above' if gap >= 0 else 'below'}"
    return points, name, f"price {side(price_gap)} its 20-day average; 20-day average {side(average_gap)} the 50-day"

'''
src = before + TREND + score_fn + after

# ---------------------------------------------------------------------------------------------------------------
# 4. Company figures from a second source when the first has none (it has none for shares outside the US)
before, _mid, after = cut(src, 'def calculate_fundamental_score_enhanced(fundamentals):', 'def calculate_technical_score_enhanced(')
FIGURES = r'''FIGURE_KEYS = ('pe_ratio', 'revenue_growth', 'profit_margin', 'debt_to_equity', 'current_ratio', 'return_on_equity', 'price_to_book')
_yahoo_session = {'opener': None, 'crumb': None, 'at': 0}

def fetch_yahoo_figures(symbol):
    """Company figures from Yahoo's summary of a share, in the units the score expects (percent; debt as a ratio).
    {} when they cannot be had: the report then says so and scores on price and volume alone."""
    import http.cookiejar
    agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'

    def get(url):
        req = urllib.request.Request(url, headers={'User-Agent': agent, 'Accept': '*/*'})
        with _yahoo_session['opener'].open(req, timeout=4) as response:
            return response.read()

    try:
        if not _yahoo_session['crumb'] or time.time() - _yahoo_session['at'] > 1800:
            _yahoo_session['opener'] = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            try:
                get('https://fc.yahoo.com')          # answers "not found" and still hands out the cookie that is needed
            except Exception:
                pass
            crumb = get('https://query2.finance.yahoo.com/v1/test/getcrumb').decode('utf-8', 'ignore').strip()
            if not crumb or '<' in crumb or len(crumb) > 40:
                raise ValueError('no crumb')
            _yahoo_session.update(crumb=crumb, at=time.time())
        url = (f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{urllib.parse.quote(symbol)}"
               f"?modules=financialData,defaultKeyStatistics,summaryDetail&crumb={urllib.parse.quote(_yahoo_session['crumb'])}")
        result = json.loads(get(url))['quoteSummary']['result'][0]
        track_data_source('yahoo', 'call', success=True)
    except Exception as e:
        print(f"Yahoo company figures not available for {symbol}: {str(e)[:80]}")
        _yahoo_session['crumb'] = None
        return {}

    def raw(module, key):
        value = (result.get(module) or {}).get(key)
        value = value.get('raw') if isinstance(value, dict) else value
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    pct = lambda value: value * 100 if value is not None else None
    debt = raw('financialData', 'debtToEquity')
    figures = {
        'pe_ratio': raw('summaryDetail', 'trailingPE'),
        'revenue_growth': pct(raw('financialData', 'revenueGrowth')),
        'profit_margin': pct(raw('financialData', 'profitMargins')),
        'debt_to_equity': debt / 100 if debt is not None else None,
        'current_ratio': raw('financialData', 'currentRatio'),
        'return_on_equity': pct(raw('financialData', 'returnOnEquity')),
        'price_to_book': raw('defaultKeyStatistics', 'priceToBook'),
        'beta': raw('summaryDetail', 'beta'),
    }
    # A share priced in pence against a book value in pounds gives a price-to-book a hundred times too big: leave it out
    if (_report_ctx.get('currency') or '') in MINOR_UNITS:
        figures['price_to_book'] = None
    return {k: v for k, v in figures.items() if v is not None}

def fill_missing_figures(symbol, fundamentals):
    """Fill the company figures the first source did not have, for shares only (a fund has no profit margin), and note
    where the figures came from ('figures_source'; None when there are none at all)"""
    had = [k for k in FIGURE_KEYS if fundamentals.get(k) is not None]
    added = []
    if len(had) < len(FIGURE_KEYS) and (_report_ctx.get('instrument') or 'EQUITY') == 'EQUITY':
        extra = fetch_yahoo_figures(symbol)
        added = [k for k in FIGURE_KEYS + ('beta',) if fundamentals.get(k) is None and extra.get(k) is not None]
        for k in added:
            fundamentals[k] = extra[k]
    added = [k for k in added if k in FIGURE_KEYS]
    fundamentals['figures_source'] = ('Finnhub and Yahoo Finance' if had and added else 'Yahoo Finance' if added
                                      else 'Finnhub' if had else None)
    return fundamentals

def company_figure_lines(fundamentals):
    """One line per company figure with the reading the score gives it: the same thresholds as
    calculate_unified_investment_score, so the two can never disagree (they did: "Weak" above, "Adequate" below)"""
    f = fundamentals or {}
    lines = []

    def add(value, label, text, bands):
        for test, mark, words in bands:
            if test(value):
                lines.append(f"{mark} {label}: {text} ({words})")
                return

    always = lambda value: True
    v = f.get('pe_ratio')
    if v:
        add(v, 'P/E Ratio', f"{v:.1f}", [(lambda x: x < 15, '✅', 'Low valuation'), (lambda x: x > 30, '❌', 'High valuation'), (always, '⚪', 'Mid-range')])
    v = f.get('revenue_growth')
    if v is not None:
        add(v, 'Revenue Growth', f"{v:.1f}%", [(lambda x: x > 15, '✅', 'Strong'), (lambda x: x < -10, '❌', 'Declining'), (always, '⚪', 'Moderate')])
    v = f.get('profit_margin')
    if v is not None:
        add(v, 'Profit Margin', f"{v:.1f}%", [(lambda x: x > 20, '✅', 'Excellent'), (lambda x: x > 10, '✅', 'Good'), (lambda x: x < 0, '❌', 'Unprofitable'),
                                               (lambda x: x < 5, '❌', 'Weak'), (always, '⚪', 'Adequate')])
    v = f.get('debt_to_equity')
    if v is not None:
        add(v, 'Debt/Equity', f"{v:.2f}", [(lambda x: x < 0.3, '✅', 'Low debt'), (lambda x: x > 2.0, '❌', 'High debt'), (lambda x: x > 1.5, '❌', 'Elevated debt'),
                                            (always, '⚪', 'Moderate')])
    v = f.get('current_ratio')
    if v is not None:
        add(v, 'Current Ratio', f"{v:.2f}", [(lambda x: x > 2.0, '✅', 'Strong liquidity'), (lambda x: x < 1.0, '❌', 'Low liquidity'), (lambda x: x < 1.5, '❌', 'Weak liquidity'),
                                              (always, '⚪', 'Adequate')])
    v = f.get('return_on_equity')
    if v is not None:
        add(v, 'ROE', f"{v:.1f}%", [(lambda x: x > 20, '✅', 'Excellent returns'), (lambda x: x > 15, '✅', 'Strong returns'), (lambda x: x < 0, '❌', 'Negative return'),
                                     (lambda x: x < 5, '❌', 'Weak returns'), (always, '⚪', 'Moderate returns')])
    v = f.get('price_to_book')
    if v is not None:
        add(v, 'Price/Book', f"{v:.2f}", [(lambda x: x < 1.0, '✅', 'Low valuation'), (lambda x: x > 5.0, '❌', 'High valuation'), (always, '⚪', 'Mid-range')])
    return lines

'''
src = before + FIGURES + _mid + after

# dividends in the share's own currency
src, n = re.subn(r'f"\$\{(\w+):\.3f\}"', r'money(\1, 3)', src); assert n == 2, n      # the third is a log line

# ---------------------------------------------------------------------------------------------------------------
# 5. The report's text
before, writer, after = cut(src, 'def generate_streamlined_analysis(', '# What Yahoo said about the symbol of the report being written')

writer = swap(writer, '    company_name = get_company_name(symbol)\n', "    company_name = get_company_name(symbol) or _report_ctx.get('name')\n")
writer = swap(writer, '''    analysis.append(f"💰 Current Price: ${current:.2f} ({pct_change:+.2f}% today)")\n''',
              '''    analysis.append(f"💰 Current Price: ${current:.2f} ({pct_change:+.2f}% today)")\n    if currency_note(current):\n        analysis.append(currency_note(current))\n''')
writer = swap(writer, 'analysis.append(f"📰 BREAKING NEWS (Last 24 Hours)")', 'analysis.append(f"📰 LATEST NEWS")')
writer = swap(writer, 'analysis.append(f"• YTD Performance: {ytd_change:+.1f}%")', 'analysis.append(f"• 1-Year Change: {ytd_change:+.1f}%")')
writer = swap(writer, '''    analysis.append(f"• Trend: {'Bullish' if current > ma20 > ma50 else 'Bearish' if current < ma20 < ma50 else 'Mixed'}")''',
              '''    trend, trend_name, trend_words = trend_points(current, ma20, ma50)\n    analysis.append(f"• Trend: {trend_name} ({trend_words})")''')

# one explanation of the score, built from the points that really make it up
a = writer.index('    # Add detailed scoring methodology\n'); b = writer.index('''    analysis.append(f"\\n📊 SCORE INTERPRETATION:")''')
writer = writer[:a] + r'''    # How the points above add up (one explanation: it used to be followed by a second list that did not match)
    points = [int(m.group(1)) for line in score_breakdown for m in [re.search(r': ([+-]\d+)', line)] if m]
    gained = sum(p for p in points if p > 0)
    lost = -sum(p for p in points if p < 0)
    raw_score = 50 + gained - lost
    analysis.append(f"\n🧮 HOW THE SCORE IS BUILT:")
    analysis.append(f"• It starts at 50 (neutral) and the points listed above are added or taken away")
    analysis.append(f"• 50 + {gained} - {lost} = {raw_score}" + (f", held to the 0-100 range: {unified_score}" if raw_score != unified_score else ""))
    if not company_figure_lines(fundamentals):
        analysis.append(f"• No company figures were available for this share, so this score is from price and volume only")
    if _report_ctx.get('partial_day'):
        analysis.append(f"• Today's session is still open: the price is the latest, and today's part-day volume is left out")

''' + writer[b:]

# filler
a = writer.index('    # Chart reference (charts shown by web UI)\n'); b = writer.index('    # Key Technical Indicators\n')
writer = writer[:a] + writer[b:]
writer = swap(writer, '"Oversold (Buy signal)" if rsi < 30 else "Overbought (Sell signal)" if rsi > 70', '"Oversold range" if rsi < 30 else "Overbought range" if rsi > 70')

# volume: the 20-day average the score uses (the line said "20-day Average" and printed the year's)
a = writer.index('    # Volume Analysis\n'); b = writer.index('''    analysis.append(f"💰 FUNDAMENTAL ANALYSIS")''')
writer = writer[:a] + r'''    # Volume Analysis: against the 20-day average, as the score does
    analysis.append(f"\n📊 VOLUME ANALYSIS:")
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
    volume_signal = "High interest" if volume_ratio > 1.5 else "Low interest" if volume_ratio < 0.5 else "Normal interest"
    session_words = "Last full session" if _report_ctx.get('partial_day') else "Latest session"
    analysis.append(f"• {session_words}: {current_volume:,.0f} ({volume_ratio:.1f}x the 20-day average)")
    analysis.append(f"• Volume Signal: {volume_signal}")
    analysis.append(f"• 20-day Average: {avg_volume:,.0f}")

    analysis.append(f"\n{'='*60}")
''' + writer[b:]

# company figures: one list, the score's own thresholds; and plain words when there are none
a = writer.index('    # Financial Health Check\n'); b = writer.index('    # Dividend Information\n')
writer = writer[:a] + r'''    # Company figures, read with the score's own thresholds
    analysis.append(f"\n🏥 FINANCIAL HEALTH CHECK:")
    figure_lines = company_figure_lines(fundamentals)
    if figure_lines:
        for item in figure_lines:
            analysis.append(f"• {item}")
        if fundamentals.get('figures_source'):
            analysis.append(f"  Company figures from {fundamentals['figures_source']}")
    else:
        analysis.append(f"• Company figures (P/E, growth, margins, debt) were not available for this share")
        analysis.append(f"• The score above is therefore built from price and volume only")

''' + writer[b:]

writer = swap(writer, 'Poor YTD performance ({ytd_change:+.1f}%) - Underperforming market', 'Weak 1-year change ({ytd_change:+.1f}%)')
writer = swap(writer, 'Strong YTD performance ({ytd_change:+.1f}%) - May be overextended', 'Strong 1-year change ({ytd_change:+.1f}%) - A large rise can be followed by a pullback')
writer = swap(writer, '''    analysis.append(f"• Fundamental metrics: P/E, Revenue Growth, Profit Margins, Dividends")''',
              '''    analysis.append(f"• Company figures: P/E, Revenue Growth, Profit Margins, Debt" if company_figure_lines(fundamentals) else f"• Company figures: not available for this share")\n    analysis.append(f"• Dividends: yield, latest payment and frequency, where paid")''')
assert 'YTD' not in writer, [l for l in writer.split('\n') if 'YTD' in l][:3]
src = before + writer + after

# every price in the share's own currency
src, n = re.subn(r'\$\{([^{}]+?):\.2f\}', r'{money(\1)}', src); assert n == 22, n

# ---------------------------------------------------------------------------------------------------------------
# 6. Putting a report together
before, analyse, after = cut(src, 'def analyze_stock_comprehensive_enhanced(', 'def generate_streamlined_analysis(')
analyse = swap(analyse, '        fundamentals = fetch_enhanced_fundamentals(symbol)\n',
               '        fundamentals = fetch_enhanced_fundamentals(symbol)\n        fill_missing_figures(symbol, fundamentals)\n')
analyse = swap(analyse, '''        avg_volume = sum(volumes) / len(volumes) if volumes else 0
        current_volume = volumes[-1] if volumes else 0
''', '''        # Volume against the 20-day average, as the score does. While today's session is still open its volume is a
        # part of a day: it is left out (it used to read "Low Volume: -3" every morning)
        score_volumes = volumes[:-1] if _report_ctx.get('partial_day') and len(volumes) > 21 else volumes
        recent_volumes = score_volumes[-20:]
        avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
        current_volume = score_volumes[-1] if score_volumes else 0
''')
analyse, n = re.subn(r'(calculate_unified_investment_score\(\s*closes, highs, lows, )volumes,', r'\1score_volumes,', analyse); assert n == 1, n
analyse, n = re.subn(r'(generate_streamlined_analysis\(\s*symbol, current, change, pct_change, closes, highs, lows, )volumes,', r'\1score_volumes,', analyse); assert n == 1, n
src = before + analyse + after

# ---------------------------------------------------------------------------------------------------------------
# 7. The chart is drawn from the very bars the report is scored on
src = swap(src, 'def generate_stock_charts_via_lambda(symbol, stock_data):', 'def generate_stock_charts_via_lambda(symbol, stock_data, levels=None):')
a = src.index('        # Prepare data for chart generator - simplified payload\n'); b = src.index('        print(f"📊 Invoking chart generator for {symbol}")')
src = src[:a] + r'''        # The chart function is sent the very bars this report is scored on, with its support and resistance, so that
        # the picture and the text cannot differ (it used to fetch its own and work out its own RSI: 56 above, 47 below)
        chart_payload = {
            'symbol': symbol,
            'return_type': 'url'  # Request URLs for background analysis
        }
        if stock_data and len(stock_data) >= 50 and all('timestamp' in bar for bar in stock_data):
            chart_payload['series'] = {'t': [bar['timestamp'] for bar in stock_data],
                                       'h': [round(bar['high'], 4) for bar in stock_data],
                                       'l': [round(bar['low'], 4) for bar in stock_data],
                                       'c': [round(bar['close'], 4) for bar in stock_data],
                                       'v': [bar['volume'] for bar in stock_data]}
            chart_payload['currency'] = _report_ctx.get('currency') or ''
            chart_payload.update(levels or {})
        
''' + src[b:]
src = swap(src, '        price_chart_url, volume_chart_url = generate_stock_charts_via_lambda(symbol, stock_data)\n        print(f"📊 Generating charts for',
           "        price_chart_url, volume_chart_url = generate_stock_charts_via_lambda(symbol, stock_data, {'support': support, 'resistance': resistance})\n        print(f\"📊 Generating charts for")

compile(src, 'lambda_function2.py', 'exec')
open(sys.argv[2], 'w').write(src)
print('written:', len(src.split('\n')), 'lines')
