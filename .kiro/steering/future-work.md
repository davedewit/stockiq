# Future Work

---

## 1. People Also Watch Improvements

### Current State
- 5 sector peers shown per stock page (between `<!-- RELATED_SECTION_START -->` and `<!-- RELATED_SECTION_END -->`)
- Prices load live via `stock-prices.js` (static HTML shows `--` until then)
- Selection is **hybrid: 3 from PRIORITY_STOCKS dict + 2 random** from same sector

### Fix 1: Well-Known Stocks (Do First)
Replace hybrid logic with pure anchor stocks — always show top 5 well-known stocks from the sector.

**File:** `/Users/dave/VSCODE/stockiq/people_also_watch_stocks.py`

Replace in `get_related_stocks()` (~lines 70-90):
```python
# Current hybrid logic
result = []
if top_related:
    result.extend(random.sample(top_related, min(3, len(top_related))))
remaining = count - len(result)
if remaining > 0 and other_related:
    result.extend(random.sample(other_related, min(remaining, len(other_related))))
```

With:
```python
# Pure anchor: always show top known stocks for this sector
anchors = PRIORITY_STOCKS.get(sector, [])
result = [s for s in related if s['symbol'] in anchors]
result = result[:count]
if len(result) < count:
    others = [s for s in related if s not in result]
    result.extend(random.sample(others, min(count - len(result), len(others))))
```

**Trim PRIORITY_STOCKS to 8-10 per sector:**
- Technology: AAPL, MSFT, NVDA, GOOGL, META, AVGO, ORCL, AMD
- Healthcare: JNJ, UNH, PFE, ABBV, MRK, TMO, ABT, LLY
- Financial Services: JPM, BAC, WFC, GS, MS, V, MA, AXP  (BRK.B has no page; it is not in stocks.txt)
- Consumer Cyclical: AMZN, TSLA, HD, MCD, NKE, SBUX, TGT, LOW
- Consumer Defensive: WMT, PG, KO, PEP, COST, CL, GIS, K
- Energy: XOM, CVX, COP, SLB, EOG, PXD, MPC, VLO
- Industrials: CAT, BA, HON, UPS, RTX, GE, MMM, DE
- Communication Services: GOOGL, META, NFLX, DIS, CMCSA, T, VZ, TMUS
- Real Estate: AMT, PLD, CCI, EQIX, PSA, O, SPG, WELL
- Utilities: NEE, DUK, SO, D, AEP, EXC, SRE, XEL
- Basic Materials: LIN, APD, ECL, SHW, NEM, FCX, NUE, VMC

After editing, re-run and deploy:
```bash
cd /Users/dave/VSCODE/stockiq
python3 people_also_watch_stocks.py --all
./deploy.sh
```

**SEO benefit:** Every page in a sector funnels internal link equity to the same 5-8 flagship pages → those pages rank higher.

### Live prices (done)
Prices in the cards are filled in live by `website/stock-prices.js` (Lambda price proxy,
refreshes every 5 s). The HTML shows `--` until it loads, and always when a page is opened
from a local file.

---

## 2. Crypto News Integration

### Overview
Add Google News RSS support to `update_stock_news.py` for crypto symbols. Yahoo Finance RSS doesn't work well for crypto.

### Implementation (~30 min total)

**Step 1: Add crypto symbols list** (top of `update_stock_news.py`):
```python
CRYPTO_SYMBOLS = ['BTC', 'BTC-USD', 'ETH', 'ETH-USD', 'SOL', 'SOL-USD', 'XRP', 'XRP-USD', 'ADA', 'ADA-USD', 'DOGE', 'DOGE-USD']
```

**Step 2: Modify `fetch_stock_news()`** — add conditional URL:
```python
if symbol in CRYPTO_SYMBOLS:
    url = f"https://news.google.com/rss/search?q={symbol}"
else:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
```

**Step 3: Add to `COMPANY_NAMES` dict:**
```python
'BTC': 'BITCOIN', 'ETH': 'ETHEREUM', 'SOL': 'SOLANA',
'XRP': 'RIPPLE', 'ADA': 'CARDANO', 'DOGE': 'DOGECOIN',
```

**Step 4:** Create crypto HTML pages in `/website/crypto/` (same template as stock pages).

### When to Implement
- Only once the indexed stock pages (about 957 large caps, Oct 2026) are getting search traffic
  (check Search Console), and traffic reaches 100+ visitors/month
- New crypto pages should follow the same rule as stocks: real data on the page, and noindex
  unless there is enough substance
