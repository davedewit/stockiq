# StockIQ Site Overview (read this first)

How stockiq.tech works end to end, what is generated vs hand-edited, the current SEO setup,
known pitfalls, and open ideas. Last full review: 10 Oct 2026 (section 8b holds what the
9–10 Oct end-to-end test of every screener, signal and crypto path established; **section 8c is
the dashboard's practice portfolio and AI autopilot, and the routine for working on them**).

Detailed references: `stockiq.md` (AWS resources, Cognito, Lambdas, AI chat),
`script-reference.md` (every script), `add-new-stocks.md`, `stock-matching-system.md`,
`stocks-txt-csv-format.md`, `roadmap-to-9.md`, `backlinks-progress.md`, `future-work.md`.

---

## 1. What the site is

- AI-assisted stock/ETF/crypto research tool for individual investors: single-stock reports,
  trading signals, market screeners (US, Europe, Asia, other), crypto screener, AI chat.
- 3-day free trial (5 analyses/day = 15 total), then Starter $4.99, Pro $14.99, Elite $49.99 per month (Stripe).
- Traffic is very low (a few visits/day; 13 visitors/month in March 2026), revenue $0.
  The main goal is organic search traffic, then conversions.
- Owner edits in **Kiro** (not VS Code). The top folder is still named `/Users/dave/VSCODE`.

## 2. Architecture

```
Browser ──> CloudFront (EHXV50CPHY07R, www→apex redirect function)
              └─> S3 bucket stockiq-final-websitebucket-vqekic7enf9h (static files)
Browser ──> Lambda function URLs directly (no API Gateway; 982 functions, 967 with URLs, ~650 are screener workers)
              ├─ analysis-functions.js: single-stock report, signals, screener workers, charts
              ├─ index/dashboard/sidebar: market data, gainers/losers/trending, email capture
              └─ auth.js: usage/trial trackers
Browser ──> Cognito (user pool us-east-1_P4lqPzrlY, tokens in localStorage), Google/Facebook login, Stripe
Lambdas ──> Yahoo Finance + Finnhub (data), OpenAI gpt-4o-mini (AI chat), DynamoDB, S3
```

- S3 versioning is **Suspended**: an overwrite cannot be rolled back from S3. Rollback comes
  from the deploy script's daily backups in `~/VSCODE/backup/` (see section 3).
- `stockiq/lambda-sync/` is a local mirror of the deployed Lambda code, refreshed hourly by the
  deploy script. It is gitignored. Read it to see what production runs.

## 3. Folders and git repos

| Folder | GitHub repo | Notes |
|---|---|---|
| `/Users/dave/VSCODE/website/` | `davedewit/stockiq-website` | What is served. `stocks/` and `.last_*` markers are gitignored, so stock pages exist only locally and on S3 |
| `/Users/dave/VSCODE/stockiq/` | `davedewit/stockiq` | Scripts, Kiro steering, `check-tools/` (end-to-end test scripts, section 8b). `lambda-sync/`, `.analysis_cache/`, `*.json` are gitignored |
| `~/VSCODE/backup/` | – | Daily backups made by every deploy: `website_backup_<UTC time>` and `stockiq_backup_<UTC time>`, 30-day retention. **This is the backup**, including `stocks/`, which GitHub does not have |

**Restoring:** folder names use UTC (`website_backup_20260925_034730` = 13:47 AEST on 25 Sep).
- Hand-edited files and scripts: `git checkout <commit> -- <file>` (both repos are on GitHub).
- Stock pages: copy back from a backup, e.g.
  `rsync -a ~/VSCODE/backup/website_backup_<time>/stocks/ ~/VSCODE/website/stocks/`,
  then deploy (dry run first).
- The live site is simply whatever the last deploy uploaded; restore locally, then redeploy.

## 4. Generated vs hand-edited (most important rule)

**Never hand-edit generated output. Change the generator.**

| File | Owner | How to change it |
|---|---|---|
| `stocks/*.html` layout, head, footer | `generate-stock-pages.py` template | Edit the template, run the script (manual, not daily). It keeps the NEWS/RELATED/ANALYSIS sections, robots value, data descriptions and dateModified |
| `stocks/*.html` NEWS section | `update_stock_news.py` (daily) | Script only |
| `stocks/*.html` RELATED section ("People also watch") | `people_also_watch_stocks.py --missing` (daily) | Script only |
| `stocks/*.html` ANALYSIS section, robots, meta description | `update_stock_analysis.py` (daily) | Script only |
| `news.html` article list | `update_news.py`, `update_stock_news.py`, then trimmed by `finalize_news_html.py` | Head and footer are preserved by all writers, so hand edits there stick |
| `news.js` (sidebar, 100-item pool) | `update_news.py`, `update_stock_news.py` | Script only |
| `sitemap.xml` | `update_sitemap.py` (daily), `generate_sitemap.py` (manual) | Scripts only |
| `stocks.txt` (3,467 symbols, CSV) | Hand-edited + `fetch_stock_data.py` | See `stocks-txt-csv-format.md` |
| `index.html`, `about.html`, `faq.html`, `analysis.html`, `dashboard.html`, guides, legal pages, `*.js`, `styles.css` | Hand-edited, no generator | Edit directly |

Stock page lifecycle: `fetch_stock_data.py` → `stocks.txt` → `generate-stock-pages.py` →
section scripts fill NEWS / RELATED / ANALYSIS. Every section script only replaces text between
its own `<!-- X_SECTION_START/END -->` markers.

Stock page order: header, **ANALYSIS snapshot**, "Full report" CTA card, NEWS, RELATED, footer.

## 5. Daily pipeline

launchd `com.stockiq.reminder` fires every 10 min → `~/stockiq-daily.sh` runs once a day
**Mon–Sat, 11am–10pm** (lock `/tmp/stockiq-deploy-YYYYMMDD.lock`) → `deploy.sh` →
`deploy-to-s3.sh` with `UPDATE_STOCK_NEWS=true`. Log: `~/stockiq-daily.log` (cleared each run).

Order inside `deploy-to-s3.sh`:
1. `update_news.py`: Yahoo/Google RSS → OpenAI summaries → news.html + news.js (2-hour cooldown)
2. `update_stock_news.py`: per-stock news into stock pages + news.html/news.js (23-hour cooldown per stock)
3. `update_stock_analysis.py` (**daily run only**: it sits inside the `UPDATE_STOCK_NEWS=true` block, so a plain `./deploy-to-s3.sh` prints "Skipping stock data snapshots"): data snapshots on all 3,467 stocks, sets index/noindex on large caps (≥$10B), writes `indexable_stocks.txt`. ~20 min, no API cost. 404s for delisted stocks are normal/cached. When Yahoo has no price for a stock it keeps yesterday's snapshot and does not de-index it.
4. Backups (website + stockiq; prod_scripts every 23h)
5. `people_also_watch_stocks.py --missing`
6. `update_sitemap.py`: **rebuilds** stock URLs from `indexable_stocks.txt` (not all HTML files), updates lastmod on site pages. Refuses if list < 200 entries.
7. `cleanup_broken_links.py`, `remove_news_duplicates.py`, `finalize_news_html.py` (trim news.html to 240 stock + 60 general, keep noindex)
8. S3 upload:
   - `stocks/`: `aws s3 sync --delete` (size + mtime), 24h cache
   - `js/`: sync --delete, 24h cache
   - root `*.html` (1h cache), `*.css` (24h), root `*.js` (24h; news.js 1h): uploaded when the local MD5 differs from the S3 ETag
   - images (7d), and `stocks.txt robots.txt sitemap.xml`
9. CloudFront invalidation `/*` (waits for completion), `notify_search_engines.py` (IndexNow; "202" means accepted)
10. `sync-all-lambdas.sh` (hourly cooldown)
11. Git: for **both** repos, commit if changed → `pull --rebase` → push, unless the last
    push by this step was under 23h ago. Full rules and timing examples in section 5b.

Preview without uploading or pushing: `cd stockiq && DRY_RUN=true ./deploy-to-s3.sh`.
It still runs the local steps (backups, sitemap, news trim), then prints `(dryrun)` lines.
The script lost this mode once (section 9): check `grep -c DRY_RUN deploy-to-s3.sh` is above 0 first.

## 5b. GitHub: how and when changes get pushed

**Short answer: yes, changes go to GitHub automatically.** Every deploy, whether it's the daily
launchd run or a manual `./deploy.sh` / `./deploy-to-s3.sh`, ends with the same git step.
There is only one push mechanism.

**Two repos, both on `main`, both handled by that step:**
- `website/` → `davedewit/stockiq-website`: site files, news.html, news.js, sitemap.xml.
  `stocks/*.html` is **not** in git (gitignored), so stock pages exist only locally, on S3 and in backups.
- `stockiq/` → `davedewit/stockiq`: scripts, `indexable_stocks.txt`, Kiro steering.
  `lambda-sync/` and `.analysis_cache/` are not in git.
- Before 25 Sep 2026 the step only handled `stockiq/`, which is why the website repo fell
  months behind. Both are handled now.

### The git step (end of `deploy-to-s3.sh`)

1. **Cooldown check:** reads `website/.last_git_push` (a Unix timestamp). If less than
   **23 hours** (82,800 s) have passed, it prints "Skipping git push (less than 23 hours ago)"
   and does **nothing**: no commit and no push. Local changes simply wait.
2. Otherwise, for `stockiq/` then `website/`:
   - If `git status --porcelain` shows changes: `git add -A` and commit
     `"Auto-update: <UTC time>"` (this includes any uncommitted hand edits)
   - `git pull --rebase` (brings in commits made elsewhere). On conflict: `git rebase --abort`
     and log "could not rebase onto GitHub (conflict) - not pushed, needs a manual look";
     that repo is skipped, the other still runs
   - If nothing is ahead of GitHub: "already up to date on GitHub". Otherwise `git push`
     ("pushed to GitHub", or "git push failed (will retry next deploy)")
3. The marker is rewritten with the current time **only if both repos succeeded** (pushed or
   already up to date) and it is not a dry run. After any failure it retries on the next deploy.

The git step runs last, after S3, CloudFront and the Lambda sync. If the deploy aborts earlier
(no internet, or an S3 command failing 3 times), there is no push that day.
`DRY_RUN=true` only prints what it would commit and push, and never touches the marker.

### Timing in practice

- The daily run happens once a day, **Mon–Sat, between 11am and 10pm** (whenever the 10-minute
  launchd check first lands in that window). **There is no run on Sunday.**
- On normal days the runs are ~24h apart, so each daily run clears the 23h cooldown and pushes.
- **Whichever deploy first runs after the cooldown clears does the push.** Any other deploy
  inside the 23h skips the git step and only does S3.
- **A push from a deploy at an unusual time delays the next automatic push.** Example: a
  manual deploy pushes on Friday at 6pm → Saturday's 11am run is only 17h later and skips →
  there is no Sunday run → Monday's run pushes. Commits made in between wait until then.
- A plain `git push` typed by hand does **not** touch the marker, so it doesn't delay anything.
  Only the deploy script's git step (or someone writing the file) updates it.
- Check the state:
  ```bash
  date -r $(cat /Users/dave/VSCODE/website/.last_git_push)    # last push by the deploy script
  git -C /Users/dave/VSCODE/stockiq status -sb                 # "ahead N" = N commits not yet pushed
  git -C /Users/dave/VSCODE/website status -sb
  grep -E "Skipping git push|pushed to GitHub|up to date on GitHub|could not rebase|push failed" ~/stockiq-daily.log
  ```
  (`~/stockiq-daily.log` is cleared at the start of each run, so it only shows the latest run.)

### When the owner asks to "push" or "update GitHub" now

The deploy's git step won't push during the cooldown, so push directly:
```bash
cd /Users/dave/VSCODE/stockiq && git status -sb      # then the same in ../website
git add -A && git commit -m "<what changed and why>"   # descriptive message, not "Auto-update"
git log @{u}..HEAD --oneline                           # show the owner what will go up
git pull --rebase && git push
```
- Do both repos if both have changes. This does not change the marker (see above).
- Pushing to GitHub **does not update the live site**. Only the deploy script uploads to S3.
  To update the site too: `DRY_RUN=true ./deploy-to-s3.sh`, get approval, then `./deploy-to-s3.sh`.

### Changes made elsewhere (Claude cloud sessions, GitHub web edits)

- They arrive as a branch (e.g. `claude/new-session-…`) or as commits on `main`. Commits on
  `main` are pulled in automatically by the next push (`pull --rebase`); branches are not.
- To bring a branch in: `git fetch`, check that the branch doesn't touch files with uncommitted
  local edits, then `git merge --ff-only origin/<branch>`. Then deploy to make it live.
- Generated files (news.html, news.js, sitemap.xml) change every day locally. If a remote
  commit also changed them, keep the **local** version; they are regenerated anyway. A remote
  edit to them is the most likely cause of a "could not rebase" warning.
- Cloud sessions cannot see `stocks/` or run the pipeline. Stock page changes must be made in
  `generate-stock-pages.py` or a section script, then run locally.

## 6. SEO setup (set up 25 Sep 2026; numbers as of 10 Oct 2026)

- **Indexed stock pages:** market cap ≥ **$10B USD** and fresh price data → `index, follow` + data
  snapshot. That was 962 pages on 25 Sep and **957 on 10 Oct 2026** (about two thirds US; the
  rest TO, L, T, HK, AX, PA, DE, NS). The number moves a little as market caps cross $10B.
  All others (2,510, including delisted/renamed symbols with no data) → `noindex, follow`,
  with an empty snapshot section. The threshold is `INDEX_MIN_MARKET_CAP_USD` in
  `update_stock_analysis.py`. The owner chose to keep $10B for now; review after 6–8 weeks of
  Search Console data ($2B ≈ 2,000 pages; "any stock with data" ≈ 3,300).
- **Sitemap:** 974 URLs on 10 Oct 2026 (957 stocks + 17 site pages incl. about.html). news.html is excluded.
  `update_sitemap.py` refuses to touch stock URLs if the indexable list has < 200 entries.
- **news.html:** `noindex, follow`, newest 240 stock + 60 general articles, summaries cut to
  2 sentences (~0.4 MB, was 5.2 MB with 3,578 articles). Separate limits matter: stock news
  floods in daily and would otherwise push out all general news.
- **Why:** 3,400+ near-identical template pages looked like mass-produced thin content, and
  the site was getting almost no search traffic (603 of 3,469 pages indexed in March).
- **Structured data on stock pages:** `WebPage` + `about: Corporation {tickerSymbol}`,
  `dateModified` = data date. (Was a fake `NewsArticle` dated 2026-03-14 on every page.)
- **Analytics:** GA4 `G-WVETNMPF8V` on all content pages and all stock pages (before Sep 2026
  only 5 pages were tagged, so older GA numbers undercount).
- `robots.txt` allows all and points to the sitemap. Canonicals are set on all pages.
- Bot checks in `auth.js` / `js/analysis-core.js` only skip login redirects and auto-run for
  crawlers; they do not hide content.

### Anonymous usage limits and bot protection

- Anonymous visitors get **1 analysis per day**; trial users 5 per day for 3 days. The use is
  checked and counted once, at the top of `runAnalysis`; never re-check after counting (section 8b).
- For anonymous visitors the page (`auth.js` → `checkStockAnalysisAccess`)
  asks Lambda `stockiq-daily-usage-tracker-anonymous` for usage and redirects to signup when
  usage ≥ 1. The limit is enforced **in the page**; the analysis Lambdas themselves are open URLs.
- 26 Sep 2026: a scraper ran ~145 analyses from ~130 different IPs (Alibaba Cloud 47.82.x,
  Tencent Cloud 43.119.x), each IP once, in bursts at 3–4am Sydney, with a normal Chrome
  user agent. Per-IP limits and user-agent checks could not catch it.
- Fix in the anonymous tracker (Sep 2026): uses the real source IP from the request (not the
  one the browser reports), blocks `BLOCKED_IP_PREFIXES`, limits each /24 network to
  `SUBNET_DAILY_LIMIT` (5) anonymous analyses per day (DynamoDB keys `subnet_<net>@<date>`, "@" so the daily email ignores them),
  and adds headless/automation words to the user-agent check. Blocked requests are answered
  with usage = 1, so the page stops by itself.
- Registration abuse is handled separately by `stockiq-ip-blocking-service` (5 attempts/hour,
  one account per IP per 4 days).
- Daily usage email: `stockiq-usage-report-emailed` (03:00 AEST).

## 7. Scoring (two different systems)

| Where | Model | Code |
|---|---|---|
| Single-stock report (analysis option 1) and the stock page snapshots | 0–100 score: starts at 50, ± points for RSI, trend vs 20/50/200-day MA, MACD, P/E, P/B, revenue growth, margin, debt, liquidity, ROE, 1-year change, volume, 52-week position; clamped 0–100. Thresholds 75/60/40/25 | Lambda `stockiq-option-1-1-custom-analysis/lambda_function2.py` → `calculate_unified_investment_score` |
| Screeners (options 3–5, 7) | 12 weighted factors: RSI 20%, MACD 20%, short momentum 18%, volume 10%, medium 8%, long 6%, financial 6%, Bollinger 5%, sentiment 3%, market 3%, risk 2%, MA trend 1% | screener worker Lambdas |

- `stockiq/stock_metrics.py` is an **exact copy** of the Lambda's scoring functions. If the
  Lambda's scoring changes, copy the functions again or the pages will disagree with the app.
  (Breakdown label text was aligned on 9 Oct 2026; pages strip the trailing parenthesis anyway.)
- Stock pages use Yahoo fundamentals (converted to Finnhub units: %, D/E ratio) because the
  Finnhub free key is shared with the live Lambda. **Page and app scores can differ a lot**, not
  slightly: the page uses the previous close, the app the live price, and several factors are
  cliffs (AAPL showed 71 on the page and 47 in the app a day later; breakdown in section 11).
- **The screeners are price, momentum and volume only.** Their "financial", "sentiment" and "risk"
  factors do not use real company data, and the 12 weights total 102% in the code (section 8b).
- **Neutral wording everywhere**, public pages and the paid product: "Strongly positive …
  Strongly negative signals" plus "not financial advice". No BUY/SELL labels, targets or stop
  losses are shown anywhere (section 8b). The model calls its 1-year change "YTD"; pages relabel it.
- `about.html` documents both systems, including the 102% and the price-and-volume-only note.
  Keep it in sync if scoring changes.

## 7b. Does the screener score predict anything? (backtest, 10 Oct 2026)

The owner asked for a way to see whether the analysis "works in his favour" using fake money. First
answer: a replay of the S&P 500 screener over two years (10 Oct 2024 – 9 Oct 2026, 501 trading days,
502 stocks), using the unchanged live worker code on the prices it would have had each day. The
replay reproduced that morning's live scores exactly (502 of 502). Tools and full output:
`stockiq/check-tools/backtest/`.

- **$100,000 following the top 10, bought at the next morning's open:** changed weekly $150,177
  with no costs, $141,786 at 0.03% per trade, $123,969 at 0.1%; changed daily $159,601 / $128,312 /
  $77,086 (almost the whole account is replaced every day, so costs decide it); changed monthly
  $132,153. Index fund (SPY) $134,752; an equal amount in every stock $129,823.
- **Against luck:** 6% (daily) and 11% (weekly) of 300 random 10-stock portfolios did better than the
  top 10 before costs; monthly, 43% did. The top 10's lead over the average stock is +0.07% a day,
  +0.12% a week, +1.05% a month, none of it statistically clear (t 1.2, 0.5, 0.4).
- **The score does not sort good from bad.** The bottom 10 also beat the average stock, and held for
  a month did best of all ($193,505). By label, "Strongly negative" stocks rose most over the next
  week (+0.62%), "Strongly positive" +0.32%, "Mixed" +0.29%: the labels carried no information in
  this period.
- **Conclusion:** a small, unproven edge at a day to a week before costs, nothing at a month, and
  no support for the signal labels or the "model probability" figure. Limits: today's index members
  used throughout, no dividends, one rising market.
- Not done yet: the same test for the other screeners and crypto, and a test of each of the 12
  factors separately (to find which ones help and re-weight the score). The live paper portfolio
  now exists: the dashboard's practice portfolio and its autopilot (section 8c), whose own record
  is the forward test.
  Do not publish any of this as a promise; if shown to users it is past performance with the limits.

## 8. Front end

- `analysis.html`: options 1–7 (stock/ETF report, signals, US/EU/Asia/other screeners, crypto).
  Logic in `analysis-functions.js` (~350 KB, holds the stock lists and all formatters) +
  `js/analysis-core.js`. How the screeners, signals and crypto work: section 8b.
- `dashboard.html`: report history, favourites, plans/upgrade (Stripe), manage subscription,
  "Run in Background" (through `stockiq-screener-coordinator`), 🎯 performance tracker.
- `index.html`: market overview widgets, guides, "How StockIQ Works", **Pricing section**
  (`#pricing`, three plans in USD), email signup ("Get Screener Highlights by Email", details in
  `stockiq.md`), comparison table.
- **Practice portfolio and AI autopilot** (dashboard, built 10 Oct 2026): a fake-money portfolio the
  owner buys and sells in by hand, and an autopilot that trades it from the screeners' results,
  reviews its holdings with the AI model and recent headlines, and tries bounded changes to its own
  rules. `practice-portfolio.js`, `practice-autopilot.js`, Lambdas `stockiq-paper-portfolio` and
  `stockiq-ai-trader`. **Everything about them, and how to work on them, is in section 8c.**
- Stock pages load `sidebar.js`, `stock-prices.js` (live ticker), `ai-chat.js`, `auth.js`, `theme.js`.
- AI chat button: bottom-right on every page; on the home page it moves left of the news panel
  only from 1401px wide (the panel is hidden below that).
- Every public page footer carries a "General information only, not financial advice …" line.
- Theme: light/dark by time of day unless the user overrides (`localStorage.theme`).
- Live prices on stock pages (main ticker + "People also watch" cards) come from
  `stock-prices.js` → a price Lambda, refreshed every 5 s. Pages opened from local files
  show `--` (the proxy only answers the live site), which is expected.
- Utility page with no footer, not in the sitemap: `clear-cache.html`. (`market-data-sidebar.html`
  and `market-data-widget.html` called a Lambda that no longer exists and were deleted 10 Oct 2026.)
- Lambda function URLs are hard-coded in the JS/HTML. `stockiq/lambda-url-mapping.json` maps
  each URL to its function name. Regenerate it with `bash generate-lambda-url-mappings.sh`
  (it rewrites the file in place over a few minutes; don't read it meanwhile).

## 8b. Screeners, signals and crypto: how they work now (verified end to end 9–10 Oct 2026)

Everything in this section was checked by running every analysis button with real data
(method at the end). Read it before touching `analysis-functions.js`, the coordinator, the
crypto orchestrator or any worker.

### Two code paths, one set of lists

- **On-page run:** `runAnalysis(option, subOption, event)` in `analysis-functions.js` calls the
  worker Lambdas straight from the browser and formats the text itself.
- **"Run in Background" (dashboard):** `stockiq-screener-coordinator` calls the same workers
  server-side, formats the report and CSV, and saves them to the user's history.
- The stock lists therefore live in **two places that must stay identical**: the `*Universe`
  arrays in `analysis-functions.js` and `STOCK_UNIVERSES` in the coordinator. Exception: on the
  page path Russell 1000/2000 send only `worker_id`, so those workers use lists built into
  their own code; the coordinator sends its own lists for them.
- Wording is applied only in those two places (plus the report Lambda and the crypto
  orchestrator). **Workers return data only, so a wording or list change never needs a worker
  redeploy.**

| Screener | Page call | Coordinator key | Worker group (count) | List size | Source of the list |
|---|---|---|---|---|---|
| Dow 30 | `3, '8'` | `3-8` | `stockiq-option-3-8-worker-N` (3) | 30 | slickcharts.com |
| S&P 100 | `3, '100'` | `3-100` | `stockiq-option-3-1-worker-N` (10) | 101 | Wikipedia |
| NASDAQ 100 | `3, '7'` | `3-7` | `stockiq-option-3-7-worker-N` (10) | 101 | slickcharts.com |
| S&P 500 | `3, '3'` | `3-3` | first 50 of `stockiq-option-3-5-worker-N` | 502 | Wikipedia |
| S&P 400+600 | `3, '2'` | `3-2` | `stockiq-option-3-2-worker-N` (100) | 995 | Wikipedia (400 + 600) |
| S&P 1500 | `3, '4'` | `3-4` | `stockiq-option-3-4-worker-N` (150) | 1,497 | Wikipedia (500 + 400 + 600) |
| Russell 1000 | `3, '5'` | `3-5` | `stockiq-option-3-5-worker-N` (100) | 877 | old list, dead tickers removed |
| Russell 2000 | `3, '6'` | `3-6` | `stockiq-option-3-6-worker-N` (200) | 1,829 | old list, dead tickers removed |
| ASX 50 / 100 / 200 / 300 | `5, '50'` … `'300'` | `4-50` … `4-300` | `stockiq-asia-5-1` … `5-4-worker-N` (5 / 10 / 20 / 30) | 49 / 99 / 195 / 294 | Wikipedia ASX 50 and ASX 200; 100 = largest 100 of the 200; 300 = the 200 plus live members of the old list |
| UK FTSE 100 | `4, 'ftse100'` | `5-ftse100` | `stockiq-europe-4-1-worker-N` (10) | 100 | Wikipedia |
| Japan Nikkei 225 | `5, 'nikkei225'` | `5-nikkei225` | `stockiq-asia-5-5-worker-N` (21) | 225 | Wikipedia |
| Crypto universe | `7, 'coinspot'` | `7-1` | orchestrator + 54 `stockiq-option-7-1-worker-N` | 540 coins | CoinGecko top by market cap, price-checked |
| Single coin | `72, 'single'` | – | `stockiq-option-7-2-worker-1` | – | – |

- The option numbers are inconsistent for historical reasons (ASX is page option 5 but
  coordinator `4-…`; FTSE the reverse). New screeners: use `5` + the same subOption everywhere.
- Russell 1000/2000 were **not** refreshed: no complete free source a script can read (iShares
  holdings URLs return a web page, Wikipedia has no list). ASX 300 is an approximation.
- Do not use asx50list.com / asx100list.com / asx200list.com / asx300list.com: years out of date.
- Yahoo symbol format: US share classes use a dash (`BRK-B`, not `BRK.B`); FTSE adds `.L`
  (`BT.A` → `BT-A.L`); ASX `.AX`; Tokyo `.T`. A symbol Yahoo does not know is silently dropped.
- Every symbol in a list was checked against the price source before being included. To check a
  symbol, call `stockiq-price-proxy` (`?symbol=X`; it answers 500 for an unknown symbol).
  **Do not probe Yahoo in bulk from this machine**: after a few hundred calls it returns HTTP 429,
  and the daily run's snapshot step then gets no prices (section 9).
- Button labels in `analysis.html`, the `universeSize` constants in the formatters and the
  coordinator's `universe_sizes` all carry the real list sizes. Update all three with a list.
- `NIKKEI_COMPANY_NAMES` in `analysis-functions.js` supplies names for the Nikkei output.

### Batching

- Each worker gets 10 stocks, or a few more only when a list is longer than workers × 10:
  `perWorker = max(10, ceil(list / workers))`. Workers accept more than 10.
- **Never send a worker an empty batch.** Some groups (the S&P 500 / Russell 1000 workers) fall
  back to their built-in list and return unrelated stocks. Both paths skip empty batches.
- No worker Lambda needs creating or deleting when a list changes; idle functions cost nothing.
- The coordinator de-duplicates results by symbol.

### What the screener workers really do

- They return ~47 data fields per stock and no report text. Codes: `STRONG_BUY`, `BUY`,
  `MODERATE_BUY`, `HOLD`, `MODERATE_SELL`, `SELL`, `STRONG_SELL` (underscores). Field names that
  matter for CSV: `change_24h`, `distance_from_52w_low`, `52w_high`, `52w_low`.
- **They do not fetch fundamentals.** `get_fundamentals()` returns hard-coded guesses for ~50
  large US stocks and defaults for everything else (P/E 25, beta 1.0, dividend 0, size "Mid",
  sector "OTHER"). "Earnings risk" is the calendar month (Jan/Apr/Jul/Oct = HIGH), "sentiment" is
  the day's price move. The "Financial health" factor therefore adds the same +0.12 to nearly
  every stock: **the screeners are price, momentum and volume only.** `about.html` says so, and
  the CSV no longer exports P/E, market cap, beta, dividend, sector or earnings risk.
- The 12 weights really total 102% in the code (0.18+0.08+0.06+0.20+0.20+0.10+0.06+0.05+0.03+
  0.03+0.02+0.01). The About and FAQ pages say so. Changing it would change every score.
- **ASX quirk (open):** once the ASX has closed, Yahoo returns the last session bar twice, so the
  ASX workers compute a 24-hour change of 0 for every stock (also flattening their sentiment
  factor and `Momentum_Signal`). Not checked during ASX hours. Fix belongs in the 65 ASX workers.
- A worker returns nothing for a few valid symbols even when asked directly (WBD, PSKY). Open.
- Real fundamentals, or the ASX fix, mean redeploying worker groups (~630 functions in total).

### Output wording: describe, don't advise

- Codes are used for logic but **never shown**. Everything printed goes through a label function:
  `signalLabel()` / `horizonLabel()` in `analysis-functions.js`, `signal_label()` /
  `horizon_label()` in the coordinator and crypto orchestrator, `signal_label()` in the report
  Lambda. Labels: Strongly positive, Positive, Slightly positive, Mixed, Slightly negative,
  Negative, Strongly negative. Both code styles are accepted (stock: underscores; crypto: spaces,
  plus `CONSIDER` and `AVOID`). An unknown code shows as **"Unrated"**: if that ever appears, a
  worker has a new code that must be added to all the label maps.
- Stop loss / take profit are shown as "Lower / Upper reference level"; buy limit / buy stop as
  "Pullback / Breakout level"; profit probability as "Model probability estimate"; strategy as
  "Horizon". Lists are headed "TOP N BY SCORE".
- The single-stock report (`stockiq-option-1-1-custom-analysis`) no longer prints BUY/SELL,
  "Buy immediately", position size, urgency or action steps; it prints a signal summary, "what
  the model sees", reference levels and a disclaimer. Scoring is unchanged.
- The dashboard performance popup reports the price change since the report (it used to say
  "The AI predicted upward movement" whenever the price was up).
- Any new formatter must follow this: no "buy", "sell", "target", "stop loss", "take profit",
  "position size", "recommendation", "picks" or "opportunities" in output.
- Not changed: the workers still return raw codes and a few descriptive breakdown strings
  ("RSI Buy Zone"); three Lambdas with old wording are not called by the site
  (`stockiq-option-3-1-us-screener`, `stockiq-option-3-1-sp100`,
  `stockiq-option-3-dynamic-coordinator`). Reports already saved in users' history keep the old
  wording until the 30/90-day auto-delete removes them.

### CSV exports

- Stock CSV columns (page `generateExcelExport` and coordinator): `Signal`, `Lower_Level`,
  `Upper_Level`, `Model_Probability_%`, `Horizon`, `Horizon_Days`, the change columns,
  indicators, `Distance_52W_High_%`, `Distance_From_Low_%`, `52W_High`, `52W_Low`,
  `Market_Regime`, `SPY_20d_Change_%`, `Score_Breakdown`. Several of these were always 0 before
  Oct 2026 because the code read field names the workers do not return.

### Dashboard performance tracker (🎯 button)

- `trackScreenerPerformance` in `dashboard.html` parses the saved report text: the symbol and
  price at the start of each numbered line. Do not change that part of a line.
- Stock pattern: `N. SYMBOL <up to 40 chars> <currency>PRICE`, symbols 1–10 characters with an
  optional `.XX` or `-X` suffix, currencies `$ £ € ¥`. Add `₹` / `₩` for India / Korea.
- A company name between symbol and price must stay short (Nikkei names are cut to 22 chars).
- Rebuilt 10 Oct 2026: one parser (`parseScreenerTop10`) and one calculation
  (`screenerTop10Performance`) feed both the row badge and the popup. Before that the two had
  separate copies: the popup failed on every UK report, the badge never appeared for Nikkei, a
  symbol with no price still counted in the average, stocks under $1 showed false moves, every
  currency was shown as "$", and old crypto reports priced the wrong coin.
- The popup also shows "Top 10 and the index over the same time": the top-10 average 1 day, 1 week,
  2 and 3 weeks after the report and now, beside the index the list comes from (`TOP10_BENCHMARKS`
  keyed on the report's name; Bitcoin for crypto; add a line there for a new screener). The price
  source keeps about a month of daily closes, so index figures start from the close on the report
  day (approximate) and appear only after the next trading day.
- Test it without logging in: `check-tools/tracker_run.js` runs the page's real tracker code on a
  saved report text with live prices (`NAME='<report name>' DASH=<dashboard.html> node tracker_run.js <label> <report.json> <ISO time>`).

### Crypto

- **The 54 crypto workers ignore the coin list they are sent in batch mode** and use a list
  built into their code. So `stockiq-option-7-1-orchestrator` holds the list itself (`COINS`:
  540 pairs of `(symbol shown, Yahoo ticker without -USD)`) and calls each worker's
  **single-coin mode** (`{"single_coin": "<ticker>"}`) once per coin, 60 at a time, round-robin
  over the 54 worker URLs, retrying a failed call on the next worker. ~15 s for 540 coins with
  2,048 MB (it was 45 s at 512 MB).
- The list is the top coins by market cap (CoinGecko, 10 Oct 2026) without stablecoins and
  wrapped/staked tokens. A coin is only included if Yahoo's price for its ticker was within
  0.8×–1.25× of CoinGecko's and it had 60+ days of history. **Many coins share a symbol on
  Yahoo**: 125 need Yahoo's numbered ticker (SUI is `SUI20947-USD`, ARB is `ARB11841-USD`);
  the plain symbol is a different coin. Before this, the top-ranked coin was often a wrong match
  (CORE priced as cVault.finance at $5,698) and 27% of coins had no data.
- `CRYPTO_TICKER_MAP` in `analysis-functions.js` holds the same symbol → ticker mapping for
  single-coin analysis. **Keep it in step with `COINS`.** `mismatchedCoinSymbols` in
  `formatSingleCoinResult` warns on symbols still known to be the wrong coin.
- To rebuild the list: CoinGecko `/coins/markets` by market cap; drop stablecoins and wrapped
  tokens; check `SYMBOL-USD` on Yahoo; if the price does not match, use Yahoo's search API
  (`query2.finance.yahoo.com/v1/finance/search?q=<coin name>`) to find the numbered ticker and
  check its price. Go slowly (429s).
- The orchestrator zip must contain `orchestrator.py`, `orchestrator_simple.py`,
  `prediction_memory.py`. Handler `orchestrator.lambda_handler`.
- The page shows the orchestrator's `report` text directly (`type: 'coinspot_comprehensive'`);
  internal names still say "coinspot" although the list is no longer CoinSpot's.
- Equal scores are ranked in coin-list order (largest market cap first), so the top 10 is the
  same on every run. (It used to depend on which worker answered first.)

**Top-10 history (rebuilt 10 Oct 2026).** Each top-10 coin in a report shows how long it has been
in the top 10 and what its price has done since: "In the top 10 since 10 Oct 06:02 UTC: $a → $b
(+5.0%)", the time, the score then and now, and "in the top 10 at N of M checks since then".
- EventBridge rule `stockiq-coinspot-predictions-schedule` (every 30 minutes) invokes **the
  orchestrator itself**. A scheduled run records the top 10; a user's run (through the Function
  URL, or the coordinator) only reads. One coin list and one ranking, so the history always
  describes the list the user sees. A URL call can never write: it always has `requestContext`.
- Table `stockiq-coinspot-prediction-status`: one row per coin (`streak_start`, `streak_price`,
  `streak_score`, `last_seen`, `checks_in_top10`, `ticker`) plus the marker row `_last_check`
  (`last_check`, `check_no`). A coin keeps its run across one missed check (65 minutes); after
  that a new run starts. If the last check is older than 100 minutes the report says history is
  not available. A check that ranked under 80% of the list is not recorded. Rows without
  `last_seen` are left over from the old updater and are ignored.
- **Track-record log:** every time a coin enters the top 10, a permanent row goes into
  `stockiq-coinspot-predictions` (`log_version` 2: entry time, ticker, price, score, rank, the
  coin's 24h / 7d / 30d change, RSI, volume ratio). Nothing reads it yet. Its purpose: after a
  few weeks, measure what coins did in the 24 hours / 7 days after entering the top 10 compared
  with the average coin. **Nobody knows yet whether the score predicts anything**; the owner's aim
  is to make it easier to see which coins tend to do well, and this log is the evidence for that.
  Present any result as past performance, never as "likely to profit".
- Icons: 🟢 an hour or more, 🟡 under an hour, 🔵 new or no history. Keep an emoji from the
  U+1F300–1F9FF range before the symbol: the dashboard uses it to recognise a crypto report.
- The report's wrapper carries `data-top10-tickers='IMX:IMX10603,…'`. The dashboard 🎯 tracker
  reads it to look up the right coin (old saved reports have none and fall back to `SYMBOL-USD`).
- `crypto-filter-buttons.js` adds the "Time in the top 10" slider to crypto results; it filters
  the top 10 on `hours_in_top10` and re-uses `signalLabel()`.
- What it replaced: `stockiq-coinspot-predictions-updater` ran every 15 minutes as an old copy
  of the orchestrator, ranking the workers' built-in list, so its history matched almost none of
  the coins users saw; "consistency" stars partly came from the letters of the coin's symbol and
  the report printed LOW / MEDIUM / HIGH RISK. That function is no longer triggered (still exists).

### Access checks and usage counting

- `runAnalysis` checks access (`checkDailyUsageLimit` → `authManager.checkStockAnalysisAccess`)
  and counts the use **once, at the top, for every option**. Anonymous: 1 per day. Trial: 5 per
  day for 3 days. Paid plans pass the check.
- **Never check access again after the use has been counted.** 14 handlers used to (crypto,
  single coin, six US screeners, ASX, Nikkei): the second check saw zero left, so an anonymous
  visitor's single-coin run went to signup.html and a trial user's last analysis of the day went
  to the upgrade page, both with the use spent and no result. Removed 10 Oct 2026.

### How to test every button end to end (no browser needed)

The scripts are in `stockiq/check-tools/` (see its `README.md` for one-line examples):
`page_run.js` (step 1), `anon_run.js` and `trial_run.js` (step 2), `run_all.py` and `analyse.py`
(step 3). `check-tools/lists/` holds the one-off scripts that rebuilt the index and crypto lists.
The method:
1. **Page path:** load `analysis-functions.js` in a Node `vm` context with a stub `document` /
   `window`, real `fetch`, and `displayResults`, `displayError`, `saveAnalysisToHistory`
   overridden to capture the result. Block fetches to usage / trial / dashboard Lambdas (answer
   them with a fake OK) so nothing is written. Call `runAnalysis(option, subOption, event)` per
   button and check: no error, every worker call 200, result count ≈ list size, no raw codes,
   no "Unrated", no `undefined` / `NaN`, and the tracker regex finds 10 symbols.
2. **Access rules:** also load `auth.js` (expose `authManager` on the global object) and
   simulate the usage tracker in the fake fetch; record every write to `location.href` with a
   stack trace. Test 1 use left (must get a result) and 0 left (must redirect before running).
3. **Coordinator path:** import the coordinator in Python, patch `urllib.request.urlopen` to
   intercept the dashboard save URL, call `lambda_handler` for each key. Needs
   `AWS_DEFAULT_REGION=us-east-1` for the `worker_id` screeners (`3-4`, `3-5`, `3-6`).
4. **Report Lambda and formatters:** run old and new code on identical cached inputs and diff:
   scores and numbers must not change when only wording changes.
5. Read a few outputs. Tests that only count lines miss wrong content.
Not testable this way: anything behind a real login (payments, dashboard screens, real trial
accounts). Say so when reporting.

## 8c. Dashboard: practice portfolio and AI autopilot (read this before working on the dashboard)

Built 10 Oct 2026 from the owner's idea of "fake money" to see whether the analysis works in his
favour, then extended the same day into an autopilot that trades it. **Everything here is fake
money: no real trade is ever placed, and nothing here may ever be connected to real money.** This
section is written from the code as deployed on the evening of 10 Oct 2026. Verify against the
code before relying on a detail (section 10).

### What the owner sees on the dashboard, top to bottom

**Practice portfolio** (above Report History, container `#practice-portfolio`):
- Four cards: Account value (the cash plus every holding at its latest price; under it the change
  since the start, split into what has been sold and what is still held), Practice cash left, In
  holdings, and "For comparison" (the same money in an S&P 500 index fund instead; it says "no change
  yet" while the US stock market has not traded since the buys, e.g. a weekend: `marketFlat`).
  **Nothing is shown until the latest prices are in** (4 seconds at most): before 10 Oct the page
  first showed holdings at what was paid, which the owner took for a second, "correct" account value.
- One line, **whose result is whose**: "Of the +$226.84 since the start: your own buys +$201.85;
  the autopilot +$24.99 (+$7.91 on what it has sold, +$17.08 on what it still holds)". Shown once
  the autopilot has bought anything. A holding not sold yet counts at its latest price.
- The buy row: search box (code or company name, same lookup as the home page), "Enter $" **or**
  "or quantity" (the other is worked out from the latest price), an optional note, "Practice buy".
- The holdings table: Holding, Bought (date and time), Price then, Price now, Value, Change, Sell.
  Under each name a line says whose it is: "Bought by you: it stays until you sell it", or for the
  autopilot's, when it will sell at the latest and at what loss or gain sooner.
- "Sold (N)" folded list with a summary, "Clear sold list" and an × per line (clearing only tidies
  the list: what a sale brought in is already in the cash). "Refresh prices", "Reset fake money".

**AI autopilot** (directly under it, container `#practice-autopilot`; shown only to allowed users):
- On/off switch and a status box (what it holds, last and next check-in).
- **Quick set-ups**: "Quick coin trading", "Steady shares", "Shares and coins".
- **Risk level** slider (Cautious … Adventurous) with a sentence of what the level means, and
  **Your own limits**: two optional fields, "Sell at a loss of __ %" and "Sell at a gain of __ %",
  and a **Trailing stop** menu (protects a gain / from the moment it is bought / off) with a line
  saying what the chosen kind does.
- Budget for the AI, and the three **pace** fields: Build up to it over (days), Checks in, Keeps a
  holding at most. Each pace field is tagged "automatic" (it follows the risk level and moves with
  the slider; shown as an empty box with the level's value in grey, or "Automatic: …" in a menu) or
  "set by you" (it stays put); a link hands all three back to the level. Then **two lines that
  describe what exactly these settings will do**.
- Screeners it buys from, grouped by market (all 15).
- **What it may do by itself**: three switches (sell early on the AI model's review, try changes
  to its own rules, email me its reviews).
- "Check in now", "Sell everything it holds (N)", and a line saying "Saving…" / "✓ Saved." /
  "Not saved: reason". There is no save button: every change saves itself.
- **How it is doing**: what it holds now and when each will be sold, with the AI model's latest
  review of it; the last 30 days in dollars and as a share of the budget; finished trades (up /
  down, average); a folded breakdown; notes the AI model wrote from the record.
- **Improving its own rules**: the rules in force, which are set by the owner, which it changed
  itself ("put it back"), the running trial ("Stop this trial") and earlier trials.
- **What it has done**: every buy, sell and check-in note, newest first; "Why, and the details" /
  "The plan for it" folded under each trade; "Refresh now"; a switch "Buys and sells only".

### Files and services

| Thing | Where | Notes |
|---|---|---|
| Portfolio section | `website/practice-portfolio.js` (`?v=11` in `dashboard.html`) | Sums and page. Pure functions exported for tests: `newState, fxFor, fxRate, versusMarket, applyBuy, applySell, applyClearSold, soldSummary, valueOf, summarize, splitGain, planLine` |
| Autopilot panel | `website/practice-autopilot.js` (`?v=17`) | Controls and reports only; decisions are made by the Lambda |
| Page | `website/dashboard.html` | Two containers (about line 1250) and the two script tags at the end. **Raise `?v=N` whenever a script changes**: scripts are cached for a day |
| Portfolio storage | Lambda `stockiq-paper-portfolio` (128 MB, 10 s), table `stockiq-paper-portfolios` | Actions `get`, `save` (with `expectedVersion`), `reset`. One item per user: `data` (JSON), `version` |
| Autopilot | Lambda `stockiq-ai-trader` (Python 3.12, 512 MB, 300 s, role `acp-lambda-role`), table `stockiq-ai-trader` | Actions `get`, `save`, `run`, `sellall`, `tune`. Env `AI_TRADER_USERS` (allow-list; `*` = everyone) and `OPENAI_API_KEY` (never print it) |
| Schedule | EventBridge `stockiq-ai-trader-schedule`, `cron(10,40 * * * ? *)` | Every 30 minutes; `SLOT_MINUTES` in the Lambda must match. **Disable this rule to stop everything** |
| Screener data | `stockiq-screener-coordinator` | Called with no `userId`, so nothing is saved to anyone's history |
| Prices | `stockiq-price-proxy` | Also exchange rates (`AUDUSD=X`, `USDJPY=X`) and the S&P 500 fund (`SPY`) |
| Headlines | Google News RSS (coins), Yahoo Finance RSS (shares) | Fetched by the Lambda; the AI model has no internet |
| AI model | OpenAI `gpt-4o-mini`, JSON replies; `gpt-4o` for the holdings review when a gain is at stake | Three uses: choose buys, review holdings, write notes. `aws lambda invoke … --payload '{"model_test": true}'` asks each one question and says which answered |
| Email | SES, from `autopilot@stockiq.tech` to the account's own address | The role has SES access; the owner's address is a verified identity (SES is still in sandbox) |

The Function URLs are written into the two scripts. As everywhere on this site the `userId` is
whatever the browser sends; the autopilot only acts for addresses in `AI_TRADER_USERS`.

### The practice portfolio in detail

- The browser does the sums and sends the whole portfolio; the Lambda checks shape and size and
  uses `version` so two tabs (or the autopilot) cannot overwrite each other. On a clash the page
  reloads and says so.
- A holding: `id, symbol, label, name, currency, qty, buyPrice, buyFx, costUsd, boughtAt,
  spyAtBuy, note`, and for the autopilot's `by: 'ai'` and `screener`. A sold one adds `sellPrice,
  sellFx, proceedsUsd, soldAt, spyAtSell`. `symbol` is what prices are looked up by (a coin may
  need Yahoo's numbered ticker); `label` is what is shown.
- Other currencies are valued in US dollars. **`fxFor` / `fxRate` here and `fx_pair` / `usd_rate`
  in the autopilot must follow the same rule**: AUD, GBP, EUR, NZD use the dollars-per-unit quote
  (`AUDUSD=X`); every other currency the per-dollar quote turned over (`USDJPY=X`), because Yahoo
  rounds `JPYUSD=X` to 0.0063. London prices are pence (÷100). A holding with no price shows at cost.
- `planLine(h, plan)` writes the "whose is it" line. The plans come from the autopilot panel through
  `practicePortfolio.setPlans(plans, { realizedUsd })`. `splitGain` uses that `realizedUsd` (the
  autopilot's own running total) so that clearing the sold list does not move its sales into "your
  own". `redraw()` re-renders without losing what is being typed in the buy row.
- `window.practiceBuyFromTop10` is the "＋ Practice buy" button on each line of the Top 10
  Performance popup (it uses the report's price-source ticker).
- **Owner's decisions:** buying, selling and progress stay on the dashboard (no buy buttons on stock
  pages or reports). The S&P 500 columns and "N of M ahead" sentences were removed at his request;
  only the "For comparison" card remains. `spyAtBuy` / `spyAtSell` are still stored, because the
  autopilot's record uses them. Wording stays "practice", "fake money, no real trades".

### The autopilot: settings (table `stockiq-ai-trader`, cleaned by `clean_settings`)

| Setting | Values | Meaning |
|---|---|---|
| `enabled` | on / off (default off) | Only for users in `AI_TRADER_USERS` |
| `risk` | 1–5 (default 3) | The level: see the table below |
| `budgetUsd` | 100 … 1,000,000 (default 10,000) | The most it has invested at once |
| `periodDays` | 1–90 | "Build up to it over": the budget is released in equal steps over this long. **Not the holding time** (the owner mixed them up twice) |
| `everyHours` | 0.5, 1, 3, 6, 12, 24 | How often it checks in |
| `maxHoldDays` | 0.5 h … 60 days, stored in days | The longest it keeps a holding |
| `auto` | any of `periodDays`, `everyHours`, `maxHoldDays` | **Which of those three are left to the risk level.** For a listed one `clean_settings` puts in the level's own value (`PACE`) every time, so the rest of the code only ever sees numbers. A new user leaves all three; settings saved before 10 Oct evening have none (all set by hand) |
| `screeners` | any of the 15 keys (default none) | Coordinator keys: `3-8 3-100 3-7 3-3 3-2 3-4 3-5 3-6 4-50 4-100 4-200 4-300 5-ftse100 5-nikkei225 7-1` |
| `aiSell`, `selfTune`, `emails` | on unless switched off | "What it may do by itself" |
| `stopPct`, `takePct` | empty, or 1.5–30 and 2–80 | The owner's own loss limit and gain mark, as sizes in percent |
| `trailMode` | `gains` (default), `full`, `off` | The kind of stop that follows a holding. `gains`: it starts once the holding has risen beyond its normal wobble. `full`: a full trailing stop loss, under the price from the moment of buying, so a faller is cut early (exit kind `cut`). `off`: none |

| Level | Holdings | Buys from the top | RSI under | 30-day move within | Loss limit | Gain mark | Coins, when shares are ticked too |
|---|---|---|---|---|---|---|---|
| 1 Cautious | 12 | 5 | 68 | 20% | −5% | +8% | 0% |
| 2 Careful | 10 | 8 | 72 | 30% | −7% | +12% | 0% |
| 3 Balanced | 8 | 10 | 76 | 45% | −10% | +18% | 25% |
| 4 Bold | 6 | 15 | 82 | 70% | −14% | +28% | 50% |
| 5 Adventurous | 4 | 20 | no limit | no limit | −20% | +45% | 100% |

- **The pace each level sets** (`PACE`, sent to the panel as `options.pace`; added 10 Oct when the
  owner asked why the slider did not move these fields): Cautious 10 days / once a day / 20 days;
  Careful 7 / twice a day / 10; Balanced 5 / every 6 hours / 5; Bold 2 / every 3 hours / 2;
  Adventurous 1 day / every hour / 1 day (build-up / check-in / longest holding). So one slider can
  drive everything, and anything set by hand overrides it. The quick set-ups set these by hand.
- **With only coin screeners ticked the whole budget may go into coins at any level**
  (`coin_share`); the last column only applies to a mix. The panel's wording follows (`mixed`).
- The rules in force for a user are `rules_for(settings, state)`: the level, then what the
  autopilot changed itself for that level (`state.tune.values`), then the owner's own limits.
- A screener belongs to a market and is only traded while that market is open (`MARKET_HOURS`,
  UTC, Mon–Fri: US 14:35–19:55, Australia 00:05–04:55, Japan 00:05–05:55, UK 08:05–15:25; coins
  always). Each market keeps its own last-checked time, so a user with US and Australian screeners
  is checked in both sessions. **The markets of what it still holds count too** (`its_markets`):
  on 10 Oct the owner un-ticked the crypto screener while it held a coin, and because only the
  ticked screeners' markets were looked at, the coin was left unattended (no time limit, no stop)
  until that was fixed the same afternoon. "Check in now" acts on everything (10-minute gap between presses).
- Add a screener: one line in `SCREENERS` (name, coordinator option and subOption, kind, market,
  group). The panel lists whatever the Lambda sends.

### One check-in, step by step (`run_user`)

1. Load the user's practice portfolio. `settle`: anything sold since last time, also by hand, goes
   into the history. `look_back`: re-price holdings sold a while ago (see "learning").
   `review_ai_sells`: pause or un-pause the AI model's early sells.
2. Fetch the chosen screeners' results (`get_snapshot`: a fresh run through the coordinator unless a
   copy under 20 minutes old is stored as `_snapshot#<key>`, so **the data is fresh at every
   check-in**), the latest price of each of its holdings, and exchange rates.
3. **Fixed selling rules** (`review_sells`), first that applies: at the loss limit; at the gain
   mark; **keeping part of a gain** (see below: `gain_arm`, `gain_floor`); held the longest
   allowed time; the screener
   signal turned negative or its score fell below zero; **slipped down the ranking** (below 5 times
   the level's ranking limit with under half the score it was bought on: `FADE`). A check-in up to
   5 minutes early still counts for the time limit (`GRACE`). Each holding's best and worst change,
   as seen at check-ins, is kept (`peak`, `low`), and its path (`path`: hours held and change at
   each of the last 16 check-ins).
   **Keeping part of a gain: the stop that follows a rising holding** (`follow_stop`; reworked twice
   on 10 Oct). The gain mark is where it always sells, but waiting for +18% on a 6-hour holding
   hands back most quick rises, and the owner then rejected fixed distances as "a dumb static
   rule". So the stop is set from **that holding's own movement and its figures now**:
   - `daily_range`: how much it normally moves in a day, the average of its last 14 days' high-to-low
     range, from the daily prices `fetch_quote` already receives (CFX about 6.3%, Bitcoin 2.4%, a
     large share about 1.9%). `typical_move` scales that to the gap between check-ins by the square
     root of time (CFX: about 0.9% in 30 minutes).
   - Protection starts once it has risen 1.5 typical moves (`STOP_ARM`): beyond its normal wobble.
   - From then on it may slip a number of typical moves from its best before it is sold
     (`stop_room`): 2.5 as a rule (`STOP_ROOM`, scaled by the level's `trail`, which its own trials
     may change); +0.5 while its screener score and rank are as strong as when it was bought;
     −0.75 when they have weakened (score under 70% of then, or rank far lower); −0.5 when RSI is 80
     or more; −0.5 in the last quarter of its holding time; −1 when the AI review answered
     "tighten". Never under 1 or over 3.5, and it is always sold while a fifth of the best gain is
     left (`STOP_KEEP`). Example: CFX up 6.15% at its best with strong figures is sold if it slips to
     about +3.4%; with weakened figures at about +4.6%; a calm coin at about +5.3%.
   - **The owner chooses the kind** (`trailMode`, added after he asked "should this have a trailing
     stop loss?": it had one, but only for gains, and nothing on the panel showed it). `gains` is
     the above. `full` puts the stop under the price from the moment of buying
     (`best − room × typical move`, with the best starting at the buying price), so a holding that
     only falls is sold after that many typical moves instead of waiting for the loss limit; such a
     sale is exit kind `cut` ("sold by its trailing stop before it had risen"), so the record shows
     whether it saves more than normal dips cost. `off` sets no following stop. `stop_words` puts
     the chosen kind into the plan of a buy and the story of a sale.
   - The reasons are kept and shown under the sale ("The stop that followed it: …") and the stop as
     last worked out is stored with the holding (`state.open[id].stop`) for the dashboard.
   - Without daily prices for a holding the simpler rule by holding time still applies (`gain_arm`,
     `gain_floor`: protection from half the gain mark at 20 days down to 1% at 6 hours; a small gain
     may give back half, one near the mark a quarter). The tuner's hindsight estimate for `trail`
     still uses that simpler rule.
4. **The AI model's review** (`ai_review`, if `aiSell` is on and not paused): for each holding the
   rules are keeping it is given what it was bought on, the screener's figures now, how it has
   moved, **its path since buying**, what is protected, when the rules will sell it, and up to three
   recent headlines that name it. It is asked whether a rise is still building or has stalled or
   turned, weighed against the time left, and told how much the holding normally moves between
   check-ins (so a dip smaller than that is not taken for a turn). It answers **hold, tighten or
   sell** with a reason; "tighten" keeps the holding with a closer stop (`tight`). **A larger model
   (`STRONG_MODEL`, gpt-4o) does this review when a gain is at stake** (some holding is up enough
   for its gain to be protected), at most 8 times a day per user (`STRONG_PER_DAY`, `state.strong`;
   about 0.3 US cents a call, so under $1 a month; the owner's limit). Otherwise gpt-4o-mini. If the
   larger model cannot be reached the usual one answers. **It can only sell earlier than the rules, never keep past one.**
   A "keep" is stored with the holding (`view`) and shown on the panel.
5. The sales are made; each gets a log entry with its story (`sale_detail`).
6. What may be spent (`allowance`): the budget released in equal steps per check-in over
   `periodDays`, rounded up to whole holdings, never more than the budget or the practice cash; at
   most 3 buys a check-in; buys are in whole cents and the last one takes exactly what is left.
   **"Check in now" is a request to act**: when only the pace of the build-up stands in the way, a
   check-in asked for by hand releases the next part of the budget early (`state.ahead`, counted
   into the steps; reset when the build-up restarts) and notes it. The schedule then carries on
   from there, no faster. Added 10 Oct after the owner pressed the button expecting a buy and got
   none. The answer to `run` also carries `summary.why`, the reason when nothing was traded.
7. The shortlist (`shortlist`): the top of each chosen screener with a positive score and signal,
   not already held, not sold within two days (or twice the holding time if shorter), inside the
   level's RSI and 30-day-move limits; ordered by place in its own screener.
   **A coin must have stayed there** (`note_stays`, `STAY_CHECKS` = 2): when it checks in every
   3 hours or less, a coin is only bought once it has been on the shortlist at two check-ins
   running, so the first coin buy comes at the second check-in (note key `stay`). Reason, from the
   live data of 10 Oct: the site's own top-10 history showed 8 of 26 coins gone again after one
   30-minute check, and the owner's first coin went from rank 1 to rank 149 in four hours. Shares
   are never held back, and nor are coins when it checks in less often (a day is too long to wait).
   Each buy remembers how long it had stayed (`stay`), the model is told, and the record is split
   by it ("By how long it had stayed near the top when bought").
8. The AI model chooses among the first 12 (`choose`), each shown with recent headlines
   (`candidate_news`), and gives a reason naming the figures. **The code enforces every limit**: it
   can only pick from the shortlist; if it fails the top of the shortlist is bought and the log says
   "chosen by rank". A buy is recorded at the live price, and skipped if that is not within
   0.8–1.25 times the screener's price. `remember_buy` keeps the figures it was bought on.
9. If nothing was traded, one note says why (`key`): `pace` (waiting for the next step of the
   budget, with when), `full`, `cash`, `coins` (the coin share is used up), `shut`, `none`, `nodata`, `same`.
   The same note at the next check-in is counted on that line, not added again (`add_log`).
10. The portfolio is saved with a version check. If the owner changed it at the same moment,
    nothing is traded and it tries again next time.
11. `settle` again, then `review_resting`, `write_lessons`, `review_tuning`.

### Headlines

`fetch_news` (holdings) and `candidate_news` (the shortlist): Google News RSS search for coins,
Yahoo Finance RSS by symbol for shares (a share's company name comes from its quote).
`pick_headlines` keeps at most three, under 72 hours old, that **name the holding** (its code or
the first real word of its name) and drops price, forecast and converter pages (`NEWS_JUNK`; the
first real headline to reach the model, at 15:10 UTC on 10 Oct, was a "price forecast" page). Kept two hours
(`state.news`, `state.seen`). Headlines are untrusted text: both prompts say so, and the model's
answer can only pick from a list or say hold / sell. Small coins usually have none; then it is the
figures alone. Only the deployed function fetches (`AWS_LAMBDA_FUNCTION_NAME`); a test run never
calls out.

### Learning from its own results

- **The record.** Each finished trade goes into `history` (last 300): what it was bought on (rank,
  score, RSI, 7- and 30-day change, volume, who chose), result in percent and dollars, the S&P 500
  fund over the same time (`market`, `vs`), how long it was held, how it was sold (`exit`: `stop`,
  `take`, `trail`, `cut`, `time`, `signal`, `fade`, `ai`, `hand`), its best and worst while held, and,
  filled in later by `look_back`, **what it did after it was sold** (`after`: the further change
  once the same length of time had passed again).
- **Scorecard** (`scorecard`): overall and by screener, rank band, RSI band, who chose, and exit.
  Shown as "How it is doing" and given to the model at each decision (`memory_text`).
- **Resting a screener** (`review_resting`): when its last 12 trades (at least 8) average 1.5% or
  more behind the S&P 500 fund, it is rested 14 days, then tried again with a clean slate. **A coin
  screener is judged on its own results** (an average loss of 1.5% or more), not against the fund:
  the share market says nothing about a coin and is shut at weekends.
- **After costs.** No trading cost is taken from the fake money. `month_figures` also works out the
  last 30 days after a typical 0.1% on each buy and each sell (`COST_EACH_WAY`, `afterCosts`); the
  panel and the review emails show it beside the plain figure. It matters most for quick trading.
- **Notes** (`write_lessons`): after every 5 more finished trades the model writes up to four short
  notes on what the record shows.
- **Pausing the AI model's early sells** (`review_ai_sells`): when the last 8–12 holdings it sold
  early went on to rise 0.5% or more on average, its early sells are paused 14 days.
- **Trials of its own rules** (`review_tuning`, if `selfTune` is on). It may change only what is in
  `TUNABLE`, inside hard bounds: loss limit (−1.5 … −30), gain mark (2 … 80), share of a gain given
  back (0.2 … 0.8), how far down a ranking it buys (3 … 30), highest RSI it buys at (45 … none).
  Every 20 finished trades `propose` looks over up to 60 for the one change that would have helped
  most **in hindsight** (at least 0.2 points a trade): a nearer gain mark or loss limit from each
  trade's best and worst; a further one when holdings went on rising after such a sale; nearer or
  further down the ranking and a lower or higher RSI limit from how those groups of buys did.
  It does **not** adopt it. It runs a **trial beside the current rule over the same days**: for a
  selling rule every second buy follows the changed rule (`x`, `v` on the remembered buy,
  `own_rules`); for a buying rule it buys by the wider of the two and compares the groups. After
  10 finished trades each way it keeps the change only if that group's average beat the other by
  more than one standard error (`trial_figures`); otherwise the rule stays. A change dropped lately
  is not retried for three trials; a trial ends unchanged after 30 days, when the level changes,
  when the owner sets that rule himself, or when he stops it.
- **Emails** (`send_mail`, if `emails` is on): one at each review (no change / trial started /
  trial finished) with the record so far and suggestions about settings only the owner can change.
  `aws lambda invoke --function-name stockiq-ai-trader --payload '{"mail_test": true}' …` sends one
  test email to every account that has the autopilot on.

**Deliberately not built, although the owner asked for it:** letting it "modify anything on my
site". It changes five numbers of its own, for fake-money trades, and nothing else: no code, no
page, no setting of the owner's, no budget. An unattended program rewriting live code cannot check
its own work. Bigger changes come through a session like this one, informed by its emails.
**And say this plainly whenever results come up:** the backtests (sections 7b and 11) found no
reliable edge in the screener scores, tuning on a few dozen trades is mostly noise, and a goal
like "70% a month" is not something this or anything else delivers. The trial design exists so
that it at least does not fool itself.

### What the Lambda keeps per user, and what it sends the page

- The record: `settings`; `log` (last 80: `t, type` buy / sell / note, `symbol, usd, text`, and
  where relevant `kind, pct, detail[], key, n, first`); `history`; `state` with `startedAt`
  (when the budget's build-up began; reset when it is switched on or the budget or build-up
  changes), `lastRun`, `lastRunBy`, `open` (remembered buys), `exits`, `rest`, `restSince`,
  `lessons`, `tune` (`values`, `trial`, `past`, `mark`, `seq`), `watch`, `news`, `seen`, `stay`,
  `strong`, `ahead`, `aiSell`, `closedCount`, `realizedUsd`.
- `public()` (every action returns it): `settings, state, log, scorecard, lessons, resting, recent,
  minSample, practiceCash, rules` (in force, with `yours`, `level`, `changed`, `arm`), `tune`
  (`trial` with its figures, `past`, `nextReviewIn`, `batch`, `group`), `aiSellPausedUntil`,
  `coinShare, realizedUsd, month` (`last30`, `before30`), `now, nextCheck, holding, plans` (per
  holding: `sellBy, stop, take, arm, floor, move, room, tight, mode, trail, peak, trial, view, auto`) and `options` (screeners,
  check-in and holding-time choices, the level table). **The panel is drawn from these; change the
  two together.**
- Other actions: `sellall` (`sell_everything`: only the autopilot's holdings, recorded as sold by
  the owner) and `tune` (`tune_by_hand`: `op: 'restore', param` puts one rule back to the level's;
  `op: 'stop'` ends the running trial; nothing outside `TUNABLE` can be touched).

### How the panel script behaves (`practice-autopilot.js`)

- **Every change saves itself**: the switch at once, ticks and menus after 0.15 s, typing and the
  slider after 0.9 s, anything still waiting when the page is left. `accepted` stops a value the
  server tidied (20000.4 → 20000) being saved over and over. While something is being typed the
  panel is updated in place (`syncDraft`), not redrawn, so the cursor stays put.
- **It keeps itself up to date** (`refresh`, every minute while the page is visible, not while
  something is being typed or saved) and reloads the practice portfolio when the autopilot traded.
- The two description lines (`planText`, `paceText`) are built from what is selected. The sums in
  `buildUp()` are **a copy of the Lambda's rules** (`allowance`, the time rule, 3 buys a check-in,
  the coin share, the $25 smallest buy): change one, change the other, and run
  `autopilot_plan_check.py`.
- `levelRules` gives the rules to describe: the level's (`options.risk`), what it changed itself
  (`rules.level`), then the owner's own limits as typed. `readDraft` turns an empty build-up box or
  "Automatic" in a menu into the level's own value (`paceOf`) and lists the field in `auto`; while
  the slider moves, `syncDraft` updates the greyed value, the "Automatic: …" menu entries and the
  descriptions. `auto` is only sent if the Lambda sent it. Quick set-ups are `PRESETS` (they never
  touch the budget or the switch).
- "Buys and sells only" is a way of looking at the list, not a setting: it is remembered in the
  browser (`localStorage` key `stockiqAutopilotTradesOnly`) and nothing is sent to the Lambda. With
  it on, the latest check-in's own line is still shown above the trades when it is newer than the
  last trade, and after "Check in now" the message itself gives the reason if nothing was traded
  (the owner had the switch on, so the note that explained an empty check-in was hidden from him).
- Styles are one `<style id="ap-style">` block the script adds.

### Smaller facts worth knowing

- No screener is ticked for a new user, and it can be switched on with none: it then waits and
  says so. "Check in now" is greyed out, with the reason, while it is off or nothing is ticked.
- The holding time and the check-in gap are stored in days and hours as fractions (1 hour is
  0.041666… days); the panel reads both with `parseFloat` and sends them back exactly.
- A burst of saved changes leaves one "Autopilot on: …" line in the activity list, not one per
  keystroke (the last such line is replaced if it is under 15 minutes old).
- Stored screener results keep the top 150 rows in full and the rest as score, signal and rank
  only. A cold Russell 2000 run takes about 35 s, a four-screener check-in about 45 s, a crypto
  check-in about 16 s (the Lambda has 300 s).
- The sell rules measure a holding's change in US dollars, as the dashboard shows it; with no
  exchange rate a buy is skipped.
- The schedule scans the table for items with `enabled` true and runs each user who is due
  (`due_markets`); `next_check` works out the next slot for the status box.
- In the portfolio's search box, picking a suggestion shows the company name and latest price
  before anything is bought ("Checking exchanges...", "No matches found", like the home page).
- `panel_page.py` is the older browser page for the autopilot panel alone; `dashboard_page.py`
  (both sections together) is the one to use.

### How to work on it: the routine that held up

1. **Start from what is live.** Both repos clean (`git status -sb`), then check the live function is
   the mirror: download it, `cmp` with `lambda-sync/stockiq-ai-trader/lambda_function.py`, and note
   its `CodeSha256` and the `shasum -a 256` of the website files. Run one session at a time.
2. **Stage, do not edit in place**: copy the function and the website files to
   `check-tools/pending-<name>/lambda` and `/web`, and change the copies.
3. **Test the copies** (none of these touches anything real):
   ```bash
   cd /Users/dave/VSCODE/stockiq/check-tools
   python3 -W ignore ai_trader_test.py pending-<name>/lambda/lambda_function.py | grep -v '^PASS'   # 224 checks
   node autopilot_test.js pending-<name>/web/practice-autopilot.js | grep -v '^PASS'                 # 111 checks
   sed 's#https://5c7pt7qurshld4cwaqyopfxcei0cuurj.lambda-url.us-east-1.on.aws/#__PRACTICE_API_URL__#' \
     pending-<name>/web/practice-portfolio.js > /tmp/pp.js && node practice_test.js /tmp/pp.js | grep -v '^PASS'   # 64 checks
   python3 -W ignore autopilot_plan_check.py pending-<name>/lambda/lambda_function.py pending-<name>/web/practice-autopilot.js 150
   ```
   `ai_trader_test.py` sets the pace by hand at its top (it patches `DEFAULTS`), as a user who chose
   his own values; the real defaults, where the level sets the pace, are tested in their own part.
   It also sets `STAY_CHECKS` to 1 so that older tests buy a coin at once; the real wait has its own part.
   **Never run `practice_test.js` on the real `practice-portfolio.js`**: it holds the live storage
   address and would write to the live table (it happened once). Add checks for what you change.
4. **See it in a browser** without a login: `dashboard_page.py` (both sections, stand-in server,
   steps such as `type,sale,trial,preset,sellall,limits,trailstop,split,cards,pace,listswitch,open`) with headless
   Chrome; `--dump-dom` for what it printed, `--screenshot` for the look (section 12).
5. **Try the staged function on a copy of the real record**: read the owner's item from both tables
   (read-only), load it into stand-in storage under another name, run `run_user` / `public` with
   stand-in prices. This catches a record written by older code. Redact the email when printing.
6. **Deploy with `pending-<name>/deploy.sh`** (the owner's permission rule only allows that form:
   `bash /Users/dave/VSCODE/stockiq/check-tools/pending-<name>/deploy.sh`, absolute path, nothing
   else on the line). The script must: stop if the daily deploy is running; download the live
   function and stop unless its `CodeSha256` and its file equal what the change was built from;
   keep the old zip as `~/VSCODE/backup/<function>_before_<name>_<date>.zip`; update the code and
   copy it into `lambda-sync/`; check each website file's fingerprint before copying it in; upload
   with the cache headers of section 12; invalidate just those paths; support `DRY_RUN=true`; be
   safe to run twice. Copy the last one from git history (`git log --diff-filter=A --
   'check-tools/pending-*/deploy.sh'`). Run the dry run, then the real one, **away from :10 and :40
   past the hour**, when the schedule runs.
7. **Verify live**: `curl` the scripts with their new `?v=N` and `cmp` with the local files;
   download the function again and `cmp`; make the page's own read-only call (`action: get`) and
   read it; look at the function's log after the next scheduled run
   (`aws logs tail /aws/lambda/stockiq-ai-trader --since 10m`).
8. **Write it down and commit in steps**: update this section, commit and push each finished stage
   (the staging folder too, marked "work in progress, not live yet"), remove the folder after the
   deploy, commit the website files by name. The owner's sessions can stop mid-task.

Traps met on 10 Oct: a deploy script checking `pgrep -f deploy-to-s3.sh` finds its own text when it
is written and run in one command (run it on its own, or match the process as the last script
does); in zsh write `"${C}:path"` for `git show` (`$C:c…` is read as a modifier and left an empty
file once); a stand-in page that does not finish has a syntax error in its own script (check each
`<script>` block with `node --check`); in a browser step, take an element afresh after the panel
has redrawn (a kept reference is to the old one and nothing happens); test expectations with dates must allow for the local time
zone; SES and the news feeds are only used when running as the Lambda, so tests need stand-ins
(`mail=`, `headlines=`); two sessions building at once collided (the fingerprint check caught it).

### Where things stood late on 10 Oct 2026 (about 15:45 UTC)

- The owner was trying settings out all evening, so read his record rather than trust this line.
  Last seen: Adventurous, $50,000 built up over 1 day (set by hand), check-ins and holding time left
  to the level (every hour, 1 day), crypto screener ticked, all three switches on.
- Two finished trades, both up: WEMIX +0.6% (+$7.91; its score fell below zero, rank 1 → 149) and
  CFX +1.0% (+$12.79; **the first real sale by the stop that follows a rising holding**: it had been
  up 6.15% and was sold on the way down). It holds one Nikkei share (4307.T), bought with "Check in
  now" while Japan was closed; the fix above means it is looked after when Japan opens on Monday.
- **A limit that sale showed:** the stop stood at about +2.3% but the sale came at +1.0%, because the
  price is only seen at check-ins and it fell through between two of them. The autopilot does not
  watch prices in between. Shorter check-in gaps narrow this; nothing removes it.
- Seen for real: clean scheduled check-ins on every version, a headline reaching the model, both AI
  models answering the test question, the stop's sale with its explanation.
- Not yet seen for real: a sale made by the AI model's review, a "tighten" answer, the larger model
  being used, a coin being held back until it has stayed, a review of its own rules (after 20
  finished trades), a trial, the emails that go with them (a set-up email was sent; arrival not
  confirmed), and the logged-in dashboard itself (all checks used a stand-in server). **Worth
  checking first in a new session:** the function's log and the owner's record for errors and for
  the first of each of these.
- It is the owner's account only (`AI_TRADER_USERS`). Opening it to users is his decision and
  touches the same legal question as the signals (an AI choosing stocks, even with fake money,
  reads as picks); each user's check-in also runs screeners and AI calls, so cost limits first.
- Cost: a crypto check-in is a full crypto screener run (about 540 worker calls) unless a copy
  under 20 minutes old exists, so one user on 30-minute check-ins adds about 780,000 Lambda calls
  a month, plus up to two small AI calls per check-in and at most 8 larger ones a day: a few
  dollars a month in all at the very most.

### Ideas offered and not built

A chart of the account and of the autopilot's result over time; a weekly summary email even when
there is no review; a coin yardstick (Bitcoin) for coin trades in the breakdown; watching prices
between check-ins (a stop can only act at a check-in); trials that cover the owner's settings
(holding time, how often it checks in); selling part of a holding; sorting the tables; recording
which report a manual buy came from; dividends; per-user cost limits before opening it up.

## 9. Pitfalls learned the hard way

- **Template drift:** in Sep 2026 the live stock pages had a newer footer than the generator
  template, so running the generator would have reverted all 3,467 footers. Before running
  `generate-stock-pages.py` after template edits, test it on a copy of `stocks/` and diff.
- **`--size-only` S3 sync** skipped same-size edits (1,051 stale live pages). Now size + mtime.
- **Yahoo throttling:** `.info` lookups return false 404s ("Quote not found" for real tickers
  like BK) when too parallel. Use 2 threads. Failed lookups are cached for 1 day; fundamentals
  refresh weekly for stocks ≥ $5B, monthly otherwise; market cap is recomputed daily from
  cached shares × latest close × FX.
- **Currency units:** Yahoo prices for `.L` (GBp), `.JO` (ZAc), `.TA` (ILA) are in minor units
  (÷100), but Yahoo's `marketCap` is already in the major unit. ETFs have no market cap → noindex.
- `Sync_stock_to_news.py` re-adds ~3,000 articles to news.html. Harmless: the next deploy's
  `finalize_news_html.py` trims them. `check_news_sync.py` only compares within the time window
  news.html still covers, so do not "fix" its window logic back.
- `.kiro/steering/*` are real files now (the `.amazonq` mirror was removed Sep 2026).
  `stockiq/CLAUDE.md` (added 9 Oct 2026) only points Claude Code at these same files; keep the
  content here, not in `CLAUDE.md`. If a steering file is added or renamed, update its list.
- `website/.s3-excludes` is **not used** by any script; the deploy has its own include and
  exclude rules. Leftover local files that are never uploaded: `sitemap copy.xml`,
  `sitemap.xml.backup`, `sitemap_stocks.xml`, `blog.html.backup`, `Table.csv`,
  `company_names_dict.txt`, `robots-http.txt`, `*.py`.
- Running `generate-stock-pages.py` rewrites all 3,467 pages, so the next deploy uploads all
  of them (~110 MB). That's fine, just slower.
- **generate-stock-pages.py wipes news on pages without markers:** If stock pages were created before `<!-- NEWS_SECTION_START/END -->` markers existed, regenerating wipes their news silently. Fixed Oct 2026 — script now has a fallback to extract news from old-format pages, plus a pre-run count showing how many pages have news. If running after a long gap, check that count before and after. Always run `sync_news_to_stock_pages.py` after regenerating if news is lost.
- **Generator template reverted silently (found 9 Oct 2026):** the Oct 2 "Auto-update" commit (7e14c8f)
  rewrote `generate-stock-pages.py` back to the pre-Sep 25 template (no ANALYSIS markers, fake
  `NewsArticle` schema, no GA4, hardcoded `index, follow`). A regeneration on Oct 9 then rebuilt all
  3,467 pages with it and the deploy uploaded them, making every page indexable and removing every
  snapshot. Fixed by restoring the Sep 25 version (commit 2485162) plus the Oct 9 news-preservation
  fixes. **After ANY regeneration, run `update_stock_analysis.py`** (it sets index/noindex, snapshots and
  `indexable_stocks.txt`; with no ANALYSIS markers it silently writes nothing). **Before every deploy,
  sanity check:** `grep -l 'content="index, follow"' ../website/stocks/*.html | wc -l` should be ~950, not 3,467,
  and `wc -l indexable_stocks.txt` should be ~950. Also review `git diff --stat` on scripts after the
  "Auto-update" commits; they bundle everything and hide reverts.
- **The same Oct 2 commit also reverted `deploy-to-s3.sh`** (found 9 Oct 2026): `DRY_RUN` was gone
  (a "dry run" did a real deploy), stock pages synced with `--size-only` again, and only `stockiq/`
  was pushed to GitHub. Restored from commit 2485162 plus the `$PYTHON` variable. **Before trusting
  `DRY_RUN=true`, check the script still supports it:** `grep -c DRY_RUN deploy-to-s3.sh` must be > 0,
  and the output must contain `(dryrun)` lines and no `upload:` lines. That commit touched 24 scripts
  (`git diff --stat 2485162 7e14c8f`). All were compared with their Sep 25 versions on 9 Oct: the
  rest only had path changes, except `check_news_sync.py` (window logic lost; restored) and
  `update_sitemap.py` / `generate_sitemap.py` (rewritten in Oct on purpose; verified working).
- **News script wiped news on the current template (fixed 9 Oct 2026):** `update_stock_news.py`
  (`update_stock_page`) removed the page's NEWS section and then looked for a "features grid" to insert
  before. That grid only exists in the pre-Sep 25 template, so on current pages a new article **deleted the
  news section and its markers** and still returned success. This is why pages kept losing their markers and
  why "news in the sidebar but not on the stock page" kept happening. It now replaces the content between the
  NEWS markers in place, falls back to inserting before `RELATED_SECTION_START`, and returns False (page
  untouched) if neither exists. `sync_news_to_stock_pages.py` had the same fallback and is fixed too. The
  "History" heading is now only written when there is an older article under it (448 pages had an empty one;
  cleaned up). **Any script that writes into stock pages must anchor on the section markers, never on other
  template HTML.**
- If stock pages show old data dates, check `update_stock_analysis.py` is still in `deploy-to-s3.sh`
  (it went missing once) and look for a large "No price data" count in `~/stockiq-daily.log`.
- **Yahoo rate-limits this machine** (HTTP 429) after a few hundred chart requests. On 10 Oct 2026
  manual symbol checks caused the daily run's snapshot step to get no prices for 2,041 stocks. It
  kept yesterday's snapshots and de-indexed nothing; a re-run an hour later was clean.
- **Lambda code is not in git** (`lambda-sync/` is a gitignored mirror). The only history of a
  Lambda is whatever zip you keep before changing it.
- A worker address in the crypto orchestrator had a one-character typo for months and returned
  403; its coins were silently missing. Failed worker calls are easy to miss: count results.
- A stray `test-news-layout.html` was publicly live on S3 (deleted 25 Sep 2026). Check S3 for files with no local
  copy occasionally (`aws s3api list-objects-v2 --delimiter /`).

## 10. Working rules for AI assistants

- The owner (Dave) built this with AI help, works in **Kiro**, and is not going to read code.
  Explain in plain terms what will change and what you found. Lead with the result.
- **Verify, don't assume, and don't trust these docs blindly.** On 9 Oct 2026 the docs said
  `DRY_RUN=true` worked; the script had lost it and a "dry run" deployed for real. Before relying
  on a script feature or a claim here, check the code. When something is fixed, say how it was
  checked; when something could not be tested (logged-in screens, a real phone), say that too.
- **Test with real data, end to end.** Spot checks missed real bugs repeatedly on 9–10 Oct
  (missing label codes, stocks never sent to a worker, a column that was always 0, a worker
  address with a typo). When asked to "check", run the whole thing (section 8b) and read the
  output. List every code, field or symbol a component can produce before mapping it.
- **Before editing a Lambda:** download the live code and diff it with `lambda-sync/` (they must
  match). Lambda code is not in git, so keep the previous zip in `~/VSCODE/backup/` with a clear
  name as the rollback. After deploying, smoke-test the live function. If the daily run's Lambda
  sync is about to run, deploy straight after editing `lambda-sync/` so it does not overwrite you.
- **The daily deploy starts at 11:00** (Mon–Sat) and publishes and commits whatever is in
  `website/`. Near that time, stage edits in a scratch folder and copy them in only when
  verified. If the job's own files (news.html, news.js, sitemap.xml) are dirty, commit only your
  files by name, never `git add -A`.
- **Production deploys go through a packaged script.** Since 10 Oct 2026 the session's safety
  check refuses a direct Lambda or S3 deploy; the owner added one permission rule,
  `Bash(bash /Users/dave/VSCODE/stockiq/check-tools/pending-*/deploy.sh)`. So: stage the change in
  `check-tools/pending-<name>/` with a `deploy.sh`, run its dry run, then run it with exactly that
  command form. The full routine is in section 8c ("How to work on it"). If the rule is ever
  missing, only the owner can add it; say so plainly instead of trying another route.
- **Commit and push in steps** (owner, 10 Oct: "so long as you commit to github in steps and can
  track changes"). His sessions can stop mid-task when usage runs out: push each finished stage,
  marked "work in progress, not live yet" until it is deployed, and say what is live and what is
  only committed.
- Ask the owner before an S3 upload or GitHub push and show the `DRY_RUN=true` list. (On 9–10
  Oct the owner approved deploys as each fix was ready; a few hand-edited files can go up with
  `aws s3 cp` plus a CloudFront invalidation of just those paths, which avoids a full pipeline run.)
- No extra backups before changes: the daily backups in `~/VSCODE/backup/` (30 days, both
  folders incl. `stocks/`) plus GitHub are enough. The one exception is the Lambda rollback zip.
- Change generators and templates, not generated pages (section 4). Any script that writes into
  stock pages must anchor on the section markers, never on other template HTML.
- **Describe, don't advise** (owner's instruction; StockIQ holds no financial services licence).
  On pages, in emails, in product output and in the AI chat: no "you should buy/sell", "picks",
  "winning stocks", "recommendations", price targets or predictions presented as StockIQ's view.
  Say "scores", "signals", "screener rankings", "what the data shows". The AI chat prompt
  (`stockiq-ai-chat`) must keep its rule never to give buy/sell/hold calls, price targets or
  picks. Keep the footer disclaimer and the no-licence statement (terms.html, about.html).
  Educational text about how technical analysis works is fine. Details: section 8b.
- Verify claims against code or data before putting them on public pages. Don't promise what
  doesn't exist (the giveaway and "daily picks at 6 AM" were removed for that reason).
- Commit with a message that says what changed and why. The "Auto-update" commits bundle
  everything; one of them hid a revert of 24 scripts (section 9).
- Don't hit Yahoo in bulk from this machine (section 8b). Use `stockiq-price-proxy` or go slowly.

## 11. Open items and optimisation ideas

Needs the owner's decision or more work (nothing here is fixed):
- **Legal.** The business is "StockIQ", online-only, no physical address, **no financial services
  licence**; billing is in USD ($4.99 / $14.99 / $49.99 per month, confirmed on the live Stripe
  prices). The terms, About page, pricing section and FAQ say all of this, and the product
  wording was neutralised (section 8b). Whether issuing automated signals to paying users
  without a licence is acceptable under Australian law is a question for a lawyer; the owner
  knows and has not had it reviewed. The owner trades as an individual (no company structure).
- **Screener quality** (section 8b): no real fundamentals in the workers; ASX 24-hour change is 0
  after the ASX close; a few valid symbols return nothing (WBD, PSKY); Russell 1000/2000 lists
  not refreshed; ASX 300 is approximate. All but the lists need worker redeploys.
- **Crypto track record (review from early Nov 2026).** The entry log (section 8b "Crypto") started
  10 Oct 2026. Once it holds a few hundred entries, compare each coin's price 24 hours and 7 days
  after entering the top 10 with the average coin over the same days. Leftovers that can be
  deleted when the owner agrees: Lambda `stockiq-coinspot-predictions-updater` (no longer
  triggered) and the old-format rows in both crypto tables.
- **UK FTSE screener shows prices one trading day old.** Yahoo's latest daily close is empty for
  London stocks (seen 10 Oct: Friday's bar `null`), and the `stockiq-europe-4-1` workers fall back
  to the day before (IMB.L 2,614 in the report, 2,662 actual). The report also prints pence with a
  £ sign ("£2614.00" is 2,614p). Needs the 10 workers redeployed (use `meta.regularMarketPrice`).
- **Fake-money test of the screeners (owner's idea, 10 Oct 2026; first results in).** Tool:
  `stockiq/check-tools/paper-test/` (`python3 fetch.py && python3 backtest.py dow30|sp100 [start date]`).
  It replays the worker's own scoring code over daily prices (the screeners use nothing else), takes
  each day's top 10 and compares what they did next with the whole list and with SPY; it also runs
  a $10,000 paper account re-invested in the top 10 weekly. The replay's top 10 for 9 Oct matched
  the live Dow 30 and S&P 100 reports exactly. Results, 3 Jan 2023 – 9 Oct 2026 (946 trading days):
  - **Dow 30: no edge.** Top 10 +16.8% a year, whole list +18.4%, bottom 10 +19.3%, SPY +21.0%.
    No reliable difference at 1 day, 1 week, 1 month or 3 months. With 0.1% cost per trade: +10.3%.
  - **S&P 100: ahead, but not reliably.** Top 10 +43% a year (no costs; +31% with 0.1% costs)
    against +25% for the whole list; bottom 10 +16%. The gap is inside the margin of error at 1 week
    and longer, most of it came in 2026, and it disappears (+0.02% a week) when seven chip / AI
    stocks are left out (SNDK, MU, AMD, ANET, NVDA, PLTR, DELL). The score is a momentum score, and
    momentum paid in those names in this period. The list is today's membership, which flatters it.
  - The top 10 changes a lot: the account trades 57–84 times its own value a year.
  - **Do not publish these numbers as a track record.** The fair test is forward: the lists were
    frozen on 10 Oct 2026 (`frozen_lists.txt`); re-run with a start date of 2026-10-12 or later
    (suggested: early Dec 2026 and early Jan 2027). No scheduled job is needed for this, because the
    replay gives exactly what a daily automatic paper-trader would have recorded.
  - Not covered: the larger US lists (one price download per stock; Yahoo blocks this machine after
    a few hundred), ASX / FTSE / Nikkei (different worker code; same method would work), crypto
    (the entry log in section 8b does this job from 10 Oct). The practice portfolio and autopilot
    built the same day (section 8c) are the live counterpart: the autopilot's finished trades are a
    forward test of buying from the top of the rankings, with its own record on the dashboard.
- **Page score vs app score.** Same model, different inputs (checked on AAPL, 71 vs 47): the page
  uses the previous close and Yahoo fundamentals, the app uses the live price and Finnhub. A
  price 0.1% under the 20-day average swung the trend factor by 18 points; Finnhub had no revenue
  growth (−8); and during market hours the app compares part-day volume with a full-day average
  ("Low Volume −3"). Worth fixing: the part-day volume penalty, and a Yahoo fallback when Finnhub
  lacks a figure. Both are scoring changes: change `stock_metrics.py` too.
- **Dashboard plan cards** list features that are not verified to differ by plan ("Advanced
  screening & alerts", "Portfolio tracking", "White-label options", "Dedicated support"), while
  the FAQ says all plans get the same features. Old accounts carry legacy limits (a cancelled
  Starter at 50/day, the owner's Pro at 200/day); new purchases get 15 / 50 / unlimited. One
  `@dewit.com.au` test account has a limit of 20, which is why a "19/20 today" badge can appear.
- **Usage badge** (`#trial-status-display`, created in `auth.js`, fixed top-right) overlaps the
  index cards under the nav. Bottom-left is taken by the anonymous "Start 3-Day Free Trial"
  sticky button, so it needs a placement decision.
- **Mobile:** the owner reports the page zooms when tapping the AI chat input. The input is
  already 16px; cause not found. Need the phone model and browser to chase it. One candidate is
  the fixed 500px window height when the keyboard opens.
- **AI chat rate limit** is keyed on a browser-generated anonymous ID, so clearing site data
  resets it; the Lambda also looks up paid status from the `userId` the browser sends.
- **Email signup:** the endpoint is public (a bot could flood signups and notification emails),
  the Lambda has no CloudWatch log group, and nothing is sent to subscribers yet.
- Home page: the comparison table still benchmarks against Bloomberg ($24,000/yr) and
  Morningstar. `analysis.html` shows 12 "Coming Soon" screener buttons.
- Guides are ~800 words of definitions with no worked examples.
- `uniqueSymbolsCount` constants in `saveAnalysisToHistory` (`analysis-functions.js`) still use
  the old list sizes (bookkeeping only).
- News `data-timestamp` values on stock pages get bumped past the article date (e.g. 0006.HK
  showed 16 Sep for a 10 Sep article). This inflates sitemap lastmod; cause not found (look in
  `update_stock_news.py`). Also seen 10 Oct: a page with one article sometimes ends with one
  article after a new one arrives (the old one is not carried into History); counts never drop.
- `website/stocks-backup-before-restore/` (118 MB, created 9 Oct, gitignored, not uploaded) can
  be deleted. Three rollback zips `~/VSCODE/backup/*_before_neutral_wording_20261009.zip` hold the
  pre-rewording code of the report Lambda, the coordinator and the crypto orchestrator.

Ideas:
- Review Search Console around 6 Nov 2026 (six weeks after 25 Sep): impressions and clicks on
  the ~957 indexed pages; consider the $2B threshold if they perform.
- Backlinks remain the biggest lever (see `backlinks-progress.md`).
- Link to indexed stock pages from index.html, the guides and analysis results (internal links).
- Home page market widgets are filled in by JavaScript; crawlers see "Loading...".
- news.html `<title>` still says "Free Stock Analysis Guide & Investment Blog". Rename it.
- "People also watch" Fix 1 in `future-work.md`. India (BSE Sensex) is the next screener
  (`add-new-screener.md`). Price alerts are not built (`roadmap-to-9.md`).
- `fix_amazonq_chat.sh` is obsolete (Amazon Q is not used).
- `update_news.py` `MAX_BLOG_ARTICLES` stays commented out on purpose. Trimming is done by
  `finalize_news_html.py` with separate stock/general limits.

## 12. Quick checks

```bash
cd /Users/dave/VSCODE/stockiq
python3 check_news_sync.py                                   # news sync + coverage
python3 update_stock_analysis.py AAPL 7203.T --dry-run       # snapshot logic without writing
grep -c DRY_RUN deploy-to-s3.sh                              # must be > 0 before trusting a dry run
DRY_RUN=true ./deploy-to-s3.sh                               # prints (dryrun) lines; no "upload:" without it
curl -s https://stockiq.tech/sitemap.xml | grep -c '<loc>\|:loc>'   # live sitemap size (~975)
```

**Before every deploy** (after any regeneration these catch a broken template):
```bash
grep -l 'content="index, follow"' ../website/stocks/*.html | wc -l   # ~950-960, never 3,467
wc -l indexable_stocks.txt                                           # same number, never ~0
grep -l 'ANALYSIS_SECTION_START' ../website/stocks/*.html | wc -l    # 3,467
grep -l 'Read full article' ../website/stocks/*.html | wc -l         # ~3,150; should not fall
```

**After the daily run** (`~/stockiq-daily.log`, cleared each run):
```bash
grep -a -E "Pages written|Indexable|No price data|Sync complete|pushed|could not|failed|All done" ~/stockiq-daily.log
```
A large "No price data" number means Yahoo rate-limited this machine: nothing is de-indexed
(yesterday's snapshot is kept); re-run `python3 update_stock_analysis.py` later, then
`./deploy-to-s3.sh`.

**Upload a few hand-edited files without a full deploy:**
```bash
cd /Users/dave/VSCODE/website
aws s3 cp faq.html s3://stockiq-final-websitebucket-vqekic7enf9h/faq.html \
  --cache-control "public, max-age=3600" --content-type "text/html; charset=utf-8" --profile default --region us-east-1
aws cloudfront create-invalidation --distribution-id EHXV50CPHY07R --paths "/faq.html" --profile default --region us-east-1
```
(`*.js`: `--cache-control "public, max-age=86400"`, no content-type.)

**Test a template change safely** (before running `generate-stock-pages.py` for real):
```bash
T=$(mktemp -d); cp -R ../website/stocks $T/stocks; cp -R $T/stocks $T/orig
sed "s#/Users/dave/VSCODE/website/stocks\"#$T/stocks\"#" generate-stock-pages.py > $T/gen.py
python3 $T/gen.py && diff -r $T/orig $T/stocks | head -100    # check only intended lines change
```
Also check that every page's NEWS and RELATED sections are byte-identical before and after,
then run `update_stock_analysis.py` (it sets index/noindex and the snapshots).

**Screenshot a page** (headless Chrome; use the live URL, local files hang):
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
  --window-size=1300,2200 --virtual-time-budget=8000 --screenshot=/tmp/page.png https://stockiq.tech/stocks/AAPL.html
```
Run one at a time with a time limit; a tall capture can be sliced with `sips -c H W --cropOffset Y 1`.
Narrow window sizes look cut off in headless mode even for unchanged pages; that's a headless
quirk, not a layout bug. The home page shows its right-hand news panel only from 1401px wide.

**Check a logged-in panel in a real browser** (the dashboard cannot be opened without a login, but
a panel script can be run on its own): `python3 check-tools/panel_page.py <script.js> <out.html>
<light|dark> "<steps>"` writes a page holding the real script, the site's stylesheet and a stand-in
server, then performs the steps (clicks, typing) and prints what happened into the page. Open it with
headless Chrome using `--dump-dom` for the printed results and `--screenshot` for the look (a local
file with no site scripts does not hang). Nothing live is called. Written for the autopilot panel;
copy and adapt the stand-in answers for another panel.
`python3 check-tools/dashboard_page.py <practice-portfolio.js> <practice-autopilot.js> <out.html> <light|dark> "<steps>"`
does the same with **both** practice sections together (two holdings bought by hand, one by the
autopilot; steps `type`, `sale`, `trial`, `off`, `open`, `preset`, `sellall`, `limits`, `split`): use it to see how they work with each other,
for example that a sale made in the background appears without losing what is being typed.
A deploy script that checks `pgrep -f deploy-to-s3.sh` must be run as its own command: written and run
in one command, the check finds its own text and stops.

**Run every analysis button end to end:** section 8b, last part.
**Work on the dashboard's practice portfolio or autopilot:** section 8c, "How to work on it" (tests,
browser page, copy-of-the-live-record check, deploy script, verification).

## 13. Change log

- **25 Sep 2026** (Claude Code session, full review):
  - Merged cloud branch `claude/new-session-cuwqcx`: `about.html`, homepage testimonials
    replaced, About link in footers, FAQ accuracy claims removed.
  - About page scoring section corrected; GA4 added to content pages and all stock pages.
  - Stock pages: new template (WebPage schema, filler cards removed, footer fixed), daily data
    snapshot on 962 large caps (`update_stock_analysis.py` + `stock_metrics.py`), others noindex.
  - Sitemap 3,486 → 979 URLs; news.html trimmed and noindex (`finalize_news_html.py`).
  - `deploy-to-s3.sh`: stock pages uploaded by size+time (1,051 were stale), root html/css/js by
    MD5, root JS now uploaded, `DRY_RUN` mode, both repos pushed.
  - `.amazonq` mirror removed (Kiro only); steering docs reviewed; `verification-summary.md` removed.

- **Oct 2026** (Kiro session, new MacBook setup + Japan screener + SEO fixes):
  - Migrated all paths from `/Users/ddewit/` → `/Users/dave/` across 31 files.
  - Python deps installed: requests, openai, yfinance, pytz, bs4, dateutil.
  - Scheduled task converted from AppleScript to bash (`~/stockiq-daily.sh`), window extended to 11am–10pm.
  - Dropbox one-way sync configured (`~/dropbox-sync.sh`, daily launchd job).
  - Git identity updated to `dave@dewit.com.au`.
  - `deploy-to-s3.sh`: fixed `$PYTHON` path variable; added `update_stock_analysis.py` (was missing — stock data stale since Sep 25); added root JS sync loop; added `finalize_news_html.py` (was also missing).
  - `sync-all-lambdas.sh`: added `--profile default --region us-east-1`.
  - `update_sitemap.py`: fully rewritten to rebuild stock URLs from `indexable_stocks.txt` (old version never removed URLs — sitemap stuck at 3,485 instead of ~970).
  - `generate_sitemap.py`: fixed to use `indexable_stocks.txt` instead of all HTML files.
  - `generate-stock-pages.py`: fixed to preserve news/analysis from pages without NEWS_SECTION_START markers; added pre/post news count safety check.
  - `update_stock_news.py`: article fetch window extended 2 → 4 days (laptop sometimes off for days).
  - Ran `update_stock_analysis.py` manually — refreshed 953 large-cap pages (data was 11 days stale). Sitemap rebuilt to 970 URLs, resubmitted to Google Search Console.
  - Restored news from backup after generate-stock-pages.py wipe; ran `sync_news_to_stock_pages.py` to resync.
  - Cleaned up: sitemap copy.xml, blog.html.backup, stocks copy.txt, generate-stock-pages.py.backup, sitemap.xml.backup, github-repo/, stockiq/sitemap.xml, __pycache__.
  - **Japan Nikkei 225 screener** built end-to-end (21 workers, 210 stocks, full dashboard integration).
  - Added `add-new-screener.md` steering doc. Trimmed roadmap, backlinks, script-reference docs.

- **9–10 Oct 2026** (Claude Code session: recovery, full end-to-end check, lists and crypto rebuilt):
  - **Recovery.** The Oct 2 "Auto-update" commit had silently reverted `generate-stock-pages.py`,
    `deploy-to-s3.sh` and `check_news_sync.py` to pre-Sep 25 versions; a regeneration on Oct 9 then
    made all 3,467 pages indexable with no snapshot. Scripts restored from 2485162, pages
    regenerated, 957 indexable. `.gitignore` in both repos restored.
  - **News script:** `update_stock_news.py` was deleting the news section on current-template
    pages; fixed (anchors on markers). 448 empty "History" headings removed.
  - **Site text:** unsupported accuracy claims, "real-time" / "zero delay", conflicting counts and
    the giveaway removed; footer disclaimer on public pages; plan names and limits match the
    payment Lambda; pricing section added to the home page; signup Terms link fixed; terms and
    About state USD billing, online-only, no licence.
  - **Email signup:** reworded; `stockiq-email-capture` emails `noreply@stockiq.tech` per signup.
  - **Describe, don't advise:** AI chat prompt and suggested questions, the single-stock report,
    all screener / signal / crypto formatters, the coordinator, CSV headers, the dashboard popup
    and the FAQ no longer use BUY/SELL, targets, stop loss, picks or recommendations.
  - **Full end-to-end test of all 21 analysis buttons** through the page code and of all 15
    screeners through the coordinator. Fixed: missing `MODERATE_*` labels, `BRK.B` format, stocks
    never sent to a worker, duplicate rows, empty-batch fallback, CSV columns that were always 0,
    fake-fundamentals columns removed, tracker regex (single-letter tickers, long names), crypto
    legend, AI chat button position, a typo in crypto worker 26's address.
  - **Lists rebuilt** from current index members (all but Russell 1000/2000), every symbol
    verified; batching sizes itself to the list; labels and headers show real sizes.
  - **Crypto rebuilt:** new 540-coin list verified against CoinGecko, driven from the
    orchestrator through the workers' single-coin mode; orchestrator memory 512 → 2,048 MB.
  - **Access bug:** 14 handlers re-checked access after counting the use, eating the last free
    use of the day (anonymous single coin; trial users on 13 screeners). Removed.
  - Orphan pages `market-data-sidebar.html` / `market-data-widget.html` deleted;
    `lambda-url-mapping.json` regenerated (982 functions, 967 with URLs).
  - **Crypto top-10 history rebuilt** (section 8b "Crypto"): the 15-minute updater was tracking the old
    coin list; the schedule now runs the orchestrator itself every 30 minutes, risk labels and stars
    removed, results slider reworded, dashboard tracker uses the right ticker, permanent entry log
    added. Deployed by the owner with a packaged script, because the Claude Code session was not
    permitted to run production deploys (Lambda, S3); read-only AWS calls and git pushes were fine.
  - **Dashboard Top 10 Performance rebuilt** (section 8b): faults above fixed, over-time table against
    the index added. **Fake-money test** of the Dow 30 and S&P 100 screeners run (section 11).
  - **Practice portfolio** added to the dashboard (section 8c), with a new table and Lambda.
  - **AI autopilot upgraded** (section 8c): all 15 screeners with per-market hours and currencies,
    quick trading (check-ins from every 30 minutes, holds from 30 minutes),
    stored screener results, and a record of its own closed trades that it learns from (scorecard,
    resting a lagging screener, AI-written notes fed back into its choices). Dollars-or-quantity
    fields on the practice buy row. Two sessions built an autopilot at the same moment on 10 Oct;
    the deploy script's fingerprint check caught it and the second build was dropped. **Run one
    session on the site at a time.**
  - **Your own loss limit and gain mark; whose result is whose** (section 8c): two optional fields
    on the autopilot panel, and a line on the practice portfolio that separates the owner's own buys
    from the autopilot's. Rollback zip: `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_limits_20261010.zip`.
    In zsh, write `"${C}:path"` for `git show`: `$C:c…` is read as a modifier and fails (it left an
    empty deploy script in one work-in-progress commit, corrected in the next).
  - **Autopilot managed from the dashboard** (section 8c): quick set-ups, switches for what it may do
    by itself, "Sell everything it holds", undoing its own rule changes; headlines when choosing what
    to buy; coins use the whole budget when only coin screeners are ticked; a sale on a score below
    zero now says so (it said "signal turned negative"). Rollback zips:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_controls_20261010.zip` and `…_wording_…`.
  - **The AI model reviews each holding at every check-in** (section 8c): fresh screener figures and
    real headlines fetched by the function; it may sell earlier than the rules, and its early sells are
    paused if they prove too early. Rollback zip: `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_review_20261010.zip`.
  - **Autopilot made clearer and able to review itself** (section 8c): whose holding is whose and when
    the autopilot will sell; S&P columns removed from the practice portfolio; details under each buy
    and sale; the panel refreshes itself; two more selling rules; bounded trials of its own rules with
    an email at each step. Rollback zip: `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_smart_20261010.zip`.
  - **Autopilot description follows every setting** (section 8c): the two
    lines under the fields are built from the check-in, holding time, level, budget and ticked
    screeners. Checking them against the Lambda found a rounding fault (the last holding of an
    uneven budget was never bought); fixed in `stockiq-ai-trader`. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_desc_20261010.zip`.
  - **AI autopilot** for the practice portfolio (section 8c): new Lambda, table and hourly schedule.
  - **Deploy permission:** from the afternoon of 10 Oct the session's safety check refused production
    deploys and refused to let Claude change its own settings. The owner added the allow rule
    `Bash(bash /Users/dave/VSCODE/stockiq/check-tools/pending-*/deploy.sh)` himself; with it, a deploy
    packaged as `check-tools/pending-<name>/deploy.sh` runs without a hand-off. Keep packaging deploys
    that way (live-code check, rollback copy, `DRY_RUN=true`), run the dry run, then run it.
  - Autopilot activity list: "Buys and sells only" became a switch remembered in the browser.
  - **"Check in now" acts, and says why when it cannot** (section 8c): a check-in asked for by hand
    releases the next part of the budget early; the reason for an empty check-in is in the message
    and stays visible with "Buys and sells only" on. When trying a staged function on a copy of the
    real record, give the stand-in prices the real buying price of what is held: a made-up price
    makes a holding look sold at a huge loss. Rollback zip: `…_before_autopilot_now_20261010.zip`.
  - **The kind of trailing stop is a choice** (section 8c): "Your own limits" gains a "Trailing stop"
    menu: protects a gain (as before), a full trailing stop loss from the moment of buying, or off.
    Rollback zip: `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_trail_20261010.zip`.
  - **Found in the live data and fixed** (section 8c): a holding whose screener had been un-ticked
    was left unattended (`its_markets`); a coin is now bought only once it has stayed near the top
    for two check-ins; coin screeners are rested on their own results; results are also shown after
    a typical trading cost. Rollback zips: `…_before_autopilot_orphan_…` and `…_steady_…`.
  - **The stop that follows a rising holding is set from the holding's own movement** (section 8c):
    its daily range scaled to the check-in gap, with room that widens or tightens with its screener
    figures, the time left and the AI review's new "tighten" answer. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_stop_20261010.zip`.
  - **The pace follows the risk level** (section 8c): the three pace settings can be left to the
    level ("automatic") or set by hand. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_pace_20261010.zip`.
  - **Gain protection reworked; clearer account figures** (section 8c): a gain is protected from a
    rise that follows the holding time, and a big gain gives back less; the AI review sees each
    holding's path and a larger model is used, capped, when a gain is at stake; the practice
    portfolio no longer flashes a figure before prices arrive, says what is from sales and what is
    on holdings still held, and says when the stock market has been closed. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_gains_20261010.zip`.
  - Docs consolidated: section 8b added, section 11 reduced to open items, `CLAUDE.md` (added
    9 Oct) loads these steering files into Claude Code sessions. On the evening of 10 Oct the
    practice portfolio and autopilot notes, which had grown in layers through the day, were rewritten
    from the deployed code as **section 8c**, with the working routine, so a new session can resume
    dashboard work from the notes alone.
