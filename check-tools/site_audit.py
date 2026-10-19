#!/usr/bin/env python3
"""The site checked every night, with no AI and no cost (18 Oct 2026). The owner, after finding one weak spot after another
himself: "why can't you actively do this every 24+ hours since a last check". Reads the site's own files (the pages, their
scripts, the sitemap, a sample of stock pages) and tests concrete things a session had missed:

  stock-links     links to the stock pages from the home page and the guides (none, until 18 Oct 2026)
  loading-text    "Loading..." in the HTML of an indexed page: what a search engine reads before any script runs
  broken-links    a link or a script on a page whose file is not on the site
  duplicate-code  the same function defined in several pages or scripts (the market panel was three copies)
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
    'stale-until': {'BEZ.L': '2026-10-24', 'SDR.L': '2026-10-24', 'PSKY': '2026-10-24'},   # taken over / no usable prices; the 21-day rule de-indexes them
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
    pages = sorted(os.path.basename(p) for p in glob.glob(os.path.join(WEB, '*.html')))
    scripts = sorted(os.path.basename(p) for p in glob.glob(os.path.join(WEB, '*.js')))
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

    # broken-links
    for p in pages:
        body = src[p]
        for ref in set(re.findall(r'(?:href|src)="([^"#?]+)(?:[?#][^"]*)?"', body)):
            if re.match(r'^(https?:|mailto:|tel:|javascript:|data:|//)', ref) or '${' in ref or ref.startswith('{') or not ref.strip():
                continue
            target = os.path.normpath(os.path.join(WEB, ref.lstrip('/')))
            if not os.path.exists(target):
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
        if p in last and last[p] and kb > last[p] * 1.15 and kb - last[p] > 10:
            find('page-weight', 'problem', f'{kb:.0f} KB, up from {last[p]:.0f} KB at the last check', p)

    # stale-counts
    m = re.search(r'(\d+)\s*(?:</[^>]+>\s*)*(?:<[^>]+>\s*)*screeners', src.get('index.html', ''), re.I)
    keys = len(re.findall(r"^\s*'\d+-[\w]+'\s*:\s*\{", src.get('screeners.js', ''), re.M))
    if m and keys:
        want = keys + 1                                    # the share screeners, and the crypto screener
        if int(m.group(1)) != want:
            find('stale-counts', 'problem', f'the home page says {m.group(1)} screeners; screeners.js has {keys} share screeners and there is crypto: {want}', 'index.html')

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
    hist = (hist + [{'at': at, 'keys': now_keys, 'weights': weights}])[-60:]
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
