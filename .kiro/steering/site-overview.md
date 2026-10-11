# StockIQ Site Overview (read this first)

How stockiq.tech works end to end, what is generated vs hand-edited, the current SEO setup,
known pitfalls, and open ideas. **Last full sweep: 11 Oct 2026, evening** (every part of section 8c
rewritten or checked against the deployed code; the other steering files, the README files and the AI chat's
own guide brought into line). Section 8b holds what the 9–10 Oct end-to-end test of every screener, signal
and crypto path established; section 7b the backtests and the factor study of the screener score; **section 8c
is the dashboard (practice portfolio, AI autopilot, notification bell): to resume that work, read it from
"Start here when resuming"**.

Detailed references: `stockiq.md` (AWS resources, Cognito, Lambdas, AI chat),
`script-reference.md` (every script), `add-new-stocks.md`, `stock-matching-system.md`,
`stocks-txt-csv-format.md`, `roadmap-to-9.md`, `backlinks-progress.md`, `future-work.md`.

---

## 1. What the site is

- AI-assisted stock/ETF/crypto research tool for individual investors: single-stock reports,
  trading signals, market screeners (US, Europe, Asia, other), crypto screener, AI chat.
- 3-day free trial (5 analyses/day = 15 total), then Starter $4.99, Pro $14.99, Elite $49.99 per month (Stripe).
  Every logged-in account has the practice portfolio (fake money, by hand); **paid plans add the AI
  autopilot** that runs it (section 8c).
- Traffic is very low (a few visits/day; 13 visitors/month in March 2026), revenue $0.
  The main goal is organic search traffic, then conversions.
- Owner edits in **Kiro** (not VS Code). The top folder is still named `/Users/dave/VSCODE`.

## 2. Architecture

```
Browser ──> CloudFront (EHXV50CPHY07R, www→apex redirect function)
              └─> S3 bucket stockiq-final-websitebucket-vqekic7enf9h (static files)
Browser ──> Lambda function URLs directly (no API Gateway; 984 functions, 969 with URLs, ~650 are screener workers)
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
| `/Users/dave/VSCODE/stockiq/` | `davedewit/stockiq` | Scripts, Kiro steering, `check-tools/` (end-to-end test scripts, section 8b), **`workers/` (the one source file every share-screener worker runs, with its build, proof and deploy tools: section 8b)**. `lambda-sync/`, `.analysis_cache/`, `*.json` are gitignored |
| `~/VSCODE/backup/` | – | Daily backups made by every deploy: `website_backup_<UTC time>` and `stockiq_backup_<UTC time>`, 30-day retention. **This is the backup**, including `stocks/`, which GitHub does not have |

**Restoring:** folder names use UTC (`website_backup_20260925_034730` = 13:47 AEST on 25 Sep).
- Hand-edited files and scripts: `git checkout <commit> -- <file>` (both repos are on GitHub).
- Stock pages: copy back from a backup, e.g.
  `rsync -a ~/VSCODE/backup/website_backup_<time>/stocks/ ~/VSCODE/website/stocks/`,
  then deploy (dry run first).
- The live site is simply whatever the last deploy uploaded; restore locally, then redeploy.
- **The daily backup does not include Lambda code.** Both copies are made with `--exclude='lambda-sync'` (`deploy-to-s3.sh`),
  and `lambda-sync/` is not in git either, so a Lambda's old code exists only where someone kept it:
  - **`~/VSCODE/backup/lambda_full_20261011_before_one_worker_code/`**: every one of the 984 functions as it was live at
    12:20 UTC on 11 Oct 2026, before the share-screener workers were moved to one code base (`functions.tsv` names each
    function's zip and fingerprint, `packages/` holds the 385 distinct zips, `README.txt` has the restore command). Its
    name has no `_backup_` in it on purpose: the deploy deletes `*_backup_*` folders after 30 days.
  - `~/VSCODE/backup/workers_before_onecode_20261011/`: the same day's old package of each of the 669 share-screener workers.
  - the single zips kept before each Lambda change (`<function>_before_<name>_<date>.zip`, listed in section 8c).
  - The share-screener workers' code is the exception: it is in git (`stockiq/workers/`), and so in the daily backup too.

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
The hours are the **machine's own clock** (`date` in `~/stockiq-daily.sh`). On 11 Oct 2026 this Mac was
set to UTC+7, not Sydney time, so "11am–10pm" was 04:00–15:00 UTC; check `date` before working
out when the next run is.

Order inside `deploy-to-s3.sh`:
1. `update_news.py`: Yahoo/Google RSS → OpenAI summaries → news.html + news.js (2-hour cooldown)
2. `update_stock_news.py`: per-stock news into stock pages + news.html/news.js (23-hour cooldown per stock)
3. `update_stock_analysis.py` (**daily run only**: it sits inside the `UPDATE_STOCK_NEWS=true` block, so a plain `./deploy-to-s3.sh` prints "Skipping stock data snapshots"): data snapshots on all 3,467 stocks, sets index/noindex on large caps (≥$10B), writes `indexable_stocks.txt`. ~20 min, no API cost. 404s for delisted stocks are normal/cached. When Yahoo has no price for a stock it keeps yesterday's snapshot and does not de-index it. Straight after it, in the same block, `publish_company_figures.py` publishes the company figures the single-stock report uses for shares outside the US (section 7, "The single-stock report"); it never stops the deploy.
4. Backups (website + stockiq; prod_scripts every 23h)
5. `people_also_watch_stocks.py --missing`
6. `update_sitemap.py`: **rebuilds** stock URLs from `indexable_stocks.txt` (not all HTML files), updates lastmod on site pages. Refuses if list < 200 entries.
7. `cleanup_broken_links.py`, `remove_news_duplicates.py`, `finalize_news_html.py` (trim news.html to 240 stock + 60 general, keep noindex)
8. S3 upload:
   - `stocks/`: `aws s3 sync --delete` (size + mtime), 24h cache
   - `js/`: sync --delete
   - root `*.html`, `*.css`, root `*.js`: uploaded when the local MD5 differs from the S3 ETag
   - **How long a copy may be kept (since 11 Oct 2026; `HTML_CACHE`, `ASSET_CACHE`, `NEWS_JS_CACHE` in the script):** a
     browser must ask again for a root page every time (`max-age=0, s-maxage=3600, must-revalidate`) and keeps a root
     script, stylesheet or `js/` file for five minutes (`max-age=300, s-maxage=86400`; news.js `s-maxage=3600`).
     CloudFront keeps them for the `s-maxage` and is emptied by the invalidation that ends every deploy. Before that
     browsers kept pages an hour and scripts a day: see section 9, "A fix that is live but not seen". The stock pages
     are still 24h
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
  `python3 check-tools/report/patch_metrics.py <the Lambda's file> stock_metrics.py stock_metrics.py` copies the functions
  across and stops if the two differ afterwards.
- Stock pages use Yahoo fundamentals (converted to Finnhub units: %, D/E ratio) because the
  Finnhub free key is shared with the live Lambda. **Page and app scores can still differ**: the page uses
  the previous close and Yahoo's figures, the app the live price and Finnhub's figures first (Yahoo's, from the
  pages' own cache, only for what Finnhub lacks). The largest cause of big jumps, a trend factor of +12 or -12 on
  the sign alone, was replaced by a graded one on 11 Oct 2026 (next part); RSI, MACD and the one-year change still
  score in steps (AAPL once showed 71 on the page and 47 in the app a day later).
- **The screeners are price, momentum and volume only.** Their "financial", "sentiment" and "risk"
  factors do not use real company data, and the 12 weights total 102% in the code (section 8b).
- **Every share screener is scored by one file since 11 Oct 2026** (`stockiq/workers/stock_worker.py`, section 8b "The worker
  groups"), so a stock scores the same whichever screener lists it. Before that the US and London workers worked out RSI as a
  plain 14-day average, the ASX and Nikkei workers by Wilder's smoothing (the standard, what charting sites show), and the
  NASDAQ 100 and Dow 30 workers had a "financial" and a "risk" factor of their own. All now use Wilder's RSI and the common
  factors. Crypto is a different program (section 8b "Crypto").
- **Neutral wording everywhere**, public pages and the paid product: "Strongly positive …
  Strongly negative signals" plus "not financial advice". No BUY/SELL labels, targets or stop
  losses are shown anywhere (section 8b). Until 11 Oct 2026 the model called its 1-year change "YTD"; it now says
  "over 1 year" (the pages' relabelling of "YTD" is left in and does nothing).
- `about.html` documents both systems, including the 102% and the price-and-volume-only note.
  Keep it in sync if scoring changes.

### The single-stock report and its chart: how they work now (rebuilt 11 Oct 2026)

The owner asked whether the individual stock analysis could be improved ("it took a long time to create back in the day
with an older version of AI"). The live report was run for a US share, an Australian one, a UK one and a fund and read
line by line. What was wrong, and what it does now:

- **Two functions.** `stockiq-option-1-1-custom-analysis` (`lambda_function2.py`, about 2,440 lines) fetches a year of
  daily prices from Yahoo, company figures, dividends, the VIX and the latest news from the share's own stock page,
  scores the share and writes the report text. It calls `stockiq-chart-generator` (`lambda_function_simple.py`) for the
  picture, which comes back inside the report text as a `data:` address. The pages can also ask the chart function for
  a chart by itself (`script.js`, `analysis-functions.js`: they turn the SVG text into a picture with `btoa()`, so **the
  chart's text must be plain ASCII**: a pound or yen sign is written as a character code).
- **Prices in the share's own currency** (`money()`, `currency_note()`; the currency comes with Yahoo's prices). Every
  share was printed with a dollar sign: BHP.AX "$60.94" (Australian dollars), IMB.L "$2662.00" (2,662 pence). Now
  "A$60.94", "2,662.00p" with a line "Prices for this share are in pence: 2,662.00p is £26.62", "¥2,910.50", "C$243.83".
- **One bar a day, and the latest session from the quote** (`bars_from_chart`: the same rules as the screener workers).
  ASX shares said "+0.00% today" after the close (Yahoo sends the last session twice); a London share whose latest bar
  arrives empty showed the price of the day before.
- **One RSI** (Wilder's, as the chart and the screeners use). The text said 47.3 under a chart that said 56: the report
  used a plain 14-day average, the chart Wilder's smoothing.
- **A trend factor that grows with the distance** (`trend_points`): up to 6 points for where the price is against its
  20-day average and up to 6 for where the 20-day average is against the 50-day, each in full at 2% apart
  (`TREND_FULL_AT`). Names: Strong Uptrend (9 or more), Uptrend (3 or more), Flat Trend, Mixed Trend (two clear halves
  that point opposite ways: a bounce inside a decline), Downtrend, Strong Downtrend. It was +12 or -12 on the sign
  alone: BHP.AX, up 45% in a year, read "Strong Downtrend: -12" for being 0.03% under its 20-day average, and a move of
  a few cents swung a score by 24 points.
- **One explanation of the score.** Under the breakdown stood a "detailed scoring methodology" that used other points
  (a one-year gain +7 where the breakdown said +3), did not add up to the score and quoted 40% / 40% / 20% weights that
  do not exist. It is gone. "How the score is built" now adds the breakdown's own points: "50 + 41 - 28 = 63". The
  company-figure lines use the score's own thresholds (`company_figure_lines`): a figure could read "Weak" in the
  breakdown and "Adequate" below it.
- **Company figures for shares outside the US.** Finnhub (free plan) has them for US shares only, so every Australian,
  UK, Japanese, Canadian, European and Hong Kong share was scored on price alone while the report listed "fundamental
  metrics". **Yahoo's own summary cannot be read from AWS or from a script**: it answers "429 Too Many Requests" to
  anything that is not a browser (tried in the first deploy, taken out again). What works: `update_stock_analysis.py`
  already keeps Yahoo's figures for every stock on the site in `.analysis_cache/info/`.
  **`publish_company_figures.py`** puts them, in the score's units, into one private file,
  `s3://stockiq-dynamic-stock-lists/site-data/company_figures.json` (3,333 stocks, 570 KB; refuses to upload fewer
  than 1,000; leaves out figures older than 75 days). The daily deploy runs it straight after the snapshot step (it
  never stops a deploy; a dry run only builds the file). The function reads the file once per warm container and for six
  hours (`site_company_figures`), fills only the figures Finnhub did not have (`fill_missing_figures`), for shares only
  (a fund gets none), and the report says "Company figures from Yahoo Finance (as of 5 Oct 2026)" or "from Finnhub and
  Yahoo Finance (…)". A share that is not on the site, or a file that cannot be read: "Company figures were not
  available for this share. The score above is therefore built from price and volume only".
- **Smaller things:** "YTD" is called the one-year change it is; "Breaking news (last 24 hours)" is "Latest news" (the
  article can be days old); "Oversold (Buy signal)" / "Overbought (Sell signal)" lost their brackets (advice wording
  that the Oct 9 pass had missed); volume is compared with the 20-day average the score uses (a line labelled "20-day
  average" printed the year's); while a session is still open its part-day volume is left out of the score
  (`partial_day`; it read "Low Volume: -3" every morning); "Liquidity Crisis" is "Low Liquidity"; filler lines removed.
- **The chart** (`draw_chart`) is drawn from the very prices the report scored, sent to it by the report with its
  support and resistance (`series`, `currency`, `support`, `resistance` in the request), so picture and text cannot
  differ; asked by itself it fetches its own with the same rules. Averages and RSI start when they have their days (they
  were padded: flat lines, then a jump); the 200-day average is on it; it has no background of its own and mid-tone
  lettering, so it sits on a dark page; **lettering grows when the picture is shown small** (a rule inside the SVG:
  `@media (max-width:480px)`, which a browser applies to the size the picture is shown at); 21 KB (it was 79 KB, and a
  saved report 115 KB: now about 35 KB).
- **Scores moved, and the stock pages with them.** On saved prices for 106 US shares the page score moved 6 points on
  average (27 of them by 10 or more, no lean up or down), mostly from the RSI method. `stock_metrics.py` carries the
  same functions; the pages follow at the next daily run. **None of this makes the score better at predicting**
  (section 7b): it makes the report correct and consistent.
- **The functions' code is still not in git, and the report's cannot be yet: it holds the Finnhub key in the code.**
  What changed is kept as the scripts that made the change: `check-tools/report/changes-2026-10-11/` (run in order
  against the copies in the rollback zips they rebuild the live code exactly). Tests:
  `python3 check-tools/report/report_test.py <the file from ~/VSCODE/backup/stockiq-option-1-1-custom-analysis_before_report_20261011.zip> lambda-sync/stockiq-option-1-1-custom-analysis/lambda_function2.py`
  (79 checks: the old code and the new on the same saved prices, `--show SYMBOL` prints a whole report) and
  `python3 check-tools/report/chart_test.py lambda-sync/stockiq-chart-generator/lambda_function_simple.py lambda-sync/stockiq-option-1-1-custom-analysis/lambda_function2.py`
  (29 checks). A live report without saving anything: POST `{"symbols":["BHP.AX"],"userId":"nobody-deploy-check@example.com","skipHistorySave":true}`
  to the function's address (with no `userId` it is treated as a background run and **saved**).
- **Live** (13:29 UTC, 11 Oct 2026): `stockiq-option-1-1-custom-analysis` `cPDWynX/4N+25Ec/+jot60nlhFWq1aeZ8wH/ozEqKps=`,
  `stockiq-chart-generator` `OIDrZ2W9G3lJ2sKarnoT4c7RvoLh1ApDX43NWjR72z4=`, both equal to their mirrors. Checked with
  the live report for AAPL, BHP.AX, IMB.L, 7203.T, SHOP.TO and SPY, through the page's own code (`page_run.js 1 custom`),
  and by looking at the live chart at desktop and phone width on light and dark. **Not checked:** the analysis page
  itself in a browser, a real phone, the dashboard's "Run in Background" for a single stock.
  Rollback zips, in order: `~/VSCODE/backup/stockiq-chart-generator_before_report_20261011.zip`,
  `stockiq-option-1-1-custom-analysis_before_report_…`, `…_before_figures_…`, `…_before_source_…`.
- **Left as it is:** the first line still says "(REAL-TIME DATA)", as every screener's does (one wording decision for
  the whole site); MACD still scores +8 or -8 on its sign and RSI in steps at 30 / 40 / 60 / 70; valuation is counted
  twice for a share with a high P/E and a high price-to-book; the Finnhub call is still made for shares it never has;
  the report's time is the visitor's only when the page sends its offset.

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
- **This two-year test used the US workers' RSI of the time** (a plain 14-day average). Since 11 Oct 2026 every screener uses
  Wilder's RSI (section 7), which changes about a third of US signal labels and three or four of a day's top 10, so the dollar
  figures above describe the scorer as it was. It was not run again (its 502 price series are not on this machine); the
  studies that could be run again say the same thing as before (end of this section).

**Factor by factor (11 Oct 2026).** The owner asked whether the scoring that produces the screeners'
CSV could be improved to raise the chance of profit, with "70% profit, 30% loss" as the aim. Tool
and full output: `check-tools/paper-test/factor_study.py`, `results-factors-2026-10-11.txt` (the S&P
100 worker's own code replayed on saved prices, 101 stocks, 999 trading days, 17 Oct 2022 – 9 Oct
2026; no downloads; about 100 seconds).
- **None of the score's own factors had a reliable link with what a stock did next** (day, week or
  month): RSI, MACD, short / medium / long momentum, Bollinger, sentiment, MA trend all inside the
  margin of error, several with opposite signs in the two halves of the period. The final score:
  +0.19 points a week for its top fifth over its bottom fifth (t 1.3). The labels: nothing.
  Volume, Market and Risk are the same for nearly every stock on a day, so they cannot sort.
  The "Financial" factor looks clear (t 2.3–2.6) but **is an artefact**: it is the hard-coded guess
  per company name (section 8b), which happens to favour the companies that rose.
- **Two raw figures did point the right way in both halves:** how jumpy a stock is (`atr`, t 3.5)
  and how far it is above its 52-week low (t 2.6). The first is risk, not skill: a score built
  from the two had a top 10 that moved 2.2 times as far as the list in rising weeks and 1.4 times
  as far in falling weeks, worst month -32% against -12%, and half its lead went when the seven
  chip / AI names were left out. **The second kept a modest lead among equally jumpy stocks:**
  +0.40 points a week, +1.5 a month (t 2.0, same sign in both halves). That is the known momentum
  effect, flattered here by using today's index members.
- **A win rate is set by the selling rule, not by skill.** Under the autopilot's own rules 45–51%
  of trades ended up, for the score's top 10 and for any stock alike. A rule built to "win" (sell
  at +2%, loss limit -15%) ended up 76% of the time for the top 10 and 74% for any stock at all,
  and made no more per trade than the rest. **"70% up, 30% down" can be had by anyone and says
  nothing about profit**; what counts is the average per trade against the average stock, and
  there the top 10's lead was +0.02 to +0.22 points a trade, never clear (t under 1).
- **Quick trading in shares loses to costs:** with 0.2% a trade taken off, one-day holds averaged
  -0.14% a trade and two-day holds -0.02%; 20-day holds +0.86%, most of it the market's own rise.
- **What was done with it:** nothing in the screeners (re-weighting 650 worker functions to one
  rising market's winner would be fitting to the past, and it is a product-wide change that is the
  owner's to decide). The autopilot now records how far above its 52-week low each share was when
  bought and splits its record by it (section 8c), so its own fake-money trades test the one
  finding that survived. **If that split shows the same after 8 or more trades a band, the next
  step is a trial of buying shares in that order**, beside the current order, through its trial
  mechanism. Not covered: coins (no saved prices; the entry log of section 8b is their test).

**The same studies with the one worker file (11 Oct 2026, evening).** When every share screener was moved to one file with
Wilder's RSI, the studies that read the worker's code were pointed at `workers/stock_worker.py` and run again on the same
saved prices. Nothing in their conclusions moved:
- Factor study (`paper-test/results-factors-2026-10-11-one-worker.txt`): the score's top fifth over its bottom fifth +0.06
  points the next day (t 2.0), +0.19 a week (t 1.2), +0.75 a month (t 1.2); it was +0.04 / +0.19 / +0.84. The RSI factor has
  no reliable link with what a stock did next under either way of working it out; every other factor's line is identical,
  figure for figure, which is also a check that nothing else in the scoring changed.
- Fake-money tests (`paper-test/results-backtest-2026-10-11-one-worker.txt`): Dow 30 top 10 +12.2% a year against +18.4% for
  the whole list (it was +16.8%); S&P 100 top 10 +40.4% a year against +25.2% (it was +43%), still inside the margin of error
  from a week out. **Their top 10 for the last close equal the live Dow 30 and S&P 100 pages name for name**: the replay
  reproduces the live scores with the new file.
- Replay of the autopilot's rules (`replay/results-replay-2026-10-11-one-worker.txt`; the earlier run is kept beside it, and
  `replay/panel.json` now holds the new scores): the five levels still end behind the index fund after costs, quick trading
  still loses, and buying the share furthest above its 52-week low without selling on the signal is still what holds up on
  the part of the period the search never saw.
- So there is no evidence for or against either RSI: the choice was for one way everywhere and the standard definition.

**The autopilot's own rules, replayed (11 Oct 2026, evening).** The owner asked, honestly, whether this will ever make
more than it loses, and whether it could "run on some kind of rapid speed to learn faster". It can: `check-tools/replay/
replay.py` runs the autopilot's rules (imported from the deployed function) over the same four years of S&P 100 prices
in 20 seconds, with 0.1% taken off each buy and each sale, decisions once a day at the close and trades at the next
open. Full output: `check-tools/replay/results-replay-2026-10-11.txt`. To keep it honest an idea is found on the first
60% of the days and judged on the last 40%, and compared with the same rules buying at random.
- **The five levels as they are all finished behind an S&P 500 fund** (+107.5% over the period): Balanced +92%, Careful
  +55%, Cautious +44%, Bold +26%, Adventurous -17%. Per trade none is clearly ahead of the fund.
- **Holding time decides most of it.** Everything else as Balanced: kept 1 day -4%, 2 days +29%, 5 days +92%, 10 days
  +97%, 20 days and longer +103% to +106%; without selling on the screener's signal, 20 to 60 days gave +112% to +115%.
  **Shares kept a day or two lose to costs at every level**; the automatic pace of Bold (2 days) and Adventurous (1 day)
  is that. The panel now says so when shares are ticked with a holding time of two days or less.
- **Selling when the screener's signal turns cuts winners short** in this replay: holdings were kept 4 to 7 days on
  average whatever the time limit, because the signal sold them.
- **Ranking by something else than the screener's score** (same rules, 20-day holds; first part → second part, per trade
  against the fund): the score +0.33 → +0.58 (never clear, luck better in 6%); furthest above its 52-week low +1.96 →
  +2.33 (t about 3 both times, luck never better); biggest rise over 90 days +0.88 → +3.50; over a year +0.59 → +2.46;
  the jumpiest stocks +1.64 → +2.97; the calmest and the lowest RSI clearly behind. That is momentum, and risk.
- **Why this is still not a reason to believe it:** the whole period was a rising market led by a few chip and AI names;
  without the seven of them the best variants' lead falls inside the margin of error (t about 1); the list is today's
  members, which hands any "buy what has risen" rule the survivors; daily decisions, no AI model in the loop. Of 240
  variants of the rules, 208 looked ahead on the first part and 103 on the second.
- **What it changes:** nothing is adopted from it. It says what is worth a forward trial with the fake money: the order
  shares are bought in (already on trial, section 8c), longer holding times for shares, and not selling on the signal.
  It also gives the owner one plain piece of information for his own settings: with shares, a holding time of a week or
  more. **Not possible here:** inputs about the company itself (profit, debt, growth). There are no past figures of that
  kind on this machine, so they cannot be replayed; the way to test them is forward (record them with each share bought
  and split the record), and they need a data source the function does not have.
- **The owner's question, answered plainly to him:** as built, it is unlikely to learn its way to steady profit; the
  inputs have shown no edge beyond momentum in a rising market; real money should wait for the bar (section 8c) and then
  be small; the likelier income is subscriptions. He chose to carry on in the order: replay, real costs, better inputs,
  the bar in writing.

## 8. Front end

- `analysis.html`: options 1–7 (stock/ETF report, signals, US/EU/Asia/other screeners, crypto).
  Logic in `analysis-functions.js` (~350 KB, holds the stock lists and all formatters) +
  `js/analysis-core.js`. How the screeners, signals and crypto work: section 8b.
- `dashboard.html`: report history, favourites, plans/upgrade (Stripe), manage subscription,
  "Run in Background" (through `stockiq-screener-coordinator`), 🎯 performance tracker. **Since 10 Oct
  2026 it has tabs under the heading: Reports (the statistics, Report History, auto-delete),
  Practice portfolio, AI autopilot** (section 8c). The plan sections ("Upgrade Your Plan", "Manage
  Subscription") stay below every tab, because other pages link to `dashboard.html#upgrade` and
  code scrolls there.
- `index.html`: market overview widgets, guides, "How StockIQ Works", **Pricing section**
  (`#pricing`, three plans in USD), email signup ("Get Screener Highlights by Email", details in
  `stockiq.md`), comparison table.
- **Practice portfolio and AI autopilot** (dashboard, built 10 Oct 2026): a fake-money portfolio the
  owner buys and sells in by hand, and an autopilot that trades it from the screeners' results,
  reviews its holdings with the AI model and recent headlines, and tries bounded changes to its own
  rules. `practice-portfolio.js`, `practice-autopilot.js`, Lambdas `stockiq-paper-portfolio` and
  `stockiq-ai-trader`. **Everything about them, and how to work on them, is in section 8c.**
- Stock pages load `sidebar.js`, `stock-prices.js` (live ticker), `ai-chat.js`, `auth.js`, `theme.js`.
- **Notification bell** (🔔 in the header of 18 hand-edited pages and of the stock pages): one list, drawn by
  `autopilot-bell.js` for every page, of the reports and the AI autopilot's buys and sells (section 8c, "The notification
  bell").
- AI chat button: bottom-right on the pages that load `ai-chat.js` (the home page, blog, the dashboard and the stock pages); on the home page it moves left of the news panel
  only from 1401px wide (the panel is hidden below that).
- Every public page footer carries a "General information only, not financial advice …" line.
- Theme: light/dark by time of day unless the user overrides (`localStorage.theme`).
- Live prices on stock pages (main ticker + "People also watch" cards) come from
  `stock-prices.js` → Lambda `stockiq-popular-prices`, refreshed every 5 s. Pages opened from local files
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
  page path Russell 1000/2000 send only `worker_id`, and each worker takes its own ten stocks from
  `lists.txt` inside the worker package. **That file is the coordinator's two Russell lists**
  (`workers/lists.txt`; `workers/build.py` refuses to build if they differ, `build.py --lists` writes it
  again), so a page run and a background run now cover the same stocks. A Russell list change is therefore
  the coordinator, `lists.txt` and a worker deploy.
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
- An empty batch returns nothing (since 11 Oct 2026; before, the Russell and NASDAQ workers fell back to a
  built-in list and returned unrelated stocks). Both paths still skip empty batches. Only a call with **no
  `stock_batch` at all** to a Russell 1000 / 2000 worker takes that worker's ten stocks of `lists.txt`.
- No worker Lambda needs creating or deleting when a list changes; idle functions cost nothing.
- The coordinator de-duplicates results by symbol.

### The worker groups: one file for every share screener (done 11 Oct 2026)

The owner asked whether the screeners "all share the same function", and for it to be made simpler to manage. They did
not; now they do. **All 669 share-screener workers (13 groups) run the same package, built from `stockiq/workers/` in git.**
Checked at the end by downloading every package: one set of four files in all 669, byte for byte the files in git.

| In `stockiq/workers/` | What it is |
|---|---|
| `stock_worker.py` | **The code.** Prices from Yahoo, the indicators, the 12-factor score. Change the scoring here and nowhere else |
| `lambda_function.py`, `advanced_lambda.py` | Two lines each: the two handler names the functions are set up with (`advanced_lambda.lambda_handler` for the ten S&P 100 workers, `lambda_function.lambda_handler` for the rest) |
| `lists.txt` | The Russell 1000 and Russell 2000 lists (the coordinator's), for page runs that send a worker number and no stocks |
| `groups.py` | **The one table of groups and markets** (group, screener, number of functions, market; per market its currency and sample shares). `deploy.py`, `prove.py`, `build.py` and `check-tools/workers.py` all read it |
| `build.py` | Builds the package. The same input always gives the same zip, so every function shows one fingerprint |
| `prove.py` | What a change does: replays saved prices through the live copy (the mirror) and the changed file, lists every figure that differs, then how far scores, labels and each day's top 10 move. `--fetch` once for the non-US sample |
| `deploy.py` | Puts the package on the functions, a group at a time, through a `check-tools/pending-<name>/deploy.sh` (its header has the three-line template). `--selftest` plays its rules against a stand-in for AWS |
| `live.txt` | The fingerprint of the package that is live (`q9ZX/UvTB…` since 11 Oct 2026). The deploy accepts only this one or the new one on a function |
| `results-proof-2026-10-11.txt` | The proof run before the first deploy |

**To change the workers (scoring, a fault, real company figures one day):** edit `stock_worker.py`; `python3 workers/prove.py`
and read every difference (only the ones meant may remain); commit; make `check-tools/pending-<name>/` with `deploy.sh` (the
template) and `groups.txt` (one small group first, e.g. `stockiq-option-3-8-worker`, later the word `all`); dry run, deploy;
run that group's button through the page and the coordinator (end of this section); then the rest; commit `workers/live.txt`;
remove the folder. `python3 check-tools/workers.py` must show "one" for the 13 groups and the same code across them
(`--contents` downloads and compares, the honest count).

- **928 worker functions in 18 groups; 724 are called by the site** (669 share workers, 54 crypto workers, 1 single-coin
  worker). **204 are not called at all** (`stockiq-option-3-3-worker` 60, `stockiq-option-7-4-worker` 139,
  `stockiq-option-3-worker` 5): left over, they cost nothing idle, and can be deleted when the owner agrees. They were not
  touched and still hold old code.
- **What the audit really found (the first table was misleading).** `workers.py` counts package fingerprints, and a zip's
  fingerprint changes with the dates of the files inside it. The "100 / 200 different versions" of the Russell groups were
  two programs zipped 300 times; FTSE's "9 different" were two files differing in one default number. Across the 669 share
  workers there were **seven code files**: S&P 100 / 400+600 / 1500 (one), Russell 1000, Russell 2000 (the same with a list
  file each), NASDAQ 100 / Dow 30 (one), ASX x4 / Nikkei (one), FTSE (two).
- **What the one file is:** the ASX / Nikkei copy (it had Wilder's RSI and the right 52-week formula) with the UK sector
  list, and these changes, each shown in `results-proof-2026-10-11.txt`:
  1. **One RSI: Wilder's smoothing, everywhere.** The US and London workers used a plain 14-day average. **This is not a
     small change** (the notes written before it said "a little"): on saved prices about 37% of US and London signal
     labels differ on a given day, the score moves by 0.5 or more (on a scale of about -2 to +3) on 46% of stock-days,
     and a day's top 10 keeps 6 or 7 of its 10 names. It is no better or worse at predicting anything (section 7b). ASX
     and Nikkei scores did not change from this.
  2. **NASDAQ 100 and Dow 30 lost their own company-figures tables.** Their copy gave bonus points to seven named tech
     companies and seven "growth leaders", used a wider "healthy" P/E band and its own P/E guesses, and counted earnings
     risk differently; the Dow 30 ran this "tech" copy by accident of copying. They now use the common factors, so AAPL
     scores the same in the Dow 30, NASDAQ 100, S&P 100 and S&P 500. With RSI held still this alone moves the score by
     0.5 or more on 11% of stock-days and changes 17% of labels for those two screeners.
  3. **A session Yahoo sends twice is kept once.** After the ASX closes Yahoo sends the day's bar and the closing quote as
     two bars (seen for 12 of 12 ASX shares on 9 Oct); the 24-hour change was 0 for every ASX stock and every look-back
     was a day short. Bars are now one per trading day on the exchange's own clock (`bars_from_chart`). On the day of the
     deploy the ASX top 10s kept 5 to 7 of 10 for this reason.
  4. **A latest session that arrives empty is taken from the quote** that comes with the chart (London, seen 10 Oct: prices
     a trading day old). **Tested on a real answer with its last session emptied (12 of 12 right), not yet seen live**: by
     11 Oct Yahoo had filled Friday's bar in. Look at a FTSE run on a morning after a London session.
  5. **SPY is fetched once per batch**, not once per stock (the market's state is the same for all ten): half the calls to Yahoo.
  6. **The Russell lists in the package are the coordinator's** (877 and 1,829). The old packages held 1,000 entries for the
     Russell 1000, **125 of them company names instead of tickers** ("Amazon", "Airbnb", "3M"), without BRK-B and BF-B, and
     1,977 for the Russell 2000 with 147 dead tickers; a page run and a background run covered different stocks.
  7. A fallback for the distance from the 52-week low that gave a wrong figure for a share more than 500% above its low
     (99 of 21,870 stock-days) is gone; an empty batch returns nothing; each stock carries a new field `currency` (as Yahoo
     gives it: `USD`, `AUD`, `JPY`, `GBp` for pence); the CSV writer and test block the function never ran were removed.
  With each copy's own RSI put back into the new file, everything else was identical: S&P family 99.5% of 21,870
  stock-days (the rest is item 7), Tokyo 600 of 600, London 624 of 624, ASX all but the day of the doubled bar.
- **How it was deployed:** a group at a time through a packaged script (Dow 30 first; it was then put back once to prove
  the way back, its fingerprint matching the independent copy, and deployed again), each group's first and last worker
  tried for real, and every one of the 14 share buttons run through the page code and the coordinator afterwards: every
  worker call answered, no flags, the tracker found 10 symbols each time, and a live worker's answer equalled the file
  in git run on this machine on all 480 figures of ten stocks.
- **The way back to before 11 Oct 2026:** every function's old package is in
  `~/VSCODE/backup/workers_before_onecode_20261011/<function>.zip` (669 files), and the deploy script of that day puts
  them back: `git show a6edbd9:check-tools/pending-workers/deploy.sh` and `deploy.py` into a `pending-` folder with a
  `groups.txt`, then `ROLLBACK=true bash …/deploy.sh`. A full copy of every Lambda function as it was at 12:20 UTC that
  day, with a README, is in `~/VSCODE/backup/lambda_full_20261011_before_one_worker_code/` (made outside this session).
  From now on `deploy.py` keeps one zip per deploy (`~/VSCODE/backup/workers_package_<fingerprint>.zip`).
- **Settings were not changed** and still differ a little by group (Python 3.11, 3.12 or 3.13; 128 or 256 MB; timeouts of
  30 to 900 s; a few unused environment variables). The code does not depend on any of it.
- **Left as they are, on purpose, because changing them would change labels again** (each is one line in the one file now,
  and the owner's to decide): `MODERATE_SELL` is only given at a score of exactly -0.8 (the test above it catches the
  rest as `HOLD`); `momentum_signal` can never say `STRONG_DOWN` (the `DOWN` test comes first); the line "PRE-SCALE
  TOTAL" prints the scaled score; the 12 weights total 102%; the market's state is the US market's (SPY) for every
  country; no real company figures.
- **Not part of the workers, found on the way and still open** (section 11): London prices are in pence and both report
  writers print them with a currency sign as if pounds; the coordinator's report cuts every symbol to five characters
  and prints "$" for every market.
- **The crypto workers** (54, one version) are a different program; their MACD fault was fixed the same day ("Crypto",
  below). The single-coin worker asks for 60 days and does not have it.

### What the screener workers really do

- They return 48 data fields per stock (`currency` since 11 Oct 2026) and no report text. Codes: `STRONG_BUY`, `BUY`,
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
- **ASX quirk (fixed 11 Oct 2026):** once the ASX has closed, Yahoo returns the last session bar twice, so the
  ASX workers computed a 24-hour change of 0 for every stock (also flattening their sentiment
  factor and `Momentum_Signal`). Bars are now one per trading day. Not checked during ASX hours.
- A worker returns nothing for WBD and PSKY because **Yahoo has no usable history for them** (11 Oct 2026: one bar
  for WBD, which stopped trading on 6 Oct; 42 of PSKY's 52 bars empty). The price source, not the worker.
- Real fundamentals are now one file and one deploy (`workers/`, above), once there is a source for them.

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

**How a coin is scored and ordered, and three faults fixed on 11 Oct 2026.** The owner looked at a crypto export and asked
whether the top 10 is even in the right order (the 11th coin had the same score as the 9th and 10th).
- **The score** (`stockiq-option-7-1-worker-N`, in the code after "ADVANCED SCORING SYSTEM") is a whole number of points
  from yes/no rules: MACD (strong bull +3, bull +2, bear -2, strong bear -3), RSI (extremely oversold +3, oversold +2,
  overbought -2, extremely overbought -3), Bollinger band (oversold +2, bullish +1, bearish -1, overbought -2),
  stochastic (±1), volume (±1), momentum (strong ±2, ±1), the day's change (over 10% +2, over 5% +1, and the reverse),
  a breakout above the last 20 days' high (+2), a volume surge on a rising day (+2), 3- and 5-day rise together (+1),
  a +1 for ten named large coins, and penalties (RSI over 75 and falling -3; down more than 15% in a week -2). Labels by
  score: 7 or more Strongly positive, 4 Positive, 2 Slightly positive, -1 Mixed, -3 Slightly negative, -5 Negative.
  **It rewards opposite things at once** (being oversold, and breaking out upwards), and nobody has tested whether it
  predicts anything for coins (there are no saved coin prices to replay; the entry log below is the forward test).
- **The order** is by score, and **coins with the same score are listed largest first** (their place in `COINS`), so that
  the list is the same on every run. That was right in his export. But a whole-number score means many ties: at one run
  six coins had +3 and three of them were "in the top 10" by size alone. The report now says so under the list when coins
  tie at the cut ("4 coins have a score of +6; 2 of them are in this list…").
- **Fault 1: MACD was never worked out, for any coin.** The worker asked for 30 days of prices and MACD needs 35, so
  `calculate_macd` answered "not enough" every time, and that was read as "BEAR - Below signal line": all 540 coins got
  "MACD Bear: -2" (the export's MACD column said the same for every row). The order was not changed by it (the same -2
  for everyone) but every score was 2 too low, every label a notch lower, and the heaviest input was missing. Now 90 days
  are asked for, for MACD alone (`macd_closes`; everything else still uses the last 30 days, and each coin's other figures
  were compared before and after: identical), and too little history counts as "NEUTRAL - Not enough history", 0 points.
  After the fix one run gave: bear 289, strong bear 138, strong bull 71, bull 38; scores from -7 to +11 (they were -7 to
  +6); 8 coins Strongly positive (there were none).
- **Fault 2: a coin whose price does not move could stand in the top 10.** VVS (price $0.00000097, too small for the price
  source's digits) had the same change over 1, 7 and 30 days and an RSI of 0; a flat line reads as "extremely oversold"
  (+3, +2, +1), which put it 5th. The orchestrator now leaves such coins out of the ranking (`stuck`: no daily range, or
  the same change over 24 hours, 7 days and 30 days): three at the time (VVS, HTX, GEKKO), so 536 or so are ranked.
- **What follows from the fix:** the top 10 after 11:52 UTC on 11 Oct 2026 is partly different from before, so "in the top
  10 since" started again for the newcomers, and **rows of the entry log from before that time were ranked without MACD**:
  do not mix the two when the track record is measured. The autopilot buys coins by this ranking, so the same goes for
  its coin trades before and after.
- **Not touched:** `stockiq-option-7-2-worker-1` (single-coin analysis on the page) has other code than the 54; whether its
  MACD has the same fault was not checked. The rules themselves (what earns points) were not changed.
- Deployed with a packaged script to all 54 workers (one zip, the same `CodeSha256` on each: `NmXC9dcsA6p5…`) and the
  orchestrator (`Tyyx+Pb2l+sy…`). Rollback zips: `~/VSCODE/backup/stockiq-option-7-1-worker_before_macd_20261011.zip`
  (the same to all 54) and `stockiq-option-7-1-orchestrator_before_macd_20261011.zip`.

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
section is written from the code as deployed on the evening of 11 Oct 2026, and was swept in full then: the
function, the scripts and AWS were compared with it. **A new session starts at "Start here when resuming" near the
end of this section.** Verify against the code before relying on a detail (section 10).

### What the owner sees on the dashboard

The dashboard was one long page until the owner asked for it to be tidied (10 Oct). It now has
**three tabs** under the heading: 📈 Reports, 💵 Practice portfolio, 🤖 AI autopilot. One panel is
shown at a time; the choice is remembered in the browser (`localStorage` key
`stockiqDashboardTab`) and kept in the address (`dashboard.html#practice`, `#autopilot`), so a
refresh or a link lands on the same tab; any other address (`#upgrade`) opens Reports. Every signed-in account has all three tabs; without a paid plan the AI autopilot tab shows what it is and a button to the plans (its tab carries a 🔒). The markup is `data-dash-tab` buttons and `data-dash-panel` blocks, with a small inline
script between the `DASH_TABS_SCRIPT_START/END` comments in `dashboard.html`
(`window.dashboardTabs.show(name)` switches from code). Report code keeps working while its panel
is hidden. **Keep the Reports panel first in the page**: one report routine finds "Recent Reports"
with `document.querySelector('h3')`.

**Practice portfolio** (its own tab, container `#practice-portfolio`):
- Four cards: Account value (the cash plus every holding at its latest price; under it the change
  since the start, split into what has been sold and what is still held), Practice cash left, In
  holdings, and "For comparison" (the same money in an S&P 500 index fund instead; it says "no change
  yet" while the US stock market has not traded since the buys, e.g. a weekend: `marketFlat`).
  **Nothing is shown until the latest prices are in** (4 seconds at most): before 10 Oct the page
  first showed holdings at what was paid, which the owner took for a second, "correct" account value.
- **A result is an arrow and an amount**, as a broker's screen shows it: `▲ $801.50 (0.80%)` in green, `▼ $58.48 (0.06%)`
  in red, `– $0.00` in grey (`movedHtml`, `pctHtml` in `practice-portfolio.js`; `deltaHtml` in `practice-autopilot.js`).
  The words stay as each arrow's `aria-label` for screen readers, and `moved()` gives the words ("down $58.48") for the
  AI chat's summary. History: the owner could not make sense of bare signed figures ("Of the -$58.48 since the start: your
  own buys +$144.12…"), so they became words, and then at his request arrows ("look like a professional stock
  portfolio"). **Never a bare signed figure without an arrow.**
- One framed row, **whose result is whose**: "Your own buys ▲ $793.59 · 🤖 AI autopilot ▲ $7.91 sold ▲ $7.91 · still held
  – $0.00" (`splitGain`; shown once the autopilot has bought anything; the two add up to the account's change).
- The cards have small capital labels and a green or red top edge on Account value; table headings are small capitals,
  rows highlight under the pointer, figures use tabular numerals.
- The notification bell in the page header lists the autopilot's buys and sells with the reports: its own part below,
  "The notification bell".
- The buy row: search box (code or company name, same lookup as the home page), "Enter $" **or**
  "or quantity" (the other is worked out from the latest price), an optional note, "Practice buy".
- The holdings table: Holding, Bought (date and time), Price then, Price now, Value, Change, Sell.
  Under each name a line says whose it is: "Bought by you: it stays until you sell it", or for the
  autopilot's, when it will sell at the latest, at what loss or gain sooner, how the stop that
  follows it works, and, while its market is closed, that nothing happens to it until the market
  opens, with the time.
- "Sold (N)" folded list with a summary, "Clear sold list" and an × per line (clearing only tidies
  the list: what a sale brought in is already in the cash). "Refresh prices", "Reset fake money".

**AI autopilot (Beta)** (its own tab, container `#practice-autopilot`; every logged-in account sees the tab, accounts without a paid plan see the locked view). **It is labelled Beta wherever it is named to users** (the owner, 11 Oct: "more professional, as in under testing"): the panel heading (`ap-beta` badge), the dashboard tab ("🤖 AI autopilot (Beta)", also set by `markTab`), the plan cards, the home page pricing and the FAQ, each time with "new, and still being tested and changed". Keep the label when adding text about it. The
on/off switch, the status box (what it holds, last and next check-in, and **a live countdown to the
next check-in**), a **"Needs you"** line (green "Nothing needs you right now", or an amber box
listing what only the owner can put right) and the buttons "Check in now" / "Sell everything it
holds" sit at the top; below them the panel is in **two parts, Activity and Settings**, so neither is a long scroll (it opens on Settings until it is switched on with a
screener, then on Activity; the part last looked at is remembered, `stockiqAutopilotPart`). Both
parts are always in the page and one is hidden, so settings are read and saved whichever is on
show. Settings holds the first five items below, Activity the last five:
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
- Screeners it buys from, grouped by market (all 15). Under each market with a ticked screener: a
  menu "Share of the budget" (automatic, or a step picked by hand), and under the card one line in
  words on how the budget is spread.
- **What it may do by itself**: three switches (sell early on the AI model's review, try changes
  to its own rules, email me its reviews). Under the email switch: what became of the last email
  ("accepted by the mail service", or "could not be sent" and why) and "Send me a test email".
- (At the top, beside the buttons: a line saying "Saving…" / "✓ Saved." / "Not saved: reason".
  There is no save button: every change saves itself.)
- **What happens next** (first under Activity, added 11 Oct): what is coming, soonest first, each
  with a countdown that ticks and its time: the next check-in and what it may do, the next release
  of the budget, the first check-in after each closed market opens, the latest each holding is
  kept; then what goes by the number of finished trades (its own review, the AI model's notes).
  A sentence under it says that reviews and trials happen by themselves and nothing has to be pushed.
- **How it is doing** (its folded "Breakdown" table was laid out afresh on 11 Oct after the owner could not tell a group heading from the rows under it: each heading is a band of its own (`ap-bd-head`), its rows are indented, and the "Against an index fund" column is shown only when it differs from the average for some group; styles are the `.ap-bd` rules): what it holds now and when each will be sold, with the AI model's latest
  review of it; the last 30 days in dollars and as a share of the budget; finished trades (up /
  down, average); a folded breakdown; notes the AI model wrote from the record.
- **Progress, 20 finished trades at a time** (added 11 Oct): a table with a row per batch of 20
  (trades, dates, how many ended up, average a trade, dollars, "better / worse / about the same"
  against the 20 before, and what it did about it), newest first, the batch still filling on top;
  what stood out in the last complete batch can be unfolded. Before the first 20 it says when the
  first report comes and what happens then.
- **Improving its own rules**: the rules in force, which are set by the owner, which it changed
  itself ("put it back"), the running trial ("Stop this trial") and earlier trials.
- **What it has done**: every buy, sell and check-in note, newest first; "Why, and the details" /
  "The plan for it" folded under each trade; "Refresh now"; a switch "Buys and sells only".

### The notification bell (one list, on every page)

Built on 11 Oct 2026 in several rounds; this is the state it ended in. The story of the rounds is in section 9.

- **What it shows.** The 🔔 in the page header opens one list headed "🔔 Notifications": the account's reports and the AI
  autopilot's buys and sells **together, newest first**, each line saying which it is ("📊 Report · time" / "🤖 AI
  autopilot (Beta) · name · time"); it ends with "View Dashboard". A trade reads "Sold at a profit: CFX-USD ▲ $12.79
  (1.0%)", "Sold at a loss: … ▼ …" or "Bought: … $1,250". Only real buys and sells, never check-in notes.
- **Unread and the red number.** Trades made since the bell was last opened are counted in the red number together with
  unseen reports; opening the bell clears the number, but a line stays marked unread (blue dot, bold, a coloured edge;
  the heading says "3 unread: 1 report, 2 autopilot buys and sells") until one is clicked. The first list a browser gets
  is not news. A click on a trade opens the autopilot tab's list "What it has done"; on a report it does what the page
  does with a report (`viewAnalysisFromNotification`), or goes to the dashboard.
- **Where.** Pages that open a list on the bell (dashboard, home page, analysis page, stock pages, login on a phone) show
  the one list. On the pages whose bell only goes to the dashboard (About, FAQ, the guides, legal pages) the red number
  shows and the click goes to the dashboard as before. Nothing is shown to a visitor who is not signed in.
- **One script draws it for every page: `website/autopilot-bell.js`** (`window.autopilotBell`: `version, set, trades,
  reports, unseen, unread, markSeen, markRead, html, place, open, report, badge, load, onTop, state`). Each page used to
  draw its own report list in its own code; the owner called that "a shit setup… would have been nice to have it all setup
  in one way". The script does not depend on how a page draws its bell: it listens for a click on `#notification-bell` /
  `#mobile-notification-bell`; if the page opened `#notification-dropdown` it empties it and puts the one list in
  (`#bell-list`, built by `html`, `reportRow`, `tradeRow`); it watches that list and draws it again when the page redraws
  its own; and it watches the two badge elements to add its count to whatever number the page sets. The page still
  opens, places and closes the list, and supplies the reports (`analysisHistory`) and what a click or "run again" does.
  If the script fails, the page's own list simply stays.
- **How it is loaded.** Signed-in visitors only. Each of the 17 hand-edited pages with a bell has one line after its
  `theme.js` tag, between the comments `AUTOPILOT_BELL_START/END`; `dashboard.html` has the same line near its other
  scripts; and `theme.js` asks for it too, which is what covers the generated stock pages. **The address is relative and
  has no version number**: `autopilot-bell.js?h=<the hour>` beside the page (`theme.js`: beside itself). **Never
  "/autopilot-bell.js"**: that exists only when the site is at the top of its address (section 9). Because the address
  changes every hour and browsers keep a script five minutes, **a change to the script needs no edit to any page**.
  Inside the script `SITE` is where it was loaded from; its links are built from that.
- **Where the trades come from.** On the dashboard the panel hands over its own list (`practiceAutopilot.bellFeed` →
  `autopilotBell.set`). On every other page the script asks the function's **read-only action `bell`** (`bell_trades`:
  the last 12 buys and sells with `t, type, symbol, name, usd, gain, pct`; it is not a visit and writes nothing; an
  account without the autopilot gets an empty list) at most every two minutes (30 for an account without it) and keeps
  the answer in the browser (`stockiqBellTrades_<address>`) so that every page and tab shows the same. A sale's dollars
  are the entry's `gain` (stored since 11 Oct) or are read from an older entry's words ("Put in $X, got back $Y");
  entries from before that have no name.
- **In the browser's store:** `stockiqBellTrades_`, `stockiqBellBell_` ("seen": clears the red number), `stockiqBellRead_`
  ("read": clears the unread marks); the reports' own keys `unreadReports_` and `seenReports_` belong to the pages.
- **It takes over from an older copy of itself** (`VERSION`, 8 at the sweep): a browser can run an older copy for a while
  after a change, and an older copy that ran first once shut the current one out. The current one always takes over,
  empties the store of the copies before version 4 (`stockiqAutopilotTrades_…`), marks its question to the function
  `list: 2` (**the function answers `bell` only then**), carries on its list the signature a version-3 copy expects
  (`olderSig`) so that copy leaves the list alone, and stops redrawing if something undoes the list more than 12 times in
  two seconds (`state()` says so, with any `fault` met while drawing). This part can be thinned out once no browser can
  still hold a copy from 11 Oct 2026 (a week is ample): keep the "newer version wins" guard.
- **Tests.** `node check-tools/autopilot_bell_test.js ../website/autopilot-bell.js` (22 checks); a stand-in page in a real
  browser: `python3 check-tools/bell_page.py ../website/autopilot-bell.js /tmp/bell.html light trade` (or `report`); and
  **the live pages as a real account**: `REAL_USER=<address> PASS_GET=1 SHOT=/tmp/bell.png node
  check-tools/live_bell_check.js dashboard.html index.html analysis.html` opens them in headless Chrome as that account,
  lets only its read-only questions through (everything else the page asks is answered locally, so nothing is written),
  and prints what the bell holds. Its other switches reproduce what a particular browser sees: `BASE_URL=` (the local copy
  served from a folder, as a local preview does), `OLD_THEME=` / `OLD_BELL=` (old copies played back), `NO_THEME=1`,
  `LOCAL_BELL=` (a staged copy tried on the live pages before deploying). Details in `check-tools/README.md`.
- **Limits:** a notice on the site, not an email or a phone notification. The 14 pages whose bell goes to the dashboard
  have no list of their own. Not checked on a phone.

### Files and services

| Thing | Where | Notes |
|---|---|---|
| Portfolio section | `website/practice-portfolio.js` (`?v=18` in `dashboard.html`) | Sums and page. Pure functions exported for tests: `newState, fxFor, fxRate, versusMarket, applyBuy, applySell, applyClearSold, soldSummary, valueOf, summarize, splitGain, planLine` |
| Autopilot panel | `website/practice-autopilot.js` (`?v=38`) | Controls and reports only; decisions are made by the Lambda |
| The bell (one list for every page) | `website/autopilot-bell.js` (asked for as `?h=<the hour>`, no version to raise; fetched by each hand-edited page with a bell, by `dashboard.html`, and by `theme.js` for the stock pages) | The autopilot's buys and sells in the notification bell |
| Page | `website/dashboard.html` | The tab bar, the three panels with the two containers in the second and third, the tab script before the footer, and the two script tags at the end. **Raise `?v=N` whenever a script changes** (since 11 Oct browsers keep a script only five minutes, so this is a belt on top of that, not the only way a change arrives) |
| Portfolio storage | Lambda `stockiq-paper-portfolio` (128 MB, 10 s), table `stockiq-paper-portfolios` | Actions `get`, `save` (with `expectedVersion`), `reset`. One item per user: `data` (JSON), `version` |
| Autopilot | Lambda `stockiq-ai-trader` (Python 3.12, 512 MB, 300 s, role `acp-lambda-role`), table `stockiq-ai-trader` | Actions `get`, `save`, `run`, `sellall`, `tune`, `mailtest`, `bell` (read-only, for the notification bell; `belllog` is answered and ignored, a leftover). Env `AI_TRADER_USERS` (accounts that may use it without a paid plan; everyone on a paid plan may use it; `*` would make it free for all) and `OPENAI_API_KEY` (never print it) |
| Schedule | EventBridge `stockiq-ai-trader-schedule`, `cron(10,40 * * * ? *)` | Every 30 minutes; `SLOT_MINUTES` in the Lambda must match. **Disable this rule to stop everything** |
| Screener data | `stockiq-screener-coordinator` | Called with no `userId`, so nothing is saved to anyone's history |
| Prices | `stockiq-price-proxy` | Also exchange rates (`AUDUSD=X`, `USDJPY=X`) and the S&P 500 fund (`SPY`) |
| Headlines | Google News RSS (coins), Yahoo Finance RSS (shares) | Fetched by the Lambda; the AI model has no internet |
| AI model | OpenAI `gpt-4o-mini`, JSON replies; `gpt-4o` for the holdings review when a gain is at stake | Three uses: choose buys, review holdings, write notes. `aws lambda invoke … --payload '{"model_test": true}'` asks each one question and says which answered |
| Email | SES, from `autopilot@stockiq.tech` to the account's own address | The role has SES access; the owner's address is a verified identity (SES is still in sandbox) |

The Function URLs are written into the scripts. As everywhere on this site the `userId` is whatever the browser
sends. The autopilot acts for accounts on a paid plan and for the accounts listed in `AI_TRADER_USERS` (`allowed`).

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
- **A trading cost is taken off every practice buy and every sale** (since 11 Oct 2026, evening): `TRADE_COST_PCT` 0.1 in
  `practice-portfolio.js` (by hand) and `TRADE_COST` 0.1 in the function (the autopilot); **keep the two the same**. The
  whole amount leaves the cash and a thousandth of it is the cost, so a holding starts a little below what was put in
  (`qty = amount × 0.999 / price`); a sale brings back `qty × price × 0.999`. No new field: the cost is inside `qty` and
  `proceedsUsd`, so every sum works as before. Holdings bought earlier have no buying cost in them. The line under the
  buttons says so. Reason: a record without costs flatters itself, most of all when trading often (section 7b).
- **Owner's decisions:** buying, selling and progress stay on the dashboard (no buy buttons on stock
  pages or reports). The S&P 500 columns and "N of M ahead" sentences were removed at his request;
  only the "For comparison" card remains. `spyAtBuy` / `spyAtSell` are still stored, because the
  autopilot's record uses them. Wording stays "practice", "fake money, no real trades".

### The autopilot: settings (table `stockiq-ai-trader`, cleaned by `clean_settings`)

| Setting | Values | Meaning |
|---|---|---|
| `enabled` | on / off (default off) | Only for accounts on a paid plan, or listed in `AI_TRADER_USERS` (`allowed`) |
| `risk` | 1–5 (default 3) | The level: see the table below |
| `budgetUsd` | 100 … the practice money there is (default 10,000) | The most it has invested at once. **It cannot be more than the practice cash plus what the autopilot itself has invested** (`money_of`, sent as `money`: `cash, invested, reach`). On 11 Oct the owner typed $200,000 against $100,000 of fake money and nothing objected; it would have bought one $50,000 holding and stalled. Now the panel says under the field how much there is (`budgetHint`), refuses a larger number ("Not saved: the budget can be at most …"), offers "Set it to $…" (`maxbudget`), and the `save` action sets a larger one to that amount and notes it (the backstop for an older cached script). An older, too-large budget does not block other settings from saving. **And a budget that is too large is put right wherever it is met** (`fit_budget`: when the page is opened (`get`), when settings are saved, at the start of every check-in), with the same line in the activity list: the owner had asked twice why $200,000 was still shown, because his saved figure predated the check. So the "Needs you" item `budget` should now never appear |
| `periodDays` | 1–90 | "Build up to it over": the budget is released in equal steps over this long. **Not the holding time** (the owner mixed them up twice) |
| `everyHours` | 0.5, 1, 3, 6, 12, 24 | How often it checks in |
| `maxHoldDays` | 0.5 h … 60 days, stored in days | The longest it keeps a holding |
| `auto` | any of `periodDays`, `everyHours`, `maxHoldDays` | **Which of those three are left to the risk level.** For a listed one `clean_settings` puts in the level's own value (`PACE`) every time, so the rest of the code only ever sees numbers. A new user leaves all three; settings saved before 10 Oct evening have none (all set by hand) |
| `screeners` | any of the 15 keys (default none) | Coordinator keys: `3-8 3-100 3-7 3-3 3-2 3-4 3-5 3-6 4-50 4-100 4-200 4-300 5-ftse100 5-nikkei225 7-1` |
| `aiSell`, `selfTune`, `emails` | on unless switched off | "What it may do by itself" |
| `stopPct`, `takePct` | empty, or 1.5–30 and 2–80 | The owner's own loss limit and gain mark, as sizes in percent |
| `shares` | `{market: percent}`, only for markets set by hand (default none) | A market's share of the budget. Markets are the groups of `SCREENERS` (`GROUPS`: US shares, Australian shares, UK shares, Japanese shares, Coins). A market left out is automatic. Together at most 100 (`clean_settings` takes the excess off the later ones). See "How the budget is spread" below |
| `trailMode` | `gains` (default), `full`, `off` | The kind of stop that follows a holding. `gains`: it starts once the holding has risen beyond its normal wobble. `full`: a full trailing stop loss, under the price from the moment of buying, so a faller is cut early (exit kind `cut`). `off`: none |

| Level | Holdings | Buys from the top | RSI under | 30-day move within | Loss limit | Gain mark | Coins at most, on automatic with a share market ticked too |
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
- **How the budget is spread over the markets ticked** (11 Oct; the owner asked whether ticking
  several screeners spreads the money evenly, and proposed a share per market with an override).
  It did not: only coins had a limit, so whichever share market opened first could take the rest
  (with US and Australian screeners ticked, Sydney opens 14 hours before New York). Now:
  - `market_split(settings)`: each ticked market's share as a fraction. A share set by hand
    (`settings.shares`) stands. What is left is spread **evenly** over the other ticked markets,
    except that **coins never get more than the level's share** (last column of the table) while a
    share market is ticked too. One market ticked: all of it, coins included.
  - `market_slots(settings)`: the split in **whole holdings** of the level (each holding is the
    budget over the level's number of holdings), fractions to the largest remainders, a tie to the
    market listed first. Balanced with US, Australian and coin screeners: 3 / 3 / 2 of 8.
    Adventurous: 2 / 1 / 1 of 4. Several screeners of one market count as that one market.
  - At a check-in each market's room is its holdings times the holding size, less what it already
    holds there (`group_room`); a market with no room is not offered, the AI model is told a
    market's limit, `choose(..., limits)` passes over picks beyond it and fills from the others by
    rank, and no buy is larger than its market's room. Holdings from a market that is no longer
    ticked stay until sold and still count against the budget, not against any market.
  - `coin_share(settings)` is now the coin market's holdings over all (it was the level's figure).
  - **Layout of the card (redone 11 Oct, v34):** the owner "didn't even see the dropdown boxes for
    a while", and took the absence of a menu under UK and Japan (nothing ticked there) for a fault.
    Now: one line saying what to do; a coloured bar (`splitBar`, `#ap-splitbar`) with one part per
    market as wide as its share, and a grey "cash" part when shares set by hand leave some out; each
    market is a row of three columns (`ap-group shared`): name with its colour dot, the screener
    chips, and its share in an outlined box of its own on the right (`ap-share`, in the market's
    colour, `MARKET_COLOURS`); a market with nothing ticked says "No share of the budget: nothing
    is ticked in this market". Under 980px the share box drops below the chips.
  - The panel shows it: a menu per ticked market, "Automatic: 38% (3 holdings, $18,750)" or one of
    the steps (0 to all holdings, each with its percent and dollars), tagged "automatic" / "set by
    you" (`shareRow`), and a line in words (`splitText`) that also says when a market gets nothing
    and why, and when shares set by hand leave part of the budget in cash. Shares adding up to more
    than 100% are not saved ("Not saved: the shares you picked add up to 125%…"). **A share is
    picked from steps, not typed, so nothing impossible can be entered**; "5% in UK" at Balanced
    is not possible (one holding is 12.5%): choose a level with more holdings for finer steps.
  - `marketSplit` / `marketSlots` in `practice-autopilot.js` are **a copy of the Lambda's two
    functions** (between `MARKET_SPLIT_START/END`): `autopilot_plan_check.py` compares them for
    2,915 combinations of level, markets and hand-set shares. Change one, change the other.
  - Within a market the choice among its screeners is as before: by place in each screener's own
    ranking, then the AI model's pick. There is no per-screener share.
- The rules in force for a user are `rules_for(settings, state)`: the level, then what the
  autopilot changed itself for that level (`state.tune.values`), then the owner's own limits.
- A screener belongs to a market and is only traded while that market is open (`MARKET_HOURS`,
  UTC, Mon–Fri: US 14:35–19:55, Australia 00:05–04:55, Japan 00:05–05:55, UK 08:05–15:25; coins
  always). Each market keeps its own last-checked time, so a user with US and Australian screeners
  is checked in both sessions. **The markets of what it still holds count too** (`its_markets`):
  on 10 Oct the owner un-ticked the crypto screener while it held a coin, and because only the
  ticked screeners' markets were looked at, the coin was left unattended (no time limit, no stop)
  until that was fixed the same afternoon.
- **Trading hours hold by hand too** (11 Oct; the owner: "no point it buying something when the
  market isn't open… making it unrealistic"). "Check in now" (10-minute gap between presses) and
  "Sell everything it holds" trade only in markets that are open: a closed market's last price is
  not one anybody could trade at. A closed market is named in the answer and in the activity list
  with when it opens (`opens_in`); "Sell everything" keeps the holdings of a closed market and lists
  them (`summary.closed`). A longest-holding time that ends while the holding's market is closed is
  acted on at the next opening, and the dashboard is given that time (`when_open`). Before this, a
  Nikkei share (4307.T) was bought on a Saturday at Friday's closing price.
  **Limits:** the hours are fixed windows a little inside the real sessions; public holidays and
  Tokyo's lunch break are not known, so on such a day a share can still be traded at its last price.
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
   - **Wording rule (11 Oct): the point where the stop starts must never read like a selling
     price.** The first wording ("sooner at -10% or +18%; once it has been up 4.5%, sell if it
     slips back far enough…") was read by the owner as "it sells at +4.6%, so how would it get to
     +18%?". Every place now says the same three things in this order: rising is not a reason to
     sell (while it rises it is kept); once it has been up that much a stop starts following it;
     it is sold only if it then falls back. Places: the plan under a buy, the story under a sale,
     `planLine` on the portfolio, "Holding now", and the line under the Trailing stop menu
     (`TRAILS`). Keep them in step.
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
   It releases as many steps as one more holding takes (with hourly steps and 4 large holdings
   that is several; until 11 Oct it gave up after as many steps as the level has holdings).
   If the early release buys nothing after all (nothing fit to buy, its market closed), it is taken
   back, so pressing the button again and again cannot use up the build-up. Nor can it overshoot:
   each press releases one more step at most, never past the budget, the practice cash, the
   level's number of holdings or the coin share.
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
   budget, with when), `full`, `cash`, `share` (the markets that are open already hold their share of the budget; it was `coins`), `shut` (by hand: "Nothing
   to do: none of its markets is open."), `none`, `nodata`, `same`.
   The same note at the next check-in is counted on that line, not added again (`add_log`).
10. The portfolio is saved with a version check. If the owner changed it at the same moment,
    nothing is traded and it tries again next time.
11. `settle` again, then `review_resting`, `write_lessons`, `review_tuning`.

### Headlines

`fetch_news` (holdings) and `candidate_news` (the shortlist): Google News RSS search for coins,
Yahoo Finance RSS by symbol for shares (a share's company name comes from its quote).
`pick_headlines` keeps at most three, under 72 hours old, that **name the holding** (its code or
the first real word of its name) and drops price, forecast and converter pages (`NEWS_JUNK`; the
first real headline to reach the model, at 15:10 UTC on 10 Oct, was a "price forecast" page).
**A coin's headline must be about the coin.** A coin's ticker is often also a company or a word:
on 10 Oct the model was shown share news about ERG S.p.A. (an Italian energy company, "ERG
(BIT:ERG) Stock Could Be Trading At A Premium…") as headlines for the Ergo coin. For a coin a
headline now counts only if it names the coin by its own name ("Ergo"; taken from its quote, also
for candidates), or by its ticker beside a crypto word (`COIN_WORDS`), or the ticker has five
letters or more; and never if it reads like share news (`SHARE_NEWS`: an exchange code in
brackets, "stock", "shares", "dividend", "earnings"). Share headlines are not touched by this. Kept two hours
(`state.news`, `state.seen`). Headlines are untrusted text: both prompts say so, and the model's
answer can only pick from a list or say hold / sell. Small coins usually have none; then it is the
figures alone. Only the deployed function fetches (`AWS_LAMBDA_FUNCTION_NAME`); a test run never
calls out.

### Learning from its own results

**Since 11 Oct 2026 these reviews run once, on every account's finished trades together** (next part, "Learning is shared
by every account"); an account's own check-in no longer runs them. What each review does is described here and is the
same code; read "its record" below as the shared record, or the shared record at the account's risk level.

- **The record.** Each finished trade goes into `history` (last 300): what it was bought on (rank,
  score, RSI, 7- and 30-day change, volume, who chose), result in percent and dollars, the S&P 500
  fund over the same time (`market`, `vs`), how long it was held, how it was sold (`exit`: `stop`,
  `take`, `trail`, `cut`, `time`, `signal`, `fade`, `ai`, `hand`), its best and worst while held, and,
  filled in later by `look_back`, **what it did after it was sold** (`after`: the further change
  once the same length of time had passed again).
- **Scorecard** (`scorecard`): overall and by screener, rank band, RSI band, who chose, exit, how long it had stayed, and, for shares, **how far above its 52-week low it was when bought** (`above` on the remembered buy, from the screener row's `from_low`; added 11 Oct after the factor study of section 7b, as a measurement and not a rule).
  Shown as "How it is doing" and given to the model at each decision (`memory_text`).
- **Resting a screener** (`review_resting`): when its last 12 trades (at least 8) average 1.5% or
  more behind the S&P 500 fund, it is rested 14 days, then tried again with a clean slate. **A coin
  screener is judged on its own results** (an average loss of 1.5% or more), not against the fund:
  the share market says nothing about a coin and is shut at weekends.
- **After costs.** A trading cost is taken off every buy and sale (above). A finished trade made that way carries `c`; the
  month's figures (`month_figures`, `afterCosts`) and the bar charge the same 0.1% each way (`COST_EACH_WAY`) only to
  trades without it, and the panel says when a figure includes such older trades.
- **The bar its record has to clear** (`bar_of`, `BAR_TRADES` 300; sent as `bar`: `need, n, avg, margin, met, shared`; on the
  panel as an amber-edged box at the top of "How it is doing", `barHtml`). Set down on 11 Oct 2026, before the results are
  in, so that a lucky run cannot be talked into a success: **300 finished trades whose average result, after trading
  costs, is ahead of the yardstick by more than twice the margin of error; the yardstick is an S&P 500 index fund over
  the same days for a share and zero for a coin.** It is measured on the shared record (every account). At the sweep: 4
  of 300, averaging -0.68 against the yardstick. Until it is cleared no result here is evidence of anything, and it must
  be cleared before real money is even discussed (and then discussed with a licensed adviser: section 11, "Legal").
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
- **Progress, a batch at a time, and what it does when a batch is no better** (11 Oct; the owner:
  "if its doing well it continues improving as it is, if its doing worse or the same it needs
  investigating and fixing, ideally i'd prefer AI actively do this").
  - `batches(record)`: the finished trades in batches of `TUNE_BATCH` (20), numbered from the first
    trade ever (`closedCount` keeps counting when old trades drop off the 300 remembered; a batch
    cut off that way is left out). Per batch: `no, first, last, n, full, from, to, up, avg, usd,
    se`, and for a complete batch after the first `prev, diff, margin, verdict`: **better / worse /
    same, where "same" means the difference is inside the margin of error of the two averages**.
  - `review_progress(record, now, model, mail)` runs in `run_user` just before `review_tuning`,
    once per completed batch (`state.progress.done`). It writes a report (`state.progress.reports`,
    last 15: `no, at, trades, avg, usd, up, n, verdict, prev, findings, actions`), a line in the
    activity list ("Progress after 40 finished trades: …") and an email.
  - **Better (or a first batch that is up): "It carries on as it is."** The ordinary review of
    its rules (`review_tuning`) still runs on its own count.
  - **Worse, the same, or a first batch that is not up:** (1) `batch_findings` says what stands out
    in the batch's own figures (the kinds of sale and the screeners that did worst and best, what
    holdings did after they were sold); (2) if the verdict is "worse" and a change of its own was
    kept before this batch began, **that change is put back** (`undone` on the past trial);
    (3) unless a trial is already running, it starts **a trial of the most promising change to one
    of its five rules, with a lower bar than usual** (`propose(..., least=0.05)` instead of
    `TUNE_MIN_GAIN` 0.2), and **the AI model picks which** from up to four numbered candidates (it
    cannot invent one; an answer off the list is ignored and the first candidate is used);
    (4) `tune.mark` is set, so the ordinary review does not start a second change. With "Try
    changes to its own rules" off it reports and changes nothing. The trial still decides whether
    a change is kept, so nothing is adopted on hindsight.
  - What it cannot do stays the same: only the five rules in `TUNABLE`, inside their bounds. When
    nothing in them stands out it says so and points at the settings only the owner can change.
  - The panel's table is `progressHtml` (`data.progress`: `batch, batches, reports`).
- **Its own trial of which share to buy** (11 Oct, after the owner said the study had produced no
  improvement "to increase profit": he was right, it had only been measured). The factor study
  (section 7b) found no link between a screener's ranking and what shares did next, and a modest one
  for how far a share stands above its 52-week low. So the autopilot tests that itself:
  - `order_of(state, settings, now)`: `state.order` = `{mode, since, buys, ended, result, kept,
    undone}`; mode `trial` (running), `low52` (kept), `rank` (not kept, stopped, or put back). **It
    starts by itself at the first share buy** when "Try changes to its own rules" is on; never
    with that off.
  - `apply_order(order, picks, candidates)` runs straight after `choose`: on trial, **every second
    share pick is swapped for the share furthest above its 52-week low** (`from_low`) among the
    candidates of the same market (so the market shares still hold); once kept, every share pick
    is. Each share buy is tagged (`o`: `low52` or `rank` on the remembered buy; `chosen: 'order'`
    for a swapped one, shown in the record as "bought furthest above its 52-week low"). Coins are
    never touched: they have no such figure.
  - `review_order` judges it at check-ins: after `TUNE_GROUP` (10) finished each way, the new order
    is kept only if its average beat the other by more than the margin of error; otherwise shares
    go on being bought as ranked. It gives up unchanged after `ORDER_GIVE_UP_DAYS` (90), and ends
    when its trials are switched off. A note and an email either way.
  - The owner can stop it or put a kept order back: `tune` action with `op: 'stoporder'` /
    `'restoreorder'`. The page gets `order` (`mode, since, ended, result, kept, undone, group, why,
    with, without, avgWith, avgWithout`).
  - On the panel under "Improving its own rules": **"Improvements so far: N being tried now, N kept
    after a trial, N put back, N tried in all"** (`improvedLine`), and the trial itself
    (`orderHtml`: "Next, for shares…" before it has started, "Also trying, for shares…" with the
    two sides' figures and "Stop this trial", then kept with "put it back", or not kept).
  - Honest limits: ten trades a side is little; the study's edge was modest, from one rising
    market and today's index members. That is why it is a trial and not a rule.
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
that it at least does not fool itself. The owner's later aim, "70% profit, 30% loss", needs the
same care: section 7b shows that share of winning trades comes from the selling rule (any stock
"wins" 74% of the time under a sell-at-+2% rule) and is not profit. Judge it by dollars and by
the average per trade, which the panel shows, never by the share of trades that ended up.

### Learning is shared by every account (11 Oct 2026, the last change of the session)

The owner: "it should be learning regardless of the user that runs something. so the more users… the smarter it gets. I
think the way you have done it is its going from scratch on each new user… It should be a smart AI that is learning in a
central location for all users". He was right about how it was built: every account kept its own record, trials and notes.
Now there is **one shared record**, and what follows replaces the per-account learning described under "Learning from its
own results" (those routines are the same; they now run once, on everyone's trades).

- **Where:** item `_brain` in table `stockiq-ai-trader` (one compressed attribute `z`; `load_brain`, `save_brain`,
  `new_brain`): `pool` (finished trades of every account, newest last, at most `POOL_KEEP` 3,000), `count` (all ever
  taken in), `counts` per risk level, `accounts` (8-character scrambled ids, only to count them), `state` (`rest`,
  `restSince`, `lessons`, `order`), `tunes` and `progress` per risk level (the same shapes an account's `state.tune` and
  `state.progress` had), `news` (the last 30 notes, numbered by `seq`). Switch: `CENTRAL = True` in the function.
- **What goes in, and privacy:** when an account's record is saved (`save_item` → `share_trades`), its finished trades that
  have not been sent yet are queued as one small item `_pool#<time>#<id>#<random>`: the figures it was bought on, the
  result, how it was sold, the level (`POOL_FIELDS`). **No address and no holding id**; a scrambled key (`k`) only stops
  a trade being counted twice. Sent rows are marked on the account's own history (`p`: 1 sent, 2 sent with what it did
  after it was sold; that later figure is sent on as `{k, after}`). The codes of the shares and coins are in it; nothing
  about who traded them.
- **The scheduled run, before the check-ins** (single writer, so accounts running side by side never write it):
  `gather` folds the queue into the pool and deletes the queue items once the record is saved; `think` reviews once for
  everyone: `review_resting` (a screener whose pooled trades lag is rested for every account), `write_lessons` (notes
  from every account's trades, every 5 more), `order_of` / `review_order` (the trial of which share to buy, over every
  account's share buys), and per risk level, through `mind_of(brain, level)` (the shared record seen as one account at
  that level), `review_progress` and `review_tuning`. Notes it produces go to `news` (`tell_all`), prefixed "Learned from
  every account…". If any of this fails the log says "shared learning failed" and the accounts work from the record as
  last saved.
- **What an account takes over** (`adopt`, at the start of every check-in and when the page is drawn): the rules changed
  after a trial and the running trial for its level, the trial of the buying order, the rested screeners and the notes.
  Which of its own buys follow a rule on trial is still counted per account (`buys`). New notes go into its activity list
  and one email ("what it has learned from every account"); an account that is new gets no backlog. **With "Try changes
  to its own rules" off, an account keeps the level's plain rules and takes no part in trials** (rests and notes still
  apply). In a check-in the per-account reviews no longer run (`solo` is false).
- **The AI model is shown both** when it chooses what to buy: this account's own finished trades, and every account's
  together (a summary of the latest `POOL_CARD` 600) with the shared notes.
- **Who can undo what is shared:** "put it back" and "Stop this trial" act on the shared record, for everyone, and only
  for the site's own accounts (`listed`, env `AI_TRADER_USERS`); any other account is answered HTTP 403 and pointed to
  its own switch, and the panel does not show those links to it (`central.canChange`).
- **What the page gets:** `central` = `{trades, accounts, level, on, canChange}`; `progress` and the figures of a trial
  are those of every account at the user's level (`progress.shared`); "How it is doing" stays the account's own record.
  The panel says so in a framed box at the top of "Improving its own rules" (`sharedHtml`). The chat's summary has a line.
- **Fixed on the way:** the schedule's table scan took only the first megabyte (the stored screener results are large, so
  with more accounts some would have been skipped without a word): it now pages through the table. Notes are refreshed by
  the count of trades ever finished, not by the length of a list that stops growing.
- **Does it need another AWS service or "machine learning"? No, and not yet** (the owner asked). What limits it is the
  number of finished trades and how little the screener figures have predicted so far (section 7b), not the tools: a
  statistical model fitted to a few dozen trades learns noise. The shared record is what any such model would be trained
  on, and it is being collected from now. When it holds some thousands of trades, the next step is a small model (a
  logistic regression or boosted trees on the bought-on figures, fitted inside this same function or a second small
  one, no SageMaker needed) that scores a candidate, tried the same way as every other change: beside the current rule,
  kept only if clearly better. The OpenAI model stays what it is: it weighs the figures and headlines of one decision; it
  does not learn from the record except through the summary and notes it is shown.
- **More that it could change** (the owner: "the more changes it can make the better"): still the five rules of `TUNABLE`
  and the buying order. Candidates once the pool has the trades to judge them: the automatic pace of each level (holding
  time, check-in gap), the stop's distances (`STOP_ARM`, `STOP_ROOM`), the wait for a coin to stay, per-screener ranking
  depth. Each needs a tag on the buy and a trial; none should be adopted from hindsight.
- **Limits, said plainly:** on 11 Oct there was one paying account with four finished trades, so today the shared record
  is that one account; the gain comes with accounts. Accounts at different risk levels pool separately for the rule
  trials (a level's rules differ), together for rests, notes and the buying order. A site account's "put it back" and the
  schedule could write the record in the same second (not guarded; the schedule runs at :10 and :40). The deploy's own
  check created a record for the deploy test account (switched off; harmless).
- **Tests:** the last part of `ai_trader_test.py` (17 checks) runs with `CENTRAL` on; the rest set it off at the top so
  that each review is tested on one record. `dashboard_page.py`'s stand-in says learning is shared.
- **Seen for real (09:10 UTC, 11 Oct):** the scheduled run logged "shared learning: 4 new finished trades, 4 in all from 1
  accounts, 0 notes": the owner's four trades are in the shared record and the queue is empty again.
  **Not yet seen for real:** a shared note reaching an activity list (the first comes with the first review, at 20
  finished trades at a level, or the first notes at 5 more trades), and the bell on the logged-in pages.
- The AI chat knows: its `DASHBOARD_GUIDE` says that learning is shared, and the page's summary gives it the numbers.
- Rollback zip: `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_central_20261011.zip`. The older function ignores
  `_brain` and `_pool#` items, as it does the stored screener results.

### The AI chat on the dashboard (added 11 Oct 2026)

The owner noticed the chat was on every page but the dashboard, and wanted it to "know everything"
there. Setting things up for the user by chat was judged too much for now and is not built.
- `dashboard.html` loads `ai-chat.js?v=2` (the other pages still load it without a version).
- **What the chat is told on the dashboard** (Lambda `stockiq-ai-chat`, `page: 'dashboard'`):
  `DASHBOARD_GUIDE`, a fixed description of the three tabs, every autopilot setting and every part
  of its Activity view; and **a summary of what this user's own dashboard shows**, built in the
  browser: `practicePortfolio.summary()` (account value, the user's holdings, the autopilot's
  holdings) and `practiceAutopilot.summary()` (on or off, level, budget, pace, screeners and the
  spread over markets, switches, next check-in, what is coming, "Needs you", holdings, results,
  trials, the last three entries), sent as `pageContext.dashboard`, cut to 2,500 characters and
  stripped of control characters. It is marked in the prompt as data from the user's browser,
  never instructions. Away from the dashboard the chat only knows that the practice portfolio is
  free and the AI autopilot (Beta) is in the paid plans.
- **Rules added to the prompt** (the no-advice rule stands): it cannot change anything for the
  user; it never says which settings, screeners or holdings will make money; it keeps to what the
  figures say and adds no steps, amounts or times; no "opportunities", "picks" or "recommend";
  results are "practice results with fake money". Replies on the dashboard may be a little longer
  (400 tokens instead of 300).
- **The risk-level numbers in `DASHBOARD_GUIDE` are a copy of `RISK` in `stockiq-ai-trader`**
  (holdings, loss limit, gain mark per level): `check-tools/ai_chat_test.py` compares them. They
  were added after the model told a test question that Cautious means "fewer" holdings.
- Test: `python3 check-tools/ai_chat_test.py lambda-sync/stockiq-ai-chat/lambda_function.py` (16
  checks; stand-ins for the database and the AI model). The guide was brought up to date in the evening sweep of 11 Oct
  (results as arrows, the bell's one list, a release of the budget listed at its check-in, learning shared by every
  account). Tried live with real questions on 11 Oct:
  it answered from the figures, pointed to the right controls, and declined "which settings will
  make the most money" and "should I switch to Cautious". It is still a small model: read a few
  answers after any change to the guide.
- When a dashboard feature changes, **update `DASHBOARD_GUIDE` and the two `summary()` functions**,
  or the chat will describe the old dashboard.
- Cost: about 1,600 tokens a dashboard question instead of 650 elsewhere, roughly $0.0003 each.
- Rollback zips: `~/VSCODE/backup/stockiq-ai-chat_before_dashboard_20261011.zip`, `…_wording_…`, `…_levels_…`, `…_before_sweep_…`.

### What the Lambda keeps per user, and what it sends the page

- The record: `settings`; `log` (last 80: `t, type` buy / sell / note, `symbol, usd, text`, and
  where relevant `kind, pct, detail[], key, n, first`); `history`; `state` with `startedAt`
  (when the budget's build-up began; reset when it is switched on or the budget or build-up
  changes), `lastRun`, `lastRunBy`, `open` (remembered buys), `exits`, `rest`, `restSince`,
  `lessons`, `tune` (`values`, `trial`, `past`, `mark`, `seq`, `reviewed`), `watch`, `news`, `seen`, `stay`,
  `strong`, `ahead`, `aiSell`, `closedCount`, `realizedUsd`, `progress` (`done`: batches reported, `reports`), `order` (the trial of which share to buy), `visit`, `pausedAt`, `pausedWhy`, `ai` (today's AI calls), `mail` (what became of the last email:
  `t, ok, subject, why`), `fail` (a scheduled check-in that stopped on an error; cleared by the next
  good one), `savedAt` (when the settings last changed).
- `public()` (every action returns it): `settings, state, log, scorecard, lessons, resting, recent,
  minSample, practiceCash, rules` (in force, with `yours`, `level`, `changed`, `arm`), `tune`
  (`trial` with its figures, `past`, `nextReviewIn`, `batch`, `group`), `aiSellPausedUntil`,
  `coinShare, realizedUsd, month` (`last30`, `before30`), `now, nextCheck, holding, plans` (per
  holding: `sellBy` (the end of its holding time, moved on to its market's next opening), `market,
  closed, opens, stop, take, arm, floor, move, room, tight, mode, trail, peak, trial, view, auto`) and `options` (screeners,
  check-in and holding-time choices, the level table, `groups`); `split` (per ticked market: `group, holdings, pct, usd, own`); `money`; `progress` (`batch, batches, reports`); `order`; and `coming`, `needs`, `mail`, `reviewed` (next section). **The panel is drawn from these; change the
  two together.**
- Other actions: `mailtest` (one test email to the account's own address, at most every 10 minutes), `sellall` (`sell_everything`: only the autopilot's holdings, recorded as sold by
  the owner; holdings of a closed market are kept; its `summary` has `sold`, `skipped`, `closed`) and `tune` (`tune_by_hand`: `op: 'restore', param` puts one rule back to the level's;
  `op: 'stop'` ends the running trial; `op: 'stoporder'` / `'restoreorder'` stop the trial of the buying order or put a kept order back; nothing else can be touched).

- **Added with the shared learning and the bell (11 Oct, evening):** a finished trade in `history` carries `p` once it has
  been sent to the shared record (1 sent, 2 sent with what it did afterwards); `state.brainSeen` is the number of the last
  shared note the account has had; what `adopt` takes over sits in `state.tune`, `state.order`, `state.rest`,
  `state.restSince` and `state.lessons` as before, but is now a copy of the shared record's. A buy or sell entry in `log`
  carries `name`, and a sell its `gain` in dollars. `public()` adds `central` (`trades, accounts, level, on, canChange`)
  and `progress.shared`. Action `bell` answers the notification bell (read-only).

### What happens next, and what needs the owner (added 11 Oct 2026)

The owner asked for "some kind of countdown timer to know when next action is going to occur… and
what future actions are going to take place", and "something on the site to tell me whats going on
so i'm aware of everything thats going on in the background or needing my assistance". He also was
not sure whether its improvements needed him to "push" them. They do not, and the panel now says so.

- **`coming(record, portfolio, now, plans)`** (sent as `coming`): a list of `{kind, text}` with
  either `at` (a time) or `after` (a number of finished trades), soonest first, timed ones before
  counted ones. Kinds: `check` (the next scheduled check-in: which market, which holdings it looks
  at, and what it may buy, worked out with the same `allowance` the check-in will use, including
  the coin share, a full budget and too little cash), `open` (the first check-in after each other
  market it has opens), `release` (the next step of the budget's build-up, with amounts:
  `released()`, which `allowance` now also uses; **listed at the check-in that can first spend it, not at the minute of
  the release**: the steps are counted from when the build-up began, so a release fell at 15:55 with the check-in at
  16:10, and the owner read "more is released in 1 h 38 min" above "next check-in in 1 h 53 min" as two different next
  actions and thought the countdown wrong), `sell` (the latest each holding is kept), `rest`
  (a rested screener or the AI model's paused early sells coming back), `trial` (the latest a
  running trial ends), `review` (trades to go until it reviews its own rules; or that this is
  switched off), `notes` (trades to go until the AI model writes fresh notes). **It is a forecast
  from the settings and the state: the check-in itself decides from the prices of the moment**, and
  the panel says so. Empty when switched off.
- **`needs(record, portfolio, now)`** (sent as `needs`): what only the owner can put right. Kinds:
  `off` (switched off while holding something), `noscreener`, `resting` (every ticked screener
  rested), `cash` (less practice cash than one holding), `budget` (the budget is more than the
  practice money there is: on 11 Oct the owner had set $200,000 against $100,000 of fake money),
  `fail` (the last scheduled check-in stopped on an error: the schedule's `except` now leaves
  `state.fail`), `missed` (`missed_check`: two scheduled slots in a row were due and did not
  happen, both since the settings last changed, `state.savedAt`; one miss is forgiven), `mail` (the
  mail service refused the last email). An empty list shows as "Nothing needs you right now".
  **Its reviews, trials and rule changes are never in this list: they happen by themselves.**
- **Email status.** `send_mail` answers True (the mail service accepted it), False (refused; the
  reason is kept in `MAIL_ERROR`) or None (not running as the function, nothing attempted);
  `note_mail` keeps the outcome in `state.mail`; `test_mail` is the one test email (the `mailtest`
  action from the panel, or `{"mail_test": true}` by hand). **"Accepted" is not "arrived"**: the
  panel says to look in junk. Checked 11 Oct: SES healthy and sending (still in sandbox, so only
  verified addresses), domain `stockiq.tech` verified with DKIM and its own MAIL FROM
  (`mail.stockiq.tech`), the owner's address verified, no bounces, complaints or suppressed
  addresses, and a test accepted at 03:00 UTC. Whether it reached his inbox only he can say.
- **The panel** (`practice-autopilot.js`): `leftText` words the time left ("in 1 h 48 min", "in 12
  min 05 s", "any moment now"); `tick` runs every second and only rewrites the text of elements
  carrying `data-ap-until`, so nothing is redrawn and typing is not disturbed; `skew` is the
  server's clock minus the browser's (from `now` in each answer), so a wrong computer clock does not
  spoil a countdown. `countLine`, `needsHtml`, `comingHtml` (four rows shown, the rest folded),
  `mailHtml`. `markTab` puts a ⚠ on the dashboard's own "AI autopilot" tab button while `needs` is
  not empty, so it is seen from the Reports or Practice portfolio tab too. An answer from an older function (none of these fields) shows as before.
- The review email's own description of the rules was the last place with the wording the owner had
  misread as a selling price; it now follows the wording rule above.
- Not done: the same kind of box for the rest of the site (the daily deploy runs on the owner's Mac
  and leaves nothing a web page can read); a summary email.

### How the panel script behaves (`practice-autopilot.js`)

- **Every change saves itself**: the switch at once, ticks and menus after 0.15 s, typing and the
  slider after 0.9 s, anything still waiting when the page is left. `accepted` stops a value the
  server tidied (20000.4 → 20000) being saved over and over. While something is being typed the
  panel is updated in place (`syncDraft`), not redrawn, so the cursor stays put.
- **It keeps itself up to date** (`refresh`, every minute while the page is visible, not while
  something is being typed or saved) and reloads the practice portfolio when the autopilot traded.
- The two description lines (`planText`, `paceText`) are built from what is selected. The sums in
  `buildUp()` are **a copy of the Lambda's rules** (`allowance`, the time rule, 3 buys a check-in,
  the $25 smallest buy), and `marketSplit` / `marketSlots` a copy of how it spreads the budget over
  markets: change one, change the other, and run `autopilot_plan_check.py` (it checks both).
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

### On a phone (added 11 Oct 2026)

The owner asked how the dashboard presents on a phone. Measured at 390px wide it did not: the third
tab was half hidden (the bar had to be scrolled sideways), the holdings table was 740px wide inside
a 308px box with its first column squeezed to a few letters a line, the progress table 729px, and
the trailing-stop menu stuck out past the screen. What was done, all in CSS that only applies on a
narrow screen (nothing changes at desktop width):
- **Tabs** (`dashboard.html`, `@media (max-width: 560px)`): the three tabs share the width and their
  names wrap onto two lines.
- **Tables become cards** (640px and under). The holdings and sold tables carry class `pp-stack`
  (heading row `pp-head`, name cell `pp-name`, button cell `pp-act`) and the progress table
  `ap-stack` (`ap-stack-head`, `ap-stack-title`, `ap-stack-wide`). Each figure cell has a
  `data-label` ("Bought", "Price then", "Price now", "Value", "Change"; "When", "Ended up", …) that
  the phone rule prints before the figure, so a row reads as a card with one labelled line per
  figure and a full-width Sell button. **A new column in one of these tables needs its
  `data-label`**, or it shows on a phone as a bare figure. The cells carry inline styles, hence the
  `!important` in those rules. `practice-portfolio.js` had no stylesheet before: it now adds one
  small `<style id="pp-style">` block (`ensureStyle`).
- **The breakdown** (`.ap-bd`) keeps its columns: headings and section titles wrap, padding shrinks,
  the name column loses its 240px minimum.
- The buy row (dollars and quantity side by side, note and button full width), the trailing-stop
  menu, "Check in now" / "Sell everything" and the Activity / Settings switch take the full width.
- Every box and menu was already 16px text, so a phone does not zoom in when one is tapped.
- **How to check:** `dashboard_page.py` step `mobile` (or `mobile:practice`, `mobile:activity`,
  `mobile:settings` to leave that view up for a screenshot) lists what sticks out past the screen
  and what has to be scrolled sideways inside its own box. Headless Chrome will not make its window
  as narrow as a phone, so wrap the test page first: `python3 check-tools/mobile_frame.py
  <page.html> <frame.html> [width]` puts it in a frame of that width (default 390) and shows what
  the page printed underneath. Checked at 320, 360, 390 and 430px, light and dark, with the
  breakdown open, and the locked view: nothing sticks out, nothing scrolls sideways.
- **Not checked:** a real phone, and the logged-in dashboard itself. The Reports tab (statistics,
  Report History) was not part of this: it is the older page and has its own rules for 768px and
  under, which were not re-measured because its content needs a login.
- With `sips`, a crop offset of 0 means "centred": use `--cropOffset 1 0` for the top of a tall
  screenshot, and crop at the image's full width.

### Smaller facts worth knowing

- **Changing which screeners are ticked while it holds something** (the owner asked what happens
  on switching from crypto to the S&P; tested, `ai_trader_test.py` near "switches from coins"):
  there are no separate jobs per screener. One check-in looks after everything it holds, whatever
  screener it came from. Holdings from an un-ticked screener keep all their rules (time limit,
  loss limit, gain mark, the following stop, the AI review; that screener is still read for them)
  until they are sold; new buys come only from what is ticked, from the part of the budget that is
  not invested; a market drops out of the check-ins once nothing from it is held. With coin and
  share screeners both ticked, the level's coin share applies (Balanced: a quarter of the budget).
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

**Before building an idea about how it trades, replay it:** `python3 check-tools/replay/replay.py` (20 seconds; section 7b,
last part). An idea that is not ahead on both parts of the period, or that random buying beats, is not worth a deploy.

1. **Start from what is live.** Both repos clean (`git status -sb`), then check the live function is
   the mirror: download it, `cmp` with `lambda-sync/stockiq-ai-trader/lambda_function.py`, and note
   its `CodeSha256` and the `shasum -a 256` of the website files. Run one session at a time.
2. **Stage, do not edit in place**: copy the function and the website files to
   `check-tools/pending-<name>/lambda` and `/web`, and change the copies.
3. **Test the copies** (none of these touches anything real):
   ```bash
   cd /Users/dave/VSCODE/stockiq/check-tools
   python3 -W ignore ai_trader_test.py pending-<name>/lambda/lambda_function.py | grep -v '^PASS'   # 386 checks
   node autopilot_test.js pending-<name>/web/practice-autopilot.js | grep -v '^PASS'                 # 198 checks
   sed 's#https://5c7pt7qurshld4cwaqyopfxcei0cuurj.lambda-url.us-east-1.on.aws/#__PRACTICE_API_URL__#' \
     pending-<name>/web/practice-portfolio.js > /tmp/pp.js && node practice_test.js /tmp/pp.js | grep -v '^PASS'   # 74 checks
   python3 -W ignore autopilot_plan_check.py pending-<name>/lambda/lambda_function.py pending-<name>/web/practice-autopilot.js 150
   node autopilot_bell_test.js pending-<name>/web/autopilot-bell.js | grep -v '^PASS'                 # 22 checks (the notification bell)
   python3 ai_chat_test.py pending-<name>/chat/lambda_function.py | grep -v '^PASS'                 # 16 checks (the AI chat's function)
   ```
   `ai_trader_test.py` sets the pace by hand at its top (it patches `DEFAULTS`), as a user who chose
   his own values; the real defaults, where the level sets the pace, are tested in their own part.
   It also sets `STAY_CHECKS` to 1 so that older tests buy a coin at once; the real wait has its own part.
   **Never run `practice_test.js` on the real `practice-portfolio.js`**: it holds the live storage
   address and would write to the live table (it happened once). Add checks for what you change.
4. **See it in a browser** without a login: `dashboard_page.py` (both sections, stand-in server;
   give it `dashboard.html` as a sixth argument and it puts the page's real tab bar and tab script
   into the test page, step `tabs`). After any edit to `dashboard.html` also check that the
   sections still balance and that every inline script parses (`node --check` on each `<script>`
   block): the logged-in page itself cannot be opened from here, it redirects to Sign In.
   Steps such as `type,sale,trial,preset,sellall,limits,trailstop,split,cards,pace,listswitch,next,budget,shares,progress,breakdown,locked,mobile,open`) with headless
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
has redrawn (a kept reference is to the old one and nothing happens); **a link inside the panel
must not be a bare `href="#"` unless its click is cancelled** (`preventDefault`): "What happens then"
was one, handled by the part-switching branch that did not cancel it, so the browser went to the top
of the page (the owner: "it just stays at top of screen"); the site's stylesheet sets
`scroll-behavior: smooth`, and a headless browser does not play the glide, so a scroll looks like no
movement there unless the test sets `scrollBehavior = 'auto'` first (`dashboard_page.py`, step `next`); test expectations with dates must allow for the local time
zone; SES and the news feeds are only used when running as the Lambda, so tests need stand-ins
(`mail=`, `headlines=`); two sessions building at once collided (the fingerprint check caught it);
the panel test's `text()` leaves `&#39;` as it is, so a pattern that quotes a notice with an
apostrophe must allow for it; a test of an action that depends on the day (trading hours, `sellall`)
must set the function's clock (`m.datetime = at(when)` in `ai_trader_test.py`), or it passes on
weekdays and fails at the weekend.

### Start here when resuming (state at 13:10 UTC on 11 Oct 2026: the full sweep, the replay, real costs and the bar, then one code base for the share screeners)

**The job that was next is done (11 Oct 2026, evening): one code base for the share screeners.** All 669 share-screener
workers run the one package built from `stockiq/workers/` (section 8b, "The worker groups": what changed, how it was proved
and deployed, the way back). Confirm nothing has moved: `python3 check-tools/workers.py` shows "one" for the 13 share groups
and the same code across them; `python3 workers/build.py` prints the fingerprint in `workers/live.txt`.
**To look at first, Monday 12 Oct or the next working day:** (a) one FTSE 100 run on a morning after a London session: the
price must be that session's, not the one before (the fix for the empty latest session was tested on a doctored answer
only); (b) an ASX run during ASX hours (the one-bar-a-day rule was only seen after the close); (c) the autopilot's first
share buys, which now come from rankings made with the one RSI.
**The next small job (section 11, "Report writers"):** London prices are pence and are printed as pounds; the coordinator's
report cuts symbols to five characters and prints "$" for every market, so the 🎯 tracker cannot read a background report
of an ASX, Nikkei or FTSE screener. Both are in the report writers (page and coordinator), not the workers, which now send
each stock's `currency`.
**Other things waiting, in order:** (1) the owner's decision on the two **public** GitHub repositories and his personal
file in one of them (section 11, first item); (2) Monday 12 Oct: the first daily deploy with the new copy-keeping rules,
and the first share trades; (3) the autopilot's own trials of a longer holding time and of not selling on the signal, and
recording company figures with each share bought (below, item 0); (4) deleting the 204 worker functions the site never
calls, with his agreement; (5) thinning the bell script's handling of older copies after a week; (6) the worker oddities
left on purpose (section 8b: `MODERATE_SELL`, `STRONG_DOWN`), each a one-line change now, each changing labels.

**What is live, and how to confirm nothing has moved since:**
- Lambda `stockiq-ai-trader`: `CodeSha256` `k2OocgJogAZjcF8LYC6WOtH0n7I3VaE5nb9EmxWzAnI=`, equal to
  `lambda-sync/stockiq-ai-trader/lambda_function.py` (2,887 lines).
- Lambda `stockiq-ai-chat`: `CodeSha256` `cTz2ks6BStwoDLEIod20m/pzvn59WP2VHo9Hc/RtEV8=`, equal to
  `lambda-sync/stockiq-ai-chat/lambda_function.py` (350 lines).
- Website (sha256 starts): `practice-autopilot.js?v=38` (`43520270763f`), `practice-portfolio.js?v=18` (`b48ff650293c`),
  `autopilot-bell.js` version 8 (`88119f40c022`), `theme.js` (`66da2c7c26a1`), `dashboard.html` (`79986e57a7ee`),
  `ai-chat.js?v=2` (`87eaadf52197`); 17 more pages carry the bell's loader line; `index.html` and `faq.html` the plan wording.
  Live files were compared byte for byte at each deploy.
- `deploy-to-s3.sh` carries the rules for how long a browser may keep a copy (section 5, step 8); the first daily run with
  it is Monday 12 Oct: look at its log once (section 12, "After the daily run").
- The single-stock report and its chart (section 7, "The single-stock report"): `stockiq-option-1-1-custom-analysis`
  `cPDWynX/4N+25Ec/+jot60nlhFWq1aeZ8wH/ozEqKps=`, `stockiq-chart-generator` `OIDrZ2W9G3lJ2sKarnoT4c7RvoLh1ApDX43NWjR72z4=`,
  both equal to their mirrors; `stock_metrics.py` sha256 starts `5c034782379b`; tests 79 report, 29 chart.
- Crypto: the 54 `stockiq-option-7-1-worker-N` all `NmXC9dcsA6p5tXJl+u6VZIfdsrvM3ERN/DmMSQ9zalI=`, the orchestrator
  `Tyyx+Pb2l+sy7avfCncwduEtmFtYn6Lws+5g6dj9Kc0=`, both equal to their mirrors (MACD fix of 11 Oct, section 8b).
- Share-screener workers: all 669 show `CodeSha256` `q9ZX/UvTBcszKxRPR9lvJw9UpyfWrB5sOB3pDWccm6c=` (`workers/live.txt`), built from `workers/` in git.
- Both repos clean and pushed; **no `check-tools/pending-*` folder is left**. Tests on the live files: 386 function, 198 panel, 74 portfolio, 22 bell, 16 chat; the panel-versus-function comparison clean (3,780 budget combinations, 2,915
  spreads over markets).
- Rollback copies, one per deploy, in `~/VSCODE/backup/`: `stockiq-ai-trader_before_autopilot_<name>_<date>.zip`, in order:
  10 Oct `v2, fast, panel, autosave, desc, smart, review, controls, wording, limits, gains, pace, stop, orphan, steady,
  trail, now, news`; 11 Oct `clear, hours, next, budget, shares, low52, progress, order, idle, paid, central, release, bell,
  takeover, report`, then `stockiq-ai-trader_before_sweep_20261011.zip` and `…_before_autopilot_costs_…`;
  `stockiq-ai-chat_before_{dashboard, wording, levels, sweep, costs}_20261011.zip`.
- First thing to do: the routine's step 1 ("How to work on it"), then read the owner's record and the function's log
  (`aws logs tail /aws/lambda/stockiq-ai-trader --since 12h`) for errors ("check-in failed", "shared learning failed",
  "not worked out", "not sent") and for the firsts listed below.

**The owner's autopilot at the sweep** (he changes settings often: read the record, do not trust this):
Adventurous; budget $99,941 (all his practice money); built up over 1 day (by hand); checks in every hour (left to the
level); keeps a holding at most 2 days (by hand); trailing stop "protects a gain"; all three switches on. Screeners
ticked: S&P 500, Russell 1000, Russell 2000, NASDAQ 100, Dow 30, ASX 200, FTSE 100, Nikkei 225 and crypto, **with the
share of the budget set by hand to 0% for US, Australian, UK and Japanese shares: everything goes to coins.** It holds
WAL-USD and MANTA-USD ($24,985 each, bought 11 Oct) and one Nikkei share (4307.T, $12,500, bought on a Saturday before
the trading-hours rule; it is sold when Tokyo opens, Monday 00:05 UTC). Practice cash $37,471.

**Its record: four finished trades, two up, -$202.60.** WEMIX +0.6% (+$7.91; score fell below zero). CFX +1.0% (+$12.79;
first sale by the following stop; it rose a further 7.95% afterwards). ERG -2.8% (-$173.03; first sale by the AI review).
CKB -0.8% (-$50.27; the stop was passed between two check-ins). All four were bought at the Balanced level, so the
shared record holds 4 trades from 1 account at that level. Far too few to judge anything.

**Seen for real:** clean scheduled check-ins on every version; headlines reaching the model; both AI models answering
the test question; sales by the following stop and by the AI review; the look-back; "Check in now" releasing the next
step early; a test email accepted by the mail service; the budget being put right on opening the page; the shared
record taking in the four trades (09:10 UTC, 11 Oct) and its trial of the buying order starting; the bell's one list on
the live dashboard, home, analysis and a stock page, opened as the owner's account in a test browser, **and the owner's
own confirmation that the bell works ("ah all good now")**; the AI chat answering dashboard questions from its new guide.
**Not yet seen for real:** a "tighten" answer; the larger model in a review; a coin held back until it has stayed; a buy
spread over several markets; "Check in now" with a market closed; the first notes (at 5 finished trades in the shared
record: one more), a shared note reaching an activity list and its email; the first progress report and review of its
rules (at 20 finished trades at one level); any trial of a rule; a share bought under the buying-order trial; whether
the test email reached the owner's inbox; the dashboard on a real phone.

**Not known:** how the owner looks at the site (stockiq.tech, or a local preview from Kiro). He was asked and did not say;
the bell worked for him only once its addresses were relative, which points to something other than the live domain.
Ask early next time a change "does not show" (section 9).

**Limits to remember:** a stop only acts at a check-in (CFX and CKB were both sold below where their stop stood); the
trading hours know no public holidays; a market's share is a number of whole holdings; the trading cost is one typical
figure (0.1% each way; a small coin costs more in real life); with one account the shared learning is that account.

**What the owner is after, in his words:** "trying to optimise this to always be active ever changing and improving", a
goal of "close to 70% profit 30% loss", "seamless and straightforward so a dummy could figure it all out", "something on
the site to tell me whats going on", "a smart AI that is learning in a central location for all users", "look like a
professional stock portfolio", and things "setup in one way not multiple ways". Hold the goal against section 7b: the
share of winning trades comes from the selling rule and is not profit; the screener's own factors showed no reliable
link with what shares did next. Say so plainly each time results come up, and judge by dollars and the average per trade.

**The honest position, as told to the owner on 11 Oct (section 7b, last part):** the replay and both backtests say the
screener's score has no clear edge; what shows up is momentum in a rising market, and that quick share trading loses to
costs. He asked to carry on in this order: (1) the fast replay: done; (2) real costs on the practice money: done;
(3) better inputs: the replay has tested the price-based ones, company figures are still to do (below); (4) the bar in
writing: done, and shown on the panel.

**Open, in the order I would take them:**
0. **Better inputs, next steps.** (a) Let the autopilot try, by its own trial mechanism, what the replay points to for
   shares: a longer holding time and not selling on the screener's signal (neither is in `TUNABLE`; each needs a tag on
   the buy and a trial like the buying order's). (b) Company figures: record a few real ones with each share bought
   (earnings yield, profit margin, debt, growth; the single-stock report Lambda already fetches them from Finnhub and
   Yahoo) and split the record by them, as was done for the 52-week low; no rule until the record supports one.
   (c) Saved coin prices, so that coins can be replayed too. (d) The replay on a list that is not today's members.
1. Monday 12 Oct: the first daily deploy with the new copy-keeping rules (its log); what happened when Tokyo, Sydney and
   New York opened (4307.T sold; his shares for share markets are 0%, so no share buys are expected unless he changes
   that); "What happens next" reading right against what really happened.
2. The first shared notes (5 trades) and the first progress report (20 at one level): read the note, the email, the table.
3. The trial of which share to buy: it cannot move while every share market's share is 0%. If he asks why nothing is
   being tried, that is why.
4. Thin out the bell script's dealings with older copies after a week (see "The notification bell").
5. Next ideas of the same kind as the buying-order trial, each to be tried and never adopted from hindsight: longer
   holding times for shares, the automatic pace of each level, the stop's distances, the wait for a coin to stay; and,
   once the shared record holds thousands of trades, a small fitted model scoring a candidate (no new AWS service needed).
6. The screener scoring itself (section 7b): untouched; changing it is the owner's decision and a redeploy of worker groups.
7. Smaller: a leftover holding of an odd size can leave less than one holding's room, never used; a summary email; the
   deploy test account has an empty, switched-off autopilot record (harmless; made by a deploy check).

**Who can use it, and what guards every account:**
- **The practice portfolio by hand is free for every signed-in account.** The AI autopilot (Beta) is for accounts on a paid
  plan, or listed in env `AI_TRADER_USERS` (the owner's account and the deploy test account; "may use it without
  paying"). Decided in the function: `allowed(user)` = `listed(user)` or `plan_of(user) == 'paid'`; `plan_of` reads table
  `stockiq-user-tracking`, item `<email>#registration`: paid = `subscriptionStatus` `active`, or `cancelled` with
  `expiryDate` not yet past; a free trial is `free`; a read that fails is `unknown` (cached 60 seconds). On 11 Oct: 66
  registered accounts, 1 paid (the owner's); one autopilot record besides his (the deploy test account's, off).
- **Without a paid plan:** `get` answers `{allowed: false, locked: 'plan', upgrade}` and no record is made; every other
  action is refused with HTTP 402 and the same pointer; the panel shows `lockedHtml` (what it is, that it is in every paid
  plan, that buying by hand stays free, "See the plans") and its tab a 🔒. `locked: 'unknown'`: "could not be checked,
  refresh in a moment" (HTTP 503 for actions); nobody is paused on an unknown.
- **A plan that ends:** the scheduled run pauses the autopilot (`pause_for_plan`, `pausedWhy: 'plan'`, a line and one
  email); it switches back on by itself when the account is on a paid plan again and its dashboard is opened.
- **Paused after two weeks without a visit** (`seen_now` writes `state.visit` at most every 6 hours; `pause_if_away`,
  `IDLE_DAYS` 14): switched off, a line and one email; back on at the next visit to the dashboard. The bell's question on
  other pages is not a visit. What it holds is neither sold nor watched while paused.
- **The schedule** runs every account that is due, up to `RUN_TOGETHER` (4) side by side, and starts no check-in with less
  than `RUN_RESERVE_SECONDS` (100) left; such an account runs at the next slot. This is not a limit on users. It scans
  the whole table page by page. If paying users ever number in the hundreds, give each account its own invocation.
- **A daily limit on AI calls per account:** `AI_CALLS_PER_DAY` (120); past it, buys go by rank and only the fixed rules
  sell. Screener results are shared between accounts for 20 minutes.
- **What the site says:** home page pricing (`index.html` `#pricing`), the dashboard's three plan cards and an FAQ entry
  name the practice portfolio (free) and the AI autopilot (Beta, paid plans). Wording rule: "practice", "fake money", "no
  real trade is placed", "not financial advice", "past screener results have not shown a reliable edge"; never "picks".
- **Still to weigh, and the owner knows:** an AI choosing what to buy for paying users, even with fake money, sits on the
  same unreviewed legal question as the signals (section 11). And the `userId` is whatever the browser sends: someone who
  knows a paying user's email could open that user's autopilot (fake money only).
- **Cost:** a crypto check-in is a full crypto screener run (about 540 worker calls) unless a copy under 20 minutes old
  exists, so one user on 30-minute check-ins adds about 780,000 Lambda calls a month, plus up to two small AI calls per
  check-in and at most 8 larger ones a day: a few dollars a month at the very most.

### Ideas offered and not built

A chart of the account and of the autopilot's result over time; a weekly summary email even when
there is no review; a coin yardstick (Bitcoin) for coin trades in the breakdown; watching prices
between check-ins (a stop can only act at a check-in); trials that cover the owner's settings
(holding time, how often it checks in); selling part of a holding; sorting the tables; recording
which report a manual buy came from; dividends; per-user cost limits before opening it up;
public holidays for each market. **Separate pots** (offered 11 Oct, when the owner wondered about
"a better way to manage it all" after asking what happens on switching screeners): instead of one
budget across everything ticked, a few named pots, each with its own budget, screeners and pace
(say "Coins, quick" and "US shares, steady"), shown and judged separately. It would make a switch
of screeners a visible choice instead of a side effect, and show which kind of trading earns its
keep. Not asked for yet; it is a rework of the settings, the allowance and the panel. (The share
of the budget per market, built the same day, covers the "how much goes where" half of this; a
separate pace and record per market is the half that is not built.) Also not built: letting the
automatic split follow results (more to the market whose trades have done better); it needs far
more finished trades than there are, and would chase noise before then.

## 9. Pitfalls learned the hard way

- **"It does not show for me" (the notification bell, 11 Oct 2026): six rounds, one cause found late.** The owner asked
  for the autopilot's trades in the bell on every page. He then reported, round after round, that nothing showed ("no
  change", "something is overriding your changes"), while every check here passed. What was wrong, in the order found:
  1. *The trades sat out of sight.* The first forms put them as a group above or below each page's own report list,
     whichever had the newest item; with a report newer than the last trade they were under seven reports in a 400px
     list. Checks with a made-up account and no reports had passed. Fixed by one list, newest first.
  2. *Browsers kept old copies.* The site let a browser keep a page for an hour and a script for a day, so a fix was live
     and unseen. Fixed at the source (section 5, step 8: pages are asked for again every time, scripts kept five minutes).
  3. *An old copy outran the new one.* An old `theme.js` in a browser's store asked for the first version of the bell's
     script, which ran before the current one arrived; the current one then stood down ("if I am already here, do
     nothing"). Fixed: the newer version always takes over.
  4. **The one that fits everything he saw: the script was asked for at `/autopilot-bell.js`.** That address exists only
     when the site is at the top of its address. Served from a folder (a local preview of `~/VSCODE/website`), it is a
     404, the script never runs, and nothing on the page says so. The dashboard had worked at first because its script
     tag was relative, and stopped when it was given the same absolute address as the other pages. With relative
     addresses he confirmed at once that it worked.
  **Lessons, all learned the expensive way:**
  - **Ask where he is looking at the site, first** (stockiq.tech, a local preview, a phone, which browser), and reproduce
    *that*. A check in a clean browser on stockiq.tech proves the site, not what he sees.
  - **Reproduce with the real account's data** (`live_bell_check.js`, `REAL_USER`, read-only) before saying a thing works;
    do not say "fixed" on the strength of a made-up account.
  - **Never address the site's own files as "/file"** in a script or a loader line: relative to the page, or to the
    script itself (`document.currentScript.src`).
  - A script that may be loaded twice must let the newer version win, and its author must think through what an older
    copy still on the page will do.
  - When a deployed change "does not show": `curl -sI` the plain address (no `?something`) for `cache-control` and compare
    the body with the local file; that settles in a minute whether the site or the viewer is behind.
  - Change one thing per round and say what was and was not reproduced. Four deploys chasing guesses cost more than one
    question would have.
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
- **A count of fingerprints is not a count of programs (11 Oct 2026).** The first audit of the screener workers said the
  Russell groups had "100 and 200 different versions" and planned a large clean-up around that. They were two programs
  zipped 300 times: a zip's `CodeSha256` changes with the dates of the files inside it. Compare what is inside
  (`check-tools/workers.py --contents`) before believing that functions differ.
- **"It will move a little" was a guess; measure (11 Oct 2026).** These notes said one RSI for all screeners would move US
  scores "a little". Replayed on saved prices it changed a third of the signal labels. `workers/prove.py` exists so that
  the size of a scoring change is known before it is deployed: run it and read it, whatever the change looks like.
- **A deploy by hand commits whatever is lying in both repos (11 Oct 2026).** A `./deploy-to-s3.sh` was run on a Sunday
  evening while a session was mid-task; its git step swept seven unfinished files into an "Auto-update" commit and
  pushed them (harmless that time). It also moved the 23-hour push marker. Another reason to commit finished stages
  promptly, and to check `git log` for an "Auto-update" when a file is unexpectedly already committed.
- **Lambda code is not in git** (`lambda-sync/` is a gitignored mirror; the one exception since 11 Oct 2026 is the
  share-screener workers' code, which lives in `stockiq/workers/`). The only history of a
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
- **The share-screener workers are changed in `stockiq/workers/`, never in the AWS console and never in `lambda-sync/`**:
  edit `stock_worker.py`, run `workers/prove.py` and read every difference, commit, deploy with `workers/deploy.py` through a
  packaged script, one small group first (section 8b, "The worker groups").
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
  folders incl. `stocks/`) plus GitHub are enough. The one exception is the Lambda rollback zip:
  **the daily backup leaves Lambda code out** (section 3), so the zip kept before a change is the only way back.
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
- **`analysis.html`, `analysis-functions.js`, `index.html` and `dashboard.html` are very large: never read them whole.**
  Search for what is needed (the owner's instruction for `analysis.html`), read the few lines around a match, edit by
  exact replacement and confirm with a diff or a line count that nothing else changed.
- **When the owner says a change does not show, ask where he is looking at the site and reproduce that** before changing
  anything; never address the site's own files as "/file" (section 9, the bell).
- **Both GitHub repositories are public** (checked 11 Oct 2026): nothing private belongs in a commit, in a commit message
  or in these notes: no keys, no customer addresses, nothing personal. An account is "the owner's account" here, not
  an address.

## 11. Open items and optimisation ideas

Needs the owner's decision or more work (nothing here is fixed):
- **Both GitHub repositories are public** (`davedewit/stockiq` and `davedewit/stockiq-website`; checked without signing
  in, 11 Oct 2026). Two things follow that only the owner can decide. (1) `stockiq/youtube-channel-plan.md` is a
  **personal** plan that has nothing to do with the site and can be read by anyone; taking it out of the repo does not
  take it out of the history, which needs a rewrite or the repo made private. (2) These notes describe how the site is
  built, including its weak points (the `userId` is whatever the browser sends; the analysis Lambdas are open URLs; the
  AWS account number and function addresses). Making `stockiq` private would cost nothing the site needs: only the
  deploy's `git push` uses it. He was told at the end of the session of 11 Oct; nothing was changed.
- **Practice portfolio and AI autopilot: what is open** is listed in section 8c, "Start here when
  resuming" (Monday's first trades across markets, the first progress report at 20 finished trades,
  a trial of buying shares by distance above the 52-week low if the record supports it, the
  screener scoring left untouched after the factor study of section 7b).
- **Legal.** The business is "StockIQ", online-only, no physical address, **no financial services
  licence**; billing is in USD ($4.99 / $14.99 / $49.99 per month, confirmed on the live Stripe
  prices). The terms, About page, pricing section and FAQ say all of this, and the product
  wording was neutralised (section 8b). Whether issuing automated signals to paying users
  without a licence is acceptable under Australian law is a question for a lawyer; the owner
  knows and has not had it reviewed. The owner trades as an individual (no company structure).
- **Report writers: pence, cut symbols, "$" for every market (found 11 Oct 2026; the next small job).**
  - London prices are pence (Yahoo's `GBp`). The page prints them with a pound sign ("£503.80" for Tesco at 503.8p; the three
    FTSE formatters in `analysis-functions.js`, lines with `£${`), the coordinator with a dollar sign. UK shares are quoted
    in pence, so "503.80p" is the right form. **The 🎯 tracker reads the price after a currency sign** (`[$£€¥]` in
    `parseScreenerTop10`, `dashboard.html`), and reports already saved say "£2614.00" meaning pence, so the tracker must
    accept both "£2614.00" and "2614.00p" as the same number of pence. The practice portfolio and the autopilot already
    treat `GBp` as pence. Three places to change together: the page formatters, the coordinator, the tracker's pattern.
  - **The coordinator's report cuts every symbol to five characters** (`(symbol + '     ')[:5]`, about line 633 of its
    `lambda_function.py`) and prints "$" before every price: a background ASX report says "AGL.A  $8.43", Nikkei "4307.
    $5613.00", FTSE "TSCO.  $503.80". The tracker cannot find those tickers, so the 🎯 button on a **background** report of
    a non-US screener shows nothing or the wrong share (a page-run report is fine). Fix: do not cut the symbol, and take
    the sign from the stock's `currency` field, which the workers send since 11 Oct 2026.
  - Test with `check-tools/tracker_run.js` on a `res_<key>.json` from `run_all.py` and on a `page_*.json`, old and new.
- **Share-screener workers** (section 8b, "The worker groups"): one code base since 11 Oct 2026. Open: no real company figures
  (one file to change now, once there is a source); the two fixes for Yahoo's oddities to be seen live (FTSE on a morning
  after a session, ASX during its hours); the oddities left on purpose (`MODERATE_SELL`, `STRONG_DOWN`); Russell 1000/2000
  lists not refreshed (7 and 27 of their symbols no longer have prices); ASX 300 approximate; the 204 unused worker
  functions to delete when the owner agrees.
- **Crypto scoring** (section 8b, "How a coin is scored"): the single-coin worker `stockiq-option-7-2-worker-1` was not
  checked for the MACD fault the 54 screener workers had; the score mixes opposite ideas and has never been tested for
  coins; whole-number scores tie often. A finer score, or a test of it, needs saved coin prices.
- **Crypto track record (review from early Nov 2026).** Entries from before 11:52 UTC on 11 Oct 2026 were ranked without
  MACD (section 8b): measure the two periods apart. The entry log (section 8b "Crypto") started
  10 Oct 2026. Once it holds a few hundred entries, compare each coin's price 24 hours and 7 days
  after entering the top 10 with the average coin over the same days. Leftovers that can be
  deleted when the owner agrees: Lambda `stockiq-coinspot-predictions-updater` (no longer
  triggered) and the old-format rows in both crypto tables.
- **UK FTSE screener showed prices one trading day old** (seen 10 Oct: Yahoo's latest daily bar empty for London stocks,
  IMB.L 2,614 in the report, 2,662 actual). Fixed in the one worker file on 11 Oct 2026 (the latest session is taken from the
  quote); **not yet seen live**, because Yahoo had filled the bar in by then. The pence shown as pounds is the item above.
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
- **Page score vs app score.** Same model, different inputs (once 71 vs 47 for AAPL): the page uses the previous
  close and Yahoo's figures, the app the live price and Finnhub's. Three of its causes were dealt with on 11 Oct 2026
  (section 7, "The single-stock report"): the trend factor is graded, part-day volume is left out, and figures Finnhub
  lacks come from the pages' own Yahoo cache. What is left: MACD (+8 or -8 on its sign) and RSI still score in steps.
- **Single-stock report, left open on 11 Oct 2026** (section 7): its code cannot go into git while the Finnhub key is
  written in it (move the key to the function's settings first; both repositories are public); company figures only for
  the 3,333 stocks the site's daily job keeps them for, up to a month old; the analysis page in a browser and on a real
  phone was not looked at; the first run of `publish_company_figures.py` inside the daily deploy is Monday 12 Oct:
  look for "Company figures" in `~/stockiq-daily.log`.
- **Dashboard plan cards** (the line "AI autopilot for your practice portfolio (fake money)" added on 11 Oct is real and the same on all three plans) list features that are not verified to differ by plan ("Advanced
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
  --cache-control "public, max-age=0, s-maxage=3600, must-revalidate" --content-type "text/html; charset=utf-8" --profile default --region us-east-1
aws cloudfront create-invalidation --distribution-id EHXV50CPHY07R --paths "/faq.html" --profile default --region us-east-1
```
(`*.js`: `--cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript"`. These are the values of
section 5, step 8: a page uploaded with the old "max-age=3600" would again be kept by browsers for an hour.)

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
autopilot; steps `type`, `sale`, `trial`, `off`, `open`, `preset`, `sellall`, `limits`, `split` and more, listed in `check-tools/README.md`): use it to see how they work with each other,
for example that a sale made in the background appears without losing what is being typed.
A deploy script that checks `pgrep -f deploy-to-s3.sh` must be run as its own command: written and run
in one command, the check finds its own text and stops.

**Share-screener workers** (one file for all 13 groups, section 8b "The worker groups"):
```bash
cd /Users/dave/VSCODE/stockiq
python3 check-tools/workers.py            # every group "one", and the 13 share groups the same code as each other
python3 workers/build.py                  # prints the package's fingerprint: must equal workers/live.txt when nothing is being changed
python3 workers/prove.py                  # what a change to workers/stock_worker.py does, on saved prices (about 3 minutes)
python3 workers/deploy.py --selftest      # the deploy tool's rules against a stand-in for AWS
```

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
  - **Headlines for a coin must be about the coin** (section 8c): share news about a company with the
    same letters as a coin's ticker had reached the model. Rollback zip: `…_before_autopilot_news_…`.
  - **Dashboard tidied into tabs** (sections 8 and 8c): Reports, Practice portfolio and AI autopilot
    each have a tab; the autopilot panel is split into Activity and Settings with its switch and
    buttons kept at the top. Website files only.
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

- **11 Oct 2026** (same Claude Code session, continued):
  - **The plan for a holding in words nobody can misread** (section 8c, "Wording rule"): the owner
    read "once it has been up 4.5%, sell if it slips back…" as a selling price. Buy plans, sale
    stories, the portfolio's line under a holding, "Holding now" and the Trailing stop menu now say
    that rising is not a reason to sell and that the stop only starts following there.
  - **Trading hours hold by hand too** (section 8c): "Check in now" and "Sell everything it holds"
    only trade in markets that are open, and say which are closed and when they open; an early
    release of the budget is taken back when nothing was bought. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_clear_20261011.zip`.
  - **A share's "sold at the latest" time is its market's next opening** after the holding time
    ends, each holding's line says when its market is closed and when it opens, and the settings
    line in the activity list says "over 1 day". Rollback zip: `…_before_autopilot_hours_20261011.zip`.
    Live: function `CodeSha256` `yveoXxKn…`, `practice-portfolio.js?v=13`, `practice-autopilot.js?v=20`.
  - **Full check of these notes against the code**: all 282 code names in section 8c exist; the
    level table, pace table, market hours, bounds, limits and AWS settings match; test counts,
    script versions and "where things stood" brought up to date; the function count corrected to
    984 (the two functions made on 10 Oct were not counted) and `lambda-url-mapping.json` regenerated.
  - First real sale by the AI review (ERG, -2.8%) and first look-back result (CFX rose a further
    7.95% after the stop sold it) recorded in section 8c.
  - **"What happens next" and "Needs you" on the autopilot panel** (section 8c): a live countdown to
    the next check-in, a list of what is coming with what each check-in may do, what goes by the
    number of finished trades, a box for what only the owner can put right (a missed or failed
    check-in, a refused email, too little practice money, no screener), the last email's status and a
    "Send me a test email" link. Email set-up checked on AWS and one test accepted. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_next_20261011.zip`. The dashboard's AI autopilot tab
    carries a ⚠ while something needs the owner. Live: `practice-autopilot.js?v=22`.
  - **The budget cannot be more than the practice money there is** (section 8c, settings table): said
    at the field with a one-click fix, refused in plain words, and set right by the function as a
    backstop. A sale by the following stop that ends below the buying price now says the gain was
    gone before the stop could act (it had said "sold to keep part of the gain" on a -0.8% sale).
    Rollback zip: `…_before_autopilot_budget_20261011.zip`. Live: `practice-autopilot.js?v=23`.
  - **The budget is spread over the markets ticked** (section 8c, "How the budget is spread"): a
    share per market in whole holdings, even on automatic (coins held to the level's share) or
    picked from a menu under the market; enforced at every buy. Before this the first market to
    open could take most of the budget. "Check in now" now releases a whole holding's worth of the
    budget however small the steps. A local name `slots` had hidden the schedule helper of the same
    name (now `slot_times`): the "what happens next" list silently failed in tests until renamed,
    which is what its `except` and log line are for. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_shares_20261011.zip`. Live: `practice-autopilot.js?v=24`.
  - **Factor study of the screener score** (section 7b): none of its own factors reliably sorted
    stocks; a win rate comes from the selling rule, not from skill; one raw figure (distance above
    the 52-week low) kept a modest lead. The autopilot now records that figure with each share it
    buys and splits its record by it: a measurement, not a rule. Rollback zip:
    `…_before_autopilot_low52_20261011.zip`. Live: `practice-autopilot.js?v=25`.
  - **Progress per batch of 20 finished trades, with its own investigation** (section 8c, "Learning"):
    a table on the panel; after each 20 it compares them with the 20 before and, if they did no
    better, says what stands out, puts back a change of its own that was followed by a clearly
    worse batch, and starts a trial of a change the AI model picks from its candidates. **A budget
    larger than the practice money is now put right wherever it is met**, not only refused when
    typed (the owner's saved $200,000 became $99,941 the moment the page was opened). Rollback zip:
    `…_before_autopilot_progress_20261011.zip`. Live: `practice-autopilot.js?v=26`.
  - **Its own trial of which share to buy** (section 8c, "Learning"): every second share is the one
    furthest above its 52-week low on the shortlist, kept only if clearly better after 10 finished
    each way; "Improvements so far" line on the panel. Built after the owner pointed out that the
    study had been measured and reported but not acted on. Rollback zip:
    `…_before_autopilot_order_20261011.zip`. Live: `practice-autopilot.js?v=28`.
  - **Safeguards for every account** (section 8c, "Start here"): paused after two weeks without a
    visit to the dashboard and back on at the next visit; check-ins of several accounts side by
    side; a daily limit on AI calls per account. The autopilot itself is still open to the two
    listed accounts only. Function only. Rollback zip: `…_before_autopilot_idle_20261011.zip`.
  - The breakdown table under "How it is doing" laid out more clearly (website only, `practice-autopilot.js?v=29`).
  - **The AI autopilot opened to every account on a paid plan** (section 8c, "Start here"): the
    function checks the plan itself; accounts without one see what it is and a button to the plans,
    and are refused and sent there if they try to use it; an ended plan pauses it. Home page
    pricing, dashboard plan cards and a new FAQ entry say what the plans include. Rollback zip:
    `…_before_autopilot_paid_20261011.zip`. Live: `practice-autopilot.js?v=30`.
  - **Results in words, and the Beta label** (section 8c, "What the owner sees"): the practice
    portfolio says "up", "down" or "level" instead of signed figures in its "whose result is whose"
    line and its Account value card; the AI autopilot is labelled Beta on the panel, the dashboard
    tab, the plan cards, the home page pricing and the FAQ. Website only:
    `practice-portfolio.js?v=14`, `practice-autopilot.js?v=31`.
  - **The AI chat is on the dashboard and knows it** (section 8c, "The AI chat on the dashboard"):
    how the dashboard works, and what the user's own practice portfolio and autopilot show, with
    rules against advice and against adding to the figures. Changing settings by chat is not built.
    Live: `ai-chat.js?v=2`, `practice-autopilot.js?v=32`, `practice-portfolio.js?v=15`.
  - "What happens then" beside the countdown now opens Activity and goes down to the list (it was a
    bare "#" link that sent the page to the top). Website only, `practice-autopilot.js?v=33`.
  - The "Screeners it buys from" card laid out afresh: a bar for the split, each market's share in
    a box of its own (website only, `practice-autopilot.js?v=34`).
  - **The dashboard on a phone** (section 8c "On a phone"): the tabs fit, the holdings, sold and
    progress tables become cards with a label on every figure, the breakdown wraps, the buy row,
    menus and main buttons take the full width. Website only: `practice-portfolio.js?v=16`,
    `practice-autopilot.js?v=35`, `dashboard.html`. New test tools: the `mobile` step of
    `dashboard_page.py` and `mobile_frame.py`. Checked in a phone-width frame in a headless
    browser, not on a real phone.
  - **Learning shared by every account; arrows; the bell** (section 8c, "Learning is shared by every account" and "What the
    owner sees"): every account's finished trades go, anonymously, into one record that the scheduled run reviews once
    for everyone and every autopilot uses; results are shown as green and red arrows with amounts; the dashboard's bell
    lists and counts the autopilot's buys and sells with profit or loss. The schedule's table scan now pages through the
    whole table. Rollback zip: `…_before_autopilot_central_20261011.zip`. Live: function `5kK9DYb9…`,
    `practice-portfolio.js?v=17`, `practice-autopilot.js?v=36`.
  - "What happens next": a release of the budget is listed at the check-in that can first spend it (it had its own,
    earlier time, which read like a second "next action"). Function only (`MMmJJ9M5…`). Rollback zip:
    `…_before_autopilot_release_20261011.zip`. First scheduled run of the shared learning seen in the log at 08:10 UTC
    ("shared learning: 0 new finished trades…", the record `_brain` written); the owner's four trades follow his next
    check-in.
  - **The notification bell** (section 8c, "The notification bell"; the story in section 9): the autopilot's buys and sells
    are in the bell with the reports, as one list, newest first, drawn by one script (`autopilot-bell.js`) for every page
    that has a bell; unread marks and the red number work as for reports. The function has a read-only action `bell`. It
    took six rounds: the trades first sat out of sight under the reports, browsers kept old copies, an old copy outran the
    new one, and finally the cause that fitted everything: the script was asked for at "/autopilot-bell.js", which is
    nowhere unless the site sits at the top of its address. The owner confirmed it works.
  - **Browsers no longer keep old copies** (section 5, step 8): root pages are asked for again every time, scripts and
    stylesheets are kept five minutes (`deploy-to-s3.sh`; the 36 files on the site relabelled, content untouched).
  - **Full sweep, evening:** the temporary diagnostics taken out of the bell's script and the function; the AI chat's guide
    to the dashboard brought up to date (arrows, the bell, shared learning) and tried live; section 8c's parts on the
    bell, "Start here when resuming" and who can use the autopilot rewritten from the deployed state; the other steering
    files and the two README files corrected; two superseded task plans removed (`.agents/tasks/nikkei225-*.md`);
    every code name these notes mention checked against the code. Found and passed to the owner: both repositories are
    public (section 11). Live at the end: `stockiq-ai-trader` `e6X8RM+w…`, `stockiq-ai-chat` `8QzCNJ8L…`,
    `autopilot-bell.js` version 8, `practice-autopilot.js?v=37`, `practice-portfolio.js?v=17`.
  - **After the sweep, at the owner's word ("go ahead with what you think is best in that order"):** the fast replay of the
    autopilot's rules (`check-tools/replay/replay.py`; findings in section 7b); **a trading cost of 0.1% on every practice
    buy and sale**, by hand and by the autopilot; **the bar its record has to clear**, set down and shown on the panel
    (300 finished trades, after costs, ahead of the yardstick by twice the margin of error); the panel's note on shares
    kept two days or less; the AI chat's guide told of the cost and the bar. Live: `stockiq-ai-trader` `k2OocgJo…`,
    `stockiq-ai-chat` `cTz2ks6B…`, `practice-portfolio.js?v=18`, `practice-autopilot.js?v=38`. Tests: 386 function,
    198 panel, 74 portfolio, 22 bell, 16 chat.
  - **Crypto screener: three faults** (section 8b, "How a coin is scored"), found when the owner asked whether the top 10 is
    in the right order. It is; but MACD had never been worked out for any coin (30 days of prices asked for, 35 needed:
    every coin scored "MACD Bear: -2"), a coin with a stuck price stood 5th, and ties at the cut went unsaid. The 54
    workers now ask for 90 days for MACD; the orchestrator leaves stuck coins out and states ties. Scores and the top 10
    changed at 11:52 UTC.
  - **Audit of the worker groups** (section 8b, "The worker groups"; `check-tools/workers.py`): 928 workers in 18 groups, 204
    never called; the share screeners are one code base with small drift (two ways of working out RSI, a file per function
    in the two Russell groups); a plan to make it one source file in git, written and not started.
  - **One code base for the share screeners (evening; section 8b, "The worker groups").** All 669 share-screener workers in
    13 groups run one package built from `stockiq/workers/` in git (fingerprint `q9ZX/UvTB…`); before, seven copies that had
    drifted. One RSI everywhere (Wilder's): **about a third of US and London signal labels and three or four of each top 10
    changed on the day**, far more than these notes had expected; the NASDAQ 100 and Dow 30 lost their own company-figures
    tables; the ASX 24-hour change of 0 and the London price a day old fixed at the source; the Russell lists in the
    packages replaced by the coordinator's (the old ones held 125 company names); SPY fetched once per batch. Proved on
    saved prices first (`workers/prove.py`, `workers/results-proof-2026-10-11.txt`), deployed a group at a time with the
    way back tested on the Dow 30, every share button run through the page and the coordinator afterwards. The studies of
    section 7b run again with the one file: same conclusions. New tools kept for good: `workers/build.py`, `prove.py`,
    `deploy.py` (with a self-test), `groups.py`; `check-tools/workers.py --contents`. Old packages:
    `~/VSCODE/backup/workers_before_onecode_20261011/`. About and FAQ pages checked: neither says how RSI is worked out,
    nothing to change. `add-new-screener.md` rewritten around the one package, with Germany (DAX 40) as its example.
    **Lessons: a count of zip fingerprints is not a count of programs; and measure a scoring change before describing its
    size** (section 9).
  - Found on the way and left open (section 11, "Report writers"): pence printed as pounds, and the coordinator's report
    cutting symbols to five characters.
  - Notes: section 8c ends with "Start here when resuming". Everything known is in these files.
  - **The single-stock report and its chart rebuilt** (section 7, "The single-stock report and its chart"), in the first
    session again, after the owner asked whether the individual analysis could be improved. Prices in the share's own
    currency (every share had a dollar sign, pence included); one bar a day (ASX "+0.00% today") and the latest session
    from the quote (London a day old); one RSI for text and chart (47 against 56); a trend factor that grows with the
    distance (0.03% under an average read "Strong Downtrend: -12"); one explanation of the score that adds up; company
    figures for shares outside the US from the pages' own cache, published by the new `publish_company_figures.py`
    (Yahoo's summary cannot be read from AWS: tried, refused, taken out); a chart drawn from the report's own prices,
    with clean lines, the 200-day average, no background and lettering that grows on a phone. Three deploys with dry
    runs (13:20, 13:27, 13:28 UTC); `stock_metrics.py` follows; tests kept in `check-tools/report/`. **Lesson: read the
    live output a second time after a deploy: the third deploy fixed a wrong source label that only a repeat report from
    a warm function showed.**
