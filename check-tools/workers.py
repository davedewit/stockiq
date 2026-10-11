"""Who runs what: every screener worker group on AWS, how many functions it has, whether they all run one version of their
code, which groups run the same code as another, and which the site calls at all. Read-only.

   python3 check-tools/workers.py            # the table
   python3 check-tools/workers.py --diff     # also: how each group's code (the copy in lambda-sync/) differs from the S&P 100 worker's

Why it exists: on 11 Oct 2026 the owner asked whether the screeners "all share the same function". They do not, quite:
928 worker functions in 18 groups, most groups on one version, the two Russell groups with a different file in every function
(each carries its own list of stocks), and small differences between markets that nobody had chosen (two ways of working
out RSI). See site-overview.md section 8b, "The worker groups".
"""
import sys, re, json, glob, os, collections, subprocess
import boto3
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = {'stockiq-option-3-1-worker': 'S&P 100', 'stockiq-option-3-2-worker': 'S&P 400+600', 'stockiq-option-3-4-worker': 'S&P 1500', 'stockiq-option-3-5-worker': 'Russell 1000 (its first 50: S&P 500)',
         'stockiq-option-3-6-worker': 'Russell 2000', 'stockiq-option-3-7-worker': 'NASDAQ 100', 'stockiq-option-3-8-worker': 'Dow 30', 'stockiq-asia-5-1-worker': 'ASX 50', 'stockiq-asia-5-2-worker': 'ASX 100',
         'stockiq-asia-5-3-worker': 'ASX 200', 'stockiq-asia-5-4-worker': 'ASX 300', 'stockiq-asia-5-5-worker': 'Nikkei 225', 'stockiq-europe-4-1-worker': 'FTSE 100', 'stockiq-option-7-1-worker': 'Crypto (540 coins)',
         'stockiq-option-7-2-worker': 'Single coin'}
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
