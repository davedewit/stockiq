# Nikkei 225 Screener — Implementation Plan

## Architecture findings (from code exploration)

**Critical discovery:** The frontend does NOT route option 4/5 screeners through the
`stockiq-screener-coordinator` Lambda. Instead, `analysis-functions.js` directly calls each
worker Lambda URL, assembles the results, and formats them inline. The coordinator
`WORKER_URLS` / `STOCK_UNIVERSES` dicts are irrelevant for this screener.

**How the existing pattern works (option 5, ASX 300 as closest template):**

1. `analysis.html` button: `onclick="runAnalysis(5, '300', event)"`
2. `analysis-functions.js` catches `option === 5 && subOption === '300'` (around line 2364)
3. It has a hard-coded stock universe array and 30 worker URLs
4. It splits the universe into batches of 10 and fires all workers with `Promise.all`
5. Results are sorted and formatted via `formatASXResult(apiData, subOption)`
6. A separate `screenerMappings` dict (around line 635) maps a display name to a URL for
   bookmarking/auto-run: `'ASX 300 Screener': 'analysis.html?option=5&subOption=300&autorun=true'`
7. A `companyName` lookup in the usage-counter section (around line 3033) maps subOption to
   a display string

**Japan coordinator key (for reference / future use):**  
If the coordinator is ever used, the key would be `'5-nikkei225'` (formed as
`f"{option}-{sub_option}"` = `f"5-nikkei225"`). The existing Asia screener keys follow the
same rule: `'4-50'` comes from `option=4, subOption='50'`… except the HTML buttons actually
say `option=5` and `subOption='50'`. This mismatch exists because the frontend bypasses the
coordinator entirely for option 4 and 5 — so the coordinator key is never actually used for
these screeners. **Do not add a coordinator key for Japan** — it would be dead code.

---

## Coordinator changes (NONE needed)

The coordinator Lambda (`stockiq-screener-coordinator`) does **not** need to be modified.
The frontend calls workers directly. Adding entries to `WORKER_URLS` / `STOCK_UNIVERSES` in
the coordinator would be unused code.

---

## Worker naming convention

Existing groups:
- `stockiq-asia-5-1-worker-{1..5}` → ASX 50 (5 workers)
- `stockiq-asia-5-2-worker-{1..10}` → ASX 100 (10 workers)
- `stockiq-asia-5-3-worker-{1..20}` → ASX 200 (20 workers)
- `stockiq-asia-5-4-worker-{1..30}` → ASX 300 (30 workers)

**Japan = group `asia-5-5`**:
- `stockiq-asia-5-5-worker-1` through `stockiq-asia-5-5-worker-21`
- 21 workers × 10 stocks = 210 stocks

---

## Duplicate check

All 210 stock symbols across the 21 batches are unique. No duplicates found.

---

## Stock universe — 21 batches × 10 stocks

```
Batch 1  (worker-1):  6758.T, 6861.T, 6902.T, 6954.T, 6971.T, 6976.T, 8035.T, 6857.T, 6920.T, 6723.T
Batch 2  (worker-2):  6762.T, 6841.T, 6869.T, 6963.T, 6506.T, 6645.T, 6702.T, 6701.T, 6752.T, 6501.T
Batch 3  (worker-3):  6503.T, 6504.T, 6526.T, 6770.T, 6724.T, 6967.T, 6844.T, 6845.T, 6849.T, 6674.T
Batch 4  (worker-4):  6707.T, 7735.T, 4704.T, 4812.T, 6807.T, 9432.T, 9433.T, 9984.T, 4689.T, 4755.T
Batch 5  (worker-5):  6098.T, 4385.T, 2413.T, 7751.T, 7731.T, 7974.T, 7832.T, 9766.T, 7752.T, 4901.T
Batch 6  (worker-6):  7203.T, 7267.T, 7269.T, 7270.T, 7201.T, 7202.T, 7205.T, 7211.T, 7261.T, 7272.T
Batch 7  (worker-7):  5108.T, 5110.T, 7011.T, 7013.T, 7012.T, 6301.T, 6326.T, 6361.T, 6471.T, 6481.T
Batch 8  (worker-8):  8306.T, 8316.T, 8411.T, 8308.T, 8309.T, 8331.T, 8354.T, 7186.T, 8604.T, 8601.T
Batch 9  (worker-9):  8630.T, 8725.T, 8750.T, 8795.T, 8766.T, 8697.T, 8802.T, 8830.T, 3289.T, 3003.T
Batch 10 (worker-10): 1925.T, 1928.T, 8905.T, 4502.T, 4503.T, 4507.T, 4519.T, 4523.T, 4528.T, 4543.T
Batch 11 (worker-11): 4578.T, 4568.T, 4151.T, 4506.T, 4063.T, 4183.T, 4188.T, 4208.T, 4452.T, 4911.T
Batch 12 (worker-12): 3407.T, 3436.T, 5201.T, 5214.T, 5232.T, 5233.T, 5301.T, 5332.T, 5333.T, 5401.T
Batch 13 (worker-13): 5406.T, 5411.T, 5713.T, 5711.T, 5706.T, 5714.T, 5802.T, 5801.T, 5803.T, 2502.T
Batch 14 (worker-14): 2503.T, 2801.T, 2802.T, 2914.T, 2269.T, 2282.T, 2501.T, 2871.T, 2270.T, 9983.T
Batch 15 (worker-15): 9843.T, 3382.T, 8267.T, 3099.T, 3086.T, 7453.T, 3197.T, 3543.T, 8136.T, 1605.T
Batch 16 (worker-16): 5019.T, 5020.T, 9501.T, 9502.T, 9503.T, 9531.T, 9532.T, 9020.T, 9021.T, 9022.T
Batch 17 (worker-17): 9202.T, 9201.T, 9064.T, 9147.T, 9101.T, 9104.T, 9107.T, 1801.T, 1802.T, 1803.T
Batch 18 (worker-18): 1812.T, 1963.T, 8001.T, 8002.T, 8015.T, 8031.T, 8053.T, 8058.T, 2768.T, 7911.T
Batch 19 (worker-19): 7912.T, 4661.T, 6178.T, 4739.T, 6367.T, 6302.T, 6305.T, 6363.T, 6370.T, 6473.T
Batch 20 (worker-20): 6588.T, 6703.T, 6708.T, 6853.T, 7004.T, 7003.T, 5631.T, 5541.T, 1808.T, 6366.T
Batch 21 (worker-21): 6756.T, 6755.T, 6753.T, 6767.T, 6773.T, 9681.T, 4565.T, 8616.T, 8698.T, 3034.T
```

---

## Implementation Plan

### Step 1 — Create 21 worker Lambda functions on AWS

Use `stockiq-asia-5-1-worker-1` as the code template (identical Lambda code for all workers).

**For each worker, run these three commands (substitute N = 1..21):**

```bash
# Download template code once
aws lambda get-function \
  --function-name stockiq-asia-5-1-worker-1 \
  --profile default --region us-east-1 \
  --query 'Code.Location' --output text \
  | xargs curl -s -o /tmp/worker_template.zip

mkdir -p /tmp/nikkei_worker
unzip -o /tmp/worker_template.zip -d /tmp/nikkei_worker/
cd /tmp/nikkei_worker
zip lambda_function.zip lambda_function.py
```

Then for N in 1..21:

```bash
aws lambda create-function \
  --function-name stockiq-asia-5-5-worker-N \
  --runtime python3.12 \
  --role arn:aws:iam::114366766218:role/acp-lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb:///tmp/nikkei_worker/lambda_function.zip \
  --timeout 60 \
  --memory-size 256 \
  --profile default --region us-east-1

aws lambda create-function-url-config \
  --function-name stockiq-asia-5-5-worker-N \
  --auth-type NONE \
  --cors '{"AllowOrigins":["*"],"AllowMethods":["POST","OPTIONS"],"AllowHeaders":["*"]}' \
  --profile default --region us-east-1
```

After creating each function, retrieve its URL:

```bash
aws lambda get-function-url-config \
  --function-name stockiq-asia-5-5-worker-N \
  --profile default --region us-east-1 \
  --query 'FunctionUrl' --output text
```

Record the 21 URLs — they will be embedded in `analysis-functions.js` in Step 2.

**Convenience script** (creates all 21 in one shot, saves URLs to /tmp/nikkei_urls.txt):

```bash
#!/bin/bash
set -e

# One-time: get template code
aws lambda get-function \
  --function-name stockiq-asia-5-1-worker-1 \
  --profile default --region us-east-1 \
  --query 'Code.Location' --output text \
  | xargs curl -s -o /tmp/worker_template.zip

mkdir -p /tmp/nikkei_worker
cd /tmp/nikkei_worker
unzip -o /tmp/worker_template.zip
zip lambda_function.zip lambda_function.py

rm -f /tmp/nikkei_urls.txt

for N in $(seq 1 21); do
  FNAME="stockiq-asia-5-5-worker-$N"
  echo "Creating $FNAME..."

  aws lambda create-function \
    --function-name "$FNAME" \
    --runtime python3.12 \
    --role arn:aws:iam::114366766218:role/acp-lambda-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb:///tmp/nikkei_worker/lambda_function.zip \
    --timeout 60 \
    --memory-size 256 \
    --profile default --region us-east-1 \
    --query 'FunctionArn' --output text

  aws lambda create-function-url-config \
    --function-name "$FNAME" \
    --auth-type NONE \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["POST","OPTIONS"],"AllowHeaders":["*"]}' \
    --profile default --region us-east-1 \
    --query 'FunctionUrl' --output text \
    >> /tmp/nikkei_urls.txt
done

echo "Done. URLs saved to /tmp/nikkei_urls.txt"
cat /tmp/nikkei_urls.txt
```

---

### Step 2 — Edit `analysis-functions.js`

File: `/Users/dave/VSCODE/website/analysis-functions.js`

There are **five places** to add Japan support.

#### 2a. Add handler block (insert after the ASX 300 handler, before the `option === 4 && subOption === 'ftse100'` block, around line 2441)

Insert the following block. Replace the 21 placeholder URLs with the real URLs recorded in Step 1.

```javascript
        } else if (option === 5 && subOption === 'nikkei225') {
            // Check access for authenticated users
            if (typeof authManager !== 'undefined' && authManager.isAuthenticated()) {
                const canAccess = await authManager.checkStockAnalysisAccess();
                if (!canAccess) return;
            }
            console.log('🚀 OPTION 5.5 SMART SCALING - Japan Nikkei 225 Stock Screener');
            const nikkei225Universe = [
                '6758.T','6861.T','6902.T','6954.T','6971.T','6976.T','8035.T','6857.T','6920.T','6723.T',
                '6762.T','6841.T','6869.T','6963.T','6506.T','6645.T','6702.T','6701.T','6752.T','6501.T',
                '6503.T','6504.T','6526.T','6770.T','6724.T','6967.T','6844.T','6845.T','6849.T','6674.T',
                '6707.T','7735.T','4704.T','4812.T','6807.T','9432.T','9433.T','9984.T','4689.T','4755.T',
                '6098.T','4385.T','2413.T','7751.T','7731.T','7974.T','7832.T','9766.T','7752.T','4901.T',
                '7203.T','7267.T','7269.T','7270.T','7201.T','7202.T','7205.T','7211.T','7261.T','7272.T',
                '5108.T','5110.T','7011.T','7013.T','7012.T','6301.T','6326.T','6361.T','6471.T','6481.T',
                '8306.T','8316.T','8411.T','8308.T','8309.T','8331.T','8354.T','7186.T','8604.T','8601.T',
                '8630.T','8725.T','8750.T','8795.T','8766.T','8697.T','8802.T','8830.T','3289.T','3003.T',
                '1925.T','1928.T','8905.T','4502.T','4503.T','4507.T','4519.T','4523.T','4528.T','4543.T',
                '4578.T','4568.T','4151.T','4506.T','4063.T','4183.T','4188.T','4208.T','4452.T','4911.T',
                '3407.T','3436.T','5201.T','5214.T','5232.T','5233.T','5301.T','5332.T','5333.T','5401.T',
                '5406.T','5411.T','5713.T','5711.T','5706.T','5714.T','5802.T','5801.T','5803.T','2502.T',
                '2503.T','2801.T','2802.T','2914.T','2269.T','2282.T','2501.T','2871.T','2270.T','9983.T',
                '9843.T','3382.T','8267.T','3099.T','3086.T','7453.T','3197.T','3543.T','8136.T','1605.T',
                '5019.T','5020.T','9501.T','9502.T','9503.T','9531.T','9532.T','9020.T','9021.T','9022.T',
                '9202.T','9201.T','9064.T','9147.T','9101.T','9104.T','9107.T','1801.T','1802.T','1803.T',
                '1812.T','1963.T','8001.T','8002.T','8015.T','8031.T','8053.T','8058.T','2768.T','7911.T',
                '7912.T','4661.T','6178.T','4739.T','6367.T','6302.T','6305.T','6363.T','6370.T','6473.T',
                '6588.T','6703.T','6708.T','6853.T','7004.T','7003.T','5631.T','5541.T','1808.T','6366.T',
                '6756.T','6755.T','6753.T','6767.T','6773.T','9681.T','4565.T','8616.T','8698.T','3034.T'
            ];
            const allWorkerUrls = [
                'WORKER_1_URL_HERE',   // stockiq-asia-5-5-worker-1
                'WORKER_2_URL_HERE',   // stockiq-asia-5-5-worker-2
                'WORKER_3_URL_HERE',   // stockiq-asia-5-5-worker-3
                'WORKER_4_URL_HERE',   // stockiq-asia-5-5-worker-4
                'WORKER_5_URL_HERE',   // stockiq-asia-5-5-worker-5
                'WORKER_6_URL_HERE',   // stockiq-asia-5-5-worker-6
                'WORKER_7_URL_HERE',   // stockiq-asia-5-5-worker-7
                'WORKER_8_URL_HERE',   // stockiq-asia-5-5-worker-8
                'WORKER_9_URL_HERE',   // stockiq-asia-5-5-worker-9
                'WORKER_10_URL_HERE',  // stockiq-asia-5-5-worker-10
                'WORKER_11_URL_HERE',  // stockiq-asia-5-5-worker-11
                'WORKER_12_URL_HERE',  // stockiq-asia-5-5-worker-12
                'WORKER_13_URL_HERE',  // stockiq-asia-5-5-worker-13
                'WORKER_14_URL_HERE',  // stockiq-asia-5-5-worker-14
                'WORKER_15_URL_HERE',  // stockiq-asia-5-5-worker-15
                'WORKER_16_URL_HERE',  // stockiq-asia-5-5-worker-16
                'WORKER_17_URL_HERE',  // stockiq-asia-5-5-worker-17
                'WORKER_18_URL_HERE',  // stockiq-asia-5-5-worker-18
                'WORKER_19_URL_HERE',  // stockiq-asia-5-5-worker-19
                'WORKER_20_URL_HERE',  // stockiq-asia-5-5-worker-20
                'WORKER_21_URL_HERE'   // stockiq-asia-5-5-worker-21
            ];
            console.log('🧠 Dynamic allocation: 210 base stocks → 21 workers × 10 stocks each');
            console.log('📊 Processing 210 stocks (21 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 21 workers for 210 Japan Nikkei stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 21; i++) {
                const startIdx = i * 10;
                const stockBatch = nikkei225Universe.slice(startIdx, startIdx + 10);
                workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 21/21 workers for 210 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.stock_batch.length} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 21 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result && workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 Japan Nikkei 225 Analysis: ${allResults.length}/210 stocks (${((allResults.length/210)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 210, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'Japan_Nikkei225_Screener');
            result = formatNikkeiResult(apiData);
            result.csvData = csvData;
```

#### 2b. Add `screenerMappings` entry (around line 635, inside the `screenerMappings` object)

Add after the `'ASX 300 Screener'` entry:

```javascript
        'Japan Nikkei 225 Screener': 'analysis.html?option=5&subOption=nikkei225&autorun=true',
```

#### 2c. Add `companyName` mapping (around line 3033, inside the `option === 5` block in the usage-counter section)

Inside the `subNames` object for option 5:

```javascript
            const subNames = {
                '50': 'ASX 50 Screener',
                '100': 'ASX 100 Screener',
                '200': 'ASX 200 Screener',
                '300': 'ASX 300 Screener',
                'nikkei225': 'Japan Nikkei 225 Screener'   // ADD THIS LINE
            };
```

#### 2d. Add `uniqueSymbolsCount` mapping (around line 3033, inside the `option === 5` block in the usage-counter section)

The block that maps subOptions to `uniqueSymbolsCount` for option 5 needs a `nikkei225` case:

```javascript
            } else if (subOption === '300') {
                symbols = ['ASX_SCREENER'];
                uniqueSymbolsCount = 300;
            } else if (subOption === 'nikkei225') {   // ADD THIS BLOCK
                symbols = ['JAPAN_SCREENER'];
                uniqueSymbolsCount = 210;
            } else {
```

#### 2e. Add `formatNikkeiResult` function

Add this new function near `formatASXResult` (after it, around line 3860-ish):

```javascript
function formatNikkeiResult(apiData) {
    const universeSize = 210;
    let output = `
============================================================
🇯🇵 JAPAN NIKKEI 225 RESULTS (REAL-TIME DATA)
============================================================
Screening Universe: ${universeSize} Japan Nikkei stocks
Market Type: Tokyo Stock Exchange
Universe Size: ${universeSize}
Analysis Date: ${new Date().toLocaleString()}
`;
    if (apiData.results && apiData.results.length > 0) {
        const sortedResults = [...apiData.results].sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
        const topCount = Math.min(10, sortedResults.length);
        output += `🟢 TOP ${topCount} BUY OPPORTUNITIES:\n`;
        sortedResults.slice(0, topCount).forEach((stock, i) => {
            const symbol = (stock.symbol || 'N/A').padEnd(8);
            const price = `¥${(stock.current_price || stock.price || 0).toFixed(0)}`.padStart(10);
            const score = (stock.total_score || stock.score || 0) >= 0 ? `+${(stock.total_score || stock.score || 0).toFixed(1)}` : `${(stock.total_score || stock.score || 0).toFixed(1)}`;
            const rsi = (stock.rsi || 0).toFixed(1).padStart(5);
            const ytd = (stock.ytd_change || 0) >= 0 ? `+${(stock.ytd_change || 0).toFixed(1)}%` : `${(stock.ytd_change || 0).toFixed(1)}%`;
            const vol = `${(stock.volume_ratio || 1).toFixed(1)}x`;
            output += `${(i+1).toString().padStart(2)}. ${symbol} ${price} | Score: ${score} | RSI: ${rsi} | YTD: ${ytd}, Vol: ${vol}\n`;
        });
        output += '\n</pre><div style="margin: 20px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;">📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.</div><pre style="white-space: pre-wrap; font-family: monospace;">\n🎯 TOP 3 DETAILED ANALYSIS:\n';
        output += '================================================================\n';
        sortedResults.slice(0, 3).forEach((stock, i) => {
            output += `${i+1}. ${stock.symbol}: ¥${(stock.price || 0).toFixed(0)} | ${stock.recommendation || 'HOLD'} | Score: ${(stock.total_score || stock.score || 0) >= 0 ? '+' : ''}${(stock.total_score || stock.score || 0).toFixed(1)}\n`;
            if (stock.score_breakdown && stock.score_breakdown.length > 0) {
                output += '   📊 Score Breakdown:\n';
                stock.score_breakdown.forEach(breakdown => {
                    output += `      ${breakdown}\n`;
                });
            }
            output += `   📈 Technical: RSI ${(stock.rsi || 50).toFixed(1)} | MACD ${stock.macd_signal || 'NEUTRAL'}\n`;
            output += `   💰 Levels: Support ¥${(stock.support || 0).toFixed(0)} | Resistance ¥${(stock.resistance || 0).toFixed(0)}\n`;
            output += `   🎯 Targets: Stop ¥${(stock.stop_loss || 0).toFixed(0)} | Take Profit ¥${(stock.take_profit || 0).toFixed(0)}\n`;
            output += `   📊 Strategy: ${stock.strategy_type || 'N/A'} | Confidence: ${(stock.confidence || 0).toFixed(0)}%\n\n`;
        });
        const positiveStocks = sortedResults.filter(s => (s.total_score || s.score || 0) > 0).length;
        const negativeStocks = sortedResults.filter(s => (s.total_score || s.score || 0) < 0).length;
        const avgScore = sortedResults.reduce((sum, s) => sum + (s.total_score || s.score || 0), 0) / sortedResults.length;
        output += `\n📊 ANALYSIS SUMMARY:\n`;
        output += `• Total stocks analyzed: ${sortedResults.length}\n`;
        output += `• Stocks with positive scores: ${positiveStocks}\n`;
        output += `• Stocks with negative scores: ${negativeStocks}\n`;
        output += `• Average score: ${avgScore.toFixed(1)}\n`;
        output += `• Success rate: ${((sortedResults.length/universeSize)*100).toFixed(1)}%\n`;
    } else {
        output += 'No results available\n';
    }
    output += `\n✅ Real-time Japan Nikkei 225 complete!`;
    return { type: 'option_5nikkei225_screener', data: output };
}
```

---

### Step 3 — Edit `analysis.html`

File: `/Users/dave/VSCODE/website/analysis.html`

**Replace** (line ~518):
```html
                    <button class="screener-btn coming-soon" onclick="showComingSoonPopup()">🇯🇵 Japan (Nikkei 225) - Coming Soon</button>
```

**With:**
```html
                    <button class="screener-btn" onclick="runAnalysis(5, 'nikkei225', event)">🇯🇵 Japan (Nikkei 225) (210 stocks)</button>
```

---

## Summary of all changes

| What | File | Status |
|------|------|--------|
| Create 21 worker Lambdas with Function URLs | AWS console / CLI | New |
| `else if (option === 5 && subOption === 'nikkei225')` handler block | `analysis-functions.js` | New |
| `screenerMappings` entry for Nikkei | `analysis-functions.js` | New |
| `companyName` subNames entry | `analysis-functions.js` | New |
| `uniqueSymbolsCount` entry | `analysis-functions.js` | New |
| `formatNikkeiResult()` function | `analysis-functions.js` | New |
| Replace Coming Soon button | `analysis.html` | Edit |
| Coordinator Lambda | `stockiq-screener-coordinator` | **No changes needed** |

---

## Notes

- **Coordinator not involved.** All option 4/5 screeners call workers directly from the
  browser. The coordinator key `'5-nikkei225'` would never be called, so it is not added.
- **Worker code is identical** to the existing Asia workers. No code modification needed.
- **Japanese stock prices from Yahoo Finance** come back in JPY. The worker returns raw
  `current_price` / `price` values. `formatNikkeiResult` formats them with `¥` and `toFixed(0)`
  (JPY trades in whole numbers, not cents).
- **Sector classification** for `.T` symbols will fall through to `'OTHER'` in the worker's
  `get_sector_info()` function — this is the same as any unlisted stock and does not affect
  the analysis score.
- **After creating the 21 functions**, run the deploy to push `analysis-functions.js` and
  `analysis.html` to S3: `cd /Users/dave/VSCODE/stockiq && ./deploy-to-s3.sh`
