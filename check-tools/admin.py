#!/usr/bin/env python3
"""The owner's Admin page, from a session's side (17 Oct 2026). The page lives in the dashboard (website/admin-panel.js) and
keeps its proposals in item `_admin` of table stockiq-ai-trader. A session starts by reading the answers:

    python3 check-tools/admin.py                     what is open, and what the owner said "yes" to for a session to do
    python3 check-tools/admin.py done <id> "<what was done>"     mark a "yes" as done once it is built and live
    python3 check-tools/admin.py add session "<title>" "<why>"   put a question to the owner that needs code
    python3 check-tools/admin.py add setting "<title>" "<why>" '<json change>'   e.g. '{"aiSell": false}' or '{"untick": "7-1"}'

A "setting" proposal is applied by the function itself the moment the owner presses "Yes"; a "session" one waits for a
session. Nothing here prints an account's address.
"""
import json, sys
from datetime import datetime, timezone
import boto3

TABLE, KEY = 'stockiq-ai-trader', '_admin'
table = boto3.Session(profile_name='default', region_name='us-east-1').resource('dynamodb').Table(TABLE)


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
elif args[0] == 'done' and len(args) >= 3:
    p = next((x for x in admin['proposals'] if str(x['id']) == args[1]), None)
    if not p:
        sys.exit(f'no proposal #{args[1]}')
    p.update(status='done', done=args[2], doneAt=now())
    save(admin)
    print(f"#{p['id']} marked done: {args[2]}")
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
