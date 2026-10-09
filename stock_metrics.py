#!/usr/bin/env python3
"""
Scoring helpers for static stock pages.

The functions below are copied unchanged from the live single-stock analysis
Lambda (lambda-sync/stockiq-option-1-1-custom-analysis/lambda_function2.py),
so the score on a stock page matches the 0-100 score in the app's report.
If the Lambda's scoring changes, copy the updated functions here too.

compute_analysis() prepares the inputs the same way
analyze_stock_comprehensive_enhanced() does in the Lambda.
"""


def calculate_rsi(closes, period=14):
    """Calculate RSI"""
    if len(closes) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return None
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(closes, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    if len(closes) < slow:
        return None, None, None
    
    def ema(data, period):
        if len(data) < period:
            return [data[0]] * len(data)
        
        multiplier = 2 / (period + 1)
        ema_values = [data[0]]
        
        for i in range(1, len(data)):
            ema_val = (data[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema_val)
        
        return ema_values
    
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    
    macd_line = [fast_ema[i] - slow_ema[i] for i in range(len(closes))]
    signal_line = ema(macd_line, signal)
    histogram = [macd_line[i] - signal_line[i] for i in range(len(macd_line))]
    
    return macd_line[-1], signal_line[-1], histogram[-1]


def calculate_bollinger_bands(closes, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    if len(closes) < period:
        return None, None, None
    
    recent_closes = closes[-period:]
    sma = sum(recent_closes) / period
    
    variance = sum((x - sma) ** 2 for x in recent_closes) / period
    std = variance ** 0.5
    
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    
    return upper_band, sma, lower_band


def calculate_support_resistance_enhanced(highs, lows):
    """Enhanced support and resistance calculation"""
    try:
        if len(highs) >= 60 and len(lows) >= 60:
            # Use more sophisticated calculation for longer data
            recent_highs = sorted(highs[-60:], reverse=True)[:5]
            recent_lows = sorted(lows[-60:])[:5]
            resistance = sum(recent_highs) / len(recent_highs)
            support = sum(recent_lows) / len(recent_lows)
        else:
            # Fallback for shorter data
            resistance = max(highs[-20:]) if len(highs) >= 20 else max(highs)
            support = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        
        return support, resistance
    except:
        return 0, 0


def calculate_unified_investment_score(closes, highs, lows, volumes, rsi, macd_line, signal_line, 
                                      bb_upper, bb_lower, fundamentals, ytd_change, current, ma20, ma50, ma200, range_position):
    """Calculate unified 0-100 investment score with clear meaning"""
    score = 50  # Start neutral
    score_breakdown = []
    
    # Technical Analysis (40% weight)
    if rsi:
        if rsi < 30:
            score += 15
            score_breakdown.append("RSI Oversold: +15 (Oversold reading)")
        elif rsi > 70:
            score -= 15
            score_breakdown.append("RSI Overbought: -15 (Caution signal)")
        elif 40 <= rsi <= 60:
            score += 5
            score_breakdown.append("RSI Neutral: +5 (Healthy condition)")
    
    # Trend Analysis
    if current > ma20 > ma50:
        score += 12
        score_breakdown.append("Strong Uptrend: +12 (Price above both MAs)")
    elif current < ma20 < ma50:
        score -= 12
        score_breakdown.append("Strong Downtrend: -12 (Price below both MAs)")
    elif current > ma20:
        score += 6
        score_breakdown.append("Short-term Uptrend: +6 (Above 20-day MA)")
    elif current < ma20:
        score -= 6
        score_breakdown.append("Below 20-day MA: -6 (Short-term weakness)")
    
    # MACD Signal
    if macd_line and signal_line:
        if macd_line > signal_line:
            score += 8
            score_breakdown.append("MACD Bullish: +8 (MACD above signal)")
        else:
            score -= 8
            score_breakdown.append("MACD Bearish: -8 (MACD below signal)")
    
    # Fundamental Analysis (40% weight)
    if fundamentals:
        pe_ratio = fundamentals.get('pe_ratio')
        if pe_ratio:
            if pe_ratio < 15:
                score += 10
                score_breakdown.append(f"Low P/E ({pe_ratio:.1f}): +10 (Undervalued)")
            elif pe_ratio > 30:
                score -= 10
                score_breakdown.append(f"High P/E ({pe_ratio:.1f}): -10 (Overvalued)")
        
        revenue_growth = fundamentals.get('revenue_growth')
        if revenue_growth and revenue_growth > 15:
            score += 8
            score_breakdown.append(f"Strong Revenue Growth ({revenue_growth:.1f}%): +8")
        elif revenue_growth and revenue_growth < -10:
            score -= 8
            score_breakdown.append(f"Declining Revenue ({revenue_growth:.1f}%): -8")
        
        # Profitability Analysis (±10 points)
        profit_margin = fundamentals.get('profit_margin')
        if profit_margin is not None:
            if profit_margin > 20:
                score += 10
                score_breakdown.append(f"Excellent Profit Margin ({profit_margin:.1f}%): +10")
            elif profit_margin > 10:
                score += 5
                score_breakdown.append(f"Good Profit Margin ({profit_margin:.1f}%): +5")
            elif profit_margin < 0:
                score -= 15
                score_breakdown.append(f"Unprofitable ({profit_margin:.1f}%): -15 (Losing money)")
            elif profit_margin < 5:
                score -= 8
                score_breakdown.append(f"Weak Profit Margin ({profit_margin:.1f}%): -8")
        
        # Financial Health - Debt (±10 points)
        debt_to_equity = fundamentals.get('debt_to_equity')
        if debt_to_equity is not None:
            if debt_to_equity < 0.3:
                score += 8
                score_breakdown.append(f"Low Debt ({debt_to_equity:.2f} D/E): +8 (Strong balance sheet)")
            elif debt_to_equity > 2.0:
                score -= 10
                score_breakdown.append(f"High Debt ({debt_to_equity:.2f} D/E): -10 (Leverage risk)")
            elif debt_to_equity > 1.5:
                score -= 5
                score_breakdown.append(f"Elevated Debt ({debt_to_equity:.2f} D/E): -5")
        
        # Financial Health - Liquidity (±10 points)
        current_ratio = fundamentals.get('current_ratio')
        if current_ratio is not None:
            if current_ratio > 2.0:
                score += 8
                score_breakdown.append(f"Strong Liquidity ({current_ratio:.2f} Current Ratio): +8")
            elif current_ratio < 1.0:
                score -= 10
                score_breakdown.append(f"Liquidity Crisis ({current_ratio:.2f} Current Ratio): -10")
            elif current_ratio < 1.5:
                score -= 5
                score_breakdown.append(f"Weak Liquidity ({current_ratio:.2f} Current Ratio): -5")
        
        # Returns - ROE (±8 points)
        roe = fundamentals.get('return_on_equity')
        if roe is not None:
            if roe > 20:
                score += 8
                score_breakdown.append(f"Excellent ROE ({roe:.1f}%): +8")
            elif roe > 15:
                score += 5
                score_breakdown.append(f"Strong ROE ({roe:.1f}%): +5")
            elif roe < 0:
                score -= 10
                score_breakdown.append(f"Negative ROE ({roe:.1f}%): -10 (Destroying value)")
            elif roe < 5:
                score -= 6
                score_breakdown.append(f"Weak ROE ({roe:.1f}%): -6")
        
        # Valuation - Price/Book (±5 points)
        price_to_book = fundamentals.get('price_to_book')
        if price_to_book is not None:
            if price_to_book < 1.0:
                score += 5
                score_breakdown.append(f"Low P/B ({price_to_book:.2f}): +5 (Undervalued)")
            elif price_to_book > 5.0:
                score -= 5
                score_breakdown.append(f"High P/B ({price_to_book:.2f}): -5 (Overvalued)")
    
    # Long-term Trend - MA200 (±8 points)
    if ma200 and len(closes) >= 200:
        if current > ma200:
            pct_above = ((current - ma200) / ma200) * 100
            if pct_above > 10:
                score += 8
                score_breakdown.append(f"Strong Long-term Uptrend: +8 ({pct_above:.1f}% above MA200)")
            else:
                score += 4
                score_breakdown.append(f"Above MA200: +4 (Long-term support)")
        else:
            pct_below = ((ma200 - current) / ma200) * 100
            if pct_below > 10:
                score -= 8
                score_breakdown.append(f"Long-term Downtrend: -8 ({pct_below:.1f}% below MA200)")
            else:
                score -= 4
                score_breakdown.append(f"Below MA200: -4 (Long-term resistance)")
    
    # Market Momentum (20% weight)
    # Momentum with overextension penalties
    if ytd_change > 100:
        score -= 15
        score_breakdown.append(f"Extreme Overextension ({ytd_change:+.1f}% YTD): -15 (High pullback risk)")
    elif ytd_change > 50:
        score -= 8
        score_breakdown.append(f"Overextended ({ytd_change:+.1f}% YTD): -8 (Caution - mean reversion likely)")
    elif ytd_change > 30:
        score += 3
        score_breakdown.append(f"Strong Momentum ({ytd_change:+.1f}% YTD): +3 (Good but stretched)")
    elif ytd_change > 15:
        score += 7
        score_breakdown.append(f"Healthy Momentum ({ytd_change:+.1f}% YTD): +7 (Ideal range)")
    elif ytd_change > 0:
        score += 3
        score_breakdown.append(f"Positive YTD ({ytd_change:+.1f}%): +3")
    elif ytd_change > -20:
        score -= 5
        score_breakdown.append(f"Underperforming ({ytd_change:+.1f}% YTD): -5")
    else:
        score -= 10
        score_breakdown.append(f"Severe Underperformance ({ytd_change:+.1f}% YTD): -10")
    
    # Volume confirmation
    if volumes:
        avg_volume = sum(volumes[-20:]) / min(20, len(volumes))
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio > 1.5:
            score += 3
            score_breakdown.append(f"High Volume ({volume_ratio:.1f}x): +3 (Strong interest)")
        elif volume_ratio < 0.5:
            score -= 3
            score_breakdown.append(f"Low Volume ({volume_ratio:.1f}x): -3 (Weak interest)")
    
    # Range Position - Overextension Check (±5 points)
    if range_position > 95:
        score -= 5
        score_breakdown.append(f"Near 52-Week High ({range_position:.0f}%): -5 (Limited upside)")
    elif range_position < 5:
        score += 5
        score_breakdown.append(f"Near 52-Week Low ({range_position:.0f}%): +5 (Potential value)")
    
    final_score = max(0, min(100, score))
    return final_score, score_breakdown


def compute_analysis(closes, highs, lows, volumes, fundamentals):
    """Return the figures and 0-100 score for one stock (same inputs as the Lambda)."""
    current = closes[-1]
    prev = closes[-2] if len(closes) > 1 else current
    pct_change = ((current - prev) / prev) * 100 if prev != 0 else 0

    rsi = calculate_rsi(closes)
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current
    ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current
    ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else current
    macd_line, signal_line, _ = calculate_macd(closes)
    bb_upper, _, bb_lower = calculate_bollinger_bands(closes)
    support, resistance = calculate_support_resistance_enhanced(highs, lows)

    year_high = max(highs)
    year_low = min(lows)
    range_position = ((current - year_low) / (year_high - year_low)) * 100 if year_high != year_low else 50
    year_change = ((current - closes[0]) / closes[0]) * 100 if closes[0] != 0 else 0

    score, breakdown = calculate_unified_investment_score(
        closes, highs, lows, volumes, rsi, macd_line, signal_line,
        bb_upper, bb_lower, fundamentals, year_change, current, ma20, ma50, ma200, range_position
    )
    return {
        'price': current, 'pct_change': pct_change,
        'rsi': rsi, 'ma50': ma50, 'ma200': ma200 if len(closes) >= 200 else None,
        'macd_bullish': (macd_line > signal_line) if macd_line is not None and signal_line is not None else None,
        'support': support, 'resistance': resistance,
        'year_high': year_high, 'year_low': year_low, 'range_position': range_position,
        'year_change': year_change, 'score': score, 'breakdown': breakdown,
    }


def score_label(score):
    """Neutral wording using the app's thresholds (75 / 60 / 40 / 25)."""
    if score >= 75:
        return 'Strongly positive'
    if score >= 60:
        return 'Positive'
    if score >= 40:
        return 'Mixed'
    if score >= 25:
        return 'Negative'
    return 'Strongly negative'
