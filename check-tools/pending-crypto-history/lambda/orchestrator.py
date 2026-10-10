import json
import urllib.request
import urllib.parse
import time
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from decimal import Decimal

# Display wording for model output codes. StockIQ gives general information, not advice,
# so codes such as BUY / SELL are used internally but never shown.
_SIGNAL_LABELS = {
    'STRONG BUY': 'Strongly positive', 'BUY': 'Positive', 'MODERATE BUY': 'Slightly positive', 'CONSIDER': 'Slightly positive',
    'HOLD': 'Mixed', 'NEUTRAL': 'Mixed',
    'MODERATE SELL': 'Slightly negative', 'AVOID': 'Slightly negative', 'SELL': 'Negative', 'STRONG SELL': 'Strongly negative',
}
_HORIZON_LABELS = {
    'IMMEDIATE': 'Very short term', 'SHORT_TERM': 'Short term', 'SHORT-TERM': 'Short term', 'MEDIUM_TERM': 'Medium term',
    'MEDIUM-TERM': 'Medium term', 'LONG_TERM': 'Long term', 'LONG-TERM': 'Long term', 'DAY TRADE': 'Intraday', 'HOLD': 'n/a', 'AVOID': 'n/a',
}

def signal_label(code):
    # stock workers use underscores (STRONG_BUY, MODERATE_BUY ...), crypto workers use spaces;
    # an unknown code is shown as "Unrated" rather than guessed
    return _SIGNAL_LABELS.get(str(code or 'HOLD').replace('_', ' ').strip().upper(), 'Unrated')

def horizon_label(code):
    raw = str(code or '').strip()
    if not raw or raw == 'N/A':
        return 'n/a'
    return _HORIZON_LABELS.get(raw.upper(), raw)


# ---------------------------------------------------------------------------------------------------------
# Top-10 history
# A scheduled run of THIS function (EventBridge rule stockiq-coinspot-predictions-schedule) records which
# coins are in the top 10. A user's run only reads that record. Both use the same coin list and ranking, so
# the history line always describes the list the user is looking at.
# Table stockiq-coinspot-prediction-status, one row per coin (key: symbol) plus one marker row.
# Rows written by the old separate updater have no `last_seen` and are ignored.
# ---------------------------------------------------------------------------------------------------------
HISTORY_TABLE = 'stockiq-coinspot-prediction-status'
HISTORY_MARKER = '_last_check'                      # row holding the time and number of the last scheduled check
CHECK_MINUTES = 30                                  # keep in step with the EventBridge rule's schedule
STREAK_GAP_MINUTES = CHECK_MINUTES * 2 + 5          # a coin keeps its run in the top 10 across one missed check
HISTORY_STALE_MINUTES = CHECK_MINUTES * 3 + 10      # older than this: the schedule is not running, show no history
ESTABLISHED_HOURS = 1.0                             # 🟢 from this long in the top 10
MIN_COINS_SHARE = 0.8                               # do not record a check that ranked fewer coins than this
ENTRY_LOG_TABLE = 'stockiq-coinspot-predictions'    # permanent log: one row each time a coin enters the top 10
ENTRY_LOG_VERSION = 2                               # rows without this were written by the old updater: ignore them


def fmt_price(price):
    if price >= 1:
        return f"${price:.2f}"
    if price >= 0.001:
        return f"${price:.6f}"
    return f"${price:.10f}".rstrip('0')             # very small prices: keep the digits that matter


def _parse_time(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', ''))
    except Exception:
        return None


def log_top10_entry(dynamodb, coin, now, check_no, coins_ranked):
    """Keep a permanent record of a coin entering the top 10, so the ranking's track record can be measured
    later (what did coins do in the 24 hours / 7 days after they entered, compared with the average coin?).
    Rows are never updated or deleted. Key: symbol + prediction_time (the entry time, UTC)."""
    def num(value):
        try:
            return Decimal(repr(float(value)))          # no rounding: some coins trade far below a cent
        except Exception:
            return None
    item = {
        'symbol': coin['symbol'],
        'prediction_time': now.isoformat(),
        'log_version': ENTRY_LOG_VERSION,
        'ticker': coin.get('yahoo_ticker', ''),
        'entry_price': num(coin['price']),
        'entry_score': int(coin['score']),
        'entry_rank': int(coin.get('rank', 0)),
        'signal_code': str(coin.get('recommendation', '')),
        'change_24h': num(coin.get('change_24h')),
        'change_7d': num(coin.get('change_7d')),
        'change_30d': num(coin.get('change_30d')),
        'rsi': num(coin.get('rsi')),
        'volume_ratio': num(coin.get('volume_ratio')),
        'check_no': check_no,
        'coins_ranked': int(coins_ranked),
    }
    dynamodb.Table(ENTRY_LOG_TABLE).put_item(Item={k: v for k, v in item.items() if v is not None})


def record_top10_history(dynamodb, top10, now, coins_ranked):
    """Scheduled run: start or continue each top-10 coin's run in the top 10."""
    table = dynamodb.Table(HISTORY_TABLE)
    marker = table.get_item(Key={'symbol': HISTORY_MARKER}).get('Item') or {}
    check_no = int(marker.get('check_no', 0)) + 1
    continued, started = [], []
    for coin in top10:
        row = table.get_item(Key={'symbol': coin['symbol']}).get('Item') or {}
        last_seen = _parse_time(row.get('last_seen'))
        same_coin = row.get('ticker', '') == coin.get('yahoo_ticker', '')
        if last_seen and row.get('streak_start') and same_coin and (now - last_seen) <= timedelta(minutes=STREAK_GAP_MINUTES):
            item = {
                'streak_start': row['streak_start'],
                'streak_price': row['streak_price'],
                'streak_score': row['streak_score'],
                'streak_start_check': row.get('streak_start_check', check_no),
                'checks_in_top10': int(row.get('checks_in_top10', 1)) + 1,
            }
            continued.append(coin['symbol'])
        else:
            item = {
                'streak_start': now.isoformat(),
                'streak_price': Decimal(str(coin['price'])),
                'streak_score': int(coin['score']),
                'streak_start_check': check_no,
                'checks_in_top10': 1,
            }
            started.append(coin['symbol'])
            try:
                log_top10_entry(dynamodb, coin, now, check_no, coins_ranked)
            except Exception as e:                      # the log must never stop the history being recorded
                print(f"⚠️ Entry log failed for {coin['symbol']}: {e}")
        item.update({
            'symbol': coin['symbol'],
            'ticker': coin.get('yahoo_ticker', ''),
            'last_seen': now.isoformat(),
            'last_price': Decimal(str(coin['price'])),
            'last_score': int(coin['score']),
            'last_rank': int(coin.get('rank', 0)),
        })
        table.put_item(Item=item)
    table.put_item(Item={'symbol': HISTORY_MARKER, 'last_check': now.isoformat(), 'check_no': check_no,
                         'coins_ranked': int(coins_ranked)})
    print(f"🧠 Top-10 history check {check_no}: continued {continued}, new {started}")
    return {'check_no': check_no, 'continued': continued, 'new': started}


def read_top10_history(dynamodb, top10, now):
    """User run: describe how long each top-10 coin has been there. Returns False when there is no recent check."""
    table = dynamodb.Table(HISTORY_TABLE)
    marker = table.get_item(Key={'symbol': HISTORY_MARKER}).get('Item') or {}
    last_check = _parse_time(marker.get('last_check'))
    if not last_check or (now - last_check) > timedelta(minutes=HISTORY_STALE_MINUTES):
        print(f"⚠️ Top-10 history not used: last scheduled check was {marker.get('last_check', 'never')}")
        return False
    check_no = int(marker.get('check_no', 0))
    for coin in top10:
        row = table.get_item(Key={'symbol': coin['symbol']}).get('Item') or {}
        last_seen = _parse_time(row.get('last_seen'))
        start = _parse_time(row.get('streak_start'))
        current = (last_seen and start and row.get('ticker', '') == coin.get('yahoo_ticker', '')
                   and (now - last_seen) <= timedelta(minutes=STREAK_GAP_MINUTES))
        if not current:
            coin['prediction_status'] = 'NEW'
            coin['hours_in_top10'] = 0
            coin['prediction_message'] = "New in the top 10 (not there at the last check)"
            continue
        hours = max(0.0, (now - start).total_seconds() / 3600)
        start_price = float(row['streak_price'])
        start_score = int(row['streak_score'])
        change = ((coin['price'] - start_price) / start_price * 100) if start_price > 0 else 0.0
        checks_in = int(row.get('checks_in_top10', 1))
        checks_total = max(checks_in, check_no - int(row.get('streak_start_check', check_no)) + 1)
        score_diff = coin['score'] - start_score
        score_note = 'rising' if score_diff >= 2 else 'falling' if score_diff <= -2 else 'steady'
        duration = f"{hours:.1f}h" if hours >= 1 else f"{hours * 60:.0f}m"
        coin['prediction_status'] = 'ESTABLISHED' if hours >= ESTABLISHED_HOURS else 'RECENT'
        coin['is_predictive'] = hours >= ESTABLISHED_HOURS
        coin['hours_in_top10'] = round(hours, 2)
        coin['top10_since'] = start.isoformat() + 'Z'
        coin['prediction_message'] = (f"In the top 10 since {start.strftime('%d %b %H:%M')} UTC: "
                                      f"{fmt_price(start_price)} → {fmt_price(coin['price'])} ({change:+.1f}%)")
        coin['time_since_message'] = f"⏱️ {duration} in the top 10"
        coin['momentum_message'] = (f"Score then {start_score:+d}, now {coin['score']:+d} ({score_note}) · "
                                    f"in the top 10 at {checks_in} of {checks_total} checks since then")
    return True


def lambda_handler(event=None, context=None):
    run_started = time.time()
    print("🚀 CRYPTO ORCHESTRATOR - Analyzing ALL coins with proper ranking")
    print("📊 System: top coins by market cap, one single-coin call per coin across 54 worker functions")
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # The scheduled run arrives straight from EventBridge. A call through the public Function URL always has
    # 'requestContext' and 'body', so it can never be mistaken for one (and so can never write history).
    scheduled = (isinstance(event, dict) and 'requestContext' not in event and 'body' not in event
                 and (event.get('source') == 'aws.events' or event.get('scheduled_history_check') is True))
    print(f"⚙️ Mode: {'scheduled top-10 history check' if scheduled else 'user run (reads history, writes nothing)'}")

    # Coin list: the top coins by market cap (CoinGecko, 10 Oct 2026), each one checked against the price
    # source before being included: Yahoo's price for the ticker had to be within 0.8x-1.25x of CoinGecko's
    # price for that coin, with at least 60 days of history. Stablecoins and wrapped/staked tokens are left out.
    # Each entry is (symbol shown to the user, Yahoo ticker without "-USD"). Many coins share a symbol on Yahoo,
    # so e.g. SUI is SUI20947-USD and ARB is ARB11841-USD; the plain symbol would price a different coin.
    # To refresh: rebuild from CoinGecko /coins/markets and re-check every price (see site-overview.md).
    COINS = [
        ('BTC', 'BTC'), ('ETH', 'ETH'), ('BNB', 'BNB'), ('XRP', 'XRP'), ('SOL', 'SOL'), ('TRX', 'TRX'),
        ('ZEC', 'ZEC'), ('HYPE', 'HYPE32196'), ('DOGE', 'DOGE'), ('XMR', 'XMR'), ('WBT', 'WBT'), ('LINK', 'LINK'),
        ('ADA', 'ADA'), ('LEO', 'LEO'), ('XLM', 'XLM'), ('NEAR', 'NEAR'), ('BCH', 'BCH'), ('LTC', 'LTC'),
        ('CC', 'CC37263'), ('UNI', 'UNI7083'), ('AVAX', 'AVAX'), ('SUI', 'SUI20947'), ('BTW', 'BTW39158'), ('GRAM', 'GRAM'),
        ('HBAR', 'HBAR'), ('QNT', 'QNT'), ('XAUT', 'XAUT'), ('SHIB', 'SHIB'), ('TAO', 'TAO22974'), ('CRO', 'CRO'),
        ('ENA', 'ENA'), ('OKB', 'OKB'), ('AAVE', 'AAVE'), ('PUMP', 'PUMP36507'), ('ONDO', 'ONDO'), ('DOT', 'DOT'),
        ('WLD', 'WLD'), ('PAXG', 'PAXG'), ('WLFI', 'WLFI33251'), ('ICP', 'ICP'), ('MORPHO', 'MORPHO34104'), ('PEPE', 'PEPE24478'),
        ('HTX', 'HTX'), ('BGB', 'BGB'), ('ETC', 'ETC'), ('ARB', 'ARB11841'), ('JST', 'JST'), ('KAS', 'KAS'),
        ('GT', 'GT'), ('ATOM', 'ATOM'), ('VVV', 'VVV35509'), ('ALGO', 'ALGO'), ('KCS', 'KCS'), ('RENDER', 'RENDER'),
        ('LIT', 'LIT39125'), ('FIL', 'FIL'), ('NEXO', 'NEXO'), ('AERO', 'AERO29270'), ('ZRO', 'ZRO26997'), ('NIGHT', 'NIGHT'),
        ('STX', 'STX4847'), ('APT', 'APT21794'), ('CAKE', 'CAKE'), ('XDC', 'XDC'), ('INJ', 'INJ'), ('PYTH', 'PYTH'),
        ('ETHFI', 'ETHFI'), ('VET', 'VET'), ('DASH', 'DASH'), ('RAY', 'RAY'), ('AKE', 'AKE'), ('BDX', 'BDX'),
        ('FLR', 'FLR'), ('CRV', 'CRV'), ('DRV', 'DRV35014'), ('STRK', 'STRK'), ('KAU', 'KAU24382'), ('TRUMP', 'TRUMP35336'),
        ('PENGU', 'PENGU34466'), ('FET', 'FET'), ('YLDS', 'YLDS'), ('VIRTUAL', 'VIRTUAL'), ('TIA', 'TIA'), ('GRASS', 'GRASS32956'),
        ('SEI', 'SEI'), ('A7A5', 'A7A5'), ('BSV', 'BSV'), ('XPL', 'XPL'), ('HASH', 'HASH19960'), ('PENDLE', 'PENDLE'),
        ('PIEVERSE', 'PIEVERSE'), ('FF', 'FF38482'), ('UB', 'UB38339'), ('SPX', 'SPX28081'), ('LDO', 'LDO'), ('KAIA', 'KAIA'),
        ('SUN', 'SUN'), ('XTZ', 'XTZ'), ('BP', 'BP39686'), ('DCR', 'DCR'), ('APEPE', 'APEPE27048'), ('GNO', 'GNO'),
        ('OHM', 'OHM'), ('BONK', 'BONK'), ('GRT', 'GRT6719'), ('MON', 'MON'), ('KITE', 'KITE'), ('OP', 'OP'),
        ('LUNC', 'LUNC'), ('JTO', 'JTO'), ('SYRUP', 'SYRUP'), ('AR', 'AR'), ('ENS', 'ENS'), ('CFX', 'CFX'),
        ('FLOKI', 'FLOKI'), ('CARDS', 'CARDS38283'), ('JASMY', 'JASMY'), ('PONS', 'PONS'), ('IOTA', 'IOTA'), ('ZBCN', 'ZBCN'),
        ('MET', 'MET38353'), ('RUNE', 'RUNE'), ('KOGE', 'KOGE'), ('THETA', 'THETA'), ('AKT', 'AKT'), ('EIGEN', 'EIGEN'),
        ('TWT', 'TWT'), ('WIF', 'WIF'), ('AXS', 'AXS'), ('SAND', 'SAND'), ('KMNO', 'KMNO'), ('SHFL', 'SHFL'),
        ('CVX', 'CVX'), ('USELESS', 'USELESS36828'), ('EURCV', 'EURCV'), ('ZAMA', 'ZAMA'), ('2Z', '2Z'), ('TRAC', 'TRAC'),
        ('BAT', 'BAT'), ('USAT', 'USAT'), ('MANA', 'MANA'), ('MX', 'MX'), ('NPC', 'NPC27960'), ('FLUID', 'FLUID'),
        ('NEO', 'NEO'), ('XCN', 'XCN18679'), ('IMX', 'IMX10603'), ('FARTCOIN', 'FARTCOIN'), ('BORG', 'BORG'), ('CHZ', 'CHZ'),
        ('STRCX', 'STRCX'), ('SENT', 'SENT38868'), ('BTSE', 'BTSE'), ('RAIL', 'RAIL'), ('GOMINING', 'GOMINING'), ('BR', 'BR36063'),
        ('ZK', 'ZK24091'), ('ORCA', 'ORCA'), ('SUPER', 'SUPER8290'), ('XEC', 'XEC'), ('AIOZ', 'AIOZ'), ('APE', 'APE'),
        ('GEOD', 'GEOD'), ('SFP', 'SFP'), ('1INCH', '1INCH'), ('ULTIMA', 'ULTIMA'), ('SN51', 'SN51'), ('SNX', 'SNX'),
        ('JPYC', 'JPYC40123'), ('META', 'META38146'), ('GLM', 'GLM'), ('ATH', 'ATH30083'), ('SHX', 'SHX'), ('OZO', 'OZO'),
        ('EDGE', 'EDGE39720'), ('SOSO', 'SOSO'), ('EGLD', 'EGLD'), ('AWE', 'AWE'), ('BC', 'BC35067'), ('PLUME', 'PLUME'),
        ('PEAQ', 'PEAQ'), ('SN64', 'SN64'), ('ZEN', 'ZEN'), ('SKR', 'SKR39377'), ('MSTRX', 'MSTRX'), ('DYDX', 'DYDX'),
        ('DBR', 'DBR31528'), ('RLB', 'RLB'), ('GENIUS', 'GENIUS'), ('CASHCAT', 'CASHCAT'), ('OPEN', 'OPEN37456'), ('ANVL', 'ANVL'),
        ('MINA', 'MINA'), ('ZRX', 'ZRX'), ('HNT', 'HNT'), ('QTUM', 'QTUM'), ('NMR', 'NMR'), ('RSR', 'RSR'),
        ('DOG', 'DOG30933'), ('FUN', 'FUN'), ('ZANO', 'ZANO'), ('PROM', 'PROM'), ('US', 'US'), ('WEMIX', 'WEMIX'),
        ('MARSCOIN', 'MARSCOIN'), ('CRCLX', 'CRCLX'), ('KSM', 'KSM'), ('QRL', 'QRL'), ('MELANIA', 'MELANIA35347'), ('AI', 'AI40925'),
        ('ARKM', 'ARKM'), ('WAL', 'WAL36119'), ('YZY', 'YZY'), ('ORDI', 'ORDI'), ('VELO', 'VELO'), ('GAS', 'GAS'),
        ('QUBIC', 'QUBIC'), ('LPT', 'LPT'), ('GGBR', 'GGBR'), ('ZIG', 'ZIG'), ('SN4', 'SN4'), ('YFI', 'YFI'),
        ('COW', 'COW19269'), ('RIF', 'RIF'), ('KNTQ', 'KNTQ'), ('UAI', 'UAI38841'), ('RED', 'RED21707'), ('ESP', 'ESP39548'),
        ('RLC', 'RLC'), ('ZETA', 'ZETA'), ('OMI', 'OMI19075'), ('MUBARAK', 'MUBARAK'), ('KAITO', 'KAITO'), ('KAVA', 'KAVA'),
        ('BERA', 'BERA'), ('TSLAX', 'TSLAX'), ('FT', 'FT38544'), ('TFUEL', 'TFUEL'), ('HOT', 'HOT'), ('BOME', 'BOME'),
        ('RE', 'RE'), ('TAG', 'TAG34958'), ('DATA', 'DATA35626'), ('XAUM', 'XAUM'), ('DGB', 'DGB'), ('VTHO', 'VTHO'),
        ('GAL', 'GAL11877'), ('UNP', 'UNP'), ('BANANAS31', 'BANANAS31'), ('ZIL', 'ZIL'), ('MERL', 'MERL'), ('NILA', 'NILA'),
        ('NXPC', 'NXPC'), ('TURBO', 'TURBO'), ('SUSHI', 'SUSHI'), ('LINEA', 'LINEA'), ('BABY', 'BABY32198'), ('SPYX', 'SPYX'),
        ('ELG', 'ELG'), ('XPR', 'XPR'), ('DEXE', 'DEXE'), ('AXL', 'AXL17799'), ('ROSE', 'ROSE'), ('CKB', 'CKB'),
        ('ALLO', 'ALLO'), ('ENJ', 'ENJ'), ('GPS', 'GPS'), ('BAN', 'BAN33881'), ('METAL', 'METAL21769'), ('ARC', 'ARC34926'),
        ('ONT', 'ONT'), ('IO', 'IO29835'), ('BIO', 'BIO34812'), ('AMP', 'AMP'), ('SNEK', 'SNEK25264'), ('NOS', 'NOS'),
        ('ASTR', 'ASTR'), ('DIEM', 'DIEM'), ('CTC', 'CTC'), ('PC', 'PC36834'), ('LCX', 'LCX'), ('ANSEM', 'ANSEM'),
        ('EDU', 'EDU24613'), ('CELO', 'CELO'), ('ID', 'ID21846'), ('AB', 'AB'), ('0G', '0G'), ('HUMA', 'HUMA'),
        ('COAI', 'COAI38489'), ('SN44', 'SN44'), ('SN53', 'SN53'), ('ARX', 'ARX39970'), ('BLUR', 'BLUR'), ('ALT', 'ALT29073'),
        ('ELF', 'ELF'), ('BRZ', 'BRZ'), ('FONQ', 'FONQ'), ('ARRR', 'ARRR'), ('TRB', 'TRB'), ('SN120', 'SN120'),
        ('CX', 'CX35735'), ('JELLYJELLY', 'JELLYJELLY'), ('CFG', 'CFG'), ('TPT', 'TPT'), ('XVS', 'XVS'), ('FLOW', 'FLOW'),
        ('BRETT', 'BRETT29743'), ('LSK', 'LSK'), ('DEEP', 'DEEP33391'), ('POLYX', 'POLYX'), ('WIN', 'WIN'), ('GEKKO', 'GEKKO'),
        ('XYO', 'XYO'), ('NOCK', 'NOCK'), ('AP3X', 'AP3X'), ('PNUT', 'PNUT'), ('PHA', 'PHA'), ('BIM', 'BIM'),
        ('AVNT', 'AVNT'), ('API3', 'API3'), ('RAVE', 'RAVE38967'), ('SC', 'SC'), ('SPCXX', 'SPCXX'), ('HOLO', 'HOLO38309'),
        ('MEGA', 'MEGA38770'), ('DUSK', 'DUSK'), ('DOS', 'DOS'), ('ANKR', 'ANKR'), ('ALEO', 'ALEO'), ('XNO', 'XNO'),
        ('XVG', 'XVG'), ('AIAT', 'AIAT'), ('MASK', 'MASK8536'), ('NOT', 'NOT'), ('HDX', 'HDX'), ('AZTEC', 'AZTEC'),
        ('NVDAX', 'NVDAX'), ('ACU', 'ACU36492'), ('FOLKS', 'FOLKS'), ('CSPR', 'CSPR'), ('NIL', 'NIL35702'), ('REQ', 'REQ'),
        ('ME', 'ME32197'), ('ARK', 'ARK'), ('VVS', 'VVS'), ('CATI', 'CATI'), ('FB', 'FB32941'), ('ALCH', 'ALCH'),
        ('LION', 'LION35954'), ('CCD', 'CCD'), ('ZCHF', 'ZCHF'), ('ONG', 'ONG3217'), ('BAND', 'BAND'), ('KTA', 'KTA'),
        ('SXT', 'SXT'), ('SYN', 'SYN12147'), ('SSV', 'SSV'), ('MEW', 'MEW30126'), ('QQQX', 'QQQX'), ('RPL', 'RPL'),
        ('ATOS', 'ATOS'), ('GOHOME', 'GOHOME'), ('MOODENG', 'MOODENG33093'), ('KUB', 'KUB'), ('GOOGLX', 'GOOGLX'), ('NES', 'NES'),
        ('PEOPLE', 'PEOPLE'), ('SN3', 'SN3'), ('GWEI', 'GWEI'), ('MOCA', 'MOCA31526'), ('PROVE', 'PROVE'), ('PCI', 'PCI'),
        ('AUKI', 'AUKI'), ('MAGMA', 'MAGMA'), ('COTI', 'COTI'), ('UMA', 'UMA'), ('SNT', 'SNT'), ('BOLD', 'BOLD'),
        ('NKYC', 'NKYC'), ('EURI', 'EURI'), ('UP', 'UP39665'), ('BFC', 'BFC7817'), ('HEZ', 'HEZ'), ('RVN', 'RVN'),
        ('SB', 'SB'), ('SAHARA', 'SAHARA'), ('MOOLAH', 'MOOLAH36818'), ('VENOM', 'VENOM'), ('MNGO', 'MNGO'), ('GIGGLE', 'GIGGLE38470'),
        ('MEME', 'MEME'), ('ORBS', 'ORBS'), ('XPIN', 'XPIN'), ('REZ', 'REZ'), ('PRO', 'PRO'), ('OCEAN', 'OCEAN'),
        ('POWR', 'POWR'), ('IOTX', 'IOTX'), ('NEIRO', 'NEIRO32521'), ('ETN', 'ETN'), ('ABEY', 'ABEY'), ('YFSX', 'YFSX'),
        ('LISTA', 'LISTA'), ('AIPF', 'AIPF'), ('SN9', 'SN9'), ('SKYAI', 'SKYAI'), ('FLUX', 'FLUX'), ('SQD', 'SQD'),
        ('MBG', 'MBG'), ('STEEM', 'STEEM'), ('EUL', 'EUL'), ('VELVET', 'VELVET'), ('SRX', 'SRX'), ('OPG', 'OPG'),
        ('HSK', 'HSK'), ('SOMI', 'SOMI'), ('CXO', 'CXO'), ('BULLA', 'BULLA36769'), ('B3', 'B3'), ('AT', 'AT38757'),
        ('COINDEPO', 'COINDEPO'), ('CTSI', 'CTSI'), ('NOW', 'NOW'), ('BORA', 'BORA'), ('SKL', 'SKL'), ('BNKR', 'BNKR37545'),
        ('SENTIS', 'SENTIS'), ('TORN', 'TORN'), ('BEAT', 'BEAT38837'), ('ILV', 'ILV'), ('BNT', 'BNT'), ('CPOOL', 'CPOOL'),
        ('ZORA', 'ZORA35931'), ('NEET', 'NEET'), ('ACX', 'ACX22620'), ('XT', 'XT'), ('DIME', 'DIME39656'), ('GPT', 'GPT36614'),
        ('MANTA', 'MANTA'), ('ABT', 'ABT'), ('IOST', 'IOST'), ('HIVE', 'HIVE'), ('SWFTC', 'SWFTC'), ('ETHW', 'ETHW'),
        ('XCH', 'XCH'), ('SN68', 'SN68'), ('IRYS', 'IRYS'), ('MVL', 'MVL'), ('DEP', 'DEP'), ('JCT', 'JCT'),
        ('MTL', 'MTL'), ('ZEREBRO', 'ZEREBRO'), ('PUNDIX', 'PUNDIX'), ('MANTRA', 'MANTRA'), ('TRUTH', 'TRUTH38178'), ('KGEN', 'KGEN'),
        ('BDCA', 'BDCA'), ('XP', 'XP36056'), ('XAN', 'XAN'), ('SPACE', 'SPACE38136'), ('EWT', 'EWT'), ('KNC', 'KNC'),
        ('AUCTION', 'AUCTION'), ('UQC', 'UQC'), ('CARV', 'CARV'), ('VATRENI', 'VATRENI'), ('OSMO', 'OSMO'), ('EDEL', 'EDEL38966'),
        ('METIS', 'METIS'), ('ARDR', 'ARDR'), ('PREOPAI', 'PREOPAI'), ('OGN', 'OGN'), ('TNSR', 'TNSR'), ('EDEN', 'EDEN38513'),
        ('FLOCK', 'FLOCK'), ('UTYA', 'UTYA'), ('WAXP', 'WAXP'), ('TGBP', 'TGBP'), ('TIG', 'TIG34102'), ('WAVES', 'WAVES'),
        ('ZEST', 'ZEST'), ('EV', 'EV39394'), ('DAG', 'DAG'), ('FLIP', 'FLIP'), ('BUCK', 'BUCK31225'), ('GRVT', 'GRVT'),
        ('ZBT', 'ZBT38427'), ('WOULD', 'WOULD'), ('SIREN', 'SIREN'), ('CVC', 'CVC'), ('AEVO', 'AEVO'), ('VR', 'VR'),
        ('CYS', 'CYS39071'), ('RHEA', 'RHEA'), ('HEMI', 'HEMI'), ('AUDIO', 'AUDIO'), ('CETUS', 'CETUS'), ('FOGO', 'FOGO'),
        ('ICNT', 'ICNT'), ('KEEP', 'KEEP'), ('MLK', 'MLK'), ('AGRS', 'AGRS'), ('ERG', 'ERG'), ('BSB', 'BSB38889'),
        ('LON', 'LON'), ('MOVR', 'MOVR'), ('TAKE', 'TAKE38175'), ('STRAX', 'STRAX'), ('BIGTIME', 'BIGTIME'), ('PYBOBO', 'PYBOBO'),
        ('HYPER', 'HYPER36281'), ('BROCCOLI', 'BROCCOLI35749'), ('USUAL', 'USUAL'), ('CELR', 'CELR'), ('AIC', 'AIC32968'), ('WOO', 'WOO'),
        ('MPLX', 'MPLX'), ('RIVER', 'RIVER'), ('WWB', 'WWB'), ('AIOT', 'AIOT'), ('IQ', 'IQ'), ('BILL', 'BILL39545'),
        ('INIT', 'INIT'), ('SLP', 'SLP'), ('LQTY', 'LQTY'), ('CHR', 'CHR'), ('BNX', 'BNX'), ('SN93', 'SN93'),
        ('BURN', 'BURN30460'), ('SOLV', 'SOLV'), ('ZYLO', 'ZYLO'), ('ANTFUN', 'ANTFUN'), ('SN56', 'SN56'), ('BANK', 'BANK36296'),
        ('SN75', 'SN75'), ('IXS', 'IXS'), ('ACE', 'ACE28674'), ('MY', 'MY'), ('SHARE', 'SHARE39955'), ('SBC', 'SBC26456'),
    ]

    worker_urls = [
        'https://yz4wgbaiyt4dz63o7zporpxeaa0foivx.lambda-url.us-east-1.on.aws/',  # 1
        'https://42s6qdfsrkszoyqj6w5bgr3s6u0nspqq.lambda-url.us-east-1.on.aws/',  # 2
        'https://xjvbgrwttpj7kcytm5ddwy7tt40vqzze.lambda-url.us-east-1.on.aws/',  # 3
        'https://lgijndtq7ewr2lmyrswdstnpvi0netpw.lambda-url.us-east-1.on.aws/',  # 4
        'https://hmtko2skeg75blcxqutogigcvy0ntkec.lambda-url.us-east-1.on.aws/',  # 5
        'https://4a7hfulggyeps7k7hj77adxrpq0kdfqg.lambda-url.us-east-1.on.aws/',  # 6
        'https://hf3u36qg5aqrdv7gptkuaf7jh40evdze.lambda-url.us-east-1.on.aws/',  # 7
        'https://pnwisraruzcpqe3qe7d7vmzu2e0dgrpm.lambda-url.us-east-1.on.aws/',  # 8
        'https://qktdyjwut2lkvwfmmdfuexr33i0xcurs.lambda-url.us-east-1.on.aws/',  # 9
        'https://g5j55xk5lzhjnnyr7y6prqpljy0tlqkx.lambda-url.us-east-1.on.aws/',  # 10
        'https://rksirshiz7na7euikh2yxgxv5u0ptnkb.lambda-url.us-east-1.on.aws/',  # 11
        'https://o44c7mdftemfbqgke4p376q2qa0sghly.lambda-url.us-east-1.on.aws/',  # 12
        'https://jmwrrbr6xrgf42notwv234pp5e0vwnxq.lambda-url.us-east-1.on.aws/',  # 13
        'https://xqzmcavblj2nszw4hc7es5ebd40egggz.lambda-url.us-east-1.on.aws/',  # 14
        'https://oc7vm7dmjyjylsrzo3ihc2gl440kywzh.lambda-url.us-east-1.on.aws/',  # 15
        'https://t74yqsnigpnpykey7bbph2xriq0zsupv.lambda-url.us-east-1.on.aws/',  # 16
        'https://6ks6qmi2jhzhya4qkmsu4h53340lrnht.lambda-url.us-east-1.on.aws/',  # 17
        'https://iqacrdbony762obypmcdshflu40seodc.lambda-url.us-east-1.on.aws/',  # 18
        'https://f2ch4df3razl4iq6nhi3fx4pfy0rezrq.lambda-url.us-east-1.on.aws/',  # 19
        'https://wivjg5naxgnpcegeimadx5mac40fycha.lambda-url.us-east-1.on.aws/',  # 20
        'https://7hedis4qzuqffimgrwut5nahum0gojxv.lambda-url.us-east-1.on.aws/',  # 21
        'https://w2gyerbb3an74v5o4mszioxzcy0dsirm.lambda-url.us-east-1.on.aws/',  # 22
        'https://5jcl2g42j7qq4tn2gkutgiguga0gkjgp.lambda-url.us-east-1.on.aws/',  # 23
        'https://pb7rno2ujzy5bhiflwp5lkfniq0fgzol.lambda-url.us-east-1.on.aws/',  # 24
        'https://jesemnyoethppyjg3tcvmyrb5q0nhykg.lambda-url.us-east-1.on.aws/',  # 25
        'https://yfo27hj5g2m2lg2oe2c6weu23a0isjkc.lambda-url.us-east-1.on.aws/',  # 26
        'https://kcrx2dqjkjzucnz7yzpqcy3c7m0hjgvo.lambda-url.us-east-1.on.aws/',  # 27
        'https://qiqc4u7iohqcmfme6qjzhoamhi0vjodk.lambda-url.us-east-1.on.aws/',  # 28
        'https://tqzh2eh3aioidkw4y2nnjnmn6e0exzbg.lambda-url.us-east-1.on.aws/',  # 29
        'https://6okdvhjqmnrgg2em2sgjcjapri0mxnpx.lambda-url.us-east-1.on.aws/',  # 30
        'https://p7i7wjt4k2e3qy6jjhskdbrthq0mieft.lambda-url.us-east-1.on.aws/',  # 31
        'https://3o5qycqu5gkii4l6i72nwr5mve0hlnvb.lambda-url.us-east-1.on.aws/',  # 32
        'https://zf6ahie32bm3akchiooj5clwqq0bgmlj.lambda-url.us-east-1.on.aws/',  # 33
        'https://2kq7slfzjyromdju4utydnddai0fptqa.lambda-url.us-east-1.on.aws/',  # 34
        'https://w73pyxjiea5xfks7ogmq4ucbqq0jlhvi.lambda-url.us-east-1.on.aws/',  # 35
        'https://bmimmu4alwcx7er6sonkjdcie40zncfz.lambda-url.us-east-1.on.aws/',  # 36
        'https://4m7xqzv2f47eend5ky7njpbnle0gxvri.lambda-url.us-east-1.on.aws/',  # 37
        'https://4wmicc5efuxt4mduvflrh5ugpe0weqvf.lambda-url.us-east-1.on.aws/',  # 38
        'https://3jftb3ogkknnxvrfcdiqx547qa0kwcpc.lambda-url.us-east-1.on.aws/',  # 39
        'https://mrrmwtoxtlgzrjtjpvltprq3ra0qyvas.lambda-url.us-east-1.on.aws/',  # 40
        'https://zur6azefrs3becakhtbzayq7za0xdkdy.lambda-url.us-east-1.on.aws/',  # 41
        'https://p55sp6yjepzapphukghiylhy4e0imrgo.lambda-url.us-east-1.on.aws/',  # 42
        'https://7r3ufoc77ebkdjna4fncr7776i0tqbka.lambda-url.us-east-1.on.aws/',  # 43
        'https://zdaxzaz7lc4hyfez2ldrcjkdl40acckb.lambda-url.us-east-1.on.aws/',  # 44
        'https://t7dooxpa4kt34v24a7di4sve640rlkxs.lambda-url.us-east-1.on.aws/',  # 45
        'https://mbyu5oiqzo3cl3toxbs444urvq0zrqvx.lambda-url.us-east-1.on.aws/',  # 46
        'https://htbmqldvtp4g6d4m3tmxgjirna0dsqho.lambda-url.us-east-1.on.aws/',  # 47
        'https://4mgjwrqrkqxrydo3xfgl3j3qj40ubnlu.lambda-url.us-east-1.on.aws/',  # 48
        'https://yzodprguj524e42w46engj6yry0sgbkd.lambda-url.us-east-1.on.aws/',  # 49
        'https://sfupc4guzpvh6a3jl22oc7qg6y0wokoh.lambda-url.us-east-1.on.aws/',  # 50
        'https://4mjthlkcbkrjuih7izkxxis5jq0iylrz.lambda-url.us-east-1.on.aws/',  # 51
        'https://itm5zrkanirobkqkuqynurnwom0wpvns.lambda-url.us-east-1.on.aws/',  # 52
        'https://wxgkp6xldxm3kygvnv2h2nuxpm0rbqve.lambda-url.us-east-1.on.aws/',  # 53
        'https://n36vyw5k4nc6kimznyekpr2jly0eqwzm.lambda-url.us-east-1.on.aws/'   # 54
    ]

    def call_worker(task_id, url, display_symbol, yahoo_ticker):
        """Analyse one coin through a worker's single-coin mode.

        The workers' batch mode ignores the coins it is sent and uses a list built into the worker code, so the
        orchestrator drives the list itself, one coin per call, spread across the worker functions."""
        payload = json.dumps({'single_coin': yahoo_ticker}).encode()
        last_error = None
        # If one worker function is unavailable, try the same coin on the next one
        for attempt_url in (url, worker_urls[(worker_urls.index(url) + 1) % len(worker_urls)]):
            try:
                req = urllib.request.Request(attempt_url, data=payload, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=45) as response:
                    result = json.loads(response.read().decode())
                    if 'body' in result:
                        result = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
                    coins = result.get('coins', [])
                    for coin in coins:
                        coin['symbol'] = display_symbol          # show the familiar symbol, not Yahoo's numbered ticker
                        coin['yahoo_ticker'] = yahoo_ticker
                        coin.setdefault('hours_since_prediction', None)
                    return {'worker_id': task_id, 'coins': coins, 'status': 'success'}
            except Exception as e:
                last_error = e
        print(f"❌ {display_symbol} ({yahoo_ticker}) failed: {str(last_error)}")
        return {'worker_id': task_id, 'coins': [], 'status': 'error'}

    # Analyse every coin in parallel, spread round-robin over the worker functions
    all_coins = []
    successful_workers = 0
    failed_workers = []
    successful_worker_ids = []

    with ThreadPoolExecutor(max_workers=60) as executor:
        future_to_worker = {
            executor.submit(call_worker, i + 1, worker_urls[i % len(worker_urls)], display, ticker): i + 1
            for i, (display, ticker) in enumerate(COINS)
        }
        for future in as_completed(future_to_worker):
            result = future.result()
            if result['status'] == 'success':
                all_coins.extend(result['coins'])
                successful_workers += 1
                successful_worker_ids.append(result['worker_id'])
            else:
                failed_workers.append(result['worker_id'])

    total_expected = len(COINS)
    print(f"⚡ {successful_workers}/{total_expected} coin calls completed across {len(worker_urls)} worker functions")
    print(f"📊 Crypto analysis: {len(all_coins)}/{total_expected} coins ({((len(all_coins)/total_expected)*100):.1f}%)")

    # Leave out coins the price source returned nothing for
    coins_returned = len(all_coins)
    no_price_count = sum(1 for c in all_coins if not c.get('price') or c.get('price') <= 0) + (total_expected - coins_returned)
    mismatch_count = 0  # the list is pre-checked, so there are no known wrong matches left to exclude
    all_coins = [c for c in all_coins if c.get('price') and c.get('price') > 0]
    print(f"🧹 Left out {no_price_count} coins with no price data ({len(all_coins)} of {total_expected} kept)")

    # Remove duplicates by symbol, keeping highest score, and filter out BTG
    seen_symbols = {}
    unique_coins = []
    for coin in all_coins:
        symbol = coin.get('symbol')
        if symbol == 'BTG':  # Skip BTG
            continue
        if symbol not in seen_symbols or coin.get('score', 0) > seen_symbols[symbol].get('score', 0):
            seen_symbols[symbol] = coin
    
    unique_coins = list(seen_symbols.values())
    
    # Sort by score; equal scores keep the coin list's order (largest market cap first) so the ranking is
    # the same on every run instead of depending on which worker answered first
    list_position = {display: i for i, (display, _ticker) in enumerate(COINS)}
    unique_coins.sort(key=lambda x: (-x.get('score', 0), list_position.get(x.get('symbol'), len(COINS))))
    for i, coin in enumerate(unique_coins, 1):
        coin['rank'] = i
    
    all_coins = unique_coins
    
    now = datetime.utcnow()
    top10 = all_coins[:10]
    for coin in all_coins:
        coin['prediction_status'] = 'NOT_TOP_10'
        coin['is_predictive'] = False
        coin['hours_in_top10'] = None

    if scheduled:
        if len(all_coins) < total_expected * MIN_COINS_SHARE:
            print(f"⚠️ Only {len(all_coins)} of {total_expected} coins ranked - history check not recorded")
            return {'statusCode': 200, 'body': json.dumps({'status': 'skipped', 'coins_ranked': len(all_coins)})}
        try:
            summary = record_top10_history(dynamodb, top10, now, len(all_coins))
        except Exception as e:
            print(f"❌ Top-10 history check failed: {e}")
            raise
        return {'statusCode': 200, 'body': json.dumps({'status': 'history_recorded', 'coins_ranked': len(all_coins),
                                                       'seconds': round(time.time() - run_started, 1), **summary})}

    history_available = False
    try:
        history_available = read_top10_history(dynamodb, top10, now)
    except Exception as e:
        print(f"⚠️ Top-10 history lookup failed: {e}")
    if not history_available:
        for coin in top10:
            coin['prediction_status'] = 'NO_HISTORY'

    print("📊 Orchestrator aggregation complete - generating comprehensive report...")
    
    # Generate comprehensive detailed report in HTML format
    report_lines = [
        # data-top10-tickers: the price-source ticker of each top-10 coin, read by the dashboard's performance tracker
        "<div style='font-family: monospace; line-height: 1.4; white-space: pre-wrap;' data-top10-tickers='"
        + ",".join(f"{c['symbol']}:{c.get('yahoo_ticker', c['symbol'])}" for c in all_coins[:10]) + "'>",
        "=" * 60,
        "₿ CRYPTO SCREENER RESULTS (TOP COINS BY MARKET CAP)",
        "=" * 60,
        "",
        "Screening Universe: Top crypto by market cap (USD)",
        f"Coins Analyzed: {len(all_coins)} (USD pricing)",
        f"Coin list: top coins by market cap, each checked against the price source. Not included today: {no_price_count} with no price data",
        f"Processing Time: {time.time() - run_started:.0f}s",
        f"Analysis Date: <span id='analysis-timestamp'>{now.strftime('%d/%m/%Y, %H:%M')} UTC</span>",
        "📈 Technical Analysis: MACD, RSI, Bollinger Bands, Stochastic, Volume, Momentum",
        ("(🟢 = in the top 10 for an hour or more   🟡 = under an hour   🔵 = new at this run. "
         f"The top 10 is recorded every {CHECK_MINUTES} minutes.)") if history_available
        else "(🔵 = top-10 history is not available for this run)",
        "",
        "🔥 TOP 10 BY SCORE:"
    ]
    
    # Always show top 10 coins in comprehensive report
    # Frontend slider will handle filtering by time threshold
    display_coins = all_coins[:10]
    
    # Top 10 list with prediction context
    for i, coin in enumerate(display_coins, 1):
        price_str = fmt_price(coin['price'])
        prediction_icon = {'ESTABLISHED': '🟢', 'RECENT': '🟡'}.get(coin.get('prediction_status'), '🔵')
        report_lines.append(f"{i:2d}. {prediction_icon} {coin['symbol']:<8} {price_str:<12} | {signal_label(coin['recommendation']):<17} | Score: {coin['score']:+d}")
        if coin.get('prediction_message'):
            report_lines.append(f"     {coin['prediction_message']}")
        if coin.get('time_since_message'):
            report_lines.append(f"     {coin['time_since_message']}")
        if coin.get('momentum_message'):
            report_lines.append(f"     {coin['momentum_message']}")
        report_lines.append("")
    
    report_lines.extend([
        "",
        "ℹ️ Prices come from Yahoo Finance. Some symbols are shared by more than one coin, so check the price matches the coin you mean.",
        "General information only, not financial advice.",
        "",
        "✅ COMPREHENSIVE ANALYSIS COMPLETE!",
        "</div>"
    ])
    
    report = "\n".join(report_lines)
    
    print("✅ Comprehensive report generated!")
    print(f"📊 Total coins in final ranking: {len(all_coins)}")
    print("📊 Orchestrator completed successfully!")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'coins': all_coins,
            'total_coins': len(all_coins),
            'successful_workers': successful_workers,
            'report': report,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        })
    }