#!/usr/bin/env python3
"""
Recovery tool: syncs news from stock HTML pages into news.html.

Scans all stock pages for news sections (<!-- NEWS_SECTION_START/END -->), extracts
headlines and summaries, removes stale entries from news.html, and inserts current ones
sorted by timestamp. Use this when news.html is out of sync with stock pages.

Run after: any manual edits to stock pages, or when check_news_sync.py reports mismatches.

Usage:
    python3 Sync_stock_to_news.py
"""

import os
import re
from datetime import datetime

STOCKS_DIR = '/Users/ddewit/VSCODE/website/stocks'
NEWS_HTML_PATH = '/Users/ddewit/VSCODE/website/news.html'

# Read news.html
with open(NEWS_HTML_PATH, 'r') as f:
    news_html = f.read()

# Get symbols already in blog
existing_symbols = set(re.findall(r'Category: ([A-Z0-9.]+) Stock News', news_html))
general_news_count = len(re.findall(r'Category: Market News', news_html))
print(f"📊 News currently has {len(existing_symbols)} stock articles + {general_news_count} general news = {len(existing_symbols) + general_news_count} total")

# Extract summaries from stock pages
summaries = {}
for filename in os.listdir(STOCKS_DIR):
    if not filename.endswith('.html'):
        continue
    
    symbol = filename.replace('.html', '')
    filepath = os.path.join(STOCKS_DIR, filename)
    with open(filepath, 'r') as f:
        content = f.read()
    
    news_match = re.search(r'<!-- NEWS_SECTION_START -->(.*?)<!-- NEWS_SECTION_END -->', content, re.DOTALL)
    if not news_match or not news_match.group(1).strip():
        continue
    
    news_section = news_match.group(1).strip()
    headline_match = re.search(r'<strong>([^<]+)</strong>', news_section)
    date_match = re.search(r'<p[^>]*data-timestamp="([^"]+)"[^>]*class="article-date"[^>]*>([^<]+)</p>', news_section)
    
    if date_match:
        full_date_text = date_match.group(2)
        simple_date = full_date_text
        timestamp = date_match.group(1)
    else:
        simple_date = None
        timestamp = None
    
    paragraphs = re.findall(r'<p[^>]*>([^<]+)</p>', news_section)
    summary = ''
    for p in paragraphs:
        if 'Read full article' in p or len(p) < 50:
            continue
        summary = p
        break
    
    url_match = re.search(r'<a href="([^"]+)"[^>]*>Read full article', news_section)
    
    if headline_match and summary:
        if not simple_date:
            simple_date = datetime.utcnow().strftime('%a, %B %d, %Y')
        if not timestamp:
            timestamp = datetime.utcnow().isoformat() + 'Z'
        summaries[symbol] = {
            'headline': headline_match.group(1).strip(),
            'summary': summary.strip(),
            'url': url_match.group(1) if url_match else '',
            'date': simple_date,
            'timestamp': timestamp
        }

print(f"🔍 Found {len(summaries)} stock pages with complete news (headline + summary)")

# Remove old articles for stocks that have new news
removed = 0
for symbol in summaries.keys():
    if symbol in existing_symbols:
        pattern = rf'<article class="blog-post" id="{re.escape(symbol.lower())}-stock-news">.*?</article>'
        match = re.search(pattern, news_html, re.DOTALL | re.IGNORECASE)
        if match:
            news_html = news_html[:match.start()] + news_html[match.end():]
            removed += 1
            existing_symbols.remove(symbol)

if removed > 0:
    print(f"🗑️  Removed {removed} old articles (will be replaced with current news)")

# Add new/updated articles
new_articles = []
for symbol, data in summaries.items():
    full_summary = data['summary']
    words = full_summary.split()
    truncate_at = int(len(words) * 0.6)
    preview = ' '.join(words[:truncate_at]) + '...' if len(words) > truncate_at else full_summary
    
    new_articles.append(f'''            <article class="blog-post" id="{symbol.lower()}-stock-news">
                <h2 style="margin: 0;"><a href="stocks/{symbol}.html" style="color: inherit; text-decoration: none; display: inline-block; width: 100%; padding: 0 0 10px 0;">📰 {data['headline']}</a></h2>
                <div class="blog-meta"><span data-timestamp="{data['timestamp']}" class="article-date">Published: {data['date']}</span> | Category: {symbol} Stock News</div>
                <div class="blog-excerpt">
                    <p>{preview}</p>
                    <p><a href="{data['url']}" target="_blank" style="color: #007bff;">Read full article →</a> | <a href="analysis.html?symbol={symbol}&option=1&subOption=custom" style="color: #007bff;">Analyze {symbol} Stock →</a></p>
                </div>
            </article>
''')

if new_articles:
    articles = re.findall(r'<article class="blog-post"[^>]*>.*?</article>', news_html, re.DOTALL)
    
    from datetime import datetime, timezone
    def parse_timestamp(article_html):
        timestamp_match = re.search(r'data-timestamp="([^"]+)"', article_html)
        if timestamp_match:
            try:
                ts = timestamp_match.group(1)
                if ts.endswith('Z'):
                    ts = ts[:-1] + '+00:00'
                return datetime.fromisoformat(ts)
            except:
                pass
        return datetime.min.replace(tzinfo=timezone.utc)
    
    new_articles_sorted = sorted(new_articles, key=parse_timestamp, reverse=True)
    articles_sorted = sorted(articles, key=parse_timestamp, reverse=True)
    all_articles = sorted(new_articles_sorted + articles_sorted, key=parse_timestamp, reverse=True)
    
    content_start = news_html.find('<div class="blog-content">')
    before = news_html[:content_start + len('<div class="blog-content">')]
    after_match = re.search(r'</div>\s*<div style="text-align: center', news_html)
    if not after_match:
        after_match = re.search(r'</div>\s*<footer', news_html)
    
    if after_match:
        after = news_html[after_match.start():]
        article_count = len(all_articles)
        after = re.sub(r'<span id="article-count">[0-9]+</span>', f'<span id="article-count">{article_count}</span>', after)
        
        news_html = before + '\n' + '\n'.join(all_articles) + '        ' + after
        print(f"✅ Added {len(new_articles)} current stock articles")
        
        with open(NEWS_HTML_PATH, 'w') as f:
            f.write(news_html)
        print(f"✅ Wrote changes to news.html")
    else:
        print("⚠️  Could not find end marker, skipping write")
else:
    print("⚠️  No articles to add")

general_news_count = len(re.findall(r'Category: Market News', news_html))
total_articles = len(summaries) + general_news_count
print(f"📊 News now has {len(summaries)} stock articles + {general_news_count} general news = {total_articles} total")
