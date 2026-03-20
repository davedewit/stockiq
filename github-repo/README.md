# StockIQ - Stock Analysis Automation Scripts

Python scripts for automating stock news aggregation, page generation, and content management for [StockIQ.tech](https://stockiq.tech) - a professional stock analysis platform.

## 🚀 Features

- **Automated News Aggregation**: Fetches and filters stock news from Yahoo Finance RSS feeds
- **AI-Powered Summaries**: Generates concise news summaries using OpenAI GPT-4o-mini
- **SEO-Optimized Pages**: Generates 3,400+ individual stock pages with proper metadata
- **Smart Matching**: Matches news articles to stocks using company names and symbols
- **Sync Verification**: Diagnostic tools to ensure content consistency across all pages

## 📊 About StockIQ

[StockIQ.tech](https://stockiq.tech) is a professional investment research platform offering:

- **AI-Powered Stock Analysis**: Comprehensive technical and fundamental analysis
- **Real-Time Data**: Live market data and trading signals
- **3,400+ Stock Pages**: Individual pages for US and international stocks
- **Automated News Updates**: Latest news with AI summaries for 1,500+ stocks
- **Free Trial**: 15 free analyses to get started

Visit [stockiq.tech](https://stockiq.tech) to try it out!

## 🛠️ Scripts

### update_stock_news.py
Fetches recent news for stocks and updates individual stock pages with AI-generated summaries.

**Features:**
- Filters by critical keywords (earnings, mergers, FDA approvals, etc.)
- 23-hour cooldown per stock to avoid duplicates
- Matches US stocks via CSV parsing and non-US stocks via fallback dictionary
- Updates homepage sidebar and news archive

**Usage:**
```bash
python3 update_stock_news.py              # Check all stocks
python3 update_stock_news.py AAPL         # Single stock
python3 update_stock_news.py "AAPL,MSFT"  # Multiple stocks
```

### generate-stock-pages.py
Generates SEO-optimized HTML pages for 3,400+ stocks.

**Features:**
- Preserves existing news and related sections when regenerating
- Includes Open Graph, Twitter Card, and JSON-LD schemas
- Handles quoted company names with commas (proper CSV parsing)
- Removes orphaned pages automatically

**Usage:**
```bash
python3 generate-stock-pages.py           # All stocks
python3 generate-stock-pages.py AAPL      # Single stock
```

### fetch_stock_data.py
Fetches company names and sectors from Yahoo Finance and updates stocks.txt.

**Features:**
- Auto-updates NUMERIC_COMPANY_NAMES for non-US stocks (Hong Kong, Japan)
- Removes stocks that return no data
- Proper CSV formatting with quoted names

**Usage:**
```bash
python3 fetch_stock_data.py
```

### check_news_sync.py
Diagnostic tool that verifies news is in sync across all files.

**Features:**
- Shows coverage stats (% of stock pages with news)
- Detects broken links, missing articles, orphaned entries
- Tracks changes between runs (saves stats every 23+ hours)
- Provides actionable fix commands

**Usage:**
```bash
python3 check_news_sync.py
```

## 📋 Requirements

```bash
pip install yfinance requests beautifulsoup4 openai python-dateutil
```

## 🔑 Environment Variables

```bash
export OPENAI_API_KEY=sk-...
```

Or create `~/.openai_key` with your API key.

## 📈 Stats

- **3,467 stocks** tracked (US + international)
- **1,500+ stock pages** with news coverage (46%)
- **2,500+ articles** in news archive
- **100-item sidebar** (80 stock + 20 general news)

## 🌐 Live Site

Check out the live platform at [stockiq.tech](https://stockiq.tech)

## 📝 License

MIT License - Feel free to use these scripts for your own projects!

## 🤝 Contributing

Found a bug or have a suggestion? Open an issue or submit a pull request!

---

Built with ❤️ for [StockIQ.tech](https://stockiq.tech)
