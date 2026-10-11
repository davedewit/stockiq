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

## The share-screener workers (`../workers/`)

Every share-screener worker runs one package built from `stockiq/workers/` (since 11 Oct 2026). The tools for it live
there, not here: `build.py` (the package and its fingerprint), `prove.py` (what a change does to scores, on saved prices),
`deploy.py` (a group at a time, through a `pending-<name>/deploy.sh` here; `--selftest`), `create_group.py` (a new
screener's workers), `groups.py` (the one table of groups). Here: `workers.py` prints who runs what from AWS (read-only);
`--contents` downloads every package and compares the files inside, which is the honest count (fingerprints of zips
differ when only the file dates do). `page_run.js` takes `FUNCS=<file>` to run a staged copy of the page code, `run_all.py` takes `COORD=<file>` for a staged
coordinator, and `tracker_run.js` reads a `res_*.json` from `run_all.py` as well as a `page_*.json` (`DASH=<file>` for a
staged dashboard): that is how a change to a report line is proved readable by the 🎯 tracker on both paths.
Detail: `site-overview.md` section 8b, "The worker groups"; a new screener: `add-new-screener.md`.

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
python3 factor_study.py > results-factors-<date>.txt   # which parts of the S&P 100 score pointed the right way (no downloads, about 100 s)
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

The first (358 checks) runs the Lambda's code with stand-ins for the database, the screeners, prices,
the AI model, headlines and email: budget pacing, risk filters, the coin share, every sell rule, the
AI model's hold-or-sell review, headlines, the record and what it learns from it, trials of its own
rules, the owner's own limits and switches, "sell everything", trading hours (also by hand), a switch
of screeners while it holds something, the spread of the budget over markets, progress per batch of 20 trades and what it does when a batch is no better, its own trial of which share to buy, the pause after two weeks without a visit, several accounts at once, the daily limit on AI calls, who may use it (paid plans and the listed accounts) and what the others are shown, a budget that always fits the practice money, what happens next and what needs the owner, the email's status, a clash with the user, missing data, when it is due. The second (189 checks) drives the controls with a stand-in API (the file's real
address is never called, because the test replaces `fetch`) and a stand-in for the browser's storage.
Add a check for whatever you change; when wording changes, the checks that quote it must change too.

## ai_chat_test.py

The AI chat function's prompt, with stand-ins for the database and the AI model (13 checks): what it is told away from
the dashboard and on it, that the user's dashboard summary is treated as data and cut to length, that the rule against
advice stands, and that the risk-level numbers it quotes are the autopilot's own.

```bash
python3 check-tools/ai_chat_test.py lambda-sync/stockiq-ai-chat/lambda_function.py
```

## panel_page.py

The older browser test page for the autopilot panel alone (stand-in server, steps such as
`btn,tick-on,run,budget,level,slide,quick,refresh,desc`). `dashboard_page.py` below loads both
sections together and is the one to use for new work.

## dashboard_page.py

Both practice sections of the dashboard (the portfolio and the autopilot) in one test page, run by the two real
scripts with a stand-in server: nothing live is called. It starts with two holdings bought by hand and one by
the autopilot, performs the steps and prints what the page shows.

```bash
python3 check-tools/dashboard_page.py ../website/practice-portfolio.js ../website/practice-autopilot.js /tmp/dash.html dark "tabs,type,sale,trial,open" ../website/dashboard.html
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=1250,2500 \
  --virtual-time-budget=15000 --screenshot=/tmp/dash.png --dump-dom file:///tmp/dash.html > /tmp/dash.dom
```

The last argument is optional: with `dashboard.html` given, the page's real tab bar and tab script are used and the
two sections sit in their own tabs, as on the site (step `tabs` presses each tab and the autopilot's two parts).

Steps: `type` (types in the buy row), `sale` (the autopilot sells in the background and the page refreshes
itself), `trial` (a trial of its own rules starts), `off` (the autopilot is switched off), `open` (unfolds the
details), `preset` (presses a quick set-up), `sellall` (presses "Sell everything it holds" and says yes), `limits` (types your own loss limit), `split` (prints the line that says whose result is whose), `cards` (prints the summary cards and every account value shown since the page opened), `pace` (hands the pace to the risk level, moves the slider, sets one field by hand), `listswitch` (switches the list to buys and sells only and reloads), `trailstop` (chooses each kind of trailing stop and prints what the page says), `tabs` (see above), `progress` (prints the table of progress per batch of 20 finished trades), `shares` (ticks three markets, sets a share by hand, tries to give out more than 100%, moves the risk level), `locked` (shows the autopilot tab as an account without a paid plan sees it), `breakdown` (fills the record with four trades and opens the breakdown table), `budget` (types a budget larger than the practice money and presses the link that puts it right), `next` (prints the countdown, "Needs you", the "What happens next" list and the email line, and presses "Send me a test email"). The printed results are in the `<pre id="out">` of the dumped page.

**On a phone:** step `mobile` lists what sticks out past the edge of the screen and what has to be scrolled
sideways inside its own box, for the practice portfolio and both parts of the autopilot (`mobile:practice`,
`mobile:activity` or `mobile:settings` leaves that view up for a screenshot). Headless Chrome will not make its
window as narrow as a phone, so put the test page in a phone-width frame first with `mobile_frame.py`:

```bash
python3 check-tools/dashboard_page.py ../website/practice-portfolio.js ../website/practice-autopilot.js /tmp/m.html light "progress,breakdown,mobile" ../website/dashboard.html
python3 check-tools/mobile_frame.py /tmp/m.html /tmp/m-frame.html 390          # width in px, default 390
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=390,3000 \
  --virtual-time-budget=30000 --dump-dom file:///tmp/m-frame.html > /tmp/m.dom   # the lines starting "mobile" are the result
```

(Steps `breakdown` and `locked` open the folded breakdown and show the view of an account without a paid plan.)

## replay/replay.py

The autopilot's own rules over four years of daily prices in about 20 seconds: the place to try an idea about how it
trades before it is built. `python3 check-tools/replay/replay.py` (`--rebuild` scores the days again after the screener
worker's scoring changed; the scores are kept in `replay/panel.json`, which is not committed). It imports the level
tables, the pace and the gain-protection rule from the deployed function's mirror, takes 0.1% off each buy and sale,
decides once a day at the close and trades at the next open. It prints, and writes to `replay/results-replay-<date>.txt`:
the five levels as they are; a search over 240 variants found on the first 60% of the days and judged on the last 40%;
the same rules buying at random (luck); the variants ahead on both parts, also without the seven chip / AI names;
a table by holding time; and the list ranked by other figures than the screener's score. Shares of the S&P 100 list
only (the prices in `paper-test/data`), today's members, no AI model in the loop: read `site-overview.md` section 7b
before quoting a number from it.

## autopilot_bell_test.js and bell_page.py

The AI autopilot's buys and sells in the notification bell (`website/autopilot-bell.js`, on every page with a bell).

```bash
node check-tools/autopilot_bell_test.js ../website/autopilot-bell.js      # 22 checks: the red number, unread marks, profit or loss, the one list in order of time, when it asks the function
python3 check-tools/bell_page.py ../website/autopilot-bell.js /tmp/bell.html light trade     # or: dark report
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=900,900 \
  --virtual-time-budget=8000 --dump-dom file:///tmp/bell.html > /tmp/bell.dom      # and --screenshot=/tmp/bell.png
```

`bell_page.py` writes a stand-in page whose bell is drawn the way the dashboard draws it, run by the real script with a
made-up answer to its question: it prints the red number, the one list in order (`trade`: the newest item is a trade;
`report`: it is a report), what happens when the page redraws its own list, and a click.

`live_bell_check.js` does the same on the **live** pages: `node check-tools/live_bell_check.js index.html analysis.html
stocks/AAPL.html` opens them in headless Chrome as a signed-in visitor with a made-up address and prints, per page, whether
the bell's script loaded, the red number and the list after a click. Every call the page makes to the site's functions is
answered locally (the bell's question with made-up trades), so nothing reaches the site or is written. `NO_THEME=1`
withholds `theme.js`, to prove a page fetches the bell's script by itself. `REAL_USER=<address>` opens the pages as that
account and lets its two read-only questions through (its reports, the bell's), so the list is the real one; `SHOT=<file.png>`
saves a picture with the bell open; `LOCAL_BELL=<file>` gives the page a staged copy of the script, to try a change on the
live pages before it is deployed. The address is never printed. `PASS_GET=1` also lets the dashboard's own opening
questions through, so `dashboard.html` can be opened as that account. `OLD_THEME=<file> OLD_BELL=<file>` play back old
copies of `theme.js` and of the bell's script (take them from git: `git -C ../website show <commit>:theme.js`) the way a
browser's own store would, ahead of the current script: the way to reproduce "it works for you but not in my browser".
`BASE_URL=http://127.0.0.1:8765/website/` opens the local copy of the site instead, served from a folder as a local preview
serves it (`cd ~/VSCODE && python3 -m http.server 8765 --bind 127.0.0.1` first, and stop it afterwards): this is what found
that the bell's script was asked for at the top of the address and so never loaded anywhere but on stockiq.tech. A page whose bell goes to the dashboard ends
with "Inspected target navigated": that is the bell working.

## workers.py

Who runs what: `python3 check-tools/workers.py` lists every screener worker group on AWS with its screener, how many
functions it has, whether they all run one version of their code, whether the site calls them, and which groups run the
same code as another (read-only; `--diff` also counts the lines by which each group's copy in `lambda-sync/` differs from
the S&P 100 worker). Run it before and after any change to a worker group: after a deploy a group must show "one".
The findings of 11 Oct 2026 and the plan for one shared source file are in `site-overview.md` section 8b, "The worker groups".

## autopilot_plan_check.py (with autopilot_plan_check.js)

Does the autopilot panel describe what the autopilot function really does? The panel works out, for
the chosen settings, how many holdings it builds up to, how much of the budget that is and after how
long. This replays the Lambda's own rules for 3,780 combinations of settings and compares, and compares how the
budget is spread over the markets ticked (the panel's `marketSlots` against the Lambda's `market_slots`) for 2,915
combinations of level, markets and hand-set shares; with a
number at the end it also runs that many as whole check-ins. Nothing real is touched.

```bash
python3 check-tools/autopilot_plan_check.py lambda-sync/stockiq-ai-trader/lambda_function.py ../website/practice-autopilot.js 150
```

Run it after changing the budget, selling or buying rules in the Lambda, or `buildUp()` in the panel
script. On 10 Oct 2026 it found that a cent of rounding stopped the Lambda buying its last holding.


## report/ (the single-stock report and its chart)

Lambdas `stockiq-option-1-1-custom-analysis` and `stockiq-chart-generator` (`site-overview.md` section 7, "The single-stock
report and its chart"). Nothing live is called: prices come from `workers/data/sample.json`.

```bash
# the report: the code from before 11 Oct 2026 against the code now, on the same saved prices (88 checks)
unzip -o -q ~/VSCODE/backup/stockiq-option-1-1-custom-analysis_before_report_20261011.zip -d /tmp/report-before
python3 check-tools/report/report_test.py /tmp/report-before/lambda_function2.py lambda-sync/stockiq-option-1-1-custom-analysis/lambda_function2.py
#   add  --show BHP.AX  to print a whole report (BHP.AX CBA.AX IMB.L AZN.L 7203.T CRWD KHC CSX MSTR ASML)

# the chart, by itself and fed by the report (29 checks)
python3 check-tools/report/chart_test.py lambda-sync/stockiq-chart-generator/lambda_function_simple.py lambda-sync/stockiq-option-1-1-custom-analysis/lambda_function2.py

# after any change to the report's scoring: copy it into the stock pages' copy (stops if the two differ afterwards)
python3 check-tools/report/patch_metrics.py lambda-sync/stockiq-option-1-1-custom-analysis/lambda_function2.py stock_metrics.py stock_metrics.py
```

`report/changes-2026-10-11/` holds the scripts that made the change of 11 Oct 2026 (the functions' code is not in git:
the report's holds a key). To change a function again: copy the mirror's file, change the copy, run the two tests on
it, and deploy with a packaged `check-tools/pending-<name>/deploy.sh` that rebuilds the change from the live code (the
last one: `git show 2df59e0:check-tools/pending-figures/deploy.sh`).

## signals/ (in the repo's top folder, not here): the two trading-signals functions

`python3 signals/test_signals.py` (42 checks on saved prices; `--show` prints the readings) and `python3 signals/build.py`
(the package and its fingerprint; `--list` rewrites the scan list from the coordinator's S&P 100). One file runs in both
functions; `site-overview.md` section 8b, "Trading signals and the presets".

## crypto/batch_test.py (the crypto job: ten coins a call)

The orchestrator from before 11 Oct 2026 (one worker call per coin) against the one now (ten coins a call), on a
stand-in for the 54 workers; nothing live is called. `coin_template.txt` is one real coin analysis the stand-in copies.

```bash
unzip -o -q ~/VSCODE/backup/stockiq-option-7-1-orchestrator_before_batch_20261011.zip -d /tmp/orch-before
unzip -o -q ~/VSCODE/backup/stockiq-option-7-1-worker_before_batch_20261011.zip -d /tmp/worker-before
python3 check-tools/crypto/batch_test.py /tmp/orch-before/orchestrator.py lambda-sync/stockiq-option-7-1-orchestrator/orchestrator.py \
  /tmp/worker-before/lambda_function.py lambda-sync/stockiq-option-7-1-worker-*/lambda_function.py check-tools/crypto/coin_template.txt
```

`crypto/worker_test.py`: the crypto worker before and after its clean-up of 11 Oct 2026, on the price source's recorded
answers for ten coins (`recorded.txt`); `crypto/patch_worker_2026-10-11.py` is the script that made that change.

```bash
unzip -o -q ~/VSCODE/backup/stockiq-option-7-1-worker_before_clean_20261011.zip -d /tmp/worker-before-clean
python3 check-tools/crypto/worker_test.py /tmp/worker-before-clean/lambda_function.py lambda-sync/stockiq-option-7-1-worker-*/lambda_function.py check-tools/crypto/recorded.txt
```
