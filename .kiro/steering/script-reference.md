# Script Reference Guide

All key scripts have detailed docstrings — run `head -50 script.py` to read them first.
For the pipeline order and deploy commands see `site-overview.md` section 5.
For adding screeners see `add-new-screener.md`. For adding stocks see `add-new-stocks.md`.

## Daily Pipeline Scripts (run by deploy-to-s3.sh)

| Script | What it does | Cooldown |
|---|---|---|
| `update_news.py` | Yahoo/Google RSS → OpenAI summaries → news.html + news.js | 2 hours |
| `update_stock_news.py` | Per-stock RSS → stock pages + news.html/news.js. Keeps last 3 articles per stock, removes articles 30+ days old. Fetches articles from the last **7 days** (2, then 4 until 18 Oct 2026: the laptop is often off a few days at a time). Keeps only "critical" news (`CRITICAL_KEYWORDS`: earnings, acquisition, upgrade, CEO, dividend …), **except that a page with no news at all takes the newest article clearly about its company** (24 Oct 2026: RHC.AX was empty; 49 of the 946 indexed pages had none, all outside the US) | 23h per stock |
| `update_stock_analysis.py` | Data snapshot + 0-100 score on large caps, sets index/noindex, writes indexable_stocks.txt. Runs on all 3,467 stocks — ~20 min, mostly free (Yahoo Finance). 404s for delisted stocks are normal and cached | none (runs in the daily run, i.e. when `UPDATE_STOCK_NEWS=true`; skipped by a plain `./deploy-to-s3.sh`) |
| `publish_company_figures.py` | Straight after `update_stock_analysis.py`: puts the company figures that step keeps for every stock (`.analysis_cache/info/`) into one private file on S3 for the single-stock report, which has none of its own for shares outside the US. Refuses to upload fewer than 1,000 stocks; never stops the deploy; `--dry-run` only builds the file. Calls `aws` by its full path (launchd's PATH has no Homebrew: its first daily run, 12 Oct 2026, could not upload). Once a week it also keeps a dated copy in `research-data/company-figures/` (not in git), so that a history of company figures builds up | none (daily run only) |
| `update_home_stock_links.py` | The home page's "Stock Pages" section (links to the largest indexed companies of each market, between its markers) and `website/stock-pages.js` (every share with a page, for `market-panel.js`). Refuses with fewer than 20 links. `--dry-run`; `LINKS_OUT=<folder>` writes into a staged copy | none (daily run only, after the snapshot step) |
| `update_screener_pages.py` | The daily public screener pages: 24 markets' top 10 by trend and the hub `screeners-today.html`, from the coordinator on AWS. Each page carries the market panel (`PANEL`, since 24 Oct 2026). `--dry-run`; `PAGES_OUT=<folder>` writes into a staged copy; keys as arguments (`3-8 5-dax40`) for only those | none (daily run only) |
| `people_also_watch_stocks.py --missing` | Adds "People also watch" section to pages missing it | none |
| `update_sitemap.py` | **Rebuilds** stock URLs from indexable_stocks.txt (only large-cap pages), updates lastmod on site pages. Safety: skips if indexable list < 200 entries | none |
| `cleanup_broken_links.py` | Removes dead article links from news.html | none |
| `remove_news_duplicates.py` | Deduplicates news.html | none |
| `finalize_news_html.py` | Trims news.html to 240 stock + 60 general articles, keeps noindex | none |

## Manual / One-Off Scripts

| Script | When to use |
|---|---|
| `fetch_stock_data.py` | After adding new stocks — fetches names/sectors from Yahoo, updates stocks.txt and NUMERIC_COMPANY_NAMES |
| `check-tools/stage_web.py` | Stages website files for a deploy in one command: `<name> <files>`, `--changed`, `--from <folder>`; writes `pending-<name>/deploy.sh` for `web_deploy.sh` |
| `check-tools/lambda_deploy.sh` | The shared Lambda deploy (checks, rollback zip, mirror): a pending `deploy.sh` hands it `FUNCS` |
| `shared_parts.py` | The menu (desktop and phone) and the footer of every page, defined once: change it there, run it, deploy. `--check` (read-only) lists pages that drifted; `--dry-run` |
| `generate-stock-pages.py` | After template changes — regenerates all 3,467 HTML pages (preserves NEWS/RELATED/ANALYSIS sections) |
| `Sync_stock_to_news.py` | When news.html is out of sync — pushes stock page news → news.html |
| `sync_news_to_stock_pages.py` | When stock pages are missing news that's in news.html |
| `clear_stock_news.py` | Nuclear reset — clears ALL news from all stock pages |
| `check_news_sync.py` | Verify news sync status and coverage stats |
| `test_stock_rss.py` | Before adding a stock — check if it has RSS news (last ~20 days) |
| `generate_sitemap.py` | Manual sitemap rebuild (update_sitemap.py is the daily version) |
| `notify_search_engines.py` | Ping Google/Bing IndexNow after sitemap changes |

## Share-screener workers (`stockiq/workers/`, since 11 Oct 2026)

| Script | What it does |
|---|---|
| `workers/stock_worker.py` | The code all 669 share-screener workers run. `python3 workers/stock_worker.py AAPL BHP.AX` runs it by hand |
| `workers/build.py` | Builds the package and prints its fingerprint; `--lists` writes the Russell lists again from the coordinator |
| `workers/prove.py` | Replays saved prices through the live copy and the changed file and lists every figure that differs (`--fetch` once) |
| `workers/deploy.py` | Deploys the package a group at a time through `check-tools/pending-<name>/deploy.sh`; `--selftest` |
| `workers/create_group.py` | Creates the workers of a new screener (`add-new-screener.md`) |
| `check-tools/workers.py` | Read-only: which group runs what (`--contents` compares the files inside every package) |

## Session checks (`check-tools/`, read-only)

| Script | What it does |
|---|---|
| `session_start.py` | The first command of every session: the account, the bill, logs, live code against the mirrors, the registers, and a numbered list of findings |
| `site_audit.py` | The nightly site check (run by the daily deploy with `--admin`, which puts its findings on the Admin page): stock links, "Loading..." text, broken links, duplicated functions, made-up charts, unused scripts, page weight, counts, titles / descriptions / canonicals, the sitemap, structured data. `AUDIT_WEB=<staging>/web` reads staged files first and saves nothing |
| `clarity_check.py` | Draws the AI autopilot tab and the Admin page with the account's real answers and flags what reads badly (near-identical lines, "A and B and C", a switched-off feature still described, huge menus, "undefined"). `CLARITY_WEB=<staging>/web` for staged files, `--keep` for the text. Run by `session_start.py` |
| `autopilot_review.py` | The weekly review of the autopilot's record |

## Deploy Scripts

**`deploy.sh`** — Full deploy: asks about news update, then calls deploy-to-s3.sh. Use when you want news updated too. Costs ~$1-2 (OpenAI).

**`deploy-to-s3.sh`** — S3 sync only (no news update unless `UPDATE_STOCK_NEWS=true`). Use after editing HTML/JS/CSS. Preview first with `DRY_RUN=true ./deploy-to-s3.sh`. Cost $0.

## Troubleshooting

| Issue | Fix |
|---|---|
| News not updating | Check 2h/23h cooldowns; verify `OPENAI_API_KEY` is set |
| Stock page news gaps | Normal — script only picks up articles that clearly match the stock from the last 4 days |
| Stock data showing old date | `update_stock_analysis.py` not running — check it's in deploy-to-s3.sh (was missing until Oct 2026) |
| Stock pages not regenerating | Run `generate-stock-pages.py`; check stocks.txt CSV format |
| NUMERIC_COMPANY_NAMES out of sync | Run `fetch_stock_data.py` |
| News out of sync | Run `Sync_stock_to_news.py` (next deploy trims it back) |
| Sidebar shows no news | `node -c /Users/dave/VSCODE/website/news.js` |
| Home page Market News shows old articles while newer ones exist | The list is sorted by each item's `timestamp` by display code that `update_news.py` and `update_stock_news.py` write into `news.js` (fixed 13 Oct 2026: it sorted on date text a browser cannot read, so not at all). `node check-tools/news_sidebar_test.js [a copy of the live news.js]` says whether the newest are shown. Also remember the site only changes when the daily run finishes its upload |
| Sitemap has too many URLs (all 3,485) | `generate_sitemap.py` was adding all HTML files — it's now fixed to use indexable_stocks.txt only. Run `python3 update_sitemap.py` to rebuild, then resubmit in Google Search Console |
| Stock page news wiped after running generate-stock-pages.py | Script only preserved news from pages with NEWS_SECTION_START markers — fixed Oct 2026, now also handles old format and shows pre/post count. If news drops: run `python3 sync_news_to_stock_pages.py` to recover from news.html |
| analysis-functions.js not updating on live site | Deploy script uploads all root `*.js` — but if running manually: `aws s3 cp analysis-functions.js s3://stockiq-final-websitebucket-vqekic7enf9h/ --cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript" --profile default --region us-east-1` (browsers keep a script five minutes since 11 Oct 2026; pages are always asked for again. See `site-overview.md` section 5 step 8) |
| Stock news appears in sidebar but not on the stock page | Was caused by `update_stock_news.py` deleting the NEWS section on current-template pages (fixed 9 Oct 2026, see `site-overview.md` section 9). If it happens again: `python3 sync_news_to_stock_pages.py` restores from news.html; it no longer needs a regeneration |
| news.html has fewer articles than expected | Restored from backup needed — check `~/VSCODE/backup/website_backup_<latest>/news.html`, copy back, then run `python3 sync_news_to_stock_pages.py` |

- Sitemap URL: `https://stockiq.tech/sitemap.xml`
- Should show ~975 URLs (about 957 large-cap stock pages + 17 site pages; it moves by a few each day)
- If it shows 3,485 URLs the sitemap bloated again — check `generate_sitemap.py` wasn't run, then run `python3 update_sitemap.py` and resubmit
- Resubmit: Search Console → Sitemaps → three dots → Resubmit
- Delete the broken `sitemap.xmp` entry if it still appears
- After any sitemap change allow 1-2 weeks for Google to reprocess

## Python Path
Scripts use `/opt/homebrew/bin/python3` (set as `$PYTHON` in deploy-to-s3.sh). Run manually with `python3` or `/opt/homebrew/bin/python3`.
