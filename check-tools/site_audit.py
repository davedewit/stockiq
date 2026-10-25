#!/usr/bin/env python3
"""The site checked every night, with no AI and no cost (18 Oct 2026). The owner, after finding one weak spot after another
himself: "why can't you actively do this every 24+ hours since a last check". Reads the site's own files (the pages, their
scripts, the sitemap, a sample of stock pages) and tests concrete things a session had missed:

  stock-links     links to the stock pages from the home page and the guides (none, until 18 Oct 2026)
  loading-text    "Loading..." in the HTML of an indexed page: what a search engine reads before any script runs
  broken-links    a link or a script on a page whose file is not on the site
  duplicate-code  the same function defined in several pages or scripts (the market panel was three copies)
  run-links       a daily screener page whose run button opens the wrong section or runs no screener
  late-layout     a page whose own padding or width is set by a style inside the body (it moves after the first draw)
  cost            AWS: a service's spend jumping, the month over the owner's $1, Cost Explorer charged, a table or Lambda calls jumping (cost_check.py, free)
  plan-claims     a plan card on the dashboard ticks a feature that is not on the list of what exists (unbuilt ones go under "Coming soon")
  news-stale      the newest article in news.html or news.js more than 2 days old (the news steps stopped adding articles)
  one-count       a page or script other than auth.js that asks the anonymous usage counter itself (two counts disagree)
  theme-early     a page that loads theme.js late (defer/async), so the menu flashes before the page is marked signed in
  copies          a block of 8+ lines (code, style or markup) word for word in 3+ hand-edited files; a problem when a change adds one
  shared-parts    a page whose menu or footer differs from the one definition in shared_parts.py
  made-up-visuals Math.random() used to draw something (the side panel's charts were random lines), a fixed line written into a
                  chart, or figures written into the code to show when the data fails
  stale-stock-pages indexed stock pages whose "Data as of" is more than 4 days behind the newest
  unused-scripts  a script no page loads; a script a page loads that finds none of its elements there (sidebar.js)
  page-weight     a page heavier than 250 KB, or 15% heavier than at the last check
  stale-counts    the home page's count of screeners against screeners.js
  seo-basics      an indexed page without a title, a description or a canonical link; two pages with one title
  sitemap         the sitemap's form, and every page in it present and indexable
  structured-data JSON-LD that does not parse
  console-noise   console.log lines left in the pages' scripts

    python3 check-tools/site_audit.py            print the findings, keep them in check-tools/audit/ (latest.json, history)
    python3 check-tools/site_audit.py --admin    also put them on the owner's Admin page (admin.py audit)
    AUDIT_WEB=<staging folder>/web python3 check-tools/site_audit.py   read the staged files first (before a deploy); saves nothing

The daily deploy runs it with --admin; session_start.py prints the latest. A finding is a lead for a session, not a verdict:
fix it, or teach this script that it is fine (KNOWN below, with the reason). Each new kind of fault found by hand gets a check.
"""
import glob, html, json, os, random, re, subprocess, sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, '..', '..', 'website')
OUT = os.path.join(HERE, 'audit')
GUIDES = ('stock-analysis-guide.html', 'stock-screener-guide.html', 'technical-analysis-guide.html', 'investment-research-tools.html')
# Accepted on purpose, with the reason, so that they are not reported every night
KNOWN = {
    # stock pages known to be stale for a reason that ends by itself, with the day it should be over: left out of the stale count
    # until then, counted again after it (19 Oct 2026: they turned the Admin page's check-in card amber for nothing)
    'stale-until': {'BEZ.L': '2026-10-27', 'SDR.L': '2026-10-27', 'PSKY': '2026-10-27'},   # taken over / no usable prices; the 21-day rule de-indexes them (24 Oct's run crashed before it: Monday 26 Oct's does it)
    'duplicate-code': {'toggleMobileMenu', 'closeMobileMenu', 'showDropdown', 'hideDropdown', 'toggleDropdown', 'toggleTheme', 'logout',
                       'fillMobileSidebar', 'emptyMobileSidebar', 'toggleMobileSidebar', 'closeMobileSidebar',   # each page's own menu and sidebar hooks (mobile-sidebar.js calls them)
                       'gtag',                                                    # Google Analytics' own snippet, on every page by design
                       'goToNotifications',                                       # one line in each page's header (go to the dashboard); not worth a shared script
                       'load', 'start', 'init', 'read', 'write', 'esc', 'render', 'go', 'tick', 'one', 'run', 'show', 'hide', 'style', 'refresh'},   # local names inside separate scripts, not shared code
}
findings = []


def find(check, level, text, where=''):
    findings.append({'check': check, 'level': level, 'text': text, 'where': where})


STAGE = os.environ.get('AUDIT_WEB', '')


def read(p):
    if STAGE and os.path.abspath(p).startswith(os.path.abspath(WEB) + os.sep):
        staged = os.path.join(STAGE, os.path.relpath(os.path.abspath(p), os.path.abspath(WEB)))
        if os.path.exists(staged):
            p = staged
    try:
        return open(p, encoding='utf-8', errors='replace').read()
    except Exception:
        return ''


def strip_scripts(s):
    return re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)


def inline_scripts(s):
    return re.findall(r'<script(?![^>]*\bsrc=)(?![^>]*application/ld\+json)[^>]*>(.*?)</script>', s, flags=re.S)


def main():
    # with AUDIT_WEB, a page or script that is new in the staging folder counts too (24 Oct 2026: a new page read as a broken link)
    roots = [WEB] + ([STAGE] if STAGE else [])
    pages = sorted({os.path.basename(p) for r in roots for p in glob.glob(os.path.join(r, '*.html'))})
    scripts = sorted({os.path.basename(p) for r in roots for p in glob.glob(os.path.join(r, '*.js'))})
    src = {p: read(os.path.join(WEB, p)) for p in pages + scripts}
    indexed = [p for p in pages if 'noindex' not in (re.search(r'<meta name="robots" content="([^"]*)"', src[p]) or [None, ''])[1] and p not in ('clear-cache.html',)]

    # stock-links
    home = len(re.findall(r'href="stocks/[^"]+\.html"', src.get('index.html', '')))
    if home < 20:
        find('stock-links', 'problem', f'the home page links to {home} stock pages (it should hold the Stock Pages section: update_home_stock_links.py)', 'index.html')
    bare = [g for g in GUIDES if g in src and not re.search(r'href="stocks/', src[g])]
    if bare:
        find('stock-links', 'idea', f'{len(bare)} of the 4 guides link to no stock page (a few relevant ones would help search)', ', '.join(bare))

    # stale-stock-pages: the indexed stock pages say "Updated daily"; the snapshot step keeps yesterday's when Yahoo refuses this
    # Mac, and on 18 Oct 2026 the owner's daily review found 532 of them still at 9 Oct (this check had not looked)
    from datetime import datetime as _dt
    dates = {}
    for sym in (l.strip() for l in open(os.path.join(HERE, '..', 'indexable_stocks.txt')) if l.strip()):
        m = re.search(r'Data as of (\d{1,2} \w{3} \d{4})', read(os.path.join(WEB, 'stocks', sym + '.html')))
        if m:
            try:
                dates[sym] = _dt.strptime(m.group(1), '%d %b %Y').date()
            except ValueError:
                pass
    if dates:
        today = _dt.utcnow().strftime('%Y-%m-%d')
        newest = max(dates.values()); old = sorted((d, s_) for s_, d in dates.items() if (newest - d).days > 4 and not today <= KNOWN['stale-until'].get(s_, ''))
        if old:
            find('stale-stock-pages', 'problem', f'{len(old)} of {len(dates)} indexed stock pages show data more than 4 days older than the newest '
                 f'({newest:%d %b}); the oldest {old[0][0]:%d %b} (e.g. {", ".join(s_ for _, s_ in old[:4])})',
                 'update_stock_analysis.py (Yahoo refuses this Mac: "No price data" in ~/stockiq-daily.log)')

    # made-up fallback figures: numbers written into the page to show when the data cannot be had (the home page's index cards
    # showed January 2024 figures as today's until 18 Oct 2026)
    for f_ in pages + scripts:
        for m in re.finditer(r'fallback\w*\s*=\s*\{[^;]{0,400}?\b(price|value)\s*:\s*\d{3,}', src[f_], re.I):
            find('made-up-visuals', 'problem', f'figures written into the code to show when the data fails (line {src[f_][:m.start()].count(chr(10)) + 1})', f_)

    # loading-text
    for p in indexed:
        n = len(re.findall(r'Loading\.\.\.|Loading…', strip_scripts(src[p])))
        if n:
            find('loading-text', 'idea', f'{n} "Loading..." placeholders a search engine reads before the scripts run', p)

    # claims: wording about StockIQ that the rewrite of 13 Oct 2026 took out, found again by hand on 23 Oct 2026 in the footer of
    # 19 pages ("Professional Investment Research Platform", "Powered by AI") and on the blog ("in real-time")
    claims = re.compile(r'(?i:Professional Investment Research Platform|Powered by AI|Professional stock analysis|institutional[- ]grade|'
                        r'professional[- ]grade|\bin real-time\b)|Real-time Data\b')   # the last as the old footer wrote it ("no real-time data" is a denial)
    for p in pages:
        if p == 'news.html':
            continue                                                       # headlines of other people's articles
        hits = sorted(set(m.group(0) for m in claims.finditer(strip_scripts(src[p]))))
        if hits:
            find('claims', 'problem', f'says {", ".join(repr(h) for h in hits)} about the site (claims the site does not make any more)', p)
    gen = read(os.path.join(HERE, '..', 'generate-stock-pages.py'))
    if claims.search(gen):
        find('claims', 'problem', 'the stock pages\' template still has wording the site does not use any more', 'generate-stock-pages.py')
    stale = sum(1 for p in glob.glob(os.path.join(WEB, 'stocks', '*.html'))[:200] if claims.search(read(p)))
    if stale and not claims.search(gen):
        find('claims', 'idea', f'{stale} of 200 stock pages looked at still carry the old footer ("Real-time Data"): the template is right, '
             'they change at the next regeneration (generate-stock-pages.py, then update_stock_analysis.py)', 'stocks/*.html')

    # stale-dates: a page that says "Last updated: <date>" more than 30 days before its last real change in git (23 Oct 2026: the
    # four guides said February and April after being reworded on 13 Oct and given stock examples on 18 Oct)
    import subprocess
    for p in pages:
        m = re.search(r'Last updated: ([A-Za-z]+ \d{1,2}, \d{4})', src[p])
        if not m:
            continue
        try:
            said = _dt.strptime(m.group(1), '%B %d, %Y').date()
            last = subprocess.run(['git', '-C', WEB, 'log', '-1', '--format=%ad', '--date=short', '--', p], capture_output=True, text=True, timeout=20).stdout.strip()
            if last and (_dt.strptime(last, '%Y-%m-%d').date() - said).days > 30:
                find('stale-dates', 'idea', f'says "Last updated: {m.group(1)}" but was last changed on {last}', p)
        except Exception:
            pass

    # broken-links
    for p in pages:
        body = src[p]
        for ref in set(re.findall(r'(?:href|src)="([^"#?]+)(?:[?#][^"]*)?"', body)):
            if re.match(r'^(https?:|mailto:|tel:|javascript:|data:|//)', ref) or '${' in ref or ref.startswith('{') or not ref.strip():
                continue
            target = os.path.normpath(os.path.join(WEB, ref.lstrip('/')))
            if not os.path.exists(target) and not (STAGE and os.path.exists(os.path.join(STAGE, ref.lstrip('/')))):
                find('broken-links', 'problem', f'links to "{ref}", which is not on the site', p)
    for p in random.Random(len(pages)).sample(sorted(glob.glob(os.path.join(WEB, 'stocks', '*.html'))), 5):
        for ref in set(re.findall(r'(?:href|src)="(\.\./[^"#?]+)', read(p))):
            if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), ref))):
                find('broken-links', 'problem', f'a stock page links to "{ref}", which is not on the site', 'stocks/' + os.path.basename(p))

    # duplicate-code
    defs = {}
    for f in pages + scripts:
        code = '\n'.join(inline_scripts(src[f])) if f.endswith('.html') else src[f]
        for name in set(re.findall(r'(?:^|\n)\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(', code)) | set(re.findall(r'window\.([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?function', code)):
            defs.setdefault(name, set()).add(f)
    dup = {n: fs for n, fs in defs.items() if len(fs) >= 3 and n not in KNOWN['duplicate-code']}
    if dup:
        worst = sorted(dup.items(), key=lambda x: -len(x[1]))[:12]
        find('duplicate-code', 'idea', f'{len(dup)} functions are defined in 3 or more pages or scripts: ' + '; '.join(f'{n} ({len(fs)})' for n, fs in worst),
             'one shared script each (as market-panel.js did for the side panel)')

    # made-up-visuals
    for f in pages + scripts:
        lines = src[f].split('\n')
        for i, l in enumerate(lines):
            if 'Math.random' in l:
                near = ' '.join(lines[max(0, i - 4):i + 5]).lower()
                if re.search(r'polyline|sparkline|points\.push|<svg|chart|y = base|candle', near) and not re.search(r'delay|setTimeout|jitter|anonymous|id\b|sample', l.lower()):
                    find('made-up-visuals', 'problem', f'Math.random() draws something (line {i + 1}: "{l.strip()[:80]}")', f)
            # a fixed line written into a chart (the home page's index cards drew one "up" or one "down" shape, whatever the market did)
            if re.search(r"setAttribute\(\s*['\"]points['\"]\s*,\s*['\"][\d ,.]{12,}['\"]", l):
                find('made-up-visuals', 'problem', f'a fixed line is drawn into a chart (line {i + 1}: "{l.strip()[:80]}")', f)
        for m in re.finditer(r'id="[\w-]*chart"[^>]*>\s*<polyline points="([\d ,.]{12,})"', src[f]):
            find('made-up-visuals', 'problem', f'a chart starts with a made-up line ("{m.group(1)[:30]}…")', f)

    # unused-scripts
    every = '\n'.join(src.values()) + '\n'.join(read(p) for p in glob.glob(os.path.join(WEB, 'stocks', 'AAPL.html'))) + '\n'.join(read(p) for p in glob.glob(os.path.join(WEB, 'js', '*.js')))
    for s in scripts:
        if s in ('news.js', 'stock-pages.js', 'screeners.js'):
            pass
        others = re.sub(re.escape(src[s]), '', every, count=1)
        if not re.search(r'["\'/ ]' + re.escape(s) + r'(\?|["\'])', others):
            find('unused-scripts', 'idea', f'{s} is loaded by no page or script', s)
    for p in pages + ['stocks/AAPL.html']:
        body = read(os.path.join(WEB, p))
        for s in set(re.findall(r'<script[^>]+src="(?:\.\./)?([a-z][\w.-]*\.js)', body)):
            ids = set(re.findall(r"getElementById\('([\w-]+)'\)", src.get(s, '')))
            if len(ids) >= 5 and not any(f'id="{i}"' in body for i in ids) and not any(f"'{i}'" in src.get(s, '').split('createElement')[0][:0] for i in ids):
                created = set(re.findall(r"\.id\s*=\s*'([\w-]+)'", src.get(s, ''))) | set(re.findall(r'id="([\w-]+)"', src.get(s, '')))   # elements the script builds itself
                if not (ids & created):
                    find('unused-scripts', 'idea', f'{p} loads {s}, which finds none of its {len(ids)} elements there', p)

    # page-weight
    hist_p = os.path.join(OUT, 'history.json')
    hist = json.load(open(hist_p)) if os.path.exists(hist_p) else []
    last = hist[-1]['weights'] if hist else {}
    weights = {}
    for p in indexed:
        kb = len(src[p].encode()) / 1024
        weights[p] = round(kb, 1)
        if kb > 250:
            find('page-weight', 'idea', f'{kb:.0f} KB of HTML (over 250 KB: slower on a phone, and search engines read less of it)', p)
        # the daily screener pages change every day by design: only the 250 KB limit above applies to them (24 Oct 2026)
        if p in last and last[p] and kb > last[p] * 1.15 and kb - last[p] > 10 and not p.startswith('screener'):
            find('page-weight', 'problem', f'{kb:.0f} KB, up from {last[p]:.0f} KB at the last check', p)

    # stale-counts
    m = re.search(r'(\d+)\s*(?:</[^>]+>\s*)*(?:<[^>]+>\s*)*screeners', src.get('index.html', ''), re.I)
    keys = len(re.findall(r"^\s*'\d+-[\w]+'\s*:\s*\{", src.get('screeners.js', ''), re.M))
    if m and keys:
        want = keys + 1                                    # the share screeners, and the crypto screener
        if int(m.group(1)) != want:
            find('stale-counts', 'problem', f'the home page says {m.group(1)} screeners; screeners.js has {keys} share screeners and there is crypto: {want}', 'index.html')
        # the AI chat's own count, which it tells visitors (24 Oct 2026: the counts are kept the same everywhere)
        chat = read(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lambda-sync', 'stockiq-ai-chat', 'lambda_function.py'))
        cm = re.search(r'\((\d+) in all, under Screeners', chat)
        if cm and int(cm.group(1)) != want:
            find('stale-counts', 'problem', f'the AI chat tells visitors there are {cm.group(1)} screeners; there are {want}', 'stockiq-ai-chat')
    # the number of daily screener pages, as the hub, the home page and the AI chat give it
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location('sp', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'update_screener_pages.py'))
        sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp); pages_n = len(sp.SCREENERS)
        chat = read(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lambda-sync', 'stockiq-ai-chat', 'lambda_function.py'))
        for where, text in (('screeners-today.html', src.get('screeners-today.html', '')), ('index.html', src.get('index.html', '')), ('stockiq-ai-chat', chat)):
            for n in set(re.findall(r'(?:for|of|across|each of) (\d+) (?:major indexes|markets)', text)):
                if int(n) != pages_n:
                    find('stale-counts', 'problem', f'says {n} markets have a daily page; update_screener_pages.py makes {pages_n}', where)
    except Exception as e:
        find('stale-counts', 'idea', f'the daily pages\' count could not be compared ({type(e).__name__})', 'update_screener_pages.py')

    # seo-basics
    titles = {}
    for p in indexed:
        head = src[p][:src[p].find('</head>')]
        t = re.search(r'<title>(.*?)</title>', head, re.S)
        if not t:
            find('seo-basics', 'problem', 'no <title>', p)
        else:
            titles.setdefault(html.unescape(t.group(1).strip()), []).append(p)
        if not re.search(r'<meta name="description" content="[^"]{30,}"', head):
            find('seo-basics', 'problem', 'no meta description (or a very short one)', p)
        if 'rel="canonical"' not in head:
            find('seo-basics', 'problem', 'no canonical link', p)
    for t, ps in titles.items():
        if len(ps) > 1:
            find('seo-basics', 'problem', f'{len(ps)} pages share the title "{t[:60]}"', ', '.join(ps))

    # sitemap
    sm = read(os.path.join(WEB, 'sitemap.xml'))
    if 'ns0:' in sm:
        find('sitemap', 'idea', 'the sitemap is written with an ns0: prefix (update_sitemap.py writes plain tags since 18 Oct 2026)', 'sitemap.xml')
    urls = re.findall(r'<(?:\w+:)?loc>https://stockiq\.tech/([^<]*)</(?:\w+:)?loc>', sm)
    missing = [u for u in urls if u and not os.path.exists(os.path.join(WEB, u))]
    if missing:
        find('sitemap', 'problem', f'{len(missing)} sitemap addresses have no file, e.g. {missing[:3]}', 'sitemap.xml')
    noidx = [u for u in urls if u.startswith('stocks/') and os.path.exists(os.path.join(WEB, u)) and 'noindex' in read(os.path.join(WEB, u))[:6000]]
    if noidx:
        find('sitemap', 'problem', f'{len(noidx)} stock pages in the sitemap are marked noindex, e.g. {noidx[:3]}', 'sitemap.xml')

    # structured-data
    for p in pages:
        for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', src[p], flags=re.S):
            try:
                json.loads(blk)
            except Exception as e:
                find('structured-data', 'problem', f'JSON-LD that does not parse ({type(e).__name__})', p)

    # console-noise
    logs = {f: src[f].count('console.log') for f in pages + scripts}
    total = sum(logs.values())
    if total > 80:
        find('console-noise', 'idea', f'{total} console.log lines in the pages and scripts (the most: ' + ', '.join(f'{f} {n}' for f, n in sorted(logs.items(), key=lambda x: -x[1])[:4]) + ')', '')

    # run-links: every daily screener page's "Run the … screener" button opens the analysis page on that market's section and runs
    # that very screener (24 Oct 2026: they opened the Asia-Pacific section for every market outside the US, and ran nothing)
    try:
        sj = read(os.path.join(WEB, 'screeners.js')); ah = read(os.path.join(WEB, 'analysis.html'))
        known = set(re.findall(r"^\s*'(\d+-[\w]+)':\s*\{", sj, re.M))
        for f in pages:
            if not f.startswith('screener-'):
                continue
            m = re.search(r'href="(analysis\.html\?option=[^"]*)">Run the ', src[f])
            if not m:
                find('run-links', 'problem', 'has no "Run the … screener" button that opens the analysis page', f); continue
            q = dict(x.split('=', 1) for x in html.unescape(m.group(1)).split('?', 1)[1].split('&'))
            run, sub, sec = q.get('run', q.get('option')), q.get('subOption'), q.get('option')
            part = re.search(rf'id="option-{sec}".*?(?=id="option-\d|$)', ah, re.S)
            if q.get('autorun') != 'true' or f'{run}-{sub}' not in known or not part or f"runAnalysis({run}, '{sub}'" not in part.group(0):
                find('run-links', 'problem', f'its run button ({m.group(1)}) does not open the right section and run its screener', f)
    except Exception as e:
        find('run-links', 'idea', f'the run buttons could not be checked: {e}')

    # late-layout: the page's own width or padding set by a style inside the body, so a first visit is drawn without it and then
    # moves (24 Oct 2026, the owner: the daily pages "load without the right side bar ... then adjust")
    for f in pages:
        b = src[f].find('<body')
        if b >= 0 and any(re.search(r'(^|[\s,}])body\s*\{[^}]*(padding|margin|width)', m.group(0)) for m in re.finditer(r'<style[^>]*>.*?</style>', src[f][b:], re.S)):
            find('late-layout', 'problem', "sets the page's own padding or width in a style inside the body: put it in the head, or the page moves after it is first drawn", f)

    # cost: what AWS costs, every day, from CloudWatch's free figures (25 Oct 2026; cost_check.py). Not on a staged copy (pre-deploy)
    if not STAGE:
        try:
            sys.path.insert(0, HERE); import cost_check
            for level, text in cost_check.run()[0]:
                find('cost', level, text, 'AWS')
        except Exception as e:
            find('cost', 'idea', f'the AWS cost check could not run ({type(e).__name__}: {str(e)[:80]})', 'AWS')

    # plan-claims: what a paying visitor is promised must exist (25 Oct 2026: the cards listed alerts, white-label and portfolio tools
    # that were never built; the owner chose to keep them as "Coming soon"). A new ticked item must be added here once it exists.
    EXISTS = [r'\d+ analyses/screeners per day', r'Unlimited analyses/screeners per day', r'Every report, all \d+ screeners and the trading signals',
              r'Company figures in every stock report', r'Export to CSV', r'AI autopilot \(Beta\)', r'Email support', r'Priority email support',
              r'Top-priority email support', r'Everything in (Starter|Pro)', r'Cancel anytime']
    dash = src.get('dashboard.html', '')
    if '💎 Upgrade Your Plan' in dash:
        cards = dash[dash.index('💎 Upgrade Your Plan'):]
        cards = cards[:cards.index('"Coming soon" features')] if '"Coming soon" features' in cards else cards[:8000]
        for item in re.findall(r'>✓ ([^<]+)</li>', cards):
            if not any(re.match(x, item.strip()) for x in EXISTS):
                find('plan-claims', 'problem', f'a plan card ticks "{item.strip()[:80]}", which is not on the list of what exists: mark it "Coming soon", or add it to EXISTS in site_audit.py once built', 'dashboard.html')

    # news-stale: the daily run adds news before this check runs, so a working run always has articles from the last day (25 Oct 2026,
    # the owner: "so long as i'm aware if ... news articles aren't updating"; nothing looked at it until then)
    from datetime import datetime as _dtn, timezone as _tzn
    for f in ('news.html', 'news.js'):
        ts = re.findall(r'(20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d)', src.get(f, ''))
        if ts:
            age = (_dtn.now(_tzn.utc) - _dtn.fromisoformat(max(ts)).replace(tzinfo=_tzn.utc)).total_seconds() / 86400
            if age > 2:
                find('news-stale', 'problem', f'the newest article is {age:.1f} days old ({max(ts)[:16]} UTC): the news steps are not adding articles (update_news.py, update_stock_news.py in ~/stockiq-daily.log)', f)

    # one-count: the visitor's free-use count is worked out in one place, auth.js (getAnonymousUsageCount: the server's count by
    # IP and the browser's own note). 25 Oct 2026, the owner on his phone: the dashboard asked the server itself and read 1/1
    # after the sign-up page had said 0/1
    for f in pages + scripts:
        if f != 'auth.js' and 'dcegrxwikpuwup7qas24dubloq0ohurf' in src[f]:
            find('one-count', 'problem', "asks the anonymous usage counter itself: use authManager.getAnonymousUsageCount() (auth.js), or the counts disagree", f)

    # theme-early: theme.js marks the page (signed in, paid, light or dark) before it is drawn; loaded with defer or async it runs
    # after, and the menu shows "Sign up free" for a moment to a signed-in visitor (24 Oct 2026, the owner on the home page)
    for f in pages:
        if re.search(r'<script[^>]*theme\.js[^>]*\b(defer|async)\b', src[f]):
            find('theme-early', 'problem', 'loads theme.js with defer or async: the page is drawn before it is marked signed in, paid or dark (the menu flashes)', f)

    # copies: one block of code or markup in 3 or more hand-edited files, so that one change has to be made in each (24 Oct 2026, the
    # owner: "make sure we don't create silly code that requires us having to update the same thing on multiple pages"). Pages written
    # from one template (the stock pages, the daily screener pages) and the generated scripts are left out. A window of 8 lines that
    # count (not a bare brace or tag) found word for word in 3+ files is one copied line; the total is the number to bring down, and a
    # run that finds clearly more than the last says which block a change copied.
    generated = re.compile(r'^(screener-.+|screeners-today)\.html$|^(news|stock-pages)\.js$')
    W, seen_in = 8, {}
    for f in pages + scripts:
        if generated.match(f):
            continue
        text = re.sub(r'<!-- SHARED_(\w+)_START.*?<!-- SHARED_\1_END -->', '', src[f], flags=re.S)   # written from one definition (shared_parts.py)
        rows = [l.strip() for l in text.split('\n')]
        rows = [l for l in rows if len(l) > 3 and not re.fullmatch(r'[{}()\[\];,]*|</?[a-z0-9]+>', l)]
        for i in range(len(rows) - W + 1):
            seen_in.setdefault(hash('\n'.join(rows[i:i + W])), (set(), rows[i]))[0].add(f)
    groups = {}
    for files, first in seen_in.values():
        if len(files) >= 3:
            g = groups.setdefault(frozenset(files), [0, first]); g[0] += 1
    copied = sum(g[0] for g in groups.values())
    copy_keys = sorted(f'{first[:60]}|{len(fs)}' for fs, (n, first) in groups.items())
    if copied:
        top = sorted(groups.items(), key=lambda x: -x[1][0] * len(x[0]))[:5]
        said = '; '.join(f'{n} lines in {len(fs)} files ({", ".join(sorted(fs)[:3])}{"…" if len(fs) > 3 else ""}), from "{first[:50]}"' for fs, (n, first) in top)
        prev = next((h['copies'] for h in reversed(hist) if h.get('copies') is not None), None)
        if prev is not None and copied > prev + W:
            known = set(next((h['copy_keys'] for h in reversed(hist) if h.get('copy_keys') is not None), []))
            fresh = [(fs, g) for fs, g in groups.items() if f'{g[1][:60]}|{len(fs)}' not in known] or top
            said = '; '.join(f'{n} lines in {len(fs)} files ({", ".join(sorted(fs)[:4])}{"…" if len(fs) > 4 else ""}), from "{first[:50]}"' for fs, (n, first) in sorted(fresh, key=lambda x: -x[1][0])[:3])
            find('copies', 'problem', f'a change copied code into several files: {copied} copied lines, {prev} at the last check. New: {said}',
                 'put it in one shared file (as site-header.js and market-panel.js) instead of in each page')
        else:
            find('copies', 'idea', f'{copied} lines are copied word for word into 3 or more hand-edited files' + (f' ({prev} at the last check)' if prev is not None else '') + f'. The largest: {said}',
                 'one shared file each, a part at a time, at the weekly review (lens "Built once")')

    # shared-parts: every page's menu and footer as defined once in shared_parts.py (24 Oct 2026); a page edited by hand drifts
    if not STAGE:
        r = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), 'shared_parts.py'), '--check'], capture_output=True, text=True)
        if r.returncode:
            lines = [l for l in r.stdout.splitlines() if l.startswith('differs')]
            find('shared-parts', 'problem', f'{len(lines)} page(s) have a menu or footer that differs from the one definition: ' + '; '.join(l[9:] for l in lines[:5]),
                 'change shared_parts.py, not the page, then run it: python3 shared_parts.py')

    # this run against the last
    os.makedirs(OUT, exist_ok=True)
    key = lambda f: f"{f['check']}|{f['where']}|{re.sub(r'[0-9]+', '#', f['text'])}"
    before = set(hist[-1]['keys']) if hist else set()
    now_keys = [key(f) for f in findings]
    for f, k in zip(findings, now_keys):
        f['new'] = bool(hist) and k not in before
    gone = len(before - set(now_keys))
    at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    out = {'at': at, 'pages': len(pages), 'scripts': len(scripts), 'problems': sum(f['level'] == 'problem' for f in findings),
           'ideas': sum(f['level'] == 'idea' for f in findings), 'new': sum(f['new'] for f in findings), 'gone': gone, 'findings': findings}
    if STAGE:
        print(f'(staged files read from {STAGE}: nothing saved)')
    else:
        json.dump(out, open(os.path.join(OUT, 'latest.json'), 'w'), indent=1, ensure_ascii=False)
    hist = (hist + [{'at': at, 'keys': now_keys, 'weights': weights, 'copies': copied, 'copy_keys': copy_keys}])[-60:]
    if not STAGE:
        json.dump(hist, open(hist_p, 'w'))
    print(f"site check {at}: {len(pages)} pages, {len(scripts)} scripts; {out['problems']} problems, {out['ideas']} ideas"
          + (f"; {out['new']} new since the last check, {gone} gone" if len(hist) > 1 else ''))
    for f in sorted(findings, key=lambda f: (f['level'] != 'problem', f['check'])):
        print(f"  [{f['level']}{', new' if f['new'] else ''}] {f['check']}: {f['text']}" + (f"  ({f['where']})" if f['where'] else ''))
    if '--admin' in sys.argv and not STAGE:
        subprocess.run([sys.executable, os.path.join(HERE, 'admin.py'), 'audit'], check=False)


if __name__ == '__main__':
    main()
