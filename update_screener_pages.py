#!/usr/bin/env python3
"""Daily public screener pages (24 Oct 2026; the traffic plan's first build, item #9 the owner said yes to on the Admin page).

One indexable page a screener, at the top of the site (website/screener-<slug>.html), plus a hub (website/screeners-today.html):
the day's top 10 by the trend score with why each ranks there, how the whole list stands, the lowest 5 and the full ranking,
each share linked to its stock page when it has one. Meant to answer searches like "ASX 200 top momentum stocks today".

Where the figures come from: the screener coordinator on AWS (the same function the dashboard's "Run in Background" uses),
called without an account, so nothing is saved to anyone's history. No call to Yahoo from this Mac.
A screener that fails, or returns fewer than half its list, keeps yesterday's page. Refuses to write anything when fewer than
half the screeners answer.

Run by the daily deploy (deploy-to-s3.sh, the UPDATE_STOCK_NEWS block). By hand:
    python3 update_screener_pages.py               all of them
    python3 update_screener_pages.py 3-8 5-dax40   only these (the hub is still rewritten)
    python3 update_screener_pages.py --dry-run     fetch and build, write nothing
    PAGES_OUT=<folder> python3 update_screener_pages.py   write into a staged copy instead of website/

Wording rule (site-overview.md section 8b): describe, never advise. No "buy", "sell", "picks", "target".
"""
import csv, html, json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WEBSITE = '/Users/dave/VSCODE/website'
OUT = os.environ.get('PAGES_OUT') or WEBSITE
STATE = os.path.join(HERE, 'screener_pages_state.json')      # yesterday's top 10s (gitignored, like every *.json here)
COORD = 'https://ls6j5jqwl5iitwjt5va3jd6mbm0zhgyr.lambda-url.us-east-1.on.aws/'
SITE = 'https://stockiq.tech/'

# key: (slug, name, region, about the index)
SCREENERS = {
    '3-8': ('dow-jones-30', 'Dow Jones 30', 'US', 'the 30 large US companies of the Dow Jones Industrial Average'),
    '3-7': ('nasdaq-100', 'NASDAQ 100', 'US', 'the 100 largest non-financial companies listed on the Nasdaq'),
    '3-3': ('sp-500', 'S&P 500', 'US', 'the 500 large US companies of the S&P 500'),
    '5-tsx60': ('tsx-60', 'TSX 60', 'Americas', 'the 60 largest companies on the Toronto Stock Exchange'),
    '5-bovespa': ('bovespa', 'Bovespa (Ibovespa)', 'Americas', "the main index of Brazil's São Paulo exchange (B3)"),
    '5-ipc': ('mexico-ipc', 'Mexico IPC', 'Americas', "the main index of the Mexican Stock Exchange"),
    '5-ftse100': ('ftse-100', 'FTSE 100', 'Europe', 'the 100 largest companies on the London Stock Exchange'),
    '5-dax40': ('dax-40', 'DAX 40', 'Europe', "Germany's 40 largest listed companies"),
    '5-cac40': ('cac-40', 'CAC 40', 'Europe', "France's 40 largest listed companies"),
    '5-sx5e': ('euro-stoxx-50', 'Euro Stoxx 50', 'Europe', '50 of the largest companies of the euro area'),
    '5-aex': ('aex', 'AEX', 'Europe', 'the 30 largest companies on Euronext Amsterdam'),
    '5-smi': ('smi', 'SMI', 'Europe', "Switzerland's 20 largest listed companies"),
    '5-ftsemib': ('ftse-mib', 'FTSE MIB', 'Europe', "Italy's 40 largest listed companies"),
    '5-ibex35': ('ibex-35', 'IBEX 35', 'Europe', "Spain's 35 largest listed companies"),
    '5-omx30': ('omx-stockholm-30', 'OMX Stockholm 30', 'Europe', 'the 30 most traded shares in Stockholm'),
    '4-200': ('asx-200', 'ASX 200', 'Asia-Pacific', "Australia's 200 largest listed companies"),
    '5-nikkei225': ('nikkei-225', 'Nikkei 225', 'Asia-Pacific', '225 large companies on the Tokyo Stock Exchange'),
    '5-hangseng': ('hang-seng', 'Hang Seng', 'Asia-Pacific', 'the largest companies on the Hong Kong exchange'),
    '5-csi300': ('csi-300', 'CSI 300', 'Asia-Pacific', 'the 300 largest shares of the Shanghai and Shenzhen exchanges'),
    '5-kospi200': ('kospi-200', 'KOSPI 200', 'Asia-Pacific', "200 large companies of South Korea's main market"),
    '5-tw50': ('taiwan-50', 'Taiwan 50', 'Asia-Pacific', 'the 50 largest companies on the Taiwan Stock Exchange'),
    '5-sensex': ('sensex', 'BSE Sensex', 'Asia-Pacific', "30 large Indian companies (the BSE Sensex, priced on the NSE)"),
    '5-sti': ('sti', 'Straits Times Index (STI)', 'Asia-Pacific', "Singapore's 30 largest listed companies"),
    '5-nzx50': ('nzx-50', 'NZX 50', 'Asia-Pacific', "New Zealand's 50 largest listed companies"),
}
REGIONS = ('US', 'Americas', 'Europe', 'Asia-Pacific')

LABELS = {'STRONG_BUY': 'Strongly positive', 'BUY': 'Positive', 'MODERATE_BUY': 'Slightly positive', 'HOLD': 'Mixed',
          'MODERATE_SELL': 'Slightly negative', 'SELL': 'Negative', 'STRONG_SELL': 'Strongly negative'}
SIGNS = {'USD': '$', 'AUD': 'A$', 'CAD': 'C$', 'EUR': '€', 'JPY': '¥', 'HKD': 'HK$', 'SGD': 'S$', 'NZD': 'NZ$', 'INR': '₹',
         'KRW': '₩', 'GBP': '£'}


def esc(s):
    return html.escape(str(s), quote=True)


def money(price, cur):
    try:
        p = float(price)
    except (TypeError, ValueError):
        return '–'
    if cur == 'GBp':
        return f'{p:,.2f}p'
    places = 0 if cur in ('JPY', 'KRW') else 2
    sign = SIGNS.get(cur)
    return f'{sign}{p:,.{places}f}' if sign else f'{cur or ""} {p:,.{places}f}'.strip()


def pct(v, places=1):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return '–'
    return f'{v:+.{places}f}%'


NAMES_CACHE = os.path.join(HERE, 'screener_names.json')       # names asked of the price function once (gitignored)
PROXY = 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/'


def load_names():
    """Company names: stocks.txt, then the analysis page's own name tables (screeners.js, the Nikkei table), then the names
    asked of the price function before."""
    names = {}
    for src in ('screeners.js', 'analysis-functions.js'):
        try:
            text = open(os.path.join(WEBSITE, src), encoding='utf-8').read()
        except OSError:
            continue
        for sym, nm in re.findall(r"""['"]([A-Z0-9][A-Z0-9.&-]{0,14})['"]\s*:\s*['"]([^'"\n]{2,60})['"]""", text):
            if '.' in sym or sym.isalpha():
                names.setdefault(sym.upper(), nm)
    with open(os.path.join(WEBSITE, 'stocks.txt'), newline='') as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0].strip():
                names[row[0].strip().upper()] = row[1].strip()
    try:
        for k, v in json.load(open(NAMES_CACHE)).items():
            names.setdefault(k, v)
    except (OSError, ValueError):
        pass
    return names


def fill_names(names, symbols, dry):
    """Ask the price function (on AWS) for the names still missing, once each; remembered in screener_names.json."""
    missing = sorted({s.upper() for s in symbols} - set(names))
    if not missing:
        return

    def one(sym):
        try:
            with urllib.request.urlopen(PROXY + '?symbol=' + urllib.parse.quote(sym), timeout=20) as r:
                meta = json.loads(r.read())['chart']['result'][0]['meta']
            return sym, (meta.get('longName') or meta.get('shortName') or '').strip()
        except Exception:
            return sym, ''
    with ThreadPoolExecutor(max_workers=8) as pool:
        found = {s: n for s, n in pool.map(one, missing) if n}
    names.update(found)
    print(f'   names: {len(found)} of {len(missing)} missing names found')
    if found and not dry:
        try:
            cache = json.load(open(NAMES_CACHE))
        except (OSError, ValueError):
            cache = {}
        cache.update(found)
        with open(NAMES_CACHE, 'w') as f:
            json.dump(cache, f, sort_keys=True)


def fetch(key):
    option, sub = key.split('-', 1)
    body = json.dumps({'option': option, 'subOption': sub}).encode()
    for attempt in range(2):
        try:
            req = urllib.request.Request(COORD, data=body, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.loads(r.read())
            if d.get('success') and d.get('results'):
                return d
        except Exception as e:
            err = f'{type(e).__name__}: {e}'
            time.sleep(5)
    return None


def reasons(stock):
    out = []
    for line in stock.get('score_breakdown') or []:
        line = str(line).strip()
        if not line or line.upper().startswith('TREND SCORE') or 'PRE-SCALE' in line.upper():
            continue
        out.append(line)
    return out


def stock_link(sym, names, pages):
    name = names.get(sym.upper(), '')
    if sym.upper() in pages:
        return f'<a href="stocks/{esc(sym)}.html"><strong>{esc(sym)}</strong></a>', name
    # no stock page on the site: the share's full analysis instead (24 Oct 2026, the owner: some shares were not clickable). nofollow, so
    # that a search engine's crawler does not set off an analysis
    q = urllib.parse.quote(sym)
    return f'<a href="analysis.html?symbol={q}&amp;option=1&amp;subOption=custom&amp;autorun=true" rel="nofollow" title="Run the full analysis of {esc(sym)}"><strong>{esc(sym)}</strong></a>', name


HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{desc}">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{url}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{desc}">
    <meta property="og:url" content="{url}">
    <meta property="og:type" content="website">
    <link rel="icon" type="image/png" href="stockiq-logo.png">
    <style>
        html, body {{ background: #0f0f0f !important; transition: none !important; }}
        [data-theme="light"] html, [data-theme="light"] body {{ background: #ffffff !important; }}
        .top-nav {{ top: 0 !important; }}
        body {{ padding-top: 64px !important; }}
        .mobile-menu {{ top: 64px !important; height: calc(100vh - 64px) !important; }}
        .sp-wrap {{ max-width: 960px; margin: 20px auto; padding: 30px 20px; color: var(--text-primary); }}
        .sp-wrap h1 {{ font-size: 1.9rem; margin: 0 0 10px; }}
        .sp-wrap h2 {{ font-size: 1.35rem; margin: 34px 0 12px; }}
        .sp-muted {{ color: var(--text-secondary); }}
        .sp-card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 18px 20px; margin: 16px 0; line-height: 1.6; }}
        .sp-table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; font-variant-numeric: tabular-nums; }}
        .sp-table th, .sp-table td {{ padding: 8px 6px; border-bottom: 1px solid var(--border-color); text-align: left; vertical-align: top; }}
        .sp-table th {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: .04em; color: var(--text-secondary); }}
        .sp-table td.n {{ text-align: right; white-space: nowrap; }}
        .sp-table a {{ color: #3b82f6; text-decoration: none; }}
        .sp-up {{ color: #16a34a; }} .sp-down {{ color: #dc2626; }}
        .sp-why {{ margin: 4px 0 0; padding-left: 18px; color: var(--text-secondary); font-size: 0.85rem; }}
        .sp-tag {{ display: inline-block; font-size: 0.72rem; padding: 1px 7px; border-radius: 10px; border: 1px solid var(--border-color); color: var(--text-secondary); margin-left: 6px; }}
        .sp-links a {{ display: inline-block; margin: 0 8px 8px 0; padding: 6px 10px; border: 1px solid var(--border-color); border-radius: 6px; text-decoration: none; color: #3b82f6; font-size: 0.9rem; }}
        .sp-cta {{ display: inline-block; background: #007bff; color: #fff !important; padding: 12px 26px; border-radius: 8px; text-decoration: none; font-weight: 700; margin: 6px 8px 6px 0; }}
        .sp-scroll {{ overflow-x: auto; }}
        @media (max-width: 640px) {{ .sp-hide {{ display: none; }} .sp-wrap h1 {{ font-size: 1.5rem; }} }}
    </style>
    <script>
        const savedTheme = localStorage.getItem('theme');
        const manualOverride = localStorage.getItem('manualOverride');
        const hour = new Date().getHours();
        const autoTheme = (hour >= 18 || hour < 6) ? 'dark' : 'light';
        const theme = (manualOverride === 'true' && savedTheme) ? savedTheme : autoTheme;
        document.documentElement.setAttribute('data-theme', theme);
    </script>
    <link rel="stylesheet" href="styles.css">
    <script src="theme.js"></script>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-WVETNMPF8V"></script>
    <script>window.dataLayer = window.dataLayer || []; function gtag(){{dataLayer.push(arguments);}} gtag('js', new Date()); gtag('config', 'G-WVETNMPF8V');</script>
<!-- AUTOPILOT_BELL_START: the AI autopilot's practice buys and sells in the notification bell, for signed-in visitors only --><script>(function(){{try{{var u=localStorage.getItem('userId');if(u&&u!=='anonymous'&&!window.autopilotBell){{var s=document.createElement('script');s.src='autopilot-bell.js?h='+Math.floor(Date.now()/36e5);s.async=true;document.head.appendChild(s);}}}}catch(e){{}}}})();</script><!-- AUTOPILOT_BELL_END -->
    <script type="application/ld+json">{ld}</script>
</head>
<body>
'''


def shell_parts():
    """The menu and the footer (with its scripts), taken from the screener guide so the pages look like the rest of the site."""
    guide = os.path.join(OUT, 'stock-screener-guide.html')
    with open(guide if os.path.exists(guide) else os.path.join(WEBSITE, 'stock-screener-guide.html'), encoding='utf-8') as f:
        page = f.read()
    nav = page[page.index('<nav class="top-nav">'):page.index('</nav>') + len('</nav>')]
    foot = page[page.index('<footer class="footer">'):page.index('</body>')]
    return nav, foot


def ranked(results):
    rows = [r for r in results if isinstance(r.get('score'), (int, float))]
    rows.sort(key=lambda r: (-r['score'], r.get('symbol', '')))
    return rows


def breadth(rows):
    n = len(rows)
    pos = sum(1 for r in rows if r['score'] > 0)
    near_high = sum(1 for r in rows if isinstance(r.get('distance_from_52w_high'), (int, float)) and r['distance_from_52w_high'] > -5)
    up_day = sum(1 for r in rows if isinstance(r.get('change_24h'), (int, float)) and r['change_24h'] > 0)
    yr = sorted(r['change_1yr'] for r in rows if isinstance(r.get('change_1yr'), (int, float)))
    med = yr[len(yr) // 2] if yr else None
    above200 = sum(1 for r in rows if isinstance(r.get('price_vs_ma200'), (int, float)) and r['price_vs_ma200'] > 0)
    return n, pos, near_high, up_day, med, above200


def page_for(key, data, names, pages, prev, today, made):
    slug, name, region, about = SCREENERS[key]
    rows = ranked(data['results'])
    size = data.get('universe_size') or len(rows)
    top = rows[:10]
    n, pos, near_high, up_day, med, above200 = breadth(rows)
    url = f'{SITE}screener-{slug}.html'
    top3 = ', '.join(f"{names.get(r['symbol'].upper(), r['symbol'])}" for r in top[:3])
    title = f'{name} stocks ranked today: the top 10 by trend | StockIQ'
    desc = (f'The {n} shares of the {name} ranked by trend on {today}: {top3} lead. Why each ranks there, how the whole list '
            f'stands, and the full ranking, updated every trading day. General information, not advice.')
    ld = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': title, 'url': url, 'description': desc,
          'dateModified': made, 'isPartOf': {'@type': 'WebSite', 'name': 'StockIQ', 'url': SITE},
          'mainEntity': {'@type': 'ItemList', 'name': f'{name}: top 10 by trend score, {today}', 'numberOfItems': len(top),
                         'itemListElement': [{'@type': 'ListItem', 'position': i + 1,
                                              'name': f"{names.get(r['symbol'].upper(), r['symbol'])} ({r['symbol']})",
                                              **({'url': f"{SITE}stocks/{r['symbol']}.html"} if r['symbol'].upper() in pages else {})}
                                             for i, r in enumerate(top)]}}
    before = prev.get(key) or {}
    streak = before.get('streak') or {}
    new_streak = {r['symbol']: streak.get(r['symbol'], 0) + 1 for r in top}
    had = set(before.get('top') or [])
    entered = [r['symbol'] for r in top if had and r['symbol'] not in had]
    left = [s for s in (before.get('top') or []) if s not in new_streak]

    out = [HEAD.format(title=esc(title), desc=esc(desc), url=url, ld=json.dumps(ld, ensure_ascii=False).replace('</', '<\\/'))]
    out.append('{nav}')
    out.append('<main class="sp-wrap">')
    out.append(f'<p class="sp-muted" style="margin:0 0 6px;"><a href="screeners-today.html" style="color:#3b82f6;text-decoration:none;">Screeners today</a> › {esc(region)} › {esc(name)}</p>')
    out.append(f'<h1>{esc(name)} stocks ranked today</h1>')
    out.append(f'<p class="sp-muted">The {n} shares of the {esc(name)} ({esc(about)}), ranked by StockIQ\'s trend score on '
               f'<strong>{esc(today)}</strong> with the latest available prices. Updated every trading day.</p>')

    # how the whole list stands, in words
    s = [f'<strong>{pos} of {n}</strong> shares score above zero (a rising trend by this measure)',
         f'{above200} trade above their 200-day average', f'{near_high} are within 5% of their 52-week high',
         f'{up_day} rose on the latest trading day']
    if med is not None:
        s.append(f'the typical share is {pct(med)} over the past year')
    lead = '; '.join(s) + '.'
    if entered:
        lead += ' New in the top 10 since the last update: ' + ', '.join(esc(x) for x in entered) + '.'
    if left:
        lead += ' Dropped out: ' + ', '.join(esc(x) for x in left) + '.'
    out.append(f'<div class="sp-card"><strong>How the {esc(name)} stands today.</strong> {lead}</div>')

    # the top 10 with their reasons
    out.append(f'<h2>The top 10 by trend score</h2>')
    out.append('<div class="sp-scroll"><table class="sp-table"><thead><tr><th>#</th><th>Share</th><th class="n">Price</th>'
               '<th class="n">Day</th><th class="n sp-hide">1 year</th><th class="n">Score</th><th class="sp-hide">Reading</th></tr></thead><tbody>')
    for i, r in enumerate(top, 1):
        link, nm = stock_link(r['symbol'], names, pages)
        days = new_streak[r['symbol']]
        tag = f'<span class="sp-tag">{days} days in the top 10</span>' if days >= 2 else ''
        why = ''.join(f'<li>{esc(x)}</li>' for x in reasons(r))
        day = r.get('change_24h')
        cls = 'sp-up' if isinstance(day, (int, float)) and day > 0 else 'sp-down' if isinstance(day, (int, float)) and day < 0 else ''
        out.append(f'<tr><td>{i}</td><td>{link} <span class="sp-muted">{esc(nm)}</span>{tag}'
                   f'{f"<ul class=sp-why>{why}</ul>" if why else ""}</td>'
                   f'<td class="n">{esc(money(r.get("price"), r.get("currency")))}</td><td class="n {cls}">{pct(day, 2)}</td>'
                   f'<td class="n sp-hide">{pct(r.get("change_1yr"))}</td><td class="n">{r["score"]:+.1f}</td>'
                   f'<td class="sp-hide">{esc(LABELS.get(r.get("recommendation"), "Unrated"))}</td></tr>')
    out.append('</tbody></table></div>')

    # what the score is
    out.append('<div class="sp-card"><strong>What the trend score measures.</strong> Points for how far a share stands above its '
               'lowest price of the past year, for its rise over the year (leaving out the latest month), and for its price '
               'and 50-day average being above the 200-day average; points off when its RSI is over 80 (a very fast run-up). '
               'Tested on five years of daily prices in nine markets, the top 10 changed weekly beat simply holding the whole '
               'list in 13 of 18 half-periods, with deeper falls along the way. That is past performance on past data, not a '
               'forecast. <a href="about.html" style="color:#3b82f6;">How the scores work</a>.</div>')

    # the lowest 5
    low = rows[-5:][::-1] if n > 15 else []
    if low:
        out.append(f'<h2>The lowest 5 today</h2><div class="sp-scroll"><table class="sp-table"><thead><tr><th>Share</th>'
                   '<th class="n">Price</th><th class="n">1 year</th><th class="n">Score</th></tr></thead><tbody>')
        for r in low:
            link, nm = stock_link(r['symbol'], names, pages)
            out.append(f'<tr><td>{link} <span class="sp-muted">{esc(nm)}</span></td><td class="n">{esc(money(r.get("price"), r.get("currency")))}</td>'
                       f'<td class="n">{pct(r.get("change_1yr"))}</td><td class="n">{r["score"]:+.1f}</td></tr>')
        out.append('</tbody></table></div>')

    # call to action
    option, sub = key.split('-', 1)
    out.append(f'<div class="sp-card" style="border:2px solid #007bff;text-align:center;"><p style="margin:0 0 10px;">'
               f'The full screener adds each share\'s RSI, MACD, volume, reference levels and a CSV of all {size}.</p>'
               f'<a class="sp-cta" href="analysis.html?option={esc(option)}">Run the {esc(name)} screener</a>'
               f'<a class="sp-cta" href="signup.html" style="background:#16a34a;">Free 3-day trial (15 analyses)</a></div>')

    # the full ranking
    out.append(f'<h2>The full ranking ({n} shares)</h2><details><summary style="cursor:pointer;color:#3b82f6;">Show all {n}</summary>'
               '<div class="sp-scroll"><table class="sp-table"><thead><tr><th>#</th><th>Share</th><th class="n">Score</th>'
               '<th class="sp-hide">Reading</th><th class="n">1 year</th></tr></thead><tbody>')
    for i, r in enumerate(rows, 1):
        link, nm = stock_link(r['symbol'], names, pages)
        out.append(f'<tr><td>{i}</td><td>{link} <span class="sp-muted">{esc(nm)}</span></td><td class="n">{r["score"]:+.1f}</td>'
                   f'<td class="sp-hide">{esc(LABELS.get(r.get("recommendation"), "Unrated"))}</td><td class="n">{pct(r.get("change_1yr"))}</td></tr>')
    out.append('</tbody></table></div></details>')
    if n < size:
        out.append(f'<p class="sp-muted" style="font-size:.85rem;">{size - n} of the {size} shares in the list returned no usable prices today.</p>')

    # other screeners
    others = ''.join(f'<a href="screener-{SCREENERS[k][0]}.html">{esc(SCREENERS[k][1])}</a>' for k in SCREENERS if k != key)
    out.append(f'<h2>Other markets today</h2><div class="sp-links">{others}</div>')
    out.append('<p class="sp-muted" style="font-size:.85rem;margin-top:24px;">General information only, not financial advice. '
               'Scores and readings are automated model outputs from price data that may be delayed or wrong.</p>')
    out.append('</main>')
    out.append('{foot}')
    return '\n'.join(out), {'top': [r['symbol'] for r in top], 'streak': new_streak, 'day': today}


def hub(results, names, today, made):
    url = f'{SITE}screeners-today.html'
    title = "Today's stock rankings for 24 markets: top 10 by trend | StockIQ"
    desc = ('Every trading day, the shares of 24 major indexes (S&P 500, NASDAQ 100, FTSE 100, DAX 40, ASX 200, Nikkei 225 and '
            'more) ranked by trend, with the leader of each. General information, not advice.')
    ld = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': title, 'url': url, 'description': desc, 'dateModified': made}
    out = [HEAD.format(title=esc(title), desc=esc(desc), url=url, ld=json.dumps(ld))]
    out.append('{nav}')
    out.append('<main class="sp-wrap"><h1>Stock rankings today, market by market</h1>')
    out.append(f'<p class="sp-muted">Updated <strong>{esc(today)}</strong>. Each index\'s shares ranked by StockIQ\'s trend score: '
               'what stands above its lowest price of the year, has risen over the year and holds above its long average. '
               'Open a market for its top 10, why each ranks there and the full list.</p>')
    for region in REGIONS:
        out.append(f'<h2>{esc(region)}</h2><div class="sp-scroll"><table class="sp-table"><thead><tr><th>Market</th>'
                   '<th>Leader today</th><th class="n">Scoring above zero</th></tr></thead><tbody>')
        for k, (slug, name, reg, _) in SCREENERS.items():
            if reg != region:
                continue
            info = results.get(k) or {}
            lead = info.get('lead')
            leader = f"{esc(lead)} <span class='sp-muted'>{esc(names.get(lead.upper(), ''))}</span>" if lead else '<span class="sp-muted">–</span>'
            share = f"{info['pos']} of {info['n']}" if info.get('n') else '–'
            out.append(f'<tr><td><a href="screener-{slug}.html"><strong>{esc(name)}</strong></a></td><td>{leader}</td><td class="n">{share}</td></tr>')
        out.append('</tbody></table></div>')
    out.append('<p class="sp-muted" style="font-size:.85rem;margin-top:24px;">General information only, not financial advice.</p></main>')
    out.append('{foot}')
    return '\n'.join(out)


# ---- the home page's "This week in the markets" (24 Oct 2026, the owner: the home page should show it is an active site, aware of what
# is happening today and what big things are coming). Written between <!-- MARKET_WEEK_START/END --> in index.html, from the same day's
# screener results and the week's high-impact announcements (the free ForexFactory calendar the autopilot also reads).
CALENDARS = ('https://nfs.faireconomy.media/ff_calendar_thisweek.json', 'https://nfs.faireconomy.media/ff_calendar_nextweek.json')
PLACES = {'USD': 'US', 'EUR': 'Euro area', 'GBP': 'UK', 'JPY': 'Japan', 'AUD': 'Australia', 'CAD': 'Canada', 'NZD': 'New Zealand', 'CNY': 'China', 'CHF': 'Switzerland'}
WORDS = {'Federal Funds Rate': 'Fed interest-rate decision', 'FOMC Statement': 'Fed statement', 'FOMC Press Conference': 'Fed press conference',
         'Main Refinancing Rate': 'ECB interest-rate decision', 'Official Bank Rate': 'Bank of England rate decision', 'BOJ Policy Rate': 'Bank of Japan rate decision',
         'Cash Rate': 'RBA rate decision', 'Overnight Rate': 'Bank of Canada rate decision', 'Non-Farm Employment Change': 'jobs report',
         'CPI m/m': 'inflation (month)', 'CPI y/y': 'inflation (year)', 'CPI q/q': 'inflation (quarter)', 'Trimmed Mean CPI q/q': 'core inflation (quarter)', 'Core CPI m/m': 'core inflation (month)', 'Advance GDP q/q': 'growth (GDP)'}
HOME_START, HOME_END = '<!-- MARKET_WEEK_START -->', '<!-- MARKET_WEEK_END -->'


def week_events():
    out, seen = [], set()
    for url in CALENDARS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; StockIQ)'})
            with urllib.request.urlopen(req, timeout=15) as r:
                rows = json.loads(r.read())
        except Exception:
            continue
        for e in rows if isinstance(rows, list) else []:
            if not isinstance(e, dict) or e.get('impact') != 'High':
                continue
            try:
                t = datetime.fromisoformat(str(e.get('date'))).astimezone(timezone.utc)
            except ValueError:
                continue
            key = (t.isoformat(), e.get('country'), e.get('title'))
            if key not in seen:
                seen.add(key)
                out.append({'t': t, 'cur': str(e.get('country') or '')[:3], 'title': str(e.get('title') or '')[:60],
                            'forecast': str(e.get('forecast') or '')[:12], 'previous': str(e.get('previous') or '')[:12]})
    return sorted(out, key=lambda e: e['t'])


def home_section(summary, events, now, today, names=None, overall=None):
    names = names or {}
    def ev_line(e):
        name = f"{PLACES.get(e['cur'], e['cur'])}: {WORDS.get(e['title'], e['title'])}"
        was = 'was ' if e['t'] < now else ''
        figs = f" <span class=\"sp-muted\">forecast {was}{esc(e['forecast'])}, previous {esc(e['previous'])}</span>" if e['forecast'] and e['previous'] else ''
        when = e['t'].strftime('%a %d %b, %H:%M UTC')
        return f"<li><time datetime=\"{e['t'].strftime('%Y-%m-%dT%H:%M:%SZ')}\">{esc(when)}</time> · <strong>{esc(name)}</strong>{figs}</li>"
    ahead = [e for e in events if now <= e['t'] <= now + timedelta(days=8)][:6]
    past = [e for e in events if now - timedelta(days=4) <= e['t'] < now][-4:]
    if ahead:
        cal = f"<h3>Coming up</h3><ul class=\"mw-list\">{''.join(ev_line(e) for e in ahead)}</ul>"
    elif past:
        cal = (f"<h3>Out this week</h3><ul class=\"mw-list\">{''.join(ev_line(e) for e in past)}</ul>"
               "<p class=\"sp-muted\" style=\"font-size:.85rem;\">Next week's calendar is published at the weekend.</p>")
    else:
        cal = '<h3>Coming up</h3><p class="sp-muted">No high-impact announcement in the calendar for the next few days.</p>'
    rows = [(k, v) for k, v in summary.items() if isinstance(v, dict) and v.get('n') and k in SCREENERS]
    total_pos, total_n = sum(v['pos'] for _, v in rows), sum(v['n'] for _, v in rows)
    rows.sort(key=lambda kv: -kv[1]['pos'] / kv[1]['n'])
    def mk(kv):
        k, v = kv
        return (f"<li><a href=\"screener-{SCREENERS[k][0]}.html\"><strong>{esc(SCREENERS[k][1])}</strong></a> "
                f"{round(100 * v['pos'] / v['n'])}% rising <span class=\"sp-muted\">· leader {esc(short(names.get(v['lead'].upper(), v['lead'])))}</span></li>")
    # each share counted once (24 Oct 2026, the owner queried the total: the Dow 30 sits inside the S&P 500, the Euro Stoxx 50 inside the
    # national lists, so adding the markets up counted about 160 shares twice)
    if overall and overall[1]:
        total_pos, total_n = overall[0], overall[1]
    breadth = (f"<p style=\"margin:0 0 8px;\"><strong>{round(100 * total_pos / total_n) if total_n else 0}%</strong> of the {total_n:,} shares in "
               f"{len(rows)} main indexes are in a rising trend by StockIQ's trend score.</p>") if rows else ''
    strong = f"<h4>Strongest trend</h4><ul class=\"mw-list\">{''.join(mk(kv) for kv in rows[:3])}</ul>" if rows else ''
    weak = f"<h4>Weakest trend</h4><ul class=\"mw-list\">{''.join(mk(kv) for kv in rows[-3:][::-1])}</ul>" if len(rows) > 5 else ''
    return f'''{HOME_START}
<section id="market-week" style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 24px 22px; margin: 30px 0; text-align: left;">
<style>#market-week h2{{margin:0 0 4px;font-size:1.4rem;color:var(--text-primary);}}#market-week h3{{font-size:1rem;margin:14px 0 8px;color:var(--text-primary);}}#market-week h4{{font-size:.85rem;margin:10px 0 6px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;}}#market-week .mw-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px 30px;}}#market-week .mw-list{{list-style:none;padding:0;margin:0;}}#market-week .mw-list li{{padding:5px 0;border-bottom:1px solid var(--border-color);color:var(--text-primary);font-size:.92rem;line-height:1.45;}}#market-week a{{color:#3b82f6;text-decoration:none;}}#market-week .sp-muted{{color:var(--text-secondary);}}#market-week time{{color:var(--text-secondary);}}@media(max-width:700px){{#market-week .mw-grid{{grid-template-columns:1fr;}}}}</style>
<div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:10px;"><h2>This week in the markets</h2><a href="screeners-today.html" style="display:inline-block;background:#007bff;color:#fff;padding:9px 16px;border-radius:8px;font-weight:700;font-size:.92rem;">See every market&rsquo;s top 10 today &rarr;</a></div>
<p class="sp-muted" style="margin:0 0 6px;font-size:.88rem;">Updated {esc(today)}: the scheduled announcements that can move whole markets, and where the trend stands in 24 markets today. General information, not advice.</p>
<div class="mw-grid"><div>{cal}</div><div><h3>Today across the markets</h3>{breadth}{strong}{weak}</div></div>
<script>(function(){{try{{document.querySelectorAll('#market-week time[datetime]').forEach(function(t){{var d=new Date(t.getAttribute('datetime'));if(!isNaN(d))t.textContent=d.toLocaleString(undefined,{{weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}});}});}}catch(e){{}}}})();</script>
</section>
{HOME_END}'''


def short(name):
    """A company name without its legal form, 28 characters at most."""
    n = re.sub(r'[,.]?\s+(Inc|Incorporated|Corporation|Corp|Ltd|Limited|plc|PLC|SE|S\.A|SA|AG|N\.V|NV|AB|Co|Company|Group Limited|Holdings Limited)\.?$', '', str(name)).strip()
    return n[:28]


def write_home(summary, now, today, dry, names=None, overall=None):
    path = os.path.join(OUT, 'index.html') if os.path.exists(os.path.join(OUT, 'index.html')) else os.path.join(WEBSITE, 'index.html')
    page = open(path, encoding='utf-8').read()
    if HOME_START not in page or HOME_END not in page:
        print('⚠️  index.html has no MARKET_WEEK markers: the home page section is not written')
        return
    block = home_section(summary, week_events(), now, today, names, overall)
    new = page[:page.index(HOME_START)] + block + page[page.index(HOME_END) + len(HOME_END):]
    if dry:
        print(f'   (dry run) index.html: This week in the markets, {len(block) // 1024} KB')
    elif new != page:
        with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(new)
        print('✅ Home page: This week in the markets written')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in sys.argv or os.environ.get('DRY_RUN') == 'true'
    keys = [k for k in SCREENERS if not args or k in args]
    names = load_names()
    pages = {f[:-5].upper() for f in os.listdir(os.path.join(WEBSITE, 'stocks')) if f.endswith('.html')}
    prev = {}
    if os.path.exists(STATE):
        try:
            prev = json.load(open(STATE))
        except ValueError:
            prev = {}
    now = datetime.now(timezone.utc)
    today, made = f'{now.day} {now.strftime("%B %Y")}', now.strftime('%Y-%m-%d')
    nav, foot = shell_parts()

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as pool:
        got = dict(zip(keys, pool.map(fetch, keys)))
    ok = {k: d for k, d in got.items() if d and len(ranked(d['results'])) >= 0.5 * (d.get('universe_size') or 1)}
    print(f'📊 Screener pages: {len(ok)} of {len(keys)} screeners answered in {time.time() - t0:.0f} s')
    if len(ok) < 0.5 * len(keys):
        print('⚠️  Fewer than half answered: no page written (yesterday\'s stay)')
        return 1
    fill_names(names, [r.get('symbol', '') for d in ok.values() for r in d['results']], dry)
    summary = {k: v for k, v in (prev.get('_hub') or {}).items()}
    state = dict(prev)
    for k, d in ok.items():
        text, st = page_for(k, d, names, pages, prev, today, made)
        text = text.replace('{nav}', nav).replace('{foot}', foot)
        rows = ranked(d['results'])
        summary[k] = {'lead': rows[0]['symbol'], 'pos': sum(1 for r in rows if r['score'] > 0), 'n': len(rows)}
        state[k] = st
        path = os.path.join(OUT, f'screener-{SCREENERS[k][0]}.html')
        if dry:
            print(f'   (dry run) {os.path.basename(path)}: {len(text) // 1024} KB, leader {rows[0]["symbol"]}')
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
    for k in keys:
        if k not in ok:
            print(f'⚠️  {SCREENERS[k][1]}: no answer, yesterday\'s page kept')
    state['_hub'] = summary
    text = hub(summary, names, today, made).replace('{nav}', nav).replace('{foot}', foot)
    if not dry:
        with open(os.path.join(OUT, 'screeners-today.html'), 'w', encoding='utf-8') as f:
            f.write(text)
        with open(STATE, 'w') as f:
            json.dump(state, f)
        print(f'✅ Screener pages written: {len(ok)} and the hub')
    shares = {}
    for d in ok.values():
        for r in ranked(d['results']):
            shares[r['symbol']] = r['score'] > 0
    overall = (sum(shares.values()), len(shares)) if len(ok) == len(keys) == len(SCREENERS) else None
    write_home(summary, now, today, dry, names, overall)
    return 0


if __name__ == '__main__':
    sys.exit(main())
