# Stock Matching System

## Overview
The system matches news articles to stocks using two parallel mechanisms:

1. **US Stocks (3,322)** - Dynamic, read from stocks.txt
2. **Non-US Stocks (144)** - Hardcoded fallback for numeric symbols

Both are kept in sync by `fetch_stock_data.py`.

---

## How It Works

### US Stocks (AAPL, TSLA, etc.)
**File:** `update_stock_news.py` - `load_company_names()` function

```python
def load_company_names():
    """Load company names from stocks.txt and extract key words"""
    # Reads stocks.txt at startup
    # Extracts company names and keywords
    # Returns dict: {symbol: 'KEY WORDS'}
```

**Process:**
1. Reads stocks.txt using csv.reader (handles quoted names)
2. Extracts keywords from company names
3. Removes common suffixes (INC, CORP, LTD, etc.)
4. Returns dict: `{'AAPL': 'APPLE', 'TSLA': 'TESLA', ...}`

**Example:**
- Stock: `AAPL,Apple Inc.,Technology`
- Extracted: `{'AAPL': 'APPLE'}`
- News: "Apple Reports Earnings" → Matches AAPL

### Non-US Stocks (0700.HK, 7203.T, etc.)
**File:** `update_stock_news.py` - `NUMERIC_COMPANY_NAMES` dictionary

```python
NUMERIC_COMPANY_NAMES = {
    '0700.HK': 'TENCENT',
    '7203.T': 'TOYOTA MOTOR',
    ...
}
```

**Why hardcoded?**
- Numeric symbols don't have standard ticker symbols
- Need simplified names for news matching
- Updated automatically by `fetch_stock_data.py`

**Process:**
1. `fetch_stock_data.py` reads stocks.txt
2. Extracts numeric symbols (0700.HK, 7203.T, etc.)
3. Generates simplified company names
4. Updates NUMERIC_COMPANY_NAMES in update_stock_news.py

**Example:**
- Stock: `0700.HK,"Tencent Holdings Limited",Technology`
- Extracted: `{'0700.HK': 'TENCENT'}`
- News: "Tencent Expands Services" → Matches 0700.HK

---

## News Matching Logic

**File:** `update_stock_news.py` - `find_matching_stock()` function

```python
def find_matching_stock(title):
    """Find which stock this article is actually about"""
    title_upper = title.upper()
    
    # First check company names (most specific)
    for symbol, names in COMPANY_NAMES.items():
        for name in names:
            if name in title_upper:
                return symbol
    
    # Then check symbols (only 3+ characters to avoid false matches)
    for symbol in COMPANY_NAMES.keys():
        if len(symbol) >= 3:
            if re.search(r'\b' + re.escape(symbol) + r'\b', title_upper):
                return symbol
    
    return None
```

**Priority:**
1. Company names (most specific) - "APPLE" in title → AAPL
2. Symbols (3+ chars only) - "AAPL" in title → AAPL
3. No match - Return None

---

## Auto-Sync Process

**File:** `fetch_stock_data.py` - `update_numeric_company_names()` function

**When you run:**
```bash
python3 /Users/ddewit/VSCODE/stockiq/fetch_stock_data.py
```

**It does:**
1. Reads stocks.txt
2. Fetches company data from Yahoo Finance
3. Updates stocks.txt with new names/sectors
4. **Extracts numeric symbols from stocks.txt**
5. **Generates simplified company names**
6. **Updates NUMERIC_COMPANY_NAMES in update_stock_news.py**

**Result:** Both US and non-US stocks stay in sync automatically.

---

## Stock Count

| Type | Count | Source | Updated |
|------|-------|--------|---------|
| US stocks | 3,322 | stocks.txt | Dynamic (load_company_names) |
| Non-US stocks | 144 | stocks.txt | Auto-sync (fetch_stock_data.py) |
| **Total** | **3,466** | - | - |

---

## Testing

To verify the system works:

```bash
python3 /Users/ddewit/VSCODE/stockiq/test_us_and_nonUS.py
```

This tests:
- US stock matching (NVDA)
- Non-US stock matching (0005.HK, 0700.HK)
- Company name extraction
- NUMERIC_COMPANY_NAMES dictionary

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| News not matching to stock | Company name not in stocks.txt | Update stocks.txt with correct name |
| Non-US stock not matching | Missing from NUMERIC_COMPANY_NAMES | Run `fetch_stock_data.py` |
| Duplicate matches | Multiple stocks with same keyword | Refine company names in stocks.txt |
| False positives | Short symbols matching unrelated words | Symbol matching requires 3+ chars |

---

## Files Involved

- `stockiq/update_stock_news.py` - Main matching logic
- `stockiq/fetch_stock_data.py` - Auto-sync for non-US stocks
- `website/stocks.txt` - Source of truth for all stocks
- `stockiq/.amazonq/rules/stocks-txt-csv-format.md` - CSV format rules
