#!/usr/bin/env python3
"""
Update Market News with AI-Generated Summaries

This script:
1. Fetches latest market news from Yahoo Finance RSS feeds
2. Filters by critical keywords (earnings, merger, FDA approval, etc.)
3. Generates AI summaries using OpenAI GPT-4o-mini
4. Updates news.html archive with new articles
5. Updates news.js sidebar with top 5 most recent articles
6. Respects 2-hour cooldown to avoid duplicate updates

Output:
- Updates /Users/ddewit/VSCODE/website/news.html (archive)
- Updates /Users/ddewit/VSCODE/website/news.js (sidebar - top 5)

Usage:
    python3 update_news.py

Requirements:
    - OPENAI_API_KEY environment variable (or ~/.openai_key file)
    - Internet connection for RSS feeds

Features:
- Fetches from Yahoo Finance RSS feeds
- Filters by critical keywords to avoid noise
- Generates concise AI summaries
- Maintains 30-day retention (auto-cleanup)
- 2-hour cooldown between updates

Note:
    - Cost: ~$0.01-0.02 per update (OpenAI API)
    - Runs daily via cron job
    - Can be run manually anytime
"""

import os
import requests
import json
import re
from datetime import datetime, timedelta
import pytz
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

NEWS_JS_PATH = '/Users/ddewit/VSCODE/website/news.js'
NEWS_HTML_PATH = '/Users/ddewit/VSCODE/website/news.html'
STOCKS_DIR = '/Users/ddewit/VSCODE/website/stocks'
MAX_NEWS_ITEMS = 100
MAX_BLOG_ARTICLES = 500

# Load available stock symbols
AVAILABLE_STOCKS = set()
try:
    AVAILABLE_STOCKS = {f.replace('.html', '').upper() for f in os.listdir(STOCKS_DIR) if f.endswith('.html')}
except:
    pass

# Load OpenAI API key from file or environment
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    try:
        with open(os.path.expanduser('~/.openai_key'), 'r') as f:
            OPENAI_API_KEY = f.read().strip()
    except:
        pass

def get_us_eastern_time():
    """Get current time in US Eastern timezone"""
    return datetime.now(pytz.timezone('US/Eastern'))

def fetch_article_content(url):
    """Fetch article text from URL"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text and clean it
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Return first 2000 chars (enough for context)
        return text[:2000]
    except:
        return None

def generate_ai_content(headline, article_text=None):
    """Use OpenAI to generate article content from headline and article text"""
    if not OPENAI_API_KEY:
        return f"{headline}\n\nBreaking market news. Full analysis coming soon."
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        if article_text:
            prompt = f"""Summarize this market news article in 2-3 paragraphs (120-150 words):

Headline: {headline}

Article: {article_text}

Write a professional summary that:
- Highlights the key facts and specific details (stocks, numbers, companies)
- Explains what this means for investors
- Mentions broader market implications
- Keep it factual and forward-looking"""
        else:
            # Extract key info from headline
            prompt = f"""Based on this financial news headline, write a 2-3 paragraph analysis (120-150 words):

"{headline}"

CRITICAL RULES - FOLLOW EXACTLY:
1. DO NOT invent ANY specific numbers, percentages, or dollar amounts
2. DO NOT say things like "rose 1.5%" or "gained $50" or "climbed 2.3%"
3. ONLY use general descriptive terms: "significant gains", "notable increase", "strong performance"
4. If the headline contains specific numbers, you MAY reference those ONLY
5. Focus on implications and context, not fabricated statistics
6. Discuss the companies or events mentioned in the headline
7. Explain what this means for investors
8. Keep it professional and forward-looking

Remember: It's better to be vague than to invent false data."""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cheaper, faster, and follows instructions better for factual tasks
            messages=[
                {"role": "system", "content": "You are a professional financial analyst writing market news summaries. Current context: Donald Trump is the current U.S. President (inaugurated January 2025). Always refer to him as 'President Trump' or 'President Donald Trump', never as 'former President'."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.1  # Very low temperature to minimize hallucinations
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Error generating AI content: {e}")
        return f"{headline}\n\nBreaking market news. Full analysis coming soon."

def assess_news_importance(titles):
    """Always return 1 article per day"""
    return 1

def is_breaking_news(title):
    """Check if headline is breaking/urgent news"""
    breaking_keywords = ['crash', 'plunge', 'surge', 'soar', 'breaking', 'urgent', 'alert', 'explode', 'collapse', 'rally']
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in breaking_keywords)

def is_similar_title(title1, title2, threshold=0.30):
    """Check if two titles are similar based on keyword overlap"""
    # Remove common words and source names
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'today', 'live', 'updates', 'news', 'market', 'stock', 'stocks', '-', '—', ':', '|', 'new', 'high', 'record'}
    sources = {'yahoo', 'finance', 'cnbc', 'bloomberg', 'reuters', 'wsj', 'journal', 'barron', 'investor', 'business', 'daily', 'marketwatch', 'seeking', 'alpha', 'motley', 'fool', 'benzinga', 'stocktwits', 'aol', 'com'}
    
    # Check for common key phrases that indicate same story
    title1_lower = title1.lower()
    title2_lower = title2.lower()
    
    # If both mention same companies (3+ in common), likely same story
    company_keywords = ['nvidia', 'apple', 'tesla', 'microsoft', 'amazon', 'google', 'meta', 'netflix', '3m', 'coinbase', 'newmont', 'rapt', 'applovin', 'intel', 'sandisk', 'fastenal', 'warner']
    companies1 = [kw for kw in company_keywords if kw in title1_lower]
    companies2 = [kw for kw in company_keywords if kw in title2_lower]
    common_companies = set(companies1) & set(companies2)
    if len(common_companies) >= 3:
        return True
    
    # If both mention same company + same year + price prediction, likely same story
    if common_companies:
        year_match = False
        for year in ['2024', '2025', '2026', '2027']:
            if year in title1_lower and year in title2_lower:
                year_match = True
                break
        
        if year_match:
            price_keywords = ['$', 'price', 'target', 'reach', 'going to', 'soar', 'prediction']
            has_price1 = any(kw in title1_lower for kw in price_keywords)
            has_price2 = any(kw in title2_lower for kw in price_keywords)
            if has_price1 and has_price2:
                return True
    
    # If both are "Stock Market Today" articles, they're duplicates
    if 'stock market today' in title1_lower and 'stock market today' in title2_lower:
        return True
    
    # If both mention defense stocks, likely same story
    if 'defense' in title1_lower and 'defense' in title2_lower:
        return True
    
    # Check for same major index/topic - only allow ONE article per major topic
    major_topics = [
        ['dow', 'djia', 'dow jones'],
        ['s&p', 'sp500', 's&p 500'],
        ['nasdaq', 'qqq'],
        ['bitcoin', 'btc', 'crypto'],
        ['oil', 'crude', 'wti'],
        ['fed', 'federal reserve', 'interest rate', 'powell']
    ]
    
    for topic_group in major_topics:
        has_topic1 = any(topic in title1_lower for topic in topic_group)
        has_topic2 = any(topic in title2_lower for topic in topic_group)
        if has_topic1 and has_topic2:
            return True  # Same major topic = duplicate
    
    # Define keywords once for reuse
    dow_keywords = ['fall', 'down', 'drop', 'tumble', 'sink', 'fear', 'concern']
    
    # If both mention Dow + similar point drops (within 200 points), likely same story
    if 'dow' in title1_lower and 'dow' in title2_lower:
        # Extract point numbers from both titles
        points1 = re.findall(r'(\d+)\s*points?', title1_lower)
        points2 = re.findall(r'(\d+)\s*points?', title2_lower)
        if points1 and points2:
            p1 = int(points1[0])
            p2 = int(points2[0])
            # If within 200 points and both negative, same story
            if abs(p1 - p2) <= 200:
                has_negative1 = any(kw in title1_lower for kw in dow_keywords)
                has_negative2 = any(kw in title2_lower for kw in dow_keywords)
                if has_negative1 and has_negative2:
                    return True
    
    # If both mention Dow + Fed/Powell (falling/down/fears), likely same story
    fed_keywords = ['fed', 'powell', 'federal reserve']
    if 'dow' in title1_lower and 'dow' in title2_lower:
        has_fed1 = any(kw in title1_lower for kw in fed_keywords)
        has_fed2 = any(kw in title2_lower for kw in fed_keywords)
        has_negative1 = any(kw in title1_lower for kw in dow_keywords)
        has_negative2 = any(kw in title2_lower for kw in dow_keywords)
        if has_fed1 and has_fed2 and has_negative1 and has_negative2:
            return True
    
    # If both mention Dow futures + Greenland + positive movement, likely same story
    if 'dow' in title1_lower and 'dow' in title2_lower:
        if 'greenland' in title1_lower and 'greenland' in title2_lower:
            positive_keywords = ['rise', 'rebound', 'gain', 'up', 'rally']
            has_positive1 = any(kw in title1_lower for kw in positive_keywords)
            has_positive2 = any(kw in title2_lower for kw in positive_keywords)
            if has_positive1 and has_positive2:
                return True
    
    # If both mention Dow + Greenland + negative movement, likely same story
    if 'dow' in title1_lower and 'dow' in title2_lower:
        geo_keywords = ['greenland', 'tariff', 'trade war', 'capital flight']
        has_geo1 = any(kw in title1_lower for kw in geo_keywords)
        has_geo2 = any(kw in title2_lower for kw in geo_keywords)
        has_negative1 = any(kw in title1_lower for kw in dow_keywords)
        has_negative2 = any(kw in title2_lower for kw in dow_keywords)
        # Only mark as duplicate if BOTH have Greenland specifically
        if 'greenland' in title1_lower and 'greenland' in title2_lower and has_negative1 and has_negative2:
            return True
    
    # If both mention same specific numbers/milestones, likely same story
    key_phrases = [
        ('49,000', 'dow'), ('49000', 'dow'), ('49,', 'dow'),
        ('s&p 500', 'record'), ('s&p 500', 'high'),
        ('nasdaq', 'record'), ('nasdaq', 'high'),
        ('dow', 'record'), ('dow', 'high')
    ]
    
    for phrase1, phrase2 in key_phrases:
        if (phrase1 in title1_lower and phrase2 in title1_lower and 
            phrase1 in title2_lower and phrase2 in title2_lower):
            return True
    
    # Extract meaningful words
    words1 = set(re.findall(r'\b\w+\b', title1.lower())) - stop_words - sources
    words2 = set(re.findall(r'\b\w+\b', title2.lower())) - stop_words - sources
    
    if not words1 or not words2:
        return False
    
    # Calculate Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    similarity = intersection / union if union > 0 else 0
    
    return similarity >= threshold

def contains_old_date(text):
    """Check if text contains a date that's not today or yesterday (US Eastern time)"""
    today = get_us_eastern_time()
    yesterday = today - timedelta(days=1)
    
    # Common date patterns in headlines
    date_patterns = [
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{1,2}),?\s+(\d{4})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})'
    ]
    
    month_map = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if len(match) == 3:
                    if match[0].isdigit():  # MM/DD/YYYY format
                        date_str = f"{match[0]}/{match[1]}/{match[2]}"
                        article_date = datetime.strptime(date_str, '%m/%d/%Y')
                    else:  # Month name format
                        month_str = match[0].replace('.', '')
                        if month_str in month_map:
                            article_date = datetime(int(match[2]), month_map[month_str], int(match[1]))
                        else:
                            continue
                    
                    # If article date is before yesterday, skip it
                    if article_date.date() < yesterday.date():
                        return True
            except:
                pass
    
    return False

def fetch_google_news():
    """Fetch top market news from Google News RSS (finance section)"""
    # Rotate between different search queries for diversity
    queries = [
        "stock+market+OR+dow+jones+OR+s%26p+500+OR+nasdaq+when:23h",  # Broad market indices
        "federal+reserve+OR+interest+rates+OR+inflation+OR+economy+when:23h",  # Economic news
        "earnings+OR+revenue+OR+profit+OR+quarterly+results+when:23h",  # Earnings season
        "merger+OR+acquisition+OR+ipo+OR+buyout+when:23h",  # Corporate actions
    ]
    
    # Use current day of month to rotate queries (changes daily)
    from datetime import datetime
    query_index = datetime.now().day % len(queries)
    selected_query = queries[query_index]
    
    url = f"https://news.google.com/rss/search?q={selected_query}&hl=en-US&gl=US&ceid=US:en"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        print("   Requesting Google News RSS...")
        response = requests.get(url, headers=headers, timeout=15)
        print("   Got response, parsing...")
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        print("   Parsed RSS feed")
        
        # Read existing articles to check for duplicates and today's count
        existing_ids = set()
        existing_titles = []
        today_date = get_us_eastern_time().strftime('%b %d, %Y')
        today_count = 0
        recent_cutoff = datetime.now() - timedelta(days=2)  # Only check last 2 days for similarity
        try:
            print("   Reading existing news...")
            existing_news = read_existing_news()
            for item in existing_news:
                existing_ids.add(item['id'])
                # Only check similarity against general market news (not stock news) from last 2 days
                if item.get('title') and not item.get('stockSymbol'):  # Empty stockSymbol = general news
                    if item.get('date'):
                        try:
                            from dateutil import parser as date_parser
                            item_date = date_parser.parse(item['date'])
                            if item_date.replace(tzinfo=None) >= recent_cutoff:
                                existing_titles.append(item['title'])
                        except:
                            pass
            
            print("   Checking today's article count...")
            with open(NEWS_HTML_PATH, 'r') as f:
                html_content = f.read()
                # Count only general market news from today (not stock news)
                today_pattern = f'Published: {today_date} \| Category: Market News'
                today_count = len(re.findall(today_pattern, html_content, re.DOTALL))
            
            # Also check news.js sidebar for general news
            sidebar_general_count = 0
            try:
                with open(NEWS_JS_PATH, 'r') as f:
                    newsjs_content = f.read()
                    # Count items with empty stockSymbol (general news)
                    sidebar_general_count = len(re.findall(r"stockSymbol:\s*''", newsjs_content))
            except:
                pass
            
            print(f"   Found {today_count} general market articles in news.html, {sidebar_general_count} in sidebar")
        except Exception as e:
            print(f"   Error reading existing: {e}")
            pass
        
        # If sidebar is missing general news but news.html has articles, copy one over
        if sidebar_general_count == 0 and today_count >= 1:
            print(f"   Sidebar missing general news, copying from news.html...")
            # Extract most recent general market article from news.html
            general_articles = re.findall(r'<article class="blog-post" id="([^"]+)">(.*?)Category: Market News(.*?)</article>', html_content, re.DOTALL)
            if general_articles:
                article_id, before_cat, after_cat = general_articles[0]  # Most recent
                # Extract title
                title_match = re.search(r'<h2>([^<]+)</h2>', before_cat)
                # Extract date with timestamp
                date_match = re.search(r'data-timestamp="([^"]+)"[^>]*class="article-date"[^>]*>Published: ([^<]+)</span>', before_cat + after_cat)
                # Extract preview from first paragraph
                preview_match = re.search(r'<p>([^<]+)</p>', after_cat)
                
                if title_match and date_match and preview_match:
                    title = title_match.group(1).strip()
                    timestamp = date_match.group(1)
                    date_str = date_match.group(2).strip()
                    preview = preview_match.group(1).strip()[:150] + '...'
                    
                    # Get emoji from title
                    emoji = get_emoji(title)
                    
                    copied_item = [{
                        'id': article_id,
                        'emoji': emoji,
                        'title': title,
                        'date': date_str,
                        'timestamp': timestamp,
                        'preview': preview,
                        'stock_symbol': ''
                    }]
                    
                    update_news_js(copied_item)
                    print(f"   ✅ Copied article to sidebar: {title[:50]}...")
                    return []
        
        # Check if we already have 1 general market article today AND in sidebar
        if today_count >= 1 and sidebar_general_count >= 1:
            print(f"   Already have {today_count} general market article(s) for {today_date} and {sidebar_general_count} in sidebar, skipping fetch")
            return []
        
        news_items = []
        items = soup.find_all('item', limit=30)
        
        # First pass: collect titles to assess importance
        all_titles = []
        for item in items[:10]:  # Check first 10 for assessment
            title_tag = item.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                # Skip if title contains old dates
                if not contains_old_date(title):
                    all_titles.append(title)
        
        # Determine how many articles to generate (up to 3)
        target_count = min(3, 3 - today_count)
        
        # If we already have 3+ general market articles today, skip
        if today_count >= 3:
            print(f"   Already have {today_count} general market article(s) for {today_date}, keeping existing")
            return []
        
        # Only add articles if new batch would give us 1+ total
        if target_count + today_count < 1 and today_count > 0:
            print(f"   Already have articles for today, keeping existing")
            return []
        
        # Adjust target if we already have some articles today
        target_count = min(target_count, 3 - today_count)
        print(f"   Generating up to {target_count} article(s) for today")
        
        # Track IDs and titles to prevent duplicates
        seen_ids_this_fetch = set()
        seen_titles_this_fetch = []
        seen_topics = set()  # Track major topics to ensure diversity
        
        for item in items:
            title_tag = item.find('title')
            desc_tag = item.find('description')
            link_tag = item.find('link')
            pubdate_tag = item.find('pubDate') or item.find('pubdate')  # Try both cases
            if not title_tag:
                continue
                
            import html
            title = html.unescape(title_tag.get_text(strip=True))
            # Remove non-English text (Arabic, Chinese, etc.) from title
            title = re.sub(r'[^\x00-\x7F]+', '', title).strip()
            # Remove source names at end (e.g., "- Yahoo Finance", "- CNBC")
            title = re.sub(r'\s*[-–—]\s*[A-Za-z\s]+$', '', title).strip()
            description = desc_tag.get_text(strip=True) if desc_tag else title
            link = link_tag.get_text(strip=True) if link_tag else ''
            
            # Parse publication date from RSS feed
            pub_datetime = None
            if pubdate_tag:
                try:
                    from dateutil import parser as date_parser
                    pub_datetime = date_parser.parse(pubdate_tag.get_text(strip=True))
                except:
                    pass
            
            # Fallback to current time if no pubDate
            if not pub_datetime:
                pub_datetime = get_us_eastern_time()
            
            # Skip articles with old dates in title
            if contains_old_date(title):
                print(f"   Skipping (old date in title): {title[:50]}...")
                continue
            
            # Skip articles with specific prices in title (too specific, becomes outdated)
            if re.search(r'\$[\d,]+', title):
                print(f"   Skipping (price in title): {title[:50]}...")
                continue
            
            # Ensure topic diversity - only one article per major topic
            title_lower = title.lower()
            current_topic = None
            
            # Identify the main topic
            if 'dow jones' in title_lower or 'dow ' in title_lower:
                current_topic = 'dow'
            elif 's&p 500' in title_lower or 's&p' in title_lower:
                current_topic = 'sp500'
            elif 'nasdaq' in title_lower:
                current_topic = 'nasdaq'
            elif 'bitcoin' in title_lower or 'crypto' in title_lower:
                current_topic = 'crypto'
            elif 'oil' in title_lower and 'dow' not in title_lower:
                current_topic = 'oil'
            elif 'fed' in title_lower or 'federal reserve' in title_lower or 'powell' in title_lower:
                current_topic = 'fed'
            
            # Skip if we already have an article about this topic
            if current_topic and current_topic in seen_topics:
                print(f"   Skipping (already have {current_topic} article): {title[:50]}...")
                continue
            
            # Clean up description (remove HTML tags)
            description = re.sub(r'<[^>]+>', '', description)
            
            article_id = re.sub(r'[^a-z0-9]+', '-', title.lower())[:50].strip('-')
            
            # Skip if already exists or seen in this fetch
            if article_id in existing_ids or article_id in seen_ids_this_fetch:
                print(f"   Skipping (already exists): {title[:50]}...")
                continue
            
            # Skip if too similar to already selected titles OR existing titles
            is_duplicate = False
            all_existing_titles = existing_titles + seen_titles_this_fetch
            for existing_title in all_existing_titles:
                if is_similar_title(title, existing_title):
                    print(f"   Skipping (similar story): {title[:50]}...")
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            seen_ids_this_fetch.add(article_id)
            seen_titles_this_fetch.append(title)
            
            emoji = get_emoji(title)
            
            # Generate AI content using headline and RSS description
            print(f"   Generating AI content for: {title[:50]}...")
            full_content = generate_ai_content(title, description if description != title else None)
            
            # Validate: reject if contains fabricated percentages
            if re.search(r'\d+\.?\d*%', full_content):
                print(f"   ⚠️  Rejected (contains percentages): {title[:50]}...")
                continue
            
            # Use first 150 chars of AI content as preview (not the title)
            preview = full_content[:150] + '...' if len(full_content) > 150 else full_content
            
            # Extract stock symbol from title if present
            stock_symbol = extract_stock_symbol(title)
            
            news_items.append({
                'id': article_id,
                'emoji': emoji,
                'title': title,
                'date': pub_datetime.strftime('%a, %B %-d, %Y at %-I:%M %p UTC 3 min read'),
                'timestamp': pub_datetime.isoformat(),
                'preview': preview,
                'full_description': full_content,
                'link': link,
                'stock_symbol': stock_symbol
            })
            
            # Stop when we reach target count
            if len(news_items) + today_count >= target_count:
                break
        
        return news_items
    
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

def extract_stock_symbol(title):
    """Extract stock symbol from title if it matches available stocks"""
    company_map = {
        'apple': 'AAPL', 'tesla': 'TSLA', 'nvidia': 'NVDA', 'microsoft': 'MSFT',
        'amazon': 'AMZN', 'google': 'GOOGL', 'meta': 'META', 'netflix': 'NFLX',
        'amd': 'AMD', 'intel': 'INTC', 'coinbase': 'COIN'
    }
    
    title_lower = title.lower()
    for company, symbol in company_map.items():
        if company in title_lower and symbol in AVAILABLE_STOCKS:
            return symbol
    
    words = re.findall(r'\b[A-Z]{2,5}\b', title)
    for word in words:
        if word in AVAILABLE_STOCKS:
            return word
    
    return None

def get_emoji(title):
    """Pick emoji based on article title keywords"""
    title_lower = title.lower()
    
    if any(word in title_lower for word in ['surge', 'rally', 'soar', 'jump', 'gain', 'up']):
        return '🚀'
    elif any(word in title_lower for word in ['drop', 'plunge', 'crash', 'fall', 'down', 'sink']):
        return '🔴'
    elif 'bitcoin' in title_lower or 'crypto' in title_lower:
        return '₿'
    elif 'gold' in title_lower:
        return '🥇'
    elif 'silver' in title_lower:
        return '🥈'
    elif 'oil' in title_lower:
        return '🛢️'
    elif any(word in title_lower for word in ['fed', 'rate', 'inflation']):
        return '📊'
    else:
        return '📰'

def read_existing_news():
    """Read existing news items from news.js"""
    try:
        with open(NEWS_JS_PATH, 'r') as f:
            content = f.read()
            # Extract the array from the JS file
            match = re.search(r'const newsItems = (\[.*?\]);', content, re.DOTALL)
            if match:
                js_array = match.group(1)
                # Extract IDs, titles, dates, and stockSymbol for duplicate checking
                items = []
                # Match each item block
                item_blocks = re.findall(r'\{([^}]+)\}', js_array)
                for block in item_blocks:
                    item_id = re.search(r"id:\s*'([^']+)'", block)
                    title = re.search(r"title:\s*'([^']+)'", block)
                    date = re.search(r"date:\s*'([^']+)'", block)
                    stock_symbol = re.search(r"stockSymbol:\s*'([^']*)'", block)  # Empty string for general news
                    if item_id:
                        items.append({
                            'id': item_id.group(1),
                            'title': title.group(1) if title else '',
                            'date': date.group(1) if date else '',
                            'stockSymbol': stock_symbol.group(1) if stock_symbol else ''
                        })
                return items
    except Exception as e:
        print(f"Error reading existing news: {e}")
    
    return []

def update_news_js(new_items):
    """Update news.js with new items at the top"""
    # Read existing items by parsing the JS array properly
    existing_items = []
    if os.path.exists(NEWS_JS_PATH):
        with open(NEWS_JS_PATH, 'r') as f:
            content = f.read()
        
        # Extract array content between [ and ];
        match = re.search(r'const newsItems = \[(.*?)\];', content, re.DOTALL)
        if match:
            array_content = match.group(1)
            # Split by },
            raw_items = re.split(r'\},\s*\{', array_content)
            for raw in raw_items:
                raw = raw.strip()
                if not raw:
                    continue
                # Add back braces if needed
                if not raw.startswith('{'):
                    raw = '{' + raw
                if not raw.endswith('}'):
                    raw = raw + '}'
                existing_items.append(raw)
    
    # Get IDs of new items
    new_ids = {item['id'] for item in new_items}
    
    # Filter existing: remove old general news (no stockSymbol), keep all stock news
    from dateutil import parser as date_parser
    cutoff_date = datetime.now() - timedelta(days=30)
    filtered_existing = []
    
    for existing in existing_items:
        symbol_match = re.search(r"stockSymbol:\s*'([^']+)'", existing)
        date_match = re.search(r"date:\s*'([^']+)'", existing)
        
        # Check if item is too old
        if date_match:
            try:
                item_date = date_parser.parse(date_match.group(1))
                if item_date.replace(tzinfo=None) < cutoff_date:
                    continue  # Skip old items
            except:
                pass
        
        if symbol_match and symbol_match.group(1):  # Has stockSymbol = stock news
            # Always keep stock news (if not old)
            filtered_existing.append('    ' + existing)
        else:
            # General market news - only keep if not being replaced
            id_match = re.search(r"id:\s*'([^']+)'", existing)
            if id_match and id_match.group(1) not in new_ids:
                filtered_existing.append('    ' + existing)
    
    # Generate the JS file content
    js_content = """// Shared news items for Market News sidebar
const newsItems = [
"""
    
    # Add new items first
    for i, item in enumerate(new_items):
        # Properly escape strings for JavaScript
        item_id = item['id']  
        emoji = item['emoji']
        title = item['title'].replace("\\", "\\\\").replace("'", "\\'")
        date = item['date']
        preview = item['preview'].replace("\\", "\\\\").replace("'", "\\'")
        stock_symbol = item.get('stock_symbol', '') or ''
        link = item.get('link', '') or ''
        
        timestamp = item.get('timestamp', '')
        js_content += f"""    {{
        id: '{item_id}',
        emoji: '{emoji}',
        title: '{title}',
        date: '{date}',
        timestamp: '{timestamp}',
        preview: '{preview}',
        stockSymbol: '{stock_symbol}',
        link: '{link}'
    }}"""
        
        # Add comma if not last item or if there are existing items
        if i < len(new_items) - 1 or filtered_existing:
            js_content += ',\n'
        else:
            js_content += '\n'
    
    # Separate stock and general news from filtered_existing
    stock_existing = [item for item in filtered_existing if "stockSymbol: ''" not in item and "stockSymbol: \"\"" not in item]
    general_existing = [item for item in filtered_existing if "stockSymbol: ''" in item or "stockSymbol: \"\"" in item]
    
    # Limit: 80 stock + 20 general = 100 total
    # Reserve space for new items (which are general market news)
    max_general = 20 - len(new_items)
    max_stock = 80
    
    stock_existing = stock_existing[:max_stock]
    general_existing = general_existing[:max_general] if max_general > 0 else []
    
    # Combine: new items first, then existing (general + stock)
    combined = general_existing + stock_existing
    for i, item in enumerate(combined):
        js_content += item
        if i < len(combined) - 1:
            js_content += ',\n'
        else:
            js_content += '\n'
    
    js_content += """];

// Render news items into the sidebar
function renderNewsItems() {
    const container = document.getElementById('news-items');
    if (!container) return;
    
    // Sort all items by date (newest first)
    const sortedItems = [...newsItems].sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return dateB - dateA;
    });
    
    // Separate stock news and general news from sorted items
    const stockNews = sortedItems.filter(item => item.stockSymbol);
    const generalNews = sortedItems.filter(item => !item.stockSymbol);
    
    // Show 1 general + 4 stock news
    const displayItems = [];
    if (generalNews.length > 0) displayItems.push(generalNews[0]);
    displayItems.push(...stockNews.slice(0, 4));
    
    container.innerHTML = displayItems.map(item => {
        const url = item.stockSymbol ? `stocks/${item.stockSymbol}.html` : `news.html#${item.id}`;
        return `
        <div class="news-item" style="padding: 8px; margin-bottom: 8px; border-bottom: 1px solid var(--border-color); cursor: pointer;" onclick="window.location.href='${url}'">
            <div style="font-weight: 600; color: var(--text-primary); font-size: 0.85rem; margin-bottom: 3px;">${item.emoji} ${item.title}</div>
            <div style="color: var(--text-secondary); font-size: 0.7rem; margin-bottom: 2px;" data-timestamp="${item.timestamp || ''}" class="article-date">${item.date}</div>
            <div style="color: var(--text-secondary); font-size: 0.75rem; line-height: 1.3;">${item.preview}</div>
        </div>
        `;
    }).join('');
}

// Auto-render when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderNewsItems);
} else {
    renderNewsItems();
}
"""
    
    # Write to file
    with open(NEWS_JS_PATH, 'w') as f:
        f.write(js_content)
    
    print(f"✅ Updated news.js with {len(new_items)} new items")
    for item in new_items:
        print(f"   {item['emoji']} {item['title']}")

def update_news_html(new_items):
    """Add new articles to news.html and remove old general market news (3+ days)"""
    try:
        with open(NEWS_HTML_PATH, 'r') as f:
            html_content = f.read()
        
        # Find the blog-content div
        content_start = html_content.find('<div class="blog-content">')
        if content_start == -1:
            print("Error: Could not find blog-content div")
            return
        
        # Find all existing articles
        articles = re.findall(r'<article class="blog-post"[^>]*>.*?</article>', html_content, re.DOTALL)
        
        # Filter: remove old general market news (30+ days), keep all stock news
        from dateutil import parser as date_parser
        cutoff_date = datetime.now() - timedelta(days=30)
        existing_ids = set()
        unique_existing = []
        
        for article in articles:
            id_match = re.search(r'id="([^"]+)"', article)
            if id_match:
                article_id = id_match.group(1)
                if article_id not in existing_ids:
                    existing_ids.add(article_id)
                    
                    # Check if general market news or stock news
                    is_stock_news = 'Stock News' in article
                    
                    if is_stock_news:
                        # Keep all stock news (handled by update_stock_news.py)
                        unique_existing.append(article)
                    else:
                        # General market news - check age
                        date_match = re.search(r'Published: ([^|]+)', article)
                        if date_match:
                            try:
                                article_date = date_parser.parse(date_match.group(1).strip())
                                if article_date.replace(tzinfo=None) >= cutoff_date:
                                    unique_existing.append(article)
                            except:
                                unique_existing.append(article)  # Keep if can't parse date
                        else:
                            unique_existing.append(article)
        
        # Filter out new items that already exist
        new_items_filtered = [item for item in new_items if item['id'] not in existing_ids]
        
        if not new_items_filtered:
            print("⏭️  No new articles to add (all already exist)")
            return
        
        # Create new articles HTML
        new_articles_html = []
        for item in new_items_filtered:
            # Get link - only include if it's a direct article URL (not Google News redirect)
            article_link = item.get('link', '')
            read_article_link = ''
            
            # Only add link if it's NOT a Google News redirect and is a valid URL
            if article_link and 'news.google.com' not in article_link and article_link.startswith('http'):
                read_article_link = f'<a href="{article_link}" target="_blank" style="color: #007bff;">Read full article →</a>'
            
            # Extract stock symbols using company name mapping (up to 3)
            # Order matters: more specific terms first
            company_map = {
                # Crypto (check first to avoid false matches)
                'bitcoin': 'BTC-USD', 'ethereum': 'ETH-USD', 'xrp': 'XRP-USD',
                'solana': 'SOL-USD', 'cardano': 'ADA-USD', 'dogecoin': 'DOGE-USD',
                'shiba inu': 'SHIB-USD', 'polkadot': 'DOT-USD', 'avalanche': 'AVAX-USD',
                'polygon': 'MATIC-USD', 'chainlink': 'LINK-USD', 'litecoin': 'LTC-USD',
                'uniswap': 'UNI-USD', 'stellar': 'XLM-USD', 'algorand': 'ALGO-USD',
                # Major tech companies
                'apple': 'AAPL', 'tesla': 'TSLA', 'nvidia': 'NVDA', 'broadcom': 'AVGO',
                'microsoft': 'MSFT', 'amazon': 'AMZN', 'google': 'GOOGL', 'alphabet': 'GOOGL',
                'meta': 'META', 'netflix': 'NFLX', 'amd': 'AMD', 'intel': 'INTC',
                'coinbase': 'COIN', 'oracle': 'ORCL', 'adobe': 'ADBE', 'salesforce': 'CRM',
                'cisco': 'CSCO', 'ibm': 'IBM', 'qualcomm': 'QCOM', 'paypal': 'PYPL',
                'uber': 'UBER', 'lyft': 'LYFT', 'airbnb': 'ABNB', 'spotify': 'SPOT', 'zoom': 'ZM',
                # Other sectors
                'exxonmobil': 'XOM', 'exxon': 'XOM', 'chevron': 'CVX', 'boeing': 'BA',
                'walmart': 'WMT', 'jpmorgan': 'JPM', 'visa': 'V', 'mastercard': 'MA',
                'disney': 'DIS', 'pfizer': 'PFE', 'coca-cola': 'KO',
                # Index ETFs
                's&p 500': 'SPY', 's&p': 'SPY', 'sp500': 'SPY', 'sp 500': 'SPY',
                'dow jones': 'DIA', 'dow': 'DIA', 'djia': 'DIA',
                'nasdaq': 'QQQ', 'nasdaq 100': 'QQQ',
                'russell 2000': 'IWM', 'russell': 'IWM',
                # Sector ETFs (check before commodities)
                'energy stocks': 'XLE', 'energy sector': 'XLE',
                'tech stocks': 'XLK', 'technology': 'XLK', 'tech sector': 'XLK',
                'bank stocks': 'XLF', 'banks': 'XLF',
                # Commodity ETFs (check after sector ETFs)
                'crude oil': 'USO', 'oil prices': 'USO', 'oil': 'XLE',
                'gold': 'GLD', 'bonds': 'TLT', 'treasuries': 'TLT'
            }
            
            # Symbol descriptions
            symbol_descriptions = {
                # Index ETFs
                'SPY': 'US Market', 'DIA': 'US Market', 'QQQ': 'US Market', 'IWM': 'US Market',
                # Sector ETFs
                'XLK': 'Tech Sector', 'XLF': 'Financial Sector', 'XLE': 'Energy Sector',
                # Commodity ETFs
                'GLD': 'Gold', 'USO': 'Oil', 'TLT': 'Bonds',
                # Cryptocurrencies
                'BTC-USD': 'Bitcoin', 'ETH-USD': 'Ethereum', 'XRP-USD': 'XRP',
                'SOL-USD': 'Solana', 'ADA-USD': 'Cardano', 'DOGE-USD': 'Dogecoin',
                'SHIB-USD': 'Shiba Inu', 'DOT-USD': 'Polkadot', 'AVAX-USD': 'Avalanche',
                'MATIC-USD': 'Polygon', 'LINK-USD': 'Chainlink', 'LTC-USD': 'Litecoin',
                'UNI-USD': 'Uniswap', 'XLM-USD': 'Stellar', 'ALGO-USD': 'Algorand'
            }
            
            # Decode HTML entities before searching
            import html
            search_text = html.unescape((item['title'] + ' ' + item['full_description'])).lower()
            mentioned_stocks = []
            
            # First check if item has stock_symbol (extracted from title)
            item_stock_symbol = item.get('stock_symbol', '')
            if item_stock_symbol and os.path.exists(os.path.join(STOCKS_DIR, f"{item_stock_symbol}.html")):
                mentioned_stocks.append(item_stock_symbol)
            
            # Then check for company names in text
            for company, symbol in company_map.items():
                if company in search_text:
                    if symbol not in mentioned_stocks:
                        mentioned_stocks.append(symbol)
                        if len(mentioned_stocks) >= 3:  # Max 3 stocks
                            break
            
            # Create links for mentioned stocks (up to 3)
            stock_links = []
            title_link = None  # For linking title to stock page
            
            for stock_symbol in mentioned_stocks:
                # Get description if available
                description = symbol_descriptions.get(stock_symbol, '')
                label = f"{stock_symbol} ({description})" if description else stock_symbol
                
                # Check if stock page exists
                if os.path.exists(os.path.join(STOCKS_DIR, f"{stock_symbol}.html")):
                    # Use first stock with page for title link
                    if not title_link:
                        title_link = f'stocks/{stock_symbol}.html'
                    # Just analyze link (title already links to stock page)
                    stock_links.append(f'<a href="analysis.html?symbol={stock_symbol}&option=1&subOption=custom" style="color: #007bff;">Analyze {label} →</a>')
                else:
                    # Just analyze link
                    stock_links.append(f'<a href="analysis.html?symbol={stock_symbol}&option=1&subOption=custom" style="color: #007bff;">Analyze {label} →</a>')
            
            # Join with separator
            analyze_button = ' | '.join(stock_links) if stock_links else ''
            
            # Create title - no link for general market news
            title_html = f'<h2>{item["emoji"]} {item["title"]}</h2>'
            
            article_html = f'''            <article class="blog-post" id="{item['id']}">
                {title_html}
                <div class="blog-meta"><span data-timestamp="{item.get('timestamp', '')}" class="article-date">Published: {item['date']}</span> | Category: Market News | AI Analysis</div>
                <div class="blog-excerpt">
                    <p>{item['full_description']}</p>
                    <p>{read_article_link}{' | ' if read_article_link and analyze_button else ''}{analyze_button}</p>
                </div>
            </article>
'''
            new_articles_html.append(article_html)
        
        # Combine and sort all articles by date (newest first)
        all_articles = new_articles_html + unique_existing
        
        # Sort by date
        def extract_date(article_html):
            # Try timestamp first (most accurate)
            timestamp_match = re.search(r'data-timestamp="([^"]+)"', article_html)
            if timestamp_match:
                try:
                    from dateutil import parser as date_parser
                    return date_parser.parse(timestamp_match.group(1)).replace(tzinfo=None)
                except:
                    pass
            # Fallback to Published date
            date_match = re.search(r'Published: ([^|<]+)', article_html)
            if date_match:
                try:
                    from dateutil import parser as date_parser
                    return date_parser.parse(date_match.group(1).strip()).replace(tzinfo=None)
                except:
                    pass
            return datetime.min
        
        all_articles = sorted(all_articles, key=extract_date, reverse=True)
        # Keep all articles (no limit)
        # all_articles = all_articles[:MAX_BLOG_ARTICLES]
        
        # Rebuild HTML
        before_content = html_content[:content_start + len('<div class="blog-content">')]
        after_content_match = re.search(r'</div>\s*<div style="text-align: center', html_content)
        if not after_content_match:
            after_content_match = re.search(r'</div>\s*</div>\s*<footer', html_content)
        if not after_content_match:
            print("Error: Could not find end of blog-content")
            return
        
        after_content = html_content[after_content_match.start():]
        
        new_html = before_content + '\n' + '\n'.join(all_articles) + '        ' + after_content
        
        with open(NEWS_HTML_PATH, 'w') as f:
            f.write(new_html)
        
        print(f"✅ Updated news.html with {len(new_items_filtered)} new articles")
    
    except Exception as e:
        print(f"Error updating news.html: {e}")

def main():
    print("🔄 Fetching latest market news from Google News...")
    new_items = fetch_google_news()
    
    if new_items:
        update_news_js(new_items)
        update_news_html(new_items)
        print(f"\n✅ Successfully updated {len(new_items)} news items!")
        
        # Update stock pages for items with stock symbols
        for item in new_items:
            if item.get('stock_symbol'):
                symbol = item['stock_symbol']
                print(f"\n📰 Updating stock page for {symbol}...")
                
                news_html = f"""<div style="background: var(--bg-secondary); border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <h3 style="margin-top: 0; color: var(--text-primary);">📰 Latest Update</h3>
            <p style="margin: 10px 0; color: var(--text-primary);"><strong>{item['title']}</strong></p>
            <p style="margin: 5px 0; font-size: 0.85em; color: var(--text-secondary);" data-timestamp="{item.get('timestamp', '')}" class="article-date">{item['date']}</p>
            <p style="margin: 10px 0; color: var(--text-secondary);">{item['full_description']}</p>
            <p style="margin: 10px 0 0 0; font-size: 0.9em; color: var(--text-secondary);">
                <a href="{item.get('link', '')}" target="_blank" style="color: #007bff;">Read full article →</a>
            </p>
        </div>"""
                
                file_path = f"{STOCKS_DIR}/{symbol}.html"
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    content = re.sub(r'<!-- NEWS_SECTION_START -->.*?<!-- NEWS_SECTION_END -->', '', content, flags=re.DOTALL)
                    
                    news_section = f"""\n        <!-- NEWS_SECTION_START -->
        {news_html}
        <!-- NEWS_SECTION_END -->\n"""
                    
                    pattern = r'(</div>\s*)(<!-- NEWS_SECTION_START -->)'
                    if re.search(pattern, content):
                        content = re.sub(pattern, f'\\1{news_section}', content, count=1)
                    
                    with open(file_path, 'w') as f:
                        f.write(content)
                    
                    print(f"   ✅ Updated {symbol}.html")
    else:
        print("⚠️  No new items found")

if __name__ == '__main__':
    main()
