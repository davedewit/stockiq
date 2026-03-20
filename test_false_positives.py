#!/usr/bin/env python3
"""
Test False Positive Rate for News Matching

Samples 50 random stocks and checks if their latest news articles
are actually about them or false positives.
"""

import os
import re
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Load company names
def load_company_names():
    import csv
    company_names = {}
    skip_words = {'INC', 'CORP', 'LTD', 'LIMITED', 'PLC', 'CO', 'COMPANY', 'CORPORATION', 'INCORPORATED', 'GROUP', 'HOLDINGS', 'THE', 'AND', '&', 'SA', 'S.A', 'AG', 'SE', 'NV', 'N.V', 'N.V.', 'REIT', 'BANCORP', 'TRUST', 'BANK', 'AKTIENGESELLSCHAFT', 'CANADA', 'PROPERTIES'}
    
    with open('/Users/ddewit/VSCODE/website/stocks.txt', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                symbol = row[0].strip()
                name = row[1].strip()
                words = re.findall(r'\b[A-Z][A-Za-z]*\b', name)
                key_words = [w.upper() for w in words if w.upper() not in skip_words]
                if key_words:
                    company_names[symbol] = ' '.join(key_words)
    return company_names

COMPANY_NAMES = load_company_names()

# Critical keywords
CRITICAL_KEYWORDS = [
    'earnings', 'beat', 'miss', 'guidance', 'revenue', 'profit', 'loss',
    'acquisition', 'merger', 'buyout', 'deal', 'partnership', 'contract',
    'fda approval', 'approved', 'rejected', 'recall',
    'lawsuit', 'investigation', 'sec', 'fraud', 'settlement',
    'ceo', 'resignation', 'appointed', 'fired', 'steps down',
    'dividend', 'split', 'buyback', 'stock split',
    'bankruptcy', 'restructuring', 'layoffs', 'cuts jobs',
    'upgrade', 'downgrade', 'rating', 'price target',
    'breakthrough', 'innovation', 'launch', 'unveils',
    'stops production', 'halts', 'suspends', 'resumes',
    'expands', 'opens', 'closes', 'shuts down',
    'surges', 'plunges', 'soars', 'tumbles', 'rallies', 'drops', 'slips', 'dip', 'falls',
    'record', 'all-time high', 'new high', 'new low',
    'analyst', 'wall street', 'investors', 'institutional',
    'stock going to', 'price prediction', 'forecast'
]

def fetch_first_article(symbol):
    """Fetch first matching article for a stock"""
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        for item in items[:30]:
            title = item.find('title').text if item.find('title') else ''
            
            # Check if matches
            title_upper = title.upper()
            base_symbol = symbol.split('.')[0]
            is_match = False
            
            # Check company name or symbol
            company_name = COMPANY_NAMES.get(symbol, '')
            if company_name and company_name in title_upper:
                is_match = True
            elif len(symbol) >= 3 and re.search(r'\b' + re.escape(symbol) + r'\b', title_upper):
                is_match = True
            elif base_symbol in COMPANY_NAMES and len(base_symbol) >= 3:
                if re.search(r'\b' + re.escape(base_symbol) + r'\b', title_upper):
                    is_match = True
            
            if not is_match:
                continue
            
            # Check if critical
            is_critical = any(keyword in title.lower() for keyword in CRITICAL_KEYWORDS)
            
            if is_critical:
                # Check if other symbols in title
                other_symbols = []
                for other_symbol in list(COMPANY_NAMES.keys())[:1000]:
                    if other_symbol != symbol and len(other_symbol) >= 3:
                        if re.search(r'\b' + re.escape(other_symbol) + r'\b', title_upper):
                            other_symbols.append(other_symbol)
                
                return {
                    'title': title,
                    'symbol': symbol,
                    'company_name': company_name,
                    'other_symbols': other_symbols
                }
        
        return None
    except Exception as e:
        return None

# Sample 50 random stocks
all_symbols = list(COMPANY_NAMES.keys())
sample_symbols = random.sample(all_symbols, min(50, len(all_symbols)))

print(f"🔍 Testing {len(sample_symbols)} random stocks for false positives...\n")

results = []
checked = 0
for symbol in sample_symbols:
    checked += 1
    print(f"⏳ [{checked}/{len(sample_symbols)}] Checking {symbol}...", end='\r', flush=True)
    
    article = fetch_first_article(symbol)
    if article:
        results.append(article)

print(f"\n\n📊 Found {len(results)} articles\n")

# Analyze false positives
false_positives = []
true_positives = []

for result in results:
    # If other symbols found AND our symbol NOT in title = likely false positive
    if result['other_symbols']:
        our_symbol_in_title = False
        symbol = result['symbol']
        base_symbol = symbol.split('.')[0]
        title_upper = result['title'].upper()
        
        if len(symbol) >= 3 and re.search(r'\b' + re.escape(symbol) + r'\b', title_upper):
            our_symbol_in_title = True
        elif len(base_symbol) >= 3 and re.search(r'\b' + re.escape(base_symbol) + r'\b', title_upper):
            our_symbol_in_title = True
        
        if not our_symbol_in_title:
            false_positives.append(result)
        else:
            true_positives.append(result)
    else:
        true_positives.append(result)

print(f"✅ True Positives: {len(true_positives)}")
print(f"❌ False Positives: {len(false_positives)}")
print(f"📈 False Positive Rate: {len(false_positives) / len(results) * 100:.1f}%\n")

if false_positives:
    print("❌ False Positive Examples:\n")
    for fp in false_positives[:5]:
        print(f"  {fp['symbol']} ({fp['company_name']})")
        print(f"  Title: {fp['title']}")
        print(f"  Other symbols: {', '.join(fp['other_symbols'])}")
        print()

if true_positives:
    print("✅ True Positive Examples:\n")
    for tp in true_positives[:5]:
        print(f"  {tp['symbol']} ({tp['company_name']})")
        print(f"  Title: {tp['title']}")
        if tp['other_symbols']:
            print(f"  Other symbols: {', '.join(tp['other_symbols'])} (but our symbol IS in title)")
        print()
