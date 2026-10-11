"""Builds the one package every share-screener worker runs, and prints its fingerprint (what AWS shows as CodeSha256).

    python3 workers/build.py [where to write the zip; default workers/workers.zip, which git ignores]
    python3 workers/build.py --lists      # write lists.txt again from the coordinator's lists (after a Russell list changed)

The package: stock_worker.py (the code), lambda_function.py and advanced_lambda.py (two lines each: the two handler names
the functions are set up with), lists.txt (the Russell 1000 and Russell 2000 lists, for the page's runs, which send a worker
number and no stocks). The same input always gives the same zip, so every function shows the same fingerprint.

The Russell lists must be the coordinator's (the background runs send its lists): this stops if lists.txt differs from
STOCK_UNIVERSES in lambda-sync/stockiq-screener-coordinator.
"""
import sys, os, ast, zipfile, hashlib, base64
HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ['stock_worker.py', 'lambda_function.py', 'advanced_lambda.py', 'lists.txt']
GROUPS = {'stockiq-option-3-5-worker': '3-5', 'stockiq-option-3-6-worker': '3-6'}      # the groups called with a worker number only
COORDINATOR = os.path.join(os.path.dirname(HERE), 'lambda-sync', 'stockiq-screener-coordinator', 'lambda_function.py')

def coordinator_lists():
    for node in ast.walk(ast.parse(open(COORDINATOR).read())):
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'STOCK_UNIVERSES' for t in node.targets):
            universes = ast.literal_eval(node.value)
            return {group: universes[key] for group, key in GROUPS.items()}
    raise SystemExit('STOCK_UNIVERSES not found in the coordinator')

def lists_text(lists):
    return ''.join(f"{group}: {' '.join(lists[group])}\n" for group in GROUPS)

def build(path):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o644 << 16; info.create_system = 3
            z.writestr(info, open(os.path.join(HERE, name), 'rb').read())
    return base64.b64encode(hashlib.sha256(open(path, 'rb').read()).digest()).decode()

if __name__ == '__main__':
    if '--lists' in sys.argv:
        open(os.path.join(HERE, 'lists.txt'), 'w').write(lists_text(coordinator_lists()))
        print('lists.txt written from the coordinator:', {g: len(v) for g, v in coordinator_lists().items()})
        sys.exit()
    if os.path.exists(COORDINATOR):
        if open(os.path.join(HERE, 'lists.txt')).read() != lists_text(coordinator_lists()):
            raise SystemExit('STOPPED: workers/lists.txt is not the coordinator\'s Russell lists. Run: python3 workers/build.py --lists (and read the difference first)')
    else:
        print('(the coordinator is not in lambda-sync/: lists.txt was not compared with it)')
    out = next((a for a in sys.argv[1:] if not a.startswith('--')), os.path.join(HERE, 'workers.zip'))
    print(build(out), out)
