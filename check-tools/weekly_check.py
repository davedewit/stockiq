#!/usr/bin/env python3
"""The full check of the site, every 7 days or more (19 Oct 2026; the owner: "do a full check of everything on the site, to find
problems ... in math? in display to user? does it all make sense? ... it's like i ask for things to be added, they get added but
then it breaks something else ... consistency and confidence everything is good"). Read-only, about 15 minutes.

    python3 check-tools/weekly_check.py            everything; writes check-tools/reviews/weekly/check-<date>.txt and
                                                    check-tools/weekly_check.json, and puts the result on the Admin page
    python3 check-tools/weekly_check.py --quick    the test suites and the consistency checks, without the browser checks and
                                                    the real screener runs

Three parts:
  1. every test suite run against the LIVE code (lambda-sync/ and website/, which session_start.py proves equal to what is live);
  2. the figures agree with each other across the site: the account value on the Admin page and on the Practice portfolio tab,
     the holdings, the finished trades and the diary, the money the autopilot can reach, the bill's parts, the sitemap;
  3. real buttons: a few screeners through the page's own code, with real worker calls (nothing is saved anywhere).
It is the floor, not the whole job: a session that runs it also reads the dashboard as the owner does (clarity_check.py --keep)
and reports in plain words what was checked and what was fixed (site-overview.md, the HI routine).
"""
import os, sys, json, re, subprocess, tempfile, datetime, importlib.util, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); WEB = os.path.join(os.path.dirname(ROOT), 'website')
QUICK = '--quick' in sys.argv
EMAIL = '--email' in sys.argv               # send the owner a short summary (SES, from autopilot@stockiq.tech; free at this volume)
if '--if-due' in sys.argv:                  # the daily update calls it every day; it runs when the last full check is 7 days old or more
    try:
        w = json.load(open(os.path.join(HERE, 'weekly_check.json')))
        if not w.get('quick') and (datetime.datetime.utcnow() - datetime.datetime.strptime(w['at'], '%Y-%m-%dT%H:%M:%SZ')).days < 7:
            print('full check not due yet'); sys.exit(0)
    except FileNotFoundError:
        pass
OWNER = os.environ.get('REVIEW_ACCOUNT', 'dave@dewit.com.au')
results = []          # (part, name, ok, detail)


def run(cmd, timeout=900, cwd=None, env=None):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd or HERE, env=dict(os.environ, **(env or {})))
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 99, 'timed out'


def note(part, name, ok, detail=''):
    results.append((part, name, bool(ok), str(detail)[:300]))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ('' if ok else f"   {str(detail)[:200]}"), flush=True)


def suite(name, cmd, timeout=900, env=None):
    code, out = run(cmd, timeout, env=env)
    fails = [l for l in out.splitlines() if l.strip().startswith('FAIL')]
    passed = len([l for l in out.splitlines() if l.strip().startswith('PASS')])
    ok = ('ALL PASS' in out or re.search(r'all (\d+ )?checks passed', out) or re.search(r'\b\d+ passed, 0 failed', out)) and not fails
    note('1. Test suites on the live code', f"{name} ({passed} checks)" if passed else name, ok, '; '.join(fails[:3]) or out.strip().splitlines()[-1:] if not ok else '')


LIVE_FN = lambda f: os.path.join(ROOT, 'lambda-sync', f, 'lambda_function.py')
print('\n== 1. Test suites on the live code', flush=True)
suite('the autopilot function', ['python3', '-W', 'ignore', 'ai_trader_test.py', LIVE_FN('stockiq-ai-trader')], 1500)
suite('the autopilot panel', ['node', 'autopilot_test.js', os.path.join(WEB, 'practice-autopilot.js')])
tmp = tempfile.mkdtemp()
pp = open(os.path.join(WEB, 'practice-portfolio.js')).read().replace('https://5c7pt7qurshld4cwaqyopfxcei0cuurj.lambda-url.us-east-1.on.aws/', '__PRACTICE_API_URL__')
open(os.path.join(tmp, 'pp.js'), 'w').write(pp)          # never the real file: it holds the live storage address (it wrote to the live table once)
suite('the practice portfolio', ['node', 'practice_test.js', os.path.join(tmp, 'pp.js')])
suite('the Admin page', ['node', 'admin_panel_test.js', os.path.join(WEB, 'admin-panel.js')])
suite('the notification bell', ['node', 'autopilot_bell_test.js', os.path.join(WEB, 'autopilot-bell.js')])
suite('the AI chat', ['python3', 'ai_chat_test.py', LIVE_FN('stockiq-ai-chat')])
suite('the trading signals', ['python3', os.path.join(ROOT, 'signals', 'test_signals.py')])
suite('the home page news list', ['node', 'news_sidebar_test.js'])
code, out = run(['python3', '-W', 'ignore', 'autopilot_plan_check.py', LIVE_FN('stockiq-ai-trader'), os.path.join(WEB, 'practice-autopilot.js'), '60'], 1200)
diff = re.findall(r'differs from the function in: (\d+)', out)
note('1. Test suites on the live code', 'the panel works out the budget, the spread and the check-ins as the function does', diff and all(d == '0' for d in diff), out.strip().splitlines()[-3:])
code, out = run(['python3', 'clarity_check.py'], 600)
note('1. Test suites on the live code', 'the AI autopilot tab and the Admin page read clearly (clarity check)', 'nothing reads badly' in out, out.strip().splitlines()[-4:])
code, out = run(['python3', 'site_audit.py'], 900)
# Problems already understood, with the day they should be gone by: they pass until then, and fail again if still there after it
KNOWN_UNTIL = {'stale-stock-pages': ('2026-10-24', 'BEZ.L and SDR.L (taken over, last traded 1 Oct) and PSKY leave the index by the 21-day rule')}
m = re.search(r'(\d+) problems', out)
probs = re.findall(r'\[problem[^\]]*\] ([a-z-]+):', out)
today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
left = [x for x in probs if not (x in KNOWN_UNTIL and today <= KNOWN_UNTIL[x][0])]
known = [f"{x} (known: {KNOWN_UNTIL[x][1]}, by {KNOWN_UNTIL[x][0]})" for x in probs if x not in left]
note('1. Test suites on the live code', f"the nightly site check's tests ({m.group(0) if m else '?'}{'; ' + '; '.join(known) if known else ''})", m is not None and not left, out.strip().splitlines()[-6:])
code, out = run(['python3', 'lists_check.py'], 300)
note('1. Test suites on the live code', "the screeners' stock lists (page and coordinator alike, no duplicates)", 'FINDINGS: none' in out, out.strip().splitlines()[-4:])
suite('every index the site compares with has daily prices', ['node', 'index_check.js'], 300)
code, out = run(['python3', 'workers.py'], 600)
bad = [l for l in out.splitlines() if 'DIFFEREN' in l and '(not used)' not in l]      # old groups the site no longer calls are left alone (section 8b)
note('1. Test suites on the live code', 'every share-screener worker runs the one package', code == 0 and not bad, bad[:3])
if not QUICK:
    for name, cmd in (('the market panel and live figures', ['node', 'live_market_check.js', 'index.html', 'dashboard.html']),
                      ('the two sliding panels on a phone', ['node', 'mobile_sidebar_check.js', 'index.html', 'dashboard.html', 'analysis.html']),
                      ('the header and the room under it', ['node', 'header_room_check.js'])):
        code, out = run(cmd, 900)
        tail = out.strip().splitlines()[-1:] if out.strip() else ['no output']
        note('1. Test suites on the live code', name, ('ALL PASS' in out or re.search(r'all \d+ checks passed', out)) and 'FAIL' not in out, [l for l in out.splitlines() if 'FAIL' in l][:3] or tail)

# ---------------------------------------------------------------- 2. the figures agree with each other
print('\n== 2. The figures agree across the site', flush=True)
try:
    import boto3
    os.environ.setdefault('AWS_PROFILE', 'default'); os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1'); os.environ.setdefault('AI_TRADER_USERS', '')
    spec = importlib.util.spec_from_file_location('trader', LIVE_FN('stockiq-ai-trader')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    db = boto3.Session(profile_name='default', region_name='us-east-1').resource('dynamodb')
    rec = m.load_item(OWNER)
    item = db.Table('stockiq-paper-portfolios').get_item(Key={'userId': OWNER}).get('Item')
    pf = json.loads(item['data'])
    now = datetime.datetime.utcnow()
    goal = m.goal_standing(rec, pf, now, m.fetch_quote)
    # the Practice portfolio's own sums (the page's script, run here on the same portfolio and live prices)
    js = r"""
const pp = require(process.argv[2]); const PRICE = 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/?symbol=';
(async () => { const state = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8')); const syms = new Set(['SPY']);
  [...state.holdings, ...state.closed].forEach(h => { syms.add(h.symbol); const fx = pp.fxFor(h.currency || 'USD'); if (fx.symbol) syms.add(fx.symbol); });
  const quotes = {}; await Promise.all([...syms].map(async s => { try { const j = await (await fetch(PRICE + encodeURIComponent(s))).json(); const r = j.chart.result[0], mm = r.meta;
    quotes[s] = { price: mm.regularMarketPrice, currency: mm.currency, time: mm.regularMarketTime, series: pp.seriesOf(r, s) }; } catch (e) {} }));
  const s = pp.summarize(state, quotes), vs = pp.versusStart(state, quotes, Date.now()), d = pp.versusDays(state, quotes, Date.now());
  console.log(JSON.stringify({ account: s.accountValue, fund: vs && vs.value, days: d && d.days })); })();"""
    open(os.path.join(tmp, 'sums.js'), 'w').write(js); open(os.path.join(tmp, 'pf.json'), 'w').write(json.dumps(pf))
    shutil.copy(os.path.join(WEB, 'practice-portfolio.js'), os.path.join(tmp, 'ppreal.js'))   # read only: nothing in it is called that writes
    code, out = run(['node', os.path.join(tmp, 'sums.js'), os.path.join(tmp, 'ppreal.js'), os.path.join(tmp, 'pf.json')], 300)
    page = json.loads(out.strip().splitlines()[-1]) if code == 0 and out.strip() else {}
    gap = abs(num := (page.get('account') or 0) - goal['value'])
    note('2. The figures agree across the site', f"the account value: the Admin page's ${goal['value']:,.0f} and the Practice portfolio tab's ${page.get('account', 0):,.0f} (prices a few seconds apart)", page and gap < max(60, 0.001 * goal['value']), f"apart by ${gap:,.2f}")
    fund_fn = m.fund_since_start(pf, goal['value'], now)
    note('2. The figures agree across the site', 'the S&P 500 fund since the start: the weekly review and the graph agree', fund_fn and page.get('fund') and abs(fund_fn[0] - page['fund']) < 25, (fund_fn and round(fund_fn[0]), page.get('fund')))
    held_ai = [h for h in pf['holdings'] if h.get('by') == 'ai' and h.get('screener') != 'themes']
    opened = rec['state'].get('open') or {}
    missing = [h['label'] for h in held_ai if h['id'] not in opened]
    note('2. The figures agree across the site', f"every holding of the autopilot ({len(held_ai)}) has its remembered buy (the plan and the record need it)", not missing, missing[:5])
    stale = [k for k in opened if k not in {h['id'] for h in pf['holdings']}]
    note('2. The figures agree across the site', 'no remembered buy is left for a holding already sold', len(stale) <= 2, stale[:5])
    money = m.money_of(pf)
    note('2. The figures agree across the site', f"the budget (${rec['settings']['budgetUsd']:,.0f}) is within the practice money it can reach (${money['reach']:,.0f})", rec['settings']['budgetUsd'] <= money['reach'] + 1, money)
    hist = rec.get('history') or []
    real = m.num(rec['state'].get('realizedUsd')); summed = sum(m.num(t.get('usd')) for t in hist)
    note('2. The figures agree across the site', f"the autopilot's results so far: its running total (${real:,.2f}) and its finished trades added up (${summed:,.2f})", abs(real - summed) < 5 or len(hist) >= 300, f"apart by ${abs(real - summed):,.2f} (the themes part's sales are in the total, not the list: {len((rec['state'].get('themes') or {}).get('trades') or [])})")
    diary = db.Table('stockiq-ai-trader-journal')
    from boto3.dynamodb.conditions import Key
    rows, kw = 0, {'KeyConditionExpression': Key('userId').eq(OWNER), 'ProjectionExpression': 'kind'}
    while True:
        r = diary.query(**kw); rows += sum(1 for x in r['Items'] if x.get('kind') == 'trade')
        if 'LastEvaluatedKey' not in r: break
        kw['ExclusiveStartKey'] = r['LastEvaluatedKey']
    note('2. The figures agree across the site', f"the diary holds every finished trade ({rows} written, {len(hist)} in the record)", rows >= len(hist), (rows, len(hist)))
    admin = m.load_admin(); u = admin.get('usage') or {}
    if u.get('costStockiq') is not None and u.get('cost') is not None:
        parts = u['costStockiq'] + u.get('costExplorer', 0) + u.get('costOther', 0)
        note('2. The figures agree across the site', f"the bill on the Admin page adds up (${u['cost']:.2f} = StockIQ ${u['costStockiq'] + u.get('costExplorer', 0):.2f} + other ${u.get('costOther', 0):.2f})", abs(parts - u['cost']) < 0.05, parts)
        note('2. The figures agree across the site', f"StockIQ's running cost within the cost rule (${u['costStockiq']:.2f} this month, under $1)", u['costStockiq'] < 1, u.get('costStockiqForecast'))
    if u.get('forecast'):
        note('2. The figures agree across the site', f"Lambda calls on course for {u['forecast']:,} of the free 1,000,000", u['forecast'] < 900000, u['forecast'])
    smap = open(os.path.join(WEB, 'sitemap.xml')).read(); listed = [l.strip() for l in open(os.path.join(ROOT, 'indexable_stocks.txt')) if l.strip()]
    in_map = len(re.findall(r'/stocks/[^<]+\.html', smap))
    note('2. The figures agree across the site', f"the sitemap lists every indexed stock page ({in_map} in it, {len(listed)} indexed)", abs(in_map - len(listed)) <= 2, (in_map, len(listed)))
    ex = json.load(open(os.path.join(HERE, 'experiments.json')))['experiments']
    overdue = [x['id'] for x in ex if x.get('status') == 'running' and x.get('decide') and x['decide'] < datetime.datetime.utcnow().strftime('%Y-%m-%d')]
    note('2. The figures agree across the site', 'every improvement on trial past its decision day has been decided (the Improvements tab stays true)', not overdue, overdue)
    h = admin.get('health') or {}
    note('2. The figures agree across the site', 'the autopilot\'s last scheduled run reported no failed check-in', h and not h.get('failed'), h)
except Exception as e:
    note('2. The figures agree across the site', 'the consistency checks themselves ran', False, f"{type(e).__name__}: {e}")

# ---------------------------------------------------------------- 3. real buttons, every one (19 Oct 2026, the owner: "make sure its thorough")
if not QUICK:
    from concurrent.futures import ThreadPoolExecutor
    print('\n== 3. Analysis buttons, end to end: six screeners in turn, and the report, signals and crypto buttons (real worker calls; nothing saved)', flush=True)
    keys = sorted(set(re.findall(r"'(\d-[a-z0-9]+)':\s*\{", open(os.path.join(WEB, 'screeners.js')).read())))
    names = dict(re.findall(r"'(\d-[a-z0-9]+)':\s*\{\s*name:\s*'([^']+)'", open(os.path.join(WEB, 'screeners.js')).read()))
    # Six share screeners a run, in turn (the owner: "you probably don't need to check every screener"), so every one is pressed about
    # every five weeks: data changes (a takeover, an index review, the price source) can break a screener without any code changing.
    # ROTATE_ALL=1 presses all of them.
    if os.environ.get('ROTATE_ALL') != '1':
        week = datetime.datetime.utcnow().isocalendar()[1]; per = 6; rounds = (len(keys) + per - 1) // per
        start = (week % rounds) * per; keys = keys[start:start + per]
    buttons = [(k.split('-')[0], k.split('-', 1)[1], names.get(k, k), True) for k in keys]
    buttons += [('1', 'custom', 'the single-stock report (AAPL, KO)', False), ('2', 'custom', 'live trading signals', False), ('2', 'auto', 'auto-detect signals', False),
                ('7', 'coinspot', 'the crypto screener', True), ('72', 'single', 'single coin analysis (BTC)', False)]
    def press(b):
        opt, sub, name, top10 = b
        d = tempfile.mkdtemp(dir=tmp)
        code, out = run(['node', os.path.join(HERE, 'page_run.js'), opt, sub], 900, cwd=d)
        try: sm = json.loads([l for l in out.splitlines() if l.startswith('{')][-1])
        except Exception: sm = {}
        ok = bool(sm) and not sm.get('error') and not sm.get('flags') and (not top10 or (sm.get('trackerSymbols') or 0) >= 10)
        return name, ok, ({k: sm.get(k) for k in ('error', 'flags', 'trackerSymbols', 'secs')} if sm else out[-200:]), top10
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, ok, detail, top10 in pool.map(press, buttons):
            note('3. Every analysis button', f"{name}: runs, no error, no raw codes or 'undefined'" + (', the 🎯 tracker reads its top 10' if top10 else ''), ok, detail)
    print('\n== 4. The background run, the visitors\' limits, and your live pages (read-only)', flush=True)
    code, out = run(['python3', os.path.join(HERE, 'run_all.py'), '3-8', '5-dax40', '5-nikkei225', '4-200'], 1800, cwd=tmp, env={'AWS_DEFAULT_REGION': 'us-east-1'})
    for line in out.splitlines():
        if re.match(r'^[0-9]-[a-z0-9]+ \{', line):
            key, js = line.split(' ', 1); r = json.loads(js)
            ok = r.get('status') == 200 and not r.get('error') and not r.get('failed_workers') and r.get('saved_report') and (r.get('results') or 0) >= 0.9 * (r.get('listed') or 1)
            label = names.get(key) or names.get('5-' + key.split('-', 1)[1]) or names.get('4-' + key.split('-', 1)[1]) or key   # the coordinator's keys differ from the page's for ASX and FTSE
            note('4. Background run and visitors', f"\"Run in Background\" for {label} (the dashboard's path): every worker answers, the report is formed ({r.get('results')} of {r.get('listed')})", ok, r)
    code, out = run(['node', os.path.join(HERE, 'anon_run.js'), '3', '8'], 600, cwd=tmp)
    note('4. Background run and visitors', 'a visitor who is not signed in gets their one free analysis', 'result=true' in out, out.strip().splitlines()[-3:])
    code, out = run(['node', os.path.join(HERE, 'anon_run.js'), '3', '8'], 600, cwd=tmp, env={'USED': '1'})
    note('4. Background run and visitors', 'and after it is used, is sent to sign up before anything runs', 'result=false' in out and 'signup' in out, out.strip().splitlines()[-3:])
    code, out = run(['node', os.path.join(HERE, 'trial_run.js'), '3', '8'], 600, cwd=tmp, env={'TRIAL': '1'})
    note('4. Background run and visitors', 'a visitor on the free trial gets a result', 'result=true' in out, out.strip().splitlines()[-3:])
    code, out = run(['node', os.path.join(HERE, 'trial_run.js'), '3', '8'], 600, cwd=tmp, env={'TRIAL': '1', 'USED': '5'})
    note('4. Background run and visitors', "and with the day's 5 used, is sent to the plans before anything runs", 'result=false' in out, out.strip().splitlines()[-3:])
    code, out = run(['node', 'visitor_bar_check.js'], 1500)
    note('4. Background run and visitors', 'the usage chip and the sign-up buttons, for every kind of visitor, at four widths', ('ALL PASS' in out or re.search(r'all \d+ checks passed', out)) and 'FAIL' not in out, [l for l in out.splitlines() if 'FAIL' in l][:3] or out.strip().splitlines()[-1:])
    code, out = run(['node', 'pricing_link_check.js'], 300)
    note('4. Background run and visitors', "the home page's \"View Pricing Plans\" lands on the plans, clear of the header", code == 0 and 'FAIL' not in out, out.strip().splitlines()[-2:])
    code, out = run(['node', 'live_practice_check.js'], 300, env={'REAL_USER': OWNER})
    note('4. Background run and visitors', 'your Practice portfolio tab, opened as your account (read-only): it draws, with your holdings', '"shown": true' in out and 'Holding (' in out and 'Error' not in out, out.strip().splitlines()[-3:])
    code, out = run(['node', 'live_bell_check.js', 'index.html'], 300, env={'REAL_USER': OWNER, 'PASS_GET': '1'})
    note('4. Background run and visitors', 'the notification bell on the home page, as your account (read-only): one list, no errors', 'ONE LIST' in out and '"errors":[]' in out, out.strip().splitlines()[-2:])
    log = os.path.expanduser('~/stockiq-daily.log')
    if os.path.exists(log):
        t = open(log, errors='replace').read(); age = (datetime.datetime.now().timestamp() - os.path.getmtime(log)) / 86400
        note('4. Background run and visitors', f"the last daily update finished cleanly ({age:.0f} day{'' if round(age) == 1 else 's'} ago)", 'All done' in t and not re.search(r'could not rebase|push failed|Traceback', t) and age < 3, [l for l in t.splitlines() if re.search('could not|failed|Traceback', l)][:3] or f'{age:.1f} days old')

shutil.rmtree(tmp, ignore_errors=True)
passed, total = sum(1 for r in results if r[2]), len(results)
# Which of the 44 parts of the site (site_parts.json) the checks cover; the rest need a person (a real login, payments, judgement)
COVER = [('the autopilot function', 'ap-buying ap-selling ap-learning ap-status ap-switches'), ('the autopilot panel', 'ap-status ap-settings ap-screeners ap-switches ap-activity ap-doing'),
         ('the practice portfolio', 'pp-top pp-graph pp-holdings'), ('the Admin page', 'admin'), ('notification bell', 'bell'), ('the AI chat', 'chat'),
         ('trading signals', 'signals'), ('auto-detect signals', 'signals'), ('news list', 'news'), ('the panel works out', 'ap-settings ap-screeners'),
         ('read clearly', 'ap-activity ap-doing admin'), ("site check's tests", 'stock-pages seo guides about-faq legal home-hero home-features home-email'),
         ("stock lists", 'stock-lists'), ('market panel', 'home-widgets'), ('sliding panels', 'phone'), ('the header', 'phone'), ('account value', 'pp-top admin'),
         ('S&P 500 fund since', 'pp-graph'), ('remembered buy', 'pp-holdings'), ('running total', 'ap-doing'), ('diary', 'ap-learning'), ('bill', 'costs'),
         ('cost rule', 'costs'), ('Lambda calls', 'costs'), ('sitemap', 'seo'), ('decision day', 'admin'), ('scheduled run', 'ap-status'),
         ('single-stock report', 'report presets'), ('crypto screener', 'crypto'), ('single coin', 'crypto'), ('tracker reads', 'tracker'),
         ('Run in Background', 'reports-tab'), ('free analysis', 'usage-chip'), ('free trial', 'usage-chip'), ('usage chip', 'usage-chip phone'),
         ('Pricing Plans', 'home-pricing plans'), ('Practice portfolio tab, opened', 'pp-top pp-holdings'), ('daily update', 'daily-run')]
REGION = {'us': '3-', 'europe': 'ftse100 dax40 cac40 aex ftsemib ibex35 smi sx5e omx30', 'apac': '5-50 5-100 5-200 5-300 nikkei225 hangseng sensex kospi200 sti csi300 tw50 nzx50', 'americas': 'tsx60 bovespa ipc'}
parts = {x['id']: x['part'] for x in json.load(open(os.path.join(HERE, 'site_parts.json')))['parts']}
covered = set()
for p_, name, ok, d in results:
    for key, ids in COVER:
        if key in name: covered.update(ids.split())
    if p_.startswith('3.') and 'tracker' in name: covered.add('tracker')
covered.update(f"screeners-{r}" for r in REGION if any(n for p_, n, ok, d in results if p_.startswith('3.')))
covered &= set(parts)
uncovered = [parts[k] for k in parts if k not in covered]
at = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
lines = [f"FULL CHECK OF THE SITE, {at[:10]} ({'quick' if QUICK else 'everything'}): {passed} of {total} passed", f"It covers {len(covered)} of the {len(parts)} parts of the site. Left to a person: " + '; '.join(uncovered) + '.', '']
for part in sorted({r[0] for r in results}):
    lines.append(part)
    lines += [f"  {'PASS' if ok else 'FAIL'}  {name}" + ('' if ok else f"\n        {detail}") for p, name, ok, detail in results if p == part]
    lines.append('')
os.makedirs(os.path.join(HERE, 'reviews', 'weekly'), exist_ok=True)
open(os.path.join(HERE, 'reviews', 'weekly', f"check-{at[:10]}.txt"), 'w').write('\n'.join(lines))
json.dump({'at': at, 'quick': QUICK, 'passed': passed, 'total': total, 'covered': len(covered), 'parts': len(parts), 'uncovered': uncovered,
           'items': [{'part': p, 'name': n, 'ok': ok} for p, n, ok, d in results], 'failed': [{'part': p, 'name': n, 'detail': d} for p, n, ok, d in results if not ok]},
          open(os.path.join(HERE, 'weekly_check.json'), 'w'), indent=1)
print('\n' + lines[0])
if not QUICK:
    run(['python3', os.path.join(HERE, 'admin.py'), 'weekly'], 300)
if EMAIL:
    try:
        import boto3
        failed = [f"- {p}: {n}" for p, n, ok, d in results if not ok]
        body = (('What failed (a session fixes these first):\n' + '\n'.join(failed) + '\n\n' if failed else 'Everything passed.\n\n')
                + '\n'.join(lines) + '\nThe Admin page shows the same list under "Full check of the site".\n\nStockIQ')
        boto3.Session(profile_name='default', region_name='us-east-1').client('ses').send_email(
            Source='StockIQ <autopilot@stockiq.tech>', Destination={'ToAddresses': [OWNER]},
            Message={'Subject': {'Data': f"StockIQ full check: {'all ' + str(total) + ' passed' if passed == total else str(total - passed) + ' of ' + str(total) + ' failed'}"},
                     'Body': {'Text': {'Data': body}}})
        print('emailed the owner')
    except Exception as e:
        print(f'email not sent: {type(e).__name__}')
