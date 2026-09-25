# Add New Stocks Workflow

## Complete Process

### 0. Find new stocks to add
- Research/find stocks you want to add (screeners, news, etc.)
- Run `test_stock_rss.py` to check if they have recent news (~20 days)
- Only proceed with stocks that show "✅ Matched (ready now)"
- Script is free to run; cost only occurs when articles are discovered and processed

### 1. Check RSS for new stocks
```bash
echo -e "2\nTSLA\n" | python3 /Users/ddewit/VSCODE/stockiq/test_stock_rss.py
```
- Only proceed if "Matched (ready now)" appears
- Stock must have had a news article in the last ~20 days to be worth adding

### 2. Add stocks to stocks.txt
```bash
echo "TSLA" >> /Users/ddewit/VSCODE/website/stocks.txt
```
- Just add the symbol (no company name or sector yet)

### 3. Fetch company data and update stocks.txt
```bash
python3 /Users/ddewit/VSCODE/stockiq/fetch_stock_data.py
```
- Fetches company names and sectors from Yahoo Finance
- Updates stocks.txt with proper CSV format
- Also updates NUMERIC_COMPANY_NAMES for non-US stocks

### 4. Regenerate stock pages
```bash
python3 /Users/ddewit/VSCODE/stockiq/generate-stock-pages.py
```
- Creates HTML files for all stocks in stocks.txt
- Preserves existing news sections

### 5. Add missing pages to sitemap
```bash
python3 /Users/ddewit/VSCODE/stockiq/generate_sitemap.py
```
- Finds HTML files not in sitemap
- Adds only missing URLs
- Dates will be updated by deploy script

### 6. Verify files created
```bash
ls -lh /Users/ddewit/VSCODE/website/stocks/TSLA.html
```
- Confirm HTML file exists
- Check file size (~23KB typical)

### 7. Deploy
```bash
cd /Users/ddewit/VSCODE/stockiq && ./deploy-to-s3.sh
```
- Syncs to S3
- Updates sitemap dates (update_sitemap.py)
- Invalidates CloudFront cache
- Notifies search engines

## Key Files

- `/Users/ddewit/VSCODE/website/stocks.txt` - Source of truth (SYMBOL, Company Name, Sector)
- `/Users/ddewit/VSCODE/website/stocks/` - Generated HTML pages (3,467+ files)
- `/Users/ddewit/VSCODE/website/sitemap.xml` - All URLs for search engines

## Scripts

| Script | Purpose |
|--------|---------|
| test_stock_rss.py | Check if stock has RSS news available |
| fetch_stock_data.py | Fetch company names/sectors from Yahoo Finance |
| generate-stock-pages.py | Create HTML pages for all stocks |
| generate_sitemap.py | Add missing stock URLs to sitemap |
| update_sitemap.py | Update lastmod dates (called by deploy) |
| deploy-to-s3.sh | Deploy to S3 + CloudFront + search engines |

## Important Rules

- **Test RSS first** - Only add stocks with recent news activity (~20 days); no point generating a page for a stock with no coverage (cost is per article discovered, not per page)
- **Keep scripts separate** - generate_sitemap.py and update_sitemap.py do different things
- **Verify before deploy** - Always check HTML files exist before deploying
- **Batch adds** - Add multiple stocks at once, then regenerate once
- **stocks.txt format** - CSV with quoted company names: `TSLA,Tesla Inc.,Consumer Cyclical`

## Example: Add 3 Stocks

```bash
# 1. Test each stock
echo -e "2\nTSLA\n" | python3 test_stock_rss.py
echo -e "2\nNVDA\n" | python3 test_stock_rss.py
echo -e "2\nAAPL\n" | python3 test_stock_rss.py

# 2. Add to stocks.txt (only ones with news)
echo "TSLA" >> stocks.txt
echo "NVDA" >> stocks.txt

# 3. Fetch company data
python3 fetch_stock_data.py

# 4. Regenerate pages
python3 generate-stock-pages.py

# 5. Add to sitemap
python3 generate_sitemap.py

# 6. Verify
ls -lh /Users/ddewit/VSCODE/website/stocks/{TSLA,NVDA}.html

# 7. Deploy
./deploy-to-s3.sh
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Stock has no news | Don't add it (wastes crawl budget) |
| HTML file not created | Check stocks.txt format and run generate-stock-pages.py again |
| Stock not in sitemap | Run generate_sitemap.py |
| Sitemap dates not updated | Deploy script calls update_sitemap.py automatically |
