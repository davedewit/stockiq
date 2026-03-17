#!/usr/bin/env python3
"""Update sitemap.xml lastmod dates based on actual file modification times.

Only updates <lastmod> for URLs whose files have changed — avoids inflating
dates for unchanged pages. Called automatically by deploy-to-s3.sh.

Usage:
    python3 update_sitemap.py
"""
import re
import os
from datetime import datetime, timezone

WEBSITE_DIR = '/Users/ddewit/VSCODE/website'
SITEMAP_PATH = os.path.join(WEBSITE_DIR, 'sitemap.xml')

def get_file_mtime(url):
    """Get file modification date for a given URL, returns None if file not found"""
    path = url.replace('https://stockiq.tech/', '')
    filepath = os.path.join(WEBSITE_DIR, path)
    if os.path.exists(filepath):
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime('%Y-%m-%d')
    return None

with open(SITEMAP_PATH, 'r') as f:
    content = f.read()

def replace_lastmod(match):
    url = re.search(r'<loc>(.*?)</loc>', match.group(0)).group(1)
    mtime = get_file_mtime(url)
    if mtime:
        return re.sub(r'<lastmod>[\d-]+</lastmod>', f'<lastmod>{mtime}</lastmod>', match.group(0))
    return match.group(0)

updated = re.sub(r'<url>.*?</url>', replace_lastmod, content, flags=re.DOTALL)

with open(SITEMAP_PATH, 'w') as f:
    f.write(updated)

print(f"✅ Updated sitemap.xml with actual file modification dates")
