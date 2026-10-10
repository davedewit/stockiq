# check-tools

Scripts used for the full end-to-end check in October 2026. They run the real site code against the
real analysis Lambdas without a browser. Nothing here is part of the daily pipeline or the deploy.
How and when to use them: `.kiro/steering/site-overview.md` section 8b ("How to test every button").

**Working on the dashboard's practice portfolio or its AI autopilot?** The tools are further down
(`practice_test.js`, `ai_trader_test.py`, `autopilot_test.js`, `autopilot_plan_check.py`,
`dashboard_page.py`) and the whole routine, from staging a change to verifying it live, is in
`site-overview.md` section 8c ("How to work on it"). A change being built lives in a
`pending-<name>/` folder here until it is deployed, then the folder is removed.

Run them from this folder. They write `*.json` result files here, which git ignores.

| Script | What it does | Example |
|---|---|---|
| `page_run.js` | Runs one analysis button through `website/analysis-functions.js`. Calls the worker Lambdas for real; blocks anything that writes user data (usage, trial, history). Prints a one-line summary and flags raw codes, "Unrated", `undefined`, `NaN`. | `node page_run.js 3 8` (Dow 30), `node page_run.js 72 single '{"coin-symbol-input":"ETH"}'` |
| `anon_run.js` | Same page code plus `auth.js`, as an anonymous visitor with a simulated usage tracker. Logs every redirect with the line that caused it. | `node anon_run.js 72 single` (1 use left: must show a result), `USED=1 node anon_run.js 72 single` (none left: must redirect before running) |
| `trial_run.js` | As above for a signed-in trial user (5 a day). | `TRIAL=1 node trial_run.js 3 8`, `TRIAL=1 USED=5 node trial_run.js 3 8` |
| `run_all.py` | Runs the background coordinator (`lambda-sync/stockiq-screener-coordinator`) locally for every screener key, or the keys given. The dashboard save is intercepted, so nothing is stored. | `AWS_DEFAULT_REGION=us-east-1 python3 run_all.py 3-8 4-50` |
| `tracker_run.js` | Runs the dashboard's real "Top 10 Performance" code (row badge and 🎯 popup) on a saved report with live prices; nothing is saved. Takes a label, a `page_*.json` from `page_run.js` (or a saved orchestrator response) and the report time. `DASH=<path>` tests another copy of `dashboard.html`. A report made while its market is closed must show 0.00%. | `node tracker_run.js FTSE page_4-ftse100.json 2026-10-10T03:58:00+00:00` |
| `analyse.py` | Reads the `res_*.json` files from `run_all.py` and reports coverage per screener (`-v` lists missing symbols). | `python3 analyse.py -v` |

Button codes (option, subOption) are in the screener table in section 8b. Refresh `lambda-sync/`
(`../sync-all-lambdas.sh`) before `run_all.py` so it tests the live coordinator code.

## lists/

How the index lists and the crypto coin list were rebuilt. Kept as a starting point for the next
refresh; they are one-off scripts and need reading before re-use.

- `fetch_lists.py` then `build_lists2.py`: index members from Wikipedia, each symbol checked through
  the `stockiq-price-proxy` Lambda (not Yahoo directly, which blocks this machine after a few hundred calls).
- `cg.py` then `build_crypto.py`: coins from CoinGecko by market value, each matched to a Yahoo ticker
  by comparing prices, so a symbol shared by two coins picks the right one.

After changing a list, put the same list in both `website/analysis-functions.js` and the coordinator
Lambda, and update the count on the button in `website/analysis.html`.

## backtest/

Two-year replay of the S&P 500 screener with the unchanged live worker code (10 Oct 2026). It has its own
`README.md`; the results and what they mean are in `site-overview.md` section 7b.

## paper-test/

Fake-money test of the Dow 30 and S&P 100 screeners: replays the screener worker's own scoring over
daily prices and reports how each day's top 10 went on to do against the whole list and the S&P 500,
plus a $10,000 paper account re-invested weekly. Results and caveats: `site-overview.md` section 11.

```bash
cd check-tools/paper-test
python3 fetch.py                      # 106 price downloads, about 2 minutes; run it once per session at most
python3 backtest.py sp100             # from Jan 2023
python3 backtest.py sp100 2026-10-12  # the fair forward test: only prices after the lists were frozen
```

`frozen_lists.txt` holds the lists as they were on 10 Oct 2026; keep it, or the forward test loses
its meaning. `data/` is a local cache and is not in git.

## practice_test.js

Tests the dashboard's practice portfolio (`website/practice-portfolio.js`) in a stand-in page with real
prices and an in-memory copy of the storage function: buys by code and by name, currencies, the Top 10
button, selling, a change from another window, reset. Give it a copy of the script that still has the
`__PRACTICE_API_URL__` placeholder (put it back with a text replace first). Never point it at the
deployed file: that holds the real address and would write to the live table.

## ai_trader_test.py and autopilot_test.js

Tests of the practice portfolio's AI autopilot. Neither touches anything real.

```bash
python3 check-tools/ai_trader_test.py lambda-sync/stockiq-ai-trader/lambda_function.py   # the trading rules
node check-tools/autopilot_test.js ../website/practice-autopilot.js                      # the dashboard controls
```

The first (183 checks) runs the Lambda's code with stand-ins for the database, the screeners, prices,
the AI model, headlines and email: budget pacing, risk filters, the coin share, every sell rule, the
AI model's hold-or-sell review, headlines, the record and what it learns from it, trials of its own
rules, the owner's own limits and switches, "sell everything", a clash with the user, missing data,
when it is due. The second (97 checks) drives the controls with a stand-in API (the file's real
address is never called, because the test replaces `fetch`) and a stand-in for the browser's storage.
Add a check for whatever you change; when wording changes, the checks that quote it must change too.

## panel_page.py

The older browser test page for the autopilot panel alone (stand-in server, steps such as
`btn,tick-on,run,budget,level,slide,quick,refresh,desc`). `dashboard_page.py` below loads both
sections together and is the one to use for new work.

## dashboard_page.py

Both practice sections of the dashboard (the portfolio and the autopilot) in one test page, run by the two real
scripts with a stand-in server: nothing live is called. It starts with two holdings bought by hand and one by
the autopilot, performs the steps and prints what the page shows.

```bash
python3 check-tools/dashboard_page.py ../website/practice-portfolio.js ../website/practice-autopilot.js /tmp/dash.html dark "type,sale,trial,open"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=1250,2500 \
  --virtual-time-budget=15000 --screenshot=/tmp/dash.png --dump-dom file:///tmp/dash.html > /tmp/dash.dom
```

Steps: `type` (types in the buy row), `sale` (the autopilot sells in the background and the page refreshes
itself), `trial` (a trial of its own rules starts), `off` (the autopilot is switched off), `open` (unfolds the
details), `preset` (presses a quick set-up), `sellall` (presses "Sell everything it holds" and says yes), `limits` (types your own loss limit), `split` (prints the line that says whose result is whose), `cards` (prints the summary cards and every account value shown since the page opened), `pace` (hands the pace to the risk level, moves the slider, sets one field by hand), `listswitch` (switches the list to buys and sells only and reloads). The printed results are in the `<pre id="out">` of the dumped page.

## autopilot_plan_check.py (with autopilot_plan_check.js)

Does the autopilot panel describe what the autopilot function really does? The panel works out, for
the chosen settings, how many holdings it builds up to, how much of the budget that is and after how
long. This replays the Lambda's own rules for 3,780 combinations of settings and compares; with a
number at the end it also runs that many as whole check-ins. Nothing real is touched.

```bash
python3 check-tools/autopilot_plan_check.py lambda-sync/stockiq-ai-trader/lambda_function.py ../website/practice-autopilot.js 150
```

Run it after changing the budget, selling or buying rules in the Lambda, or `buildUp()` in the panel
script. On 10 Oct 2026 it found that a cent of rounding stopped the Lambda buying its last holding.

