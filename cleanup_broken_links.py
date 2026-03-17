#!/usr/bin/env python3
"""
Clean up news.html: remove broken links and orphaned stock articles.

Does two things:
1. Removes empty href="" article links (broken source URLs)
2. Removes stock articles from news.html where the stock page no longer has news

Called automatically during deployment via deploy-to-s3.sh.

Usage:
    python3 cleanup_broken_links.py
"""
import re
from pathlib import Path

NEWS_HTML_PATH = Path('/Users/ddewit/VSCODE/website/news.html')
STOCKS_DIR = Path('/Users/ddewit/VSCODE/website/stocks')

def cleanup_broken_links():
    """Remove broken article links with empty hrefs"""
    try:
        content = NEWS_HTML_PATH.read_text()
        original_content = content
        
        # Remove " | Read full article →" when href is empty
        content = content.replace(' | <a href="" target="_blank" style="color: #007bff;">Read full article →</a>', '')
        
        if content != original_content:
            NEWS_HTML_PATH.write_text(content)
            print("✅ Cleaned up broken article links in news.html")
            return True
        else:
            print("✓ No broken links found in news.html")
            return False
    
    except Exception as e:
        print(f"⚠️  Error cleaning up broken links: {e}")
        return False

def remove_orphaned_articles():
    """Remove articles from news.html where stock page no longer has news"""
    try:
        content = NEWS_HTML_PATH.read_text()
        
        # Get stock symbols with news from stock pages
        stock_symbols_with_news = set()
        for page in STOCKS_DIR.glob('*.html'):
            page_content = page.read_text()
            if '<div style="background: var(--bg-secondary); border-left: 4px solid #ffc107' in page_content:
                stock_symbols_with_news.add(page.stem)
        
        # Find stock-specific articles in news.html
        articles = re.findall(r'<article class="blog-post"[^>]*>.*?</article>', content, re.DOTALL)
        orphaned = []
        
        for article in articles:
            # Skip general market news
            if 'Category: Market News' in article:
                continue
            
            # Extract stock symbol from category
            match = re.search(r'Category: ([A-Z0-9.]+) Stock News', article)
            if match:
                symbol = match.group(1)
                if symbol not in stock_symbols_with_news:
                    orphaned.append((symbol, article))
        
        if orphaned:
            for symbol, article in orphaned:
                content = content.replace(article, '')
            
            NEWS_HTML_PATH.write_text(content)
            print(f"✅ Removed {len(orphaned)} orphaned articles from news.html")
            print(f"   Symbols: {', '.join(s for s, _ in orphaned)}")
            return True
        else:
            print("✓ No orphaned articles found in news.html")
            return False
    
    except Exception as e:
        print(f"⚠️  Error removing orphaned articles: {e}")
        return False

if __name__ == '__main__':
    print("🧹 Cleaning up news.html...\n")
    cleaned_links = cleanup_broken_links()
    cleaned_orphans = remove_orphaned_articles()
    
    if cleaned_links or cleaned_orphans:
        print("\n✅ Cleanup complete!")
    else:
        print("\n✅ No cleanup needed - news.html is clean!")
