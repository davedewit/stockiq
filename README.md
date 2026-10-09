# StockIQ Automation Scripts

Python automation powering [StockIQ.tech](https://stockiq.tech) - a professional AI-driven stock analysis platform with 3,467 stock pages, real-time data, and intelligent news aggregation.

## 🚀 What This Powers

**Live Platform:** [stockiq.tech](https://stockiq.tech)

- 📊 **3,467 stock pages** (US, Europe, Asia) with SEO optimization
- 📰 **Automated news updates** - 3,148 pages with current news
- 🤖 **AI summaries** via GPT-4o-mini (OpenAI)
- 🔍 **Market screeners** - S&P 500, Russell 2000, FTSE 100, Nikkei 225
- 💬 **AI chat assistant** with live prices and conversation memory
- 📈 **Trading signals** and technical analysis

## 🛠️ Key Scripts

### News & Content
- `update_stock_news.py` - Fetch Yahoo Finance RSS → match to stocks → AI summarize
- `update_news.py` - Market news aggregation with 2-hour cooldown
- `Sync_stock_to_news.py` - Sync news between stock pages and news archive

### Page Generation
- `generate-stock-pages.py` - Generate 3,467 SEO-optimized HTML pages
- `update_stock_analysis.py` - Daily data snapshots + index/noindex decisions
- `people_also_watch_stocks.py` - Related stocks section with live prices

### Data
- `fetch_stock_data.py` - Yahoo Finance company data + auto-sync non-US stocks
- `stock_metrics.py` - 0-100 scoring system (mirrors Lambda logic)

### Deploy
- `deploy.sh` - Full pipeline (news + analysis + S3 sync)
- `deploy-to-s3.sh` - S3 upload + CloudFront invalidation + git push

### Utilities
- `check_news_sync.py` - Verify news sync across all pages
- `cleanup_broken_links.py` - Remove dead article links
- `finalize_news_html.py` - Trim news.html to 240 stock + 60 general articles

## 🏗️ Architecture

```
Python Scripts (local)
    ↓
AWS S3 (static hosting)
    ↓
CloudFront CDN
    ↓
~680 Lambda Functions (analysis, screeners, auth)
    ↓
DynamoDB + OpenAI API
```

### Tech Stack
- **Language:** Python 3.14
- **Cloud:** AWS (S3, Lambda, CloudFront, Cognito, DynamoDB)
- **AI:** OpenAI GPT-4o-mini
- **Data:** Yahoo Finance, Finnhub
- **Frontend:** Vanilla JS (analysis-functions.js is 310KB)
- **Auth:** AWS Cognito + Google/Facebook OAuth
- **Payment:** Stripe

## 📖 Documentation

Complete docs in `.kiro/steering/`:
- `site-overview.md` - Architecture, deploy pipeline, SEO strategy
- `script-reference.md` - Every script documented
- `lambda-reference.md` - All 680 Lambda functions
- `add-new-screener.md` - How to add regional screeners
- `stock-matching-system.md` - News → stock matching logic

## 🎯 Key Features

### Intelligent News Matching
- **3,323 letter symbols** (AAPL, TSLA, etc.) - dynamic from stocks.txt
- **144 numeric symbols** (0700.HK, 7203.T) - hardcoded fallback
- Keyword extraction + company name matching
- 23-hour cooldown per stock (prevents duplicate fetches)

### SEO Strategy
- **962 large-cap pages** (≥$10B market cap) → "index, follow" with daily snapshots
- **2,505 small-cap pages** → "noindex, follow" (internal links only)
- Sitemap: 979 URLs (962 stocks + 17 site pages)
- WebPage schema + GA4 on all pages

### Daily Pipeline
Runs Mon-Sat, 11am-3pm via launchd:
1. Update market news (2h cooldown)
2. Update stock news (~60-90 stocks/day, 23h cooldown each)
3. Update analysis snapshots on large caps
4. Sync sitemap, cleanup duplicates, trim news.html
5. Upload to S3, invalidate CloudFront
6. Git commit + push (both repos, 23h cooldown)

## 📊 Stats

- **Stock pages:** 3,467 (US, Tokyo, London, Hong Kong, Sydney, Paris, etc.)
- **Pages with news:** 3,148
- **Indexed pages:** ~962 (large caps only)
- **Lambda functions:** ~680 (50 named + 630 screener workers)
- **Deploy time:** ~15-20 min (with news updates)
- **News articles:** 240 stock + 60 general (trimmed daily)

## 🚀 Live Platform

**Try it:** [stockiq.tech](https://stockiq.tech)

- 3-day free trial (15 analyses)
- Starter: $4.99/month
- Pro: $14.99/month  
- Elite: $49.99/month

## 📫 Contact

Built by Dave for [StockIQ.tech](https://stockiq.tech) - making professional investment research accessible to everyone.

---

⭐ **Like this project?** Check out the [live platform](https://stockiq.tech) or give it a star!
