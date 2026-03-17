# Script Reference Guide

All key scripts have detailed docstrings. Read them first for complete info.

## Quick Navigation

- [Core Scripts](#core-scripts) - Main workflow scripts
- [Utility Scripts](#utility-scripts) - Maintenance and sync tools
- [Workflow](#workflow) - Daily deployment and manual processes
- [Key Files](#key-files) - Important data files
- [Dependencies](#dependencies) - Required packages
- [Troubleshooting](#troubleshooting) - Common issues and fixes
- [Tips](#tips) - Best practices

For detailed stock matching system info, see [stock-matching-system.md](stock-matching-system.md)

---

## Core Scripts

### fetch_stock_data.py
**What it does:** Fetches company data from Yahoo Finance and syncs NUMERIC_COMPANY_NAMES

**Read docstring:**
```bash
head -40 /Users/ddewit/VSCODE/stockiq/fetch_stock_data.py
```

**Run it:**
```bash
python3 /Users/ddewit/VSCODE/stockiq/fetch_stock_data.py
```

**Output:**
- Updates stocks.txt with real company names/sectors
- Updates NUMERIC_COMPANY_NAMES in update_stock_news.py (144 non-US stocks)

---

### generate-stock-pages.py
**What it does:** Generates 3,466 HTML stock pages with SEO metadata

**Read docstring:**
```bash
head -50 /Users/ddewit/VSCODE/stockiq/generate-stock-pages.py
```

**Run it:**
```bash
python3 /Users/ddewit/VSCODE/stockiq/generate-stock-pages.py
```

**Output:**
- Creates /Users/ddewit/VSCODE/website/stocks/*.html (3,466 files)
- Preserves existing news articles
- Adds Open Graph, Twitter Card, JSON-LD schemas

---

### update_stock_news.py
**What it does:** Fetches news for stocks and updates individual stock pages

**Read docstring:**
```bash
head -50 /Users/ddewit/VSCODE/stockiq/update_stock_news.py
```

**Run it:**
```bash
python3 /Users/ddewit/VSCODE/stockiq/update_stock_news.py
```

**Output:**
- Updates individual stock HTML pages with news
- Updates news.html archive
- Updates news.js sidebar (top 5 articles)
- Respects 23-hour cooldown per stock

**Key features:**
- Matches US stocks via load_company_names() (reads stocks.txt)
- Matches non-US stocks via NUMERIC_COMPANY_NAMES (hardcoded fallback)
- Filters by critical keywords (earnings, merger, FDA approval, etc.)

---

### update_news.py
**What it does:** Fetches market news and generates AI summaries

**Read docstring:**
```bash
head -50 /Users/ddewit/VSCODE/stockiq/update_news.py
```

**Run it:**
```bash
python3 /Users/ddewit/VSCODE/stockiq/update_news.py
```

**Output:**
- Updates news.html with market news
- Updates news.js sidebar (top 5 articles)
- Respects 2-hour cooldown between updates

**Requirements:**
- OPENAI_API_KEY environment variable

---

### people_also_watch_stocks.py
**What it does:** Adds "People also watch" section to stock pages

**Read docstring:**
```bash
head -30 /Users/ddewit/VSCODE/stockiq/people_also_watch_stocks.py
```

**Run it:**
```bash
python3 /Users/ddewit/VSCODE/stockiq/people_also_watch_stocks.py
```

---

### check_news_sync.py
**What it does:** Verifies news is in sync across all files and shows coverage stats

**Read docstring:**
```bash
head -30 /Users/ddewit/VSCODE/stockiq/check_news_sync.py
```

**Run it:**
```bash
python3 /Users/ddewit/VSCODE/stockiq/check_news_sync.py
```

**Output:**
- Shows how many stock pages have news
- Coverage percentage (e.g., "20% of stock pages have news")
- Sync status between stock pages, news.html, and news.js
- Detects broken links and sync issues
- Runs automatically at end of `./deploy.sh`

---

### clear_stock_news.py
**What it does:** Nuclear reset - clears ALL news from all stock pages

**Read docstring:**
```bash
head -20 /Users/ddewit/VSCODE/stockiq/clear_stock_news.py
```

**Use when:** You need to start completely fresh

---

### sync_news_to_stock_pages.py
**What it does:** Reverse sync - pushes news from news.html back to stock pages

**Read docstring:**
```bash
head -20 /Users/ddewit/VSCODE/stockiq/sync_news_to_stock_pages.py
```

**Use when:** Stock pages are missing news that's in news.html

---

### Sync_stock_to_news.py
**What it does:** Forward sync - pushes news from stock pages to news.html

**Use when:** news.html is out of sync with stock pages

---

### fix_news_categories.py
**What it does:** Fixes news article categories

---

### remove_news_duplicates.py
**What it does:** Removes duplicate news articles

---

### update_sitemap.py
**What it does:** Updates sitemap.xml with all stock pages

---

### notify_search_engines.py
**What it does:** Notifies Google and Bing about sitemap updates

---

## Workflow

### deploy.sh — Full deployment (news + S3 sync)

```bash
cd /Users/ddewit/VSCODE/stockiq && ./deploy.sh
```

**Use when:** You want to update news AND deploy. Runs the full pipeline.
**Do NOT use** just to push HTML changes — it triggers OpenAI API calls unnecessarily.

Steps:
1. Pre-flight check - Shows current news sync status
2. Asks if you want to update stock news (y/n)
3. Calls `deploy-to-s3.sh` with UPDATE_STOCK_NEWS flag
4. Inside deploy-to-s3.sh:
   - `update_news.py` - Fetches market news (2-hour cooldown)
   - `update_stock_news.py` - Updates ~60-90 stocks with latest news (23-hour cooldown)
   - `people_also_watch_stocks.py` - Adds internal links to pages
   - `update_sitemap.py` - Updates sitemap.xml with current date
   - `cleanup_broken_links.py` - Removes broken article links
   - `remove_news_duplicates.py` - Removes duplicate articles
   - Deploy to S3 - Uploads website to AWS
   - Invalidate CloudFront - Clears CDN cache
   - `notify_search_engines.py` - Pings Google/Bing about sitemap
   - `sync-all-lambdas.sh` - Syncs Lambda functions (every 15 min)
5. Post-deployment verification - Runs `check_news_sync.py` to verify sync status

**Time:** ~15-20 minutes
**Cost:** ~$1-2 (OpenAI API for news summaries)

### deploy-to-s3.sh — Quick deployment (S3 sync only)

```bash
cd /Users/ddewit/VSCODE/stockiq && ./deploy-to-s3.sh
```

**Use when:** You've already generated/edited HTML files and just need to push them live.
Examples: regenerated stock pages, fixed a template, edited index.html.

Does:
- Syncs website to S3
- Invalidates CloudFront cache
- Notifies search engines

**Time:** ~5 minutes
**Cost:** $0 (no API calls)

### Manual Workflow

**Add new stocks:**
See [add-new-stocks.md](add-new-stocks.md) for complete workflow

**Update news manually:**
```bash
python3 update_stock_news.py    # Update stock pages with news
python3 update_news.py          # Update market news
```

**Sync news if out of sync:**
```bash
python3 Sync_stock_to_news.py   # Push stock page news → news.html
python3 sync_news_to_stock_pages.py  # Push news.html → stock pages
```

**Start fresh:**
```bash
python3 clear_stock_news.py     # Remove all news
python3 update_stock_news.py    # Repopulate with fresh news
```

---

## Key Files

- **stocks.txt** - Source of truth (3,466 stocks with names/sectors)
  - Format: CSV with 3 columns: `SYMBOL,Company Name,Sector`
  - Company names with commas are quoted: `"Ajinomoto Co., Inc."`
  - Read with Python's csv.reader (not awk/cut/sed)
  
- **update_stock_news.py** - Contains NUMERIC_COMPANY_NAMES (144 non-US stocks)
  - Hardcoded fallback for numeric symbols (0700.HK, 7203.T, etc.)
  - Auto-synced by fetch_stock_data.py
  
- **website/stocks/*.html** - Generated stock pages (3,466 files)
  - Each page has: stock info, sector, news section, SEO metadata
  - News preserved between regenerations (<!-- NEWS_SECTION_START/END -->)
  
- **website/news.html** - News archive (all articles)
  
- **website/news.js** - Sidebar (top 5 most recent articles)

---

## Dependencies

All scripts require:
- Python 3.9.6+
- yfinance (stock data)
- requests (HTTP)
- BeautifulSoup (HTML parsing)
- OpenAI API key (for news summarization)

Install:
```bash
pip install yfinance requests beautifulsoup4 openai
```

## Troubleshooting

### Script runs but no output
- Run without piping: `python3 script.py` (not `python3 script.py | tail -20`)
- Output is buffered until script finishes

### OPENAI_API_KEY not found
- Set environment variable: `export OPENAI_API_KEY=sk-...`
- Or create file: `~/.openai_key` with your API key

### News not updating
- Check 2-hour cooldown (update_news.py)
- Check 23-hour cooldown per stock (update_stock_news.py)
- Verify OPENAI_API_KEY is set
- Check internet connection for RSS feeds

### Stock pages not regenerating
- Run `generate-stock-pages.py` after updating stocks.txt
- Check that stocks.txt has proper CSV format (quoted names)

### NUMERIC_COMPANY_NAMES out of sync
- Run `fetch_stock_data.py` to auto-sync
- It extracts numeric symbols from stocks.txt and updates update_stock_news.py

## Tips

- Always read the docstring first: `head -50 script.py`
- Check script output for real-time progress
- All scripts have detailed docstrings with usage examples
- File paths are hardcoded in scripts (no config files needed)
- All scripts are idempotent (safe to run multiple times)
