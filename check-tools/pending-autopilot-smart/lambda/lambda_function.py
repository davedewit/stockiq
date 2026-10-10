"""stockiq-ai-trader: the practice portfolio's "AI autopilot". FAKE MONEY ONLY: it never places a real trade.

What it does, for each user who has switched it on:
  1. reads the latest screener results (the same data as the screener CSVs) from the screener coordinator;
  2. reviews what it bought earlier and sells by fixed rules (fell too far, rose enough, held long enough,
     signal turned negative);
  3. works out how much of the user's budget may be spent now (budget spread over the chosen period);
  4. shortlists stocks or coins from the top of the chosen screeners, filtered by the risk level;
  5. asks the AI model to choose among the shortlist and give a one-line reason (rules decide if it fails);
  6. records the practice buys in the user's practice portfolio (table stockiq-paper-portfolios) and a log.
The code, not the AI model, enforces every limit: budget, position size, which symbols may be bought.

Run by: EventBridge (hourly) for every user who is due, or a user's "Check in now" through the Function URL.
Settings, state, log and trade history: table stockiq-ai-trader (key userId). Who may use it: env
AI_TRADER_USERS (comma-separated emails, or * for everyone). Actions (POST JSON): get | save {settings} | run.

Markets: each screener belongs to a market (US, Australia, UK, Japan, coins). A scheduled check-in only acts
on the markets that are open at that moment, and each market keeps its own "last checked" time, so a user with
US and Australian screeners is checked in both sessions. Shares outside the US are bought in their own
currency and valued in US dollars at the day's exchange rate.

Learning from its own results: every holding it buys is remembered with the figures it was bought on. When
the holding is sold (by a rule, or by the user), the result goes into `history`: change, the S&P 500 fund over
the same days, how long, why it was sold. From that history the code builds a scorecard (by screener, by exit
reason, by who chose, by rank and RSI band); rests a screener whose recent trades have clearly lagged the
market; and, every few closed trades, asks the AI model to write short notes on what the record shows. The
scorecard and notes are shown on the dashboard and given to the model at each decision. They inform the choice
among the shortlist only: every limit is still enforced by this code. With few trades the record is mostly
chance, so nothing adapts until a group has MIN_SAMPLE trades.

Improving its own rules (bounded): every TUNE_BATCH finished trades it looks back over its record for ONE change
to one of its own rules (TUNABLE: loss limit, gain mark, how much of a gain it gives back, how far down a ranking
it buys, the highest RSI it buys at) that would have done better in hindsight, and then TRIES it beside the
current rule over the same days (every second buy for a selling rule; the two groups of buys for a buying rule).
After TUNE_GROUP trades each way it keeps the change only if that group did clearly better; otherwise the rule
stays as it was. Each step is emailed to the account's address and listed on the dashboard. It changes nothing
else: not the budget, not the user's settings, not any code. FAKE MONEY ONLY.

The same rows are also kept, 45 minutes at a time, as `_snapshot#<key>` items so that several users (or a
check-in and a "Check in now") do not run the same screener twice."""
import json
import math
import os
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

SETTINGS_TABLE = 'stockiq-ai-trader'
PORTFOLIO_TABLE = 'stockiq-paper-portfolios'
COORDINATOR_URL = 'https://ls6j5jqwl5iitwjt5va3jd6mbm0zhgyr.lambda-url.us-east-1.on.aws/'
PRICE_URL = 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/?symbol='
STARTING_CASH = 100000
BENCHMARK = 'SPY'

# key (the coordinator's own key): (name shown, coordinator option, subOption, kind, market, group shown)
SCREENERS = {
    '3-8': ('Dow 30', '3', '8', 'stock', 'us', 'US shares'),
    '3-100': ('S&P 100', '3', '100', 'stock', 'us', 'US shares'),
    '3-7': ('NASDAQ 100', '3', '7', 'stock', 'us', 'US shares'),
    '3-3': ('S&P 500', '3', '3', 'stock', 'us', 'US shares'),
    '3-2': ('S&P 400+600 (mid and small)', '3', '2', 'stock', 'us', 'US shares'),
    '3-4': ('S&P 1500', '3', '4', 'stock', 'us', 'US shares'),
    '3-5': ('Russell 1000', '3', '5', 'stock', 'us', 'US shares'),
    '3-6': ('Russell 2000 (small)', '3', '6', 'stock', 'us', 'US shares'),
    '4-50': ('ASX 50', '4', '50', 'stock', 'au', 'Australian shares'),
    '4-100': ('ASX 100', '4', '100', 'stock', 'au', 'Australian shares'),
    '4-200': ('ASX 200', '4', '200', 'stock', 'au', 'Australian shares'),
    '4-300': ('ASX 300', '4', '300', 'stock', 'au', 'Australian shares'),
    '5-ftse100': ('UK FTSE 100', '5', 'ftse100', 'stock', 'uk', 'UK shares'),
    '5-nikkei225': ('Japan Nikkei 225', '5', 'nikkei225', 'stock', 'jp', 'Japanese shares'),
    '7-1': ('Crypto (top coins)', '7', '1', 'crypto', 'crypto', 'Coins'),
}
# When each share market is taken to be open, in minutes of the day UTC, Monday to Friday. Each window sits
# inside the real trading hours in both summer and winter time; coins trade all the time.
MARKET_HOURS = {'us': (14 * 60 + 35, 19 * 60 + 55), 'au': (5, 4 * 60 + 55), 'jp': (5, 5 * 60 + 55), 'uk': (8 * 60 + 5, 15 * 60 + 25)}
MARKET_NAMES = {'us': 'US', 'au': 'Australian', 'uk': 'UK', 'jp': 'Japanese', 'crypto': 'coin'}
# What the risk slider changes. positions: how many holdings the budget is split across. top: how far down
# each screener's ranking it may buy. max_rsi / max_move30: leaves out stocks that have already run hard.
# stop / take: sells when a holding is down / up this much. crypto: largest share of the budget in coins.
RISK = {
    1: dict(name='Cautious',    positions=12, top=5,  max_rsi=68,  max_move30=20,   stop=-5,  take=8,  crypto=0.0),
    2: dict(name='Careful',     positions=10, top=8,  max_rsi=72,  max_move30=30,   stop=-7,  take=12, crypto=0.0),
    3: dict(name='Balanced',    positions=8,  top=10, max_rsi=76,  max_move30=45,   stop=-10, take=18, crypto=0.25),
    4: dict(name='Bold',        positions=6,  top=15, max_rsi=82,  max_move30=70,   stop=-14, take=28, crypto=0.5),
    5: dict(name='Adventurous', positions=4,  top=20, max_rsi=101, max_move30=1e9,  stop=-20, take=45, crypto=1.0),
}
EVERY_HOURS = (0.5, 1, 3, 6, 12, 24)        # how often it may check in; the schedule runs every 30 minutes
HOLD_HOURS = (0.5, 1, 3, 6, 12, 24, 48, 120, 240, 480, 1440)
HOLD_DAYS = tuple(h / 24 for h in HOLD_HOURS)   # the longest it keeps a holding, in days (30 minutes to 60 days)
SLOT_MINUTES = (10, 40)                     # minutes of the hour at which EventBridge runs it: cron(10,40 * * * ? *)
GRACE = timedelta(minutes=5)                # a check-in a little early still counts as "the time is up"
DEFAULTS = dict(enabled=False, risk=3, budgetUsd=10000, periodDays=10, everyHours=24, maxHoldDays=20, screeners=[])   # no screener until the user picks one
POSITIVE = {'STRONG BUY', 'BUY', 'MODERATE BUY', 'CONSIDER'}
NEGATIVE = {'STRONG SELL', 'SELL', 'MODERATE SELL', 'AVOID'}
MAX_BUYS_PER_CHECK = 3
MIN_TRADE_USD = 25
LOG_KEEP = 80
RUN_NOW_COOLDOWN_MIN = 10
SNAPSHOT_MINUTES = 20            # how long a screener's results are reused (shorter than the 30 minutes between check-ins)
SNAPSHOT_FULL_ROWS = 150         # rows kept in full in the stored copy; the rest keep score, signal and rank only
HISTORY_KEEP = 300               # closed trades remembered per user
MIN_SAMPLE = 8                   # a group needs this many closed trades before anything is concluded from it
REST_BELOW = -1.5                # a screener rests when its recent trades average this far (%) behind the market ...
REST_LOOKBACK = 12               # ... over its last this-many trades
REST_DAYS = 14
LESSONS_EVERY = 5                # ask the AI model for fresh notes after this many more closed trades
TRAIL_ARM = 0.5                  # once a holding has been up this share of the gain mark, part of the gain is protected:
for _rule in RISK.values():
    _rule['trail'] = 0.5         # it is sold when it has given back this share of its best gain
FADE = 5                         # sold when it has slipped below this many times the level's ranking limit with half its score
# What the autopilot may change about its own rules, and how far (lowest, highest). It never changes anything else.
TUNABLE = {'stop': (-30.0, -1.5), 'take': (2.0, 80.0), 'trail': (0.2, 0.8), 'top': (3, 30), 'max_rsi': (45, 101)}
EXIT_RULES = ('stop', 'take', 'trail')   # selling rules: a trial uses every second buy. 'top' and 'max_rsi' decide what is bought
TUNE_BATCH = 20                  # finished trades between reviews of its own rules
TUNE_GROUP = 10                  # a trial is judged once this many trades have finished with the change, and as many without
TUNE_MIN_GAIN = 0.2              # in hindsight a change must look worth this many percentage points a trade to be tried
TUNE_LOOKBACK = 60               # finished trades a review looks back over
TUNE_GIVE_UP_DAYS = 30           # a trial that cannot fill both groups ends after this long, unchanged
WATCH_KEEP = 40                  # sold holdings whose later price is still to be looked up ("what it did after it was sold")
MAIL_FROM = 'StockIQ autopilot <autopilot@stockiq.tech>'
SIGNAL_LABELS = {'STRONG BUY': 'Strongly positive', 'BUY': 'Positive', 'MODERATE BUY': 'Slightly positive', 'CONSIDER': 'Slightly positive',
                 'HOLD': 'Mixed', 'NEUTRAL': 'Mixed', 'MODERATE SELL': 'Slightly negative', 'AVOID': 'Slightly negative',
                 'SELL': 'Negative', 'STRONG SELL': 'Strongly negative'}

_db = None


def db():
    global _db
    if _db is None:
        _db = boto3.resource('dynamodb', region_name='us-east-1')
    return _db


def respond(status, body):
    return {'statusCode': status, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(body)}


def iso(t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_time(value):
    try:
        return datetime.strptime(str(value)[:19], '%Y-%m-%dT%H:%M:%S')
    except (ValueError, TypeError):
        return None


def span_text(days):
    """A length of time in plain words: 30 minutes, 3 hours, 5 days."""
    hours = days * 24
    if hours < 0.75:
        return f"{round(hours * 60)} minutes"
    if hours < 23.5:
        return f"{round(hours)} hour{'' if round(hours) == 1 else 's'}"
    return f"{round(days)} day{'' if round(days) == 1 else 's'}"


def every_text(hours):
    return 'every 30 minutes' if hours < 1 else 'every hour' if hours == 1 else f"every {hours:g} hours"


def allowed(user_id):
    listed = [u.strip().lower() for u in os.environ.get('AI_TRADER_USERS', '').split(',') if u.strip()]
    return '*' in listed or str(user_id).lower() in listed


def code(value):
    return str(value or '').replace('_', ' ').strip().upper()


def num(value, default=0.0):
    try:
        f = float(value)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


# ------------------------------------------------------------------------------------------------ settings
def clean_settings(raw, user_id):
    raw = raw if isinstance(raw, dict) else {}
    out = dict(DEFAULTS)
    out['enabled'] = bool(raw.get('enabled')) and allowed(user_id)
    out['risk'] = int(min(5, max(1, round(num(raw.get('risk'), DEFAULTS['risk'])))))
    out['budgetUsd'] = float(min(STARTING_CASH * 10, max(100, round(num(raw.get('budgetUsd'), DEFAULTS['budgetUsd'])))))
    out['periodDays'] = int(min(90, max(1, round(num(raw.get('periodDays'), DEFAULTS['periodDays'])))))
    every = num(raw.get('everyHours'), DEFAULTS['everyHours'])
    out['everyHours'] = next((h for h in EVERY_HOURS if abs(h - every) < 1e-6), DEFAULTS['everyHours'])
    hold = num(raw.get('maxHoldDays'), DEFAULTS['maxHoldDays'])
    out['maxHoldDays'] = next((d for d in HOLD_DAYS if abs(d - hold) < 1e-6), DEFAULTS['maxHoldDays'])
    chosen = [k for k in (raw.get('screeners') or []) if k in SCREENERS]
    out['screeners'] = sorted(set(chosen))                 # may be empty: it then waits until one is chosen
    return out


def load_item(user_id):
    item = db().Table(SETTINGS_TABLE).get_item(Key={'userId': user_id}).get('Item')
    data = json.loads(item['data']) if item else {}
    return {'settings': clean_settings(data.get('settings'), user_id), 'state': data.get('state') or {}, 'log': data.get('log') or [],
            'history': data.get('history') or []}


def save_item(user_id, record):
    record['log'] = record['log'][-LOG_KEEP:]
    record['history'] = record.get('history', [])[-HISTORY_KEEP:]
    db().Table(SETTINGS_TABLE).put_item(Item={
        'userId': user_id, 'data': json.dumps(record), 'enabled': bool(record['settings']['enabled']),
        'updatedAt': iso(datetime.utcnow())})


# ------------------------------------------------------------------------------------------------ outside data
def http_json(url, payload=None, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


def fetch_snapshot(key):
    """Latest results of one screener, best score first. No userId is sent, so the coordinator saves nothing."""
    _name, option, sub, kind = SCREENERS[key][:4]
    body = http_json(COORDINATOR_URL, {'option': option, 'subOption': sub}, timeout=240)
    rows = []
    for position, r in enumerate(body.get('results') or []):
        symbol = str(r.get('symbol') or '').upper()
        price = num(r.get('price') or r.get('current_price'))
        if not symbol or price <= 0:
            continue
        lookup = (str(r.get('yahoo_ticker') or symbol).upper() + '-USD') if kind == 'crypto' else symbol
        rows.append({
            'symbol': lookup, 'label': (symbol + '-USD') if kind == 'crypto' else symbol, 'kind': kind, 'screener': key,
            'price': price, 'score': num(r.get('score')), 'signal': code(r.get('recommendation')),
            'rsi': num(r.get('rsi')), 'd1': num(r.get('change_24h')), 'd7': num(r.get('change_7d')), 'd30': num(r.get('change_30d')),
            'volume': num(r.get('volume_ratio'), 1.0), 'from_high': num(r.get('distance_from_52w_high')),
            'macd': str(r.get('macd_signal') or '')[:40], 'position': position,
        })
    rows.sort(key=lambda x: (-x['score'], x['position']))
    for rank, row in enumerate(rows, 1):
        row['rank'] = rank
    return rows


def get_snapshot(key, now=None):
    """A screener's results, reusing the stored copy while it is fresh."""
    now = now or datetime.utcnow()
    table = db().Table(SETTINGS_TABLE)
    try:
        item = table.get_item(Key={'userId': f'_snapshot#{key}'}).get('Item')
        at = parse_time(item.get('at')) if item else None
        if at and timedelta(0) <= now - at <= timedelta(minutes=SNAPSHOT_MINUTES):
            kept = json.loads(item['data'])
            kind = SCREENERS[key][3]
            rest = [{'symbol': s, 'label': s, 'kind': kind, 'screener': key, 'price': 0.0, 'score': v[0], 'signal': v[1], 'rank': v[2],
                     'rsi': 0.0, 'd1': 0.0, 'd7': 0.0, 'd30': 0.0, 'volume': 1.0, 'from_high': 0.0, 'macd': '', 'position': v[2]} for s, v in kept['rest'].items()]
            return kept['top'] + sorted(rest, key=lambda r: r['rank'])
    except Exception as e:
        print(f'stored snapshot {key} not used: {type(e).__name__}')
    rows = fetch_snapshot(key)
    if rows:
        try:
            compact = {'top': rows[:SNAPSHOT_FULL_ROWS], 'rest': {r['symbol']: [r['score'], r['signal'], r['rank']] for r in rows[SNAPSHOT_FULL_ROWS:]}}
            table.put_item(Item={'userId': f'_snapshot#{key}', 'data': json.dumps(compact), 'at': iso(now)})
        except Exception as e:
            print(f'snapshot {key} not stored: {type(e).__name__}')
    return rows


def market_of(screener_key):
    return SCREENERS[screener_key][4] if screener_key in SCREENERS else 'us'


def market_open(market, now):
    if market == 'crypto':
        return True
    start, end = MARKET_HOURS[market]
    return now.weekday() < 5 and start <= now.hour * 60 + now.minute <= end


FX_DIRECT = ('AUD', 'GBP', 'EUR', 'NZD')      # quoted as dollars per unit. Others (yen ...) are quoted per dollar and turned over,
                                              # because their per-unit quote is rounded too coarsely (JPYUSD=X is 0.0063)


def fx_pair(currency):
    """(price symbol, divisor, turn over?) to get US dollars for one unit of `currency`. London prices are pence.
    The same rule is in website/practice-portfolio.js (fxFor): keep them alike, or holdings are valued differently."""
    if not currency or currency == 'USD':
        return None, 1, False
    minor = {'GBp': 'GBP', 'GBX': 'GBP', 'ZAc': 'ZAR', 'ILA': 'ILS'}.get(currency)
    base = (minor or currency).upper()
    return (base + 'USD=X', 100 if minor else 1, False) if base in FX_DIRECT else ('USD' + base + '=X', 100 if minor else 1, True)


def usd_rate(currency, quote, known):
    """US dollars for one unit of `currency`, or None if the rate cannot be found. `known` remembers rates within a check-in."""
    pair, divisor, turn = fx_pair(currency)
    if pair is None:
        return 1.0
    if pair not in known:
        q = quote(pair)
        known[pair] = q['price'] if q and q.get('price', 0) > 0 else None
    if not known[pair]:
        return None
    return (1 / known[pair] if turn else known[pair]) / divisor


def fetch_quote(symbol):
    try:
        meta = http_json(PRICE_URL + urllib.parse.quote(symbol), timeout=20)['chart']['result'][0]['meta']
        price = num(meta.get('regularMarketPrice'))
        if price <= 0:
            return None
        return {'price': price, 'currency': meta.get('currency') or 'USD', 'name': meta.get('longName') or meta.get('shortName') or ''}
    except Exception:
        return None


def ask_model(prompt):
    """The AI model's choice among the shortlist, as a dict, or None if it cannot be reached."""
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        return None
    try:
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=json.dumps({'model': 'gpt-4o-mini', 'temperature': 0.3, 'max_tokens': 500,
                             'response_format': {'type': 'json_object'},
                             'messages': [{'role': 'system', 'content': prompt['system']}, {'role': 'user', 'content': prompt['user']}]}).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'})
        with urllib.request.urlopen(req, timeout=40) as response:
            return json.loads(json.loads(response.read().decode())['choices'][0]['message']['content'])
    except Exception as e:
        print(f'AI model not used: {type(e).__name__}')
        return None


# ------------------------------------------------------------------------------------------------ decisions
def ai_holdings(portfolio):
    return [h for h in portfolio['holdings'] if h.get('by') == 'ai']


def tune_of(state):
    """Where the autopilot keeps what it has changed about its own rules, its running trial and the past ones."""
    tune = state.setdefault('tune', {})
    for key, empty in (('values', {}), ('past', []), ('trial', None), ('mark', 0)):
        tune.setdefault(key, empty)
    return tune


def bounded(param, value):
    low, high = TUNABLE[param]
    value = min(high, max(low, num(value, low)))
    return int(round(value)) if param in ('top', 'max_rsi') else round(value, 2 if param == 'trail' else 1)


def rules_for(settings, state=None):
    """The risk level's rules, with whatever the autopilot has changed about itself for that level."""
    rules = dict(RISK[settings['risk']])
    own = (((state or {}).get('tune') or {}).get('values') or {}).get(str(settings['risk'])) or {}
    for param, value in own.items():
        if param in TUNABLE:
            rules[param] = bounded(param, value)
    return rules


def live_trial(settings, state):
    """The trial of a changed rule that is running for the current risk level, or None."""
    trial = ((state or {}).get('tune') or {}).get('trial')
    return trial if trial and trial.get('risk') == settings['risk'] else None


def own_rules(rules, facts, trial):
    """The rules one holding is sold by: in a trial of a selling rule, every second buy follows the changed rule."""
    if trial and facts and facts.get('x') == trial.get('id') and trial.get('param') in EXIT_RULES:
        return dict(rules, **{trial['param']: trial['new'] if facts.get('v') == 'new' else trial['old']})
    return rules


def review_sells(portfolio, settings, snapshots, quotes, now, rates=None, only_markets=None, kinds=None, rules=None, opened=None, trial=None, info=None):
    """Rule-based: which of the AI's own holdings to sell now, and why. Returns [(holding, price, reason)].
    The change is measured in US dollars, as the dashboard shows it. `kinds` (a dict) receives the kind of exit and
    `info` the figures at the sale. `opened` (state['open']) is where each holding's best and worst change so far is kept."""
    level = rules or RISK[settings['risk']]
    sells = []
    for h in ai_holdings(portfolio):
        if only_markets is not None and market_of(h.get('screener')) not in only_markets:
            continue                                        # its market is closed: leave it until it opens
        quote = quotes.get(h['symbol'])
        if not quote:
            continue
        rate = 1.0 if h.get('currency', 'USD') == 'USD' else (rates or {}).get(h['symbol'])
        if not rate:
            continue
        change = (quote['price'] * rate / (h['buyPrice'] * h.get('buyFx', 1)) - 1) * 100
        bought = parse_time(h.get('boughtAt')) or now
        days = (now - bought).total_seconds() / 86400
        row = next((r for r in snapshots.get(h.get('screener'), []) if r['symbol'] == h['symbol']), None)
        seen = (opened or {}).get(h['id'])
        if seen is not None:                                # its best and worst so far, as seen at check-ins
            seen['peak'] = round(max(num(seen.get('peak'), change), change), 2)
            seen['low'] = round(min(num(seen.get('low'), change), change), 2)
        peak = seen['peak'] if seen is not None else change
        rules = own_rules(level, seen, trial)
        reason = kind = None
        if change <= rules['stop']:
            kind, reason = 'stop', f"Down {abs(change):.1f}% since it was bought: past the {rules['stop']:g}% limit for the {rules['name']} level"
        elif change >= rules['take']:
            kind, reason = 'take', f"Up {change:+.1f}% since it was bought: reached the +{rules['take']:g}% mark for the {rules['name']} level"
        elif peak >= rules['take'] * TRAIL_ARM and change <= peak * (1 - rules['trail']):
            kind, reason = 'trail', f"Was up {peak:+.1f}% at its best and has slipped back to {change:+.1f}%: sold to keep part of the gain"
        elif now - bought >= timedelta(days=settings['maxHoldDays']) - GRACE:
            kind, reason = 'time', f"Held {span_text(days)}, the longest this autopilot keeps a holding ({change:+.1f}%)"
        elif row and (row['signal'] in NEGATIVE or row['score'] < 0):
            kind, reason = 'signal', f"Its screener signal turned negative (score {row['score']:+.1f}, rank {row['rank']}); {change:+.1f}% since it was bought"
        elif row and seen is not None and row['rank'] > rules['top'] * FADE and row['score'] < num(seen.get('score')) / 2:
            kind, reason = 'fade', (f"Slipped to rank {row['rank']} in its screener with less than half the score it was bought on "
                                    f"(score {row['score']:+.1f}, was {num(seen.get('score')):+.1f}); {change:+.1f}% since it was bought")
        if reason:
            sells.append((h, quote['price'], reason))
            if kinds is not None:
                kinds[h['id']] = kind
            if info is not None:
                info[h['id']] = {'kind': kind, 'change': round(change, 2), 'peak': round(peak, 2), 'low': round(num((seen or {}).get('low'), change), 2),
                                 'days': days, 'rank': row['rank'] if row else None, 'score': row['score'] if row else None,
                                 'signal': row['signal'] if row else None, 'stop': rules['stop'], 'take': rules['take'], 'trail': rules['trail']}
    return sells


def allowance(portfolio, settings, state, now):
    """How many practice dollars may be put in at this check-in."""
    invested = sum(h['costUsd'] for h in ai_holdings(portfolio))
    started = parse_time(state.get('startedAt')) or now
    elapsed_hours = max(0.0, (now - started).total_seconds() / 3600)
    # the budget is released in equal steps, one per check-in, over the chosen period ...
    steps = int(elapsed_hours // settings['everyHours']) + 1
    pace = settings['budgetUsd'] * min(1.0, steps * settings['everyHours'] / (settings['periodDays'] * 24))
    # ... rounded up to whole positions, so the first check-in can always buy one
    size = settings['budgetUsd'] / RISK[settings['risk']]['positions']
    pace_cap = min(settings['budgetUsd'], math.ceil(pace / size - 1e-9) * size)
    return max(0.0, min(portfolio['cash'], settings['budgetUsd'] - invested, pace_cap - invested)), invested


def next_release(settings, state, invested, now):
    """When the next holding's worth of the budget is released (the same steps as allowance()), or None if it all is."""
    started = parse_time(state.get('startedAt')) or now
    positions = RISK[settings['risk']]['positions']
    size = settings['budgetUsd'] / positions
    done = int(max(0.0, (now - started).total_seconds() / 3600) // settings['everyHours']) + 1
    for step in range(done + 1, math.ceil(settings['periodDays'] * 24 / settings['everyHours']) + 2):
        pace = settings['budgetUsd'] * min(1.0, step * settings['everyHours'] / (settings['periodDays'] * 24))
        if min(settings['budgetUsd'], math.ceil(pace / size - 1e-9) * size) - invested >= size - 0.01 * positions:
            return started + timedelta(hours=(step - 1) * settings['everyHours'])
    return None


def shortlist(portfolio, settings, snapshots, now, rules=None, trial=None):
    """Candidates from the top of each screener in `snapshots` that the user chose, filtered by the risk level."""
    rules = dict(rules or RISK[settings['risk']])
    if trial and trial.get('param') in ('top', 'max_rsi'):  # a trial of a buying rule: buy by the wider of the two, compare the groups
        rules[trial['param']] = max(trial['old'], trial['new'])
    held = {h['symbol'] for h in ai_holdings(portfolio)}
    # not straight back into something it has just sold: two days, or twice the holding time when that is shorter
    wait = timedelta(days=min(2.0, 2 * settings['maxHoldDays']))
    recent = {h['symbol'] for h in portfolio.get('closed', []) if h.get('by') == 'ai'
              and (parse_time(h.get('soldAt')) or datetime.min) > now - wait}
    best = {}
    for key in settings['screeners']:
        for row in snapshots.get(key, [])[:rules['top']]:
            if row['kind'] == 'crypto' and rules['crypto'] <= 0:
                continue
            if row['score'] <= 0 or row['signal'] not in POSITIVE or row['symbol'] in held or row['symbol'] in recent:
                continue
            if row['rsi'] >= rules['max_rsi'] or abs(row['d30']) > rules['max_move30']:
                continue
            if row['kind'] == 'crypto' and (row['rsi'] <= 0 or row['d7'] == row['d30']):
                continue                                    # a coin with too little price history to judge
            if row['symbol'] not in best or row['rank'] < best[row['symbol']]['rank']:
                best[row['symbol']] = row
    # by place in its own screener, not raw score: the screeners' scores are on different scales
    return sorted(best.values(), key=lambda r: (r['rank'], -r['score']))


def build_prompt(settings, candidates, holdings_view, count, memory=''):
    rules = RISK[settings['risk']]
    lines = [f"{c['label']} | {SCREENERS[c['screener']][0]} rank {c['rank']} | score {c['score']:+.1f} | RSI {c['rsi']:.0f} | "
             f"1 day {c['d1']:+.1f}% | 7 days {c['d7']:+.1f}% | 30 days {c['d30']:+.1f}% | volume {c['volume']:.1f}x normal"
             + (f" | {c['from_high']:+.0f}% from 52-week high" if c['kind'] == 'stock' else '') for c in candidates]
    system = ("You are the decision step of a paper-trading simulation on StockIQ. All money is fake and no real trade is placed. "
              "Choose which candidates the practice portfolio buys now. Choose ONLY from the candidates listed, each at most once. "
              "Weigh the data given: the screener score and rank, whether the recent rise looks stretched (high RSI, a very large "
              "30-day move), volume, and variety against what is already held. Each reason must name the two or three figures you relied on (for example \"rank 2, RSI 55, up 3% in 7 days "
              "on 1.4x volume\"), in under 150 characters, with no promises or predictions. Reply with JSON only: "
              '{"picks": [{"symbol": "<as listed>", "reason": "<why, from the data>"}]}')
    user = (f"Risk level: {rules['name']} ({settings['risk']} of 5). Pick exactly {count}.\n"
            f"Already held by the autopilot: {holdings_view or 'nothing yet'}\n"
            + (f"\nThis autopilot's own record so far (use it where it is relevant; small numbers are weak evidence):\n{memory}\n" if memory else '')
            + "\nCandidates:\n" + '\n'.join(lines))
    return {'system': system, 'user': user}


def choose(settings, candidates, holdings_view, count, model=ask_model, memory=''):
    """Returns ([(candidate, reason)], 'ai' or 'rules'). The model can only reorder and explain the shortlist."""
    by_label = {c['label'].upper(): c for c in candidates}
    picks, used, source = [], set(), 'rules'
    answer = model(build_prompt(settings, candidates, holdings_view, count, memory)) if candidates else None
    if isinstance(answer, dict) and isinstance(answer.get('picks'), list):
        for p in answer['picks']:
            if not isinstance(p, dict):
                continue
            c = by_label.get(str(p.get('symbol') or '').strip().upper())
            if c and c['symbol'] not in used and len(picks) < count:
                reason = re.sub(r'\s+', ' ', str(p.get('reason') or '')).strip()[:170]
                picks.append((c, reason or f"Chosen from the {SCREENERS[c['screener']][0]} shortlist"))
                used.add(c['symbol'])
        if picks:
            source = 'ai'
    for c in candidates:                                   # fill any gap from the top of the shortlist
        if len(picks) >= count:
            break
        if c['symbol'] not in used:
            picks.append((c, f"Highest-ranked on the shortlist not yet held (rank {c['rank']} in {SCREENERS[c['screener']][0]}, score {c['score']:+.1f}, RSI {c['rsi']:.0f})"))
            used.add(c['symbol'])
    return picks, source


# ------------------------------------------------------------------------------------------------ portfolio
def new_portfolio(now):
    return {'v': 1, 'startingCash': STARTING_CASH, 'cash': float(STARTING_CASH), 'createdAt': iso(now), 'holdings': [], 'closed': []}


def do_buy(portfolio, c, quote, usd, reason, spy, now, counter, rate=1.0):
    """`rate` is US dollars per unit of the quote's currency (1 for US shares and coins)."""
    usd = round(usd, 2)
    holding = {
        'id': f"a{int(now.timestamp()):x}{counter}", 'symbol': c['symbol'], 'label': c['label'], 'name': quote.get('name', '')[:120],
        'currency': quote.get('currency') or 'USD', 'qty': usd / (quote['price'] * rate), 'buyPrice': quote['price'], 'buyFx': rate, 'costUsd': usd,
        'boughtAt': iso(now), 'spyAtBuy': spy, 'note': ('AI: ' + reason)[:200], 'by': 'ai', 'screener': c['screener']}
    if holding['currency'] == 'USD':
        holding['buyFx'] = 1
    portfolio['holdings'].append(holding)
    portfolio['cash'] = round(portfolio['cash'] - usd, 2)
    return holding


def do_sell(portfolio, h, price, spy, now, rate=1.0):
    rate = 1 if h.get('currency', 'USD') == 'USD' else rate
    proceeds = round(h['qty'] * price * rate, 2)
    portfolio['holdings'] = [x for x in portfolio['holdings'] if x['id'] != h['id']]
    portfolio['closed'] = (portfolio.get('closed') or []) + [dict(h, sellPrice=price, sellFx=rate, proceedsUsd=proceeds, soldAt=iso(now), spyAtSell=spy)]
    portfolio['closed'] = portfolio['closed'][-200:]
    portfolio['cash'] = round(portfolio['cash'] + proceeds, 2)
    return proceeds


# ------------------------------------------------------------------------------------------------ learning from results
def remember_buy(state, holding, c, settings, source):
    """Keep the figures a holding was bought on, to compare with how it turns out."""
    facts = {
        'symbol': c['symbol'], 'label': c['label'], 'screener': c['screener'], 'risk': settings['risk'], 'chosen': source,
        'rank': c['rank'], 'score': c['score'], 'rsi': round(c['rsi'], 1), 'd7': round(c['d7'], 1), 'd30': round(c['d30'], 1),
        'volume': round(c['volume'], 2), 't': holding['boughtAt'], 'hold': settings['maxHoldDays'], 'peak': 0.0, 'low': 0.0}
    trial = live_trial(settings, state)
    if trial and trial['param'] in EXIT_RULES:
        trial['buys'] = int(trial.get('buys', 0)) + 1
        facts.update(x=trial['id'], v='new' if trial['buys'] % 2 else 'old')      # every second buy follows the changed rule
    elif trial:
        tighter = min(trial['old'], trial['new'])
        within = c['rank'] <= tighter if trial['param'] == 'top' else c['rsi'] < tighter
        # a tighter rule on trial: 'new' are the buys it would still make. A wider one: 'new' are the extra buys it lets in.
        facts.update(x=trial['id'], v=('new' if within else 'old') if trial['new'] < trial['old'] else ('old' if within else 'new'))
    state.setdefault('open', {})[holding['id']] = facts
    return facts


def settle(record, portfolio):
    """Move every remembered holding that has since been sold into the history, with its result. Returns how many."""
    state = record['state']
    opened = state.get('open') or {}
    held = {h['id'] for h in portfolio.get('holdings', [])}
    closed = {h['id']: h for h in portfolio.get('closed', [])}
    exits = state.get('exits') or {}
    done = 0
    for hid in [k for k in opened if k not in held]:
        facts, sold = opened.pop(hid), closed.get(hid)
        if not sold or not sold.get('costUsd'):
            continue                                        # sold list cleared or portfolio reset: the result is not known
        pct = (sold['proceedsUsd'] / sold['costUsd'] - 1) * 100
        market = (sold['spyAtSell'] / sold['spyAtBuy'] - 1) * 100 if sold.get('spyAtBuy') and sold.get('spyAtSell') else None
        bought, ended = parse_time(sold.get('boughtAt')), parse_time(sold.get('soldAt'))
        how = exits.pop(hid, 'hand')
        how = how if isinstance(how, dict) else {'kind': how}
        state['closedCount'] = int(state.get('closedCount', len(record.get('history', [])))) + 1
        record.setdefault('history', []).append(dict(
            facts, id=hid, pct=round(pct, 2), usd=round(sold['proceedsUsd'] - sold['costUsd'], 2), cost=sold['costUsd'],
            market=None if market is None else round(market, 2), vs=None if market is None else round(pct - market, 2),
            days=round((ended - bought).total_seconds() / 86400, 3) if bought and ended else None,
            exit=how.get('kind') or 'hand', xrank=how.get('rank'), xscore=how.get('score'), sold=sold.get('soldAt')))
        if ended and sold.get('sellPrice'):                 # look at its price again later: what did it do after it was sold?
            later = ended + timedelta(days=min(5.0, max(1 / 24, num(facts.get('hold'), 1.0))))
            state['watch'] = (state.get('watch') or [])[-(WATCH_KEEP - 1):] + [{'id': hid, 'symbol': facts.get('symbol') or sold.get('symbol'), 'price': sold['sellPrice'], 'due': iso(later)}]
        done += 1
    state['open'] = opened
    state['exits'] = {k: v for k, v in exits.items() if k in held}
    return done


def _group(trades, label):
    judged = [t for t in trades if t.get('vs') is not None]
    return {'label': label, 'n': len(trades), 'avg': round(sum(t['pct'] for t in trades) / len(trades), 2),
            'vs': round(sum(t['vs'] for t in judged) / len(judged), 2) if judged else None,
            'beat': sum(t['vs'] > 0 for t in judged), 'judged': len(judged), 'up': sum(t['pct'] > 0 for t in trades)}


def scorecard(history):
    """What the closed trades add up to: overall and split five ways. `vs` is the average result minus the S&P 500 fund."""
    if not history:
        return {'n': 0, 'groups': {}}
    def split(name_of, order=None):
        found = {}
        for t in history:
            found.setdefault(name_of(t), []).append(t)
        keys = [k for k in (order or sorted(found, key=lambda k: -len(found[k]))) if k in found]
        return [_group(found[k], k) for k in keys]
    rank_band = lambda t: 'rank 1 to 3' if t.get('rank', 99) <= 3 else 'rank 4 to 10' if t.get('rank', 99) <= 10 else 'rank 11 and below'
    rsi_band = lambda t: 'RSI under 45' if t.get('rsi', 50) < 45 else 'RSI 45 to 60' if t.get('rsi', 50) <= 60 else 'RSI over 60'
    exit_names = {'stop': 'sold at the loss limit', 'take': 'sold at the gain mark', 'trail': 'sold to keep part of a gain', 'time': 'sold at the time limit',
                  'signal': 'sold when the signal turned', 'fade': 'sold when it slipped down the ranking', 'hand': 'sold by you'}
    card = _group(history, 'all')
    card['groups'] = {
        'screener': split(lambda t: SCREENERS[t['screener']][0] if t.get('screener') in SCREENERS else 'other'),
        'exit': split(lambda t: exit_names.get(t.get('exit'), 'other'), list(exit_names.values())),
        'chosen': split(lambda t: 'chosen by the AI model' if t.get('chosen') == 'ai' else 'chosen by rank', ['chosen by the AI model', 'chosen by rank']),
        'rank': split(rank_band, ['rank 1 to 3', 'rank 4 to 10', 'rank 11 and below']),
        'rsi': split(rsi_band, ['RSI under 45', 'RSI 45 to 60', 'RSI over 60']),
    }
    return card


def memory_text(card, lessons):
    """The record in a few lines, for the AI model's decision prompt."""
    if not card.get('n'):
        return ''
    def line(g):
        return f"{g['label']}: {g['n']} trades, average {g['avg']:+.1f}%" + (f", {g['vs']:+.1f}% against the market, ahead in {g['beat']} of {g['judged']}" if g['vs'] is not None else '')
    out = [line(dict(card, label=f"All {card['n']} closed trades"))]
    for name in ('screener', 'rank', 'rsi', 'chosen'):
        out += ['- ' + line(g) for g in card['groups'][name] if g['n'] >= MIN_SAMPLE]
    if card['n'] < MIN_SAMPLE:
        out.append(f"(Fewer than {MIN_SAMPLE} trades: too few to conclude anything.)")
    out += ['Note from the last review: ' + x for x in (lessons or {}).get('items', [])[:4]]
    return '\n'.join(out)


def review_resting(record, now):
    """Rest a screener whose recent trades have clearly lagged the market; wake one whose rest is over. Returns log entries."""
    state, entries = record['state'], []
    rest, since = state.setdefault('rest', {}), state.setdefault('restSince', {})
    for key in [k for k, until in rest.items() if (parse_time(until) or now) <= now]:
        rest.pop(key)
        since[key] = iso(now)                               # only trades closed from now count towards resting it again
        entries.append({'t': iso(now), 'type': 'note', 'symbol': '', 'usd': 0, 'text': f"Trying the {SCREENERS[key][0]} screener again after its rest."})
    for key in record['settings']['screeners']:
        if key in rest:
            continue
        recent = [t for t in record.get('history', []) if t.get('screener') == key and t.get('vs') is not None and (t.get('sold') or '') > since.get(key, '')][-REST_LOOKBACK:]
        if len(recent) >= MIN_SAMPLE:
            lag = sum(t['vs'] for t in recent) / len(recent)
            if lag <= REST_BELOW:
                rest[key] = iso(now + timedelta(days=REST_DAYS))
                entries.append({'t': iso(now), 'type': 'note', 'symbol': '', 'usd': 0,
                                'text': f"Resting the {SCREENERS[key][0]} screener for {REST_DAYS} days: its last {len(recent)} trades averaged {lag:+.1f}% against the market."})
    return entries


def write_lessons(record, now, model):
    """Every few closed trades, have the AI model put the record into words. Notes only: they change no limit."""
    state, history = record['state'], record.get('history', [])
    last = state.get('lessons') or {}
    if len(history) < LESSONS_EVERY or len(history) - int(last.get('n', 0)) < LESSONS_EVERY:
        return False
    card = scorecard(history)
    trades = '\n'.join(
        f"{t['label']} | {SCREENERS[t['screener']][0] if t.get('screener') in SCREENERS else '?'} rank {t.get('rank')} | score {t.get('score', 0):+.1f} | RSI {t.get('rsi', 0):.0f} | "
        f"30 days before {t.get('d30', 0):+.0f}% | held {span_text(t['days']) if t.get('days') is not None else '?'} | result {t['pct']:+.1f}% | market {t['market'] if t.get('market') is not None else '?'}% | exit: {t.get('exit')}"
        for t in history[-25:])
    system = ("You review the record of a paper-trading experiment on StockIQ (fake money). Write at most 4 short notes, each under 160 "
              "characters, on what the record shows about which buys did better or worse: screener, rank, RSI, the move before buying, "
              "how they were sold. Every note must rest on the figures given and mention how many trades it is based on. If the numbers "
              "are too few to tell, say that plainly instead of guessing. No predictions, no advice, no promises. "
              'Reply with JSON only: {"lessons": ["...", "..."]}')
    answer = model({'system': system, 'user': 'Scorecard:\n' + memory_text(card, None) + '\n\nMost recent closed trades:\n' + trades})
    items = [re.sub(r'\s+', ' ', str(x)).strip()[:200] for x in (answer.get('lessons') if isinstance(answer, dict) and isinstance(answer.get('lessons'), list) else []) if str(x).strip()][:4]
    if not items:
        return False
    state['lessons'] = {'at': iso(now), 'n': len(history), 'items': items}
    return True


def look_back(record, now, quote):
    """What a holding did after it was sold: once the same length of time has passed again, note the further change.
    This is how it can tell a sale that came too early from one that came in time."""
    state = record['state']
    watch = state.get('watch') or []
    due = [w for w in watch if (parse_time(w.get('due')) or now) <= now][:8]
    if not due:
        return 0
    by_id = {t.get('id'): t for t in record.get('history', [])}
    with ThreadPoolExecutor(max_workers=8) as pool:
        quotes = list(pool.map(lambda w: _safe(quote, w['symbol']), due))
    for w, q in zip(due, quotes):
        trade = by_id.get(w['id'])
        if trade is not None and q and q.get('price', 0) > 0 and num(w.get('price')) > 0:
            trade['after'] = round((q['price'] / w['price'] - 1) * 100, 2)
    gone = {w['id'] for w in due}
    state['watch'] = [w for w in watch if w['id'] not in gone]
    return len(due)


def month_figures(history, budget, now):
    """Dollars made or lost on finished trades in the last 30 days and the 30 before, also as a share of the budget."""
    def span(start, end):
        rows = [t for t in history if t.get('usd') is not None and start < (parse_time(t.get('sold')) or datetime.min) <= end]
        usd = sum(t['usd'] for t in rows)
        return {'n': len(rows), 'up': sum(t['usd'] > 0 for t in rows), 'usd': round(usd, 2), 'pct': round(usd / budget * 100, 2) if budget else None}
    return {'last30': span(now - timedelta(days=30), now), 'before30': span(now - timedelta(days=60), now - timedelta(days=30))}


def rule_text(param, value):
    if param == 'stop':
        return f"sell at {value:g}%"
    if param == 'take':
        return f"sell at +{value:g}%"
    if param == 'trail':
        return f"sell after giving back {value * 100:.0f}% of its best gain"
    if param == 'top':
        return f"buy from the top {value:g} of a ranking"
    return 'buy at any RSI' if value >= 100 else f"buy only with RSI under {value:g}"


def propose(trades, rules, past=()):
    """Changes to its own rules that the record suggests, most promising first.
    Each is an estimate IN HINDSIGHT on finished trades (`gain`: percentage points a trade the result would have
    been better by). Hindsight flatters, so nothing is adopted on this: the trial that follows decides."""
    if len(trades) < TUNE_BATCH:
        return []
    avg = lambda xs: sum(xs) / len(xs)
    base = avg([t['pct'] for t in trades])
    path = [t for t in trades if t.get('peak') is not None and t.get('low') is not None]
    ideas = []

    def add(param, new, gain, why):
        new = bounded(param, new)
        direction = 'up' if new > rules[param] else 'down'
        if new == rules[param] or gain < TUNE_MIN_GAIN:
            return
        if any(p.get('param') == param and p.get('direction') == direction and p.get('verdict') != 'kept' for p in list(past)[-3:]):
            return                                          # tried lately without success: leave it for now
        ideas.append({'param': param, 'old': rules[param], 'new': new, 'direction': direction, 'gain': round(gain, 2), 'base': round(base, 2), 'why': why})

    if len(path) >= MIN_SAMPLE:
        for share in (0.5, 0.75):                           # a nearer gain mark: sold at the mark instead of what they ended at
            mark = bounded('take', rules['take'] * share)
            reached = [t for t in path if t['peak'] >= mark]
            if reached:
                add('take', mark, sum(mark - t['pct'] for t in reached) / len(path),
                    f"{len(reached)} of the last {len(path)} finished trades were up {mark:g}% or more at some point while held, and ended at {avg([t['pct'] for t in reached]):+.1f}% on average")
            limit = bounded('stop', rules['stop'] * share)   # a nearer loss limit
            touched = [t for t in path if t['low'] <= limit]
            if touched:
                add('stop', limit, sum(limit - t['pct'] for t in touched) / len(path),
                    f"{len(touched)} of the last {len(path)} finished trades were down {abs(limit):g}% or more at some point while held, and ended at {avg([t['pct'] for t in touched]):+.1f}% on average")
        tighter = 0.3                                       # giving back less of a gain before selling
        armed = [t for t in path if t['peak'] >= rules['take'] * TRAIL_ARM]
        slipped = [t for t in armed if t['pct'] < t['peak'] * (1 - tighter)]
        if tighter < rules['trail'] and slipped:
            add('trail', tighter, sum(t['peak'] * (1 - tighter) - t['pct'] for t in slipped) / len(path),
                f"{len(slipped)} of the {len(armed)} trades that had been up {rules['take'] * TRAIL_ARM:g}% or more ended well below their best ({avg([t['pct'] for t in slipped]):+.1f}% against a best of {avg([t['peak'] for t in slipped]):+.1f}%)")
    # sold too early? what the holdings did after each kind of sale
    for kind, param, new, name in (('take', 'take', rules['take'] * 1.5, 'gain mark'), ('stop', 'stop', rules['stop'] * 1.5, 'loss limit'),
                                   ('trail', 'trail', rules['trail'] + 0.2, 'point where part of a gain is kept')):
        after = [t['after'] for t in trades if t.get('exit') == kind and t.get('after') is not None]
        if len(after) >= MIN_SAMPLE // 2 and avg(after) > 0:
            add(param, new, avg(after) * len(after) / len(trades) / 2,
                f"the {len(after)} holdings sold at the {name} went on to {avg(after):+.1f}% on average afterwards")
    # what it buys: nearer the top of the ranking against further down
    near_limit = max(3, rules['top'] // 2)
    near, far = [t['pct'] for t in trades if t.get('rank', 99) <= near_limit], [t['pct'] for t in trades if t.get('rank', 99) > near_limit]
    if len(near) >= MIN_SAMPLE and len(far) >= MIN_SAMPLE // 2 and avg(near) > avg(far):
        add('top', near_limit, avg(near) - base, f"buys ranked 1 to {near_limit} averaged {avg(near):+.1f}% over {len(near)} trades; those ranked lower {avg(far):+.1f}% over {len(far)}")
    elif len(far) >= MIN_SAMPLE and len(near) >= MIN_SAMPLE // 2 and avg(far) > avg(near):
        add('top', rules['top'] * 1.5, (avg(far) - base) / 2, f"buys ranked below {near_limit} averaged {avg(far):+.1f}% over {len(far)} trades; those ranked 1 to {near_limit} {avg(near):+.1f}% over {len(near)}")
    # ... and a calmer RSI against a hotter one
    cut = min(rules['max_rsi'], 100) - 8
    cool, hot = [t['pct'] for t in trades if t.get('rsi', 50) < cut], [t['pct'] for t in trades if t.get('rsi', 50) >= cut]
    if len(cool) >= MIN_SAMPLE and len(hot) >= MIN_SAMPLE // 2 and avg(cool) > avg(hot):
        add('max_rsi', cut, avg(cool) - base, f"buys with RSI under {cut:g} averaged {avg(cool):+.1f}% over {len(cool)} trades; those with a higher RSI {avg(hot):+.1f}% over {len(hot)}")
    elif len(hot) >= MIN_SAMPLE and len(cool) >= MIN_SAMPLE // 2 and avg(hot) > avg(cool) and rules['max_rsi'] < 101:
        add('max_rsi', rules['max_rsi'] + 6, (avg(hot) - base) / 2, f"buys with RSI of {cut:g} or more averaged {avg(hot):+.1f}% over {len(hot)} trades; calmer ones {avg(cool):+.1f}% over {len(cool)}")
    return sorted(ideas, key=lambda i: -i['gain'])


def trial_figures(trial, history):
    """How the two groups of a trial have done so far: the trades bought under the changed rule and those under the current one."""
    groups = {v: [t['pct'] for t in history if t.get('x') == trial.get('id') and t.get('v') == v] for v in ('new', 'old')}
    mean = lambda xs: sum(xs) / len(xs)
    error = lambda xs: math.sqrt(sum((x - mean(xs)) ** 2 for x in xs) / (len(xs) - 1) / len(xs))
    out = {'with': len(groups['new']), 'without': len(groups['old']),
           'avgWith': round(mean(groups['new']), 2) if groups['new'] else None, 'avgWithout': round(mean(groups['old']), 2) if groups['old'] else None}
    if len(groups['new']) >= 2 and len(groups['old']) >= 2:
        out['diff'] = round(mean(groups['new']) - mean(groups['old']), 2)
        out['margin'] = round(math.sqrt(error(groups['new']) ** 2 + error(groups['old']) ** 2), 2)   # one standard error of the difference
    return out


def trial_how(trial):
    if trial['param'] in EXIT_RULES:
        return 'Every second buy follows the changed rule, the others the current one, so both are tried over the same days.'
    if trial['new'] < trial['old']:
        return 'It keeps buying as it does now, and compares the buys the tighter rule would still have made with the ones it would have skipped.'
    return 'It also buys from the wider range, and compares those extra buys with the usual ones.'


def review_tuning(record, now, mail=None):
    """After sales: judge a running trial of a changed rule, or look for the next change worth trying. Returns log entries.
    The only things it can change are the rules in TUNABLE, inside their bounds, for the user's own practice trades."""
    settings, state, history = record['settings'], record['state'], record.get('history', [])
    tune, entries = tune_of(state), []
    count = int(state.get('closedCount', len(history)))
    note = lambda text: entries.append({'t': iso(now), 'type': 'note', 'symbol': '', 'usd': 0, 'text': text})
    tell = lambda subject, lines: mail and mail(subject, lines + review_lines(record, now))
    trial = tune.get('trial')
    if trial:
        figures = trial_figures(trial, history)
        change = f"{rule_text(trial['param'], trial['new'])} instead of the current \"{rule_text(trial['param'], trial['old'])}\""
        if trial.get('risk') != settings['risk']:
            verdict, why = 'stopped', f"the risk level was changed, and the trial belonged to the {RISK[trial['risk']]['name']} level"
        elif figures['with'] >= TUNE_GROUP and figures['without'] >= TUNE_GROUP:
            result = (f"{figures['with']} trades with the change averaged {figures['avgWith']:+.2f}%, {figures['without']} without it {figures['avgWithout']:+.2f}% "
                      f"(difference {figures['diff']:+.2f}, margin of error {figures['margin']:.2f})")
            clear = figures['diff'] > 0 and figures['diff'] >= figures['margin']
            verdict, why = ('kept', result) if clear else ('dropped', result + (': no clear improvement' if figures['diff'] > -figures['margin'] else ': worse'))
        elif now - (parse_time(trial.get('since')) or now) > timedelta(days=TUNE_GIVE_UP_DAYS):
            verdict, why = 'dropped', f"after {TUNE_GIVE_UP_DAYS} days too few trades had finished in one of the two groups to tell ({figures['with']} with the change, {figures['without']} without)"
        else:
            return entries
        if verdict == 'kept':
            tune['values'].setdefault(str(trial['risk']), {})[trial['param']] = trial['new']
        tune['past'] = (tune['past'] + [dict(trial, verdict=verdict, ended=iso(now), result=why, **figures)])[-20:]
        tune['trial'], tune['mark'] = None, count
        outcome = {'kept': 'The change is kept', 'dropped': 'The rule stays as it was', 'stopped': 'The trial was stopped'}[verdict]
        note(f"Trial of its own rules finished: {change}. {outcome}: {why}.")
        tell(f"StockIQ autopilot (fake money): trial finished, {'change kept' if verdict == 'kept' else 'rule left as it was'}",
             ['The autopilot has finished a trial of one of its own rules.', '', f"What it tried: {change}.", f"Result: {outcome.lower()}. {why[0].upper() + why[1:]}.",
              'A change is kept only when the trades with it did better by more than the margin of error; otherwise the rule stays as it was.'])
        return entries
    if count - int(tune.get('mark', 0)) < TUNE_BATCH:
        return entries
    tune['mark'] = count
    rules = rules_for(settings, state)
    ideas = propose([t for t in history if t.get('risk') == settings['risk']][-TUNE_LOOKBACK:], rules, tune['past'])
    if not ideas:
        note(f"Reviewed its own rules after {count} finished trades: nothing in the record suggests a change worth trying. Next review after {TUNE_BATCH} more.")
        tell('StockIQ autopilot (fake money): review of its rules, no change',
             [f"The autopilot has reviewed its own rules after {count} finished trades.", '', 'Nothing in the record suggests a change worth trying, so its rules stay as they are.',
              f"It reviews them again after {TUNE_BATCH} more finished trades."])
        return entries
    best = ideas[0]
    tune['seq'] = int(tune.get('seq', 0)) + 1
    trial = tune['trial'] = {'id': tune['seq'], 'risk': settings['risk'], 'param': best['param'], 'old': best['old'], 'new': best['new'], 'direction': best['direction'],
                             'since': iso(now), 'why': best['why'], 'gain': best['gain'], 'buys': 0}
    change = f"{rule_text(best['param'], best['new'])} instead of the current \"{rule_text(best['param'], best['old'])}\""
    note(f"Reviewed its own rules after {count} finished trades and started a trial: {change}. Why: {best['why']}. {trial_how(trial)}")
    tell('StockIQ autopilot (fake money): trying a change to one of its rules',
         [f"The autopilot has reviewed its own rules after {count} finished trades and is trying one change.", '',
          f"What it is trying: {change} ({RISK[settings['risk']]['name']} level).", f"Why: {best['why']}.",
          f"In hindsight that would have been worth about {best['gain']:+.2f} percentage points a trade. Hindsight flatters, so this is only a reason to try it.",
          f"How it is tried: {trial_how(trial)[0].lower() + trial_how(trial)[1:]}",
          f"It decides after {TUNE_GROUP} finished trades each way, keeps the change only if that group did clearly better, and emails the result."])
    return entries


def review_lines(record, now):
    """The rest of a review email: the record so far, the AI model's notes, and what only the user can change."""
    settings, state, history = record['settings'], record['state'], record.get('history', [])
    month, rules = month_figures(history, settings['budgetUsd'], now), rules_for(settings, state)
    recent = month['last30']
    lines = ['', 'THE RECORD SO FAR (fake money)']
    lines.append(f"Last 30 days: {recent['n']} finished trades, {recent['up']} of them up, ${recent['usd']:+,.2f} in all"
                 + (f", which is {recent['pct']:+.2f}% of the ${settings['budgetUsd']:,.0f} budget." if recent['pct'] is not None else '.'))
    if month['before30']['n']:
        earlier = month['before30']
        lines.append(f"The 30 days before: {earlier['n']} finished trades, ${earlier['usd']:+,.2f}" + (f" ({earlier['pct']:+.2f}% of the budget)." if earlier['pct'] is not None else '.'))
    lines += memory_text(scorecard(history), None).split('\n') if history else []
    notes = (state.get('lessons') or {}).get('items') or []
    if notes:
        lines += ['', 'WHAT THE AI MODEL NOTED FROM THE RECORD'] + ['- ' + n for n in notes]
    lines += ['', f"ITS RULES NOW ({rules['name']} level)",
              f"Sells at {rules['stop']:g}% or +{rules['take']:g}%; once a holding has been up {rules['take'] * TRAIL_ARM:g}%, sells if it gives back {rules['trail'] * 100:.0f}% of its best gain; "
              f"buys from the top {rules['top']:g} of a ranking" + ('.' if rules['max_rsi'] >= 100 else f" with RSI under {rules['max_rsi']:g}.")]
    yours = []
    timed = [t['after'] for t in history[-TUNE_LOOKBACK:] if t.get('exit') == 'time' and t.get('after') is not None]
    if len(timed) >= MIN_SAMPLE:
        went = sum(timed) / len(timed)
        if abs(went) >= 0.3:
            yours.append(f"The {len(timed)} holdings sold at the time limit went on to {went:+.1f}% on average over the same length of time again: "
                         + ('a longer "Keeps a holding at most" may be worth trying.' if went > 0 else 'the time limit has been getting out in time.'))
    coins_only = settings['screeners'] and all(SCREENERS[k][3] == 'crypto' for k in settings['screeners'])
    if coins_only and RISK[settings['risk']]['crypto'] < 1:
        yours.append(f"Only coin screeners are ticked: at the {rules['name']} level it puts at most {RISK[settings['risk']]['crypto'] * 100:.0f}% of the budget in coins.")
    if yours:
        lines += ['', 'SETTINGS ONLY YOU CAN CHANGE (it never touches these)'] + ['- ' + y for y in yours]
    lines += ['', 'This is a fake-money experiment on your StockIQ dashboard: no real trade is placed. The numbers are past results of a small',
              'number of practice trades and say nothing certain about the future. Not financial advice.', 'https://stockiq.tech/dashboard.html']
    return lines


def send_mail(to, subject, lines):
    """Email a review to the account's own address. Only the deployed function sends; a failure never stops a check-in."""
    if not os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        return False
    try:
        boto3.client('ses', region_name='us-east-1').send_email(
            Source=MAIL_FROM, Destination={'ToAddresses': [to]},
            Message={'Subject': {'Data': subject[:150]}, 'Body': {'Text': {'Data': '\n'.join(lines)}}})
        return True
    except Exception as e:
        print(f'review email not sent: {type(e).__name__}')
        return False


def sale_detail(h, facts, at_sale, settings, spy, now):
    """The fuller story of one sale, for the "Details" under it on the dashboard."""
    lines = []
    if facts:
        lines.append(f"Bought at rank {facts.get('rank')} of {SCREENERS[facts['screener']][0] if facts.get('screener') in SCREENERS else 'its screener'} "
                     f"(score {num(facts.get('score')):+.1f}, RSI {num(facts.get('rsi')):.0f}), {'chosen by the AI model' if facts.get('chosen') == 'ai' else 'chosen by rank'}"
                     + (': ' + str(h.get('note'))[4:] if str(h.get('note') or '').startswith('AI: ') else '') + '.')
    days = at_sale.get('days')
    if days is not None:
        lines.append(f"Held {span_text(days)}. It was set to keep a holding at most {span_text(settings['maxHoldDays'])}.")
    if 'peak' in at_sale:
        lines.append(f"While it was held: {at_sale['peak']:+.1f}% at its best, {at_sale['low']:+.1f}% at its worst (as seen at check-ins).")
    if at_sale.get('rank') is not None:
        lines.append(f"At the sale: rank {at_sale['rank']}, score {num(at_sale.get('score')):+.1f}, signal {SIGNAL_LABELS.get(at_sale.get('signal'), 'Unrated').lower()}.")
    if 'stop' in at_sale:
        lines.append(f"Its rules for this holding: sell at {at_sale['stop']:g}% or +{at_sale['take']:g}%; once up {at_sale['take'] * TRAIL_ARM:g}%, sell if it gives back "
                     f"{at_sale['trail'] * 100:.0f}% of its best gain; sell if the screener signal turns negative or it slips far down the ranking."
                     + (' This buy was part of a trial of a changed rule.' if facts and facts.get('v') == 'new' else ''))
    if h.get('spyAtBuy') and spy:
        lines.append(f"An S&P 500 fund over the same time: {(spy / h['spyAtBuy'] - 1) * 100:+.1f}%.")
    return [line[:320] for line in lines][:6]


def add_log(record, entries, now):
    """Add to the activity list. A check-in that changed nothing, the same as the one before, is counted, not listed again."""
    log = record['log']
    for e in entries:
        last = log[-1] if log else None
        if last and e.get('key') and last.get('type') == 'note' and last.get('key') == e['key']:
            last['first'] = last.get('first') or last['t']
            last['n'] = int(last.get('n', 1)) + 1
            last['t'], last['text'] = e['t'], e['text']
        else:
            log.append(e)


def stocks_open(now):
    """US market hours (see MARKET_HOURS)."""
    return market_open('us', now)


def run_user(user_id, record, now, snapshot=None, quote=None, model=None, manual=False, markets=None, mail=None):
    """One check-in for one user. Changes `record` (state, log, history) and the user's portfolio. Returns a summary.
    `markets`: the markets to act on (the scheduled run passes the ones that are open and due); None means all."""
    snapshot, quote, model = snapshot or (lambda k: get_snapshot(k, now)), quote or fetch_quote, model or ask_model
    mail = mail or (lambda subject, lines: send_mail(user_id, subject, lines))
    settings, state = record['settings'], record['state']
    rules, trial, opened = rules_for(settings, state), live_trial(settings, state), state.setdefault('open', {})
    table = db().Table(PORTFOLIO_TABLE)
    item = table.get_item(Key={'userId': user_id}).get('Item')
    portfolio = json.loads(item['data']) if item else new_portfolio(now)
    version = int(item['version']) if item else 0
    portfolio.setdefault('closed', [])

    entries = []
    settle(record, portfolio)                               # anything sold since last time (also by hand) goes into the history
    look_back(record, now, quote)
    entries += review_resting(record, now)
    resting = set(state.get('rest') or {})
    active = lambda key: markets is None or market_of(key) in markets
    buy_from = [k for k in settings['screeners'] if active(k) and k not in resting]
    mine = [h for h in ai_holdings(portfolio) if active(h.get('screener'))]

    wanted = set(buy_from) | {h.get('screener') for h in mine if h.get('screener') in SCREENERS}
    with ThreadPoolExecutor(max_workers=5) as pool:
        got = list(pool.map(lambda k: (k, _safe(snapshot, k)), sorted(wanted)))
    snapshots = {k: rows for k, rows in got if rows}
    missing = [SCREENERS[k][0] for k, rows in got if not rows]

    symbols = {h['symbol'] for h in mine} | {BENCHMARK}
    with ThreadPoolExecutor(max_workers=8) as pool:
        quotes = dict(zip(sorted(symbols), pool.map(quote, sorted(symbols))))
    spy = (quotes.get(BENCHMARK) or {}).get('price')
    fx = {}                                                 # exchange rates looked up in this check-in
    rates = {h['symbol']: usd_rate(h.get('currency', 'USD'), quote, fx) for h in mine if h.get('currency', 'USD') != 'USD'}

    sold, kinds, at_sale = 0, {}, {}
    for h, price, reason in review_sells(portfolio, settings, snapshots, quotes, now, rates, None if markets is None else set(markets), kinds, rules, opened, trial, at_sale):
        proceeds = do_sell(portfolio, h, price, spy, now, rates.get(h['symbol'], 1.0))
        figures = at_sale.get(h['id'], {})
        state.setdefault('exits', {})[h['id']] = {'kind': kinds.get(h['id'], 'hand'), 'rank': figures.get('rank'), 'score': figures.get('score')}
        entries.append({'t': iso(now), 'type': 'sell', 'symbol': h['label'], 'usd': proceeds, 'text': f"{reason}. Put in ${h['costUsd']:,.2f}, got back ${proceeds:,.2f}.",
                        'kind': kinds.get(h['id']), 'pct': round((proceeds / h['costUsd'] - 1) * 100, 2) if h.get('costUsd') else None,
                        'detail': sale_detail(h, opened.get(h['id']), figures, settings, spy, now)})
        sold += 1

    room, invested = allowance(portfolio, settings, state, now)
    size = settings['budgetUsd'] / rules['positions']
    # holdings are bought in whole cents, so a few of them can leave the room a cent or two short of one more:
    # allow a cent per holding, and let the last one take exactly what is left (never over the budget)
    slack = 0.01 * rules['positions']
    count = min(MAX_BUYS_PER_CHECK, int((room + slack) // size))
    candidates = shortlist(portfolio, dict(settings, screeners=buy_from), snapshots, now, rules, trial)
    in_coins = sum(h['costUsd'] for h in ai_holdings(portfolio) if h['symbol'].endswith('-USD'))
    crypto_room = settings['budgetUsd'] * rules['crypto'] - in_coins
    coins_full = crypto_room < MIN_TRADE_USD and any(c['kind'] == 'crypto' for c in candidates)
    if coins_full:                                          # the level's share in coins is used up: no coin can be bought, so none is offered
        candidates = [c for c in candidates if c['kind'] != 'crypto']

    bought, source = 0, 'rules'
    if count and candidates:
        def view_of(h):
            q, rate = quotes.get(h['symbol']), 1.0 if h.get('currency', 'USD') == 'USD' else rates.get(h['symbol'])
            return f"{h['label']} ({(q['price'] * rate / (h['buyPrice'] * h.get('buyFx', 1)) - 1) * 100:+.1f}%)" if q and rate else h['label']
        view = ', '.join(view_of(h) for h in ai_holdings(portfolio))
        memory = memory_text(scorecard(record.get('history', [])), state.get('lessons'))
        picks, source = choose(settings, candidates[:12], view, count, model, memory)
        for n, (c, reason) in enumerate(picks):
            amount = min(size, portfolio['cash'], room)
            if c['kind'] == 'crypto':
                amount = min(amount, crypto_room)
            if amount < MIN_TRADE_USD:
                continue
            live = quote(c['symbol'])
            rate = usd_rate(live['currency'], quote, fx) if live else None
            if not live or not rate or not (0.8 < live['price'] / c['price'] < 1.25):
                entries.append({'t': iso(now), 'type': 'note', 'symbol': c['label'], 'usd': 0, 'text': 'Skipped: no matching live price for it.'})
                continue
            holding = do_buy(portfolio, c, live, amount, reason, spy, now, n, rate)
            room -= holding['costUsd']
            facts = remember_buy(state, holding, c, settings, source)
            if c['kind'] == 'crypto':
                crypto_room -= amount
            mine_rules = own_rules(rules, facts, trial)
            entries.append({'t': iso(now), 'type': 'buy', 'symbol': c['label'], 'usd': round(amount, 2),
                            'text': f"{reason} ({SCREENERS[c['screener']][0]} rank {c['rank']}, score {c['score']:+.1f}; {'chosen by the AI model' if source == 'ai' else 'chosen by rank'})",
                            'detail': [f"The plan for it: sell {span_text(settings['maxHoldDays'])} after buying at the latest; sooner at {mine_rules['stop']:g}% or +{mine_rules['take']:g}%; "
                                       f"once it has been up {mine_rules['take'] * TRAIL_ARM:g}%, sell if it gives back {mine_rules['trail'] * 100:.0f}% of its best gain; "
                                       'sell if its screener signal turns negative or it slips far down the ranking.']
                                      + ([f"Part of a trial of one of its own rules: this buy follows {'the changed rule' if facts.get('v') == 'new' else 'the current rule, for comparison'}."] if facts.get('x') else [])})
            bought += 1

    if not bought and not sold:
        if missing and not snapshots:
            key, why = 'nodata', 'Screener data was not available: ' + ', '.join(missing) + '.'
        elif not count:
            if portfolio['cash'] < size:
                key, why = 'cash', f"Not enough practice cash for another holding (${portfolio['cash']:,.0f} left, a holding is ${size:,.0f})."
            elif settings['budgetUsd'] - invested < size - slack:
                key, why = 'full', f"The ${settings['budgetUsd']:,.0f} budget is fully invested in {len(ai_holdings(portfolio))} holdings."
            else:
                more = next_release(settings, state, invested, now)
                key, why = 'pace', (f"Nothing to spend yet: ${invested:,.0f} of the ${settings['budgetUsd']:,.0f} budget is invested. The rest is released in steps over the "
                                    f"{settings['periodDays']} day{'' if settings['periodDays'] == 1 else 's'} set under \"Build up to it over\""
                                    + (f"; the next ${size:,.0f} in about {span_text(max(0.0, (more - now).total_seconds()) / 86400)}." if more else '.'))
        elif not buy_from:
            key, why = 'shut', 'Every screener you chose is resting after lagging the market.' if resting & set(settings['screeners']) else 'None of the chosen markets is open.'
        elif coins_full and not candidates:
            key, why = 'coins', (f"${in_coins:,.0f} is in coins, and the {rules['name']} level puts at most {rules['crypto'] * 100:.0f}% of the budget "
                                 f"(${settings['budgetUsd'] * rules['crypto']:,.0f}) in coins. Tick a share screener as well, or move the level up, for it to buy more.")
        elif not candidates:
            key, why = 'none', f"Nothing on the shortlist passed the {rules['name']} filters this time."
        else:
            key, why = 'same', 'No change.'
        entries.append({'t': iso(now), 'type': 'note', 'symbol': '', 'usd': 0, 'text': 'Checked in. ' + why, 'key': key})
    shut = sorted({MARKET_NAMES[market_of(k)] for k in settings['screeners'] if not market_open(market_of(k), now)})
    if manual and shut:
        entries.append({'t': iso(now), 'type': 'note', 'symbol': '', 'usd': 0,
                        'text': ('US market is closed' if shut == ['US'] else 'Closed right now: ' + ', '.join(shut) + ' market' + ('s' if len(shut) > 1 else '')) + ': stock prices are the last traded ones.'})

    if bought or sold:
        try:
            table.put_item(Item={'userId': user_id, 'data': json.dumps(portfolio), 'version': version + 1, 'updatedAt': iso(now)},
                           ConditionExpression='attribute_not_exists(userId) OR version = :v', ExpressionAttributeValues={':v': version})
        except ClientError as e:
            if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                raise
            # the user changed the portfolio at the same moment: change nothing, try again at the next check-in
            record['log'].append({'t': iso(now), 'type': 'note', 'symbol': '', 'usd': 0, 'text': 'Checked in, but the portfolio was being changed at the same time. Nothing was traded.'})
            for holding_id in [k for k, v in (state.get('open') or {}).items() if v.get('t') == iso(now)]:
                state['open'].pop(holding_id)                 # buys that were not saved are not remembered either
            return {'bought': 0, 'sold': 0, 'conflict': True}
    state['lastRun'] = iso(now)
    checked = state.setdefault('lastRunBy', {})
    for market in ({market_of(k) for k in settings['screeners']} if markets is None else set(markets)):
        checked[market] = iso(now)
    if settle(record, portfolio):                           # what was sold in this check-in
        entries += review_resting(record, now)
    if write_lessons(record, now, model):
        entries.append({'t': iso(now), 'type': 'note', 'symbol': '', 'usd': 0, 'text': 'Reviewed its own record: ' + ' '.join(state['lessons']['items'])[:400]})
    entries += review_tuning(record, now, mail)             # its own rules: judge a trial, or find the next change to try
    add_log(record, entries, now)
    return {'bought': bought, 'sold': sold, 'decidedBy': source, 'entries': entries}


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        print(f'{getattr(fn, "__name__", "call")}{args} failed: {type(e).__name__}: {e}')
        return None


def due_markets(record, now):
    """The markets among the user's screeners that are open now and have not been checked within the chosen gap."""
    settings, state = record['settings'], record['state']
    if not settings['enabled']:
        return []
    checked = state.get('lastRunBy') or {}
    out = []
    for market in sorted({market_of(k) for k in settings['screeners']}):
        last = parse_time(checked.get(market) or (state.get('lastRun') if not checked else None))
        if market_open(market, now) and (last is None or now - last >= timedelta(hours=settings['everyHours']) - GRACE):
            out.append(market)
    return out


def due(record, now):
    return bool(due_markets(record, now))


def next_check(record, now):
    """When the schedule (every 30 minutes, see SLOT_MINUTES) will next run this user, and for which markets."""
    if not record['settings']['enabled']:
        return None
    hour = now.replace(minute=0, second=0, microsecond=0)
    slots = [hour + timedelta(hours=h, minutes=m) for h in range(24 * 10 + 1) for m in SLOT_MINUTES]
    for t in slots:
        if t <= now:
            continue
        markets = due_markets(record, t)
        if markets:
            return {'at': iso(t), 'markets': [MARKET_NAMES[m] for m in markets]}
    return None


def public(record, now=None, user_id=None):
    """What the dashboard gets: the record without the bulk, plus the scorecard, the next check-in and what it holds."""
    state = record['state']
    rest = {k: v for k, v in (state.get('rest') or {}).items() if k in SCREENERS}
    out = {'settings': record['settings'], 'state': {k: state.get(k) for k in ('lastRun', 'lastRunBy', 'startedAt')}, 'log': record['log'],
           'scorecard': scorecard(record.get('history', [])), 'lessons': state.get('lessons'), 'resting': rest,
           'recent': record.get('history', [])[-10:], 'minSample': MIN_SAMPLE, 'practiceCash': STARTING_CASH}
    settings, tune = record['settings'], tune_of(dict(state, tune=dict(state.get('tune') or {})))
    rules, trial, count = rules_for(settings, state), live_trial(settings, state), int(state.get('closedCount', len(record.get('history', []))))
    fields = ('stop', 'take', 'trail', 'top', 'max_rsi')
    out['rules'] = dict({f: rules[f] for f in fields}, name=rules['name'], arm=rules['take'] * TRAIL_ARM,
                        changed={f: RISK[settings['risk']][f] for f in fields if rules[f] != RISK[settings['risk']][f]})
    out['tune'] = {'trial': dict(trial, how=trial_how(trial), text=f"{rule_text(trial['param'], trial['new'])} instead of \"{rule_text(trial['param'], trial['old'])}\"",
                                 **trial_figures(trial, record.get('history', []))) if trial else None,
                   'past': [dict(p, text=f"{rule_text(p['param'], p['new'])} instead of \"{rule_text(p['param'], p['old'])}\"") for p in tune['past'][-8:]],
                   'nextReviewIn': None if trial else max(0, TUNE_BATCH - (count - int(tune.get('mark', 0)))), 'batch': TUNE_BATCH, 'group': TUNE_GROUP, 'finished': count}
    if now is not None:
        out['month'] = month_figures(record.get('history', []), settings['budgetUsd'], now)
        out['now'] = iso(now)
        out['nextCheck'] = next_check(record, now)
    if user_id is not None:
        try:
            item = db().Table(PORTFOLIO_TABLE).get_item(Key={'userId': user_id}).get('Item')
            mine = ai_holdings(json.loads(item['data'])) if item else []
            out['holding'] = {'count': len(mine), 'investedUsd': round(sum(h['costUsd'] for h in mine), 2)}
            plans = []                                      # for each holding it bought: when and at what it will be sold
            for h in mine:
                facts, bought = (state.get('open') or {}).get(h['id']), parse_time(h.get('boughtAt'))
                own = own_rules(rules, facts, trial)
                plans.append({'id': h['id'], 'label': h.get('label'), 'boughtAt': h.get('boughtAt'), 'auto': bool(settings['enabled']),
                              'sellBy': iso(bought + timedelta(days=settings['maxHoldDays'])) if bought else None, 'holdDays': settings['maxHoldDays'],
                              'stop': own['stop'], 'take': own['take'], 'arm': own['take'] * TRAIL_ARM, 'trail': own['trail'],
                              'peak': (facts or {}).get('peak'), 'trial': bool(facts and facts.get('v') == 'new')})
            out['plans'] = plans
        except Exception:
            pass
    return out


# ------------------------------------------------------------------------------------------------ entry point
def lambda_handler(event, context):
    now = datetime.utcnow().replace(microsecond=0)
    event = event if isinstance(event, dict) else {}
    if 'requestContext' not in event and 'body' not in event:
        # the hourly schedule: every user who has it switched on and is due
        done = []
        rows = db().Table(SETTINGS_TABLE).scan(ProjectionExpression='userId, enabled').get('Items', [])
        rows = [r for r in rows if not str(r.get('userId', '')).startswith('_')]      # not the stored screener results
        if event.get('mail_test'):
            # run by hand (aws lambda invoke) to check that review emails arrive: one email to each user who has it on
            sent = 0
            for row in rows:
                if row.get('enabled') and allowed(row['userId']):
                    record = load_item(row['userId'])
                    sent += bool(send_mail(row['userId'], 'StockIQ autopilot (fake money): review emails are set up',
                                           ['This is the address the practice-portfolio autopilot will email when it reviews its own rules.', '',
                                            f"It reviews them after every {TUNE_BATCH} finished trades. If the record suggests a change worth trying, it tries it beside",
                                            'the current rule over the same days, and emails you what it is trying and why, and later whether it helped.'] + review_lines(record, now)))
            print(f'mail test: {sent} sent')
            return {'statusCode': 200, 'body': json.dumps({'mailTest': sent})}
        for row in rows:
            user_id = row['userId']
            if not row.get('enabled') or not allowed(user_id):
                continue
            try:
                record = load_item(user_id)
                open_and_due = due_markets(record, now)
                if open_and_due:
                    summary = run_user(user_id, record, now, markets=open_and_due)
                    save_item(user_id, record)
                    done.append({'user': user_id[:3] + '…', 'bought': summary.get('bought'), 'sold': summary.get('sold')})
            except Exception as e:
                print(f'check-in failed for {user_id[:3]}…: {type(e).__name__}: {e}')
        print(f'scheduled check: {len(done)} of {len(rows)} users were due: {done}')
        return {'statusCode': 200, 'body': json.dumps({'ran': done})}

    try:
        raw = event.get('body')
        body = json.loads(raw) if isinstance(raw, str) else (raw or {})
        assert isinstance(body, dict)
    except Exception:
        return respond(400, {'error': 'Bad request'})
    user_id = body.get('userId')
    if not isinstance(user_id, str) or not (3 <= len(user_id) <= 200) or '@' not in user_id:
        return respond(400, {'error': 'Sign in to use the autopilot'})
    action = body.get('action')
    options = {'screeners': {k: {'name': v[0], 'kind': v[3], 'group': v[5]} for k, v in SCREENERS.items()}, 'everyHours': list(EVERY_HOURS), 'holdDays': list(HOLD_DAYS),
               'risk': {str(k): {f: v[f] for f in ('name', 'positions', 'top', 'stop', 'take', 'crypto', 'trail', 'max_rsi')} for k, v in RISK.items()}}
    try:
        if not allowed(user_id):
            return respond(200, {'success': True, 'allowed': False})
        record = load_item(user_id)
        if action == 'get':
            return respond(200, {'success': True, 'allowed': True, 'options': options, **public(record, now, user_id)})
        if action == 'save':
            before = record['settings']
            record['settings'] = clean_settings(body.get('settings'), user_id)
            after = record['settings']
            if after['enabled'] and (not before['enabled'] or (before['budgetUsd'], before['periodDays']) != (after['budgetUsd'], after['periodDays'])):
                record['state']['startedAt'] = iso(now)     # the budget's spread starts (again) from now
            if after['enabled'] and (not before['enabled'] or any(before[k] != after[k] for k in ('risk', 'budgetUsd', 'periodDays', 'everyHours'))):
                # the dashboard saves each change as it is made: keep one line for a burst of changes, not one per keystroke
                last = record['log'][-1] if record['log'] else None
                if last and last.get('type') == 'note' and str(last.get('text', '')).startswith('Autopilot on:') and now - (parse_time(last.get('t')) or now) < timedelta(minutes=15):
                    record['log'].pop()
                record['log'].append({'t': iso(now), 'type': 'note', 'symbol': '', 'usd': 0,
                                      'text': f"Autopilot on: {RISK[after['risk']]['name']} level, ${after['budgetUsd']:,.0f} over {after['periodDays']} days, checking {every_text(after['everyHours'])}."})
            elif before['enabled'] and not after['enabled']:
                record['log'].append({'t': iso(now), 'type': 'note', 'symbol': '', 'usd': 0, 'text': 'Autopilot off. Its holdings stay until you sell them.'})
            save_item(user_id, record)
            return respond(200, {'success': True, 'allowed': True, 'options': options, **public(record, now, user_id)})
        if action == 'run':
            if not record['settings']['enabled']:
                return respond(400, {'error': 'Switch the autopilot on first'})
            if not record['settings']['screeners']:
                return respond(400, {'error': 'Choose at least one screener for it to buy from first'})
            last = parse_time(record['state'].get('lastRun'))
            if last and now - last < timedelta(minutes=RUN_NOW_COOLDOWN_MIN):
                return respond(429, {'error': f'It checked in a moment ago. Try again in {RUN_NOW_COOLDOWN_MIN} minutes'})
            summary = run_user(user_id, record, now, manual=True)
            save_item(user_id, record)
            return respond(200, {'success': True, 'allowed': True, 'options': options, 'summary': {k: summary.get(k) for k in ('bought', 'sold', 'decidedBy', 'conflict')}, **public(record, now, user_id)})
        return respond(400, {'error': 'Unknown action'})
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')
        return respond(500, {'error': 'Internal server error'})
