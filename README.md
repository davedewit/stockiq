# StockIQ Automation Scripts

Python automation for [StockIQ.tech](https://stockiq.tech) - AI-powered stock analysis platform.

## 🚀 Features

- **Automated News**: Fetches stock news from Yahoo Finance RSS
- **AI Summaries**: GPT-4o-mini generates concise summaries
- **SEO Pages**: Generates 3,467 stock pages with metadata
- **Smart Matching**: Matches news to stocks by company names

## 🛠️ Key Scripts

- `update_stock_news.py` - Fetch news and update pages
- `generate-stock-pages.py` - Generate SEO-optimized HTML (the stock page template)
- `update_stock_analysis.py` - Daily data snapshot and score on large-cap stock pages; decides which pages are indexed
- `finalize_news_html.py` - Trims news.html and keeps it noindex
- `fetch_stock_data.py` - Fetch company data from Yahoo Finance
- `deploy-to-s3.sh` - Deploy to AWS S3 + CloudFront

## 📊 Live Platform

Visit [stockiq.tech](https://stockiq.tech) for AI-powered stock analysis.

Built with ❤️ for [StockIQ.tech](https://stockiq.tech)
