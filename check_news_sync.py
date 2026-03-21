#!/usr/bin/env python3

"""
StockIQ News Sync Diagnostic Tool.

Checks if stock pages, news.html, and news.js are in sync and reports:
- Stock page news coverage (total, by article count)
- news.html article counts (stock vs general)
- news.js sidebar item counts (80 stock + 20 general limit)
- Broken links, missing articles, orphaned entries, sort order

Tracks changes between runs (saves stats every 23+ hours to .news_stats_history.json).
Prints actionable fix commands when issues are detected.

Usage:
    python3 check_news_sync.py
"""
import re
from pathlib import Path
import sys
import json
from datetime import datetime, timedelta
import os

# Website directory
website_dir = Path.home() / 'VSCODE' / 'website'

if not website_dir.exists():
    print("❌ Could not find website directory at:", website_dir)
    sys.exit(1)

# Change to website directory
os.chdir(website_dir)

STATS_FILE = ".news_stats_history.json"

def load_history():
    """Load previous statistics"""
    if Path(STATS_FILE).exists():
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else None
    return None

def should_save_history(previous):
    """Check if 23+ hours have passed since last save"""
    if previous is None:
        return True
    
    try:
        last_timestamp = datetime.fromisoformat(previous["timestamp"])
        current_time = datetime.now()
        time_diff = current_time - last_timestamp
        return time_diff >= timedelta(hours=23)
    except:
        return True

def save_history(current_stats):
    """Save statistics history (only keep last run)"""
    with open(STATS_FILE, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "stock_pages": current_stats["stock_pages"],
            "news_html": current_stats["news_html"]
        }, f, indent=2)

def format_change(current, previous):
    """Format change as +X or -X"""
    if previous is None:
        return ""
    change = current - previous
    if change > 0:
        return f" +{change}"
    elif change < 0:
        return f" {change}"
    return ""

def format_percentage_change(current, previous):
    """Format percentage change as +X% or -X%"""
    if previous is None:
        return ""
    change = current - previous
    if change > 0:
        return f" +{change}%"
    elif change < 0:
        return f" {change}%"
    return ""

print("🔍 StockIQ News Sync Diagnostic\n")

# Check required files exist
if not Path('news.js').exists():
    print("❌ news.js not found!")
    sys.exit(1)
if not Path('news.html').exists():
    print("❌ news.html not found!")
    sys.exit(1)
if not Path('stocks').exists():
    print("❌ stocks/ directory not found!")
    sys.exit(1)

# Check news.js sidebar (100 item limit: 80 stock + 20 general)
news_js = Path('news.js').read_text()
stock_items = news_js.count("stockSymbol: '") - news_js.count("stockSymbol: ''")
general_items = news_js.count("stockSymbol: ''")
total_items = stock_items + general_items

print(f"📱 News.js (Homepage Sidebar):")
print(f"   Stock items: {stock_items}/80")
print(f"   General items: {general_items}/20")
print(f"   Total: {total_items}/100")
if total_items > 100:
    print(f"   ⚠️  OVER LIMIT by {total_items - 100} items!")
print()

# Count stock pages
stock_pages = list(Path('stocks').glob('*.html'))
total_stock_pages = len(stock_pages)

# Count stock pages with news and count articles per page
stock_with_news = 0
stock_symbols_with_news = set()
stocks_with_1_article = 0
stocks_with_2_articles = 0
stocks_with_3_articles = 0
total_articles_in_stock_pages = 0
example_1_article = None
example_2_articles = None
example_3_articles = None

for page in stock_pages:
    content = page.read_text()
    if '<div style="background: var(--bg-secondary); border-left: 4px solid #ffc107' in content:
        stock_with_news += 1
        stock_symbols_with_news.add(page.stem)
        
        # Count articles in this stock page
        news_section = re.search(r'<!-- NEWS_SECTION_START -->(.*?)<!-- NEWS_SECTION_END -->', content, re.DOTALL)
        if news_section:
            section_content = news_section.group(1)
            # Count articles: main article + collapsed articles
            # Main article is always present if news section exists
            article_count = 1
            # Count collapsed articles within the news section only
            collapsed_count = section_content.count('<div id="older-news-')
            article_count += collapsed_count
            total_articles_in_stock_pages += article_count
            
            if article_count == 1:
                stocks_with_1_article += 1
                if not example_1_article:
                    example_1_article = page.stem
            elif article_count == 2:
                stocks_with_2_articles += 1
                if not example_2_articles:
                    example_2_articles = page.stem
            elif article_count >= 3:
                stocks_with_3_articles += 1
                if not example_3_articles:
                    example_3_articles = page.stem

# Count articles in news.html
news_html = Path('news.html').read_text()
total_articles = news_html.count('<article class="blog-post"')
general_news = news_html.count('Category: Market News')
stock_articles = total_articles - general_news

# Get stock symbols in news.html (both stock-specific and general market articles)
stock_symbols_in_news = set()
# Stock-specific articles
for match in re.finditer(r'Category: ([A-Z0-9.]+) Stock News', news_html):
    stock_symbols_in_news.add(match.group(1))
# General market articles that mention stocks (e.g., "Getty Images (GETY)")
for match in re.finditer(r'\b([A-Z]{2,5})\b(?=\))', news_html):
    symbol = match.group(1)
    # Only count if it's a valid stock symbol we have (filters out words like NEWS, STOCK)
    if symbol in stock_symbols_with_news:
        stock_symbols_in_news.add(symbol)

# Find mismatches
missing_from_news = stock_symbols_with_news - stock_symbols_in_news
extra_in_news = stock_symbols_in_news - stock_symbols_with_news

# Load history for comparison
previous = load_history()

# Prepare current stats for saving
current_stats = {
    "stock_pages": {
        "total": total_stock_pages,
        "with_news": stock_with_news,
        "percentage": round((stock_with_news / total_stock_pages * 100), 1) if total_stock_pages > 0 else 0,
        "by_article_count": {
            "1_article": stocks_with_1_article,
            "2_articles": stocks_with_2_articles,
            "3_articles": stocks_with_3_articles
        },
        "total_articles": total_articles_in_stock_pages
    },
    "news_html": {
        "stock_articles": stock_articles,
        "general_news": general_news,
        "total_articles": total_articles
    }
}

# Only save to history if 23+ hours have passed
if should_save_history(previous):
    save_history(current_stats)

# Display results with changes
print(f"📊 Stock Pages:")
print(f"   Total: {total_stock_pages}")

prev_with_news = previous["stock_pages"]["with_news"] if previous else None
change = format_change(stock_with_news, prev_with_news)
coverage = current_stats["stock_pages"]["percentage"]
prev_coverage = previous["stock_pages"]["percentage"] if previous else None
coverage_change = format_percentage_change(coverage, prev_coverage)

print(f"   With news: {stock_with_news} ({coverage}%){change}{coverage_change}")

# Article breakdown
prev_by_count = previous["stock_pages"]["by_article_count"] if previous else None
print(f"   - 1 article: {stocks_with_1_article} pages{format_change(stocks_with_1_article, prev_by_count['1_article'] if prev_by_count else None)} (e.g. {example_1_article})")
print(f"   - 2 articles: {stocks_with_2_articles} pages{format_change(stocks_with_2_articles, prev_by_count['2_articles'] if prev_by_count else None)} (e.g. {example_2_articles})")
print(f"   - 3 articles: {stocks_with_3_articles} pages{format_change(stocks_with_3_articles, prev_by_count['3_articles'] if prev_by_count else None)} (e.g. {example_3_articles})")

prev_total_articles = previous["stock_pages"]["total_articles"] if previous else None
print(f"   Total articles: {total_articles_in_stock_pages}{format_change(total_articles_in_stock_pages, prev_total_articles)}")
print()

print(f"📰 News.html:")
prev_stock_articles = previous["news_html"]["stock_articles"] if previous else None
prev_general_news = previous["news_html"]["general_news"] if previous else None
prev_total_news = previous["news_html"]["total_articles"] if previous else None

print(f"   Stock articles: {stock_articles}{format_change(stock_articles, prev_stock_articles)}")
print(f"   General news: {general_news}{format_change(general_news, prev_general_news)}")
print(f"   Total articles: {total_articles}{format_change(total_articles, prev_total_news)}")
print()

# Check for issues and provide advice
issues = []
malformed_articles = []
old_articles_no_timestamp = []
duplicate_articles = []

# Check for malformed news (missing date/timestamp or empty links) in stock pages
broken_links = []
for page in stock_pages:
    if page.stem not in stock_symbols_with_news:
        continue
    content = page.read_text()
    news_match = re.search(r'<!-- NEWS_SECTION_START -->(.*?)<!-- NEWS_SECTION_END -->', content, re.DOTALL)
    if news_match and news_match.group(1).strip():
        news_section = news_match.group(1)
        has_timestamp = 'data-timestamp=' in news_section
        has_empty_link = 'href=""' in news_section or 'href="" ' in news_section
        
        if not has_timestamp:
            old_articles_no_timestamp.append(page.stem)
            malformed_articles.append(page.stem)
        if has_empty_link:
            broken_links.append(f"{page.stem} (stock page)")
            malformed_articles.append(page.stem)

# Check for broken links in news.html
empty_links_in_news = re.findall(r'<article[^>]*id="([^"]+)"[^>]*>.*?href=""', news_html, re.DOTALL)
for article_id in empty_links_in_news:
    broken_links.append(f"{article_id} (news.html)")
    malformed_articles.append(article_id)

if malformed_articles:
    issues.append("malformed_news")

# Check if news.html is sorted by timestamp
timestamps = re.findall(r'data-timestamp="([^"]+)"', news_html)
if len(timestamps) > 1:
    from datetime import datetime, timezone
    parsed_timestamps = []
    for ts in timestamps:
        try:
            if ts.endswith('Z'):
                ts = ts[:-1] + '+00:00'
            parsed_timestamps.append(datetime.fromisoformat(ts))
        except:
            parsed_timestamps.append(datetime.min.replace(tzinfo=timezone.utc))
    
    # Check if sorted (newest first)
    is_sorted = all(parsed_timestamps[i] >= parsed_timestamps[i+1] for i in range(len(parsed_timestamps)-1))
    if not is_sorted:
        issues.append("news_not_sorted")

# Stock pages can have max 3 articles per symbol, but news.html can accumulate more
# Only flag as mismatch if stock_with_news > stock_articles (stock pages have news but not in news.html)
if stock_with_news > stock_articles:
    issues.append("sync_mismatch")
    
if missing_from_news:
    issues.append("missing_from_news")
    
if extra_in_news:
    issues.append("extra_in_news")

if total_items > 100:
    issues.append("newsjs_over_limit")

if stock_items > 80:
    issues.append("newsjs_stock_over_limit")

if general_items > 20:
    issues.append("newsjs_general_over_limit")

if not issues:
    print("\n✅ PERFECT: Everything is in sync!")
    print(f"✅ Checked {total_stock_pages} stock pages and news.html - no broken links found")
    print()
    print("📈 Coverage: {:.1f}% of stock pages have news".format(stock_with_news / total_stock_pages * 100))
elif stock_with_news == stock_articles and not extra_in_news and total_items <= 100 and not broken_links:
    print("\n✅ FRESH PERFECT SYNC (first articles only)")
    print(f"   Stock pages with news: {stock_with_news}")
    print(f"   Stock articles in news.html: {stock_articles}")
    print(f"✅ Checked {total_stock_pages} stock pages and news.html - no broken links found")
    print()
    if old_articles_no_timestamp:
        print(f"ℹ️  {len(old_articles_no_timestamp)} stock pages have old articles without timestamps")
        print(f"   (will be replaced with timestamped versions on next article update)")
    if len(missing_from_news) > 0:
        print(f"ℹ️  {len(missing_from_news)} stock pages have general market news not yet in news.html")
        if len(missing_from_news) <= 10:
            print(f"   Symbols: {', '.join(sorted(missing_from_news))}")
    print()
    print("📈 Coverage: {:.1f}% of stock pages have news".format(stock_with_news / total_stock_pages * 100))
elif len(missing_from_news) <= 5 and not extra_in_news and total_items <= 100 and not broken_links:
    print("\n✅ MOSTLY IN SYNC (news.html has accumulated articles)")
    print(f"   Stock pages with news: {stock_with_news}")
    print(f"   Stock articles in news.html: {stock_articles}")
    print(f"   Total articles in stock pages: {total_articles_in_stock_pages} (includes 2nd/3rd articles)")
    print(f"✅ Checked {total_stock_pages} stock pages and news.html - no broken links found")
    print()
    if old_articles_no_timestamp:
        print(f"ℹ️  {len(old_articles_no_timestamp)} stock pages have old articles without timestamps")
        print(f"   (will be replaced with timestamped versions on next article update)")
    if len(missing_from_news) > 0:
        print(f"ℹ️  {len(missing_from_news)} stock pages have general market news not yet in news.html")
        if len(missing_from_news) <= 10:
            print(f"   Symbols: {', '.join(sorted(missing_from_news))}")
    print()
    print("📈 Coverage: {:.1f}% of stock pages have news".format(stock_with_news / total_stock_pages * 100))
else:
    print("\n⚠️  ISSUES DETECTED\n")
    
    if "malformed_news" in issues:
        if old_articles_no_timestamp:
            print(f"ℹ️  {len(old_articles_no_timestamp)} stock pages have old articles without timestamps")
            print(f"   (will be replaced with timestamped versions on next article update)")
        if broken_links:
            print(f"❌ {len(broken_links)} articles have broken links (href=\"\")")
            if len(broken_links) <= 10:
                for item in sorted(broken_links):
                    print(f"   • {item}")
        else:
            print(f"✅ Checked {total_stock_pages} stock pages and news.html - no broken links found")
        print()
    
    if "news_not_sorted" in issues:
        print(f"❌ News.html is NOT sorted by timestamp (newest first)")
        print(f"   Articles are out of order - run Sync_stock_to_news.py to fix")
        print()
    
    if "sync_mismatch" in issues:
        diff = stock_with_news - stock_articles
        print(f"❌ Sync Mismatch: {abs(diff)} articles {'missing from' if diff > 0 else 'extra in'} news.html")
        print()
    
    if missing_from_news:
        print(f"❌ Missing from news.html: {len(missing_from_news)} articles")
        if len(missing_from_news) <= 10:
            print(f"   Symbols: {', '.join(sorted(missing_from_news))}")
        print()
    
    if extra_in_news:
        print(f"❌ Extra in news.html: {len(extra_in_news)} articles (stock pages don't have news)")
        if len(extra_in_news) <= 10:
            print(f"   Symbols: {', '.join(sorted(extra_in_news))}")
        print()
    
    if "newsjs_over_limit" in issues or "newsjs_general_over_limit" in issues:
        if total_items > 100:
            print(f"❌ News.js over 100 item limit: {total_items} items")
        if stock_items > 80:
            print(f"❌ Stock items: {stock_items}/80 (over by {stock_items - 80})")
        if general_items > 20:
            print(f"❌ General items: {general_items}/20 (over by {general_items - 20})")
        print()
    
    print("🔧 HOW TO FIX:\n")
    
    if "news_not_sorted" in issues:
        print("1. Sort news.html by timestamp:")
        print("   python3 Sync_stock_to_news.py")
        print()
    
    if missing_from_news or "sync_mismatch" in issues:
        print("1. Sync stock pages → news.html:")
        print("   python3 Sync_stock_to_news.py")
        print()
    
    if extra_in_news:
        print("2. Remove orphaned articles from news.html:")
        print("   python3 cleanup_broken_links.py")
        print()
    
    if "newsjs_over_limit" in issues or "newsjs_general_over_limit" in issues or "newsjs_stock_over_limit" in issues:
        print("3. Fix news.js limits:")
        if general_items > 20:
            print("   python3 update_news.py        # Will trim to 20 general items")
        if stock_items > 80:
            print("   python3 update_stock_news.py  # Will trim to 80 stock items")
        print()
    
    print("4. Verify fix:")
    print("   python3 check_news_sync.py")
    print()
    print("5. Deploy changes:")
    print("   ./deploy-to-s3.sh")
