"""Puts the one share-screener package (built from this folder) on the worker functions. Run it through a packaged script:

    check-tools/pending-<name>/deploy.sh      three lines, see TEMPLATE below
    check-tools/pending-<name>/groups.txt     the groups this run does, one a line, or the one word: all

    DRY_RUN=true bash check-tools/pending-<name>/deploy.sh     preview: checks everything, changes nothing
    bash check-tools/pending-<name>/deploy.sh                  deploy
    ROLLBACK=true bash check-tools/pending-<name>/deploy.sh    put the groups back on the package that was live before

How it stays safe. Every worker runs the same package, so there are only two fingerprints it accepts on a function: the
one that is live (live.txt in this folder, written by the last finished deploy) and the new one it has just built. A
function showing anything else is not touched and the run stops. Before the first update it keeps the live package once, as
~/VSCODE/backup/workers_package_<its fingerprint>.zip (that zip is the way back for every function). A group is updated,
checked against the fingerprint AWS reports, then tried for real (its first and last worker, three stocks of its market, an
empty batch, and a call with the number only); a group that fails the try is put back by itself and the run stops. When
every group is on the new package it writes live.txt: commit it. Safe to run twice. It will not start within a few
minutes of :10 or :40 (the autopilot reads the screeners then), while the daily deploy runs, or with uncommitted
changes in workers/.

TEMPLATE for check-tools/pending-<name>/deploy.sh:
    #!/bin/bash
    set -euo pipefail
    exec /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/deploy.py "$(cd "$(dirname "$0")" && pwd)"

    python3 workers/deploy.py --selftest      the rules above, played against a stand-in for AWS (nothing real is called)

First used in this form after 11 Oct 2026. That day's deploy (seven different copies to one) used an earlier form that
checked each function's files one by one: git show a6edbd9:check-tools/pending-workers/deploy.py, and its per-function
copies of the old code are in ~/VSCODE/backup/workers_before_onecode_20261011/.
"""
import os, sys, re, json, time, base64, hashlib, zipfile, shutil, glob, subprocess, urllib.request, datetime, concurrent.futures
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import build, groups as G
MIRROR = os.path.join(ROOT, 'lambda-sync'); BACKUP = '/Users/dave/VSCODE/backup'; LIVE_FILE = os.path.join(HERE, 'live.txt')

class Stop(Exception): pass
def say(*a): print(*a, flush=True)
def b64sha(data): return base64.b64encode(hashlib.sha256(data).digest()).decode()
def many(fn, items, threads=6):
    with concurrent.futures.ThreadPoolExecutor(threads) as pool: return list(pool.map(fn, items))

class Aws:
    """The few calls this needs. The self-test puts a stand-in with the same methods in its place."""
    def __init__(self):
        import boto3, botocore.config
        self.lam = boto3.Session(profile_name='default', region_name='us-east-1').client('lambda', config=botocore.config.Config(retries={'max_attempts': 12, 'mode': 'adaptive'}, read_timeout=120))
    def functions(self):
        return {f['FunctionName']: (f['CodeSha256'], f['Handler']) for page in self.lam.get_paginator('list_functions').paginate() for f in page['Functions']}
    def package(self, name):
        return urllib.request.urlopen(self.lam.get_function(FunctionName=name)['Code']['Location'], timeout=60).read()
    def put(self, name, data):
        self.lam.update_function_code(FunctionName=name, ZipFile=data); want = b64sha(data)
        for _ in range(40):
            c = self.lam.get_function_configuration(FunctionName=name)
            if c.get('LastUpdateStatus') == 'Successful' and c['CodeSha256'] == want: return True
            if c.get('LastUpdateStatus') == 'Failed': return False
            time.sleep(1.5)
        return False
    def call(self, name, payload):
        r = self.lam.invoke(FunctionName=name, Payload=json.dumps(payload).encode()); out = json.loads(r['Payload'].read())
        if r.get('FunctionError') or out.get('statusCode') != 200: return {'success': False, 'error': str(out)[:300]}
        return json.loads(out['body'])

def try_group(aws, group, names):
    """The group's first and last worker, run for real. Returns what was wrong (nothing: it passed)."""
    market = G.MARKETS[G.GROUPS[group][2]]; batch = market['try_with']; problems = []
    for name in sorted({names[0], names[-1]}, key=names.index):
        r = aws.call(name, {'stock_batch': batch, 'worker_id': 1}); rows = r.get('results') or []
        ok = r.get('success') and len(rows) == len(batch) and all(x.get('currency') == market['currency'] and isinstance(x.get('score'), (int, float)) and x.get('recommendation') and x.get('price', 0) > 0 for x in rows)
        say(f"      {name}: {len(rows)} of {len(batch)} analysed" + (': ' + ', '.join(f"{x['symbol']} {x['price']} {x.get('currency')} score {x['score']:+.1f} 24h {x['change_24h']:+.2f}%" for x in rows) if rows else f" ({r.get('error')})"))
        if not ok: problems.append(f"{name} did not answer as expected")
        empty = aws.call(name, {'stock_batch': [], 'worker_id': 1})
        if not (empty.get('success') and empty.get('stocks_processed') == 0): problems.append(f"{name}, sent an empty batch, answered {str(empty)[:120]}")
    r = aws.call(names[0], {'worker_id': 1, 'batch_size': 10})
    if group in G.NUMBER_ONLY:
        lists = {l.split(':')[0]: l.split(':')[1].split() for l in open(os.path.join(HERE, 'lists.txt'))}; got = [x['symbol'] for x in r.get('results') or []]
        say(f"      {names[0]} called with its number only: {r.get('stocks_processed')} taken from its list, {len(got)} analysed")
        if r.get('stocks_processed') != 10 or not set(got) <= set(lists[group][:10]) or len(got) < 8: problems.append("a call with the number only did not take the list's first ten")
    elif r.get('stocks_processed') != 0: problems.append('a call with the number only processed stocks')
    return problems

def run(aws, wanted, new_data, live, dry=False, rollback=False, backup=BACKUP, mirror=MIRROR, write_live=True):
    NEW = b64sha(new_data); kept = os.path.join(backup, 'workers_package_' + re.sub(r'[^A-Za-z0-9]', '', live)[:16] + '.zip')
    say(f"live package {live}\nnew package  {NEW}" + ('   (the same: this run only checks)' if NEW == live else ''))
    listed = aws.functions(); done = []
    for group in wanted:
        screener, count, market = G.GROUPS[group]
        names = sorted((n for n in listed if re.fullmatch(re.escape(group) + r'-\d+', n)), key=lambda n: int(n.rsplit('-', 1)[1]))
        say(f"\n== {group} ({screener}; {len(names)} functions)")
        if len(names) != count: raise Stop(f"{group} has {len(names)} functions, groups.py says {count}")
        bad = [n for n in names if listed[n][1] not in ('lambda_function.lambda_handler', 'advanced_lambda.lambda_handler')]
        if bad: raise Stop(f"{bad[0]} has the handler {listed[bad[0]][1]}, which the package does not provide")
        odd = [n for n in names if listed[n][0] not in (NEW, live)]
        if odd: raise Stop(f"{len(odd)} function(s) of {group} hold neither the live package nor the new one, e.g. {odd[0]} ({listed[odd[0]][0]}): look before anything is changed")
        if rollback:
            todo = [n for n in names if listed[n][0] == NEW and NEW != live]
            say(f"   on the new package: {len(todo)}; already on the one that was live: {len(names) - len(todo)}")
            if not todo or dry: continue
            if not os.path.exists(kept) or b64sha(open(kept, 'rb').read()) != live: raise Stop(f"the kept copy of the live package is missing or is not it: {kept}")
            old = open(kept, 'rb').read(); failed = [n for n, ok in many(lambda n: (n, aws.put(n, old)), todo) if not ok]
            if failed: raise Stop(f"{len(failed)} function(s) could not be put back, e.g. {failed[0]}: run this again")
            say(f"   {len(todo)} put back"); continue
        todo = [n for n in names if listed[n][0] == live and NEW != live]
        say(f"   already on the new package: {len(names) - len(todo)}; to update: {len(todo)}")
        if not todo: done.append(group); continue
        if not os.path.exists(kept):
            old = aws.package(todo[0])
            if b64sha(old) != live: raise Stop(f"the package downloaded from {todo[0]} is not the live one")
            if dry: say(f"   (dry run) would keep the live package as {kept}")
            else: open(kept, 'wb').write(old); say(f"   the live package kept as {kept}")
        elif b64sha(open(kept, 'rb').read()) != live: raise Stop(f"{kept} exists and is not the live package")
        if dry: say(f"   (dry run) would update {len(todo)} functions and try the group"); continue
        failed = [n for n, ok in many(lambda n: (n, aws.put(n, new_data)), todo) if not ok]
        if failed: raise Stop(f"{len(failed)} function(s) did not take the new package (run this again; nothing is half-written): {', '.join(failed[:8])}")
        fresh = aws.functions(); on_new = sum(1 for n in names if fresh[n][0] == NEW)
        say(f"   {on_new} of {len(names)} functions report the new fingerprint")
        if on_new != len(names): raise Stop('not every function reports the new fingerprint: run this again')
        say('   the group tried for real:'); problems = try_group(aws, group, names)
        if problems:
            say('   THE TRY FAILED: ' + '; '.join(problems) + '\n   putting the group back...')
            old = open(kept, 'rb').read(); back = many(lambda n: (n, aws.put(n, old)), todo)
            raise Stop(f"{group} failed its try and was put back ({sum(1 for _, ok in back if ok)} of {len(todo)} restored)")
        for d in glob.glob(os.path.join(mirror, group + '-*')):                      # the mirror keeps one function per group
            for f in glob.glob(os.path.join(d, '*')): shutil.rmtree(f) if os.path.isdir(f) else os.remove(f)
            for f in build.FILES: shutil.copy(os.path.join(HERE, f), d)
        done.append(group)
    if not dry and not rollback and NEW != live:
        final = aws.functions(); everywhere = all(final[n][0] == NEW for g in G.GROUPS for n in final if re.fullmatch(re.escape(g) + r'-\d+', n))
        if everywhere and write_live:
            open(LIVE_FILE, 'w').write(f"{NEW} {datetime.date.today().isoformat()}\n"); say(f"\nevery group is on the new package: workers/live.txt written. Commit it.")
        elif not everywhere: say('\nnot every group is on the new package yet: workers/live.txt is left as it is until they all are (put the other groups in groups.txt and run again)')
    return done

def selftest():
    """The rules, played against a stand-in for AWS: nothing real is called and nothing is written outside a temporary folder"""
    import tempfile, io, contextlib
    tmp = tempfile.mkdtemp(); live_zip, new_zip = b'the live package', b'the new package'; live, NEW = b64sha(live_zip), b64sha(new_zip)
    class Fake:
        def __init__(self, odd=None, fail_try=False):
            self.code = {f"{g}-{i}": live_zip for g, v in G.GROUPS.items() for i in range(1, v[1] + 1)}; self.fail_try = fail_try
            if odd: self.code[odd] = b'something else'
        def functions(self): return {n: (b64sha(d), 'lambda_function.lambda_handler') for n, d in self.code.items()}
        def package(self, name): return self.code[name]
        def put(self, name, data): self.code[name] = data; return True
        def call(self, name, p):
            g = name.rpartition('-')[0]; m = G.MARKETS[G.GROUPS[g][2]]; batch = p.get('stock_batch')
            if batch is None: batch = [l.split(':')[1].split() for l in open(os.path.join(HERE, 'lists.txt')) if l.startswith(g + ':')][0][:10] if g in G.NUMBER_ONLY else []
            cur = 'XXX' if self.fail_try and g == 'stockiq-asia-5-5-worker' else m['currency']
            return {'success': True, 'stocks_processed': len(batch), 'results': [{'symbol': s, 'price': 1.0, 'currency': cur, 'score': 0.5, 'recommendation': 'HOLD', 'change_24h': 0.1} for s in batch]}
    def go(fake, wanted, **k):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            try: return run(fake, wanted, new_zip, live, backup=tmp, mirror=os.path.join(tmp, 'mirror'), write_live=False, **k), out.getvalue()
            except Stop as e: return 'STOP: ' + str(e), out.getvalue()
    every = list(G.GROUPS); checks = []
    f = Fake(); r, _ = go(f, every, dry=True); checks.append(('a dry run changes nothing', all(d == live_zip for d in f.code.values()) and not os.listdir(tmp)))
    f = Fake(); r, _ = go(f, every[:2]); checks.append(('two groups updated, the rest untouched', r == every[:2] and sum(1 for d in f.code.values() if d == new_zip) == sum(G.GROUPS[g][1] for g in every[:2])))
    checks.append(('the live package was kept once, and is it', os.listdir(tmp) and all(b64sha(open(os.path.join(tmp, x), 'rb').read()) == live for x in os.listdir(tmp) if x.endswith('.zip'))))
    r, _ = go(f, every); checks.append(('a second run finishes the rest and passes over what is done', r == every and all(d == new_zip for d in f.code.values())))
    r, _ = go(f, every[:1], rollback=True); checks.append(('putting one group back', sum(1 for d in f.code.values() if d == live_zip) == G.GROUPS[every[0]][1]))
    f = Fake(odd=every[3] + '-2'); r, _ = go(f, every[3:5]); checks.append(('a function with other code stops the run before its group is touched', str(r).startswith('STOP') and all(d != new_zip for d in f.code.values())))
    f = Fake(fail_try=True); r, _ = go(f, ['stockiq-asia-5-4-worker', 'stockiq-asia-5-5-worker', 'stockiq-europe-4-1-worker'])
    checks.append(('a group that fails its try is put back and the run stops', str(r).startswith('STOP') and all(f.code[f"stockiq-asia-5-5-worker-{i}"] == live_zip for i in range(1, 22)) and f.code['stockiq-asia-5-4-worker-1'] == new_zip and f.code['stockiq-europe-4-1-worker-1'] == live_zip))
    f = Fake(); del f.code[every[0] + '-1']; r, _ = go(f, every[:1]); checks.append(('a group with a function missing stops the run', str(r).startswith('STOP')))
    shutil.rmtree(tmp)
    for name, ok in checks: print('PASS' if ok else 'FAIL', name)
    sys.exit(0 if all(ok for _, ok in checks) else 1)

def main():
    if '--selftest' in sys.argv: selftest()
    pending = sys.argv[1] if len(sys.argv) > 1 else sys.exit('give the pending folder (see the top of this file)')
    dry = os.environ.get('DRY_RUN', 'false') == 'true'; rollback = os.environ.get('ROLLBACK', 'false') == 'true'
    try:
        if subprocess.run(['pgrep', '-f', r'bash .*/deploy-to-s3\.sh'], capture_output=True).returncode == 0 or subprocess.run(['pgrep', '-x', 'deploy-to-s3.sh'], capture_output=True).returncode == 0:
            raise Stop('the daily deploy is running; try again when it has finished')
        lines = [l.strip() for l in open(os.path.join(pending, 'groups.txt')) if l.strip() and not l.startswith('#')]
        wanted = list(G.GROUPS) if lines == ['all'] else lines
        for g in wanted:
            if g not in G.GROUPS: raise Stop(f"groups.txt names {g}, which is not in workers/groups.py")
        say(('DRY RUN: nothing will be changed\n' if dry else '') + ('PUTTING BACK the package that was live before\n' if rollback else '') + f"groups in this run: {', '.join(g.replace('stockiq-', '') for g in wanted)}")
        minute = datetime.datetime.now().minute
        if not dry and (8 <= minute <= 13 or 38 <= minute <= 43): raise Stop('it is within a few minutes of :10 or :40, when the autopilot reads the screeners: run this again in five minutes')
        dirty = [l for l in subprocess.run(['git', '-C', ROOT, 'status', '--porcelain', 'workers'], capture_output=True, text=True).stdout.splitlines() if not l.endswith('workers/live.txt')]
        if dirty and not rollback: raise Stop('workers/ has changes that are not committed: what is deployed must be what git holds\n' + '\n'.join(dirty))
        if os.path.exists(build.COORDINATOR) and open(os.path.join(HERE, 'lists.txt')).read() != build.lists_text(build.coordinator_lists()): raise Stop("workers/lists.txt is not the coordinator's Russell lists (python3 workers/build.py --lists, after reading the difference)")
        live = open(LIVE_FILE).read().split()[0]
        zip_path = os.path.join(pending, 'workers.zip'); build.build(zip_path)
        say(f"the package: {', '.join(zipfile.ZipFile(zip_path).namelist())}")
        run(Aws(), wanted, open(zip_path, 'rb').read(), live, dry=dry, rollback=rollback)
        say('\nFINISHED' + (' (dry run, nothing changed)' if dry else ''))
    except Stop as e:
        say(f"\nSTOPPED: {e}\nNothing further was changed."); sys.exit(1)

if __name__ == '__main__':
    main()
