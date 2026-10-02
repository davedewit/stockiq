#!/usr/bin/env python3
"""
Keep news.html small and out of Google's index.

news.html is a running archive of AI-rewritten news. As one huge page it is thin,
duplicated content for search engines, so this script (run by deploy-to-s3.sh after
the other news scripts):
1. Makes sure the page has <meta name="robots" content="noindex, follow">
   (Google still follows its links to the stock pages)
2. Keeps the newest MAX_STOCK_ARTICLES stock articles and MAX_GENERAL_ARTICLES general
   market articles (by data-timestamp); separate limits stop the daily flood of
   stock updates from pushing out all the general market news
3. Shortens each summary to its first MAX_SENTENCES sentences; headlines of stock
   articles already link to the stock page, which holds the full summary
4. Updates the article count

Safe to run repeatedly: a page that is already trimmed is left unchanged.

Usage:
    python3 finalize_news_html.py
    python3 finalize_news_html.py --dry-run
"""

import argparse
import re
import sys
from datetime import datetime, timedelta

NEWS_HTML_PATH = '/Users/dave/VSCODE/website/news.html'
MAX_STOCK_ARTICLES = 240
MAX_GENERAL_ARTICLES = 60
MAX_SENTENCES = 2
ROBOTS_TAG = '<meta name="robots" content="noindex, follow">'


def ensure_noindex(html):
    if re.search(r'<meta name="robots" content="[^"]*">', html):
        return re.sub(r'<meta name="robots" content="[^"]*">', ROBOTS_TAG, html, count=1)
    return html.replace('</head>', f'    {ROBOTS_TAG}\n</head>', 1)


def article_time(article):
    m = re.search(r'data-timestamp="([^"]+)"', article)
    if not m:
        return datetime.min
    try:
        dt = datetime.fromisoformat(m.group(1).replace('Z', '+00:00'))
        return dt.replace(tzinfo=None) - (dt.utcoffset() or timedelta(0))
    except ValueError:
        return datetime.min


def shorten_summary(article):
    """Cut the first <p> inside blog-excerpt to MAX_SENTENCES sentences."""
    m = re.search(r'(<div class="blog-excerpt">\s*<p>)(.*?)(</p>)', article, re.DOTALL)
    if not m:
        return article
    text = ' '.join(m.group(2).split())
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"“])', text)
    if len(sentences) <= MAX_SENTENCES and text == m.group(2):
        return article
    short = ' '.join(sentences[:MAX_SENTENCES])
    return article[:m.start(2)] + short + article[m.end(2):]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    with open(NEWS_HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    start = html.find('<div class="blog-content">')
    if start == -1:
        print("❌ Could not find blog-content in news.html")
        sys.exit(1)
    articles = list(re.finditer(r'<article class="blog-post".*?</article>', html[start:], re.DOTALL))
    if not articles:
        print("ℹ️  No articles found in news.html")
        return
    span_start = start + articles[0].start()
    span_end = start + articles[-1].end()

    newest = sorted((a.group(0) for a in articles), key=article_time, reverse=True)
    stock = [a for a in newest if 'Stock News' in a][:MAX_STOCK_ARTICLES]
    general = [a for a in newest if 'Stock News' not in a][:MAX_GENERAL_ARTICLES]
    kept = sorted(stock + general, key=article_time, reverse=True)
    kept = [shorten_summary(a) for a in kept]

    new_html = html[:span_start] + '\n'.join(kept) + html[span_end:]
    new_html = re.sub(r'<span id="article-count">[0-9]+</span>', f'<span id="article-count">{len(kept)}</span>', new_html)
    new_html = ensure_noindex(new_html)

    if new_html == html:
        print(f"✅ news.html already finalized ({len(kept)} articles, noindex)")
        return
    print(f"✅ news.html: {len(articles)} -> {len(kept)} articles, "
          f"{len(html) / 1e6:.1f} MB -> {len(new_html) / 1e6:.2f} MB, noindex set"
          f"{' (dry run - nothing written)' if args.dry_run else ''}")
    if not args.dry_run:
        with open(NEWS_HTML_PATH, 'w', encoding='utf-8') as f:
            f.write(new_html)


if __name__ == '__main__':
    main()
