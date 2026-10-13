# Add New Screener

How to add a share screener for another market, written so that a new session can build one from this file alone.
The worked example is **Germany (DAX 40)**; India (BSE Sensex) and South Korea (KOSPI) follow the same steps with the
differences listed in step 1. Rewritten 11 Oct 2026, when every share-screener worker was moved to one package: the
older version of this guide (copy a worker from `lambda-sync/`, type `aws` commands) no longer applies.

Read `site-overview.md` section 8b first (how the screeners work, the two code paths, the output wording rule) and
section 10 (working rules). Three things have changed since the Nikkei build and decide how the work is done:

1. **Workers come from the one package in `stockiq/workers/`** (`build.py`), never from a copy in `lambda-sync/`. A new
   screener needs no worker code at all: the same file serves every market.
2. **Creating functions and deploying anything goes through a packaged `check-tools/pending-<name>/deploy.sh`**, run as
   `bash /Users/dave/VSCODE/stockiq/check-tools/pending-<name>/deploy.sh` with nothing else on the line (dry run:
   `DRY_RUN=true` in front). The session's safety check refuses direct `aws lambda` / `aws s3` changes. Read-only `aws`
   calls are fine.
3. **Testing is scripted** (`check-tools/page_run.js`, `run_all.py`, `analyse.py`, `tracker_run.js`), not a checklist
   worked through in a browser.

---

## What a screener is made of

```
analysis.html button
    → runAnalysis(option, subOption)                         website/analysis-functions.js
    → calls N workers straight from the browser, 10 stocks each
    → a formatter writes the report text; saveAnalysisToHistory() stores it

dashboard "Run in Background"
    → processAnalysisGroup()                                 website/dashboard.html
    → stockiq-screener-coordinator { option, subOption, userId }
    → the coordinator calls the same N workers, writes the report and CSV, saves them
```

| Piece | Where | New for each screener |
|---|---|---|
| Worker functions | AWS, `<group>-1 … <group>-N` | Created from the one package; one line in `workers/groups.py` |
| The stock list | `screeners.js` (the entry's `list`) **and** the coordinator (`STOCK_UNIVERSES`) | The same list in both, no duplicates |
| Page entry and formatter | `screeners.js`, `analysis-functions.js` | An entry in `screeners.js`; in `analysis-functions.js` a names table, a formatter, three lookups |
| Button | `analysis.html` | One line |
| Dashboard wiring | `dashboard.html` | Five small entries |
| Coordinator | `lambda-sync/stockiq-screener-coordinator/lambda_function.py` | Worker addresses, list, title, size |
| Autopilot (optional) | Lambda `stockiq-ai-trader`, chat prompt | A `SCREENERS` line, market hours and name |

---

## Step 1: decide the names, and get the list

| | Germany (DAX 40) | India (BSE Sensex) | South Korea (KOSPI) |
|---|---|---|---|
| Page call | `runAnalysis(5, 'dax40', event)` | `(5, 'sensex', event)` | `(5, 'kospi', event)` |
| Coordinator key | `5-dax40` | `5-sensex` | `5-kospi` |
| Worker group | `stockiq-europe-4-2-worker` | `stockiq-asia-5-6-worker` | `stockiq-asia-5-7-worker` |
| Workers (list ÷ 10, rounded up) | 4 | 3 | by the list |
| Yahoo suffix | `.DE` (Xetra) | `.BO` or `.NS` (try both) | `.KS` |
| Currency Yahoo reports | `EUR` | `INR` | `KRW` |
| Sign in the report | `€` (the tracker already reads it) | `₹` (add it to the tracker, step 6) | `₩` (add it) |
| Index for the Top 10 popup | `^GDAXI` | `^BSESN` | `^KS11` |
| Result type / history name | `option_5dax40_screener` / "Germany DAX 40 Screener" | … | … |
| Market code in the autopilot | `de`, "German shares" | `in`, "Indian shares" | `kr`, "Korean shares" |

- **Use option `5` and the same subOption string everywhere** (page, dashboard, coordinator). The older screeners are
  inconsistent (ASX is page option 5 but coordinator `4-…`; FTSE the reverse): do not copy them, copy Nikkei.
- Worker group names follow `stockiq-<region>-<n>-<m>-worker`: `stockiq-europe-4-1-worker` is FTSE, so the next European
  group is `4-2`; `stockiq-asia-5-5-worker` is Nikkei, so the next Asian group is `5-6`. The name is only a label.
- **The list.** Take the index members from a current source and say where it came from (Wikipedia's index page worked
  for every list rebuilt in Oct 2026; the DAX page has a "Components" table with the Xetra tickers). Turn each into
  Yahoo's form: ticker + `.DE` (`SAP.DE`, `SIE.DE`, `ALV.DE`); a share class written with a dot becomes a dash before the
  suffix, as for London (`BT.A` → `BT-A.L`).
- **Check every symbol through the price proxy, not Yahoo directly** (Yahoo blocks this machine after a few hundred calls,
  and a blocked call looks like a dead symbol). `stockiq-price-proxy` answers `?symbol=SAP.DE` with a price, and HTTP 500
  for a symbol it does not know; its address is in `lambda-url-mapping.json`. `check-tools/lists/build_lists2.py` is the
  script that did this for the other lists. A symbol Yahoo does not know is silently dropped by a worker, so the list
  would simply come out short.
- No duplicates, and report the real count to the owner: `print(len(stocks), len(set(stocks)))` must match. Put the
  **real** count on the button and in the headers, not the index's nominal size.
- Collect the company names too (a short name per symbol, 22 characters at most: the report line and the tracker
  depend on it, step 4).

---

## Step 2: the workers

**2a. One line in `workers/groups.py`** (and a market, if it is new):

```python
GROUPS = { ...
    'stockiq-europe-4-2-worker': ('Germany DAX 40', 4, 'xetra'),
}
MARKETS = { ...
    'xetra': dict(currency='EUR', try_with=['SAP.DE', 'SIE.DE', 'ALV.DE'],
                  sample='SAP.DE SIE.DE ALV.DE DTE.DE AIR.DE MBG.DE BMW.DE BAS.DE MUV2.DE IFX.DE DBK.DE RWE.DE'.split()),
}
```

`currency` is what Yahoo reports for that exchange (check one symbol through the price proxy, or
`python3 workers/stock_worker.py SAP.DE`, which prints it). That one table is read by `workers/deploy.py`,
`workers/prove.py`, `workers/build.py` and `check-tools/workers.py`, so **there is no other list of groups to update**.
Nothing changes in `stock_worker.py`: a Yahoo suffix needs nothing special in the code. (Its `get_sector_info` has small
sector tables for US, ASX and London shares; they are cosmetic, and a market without one is "OTHER".)

**2b. Check the code on the new market before creating anything:**

```bash
cd /Users/dave/VSCODE/stockiq
python3 workers/stock_worker.py SAP.DE SIE.DE ALV.DE      # three calls to Yahoo from this machine: price, EUR, a score each
python3 workers/prove.py --fetch                          # two years of prices for the new market's sample (12 downloads, slowly)
python3 workers/prove.py                                  # the "faults" lines at the end show the new market: sessions sent twice, the currency
```

Commit `workers/groups.py` (the creator and the deploy tool refuse to run with uncommitted changes in `workers/`).

**2c. Create the functions** with a packaged script. `workers/create_group.py` makes each one like the Nikkei workers
(Python 3.12, 256 MB, 60 s, handler `lambda_function.lambda_handler`, role `acp-lambda-role`), gives it an address that
accepts POST from anywhere, adds the public permission (without it the address answers 403), tries the first and last
worker through their addresses, and writes the addresses in order to `urls.txt`:

```bash
mkdir -p check-tools/pending-dax40
cat > check-tools/pending-dax40/deploy.sh <<'EOF'
#!/bin/bash
# Creates the 4 workers of the Germany DAX 40 screener from the one share-screener package (workers/create_group.py).
set -euo pipefail
exec /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/create_group.py stockiq-europe-4-2-worker "$(cd "$(dirname "$0")" && pwd)"
EOF
printf 'workers.zip\n' > check-tools/pending-dax40/.gitignore
git add check-tools/pending-dax40 && git commit -m "DAX 40 screener (work in progress, not live yet): the script that creates its workers"
DRY_RUN=true bash /Users/dave/VSCODE/stockiq/check-tools/pending-dax40/deploy.sh
bash /Users/dave/VSCODE/stockiq/check-tools/pending-dax40/deploy.sh
cat check-tools/pending-dax40/urls.txt
```

`create_group.py` was written on 11 Oct 2026 from the Nikkei workers' real settings and its dry run was run; **it had
not created a function when this was written, so read its output on first use.** It is safe to run twice (a function
that exists is passed over). It only creates: removing functions made by mistake is the owner's decision.

Afterwards `python3 check-tools/workers.py` must list the new group with "one" version and the same code as the other
13 share groups, and from then on the group is updated with every worker deploy (`workers/deploy.py`, `groups.txt`
saying `all`).

---

## Step 3: the coordinator

File: `lambda-sync/stockiq-screener-coordinator/lambda_function.py` (this Lambda's code is not in git, and **the daily
backup does not include Lambda code**: before editing, download the live code and compare it with the mirror, and keep
the live zip in `~/VSCODE/backup/` as the way back. A full copy of every function as of 11 Oct 2026 is in
`~/VSCODE/backup/lambda_full_20261011_before_one_worker_code/`, with a README).

- `WORKER_URLS['5-dax40'] = [ the four addresses from urls.txt, in order ]`
- `STOCK_UNIVERSES['5-dax40'] = [ ... ]`, the same list as on the page
- the titles table: `'5-dax40': 'Germany DAX 40 Screener'` (search for `'5-nikkei225'` and add a line wherever it has one)
- `universe_sizes`: `'5-dax40': 40` (the real count; it appears twice)

The coordinator's report prints the whole symbol and takes each price's sign from the stock's `currency` field through
`money()` (since 11 Oct 2026; `EUR` → `€` is in its table). Add the new key to `market_currency()`, which is only the
fallback for a result without the field. Nothing else in the report writer is per market.

Deploy it with a packaged script of its own (stop if the daily deploy is running; check the live `CodeSha256` is the one
the change was built from; keep the old zip; update; copy into `lambda-sync/`; support `DRY_RUN=true`). The crypto
deploy is the pattern for a single function: `git show 146ffed:check-tools/pending-crypto/deploy.sh` (its orchestrator
half).

---

## Step 4: the page (`website/analysis-functions.js`)

The file is very large: **search, do not read it whole** (`grep -n nikkei225`), and edit by exact replacement.

**4a. The entry.** Since 13 Oct 2026 the page runs every share screener with one routine (`runShareScreener` in
`analysis-functions.js`), and a screener is one entry in **`website/screeners.js`** (`site-overview.md` section 8b, "The
page's one screener routine"). Add:

```js
    '5-dax40': {
        name: 'Germany DAX 40', size: 40, use: 4, csv: 'Germany_DAX40_Screener', format: 'dax', merge: 'guarded', timeText: false,
        list: ['SAP.DE', 'SIE.DE', … ],
        workers: [ the four addresses from urls.txt, in order ]
    },
```

`use` is the number of workers, `size` the number the report prints, `merge: 'guarded'` and `timeText: false` are the
plain choices (as Nikkei has). `format` names the formatter: add one line for it where `runShareScreener` picks the
formatter (`def.format === 'dax' ? formatDAXResult(apiData) : …`). Nothing else changes in `runAnalysis`: no block to
copy, no access check to remember (access is checked and the use counted once, at the top of `runAnalysis`).
**Adding an entry is the point after which the way back to the old 14 copies (`pending-screeners-undo`) no longer
applies by itself.**

**4b. A names table**, `DAX_COMPANY_NAMES = { 'SAP.DE': 'SAP', 'SIE.DE': 'Siemens', … }`, short names.

**4c. The formatter.** Copy `formatNikkeiResult()` and change: the names table; the `universeSize` constant (the real
count); the header text; `type: 'option_5dax40_screener'`; the company name "Germany DAX 40 Screener"; and the fallback
currency. Prices are written with `screenerMoney(stock, value, 'EUR')` (one rule for every share-screener formatter,
above `formatOption3Result`): it takes the sign from the `currency` each stock carries, and the third argument is only
the fallback. Never type a sign into a formatter. If the currency is new, add its sign to `SCREENER_MONEY_SIGNS` there,
to `MONEY_SIGNS` in the coordinator and to the single-stock report's table (the three must stay alike).

Rules the output must keep (section 8b):
- every code goes through `signalLabel()` / `horizonLabel()`; never print `STRONG_BUY` and the like, and none of "buy",
  "sell", "target", "stop loss", "take profit", "picks", "recommendation";
- the top-10 line must stay `N. SYMBOL <name, 22 characters at most> <sign>PRICE …`: the dashboard's 🎯 tracker reads the
  symbol and the price from exactly that;
- CSV columns read the field names the workers return (`change_24h`, `distance_from_52w_low`, `52w_high`, `52w_low`);
  no P/E, beta, dividend, sector, market cap or earnings risk (the workers have no real company figures).

**4d. Three lookups keyed on the subOption or the name** (find each with `grep -n nikkei225`):
1. the re-run address table: `'Germany DAX 40 Screener': 'analysis.html?option=5&subOption=dax40&autorun=true'`
2. in `saveAnalysisToHistory`, inside `option === 5`: `} else if (subOption === 'dax40') { symbols = ['GERMANY_SCREENER']; uniqueSymbolsCount = 40; }`
   (before the final `else`, which falls back to `ASIA_MARKETS`)
3. the `subNames` table: `'dax40': 'Germany DAX 40 Screener'` (without it the saved report is titled "ASX Stock Screener")

Run `node -c analysis-functions.js` after every edit. `const name` may be declared only once per `forEach` (a second one
broke the whole site during the Nikkei build).

## Step 5: the button (`website/analysis.html`)

Search for the "Coming Soon" line (`grep -n "DAX" analysis.html`) and replace it:

```html
<button class="screener-btn" onclick="runAnalysis(5, 'dax40', event)">🇩🇪 Germany (DAX 40) (40 stocks)</button>
```

## Step 6: the dashboard (`website/dashboard.html`)

Search for `japan_screener` and `Japan Nikkei`; add the German line beside each:

- `getAnalysisKey()`: `if (companyName.includes('Germany DAX') || symbol === 'GERMANY_SCREENER') return 'germany_screener';`
  placed **above** the generic tests (Japan sits above `includes('ASX')`).
- `getSubOptionFromCompanyName()`: `'Germany DAX 40 Screener': 'dax40',`
- `screenerMappings` in `getRerunUrl()`: `'Germany DAX 40 Screener'` and `'Germany DAX 40 Analysis'` →
  `'analysis.html?option=5&subOption=dax40&autorun=true'` (Japan has both names)
- `processAnalysisGroup()` ("Run in Background"): `} else if (analysisType === 'germany_screener') { endpoint = coordinatorUrl; payload = { option: '5', subOption: 'dax40', userId }; }`
- `TOP10_BENCHMARKS`: `[/DAX/i, '^GDAXI', 'DAX 40 index'],` (the index the Top 10 popup compares with)
- **The tracker's money signs.** The two patterns in `parseScreenerTop10` accept `$ £ € ¥ ₹ ₩` before the number, or a
  number followed by `p` (pence). Any other sign must be added to **both** patterns and to the copy in
  `check-tools/page_run.js`.

The page has inline scripts: after editing, check each `<script>` block still parses (`node --check`), section 8c.

## Step 7: the autopilot and the chat (only if the owner wants the autopilot to buy from the new screener)

Lambda `stockiq-ai-trader` (routine, tests and deploy script: `site-overview.md` section 8c, "How to work on it"):

- `SCREENERS`: `'5-dax40': ('Germany DAX 40', '5', 'dax40', 'stock', 'de', 'German shares'),`
  (name, coordinator option and subOption, kind, market code, market group). A new market group gets its share-of-the-
  budget menu and its colour on the panel by itself.
- `MARKET_HOURS`: `'de': (8 * 60 + 5, 15 * 60 + 25)`, minutes of the day in UTC, Monday to Friday. **A fixed window that
  lies inside the real session in both summer and winter time**: Xetra trades 09:00–17:30 Frankfurt time, which is
  07:00–15:30 UTC in summer and 08:00–16:30 UTC in winter, so 08:05–15:25 UTC is always inside. (India: 03:45–10:00 UTC
  all year, so `(3 * 60 + 50, 9 * 60 + 55)`. Korea: 00:00–06:30 UTC, so `(5, 6 * 60 + 25)`.) Public holidays are not known
  to the autopilot.
- `MARKET_NAMES`: `'de': 'German'`.
- The currency must work in `fx_pair` there and in `fxFor` in `practice-portfolio.js` (the two must follow the same
  rule). EUR is in both already (quoted as dollars per euro). INR and KRW go the "per dollar, turned over" way that the
  yen uses: check a holding's value by hand once.
- Tests: add the screener to the stand-ins in `check-tools/ai_trader_test.py` where the others are listed, and run the
  four test commands of section 8c.
- The AI chat (`stockiq-ai-chat`): its `DASHBOARD_GUIDE` does not name markets, so it needs nothing; the general prompt
  has one line listing the screeners ("…ASX, UK FTSE, Japan Nikkei, Crypto"): add the new one there. Run
  `check-tools/ai_chat_test.py`.

---

## Step 8: test before anything goes live, and again after

Stage the website files in the pending folder and test the staged copies; nothing here needs a login.

```bash
cd /Users/dave/VSCODE/stockiq/check-tools
node page_run.js 5 dax40                                   # the page path, with real worker calls
#   expect: error null, flags [], worker calls 4/4, results = the list's size, trackerSymbols 10
AWS_DEFAULT_REGION=us-east-1 python3 run_all.py 5-dax40    # the coordinator path, run locally from lambda-sync/ (COORD=<file>: a staged copy); nothing is saved
python3 analyse.py -v                                      # per screener: returned / listed, missing symbols, duplicates, zero prices, flags, CSV rows
NAME='Germany DAX 40 Screener' node tracker_run.js DAX page_5-dax40.json <the report's ISO time>   # the dashboard's 🎯 tracker on the page's report
NAME='Germany DAX 40 Screener' node tracker_run.js DAX res_5-dax40.json <ISO time>                 # and on the coordinator's (DASH=<file>: a staged dashboard.html)
#   expect: 10 lookups plus the index, and 0.00% when the market is closed (a wrong sign or a misread comma shows as a huge move)
python3 ../workers/prove.py                                # only if workers/ changed
python3 workers.py                                         # the new group: "one", same code as the other share groups
```

`page_run.js` reads `website/analysis-functions.js`; `FUNCS=<file> node page_run.js 5 dax40` runs a staged copy
instead. Read a few outputs, do not only count lines: the names, the sign before each price, a
plausible score and 24-hour change for stocks you can look up, no "undefined", "NaN" or "Unrated". "Unrated" means a
worker code is missing from a label table. Then, as an anonymous visitor and a trial user
(`anon_run.js`, `trial_run.js`): one use left must give a result, none left must redirect before running.

**Deploy** the coordinator and the website files with packaged scripts (dry run, then run), away from :10 and :40 past
the hour and not while the daily deploy runs. Website files go up with the cache rules of `site-overview.md` section 5
step 8 (a page: `public, max-age=0, s-maxage=3600, must-revalidate`; a script: `public, max-age=300, s-maxage=86400`)
and an invalidation of just those paths. Then run the same `page_run.js` and `run_all.py` lines against the live site,
and `curl` the live files to compare them with the local ones.

Cannot be tested from here, say so: the logged-in dashboard itself (Refresh, Run in Background from the row, the
notification), and a real phone.

---

## Step 9: the notes and counts to update afterwards

- `site-overview.md` section 8b: the screener table (page call, coordinator key, worker group and count, list size,
  source of the list); section 2 and `stockiq.md` / `lambda-reference.md`: the number of functions (984 + the new
  workers) and of worker functions; section 13: a change-log entry; section 8c if the autopilot uses it.
- `lambda-reference.md`: the worker-group table.
- This file: the table below.
- `roadmap-to-9.md`: the screener list and the open item.
- The list's size in **three** places that must agree: the button label (`analysis.html`), the formatter's
  `universeSize` (`analysis-functions.js`), the coordinator's `universe_sizes`.
- `lambda-url-mapping.json`: `bash generate-lambda-url-mappings.sh` (a few minutes; `check-tools/workers.py` uses it to
  say which groups the site calls).
- `about.html` / `faq.html` if they list the markets covered.
- Remove the `pending-` folders, commit the website files by name, push both repos.

---

## Existing screeners

| Screener | Page call | Coordinator key | Worker group | Workers | Stocks (Oct 2026) | Suffix | Currency |
|---|---|---|---|---|---|---|---|
| Dow 30 | `3, '8'` | `3-8` | `stockiq-option-3-8-worker` | 3 | 30 | none | USD |
| S&P 100 | `3, '100'` | `3-100` | `stockiq-option-3-1-worker` | 10 | 101 | none (`BRK-B`) | USD |
| NASDAQ 100 | `3, '7'` | `3-7` | `stockiq-option-3-7-worker` | 10 | 101 | none | USD |
| S&P 500 | `3, '3'` | `3-3` | first 50 of `stockiq-option-3-5-worker` | 50 | 502 | none | USD |
| S&P 400+600 | `3, '2'` | `3-2` | `stockiq-option-3-2-worker` | 100 | 995 | none | USD |
| S&P 1500 | `3, '4'` | `3-4` | `stockiq-option-3-4-worker` | 150 | 1,497 | none | USD |
| Russell 1000 | `3, '5'` | `3-5` | `stockiq-option-3-5-worker` | 100 | 877 (not refreshed) | none | USD |
| Russell 2000 | `3, '6'` | `3-6` | `stockiq-option-3-6-worker` | 200 | 1,829 (not refreshed) | none | USD |
| ASX 50 / 100 / 200 / 300 | `5, '50'` … `'300'` | `4-50` … `4-300` | `stockiq-asia-5-1` … `5-4-worker` | 5 / 10 / 20 / 30 | 49 / 99 / 195 / 294 | `.AX` | AUD |
| UK FTSE 100 | `4, 'ftse100'` | `5-ftse100` | `stockiq-europe-4-1-worker` | 10 | 100 | `.L` (`BT.A` → `BT-A.L`) | GBp (pence) |
| Japan Nikkei 225 | `5, 'nikkei225'` | `5-nikkei225` | `stockiq-asia-5-5-worker` | 21 | 225 | `.T` | JPY |
| **Germany DAX 40 (next)** | `5, 'dax40'` | `5-dax40` | `stockiq-europe-4-2-worker` | 4 | 40 | `.DE` | EUR |
| India BSE Sensex | `5, 'sensex'` | `5-sensex` | `stockiq-asia-5-6-worker` | 3 | 30 | `.BO` or `.NS` | INR |
| Crypto | `7, 'coinspot'` | `7-1` | orchestrator + 54 `stockiq-option-7-1-worker` in single-coin mode | 54 | 540 coins | `-USD`, sometimes a numbered ticker | USD |

The Russell 1000 / 2000 page runs send a worker number and no stocks; those workers take their ten from `lists.txt` in
the package (`site-overview.md` section 8b). A new screener sends its batches like Nikkei does and needs no list there.

---

## Pitfalls

| Problem | Cause | What to do |
|---|---|---|
| A worker's address answers 403 | The public permission is missing | `create_group.py` adds it; run it again (it passes over what exists) |
| "Unknown screener" (400) from the coordinator | The key is not in `WORKER_URLS` | Add it and deploy the coordinator |
| The list comes back short | A symbol Yahoo does not know is dropped without a word | Check every symbol through the price proxy first; `analyse.py -v` lists what is missing |
| The 🎯 tracker finds no symbols | A long name between symbol and price, or a money sign the pattern does not accept | Names of 22 characters at most; add the sign to both patterns (step 6); test with `tracker_run.js` on a `page_*.json` and a `res_*.json` |
| "Unrated" in a report | A worker code missing from a label table | Add it to `signalLabel()` and the coordinator's `signal_label()` |
| `Identifier 'name' has already been declared` | `const name` twice in one `forEach` | Declare it once; `node -c` after every edit |
| A visitor's last free use gives no result | An access check inside the handler | Never check access again after the top of `runAnalysis` |
| Page and background runs disagree | The list differs between the page and the coordinator | One list, pasted into both |
| Workers show two fingerprints | A function was updated by hand, or created from another build | `workers.py --contents`; deploy the one package to that group with `workers/deploy.py` |
| The autopilot buys at a stale price | The market's hours are wrong, or not inside both summer and winter time | Work the window out in UTC for both halves of the year |
