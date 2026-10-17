#!/usr/bin/env python3
"""The register of experiments (17 Oct 2026). The owner: "you can literally think of new ideas and add to it test over a period of
time then keep it or remove it based on whether it improves ... the opportunity to do anything you wish test decide next steps
further ideas to improve it is endless."

Every change whose worth is not certain goes in here as an experiment: what it is, which angle (profit, ease of use, appearance,
analysis, AI use, cost...), how it is measured, against what, and the day it is decided. session_start.py lists those whose day has
come; the session then reads the figures, decides KEEP or REMOVE (or extends it once, with a reason), and writes the result. An
experiment that is never decided is the failure this register exists to prevent. Ideas not yet started sit here as "idea".

    python3 check-tools/experiments.py                        all, the ones to decide first
    python3 check-tools/experiments.py due                    the ones whose day has come
    python3 check-tools/experiments.py add <id> "<what>" "<angle>" "<how it is measured>" <days>     start one today
    python3 check-tools/experiments.py idea <id> "<what>" "<angle>" "<how it would be measured>"    note one for later
    python3 check-tools/experiments.py decide <id> keep|remove|extend "<the figures and why>"

The file (check-tools/experiments.json) is in git: no addresses or keys in it.
"""
import os, sys, json, datetime
FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'experiments.json')
today = datetime.date.today()

def load(): return json.load(open(FILE)) if os.path.exists(FILE) else {'experiments': []}
def save(d):
    json.dump(d, open(FILE, 'w'), indent=1, ensure_ascii=False)
    try:                     # the Admin page shows the improvements (admin.py sync): keep it current
        import subprocess; subprocess.run([sys.executable, os.path.join(os.path.dirname(FILE), 'admin.py'), 'sync'], capture_output=True, timeout=60)
    except Exception:
        pass
def due(d): return [e for e in d['experiments'] if e['status'] == 'running' and e.get('decide') and e['decide'] <= today.isoformat()]

if __name__ == '__main__':
    d, a = load(), sys.argv[1:]
    if not a or a[0] == 'list':
        order = {'running': 0, 'idea': 1, 'kept': 2, 'removed': 3}
        for e in sorted(d['experiments'], key=lambda e: (order.get(e['status'], 9), e.get('decide') or '9')):
            print(f"[{e['status']:7s}] {e['id']}: {e['what']}  ({e['angle']}; measured by: {e['measure']}" + (f"; decide by {e['decide']}" if e.get('decide') else '') + ')' + (f"\n           result: {e['result']}" if e.get('result') else ''))
    elif a[0] == 'due':
        for e in due(d): print(f"{e['id']}: {e['what']} (started {e['started']}, measured by: {e['measure']})")
    elif a[0] in ('add', 'idea') and len(a) >= 5:
        e = {'id': a[1], 'what': a[2], 'angle': a[3], 'measure': a[4], 'status': 'running' if a[0] == 'add' else 'idea'}
        if a[0] == 'add': e.update(started=today.isoformat(), decide=(today + datetime.timedelta(days=int(a[5]) if len(a) > 5 else 28)).isoformat())
        d['experiments'] = [x for x in d['experiments'] if x['id'] != a[1]] + [e]; save(d); print(f"{a[1]}: {e['status']}")
    elif a[0] == 'decide' and len(a) >= 4:
        e = next(x for x in d['experiments'] if x['id'] == a[1])
        if a[2] == 'extend':
            e['decide'] = (today + datetime.timedelta(days=14)).isoformat(); e.setdefault('notes', []).append(f"{today}: extended: {a[3]}")
        else:
            e.update(status='kept' if a[2] == 'keep' else 'removed', decided=today.isoformat(), result=a[3])
        save(d); print(f"{a[1]}: {e['status']}")
    else:
        sys.exit(__doc__)
