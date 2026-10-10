# StockIQ Site Overview (read this first)

How stockiq.tech works end to end, what is generated vs hand-edited, the current SEO setup,
known pitfalls, and open ideas. Last full review: 10 Oct 2026 (section 8b holds what the
9–10 Oct end-to-end test of every screener, signal and crypto path established).

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
- Not done yet: the same test for the other screeners and crypto, a test of each of the 12 factors
  separately (to find which ones help and re-weight the score), and the live daily paper portfolio.
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
- **Practice portfolio** (dashboard, added 10 Oct 2026; the owner's "fake money" idea). A section above
  Report History: type a stock code or name, pick an amount of practice US dollars (default $1,000,
  from a $100,000 start) and "Practice buy"; each buy becomes a line that is then monitored: price
  then and now, value, change, and what an S&P 500 fund (SPY) did since the same day. The buy row has
  no pre-filled amount: "Enter $" and "or quantity" sit side by side, and whichever is typed, the
  other is worked out from the latest price once the code is known (`fillOther`, `priceFor`); a buy
  by quantity buys exactly that many. "Sell" closes
  the line at the latest price; the "Reset fake money to $100,000" button clears everything. Under the
  holdings a line says how many are ahead of the S&P 500 since they were bought; a holding is only
  counted once it or the market has moved 0.05% (`versusMarket`), so a buy made a moment ago is not
  called "0 of 1 ahead", and ties are reported as "about level". The "Sold" list
  ends with a summary (put in, got back, result, how many did better than the S&P 500 over the same
  days), a "Clear sold list" button and an × on each line; clearing only tidies the list, because
  what a sale brought in is already in the practice cash (added 10 Oct 2026, script `?v=3`). The
  search box works like the home page's (same `stockiq-validate-symbol` lookup, "Checking
  exchanges...", "No matches found"); picking a suggestion shows the company name and latest price
  before anything is bought. When the script changes, raise `practice-portfolio.js?v=N` in
  `dashboard.html`: the script is cached for a day. The Top 10 Performance popup has a
  "＋ Practice buy" button on every counted line (uses the report's price-source ticker, so a coin
  with a numbered ticker is bought correctly).
  - Code: `website/practice-portfolio.js` (sums and page; loaded by `dashboard.html`, container
    `#practice-portfolio`). Storage: Lambda `stockiq-paper-portfolio` (public Function URL, written
    into the JS) and DynamoDB table `stockiq-paper-portfolios` (key `userId`, pay per request). The
    browser does the sums and sends the whole portfolio; the Lambda checks shape and size and uses a
    `version` number so two tabs cannot overwrite each other. As everywhere on this site, the
    `userId` is whatever the browser sends.
  - Prices: `stockiq-price-proxy`; names: `stockiq-validate-symbol`. Other currencies are converted
    to US dollars with Yahoo's `XXXUSD=X` rates (London prices are pence, divided by 100), so a
    holding's change includes the currency move. A holding with no price is shown at cost.
  - Wording: "practice", "fake money, no real trades"; nothing suggests what to buy. Keep it so.
  - Test without logging in: `node check-tools/practice_test.js <path to practice-portfolio.js with the
    __PRACTICE_API_URL__ placeholder>` (real prices, in-memory storage). **Do not run it against the
    deployed file**: that one holds the real address and would write to the live table.
  - **Dashboard only (owner's decision, 10 Oct 2026):** buying, selling and viewing progress all stay
    on the dashboard. Do not add buy buttons to the generated stock pages or the single-stock report.
  - Not built (ideas offered to the owner, 10 Oct): a chart of the account value over time; the score
    or report a buy came from recorded automatically and compared later; selling part of a holding;
    sorting the table; dividends.
- **AI autopilot** for the practice portfolio (added 10 Oct 2026, the owner's idea; **fake money only,
  owner's account only for now**). Under the practice portfolio on the dashboard: switch it on, set a
  risk level (slider 1–5, Cautious to Adventurous), a budget and the number of days to spread it over,
  how often it checks in (every 30 minutes, 1, 3, 6, 12 or 24 hours), the longest it keeps a holding
  (30 minutes to 60 days: after that it sells whatever the price), and which
  screeners it buys from: **all 15** since the 10 Oct upgrade (the eight US lists, ASX 50/100/200/300,
  FTSE 100, Nikkei 225, crypto), shown in groups by market. Add a screener by adding a line to
  `SCREENERS` in the Lambda (name, coordinator option and subOption, kind, market, group). "Check in now" runs one
  check-in on demand (10-minute gap). "What it has done" lists every buy, sell and skipped check-in
  with the reason. Its holdings carry a 🤖 in the portfolio table and can be sold by hand.
  - **How a check-in works** (Lambda `stockiq-ai-trader`): (1) fetch the chosen screeners' latest
    results from `stockiq-screener-coordinator` (called with no `userId`, so nothing is saved to
    anyone's history); (2) sell its own holdings by fixed rules: down past the level's limit, up to
    the level's mark, held the longest allowed time, or the screener signal turned negative; (3) work
    out what may be spent: the budget is released in equal steps over the chosen days, money from
    sales is re-used, never more than the budget invested, never more than the practice cash;
    (4) shortlist the top of each screener, filtered by the risk level (`RISK` table in the code: how
    many holdings, how far down the ranking, RSI and 30-day-move limits, share allowed in coins);
    (5) send the shortlist to the AI model (gpt-4o-mini, JSON reply) to choose and give a reason
    naming the figures; (6) record the buys at the live price. **The code enforces every limit**: the
    model can only pick from the shortlist; if it fails, the top of the shortlist is used and the
    log says "chosen by rank". It never touches a holding the user bought. At most 3 buys a check-in.
    Buys are in whole cents, so the last holding of a budget takes exactly what is left (Bold at
    $10,000: five of $1,666.67 and one of $1,666.65). Until 10 Oct a cent of rounding stopped that
    last buy for good and the log called 5 of 6 "fully invested".
  - **When it runs:** EventBridge rule `stockiq-ai-trader-schedule` (`cron(10,40 * * * ? *)`, every
    30 minutes since the quick-trading options of 10 Oct; `SLOT_MINUTES` in the Lambda must match)
    runs every user who is switched on and due. A check-in up to 5 minutes early still counts
    (`GRACE`), for the gap between check-ins and for the holding time alike.
  - **Quick trading** (owner's idea, 10 Oct: "fun to watch it trade by the hour"): `EVERY_HOURS`
    (0.5 … 24) and `HOLD_HOURS` (0.5 … 1440; settings store days, so 1 hour is 0.041666…, sent back
    exactly by the panel, which reads both fields with `parseFloat`). After selling, it waits two
    days or twice the holding time, whichever is shorter, before buying the same thing again. Stored
    screener results are reused for 20 minutes. It suits coins (they trade all the time and the
    crypto ranking moves); share rankings barely change within a day. The panel says so, and says
    that no trading costs are taken off. Side effect worth having: short holds fill the record of
    closed trades in days, not months, so the learning has something to work with.
    **Cost:** a crypto check-in is a full crypto screener run (about 540 worker calls) unless a
    stored copy under 20 minutes old exists, so one user on 30-minute check-ins adds about 780,000
    Lambda calls a month on top of the crypto history job's 780,000: past the free million, at
    $0.20 per extra million, plus one small AI-model call per check-in (well under a dollar a month). **Each screener belongs to a market** and a scheduled
    check-in only buys from, and sells holdings of, the markets that are open (`MARKET_HOURS`, UTC,
    Mon–Fri, chosen to sit inside the real hours in summer and winter time: US 14:35–19:55,
    Australia 00:05–04:55, Japan 00:05–05:55, UK 08:05–15:25; coins always). Each market keeps its own
    last-checked time (`state.lastRunBy`), so someone with US and Australian screeners is checked in
    both sessions. "Check in now" acts on everything and notes which markets are shut.
  - **Other currencies:** shares outside the US are bought in their own currency and valued in US
    dollars: `fx_pair` / `usd_rate` in the Lambda and `fxFor` / `fxRate` in `practice-portfolio.js`,
    **which must follow the same rule**: AUD, GBP, EUR and NZD use the dollars-per-unit quote
    (`AUDUSD=X`); every other currency uses the per-dollar quote turned over (`USDJPY=X`), because
    Yahoo rounds `JPYUSD=X` to 0.0063. London prices are pence (÷100). The sell rules measure the
    change in US dollars, as the dashboard shows it. No exchange rate: the buy is skipped.
  - **Stored screener results:** `get_snapshot` keeps each screener's rows for 45 minutes as items
    `_snapshot#<key>` in table `stockiq-ai-trader` (top 150 rows in full, the rest as score, signal
    and rank), so several users or check-ins do not run the same screener twice. A cold Russell 2000
    run takes about 35 s; a four-screener check-in about 45 s (Lambda: 300 s, 512 MB).
  - **Learning from its own results** (added 10 Oct 2026, the owner's "it learns and fixes itself"):
    each buy is remembered with the figures it was bought on (`state.open`); when the holding is sold,
    by a rule or by hand, `settle` writes the result to `history` (last 300: change, the S&P 500 fund
    over the same days, days held, how it was sold). From that: (1) `scorecard`: overall and by
    screener, rank band, RSI band, who chose (AI model or rank) and exit; shown on the dashboard as
    "How it is doing"; (2) `review_resting`: a screener whose last 12 trades (at least 8) average 1.5%
    or more behind the market is rested for 14 days, then tried again with a clean slate;
    (3) `write_lessons`: after every 5 more closed trades the AI model writes up to 4 short notes on
    what the record shows ("What it has noted from its record"); (4) the scorecard and notes are put
    in the model's prompt at each decision. **These inform the choice among the shortlist only: every
    limit is still enforced by code, and nothing adapts on fewer than 8 trades** (`MIN_SAMPLE`).
    Honest limit: with a handful of trades the record is mostly chance, and the panel says so. It
    does not re-tune its own stop / gain limits or risk filters; that would need far more trades.
  - **Storage:** table `stockiq-ai-trader` (key `userId`: settings, state, last 60 log entries, last
    300 closed trades; `_snapshot#…` items are the stored screener results). Buys
    and sells are written into `stockiq-paper-portfolios` with the same version check the dashboard
    uses; holdings it bought carry `by: 'ai'` and `screener`. If the user changes the portfolio at
    the same moment, nothing is traded and it tries again at the next check-in.
  - **Who may use it:** env `AI_TRADER_USERS` on the Lambda (the owner's email and the deploy test
    user; `*` would open it to everyone). The controls are hidden for anyone else. **Opening it to
    users is the owner's decision** and touches the same legal question as the signals: an AI choosing
    stocks, even with fake money, reads as picks. Each user's check-in also runs the screeners again
    (not shared between users) and makes one AI call, so cache the screener results per hour first.
  - **How the panel behaves** (redesigned 10 Oct after the owner reported "the buttons are not working":
    they worked, but nothing showed it; then made to save by itself after he found his ticks gone on
    refresh). **Every change saves automatically**: the On/Off switch at once, ticks and menus after
    0.15 s, typing and the slider after a 0.9 s pause, and anything still waiting when the page is
    left. There is no save button; a line beside "Check in now" says "Saving…", "✓ Saved." or
    "Not saved: <reason>". **No screener is ticked for a new user** (`DEFAULTS` in the Lambda), and it
    can be switched on with none: it then waits and says so. "Check in now" is greyed out, with the
    reason, while it is off or nothing is ticked. The status box says what it holds, when it last
    checked in and when it will next (`nextCheck` and `holding` from the Lambda's `public()`).
    **Two lines under the fields describe what the chosen settings will do, and every part of them
    follows what is selected** (`planText`, `paceText`; the owner noticed on 10 Oct that they only
    followed the slider): how often it checks in, how many holdings of what size it builds up to and
    after how long, the holding time and the level's loss and gain marks. They also say what a
    reader would not guess: with only coin screeners ticked, the level's coin share is the limit
    (Balanced: 25%, so $2,500 of $10,000 in two coins; Cautious and Careful buy no coins at all);
    a holding time so short that it sells as fast as it can buy never uses the whole budget (3 buys
    a check-in); a holding time shorter than the gap between check-ins means the sale really happens
    at the next check-in; a budget too small for the level buys nothing ($25 smallest buy). The sums
    are `buildUp()` in the script, **a copy of the Lambda's rules** (`allowance`, the time rule in
    `review_sells`, 3 buys a check-in, the coin share, $25): change one, change the other, and run
    `check-tools/autopilot_plan_check.py`, which replays the Lambda for 3,780 combinations of
    settings and compares. The Lambda keeps one "Autopilot on: …" line in the
    activity list for a burst of saved changes. While someone is typing, the panel is updated in
    place (`syncDraft`), not redrawn, so the cursor stays put. Styles are in one
    `<style id="ap-style">` block the script adds; raise `practice-autopilot.js?v=N` in
    `dashboard.html` when it changes.
  - **To see the panel without logging in:** build a test page around the script with a stand-in
    server and open it in headless Chrome (method: section 12, "Check a logged-in panel in a real
    browser"). This is how the redesign was clicked through and screenshotted.
  - Code: `website/practice-autopilot.js` (controls only), Lambda in `lambda-sync/stockiq-ai-trader/`.
    The AI key is the same `OPENAI_API_KEY` as the AI chat, copied to this Lambda's environment.
  - Tests: `python3 check-tools/ai_trader_test.py lambda-sync/stockiq-ai-trader/lambda_function.py`
    (88 checks, stand-in database, screeners and model),
    `node check-tools/autopilot_test.js <practice-autopilot.js>` (44 checks, the controls) and
    `python3 check-tools/autopilot_plan_check.py <lambda_function.py> <practice-autopilot.js> 150`
    (the panel's description against the Lambda's own rules; it is how the rounding fault was found).
  - Honest framing, keep it: the backtests (sections 7b and 11) found no reliable edge in the
    screener scores, so this is an experiment to watch, and the panel says so. Its own results will
    be the forward test. Turn everything off: disable the EventBridge rule.
  - Ideas not built: results of the AI's holdings shown separately from manual ones; a daily summary
    email; ASX / FTSE / Nikkei screeners (need currency handling in the trader); letting the model
    also decide sells; per-user cost limits before opening it up.
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
    (the entry log in section 8b does this job from 10 Oct). A manual buy/sell practice screen on
    the site was considered and not built: it would test the user's choices, not the screeners.
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

**Run every analysis button end to end:** section 8b, last part.

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
  - **Practice portfolio** added to the dashboard (section 8), with a new table and Lambda.
  - **AI autopilot upgraded** (section 8): all 15 screeners with per-market hours and currencies,
    quick trading (check-ins from every 30 minutes, holds from 30 minutes),
    stored screener results, and a record of its own closed trades that it learns from (scorecard,
    resting a lagging screener, AI-written notes fed back into its choices). Dollars-or-quantity
    fields on the practice buy row. Two sessions built an autopilot at the same moment on 10 Oct;
    the deploy script's fingerprint check caught it and the second build was dropped. **Run one
    session on the site at a time.**
  - **Autopilot description follows every setting** (section 8, "How the panel behaves"): the two
    lines under the fields are built from the check-in, holding time, level, budget and ticked
    screeners. Checking them against the Lambda found a rounding fault (the last holding of an
    uneven budget was never bought); fixed in `stockiq-ai-trader`. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_desc_20261010.zip`.
  - **AI autopilot** for the practice portfolio (section 8): new Lambda, table and hourly schedule.
  - **Deploy permission:** from the afternoon of 10 Oct the session's safety check refused production
    deploys and refused to let Claude change its own settings. The owner added the allow rule
    `Bash(bash /Users/dave/VSCODE/stockiq/check-tools/pending-*/deploy.sh)` himself; with it, a deploy
    packaged as `check-tools/pending-<name>/deploy.sh` runs without a hand-off. Keep packaging deploys
    that way (live-code check, rollback copy, `DRY_RUN=true`), run the dry run, then run it.
  - Docs consolidated: section 8b added, section 11 reduced to open items, `CLAUDE.md` (added
    9 Oct) loads these steering files into Claude Code sessions.
