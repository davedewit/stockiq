#!/usr/bin/env python3
"""Update sitemap.xml lastmod dates based on actual file modification times.

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
        # Find all data-timestamp attributes (news article dates)
        timestamps = re.findall(r'data-timestamp="([^"]+)"', content)
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


with open(SITEMAP_PATH, 'r') as f:
    content = f.read()

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
