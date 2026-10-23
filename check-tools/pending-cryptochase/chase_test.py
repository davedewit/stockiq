"""The crypto worker before and after "a jump is not a reason to buy" (23 Oct 2026), on recorded answers of the price source.
    python3 chase_test.py <live lambda_function.py> <new lambda_function.py> <recorded.txt>"""
import sys, io, json, copy, contextlib, importlib.util, time
passed = failed = 0
def check(name, ok, detail=''):
    global passed, failed
    if ok: passed += 1; print('PASS', name)
    else: failed += 1; print('FAIL', name, '|', str(detail)[:300])
REC = json.load(open(sys.argv[3])); END = REC['end']
answers = dict(REC['answers'])
class Resp:
    def __init__(self, body): self.body = body; self.status_code = 200 if body and 'chart' in body else 404
    def json(self): return copy.deepcopy(self.body)
def fake_get(url, params=None, headers=None, timeout=None):
    sym = url.split('/chart/')[1].replace('-USD', ''); days = round((params['period2'] - params['period1']) / 86400)
    return Resp(answers.get(f'{sym}:{days}'))
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(mod)
    mod.requests.get = fake_get; return mod
time.time = lambda: END
old, new = load('w_old', sys.argv[1]), load('w_new', sys.argv[2])
def one(mod, sym):
    with contextlib.redirect_stdout(io.StringIO()): return mod.CryptoAnalytics().analyze_coin(sym, {})
coins = sorted({k.split(':')[0] for k, v in REC['answers'].items() if 'chart' in v and k.endswith(':90')})
SCOREISH = {'score', 'score_breakdown', 'signal', 'recommendation', 'confidence', 'action', 'strategy', 'profit_probability', 'risk_level', 'buy_limit', 'buy_stop', 'stop_loss', 'take_profit', 'position_size'}
for sym in coins:
    a, b = one(old, sym), one(new, sym)
    jumped = a.get('change_24h', 0) > 5 or a.get('change_7d', 0) > 20
    diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    if jumped:
        expect = (-4 if a['change_24h'] > 10 else -1 if a['change_24h'] > 5 else 0) + (-1 if a['change_7d'] > 20 else 0)
        check(f"{sym} (day {a['change_24h']:+.1f}%, week {a['change_7d']:+.1f}%): score {a['score']:+d} -> {b['score']:+d}, only the score's own fields differ",
              b['score'] - a['score'] == expect and set(diff) <= SCOREISH, [(k, a.get(k), b.get(k)) for k in diff if k not in SCOREISH][:3])
    else:
        check(f"{sym} (day {a['change_24h']:+.1f}%, week {a['change_7d']:+.1f}%): no jump, every figure the same", not diff, [(k, a.get(k), b.get(k)) for k in diff][:3])
# a made-up jump: BTC's last close 12% above the one before
jump = copy.deepcopy(REC['answers']['BTC:90']); cl = jump['chart']['result'][0]['indicators']['quote'][0]['close']
cl[-1] = cl[-2] * 1.12; answers['JUMP:90'] = jump
a, b = one(old, 'JUMP'), one(new, 'JUMP')
check('a made-up 12% day: +2 before, -2 now, and the breakdown says why', a['change_24h'] > 10 and b['score'] - a['score'] == -4 - (1 if a['change_7d'] > 20 else 0)
      and any('a jump: coins tend to fall back' in x for x in b['score_breakdown']), b.get('score_breakdown'))
print(f"\n{passed} passed, {failed} failed"); sys.exit(1 if failed else 0)
