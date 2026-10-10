import importlib.util, sys, json, io, contextlib, urllib.request, time, collections, re
real = urllib.request.urlopen
SAVE_HOST = 'nwdjnlcbtj34ywy6sgawmwhcx40ologt'
spec = importlib.util.spec_from_file_location('coord', '/Users/dave/VSCODE/stockiq/lambda-sync/stockiq-screener-coordinator/lambda_function.py')
m = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
class Resp:
    def __init__(s, b): s.b = b; s.status = 200
    def read(s, *a): return s.b
    def __enter__(s): return s
    def __exit__(s, *a): return False
captured = {}
def fake(req, *a, **k):
    url = req.full_url if hasattr(req, 'full_url') else str(req)
    if SAVE_HOST in url:
        captured['save'] = json.loads(req.data); return Resp(b'{"success": true}')
    return real(req, *a, **k)
urllib.request.urlopen = fake
keys = sys.argv[1:] or list(m.WORKER_URLS.keys())
summary = {}
for key in keys:
    option, sub = key.split('-', 1)
    captured.clear(); t0 = time.time(); buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            r = m.lambda_handler({'body': json.dumps({'option': option, 'subOption': sub, 'userId': 'claude-test@dewit.com.au'})}, None)
        body = json.loads(r['body']); res = body.get('results', []) or []
        log = buf.getvalue()
        failed = len(re.findall(r'Worker \d+ failed', log))
        fail_msgs = collections.Counter(re.sub(r'Worker \d+ failed: ', '', l)[:90] for l in log.splitlines() if 'failed' in l)
        json.dump({'key': key, 'results': res, 'save': captured.get('save')}, open(f'res_{key}.json', 'w'))
        summary[key] = dict(status=r['statusCode'], results=len(res), universe=body.get('universe_size'), listed=len(m.STOCK_UNIVERSES.get(key, [])), workers=len(m.WORKER_URLS.get(key, [])),
                            failed_workers=failed, fail_msgs=dict(fail_msgs.most_common(3)), saved_report=bool(captured.get('save')), secs=round(time.time() - t0, 1),
                            codes=dict(collections.Counter(x.get('recommendation') for x in res)), error=body.get('error'))
    except Exception as e:
        summary[key] = dict(status='EXCEPTION', error=repr(e)[:200], secs=round(time.time() - t0, 1))
    print(key, json.dumps(summary[key]), flush=True)
    json.dump(summary, open('summary.json', 'w'), indent=1)
print('DONE', flush=True)
