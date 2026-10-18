#!/usr/bin/env python3
"""
Scoring helpers for static stock pages.

The functions below are copied unchanged from the live single-stock analysis
Lambda (lambda-sync/stockiq-option-1-1-custom-analysis/lambda_function2.py),
so the score on a stock page matches the 0-100 score in the app's report.
If the Lambda's scoring changes, copy the updated functions here too
(check-tools/report/patch_metrics.py does it, and report_test.py fails when the two differ).

compute_analysis() prepares the inputs the same way
analyze_stock_comprehensive_enhanced() does in the Lambda.
"""


def calculate_rsi(closes, period=14):
    """RSI the standard way (Wilder's smoothing): the figure the chart and the screeners show. Until Oct 2026 this was
    a plain average of the last 14 days, so the report said 47 under a chart that said 56."""
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


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


TREND_FULL_AT = 2.0      # percent apart at which each half of the trend factor counts in full

def trend_points(current, ma20, ma50):
    """The trend factor of the score: up to 6 points for where the price is against its 20-day average, and up to 6 for
    where the 20-day average is against the 50-day, each in full at 2% apart. Returns (points, name, words).
    Until Oct 2026 this was +12 or -12 on the sign alone, so a share 0.03% under its 20-day average, up 45% in a year,
    read "Strong Downtrend: -12", and a move of a few cents swung the score by 24 points."""
    if not ma20 or not ma50:
        return 0, 'Flat Trend', 'not enough history for the averages'
    price_gap = (current / ma20 - 1) * 100
    average_gap = (ma20 / ma50 - 1) * 100
    part = lambda gap: max(-1.0, min(1.0, gap / TREND_FULL_AT))
    short, longer = 6 * part(price_gap), 6 * part(average_gap)
    points = int(round(short + longer))
    # Little either way is "flat"; two clear halves that point opposite ways are "mixed" (a bounce inside a decline)
    middle = 'Mixed Trend' if abs(short) >= 3 and abs(longer) >= 3 and short * longer < 0 else 'Flat Trend'
    name = ('Strong Uptrend' if points >= 9 else 'Uptrend' if points >= 3 else 'Strong Downtrend' if points <= -9
            else 'Downtrend' if points <= -3 else middle)
    side = lambda gap: 'level with' if abs(gap) < 0.05 else f"{abs(gap):.1f}% {'above' if gap > 0 else 'below'}"
    return points, name, f"price {side(price_gap)} its 20-day average; 20-day average {side(average_gap)} the 50-day"


def calculate_unified_investment_score(closes, highs, lows, volumes, rsi, macd_line, signal_line, 
                                      bb_upper, bb_lower, fundamentals, ytd_change, current, ma20, ma50, ma200, range_position):
    """Calculate unified 0-100 investment score with clear meaning"""
    score = 50  # Start neutral
    score_breakdown = []
    
    # Technical Analysis (40% weight)
    if rsi:
        # Turned round on 18 Oct 2026 (check-tools/scoring/page_score_study.py): the score bet against the trend (oversold +15,
        # overbought -15, a big rise over the year marked down, near the 52-week low marked up) and its top fifth did worse than
        # its bottom fifth in 13 of 18 half-periods of five years of prices. Now as the screeners' trend score: only an RSI over
        # 80 counts against a share, the year's rise counts for it, and so does standing near the top of its range.
        if rsi > 80:
            score -= 5
            score_breakdown.append(f"RSI Very High ({rsi:.0f}): -5 (stretched)")
        elif 40 <= rsi <= 60:
            score += 5
            score_breakdown.append("RSI Neutral: +5 (Healthy condition)")
    
    # Trend: graded, not all-or-nothing (see trend_points)
    trend, trend_name, trend_words = trend_points(current, ma20, ma50)
    score += trend
    score_breakdown.append(f"{trend_name}: {trend:+d} ({trend_words})")

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
                score_breakdown.append(f"Low P/E ({pe_ratio:.1f}): +10 (Low valuation)")
            elif pe_ratio > 30:
                score -= 10
                score_breakdown.append(f"High P/E ({pe_ratio:.1f}): -10 (High valuation)")
        
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
                score_breakdown.append(f"Low Liquidity ({current_ratio:.2f} Current Ratio): -10")
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
                score_breakdown.append(f"Negative ROE ({roe:.1f}%): -10 (Negative return)")
            elif roe < 5:
                score -= 6
                score_breakdown.append(f"Weak ROE ({roe:.1f}%): -6")
        
        # Valuation - Price/Book (±5 points)
        price_to_book = fundamentals.get('price_to_book')
        if price_to_book is not None:
            if price_to_book < 1.0:
                score += 5
                score_breakdown.append(f"Low P/B ({price_to_book:.2f}): +5 (Low valuation)")
            elif price_to_book > 5.0:
                score -= 5
                score_breakdown.append(f"High P/B ({price_to_book:.2f}): -5 (High valuation)")
    
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
    # The rise over the year, counted with the trend
    if ytd_change > 100:
        score += 12
        score_breakdown.append(f"Very Strong Rise ({ytd_change:+.1f}% over 1 year): +12 (strong momentum)")
    elif ytd_change > 50:
        score += 10
        score_breakdown.append(f"Strong Rise ({ytd_change:+.1f}% over 1 year): +10 (strong momentum)")
    elif ytd_change > 30:
        score += 8
        score_breakdown.append(f"Strong Momentum ({ytd_change:+.1f}% over 1 year): +8")
    elif ytd_change > 15:
        score += 7
        score_breakdown.append(f"Healthy Momentum ({ytd_change:+.1f}% over 1 year): +7 (Ideal range)")
    elif ytd_change > 0:
        score += 3
        score_breakdown.append(f"Up Over 1 Year ({ytd_change:+.1f}%): +3")
    elif ytd_change > -20:
        score -= 5
        score_breakdown.append(f"Underperforming ({ytd_change:+.1f}% over 1 year): -5")
    else:
        score -= 10
        score_breakdown.append(f"Severe Underperformance ({ytd_change:+.1f}% over 1 year): -10")
    
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
    
    # Range Position (±5 points): near the top of its range counts for a share, near the bottom against it
    if range_position > 95:
        score += 5
        score_breakdown.append(f"Near 52-Week High ({range_position:.0f}%): +5 (strong in its range)")
    elif range_position < 5:
        score -= 5
        score_breakdown.append(f"Near 52-Week Low ({range_position:.0f}%): -5 (weak in its range)")
    
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
