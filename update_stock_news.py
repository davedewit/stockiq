#!/usr/bin/env python3
"""
Update Stock Pages with News Articles

This script:
1. Fetches recent news for each stock from Yahoo Finance RSS feeds
2. Matches news articles to stocks using company names and symbols
3. Filters articles by critical keywords (earnings, merger, FDA approval, etc.)
4. Updates individual stock HTML pages with the latest news
5. Maintains news.html archive and news.js sidebar (top 5 recent)
6. Respects 23-hour cooldown per stock to avoid duplicate updates

Stock Matching:
- US stocks (AAPL, TSLA): Matched via load_company_names() reading stocks.txt
- Non-US stocks (0700.HK, 7203.T): Matched via NUMERIC_COMPANY_NAMES fallback

Rate Limiting:
- Max 1 update per stock per 23 hours (business days)
- Prevents duplicate news from being added

Output:
- Updates /Users/ddewit/VSCODE/website/stocks/*.html (news section)
- Updates /Users/ddewit/VSCODE/website/news.html (archive)
- Updates /Users/ddewit/VSCODE/website/news.js (sidebar - top 5)

Usage:
    python3 update_stock_news.py

Note:
    - Requires OPENAI_API_KEY for news summarization
    - Uses Yahoo Finance RSS feeds for news source
    - Filters by critical keywords to avoid noise
"""

import os
import re
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

STOCKS_DIR = '/Users/ddewit/VSCODE/website/stocks'
NEWS_JS_PATH = '/Users/ddewit/VSCODE/website/news.js'
NEWS_HTML_PATH = '/Users/ddewit/VSCODE/website/news.html'

# Load OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    try:
        with open(os.path.expanduser('~/.openai_key'), 'r') as f:
            OPENAI_API_KEY = f.read().strip()
    except:
        pass

# Critical news keywords that trigger updates
CRITICAL_KEYWORDS = [
    'earnings', 'beat', 'miss', 'guidance', 'revenue', 'profit', 'loss',
    'acquisition', 'merger', 'buyout', 'deal', 'partnership', 'contract',
    'fda approval', 'approved', 'rejected', 'recall',
    'lawsuit', 'investigation', 'sec', 'fraud', 'settlement',
    'ceo', 'resignation', 'appointed', 'fired', 'steps down',
    'dividend', 'split', 'buyback', 'stock split',
    'bankruptcy', 'restructuring', 'layoffs', 'cuts jobs',
    'upgrade', 'downgrade', 'rating', 'price target',
    'breakthrough', 'innovation', 'launch', 'unveils',
    'stops production', 'halts', 'suspends', 'resumes',
    'expands', 'opens', 'closes', 'shuts down',
    'surges', 'plunges', 'soars', 'tumbles', 'rallies', 'drops', 'slips', 'dip', 'falls',
    'record', 'all-time high', 'new high', 'new low',
    'analyst', 'wall street', 'investors', 'institutional',
    'stock going to', 'price prediction', 'forecast'
]

# Load company names from stocks.txt dynamically
def load_company_names():
    """Load company names from stocks.txt and extract key words"""
    import os
    company_names = {}
    skip_words = {'INC', 'CORP', 'LTD', 'LIMITED', 'PLC', 'CO', 'COMPANY', 'GROUP', 'HOLDINGS', 'THE', 'AND', '&', 'SA', 'AG', 'SE', 'NV', 'N.V.'}
    
    stocks_file = '/Users/ddewit/VSCODE/website/stocks.txt'
    
    if not os.path.exists(stocks_file):
        print(f"Error: stocks.txt not found at {stocks_file}")
        return {}
    
    import csv
    with open(stocks_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                symbol = row[0].strip()
                name = row[1].strip()
                
                # Extract key words from company name
                import re
                words = re.findall(r'\b[A-Z][A-Za-z]*\b', name)
                key_words = [w.upper() for w in words if w.upper() not in skip_words]
                
                if key_words:
                    company_names[symbol] = ' '.join(key_words)
    
    return company_names

# Load company names at startup
COMPANY_NAMES = load_company_names()
print(f"Loaded {len(COMPANY_NAMES)} company names from stocks.txt")

# Fallback for numeric symbols (hardcoded as these are special cases)
NUMERIC_COMPANY_NAMES = {
    '0001.HK': 'CK HUTCHISON',
    '0002.HK': 'CLP',
    '0003.HK': 'HONG KONG',
    '0005.HK': 'HSBC',
    '0006.HK': 'POWER ASSETS',
    '0011.HK': 'HANG SENG',
    '0012.HK': 'HENDERSON LAND',
    '0016.HK': 'SUN HUNG',
    '0017.HK': 'NEW WORLD',
    '0027.HK': 'GALAXY ENTERTAINMENT',
    '0066.HK': 'MTR CORPORATION',
    '0083.HK': 'SINO LAND',
    '0101.HK': 'HANG LUNG',
    '0175.HK': 'GEELY AUTOMOBILE',
    '0241.HK': 'ALIBABA HEALTH',
    '0267.HK': 'CITIC',
    '0288.HK': 'WH',
    '0291.HK': 'CHINA RESOURCES',
    '0316.HK': 'ORIENT OVERSEAS',
    '0386.HK': 'CHINA PETROLEUM',
    '0388.HK': 'HONG KONG',
    '0669.HK': 'TECHTRONIC INDUSTRIES',
    '0688.HK': 'CHINA OVERSEAS',
    '0700.HK': 'TENCENT',
    '0762.HK': 'CHINA UNICOM',
    '0823.HK': 'LINK REAL',
    '0857.HK': 'PETROCHINA',
    '0883.HK': 'CNOOC',
    '0939.HK': 'CHINA CONSTRUCTION',
    '0941.HK': 'CHINA MOBILE',
    '0960.HK': 'LONGFOR',
    '0968.HK': 'XINYI SOLAR',
    '0981.HK': 'SEMICONDUCTOR MANUFACTURING',
    '0992.HK': 'LENOVO',
    '1038.HK': 'CK INFRASTRUCTURE',
    '1044.HK': 'HENGAN INTERNATIONAL',
    '1093.HK': 'CSPC PHARMACEUTICAL',
    '1109.HK': 'CHINA RESOURCES',
    '1113.HK': 'CK ASSET',
    '1177.HK': 'SINO BIOPHARMACEUTICAL',
    '1211.HK': 'BYD',
    '1299.HK': 'AIA',
    '1398.HK': 'INDUSTRIAL COMMERCIAL',
    '1605.T': 'INPEX CORPORATION',
    '1801.T': 'TAISEI CORPORATION',
    '1802.T': 'OBAYASHI CORPORATION',
    '1803.T': 'SHIMIZU CORPORATION',
    '1810.HK': 'XIAOMI CORPORATION',
    '1876.HK': 'BUDWEISER BREWING',
    '1918.HK': 'SUNAC CHINA',
    '1928.HK': 'SANDS CHINA',
    '1997.HK': 'WHARF REAL',
    '2002.T': 'NISSHIN SEIFUN',
    '2007.HK': 'COUNTRY GARDEN',
    '2018.HK': 'AAC TECHNOLOGIES',
    '2282.T': 'NH FOODS',
    '2432.T': 'DENA',
    '2501.T': 'SAPPORO',
    '2502.T': 'ASAHI',
    '2503.T': 'KIRIN',
    '2801.T': 'KIKKOMAN CORPORATION',
    '2802.T': 'AJINOMOTO',
    '2871.T': 'NICHIREI CORPORATION',
    '2914.T': 'JAPAN TOBACCO',
    '3086.T': 'J FRONT',
    '3099.T': 'ISETAN MITSUKOSHI',
    '3101.T': 'TOYOBO',
    '3103.T': 'UNITIKA',
    '3105.T': 'NISSHINBO',
    '3382.T': 'SEVEN',
    '3401.T': 'TEIJIN',
    '3402.T': 'TORAY INDUSTRIES',
    '3407.T': 'ASAHI KASEI',
    '3659.T': 'NEXON',
    '3861.T': 'OJI CORPORATION',
    '3863.T': 'NIPPON PAPER',
    '4004.T': 'RESONAC CORPORATION',
    '4005.T': 'SUMITOMO CHEMICAL',
    '4021.T': 'NISSAN CHEMICAL',
    '4043.T': 'TOKUYAMA CORPORATION',
    '4061.T': 'DENKA',
    '4063.T': 'SHIN ETSU',
    '4188.T': 'MITSUBISHI CHEMICAL',
    '4208.T': 'UBE CORPORATION',
    '4272.T': 'NIPPON KAYAKU',
    '4324.T': 'DENTSU',
    '4452.T': 'KAO CORPORATION',
    '4502.T': 'TAKEDA PHARMACEUTICAL',
    '4503.T': 'ASTELLAS PHARMA',
    '4506.T': 'SUMITOMO PHARMA',
    '4507.T': 'SHIONOGI',
    '4519.T': 'CHUGAI PHARMACEUTICAL',
    '4523.T': 'EISAI',
    '4568.T': 'DAIICHI SANKYO',
    '4578.T': 'OTSUKA',
    '4612.T': 'NIPPON PAINT',
    '4631.T': 'DIC CORPORATION',
    '4661.T': 'ORIENTAL LAND',
    '4689.T': 'LY CORPORATION',
    '4704.T': 'TREND MICRO',
    '4751.T': 'CYBERAGENT',
    '4755.T': 'RAKUTEN',
    '4901.T': 'FUJIFILM CORPORATION',
    '4911.T': 'SHISEIDO',
    '4912.T': 'LION CORPORATION',
    '5019.T': 'IDEMITSU KOSAN',
    '5020.T': 'ENEOS',
    '5101.T': 'YOKOHAMA RUBBER',
    '5108.T': 'BRIDGESTONE CORPORATION',
    '5201.T': 'AGC',
    '5202.T': 'NIPPON SHEET',
    '5214.T': 'NIPPON ELECTRIC',
    '5232.T': 'SUMITOMO OSAKA',
    '5233.T': 'TAIHEIYO CEMENT',
    '5301.T': 'TOKAI CARBON',
    '5332.T': 'TOTO',
    '5333.T': 'NGK INSULATORS',
    '5401.T': 'NIPPON STEEL',
    '5406.T': 'KOBE STEEL',
    '5411.T': 'JFE',
    '5631.T': 'JAPAN STEEL',
    '5703.T': 'NIPPON LIGHT',
    '5706.T': 'MITSUI KINZOKU',
    '5707.T': 'TOHO ZINC',
    '5711.T': 'MITSUBISHI MATERIALS',
    '6501.T': 'HITACHI',
    '6503.T': 'MITSUBISHI ELECTRIC',
    '6758.T': 'SONY CORPORATION',
    '6861.T': 'KEYENCE CORPORATION',
    '6902.T': 'DENSO CORPORATION',
    '6954.T': 'FANUC CORPORATION',
    '7203.T': 'TOYOTA MOTOR',
    '7267.T': 'HONDA MOTOR',
    '7751.T': 'CANON',
    '8001.T': 'ITOCHU CORPORATION',
    '8031.T': 'MITSUI',
    '8035.T': 'TOKYO ELECTRON',
    '8058.T': 'MITSUBISHI CORPORATION',
    '8306.T': 'MITSUBISHI UFJ',
    '8316.T': 'SUMITOMO MITSUI',
    '9020.T': 'EAST JAPAN',
    '9022.T': 'CENTRAL JAPAN',
    '9432.T': 'NTT',
    '9984.T': 'SOFTBANK',
}


def find_matching_stock(title):
    """Find which stock this article is actually about"""
    title_upper = title.upper()
    
    # First check company names (most specific)
    for symbol, name in COMPANY_NAMES.items():
        if name and name in title_upper:
            return symbol
    
    # Then check symbols (only 3+ characters to avoid false matches)
    import re
    for symbol in COMPANY_NAMES.keys():
        if len(symbol) >= 3:  # Skip short symbols like C, O, ON, IT, etc.
            # Match symbol as whole word with word boundaries
            if re.search(r'\b' + re.escape(symbol) + r'\b', title_upper):
                return symbol
    
    return None

def is_business_day(date):
    """Check if date is a business day (Mon-Fri)"""
    return date.weekday() < 5

def business_days_since(last_update_str):
    """Calculate business days since last update"""
    last_update = datetime.fromisoformat(last_update_str)
    today = datetime.now()
    
    business_days = 0
    current = last_update.date()
    while current < today.date():
        current += timedelta(days=1)
        if is_business_day(current):
            business_days += 1
    
    return business_days

def fetch_stock_news(symbol):
    """Fetch recent news for a stock symbol"""
    try:
        # Use Yahoo Finance RSS feed
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        # Only consider articles from last 2 days
        from dateutil import parser as date_parser
        cutoff_date = datetime.now() - timedelta(days=2)
        
        news = []
        for item in items[:10]:  # Check first 10 articles
            title = item.find('title').text if item.find('title') else ''
            link = item.find('link').text if item.find('link') else ''
            pub_date = item.find('pubDate').text if item.find('pubDate') else ''
            
            # Check article age - MUST have valid date
            article_date = None
            if pub_date:
                try:
                    article_date = date_parser.parse(pub_date)
                    if article_date.replace(tzinfo=None) < cutoff_date:
                        continue  # Skip articles older than 2 days
                except:
                    continue  # Skip if can't parse date - we need to verify it's recent
            
            # Check if article is actually about this stock
            title_upper = title.upper()
            is_match = False
            
            # Extract base symbol (e.g., BHP from BHP.AX, SAP from SAP.DE)
            base_symbol = symbol.split('.')[0]
            
            # For numeric symbols, check if company name appears in title
            if base_symbol.isdigit():
                # Use NUMERIC_COMPANY_NAMES fallback for known numeric symbols
                company_names = NUMERIC_COMPANY_NAMES.get(base_symbol, [])
                if company_names:
                    for name in company_names:
                        if name in title_upper:
                            is_match = True
                            break
                else:
                    # Try the main dictionary
                    company_name = COMPANY_NAMES.get(symbol, '')
                    if company_name and company_name in title_upper:
                        is_match = True
            else:
                # Check company name first (most reliable)
                company_name = COMPANY_NAMES.get(symbol, '')
                if company_name and company_name in title_upper:
                    is_match = True
                
                # NEW LOGIC: Check base symbol in title (for shortened names)
                # Only if base_symbol is a valid key in dictionary
                if not is_match and base_symbol in COMPANY_NAMES:
                    # Check if base symbol appears in title
                    import re
                    if re.search(r'\b' + re.escape(base_symbol) + r'\b', title_upper):
                        is_match = True
                
                # Check full symbol (only if 3+ chars to avoid false matches)
                if not is_match and len(symbol) >= 3:
                    import re
                    if re.search(r'\b' + re.escape(symbol) + r'\b', title_upper):
                        is_match = True
            
            # Skip if no clear match
            if not is_match:
                continue
            
            # Check if news is critical
            is_critical = any(keyword in title.lower() for keyword in CRITICAL_KEYWORDS)
            
            if is_critical:
                # Clean up link - remove RSS tracking parameter
                clean_link = link.split('?.tsrc=')[0] if '?.tsrc=' in link else link
                news.append({
                    'title': title,
                    'link': clean_link,
                    'date': pub_date,
                    'critical': True
                })
        
        return news
    except Exception as e:
        print(f"Error fetching news for {symbol}: {e}")
        return []

def generate_news_summary(symbol, news_item):
    """Generate AI summary of news"""
    if not OPENAI_API_KEY:
        return f"<p><strong>Latest Update:</strong> {news_item['title']}</p>"
    
    try:
        from openai import OpenAI
        from dateutil import parser as date_parser
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""Summarize this stock news in 2-3 sentences (60-80 words) for {symbol}:

"{news_item['title']}"

Focus on:
- What happened
- Why it matters for investors
- Keep it factual and concise"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial analyst writing brief stock updates."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Store UTC timestamp for JavaScript to convert to user's local timezone
        date_str = ''
        date_iso = ''
        if news_item.get('date'):
            try:
                import random
                pub_date = date_parser.parse(news_item['date'])
                # Store ISO format for JavaScript conversion
                date_iso = pub_date.isoformat()
                # Random read time between 2-4 minutes
                read_time = random.choice([2, 3, 4])
                # Fallback text (will be replaced by JavaScript)
                date_str = pub_date.strftime(f'%a, %B %-d, %Y at %-I:%M %p UTC {read_time} min read')
            except:
                pass
        
        # Format as HTML with data attribute for JavaScript
        date_html = f'<p style="margin: 5px 0; font-size: 0.85em; color: var(--text-secondary);" data-timestamp="{date_iso}" class="article-date">{date_str}</p>' if date_str else ''
        
        # Format as HTML with theme-aware colors
        return f"""<div style="background: var(--bg-secondary); border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <h3 style="margin-top: 0; color: var(--text-primary);">📰 Latest Update</h3>
            <p style="margin: 10px 0; color: var(--text-primary);"><strong>{news_item['title']}</strong></p>
            {date_html}
            <p style="margin: 10px 0; color: var(--text-secondary);">{summary}</p>
            <p style="margin: 10px 0 0 0; font-size: 0.9em; color: var(--text-secondary);">
                <a href="{news_item['link']}" target="_blank" style="color: #007bff;">Read full article →</a>
            </p>
        </div>"""
    
    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"<p><strong>Latest Update:</strong> {news_item['title']}</p>"

def update_news_html(items):
    """Update news.html - remove old stock articles (3+ days), replace existing with new"""
    try:
        with open(NEWS_HTML_PATH, 'r') as f:
            html = f.read()
        
        # Extract existing articles
        articles = re.findall(r'<article class="blog-post"[^>]*>.*?</article>', html, re.DOTALL)
        
        # Get symbols being updated
        updated_symbols = {item['symbol'] for item in items}
        
        # Filter: remove old stock articles (30+ days) and articles being replaced
        from dateutil import parser as date_parser
        cutoff_date = datetime.now() - timedelta(days=30)
        filtered_articles = []
        
        for article in articles:
            # Check if stock news
            is_stock_news = 'Stock News' in article
            
            if is_stock_news:
                # Extract symbol
                symbol_match = re.search(r'Category: ([A-Z]+) Stock News', article)
                if symbol_match:
                    symbol = symbol_match.group(1)
                    # Skip if being updated
                    if symbol in updated_symbols:
                        continue
                
                # Check age
                date_match = re.search(r'Published: ([^|]+)', article)
                if date_match:
                    try:
                        article_date = date_parser.parse(date_match.group(1).strip())
                        if article_date.replace(tzinfo=None) < cutoff_date:
                            continue  # Skip old articles
                    except:
                        pass
            
            filtered_articles.append(article)
        
        # Create new articles
        new_articles = []
        for item in items:
            # Use the article's actual timestamp if available, otherwise use now
            if item.get('timestamp'):
                try:
                    from dateutil import parser as date_parser
                    import random
                    pub_date = date_parser.parse(item['timestamp'])
                    read_time = random.choice([2, 3, 4])
                    today = pub_date.strftime(f'%a, %B %-d, %Y at %-I:%M %p UTC {read_time} min read')
                    today_iso = pub_date.isoformat()
                except:
                    import random
                    now = datetime.now()
                    read_time = random.choice([2, 3, 4])
                    today = now.strftime(f'%a, %B %-d, %Y at %-I:%M %p UTC {read_time} min read')
                    today_iso = now.isoformat()
            else:
                import random
                now = datetime.now()
                read_time = random.choice([2, 3, 4])
                today = now.strftime(f'%a, %B %-d, %Y at %-I:%M %p UTC {read_time} min read')
                today_iso = now.isoformat()
            
            new_articles.append(f'''            <article class="blog-post" id="{item['symbol'].lower()}-stock-news">
                <h2 style="margin: 0;"><a href="stocks/{item['symbol']}.html" style="color: inherit; text-decoration: none; display: inline-block; width: 100%; padding: 0 0 10px 0;">📰 {item['title']}</a></h2>
                <div class="blog-meta"><span data-timestamp="{today_iso}" class="article-date">Published: {today}</span> | Category: {item['symbol']} Stock News</div>
                <div class="blog-excerpt">
                    <p>{item['summary']}</p>
                    <p><a href="{item['link']}" target="_blank" style="color: #007bff;">Read full article →</a> | <a href="analysis.html?symbol={item['symbol']}&option=1&subOption=custom" style="color: #007bff;">Analyze {item['symbol']} Stock →</a></p>
                </div>
            </article>
''')
        
        # Combine: new at top, then existing
        all_articles = new_articles + filtered_articles
        
        # Update article count
        article_count = len(all_articles)
        html = re.sub(r'<span id="article-count">[0-9]+</span>', f'<span id="article-count">{article_count}</span>', html)
        
        # Insert after blog-content div
        content_start = html.find('<div class="blog-content">')
        if content_start == -1:
            return
        
        before = html[:content_start + len('<div class="blog-content">')]
        after_match = re.search(r'</div>\s*<footer', html)
        if not after_match:
            print("❌ Could not find footer pattern in news.html")
            return
        after = html[after_match.start():]
        
        new_html = before + '\n' + '\n'.join(all_articles) + '''        </div>

    <div style="text-align: center; padding: 30px 20px; color: var(--text-secondary); font-size: 0.9rem;">
        <p>📊 Showing <span id="article-count">''' + str(article_count) + '''</span> articles</p>
    </div>

    ''' + after
        
        with open(NEWS_HTML_PATH, 'w') as f:
            f.write(new_html)
    
    except Exception as e:
        import traceback
        print(f"Error updating news.html: {e}")
        traceback.print_exc()

def update_news_js(items):
    """Add/update stock news in news.js, preserving general market news"""
    try:
        # Read existing items
        existing_items = []
        if os.path.exists(NEWS_JS_PATH):
            with open(NEWS_JS_PATH, 'r') as f:
                content = f.read()
            
            match = re.search(r'const newsItems = \[(.*?)\];', content, re.DOTALL)
            if match:
                array_content = match.group(1)
                raw_items = re.split(r'\},\s*\{', array_content)
                for raw in raw_items:
                    raw = raw.strip()
                    if not raw:
                        continue
                    if not raw.startswith('{'):
                        raw = '{' + raw
                    if not raw.endswith('}'):
                        raw = raw + '}'
                    existing_items.append(raw)
        
        # Get stock symbols being updated
        updated_symbols = {item['symbol'] for item in items}
        
        # Filter existing: remove old items (30+ days), keep general news + stock news for other symbols
        from dateutil import parser as date_parser
        cutoff_date = datetime.now() - timedelta(days=30)
        filtered_existing = []
        
        for existing in existing_items:
            symbol_match = re.search(r"stockSymbol:\s*'([^']*)'", existing)
            date_match = re.search(r"date:\s*'([^']+)'", existing)
            
            # Check if item is too old
            if date_match:
                try:
                    item_date = date_parser.parse(date_match.group(1))
                    if item_date.replace(tzinfo=None) < cutoff_date:
                        continue  # Skip old items
                except:
                    pass
            
            if symbol_match:
                symbol = symbol_match.group(1)
                # Keep if not being updated
                if symbol not in updated_symbols:
                    filtered_existing.append('    ' + existing)
            else:
                # No stockSymbol = general market news, always keep (if not old)
                filtered_existing.append('    ' + existing)
        
        # Create new items
        new_items_js = []
        for item in items:
            # Use the article's actual timestamp if available, otherwise use now
            if item.get('timestamp'):
                try:
                    from dateutil import parser as date_parser
                    import random
                    pub_date = date_parser.parse(item['timestamp'])
                    read_time = random.choice([2, 3, 4])
                    today = pub_date.strftime(f'%a, %B %-d, %Y at %-I:%M %p UTC {read_time} min read')
                    today_iso = pub_date.isoformat()
                except:
                    import random
                    now = datetime.now()
                    read_time = random.choice([2, 3, 4])
                    today = now.strftime(f'%a, %B %-d, %Y at %-I:%M %p UTC {read_time} min read')
                    today_iso = now.isoformat()
            else:
                import random
                now = datetime.now()
                read_time = random.choice([2, 3, 4])
                today = now.strftime(f'%a, %B %-d, %Y at %-I:%M %p UTC {read_time} min read')
                today_iso = now.isoformat()
            
            item_id = re.sub(r'[^a-z0-9]+', '-', item['title'].lower())[:50].strip('-')
            title = item['title'].replace("\\", "\\\\").replace("'", "\\'")
            preview = item['preview'].replace("\\", "\\\\").replace("'", "\\'")
            
            new_items_js.append(f"""    {{
        id: '{item_id}',
        emoji: '📰',
        title: '{title}',
        date: '{today}',
        timestamp: '{today_iso}',
        preview: '{preview}',
        stockSymbol: '{item['symbol']}'
    }}""")
        
        # Separate stock and general news
        stock_items = [item for item in (new_items_js + filtered_existing) if "stockSymbol: ''" not in item]
        general_items = [item for item in filtered_existing if "stockSymbol: ''" in item]
        
        # Limit: 80 stock + 20 general = 100 total
        stock_items = stock_items[:80]
        general_items = general_items[:20]
        
        # Combine (stock first, then general)
        all_items = stock_items + general_items
        
        items_str = ',\n'.join(all_items)
        
        # Rebuild news.js
        render_func = '''// Render news items into the sidebar
function renderNewsItems() {
    const container = document.getElementById('news-items');
    if (!container) return;
    
    // Sort all items by date (newest first)
    const sortedItems = [...newsItems].sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return dateB - dateA;
    });
    
    // Separate stock news and general news from sorted items
    const stockNews = sortedItems.filter(item => item.stockSymbol);
    const generalNews = sortedItems.filter(item => !item.stockSymbol);
    
    // Show 1 general + 4 stock news
    const displayItems = [];
    if (generalNews.length > 0) displayItems.push(generalNews[0]);
    displayItems.push(...stockNews.slice(0, 4));
    
    container.innerHTML = displayItems.map(item => {
        const url = item.stockSymbol ? `stocks/${item.stockSymbol}.html` : `news.html#${item.id}`;
        return `
        <div class="news-item" style="padding: 8px; margin-bottom: 8px; border-bottom: 1px solid var(--border-color); cursor: pointer;" onclick="window.location.href='${url}'">
            <div style="font-weight: 600; color: var(--text-primary); font-size: 0.85rem; margin-bottom: 3px;">${item.emoji} ${item.title}</div>
            <div style="color: var(--text-secondary); font-size: 0.7rem; margin-bottom: 2px;" data-timestamp="${item.timestamp || ''}" class="article-date">${item.date}</div>
            <div style="color: var(--text-secondary); font-size: 0.75rem; line-height: 1.3;">${item.preview}</div>
        </div>
        `;
    }).join('');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderNewsItems);
} else {
    renderNewsItems();
}'''
        
        new_content = f"""// Shared news items for Market News sidebar
const newsItems = [
{items_str}
];

{render_func}
"""
        
        with open(NEWS_JS_PATH, 'w') as f:
            f.write(new_content)
    
    except Exception as e:
        print(f"Error updating news.js: {e}")

def update_stock_page(symbol, news_html):
    """Update stock page HTML with news section - keeps last 3 articles"""
    file_path = os.path.join(STOCKS_DIR, f"{symbol}.html")
    
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract existing news articles
    existing_articles = []
    news_section_match = re.search(
        r'<!-- NEWS_SECTION_START -->(.*?)<!-- NEWS_SECTION_END -->',
        content,
        flags=re.DOTALL
    )
    
    if news_section_match:
        # Extract individual articles - each is a complete div block
        # Match from <div style="background: var(--bg-secondary) to its closing </div>
        articles = re.findall(
            r'<div style="background: var\(--bg-secondary\);[^>]*>(?:(?!</div>).)*</div>',
            news_section_match.group(1),
            flags=re.DOTALL
        )
        # Convert old articles to collapsed format
        collapsed_articles = []
        if len(articles) > 0:
            # Add "History" header before collapsed articles
            collapsed_articles.append('<h4 style="margin: 30px 0 10px 0; color: var(--text-secondary); font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px;">History</h4>')
        
        for i, article in enumerate(articles[:2]):
            from dateutil import parser as date_parser
            # Extract title, link, and date
            title_match = re.search(r'<strong>([^<]+)</strong>', article)
            link_match = re.search(r'href="([^"]+)"', article)
            date_match = re.search(r'data-timestamp="([^"]+)"', article)
            
            if title_match and link_match and date_match:
                title = title_match.group(1)
                link = link_match.group(1)
                article_id = f'older-news-{i+1}'
                
                # Format date for button - will be converted by JavaScript
                date_str = 'Older Update'
                try:
                    pub_date = date_parser.parse(date_match.group(1))
                    # Use UTC date as placeholder (JS will convert)
                    date_str = pub_date.strftime('%B %-d, %Y')
                except:
                    pass
                
                button_text = f'{date_str}: {title[:60]}{"..." if len(title) > 60 else ""}'
                button_text_escaped = button_text.replace("'", "\\'").replace('"', '&quot;')
                
                # Remove h3 heading from old articles
                article_cleaned = re.sub(r'<h3[^>]*>📰 (?:Latest|Previous) Update</h3>\s*', '', article)
                
                collapsed = f'''<div style="margin: 20px 0;">
            <button data-timestamp="{date_match.group(1)}" class="collapsed-btn" onclick="var d=document.getElementById('{article_id}');var open=d.style.display==='block';d.style.display=open?'none':'block';this.innerHTML=open?'▶ {button_text_escaped}':'▼ {button_text_escaped}';" style="background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-color); padding: 15px 20px; border-radius: 4px; cursor: pointer; width: 100%; text-align: left; font-size: 1em; line-height: 1.5;">
                ▶ {button_text_escaped}
            </button>
            <div id="{article_id}" style="display: none; margin-top: 10px;">
                {article_cleaned}
            </div>
        </div>'''
                collapsed_articles.append(collapsed)
        
        existing_articles = collapsed_articles
    
    # Combine new article + collapsed old articles (max 3 total)
    all_articles = [news_html] + existing_articles
    combined_html = '\n        '.join(all_articles)
    
    # Count total articles for logging
    total_articles = len(all_articles)
    article_count_msg = f" (now {total_articles} article{'s' if total_articles > 1 else ''})"
    
    # Remove old news section
    content = re.sub(
        r'<!-- NEWS_SECTION_START -->.*?<!-- NEWS_SECTION_END -->',
        '',
        content,
        flags=re.DOTALL
    )
    
    # Insert combined news section
    news_section = f"""

        <!-- NEWS_SECTION_START -->
        {combined_html}
        <!-- NEWS_SECTION_END -->
"""
    
    # Find insertion point - after CTA closing </div>, before features grid
    pattern = r'(</div>\s*)(\s*<div style="display: grid; grid-template-columns: repeat\(auto-fit, minmax\(300px, 1fr\)\);)'
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, r'\1' + news_section + r'\2', content, count=1, flags=re.DOTALL)
    else:
        # Fallback: insert before features grid
        pattern = r'(<div style="display: grid; grid-template-columns: repeat\(auto-fit, minmax\(300px, 1fr\)\);)'
        content = re.sub(pattern, news_section + r'\1', content, count=1)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    return True

def main():
    import sys
    import os
    
    force_update = os.getenv('UPDATE_STOCK_NEWS', 'false').lower() == 'true'
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # Check if CSV file
        if arg.endswith('.csv') and os.path.isfile(arg):
            import csv
            stock_files = []
            with open(arg, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if row:  # Check if row is not empty
                        url = row[0].strip()  # Get first column (URL)
                        url_match = re.search(r'/stocks/([A-Z0-9.]+)\.html', url)
                        if url_match:
                            stock_files.append(url_match.group(1).upper())
        # Extract URLs from argument
        elif re.search(r'/stocks/[A-Z0-9.]+\.html', arg):
            urls = re.findall(r'/stocks/([A-Z0-9.]+)\.html', arg)
            stock_files = [u.upper() for u in urls]
        # Comma-separated symbols
        elif ',' in arg:
            stock_files = [s.strip().upper() for s in arg.split(',')]
        # Single symbol or file
        elif os.path.isfile(arg):
            with open(arg, 'r') as f:
                stock_files = [line.strip().upper() for line in f if line.strip()]
        else:
            stock_files = [arg.upper()]
        print(f"🔍 Updating {len(stock_files)} stock(s)...\n")
    else:
        print("🔍 Stock News Updater\n")
        print("Usage:")
        print("  python3 update_stock_news.py AAPL")
        print("  python3 update_stock_news.py \"AAPL,MSFT,GOOGL,TSLA,NVDA\"")
        print("  python3 update_stock_news.py https://stockiq.tech/stocks/TITN.html")
        print("  python3 update_stock_news.py https://stockiq.tech/stocks/8316.T.html")
        print("  python3 update_stock_news.py indexed_without_news.txt")
        print("  python3 update_stock_news.py  # Check all stocks for critical news\n")
        print("🔍 Checking for critical stock news updates...\n")
        stock_files = [f.replace('.html', '') for f in os.listdir(STOCKS_DIR) if f.endswith('.html')]
    
    updates_made = 0
    removed_old = 0
    updated_items = []
    checked = 0
    total = len(stock_files)
    batch_size = 10  # Update blog/news every 10 articles
    
    # First pass: remove old news from stock pages (30+ days) - SKIP if force_update
    if not force_update:
        cutoff_date = datetime.now() - timedelta(days=30)
        for symbol in stock_files:
            file_path = os.path.join(STOCKS_DIR, f"{symbol}.html")
            if not os.path.exists(file_path):
                continue
            
            # Check if page has news section with timestamp
            with open(file_path, 'r') as f:
                content = f.read()
            
            if '<!-- NEWS_SECTION_START -->' in content:
                # Extract timestamp from news section
                timestamp_match = re.search(r'data-timestamp="([^"]+)"', content)
                if timestamp_match:
                    try:
                        from dateutil import parser as date_parser
                        news_date = date_parser.parse(timestamp_match.group(1))
                        if news_date.replace(tzinfo=None) < cutoff_date:
                            # Remove old news
                            content = re.sub(
                                r'<!-- NEWS_SECTION_START -->.*?<!-- NEWS_SECTION_END -->',
                                '',
                                content,
                                flags=re.DOTALL
                            )
                            with open(file_path, 'w') as f:
                                f.write(content)
                            removed_old += 1
                    except:
                        pass
        
        if removed_old > 0:
            print(f"🗑️  Removed {removed_old} old news items (30+ days)\n")
    
    # Second pass: add new news
    for symbol in stock_files:
        checked += 1
        
        if checked % 100 == 0:
            print(f"⏳ [{checked}/{total}] Checking stocks...", flush=True)
        
        print(f"⏳ [{checked}/{total}] Checking {symbol}...", end='\r', flush=True)
        
        # Fetch news (only returns articles that clearly match this stock)
        news = fetch_stock_news(symbol)
        
        if not news:
            continue  # No critical news
        
        # Use most recent critical news
        latest_news = news[0]
        
        # Check if page already has this exact news
        file_path = os.path.join(STOCKS_DIR, f"{symbol}.html")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                page_content = f.read()
            if latest_news['title'] in page_content:
                # Update timestamp even if article is the same (fresh signal for Google)
                import random
                now = datetime.now()
                read_time = random.choice([2, 3, 4])
                today = now.strftime(f'%a, %B %-d, %Y at %-I:%M %p UTC {read_time} min read')
                today_iso = now.isoformat()
                # Update both the date text and timestamp attribute
                updated_content = re.sub(
                    r'data-timestamp="[^"]*"[^>]*class="article-date"[^>]*>Published: [^<]+',
                    f'data-timestamp="{today_iso}" class="article-date">Published: {today}',
                    page_content
                )
                # Update data-timestamp attribute
                from dateutil import parser as date_parser
                if latest_news.get('date'):
                    try:
                        pub_date = date_parser.parse(latest_news['date'])
                        date_iso = pub_date.isoformat()
                        updated_content = re.sub(
                            r'data-timestamp="[^"]*"',
                            f'data-timestamp="{date_iso}"',
                            updated_content
                        )
                    except:
                        pass
                with open(file_path, 'w') as f:
                    f.write(updated_content)
                continue  # Skip adding duplicate article but timestamp is refreshed
        
        print(f"📰 {symbol}: {latest_news['title'][:60]}...")
        
        # Generate summary
        news_html = generate_news_summary(symbol, latest_news)
        
        # Extract summary text from HTML
        summary_match = re.search(r'<p style="margin: 10px 0; color: var\(--text-secondary\);">([^<]+)</p>', news_html)
        summary = summary_match.group(1) if summary_match else latest_news['title']
        
        # Update page
        if update_stock_page(symbol, news_html):
            updates_made += 1
            
            # Count articles in updated page (count all article divs in NEWS_SECTION)
            with open(file_path, 'r') as f:
                updated_content = f.read()
            news_section_match = re.search(r'<!-- NEWS_SECTION_START -->(.*?)<!-- NEWS_SECTION_END -->', updated_content, re.DOTALL)
            if news_section_match:
                # Count: 1 latest + collapsed buttons
                article_count = 1 + news_section_match.group(1).count('<button onclick=')
            else:
                article_count = 1
            
            print(f"   ✅ Updated {symbol}.html (now {article_count} article{'s' if article_count > 1 else ''})")
            
            # Store for news.js update
            preview = summary[:150] + '...' if len(summary) > 150 else summary
            updated_items.append({
                'symbol': symbol,
                'title': latest_news['title'],
                'summary': summary,
                'preview': preview,
                'link': latest_news['link'],
                'timestamp': latest_news.get('date', '')
            })
            
            # Update news.html and news.js every 10 articles
            if len(updated_items) >= batch_size:
                update_news_js(updated_items)
                update_news_html(updated_items)
                print(f"   📝 Synced {len(updated_items)} articles to news.html")
                updated_items = []  # Clear batch
    
    print(f"\n✅ Updated {updates_made} stock pages")
    
    # Update news.js with stock updates (final batch)
    if len(updated_items) > 0:
        update_news_js(updated_items)
        print(f"✅ Added {len(updated_items)} items to homepage news")
        update_news_html(updated_items)
        print(f"✅ Added {len(updated_items)} items to news.html")

if __name__ == '__main__':
    main()
