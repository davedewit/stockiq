import json
import urllib.request
import urllib.parse
import urllib.error
import time
from datetime import datetime, timedelta
import logging
import re
from typing import Dict, List, Optional, Any, Union, Tuple
from io import BytesIO
import base64
import sys

# Add timezone support
try:
    import pytz
except ImportError:
    pytz = None



# Import boto3 for S3 uploads and DynamoDB
try:
    import boto3
except ImportError:
    boto3 = None

# DynamoDB for analysis history
try:
    dynamodb = boto3.resource('dynamodb') if boto3 else None
    history_table = dynamodb.Table('stockiq-dashboard-analysis-history') if dynamodb else None
except Exception as e:
    print(f"⚠️ DynamoDB not available: {str(e)}")
    dynamodb = None
    history_table = None

# S3 client for reading stocks.txt
try:
    s3_client = boto3.client('s3') if boto3 else None
except Exception as e:
    print(f"⚠️ S3 client not available: {str(e)}")
    s3_client = None

# Cache for stocks.txt data
_stocks_cache = None

def get_company_name(symbol):
    """Get company name from stocks.txt in S3"""
    global _stocks_cache
    
    if not s3_client:
        return None
    
    try:
        # Load stocks.txt once and cache it
        if _stocks_cache is None:
            response = s3_client.get_object(
                Bucket='stockiq-final-websitebucket-vqekic7enf9h',
                Key='stocks.txt'
            )
            content = response['Body'].read().decode('utf-8')
            
            # Parse CSV: SYMBOL,Company Name,Sector
            _stocks_cache = {}
            import csv
            for parts in csv.reader(content.strip().split('\n')):
                if len(parts) >= 2:
                    _stocks_cache[parts[0].strip().upper()] = parts[1].strip()
        
        return _stocks_cache.get(symbol.upper())
    except Exception as e:
        print(f"Could not load company name for {symbol}: {str(e)[:50]}")
        return None



# Disable matplotlib for now due to Lambda layer issues
plt = None
mdates = None

# Global cache for API responses
_api_cache = {}

def clear_api_cache():
    """Clear the API cache to force fresh data"""
    global _api_cache
    _api_cache = {}
    print("🗑️ API cache cleared")

def save_analysis_history(user_id, symbol, company_name, report, is_background=False, timezone_offset=None):
    """Save analysis to user history"""
    if not user_id or not history_table:
        return
    
    try:
        import uuid
        from datetime import datetime, timezone
        
        analysis_id = str(uuid.uuid4())
        # Use UTC time to match dashboard Lambda and screeners
        timestamp = datetime.now(timezone.utc).isoformat()
        
        item = {
            'userId': user_id,
            'analysisId': analysis_id,
            'symbol': symbol.upper(),
            # a coin is saved as "<SYMBOL> Coin Analysis": that name is how the dashboard knows a single-coin entry
            'companyName': company_name if str(company_name or '').endswith(' Coin Analysis') else (f'Analysis {symbol.upper()}' if is_background else (company_name or '')),
            'timestamp': timestamp,
            'isRead': False if is_background else True
        }
        if str(company_name or '').endswith(' Coin Analysis'):
            item['analysisType'] = 'crypto_single'
        
        # For background tasks: store report in S3, save only S3 key in DynamoDB
        if is_background and boto3:
            try:
                s3 = boto3.client('s3')
                s3_key = f"reports/{user_id}/{analysis_id}.txt"
                s3.put_object(
                    Bucket='stockiq-dashboard-analysis-history',
                    Key=s3_key,
                    Body=report.encode('utf-8'),
                    ContentType='text/plain'
                )
                item['reportS3Key'] = s3_key
                print(f"📦 Report stored in S3: {s3_key}")
            except Exception as e:
                print(f"⚠️ S3 storage failed, falling back to DynamoDB: {str(e)}")
                item['report'] = report
        else:
            # Web UI: store report directly in DynamoDB
            item['report'] = report
        
        history_table.put_item(Item=item)
        print(f"✅ Analysis saved to history: {symbol} for user {user_id}")
    except Exception as e:
        print(f"⚠️ Failed to save analysis history: {str(e)}")

def get_user_timezone_timestamp(timezone_offset=None):
    """Get current timestamp in user's timezone"""
    try:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if timezone_offset is not None:
            # Apply timezone offset (in hours)
            now += timedelta(hours=timezone_offset)
            return now.strftime('%d/%m/%Y, %H:%M:%S')
        else:
            # Use a reasonable default (e.g., EST/EDT -5) instead of UTC
            now += timedelta(hours=-5)  # Default to US Eastern Time
            return now.strftime('%d/%m/%Y, %H:%M:%S')
    except Exception as e:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        return now.strftime('%d/%m/%Y, %H:%M:%S') + ' UTC'
_asx_message_shown = set()

# Finnhub Configuration
FINNHUB_API_KEY = "d2rr7chr01qv11lft3v0d2rr7chr01qv11lft3vg"
FINNHUB_SECRET = "d2rr7chr01qv11lft40g"
FINNHUB_RATE_LIMIT = 1.2
_last_finnhub_call = 0
_finnhub_failures = 0
_finnhub_disabled_session = False
USE_FINNHUB = True

# Data source tracking
_data_sources = {
    'yahoo_calls': 0,
    'finnhub_calls': 0,
    'yahoo_data_points': 0,
    'finnhub_data_points': 0,
    'yahoo_success': 0,
    'finnhub_success': 0,
    'finnhub_failures': 0
}

def reset_data_source_tracking():
    """Reset data source tracking for new analysis"""
    global _data_sources
    _data_sources = {
        'yahoo_calls': 0,
        'finnhub_calls': 0,
        'yahoo_data_points': 0,
        'finnhub_data_points': 0,
        'yahoo_success': 0,
        'finnhub_success': 0,
        'finnhub_failures': 0
    }

def track_data_source(source, call_type='call', data_points=1, success=True):
    """Track data source usage"""
    global _data_sources
    if call_type == 'call':
        _data_sources[f'{source}_calls'] += 1
        if success:
            _data_sources[f'{source}_success'] += 1
        elif source == 'finnhub':
            _data_sources['finnhub_failures'] += 1
    else:
        _data_sources[f'{source}_data_points'] += data_points

def get_data_source_summary():
    """Get data source usage summary"""
    total_calls = _data_sources['yahoo_calls'] + _data_sources['finnhub_calls']
    total_points = _data_sources['yahoo_data_points'] + _data_sources['finnhub_data_points']
    
    if total_calls == 0:
        return "No data sources used"
    
    yahoo_pct = (_data_sources['yahoo_calls'] / total_calls) * 100 if total_calls > 0 else 0
    finnhub_pct = (_data_sources['finnhub_calls'] / total_calls) * 100 if total_calls > 0 else 0
    
    summary = []
    if _data_sources['yahoo_calls'] > 0:
        yahoo_success_rate = (_data_sources['yahoo_success'] / _data_sources['yahoo_calls']) * 100
        summary.append(f"⚡ Yahoo Finance: {_data_sources['yahoo_calls']} calls ({yahoo_pct:.0f}%), {_data_sources['yahoo_data_points']} data points, {yahoo_success_rate:.0f}% success")
    
    if _data_sources['finnhub_calls'] > 0:
        finnhub_success_rate = (_data_sources['finnhub_success'] / _data_sources['finnhub_calls']) * 100
        status_icon = "✅" if finnhub_success_rate > 50 else "❌"
        summary.append(f"{status_icon} Finnhub: {_data_sources['finnhub_calls']} calls ({finnhub_pct:.0f}%), {_data_sources['finnhub_data_points']} data points, {finnhub_success_rate:.0f}% success")
        if _data_sources['finnhub_failures'] > 0:
            summary.append(f"   └─ {_data_sources['finnhub_failures']} failures detected")
    
    return "\n".join(summary)

def upload_chart_to_s3(fig, symbol, chart_type):
    """Upload matplotlib figure to S3 and return CloudFront URL"""
    if not boto3 or not plt:
        return None
    
    try:
        s3 = boto3.client('s3')
        bucket = 'stockiq-final-websitebucket-vqekic7enf9h'
        
        # Save figure to bytes
        img_buffer = BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        img_buffer.seek(0)
        
        # Upload to S3
        timestamp = int(time.time())
        key = f"charts/{symbol}_{chart_type}_{timestamp}.png"
        s3.upload_fileobj(img_buffer, bucket, key, 
                         ExtraArgs={'ContentType': 'image/png'})
        
        # Return CloudFront URL
        cloudfront_url = f"https://d26vntjujxixyq.cloudfront.net/{key}"
        print(f"📊 Chart uploaded: {cloudfront_url}")
        return cloudfront_url
        
    except Exception as e:
        print(f"Chart upload failed: {str(e)}")
        return None

def generate_stock_charts_via_lambda(symbol, stock_data, levels=None):
    """Generate charts via stockiq-chart-generator Lambda"""
    if not boto3:
        print(f"Chart generation skipped for {symbol}: boto3 not available")
        return None, None
    
    try:
        lambda_client = boto3.client('lambda')
        
        # The chart function is sent the very bars this report is scored on, with its support and resistance, so that
        # the picture and the text cannot differ (it used to fetch its own and work out its own RSI: 56 above, 47 below)
        chart_payload = {
            'symbol': _report_ctx.get('label') or symbol,          # the chart's title; a coin's familiar symbol, not its ticker
            'return_type': 'url'  # Request URLs for background analysis
        }
        if stock_data and len(stock_data) >= 50 and all('timestamp' in bar for bar in stock_data):
            chart_payload['series'] = {'t': [bar['timestamp'] for bar in stock_data],
                                       'h': [round(bar['high'], 4) for bar in stock_data],
                                       'l': [round(bar['low'], 4) for bar in stock_data],
                                       'c': [round(bar['close'], 4) for bar in stock_data],
                                       'v': [bar['volume'] for bar in stock_data]}
            chart_payload['currency'] = _report_ctx.get('currency') or ''
            chart_payload.update(levels or {})
        
        print(f"📊 Invoking chart generator for {symbol}")
        
        response = lambda_client.invoke(
            FunctionName='stockiq-chart-generator',
            InvocationType='RequestResponse',
            Payload=json.dumps(chart_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200 and 'body' in result:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
            price_chart = body.get('price_chart_url')
            volume_chart = body.get('volume_chart_url', price_chart)  # Use price chart as fallback
            print(f"✅ Charts generated for {symbol}: price={price_chart is not None}, volume={volume_chart is not None}")
            return price_chart, volume_chart
        else:
            print(f"Chart generator failed for {symbol}: {result}")
            return None, None
            
    except Exception as e:
        print(f"Chart generation failed for {symbol}: {str(e)}")
        return None, None

def generate_stock_charts(symbol, stock_data):
    """Generate price and volume charts for stock"""
    # Try Lambda chart generator first, fallback to placeholder
    price_chart_url, volume_chart_url = generate_stock_charts_via_lambda(symbol, stock_data)
    
    if not price_chart_url:
        print(f"Chart generation skipped for {symbol}: using placeholder charts")
        # Return placeholder SVG charts as data URLs
        price_chart_url = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNiIgZmlsbD0iIzMzMyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkNoYXJ0IE5vdCBBdmFpbGFibGU8L3RleHQ+PC9zdmc+"
        volume_chart_url = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjE1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzMzMyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkNoYXJ0IE5vdCBBdmFpbGFibGU8L3RleHQ+PC9zdmc+"
    
    return price_chart_url, volume_chart_url
    
    if len(stock_data) < 5:
        print(f"Chart generation skipped for {symbol}: insufficient data ({len(stock_data)} points)")
        return None, None
    
    try:
        print(f"📊 Generating charts for {symbol} with {len(stock_data)} data points")
        
        # Use available data (up to 60 days)
        chart_data = stock_data[-60:] if len(stock_data) >= 60 else stock_data
        
        # Extract data with validation
        dates = [d['date'] for d in chart_data if d.get('date')]
        closes = [d['close'] for d in chart_data if d.get('close') is not None]
        volumes = [d['volume'] for d in chart_data if d.get('volume') is not None]
        highs = [d['high'] for d in chart_data if d.get('high') is not None]
        lows = [d['low'] for d in chart_data if d.get('low') is not None]
        
        if len(dates) < 5 or len(closes) < 5:
            print(f"Insufficient valid data for {symbol} charts")
            return None, None
        
        # Create price chart
        fig1, ax1 = plt.subplots(figsize=(12, 6))
        ax1.plot(dates, closes, linewidth=2, color='#1f77b4', label='Price')
        if len(highs) == len(dates) and len(lows) == len(dates):
            ax1.fill_between(dates, lows, highs, alpha=0.3, color='#1f77b4')
        ax1.set_title(f'{symbol} - Price Chart ({len(dates)} Days)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Format x-axis
        if len(dates) > 10:
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        price_chart_url = upload_chart_to_s3(fig1, symbol, 'price')
        plt.close(fig1)
        
        # Create volume chart
        fig2, ax2 = plt.subplots(figsize=(12, 4))
        if len(volumes) == len(dates):
            ax2.bar(dates, volumes, color='#ff7f0e', alpha=0.7)
        ax2.set_title(f'{symbol} - Volume Chart ({len(dates)} Days)', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Volume', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        if len(dates) > 10:
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        volume_chart_url = upload_chart_to_s3(fig2, symbol, 'volume')
        plt.close(fig2)
        
        print(f"✅ Charts generated for {symbol}: price={price_chart_url is not None}, volume={volume_chart_url is not None}")
        return price_chart_url, volume_chart_url
        
    except Exception as e:
        print(f"Chart generation failed for {symbol}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None

def finnhub_rate_limit():
    """Enforce Finnhub rate limiting"""
    global _last_finnhub_call
    if USE_FINNHUB:
        elapsed = time.time() - _last_finnhub_call
        if elapsed < FINNHUB_RATE_LIMIT:
            sleep_time = FINNHUB_RATE_LIMIT - elapsed
            time.sleep(sleep_time)
        _last_finnhub_call = time.time()

def fetch_finnhub_data(endpoint, params, data_type="advanced"):
    """Fetch data from Finnhub with proper error handling"""
    global _finnhub_failures, _finnhub_disabled_session
    
    if not USE_FINNHUB or not FINNHUB_API_KEY or _finnhub_disabled_session:
        return None
    
    symbol = params.get('symbol', '')
    
    # Skip ASX stocks
    if '.AX' in symbol:
        return None
    
    # Skip problematic stocks
    problematic_stocks = ['NEO', 'NIO', 'XPEV', 'LI', 'BABA', 'JD', 'PDD']
    if symbol.upper() in problematic_stocks:
        return None
    
    # Check failure count
    if _finnhub_failures >= 3:
        _finnhub_disabled_session = True
        return None
    
    finnhub_rate_limit()
    
    try:
        # Use urllib instead of requests
        params['token'] = FINNHUB_API_KEY
        query_string = urllib.parse.urlencode(params)
        url = f"https://finnhub.io/api/v1/{endpoint}?{query_string}"
        
        print(f"🔥 Finnhub: {data_type} data for {symbol}")
        
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() in [429, 403]:
                print(f"⚠️ Finnhub API limit - falling back to Yahoo")
                _finnhub_failures += 1
                return None
            
            result = json.loads(response.read().decode())
            
            # Validate result
            if not result or (isinstance(result, dict) and not any(result.values())):
                print(f"⚠️ {symbol} not available on Finnhub")
                return None
        
            # Track successful call
            track_data_source('finnhub', 'call', success=True)
            
            # Count data points
            data_points = 0
            if isinstance(result, dict):
                if 'metric' in result and isinstance(result['metric'], dict):
                    data_points = len([v for v in result['metric'].values() if v is not None])
                else:
                    data_points = len([v for v in result.values() if v is not None])
            
            track_data_source('finnhub', 'data', data_points)
            
            print(f"✅ Finnhub data received for {symbol}: {data_points} data points")
            return result
            
    except urllib.error.HTTPError as e:
        if e.code in [429, 403]:
            print(f"⚠️ Finnhub API limit ({e.code}) - falling back to Yahoo")
            _finnhub_failures += 1
        else:
            print(f"⚠️ Finnhub HTTP error {e.code} for {symbol}")
            _finnhub_failures += 1
        return None
    except Exception as e:
        print(f"⚠️ Finnhub error for {symbol}: {str(e)[:50]}")
        _finnhub_failures += 1
        track_data_source('finnhub', 'call', success=False)
        return None

def lambda_handler(event, context):
    """Enhanced Custom Stock Analysis with Full Feature Set"""
    # Block known bot/crawler IP ranges before doing any work
    try:
        source_ip = event.get('requestContext', {}).get('http', {}).get('sourceIp', '')
        bot_ranges = ['66.249.', '43.172.', '43.173.', '43.119.', '47.82.']  # Googlebot, Tencent Cloud bots, Alibaba Cloud scraper (Sep 2026)
        if any(source_ip.startswith(r) for r in bot_ranges):
            print(f"🤖 Blocked Googlebot IP: {source_ip}")
            # Record the block in DynamoDB for daily report
            try:
                import boto3
                from datetime import datetime, timezone
                _ddb = boto3.resource('dynamodb', region_name='us-east-1')
                _table = _ddb.Table('stockiq-user-tracking')
                today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                ttl_48h = int(datetime.now(timezone.utc).timestamp()) + (48 * 3600)
                bot_range = next((r for r in bot_ranges if source_ip.startswith(r)), 'unknown')
                _table.update_item(
                    Key={'user_date': f'bot_blocked#{today}'},
                    UpdateExpression='ADD block_count :inc SET last_ip = :ip, last_range = :range, updated_at = :ts, ttl = :ttl',
                    ExpressionAttributeValues={
                        ':inc': 1,
                        ':ip': source_ip,
                        ':range': bot_range,
                        ':ts': datetime.now(timezone.utc).isoformat(),
                        ':ttl': ttl_48h
                    }
                )
            except Exception as e:
                print(f"Failed to record bot block: {e}")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Bot requests not supported', 'bot_blocked': True})
            }
    except Exception:
        pass

    # Reset global state for each invocation (Lambda container reuse)
    global _finnhub_failures, _finnhub_disabled_session
    _finnhub_failures = 0
    _finnhub_disabled_session = False
    
    try:
        # Handle Lambda Function URL format (direct JSON) vs API Gateway format
        if isinstance(event, dict):
            if 'body' in event and event['body']:
                # API Gateway format
                if isinstance(event['body'], str):
                    body = json.loads(event['body'])
                else:
                    body = event['body']
            else:
                # Lambda Function URL format (direct JSON)
                body = event
        else:
            body = {}
        
        symbols = body.get('symbols', [])
        asset = str(body.get('asset') or '').lower()   # 'crypto': the symbols are coins (the single-coin button)
        labels = {}
        user_id = body.get('userId')  # Get userId from request
        timezone_offset = body.get('timezone_offset', None)  # Hours from UTC
        skip_history_save = body.get('skipHistorySave', False)  # Web UI sets this to prevent duplicates
        is_background_task = body.get('isBackgroundTask', False)  # Dashboard background task flag
        
        # Debug logging to stderr
        import sys
        print(f"Event type: {type(event)}", file=sys.stderr)
        print(f"Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}", file=sys.stderr)
        print(f"Body: {body}", file=sys.stderr)
        print(f"Symbols received: {symbols}", file=sys.stderr)
        
        # Validate symbols
        if not symbols or not isinstance(symbols, list) or len(symbols) == 0:
            print(f"Invalid symbols: {symbols}")
            return error_response(400, f'Valid symbols array required. Received: {symbols}')
        
        # Clean and validate symbols
        clean_symbols = []
        for symbol in symbols[:10]:  # Limit to 10 symbols
            if symbol and isinstance(symbol, str):
                clean_symbol = str(symbol).upper().strip()
                if len(clean_symbol) >= 1:
                    if asset == 'crypto':
                        label, clean_symbol = coin_ticker(clean_symbol)
                        labels[clean_symbol] = label
                    clean_symbols.append(clean_symbol)
        
        if not clean_symbols:
            return error_response(400, f'No valid symbols found in: {symbols}')
        
        print(f"Processing symbols: {clean_symbols}", file=sys.stderr)
        
        # Analyze each symbol with enhanced features
        results = []
        for symbol in clean_symbols:
            print(f"Processing symbol: '{symbol}'", file=sys.stderr)
            
            try:
                # Detect if this is background analysis
                # Background = no userId OR isBackgroundTask flag set
                is_background = user_id is None or is_background_task
                analysis = analyze_stock_comprehensive_enhanced(symbol, timezone_offset, is_background, labels.get(symbol))
                if analysis:
                    results.append(analysis)
                    
                    # Save to user history for background tasks or when no userId
                    print(f"🔍 History save check: user_id={user_id}, skip={skip_history_save}, is_bg_task={is_background_task}", file=sys.stderr)
                    if not skip_history_save and (is_background_task or not user_id) and analysis.get('comprehensive_analysis'):
                        save_user_id = user_id if user_id else 'background'
                        print(f"💾 SAVING to history for {symbol} (userId={save_user_id}, background={is_background_task})", file=sys.stderr)
                        # Pass is_background flag to store report in S3 for background tasks
                        save_analysis_history(save_user_id, analysis.get('label') or symbol, analysis.get('history_name') or symbol, analysis.get('comprehensive_analysis'), is_background=is_background_task, timezone_offset=timezone_offset)
                    else:
                        print(f"⏭️ SKIPPING history save for {symbol} (skip={skip_history_save})", file=sys.stderr)
                    
                    print(f"✅ Successfully analyzed: {symbol}", file=sys.stderr)
                else:
                    print(f"❌ Failed to analyze: {symbol}", file=sys.stderr)
            except Exception as e:
                print(f"❌ Error analyzing {symbol}: {e}", file=sys.stderr)
                continue
        
        print(f"Total results: {len(results)}", file=sys.stderr)
        
        if not results:
            return error_response(404, f'No valid symbols found. Processed: {clean_symbols}')
        
        return success_response({
            'option': '1.1',
            'description': 'Enhanced Custom Stock Analysis - Full Feature Set',
            'symbols_analyzed': len(results),
            'results': results,
            'timestamp': get_user_timezone_timestamp(timezone_offset)
        })
        
    except Exception as e:
        print(f"Lambda handler error: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(500, f'Internal error: {str(e)}')

def analyze_stock_comprehensive_enhanced(symbol, timezone_offset=None, is_background=False, label=None):
    """Enhanced comprehensive stock analysis matching local stock.py functionality"""
    try:
        print(f"Starting analysis for symbol: {symbol}")
        
        # Reset data source tracking for this symbol
        reset_data_source_tracking()
        
        # Get stock data
        stock_data = fetch_stock_data(symbol)
        if not stock_data:
            print(f"No stock data returned for {symbol}")
            return None
            
        if len(stock_data) < 5:  # Further reduced minimum requirement
            print(f"Insufficient data for {symbol}: {len(stock_data)} points")
            return None
            
        print(f"Got {len(stock_data)} data points for {symbol}")
        
        # A coin: the single-coin button sends its symbols as coins; a ticker like BTC-USD typed as a stock is one too
        is_coin = _report_ctx.get('instrument') == 'CRYPTOCURRENCY'
        _report_ctx['coin'] = is_coin
        _report_ctx['label'] = (label or re.sub(r'-USD$', '', symbol)) if is_coin else None
        
        # Extract price data
        closes = [d['close'] for d in stock_data]
        highs = [d['high'] for d in stock_data]
        lows = [d['low'] for d in stock_data]
        volumes = [d['volume'] for d in stock_data]
        
        current = closes[-1]
        prev = closes[-2] if len(closes) > 1 else current
        change = current - prev
        pct_change = (change / prev) * 100 if prev != 0 else 0
        
        # Enhanced technical indicators
        rsi = calculate_rsi(closes)
        ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current
        ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current
        ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else current
        
        # Advanced technical indicators
        macd_line, signal_line, histogram = calculate_macd(closes)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
        stoch_k, stoch_d = calculate_stochastic(highs, lows, closes)
        williams_r = calculate_williams_r(highs, lows, closes)
        mfi = calculate_money_flow_index(highs, lows, closes, volumes)
        
        # Support/Resistance with enhanced calculation
        support, resistance = calculate_support_resistance_enhanced(highs, lows)
        
        # Enhanced fundamental analysis with Finnhub
        # a coin has no company figures and pays no dividend: nothing is asked for
        fundamentals = {} if is_coin else fetch_enhanced_fundamentals(symbol)
        if not is_coin:
            fill_missing_figures(symbol, fundamentals)
        fundamental_score, trajectory = calculate_fundamental_score_enhanced(fundamentals)
        
        # Advanced risk analysis
        risk_metrics = calculate_risk_metrics_enhanced(closes, volumes)
        distress_signals, severity_score = detect_company_distress_signals(symbol, fundamentals, closes, volumes)
        
        # Long-term trend analysis
        trend_data = analyze_long_term_trends_enhanced(closes, volumes)
        
        # Chart pattern recognition
        patterns = detect_chart_patterns_enhanced(highs, lows, closes)
        
        # Market intelligence
        # (not for a coin: the VIX is the stock market's mood, and the news comes from the share's own stock page)
        market_sentiment = None if is_coin else fetch_market_sentiment()
        recent_news = None if is_coin else fetch_recent_news_from_stock_page(symbol)
        news_sentiment = None if is_coin else fetch_news_sentiment_enhanced(symbol)
        
        # Technical score calculation
        technical_score = calculate_technical_score_enhanced(
            closes, highs, lows, volumes, rsi, macd_line, signal_line,
            bb_upper, bb_lower, stoch_k, williams_r, mfi
        )
        
        # Overall recommendation
        recommendation = get_recommendation_enhanced(fundamental_score, technical_score, severity_score)
        
        # Additional performance metrics
        volatility = calculate_volatility(closes)
        momentum_5d = calculate_momentum(closes, 5)
        momentum_20d = calculate_momentum(closes, 20)
        
        # Calculate additional metrics
        # Volume against the 20-day average, as the score does. While today's session is still open its volume is a
        # part of a day: it is left out (it used to read "Low Volume: -3" every morning)
        score_volumes = volumes[:-1] if _report_ctx.get('partial_day') and len(volumes) > 21 else volumes
        recent_volumes = score_volumes[-20:]
        avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
        current_volume = score_volumes[-1] if score_volumes else 0
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        year_high = max(highs)
        year_low = min(lows)
        range_position = ((current - year_low) / (year_high - year_low)) * 100 if year_high != year_low else 50
        ytd_change = ((current - closes[0]) / closes[0]) * 100 if closes[0] != 0 else 0
        week_change = ((current - closes[-5]) / closes[-5] * 100) if len(closes) >= 5 else 0
        month_change = ((current - closes[-20]) / closes[-20] * 100) if len(closes) >= 20 else 0
        
        # Generate charts via Lambda chart generator for ALL users
        price_chart_url, volume_chart_url = generate_stock_charts_via_lambda(symbol, stock_data, {'support': support, 'resistance': resistance})
        print(f"📊 Generating charts for {symbol} (background: {is_background})")
        
        # Calculate unified investment score
        unified_score, score_breakdown = calculate_unified_investment_score(
            closes, highs, lows, score_volumes, rsi, macd_line, signal_line,
            bb_upper, bb_lower, fundamentals, ytd_change, current, ma20, ma50, ma200, range_position
        )
        
        # Get clear recommendation with action plan
        rec_data = get_clear_recommendation_and_action(unified_score, current, support, resistance, fundamentals, rsi, bb_upper, ytd_change, range_position, closes)
        
        # Generate comprehensive analysis text with new streamlined format
        analysis_text = generate_streamlined_analysis(
            symbol, current, change, pct_change, closes, highs, lows, score_volumes,
            rsi, ma20, ma50, ma200, macd_line, signal_line, bb_upper, bb_lower,
            support, resistance, fundamentals, fundamental_score, technical_score,
            recommendation, volatility, momentum_5d, momentum_20d, risk_metrics,
            trend_data, patterns, market_sentiment, news_sentiment, distress_signals,
            avg_volume, current_volume, year_high, year_low, range_position,
            ytd_change, week_change, month_change, stoch_k, stoch_d, williams_r, mfi,
            price_chart_url, volume_chart_url, timezone_offset, is_background, recent_news
        )
        
        return {
            'symbol': symbol,
            'label': _report_ctx.get('label') or symbol,
            'asset': 'crypto' if is_coin else 'share',
            'history_name': f"{_report_ctx.get('label')} Coin Analysis" if is_coin else None,
            'current_price': current,
            'daily_change': change,
            'daily_change_pct': pct_change,
            'week_change': week_change,
            'month_change': month_change,
            'ytd_change': ytd_change,
            'year_high': year_high,
            'year_low': year_low,
            'range_position': range_position,
            
            # NEW: Unified Investment Scoring System
            'investment_score': unified_score,  # 0-100 clear scoring
            'score_breakdown': score_breakdown,  # Detailed explanation of score components
            'clear_recommendation': signal_label(rec_data['recommendation']),  # neutral label, e.g. 'Positive signals'
            'action_plan': rec_data['action'],  # Specific action to take
            'confidence_level': rec_data['confidence'],  # High/Medium/Low
            'position_size': rec_data['position_size'],  # Recommended portfolio allocation
            'urgency': rec_data['urgency'],  # Timing guidance
            'stop_loss': rec_data['stop_loss'],  # Risk management level
            'take_profit': rec_data['take_profit'],  # Profit target
            'risk_reward_ratio': rec_data['risk_reward_ratio'],  # Risk/reward calculation
            
            # Technical indicators (preserved)
            'rsi': rsi,
            'ma20': ma20,
            'ma50': ma50,
            'ma200': ma200,
            'macd_line': macd_line,
            'signal_line': signal_line,
            'bb_upper': bb_upper,
            'bb_lower': bb_lower,
            'stochastic_k': stoch_k,
            'stochastic_d': stoch_d,
            'williams_r': williams_r,
            'money_flow_index': mfi,
            'support': support,
            'resistance': resistance,
            
            # Volume analysis (preserved)
            'current_volume': current_volume,
            'avg_volume': avg_volume,
            'volume_ratio': volume_ratio,
            
            # Performance metrics (preserved)
            'volatility': volatility,
            'momentum_5d': momentum_5d,
            'momentum_20d': momentum_20d,
            
            # Legacy scores (preserved for backward compatibility)
            'fundamental_score': fundamental_score,
            'technical_score': technical_score,
            'recommendation': recommendation,  # Legacy recommendation
            
            # Enhanced fundamentals
            'pe_ratio': fundamentals.get('pe_ratio') if fundamentals else None,
            'beta': fundamentals.get('beta') if fundamentals else None,
            'market_cap': fundamentals.get('market_cap') if fundamentals else None,
            'dividend_yield': fundamentals.get('dividend_yield') if fundamentals else None,
            'revenue_growth': fundamentals.get('revenue_growth') if fundamentals else None,
            'profit_margin': fundamentals.get('profit_margin') if fundamentals else None,
            'debt_to_equity': fundamentals.get('debt_to_equity') if fundamentals else None,
            'return_on_equity': fundamentals.get('return_on_equity') if fundamentals else None,
            
            # Risk analysis
            'risk_metrics': risk_metrics,
            'distress_signals': distress_signals,
            'severity_score': severity_score,
            'bankruptcy_risk': severity_score >= 7,
            
            # Market intelligence
            'trend_data': trend_data,
            'chart_patterns': patterns,
            'market_sentiment': market_sentiment,
            'news_sentiment': news_sentiment,
            
            # Meta data
            'data_points': len(closes),
            'comprehensive_analysis': analysis_text,
            'enhanced_features': True
        }
        
    except Exception as e:
        print(f"Error analyzing {symbol}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def generate_streamlined_analysis(symbol, current, change, pct_change, closes, highs, lows, volumes,
                                 rsi, ma20, ma50, ma200, macd_line, signal_line, bb_upper, bb_lower,
                                 support, resistance, fundamentals, fundamental_score, technical_score,
                                 recommendation, volatility, momentum_5d, momentum_20d, risk_metrics,
                                 trend_data, patterns, market_sentiment, news_sentiment, distress_signals,
                                 avg_volume, current_volume, year_high, year_low, range_position,
                                 ytd_change, week_change, month_change, stoch_k, stoch_d, williams_r, mfi,
                                 price_chart_url=None, volume_chart_url=None, timezone_offset=None, is_background=False, recent_news=None):
    """Generate streamlined analysis with complete formatted header matching web UI"""
    
    # Calculate unified score and get clear recommendation
    unified_score, score_breakdown = calculate_unified_investment_score(
        closes, highs, lows, volumes, rsi, macd_line, signal_line,
        bb_upper, bb_lower, fundamentals, ytd_change, current, ma20, ma50, ma200, range_position
    )
    
    rec_data = get_clear_recommendation_and_action(unified_score, current, support, resistance, fundamentals, rsi, bb_upper, ytd_change, range_position, closes)
    
    analysis = []
    
    # FORMATTED HEADER SECTION - Matching Web UI
    analysis.append(f"{'='*80}")
    coin = bool(_report_ctx.get('coin'))
    shown = _report_ctx.get('label') or symbol
    day_words = 'since 00:00 UTC' if coin else 'today'      # a coin's day runs from midnight UTC, and never closes
    analysis.append(f"🔍 SINGLE COIN ANALYSIS: {shown}" if coin else f"📊 CUSTOM STOCK ANALYSIS RESULTS (LATEST AVAILABLE PRICES)")
    analysis.append(f"{'='*80}")
    
    # Get current timestamp
    timestamp = get_user_timezone_timestamp(timezone_offset)
    analysis.append(f"\n🕐 Analysis Generated: {timestamp} ({zone_label(timezone_offset)})")
    
    # Get company name from stocks.txt
    if coin:
        company_name = re.sub(r'\s+USD$', '', _report_ctx.get('name') or '')
    else:
        company_name = get_company_name(symbol) or _report_ctx.get('name')
    symbol_display = f"{shown} - {company_name}" if company_name else shown
    analysis.append(f"📈 Symbol: {symbol_display}")
    
    analysis.append(f"💰 Current Price: {money(current)} ({pct_change:+.2f}% {day_words})")
    if currency_note(current):
        analysis.append(currency_note(current))
    if coin:
        analysis.append(f"ℹ️ Priced as {symbol} on Yahoo Finance, in US dollars. Some symbols are shared by more than one coin: check the price matches the coin you mean")
        if shown in COIN_WRONG_MATCH:
            analysis.append(f"⚠️ {shown}: the price source lists a different coin under this symbol, so this analysis is probably not for the coin you mean")
    
    # Add chart for ALL users
    if price_chart_url:
        analysis.append(f"\n📊 TECHNICAL CHART:")
        analysis.append(f'<div class="chart-container" style="width: 100%; overflow: hidden; margin: 0; line-height: 0;">')
        analysis.append(f'<img src="{price_chart_url}" alt="{symbol} Price Chart" class="stock-chart" style="width: 100%; height: auto; display: block; margin: 0; padding: 0; vertical-align: bottom;" />')
        analysis.append(f'</div>')
    
    # EXECUTIVE SUMMARY - Most Important Information First
    analysis.append(f"\n{'='*60}")
    summary_title = f"🎯 EXECUTIVE SUMMARY - {symbol_display}"
    analysis.append(summary_title)
    analysis.append(f"{'='*60}")
    
    # Visual score representation
    score_bars = "█" * (unified_score // 10) + "░" * (10 - unified_score // 10)
    analysis.append(f"\nSTOCKIQ SCORE: {unified_score}/100")
    analysis.append(f"[{score_bars}]")
    analysis.append(f"0-25: Strongly negative  |  25-40: Negative  |  40-60: Mixed  |  60-75: Positive  |  75-100: Strongly positive")
    
    analysis.append(f"\n🎯 SIGNAL SUMMARY: {signal_label(rec_data['recommendation'])} (Model confidence: {rec_data['confidence']})")
    analysis.append(f"📋 WHAT THE MODEL SEES: {rec_data['action']}")
    analysis.append(f"ℹ️ General information only. This is an automated score, not a recommendation to buy or sell.")
    
    # NEWS SECTION - Move to top for visibility
    if recent_news and recent_news.get('has_news'):
        analysis.append(f"\n{'='*60}")
        analysis.append(f"📰 LATEST NEWS")
        analysis.append(f"{'='*60}")
        analysis.append(f"\n{recent_news['headline']}")
        if recent_news.get('date'):
            analysis.append(f"\n{local_news_date(recent_news, timezone_offset)}")
        analysis.append(f"\n{recent_news['summary']}")
        analysis.append(f"")
        links = []
        if recent_news.get('url'):
            links.append(f'<a href="{recent_news["url"]}" target="_blank" style="color: #007bff;">Read full article →</a>')
        links.append(f'<a href="https://stockiq.tech/stocks/{symbol}.html" target="_blank" style="color: #007bff;">View on StockIQ →</a>')
        analysis.append(' | '.join(links))
        analysis.append(f"\n{'='*60}")
    
    # Key metrics snapshot
    analysis.append(f"\n📊 KEY METRICS:")
    analysis.append(f"• Current Price: {money(current)} ({pct_change:+.2f}% {day_words})")
    analysis.append(f"• 1-Year Change: {ytd_change:+.1f}%")
    analysis.append(f"• 52-Week Range: {range_position:.0f}% ({money(year_low)} - {money(year_high)})")
    rsi_str = f"{rsi:.1f}" if rsi else 'N/A'
    analysis.append(f"• RSI: {rsi_str} ({'Oversold' if rsi and rsi < 30 else 'Overbought' if rsi and rsi > 70 else 'Neutral'})")
    trend, trend_name, trend_words = trend_points(current, ma20, ma50)
    analysis.append(f"• Trend: {trend_name} ({trend_words})")
    
    # Reference levels (calculated from volatility, support and resistance)
    analysis.append(f"\n📏 REFERENCE LEVELS (calculated automatically, not instructions):")
    analysis.append(f"• Lower reference level: {money(rec_data['stop_loss'])} ({((rec_data['stop_loss'] - current) / current * 100):+.1f}%)")
    analysis.append(f"• Upper reference level: {money(rec_data['take_profit'])} ({((rec_data['take_profit'] - current) / current * 100):+.1f}%)")
    analysis.append(f"• Distance ratio (upper vs lower): 1:{rec_data['risk_reward_ratio']:.1f}")
    analysis.append(f"• Volatility: {volatility:.1f}% ({'Low' if volatility < 15 else 'Moderate' if volatility < 25 else 'High'} risk)")
    
    # What the reading means (descriptive only)
    analysis.append(f"\n📋 HOW TO READ THIS:")
    if rec_data['recommendation'] in ['STRONG BUY', 'BUY']:
        analysis.append(f"1. The model reads the current data as {signal_label(rec_data['recommendation']).lower()}")
        analysis.append(f"2. Most of the factors it looks at are currently favourable")
        analysis.append(f"3. A score below 60 would move it out of the positive band")
        analysis.append(f"4. The score is recalculated from fresh data each time a report is run")
    elif rec_data['recommendation'] == 'HOLD':
        analysis.append(f"1. The model reads the current data as mixed")
        analysis.append(f"2. A score of 60 or more would move it into the positive band")
        analysis.append(f"3. A score below 40 would move it into the negative band")
        analysis.append(f"4. The score is recalculated from fresh data each time a report is run")
    else:
        analysis.append(f"1. The model reads the current data as {signal_label(rec_data['recommendation']).lower()}")
        analysis.append(f"2. Most of the factors it looks at are currently unfavourable")
        analysis.append(f"3. A score of 40 or more would move it out of the negative band")
        analysis.append(f"4. The score is recalculated from fresh data each time a report is run")
    
    # Score Breakdown
    analysis.append(f"\n🔍 SCORE BREAKDOWN ({unified_score}/100):")
    for breakdown in score_breakdown:
        analysis.append(f"• {breakdown}")
    
    # How the points above add up (one explanation: it used to be followed by a second list that did not match)
    points = [int(m.group(1)) for line in score_breakdown for m in [re.search(r': ([+-]\d+)', line)] if m]
    gained = sum(p for p in points if p > 0)
    lost = -sum(p for p in points if p < 0)
    raw_score = 50 + gained - lost
    analysis.append(f"\n🧮 HOW THE SCORE IS BUILT:")
    analysis.append(f"• It starts at 50 (neutral) and the points listed above are added or taken away")
    analysis.append(f"• 50 + {gained} - {lost} = {raw_score}" + (f", held to the 0-100 range: {unified_score}" if raw_score != unified_score else ""))
    if not company_figure_lines(fundamentals):
        analysis.append(f"• A coin has no company figures: this score is from price and volume only" if coin else f"• No company figures were available for this share, so this score is from price and volume only")
    if _report_ctx.get('partial_day'):
        analysis.append(f"• Coins trade around the clock: the price is the latest, and volume is measured on the last full day (UTC)" if coin else f"• Today's session is still open: the price is the latest, and today's part-day volume is left out")

    analysis.append(f"\n📊 SCORE INTERPRETATION:")
    analysis.append(f"• 75-100: Strongly positive signals")
    analysis.append(f"• 60-74: Positive signals")
    analysis.append(f"• 40-59: Mixed signals")
    analysis.append(f"• 25-39: Negative signals")
    analysis.append(f"• 0-24: Strongly negative signals")
    
    analysis.append(f"\n{'='*60}")
    analysis.append(f"📈 DETAILED TECHNICAL ANALYSIS")
    analysis.append(f"{'='*60}")
    
    # Key Technical Indicators
    analysis.append(f"\n🔧 KEY TECHNICAL INDICATORS:")
    analysis.append(f"• Price vs Moving Averages:")
    ma20_pct = ((current - ma20) / ma20 * 100)
    ma50_pct = ((current - ma50) / ma50 * 100)
    analysis.append(f"  - 20-day MA: {money(ma20)} ({'Above' if current > ma20 else 'Below'} {abs(ma20_pct):.1f}%)")
    analysis.append(f"  - 50-day MA: {money(ma50)} ({'Above' if current > ma50 else 'Below'} {abs(ma50_pct):.1f}%)")
    
    if rsi:
        rsi_signal = "Oversold range" if rsi < 30 else "Overbought range" if rsi > 70 else "Neutral range"
        analysis.append(f"• RSI (14): {rsi:.1f} - {rsi_signal}")
    
    if macd_line and signal_line:
        macd_signal = "Bullish" if macd_line > signal_line else "Bearish"
        analysis.append(f"• MACD: {macd_line:.3f} vs Signal: {signal_line:.3f} - {macd_signal}")
    
    if bb_upper and bb_lower:
        bb_position = "Above upper band (Overbought)" if current > bb_upper else "Below lower band (Oversold)" if current < bb_lower else "Within normal range"
        analysis.append(f"• Bollinger Bands: {money(bb_lower)} - {money(bb_upper)} - {bb_position}")
    
    # Support & Resistance
    analysis.append(f"\n🎯 SUPPORT & RESISTANCE:")
    support_pct = ((support - current) / current) * 100
    resistance_pct = ((resistance - current) / current) * 100
    analysis.append(f"• Support: {money(support)} ({abs(support_pct):.1f}% {'below' if support < current else 'above'} current)")
    analysis.append(f"• Resistance: {money(resistance)} ({abs(resistance_pct):.1f}% {'above' if resistance > current else 'below'} current)")
    
    if abs(support_pct) < 5:
        analysis.append(f"  💡 Near support - a level where the price has previously stopped falling")
    if abs(resistance_pct) < 5:
        analysis.append(f"  ⚠️ Near resistance - a level where the price has previously stopped rising")
    
    # Volume Analysis: against the 20-day average, as the score does
    analysis.append(f"\n📊 VOLUME ANALYSIS:")
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
    volume_signal = "High interest" if volume_ratio > 1.5 else "Low interest" if volume_ratio < 0.5 else "Normal interest"
    session_words = "Last full session" if _report_ctx.get('partial_day') else "Latest session"
    analysis.append(f"• {session_words}: {current_volume:,.0f} ({volume_ratio:.1f}x the 20-day average)")
    analysis.append(f"• Volume Signal: {volume_signal}")
    analysis.append(f"• 20-day Average: {avg_volume:,.0f}")

    analysis.append(f"\n{'='*60}")
    analysis.append(f"💰 FUNDAMENTAL ANALYSIS")
    analysis.append(f"{'='*60}")
    
    # Company figures, read with the score's own thresholds
    analysis.append(f"\n🏥 FINANCIAL HEALTH CHECK:")
    figure_lines = company_figure_lines(fundamentals)
    if figure_lines:
        for item in figure_lines:
            analysis.append(f"• {item}")
        if fundamentals.get('figures_source'):
            analysis.append(f"  Company figures from {fundamentals['figures_source']}")
    else:
        analysis.append(f"• Company figures (P/E, growth, margins, debt) were not available for this share")
        analysis.append(f"• The score above is therefore built from price and volume only")

    # Dividend Information
    analysis.append(f"\n💵 DIVIDEND INFORMATION:")
    if fundamentals and fundamentals.get('dividend_yield') and fundamentals.get('dividend_yield') > 0:
        div_yield = fundamentals.get('dividend_yield', 0)
        analysis.append(f"• Current Yield: {div_yield:.2f}%")
        
        if fundamentals.get('latest_dividend'):
            analysis.append(f"• Latest Dividend: {fundamentals['latest_dividend']} (Ex-date: {fundamentals.get('latest_ex_date', 'N/A')})")
        
        if fundamentals.get('annual_dividend'):
            analysis.append(f"• Annual Dividend: {fundamentals['annual_dividend']}")
        
        if fundamentals.get('dividend_frequency'):
            analysis.append(f"• Payment Frequency: {fundamentals['dividend_frequency']}")
        
        div_rating = "Excellent" if div_yield > 4 else "Good" if div_yield > 2 else "Low"
        analysis.append(f"• Dividend Rating: {div_rating} yield")
    else:
        analysis.append(f"• No dividend payments or data unavailable")
        analysis.append(f"• This stock does not currently provide dividend income")
    
    analysis.append(f"\n{'='*60}")
    analysis.append(f"⚠️ RISK ASSESSMENT")
    analysis.append(f"{'='*60}")
    
    # Risk Factors
    analysis.append(f"\n🚨 RISK FACTORS:")
    risk_factors = []
    
    if volatility > 25:
        risk_factors.append(f"❌ High volatility ({volatility:.1f}%) - Price swings have been large")
    elif volatility < 15:
        risk_factors.append(f"✅ Low volatility ({volatility:.1f}%) - Relatively stable")
    else:
        risk_factors.append(f"⚪ Moderate volatility ({volatility:.1f}%) - Normal price movement")
    
    if range_position > 80:
        risk_factors.append(f"⚠️ Near 52-week high ({range_position:.0f}% of its range)")
    elif range_position < 20:
        risk_factors.append(f"✅ Near 52-week low ({range_position:.0f}% of its range)")
    
    if ytd_change < -20:
        risk_factors.append(f"❌ Weak 1-year change ({ytd_change:+.1f}%)")
    elif ytd_change > 30:
        risk_factors.append(f"⚠️ Strong 1-year change ({ytd_change:+.1f}%) - A large rise can be followed by a pullback")
    
    for factor in risk_factors:
        analysis.append(f"• {factor}")
    
    # Reference levels (descriptive)
    analysis.append(f"\n📏 REFERENCE LEVELS:")
    analysis.append(f"• Lower reference level: {money(rec_data['stop_loss'])} (from recent volatility and support)")
    analysis.append(f"• Upper reference level: {money(rec_data['take_profit'])} (from recent volatility and resistance)")
    analysis.append(f"• These levels are calculated automatically. They are not instructions to place orders")
    
    # Target Justification
    if rec_data.get('justification'):
        analysis.append(f"\n💡 HOW THE LEVELS WERE SET:")
        for reason in rec_data['justification']:
            analysis.append(f"• {reason}")
    
    # Scenario Analysis
    if rec_data.get('scenarios'):
        analysis.append(f"\n📊 SCENARIO ANALYSIS:")
        for scenario in rec_data['scenarios']:
            analysis.append(f"• {scenario}")
    
    analysis.append(f"\n{'='*60}")
    analysis.append(f"📋 SIGNAL SUMMARY & KEY LEVELS")
    analysis.append(f"{'='*60}")
    
    # Signal summary (descriptive only)
    analysis.append(f"\n📋 SIGNAL SUMMARY:")
    analysis.append(f"• {signal_label(rec_data['recommendation'])} (score {unified_score}/100)")
    analysis.append(f"• {rec_data['action']}")
    
    # Key Levels
    analysis.append(f"\n🎯 KEY LEVELS:")
    analysis.append(f"• 🔴 Support: {money(support)} (recent lows have clustered around here)")
    analysis.append(f"• 🟢 Resistance: {money(resistance)} (recent highs have clustered around here)")
    analysis.append(f"• 📏 Lower reference level: {money(rec_data['stop_loss'])}")
    analysis.append(f"• 📏 Upper reference level: {money(rec_data['take_profit'])}")
    
    # Market Context
    analysis.append(f"\n🌍 MARKET CONTEXT:")
    if market_sentiment:
        vix_level = market_sentiment.get('vix_level', 'N/A')
        market_fear = market_sentiment.get('market_fear', 'Unknown')
        analysis.append(f"• Market Fear (VIX): {vix_level} - {market_fear} fear environment")
    
    if news_sentiment:
        analysis.append(f"• News Sentiment: {news_sentiment.get('sentiment_signal', 'Unknown')}")
        analysis.append(f"• News Articles: {news_sentiment.get('news_count', 0)} recent articles analyzed")
    
    # Data Sources

    
    analysis.append(f"\n{'='*60}")
    analysis.append(f"📊 DATA SOURCES & METHODOLOGY")
    analysis.append(f"{'='*60}")
    
    data_summary = get_data_source_summary()
    if data_summary and data_summary != "No data sources used":
        analysis.append(f"\n{data_summary}")
    else:
        analysis.append(f"\n⚡ Standard Analysis: Yahoo Finance (100%)")
        analysis.append(f"📊 Data Points: {len(closes)} price periods analyzed")
    
    analysis.append(f"\n📈 Analysis includes:")
    analysis.append(f"• Technical indicators: RSI, MACD, Bollinger Bands, Moving Averages")
    analysis.append(f"• Company figures: P/E, Revenue Growth, Profit Margins, Debt" if company_figure_lines(fundamentals) else f"• Company figures: not available for this share")
    analysis.append(f"• Dividends: yield, latest payment and frequency, where paid")
    analysis.append(f"• Risk assessment: Volatility, Support/Resistance, Volume analysis")
    analysis.append(f"• Market sentiment: News analysis, VIX levels, Momentum indicators")
    
    analysis.append(f"\n⚠️ DISCLAIMER:")
    analysis.append(f"This analysis is automated, general information only. It is not financial advice and not a recommendation to buy or sell.")
    analysis.append(f"It does not take your objectives, financial situation or needs into account. StockIQ is not a licensed financial adviser.")
    analysis.append(f"Consider seeking advice from a licensed professional before making investment decisions.")
    analysis.append(f"Past performance does not guarantee future results.")
    
    analysis.append(f"\n{'='*60}")
    analysis.append(f"📊 END OF ANALYSIS REPORT")
    analysis.append(f"{'='*60}")
    
    if coin:
        # What belongs to a company or to the stock market has no place in a coin's report
        analysis = without_section(analysis, '💰 FUNDAMENTAL ANALYSIS', '⚠️ RISK ASSESSMENT')
        drop = ('🌍 MARKET CONTEXT:', '• Company figures:', '• Dividends:', '• Market sentiment:')
        analysis = [line for line in analysis if not any(word in line for word in drop)]
        analysis = [line.replace('Fundamental metrics', 'Company figures') for line in analysis]
    return "\n".join(analysis)

# What Yahoo said about the symbol of the report being written: its currency ('USD', 'AUD', 'GBp' = pence ...), its
# name, what kind of thing it is ('EQUITY', 'ETF' ...) and whether today's session is still open
_report_ctx = {}

MONEY_SIGNS = {'USD': '$', 'AUD': 'A$', 'CAD': 'C$', 'NZD': 'NZ$', 'HKD': 'HK$', 'SGD': 'S$', 'GBP': '£', 'EUR': '€',
               'JPY': '¥', 'CNY': 'CN¥', 'INR': '₹', 'KRW': '₩'}
MINOR_UNITS = {'GBp': ('p', 'GBP', 'pence'), 'GBX': ('p', 'GBP', 'pence'), 'ZAc': ('c', 'ZAR', 'cents'), 'ZAC': ('c', 'ZAR', 'cents'),
               'ILA': (' agorot', 'ILS', 'agorot')}

def money(value, places=2):
    """A price in the currency the share trades in (until Oct 2026 every share was printed with a dollar sign)"""
    if value is None:
        return 'N/A'
    cur = _report_ctx.get('currency') or ''
    if cur in MINOR_UNITS:
        return f"{value:,.{places}f}{MINOR_UNITS[cur][0]}"
    if cur in MONEY_SIGNS or not cur:
        return f"{MONEY_SIGNS.get(cur, '$')}{value:,.{places}f}"
    return f"{cur} {value:,.{places}f}"

def currency_note(price):
    """One line saying what the prices are in, when it is not US dollars ('' for a US share)"""
    cur = _report_ctx.get('currency') or ''
    if cur in MINOR_UNITS:
        unit, major, word = MINOR_UNITS[cur]
        return f"ℹ️ Prices for this share are in {word}: {money(price)} is {MONEY_SIGNS.get(major, major + ' ')}{price / 100:,.2f}"
    if cur and cur != 'USD':
        return f"ℹ️ Prices for this share are in {cur} ({MONEY_SIGNS.get(cur, cur).strip()})"
    return ''

def bars_from_chart(result, now=None):
    """Daily bars from one Yahoo chart answer, oldest first, one bar per trading day: the same rules as the screener
    workers (workers/stock_worker.py). Returns (bars, facts about the symbol)."""
    timestamps = result.get('timestamp') or []
    quotes = (result.get('indicators') or {}).get('quote') or []
    meta = result.get('meta') or {}
    offset = meta.get('gmtoffset') or 0

    def day(timestamp):
        # The trading day a time belongs to, on the exchange's own clock
        return (int(timestamp) + offset) // 86400

    bars = []
    prices = quotes[0] if quotes else {}
    for i, ts in enumerate(timestamps):
        try:
            close, high, low = prices['close'][i], prices['high'][i], prices['low'][i]
            if close is None or high is None or low is None:
                continue
            bar = {'date': datetime.fromtimestamp(ts), 'timestamp': ts, 'open': prices['open'][i] or close,
                   'high': high, 'low': low, 'close': close, 'volume': prices['volume'][i] or 0}
        except (KeyError, IndexError, TypeError):
            continue
        # Once a market has closed Yahoo can send its last session twice (seen on the ASX): two bars for one day made
        # "today's change" 0.00%. One bar a day, the later one.
        if bars and day(bars[-1]['timestamp']) == day(ts):
            bars[-1] = bar
        else:
            bars.append(bar)

    # The latest session can arrive with empty figures (seen for London shares), which left the price a day old.
    # The quote that comes with the chart has that session: use it as the last bar.
    price = meta.get('regularMarketPrice')
    quoted = meta.get('regularMarketTime')
    if (bars and isinstance(price, (int, float)) and price > 0 and isinstance(quoted, (int, float))
            and day(quoted) > day(bars[-1]['timestamp'])):
        high, low, volume = meta.get('regularMarketDayHigh'), meta.get('regularMarketDayLow'), meta.get('regularMarketVolume')
        bars.append({'date': datetime.fromtimestamp(quoted), 'timestamp': int(quoted), 'open': bars[-1]['close'],
                     'high': max(high, price) if isinstance(high, (int, float)) else price,
                     'low': min(low, price) if isinstance(low, (int, float)) and low > 0 else price,
                     'close': price, 'volume': volume if isinstance(volume, (int, float)) else 0})

    # Is today's session still open? Then the last bar is a part of a day, and its volume is not a day's volume.
    now = time.time() if now is None else now
    session = ((meta.get('currentTradingPeriod') or {}).get('regular') or {})
    partial = bool(bars and isinstance(session.get('start'), (int, float)) and isinstance(session.get('end'), (int, float))
                   and session['start'] <= now < session['end'] and day(bars[-1]['timestamp']) == day(now))
    facts = {'currency': meta.get('currency') or '', 'name': meta.get('longName') or meta.get('shortName') or '',
             'instrument': meta.get('instrumentType') or '', 'partial_day': partial, 'offset': offset}
    return bars, facts

def fetch_stock_data(symbol):
    """Fetch a year of daily prices from Yahoo Finance"""
    try:
        print(f"⚡ Yahoo Finance: Basic price data for {symbol}")
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=365)).timestamp())

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {'period1': start_time, 'period2': end_time, 'interval': '1d'}
        full_url = f"{url}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(full_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        # Track Yahoo Finance call
        track_data_source('yahoo', 'call', success=True)

        if not data or 'chart' not in data or not data['chart']['result']:
            print(f"No chart data for {symbol}")
            return None

        result = data['chart']['result'][0]
        if 'error' in result and result['error']:
            print(f"Yahoo Finance error for {symbol}: {result['error']}")
            return None

        stock_data, facts = bars_from_chart(result)
        if not stock_data:
            print(f"No price data for {symbol}")
            return None
        _report_ctx.clear()
        _report_ctx.update(facts)

        # Track data points
        track_data_source('yahoo', 'data', len(stock_data))
        print(f"Successfully fetched {len(stock_data)} data points for {symbol}")
        return stock_data

    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return None

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

def calculate_stochastic(highs, lows, closes, k_period=14, d_period=3):
    """Calculate Stochastic Oscillator"""
    if len(closes) < k_period:
        return None, None
    
    recent_highs = highs[-k_period:]
    recent_lows = lows[-k_period:]
    current_close = closes[-1]
    
    highest_high = max(recent_highs)
    lowest_low = min(recent_lows)
    
    if highest_high == lowest_low:
        k_percent = 50
    else:
        k_percent = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
    
    # Simplified D% calculation
    d_percent = k_percent
    
    return k_percent, d_percent

def calculate_williams_r(highs, lows, closes, period=14):
    """Calculate Williams %R"""
    if len(closes) < period:
        return None
    
    recent_highs = highs[-period:]
    recent_lows = lows[-period:]
    current_close = closes[-1]
    
    highest_high = max(recent_highs)
    lowest_low = min(recent_lows)
    
    if highest_high == lowest_low:
        return -50
    
    williams_r = ((highest_high - current_close) / (highest_high - lowest_low)) * -100
    return williams_r

def calculate_money_flow_index(highs, lows, closes, volumes, period=14):
    """Calculate Money Flow Index (MFI)"""
    if len(closes) < period + 1:
        return None
    
    typical_prices = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
    money_flows = []
    
    for i in range(1, len(typical_prices)):
        if typical_prices[i] > typical_prices[i-1]:
            money_flows.append(typical_prices[i] * volumes[i])
        elif typical_prices[i] < typical_prices[i-1]:
            money_flows.append(-(typical_prices[i] * volumes[i]))
        else:
            money_flows.append(0)
    
    if len(money_flows) < period:
        return None
    
    recent_flows = money_flows[-period:]
    positive_flow = sum(flow for flow in recent_flows if flow > 0)
    negative_flow = abs(sum(flow for flow in recent_flows if flow < 0))
    
    if negative_flow == 0:
        return 100
    
    money_ratio = positive_flow / negative_flow
    mfi = 100 - (100 / (1 + money_ratio))
    return mfi

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

def fetch_enhanced_fundamentals(symbol):
    """Enhanced fundamental analysis with comprehensive dividend extraction"""
    cache_key = f"fundamentals_{symbol}"
    if cache_key in _api_cache:
        return _api_cache[cache_key]
    
    fundamentals = {}
    finnhub_success = False
    
    # Try Finnhub first for US stocks
    if USE_FINNHUB and not '.AX' in symbol:
        try:
            # Fetch basic metrics
            basic_metrics = fetch_finnhub_data('stock/metric', {'symbol': symbol}, 'basic metrics')
            if basic_metrics and 'metric' in basic_metrics:
                metrics = basic_metrics['metric']
                fundamentals.update({
                    'pe_ratio': metrics.get('peBasicExclExtraTTM'),
                    'beta': metrics.get('beta'),
                    'market_cap': metrics.get('marketCapitalization'),
                    'dividend_yield': metrics.get('dividendYieldIndicatedAnnual'),
                    'revenue_growth': metrics.get('revenueGrowthTTMYoy'),
                    'profit_margin': metrics.get('netProfitMarginTTM'),
                    'debt_to_equity': metrics.get('totalDebt2TotalEquityQuarterly'),
                    'return_on_equity': metrics.get('roeTTM'),
                    'current_ratio': metrics.get('currentRatioQuarterly'),
                    'price_to_book': metrics.get('pbQuarterly'),
                    'price_to_sales': metrics.get('psQuarterly'),
                    'earnings_growth': metrics.get('epsGrowthTTMYoy')
                })
                finnhub_success = True
                print(f"✅ Finnhub enhanced fundamentals for {symbol}")
        except Exception as e:
            print(f"Finnhub fundamentals failed for {symbol}: {str(e)[:50]}")
    
    # Use comprehensive dividend extraction from chart endpoint (more reliable)
    try:
        print(f"⚡ Yahoo dividend data for {symbol}")
        
        # Get dividend data from chart endpoint with events (extended period for better analysis)
        div_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        div_params = {
            'period1': int((datetime.now() - timedelta(days=1095)).timestamp()),  # 3 years for better analysis
            'period2': int(datetime.now().timestamp()),
            'interval': '1d',
            'events': 'div'
        }
        div_param_str = urllib.parse.urlencode(div_params)
        div_full_url = f"{div_url}?{div_param_str}"
        
        req = urllib.request.Request(div_full_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            div_data = json.loads(response.read())
        
        # Track Yahoo Finance call
        track_data_source('yahoo', 'call', success=True)
        
        # Extract comprehensive dividend information
        if div_data and 'chart' in div_data and div_data['chart']['result']:
            chart_result = div_data['chart']['result'][0]
            current_price = chart_result['meta']['regularMarketPrice']
            
            # Check for dividend events
            if 'events' in chart_result and 'dividends' in chart_result['events']:
                dividends = chart_result['events']['dividends']
                
                if dividends:
                    # Sort dividends by date (most recent first)
                    div_list = [(int(k), v) for k, v in dividends.items()]
                    div_list.sort(key=lambda x: x[0], reverse=True)
                    
                    # Most recent dividend
                    latest_timestamp, latest_div = div_list[0]
                    latest_date = datetime.fromtimestamp(latest_timestamp)
                    latest_amount = latest_div['amount']
                    
                    # Store detailed dividend information
                    fundamentals['latest_dividend'] = money(latest_amount, 3)
                    fundamentals['latest_ex_date'] = latest_date.strftime('%Y-%m-%d')
                    
                    # Calculate annual dividend from last 12 months
                    one_year_ago = datetime.now() - timedelta(days=365)
                    recent_divs = [div for div in div_list if datetime.fromtimestamp(div[0]) > one_year_ago]
                    
                    if recent_divs:
                        annual_dividend = sum([div[1]['amount'] for div in recent_divs])
                        fundamentals['annual_dividend'] = money(annual_dividend, 3)
                        
                        # Calculate dividend yield
                        if current_price and current_price > 0:
                            dividend_yield = (annual_dividend / current_price) * 100
                            fundamentals['dividend_yield'] = dividend_yield
                            print(f"📊 Calculated dividend yield: {dividend_yield:.2f}% for {symbol}")
                            print(f"   Annual dividend: ${annual_dividend:.3f}, Price: {money(current_price)}")
                    
                    # Determine dividend frequency
                    if len(div_list) >= 2:
                        days_between = (div_list[0][0] - div_list[1][0]) / 86400
                        if 80 <= days_between <= 100:
                            fundamentals['dividend_frequency'] = "Quarterly"
                        elif 160 <= days_between <= 200:
                            fundamentals['dividend_frequency'] = "Semi-Annual"
                        elif 350 <= days_between <= 380:
                            fundamentals['dividend_frequency'] = "Annual"
                        elif 25 <= days_between <= 35:
                            fundamentals['dividend_frequency'] = "Monthly"
                        else:
                            fundamentals['dividend_frequency'] = "Irregular"
                    
                    # Dividend growth analysis (year-over-year)
                    if len(div_list) >= 8:
                        current_year = datetime.now().year
                        current_year_divs = [div for div in div_list if datetime.fromtimestamp(div[0]).year == current_year]
                        last_year_divs = [div for div in div_list if datetime.fromtimestamp(div[0]).year == current_year - 1]
                        
                        if current_year_divs and last_year_divs:
                            current_total = sum([div[1]['amount'] for div in current_year_divs])
                            last_total = sum([div[1]['amount'] for div in last_year_divs])
                            
                            if last_total > 0:
                                growth_rate = ((current_total - last_total) / last_total) * 100
                                fundamentals['dividend_growth_yoy'] = f"{growth_rate:+.1f}%"
                    
                    # Next expected dividend date
                    if len(div_list) >= 2:
                        days_between = (div_list[0][0] - div_list[1][0]) / 86400
                        next_ex_date = datetime.fromtimestamp(latest_timestamp) + timedelta(days=days_between)
                        
                        if next_ex_date > datetime.now():
                            fundamentals['next_ex_date'] = next_ex_date.strftime('%Y-%m-%d')
                    
                    # Dividend stability analysis
                    if len(div_list) >= 4:
                        recent_amounts = [div[1]['amount'] for div in div_list[:4]]
                        # Check if dividends are consistent (within 10% variation)
                        if all(abs(amt - recent_amounts[0]) / recent_amounts[0] < 0.1 for amt in recent_amounts):
                            fundamentals['dividend_stability'] = "✅ Consistent payments"
                        else:
                            fundamentals['dividend_stability'] = "⚠️ Variable payments"
                    
                    # Payout ratio calculation (if EPS data available)
                    if fundamentals.get('eps_ttm') and annual_dividend:
                        eps_ttm = fundamentals['eps_ttm']
                        if eps_ttm > 0:
                            payout_ratio = (annual_dividend / eps_ttm) * 100
                            fundamentals['dividend_payout_ratio'] = payout_ratio
                    
                    print(f"✅ Comprehensive dividend data extracted for {symbol}")
                else:
                    print(f"⚠️ No dividend events found for {symbol}")
                    fundamentals['dividend_yield'] = 0
                    fundamentals['dividend_stability'] = "⚠️ No dividend payments"
            else:
                print(f"⚠️ No dividend data in chart events for {symbol}")
                fundamentals['dividend_yield'] = 0
                fundamentals['dividend_stability'] = "⚠️ No dividend data available"
        else:
            print(f"⚠️ No chart data returned for {symbol}")
        
        _api_cache[cache_key] = fundamentals
        
        if '.AX' in symbol:
            print(f"🇦🇺 Using Yahoo Finance dividend data for ASX stock {symbol}")
        elif finnhub_success:
            print(f"🔥 Hybrid data: Finnhub + Yahoo Finance for {symbol}")
        else:
            print(f"⚡ Yahoo Finance dividend data for {symbol}")
        
        return fundamentals
        
    except Exception as e:
        print(f"Enhanced fundamentals fetch failed for {symbol}: {str(e)[:50]}")
        return fundamentals if fundamentals else {}

# Coins: the ticker the price source knows each one by, where the plain symbol is a different coin (SUI is SUI20947-USD).
# The crypto screener's own list (COINS in stockiq-option-7-1-orchestrator; the page's CRYPTO_TICKER_MAP is the same):
# keep the three in step (check-tools/report/report_test.py compares this one with the orchestrator's).
COIN_TICKERS = {
    'ACE': 'ACE28674', 'ACU': 'ACU36492', 'ACX': 'ACX22620', 'AERO': 'AERO29270', 'AI': 'AI40925', 'AIC': 'AIC32968',
    'ALT': 'ALT29073', 'APEPE': 'APEPE27048', 'APT': 'APT21794', 'ARB': 'ARB11841', 'ARC': 'ARC34926',
    'ARX': 'ARX39970', 'AT': 'AT38757', 'ATH': 'ATH30083', 'AXL': 'AXL17799', 'BABY': 'BABY32198', 'BAN': 'BAN33881',
    'BANK': 'BANK36296', 'BC': 'BC35067', 'BEAT': 'BEAT38837', 'BFC': 'BFC7817', 'BILL': 'BILL39545',
    'BIO': 'BIO34812', 'BNKR': 'BNKR37545', 'BP': 'BP39686', 'BR': 'BR36063', 'BRETT': 'BRETT29743',
    'BROCCOLI': 'BROCCOLI35749', 'BSB': 'BSB38889', 'BTW': 'BTW39158', 'BUCK': 'BUCK31225', 'BULLA': 'BULLA36769',
    'BURN': 'BURN30460', 'CARDS': 'CARDS38283', 'CC': 'CC37263', 'COAI': 'COAI38489', 'COW': 'COW19269',
    'CX': 'CX35735', 'CYS': 'CYS39071', 'DATA': 'DATA35626', 'DBR': 'DBR31528', 'DEEP': 'DEEP33391',
    'DIME': 'DIME39656', 'DOG': 'DOG30933', 'DRV': 'DRV35014', 'EDEL': 'EDEL38966', 'EDEN': 'EDEN38513',
    'EDGE': 'EDGE39720', 'EDU': 'EDU24613', 'ESP': 'ESP39548', 'EV': 'EV39394', 'FB': 'FB32941', 'FF': 'FF38482',
    'FT': 'FT38544', 'GAL': 'GAL11877', 'GIGGLE': 'GIGGLE38470', 'GPT': 'GPT36614', 'GRASS': 'GRASS32956',
    'GRT': 'GRT6719', 'HASH': 'HASH19960', 'HOLO': 'HOLO38309', 'HYPE': 'HYPE32196', 'HYPER': 'HYPER36281',
    'ID': 'ID21846', 'IMX': 'IMX10603', 'IO': 'IO29835', 'JPYC': 'JPYC40123', 'KAU': 'KAU24382', 'LION': 'LION35954',
    'LIT': 'LIT39125', 'MASK': 'MASK8536', 'ME': 'ME32197', 'MEGA': 'MEGA38770', 'MELANIA': 'MELANIA35347',
    'MET': 'MET38353', 'META': 'META38146', 'METAL': 'METAL21769', 'MEW': 'MEW30126', 'MOCA': 'MOCA31526',
    'MOODENG': 'MOODENG33093', 'MOOLAH': 'MOOLAH36818', 'MORPHO': 'MORPHO34104', 'NEIRO': 'NEIRO32521',
    'NIL': 'NIL35702', 'NPC': 'NPC27960', 'OMI': 'OMI19075', 'ONG': 'ONG3217', 'OPEN': 'OPEN37456', 'PC': 'PC36834',
    'PENGU': 'PENGU34466', 'PEPE': 'PEPE24478', 'PUMP': 'PUMP36507', 'RAVE': 'RAVE38967', 'RED': 'RED21707',
    'SBC': 'SBC26456', 'SENT': 'SENT38868', 'SHARE': 'SHARE39955', 'SKR': 'SKR39377', 'SNEK': 'SNEK25264',
    'SPACE': 'SPACE38136', 'SPX': 'SPX28081', 'STX': 'STX4847', 'SUI': 'SUI20947', 'SUPER': 'SUPER8290',
    'SYN': 'SYN12147', 'TAG': 'TAG34958', 'TAKE': 'TAKE38175', 'TAO': 'TAO22974', 'TIG': 'TIG34102',
    'TRUMP': 'TRUMP35336', 'TRUTH': 'TRUTH38178', 'UAI': 'UAI38841', 'UB': 'UB38339', 'UNI': 'UNI7083',
    'UP': 'UP39665', 'USELESS': 'USELESS36828', 'VVV': 'VVV35509', 'WAL': 'WAL36119', 'WLFI': 'WLFI33251',
    'XCN': 'XCN18679', 'XP': 'XP36056', 'ZBT': 'ZBT38427', 'ZK': 'ZK24091', 'ZORA': 'ZORA35931', 'ZRO': 'ZRO26997',
}
# Symbols the price source is known to list a different coin under (checked against CoinGecko, 9 Oct 2026)
COIN_WRONG_MATCH = {
    'ACT', 'ALPHA', 'BEAM', 'CAT', 'CORE', 'CYBER', 'FLM', 'FRONT', 'G', 'GFI', 'GOAT', 'KMD', 'LOOM', 'MBOX', 'MNT',
    'ONE', 'ORN', 'PYR', 'QUICK', 'RFOX', 'SCR', 'SOLO', 'SXP', 'TON', 'TRIAS', 'TRU', 'ZCX',
}

def coin_ticker(symbol):
    """(the symbol shown, the price source's ticker) for a coin named by its symbol: 'sui' -> ('SUI', 'SUI20947-USD')"""
    label = str(symbol).upper().strip()
    if label.endswith('-USD'):
        label = label[:-4]
    return label, COIN_TICKERS.get(label, label) + '-USD'

def without_section(lines, starts, ends):
    """The report's lines without the section whose heading holds `starts`, up to the heading that holds `ends`
    (each heading is preceded by a line of ====, which goes or stays with it)"""
    first = next((i for i, line in enumerate(lines) if starts in line), None)
    last = next((i for i, line in enumerate(lines) if ends in line), None)
    if first is None or last is None or last <= first:
        return lines
    return lines[:first - 1] + lines[last - 1:]

FIGURE_KEYS = ('pe_ratio', 'revenue_growth', 'profit_margin', 'debt_to_equity', 'current_ratio', 'return_on_equity', 'price_to_book')
COMPANY_FIGURES_BUCKET = 'stockiq-dynamic-stock-lists'
COMPANY_FIGURES_KEY = 'site-data/company_figures.json'
_site_figures = {'at': 0, 'figures': None}

def site_company_figures(symbol):
    """Company figures for a share from the file the site's daily job publishes (publish_company_figures.py): Yahoo's
    figures for every stock on the site, already in the units the score uses, with the day they were read ('as_of').
    {} when the share is not on the site or the file cannot be read: the report then says so and scores on price and
    volume alone. (Yahoo's own summary cannot be read from here: it answers "too many requests" to anything that is
    not a browser. Tried and taken out again on 11 Oct 2026.)"""
    try:
        if _site_figures['figures'] is None or time.time() - _site_figures['at'] > 6 * 3600:
            client = s3_client or boto3.client('s3')
            body = client.get_object(Bucket=COMPANY_FIGURES_BUCKET, Key=COMPANY_FIGURES_KEY)['Body'].read()
            _site_figures.update(figures=json.loads(body).get('figures') or {}, at=time.time())
        entry = _site_figures['figures'].get(symbol.upper()) or {}
    except Exception as e:
        print(f"Company figures file not read for {symbol}: {str(e)[:80]}")
        return {}
    return {k: v for k, v in entry.items() if k == 'as_of' or (isinstance(v, (int, float)) and not isinstance(v, bool))}

def fill_missing_figures(symbol, fundamentals):
    """Fill the company figures the first source did not have, for shares only (a fund has no profit margin), and note
    where the figures came from ('figures_source'; None when there are none at all)"""
    if 'figures_source' in fundamentals:          # kept from an earlier report by this container: already filled
        return fundamentals
    had = [k for k in FIGURE_KEYS if fundamentals.get(k) is not None]
    added, as_of = [], ''
    if len(had) < len(FIGURE_KEYS) and (_report_ctx.get('instrument') or 'EQUITY') == 'EQUITY':
        extra = site_company_figures(symbol)
        added = [k for k in FIGURE_KEYS if fundamentals.get(k) is None and extra.get(k) is not None]
        for k in added:
            fundamentals[k] = extra[k]
        try:
            day = datetime.strptime(str(extra.get('as_of')), '%Y-%m-%d')
            as_of = f" (as of {day.day} {day.strftime('%b %Y')})"
        except ValueError:
            as_of = ''
    second = f"Yahoo Finance{as_of}"
    fundamentals['figures_source'] = (f"Finnhub and {second}" if had and added else second if added
                                      else 'Finnhub' if had else None)
    return fundamentals

def company_figure_lines(fundamentals):
    """One line per company figure with the reading the score gives it: the same thresholds as
    calculate_unified_investment_score, so the two can never disagree (they did: "Weak" above, "Adequate" below)"""
    f = fundamentals or {}
    lines = []

    def add(value, label, text, bands):
        for test, mark, words in bands:
            if test(value):
                lines.append(f"{mark} {label}: {text} ({words})")
                return

    always = lambda value: True
    v = f.get('pe_ratio')
    if v:
        add(v, 'P/E Ratio', f"{v:.1f}", [(lambda x: x < 15, '✅', 'Low valuation'), (lambda x: x > 30, '❌', 'High valuation'), (always, '⚪', 'Mid-range')])
    v = f.get('revenue_growth')
    if v is not None:
        add(v, 'Revenue Growth', f"{v:.1f}%", [(lambda x: x > 15, '✅', 'Strong'), (lambda x: x < -10, '❌', 'Declining'), (always, '⚪', 'Moderate')])
    v = f.get('profit_margin')
    if v is not None:
        add(v, 'Profit Margin', f"{v:.1f}%", [(lambda x: x > 20, '✅', 'Excellent'), (lambda x: x > 10, '✅', 'Good'), (lambda x: x < 0, '❌', 'Unprofitable'),
                                               (lambda x: x < 5, '❌', 'Weak'), (always, '⚪', 'Adequate')])
    v = f.get('debt_to_equity')
    if v is not None:
        add(v, 'Debt/Equity', f"{v:.2f}", [(lambda x: x < 0.3, '✅', 'Low debt'), (lambda x: x > 2.0, '❌', 'High debt'), (lambda x: x > 1.5, '❌', 'Elevated debt'),
                                            (always, '⚪', 'Moderate')])
    v = f.get('current_ratio')
    if v is not None:
        add(v, 'Current Ratio', f"{v:.2f}", [(lambda x: x > 2.0, '✅', 'Strong liquidity'), (lambda x: x < 1.0, '❌', 'Low liquidity'), (lambda x: x < 1.5, '❌', 'Weak liquidity'),
                                              (always, '⚪', 'Adequate')])
    v = f.get('return_on_equity')
    if v is not None:
        add(v, 'ROE', f"{v:.1f}%", [(lambda x: x > 20, '✅', 'Excellent returns'), (lambda x: x > 15, '✅', 'Strong returns'), (lambda x: x < 0, '❌', 'Negative return'),
                                     (lambda x: x < 5, '❌', 'Weak returns'), (always, '⚪', 'Moderate returns')])
    v = f.get('price_to_book')
    if v is not None:
        add(v, 'Price/Book', f"{v:.2f}", [(lambda x: x < 1.0, '✅', 'Low valuation'), (lambda x: x > 5.0, '❌', 'High valuation'), (always, '⚪', 'Mid-range')])
    return lines

def calculate_fundamental_score_enhanced(fundamentals):
    """Enhanced fundamental analysis with Finnhub integration"""
    if not fundamentals:
        return 5, "Insufficient data"
    
    score = 5
    analysis_type = "Basic analysis"
    
    # Basic scoring from Yahoo Finance
    pe_ratio = fundamentals.get('pe_ratio')
    if pe_ratio:
        if pe_ratio < 15:
            score += 2
        elif pe_ratio > 25:
            score -= 2
    
    revenue_growth = fundamentals.get('revenue_growth')
    if revenue_growth is not None and revenue_growth > 10:
        score += 1
    elif revenue_growth is not None and revenue_growth < -10:
        score -= 1

    
    profit_margin = fundamentals.get('profit_margin')
    if profit_margin is not None and profit_margin > 15:
        score += 1
    elif profit_margin is not None and profit_margin < 5:
        score -= 1

    
    # Enhanced scoring with Finnhub data
    finnhub_metrics = 0
    
    # Price-to-Book ratio (Finnhub)
    pb_ratio = fundamentals.get('price_to_book')
    if pb_ratio:
        finnhub_metrics += 1
        if pb_ratio < 1.5:
            score += 1  # Undervalued
        elif pb_ratio > 3:
            score -= 1  # Overvalued
    
    # Quick ratio (Finnhub)
    quick_ratio = fundamentals.get('quick_ratio')
    if quick_ratio:
        finnhub_metrics += 1
        if quick_ratio > 1.5:
            score += 1  # Strong liquidity
        elif quick_ratio < 0.8:
            score -= 1  # Liquidity risk
    
    # Operating margin (Finnhub)
    op_margin = fundamentals.get('operating_margin')
    if op_margin:
        finnhub_metrics += 1
        if op_margin > 20:
            score += 1  # Efficient operations
        elif op_margin < 5:
            score -= 1  # Poor efficiency
    
    # Interest coverage (Finnhub)
    int_coverage = fundamentals.get('interest_coverage')
    if int_coverage:
        finnhub_metrics += 1
        if int_coverage > 5:
            score += 1  # Safe debt levels
        elif int_coverage < 2:
            score -= 2  # Debt risk
    
    if finnhub_metrics > 0:
        analysis_type = f"Finnhub enhanced ({finnhub_metrics} advanced metrics)"
    
    return max(0, min(10, score)), analysis_type

def calculate_technical_score_enhanced(closes, highs, lows, volumes, rsi, macd_line, signal_line, bb_upper, bb_lower, stoch_k, williams_r, mfi):
    """Enhanced technical score calculation"""
    score = 5
    
    # RSI analysis
    if rsi:
        if rsi < 30:
            score += 2
        elif rsi > 70:
            score -= 2
    
    # MACD analysis
    if macd_line and signal_line:
        if macd_line > signal_line:
            score += 1
        else:
            score -= 1
    
    # Bollinger Bands
    current = closes[-1]
    if bb_upper and bb_lower:
        if current < bb_lower:
            score += 2
        elif current > bb_upper:
            score -= 2
    
    # Moving averages
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current
    ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current
    
    if current > ma20 > ma50:
        score += 2
    elif current < ma20 < ma50:
        score -= 2
    
    return max(0, min(10, score))

def analyze_long_term_trends_enhanced(closes, volumes):
    """Enhanced long-term trend analysis"""
    return {}

def calculate_risk_metrics_enhanced(closes, volumes):
    """Enhanced risk assessment"""
    if len(closes) < 50:
        return {}
    
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    volatility = (sum(r**2 for r in returns) / len(returns))**0.5 * 100
    
    # Drawdown analysis
    peak = closes[0]
    max_drawdown = 0
    for price in closes:
        if price > peak:
            peak = price
        else:
            drawdown = (peak - price) / peak
        max_drawdown = max(max_drawdown, drawdown)
    
    return {
        'volatility': volatility,
        'max_drawdown': max_drawdown * 100,
        'risk_level': 'High' if volatility > 25 else 'Moderate' if volatility > 15 else 'Low'
    }

def detect_company_distress_signals(symbol, fundamentals, closes, volumes):
    """Detect bankruptcy and distress signals"""
    return [], 0

def detect_chart_patterns_enhanced(highs, lows, closes):
    """Enhanced chart pattern recognition"""
    patterns = []
    
    if len(closes) < 20:
        return patterns
    
    recent_closes = closes[-20:]
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]
    
    # Double top pattern
    if len(recent_highs) >= 10:
        max_high = max(recent_highs)
        high_indices = [i for i, h in enumerate(recent_highs) if h >= max_high * 0.98]
        if len(high_indices) >= 2 and high_indices[-1] - high_indices[0] >= 5:
            patterns.append("DOUBLE TOP - Bearish reversal")
    
    # Double bottom pattern
    if len(recent_lows) >= 10:
        min_low = min(recent_lows)
        low_indices = [i for i, l in enumerate(recent_lows) if l <= min_low * 1.02]
        if len(low_indices) >= 2 and low_indices[-1] - low_indices[0] >= 5:
            patterns.append("DOUBLE BOTTOM - Bullish reversal")
    
    return patterns

def fetch_market_sentiment():
    """Fetch VIX and market sentiment"""
    try:
        vix_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX"
        req = urllib.request.Request(vix_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        
        if data and 'chart' in data and data['chart']['result']:
            result = data['chart']['result'][0]
            vix_price = result['meta']['regularMarketPrice']
            
            return {
                'vix_level': vix_price,
                'market_fear': 'High' if vix_price > 25 else 'Low'
            }
    except:
        pass
    
    return {'vix_level': 'N/A', 'market_fear': 'Unknown'}

def zone_label(timezone_offset):
    """The visitor's time zone as the site writes it: GMT+7, GMT-4, GMT+5:30. With no offset sent, the zone the
    report's own time falls back to (get_user_timezone_timestamp: five hours behind UTC)."""
    try:
        offset = float(timezone_offset) if timezone_offset is not None else -5.0
    except (TypeError, ValueError):
        offset = -5.0
    hours = int(abs(offset))
    minutes = int(round((abs(offset) - hours) * 60))
    return f"GMT{'+' if offset >= 0 else '-'}{hours}" + (f":{minutes:02d}" if minutes else '')

def local_news_date(recent_news, timezone_offset):
    """The article's time in the visitor's own time zone, written as the stock pages write it for him
    (js/timezone-converter.js): "Thu, October 8, 2026 at 8:31 PM GMT+7 4 min read". The report used to print the page's
    own text, which is UTC. Left as the page has it when the visitor's offset or the article's time is not known."""
    original = recent_news.get('date') or ''
    try:
        if timezone_offset is None or not recent_news.get('timestamp'):
            return original
        offset = float(timezone_offset)
        if not -14 <= offset <= 14:
            return original
        from datetime import timezone
        when = datetime.fromisoformat(str(recent_news['timestamp']).replace('Z', '+00:00'))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        local = when.astimezone(timezone(timedelta(hours=offset)))
        clock = f"{local.hour % 12 or 12}:{local.minute:02d} {'AM' if local.hour < 12 else 'PM'}"
        text = f"{local.strftime('%a')}, {local.strftime('%B')} {local.day}, {local.year} at {clock} {zone_label(offset)}"
        read_time = re.search(r'\d+ min read', original)
        return text + (' ' + read_time.group(0) if read_time else '')
    except Exception:
        return original

def fetch_recent_news_from_stock_page(symbol):
    """Fetch recent news from stock page HTML (zero cost, reuses existing news)"""
    try:
        url = f"https://stockiq.tech/stocks/{symbol}.html"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
        
        # Extract news between markers
        import re
        match = re.search(r'<!-- NEWS_SECTION_START -->(.*?)<!-- NEWS_SECTION_END -->', html, re.DOTALL)
        
        if not match or not match.group(1).strip():
            return None
        
        news_html = match.group(1).strip()
        
        # Parse headline, date, and full summary
        headline_match = re.search(r'<strong>(.*?)</strong>', news_html)
        date_match = re.search(r'data-timestamp="[^"]+"[^>]*>([^<]+)</p>', news_html)
        stamp_match = re.search(r'data-timestamp="([^"]+)"', news_html)
        # Extract full summary (the longer paragraph after the date)
        summary_match = re.search(r'data-timestamp[^>]+>.*?</p>\s*<p[^>]*>([^<]+)</p>', news_html, re.DOTALL)
        url_match = re.search(r'href="([^"]+)"', news_html)
        
        if headline_match and summary_match:
            return {
                'headline': headline_match.group(1).strip(),
                'date': date_match.group(1).strip() if date_match else '',
                'timestamp': stamp_match.group(1) if stamp_match else None,
                'summary': summary_match.group(1).strip(),
                'url': url_match.group(1) if url_match else None,
                'has_news': True
            }
        
        return None
        
    except Exception as e:
        print(f"Could not fetch news from stock page for {symbol}: {str(e)[:50]}")
        return None

def fetch_news_sentiment_enhanced(symbol):
    """Enhanced news sentiment analysis - checks if stock page has news"""
    try:
        # Check if stock page has news (more accurate than Yahoo search)
        recent_news = fetch_recent_news_from_stock_page(symbol)
        
        if recent_news and recent_news.get('has_news'):
            # Stock has recent news on its page
            return {
                'sentiment_score': 0.1,
                'sentiment_signal': 'POSITIVE news activity',
                'news_count': 1  # We have 1 article on the stock page
            }
        else:
            # No news on stock page
            return {
                'sentiment_score': 0,
                'sentiment_signal': 'No recent news',
                'news_count': 0
            }
        
    except:
        return {
            'sentiment_score': 0,
            'sentiment_signal': 'News analysis unavailable',
            'news_count': 0
        }

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
        if rsi < 30:
            score += 15
            score_breakdown.append("RSI Oversold: +15 (Oversold reading)")
        elif rsi > 70:
            score -= 15
            score_breakdown.append("RSI Overbought: -15 (Caution signal)")
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
    # Momentum with overextension penalties
    if ytd_change > 100:
        score -= 15
        score_breakdown.append(f"Extreme Overextension ({ytd_change:+.1f}% over 1 year): -15 (High pullback risk)")
    elif ytd_change > 50:
        score -= 8
        score_breakdown.append(f"Overextended ({ytd_change:+.1f}% over 1 year): -8 (Caution - mean reversion likely)")
    elif ytd_change > 30:
        score += 3
        score_breakdown.append(f"Strong Momentum ({ytd_change:+.1f}% over 1 year): +3 (Good but stretched)")
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
    
    # Range Position - Overextension Check (±5 points)
    if range_position > 95:
        score -= 5
        score_breakdown.append(f"Near 52-Week High ({range_position:.0f}%): -5 (High in its range)")
    elif range_position < 5:
        score += 5
        score_breakdown.append(f"Near 52-Week Low ({range_position:.0f}%): +5 (Low in its range)")
    
    final_score = max(0, min(100, score))
    return final_score, score_breakdown

# Display wording for the internal recommendation codes. The codes themselves
# (STRONG BUY ... STRONG SELL) are still used for logic, but are never shown:
# StockIQ gives general information, not advice. Same labels as the public stock pages.
SIGNAL_LABELS = {
    'STRONG BUY': 'Strongly positive signals',
    'BUY': 'Positive signals',
    'HOLD': 'Mixed signals',
    'SELL': 'Negative signals',
    'STRONG SELL': 'Strongly negative signals',
}

def signal_label(recommendation):
    return SIGNAL_LABELS.get(recommendation, 'Mixed signals')

def get_clear_recommendation_and_action(score, current_price, support, resistance, fundamentals=None, rsi=None, bb_upper=None, ytd_change=None, range_position=None, closes=None):
    """Convert score to clear recommendation with specific actions and scenario analysis"""
    
    # Calculate moving averages for trend confirmation
    ma50 = sum(closes[-50:]) / 50 if closes and len(closes) >= 50 else current_price
    ma200 = sum(closes[-200:]) / 200 if closes and len(closes) >= 200 else current_price
    
    # Trend confirmation flags
    above_ma50 = current_price > ma50
    above_ma200 = current_price > ma200
    strong_uptrend = above_ma50 and above_ma200
    strong_downtrend = current_price < ma50 and current_price < ma200
    
    # Base recommendation on score
    if score >= 75:
        if strong_uptrend:
            recommendation = "STRONG BUY"
            action = "Score is in the top band and the price is above both its 50-day and 200-day averages"
            confidence = "High"
        else:
            recommendation = "BUY"
            action = "Score is in the top band, but the price is not above both its 50-day and 200-day averages"
            confidence = "Medium"
        position_size = "Not provided (general information only)"
        urgency = "Not provided (general information only)"
    elif score >= 60:
        if strong_uptrend:
            recommendation = "BUY"
            action = "Score is above average and the price is above both its 50-day and 200-day averages"
            confidence = "Medium-High"
            urgency = "Not provided (general information only)"
        elif above_ma50:
            recommendation = "BUY"
            action = "Score is above average and the price is above its 50-day average"
            confidence = "Medium"
            urgency = "Not provided (general information only)"
        else:
            recommendation = "HOLD"
            action = "Score is above average, but the price is below its 50-day average"
            confidence = "Medium"
            urgency = "Not provided (general information only)"
        position_size = "Not provided (general information only)"
    elif score >= 40:
        recommendation = "HOLD"
        action = "Score is in the middle of the range, with no clear lean either way"
        confidence = "Medium"
        position_size = "Not provided (general information only)"
        urgency = "Not provided (general information only)"
    elif score >= 25:
        recommendation = "SELL"
        action = "Score is below average"
        confidence = "Medium-High"
        position_size = "Not provided (general information only)"
        urgency = "Not provided (general information only)"
    else:
        recommendation = "STRONG SELL"
        action = "Score is in the lowest band"
        confidence = "High"
        position_size = "Not provided (general information only)"
        urgency = "Not provided (general information only)"
    
    # Smart take-profit based on volatility
    beta = fundamentals.get('beta', 1.0) if fundamentals else 1.0
    
    # Calculate volatility from 60 days
    volatility = 20.0
    if closes and len(closes) >= 60:
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, min(61, len(closes)))]
        variance = sum(r**2 for r in returns) / len(returns)
        volatility = (variance**0.5) * 100 * (252**0.5)
    
    # Base target = volatility / 2 (realistic: half the volatility)
    base_target = (volatility / 2) / 100
    
    # Multiply by factors
    if ytd_change and ytd_change > 30:
        base_target *= 1.2
    elif ytd_change and ytd_change < -20:
        base_target *= 0.85
    
    if rsi and rsi < 30:
        base_target *= 1.15
    elif rsi and rsi > 70:
        base_target *= 0.90
    
    if fundamentals:
        pe = fundamentals.get('pe_ratio')
        if pe and pe < 15:
            base_target *= 1.1
        elif pe and pe > 30:
            base_target *= 0.95
    
    if range_position and range_position < 20:
        base_target *= 1.1
    elif range_position and range_position > 80:
        base_target *= 0.95
    
    total_adj = max(0.08, min(0.25, base_target))
    
    # SMART STOP LOSS - Based on volatility (not fixed %)
    # Low volatility stocks: tighter stop (5-8%)
    # High volatility stocks: wider stop (10-15%)
    stop_pct = min(0.15, max(0.05, volatility / 200))  # 5-15% range based on volatility
    stop_loss = current_price * (1.0 - stop_pct)
    
    # SMART TAKE PROFIT - Based on volatility + conditions
    take_profit = current_price * (1.0 + total_adj)
    
    # Adjust for support/resistance with intelligent logic
    if support and resistance:
        # Use support if it's within reasonable range (not more than 15% away)
        if support > current_price * 0.85:
            stop_loss = max(stop_loss, support * 0.98)
        
        # Only use resistance as target if we're in strong uptrend AND resistance is close
        resistance_pct = ((resistance - current_price) / current_price) * 100
        if strong_uptrend and 0 < resistance_pct < 15:
            # In strong uptrend, resistance likely to break - use it as target
            take_profit = max(take_profit, resistance * 0.98)
        elif 0 < resistance_pct < 8:
            # Very close to resistance above us - cap target just below it
            take_profit = min(take_profit, resistance * 0.97)
        # If resistance is below current price (stock broke out), don't cap take profit
    
    # Final sanity check - take profit must always be above current price
    if take_profit <= current_price:
        take_profit = current_price * (1.0 + max(0.08, total_adj))
    
    # Stop loss must always be below current price
    if stop_loss >= current_price:
        stop_loss = current_price * (1.0 - stop_pct)
    
    # Scenario analysis
    scenarios = []
    if beta:
        market_drop_impact = -10 * beta
        scenarios.append(f"With a beta of {beta:.2f}, a 10% market fall would imply a move of about {abs(market_drop_impact):.1f}% for this stock")
    
    if support:
        support_drop = ((support - current_price) / current_price) * 100
        scenarios.append(f"Support at {money(support)} is {abs(support_drop):.1f}% {'below' if support_drop < 0 else 'above'} the current price")
    
    if resistance:
        resistance_gain = ((resistance - current_price) / current_price) * 100
        scenarios.append(f"Resistance at {money(resistance)} is {abs(resistance_gain):.1f}% {'above' if resistance_gain > 0 else 'below'} the current price")
    
    # Valuation justification
    justification = []
    if resistance and take_profit >= resistance * 0.95:
        justification.append(f"Upper level is based on resistance at {money(resistance)}")
    else:
        gain_pct = ((take_profit - current_price) / current_price) * 100
        justification.append(f"Upper level is set {gain_pct:.1f}% above the current price, from recent volatility")
    
    if fundamentals:
        pe = fundamentals.get('pe_ratio')
        if pe and pe > 30:
            justification.append(f"P/E {pe:.1f} suggests premium valuation")
        elif pe and pe < 15:
            justification.append(f"P/E {pe:.1f} is low relative to typical levels")
    
    risk_reward = (take_profit - current_price) / (current_price - stop_loss) if current_price > stop_loss else 0
    justification.append(f"Distance ratio (upper level vs lower level): 1:{risk_reward:.2f}")
    
    return {
        'recommendation': recommendation,
        'action': action,
        'confidence': confidence,
        'position_size': position_size,
        'urgency': urgency,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'risk_reward_ratio': risk_reward,
        'scenarios': scenarios,
        'justification': justification
    }

def get_recommendation_enhanced(fundamental_score, technical_score, severity_score):
    """Enhanced recommendation - kept for backward compatibility"""
    avg_score = (fundamental_score + technical_score) / 2
    
    if avg_score >= 8:
        return "Strong Buy"
    elif avg_score >= 6:
        return "Buy"
    elif avg_score >= 4:
        return "Hold"
    elif avg_score >= 2:
        return "Sell"
    else:
        return "Strong Sell"

def determine_market_sentiment(strong_buys, buys, sells):
    """Determine overall market sentiment"""
    total_positive = strong_buys + buys
    if total_positive > sells * 1.5:
        return "Bullish"
    elif sells > total_positive * 1.5:
        return "Bearish"
    else:
        return "Neutral"

def calculate_volatility(closes):
    """Calculate annualized volatility"""
    if len(closes) < 30:
        return 0
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, min(31, len(closes)))]
    variance = sum(r**2 for r in returns) / len(returns)
    import math
    return (variance**0.5) * math.sqrt(252) * 100  # Annualized volatility

def calculate_momentum(closes, days):
    """Calculate momentum"""
    if len(closes) < days + 1:
        return 0
    return ((closes[-1] - closes[-days-1]) / closes[-days-1]) * 100



def success_response(data):
    """Return success response"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps(data)
    }

def error_response(status_code, message):
    """Return error response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'error': message})
    }

# Test runner for local execution
if __name__ == "__main__":
    # Redirect all print statements to stderr except final output
    import builtins
    original_print = builtins.print
    def stderr_print(*args, **kwargs):
        if 'file' not in kwargs:
            kwargs['file'] = sys.stderr
        return original_print(*args, **kwargs)
    builtins.print = stderr_print
    
    # Test with AAPL with timezone offset for correct local time
    test_event = {
        'symbols': ['AAPL'],
        'timezone_offset': 10  # AEST/AEDT timezone offset
    }
    result = lambda_handler(test_event, None)
    
    # Restore original print for final output
    builtins.print = original_print
    
    # Extract and print the readable analysis to stdout
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        if body['results'] and len(body['results']) > 0:
            analysis = body['results'][0]['comprehensive_analysis']
            print(analysis)
        else:
            print("No analysis results found")
    else:
        print(f"Error: {result}")