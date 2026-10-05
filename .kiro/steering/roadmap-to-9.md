# StockIQ Roadmap

**Current Score: 8.7/10** (as of Oct 2026)

## What's Built
- ✅ Serverless infrastructure (Lambda, S3, CloudFront, DynamoDB)
- ✅ 3,467 stock pages with automated daily news + data snapshots
- ✅ Auth (Cognito + Google/Facebook OAuth), Stripe payments, dashboard
- ✅ Trial system: 15 analyses over 3 days. Plans: Starter $4.99, Pro $14.99, Elite $49.99
- ✅ AI Stock Chat (GPT-4o-mini, all pages)
- ✅ SEO: 962 large-cap pages indexed (≥$10B), WebPage + Corporation schema, GA4
- ✅ Screeners: US (S&P, Russell, NASDAQ, Dow), ASX 50/100/200/300, UK FTSE 100, Japan Nikkei 225
- ✅ Bot/subnet protection on anonymous usage tracker

## Open Items (Priority Order)

### 1. Price Alerts (HIGH — not built)
DynamoDB `stockiq-price-alerts`, Lambda checker (EventBridge hourly), email via Cognito.
Uses existing email infrastructure, cost $0/month. See old roadmap for full spec.

### 2. Screeners — India BSE Sensex, South Korea KOSPI (MEDIUM)
See `add-new-screener.md` for complete process. India next (Coming Soon button already in analysis.html).

### 3. Backlinks (ONGOING)
4-5 backlinks as of March 2026 (X, StockTwits, TradingView, Medium). See `backlinks-progress.md`.
Check Search Console → Links for current count. Target: 20+ quality links.

### 4. People Also Watch improvements
See `future-work.md` Fix 1 — replace hybrid logic with pure anchor stocks per sector.

### 5. Internal linking
Link to indexed stock pages from index.html, guides, and analysis results.

## Traffic / Revenue
- March 2026: 13 visitors/month, $0 revenue, 603/3,469 pages indexed
- Sep 2026: sitemap cut to 979 URLs (962 large caps), GA4 added to all pages
- Review Search Console ~6 weeks after 25 Sep 2026 for indexing progress
