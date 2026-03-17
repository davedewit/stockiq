#!/usr/bin/env python3
"""Remove duplicate stock articles from news.html, keeping only the first occurrence per symbol.

Usage:
    python3 remove_news_duplicates.py
"""
import re
from pathlib import Path
import os

# Change to website directory
website_dir = Path('/Users/ddewit/VSCODE/website')
os.chdir(website_dir)

news_html_path = Path('news.html')
content = news_html_path.read_text()

# Find all articles
articles = re.findall(r'<article class="blog-post"[^>]*>.*?</article>', content, re.DOTALL)

# Track seen symbols and keep only first occurrence
seen_symbols = set()
articles_to_keep = []
duplicates_removed = []

for article in articles:
    # Check if it's a stock article
    symbol_match = re.search(r'Category: ([A-Z0-9.]+) Stock News', article)
    
    if symbol_match:
        symbol = symbol_match.group(1)
        if symbol in seen_symbols:
            # Duplicate - skip it
            duplicates_removed.append(symbol)
            continue
        seen_symbols.add(symbol)
    
    articles_to_keep.append(article)

if duplicates_removed:
    print(f"🗑️  Removing {len(duplicates_removed)} duplicate articles: {', '.join(duplicates_removed)}")
    
    # Rebuild news.html with deduplicated articles
    content_start = content.find('<div class="blog-content">')
    before = content[:content_start + len('<div class="blog-content">')]
    
    after_match = re.search(r'</div>\s*<div style="text-align: center', content)
    if not after_match:
        after_match = re.search(r'</div>\s*<footer', content)
    
    if after_match:
        after = content[after_match.start():]
        
        # Update count
        article_count = len(articles_to_keep)
        after = re.sub(r'<span id="article-count">[0-9]+</span>', f'<span id="article-count">{article_count}</span>', after)
        
        new_content = before + '\n' + '\n'.join(articles_to_keep) + '        ' + after
        news_html_path.write_text(new_content)
        
        print(f"✅ Removed duplicates. Articles: {len(articles)} → {len(articles_to_keep)}")
    else:
        print("⚠️  Could not find end marker")
else:
    print("✅ No duplicates found")
