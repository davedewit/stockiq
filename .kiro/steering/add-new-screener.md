# Add New Screener

Complete step-by-step guide for adding a new regional screener (e.g. India BSE Sensex).
Based on the Japan Nikkei 225 build (Oct 2026). Read this before starting.

---

## Architecture Overview

Each screener = N worker Lambdas (10 stocks each) + coordinator routing + frontend UI + dashboard wiring.

```
analysis.html button
    → runAnalysis(option, subOption)
    → calls N workers in parallel (directly from browser)
    → results aggregated in formatXxxResult()
    → saved to DynamoDB via saveAnalysisToHistory()

dashboard "Run in Background"
    → processAnalysisGroup()
    → POST to stockiq-screener-coordinator { option, subOption, userId }
    → coordinator calls N workers in parallel (server-side)
    → saves result to user's dashboard history
```

Key files touched for every new screener:
- `/Users/dave/VSCODE/website/analysis-functions.js` — runAnalysis handler + formatter
- `/Users/dave/VSCODE/website/analysis.html` — button
- `/Users/dave/VSCODE/website/dashboard.html` — getAnalysisKey, getSubOptionFromCompanyName, screenerMappings
- `/Users/dave/VSCODE/stockiq/lambda-sync/stockiq-screener-coordinator/lambda_function.py` — WORKER_URLS, STOCK_UNIVERSES, titles, universe_sizes

---

## Step 1 — Plan

Decide:
- **Option number** — new Asia/Pacific screeners go under **option 5**; coordinator key is
  `5-<subOption>` (e.g. `5-sensex`). Legacy screeners are inconsistent (the frontend sends ASX as
  option 5 subOption 50..300 but the coordinator keys are `4-50`..`4-300`; FTSE is frontend option 4
  but coordinator `5-ftse100`). Don't copy those; follow the Nikkei pattern where frontend,
  dashboard and coordinator all use `5` + the same subOption string.
- **subOption string** — e.g. `nikkei225`, `sensex`, `kospi`
- **Stock list** — get the official index constituents. Verify they work on Yahoo Finance with the
  correct suffix (`.T`=Tokyo, `.BO`=Bombay/BSE, `.NS`=NSE India, `.KS`=Korea, `.HK`=Hong Kong).
- **Worker count** — ceil(stocks / 10). E.g. 30 BSE Sensex stocks = 3 workers, 50 = 5 workers.
- **Worker naming** — follow the pattern: `stockiq-asia-5-5-worker-N` was Nikkei.
  Next Asia group would be `stockiq-asia-5-6-worker-N`.

### Verify stocks work on Yahoo Finance before building
```bash
python3 -c "
import yfinance as yf
symbols = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']  # test a few
for s in symbols:
    info = yf.Ticker(s).info
    print(s, info.get('shortName', 'NOT FOUND'))
"
```
If they return "NOT FOUND" don't proceed — the workers will get no data.

Also check the final list has the expected count and **no duplicates** (Nikkei: 210 unique, all
verified; the index nominally has 225 but only 210 were valid Yahoo symbols — report the real count
to the owner, who asked about this):
```python
print(len(stocks), len(set(stocks)))   # both must match
```
Use the official index constituent list and say where it came from; don't invent tickers from memory
without verifying each on Yahoo.

---

## Step 2 — Create Worker Lambdas on AWS

### 2a. Get the base worker code
Copy from the existing non-US worker (handles `.T`, `.AX`, `.L`, `.BO`, `.NS` etc.):
```bash
ls -d /Users/dave/VSCODE/stockiq/lambda-sync/stockiq-asia-5-5-worker-*/
# The local mirror keeps ONE worker per group (duplicates are skipped), so the folder is
# whichever number was synced, e.g. stockiq-asia-5-5-worker-10. It contains lambda_function.py
```

### 2b. Create all workers in one go
```bash
cd /Users/dave/VSCODE/stockiq/lambda-sync/stockiq-asia-5-5-worker-*/  # the one Nikkei worker in the mirror
zip /tmp/worker.zip lambda_function.py

TOTAL_WORKERS=3   # adjust to ceil(stocks/10)
GROUP="stockiq-asia-5-6"   # adjust group name

for i in $(seq 1 $TOTAL_WORKERS); do
  echo "Creating worker $i..."
  aws lambda create-function \
    --function-name ${GROUP}-worker-${i} \
    --runtime python3.12 \
    --role arn:aws:iam::114366766218:role/acp-lambda-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb:///tmp/worker.zip \
    --timeout 60 \
    --memory-size 256 \
    --profile default --region us-east-1 \
    --query 'FunctionName' --output text
done
```

### 2c. Add Function URLs to all workers
```bash
for i in $(seq 1 $TOTAL_WORKERS); do
  aws lambda create-function-url-config \
    --function-name ${GROUP}-worker-${i} \
    --auth-type NONE \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["*"],"AllowHeaders":["*"]}' \
    --profile default --region us-east-1 \
    --query 'FunctionUrl' --output text
done
```

### 2d. Add public invoke permissions (CRITICAL — workers return 403 without this)
```bash
for i in $(seq 1 $TOTAL_WORKERS); do
  aws lambda add-permission \
    --function-name ${GROUP}-worker-${i} \
    --statement-id AllowPublicAccess \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type NONE \
    --profile default --region us-east-1
done
```

### 2e. Collect the Function URLs
```bash
for i in $(seq 1 $TOTAL_WORKERS); do
  echo -n "worker-${i}: "
  aws lambda get-function-url-config \
    --function-name ${GROUP}-worker-${i} \
    --profile default --region us-east-1 \
    --query 'FunctionUrl' --output text
done
```

---

## Step 3 — Update the Coordinator Lambda

File: `/Users/dave/VSCODE/stockiq/lambda-sync/stockiq-screener-coordinator/lambda_function.py`

### 3a. Add to WORKER_URLS dict
```python
'5-sensex': [  # India BSE Sensex - 3 workers
    'https://<worker-1-url>.lambda-url.us-east-1.on.aws/',
    'https://<worker-2-url>.lambda-url.us-east-1.on.aws/',
    'https://<worker-3-url>.lambda-url.us-east-1.on.aws/'
],
```

### 3b. Add to STOCK_UNIVERSES dict
```python
'5-sensex': ['RELIANCE.BO','TCS.BO','INFY.BO', ...],  # all N stocks
```

### 3c. Add to titles dict (appears twice in file — update both)
```python
'5-sensex': 'India BSE Sensex Screener'
```

### 3d. Add to universe_sizes dict (appears twice in file — update both)
```python
'5-sensex': 30  # actual stock count
```

### 3e. Deploy the coordinator
```bash
cd /Users/dave/VSCODE/stockiq/lambda-sync/stockiq-screener-coordinator
zip lambda_function.zip lambda_function.py
aws lambda update-function-code \
  --function-name stockiq-screener-coordinator \
  --zip-file fileb://lambda_function.zip \
  --profile default --region us-east-1
rm lambda_function.zip
```

---

## Step 4 — Update analysis-functions.js

File: `/Users/dave/VSCODE/website/analysis-functions.js`

### 4a. Add the runAnalysis handler
Find the `} else if (option === 5 && subOption === 'nikkei225') {` block and add a similar block after it:

```javascript
} else if (option === 5 && subOption === 'sensex') {
    if (typeof authManager !== 'undefined' && authManager.isAuthenticated()) {
        const canAccess = await authManager.checkStockAnalysisAccess();
        if (!canAccess) return;
    }
    console.log('🚀 OPTION 5.6 - India BSE Sensex Screener');
    const sensexUniverse = ['RELIANCE.BO', 'TCS.BO', ...];  // all stocks
    const allWorkerUrls = [
        'https://<worker-1>.lambda-url.us-east-1.on.aws/',
        ...
    ];
    // ... dispatch pattern identical to nikkei225 block
```

The dispatch pattern is the same for all non-US screeners — copy the nikkei225 block and adjust
the universe, worker URLs, worker count, and call the appropriate formatter.

### 4b. Add a company names dict
```javascript
const SENSEX_COMPANY_NAMES = {
    'RELIANCE.BO': 'Reliance Industries',
    'TCS.BO': 'Tata Consultancy Services',
    ...
};
```

### 4c. Add a formatter function
Copy `formatNikkeiResult()` and adapt:
- Change `NIKKEI_COMPANY_NAMES` → `SENSEX_COMPANY_NAMES`
- Change currency symbol `¥` → `₹`
- Change header text
- Change `result.type = 'option_5nikkei225_screener'`  → `'option_5sensex_screener'`
- Change `result.companyName = 'Japan Nikkei 225 Screener'` → `'India BSE Sensex Screener'`

### 4d. Three more lookups in analysis-functions.js (easy to miss — grep `nikkei225` to find them)
All three are keyed on the subOption/company name; without them history saving and re-run break:
1. **Re-run URL map** (~line 639, `'Japan Nikkei 225 Screener': 'analysis.html?option=5&subOption=nikkei225&autorun=true'`)
   → add `'India BSE Sensex Screener': 'analysis.html?option=5&subOption=sensex&autorun=true'`
2. **saveAnalysisToHistory symbols** (~line 3141, inside `option === 5`):
   ```javascript
   } else if (subOption === 'sensex') { symbols = ['INDIA_SCREENER']; uniqueSymbolsCount = 30; }
   ```
   Must go before the final `else` (which falls back to `ASIA_MARKETS`).
3. **subNames map** (~line 3206): `'sensex': 'India BSE Sensex Screener'` — otherwise the saved
   history entry is titled "ASX Stock Screener".

**Important:** `const name` is declared once per forEach loop — do NOT declare it twice (caused a
site-breaking SyntaxError on Nikkei build). Always run `node -c analysis-functions.js` after editing.

---

## Step 5 — Update analysis.html

File: `/Users/dave/VSCODE/website/analysis.html`

Find the "Coming Soon" button for the new screener and activate it:
```html
<!-- Before -->
<button class="screener-btn coming-soon" onclick="showComingSoonPopup()">🇮🇳 India (BSE Sensex) - Coming Soon</button>

<!-- After -->
<button class="screener-btn" onclick="runAnalysis(5, 'sensex', event)">🇮🇳 India (BSE Sensex) (30 stocks)</button>
```

---

## Step 6 — Update dashboard.html

File: `/Users/dave/VSCODE/website/dashboard.html`

Four places to update:

### 6a. getAnalysisKey() — recognise the result type
```javascript
if (companyName.includes('India BSE') || symbol === 'INDIA_SCREENER') return 'india_screener';
```

Place the check **before** the generic ones in that function (Japan sits above `includes('ASX')`).

### 6b. getSubOptionFromCompanyName() — for re-run URL
```javascript
'India BSE Sensex Screener': 'sensex',
```

### 6c. screenerMappings in getRerunUrl() — for refresh button
```javascript
'India BSE Sensex Screener': 'analysis.html?option=5&subOption=sensex&autorun=true',
'India BSE Sensex Analysis': 'analysis.html?option=5&subOption=sensex&autorun=true',  // Japan has both names
```

### 6e. trackScreenerPerformance() regex — currency symbol (🎯 button)
Two regexes (~line 3612) use the currency class `[$£€¥]`. **`₹` is not in it**, so India's 🎯 button
finds no symbols. Add `₹` to both: `[$£€¥₹]`. (Same for any new currency, e.g. `₩` for Korea.)
The `.{0,30}?` that bridges the company name is already there (Japan fix) — keep it.

### 6d. processAnalysisGroup() — for "Run in Background"
```javascript
} else if (analysisType === 'india_screener') {
    endpoint = coordinatorUrl;
    payload = { option: '5', subOption: 'sensex', userId };
}
```
Add this alongside the existing `japan_screener` block.

---

## Step 7 — Deploy

```bash
# 1. Verify JS syntax first
node -c /Users/dave/VSCODE/website/analysis-functions.js

# 2. Upload changed files
cd /Users/dave/VSCODE/website
aws s3 cp analysis-functions.js s3://stockiq-final-websitebucket-vqekic7enf9h/analysis-functions.js \
  --cache-control "public, max-age=86400" --profile default --region us-east-1
aws s3 cp analysis.html s3://stockiq-final-websitebucket-vqekic7enf9h/analysis.html \
  --cache-control "public, max-age=3600" --content-type "text/html; charset=utf-8" \
  --profile default --region us-east-1
aws s3 cp dashboard.html s3://stockiq-final-websitebucket-vqekic7enf9h/dashboard.html \
  --cache-control "public, max-age=3600" --content-type "text/html; charset=utf-8" \
  --profile default --region us-east-1

# 3. Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id EHXV50CPHY07R \
  --paths "/analysis-functions.js" "/analysis.html" "/dashboard.html" \
  --profile default --region us-east-1

# 4. Wait for invalidation, then test
```

---

## Testing Checklist

- [ ] Run screener from analysis.html — results appear
- [ ] Results saved to dashboard (check dashboard history)
- [ ] Dashboard 🔄 Refresh button opens analysis.html with autorun
- [ ] Dashboard 🔁 Run in Background completes and updates dashboard (no browser tab opened)
- [ ] Dashboard 🎯 Track Performance button shows price changes for top 10 symbols
- [ ] Notifications show company names (not just ticker symbols)

---

## Existing Screeners Reference

| Screener | Option | subOption | Workers | Stocks | Symbol suffix |
|---|---|---|---|---|---|
| S&P 100 | 3 | 100 | 10 | 100 | (none) |
| S&P 500 | 3 | 3 | 50 | 500 | (none) |
| S&P 1500 | 3 | 4 | 150 | 1500 | (none) |
| Russell 1000 | 3 | 5 | 100 | 1000 | (none) |
| Russell 2000 | 3 | 6 | 200 | 2000 | (none) |
| NASDAQ 100 | 3 | 7 | 10 | 100 | (none) |
| Dow Jones 30 | 3 | 8 | 3 | 30 | (none) |
| ASX 50 | 5 (coordinator `4-50`) | 50 | 5 | 50 | `.AX` |
| ASX 100 | 5 (coordinator `4-100`) | 100 | 10 | 100 | `.AX` |
| ASX 200 | 5 (coordinator `4-200`) | 200 | 20 | 196 | `.AX` |
| ASX 300 | 5 (coordinator `4-300`) | 300 | 30 | 231 | `.AX` |
| UK FTSE 100 | 4 (coordinator `5-ftse100`) | ftse100 | 10 | 100 | `.L` |
| **Japan Nikkei 225** | **5** | **nikkei225** | **21** | **210** | **`.T`** |
| India BSE Sensex | 5 | sensex | 3 (30 stocks) | 30 | `.BO` or `.NS` (test both on Yahoo) |
| South Korea KOSPI | 5 | kospi | TBD | TBD | `.KS` |
| Crypto | 7 | 1 | 1 (orchestrator) | 548 | `-USD` |

---

## Common Pitfalls

| Problem | Cause | Fix |
|---|---|---|
| Workers return 403 | Missing `lambda:InvokeFunctionUrl` permission | Run `aws lambda add-permission` for each worker (Step 2d) |
| "Unknown screener" 400 from coordinator | Key not in WORKER_URLS | Add to coordinator and redeploy |
| No symbols in performance tracker | Company name between symbol and price breaks regex | The regex in `trackScreenerPerformance` uses `.{0,30}?` to bridge company names — keep formatter consistent |
| `Identifier 'name' has already been declared` | `const name` declared twice in same forEach | Declare it once at top of forEach, don't repeat |
| Run in Background opens browser tab instead of running server-side | `processAnalysisGroup` redirecting instead of calling coordinator | Wire it to coordinator like other screeners |
| analysis-functions.js not updating on live site | Deploy script didn't upload root JS files | Upload manually: `aws s3 cp analysis-functions.js s3://...` |
| autorun not triggering on redirect | `selectOption()` timing | The 2s timeout in autorun block handles this — don't reduce it |
