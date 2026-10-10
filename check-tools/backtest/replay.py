"""Replay the live S&P 500 screener worker (unchanged code) on every past trading day.
For each day D the worker is given exactly the prices it would have fetched that day (the previous 365 days,
nothing later) and its score for every stock is recorded. Output: scores.pkl"""
import importlib.util, io, contextlib, json, os, sys, pickle, time, datetime as dt, multiprocessing as mp, glob

WORKER = glob.glob('/Users/dave/VSCODE/stockiq/lambda-sync/stockiq-option-3-5-worker-*/lambda_function.py')[0]
DATA = {}          # symbol -> list of rows (as the worker builds them)
CAL = []           # trading days (SPY bar timestamps)
STATE = {}

def load():
    for fn in glob.glob('data/*.json'):
        sym = os.path.basename(fn)[:-5]
        r = json.load(open(fn))['chart']['result'][0]; q = r['indicators']['quote'][0]; rows = []
        for i, t in enumerate(r.get('timestamp') or []):
            if all(q[k][i] is not None for k in ('open', 'high', 'low', 'close', 'volume')):
                rows.append({'timestamp': t, 'open': float(q['open'][i]), 'high': float(q['high'][i]), 'low': float(q['low'][i]), 'close': float(q['close'][i]), 'volume': int(q['volume'][i]),
                             'day': dt.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')})
        DATA[sym] = rows
    CAL[:] = [r['day'] for r in DATA['SPY']]

def init():
    load()
    spec = importlib.util.spec_from_file_location('worker', WORKER); w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
    def get_stock_data(symbol, period='1y'):
        rows = DATA.get(symbol.upper()) or DATA.get(symbol)
        if not rows: return None
        day = STATE['day']; cutoff = STATE['cutoff']
        hi = STATE['hi'].get(symbol)
        if hi is None:      # index just past the last row on or before the as-of day
            lo_, hi_ = 0, len(rows)
            while lo_ < hi_:
                mid = (lo_ + hi_) // 2
                if rows[mid]['day'] <= day: lo_ = mid + 1
                else: hi_ = mid
            hi = lo_; STATE['hi'][symbol] = hi
        out = [r for r in rows[max(0, hi - 260):hi] if r['day'] > cutoff]       # the worker asks for the last 365 days (run after the close)
        if len(out) < 20: return None
        return out[-252:] if len(out) > 252 else out
    w.get_stock_data = get_stock_data
    real_ctx = w.get_market_context
    def get_market_context():
        if 'ctx' not in STATE: STATE['ctx'] = real_ctx()
        return STATE['ctx']
    w.get_market_context = get_market_context
    w.check_earnings_risk = lambda symbol: 'HIGH' if int(STATE['day'][5:7]) in (1, 4, 7, 10) else 'LOW'    # same rule, as-of month
    STATE['w'] = w

def run_day(args):
    day, universe = args
    w = STATE['w']; STATE.clear(); STATE['w'] = w
    STATE['day'] = day; STATE['hi'] = {}
    STATE['cutoff'] = (dt.datetime.strptime(day, '%Y-%m-%d') - dt.timedelta(days=365)).strftime('%Y-%m-%d')
    out = {}
    with contextlib.redirect_stdout(io.StringIO()):
        for s in universe:
            rows = DATA.get(s)
            if not rows: continue
            try:
                r = w.analyze_stock_advanced(s)
            except Exception:
                r = None
            if r and STATE['hi'].get(s) and rows[STATE['hi'][s] - 1]['day'] == day:      # only stocks that traded that day
                out[s] = (r['score'], r['recommendation'], r['price'])
    return day, out

if __name__ == '__main__':
    load()
    universe = [s for s in json.load(open('universe.json')) if s in DATA]
    first = 252                                   # the first year only feeds the indicators
    days = CAL[first:] if len(sys.argv) < 2 else CAL[first:first + int(sys.argv[1])]
    print(f'{len(universe)} stocks with data, {len(CAL)} trading days {CAL[0]}..{CAL[-1]}, replaying {len(days)} days from {days[0]}', flush=True)
    t0 = time.time(); scores = {}
    with mp.Pool(max(2, mp.cpu_count() - 2), initializer=init) as pool:
        for n, (day, out) in enumerate(pool.imap_unordered(run_day, [(d, universe) for d in days], chunksize=4)):
            scores[day] = out
            if n % 50 == 0: print(f'  {n}/{len(days)} days, {time.time() - t0:.0f}s', flush=True)
    pickle.dump({'scores': scores, 'universe': universe}, open('scores.pkl', 'wb'))
    print(f'REPLAY_DONE {len(scores)} days in {time.time() - t0:.0f}s; stocks scored per day: min {min(len(v) for v in scores.values())} max {max(len(v) for v in scores.values())}', flush=True)
