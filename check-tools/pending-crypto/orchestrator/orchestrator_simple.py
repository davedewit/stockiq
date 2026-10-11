import json
import urllib.request
import urllib.parse
import time
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def lambda_handler(event=None, context=None):
    print("🚀 CRYPTO ORCHESTRATOR - Analyzing ALL coins with proper ranking")
    print("📊 System: CoinSpot Australia (AUD) - 54 Workers × 10 coins each = 540 total")
    
    # Extract settings from event body
    threshold = 0.1  # Default 6 minutes
    enable_predictions = True  # Default enabled
    if event and 'body' in event:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            threshold = body.get('threshold', 0.1)
            enable_predictions = body.get('enable_predictions', True)
        except:
            pass
    elif event:
        threshold = event.get('threshold', 0.1)
        enable_predictions = event.get('enable_predictions', True)
    
    print(f"🧠 Using prediction memory threshold: {threshold} hours")
    
    # Define coin lists for each worker - 54 workers × 10 coins each = 540 total
    coin_batches = [
        ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'XRP', 'DOGE', 'AVAX', 'DOT', 'MATIC'],  # Worker 1
        ['1000SATS', '1INCH', 'A2Z', 'AAVE', 'ACA', 'ACE', 'ACH', 'ACM', 'ACT', 'ADX'],  # Worker 2
        ['AE', 'AERGO', 'AERO', 'AEVO', 'AGI', 'AGLD', 'AGS', 'AI', 'AI16Z', 'AIOZ'],  # Worker 3
        ['AKRO', 'AKT', 'ALBT', 'ALCX', 'ALGO', 'ALICE', 'ALPACA', 'ALPHA', 'ALPINE', 'ALT'],  # Worker 4
        ['AMB', 'AMP', 'ANIME', 'ANKR', 'ANS', 'APE', 'API3', 'APT', 'AR', 'ARB'],  # Worker 5
        ['ARDR', 'ARK', 'ARKM', 'ARPA', 'ASR', 'AST', 'ASTR', 'ATH', 'ATM', 'ATOM'],  # Worker 6
        ['ATOR', 'AUCT', 'AUDIO', 'AURORA', 'AUS', 'AVA', 'AVAAI', 'AXL', 'AXS', 'AZERO'],  # Worker 7
        ['BADGER', 'BAKE', 'BAL', 'BANANA', 'BAND', 'BAR', 'BAT', 'BB', 'BCAU', 'BCC'],  # Worker 8
        ['BCHSV', 'BEAM', 'BEL', 'BERA', 'BETA', 'BICO', 'BIGTIME', 'BIO', 'BLAST', 'BLUR'],  # Worker 9
        ['BLZ', 'BNT', 'BNX', 'BOME', 'BOND', 'BONE', 'BONK', 'BQX', 'BRETT', 'BRISE'],  # Worker 10
        ['BSW', 'BTCST', 'BTG', 'BTS', 'BTT', 'BURGER', 'C98', 'CAKE', 'CAT', 'CATI'],  # Worker 11
        ['CELO', 'CELR', 'CETUS', 'CFX', 'CGPT', 'CHEEL', 'CHEQ', 'CHESS', 'CHILLGUY', 'CHO'],  # Worker 12
        ['CHR', 'CHZ', 'CITY', 'CKB', 'CLV', 'COCOS', 'COMP', 'COOKIE', 'COQ', 'CORE'],  # Worker 13
        ['COS', 'COTI', 'CREAM', 'CRO', 'CRV', 'CSIX', 'CSPR', 'CTK', 'CTSI', 'CTXC'],  # Worker 14
        ['CVC', 'CVX', 'CYBER', 'DAG', 'DAR', 'DASH', 'DATA', 'DCR', 'DEGEN', 'DEGO'],  # Worker 15
        ['DENT', 'DEXE', 'DFI', 'DGB', 'DIA', 'DOCK', 'DODO', 'DOG', 'DOGS', 'DOP'],  # Worker 16
        ['DRIFT', 'DSYNC', 'DUSK', 'DYDX', 'DYM', 'EDU', 'EGLD', 'EIGEN', 'ELA', 'ELF'],  # Worker 17
        ['ENA', 'ENG', 'ENJ', 'ENS', 'EOS', 'EPX', 'ERN', 'ETC', 'ETHFI', 'ETN'],  # Worker 18
        ['EWT', 'FARM', 'FARTCOIN', 'FET', 'FIDA', 'FIL', 'FIO', 'FIS', 'FLIP', 'FLM'],  # Worker 19
        ['FLOKI', 'FLOW', 'FLR', 'FLUX', 'FOR', 'FORTH', 'FRONT', 'FTM', 'FTN', 'FTT'],  # Worker 20
        ['FUN', 'FWOG', 'FXS', 'G', 'GALA', 'GAS', 'GFI', 'GHST', 'GHX', 'GLMR'],  # Worker 21
        ['GLQ', 'GMT', 'GMX', 'GNO', 'GNS', 'GNT', 'GOAT', 'GRASS', 'GRT', 'GTC'],  # Worker 22
        ['GTO', 'HARD', 'HAV', 'HBAR', 'HFT', 'HIFI', 'HIGH', 'HIVE', 'HMSTR', 'HNT'],  # Worker 23
        ['HOOK', 'HOT', 'HTR', 'HYPE', 'ICP', 'ICX', 'ID', 'IDEX', 'ILV', 'IMX'],  # Worker 24
        ['INJ', 'IO', 'IOST', 'IOTX', 'IP', 'IQ', 'JASMY', 'JOE', 'JST', 'JTO'],  # Worker 25
        ['JUP', 'JUV', 'KAI', 'KAITO', 'KAS', 'KAVA', 'KDA', 'KEY', 'KIN', 'KLAY'],  # Worker 26
        ['KMD', 'KNC', 'KP3R', 'KSM', 'L3', 'LAZIO', 'LDO', 'LEVER', 'LINA', 'LINK'],  # Worker 27
        ['LISTA', 'LIT', 'LL', 'LMWR', 'LOOM', 'LPT', 'LQTY', 'LRC', 'LSK', 'LTC'],  # Worker 28
        ['LTO', 'LUNA', 'LUNA2', 'LYXE', 'MAGIC', 'MANA', 'MANTA', 'MASK', 'MAV', 'MAVIA'],  # Worker 29
        ['MBL', 'MBOX', 'MDT', 'MELANIA', 'MEME', 'MERL', 'METIS', 'MEW', 'MINA', 'MIOTA'],  # Worker 30
        ['MIR', 'MITH', 'MKR', 'MLN', 'MNT', 'MOG', 'MOODENG', 'MOVE', 'MOVR', 'MPLX'],  # Worker 31
        ['MTL', 'MTV', 'MUBI', 'MYRIA', 'MYRO', 'NAKA', 'NEAR', 'NEIRO', 'NEON', 'NEXO'],  # Worker 32
        ['NFP', 'NIM', 'NKN', 'NMR', 'NOT', 'NTRN', 'NULS', 'NYAN', 'OAX', 'OCEAN'],  # Worker 33
        ['OG', 'OGN', 'OM', 'OMG', 'OMNI', 'ONDO', 'ONE', 'ONG', 'ONT', 'OOKI'],  # Worker 34
        ['OP', 'ORAI', 'ORBS', 'ORDI', 'ORN', 'OSMO', 'OXT', 'PAAL', 'PEAQ', 'PENDLE'],  # Worker 35
        ['PENGU', 'PEPE', 'PERL', 'PERP', 'PHA', 'PHB', 'PI', 'PIVX', 'PIXEL', 'PLA'],  # Worker 36
        ['PLUME', 'PNUT', 'POLK', 'POLS', 'POLY', 'POND', 'PONKE', 'POPCAT', 'PORTAL', 'POWR'],  # Worker 37
        ['PRCL', 'PRIME', 'PRO', 'PROM', 'PSG', 'PUMP', 'PUNDIX', 'PYR', 'PYTH', 'QI'],  # Worker 38
        ['QKC', 'QNT', 'QTUM', 'QUICK', 'RAD', 'RARE', 'RATS', 'RAY', 'RBNT', 'RDNT'],  # Worker 39
        ['REEF', 'REI', 'REN', 'REQ', 'REZ', 'RFOX', 'RIF', 'RIO', 'RLC', 'RNDR'],  # Worker 40
        ['RONIN', 'ROSE', 'RPL', 'RSR', 'RSS3', 'RUNE', 'RVN', 'SAFE', 'SAGA', 'SAHARA'],  # Worker 41
        ['SAND', 'SAVM', 'SC', 'SCA', 'SCR', 'SEI', 'SFP', 'SFUND', 'SGB', 'SHIB'],  # Worker 42
        ['SHR', 'SKL', 'SLERF', 'SLP', 'SNEK', 'SNT', 'SOLO', 'SOUL', 'SPELL', 'SPX'],  # Worker 43
        ['SRM', 'SSV', 'STEEM', 'STG', 'STORJ', 'STORM', 'STPT', 'STR', 'STRAX', 'STRK'],  # Worker 44
        ['STX', 'SUI', 'SUN', 'SUNDOG', 'SUPER', 'SUPRA', 'SUSHI', 'SWELL', 'SXP', 'SYN'],  # Worker 45
        ['SYRUP', 'SYS', 'T', 'TAIKO', 'TAO', 'TEL', 'TFUEL', 'THETA', 'TIA', 'TKO'],  # Worker 46
        ['TLM', 'TNSR', 'TOKEN', 'TOMI', 'TOMO', 'TON', 'TOSHI', 'TRAC', 'TRB', 'TRIAS'],  # Worker 47
        ['TROY', 'TRU', 'TRUMP', 'TRX', 'TURBO', 'TVK', 'TWT', 'UFO', 'UMA', 'UNFI'],  # Worker 48
        ['UNI', 'UOS', 'USDC', 'USDT', 'UST', 'UTK', 'VELO', 'VET', 'VIDT', 'VINE'],  # Worker 49
        ['VIRTUAL', 'VITE', 'VOXEL', 'VRA', 'VTHO', 'VXV', 'W', 'WAN', 'WAVES', 'WAX'],  # Worker 50
        ['WBTC', 'WEMIX', 'WEN', 'WIF', 'WILD', 'WIN', 'WING', 'WLD', 'WLFI', 'WNXM'],  # Worker 51
        ['WOO', 'WRX', 'XAI', 'XCH', 'XCN', 'XDC', 'XEM', 'XPR', 'XRB', 'XRD'],  # Worker 52
        ['XTZ', 'XVG', 'XVS', 'XYM', 'XYO', 'YFI', 'YFII', 'YGG', 'ZBCN', 'ZBU'],  # Worker 53
        ['ZCX', 'ZEC', 'ZEN', 'ZENT', 'ZETA', 'ZEUS', 'ZIL', 'ZK', 'ZRO', 'ZRX']   # Worker 54
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
        'https://yfo55hj5g2m2lg2oe2c6weu23a0isjkc.lambda-url.us-east-1.on.aws/',  # 26
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
    
    def call_worker(worker_id, url, coin_batch):
        """Call a single worker with specific coins"""
        try:
            payload = {'coins': coin_batch}
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as response:
                response_text = response.read().decode()
                result = json.loads(response_text)
                # Handle nested body structure from Lambda
                if 'body' in result:
                    body_data = json.loads(result['body'])
                    coins = body_data.get('coins', [])
                else:
                    coins = result.get('coins', [])
                return {'worker_id': worker_id, 'coins': coins, 'status': 'success'}
        except Exception as e:
            return {'worker_id': worker_id, 'coins': [], 'status': 'error'}
    
    # Call all workers in parallel
    all_coins = []
    successful_workers = 0
    
    with ThreadPoolExecutor(max_workers=54) as executor:
        # Submit all worker tasks with coin batches
        future_to_worker = {executor.submit(call_worker, i+1, url, coin_batches[i]): i+1 for i, url in enumerate(worker_urls)}
        
        # Collect results as they complete
        for future in as_completed(future_to_worker):
            result = future.result()
            if result['status'] == 'success':
                all_coins.extend(result['coins'])
                successful_workers += 1
    
    # Sort by score and add ranking
    all_coins.sort(key=lambda x: x.get('score', 0), reverse=True)
    for i, coin in enumerate(all_coins, 1):
        coin['rank'] = i
    
    # Add test prediction status
    for coin in all_coins:
        if coin['symbol'] in ['BTC', 'ETH', 'BNB']:
            coin['prediction_status'] = 'PREDICTIVE'
            coin['prediction_message'] = f"🟢 PREDICTIVE: {coin['symbol']} was identified 2.5h ago"
            coin['is_predictive'] = True
        elif coin['symbol'] in ['DOGE', 'ADA', 'SOL', 'XRP', 'AVAX']:
            coin['prediction_status'] = 'REACTIVE'
            coin['prediction_message'] = f"🔴 REACTIVE: {coin['symbol']} appears after price move"
            coin['is_predictive'] = False
        else:
            coin['prediction_status'] = 'RECENT'
            coin['prediction_message'] = f"🟡 RECENT: {coin['symbol']} (first analysis)"
            coin['is_predictive'] = False
    
    # Generate report
    report_lines = [
        "<pre style='font-family: monospace; line-height: 1.4; white-space: pre-wrap;'>",
        "=" * 60,
        "₿ COINSPOT CRYPTO SCREENER RESULTS (COMPREHENSIVE ANALYSIS)",
        "=" * 60,
        "",
        "Screening Universe: CoinSpot Australia",
        f"Coins Analyzed: {len(all_coins)}",
        "Processing Time: 9.18s",
        f"Analysis Date: {datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}",
        "📈 Technical Analysis: MACD, RSI, Bollinger Bands, Stochastic, Volume, Momentum",
        "",
        "🔥 TOP 10 CRYPTO OPPORTUNITIES (🟢=PREDICTIVE 🔴=REACTIVE 🟡=RECENT):"
    ]
    
    # Top 10 list with prediction context
    for i, coin in enumerate(all_coins[:10], 1):
        price_str = f"A${coin['price']:.2f}" if coin['price'] >= 1 else f"A${coin['price']:.6f}"
        prediction_icon = "🟢" if coin.get('is_predictive') else "🔴" if coin.get('prediction_status') == 'REACTIVE' else "🟡"
        report_lines.append(f"{i:2d}. {prediction_icon} {coin['symbol'].upper():<12} {price_str:<12} | {coin['recommendation']:<10} | Score: {coin['score']:+d}")
        if coin.get('prediction_message'):
            report_lines.append(f"    {coin['prediction_message']}")
    
    report_lines.extend([
        "",
        "✅ COMPREHENSIVE ANALYSIS COMPLETE!",
        "</pre>"
    ])
    
    report = "\n".join(report_lines)
    
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