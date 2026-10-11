"""Builds the one package both trading-signals functions run, and prints its fingerprint (what AWS shows as CodeSha256).

    python3 signals/build.py [where to write the zip; default signals/signals.zip, which git ignores]
    python3 signals/build.py --list      # write sp100.txt again from the coordinator's S&P 100 list

The package: lambda_function.py (the code) and sp100.txt (the shares the auto-detect scans). The same input always gives
the same zip. The scan list must be the screener's own S&P 100 list: this stops if sp100.txt differs from
STOCK_UNIVERSES['3-100'] in lambda-sync/stockiq-screener-coordinator.
"""
import sys, os, ast, zipfile, hashlib, base64
HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ['lambda_function.py', 'sp100.txt']
COORDINATOR = os.path.join(os.path.dirname(HERE), 'lambda-sync', 'stockiq-screener-coordinator', 'lambda_function.py')

def coordinator_list():
    for node in ast.walk(ast.parse(open(COORDINATOR).read())):
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'STOCK_UNIVERSES' for t in node.targets):
            return ast.literal_eval(node.value)['3-100']
    raise SystemExit('STOCK_UNIVERSES not found in the coordinator')

def build(path):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o644 << 16; info.create_system = 3
            z.writestr(info, open(os.path.join(HERE, name), 'rb').read())
    return base64.b64encode(hashlib.sha256(open(path, 'rb').read()).digest()).decode()

if __name__ == '__main__':
    if '--list' in sys.argv:
        symbols = coordinator_list()
        open(os.path.join(HERE, 'sp100.txt'), 'w').write(' '.join(symbols) + '\n')
        print('sp100.txt written from the coordinator:', len(symbols), 'shares'); sys.exit()
    if os.path.exists(COORDINATOR):
        if open(os.path.join(HERE, 'sp100.txt')).read().split() != coordinator_list():
            raise SystemExit("STOPPED: signals/sp100.txt is not the coordinator's S&P 100 list. Run: python3 signals/build.py --list")
    else:
        print('(the coordinator is not in lambda-sync/: sp100.txt was not compared with it)')
    out = next((a for a in sys.argv[1:] if not a.startswith('--')), os.path.join(HERE, 'signals.zip'))
    print(build(out), out)
