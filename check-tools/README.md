# check-tools

Scripts used for the full end-to-end check in October 2026. They run the real site code against the
real analysis Lambdas without a browser. Nothing here is part of the daily pipeline or the deploy.
How and when to use them: `.kiro/steering/site-overview.md` section 8b ("How to test every button").

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
