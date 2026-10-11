import requests
import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class CryptoAnalytics:
    def __init__(self):
        # Target coins to analyze - prioritize major coins first
        self.target_coins = [
            'BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'XRP', 'DOGE', 'AVAX', 'DOT', 'MATIC',  # Major coins first
            '1000SATS', '1INCH', 'A2Z', 'AAVE', 'ACA', 'ACE', 'ACH', 'ACM', 'ACT',
            'ADX', 'AE', 'AERGO', 'AERO', 'AEVO', 'AGI', 'AGLD', 'AGS', 'AI', 'AI16Z',
            'AIOZ', 'AKRO', 'AKT', 'ALBT', 'ALCX', 'ALGO', 'ALICE', 'ALPACA', 'ALPHA', 'ALPINE',
            'ALT', 'AMB', 'AMP', 'ANIME', 'ANKR', 'ANS', 'APE', 'API3', 'APT', 'AR',
            'ARB', 'ARDR', 'ARK', 'ARKM', 'ARPA', 'ASR', 'AST', 'ASTR', 'ATH', 'ATM',
            'ATOM', 'ATOR', 'AUCT', 'AUDIO', 'AURORA', 'AUS', 'AVA', 'AVAAI', 'AXL',
            'AXS', 'AZERO', 'BADGER', 'BAKE', 'BAL', 'BANANA', 'BAND', 'BAR', 'BAT', 'BB',
            'BCAU', 'BCC', 'BCHSV', 'BEAM', 'BEL', 'BERA', 'BETA', 'BICO', 'BIGTIME', 'BIO',
            'BLAST', 'BLUR', 'BLZ', 'BNT', 'BNX', 'BOME', 'BOND', 'BONE', 'BONK',
            'BQX', 'BRETT', 'BRISE', 'BSW', 'BTCST', 'BTG', 'BTS', 'BTT', 'BURGER',  # BTC moved to front
            'C98', 'CAKE', 'CAT', 'CATI', 'CELO', 'CELR', 'CETUS', 'CFX', 'CGPT', 'CHEEL',
            'CHEQ', 'CHESS', 'CHILLGUY', 'CHO', 'CHR', 'CHZ', 'CITY', 'CKB', 'CLV', 'COCOS',
            'COMP', 'COOKIE', 'COQ', 'CORE', 'COS', 'COTI', 'CREAM', 'CRO', 'CRV', 'CSIX',
            'CSPR', 'CTK', 'CTSI', 'CTXC', 'CVC', 'CVX', 'CYBER', 'DAG', 'DAR', 'DASH',
            'DATA', 'DCR', 'DEGEN', 'DEGO', 'DENT', 'DEXE', 'DFI', 'DGB', 'DIA', 'DOCK',
            'DODO', 'DOG', 'DOGS', 'DOP', 'DRIFT', 'DSYNC', 'DUSK', 'DYDX',
            'DYM', 'EDU', 'EGLD', 'EIGEN', 'ELA', 'ELF', 'ENA', 'ENG', 'ENJ', 'ENS',
            'EOS', 'EPX', 'ERN', 'ETC', 'ETHFI', 'ETN', 'EWT', 'FARM', 'FARTCOIN',
            'FET', 'FIDA', 'FIL', 'FIO', 'FIS', 'FLIP', 'FLM', 'FLOKI', 'FLOW', 'FLR',
            'FLUX', 'FOR', 'FORTH', 'FRONT', 'FTM', 'FTN', 'FTT', 'FUN', 'FWOG', 'FXS',
            'G', 'GALA', 'GAS', 'GFI', 'GHST', 'GHX', 'GLMR', 'GLQ', 'GMT', 'GMX',
            'GNO', 'GNS', 'GNT', 'GOAT', 'GRASS', 'GRT', 'GTC', 'GTO', 'HARD', 'HAV',
            'HBAR', 'HFT', 'HIFI', 'HIGH', 'HIVE', 'HMSTR', 'HNT', 'HOOK', 'HOT', 'HTR',
            'HYPE', 'ICP', 'ICX', 'ID', 'IDEX', 'ILV', 'IMX', 'INJ', 'IO', 'IOST',
            'IOTX', 'IP', 'IQ', 'JASMY', 'JOE', 'JST', 'JTO', 'JUP', 'JUV', 'KAI',
            'KAITO', 'KAS', 'KAVA', 'KDA', 'KEY', 'KIN', 'KLAY', 'KMD', 'KNC', 'KP3R',
            'KSM', 'L3', 'LAZIO', 'LDO', 'LEVER', 'LINA', 'LINK', 'LISTA', 'LIT', 'LL',
            'LMWR', 'LOOM', 'LPT', 'LQTY', 'LRC', 'LSK', 'LTC', 'LTO', 'LUNA', 'LUNA2',
            'LYXE', 'MAGIC', 'MANA', 'MANTA', 'MASK', 'MAV', 'MAVIA', 'MBL', 'MBOX',
            'MDT', 'MELANIA', 'MEME', 'MERL', 'METIS', 'MEW', 'MINA', 'MIOTA', 'MIR', 'MITH',
            'MKR', 'MLN', 'MNT', 'MOG', 'MOODENG', 'MOVE', 'MOVR', 'MPLX', 'MTL', 'MTV',
            'MUBI', 'MYRIA', 'MYRO', 'NAKA', 'NEAR', 'NEIRO', 'NEON', 'NEXO', 'NFP', 'NIM',
            'NKN', 'NMR', 'NOT', 'NTRN', 'NULS', 'NYAN', 'OAX', 'OCEAN', 'OG', 'OGN',
            'OM', 'OMG', 'OMNI', 'ONDO', 'ONE', 'ONG', 'ONT', 'OOKI', 'OP', 'ORAI',
            'ORBS', 'ORDI', 'ORN', 'OSMO', 'OXT', 'PAAL', 'PEAQ', 'PENDLE', 'PENGU', 'PEPE',
            'PERL', 'PERP', 'PHA', 'PHB', 'PI', 'PIVX', 'PIXEL', 'PLA', 'PLUME', 'PNUT',
            'POLK', 'POLS', 'POLY', 'POND', 'PONKE', 'POPCAT', 'PORTAL', 'POWR', 'PRCL', 'PRIME',
            'PRO', 'PROM', 'PSG', 'PUMP', 'PUNDIX', 'PYR', 'PYTH', 'QI', 'QKC', 'QNT',
            'QTUM', 'QUICK', 'RAD', 'RARE', 'RATS', 'RAY', 'RBNT', 'RDNT', 'REEF', 'REI',
            'REN', 'REQ', 'REZ', 'RFOX', 'RIF', 'RIO', 'RLC', 'RNDR', 'RONIN', 'ROSE',
            'RPL', 'RSR', 'RSS3', 'RUNE', 'RVN', 'SAFE', 'SAGA', 'SAHARA', 'SAND', 'SAVM',
            'SC', 'SCA', 'SCR', 'SEI', 'SFP', 'SFUND', 'SGB', 'SHIB', 'SHR', 'SKL',
            'SLERF', 'SLP', 'SNEK', 'SNT', 'SOLO', 'SOUL', 'SPELL', 'SPX', 'SRM',
            'SSV', 'STEEM', 'STG', 'STORJ', 'STORM', 'STPT', 'STR', 'STRAX', 'STRK', 'STX',
            'SUI', 'SUN', 'SUNDOG', 'SUPER', 'SUPRA', 'SUSHI', 'SWELL', 'SXP', 'SYN', 'SYRUP',
            'SYS', 'T', 'TAIKO', 'TAO', 'TEL', 'TFUEL', 'THETA', 'TIA', 'TKO', 'TLM',
            'TNSR', 'TOKEN', 'TOMI', 'TOMO', 'TON', 'TOSHI', 'TRAC', 'TRB', 'TRIAS', 'TROY',
            'TRU', 'TRUMP', 'TRX', 'TURBO', 'TVK', 'TWT', 'UFO', 'UMA', 'UNFI', 'UNI',
            'UOS', 'USDC', 'USDT', 'UST', 'UTK', 'VELO', 'VET', 'VIDT', 'VINE', 'VIRTUAL',
            'VITE', 'VOXEL', 'VRA', 'VTHO', 'VXV', 'W', 'WAN', 'WAVES', 'WAX', 'WBTC',
            'WEMIX', 'WEN', 'WIF', 'WILD', 'WIN', 'WING', 'WLD', 'WLFI', 'WNXM', 'WOO',
            'WRX', 'XAI', 'XCH', 'XCN', 'XDC', 'XEM', 'XPR', 'XRB', 'XRD',
            'XTZ', 'XVG', 'XVS', 'XYM', 'XYO', 'YFI', 'YFII', 'YGG', 'ZBCN', 'ZBU',
            'ZCX', 'ZEC', 'ZEN', 'ZENT', 'ZETA', 'ZEUS', 'ZIL', 'ZK', 'ZRO', 'ZRX'
        ]  # 540 coins total - system will auto-scale to 54 workers (10 coins each)
        


    
    def get_coin_list(self) -> List[str]:
        """Get list of coins to analyze - uses CoinSpot API data"""
        coinspot_data = self.fetch_coinspot_data()
        return list(coinspot_data.keys())
    
    def scrape_coinspot_coins(self) -> List[str]:
        """Scrape all available coins from CoinSpot website"""
        try:
            url = "https://www.coinspot.com.au/tradecoins"
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                import re
                # Extract coin symbols from the page
                coin_pattern = r'data-coin="([A-Z0-9]+)"'
                coins = re.findall(coin_pattern, response.text)
                # Also look for alternative patterns
                alt_pattern = r'/buy/([a-z0-9]+)'
                alt_coins = re.findall(alt_pattern, response.text)
                
                all_coins = list(set(coins + [c.upper() for c in alt_coins]))
                print(f"🌐 Scraped {len(all_coins)} coins from CoinSpot website")
                return all_coins
        except Exception as e:
            print(f"Scraping error: {e}")
        
        return []
    
    def fetch_coinspot_data(self) -> Dict:
        """Not used - system uses hardcoded target_coins list"""
        return {}
    
    def calculate_macd(self, prices: List[float], fast=12, slow=26, signal=9) -> Tuple[float, float, str]:
        """Calculate MACD indicator with proper signal line"""
        if len(prices) < slow + signal:
            return 0, 0, "NEUTRAL"
        
        # Calculate MACD line for each price point
        macd_values = []
        for i in range(slow, len(prices) + 1):
            price_slice = prices[:i]
            ema_fast = self.calculate_ema(price_slice, fast)
            ema_slow = self.calculate_ema(price_slice, slow)
            macd_values.append(ema_fast - ema_slow)
        
        # Calculate signal line (EMA of MACD values)
        signal_line = self.calculate_ema(macd_values, signal)
        macd_line = macd_values[-1]
        
        # Determine trend based on MACD vs signal
        if macd_line > signal_line and macd_line > 0:
            trend = "STRONG BULL"
        elif macd_line > signal_line:
            trend = "BULL"
        elif macd_line < signal_line and macd_line < 0:
            trend = "STRONG BEAR"
        else:
            trend = "BEAR"
        
        return macd_line, signal_line, trend
    
    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if not prices or len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    def calculate_rsi(self, prices: List[float], period=14) -> float:
        """Calculate RSI indicator with memory-efficient approach"""
        if len(prices) < period + 1:
            return 50  # Default neutral RSI
        
        from collections import deque
        gains = deque(maxlen=period)
        losses = deque(maxlen=period)
        
        # Only process the last period+1 prices for efficiency
        start_idx = max(0, len(prices) - period - 10)  # Small buffer for accuracy
        for i in range(start_idx + 1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # Handle edge cases
        if avg_loss == 0:
            return 100 if avg_gain > 0 else 50
        if avg_gain == 0:
            return 0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Ensure RSI is within valid range
        return max(0, min(100, rsi))
    
    def fetch_yahoo_data(self, symbol: str) -> Tuple[List[float], float, float, float]:
        """Fetch historical price data from Yahoo Finance (USD only)"""
        try:
            yahoo_symbol = f"{symbol.upper()}-USD"
            
            import time
            end_time = int(time.time())
            start_time = end_time - (30 * 24 * 60 * 60)  # 30 days ago
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
            params = {
                'period1': start_time,
                'period2': end_time,
                'interval': '1d'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                if data and 'chart' in data and data['chart']['result']:
                    result = data['chart']['result'][0]
                    
                    if 'indicators' in result and 'quote' in result['indicators']:
                        quotes = result['indicators']['quote'][0]
                        closes = quotes.get('close', [])
                        
                        if closes:
                            # Filter out None values
                            historical_prices = [price for price in closes if price is not None]
                            
                            if len(historical_prices) > 7:
                                # Calculate changes
                                current = historical_prices[-1]
                                change_24h = ((current - historical_prices[-2]) / historical_prices[-2]) * 100
                                change_7d = ((current - historical_prices[-8]) / historical_prices[-8]) * 100 if len(historical_prices) >= 8 else 0
                                change_30d = ((current - historical_prices[0]) / historical_prices[0]) * 100
                                
                                return historical_prices, change_24h, change_7d, change_30d
                                        
        except Exception as e:
            print(f"Yahoo Finance error for {symbol}: {e}")
        
        return [], 0, 0, 0
    
    def calculate_bollinger_bands(self, prices: List[float], period=20, std_dev=2) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None, None, None
        
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period
        
        variance = sum((x - sma) ** 2 for x in recent_prices) / period
        std = variance ** 0.5
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, sma, lower_band
    
    def calculate_stochastic(self, highs: List[float], lows: List[float], closes: List[float], k_period=14) -> Tuple[float, str]:
        """Calculate Stochastic Oscillator"""
        if len(closes) < k_period:
            return 50, "NEUTRAL"
        
        recent_highs = highs[-k_period:]
        recent_lows = lows[-k_period:]
        current_close = closes[-1]
        
        highest_high = max(recent_highs)
        lowest_low = min(recent_lows)
        
        if highest_high == lowest_low:
            k_percent = 50
        else:
            k_percent = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
        
        if k_percent < 20:
            signal = "OVERSOLD"
        elif k_percent > 80:
            signal = "OVERBOUGHT"
        else:
            signal = "NEUTRAL"
        
        return k_percent, signal
    
    def calculate_trading_levels(self, current_price: float, highs: List[float], lows: List[float], closes: List[float], bb_upper: float, bb_lower: float, atr: float) -> Dict:
        """Calculate stop loss, take profit, buy limit, and buy stop levels"""
        
        # Support and resistance levels
        support_20d = min(lows[-20:]) if len(lows) >= 20 else min(lows[-10:]) if len(lows) >= 10 else current_price * 0.95
        resistance_20d = max(highs[-20:]) if len(highs) >= 20 else max(highs[-10:]) if len(highs) >= 10 else current_price * 1.05
        
        # ATR-based levels (Average True Range for volatility)
        if atr > 0:
            # Stop loss: 2x ATR below current price
            stop_loss = current_price - (2 * atr)
            # Take profit: 3x ATR above current price (1.5:1 risk/reward)
            take_profit = current_price + (3 * atr)
        else:
            # Fallback: percentage-based
            stop_loss = current_price * 0.92  # 8% stop loss
            take_profit = current_price * 1.12  # 12% take profit
        
        # Adjust stop loss to support level if closer
        if support_20d > stop_loss and support_20d < current_price * 0.98:
            stop_loss = support_20d * 0.99  # Just below support
        
        # Adjust take profit to resistance if closer
        if resistance_20d < take_profit and resistance_20d > current_price * 1.02:
            take_profit = resistance_20d * 0.99  # Just below resistance
        
        # Buy limit (for pullbacks)
        if bb_lower:
            buy_limit = max(bb_lower, current_price * 0.97)  # Bollinger lower band or 3% pullback
        else:
            buy_limit = current_price * 0.97
        
        # Buy stop (for breakouts)
        if resistance_20d > current_price * 1.01:
            buy_stop = resistance_20d * 1.01  # 1% above resistance
        else:
            buy_stop = current_price * 1.03  # 3% breakout level
        
        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'buy_limit': buy_limit,
            'buy_stop': buy_stop,
            'support': support_20d,
            'resistance': resistance_20d
        }
    
    def calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period=14) -> float:
        """Calculate Average True Range for volatility"""
        if len(closes) < period + 1:
            return 0
        
        true_ranges = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)
        
        return sum(true_ranges[-period:]) / period if len(true_ranges) >= period else 0
    
    def analyze_coin(self, symbol: str, price_data: Dict) -> Dict:
        """Perform comprehensive deep analysis on a single coin"""
        # Get comprehensive historical data from Yahoo Finance
        historical_prices, change_24h, change_7d, change_30d = self.fetch_yahoo_data(symbol)
        current_price = historical_prices[-1] if historical_prices else 0
        
        if len(historical_prices) < 20:
            return {
                'symbol': symbol,
                'price': current_price,
                'change_24h': 0,
                'change_7d': 0,
                'change_30d': 0,
                'macd_trend': 'NEUTRAL',
                'macd_signal': 'No data',
                'rsi': 50,
                'rsi_signal': 'NEUTRAL',
                'bb_signal': 'NEUTRAL',
                'stoch_signal': 'NEUTRAL',
                'volume_signal': 'NEUTRAL',
                'momentum_signal': 'NEUTRAL',
                'score': 0,
                'recommendation': 'HOLD',
                'timeframe': 'HOLD',
                'confidence': 'LOW',
                'stop_loss': current_price * 0.92,
                'take_profit': current_price * 1.12,
                'buy_limit': current_price * 0.97,
                'buy_stop': current_price * 1.03,
                'support': current_price * 0.95,
                'resistance': current_price * 1.05,
                'atr': 0,
                'profit_probability': 50,
                'score_breakdown': ['No data available']
            }
        
        # Get full OHLCV data for comprehensive analysis (USD only)
        highs = lows = closes = volumes = []
        macd_closes = None
        try:
            yahoo_symbol = f"{symbol.upper()}-USD"
            import time
            end_time = int(time.time())
            # 90 days are asked for, for MACD alone: it needs 35 days of prices, and with the 30 that used to be asked for it
            # was never worked out (every coin was scored "MACD Bear: -2"). Everything else still uses the last 30 days.
            start_time = end_time - (90 * 24 * 60 * 60)
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
            params = {'period1': start_time, 'period2': end_time, 'interval': '1d'}
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            
            response = requests.get(url, params=params, headers=headers, timeout=8)
            if response.status_code == 200:
                data = response.json()
                result = data['chart']['result'][0]
                quotes = result['indicators']['quote'][0]
                
                highs = [h for h in quotes.get('high', []) if h is not None]
                lows = [l for l in quotes.get('low', []) if l is not None]
                closes = [c for c in quotes.get('close', []) if c is not None]
                volumes = [v for v in quotes.get('volume', []) if v is not None]
                macd_closes = closes[:]
                highs, lows, closes, volumes = highs[-31:], lows[-31:], closes[-31:], volumes[-31:]
        except Exception as e:
            print(f"OHLCV fetch error for {symbol}: {e}")
        
        # Final fallback to historical_prices if OHLCV failed
        if not highs:
            highs = lows = closes = historical_prices
            volumes = [1000000] * len(closes)  # Dummy volume
        
        # COMPREHENSIVE TECHNICAL ANALYSIS
        
        # 1. MACD Analysis with detailed signals
        macd_line, macd_signal_line, macd_trend = self.calculate_macd(macd_closes or closes)
        if macd_trend == "NEUTRAL":                 # too little history to work it out: no points either way (it used to count as a bear)
            macd_signal = "NEUTRAL - Not enough history"
        elif macd_line > macd_signal_line:
            if macd_line > 0:
                macd_signal = "STRONG BULL - Above zero & signal"
            else:
                macd_signal = "BULL - Above signal line"
        else:
            if macd_line < 0:
                macd_signal = "STRONG BEAR - Below zero & signal"
            else:
                macd_signal = "BEAR - Below signal line"
        
        # 2. RSI Analysis with detailed interpretation
        rsi = self.calculate_rsi(closes)
        # Handle cases where RSI calculation fails
        if rsi == 0 and len(closes) < 15:
            rsi = 50  # Default to neutral if insufficient data
            rsi_signal = "INSUFFICIENT DATA - Using neutral RSI"
        elif rsi < 20:
            rsi_signal = "EXTREMELY OVERSOLD - Strong buy signal"
        elif rsi < 30:
            rsi_signal = "OVERSOLD - Buy signal"
        elif rsi < 40:
            rsi_signal = "WEAK - Potential buy"
        elif rsi > 80:
            rsi_signal = "EXTREMELY OVERBOUGHT - Strong sell signal"
        elif rsi > 70:
            rsi_signal = "OVERBOUGHT - Sell signal"
        elif rsi > 60:
            rsi_signal = "STRONG - Potential sell"
        else:
            rsi_signal = "NEUTRAL - No clear signal"
        
        # 3. Bollinger Bands Analysis
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(closes)
        current = closes[-1]
        if bb_upper and bb_lower:
            if current > bb_upper:
                bb_signal = "OVERBOUGHT - Price above upper band"
            elif current < bb_lower:
                bb_signal = "OVERSOLD - Price below lower band"
            elif current > bb_middle:
                bb_signal = "BULLISH - Above middle line"
            else:
                bb_signal = "BEARISH - Below middle line"
        else:
            bb_signal = "NEUTRAL - Insufficient data"
        
        # 4. Stochastic Oscillator
        stoch_k, stoch_signal = self.calculate_stochastic(highs, lows, closes)
        
        # 5. Volume Analysis
        if len(volumes) >= 20:
            recent_vol = sum(volumes[-5:]) / 5
            avg_vol = sum(volumes[-20:]) / 20
            vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
            
            if vol_ratio > 2.0:
                if change_24h > 0:
                    volume_signal = f"BULLISH - High volume ({vol_ratio:.1f}x avg) on up move"
                else:
                    volume_signal = f"BEARISH - High volume ({vol_ratio:.1f}x avg) on down move"
            elif vol_ratio < 0.5:
                volume_signal = f"WEAK - Low volume ({vol_ratio:.1f}x avg), lack of conviction"
            else:
                volume_signal = f"NORMAL - Average volume ({vol_ratio:.1f}x avg)"
        else:
            vol_ratio = 1.0
            volume_signal = "NEUTRAL - Insufficient data"
        
        # 6. Momentum Analysis
        if len(closes) >= 10:
            momentum_5d = ((closes[-1] - closes[-5]) / closes[-5]) * 100 if len(closes) >= 5 else 0
            momentum_10d = ((closes[-1] - closes[-10]) / closes[-10]) * 100
            
            if momentum_5d > 10 and momentum_10d > 15:
                momentum_signal = "STRONG BULLISH - Accelerating uptrend"
            elif momentum_5d > 5:
                momentum_signal = "BULLISH - Positive momentum"
            elif momentum_5d < -10 and momentum_10d < -15:
                momentum_signal = "STRONG BEARISH - Accelerating downtrend"
            elif momentum_5d < -5:
                momentum_signal = "BEARISH - Negative momentum"
            else:
                momentum_signal = "NEUTRAL - Sideways momentum"
        else:
            momentum_signal = "NEUTRAL - Insufficient data"
        
        # ADVANCED SCORING SYSTEM WITH BREAKDOWN
        score = 0
        confidence_factors = []
        score_breakdown = []
        
        # MACD scoring (weight: 3)
        if "STRONG BULL" in macd_signal:
            score += 3
            score_breakdown.append("MACD Strong Bull: +3")
            confidence_factors.append("Strong MACD")
        elif "BULL" in macd_signal:
            score += 2
            score_breakdown.append("MACD Bull: +2")
        elif "STRONG BEAR" in macd_signal:
            score -= 3
            score_breakdown.append("MACD Strong Bear: -3")
            confidence_factors.append("Strong MACD")
        elif "BEAR" in macd_signal:
            score -= 2
            score_breakdown.append("MACD Bear: -2")
        else:
            score_breakdown.append("MACD Neutral: 0")
        
        # RSI scoring (weight: 2)
        if "EXTREMELY OVERSOLD" in rsi_signal:
            score += 3
            score_breakdown.append("RSI Extreme Oversold: +3")
            confidence_factors.append("Extreme RSI")
        elif "OVERSOLD" in rsi_signal:
            score += 2
            score_breakdown.append("RSI Oversold: +2")
        elif "EXTREMELY OVERBOUGHT" in rsi_signal:
            score -= 3
            score_breakdown.append("RSI Extreme Overbought: -3")
            confidence_factors.append("Extreme RSI")
        elif "OVERBOUGHT" in rsi_signal:
            score -= 2
            score_breakdown.append("RSI Overbought: -2")
        else:
            score_breakdown.append("RSI Neutral: 0")
        
        # Bollinger Bands scoring (weight: 2)
        if "OVERSOLD" in bb_signal:
            score += 2
            score_breakdown.append("BB Oversold: +2")
            confidence_factors.append("BB Oversold")
        elif "OVERBOUGHT" in bb_signal:
            score -= 2
            score_breakdown.append("BB Overbought: -2")
            confidence_factors.append("BB Overbought")
        elif "BULLISH" in bb_signal:
            score += 1
            score_breakdown.append("BB Bullish: +1")
        elif "BEARISH" in bb_signal:
            score -= 1
            score_breakdown.append("BB Bearish: -1")
        else:
            score_breakdown.append("BB Neutral: 0")
        
        # Stochastic scoring (weight: 1)
        if stoch_signal == "OVERSOLD":
            score += 1
            score_breakdown.append("Stoch Oversold: +1")
        elif stoch_signal == "OVERBOUGHT":
            score -= 1
            score_breakdown.append("Stoch Overbought: -1")
        else:
            score_breakdown.append("Stoch Neutral: 0")
        
        # Volume confirmation (weight: 1)
        if "BULLISH" in volume_signal:
            score += 1
            score_breakdown.append("Volume Bullish: +1")
            confidence_factors.append("Volume confirm")
        elif "BEARISH" in volume_signal:
            score -= 1
            score_breakdown.append("Volume Bearish: -1")
            confidence_factors.append("Volume confirm")
        else:
            score_breakdown.append("Volume Neutral: 0")
        
        # Momentum scoring (weight: 2)
        if "STRONG BULLISH" in momentum_signal:
            score += 2
            score_breakdown.append("Momentum Strong Bull: +2")
            confidence_factors.append("Strong momentum")
        elif "BULLISH" in momentum_signal:
            score += 1
            score_breakdown.append("Momentum Bull: +1")
        elif "STRONG BEARISH" in momentum_signal:
            score -= 2
            score_breakdown.append("Momentum Strong Bear: -2")
            confidence_factors.append("Strong momentum")
        elif "BEARISH" in momentum_signal:
            score -= 1
            score_breakdown.append("Momentum Bear: -1")
        else:
            score_breakdown.append("Momentum Neutral: 0")
        
        # Price momentum from changes
        if change_24h > 10:
            score += 2
            score_breakdown.append(f"24h Change {change_24h:.1f}%: +2")
        elif change_24h > 5:
            score += 1
            score_breakdown.append(f"24h Change {change_24h:.1f}%: +1")
        elif change_24h < -10:
            score -= 2
            score_breakdown.append(f"24h Change {change_24h:.1f}%: -2")
        elif change_24h < -5:
            score -= 1
            score_breakdown.append(f"24h Change {change_24h:.1f}%: -1")
        else:
            score_breakdown.append(f"24h Change {change_24h:.1f}%: 0")
        
        # PROFIT PROBABILITY ENHANCEMENTS
        
        # 1. Market cap filter (avoid micro-caps for immediate profit)
        if symbol.upper() in ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'XRP', 'DOGE', 'AVAX', 'DOT', 'MATIC']:
            score += 1
            score_breakdown.append("Large Cap Bonus: +1")
        
        # 2. Breakout detection (price above recent resistance)
        if len(closes) >= 20:
            recent_high = max(closes[-20:-1])  # Exclude current price
            if closes[-1] > recent_high * 1.02:  # 2% breakout
                score += 2
                score_breakdown.append("Breakout Detected: +2")
                confidence_factors.append("Breakout")
        
        # 3. Volume surge confirmation (immediate buying pressure)
        if len(volumes) >= 5:
            recent_vol = volumes[-1]
            avg_vol = sum(volumes[-5:-1]) / 4
            surge_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
            if recent_vol > avg_vol * 1.5 and change_24h > 0:
                score += 2
                score_breakdown.append(f"Volume Surge ({surge_ratio:.1f}x): +2")
                confidence_factors.append("Volume surge")
        
        # 4. Multiple timeframe alignment
        if len(closes) >= 5:
            short_trend = closes[-1] > closes[-3]  # 3-day uptrend
            medium_trend = closes[-1] > closes[-5]  # 5-day uptrend
            if short_trend and medium_trend:
                score += 1
                score_breakdown.append("Multi-timeframe Align: +1")
                confidence_factors.append("Multi-timeframe")
        
        # 5. Risk filter - avoid coins showing weakness
        if rsi > 75 and change_24h < 0:  # Overbought but falling
            score -= 3
            score_breakdown.append("Overbought + Falling: -3")
        if change_7d < -15:  # Strong weekly decline
            score -= 2
            score_breakdown.append("Weekly Decline >15%: -2")
        
        # Enhanced recommendation with profit probability
        if score >= 7:
            recommendation = "STRONG BUY"
        elif score >= 4:
            recommendation = "BUY"
        elif score >= 2:
            recommendation = "CONSIDER"
        elif score >= -1:
            recommendation = "HOLD"
        elif score >= -3:
            recommendation = "AVOID"
        elif score >= -5:
            recommendation = "SELL"
        else:
            recommendation = "STRONG SELL"
        
        # Confidence level
        confidence = "HIGH" if len(confidence_factors) >= 3 else "MEDIUM" if len(confidence_factors) >= 2 else "LOW"
        
        # Timeframe analysis
        if abs(change_24h) > 15:
            timeframe = "DAY TRADE"
        elif score > 2 and change_7d > 5:
            timeframe = "SHORT-TERM"
        elif score > 0:
            timeframe = "LONG-TERM"
        elif recommendation == "HOLD":
            timeframe = "HOLD"
        else:
            timeframe = "AVOID"
        
        # Calculate profit probability percentage
        profit_prob = min(95, max(5, 50 + (score * 8)))  # Scale score to 5-95% range
        
        # Calculate ATR and trading levels
        atr = self.calculate_atr(highs, lows, closes)
        trading_levels = self.calculate_trading_levels(current_price, highs, lows, closes, bb_upper, bb_lower, atr)
        
        return {
            'symbol': symbol,
            'price': current_price,
            'change_24h': change_24h,
            'change_7d': change_7d,
            'change_30d': change_30d,
            'macd_trend': macd_trend,
            'macd_signal': macd_signal,
            'rsi': rsi,
            'rsi_signal': rsi_signal,
            'bb_signal': bb_signal,
            'stoch_k': stoch_k,
            'stoch_signal': stoch_signal,
            'volume_signal': volume_signal,
            'momentum_signal': momentum_signal,
            'score': score,
            'recommendation': recommendation,
            'timeframe': timeframe,
            'confidence': confidence,
            'confidence_factors': confidence_factors,
            'score_breakdown': score_breakdown,
            'profit_probability': profit_prob,
            'stop_loss': trading_levels['stop_loss'],
            'take_profit': trading_levels['take_profit'],
            'buy_limit': trading_levels['buy_limit'],
            'buy_stop': trading_levels['buy_stop'],
            'support': trading_levels['support'],
            'resistance': trading_levels['resistance'],
            'atr': atr,
            'volume_ratio': vol_ratio
        }
    
    def generate_report(self, analyzed_coins=None) -> str:
        """Generate comprehensive analytics report"""
        if analyzed_coins is None:
            print(f"🎯 Analyzing {len(self.target_coins)} target coins: {', '.join(self.target_coins)}")
            analyzed_coins = []
            
            for symbol in self.target_coins:
                print(f"📊 Analyzing {symbol.upper()}...")
                analysis = self.analyze_coin(symbol.upper(), {})
                if analysis:
                    analyzed_coins.append(analysis)
        
        # Sort coins by score for top recommendations
        analyzed_coins.sort(key=lambda x: x['score'], reverse=True)
        
        # Generate comprehensive report
        report = []
        report.append("🚀 COINSPOT CRYPTO ANALYTICS REPORT")
        report.append("=" * 50)
        report.append(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} AEST")
        report.append(f"💰 Target Coins Analyzed: {len(analyzed_coins)}/{len(self.target_coins)} (Yahoo Finance USD)")
        report.append(f"🌐 Market: Global Crypto (USD)")
        report.append(f"📈 Technical Analysis: MACD, RSI, Bollinger Bands, Stochastic, Volume, Momentum")
        report.append("")
        
        # Top 5 recommendations with detailed analysis
        report.append("🎯 TOP 5 BUY RECOMMENDATIONS")
        report.append("=" * 30)
        top_5 = analyzed_coins[:5]
        for i, coin in enumerate(top_5, 1):
            price_str = f"${coin['price']:.2f}" if coin['price'] >= 1 else f"${coin['price']:.6f}"
            report.append(f"{i}. {coin['symbol'].upper()}: {price_str} | {coin['recommendation']} | {coin['timeframe']} | Total Score: {coin['score']:+d}")
            report.append("")
            
            # Performance section
            report.append("📊 Performance:")
            report.append(f"   24h: {coin['change_24h']:+.1f}% | 7d: {coin['change_7d']:+.1f}% | 30d: {coin['change_30d']:+.1f}%")
            report.append("")
            
            # Indicators section
            report.append("📈 Indicators:")
            report.append(f"   MACD: {coin['macd_signal']}")
            report.append(f"   RSI: {coin['rsi']:.1f} - {coin['rsi_signal'].split(' - ')[0]}")
            report.append(f"   Bollinger Bands: {coin['bb_signal']}")
            report.append(f"   Momentum: {coin['momentum_signal']}")
            report.append("")
            
            # Confidence section
            report.append("🔄 Confidence:")
            report.append(f"   Confidence: {coin['confidence']}")
            report.append(f"   Profit Probability: {coin['profit_probability']:.0f}%")
            report.append("")
            
            # Signals section
            report.append("🎯 Signals:")
            report.append(f"   {', '.join(coin.get('confidence_factors', []))}")
            report.append("")
            
            # Risk Management section
            stop_str = f"${coin['stop_loss']:.2f}" if coin['stop_loss'] >= 1 else f"${coin['stop_loss']:.6f}"
            tp_str = f"${coin['take_profit']:.2f}" if coin['take_profit'] >= 1 else f"${coin['take_profit']:.6f}"
            bl_str = f"${coin['buy_limit']:.2f}" if coin['buy_limit'] >= 1 else f"${coin['buy_limit']:.6f}"
            bs_str = f"${coin['buy_stop']:.2f}" if coin['buy_stop'] >= 1 else f"${coin['buy_stop']:.6f}"
            
            report.append("🛑 Risk Management:")
            report.append(f"   Stop Loss: {stop_str}")
            report.append(f"   Take Profit: {tp_str}")
            report.append(f"   Buy Limit: {bl_str}")
            report.append(f"   Buy Stop: {bs_str}")
            report.append("")
            
            # Score breakdown section
            breakdown = coin.get('score_breakdown', [])
            if breakdown:
                report.append("📊 Score Breakdown:")
                for b in breakdown:
                    if ': ' in b:
                        component, value = b.split(': ')
                        report.append(f"   {component}: {value}")
                report.append("")
                report.append(f"🧮 Total Score: {coin['score']:+d}")
                report.append("")
                report.append("📊 SCORE RANGES:")
                report.append("   +7 and above: STRONG BUY")
                report.append("   +4 to +6: BUY")
                report.append("   +2 to +3: CONSIDER")
                report.append("   -1 to +1: HOLD")
                report.append("   -3 to -2: AVOID")
                report.append("   -5 to -4: SELL")
                report.append("   Below -5: STRONG SELL")
            report.append("")
            report.append("-" * 50)
            report.append("")
        
        # Market overview
        strong_buys = len([c for c in analyzed_coins if 'STRONG BUY' in c['recommendation']])
        buys = len([c for c in analyzed_coins if c['recommendation'] == 'BUY'])
        considers = len([c for c in analyzed_coins if c['recommendation'] == 'CONSIDER'])
        holds = len([c for c in analyzed_coins if c['recommendation'] == 'HOLD'])
        avoids = len([c for c in analyzed_coins if 'AVOID' in c['recommendation'] or 'SELL' in c['recommendation']])
        
        report.append("📊 MARKET OVERVIEW")
        report.append("=" * 30)
        report.append(f"Strong Buys: {strong_buys} | Buys: {buys} | Consider: {considers}")
        report.append(f"Holds: {holds} | Avoid/Sell: {avoids}")
        
        if strong_buys + buys > avoids:
            market_sentiment = "BULLISH"
        elif avoids > strong_buys + buys:
            market_sentiment = "BEARISH"
        else:
            market_sentiment = "NEUTRAL"
        
        report.append(f"Market Sentiment: {market_sentiment}")
        report.append("")
        
        # Best performers (7d)
        best_performers = sorted(analyzed_coins, key=lambda x: x['change_7d'], reverse=True)[:5]
        report.append("🏆 BEST PERFORMERS (7D)")
        report.append("=" * 30)
        for i, coin in enumerate(best_performers, 1):
            price_str = f"${coin['price']:.2f}" if coin['price'] >= 1 else f"${coin['price']:.6f}"
            report.append(f"{i}. {coin['symbol'].upper():<12} {coin['change_7d']:+.1f}% ({price_str}) - {coin['recommendation']}")
        report.append("")
        
        # Worst performers (7d)
        worst_performers = sorted(analyzed_coins, key=lambda x: x['change_7d'])[:5]
        report.append("📉 WORST PERFORMERS (7D)")
        report.append("=" * 30)
        for i, coin in enumerate(worst_performers, 1):
            price_str = f"${coin['price']:.2f}" if coin['price'] >= 1 else f"${coin['price']:.6f}"
            report.append(f"{i}. {coin['symbol'].upper():<12} {coin['change_7d']:+.1f}% ({price_str}) - {coin['recommendation']}")
        report.append("")
        
        # Technical analysis summary
        report.append("🔬 TECHNICAL ANALYSIS SUMMARY")
        report.append("=" * 30)
        report.append("Indicators Used:")
        report.append("• MACD (12,26,9) - Trend and momentum")
        report.append("• RSI (14) - Overbought/oversold conditions")
        report.append("• Bollinger Bands (20,2) - Volatility and mean reversion")
        report.append("• Stochastic (14) - Price momentum")
        report.append("• Volume Analysis - Confirmation of moves")
        report.append("• Momentum (5d/10d) - Short-term trend strength")
        
        # Top 5 recommendations in table format
        report.append("🎯 TOP 5 BUY RECOMMENDATIONS (PROFIT OPTIMIZED)")
        report.append("=" * 65)
        report.append(f"{'#':<3} {'COIN':<6} {'PRICE':<10} {'STOP LOSS':<10} {'TAKE PROFIT':<12} {'REC':<10}")
        report.append("-" * 65)
        top_5 = analyzed_coins[:5]
        for i, coin in enumerate(top_5, 1):
            price_str = f"${coin['price']:.2f}" if coin['price'] >= 1 else f"${coin['price']:.4f}"
            stop_str = f"${coin['stop_loss']:.2f}" if coin['stop_loss'] >= 1 else f"${coin['stop_loss']:.4f}"
            tp_str = f"${coin['take_profit']:.2f}" if coin['take_profit'] >= 1 else f"${coin['take_profit']:.4f}"
            report.append(f"{i:<3} {coin['symbol'].upper():<6} {price_str:<10} {stop_str:<10} {tp_str:<12} {coin['recommendation']:<10}")
        report.append("")
        
        return "\n".join(report)
    
    def check_prediction_status(self, symbol: str, current_price: float, threshold_hours: float = 0.25) -> Dict:
        """Check prediction status from DynamoDB status table"""
        try:
            dynamodb = boto3.resource('dynamodb')
            status_table = dynamodb.Table('stockiq-coinspot-prediction-status')
            
            # Get status record
            response = status_table.get_item(Key={'symbol': symbol})
            
            if 'Item' in response:
                item = response['Item']
                hours_since = float(item.get('hours_since_prediction', 999))
                
                # Use the appropriate status field based on threshold
                if threshold_hours <= 0.25:
                    status = item.get('status_15min', 'UNKNOWN')
                elif threshold_hours <= 1.0:
                    status = item.get('status_1hr', 'UNKNOWN')
                elif threshold_hours <= 4.0:
                    status = item.get('status_4hr', 'UNKNOWN')
                else:
                    status = item.get('status_24hr', 'UNKNOWN')
                
                if status == 'PREDICTIVE':
                    pred_time = item.get('prediction_time', '')
                    pred_price = float(item.get('prediction_price', current_price))
                    change = ((current_price - pred_price) / pred_price) * 100 if pred_price > 0 else 0
                    
                    return {
                        'status': 'PREDICTIVE',
                        'message': f"Predicted {pred_time[:10]} {pred_time[11:16]} | A${pred_price:.6f}→A${current_price:.6f} ({change:+.1f}%)",
                        'hours_since': hours_since,
                        'predicted_price': pred_price,
                        'prediction_time': pred_time
                    }
                elif status == 'REACTIVE':
                    return {
                        'status': 'REACTIVE', 
                        'message': f"Just predicted ({hours_since:.1f}h ago)",
                        'hours_since': hours_since
                    }
            
            # Fallback: check predictions table directly
            pred_table = dynamodb.Table('stockiq-coinspot-predictions')
            response = pred_table.scan(
                FilterExpression='symbol = :symbol',
                ExpressionAttributeValues={':symbol': symbol}
            )
            
            if response['Items']:
                # Get most recent prediction
                predictions = sorted(response['Items'], key=lambda x: x.get('prediction_time', ''), reverse=True)
                latest = predictions[0]
                
                pred_time = latest.get('prediction_time', '')
                pred_price = float(latest.get('prediction_price', current_price))
                change = ((current_price - pred_price) / pred_price) * 100 if pred_price > 0 else 0
                
                # Calculate hours since prediction
                try:
                    pred_dt = datetime.fromisoformat(pred_time.replace('Z', '+00:00'))
                    hours_since = (datetime.now() - pred_dt).total_seconds() / 3600
                except:
                    hours_since = 999
                
                if hours_since >= threshold_hours:
                    return {
                        'status': 'PREDICTIVE',
                        'message': f"Predicted {pred_time[:10]} {pred_time[11:16]} | A${pred_price:.6f}→A${current_price:.6f} ({change:+.1f}%)",
                        'hours_since': hours_since,
                        'predicted_price': pred_price,
                        'prediction_time': pred_time
                    }
                else:
                    return {
                        'status': 'REACTIVE',
                        'message': f"Just predicted ({hours_since:.1f}h ago)",
                        'hours_since': hours_since
                    }
            
            return {
                'status': 'NEW',
                'message': 'NEW ENTRY (never predicted)',
                'hours_since': 999
            }
            
        except Exception as e:
            print(f"Error checking prediction status for {symbol}: {e}")
            return {
                'status': 'UNKNOWN',
                'message': 'NEW ENTRY (never predicted)',
                'hours_since': 999
            }


def lambda_handler(event=None, context=None):
    """AWS Lambda handler - dynamically split coins based on worker count"""
    try:
        # Check if this is a single coin analysis request
        if event and 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
            
            if 'single_coin' in body:
                # Single coin analysis mode
                analytics = CryptoAnalytics()
                symbol = body['single_coin'].upper()
                print(f"🔍 Single coin analysis requested for: {symbol}")
                
                analysis = analytics.analyze_coin(symbol, {})
                if analysis:
                    return {
                        'statusCode': 200,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'coins': [analysis],
                            'status': 'success',
                            'analysis_type': 'single_coin',
                            'timestamp': datetime.now().isoformat()
                        })
                    }
                else:
                    return {
                        'statusCode': 500,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({'error': f'Failed to analyze {symbol}'})
                    }
        
        # Default multi-coin worker mode
        analytics = CryptoAnalytics()
        
        # Calculate dynamic worker allocation
        total_coins = len(analytics.target_coins)
        coins_per_worker = 10
        max_workers = (total_coins + coins_per_worker - 1) // coins_per_worker  # Ceiling division
        
        # Determine worker ID from function name
        function_name = context.function_name if context else 'worker-1'
        worker_id = 1
        
        # Extract worker number from function name
        import re
        worker_match = re.search(r'worker-?(\d+)', function_name)
        if worker_match:
            worker_id = int(worker_match.group(1))
        
        print(f"🔍 Function: {function_name} → Worker ID: {worker_id}")
        
        # Calculate coin allocation for this worker
        start_idx = (worker_id - 1) * coins_per_worker
        end_idx = min(start_idx + coins_per_worker, total_coins)
        worker_coins = analytics.target_coins[start_idx:end_idx]
        
        print(f"📊 Dynamic Allocation: {total_coins} coins → {max_workers} workers")
        print(f"📊 Worker {worker_id}: Processing coins {start_idx+1}-{end_idx} = {len(worker_coins)} coins")
        print(f"📊 Coin list: {worker_coins}")
        
        analyzed_coins = []
        for i, symbol in enumerate(worker_coins):
            print(f"📊 Processing coin {i+1}/{len(worker_coins)}: {symbol}")
            analysis = analytics.analyze_coin(symbol.upper(), {})
            if analysis:
                # Add prediction status
                pred_status = analytics.check_prediction_status(symbol.upper(), analysis['price'])
                analysis['prediction_status'] = pred_status['status']
                analysis['prediction_message'] = pred_status['message']
                analysis['hours_since_prediction'] = pred_status['hours_since']
                
                analyzed_coins.append(analysis)
                print(f"✅ {symbol} analyzed successfully")
            else:
                print(f"❌ {symbol} analysis failed")
        
        print(f"📊 Final result: {len(analyzed_coins)} coins analyzed")
        
        # All workers return the same format
        response_data = {
            'coins': analyzed_coins,
            'worker_id': worker_id,
            'status': 'success',
            'total_coins': total_coins,
            'max_workers': 54,  # Fixed to match orchestrator.py
            'coins_processed': len(analyzed_coins),
            'coins_assigned': len(worker_coins),
            'timestamp': datetime.now().isoformat()
        }
        
        # Any worker can generate the comprehensive report (configurable orchestrator)
        if analyzed_coins:
            response_data['report'] = analytics.generate_report(analyzed_coins)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        print(f"❌ Lambda error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'coins': [],
                'worker_id': worker_id if 'worker_id' in locals() else 0,
                'status': 'error',
                'message': str(e),
                'total_coins': len(analytics.target_coins) if 'analytics' in locals() else 0
            })
        }


if __name__ == "__main__":
    analytics = CryptoAnalytics()
    report = analytics.generate_report()
    print(report)
