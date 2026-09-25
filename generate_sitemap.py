#!/usr/bin/env python3
"""Add missing stock pages to sitemap.xml

Finds indexable stock pages (indexable_stocks.txt) not in the sitemap and adds them.
Dates are updated separately by update_sitemap.py

Usage:
    python3 generate_sitemap.py
"""
import os
import re
from datetime import datetime

WEBSITE_DIR = '/Users/ddewit/VSCODE/website'
SITEMAP_PATH = os.path.join(WEBSITE_DIR, 'sitemap.xml')
STOCKS_DIR = os.path.join(WEBSITE_DIR, 'stocks')

# Get all HTML files in stocks directory
html_files = {f.replace('.html', '') for f in os.listdir(STOCKS_DIR) if f.endswith('.html')}

# Only indexable pages belong in the sitemap (see update_stock_analysis.py);
# update_sitemap.py also removes any that are no longer indexable
INDEXABLE_FILE = '/Users/ddewit/VSCODE/stockiq/indexable_stocks.txt'
if os.path.exists(INDEXABLE_FILE):
    with open(INDEXABLE_FILE) as f:
        html_files &= {line.strip() for line in f if line.strip()}

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
    new_urls.append(f"""  <ns0:url>
    <ns0:loc>https://stockiq.tech/stocks/{symbol}.html</ns0:loc>
    <ns0:lastmod>{today}</ns0:lastmod>
    <ns0:changefreq>weekly</ns0:changefreq>
    <ns0:priority>0.6</ns0:priority>
  </ns0:url>""")

# Insert before closing </ns0:urlset>
sitemap = sitemap.replace('</ns0:urlset>', '\n'.join(new_urls) + '\n</ns0:urlset>')

# Write back
with open(SITEMAP_PATH, 'w') as f:
    f.write(sitemap)

print(f"✅ Added {len(missing)} URLs to sitemap.xml")
print(f"   Symbols: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")
