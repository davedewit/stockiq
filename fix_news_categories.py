#!/usr/bin/env python3
"""Fix misclassified news categories in news.html.

Finds stock articles incorrectly tagged as 'Market News' or 'General Market News'
and corrects them to '{SYMBOL} Stock News' based on the stock page link in the article.

Usage:
    python3 fix_news_categories.py
"""

import re

NEWS_HTML_PATH = '/Users/ddewit/VSCODE/website/news.html'

def fix_categories():
    """Fix all stock news categories in news.html"""
    with open(NEWS_HTML_PATH, 'r') as f:
        html = f.read()
    
    # Find all articles with stock links but wrong category
    # Pattern: articles that link to stocks/{SYMBOL}.html but have "General Market News" category
    
    # Extract all articles
    articles = re.findall(r'<article class="blog-post"[^>]*>.*?</article>', html, re.DOTALL)
    
    fixed_count = 0
    new_articles = []
    
    for article in articles:
        # Check if article links to a stock page
        stock_link_match = re.search(r'href="stocks/([A-Z0-9.]+)\.html"', article)
        
        if stock_link_match:
            symbol = stock_link_match.group(1)
            
            # Check if category is wrong
            if 'Category: General Market News' in article or 'Category: Market News' in article:
                # Fix the category
                fixed_article = re.sub(
                    r'Category: (?:General )?Market News',
                    f'Category: {symbol} Stock News',
                    article
                )
                new_articles.append(fixed_article)
                fixed_count += 1
                print(f"✅ Fixed {symbol}: General Market News → {symbol} Stock News")
            else:
                new_articles.append(article)
        else:
            # Not a stock article, keep as is
            new_articles.append(article)
    
    if fixed_count == 0:
        print("✅ No articles needed fixing")
        return
    
    # Rebuild HTML
    # Find the blog-content div
    content_start = html.find('<div class="blog-content">')
    if content_start == -1:
        print("❌ Could not find blog-content div")
        return
    
    before = html[:content_start + len('<div class="blog-content">')]
    after_match = re.search(r'</div>\s*<div style="text-align: center', html)
    if not after_match:
        print("❌ Could not find footer pattern")
        return
    after = html[after_match.start():]
    
    # Update article count
    article_count = len(new_articles)
    after = re.sub(r'<span id="article-count">[0-9]+</span>', f'<span id="article-count">{article_count}</span>', after)
    
    new_html = before + '\n' + '\n'.join(new_articles) + '\n        ' + after
    
    with open(NEWS_HTML_PATH, 'w') as f:
        f.write(new_html)
    
    print(f"\n✅ Fixed {fixed_count} articles in news.html")

if __name__ == '__main__':
    fix_categories()
