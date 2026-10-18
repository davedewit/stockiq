#!/usr/bin/env python3
"""The first command of every session (17 Oct 2026; the owner: "i don't want to keep having to ask things, you should be active
in this as well"). Read-only. It gathers what a session must know before it says anything, and ends with a list of FINDINGS:
everything that is off, due or waiting, so that the session acts on it instead of waiting to be told.

    python3 check-tools/session_start.py

What it looks at:
  1. the result: the practice account at the latest prices, against the same $100,000 in an S&P 500 fund, and the month's goal
  2. the Admin page: what the owner said yes to (for this session), what waits for his answer, how the scheduled runs went,
     this month's AWS bill and Lambda calls
  3. the weekly review: due when the newest file in check-tools/reviews/ is 7 days old or more
  4. faults: error lines in the logs of the functions that matter (48 hours), the daily deploy's log
  5. drift: each function that matters, live against its mirror in lambda-sync/; the site's key files, live against local
  6. both repositories: uncommitted files, commits not pushed, staging folders left over
  7. the improvements list: what the notes say is due (site-overview.md, "Improvements to come")
Never prints an account's address. Costs: a few reads, and the price function for the holdings (no Cost Explorer question:
the Admin page's figure is read).
"""
import os, sys, json, glob, time, hashlib, subprocess, importlib.util, datetime, urllib.request, zipfile, io, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); WEB = os.path.join(os.path.dirname(ROOT), 'website')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1'); os.environ.setdefault('AWS_PROFILE', 'default')
import boto3
findings, now = [], datetime.datetime.utcnow()
def finding(text): findings.append(text)
def head(t): print(f'\n== {t}')
def sh(cmd, cwd=ROOT):
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True).stdout.strip()

spec = importlib.util.spec_from_file_location('trader', os.path.join(ROOT, 'lambda-sync', 'stockiq-ai-trader', 'lambda_function.py'))
m = importlib.util.module_from_spec(spec)
with open(os.devnull, 'w') as quiet:
    _o = sys.stdout; sys.stdout = quiet
    try: spec.loader.exec_module(m)
    finally: sys.stdout = _o
db = boto3.resource('dynamodb')

# 1. the result
head('1. The result (fake money)')
owner = [u for u in (os.environ.get('AI_TRADER_OWNER') or '').split(',') if u]
rows = db.Table('stockiq-ai-trader').scan(ProjectionExpression='userId, enabled').get('Items', [])
on = [r['userId'] for r in rows if r.get('enabled') and not r['userId'].startswith('_')]
for uid in (owner or on)[:3]:
    rec = m.load_item(uid); item = db.Table('stockiq-paper-portfolios').get_item(Key={'userId': uid}).get('Item')
    pf = json.loads(item['data']) if item else m.new_portfolio(now)
    g = m.goal_standing(rec, pf, now, m.fetch_quote); vs = m.fund_since_start(pf, g['value'], now)
    print(f"  account ${g['value']:,.2f} ({g['value'] - 100000:+,.2f} since the start)" + (f"; the same $100,000 in an S&P 500 fund ${vs[0]:,.2f}: {'ahead' if vs[1] >= 0 else 'BEHIND'} by ${abs(vs[1]):,.2f}" if vs else ''))
    print(f"  {g['name']} (due {g['due']}, {g['daysLeft']} days left): {g['trades']} of {g['tradesGoal']} trades; this month {g['avg']:+.2f}% a trade "
          f"(probably between {g['avg'] - 2 * g['se']:+.2f}% and {g['avg'] + 2 * g['se']:+.2f}%, {g['n']} trades) against above {g['avgGoal']:+.1f}%; account target ${g['valueGoal']:,.0f}")
    if vs and vs[1] < 0: finding(f"BEHIND THE S&P 500 FUND by ${abs(vs[1]):,.0f}: say so first, find which groups lost, bring changes")
    if g['n'] >= 30 and g['avg'] + 2 * g['se'] < 0: finding(f"finished trades clearly losing this month ({g['avg']:+.2f}% a trade over {g['n']}): which groups? what changes?")
    if g['daysLeft'] <= 10 and not g['met']: finding(f"{g['name']} due in {g['daysLeft']} days and not met")
    print(f"  settings: level {rec['settings'].get('risk')}, holdings {rec['settings'].get('holdings')}, every {rec['settings'].get('everyHours')} h, keeps up to {rec['settings'].get('maxHoldDays')} days, "
          f"AI review sales {'on' if rec['settings'].get('aiSell') else 'off'}, {len(rec['settings'].get('screeners', []))} screeners; open trials: order {rec['state'].get('order', {}).get('mode')}, patient {'on' if m.PATIENT else 'off'}")

    if hasattr(m, 'theme_review_lines'):
        for l in m.theme_review_lines(rec, pf, now, m.fetch_quote): print('  ' + l)
        th = rec['state'].get('themes') or {}
        if m.themes_on(rec['settings']) and th.get('last') and (now - m.parse_time(th['last'])).days > m.THEME_EVERY_DAYS + 3:
            finding(f"the themes part's monthly change is overdue (last {th['last'][:10]}): look at the function's log")

# 2. the Admin page
head('2. The Admin page')
admin = m.load_admin()
yes = [p for p in admin['proposals'] if p['status'] == 'yes']; waiting = [p for p in admin['proposals'] if p['status'] == 'open']
for p in yes: finding(f"the owner said YES on the Admin page, for a session: #{p['id']} {p['title']} (do it, then: python3 check-tools/admin.py done {p['id']} \"...\")")
print(f"  waiting for his answer: {len(waiting)}" + ''.join(f"\n    #{p['id']} {p['title']}" for p in waiting))
h, u = admin.get('health') or {}, admin.get('usage') or {}
print(f"  last scheduled run {h.get('at')}: {h.get('ran')} of {h.get('on')} checked in, {h.get('failed', 0)} failed")
if not h or (now - (m.parse_time(h.get('at')) or now)).total_seconds() > 75 * 60: finding('the scheduled run has not reported for more than 75 minutes: is the schedule enabled?')
if h.get('failed'): finding(f"{h['failed']} check-in(s) stopped on an error at the last scheduled run")
if u:
    print(f"  AWS this month (read {u.get('at')}): bill ${u.get('cost', '?')}, Lambda calls {u.get('calls', '?'):,} of {u.get('free', 1000000):,} free, on course for {u.get('forecast') or '?'}, yesterday {u.get('yesterday')}")
    if (u.get('cost') or 0) >= 1: finding(f"the AWS bill this month is ${u['cost']:.2f}: the owner's limit is about $1 a month")
    if (u.get('forecast') or 0) > 0.9 * (u.get('free') or 1e6): finding(f"Lambda calls on course for {u['forecast']:,} this month, near or over the free million")
else:
    print('  AWS figures not read yet')

# 3. the weekly review
head('3. The weekly review')
files = sorted(glob.glob(os.path.join(HERE, 'reviews', 'review-*.txt')))
age = (time.time() - os.path.getmtime(files[-1])) / 86400 if files else 99
print(f"  newest: {os.path.basename(files[-1]) if files else 'none'}, {age:.1f} days old")
if age >= 7: finding(f"THE WEEKLY REVIEW IS DUE (the newest is {age:.0f} days old): run the routine in site-overview.md section 8c before anything else")

# 4. faults
head('4. Faults in the last 48 hours')
logs = boto3.client('logs'); since = int((time.time() - 48 * 3600) * 1000)
for fn in ('stockiq-ai-trader', 'stockiq-screener-coordinator', 'stockiq-option-1-1-custom-analysis', 'stockiq-ai-chat', 'stockiq-paper-portfolio', 'stockiq-price-proxy', 'stockiq-option-7-1-orchestrator'):
    try:
        ev = logs.filter_log_events(logGroupName=f'/aws/lambda/{fn}', startTime=since, filterPattern='?Traceback ?ERROR ?"Task timed out" ?failed', limit=50).get('events', [])
        ev = [e for e in ev if 'shared learning failed' in e['message'] or 'Traceback' in e['message'] or 'timed out' in e['message'] or 'ERROR' in e['message']]
        print(f"  {fn}: {len(ev)} error line(s)" + (f" (latest: {ev[-1]['message'].strip()[:140]})" if ev else ''))
        if ev: finding(f"{fn}: {len(ev)} error line(s) in 48 hours: read them (aws logs tail /aws/lambda/{fn} --since 48h)")
    except Exception as e:
        print(f"  {fn}: log not read ({type(e).__name__})")
daily = os.path.expanduser('~/stockiq-daily.log')
if os.path.exists(daily):
    text = open(daily, errors='replace').read()
    for pat in (r'No price data: (\d+)', ):
        mm = re.search(pat, text)
        if mm and int(mm.group(1)) > 1000: finding(f"the daily run got no prices for {mm.group(1)} stocks (Yahoo's limit on this machine): nothing de-indexed, but re-run update_stock_analysis.py later")
    for bad in ('could not rebase', 'push failed', 'Traceback', 'FAILED'):
        if bad in text: finding(f"the daily deploy's log says '{bad}': read ~/stockiq-daily.log")
    print(f"  daily deploy log: {time.strftime('%d %b %H:%M', time.localtime(os.path.getmtime(daily)))}; " + ('; '.join(l.strip() for l in text.splitlines() if re.search(r'Indexable|All done|pushed to GitHub', l))[:300]))

# 5. drift
head('5. Live against local')
lam = boto3.client('lambda')
for fn, f in (('stockiq-ai-trader', 'lambda_function.py'), ('stockiq-screener-coordinator', 'lambda_function.py'), ('stockiq-ai-chat', 'lambda_function.py'), ('stockiq-option-1-1-custom-analysis', 'lambda_function2.py')):
    try:
        z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(lam.get_function(FunctionName=fn)['Code']['Location'], timeout=60).read()))
        same = z.read(f) == open(os.path.join(ROOT, 'lambda-sync', fn, f), 'rb').read()
        print(f"  {fn}: {'live equals the mirror' if same else 'LIVE DIFFERS FROM THE MIRROR'}")
        if not same: finding(f"{fn}: the live code is not the mirror in lambda-sync/ (another session, or a deploy by hand?): find out before changing it")
    except Exception as e:
        print(f"  {fn}: not compared ({type(e).__name__})")
for f in ('dashboard.html', 'practice-portfolio.js', 'practice-autopilot.js', 'admin-panel.js', 'analysis-functions.js', 'screeners.js', 'autopilot-bell.js', 'index.html', 'analysis.html'):
    try:
        live = urllib.request.urlopen(f'https://stockiq.tech/{f}?check={int(time.time())}', timeout=30).read()
        same = live == open(os.path.join(WEB, f), 'rb').read()
        if not same: finding(f"website/{f}: the live file differs from the local one (not deployed, or changed elsewhere)")
        print(f"  {f}: {'same' if same else 'DIFFERS'}")
    except Exception as e:
        print(f"  {f}: not compared ({type(e).__name__})")

# 6. the repositories
head('6. The repositories')
for repo in (ROOT, WEB):
    st = sh('git status -sb', repo).splitlines()
    dirty = [l for l in st[1:] if not re.search(r'news\.html|news\.js|sitemap\.xml', l)]
    print(f"  {os.path.basename(repo)}: {st[0] if st else '?'}; {len(dirty)} other uncommitted file(s)")
    if 'ahead' in (st[0] if st else ''): finding(f"{os.path.basename(repo)}: commits not pushed ({st[0]})")
    if dirty: finding(f"{os.path.basename(repo)}: uncommitted: {', '.join(l[3:] for l in dirty[:6])} (another session's work? look before committing)")
kept = {'pending-screeners-undo', 'pending-cleanup-undo', 'pending-banners-undo', 'pending-simple-undo'}
left = [os.path.basename(d) for d in glob.glob(os.path.join(HERE, 'pending-*')) if os.path.basename(d) not in kept]
if left: finding(f"staging folders left over: {', '.join(left)} (a deploy not finished, or another session's)")
print(f"  staging folders: {', '.join(sorted(kept & set(os.listdir(HERE))))} (kept on purpose)" + (f"; others: {', '.join(left)}" if left else ''))

# 6b. the screeners' stock lists (lists_check.py: page and coordinator alike, no duplicates; the full check monthly)
head('6b. The screeners\' stock lists')
r = subprocess.run([sys.executable, os.path.join(HERE, 'lists_check.py')], capture_output=True, text=True)
got = [l.strip()[3:] if l.strip()[:3].rstrip('.').isdigit() else l.strip() for l in r.stdout.splitlines() if re.match(r'\s+\d+\. ', l)]
print('  ' + (r.stdout.strip().splitlines()[0] if r.stdout.strip() else 'not run: ' + r.stderr.strip()[:200]))
for g in got: finding('stock list: ' + re.sub(r'^\d+\.\s*', '', g))
try:
    last = json.load(open(os.path.join(ROOT, 'research-data', 'lists_check.json'))).get('full')
except Exception:
    last = None
age_days = (now - datetime.datetime.strptime(last[:19], '%Y-%m-%dT%H:%M:%S')).days if last else 99
print(f'  the full check (prices of every symbol, members against each index\'s own source): {last or "never"}')
if age_days >= 30: finding(f"the screeners' full list check is {'never run' if not last else str(age_days) + ' days old'}: python3 check-tools/lists_check.py --full (about 15 minutes), then update what it finds")

# 6c. parts of the site to review today, without being asked (site_parts.py; the owner's idea, 17 Oct 2026)
head('6c. Parts of the site to look at this session')
r = subprocess.run([sys.executable, os.path.join(HERE, 'site_parts.py'), 'next', '3'], capture_output=True, text=True)
for l in r.stdout.splitlines()[:3]:
    print('  ' + l); finding('REVIEW without being asked: ' + l.split(' (where')[0] + ' (then: python3 check-tools/site_parts.py done <id> "<what was found>")')

# 6d. experiments whose day has come (experiments.py: keep or remove on the figures; the owner, 17 Oct 2026)
head('6d. Experiments')
r = subprocess.run([sys.executable, os.path.join(HERE, 'experiments.py'), 'due'], capture_output=True, text=True)
due_now = [l for l in r.stdout.splitlines() if l.strip()]
print(f"  due for a decision: {len(due_now)}" + ''.join('\n    ' + l for l in due_now))
for l in due_now: finding('DECIDE an experiment (keep or remove, on the figures): ' + l.split(' (started')[0])
finding('every session: add at least one new idea of your own to check-tools/experiments.py (any angle: profit, ease of use, appearance, analysis, AI use, cost)')

# 6e. the page as the owner reads it (clarity_check.py; the owner, 17 Oct 2026: "anything else confusing you want to optimise?
#     and i'm tired of asking this!"): near-identical lines, "A and B and C", a switched-off feature still described, huge menus
head('6e. The dashboard as the owner reads it')
try:
    r = subprocess.run([sys.executable, os.path.join(HERE, 'clarity_check.py')], capture_output=True, text=True, timeout=400)
    out = [l for l in r.stdout.splitlines() if l.strip()]
    for l in out: print('  ' + l)
    for l in out:
        if l.startswith('FLAG '): finding('CLARITY (fix it, or teach clarity_check.py that it is fine): ' + l[5:])
    if not out: finding('clarity_check.py printed nothing: ' + (r.stderr.strip().splitlines() or ['no error'])[-1][:150])
except Exception as e:
    finding(f'clarity_check.py did not run: {type(e).__name__}: {e}')
finding('every session: read at least one tab of the dashboard as the owner would (clarity_check.py --keep gives its text) and fix whatever reads confusingly, without being asked')

# 7. the improvements list
head('7. What the notes say is due')
notes = open(os.path.join(ROOT, '.kiro', 'steering', 'site-overview.md'), encoding='utf-8').read()
part = notes[notes.find('**Improvements to come'):]
part = part[:part.find('*Housekeeping')]
for line in part.splitlines():
    if line.startswith('- **') or re.match(r'^\d+\. \*\*', line): print('  ' + line[:170])
finding('every session: add new ideas of your own to check-tools/reviews/questions.md and the improvements list, and look again at what was ruled out')

print('\n== FINDINGS (act on these; tell the owner the result in dollars first)')
for i, f in enumerate(findings, 1): print(f'  {i}. {f}')
