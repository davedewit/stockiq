# backtest

Replays a screener over past trading days to see what following it would have done. Nothing here touches
the live site. First run: 10 Oct 2026, S&P 500 screener, two years. Results: `results-sp500-2026-10-10.txt`
and `.kiro/steering/site-overview.md` section 7b.

How it works: the screener workers use only daily prices and volume, so the **unchanged live worker code**
(`lambda-sync/stockiq-option-3-5-worker-*`) is run locally for each past day, given only the prices it
would have fetched on that day. Check that was passed before trusting any number: the replay of the latest
day gave the same score and label as that morning's live run for all 502 stocks.

Run from this folder, in order (about 25 minutes, most of it the download):

| Script | What it does |
|---|---|
| `python3 fetch.py` | Downloads 3 years of daily prices for the S&P 500 list into `data/` (one request a second on purpose: the price source blocks fast callers; it can be re-run and continues where it stopped) |
| `python3 replay.py` | Scores every stock on every trading day of the last two years -> `scores.pkl` |
| `python3 analyse_bt.py` | Price change after ranking for the top 10 / bottom 10 / average stock, by label, and a $100,000 fake-money account bought at the close |
| `python3 extra_bt.py` | The fake-money account bought at the next morning's open with trading costs, the bottom 10, and 300 random 10-stock portfolios for comparison |

Limits to state with any result: today's index members are used for the whole period (flatters every
number), dividends are not counted, one two-year period in which the market rose about 35%.

To test another screener: change the list key in `fetch.py` (`STOCK_UNIVERSES['3-3']`), the benchmark
symbol, and the worker folder in `replay.py`.
