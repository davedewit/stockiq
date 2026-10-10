import json, glob, re, importlib.util, io, contextlib, collections, csv, sys
spec = importlib.util.spec_from_file_location('coord', '/Users/dave/VSCODE/stockiq/lambda-sync/stockiq-screener-coordinator/lambda_function.py')
m = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
FLAG = re.compile(r'\bundefined\b|\bNaN\b|\bnan\b|\bNone\b|\[object Object\]|Unrated|\b(STRONG_BUY|MODERATE_BUY|MODERATE_SELL|STRONG_SELL|STRONG BUY|STRONG SELL|BUY|SELL|HOLD|AVOID|CONSIDER)\b|Take Profit|Stop Loss|Recommendation|Traceback')
for fn in sorted(glob.glob('res_*.json')):
    d = json.load(open(fn)); key = d['key']; res = d['results']; save = d.get('save') or {}
    listed = m.STOCK_UNIVERSES.get(key, [])
    got = {r.get('symbol') for r in res}
    missing = [s for s in listed if s not in got]
    dup = [s for s, c in collections.Counter(r.get('symbol') for r in res).items() if c > 1]
    dup_listed = [s for s, c in collections.Counter(listed).items() if c > 1]
    rep = save.get('report', ''); csvd = save.get('csvData', '')
    plain = re.sub(r'<[^>]*>', '', rep)
    flags = sorted(set(x.group(0) for x in FLAG.finditer(plain)))
    rows = list(csv.reader(io.StringIO(csvd))) if csvd else []
    badrows = [i for i, r in enumerate(rows[1:], 2) if len(r) != len(rows[0])] if rows else []
    csvflags = sorted(set(x.group(0) for x in FLAG.finditer(csvd) if x.group(0) not in ('None',))) if csvd else []
    zero = sum(1 for r in res if not r.get('price'))
    print(f"{key:14} returned {len(res):4}/{len(listed):4} listed | missing {len(missing):3} | dup results {len(dup)} | dup in list {len(dup_listed)} | zero-price {zero} | report {len(rep):6} chars flags={flags or 'none'} | csv rows {max(0,len(rows)-1)} bad rows {len(badrows)} flags={csvflags or 'none'} | saved as '{save.get('companyName')}'")
    if '-v' in sys.argv and missing: print('      missing:', ' '.join(missing[:40]), '...' if len(missing) > 40 else '')
