#!/usr/bin/env python3
"""Keep sitemap.xml in step with the site.

Stock URLs are set to exactly the pages listed in indexable_stocks.txt (written by
update_stock_analysis.py); noindex pages such as news.html are removed. Then lastmod
dates are updated based on actual content changes.

For stock pages, checks the HTML content for news timestamps to determine
the actual last content update (not just file system mtime which can be
stale due to S3 --size-only sync).

Called automatically by deploy-to-s3.sh.

Usage:
    python3 update_sitemap.py
"""
import re
import os
from datetime import datetime, timezone

WEBSITE_DIR = '/Users/ddewit/VSCODE/website'
SITEMAP_PATH = os.path.join(WEBSITE_DIR, 'sitemap.xml')


def get_stock_page_lastmod(filepath):
    """For stock pages, extract the latest news timestamp as the true lastmod date."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # News article dates plus the data snapshot date
        timestamps = re.findall(r'data-timestamp="([^"]+)"', content)
        timestamps += re.findall(r'class="stock-snapshot" data-asof="([^"]+)"', content)
        if timestamps:
            # Parse and find the most recent one
            dates = []
            for ts in timestamps:
                try:
                    # Python 3.9 doesn't handle +00:00 in fromisoformat
                    # Strip timezone and parse as UTC
                    clean_ts = re.sub(r'[+-]\d{2}:\d{2}$', '', ts)
                    dt = datetime.fromisoformat(clean_ts)
                    dates.append(dt)
                except (ValueError, TypeError):
                    continue
            if dates:
                latest = max(dates)
                return latest.strftime('%Y-%m-%d')
    except (IOError, OSError):
        pass
    return None


def get_file_mtime(url):
    """Get file modification date for a given URL, returns None if file not found"""
    path = url.replace('https://stockiq.tech/', '')
    if not path:
        path = 'index.html'
    filepath = os.path.join(WEBSITE_DIR, path)
    if not os.path.exists(filepath):
        return None

    # For stock pages, use the latest news timestamp instead of file mtime
    if path.startswith('stocks/') and path.endswith('.html'):
        news_date = get_stock_page_lastmod(filepath)
        if news_date:
            return news_date

    # Fall back to file modification time
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime('%Y-%m-%d')


INDEXABLE_FILE = '/Users/ddewit/VSCODE/stockiq/indexable_stocks.txt'
MIN_INDEXABLE = 200  # safety: a shorter list means the analysis run failed, so leave URLs alone
EXCLUDED_URLS = {'https://stockiq.tech/news.html'}  # noindex pages must not be in the sitemap


def sync_membership(content):
    """Make the sitemap's stock URLs match indexable_stocks.txt and drop excluded pages."""
    url_blocks = re.findall(r'\s*<(?:ns0:)?url>.*?</(?:ns0:)?url>', content, flags=re.DOTALL)
    loc = lambda block: re.search(r'<(?:ns0:)?loc>(.*?)</(?:ns0:)?loc>', block).group(1)

    indexable = None
    if os.path.exists(INDEXABLE_FILE):
        with open(INDEXABLE_FILE) as f:
            indexable = {line.strip() for line in f if line.strip()}
    if indexable is not None and len(indexable) < MIN_INDEXABLE:
        print(f"⚠️  indexable_stocks.txt has only {len(indexable)} entries - leaving stock URLs unchanged")
        indexable = None

    kept, removed = [], 0
    present = set()
    for block in url_blocks:
        url = loc(block)
        m = re.match(r'https://stockiq\.tech/stocks/(.+)\.html$', url)
        if url in EXCLUDED_URLS or (m and indexable is not None and m.group(1) not in indexable):
            removed += 1
            continue
        if m:
            present.add(m.group(1))
        kept.append(block)

    added = 0
    if indexable is not None:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        for symbol in sorted(indexable - present):
            if os.path.exists(os.path.join(WEBSITE_DIR, 'stocks', f'{symbol}.html')):
                kept.append(f"""
  <ns0:url>
    <ns0:loc>https://stockiq.tech/stocks/{symbol}.html</ns0:loc>
    <ns0:lastmod>{today}</ns0:lastmod>
    <ns0:changefreq>daily</ns0:changefreq>
    <ns0:priority>0.6</ns0:priority>
  </ns0:url>""")
                added += 1

    head = content[:content.index('<ns0:urlset')]
    head += content[content.index('<ns0:urlset'):].split('>', 1)[0] + '>'
    print(f"🗺️  Sitemap membership: {added} added, {removed} removed, {len(kept)} URLs")
    return head + ''.join(kept) + '\n</ns0:urlset>\n'


with open(SITEMAP_PATH, 'r') as f:
    content = f.read()

content = sync_membership(content)

updated_count = 0

def replace_lastmod(match):
    global updated_count
    url_match = re.search(r'<(?:ns0:)?loc>(.*?)</(?:ns0:)?loc>', match.group(0))
    if not url_match:
        return match.group(0)
    url = url_match.group(1)
    mtime = get_file_mtime(url)
    if mtime:
        old_date = re.search(r'<(?:ns0:)?lastmod>([\d-]+)</(?:ns0:)?lastmod>', match.group(0))
        if old_date and old_date.group(1) != mtime:
            updated_count += 1
        return re.sub(r'(<(?:ns0:)?lastmod>)[\d-]+(</(?:ns0:)?lastmod>)', rf'\g<1>{mtime}\g<2>', match.group(0))
    return match.group(0)

updated = re.sub(r'<(?:ns0:)?url>.*?</(?:ns0:)?url>', replace_lastmod, content, flags=re.DOTALL)

with open(SITEMAP_PATH, 'w') as f:
    f.write(updated)

print(f"✅ Updated sitemap.xml — {updated_count} URLs got new lastmod dates")
