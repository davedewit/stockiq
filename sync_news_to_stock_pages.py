#!/usr/bin/env python3
"""
Reverse sync: pushes news from news.html back to stock pages.

Fixes cases where news.html has a stock article but the stock page itself is missing
the news section. Opposite direction to Sync_stock_to_news.py.

Prompts for a specific symbol or syncs all missing pages at once.

Usage:
    python3 sync_news_to_stock_pages.py
"""

import os
import re
from datetime import datetime, timedelta

STOCKS_DIR = '/Users/ddewit/VSCODE/website/stocks'
NEWS_HTML_PATH = '/Users/ddewit/VSCODE/website/news.html'

def extract_news_articles():
    """Extract stock news articles from news.html"""
    with open(NEWS_HTML_PATH, 'r') as f:
        html = f.read()
    
    articles = {}
    pattern = r'<article class="blog-post"[^>]*>.*?Category: ([A-Z]+) Stock News.*?<p>([^<]+)</p>.*?<a href="([^"]+)"[^>]*>Read full article →</a>'
    
    for match in re.finditer(pattern, html, re.DOTALL):
        symbol = match.group(1)
        summary = match.group(2).strip()
        link = match.group(3)
        
        # Extract title
        title_match = re.search(r'<h2>📰 ([^<]+)</h2>', match.group(0))
        title = title_match.group(1) if title_match else ''
        
        # Extract timestamp and date
        date_match = re.search(r'<span data-timestamp="([^"]+)" class="article-date">Published: ([^<]+)</span>', match.group(0))
        timestamp = date_match.group(1) if date_match else ''
        date_str = date_match.group(2) if date_match else ''
        
        articles[symbol] = {
            'title': title,
            'summary': summary,
            'link': link,
            'timestamp': timestamp,
            'date': date_str
        }
    
    return articles

def update_stock_page(symbol, article):
    """Update stock page with news from news.html"""
    file_path = os.path.join(STOCKS_DIR, f"{symbol}.html")
    
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already has news
    if '<!-- NEWS_SECTION_START -->' in content and '<!-- NEWS_SECTION_END -->' in content:
        match = re.search(r'<!-- NEWS_SECTION_START -->(.*?)<!-- NEWS_SECTION_END -->', content, re.DOTALL)
        if match and match.group(1).strip():
            return False  # Already has news
    
    # Create news HTML with timestamp
    news_html = f"""<div style="background: var(--bg-secondary); border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <h3 style="margin-top: 0; color: var(--text-primary);">📰 Latest Update</h3>
            <p style="margin: 10px 0; color: var(--text-primary);"><strong>{article['title']}</strong></p>
            <p style="margin: 5px 0; font-size: 0.85em; color: var(--text-secondary);" data-timestamp="{article['timestamp']}" class="article-date">{article['date']}</p>
            <p style="margin: 10px 0; color: var(--text-secondary);">{article['summary']}</p>
            <p style="margin: 10px 0 0 0; font-size: 0.9em; color: var(--text-secondary);">
                <a href="{article['link']}" target="_blank" style="color: #007bff;">Read full article →</a>
            </p>
        </div>"""
    
    # Insert news section
    news_section = f"""
        <!-- NEWS_SECTION_START -->
        {news_html}
        <!-- NEWS_SECTION_END -->
"""
    
    # Find insertion point - after CTA section, before features grid
    pattern = r'(</div>\s*<!-- NEWS_SECTION_START -->)'
    if re.search(pattern, content):
        # Markers exist but empty
        content = re.sub(
            r'<!-- NEWS_SECTION_START -->\s*<!-- NEWS_SECTION_END -->',
            news_section.strip(),
            content
        )
    else:
        # Insert before features grid
        pattern = r'(<div style="display: grid; grid-template-columns: repeat\(auto-fit, minmax\(300px, 1fr\)\);)'
        content = re.sub(pattern, f'{news_section}\\1', content, count=1)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    return True

def main():
    print("🔍 Extracting articles from news.html...")
    articles = extract_news_articles()
    print(f"   Found {len(articles)} stock articles\n")
    
    # Ask for specific symbol or sync all
    symbol_input = input("Enter stock symbol to sync (or press Enter to sync all): ").strip().upper().replace('.HTML', '')
    
    synced = 0
    if symbol_input:
        if symbol_input in articles:
            if update_stock_page(symbol_input, articles[symbol_input]):
                print(f"✅ Synced {symbol_input}.html")
                synced = 1
            else:
                print(f"⏭️  {symbol_input}.html already has news")
        else:
            print(f"❌ No news found for {symbol_input}")
    else:
        for symbol, article in articles.items():
            if update_stock_page(symbol, article):
                print(f"✅ Synced {symbol}.html")
                synced += 1
    
    print(f"\n✅ Synced {synced} stock pages")

if __name__ == '__main__':
    main()
