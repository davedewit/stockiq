# Future Work

---

## 1. People Also Watch Improvements

### Current State
- 5 sector peers shown per stock page (between `<!-- RELATED_SECTION_START -->` and `<!-- RELATED_SECTION_END -->`)
- Price shows `--` (hardcoded in HTML, never updates)
- Selection is **hybrid: 3 from PRIORITY_STOCKS dict + 2 random** from same sector

### Fix 1: Well-Known Stocks (Do First)
Replace hybrid logic with pure anchor stocks — always show top 5 well-known stocks from the sector.

**File:** `/Users/ddewit/VSCODE/stockiq/people_also_watch_stocks.py`

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
- Financial Services: JPM, BAC, WFC, GS, MS, BRK.B, V, MA
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
cd /Users/ddewit/VSCODE/stockiq
python3 people_also_watch_stocks.py --all
./deploy.sh
```

**SEO benefit:** Every page in a sector funnels internal link equity to the same 5-8 flagship pages → those pages rank higher.

### Fix 2: Live Prices (Do Second, after Fix 1)
Prices are `--` because they're hardcoded static HTML. Add JS to the shared file loaded on stock pages.

**Step 1: Find shared JS file**
```bash
grep -n '<script' /Users/ddewit/VSCODE/website/stocks/AAPL.html
```

**Step 2: Add to that shared file**
```javascript
(function() {
    const cards = document.querySelectorAll('#related-section a[href]');
    if (!cards.length) return;

    cards.forEach(card => {
        const symbol = card.href.split('/').pop().replace('.html', '');
        const priceDiv = card.querySelector('div:last-child');
        if (!priceDiv) return;

        const cached = sessionStorage.getItem('price_' + symbol);
        if (cached) { updatePriceDiv(priceDiv, JSON.parse(cached)); return; }

        fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1d`)
            .then(r => r.json())
            .then(data => {
                const meta = data.chart.result[0].meta;
                const price = meta.regularMarketPrice;
                const prev = meta.chartPreviousClose;
                const pct = ((price - prev) / prev * 100).toFixed(2);
                const info = { price, pct };
                sessionStorage.setItem('price_' + symbol, JSON.stringify(info));
                updatePriceDiv(priceDiv, info);
            })
            .catch(() => {});
    });

    function updatePriceDiv(div, info) {
        const color = info.pct >= 0 ? '#00c853' : '#ff1744';
        const sign = info.pct >= 0 ? '+' : '';
        div.style.color = color;
        div.textContent = `$${info.price.toFixed(2)} ${sign}${info.pct}%`;
    }
})();
```

Target display: `$182.45 +1.2%` (green) or `$182.45 -0.8%` (red)

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
- Stock pages reach 50%+ indexing (currently ~17%)
- Traffic grows to 100+ visitors/month
- Don't implement while stock pages are still under 30% indexed
