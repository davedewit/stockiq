#!/usr/bin/env python3
"""
Test Stock RSS - Pre-screening tool for deciding which stocks to add

Purpose:
    Check if a stock has had news articles in the last ~20 days before adding it.
    No point generating a page for a stock with no recent coverage.
    
Cost Model:
    - Running this script: FREE (just checks RSS feeds)
    - Adding stock + generating page: FREE
    - Cost only occurs when an article is discovered and processed
    
Workflow:
    1. Find candidate stocks (research, screeners, etc.)
    2. Run this script to check if they have recent news
    3. Only add stocks that show "Matched (ready now)"
    4. Add symbol to stocks.txt and proceed with workflow
    
Usage:
    Option 1: Test random stocks from existing pages
    Option 2: Test specific stocks you're considering adding
    
Example:
    echo -e "2\nTSLA\n" | python3 test_stock_rss.py
    
    Look for: ✅ Matched (ready now)
    If yes → Stock is worth adding (has recent critical news)
    If no → Skip it (no recent coverage, waste of a page)
"""

import os
import json
import random
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser as date_parser

STOCKS_DIR = '/Users/ddewit/VSCODE/website/stocks'
CONFIG_FILE = os.path.expanduser('~/.test_stock_rss_config.json')

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

def load_company_names():
    try:
        import sys
        sys.path.insert(0, '/Users/ddewit/VSCODE/stockiq')
        from update_stock_news import COMPANY_NAMES
        return COMPANY_NAMES
    except:
        return {}

COMPANY_NAMES = load_company_names()

NUMERIC_COMPANY_NAMES = {
    '7203': ['TOYOTA'],
    '0700': ['TENCENT'],
    '0005': ['HSBC'],
    '0941': ['CHINA MOBILE'],
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'days_cutoff': 2, 'articles_limit': 10}

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f)

config = load_config()
days_cutoff = config['days_cutoff']
articles_limit = config['articles_limit']

def count_articles_in_page(symbol):
    """Count articles in stock HTML page and get most recent date"""
    file_path = os.path.join(STOCKS_DIR, f"{symbol}.html")
    if not os.path.exists(file_path):
        return 0, None
    with open(file_path, 'r') as f:
        content = f.read()
    news_match = re.search(r'<!-- NEWS_SECTION_START -->(.*?)<!-- NEWS_SECTION_END -->', content, re.DOTALL)
    if not news_match:
        return 0, None
    news_content = news_match.group(1).strip()
    if not news_content:
        return 0, None
    count = 1 + news_content.count('<button')
    date_text_match = re.search(r'class="article-date"[^>]*>([^<]+)</p>', news_content)
    date_str = None
    if date_text_match:
        date_text = date_text_match.group(1).strip()
        date_match = re.search(r'(\w+,\s+\w+\s+\d+,\s+\d{4})', date_text)
        if date_match:
            date_str = date_match.group(1)
    return count, date_str

def get_news(symbol, show_all=False):
    """Get all articles for symbol with details - matches update_stock_news.py logic"""
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️  HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        if not show_all and len(items) == 0:
            print(f"   ⚠️  RSS returned 0 items (status {response.status_code})")
        
        cutoff_date = datetime.now() - timedelta(days=days_cutoff)
        
        articles = []
        for item in items[:articles_limit]:
            title = item.find('title').text if item.find('title') else ''
            pub_date = item.find('pubDate').text if item.find('pubDate') else ''
            
            title_upper = title.upper()
            is_match = False
            base_symbol = symbol.split('.')[0]
            
            # For numeric symbols, check if company name appears in title
            if base_symbol.isdigit():
                numeric_names = NUMERIC_COMPANY_NAMES.get(base_symbol, [])
                for name in numeric_names:
                    if name in title_upper:
                        is_match = True
                        break
            else:
                # Check company names first (most reliable)
                names = COMPANY_NAMES.get(symbol, [])
                if isinstance(names, str):
                    names = [names]
                for name in names:
                    if name.upper() in title_upper:
                        is_match = True
                        break
                
                # NEW LOGIC: Check base symbol in title (for shortened names)
                # Only if base_symbol is a valid key in dictionary
                if not is_match and base_symbol in COMPANY_NAMES:
                    # Check if base symbol appears in title
                    if re.search(r'\b' + re.escape(base_symbol) + r'\b', title_upper):
                        is_match = True
                
                # Check full symbol (only if 3+ chars to avoid false matches)
                if not is_match and len(symbol) >= 3:
                    if re.search(r'\b' + re.escape(symbol) + r'\b', title_upper):
                        is_match = True
            
            article_date = None
            if pub_date:
                try:
                    article_date = date_parser.parse(pub_date)
                except:
                    continue  # Skip if can't parse date - we need to verify it's recent
            
            is_critical = any(keyword in title.lower() for keyword in CRITICAL_KEYWORDS)
            is_recent = article_date and article_date.replace(tzinfo=None) >= cutoff_date if article_date else False
            
            if show_all:
                articles.append({
                    'title': title,
                    'date': pub_date,
                    'critical': is_critical,
                    'recent': is_recent,
                    'is_match': is_match
                })
            elif is_match:
                articles.append({
                    'title': title,
                    'date': pub_date,
                    'critical': is_critical,
                    'recent': is_recent
                })
        
        return articles
    except requests.RequestException as e:
        print(f"   ⚠️  Request error: {e}")
        return []

def test_random_stocks():
    """Test random stocks for available news"""
    try:
        count = int(input("\nHow many random stocks to test? ").strip())
        if count <= 0:
            print("❌ Must be greater than 0")
            return
    except ValueError:
        print("❌ Invalid number")
        return
    
    stock_files = sorted([f.replace('.html', '') for f in os.listdir(STOCKS_DIR) if f.endswith('.html')])
    symbols = random.sample(stock_files, min(count, len(stock_files)))
    
    matched = 0
    matched_no_article = 0
    missed_days = 0
    missed_filter = 0
    no_articles = 0
    
    for symbol in symbols:
        page_articles, article_date = count_articles_in_page(symbol)
        article_text = f" (stocks/{symbol}.html has {page_articles} article{'s' if page_articles != 1 else ''})"
        if page_articles == 1 and article_date:
            article_text += f" - {article_date}"
        print(f"\n{'='*60}")
        print(f"📊 {symbol}{article_text}")
        print(f"{'='*60}")
        
        articles = get_news(symbol)
        
        if not articles:
            print("❌ No articles found")
            no_articles += 1
            continue
        
        has_critical_recent = False
        has_old_critical = False
        
        for i, article in enumerate(articles, 1):
            status = "✅" if (article['critical'] and article['recent']) else "⚠️ " if article['critical'] else "❌"
            if article['critical'] and article['recent']:
                has_critical_recent = True
            elif article['critical'] and not article['recent']:
                has_old_critical = True
            
            print(f"\n{i}. {status} {article['title'][:70]}")
            print(f"   Date: {article['date']}")
            print(f"   Critical: {article['critical']} | Recent ({days_cutoff}d): {article['recent']}")
        
        if has_critical_recent:
            matched += 1
            if page_articles == 0:
                matched_no_article += 1
        elif has_old_critical:
            missed_days += 1
        else:
            missed_filter += 1
    
    print(f"\n\n📊 Summary:")
    print(f"   ✅ Matched (ready now): {matched}/{len(symbols)}")
    print(f"   ✨ Matched (no article yet): {matched_no_article}")
    print(f"   ⏰ Missed (days cutoff too low): {missed_days}")
    print(f"   🔍 Missed (filter - no critical keywords): {missed_filter}")
    print(f"   ❌ No articles (Yahoo Finance): {no_articles}")
    print(f"\n   📈 Total with potential: {matched + missed_days}/{len(symbols)} ({100*(matched+missed_days)/len(symbols):.0f}%)")

def test_stocks():
    """Test specific stocks for available news"""
    print("\nEnter stock symbols (one per line, press Enter twice when done):\n")
    symbols = []
    while True:
        symbol = input().strip().upper()
        if not symbol:
            break
        symbols.append(symbol)
    
    matched = 0
    matched_no_article = 0
    missed_days = 0
    missed_filter = 0
    no_articles = 0
    
    for symbol in symbols:
        page_articles, article_date = count_articles_in_page(symbol)
        article_text = f" (stocks/{symbol}.html has {page_articles} article{'s' if page_articles != 1 else ''})"
        if page_articles == 1 and article_date:
            article_text += f" - {article_date}"
        print(f"\n{'='*60}")
        print(f"📊 {symbol}{article_text}")
        print(f"{'='*60}")
        
        articles = get_news(symbol)
        
        if not articles:
            print("❌ No articles found")
            no_articles += 1
            continue
        
        has_critical_recent = False
        has_old_critical = False
        
        for i, article in enumerate(articles, 1):
            status = "✅" if (article['critical'] and article['recent']) else "⚠️ " if article['critical'] else "❌"
            if article['critical'] and article['recent']:
                has_critical_recent = True
            elif article['critical'] and not article['recent']:
                has_old_critical = True
            
            print(f"\n{i}. {status} {article['title'][:70]}")
            print(f"   Date: {article['date']}")
            print(f"   Critical: {article['critical']} | Recent ({days_cutoff}d): {article['recent']}")
        
        if has_critical_recent:
            matched += 1
            if page_articles == 0:
                matched_no_article += 1
        elif has_old_critical:
            missed_days += 1
        else:
            missed_filter += 1
    
    print(f"\n\n📊 Summary:")
    print(f"   ✅ Matched (ready now): {matched}/{len(symbols)}")
    print(f"   ✨ Matched (no article yet): {matched_no_article}")
    print(f"   ⏰ Missed (days cutoff too low): {missed_days}")
    print(f"   🔍 Missed (filter - no critical keywords): {missed_filter}")
    print(f"   ❌ No articles (Yahoo Finance): {no_articles}")
    print(f"\n   📈 Total with potential: {matched + missed_days}/{len(symbols)} ({100*(matched+missed_days)/len(symbols):.0f}%)")

def set_days():
    """Set days cutoff for recent articles"""
    global days_cutoff
    try:
        days = int(input(f"\nEnter days cutoff (current: {days_cutoff}): ").strip())
        if days > 0:
            days_cutoff = days
            config['days_cutoff'] = days_cutoff
            save_config(config)
            print(f"✅ Days cutoff set to {days_cutoff}")
        else:
            print("❌ Must be greater than 0")
    except ValueError:
        print("❌ Invalid number")

def set_articles():
    """Set number of articles to search"""
    global articles_limit
    try:
        limit = int(input(f"\nEnter article limit (current: {articles_limit}): ").strip())
        if limit > 0:
            articles_limit = limit
            config['articles_limit'] = articles_limit
            save_config(config)
            print(f"✅ Article limit set to {articles_limit}")
        else:
            print("❌ Must be greater than 0")
    except ValueError:
        print("❌ Invalid number")

def scan_all_stocks():
    """Scan all stocks and save those with no articles to file"""
    stock_files = sorted([f.replace('.html', '') for f in os.listdir(STOCKS_DIR) if f.endswith('.html')])
    no_articles_list = []
    
    print(f"\n🔍 Scanning {len(stock_files)} stocks...\n")
    
    for i, symbol in enumerate(stock_files, 1):
        if i % 100 == 0:
            print(f"   Progress: {i}/{len(stock_files)}")
        
        articles = get_news(symbol)
        if not articles:
            no_articles_list.append(symbol)
    
    # Save to file
    output_file = 'stocks_no_articles.txt'
    with open(output_file, 'w') as f:
        for symbol in no_articles_list:
            f.write(f"{symbol}\n")
    
    print(f"\n✅ Scan complete!")
    print(f"   Total stocks: {len(stock_files)}")
    print(f"   No articles: {len(no_articles_list)} ({100*len(no_articles_list)/len(stock_files):.1f}%)")
    print(f"   Saved to: {output_file}")

while True:
    print("\n📰 Test Stock RSS\n")
    print("1. Test random stocks")
    print("2. Test specific stocks")
    print(f"3. Set days cutoff (current: {days_cutoff})")
    print(f"4. Set article limit (current: {articles_limit})")
    print("5. Debug: Show all API articles for a stock")
    print("6. Scan all stocks (save no-articles list)")
    print("7. Exit\n")
    
    choice = input("Select option (1-7): ").strip()
    
    if choice == "1":
        test_random_stocks()
    elif choice == "2":
        test_stocks()
    elif choice == "3":
        set_days()
    elif choice == "4":
        set_articles()
    elif choice == "5":
        symbol = input("\nEnter stock symbol: ").strip().upper()
        articles = get_news(symbol, show_all=True)
        if articles:
            print(f"\n📊 All {len(articles)} articles from API for {symbol}:")
            for i, article in enumerate(articles, 1):
                match = "✅" if article['is_match'] else "❌"
                print(f"\n{i}. {match} {article['title'][:70]}")
                print(f"   Date: {article['date']}")
                print(f"   Matches stock: {article['is_match']}")
        else:
            print(f"\n❌ No articles found for {symbol}")
    elif choice == "6":
        scan_all_stocks()
    elif choice == "7":
        break
    else:
        print("Invalid option")
