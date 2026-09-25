# stocks.txt CSV Format

## Critical Rule
**stocks.txt is properly formatted CSV. Do NOT say it's "broken" when simple parsing tools show quoted company names as sectors.**

## Overview
- **Location:** `/Users/ddewit/VSCODE/website/stocks.txt`
- **Format:** CSV with 3 columns: `SYMBOL,Company Name,Sector`
- **Total:** 3,467 stocks
- **Used by:** All scripts (generate-stock-pages.py, update_stock_news.py, etc.)

```
AAPL,Apple Inc.,Technology
2802.T,"Ajinomoto Co., Inc.",Consumer Defensive
```

Company names with commas are quoted — this is correct, not broken.

## Parsing: Right vs Wrong

### ❌ WRONG (awk/cut/sed — don't understand CSV quoting):
```bash
awk -F',' '{print $3}' /Users/ddewit/VSCODE/website/stocks.txt | sort | uniq -c | sort -rn
```
Shows `Inc."`, `Ltd."` as sectors — this is a parser failure, not a data problem.

### ✅ CORRECT (Python csv.reader):
```bash
python3 -c "
import csv
sectors = {}
with open('/Users/ddewit/VSCODE/website/stocks.txt', 'r') as f:
    for row in csv.reader(f):
        if len(row) >= 3:
            sectors[row[2]] = sectors.get(row[2], 0) + 1
for sector, count in sorted(sectors.items(), key=lambda x: -x[1]):
    print(f'{count:4d} {sector}')
"
```

### ✅ SOURCE OF TRUTH (HTML pages):
```bash
grep -h "Sector:" /Users/ddewit/VSCODE/website/stocks/*.html | sed 's/.*Sector: //' | sort | uniq -c | sort -rn
```
These two should match. If they don't, regenerate HTML pages (see Workflow below).

## Expected Sector Distribution
```
 567 Financial Services
 506 Healthcare
 459 Industrials
 434 Technology
 381 Consumer Cyclical
 247 Real Estate
 210 Basic Materials
 181 Energy
 175 Consumer Defensive
 150 Communication Services
  94 Utilities
  35 General
  25 Materials
   3 Automotive
```

## Generation
`fetch_stock_data.py` generates/updates stocks.txt — reads existing file, fetches company info from Yahoo Finance, writes back with Python's `csv.writer` (proper quoting).

**NEW:** Also automatically updates `NUMERIC_COMPANY_NAMES` in `update_stock_news.py` for non-US stocks.

For detailed info, see the docstring in the script:
```bash
head -30 /Users/ddewit/VSCODE/stockiq/fetch_stock_data.py
```

Run it:
```bash
python3 /Users/ddewit/VSCODE/stockiq/fetch_stock_data.py
```

## Workflow

1. **Add stocks to stocks.txt** (manually or via script)

2. **Update stocks.txt with company data:**
   ```bash
   python3 /Users/ddewit/VSCODE/stockiq/fetch_stock_data.py
   ```
   This does TWO things:
   - Fetches company names and sectors from Yahoo Finance
   - **Automatically updates NUMERIC_COMPANY_NAMES in update_stock_news.py** (for non-US stocks)

3. **Verify sectors:**
   ```bash
   python3 -c "import csv; sectors = {}; [sectors.update({row[2]: sectors.get(row[2], 0) + 1}) for row in csv.reader(open('/Users/ddewit/VSCODE/website/stocks.txt')) if len(row) >= 3]; [print(f'{count:4d} {sector}') for sector, count in sorted(sectors.items(), key=lambda x: -x[1])]"
   ```

4. **Regenerate HTML pages:**
   ```bash
   python3 /Users/ddewit/VSCODE/stockiq/generate-stock-pages.py
   ```

5. **Verify HTML matches:**
   ```bash
   grep -h "Sector:" /Users/ddewit/VSCODE/website/stocks/*.html | sed 's/.*Sector: //' | sort | uniq -c | sort -rn
   ```

6. **Deploy:**
   ```bash
   cd /Users/ddewit/VSCODE/stockiq && yes | ./deploy.sh >> ~/stockiq-daily.log 2>&1 &
   ```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Seeing `Inc."`, `Ltd."` in sector counts | Using awk instead of csv.reader | Use Python parsing command above |
| HTML sectors differ from stocks.txt | HTML generated before stocks.txt updated | Run `generate-stock-pages.py` |
| 1,156 entries with `Inc."` as sector | Manual CSV writing without proper quoting | Run `fetch_stock_data.py` |
