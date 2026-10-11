"""The crypto screener's worker: one coin, or a list of coins, analysed from daily prices (Yahoo Finance).

The 54 stockiq-option-7-1-worker-N functions all run this file. stockiq-option-7-1-orchestrator holds the coin list and
sends it out ten coins a call ({"coin_list": [...]}); {"single_coin": "..."} analyses one. Called with neither, it
answers that there is nothing to do. How a coin is scored: site-overview.md section 8b, "How a coin is scored".
"""
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class CryptoAnalytics:
    def __init__(self):
        pass

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
    
    def fetch_bars(self, symbol: str) -> List[Dict]:
        """90 days of daily prices from Yahoo Finance (USD), oldest first, one dict a day: timestamp, high, low, close,
        volume. A day without a closing price is left out whole, so the figures of a day always stay together."""
        try:
            end_time = int(time.time())
            # 90 days: MACD needs 35 days of prices (with the 30 that were once asked for it was never worked out)
            start_time = end_time - (90 * 24 * 60 * 60)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}-USD"
            params = {'period1': start_time, 'period2': end_time, 'interval': '1d'}
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            response = requests.get(url, params=params, headers=headers, timeout=8)
            if response.status_code != 200:
                return []
            result = response.json()['chart']['result'][0]
            quotes = result['indicators']['quote'][0]
            closes = quotes.get('close') or []
            highs, lows, volumes = quotes.get('high') or [], quotes.get('low') or [], quotes.get('volume') or []
            pick = lambda values, i, fallback: values[i] if i < len(values) and values[i] is not None else fallback
            bars = []
            for i, timestamp in enumerate(result.get('timestamp') or []):
                close = pick(closes, i, None)
                if close is None:
                    continue
                bars.append({'timestamp': timestamp, 'high': pick(highs, i, close), 'low': pick(lows, i, close),
                             'close': close, 'volume': pick(volumes, i, 0)})
            return bars
        except Exception as e:
            print(f"Yahoo Finance error for {symbol}: {e}")
            return []

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
        # One request (it used to be two: 30 days for the changes, then 90 for everything else)
        bars = self.fetch_bars(symbol)
        # The last 30 days, counted as the price source counts them: from the start of the day 30 days back
        month_start = ((int(time.time()) - 30 * 24 * 60 * 60) // 86400) * 86400
        historical_prices = [bar['close'] for bar in bars if bar['timestamp'] >= month_start]
        change_24h = change_7d = change_30d = 0
        if len(historical_prices) > 7:
            current = historical_prices[-1]
            change_24h = ((current - historical_prices[-2]) / historical_prices[-2]) * 100
            change_7d = ((current - historical_prices[-8]) / historical_prices[-8]) * 100 if len(historical_prices) >= 8 else 0
            change_30d = ((current - historical_prices[0]) / historical_prices[0]) * 100
        else:
            historical_prices = []
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
        
        # MACD is worked out on all 90 days; everything else on the last 31, as before
        highs = [bar['high'] for bar in bars]
        lows = [bar['low'] for bar in bars]
        closes = [bar['close'] for bar in bars]
        volumes = [bar['volume'] for bar in bars]
        macd_closes = closes[:]
        highs, lows, closes, volumes = highs[-31:], lows[-31:], closes[-31:], volumes[-31:]
        
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
    
def lambda_handler(event=None, context=None):
    """AWS Lambda handler - dynamically split coins based on worker count"""
    try:
        # Check if this is a single coin analysis request
        if event and 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
            
            if isinstance(body.get('coin_list'), list):
                # Several coins in one call (the orchestrator sends ten). One call per coin made 540 calls a run,
                # about 0.8 million a month against a free allowance of one million. The analysis of each coin is
                # the same as in single-coin mode; a coin that cannot be analysed comes back as None.
                analytics = CryptoAnalytics()
                results = []
                for ticker in body['coin_list'][:25]:
                    ticker = str(ticker).upper()
                    try:
                        analysis = analytics.analyze_coin(ticker, {})
                    except Exception as e:
                        print(f"❌ {ticker}: {str(e)[:80]}")
                        analysis = None
                    results.append({'ticker': ticker, 'coin': analysis or None})
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'results': results,
                        'status': 'success',
                        'analysis_type': 'coin_list',
                        'timestamp': datetime.now().isoformat()
                    })
                }
            
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
        
        # Nothing to do without a coin. (Until 11 Oct 2026 the worker then analysed ten coins of a list written into this
        # file; the orchestrator has driven the list itself since 10 Oct, and this address is public.)
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Nothing to analyse: send {"coin_list": [...]} or {"single_coin": "..."}', 'coins': [], 'status': 'error'})
        }
        
    except Exception as e:
        print(f"❌ Lambda error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e), 'coins': [], 'status': 'error'})
        }


# A run by hand (it asks the price source): python3 lambda_function.py BTC ETH SUI20947
if __name__ == "__main__":
    import sys
    answer = json.loads(lambda_handler({'body': json.dumps({'coin_list': sys.argv[1:] or ['BTC', 'ETH']})}, None)['body'])
    for item in answer.get('results', []):
        coin = item['coin'] or {}
        print(f"{item['ticker']:<12} {coin.get('price', 0):>14.6f}  score {coin.get('score', 0):+d}  {coin.get('recommendation', '-'):<11} " + '; '.join(coin.get('score_breakdown', [])))
