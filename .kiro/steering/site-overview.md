# StockIQ Site Overview (read this first)

How stockiq.tech works end to end, what is generated vs hand-edited, the current SEO setup,
known pitfalls, and open ideas. Last full review: 25 Sep 2026.

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
Browser ──> ~680 Lambda function URLs directly (no API Gateway)
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
| `/Users/dave/VSCODE/stockiq/` | `davedewit/stockiq` | Scripts, Kiro steering. `lambda-sync/`, `.analysis_cache/`, `*.json` are gitignored |
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
3. `update_stock_analysis.py`: data snapshots on all 3,467 stocks, sets index/noindex on large caps (≥$10B), writes `indexable_stocks.txt`. ~20 min, no API cost. 404s for delisted stocks are normal/cached. **Was missing from deploy until Oct 2026 — caused stock data to go stale.**
4. Backups (website + stockiq; prod_scripts every 23h)
5. `people_also_watch_stocks.py --missing`
6. `update_sitemap.py`: **rebuilds** stock URLs from `indexable_stocks.txt` (not all HTML files), updates lastmod on site pages. Refuses if list < 200 entries.
7. `cleanup_broken_links.py`, `remove_news_duplicates.py`, `finalize_news_html.py` (trim news.html to 240 stock + 60 general, keep noindex)
8. S3 upload:
   - `stocks/`: `aws s3 sync --delete` (size + mtime), 24h cache
   - `js/`: sync --delete, 24h cache
   - root `*.html` (1h cache), `*.css` (24h), root `*.js` (24h; news.js 1h): uploaded when local size ≠ S3 size
   - images (7d), and `stocks.txt robots.txt sitemap.xml`
9. CloudFront invalidation `/*` (waits for completion), `notify_search_engines.py` (IndexNow; "202" means accepted)
10. `sync-all-lambdas.sh` (hourly cooldown)
11. Git: for **both** repos, commit if changed → `pull --rebase` → push, unless the last
    push by this step was under 23h ago. Full rules and timing examples in section 5b.

Preview without uploading or pushing: `cd stockiq && DRY_RUN=true ./deploy-to-s3.sh`.
It still runs the local steps (backups, sitemap, news trim), then prints `(dryrun)` lines.

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

## 6. SEO setup (as of 25 Sep 2026)

- **Indexed stock pages:** market cap ≥ **$10B USD** and fresh price data → `index, follow` + data
  snapshot. That was 962 pages (664 US; the rest TO, L, T, HK, AX, PA, DE, NS).
  All others (2,505, including 164 delisted/renamed symbols with no data) → `noindex, follow`,
  with an empty snapshot section. The threshold is `INDEX_MIN_MARKET_CAP_USD` in
  `update_stock_analysis.py`. The owner chose to keep $10B for now; review after 6–8 weeks of
  Search Console data ($2B ≈ 2,000 pages; "any stock with data" ≈ 3,300).
- **Sitemap:** 979 URLs (962 stocks + 17 site pages incl. about.html). news.html is excluded.
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

- Anonymous visitors get **1 analysis per day**. The page (`auth.js` → `checkStockAnalysisAccess`)
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
- Stock pages use Yahoo fundamentals (converted to Finnhub units: %, D/E ratio) because the
  Finnhub free key is shared with the live Lambda. Scores can differ slightly from the app.
- Public pages use **neutral wording** ("Positive signals", "Mixed") plus "not financial
  advice". No BUY/SELL labels on public pages. The model calls its 1-year change "YTD"; pages
  relabel it.
- `about.html` documents both systems. Keep it in sync if scoring changes.

## 8. Front end

- `analysis.html`: options 1–7 (stock/ETF report, signals, US/EU/Asia/other screeners, crypto).
  Logic in `analysis-functions.js` (310 KB) + `js/analysis-core.js`.
- `dashboard.html`: report history, favourites, plans/upgrade (Stripe), manage subscription.
- `index.html`: market overview widgets, guides, "How StockIQ Works", email capture, comparison.
- Stock pages load `sidebar.js`, `stock-prices.js` (live ticker), `ai-chat.js`, `auth.js`, `theme.js`.
- Theme: light/dark by time of day unless the user overrides (`localStorage.theme`).
- Live prices on stock pages (main ticker + "People also watch" cards) come from
  `stock-prices.js` → Lambda price proxy, refreshed every 5 s. Pages opened from local files
  show `--` (the proxy only answers the live site), which is expected.
- Utility pages with no footer, not in the sitemap: `clear-cache.html`,
  `market-data-sidebar.html`, `market-data-widget.html`.
- Lambda function URLs are hard-coded in the JS/HTML. `stockiq/lambda-url-mapping.json` maps
  each URL to its function name (regenerate with `generate-lambda-url-mappings.sh`).

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
  (`git diff --stat 2485162 7e14c8f`); `check_news_sync.py`, `update_sitemap.py` and
  `generate_sitemap.py` were also changed and have not been re-audited against their Sep 25 versions.
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
- `check_news_sync.py` had its news-window logic removed by the same Oct 2 commit; restored from 2485162.
- **`update_stock_analysis.py` was missing from deploy-to-s3.sh** (Oct 2026). Stock data was stale from Sep 24. It's now in the pipeline. If stock pages ever show old dates again, check it's still in deploy-to-s3.sh.
- A stray `test-news-layout.html` was publicly live on S3 (deleted 25 Sep 2026). Check S3 for files with no local
  copy occasionally (`aws s3api list-objects-v2 --delimiter /`).

## 10. Working rules for AI assistants

- The owner works in **Kiro** and hadn't touched the site for months before Sep 2026. Explain
  in plain terms what a script does and what will change, and confirm facts against the code
  and live site rather than assuming.

- Ask the owner before any S3 upload or GitHub push. Show the `DRY_RUN=true` output as the
  approval list. Remember the daily job deploys anything changed in `website/` automatically.
- No extra backups are needed before changes: the daily deploy backups in `~/VSCODE/backup/`
  (30 days, both folders incl. `stocks/`) plus GitHub are enough. The owner does not want
  additional backup copies made.
- Change generators and templates, not generated pages (section 4).
- **Wording that lowers legal risk (owner's instruction, 9 Oct 2026; StockIQ holds no financial services
  licence):** describe, don't advise. On pages, in emails and in the AI chat: no "you should buy/sell", no
  "picks", "winning stocks", "recommendations", price targets or predictions presented as StockIQ's view; say
  "scores", "signals", "screener rankings", "what the data shows". The AI chat prompt (`stockiq-ai-chat`) must
  keep its rule never to give buy/sell/hold calls, price targets or picks. Keep the footer disclaimer and the
  no-licence statement (terms.html, about.html). Educational text about how technical analysis works is fine.
- Verify claims against code or data before putting them on public pages (accuracy, user
  counts and testimonials were removed in Sep 2026 for being unsupported).

## 11. Open items and optimisation ideas

Flagged for the owner (not changed):
- **Advice-style wording in the paid product's output: done 9 Oct 2026.** The product now describes, it does
  not advise. Internal codes (`STRONG BUY` ... `STRONG SELL`, `CONSIDER`, `AVOID`) are still produced by the
  Lambdas and used for logic, but are only ever shown through a label function:
  `signalLabel()` / `horizonLabel()` in `analysis-functions.js`, `signal_label()` / `horizon_label()` in the
  coordinator and crypto orchestrator, `signal_label()` in the report Lambda. Labels: Strongly positive, Positive,
  Slightly positive, Mixed, Slightly negative, Negative, Strongly negative. Stop loss / take profit are shown as
  "Lower / Upper reference level"; buy limit / buy stop as "Pullback / Breakout level"; "Profit probability" as
  "Model probability estimate"; strategy as "Horizon". CSV headers changed to match (`Signal`, `Lower_Level`,
  `Upper_Level`, `Model_Probability_%`, `Horizon`, `Horizon_Days`). Scoring and numbers were not changed
  (old vs new compared on identical data for the report, all 8 page formatters and a Dow 30 background run).
  - Changed: `stockiq-option-1-1-custom-analysis` (report; also fixes the company name, which was cut at the
    first comma because stocks.txt was split with `split(',')`), `stockiq-screener-coordinator` (background runs),
    `stockiq-option-7-1-orchestrator` (crypto), `analysis-functions.js`, the dashboard performance popup
    (it used to say "The AI predicted upward movement" whenever the price was up), and the FAQ.
  - Previous Lambda code (not in git): `~/VSCODE/backup/*_before_neutral_wording_20261009.zip` (3 files).
  - **Keep it this way:** any new formatter must print `signalLabel(x.recommendation)`, never the raw code, and
    must not print "buy", "sell", "stop loss", "take profit", "target", "position size" or "recommendation".
    The dashboard tracker parses only the symbol and price at the start of numbered lines; don't change those.
  - Not changed: the ~630 screener worker Lambdas still return the raw codes and a few descriptive breakdown
    strings ("RSI Buy Zone"); three Lambdas with old wording are not called by the site
    (`stockiq-option-3-1-us-screener`, `stockiq-option-3-1-sp100`, `stockiq-option-3-dynamic-coordinator`).
- **Why the page score and the app score differ (AAPL 71 vs 47, checked 9 Oct 2026).** Same model, different
  inputs: (1) the page uses the previous close, the app uses the live price, and the trend factor is a cliff:
  0.1% below the 20-day average turned "Strong Uptrend +12" into "Below 20-day MA -6" (18 points); (2) the page
  had "Near 52-week high -5", the app did not after the drop (+5); (3) the app (Finnhub) had no revenue growth
  for AAPL while the page (Yahoo) had "+8"; (4) during market hours the app compares part-day volume with a
  full-day average and scores "Low Volume -3". 71 - 18 + 5 - 8 - 3 = 47. Not fixed (these are scoring changes):
  the part-day volume penalty is an artefact worth removing, and a fallback to Yahoo for missing Finnhub
  fundamentals would make the two agree more often. If either is changed, change `stock_metrics.py` too.
- Legal (owner's facts, 9 Oct 2026): the business is "StockIQ", online-only with no physical address, and
  holds **no financial services licence**. Billing is in **USD** (confirmed on the three live Stripe prices:
  $4.99 / $14.99 / $49.99 per month). The terms, About page, pricing section and FAQ now say all of this.
  Not legally reviewed: whether issuing BUY/SELL/HOLD signals without a licence is acceptable under Australian
  law is a question for a lawyer, not something the wording settles.
- Screener weights really do total 102% in the worker code (0.18+0.08+0.06+0.20+0.20+0.10+0.06+0.05+0.03+
  0.03+0.02+0.01). The About and FAQ pages now say so. Changing the code would change every screener score.
- Dashboard plan cards list features that are not verified to differ by plan ("Advanced screening & alerts",
  "Portfolio tracking", "White-label options", "Dedicated support"), while the FAQ says all plans get the same
  features. Old accounts also carry legacy limits (Starter 50/day, Pro 200/day); new purchases get 15/50/unlimited.
- Home page comparison table still benchmarks against Bloomberg ($24,000/yr) and Morningstar.
- Analysis page: 12 "Coming Soon" screener buttons; Nikkei 225 is labelled 210 stocks (the real count covered).
- Guides are ~800 words of definitions with no worked examples.
- Usage badge (`#trial-status-display`, created in `auth.js`, fixed top-right) overlaps the index cards under
  the nav. Bottom-left is taken by the anonymous "Start 3-Day Free Trial" sticky button, so it needs a proper
  placement decision, not a quick move.
- Mobile: owner reports the page zooms when tapping the AI chat input (input is already 16px; cause not found).
- News `data-timestamp` values on stock pages get bumped past the article date
  (e.g. 0006.HK showed 16 Sep for a 10 Sep article). This inflates sitemap lastmod; the cause
  is not found yet (look in `update_stock_news.py`).

Ideas:
- Review Search Console 6–8 weeks after 25 Sep 2026: impressions and clicks on the 962 indexed
  pages; consider the $2B threshold if they perform.
- Backlinks remain the biggest lever (see `backlinks-progress.md`).
- Link to indexed stock pages from index.html, the guides and analysis results (internal links).
- news.html `<title>` still says "Free Stock Analysis Guide & Investment Blog". Rename it to match its content.
- "People also watch" Fix 1 and Fix 2 in `future-work.md`.
- `fix_amazonq_chat.sh` is obsolete (Amazon Q is not used).
- `update_news.py` `MAX_BLOG_ARTICLES` stays commented out on purpose. Trimming is done by
  `finalize_news_html.py` with separate stock/general limits.

## 12. Quick checks

```bash
cd /Users/dave/VSCODE/stockiq
python3 check_news_sync.py                                   # news sync + coverage
python3 update_stock_analysis.py AAPL 7203.T --dry-run       # snapshot logic without writing
DRY_RUN=true ./deploy-to-s3.sh                               # what would upload / push
grep -l 'content="index, follow"' ../website/stocks/*.html | wc -l   # indexed stock pages
curl -s https://stockiq.tech/sitemap.xml | grep -c '<ns0:url>'      # live sitemap size
```

**Test a template change safely** (before running `generate-stock-pages.py` for real):
```bash
T=$(mktemp -d); cp -R ../website/stocks $T/stocks; cp -R $T/stocks $T/orig
sed "s#/Users/dave/VSCODE/website/stocks\"#$T/stocks\"#" generate-stock-pages.py > $T/gen.py
python3 $T/gen.py && diff -r $T/orig $T/stocks | head -100    # check only intended lines change
```
Also check that every page's NEWS and RELATED sections are byte-identical before and after.

**Screenshot a page** (headless Chrome): copy the page next to `styles.css` etc., or use the
live URL:
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --window-size=1300,2200 \
  --screenshot=/tmp/page.png https://stockiq.tech/stocks/AAPL.html
```
Narrow window sizes look cut off in headless mode even for unchanged pages; that's a headless
quirk, not a layout bug.

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

- **9 Oct 2026** (Claude Code session, recovery + site text):
  - Found and fixed the Oct 2 revert of `generate-stock-pages.py` and `deploy-to-s3.sh` (section 9). All
    3,467 pages regenerated with the correct template; 956 indexable, rest noindex; deployed.
  - Site text: removed unsupported accuracy claims, "real-time"/"zero delay", conflicting counts; added a
    "general information only, not financial advice" footer line to public pages; FAQ and terms plan names
    and limits now match the payment Lambda (Starter 15/day, Pro 50/day, Elite unlimited).
  - Home page email signup reworded (no giveaway, no 6 AM promise); `stockiq-email-capture` now emails
    `noreply@stockiq.tech` on each signup. Details: `stockiq.md` "Email Signup List".
  - `.gitignore` in both repos restored (`.last_*`, `.analysis_cache/`, `__pycache__/`,
    `stocks-backup-before-restore/`).
  - `add-new-screener.md` completed against the Japan code (India next).
