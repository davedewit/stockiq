# Script Reference Guide

All key scripts have detailed docstrings — run `head -50 script.py` to read them first.
For the pipeline order and deploy commands see `site-overview.md` section 5.
For adding screeners see `add-new-screener.md`. For adding stocks see `add-new-stocks.md`.

## Daily Pipeline Scripts (run by deploy-to-s3.sh)

| Script | What it does | Cooldown |
|---|---|---|
| `update_news.py` | Yahoo/Google RSS → OpenAI summaries → news.html + news.js | 2 hours |
| `update_stock_news.py` | Per-stock RSS → stock pages + news.html/news.js. Keeps last 3 articles per stock, removes articles 30+ days old | 23h per stock |
| `update_stock_analysis.py` | Data snapshot + 0-100 score on large caps, sets index/noindex, writes indexable_stocks.txt. Runs on all 3,467 stocks — ~20 min, mostly free (Yahoo Finance). 404s for delisted stocks are normal and cached | none (runs every deploy) |
| `people_also_watch_stocks.py --missing` | Adds "People also watch" section to pages missing it | none |
| `update_sitemap.py` | **Rebuilds** stock URLs from indexable_stocks.txt (only large-cap pages), updates lastmod on site pages. Safety: skips if indexable list < 200 entries | none |
| `cleanup_broken_links.py` | Removes dead article links from news.html | none |
| `remove_news_duplicates.py` | Deduplicates news.html | none |
| `finalize_news_html.py` | Trims news.html to 240 stock + 60 general articles, keeps noindex | none |

## Manual / One-Off Scripts

| Script | When to use |
|---|---|
| `fetch_stock_data.py` | After adding new stocks — fetches names/sectors from Yahoo, updates stocks.txt and NUMERIC_COMPANY_NAMES |
| `generate-stock-pages.py` | After template changes — regenerates all 3,467 HTML pages (preserves NEWS/RELATED/ANALYSIS sections) |
| `Sync_stock_to_news.py` | When news.html is out of sync — pushes stock page news → news.html |
| `sync_news_to_stock_pages.py` | When stock pages are missing news that's in news.html |
| `clear_stock_news.py` | Nuclear reset — clears ALL news from all stock pages |
| `check_news_sync.py` | Verify news sync status and coverage stats |
| `test_stock_rss.py` | Before adding a stock — check if it has RSS news (last ~20 days) |
| `generate_sitemap.py` | Manual sitemap rebuild (update_sitemap.py is the daily version) |
| `notify_search_engines.py` | Ping Google/Bing IndexNow after sitemap changes |

## Deploy Scripts

**`deploy.sh`** — Full deploy: asks about news update, then calls deploy-to-s3.sh. Use when you want news updated too. Costs ~$1-2 (OpenAI).

**`deploy-to-s3.sh`** — S3 sync only (no news update unless `UPDATE_STOCK_NEWS=true`). Use after editing HTML/JS/CSS. Preview first with `DRY_RUN=true ./deploy-to-s3.sh`. Cost $0.

## Troubleshooting

| Issue | Fix |
|---|---|
| News not updating | Check 2h/23h cooldowns; verify `OPENAI_API_KEY` is set |
| Stock page news gaps | Normal — script only picks up articles that clearly match the stock from last 2 days |
| Stock data showing old date | `update_stock_analysis.py` not running — check it's in deploy-to-s3.sh (was missing until Oct 2026) |
| Stock pages not regenerating | Run `generate-stock-pages.py`; check stocks.txt CSV format |
| NUMERIC_COMPANY_NAMES out of sync | Run `fetch_stock_data.py` |
| News out of sync | Run `Sync_stock_to_news.py` (next deploy trims it back) |
| Sidebar shows no news | `node -c /Users/dave/VSCODE/website/news.js` |
| Sitemap has too many URLs (all 3,485) | `generate_sitemap.py` was adding all HTML files — it's now fixed to use indexable_stocks.txt only. Run `python3 update_sitemap.py` to rebuild, then resubmit in Google Search Console |
| analysis-functions.js not updating on live site | Deploy script now uploads all root `*.js` — but if running manually: `aws s3 cp analysis-functions.js s3://stockiq-final-websitebucket-vqekic7enf9h/ --cache-control "public, max-age=86400" --profile default --region us-east-1` |

## Google Search Console

- Sitemap URL: `https://stockiq.tech/sitemap.xml`
- Should show ~970 URLs (953 large-cap stock pages + 17 site pages)
- If it shows 3,485 URLs the sitemap bloated again — check `generate_sitemap.py` wasn't run, then run `python3 update_sitemap.py` and resubmit
- Resubmit: Search Console → Sitemaps → three dots → Resubmit
- Delete the broken `sitemap.xmp` entry if it still appears
- After any sitemap change allow 1-2 weeks for Google to reprocess

## Python Path
Scripts use `/opt/homebrew/bin/python3` (set as `$PYTHON` in deploy-to-s3.sh). Run manually with `python3` or `/opt/homebrew/bin/python3`.
