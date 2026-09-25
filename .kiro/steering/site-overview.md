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
- Owner edits in **Kiro** (not VS Code). The top folder is still named `/Users/ddewit/VSCODE`.

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

- S3 versioning is **Suspended**: an overwrite cannot be rolled back from S3. Back up first
  (`aws s3 sync s3://<bucket> ~/Backups/s3_<timestamp>`).
- `stockiq/lambda-sync/` is a local mirror of the deployed Lambda code, refreshed hourly by the
  deploy script. It is gitignored. Read it to see what production runs.

## 3. Folders and git repos

| Folder | GitHub repo | Notes |
|---|---|---|
| `/Users/ddewit/VSCODE/website/` | `davedewit/stockiq-website` | What is served. `stocks/` and `.last_*` markers are gitignored, so stock pages exist only locally and on S3 |
| `/Users/ddewit/VSCODE/stockiq/` | `davedewit/stockiq` | Scripts, Kiro steering. `lambda-sync/`, `.analysis_cache/`, `*.json` are gitignored |
| `~/VSCODE/backup/` | – | Daily rsync backups made by the deploy (30-day retention) |
| `~/Backups/` | – | Manual zips + full S3 download taken before big changes |

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

launchd `com.stockiq.reminder` fires every 10 min → `~/stockiq-reminder.scpt` runs once a day
**Mon–Sat, 11am–3pm** (lock `/tmp/stockiq-deploy-YYYYMMDD.lock`) → `deploy.sh` →
`deploy-to-s3.sh` with `UPDATE_STOCK_NEWS=true`. Log: `~/stockiq-daily.log` (cleared each run).

Order inside `deploy-to-s3.sh`:
1. `update_news.py`: Yahoo/Google RSS → OpenAI summaries → news.html + news.js (2-hour cooldown)
2. `update_stock_news.py`: per-stock news into stock pages + news.html/news.js (23-hour cooldown per stock)
3. `update_stock_analysis.py`: snapshots on large caps, robots, `indexable_stocks.txt`
4. Backups (website + stockiq; prod_scripts every 23h)
5. `people_also_watch_stocks.py --missing`
6. `update_sitemap.py`: stock URLs = `indexable_stocks.txt`, drops news.html, updates lastmod
7. `cleanup_broken_links.py`, `remove_news_duplicates.py`, `finalize_news_html.py`
8. S3 upload:
   - `stocks/`: `aws s3 sync --delete` (size + mtime), 24h cache
   - `js/`: sync --delete, 24h cache
   - root `*.html` (1h cache), `*.css` (24h), `*.js` (24h; news.js 1h): uploaded when local MD5 ≠ S3 ETag (one listing call)
   - images (7d), and `stocks.txt robots.txt sitemap.xml`
9. CloudFront invalidation `/*` (waits for completion), `notify_search_engines.py` (IndexNow; "202" means accepted)
10. `sync-all-lambdas.sh` (hourly cooldown)
11. Git: once per 23h, for **both** repos: commit if changed → `pull --rebase` → push.
    Marker `website/.last_git_push` is only updated when both succeed.

Preview without uploading or pushing: `cd stockiq && DRY_RUN=true ./deploy-to-s3.sh`.
It still runs the local steps (backups, sitemap, news trim), then prints `(dryrun)` lines.

## 5b. GitHub: pushing, pulling and the daily sync

**Two repos, both on `main`:**
- `website/` → `davedewit/stockiq-website`: site files, news.html, news.js, sitemap.xml.
  `stocks/*.html` is **not** in git (gitignored), so stock pages exist only locally, on S3 and in backups.
- `stockiq/` → `davedewit/stockiq`: scripts, `indexable_stocks.txt`, Kiro steering.
  `lambda-sync/` and `.analysis_cache/` are not in git.

**Pushing to GitHub does not change the live site.** Only `deploy-to-s3.sh` (daily or by hand)
uploads to S3. The daily deploy also pushes to GitHub, at most once every 23h.

**Daily run (automatic):** the last step of `deploy-to-s3.sh`, for each repo in turn:
1. If there are changes: `git add -A` + commit "Auto-update: <UTC time>"
2. `git pull --rebase` (brings in commits made elsewhere, e.g. by cloud sessions)
3. `git push`
4. `website/.last_git_push` is updated only if both repos succeed; otherwise it retries next run.

If a rebase conflicts, the log (`~/stockiq-daily.log`) says "could not rebase onto GitHub
(conflict) - not pushed". That repo then needs a manual look; the other repo still pushes.

**When the owner says "push" / "update GitHub" (manual):**
```bash
cd /Users/ddewit/VSCODE/stockiq  && git status -sb    # repeat for ../website
git add -A && git commit -m "<what changed and why>"   # descriptive message, not "Auto-update"
git pull --rebase && git push
```
- Do both repos if both changed. Show the owner what will be pushed first (`git log @{u}..HEAD`).
- Pushing by hand does not reset the daily 23h timer. The next daily run simply finds nothing
  new, or pushes its own "Auto-update" commit.
- If the owner also wants the site updated: run `DRY_RUN=true ./deploy-to-s3.sh`, get approval,
  then `./deploy-to-s3.sh`.

**Changes made elsewhere (Claude cloud sessions, GitHub web edits):**
- They arrive as a branch (e.g. `claude/new-session-…`) or as commits on `main`.
- To bring a branch in: `git fetch`, check that the branch doesn't touch files with local
  uncommitted edits, then `git merge --ff-only origin/<branch>` (stash local marker/generated
  changes first if needed). Then deploy to make it live.
- Generated files (news.html, news.js, sitemap.xml) change every day locally. If a remote
  commit also changed them, keep the **local** version; they are regenerated anyway.
- Cloud sessions cannot see `stocks/` or run the pipeline. Stock page changes must be made in
  `generate-stock-pages.py` or a section script, then run locally.

**Check sync state:** `git status -sb` in both repos (ahead/behind). Compare the live site
with local via `DRY_RUN=true ./deploy-to-s3.sh`: an empty upload list means S3 matches.

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
- A stray `test-news-layout.html` was publicly live on S3. Check S3 for files with no local
  copy occasionally (`aws s3api list-objects-v2 --delimiter /`).

## 10. Working rules for AI assistants

- Ask the owner before any S3 upload or GitHub push. Show the `DRY_RUN=true` output as the
  approval list. Remember the daily job deploys anything changed in `website/` automatically.
- Back up (zip both folders + S3 download to `~/Backups/`) before large changes.
- Change generators and templates, not generated pages (section 4).
- Verify claims against code or data before putting them on public pages (accuracy, user
  counts and testimonials were removed in Sep 2026 for being unsupported).

## 11. Open items and optimisation ideas

Flagged for the owner (not changed):
- Homepage "First 1,000 subscribers: 5 winners get 1 YEAR FREE" giveaway. Confirm it runs, or remove it.
- Homepage "Real-time data: zero delay" and "Bank-Level Security". Yahoo data is often delayed.
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
cd /Users/ddewit/VSCODE/stockiq
python3 check_news_sync.py                                   # news sync + coverage
python3 update_stock_analysis.py AAPL 7203.T --dry-run       # snapshot logic without writing
DRY_RUN=true ./deploy-to-s3.sh                               # what would upload / push
grep -l 'content="index, follow"' ../website/stocks/*.html | wc -l   # indexed stock pages
curl -s https://stockiq.tech/sitemap.xml | grep -c '<ns0:url>'      # live sitemap size
```
