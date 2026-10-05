#!/usr/bin/env python3
"""Rebuild sitemap.xml stock URLs from indexable_stocks.txt and update lastmod dates.

- Stock URLs: rebuilt from indexable_stocks.txt (only large-cap indexed pages)
- Site pages (non-stock): preserved from existing sitemap, lastmod updated
- Safety check: refuses to touch stock URLs if indexable_stocks.txt has < 200 entries

Called automatically by deploy-to-s3.sh.

Usage:
    python3 update_sitemap.py
"""
import re
import os
from datetime import datetime, timezone

WEBSITE_DIR = '/Users/dave/VSCODE/website'
SCRIPTS_DIR = '/Users/dave/VSCODE/stockiq'
SITEMAP_PATH = os.path.join(WEBSITE_DIR, 'sitemap.xml')
INDEXABLE_FILE = os.path.join(SCRIPTS_DIR, 'indexable_stocks.txt')
MIN_INDEXABLE = 200  # Safety threshold


def get_stock_page_lastmod(filepath):
    """For stock pages, extract the latest news timestamp as the true lastmod date."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        timestamps = re.findall(r'data-timestamp="([^"]+)"', content)
        if timestamps:
            dates = []
            for ts in timestamps:
                try:
                    clean_ts = re.sub(r'[+-]\d{2}:\d{2}$', '', ts)
                    dt = datetime.fromisoformat(clean_ts)
                    dates.append(dt)
                except (ValueError, TypeError):
                    continue
            if dates:
                return max(dates).strftime('%Y-%m-%d')
    except (IOError, OSError):
        pass
    return None


def get_file_mtime(filepath):
    """Get file modification date, falling back to today."""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime('%Y-%m-%d')
    except OSError:
        return datetime.now().strftime('%Y-%m-%d')


def get_lastmod(symbol):
    """Get lastmod for a stock page — news date if available, else file mtime."""
    filepath = os.path.join(WEBSITE_DIR, 'stocks', f'{symbol}.html')
    if not os.path.exists(filepath):
        return datetime.now().strftime('%Y-%m-%d')
    news_date = get_stock_page_lastmod(filepath)
    if news_date:
        return news_date
    return get_file_mtime(filepath)


def get_site_page_lastmod(url):
    """Get lastmod for a non-stock site page."""
    path = url.replace('https://stockiq.tech/', '') or 'index.html'
    filepath = os.path.join(WEBSITE_DIR, path)
    if not os.path.exists(filepath):
        return None
    return get_file_mtime(filepath)


# --- Load indexable stocks ---
if not os.path.exists(INDEXABLE_FILE):
    print(f"❌ {INDEXABLE_FILE} not found — sitemap not updated")
    exit(1)

with open(INDEXABLE_FILE, 'r') as f:
    indexable = [line.strip() for line in f if line.strip()]

if len(indexable) < MIN_INDEXABLE:
    print(f"⚠️  Only {len(indexable)} indexable stocks (< {MIN_INDEXABLE}) — sitemap stock URLs not updated (safety check)")
    exit(0)

# --- Load existing sitemap to extract non-stock site pages ---
with open(SITEMAP_PATH, 'r') as f:
    existing = f.read()

# Extract non-stock URLs from existing sitemap
site_page_blocks = []
for match in re.finditer(r'<(?:ns0:)?url>.*?</(?:ns0:)?url>', existing, re.DOTALL):
    block = match.group(0)
    loc_match = re.search(r'<(?:ns0:)?loc>(.*?)</(?:ns0:)?loc>', block)
    if loc_match:
        url = loc_match.group(1)
        if '/stocks/' not in url:
            site_page_blocks.append(url)

# --- Build new sitemap ---
today = datetime.now().strftime('%Y-%m-%d')
lines = ['<?xml version=\'1.0\' encoding=\'utf-8\'?>']
lines.append('<ns0:urlset xmlns:ns0="http://www.sitemaps.org/schemas/sitemap/0.9">')

# Site pages first (with updated lastmod)
for url in site_page_blocks:
    lastmod = get_site_page_lastmod(url) or today
    priority = '1.0' if url == 'https://stockiq.tech/' else '0.9' if 'analysis' in url else '0.8'
    changefreq = 'daily' if url == 'https://stockiq.tech/' else 'weekly'
    lines.append(f'  <ns0:url>')
    lines.append(f'    <ns0:loc>{url}</ns0:loc>')
    lines.append(f'    <ns0:lastmod>{lastmod}</ns0:lastmod>')
    lines.append(f'    <ns0:changefreq>{changefreq}</ns0:changefreq>')
    lines.append(f'    <ns0:priority>{priority}</ns0:priority>')
    lines.append(f'  </ns0:url>')

# Stock pages (only indexable ones)
for symbol in indexable:
    url = f'https://stockiq.tech/stocks/{symbol}.html'
    lastmod = get_lastmod(symbol)
    lines.append(f'  <ns0:url>')
    lines.append(f'    <ns0:loc>{url}</ns0:loc>')
    lines.append(f'    <ns0:lastmod>{lastmod}</ns0:lastmod>')
    lines.append(f'    <ns0:changefreq>daily</ns0:changefreq>')
    lines.append(f'    <ns0:priority>0.7</ns0:priority>')
    lines.append(f'  </ns0:url>')

lines.append('</ns0:urlset>')

with open(SITEMAP_PATH, 'w') as f:
    f.write('\n'.join(lines) + '\n')

print(f"✅ Updated sitemap.xml — {len(site_page_blocks)} site pages + {len(indexable)} stock pages = {len(site_page_blocks) + len(indexable)} total URLs")
