"""Who runs what: every screener worker group on AWS, how many functions it has, whether they all run one version of their
code, which groups run the same code as another, and which the site calls at all. Read-only.

   python3 check-tools/workers.py                  # the table, from the fingerprint AWS shows for each package
   python3 check-tools/workers.py --contents [DIR] # the honest count: downloads every package and compares the files inside it
   python3 check-tools/workers.py --diff           # how each group's code (the copy in lambda-sync/) differs from the S&P 100 worker's

Why it exists: on 11 Oct 2026 the owner asked whether the screeners "all share the same function". They did not, quite:
928 worker functions in 18 groups, the share screeners on seven copies of one program that had drifted apart. The table's
"100 DIFFERENT" for the Russell groups was misleading: a package's fingerprint changes with the dates inside the zip, and
those were one program zipped 300 times (--contents shows it). Since that day every share-screener worker runs the one
package built from workers/ in git (workers/build.py), so the 13 share groups show "one" and the same code as each other.
A new share-screener group: add its name to NAMES here. See site-overview.md section 8b, "The worker groups".
"""
import sys, re, json, glob, os, collections, subprocess
import boto3
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'workers')); import groups as G        # the share-screener groups: workers/groups.py
NAMES = dict({g: v[0] for g, v in G.GROUPS.items()}, **{'stockiq-option-7-1-worker': 'Crypto (540 coins)', 'stockiq-option-7-2-worker': 'Single coin'})
lam = boto3.Session(profile_name='default', region_name='us-east-1').client('lambda')
fns = [f for page in lam.get_paginator('list_functions').paginate() for f in page['Functions']]
groups = collections.defaultdict(list)
for f in fns:
    m = re.match(r'(.*-worker)-?(\d+)?$', f['FunctionName'])
    if m: groups[m.group(1)].append(f)
called = {}
try:
    urls = json.load(open(os.path.join(ROOT, 'lambda-url-mapping.json')))
    site = ''.join(open(p, errors='ignore').read() for p in [os.path.join(ROOT, '..', 'website', 'analysis-functions.js'), os.path.join(ROOT, '..', 'website', 'dashboard.html'),
                   os.path.join(ROOT, 'lambda-sync', 'stockiq-screener-coordinator', 'lambda_function.py'), os.path.join(ROOT, 'lambda-sync', 'stockiq-option-7-1-orchestrator', 'orchestrator.py')])
    for name, url in urls.items():
        m = re.match(r'(.*-worker)-?(\d+)?$', name)
        if m and isinstance(url, str) and url.startswith('http'): called[m.group(1)] = called.get(m.group(1), 0) + (url.split('//')[1].split('.')[0] in site)
except Exception as e:
    print('(which groups the site calls could not be worked out:', e, ')')
by_sha = collections.defaultdict(list)
for g, v in groups.items():
    for sha in {f['CodeSha256'] for f in v}: by_sha[sha].append(g)
print(f"{len(fns)} functions in all; {sum(len(v) for v in groups.values())} are workers, in {len(groups)} groups\n")
print(f"{'group':<28}{'screener':<38}{'functions':>9}  {'versions of its code':<22}{'called by the site':<20}same code as")
for g in sorted(groups):
    v = groups[g]; shas = {f['CodeSha256'] for f in v}
    same = sorted({o for sha in shas for o in by_sha[sha] if o != g}) if len(shas) == 1 else []
    print(f"{g.replace('stockiq-', ''):<28}{NAMES.get(g, '(not used)'):<38}{len(v):>9}  {('one' if len(shas) == 1 else str(len(shas)) + ' DIFFERENT'):<22}{(str(called.get(g, '?')) + ' of ' + str(len(v))):<20}{', '.join(s.replace('stockiq-', '') for s in same)}")
if '--diff' in sys.argv:
    base = glob.glob(os.path.join(ROOT, 'lambda-sync', 'stockiq-option-3-1-worker-*', '*.py'))[0]
    strip = lambda p: [l.rstrip() for l in open(p, errors='ignore')]
    import difflib
    print('\nlines that differ from the S&P 100 worker (the one copy lambda-sync/ keeps per group):')
    for d in sorted(glob.glob(os.path.join(ROOT, 'lambda-sync', '*worker-*'))):
        files = sorted(glob.glob(os.path.join(d, '*.py')), key=os.path.getsize)
        if not files or 'option-7-' in d: continue
        n = sum(1 for l in difflib.unified_diff(strip(base), strip(files[-1]), lineterm='', n=0) if l[:1] in '+-' and l[:3] not in ('+++', '---'))
        print(f"   {os.path.basename(d):<34}{n:>5}")
if '--contents' in sys.argv:
    # The honest count: a package's fingerprint changes with the dates of the files inside the zip, so 100 fingerprints can
    # be one program zipped 100 times. This downloads every worker's package (read-only; kept in the folder given after
    # --contents, or a temporary one) and compares the files inside it, and the settings each function runs with.
    import hashlib, zipfile, io, tempfile, urllib.request, concurrent.futures
    i = sys.argv.index('--contents')
    keep = sys.argv[i + 1] if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith('--') else tempfile.mkdtemp(prefix='workers-')
    os.makedirs(keep, exist_ok=True)
    def fetch(f):
        path = os.path.join(keep, f['FunctionName'] + '.zip')
        if not (os.path.exists(path) and base64sha(path) == f['CodeSha256']):
            for attempt in range(4):
                try:
                    data = urllib.request.urlopen(lam.get_function(FunctionName=f['FunctionName'])['Code']['Location'], timeout=60).read()
                    open(path, 'wb').write(data); break
                except Exception as e:
                    if attempt == 3: return f['FunctionName'], None, str(e)
        z = zipfile.ZipFile(path)
        return f['FunctionName'], {n: hashlib.sha256(z.read(n)).hexdigest()[:12] for n in sorted(z.namelist()) if not n.endswith('/')}, None
    def base64sha(path):
        import base64
        return base64.b64encode(hashlib.sha256(open(path, 'rb').read()).digest()).decode()
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        inside = {name: (files, err) for name, files, err in pool.map(fetch, [f for v in groups.values() for f in v])}
    json.dump({n: v[0] for n, v in inside.items()}, open(os.path.join(keep, '_contents.json'), 'w'), indent=0, sort_keys=True)
    print(f"\nwhat is inside the packages (kept in {keep}):")
    code_of = {}
    for g in sorted(groups):
        v = groups[g]; failed = [f['FunctionName'] for f in v if inside[f['FunctionName']][0] is None]
        got = [f for f in v if inside[f['FunctionName']][0] is not None]
        py = collections.Counter(tuple(sorted((n, h) for n, h in inside[f['FunctionName']][0].items() if n.endswith('.py'))) for f in got)
        other = collections.Counter(tuple(sorted((n, h) for n, h in inside[f['FunctionName']][0].items() if not n.endswith('.py'))) for f in got)
        conf = collections.Counter((f['Handler'], f['Runtime'], f['MemorySize'], f['Timeout'], len(f.get('Layers', [])), tuple(sorted(f.get('Environment', {}).get('Variables', {})))) for f in got)
        code_of[g] = py
        print(f"\n{g.replace('stockiq-', '')}  ({NAMES.get(g, 'not used')}; {len(v)} functions{'; NOT READ: ' + ', '.join(failed) if failed else ''})")
        print(f"   code: {len(py)} version(s)")
        for files, n in py.most_common(6): print(f"      {n:>4} x  " + ', '.join(f"{a} {b}" for a, b in files))
        print(f"   other files: {len(other)} version(s)")
        for files, n in other.most_common(4): print(f"      {n:>4} x  " + (', '.join(f"{a} {b}" for a, b in files)[:150] or '(none)'))
        print(f"   settings: {len(conf)} version(s)")
        for c, n in conf.most_common(6): print(f"      {n:>4} x  handler {c[0]}, {c[1]}, {c[2]} MB, {c[3]} s, {c[4]} layer(s), env {list(c[5])}")
