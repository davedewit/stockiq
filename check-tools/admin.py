#!/usr/bin/env python3
"""The owner's Admin page, from a session's side (17 Oct 2026). The page lives in the dashboard (website/admin-panel.js) and
keeps its proposals in item `_admin` of table stockiq-ai-trader. A session starts by reading the answers:

    python3 check-tools/admin.py                     what is open, and what the owner said "yes" to for a session to do
    python3 check-tools/admin.py done <id> "<what was done>"     mark a "yes" as done once it is built and live
    python3 check-tools/admin.py add session "<title>" "<why>"   put a question to the owner that needs code
    python3 check-tools/admin.py add setting "<title>" "<why>" '<json change>'   e.g. '{"aiSell": false}' or '{"untick": "7-1"}'
    python3 check-tools/admin.py audit               the nightly site check's findings (audit/latest.json) onto the page
    python3 check-tools/admin.py change "<what>"     add a line to "What changed lately" (check-tools/changes.json), in plain words

A "setting" proposal is applied by the function itself the moment the owner presses "Yes"; a "session" one waits for a
session. Nothing here prints an account's address.
"""
import json, sys, os
from datetime import datetime, timezone
import boto3

TABLE, KEY = 'stockiq-ai-trader', '_admin'
table = boto3.Session(profile_name='default', region_name='us-east-1').resource('dynamodb').Table(TABLE)


def questions(here):
    """The questions asked so far (check-tools/reviews/questions.md, its table), for the Admin page's Improvements tab: each with its
    status and answer, so that what was already tried is seen and not tried again (23 Oct 2026, the owner)."""
    import re
    out = []
    try:
        for line in open(os.path.join(here, 'reviews', 'questions.md'), encoding='utf-8'):
            c = [x.strip() for x in line.strip().strip('|').split('|')]
            if len(c) < 5 or not c[0].isdigit():
                continue
            ans = c[-1]; m = re.match(r'\*\*([^*]+)\*\*', ans)
            word = (m.group(1) if m else ans).strip().rstrip('.:').lower()
            status = 'answered' if word.startswith('answered') else 'trial' if 'trial' in word or word.startswith('running') else 'waiting' if word.startswith('waiting') else 'open'
            clean = lambda t: re.sub(r'\*\*|`', '', t)
            out.append({'n': int(c[0]), 'asked': c[1][:40], 'q': clean(c[2])[:300], 'status': status, 'answer': clean(ans)[:420]})
    except OSError:
        pass
    return out


def load():
    item = table.get_item(Key={'userId': KEY}).get('Item')
    return dict({'proposals': [], 'review': None, 'health': None, 'seq': 0}, **(json.loads(item['data']) if item else {}))


def save(admin):
    table.put_item(Item={'userId': KEY, 'data': json.dumps(admin, separators=(',', ':')), 'enabled': False})


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


admin, args = load(), sys.argv[1:]
if not args:
    todo = [p for p in admin['proposals'] if p['status'] == 'yes']
    open_ = [p for p in admin['proposals'] if p['status'] == 'open']
    print(f"FOR THIS SESSION TO DO (the owner said yes): {len(todo)}")
    for p in todo:
        print(f"  #{p['id']} {p['title']}  (answered {p.get('answered', '')})\n      {p['why']}")
    print(f"WAITING FOR THE OWNER'S ANSWER: {len(open_)}")
    for p in open_:
        print(f"  #{p['id']} [{p['kind']}] {p['title']}")
    r, h = admin.get('review') or {}, admin.get('health') or {}
    print(f"last weekly review: {r.get('at', 'none')}; last scheduled run: {h.get('at', 'none')} ({h.get('ran', 0)} of {h.get('on', 0)} checked in, {h.get('failed', 0)} failed)")
elif args[0] == 'sync':
    # The improvements, as the Admin page lists them (17 Oct 2026: the owner asked to see what was run, what is next and what was
    # improved): check-tools/experiments.json and the last reviews of check-tools/site_parts.json. One small write.
    here = os.path.dirname(os.path.abspath(__file__))
    ex = json.load(open(os.path.join(here, 'experiments.json')))['experiments']
    parts = json.load(open(os.path.join(here, 'site_parts.json')))['parts']
    reviews = sorted(({'part': p['part'], 'at': l['at'], 'found': l['found']} for p in parts for l in p.get('log', [])), key=lambda x: x['at'], reverse=True)[:8]
    keep = ('id', 'what', 'angle', 'measure', 'status', 'added', 'started', 'decide', 'decided', 'result', 'order', 'public', 'publicText')
    kept = (admin.get('plan') or {}).get('audit')                  # the nightly site check stays when the improvements are synced
    kept_weekly = (admin.get('plan') or {}).get('weekly')          # and so does the last full check
    kept_daily = (admin.get('plan') or {}).get('dailyReview')
    kept_est = (admin.get('plan') or {}).get('estimates')
    changes = json.load(open(os.path.join(here, 'changes.json')))['changes'][:12]
    admin['plan'] = {'at': now(), 'items': [{k: e[k] for k in keep if k in e} for e in ex], 'reviews': reviews,
                     'parts': len(parts), 'reviewed': sum(1 for p in parts if p.get('last')), 'questions': questions(here)}
    if kept:
        admin['plan']['audit'] = kept
    if kept_weekly:
        admin['plan']['weekly'] = kept_weekly
    if kept_daily:
        admin['plan']['dailyReview'] = kept_daily
    if kept_est:
        admin['plan']['estimates'] = kept_est
    admin['plan']['changes'] = changes
    save(admin)
    print(f"the Admin page's improvements: {len(ex)} items, {len(reviews)} recent reviews")
elif args[0] == 'audit':
    # The nightly site check (site_audit.py --admin): its findings onto the Admin page. The autopilot's scheduled run writes the
    # same record at :10 and :40 past the hour, so this waits until it is clear of those minutes.
    import time
    here = os.path.dirname(os.path.abspath(__file__))
    a = json.load(open(os.path.join(here, 'audit', 'latest.json')))
    while datetime.now(timezone.utc).minute % 30 in (9, 10, 11, 12, 13):
        time.sleep(20)
    admin = load()
    admin.setdefault('plan', {})['audit'] = {k: a[k] for k in ('at', 'problems', 'ideas', 'new', 'gone')} | {'findings': a['findings'][:40]}
    daily = sorted(f for f in os.listdir(os.path.join(here, 'reviews', 'daily')) if f.endswith('.md')) if os.path.isdir(os.path.join(here, 'reviews', 'daily')) else []
    if daily:
        admin['plan']['dailyReview'] = daily[-1][:10]          # the latest report of the daily review by Claude, for "What runs by itself"
    save(admin)
    print(f"the Admin page's site check: {a['problems']} problems, {a['ideas']} ideas")
elif args[0] == 'weekly':
    # The full check (weekly_check.py, every 7 days or more): its result onto the Admin page, clear of :10 and :40 past the hour
    import time
    here = os.path.dirname(os.path.abspath(__file__))
    w = json.load(open(os.path.join(here, 'weekly_check.json')))
    while datetime.now(timezone.utc).minute % 30 in (9, 10, 11, 12, 13):
        time.sleep(20)
    admin = load()
    admin.setdefault('plan', {})['weekly'] = {k: w[k] for k in ('at', 'passed', 'total')} | {'failed': [f['name'] for f in w['failed']][:20],
        'covered': w.get('covered'), 'parts': w.get('parts'), 'uncovered': w.get('uncovered', [])[:12], 'items': [[i['part'][:2].strip('. '), i['name'][:150], i['ok']] for i in w.get('items', [])][:140]}
    save(admin)
    print(f"the Admin page's full check: {w['passed']} of {w['total']} passed")
elif args[0] == 'estimate' and len(args) >= 3:
    # The session's own estimate of the chance the account is ahead of an S&P 500 fund after a year (19 Oct 2026, the owner: "strange i
    # have to still ask you this ... it tells me through the site"). Updated at every weekly session, with the reason; the history stays.
    #   python3 check-tools/admin.py estimate 30 "<why, in plain words>"
    import time
    while datetime.now(timezone.utc).minute % 30 in (9, 10, 11, 12, 13):
        time.sleep(20)
    admin = load()
    plan = admin.setdefault('plan', {})
    hist = plan.get('estimates') or []
    hist.append({'at': now()[:10], 'pct': int(args[1]), 'why': ' '.join(args[2:])[:400]})
    plan['estimates'] = hist[-12:]
    save(admin)
    print(f"the Admin page's estimate: {args[1]}% ({len(plan['estimates'])} kept)")
elif args[0] == 'change' and len(args) >= 2:
    # A line for "What changed lately" on the Admin page (18 Oct 2026, the owner: "easy for me to read on admin page what is
    # going on"); then the page's copy is brought up to date.
    here = os.path.dirname(os.path.abspath(__file__)); path = os.path.join(here, 'changes.json')
    doc = json.load(open(path))
    doc['changes'] = ([{'at': now()[:10], 'what': args[1]}] + doc['changes'])[:60]
    json.dump(doc, open(path, 'w'), indent=1, ensure_ascii=False)
    admin.setdefault('plan', {})['changes'] = doc['changes'][:12]
    save(admin)
    print(f"added to What changed lately ({len(doc['changes'])} kept)")
elif args[0] == 'done' and len(args) >= 3:
    p = next((x for x in admin['proposals'] if str(x['id']) == args[1]), None)
    if not p:
        sys.exit(f'no proposal #{args[1]}')
    p.update(status='done', done=args[2], doneAt=now())
    save(admin)
    print(f"#{p['id']} marked done: {args[2]}")
elif args[0] == 'recommend' and len(args) >= 4 and args[2] in ('yes', 'no'):
    # the session's own answer to a decision, shown beside it on the Admin page (23 Oct 2026, the owner: "put your preference")
    #   python3 check-tools/admin.py recommend <id> yes|no "<why, one plain sentence, profit first>"
    hit = [p for p in admin['proposals'] if str(p['id']) == args[1]]
    if not hit:
        sys.exit('no such decision')
    hit[0]['recommend'], hit[0]['recommendWhy'] = args[2], args[3][:300]
    save(admin)
    print(f"#{args[1]}: recommends {args[2]}")
elif args[0] == 'add' and len(args) >= 4 and args[1] in ('session', 'setting'):
    change = json.loads(args[4]) if args[1] == 'setting' and len(args) > 4 else None
    if args[1] == 'setting' and not change:
        sys.exit('a setting proposal needs its change as JSON')
    admin['seq'] = int(admin.get('seq', 0)) + 1
    admin['proposals'].append({'id': admin['seq'], 'key': f"session-{admin['seq']}", 'at': now(), 'title': args[2], 'why': args[3], 'kind': args[1], 'change': change, 'status': 'open'})
    save(admin)
    print(f"#{admin['seq']} added: {args[2]}")
else:
    sys.exit(__doc__)
