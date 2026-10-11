"""The work of deploy.sh (read that first). One package for every share-screener worker, a group at a time."""
import os, sys, re, io, json, time, base64, hashlib, zipfile, shutil, glob, subprocess, urllib.request, datetime, concurrent.futures
import boto3, botocore.config
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
WORKERS = os.path.join(ROOT, 'workers'); MIRROR = os.path.join(ROOT, 'lambda-sync')
KEEP = '/Users/dave/VSCODE/backup/workers_before_onecode_20261011'
DRY = os.environ.get('DRY_RUN', 'false') == 'true'; ROLLBACK = os.environ.get('ROLLBACK', 'false') == 'true'
sys.path.insert(0, WORKERS); import build

# What each group ran when this was built (the files inside its package, by the first 12 characters of their sha256).
# A function with anything else is not touched and the run stops.
ASX = [{'lambda_function.py': 'd3a21a9124fe'}]; SP = [{'lambda_function.py': '1b36c3c53646'}]; NASDAQ = [{'lambda_function.py': '0603f71321f4', 'nasdaq100_stocks.json': '5e4a4a3d0dab'}]
WAS = {
    'stockiq-option-3-8-worker': NASDAQ, 'stockiq-option-3-7-worker': NASDAQ,
    'stockiq-option-3-1-worker': [{'advanced_lambda.py': '1b36c3c53646'}], 'stockiq-option-3-2-worker': SP, 'stockiq-option-3-4-worker': SP,
    'stockiq-option-3-5-worker': [{'lambda_function.py': 'fdd2ac2aa694', 'russell1000_stocks.json': '1f924c8ea34a'}],
    'stockiq-option-3-6-worker': [{'lambda_function.py': 'fde8402eb725', 'russell2000_stocks.json': '87cafb092fdc'}],
    'stockiq-asia-5-1-worker': ASX, 'stockiq-asia-5-2-worker': ASX, 'stockiq-asia-5-3-worker': ASX, 'stockiq-asia-5-4-worker': ASX, 'stockiq-asia-5-5-worker': ASX,
    'stockiq-europe-4-1-worker': [{'lambda_function.py': 'ec2cd960a7e4'}, {'lambda_function.py': 'e6d87870020b'}],
}
COUNT = {'stockiq-option-3-8-worker': 3, 'stockiq-option-3-7-worker': 10, 'stockiq-option-3-1-worker': 10, 'stockiq-option-3-2-worker': 100, 'stockiq-option-3-4-worker': 150,
         'stockiq-option-3-5-worker': 100, 'stockiq-option-3-6-worker': 200, 'stockiq-asia-5-1-worker': 5, 'stockiq-asia-5-2-worker': 10, 'stockiq-asia-5-3-worker': 20,
         'stockiq-asia-5-4-worker': 30, 'stockiq-asia-5-5-worker': 21, 'stockiq-europe-4-1-worker': 10}
TRY = {'stockiq-asia-5-1-worker': ['BHP.AX', 'CBA.AX', 'CSL.AX'], 'stockiq-asia-5-2-worker': ['BHP.AX', 'CBA.AX', 'CSL.AX'], 'stockiq-asia-5-3-worker': ['BHP.AX', 'CBA.AX', 'CSL.AX'],
       'stockiq-asia-5-4-worker': ['BHP.AX', 'CBA.AX', 'CSL.AX'], 'stockiq-asia-5-5-worker': ['7203.T', '6758.T', '9984.T'], 'stockiq-europe-4-1-worker': ['IMB.L', 'AZN.L', 'HSBA.L']}
CURRENCY = {'.AX': 'AUD', '.T': 'JPY', '.L': 'GBp'}
NUMBER_ONLY = ('stockiq-option-3-5-worker', 'stockiq-option-3-6-worker')        # the page calls these with a worker number and no stocks

lam = boto3.Session(profile_name='default', region_name='us-east-1').client('lambda', config=botocore.config.Config(retries={'max_attempts': 12, 'mode': 'adaptive'}, read_timeout=120))
def say(*a): print(*a, flush=True)
def stop(why): say(f"\nSTOPPED: {why}\nNothing further was changed."); sys.exit(1)
def b64sha(data): return base64.b64encode(hashlib.sha256(data).digest()).decode()
def inside(data):
    z = zipfile.ZipFile(io.BytesIO(data)); return {n: hashlib.sha256(z.read(n)).hexdigest()[:12] for n in z.namelist() if not n.endswith('/')}
def many(fn, items, threads=6):
    with concurrent.futures.ThreadPoolExecutor(threads) as pool: return list(pool.map(fn, items))

def settle(name, want, tries=40):
    """Wait until AWS has finished the update and reports the fingerprint wanted"""
    for _ in range(tries):
        c = lam.get_function_configuration(FunctionName=name)
        if c.get('LastUpdateStatus') == 'Successful' and c['CodeSha256'] == want: return True
        if c.get('LastUpdateStatus') == 'Failed': return False
        time.sleep(1.5)
    return False

def put(name, data):
    lam.update_function_code(FunctionName=name, ZipFile=data); return settle(name, b64sha(data))

def call(name, payload):
    r = lam.invoke(FunctionName=name, Payload=json.dumps(payload).encode()); out = json.loads(r['Payload'].read())
    if r.get('FunctionError') or out.get('statusCode') != 200: return {'success': False, 'error': str(out)[:300]}
    return json.loads(out['body'])

def try_group(group, names):
    """The group's first and last worker, run for real: a few stocks, and for the Russell groups a call with the number only"""
    batch = TRY.get(group, ['AAPL', 'MSFT', 'JPM']); problems = []
    for name in sorted({names[0], names[-1]}, key=names.index):
        r = call(name, {'stock_batch': batch, 'worker_id': 1}); rows = r.get('results') or []
        want = next((c for suffix, c in CURRENCY.items() if batch[0].endswith(suffix)), 'USD')
        ok = r.get('success') and len(rows) == len(batch) and all(x.get('currency') == want and isinstance(x.get('score'), (int, float)) and x.get('recommendation') and x.get('price', 0) > 0 for x in rows)
        say(f"      {name}: {len(rows)} of {len(batch)} analysed" + (': ' + ', '.join(f"{x['symbol']} {x['price']} {x['currency']} score {x['score']:+.1f} 24h {x['change_24h']:+.2f}%" for x in rows) if rows else f" ({r.get('error')})"))
        if not ok: problems.append(f"{name} did not answer as expected")
        empty = call(name, {'stock_batch': [], 'worker_id': 1})
        if not (empty.get('success') and empty.get('stocks_processed') == 0): problems.append(f"{name} sent an empty batch answered {str(empty)[:120]}")
    if group in NUMBER_ONLY:
        lists = {l.split(':')[0]: l.split(':')[1].split() for l in open(os.path.join(WORKERS, 'lists.txt'))}
        r = call(names[0], {'worker_id': 1, 'batch_size': 10}); got = [x['symbol'] for x in r.get('results') or []]
        say(f"      {names[0]} called with its number only: {r.get('stocks_processed')} taken from its list, {len(got)} analysed")
        if r.get('stocks_processed') != 10 or not set(got) <= set(lists[group][:10]) or len(got) < 8: problems.append('a call with the number only did not take the list\'s first ten')
    else:
        r = call(names[0], {'worker_id': 1})
        if r.get('stocks_processed') != 0: problems.append('a call with the number only processed stocks')
    return problems

def main():
    groups = [l.strip() for l in open(os.path.join(HERE, 'groups.txt')) if l.strip() and not l.startswith('#')]
    for g in groups:
        if g not in WAS: stop(f"groups.txt names {g}, which is not a share-screener group")
    say(('DRY RUN: nothing will be changed\n' if DRY else '') + ('PUTTING BACK the copies kept before the change\n' if ROLLBACK else '') + f"groups in this run: {', '.join(g.replace('stockiq-', '') for g in groups)}")
    minute = datetime.datetime.now().minute
    if not DRY and (8 <= minute <= 13 or 38 <= minute <= 43): stop('it is within a few minutes of :10 or :40, when the autopilot reads the screeners: run this again in five minutes')
    if not ROLLBACK:
        dirty = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain', 'workers'], capture_output=True, text=True).stdout.strip()
        if dirty: stop('workers/ has changes that are not committed: what is deployed must be what git holds\n' + dirty)
    new_path = os.path.join(HERE, 'workers.zip')
    if os.path.exists(build.COORDINATOR) and open(os.path.join(WORKERS, 'lists.txt')).read() != build.lists_text(build.coordinator_lists()): stop('workers/lists.txt is not the coordinator\'s Russell lists')
    NEW = build.build(new_path); new_data = open(new_path, 'rb').read()
    say(f"the package: {', '.join(zipfile.ZipFile(new_path).namelist())}; fingerprint {NEW}; from commit {subprocess.run(['git', '-C', ROOT, 'log', '-1', '--format=%h', '--', 'workers/stock_worker.py', 'workers/lists.txt', 'workers/lambda_function.py', 'workers/advanced_lambda.py'], capture_output=True, text=True).stdout.strip()}")
    listed = {f['FunctionName']: f for page in lam.get_paginator('list_functions').paginate() for f in page['Functions']}
    os.makedirs(KEEP, exist_ok=True)
    for group in groups:
        names = sorted((n for n in listed if re.fullmatch(re.escape(group) + r'-\d+', n)), key=lambda n: int(n.rsplit('-', 1)[1]))
        say(f"\n== {group} ({len(names)} functions)")
        if len(names) != COUNT[group]: stop(f"{group} has {len(names)} functions, {COUNT[group]} were expected")
        for n in names:
            if listed[n]['Handler'] not in ('lambda_function.lambda_handler', 'advanced_lambda.lambda_handler'): stop(f"{n} has the handler {listed[n]['Handler']}, which the package does not provide")

        if ROLLBACK:
            def back(n):
                path = os.path.join(KEEP, n + '.zip')
                if not os.path.exists(path): return n, 'no copy kept'
                data = open(path, 'rb').read()
                if listed[n]['CodeSha256'] == b64sha(data): return n, 'already the old copy'
                if DRY: return n, 'would be put back'
                return n, 'put back' if put(n, data) else 'FAILED'
            res = many(back, names); tally = {k: sum(1 for _, v in res if v == k) for k in sorted({v for _, v in res})}
            say(f"   {tally}")
            if any(v in ('FAILED', 'no copy kept') for _, v in res): stop('not every function could be put back: ' + ', '.join(n for n, v in res if v in ('FAILED', 'no copy kept'))[:400])
            continue

        todo = [n for n in names if listed[n]['CodeSha256'] != NEW]
        say(f"   already on the new package: {len(names) - len(todo)}; to update: {len(todo)}")
        def look(n):
            data = urllib.request.urlopen(lam.get_function(FunctionName=n)['Code']['Location'], timeout=60).read()
            return n, data, inside(data)
        got = many(look, todo, threads=8)
        odd = [(n, files) for n, data, files in got if files not in WAS[group]]
        if odd: stop(f"{len(odd)} function(s) of {group} hold other code than this was built against, e.g. {odd[0][0]}: {odd[0][1]}")
        say(f"   live code checked: every one of the {len(todo)} holds the copy this was built against")
        if DRY: say(f"   (dry run) would keep {len(todo)} packages in {KEEP} and update {len(todo)} functions"); continue
        for n, data, files in got:
            path = os.path.join(KEEP, n + '.zip')
            if not os.path.exists(path): open(path, 'wb').write(data)                 # never over a copy already kept
            elif inside(open(path, 'rb').read()) not in WAS[group]: stop(f"the copy kept for {n} is not the old code")
        res = many(lambda n: (n, put(n, new_data)), todo)
        failed = [n for n, ok in res if not ok]
        if failed: stop(f"{len(failed)} function(s) did not take the new package (run this again; nothing is half-written): {', '.join(failed[:8])}")
        fresh = {f['FunctionName']: f['CodeSha256'] for page in lam.get_paginator('list_functions').paginate() for f in page['Functions'] if f['FunctionName'] in names}
        on_new = sum(1 for n in names if fresh.get(n) == NEW)
        say(f"   {on_new} of {len(names)} functions report the new fingerprint")
        if on_new != len(names): stop('not every function reports the new fingerprint: run this again')
        say('   the group tried for real:')
        problems = try_group(group, names)
        if problems:
            say('   THE TRY FAILED: ' + '; '.join(problems) + '\n   putting the group back...')
            res = many(lambda n: (n, put(n, open(os.path.join(KEEP, n + '.zip'), 'rb').read())), todo)
            stop(f"{group} failed its try and was put back ({sum(1 for _, ok in res if ok)} of {len(todo)} restored)")
        for d in glob.glob(os.path.join(MIRROR, group + '-*')):                      # the mirror keeps one function per group
            for f in glob.glob(os.path.join(d, '*')):
                shutil.rmtree(f) if os.path.isdir(f) else os.remove(f)
            for f in build.FILES: shutil.copy(os.path.join(WORKERS, f), d)
        say('   mirror (lambda-sync/) updated')
    say('\nFINISHED' + (' (dry run, nothing changed)' if DRY else ''))

if __name__ == '__main__':
    main()
