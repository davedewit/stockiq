#!/usr/bin/env python3
"""
Nuclear reset: clears ALL stock news from every file.

Removes news sections from all 3,467 stock HTML pages, deletes the news cache,
resets news.js to empty, and removes all articles from news.html.

Use this to start completely fresh (e.g. after a bad batch update).
After running, repopulate with: python3 update_stock_news.py

Usage:
    python3 clear_stock_news.py
"""

import os
import re

STOCKS_DIR = '/Users/ddewit/VSCODE/website/stocks'
NEWS_CACHE_FILE = '/Users/ddewit/VSCODE/website/.stock_news_cache.json'
NEWS_JS_PATH = '/Users/ddewit/VSCODE/website/news.js'
NEWS_HTML_PATH = '/Users/ddewit/VSCODE/website/news.html'

def clear_stock_pages():
    """Remove news sections from all stock HTML files"""
    cleared = 0
    for filename in os.listdir(STOCKS_DIR):
        if filename.endswith('.html'):
            filepath = os.path.join(STOCKS_DIR, filename)
            with open(filepath, 'r') as f:
                content = f.read()
            
            new_content = re.sub(
                r'<!-- NEWS_SECTION_START -->.*?<!-- NEWS_SECTION_END -->',
                '',
                content,
                flags=re.DOTALL
            )
            
            if new_content != content:
                with open(filepath, 'w') as f:
                    f.write(new_content)
                cleared += 1
    
    print(f"✅ Cleared news from {cleared} stock pages")

def clear_cache():
    """Remove news cache file"""
    if os.path.exists(NEWS_CACHE_FILE):
        os.remove(NEWS_CACHE_FILE)
        print(f"✅ Cleared cache file")
    else:
        print(f"⚪ No cache file to clear")

def clear_news_js():
    """Clear news.js and reset to empty"""
    template = """const newsItems = [];

// Render news items into the sidebar
function renderNewsItems() {
    const container = document.getElementById('news-items');
    if (!container) return;
    
    const displayItems = newsItems.slice(0, 4);
    
    container.innerHTML = displayItems.map(item => {
        const url = item.stockSymbol ? `stocks/${item.stockSymbol}.html` : `news.html#${item.id}`;
        return `
        <div class="news-item" style="padding: 8px; margin-bottom: 8px; border-bottom: 1px solid var(--border-color); cursor: pointer;" onclick="window.location.href='${url}'">
            <div style="font-weight: 600; color: var(--text-primary); font-size: 0.85rem; margin-bottom: 3px;">${item.emoji} ${item.title}</div>
            <div style="color: var(--text-secondary); font-size: 0.7rem; margin-bottom: 2px;">${item.date}</div>
            <div style="color: var(--text-secondary); font-size: 0.75rem; line-height: 1.3;">${item.preview}</div>
        </div>
        `;
    }).join('');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderNewsItems);
} else {
    renderNewsItems();
}
"""
    with open(NEWS_JS_PATH, 'w') as f:
        f.write(template)
    print(f"✅ Cleared news.js")

def clear_news_html():
    """Remove all articles from news.html"""
    with open(NEWS_HTML_PATH, 'r') as f:
        content = f.read()
    
    new_content = re.sub(
        r'<article class="blog-post".*?</article>',
        '',
        content,
        flags=re.DOTALL
    )
    
    with open(NEWS_HTML_PATH, 'w') as f:
        f.write(new_content)
    print(f"✅ Cleared news.html")

if __name__ == '__main__':
    print("🧹 Clearing all stock news...\n")
    clear_stock_pages()
    clear_cache()
    clear_news_js()
    clear_news_html()
    print("\n✅ All stock news cleared! Run update_stock_news.py to populate with fresh news.")
