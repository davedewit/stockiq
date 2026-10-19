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
    ok = ('ALL PASS' in out or re.search(r'all \d+ checks passed', out) or re.search(r'\b\d+ passed, 0 failed', out)) and not fails
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
    h = admin.get('health') or {}
    note('2. The figures agree across the site', 'the autopilot\'s last scheduled run reported no failed check-in', h and not h.get('failed'), h)
except Exception as e:
    note('2. The figures agree across the site', 'the consistency checks themselves ran', False, f"{type(e).__name__}: {e}")

# ---------------------------------------------------------------- 3. real buttons
if not QUICK:
    print('\n== 3. Real buttons, end to end (nothing saved)', flush=True)
    for opt, sub, name in (('3', '8', 'Dow 30'), ('5', 'dax40', 'Germany DAX 40'), ('5', '200', 'ASX 200'), ('1', 'custom', 'a single-stock report')):
        code, out = run(['node', os.path.join(HERE, 'page_run.js'), opt, sub], 600, cwd=tmp)
        try:
            s = json.loads([l for l in out.splitlines() if l.startswith('{')][-1])
        except Exception:
            s = {}
        ok = s and not s.get('error') and not s.get('flags') and (opt == '1' or (s.get('trackerSymbols') or 0) >= 10)
        note('3. Real buttons', f"{name}: runs, no error, no raw codes or 'undefined', the tracker reads its top 10", ok, {k: s.get(k) for k in ('error', 'flags', 'trackerSymbols', 'secs')} if s else out[-200:])

shutil.rmtree(tmp, ignore_errors=True)
passed, total = sum(1 for r in results if r[2]), len(results)
at = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
lines = [f"FULL CHECK OF THE SITE, {at[:10]} ({'quick' if QUICK else 'everything'}): {passed} of {total} passed", '']
for part in sorted({r[0] for r in results}):
    lines.append(part)
    lines += [f"  {'PASS' if ok else 'FAIL'}  {name}" + ('' if ok else f"\n        {detail}") for p, name, ok, detail in results if p == part]
    lines.append('')
os.makedirs(os.path.join(HERE, 'reviews', 'weekly'), exist_ok=True)
open(os.path.join(HERE, 'reviews', 'weekly', f"check-{at[:10]}.txt"), 'w').write('\n'.join(lines))
json.dump({'at': at, 'quick': QUICK, 'passed': passed, 'total': total, 'failed': [{'part': p, 'name': n, 'detail': d} for p, n, ok, d in results if not ok]},
          open(os.path.join(HERE, 'weekly_check.json'), 'w'), indent=1)
print('\n' + lines[0])
if not QUICK:
    run(['python3', os.path.join(HERE, 'admin.py'), 'weekly'], 300)
if EMAIL:
    try:
        import boto3
        failed = [f"- {p}: {n}" for p, n, ok, d in results if not ok]
        body = (f"{lines[0]}\n\n" + ('Everything passed: every test suite on the live code, the figures agreeing across the pages (account, holdings, '
                'trades, bill, sitemap), and real screener buttons.' if not failed else 'What failed (a session fixes these first):\n' + '\n'.join(failed))
                + f"\n\nThe full report: stockiq/check-tools/reviews/weekly/check-{at[:10]}.txt. The Admin page shows the same result.\n\nStockIQ")
        boto3.Session(profile_name='default', region_name='us-east-1').client('ses').send_email(
            Source='StockIQ <autopilot@stockiq.tech>', Destination={'ToAddresses': [OWNER]},
            Message={'Subject': {'Data': f"StockIQ full check: {'all ' + str(total) + ' passed' if passed == total else str(total - passed) + ' of ' + str(total) + ' failed'}"},
                     'Body': {'Text': {'Data': body}}})
        print('emailed the owner')
    except Exception as e:
        print(f'email not sent: {type(e).__name__}')
