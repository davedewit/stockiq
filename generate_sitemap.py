#!/usr/bin/env python3
"""Add missing INDEXABLE stock pages to sitemap.xml

Only adds stocks that are in indexable_stocks.txt (large-cap pages >= $10B).
Do NOT add all stock HTML files — that would include noindex pages and hurt SEO.
Dates are updated separately by update_sitemap.py

Usage:
    python3 generate_sitemap.py
"""
import os
import re
from datetime import datetime

WEBSITE_DIR = '/Users/dave/VSCODE/website'
SCRIPTS_DIR = '/Users/dave/VSCODE/stockiq'
SITEMAP_PATH = os.path.join(WEBSITE_DIR, 'sitemap.xml')
INDEXABLE_FILE = os.path.join(SCRIPTS_DIR, 'indexable_stocks.txt')

# Only use indexable stocks — NOT all HTML files in stocks/
if not os.path.exists(INDEXABLE_FILE):
    print(f"❌ {INDEXABLE_FILE} not found — run update_stock_analysis.py first")
    exit(1)

with open(INDEXABLE_FILE, 'r') as f:
    html_files = {line.strip() for line in f if line.strip()}

# Read sitemap
with open(SITEMAP_PATH, 'r') as f:
    sitemap = f.read()

# Extract existing symbols from sitemap
existing = set(re.findall(r'stocks/([A-Z0-9\.\-]+)\.html', sitemap))

# Find missing symbols
missing = sorted(html_files - existing)

if not missing:
    print("✅ All stock pages already in sitemap")
    exit(0)

print(f"📝 Adding {len(missing)} missing pages to sitemap...")

# Generate new URLs
today = datetime.now().strftime('%Y-%m-%d')
new_urls = []
for symbol in missing:
    new_urls.append(f"""  <url>
    <loc>https://stockiq.tech/stocks/{symbol}.html</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>""")

# Insert before the closing tag (plain since 18 Oct 2026; an older file has the ns0: prefix, whose rows must carry it too)
if '</ns0:urlset>' in sitemap:
    new_urls = [u.replace('<', '<ns0:').replace('<ns0:/', '</ns0:') for u in new_urls]
    sitemap = sitemap.replace('</ns0:urlset>', '\n'.join(new_urls) + '\n</ns0:urlset>')
else:
    sitemap = sitemap.replace('</urlset>', '\n'.join(new_urls) + '\n</urlset>')

# Write back
with open(SITEMAP_PATH, 'w') as f:
    f.write(sitemap)

print(f"✅ Added {len(missing)} URLs to sitemap.xml")
print(f"   Symbols: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")
