#!/usr/bin/env python3
"""
Generate individual HTML stock pages for SEO.

Reads stocks.txt (3,467 stocks) and generates /website/stocks/{SYMBOL}.html for each.
Preserves existing news (<!-- NEWS_SECTION_START/END -->), related
(<!-- RELATED_SECTION_START/END -->) and analysis (<!-- ANALYSIS_SECTION_START/END -->)
sections when regenerating, plus the robots value, data-based descriptions and
dateModified that update_stock_analysis.py maintains.

Usage:
    python3 generate-stock-pages.py           # Regenerate all 3,467 pages
    python3 generate-stock-pages.py AAPL      # Single stock only

Input:  /Users/dave/VSCODE/website/stocks.txt
Output: /Users/dave/VSCODE/website/stocks/*.html

Notes:
- Uses csv.reader to handle quoted company names (e.g. "Ajinomoto Co., Inc.")
- Sectors with value 'Stock' are displayed as 'General'
- Removes orphaned HTML files (symbols no longer in stocks.txt) on full runs
- After running, deploy with: ./deploy.sh
"""

import os
import re

def load_stocks():
    """Load all stocks from stocks.txt using csv.reader (handles quoted company names with commas)."""
    import csv
    stocks = []
    stocks_file = "/Users/dave/VSCODE/website/stocks.txt"
    
    with open(stocks_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3:
                stocks.append({
                    "symbol": row[0].strip(),
                    "name": row[1].strip(),
                    "sector": row[2].strip()
                })
    return stocks



def generate_stock_page(stock, robots="noindex, follow", date_modified="2026-09-25"):
    """Generate full HTML page for a stock including SEO metadata, JSON-LD schema, nav, and CTA.

    robots and date_modified are normally carried over from the existing page, where
    update_stock_analysis.py maintains them.
    """
    import json
    symbol = stock["symbol"]
    name = stock["name"]
    sector = stock["sector"]
    
    # Handle generic "Stock" sector
    if sector == "Stock":
        meta_desc = f"Analyze {name} ({symbol}) stock with AI-powered insights, technical indicators, and market data. Free stock analysis tool."
        sector_display = "General"
        about_text = f"{name} ({symbol}) is a publicly traded company. The snapshot on this page updates daily; run a full report for the complete breakdown."
    else:
        meta_desc = f"Analyze {name} ({symbol}) stock with AI-powered insights, technical indicators, and market data. Free stock analysis tool for {sector} sector."
        sector_display = sector
        about_text = f"{name} ({symbol}) is listed in the {sector} sector. The snapshot on this page updates daily; run a full report for the complete breakdown."
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} ({symbol}) Stock Analysis - Free AI-Powered Research | StockIQ</title>
    <meta name="description" content="{meta_desc}">
    <meta name="keywords" content="{symbol} stock analysis, {name} analysis, {symbol} technical analysis">
    <meta name="robots" content="{robots}">
    <link rel="canonical" href="https://stockiq.tech/stocks/{symbol}.html">
    
    <!-- Open Graph Tags for Social Sharing -->
    <meta property="og:title" content="{name} ({symbol}) Stock Analysis - Free AI-Powered Research | StockIQ">
    <meta property="og:description" content="{meta_desc}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://stockiq.tech/stocks/{symbol}.html">
    <meta property="og:image" content="https://stockiq.tech/og-image.png">
    <meta property="og:site_name" content="StockIQ">
    
    <!-- Twitter Card Tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{name} ({symbol}) Stock Analysis">
    <meta name="twitter:description" content="{meta_desc}">
    <meta name="twitter:image" content="https://stockiq.tech/og-image.png">
    
    <!-- JSON-LD Structured Data -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "WebPage",
      "name": {json.dumps(f"{name} ({symbol}) Stock Analysis")},
      "url": "https://stockiq.tech/stocks/{symbol}.html",
      "dateModified": "{date_modified}",
      "publisher": {{
        "@type": "Organization",
        "name": "StockIQ",
        "url": "https://stockiq.tech",
        "logo": "https://stockiq.tech/stockiq-logo.png"
      }},
      "about": {{
        "@type": "Corporation",
        "name": {json.dumps(name)},
        "tickerSymbol": {json.dumps(symbol)}
      }}
    }}
    </script>
    
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-WVETNMPF8V"></script>
    <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-WVETNMPF8V');
    </script>
    
    <link rel="stylesheet" href="../styles.css">
    <link rel="icon" type="image/x-icon" href="../favicon.ico">
    <script>
    (function(){{const m=localStorage.getItem('manualOverride'),s=localStorage.getItem('theme'),h=new Date().getHours(),a=(h>=18||h<6)?'dark':'light',t=(m==='true'&&s)?s:a;document.documentElement.setAttribute('data-theme',t);}})();
    </script>
    <style>
    /* Always show notification bells */
    #notification-bell,
    #mobile-notification-bell {{
        display: block !important;
    }}
    /* Trial status positioning */
    #trial-status-display {{
        top: 70px !important;
    }}
    @media (min-width: 769px) {{
        #trial-status-display {{
            top: 107px !important;
        }}
        #ai-chat-button {{
            right: 20px !important;
        }}
        #ai-chat-window {{
            right: 20px !important;
        }}
        body.stock-page #ai-chat-widget {{
            right: 20px !important;
        }}
    }}
    </style>
    <script src="../auth.js" defer></script>
    <script src="../theme.js"></script>
    <script>
    function goToNotifications(event) {{
        const existingDropdown = document.getElementById('notification-dropdown');
        if (existingDropdown) {{
            existingDropdown.remove();
            return;
        }}
        
        const dropdown = document.createElement('div');
        dropdown.id = 'notification-dropdown';
        const userId = localStorage.getItem('userId');
        const isLoggedOut = !userId || userId === 'anonymous';
        
        dropdown.style.cssText = 'position: absolute; top: 100%; right: 0; width: ' + (isLoggedOut ? '240px' : '350px') + '; max-width: ' + (isLoggedOut ? '240px' : '350px') + '; max-height: 400px; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); z-index: 10000; overflow-y: auto; margin-top: 5px;';
        
        if (isLoggedOut) {{
            dropdown.innerHTML = '<div style="padding: 20px 10px; text-align: center; color: var(--text-secondary); font-size: 14px;"><p style="margin-bottom: 15px; white-space: nowrap;">Please log in to view notifications</p><a href="../login.html" style="color: #007bff; text-decoration: none; font-weight: 500; font-size: 14px;">Login</a></div>';
        }} else {{
            dropdown.innerHTML = '<div style="padding: 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary);"><h4 style="margin: 0; color: var(--text-primary); font-size: 14px;">📊 Recent Analysis Reports</h4><p style="margin: 5px 0 0 0; color: var(--text-secondary); font-size: 12px;">0 unread</p></div><div style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 14px;"><p>No analysis reports yet</p><a href="../analysis.html" style="color: #007bff; text-decoration: none; font-size: 14px;">Start your first analysis</a></div>';
        }}
        
        const bell = event.currentTarget;
        bell.style.position = 'relative';
        bell.appendChild(dropdown);
        
        setTimeout(function() {{
            document.addEventListener('click', function closeDropdown(e) {{
                if (!bell.contains(e.target)) {{
                    dropdown.remove();
                    document.removeEventListener('click', closeDropdown);
                }}
            }});
        }}, 100);
    }}
    </script>
    <script>if(document.body)document.body.classList.add('stock-page');else document.addEventListener('DOMContentLoaded',()=>document.body.classList.add('stock-page'));</script>
</head>
<body>
    <!-- SHARED_STRIP_START: the strip across the top on a desktop, written by stockiq/shared_parts.py: change it there, not here -->
<a id="site-strip" class="site-strip" href="../signup.html" hidden></a>
<script>(function () {{ try {{ var d = document.documentElement, s = document.getElementById('site-strip'), u = localStorage.getItem('userId'), signed = !!u && u !== 'anonymous'; if (window.innerWidth <= 768 || (signed && localStorage.getItem('userPaidStatus_' + u) === 'paid')) {{ s.remove(); d.style.setProperty('--nav-top', '0px'); return; }} s.innerHTML = '<span>' + (signed ? 'Plans from <strong>$4.99/month</strong>: more analyses a day, and the AI autopilot (Beta) for your practice portfolio' : 'Free 3-day trial: <strong>15 analyses</strong>, no credit card needed') + '</span>'; if (signed) s.href = '../index.html#pricing'; s.hidden = false; d.classList.add('has-strip'); d.style.setProperty('--nav-top', '41px'); }} catch (e) {{ }} }})();</script>
<!-- SHARED_STRIP_END -->
    <nav class="top-nav" style="top: var(--nav-top, 41px);">
        <div class="nav-container">
            <div class="nav-brand">
                <a href="../index.html" style="display: flex; align-items: center; gap: 8px; text-decoration: none; color: inherit;">
                    <img src="../stockiq-logo.png" alt="StockIQ Logo" class="brand-logo" style="width: 24px; height: 24px;" width="24" height="24">
                    <span class="brand-text">StockIQ</span>
                </a>
            </div>

            <div class="desktop-nav">
                <!-- SHARED_MENU_START: the menu, written by stockiq/shared_parts.py: change it there, not here -->
<a href="../index.html" class="nav-item home-link" style="text-decoration: none !important; color: inherit; display: flex; align-items: center;">Home</a>
<div class="nav-item dropdown" onclick="showDropdown('analysis-dropdown', event)">Analysis <span class="dropdown-arrow">▼</span><div class="dropdown-menu" id="analysis-dropdown"><a href="../analysis.html?option=1">Stock &amp; ETF Analysis</a><a href="../analysis.html?option=2">Trading Signals</a></div></div>
<div class="nav-item dropdown" onclick="showDropdown('screeners-dropdown', event)">Screeners <span class="dropdown-arrow">▼</span><div class="dropdown-menu" id="screeners-dropdown"><a href="../screeners-today.html">📊 Today&rsquo;s top 10s</a><a href="../analysis.html?option=3">🇺🇸 US Markets</a><a href="../analysis.html?option=4">🇪🇺 Europe Markets</a><a href="../analysis.html?option=5">🌏 Asia-Pacific Markets</a><a href="../analysis.html?option=6">🌎 Americas Markets</a><a href="../analysis.html?option=7">🪙 Crypto (540 coins)</a></div></div>
<a href="../index.html#pricing" class="nav-item home-link nav-pricing" style="text-decoration: none !important; color: inherit; display: flex; align-items: center;">Pricing</a>
<a href="../login.html" class="nav-item home-link nav-login">Log in</a>
<a href="../signup.html" class="nav-signup">Sign up free</a>
<div class="nav-item dropdown nav-account" onclick="showDropdown('account-dropdown', event)" style="margin-left: auto;">Account <span class="dropdown-arrow">▼</span><div class="dropdown-menu" id="account-dropdown"><a href="../signup.html">Register</a><a href="../login.html">Login</a></div></div>
<!-- SHARED_MENU_END -->
                <button class="notification-bell" id="notification-bell" onclick="goToNotifications(event)" title="Notifications" aria-label="View notifications" style="display: none; position: relative; background: none; border: none; font-size: 20px; cursor: pointer; color: var(--text-primary); margin-right: 10px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                    </svg>
                    <span class="notification-badge" id="notification-badge" style="position: absolute; top: -5px; right: -5px; background: #dc3545; color: white; border-radius: 50%; width: 18px; height: 18px; font-size: 11px; font-weight: bold; display: none; align-items: center; justify-content: center;"></span>
                </button>
                <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme" aria-label="Toggle dark mode">
                    <span class="theme-icon">🌙</span>
                </button>
            </div>

            <div class="mobile-nav">
                <button class="hamburger-btn" onclick="toggleMobileMenu()" aria-label="Open menu">
                    <span class="hamburger-line"></span>
                    <span class="hamburger-line"></span>
                    <span class="hamburger-line"></span>
                </button>
            </div>
        </div>
    </nav>

    <div class="mobile-menu-overlay" id="mobile-menu-overlay" onclick="closeMobileMenu()"></div>

    <div class="mobile-menu" id="mobile-menu">
        <div class="mobile-menu-header">
            <span class="mobile-brand"><img src="../stockiq-logo.png" alt="StockIQ" style="width: 20px; height: 20px; margin-right: 8px; vertical-align: middle;" width="20" height="20">StockIQ.tech</span>
            <div class="mobile-header-controls">
                <button class="close-btn" onclick="closeMobileMenu()" aria-label="Close menu">×</button>
            </div>
        </div>
        <div class="mobile-menu-content">
<!-- SHARED_PHONE_MENU_START: the phone menu, written by stockiq/shared_parts.py: change it there, not here -->
<div class="mobile-section mobile-join only-signed-out"><a href="../signup.html" class="mobile-signup">Sign up free</a><a href="../login.html" class="mobile-login">Log in</a></div>
<div class="mobile-section"><a href="../index.html">🏠 Home</a></div>
<div class="mobile-section only-signed-in" id="mobile-dashboard-section"><a href="../dashboard.html">📊 Dashboard</a></div>
<div class="mobile-section"><div class="mobile-section-title">Analysis</div><a href="../analysis.html?option=1">Stock &amp; ETF Analysis</a><a href="../analysis.html?option=2">Trading Signals</a></div>
<div class="mobile-section"><div class="mobile-section-title">Screeners</div><a href="../screeners-today.html">📊 Today&rsquo;s top 10s</a><a href="../analysis.html?option=3">🇺🇸 US Markets</a><a href="../analysis.html?option=4">🇪🇺 Europe Markets</a><a href="../analysis.html?option=5">🌏 Asia-Pacific Markets</a><a href="../analysis.html?option=6">🌎 Americas Markets</a><a href="../analysis.html?option=7">🪙 Crypto (540 coins)</a></div>
<div class="mobile-section mobile-pricing"><a href="../index.html#pricing">💳 Pricing</a></div>
<div class="mobile-section only-signed-in"><div class="mobile-section-title">Account</div><a href="../signup.html">Register</a><a href="../login.html">Login</a></div>
<div class="mobile-section"><div class="mobile-section-title">Theme</div><a href="#" onclick="event.preventDefault(); toggleTheme()" id="mobile-theme-toggle">🌙 Dark Mode</a></div>
<!-- SHARED_PHONE_MENU_END -->
</div>
    </div>

    <main style="max-width: 1200px; margin: 0 auto; padding: 5px 20px 20px;">
        <div style="text-align: center; margin-bottom: 40px;">
            <h1>{name} ({symbol}) Stock Analysis</h1>
            <div id="live-ticker" data-main-symbol="{symbol}" style="font-size: 1.3rem; margin: 15px 0; color: var(--text-secondary);">
                --
            </div>
            <p style="font-size: 1.2rem; color: var(--text-secondary); margin-top: 10px;">
                Free AI-powered analysis and research for {name} stock
            </p>
            <p style="color: var(--text-secondary); margin-top: 10px;">
                Sector: {sector_display}
            </p>
        </div>

        <!-- ANALYSIS_SECTION_START -->
        <!-- ANALYSIS_SECTION_END -->

        <div style="background: var(--card-bg); border-radius: 12px; padding: 40px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="margin: 0;">Full {symbol} report</h2><p style="margin: 0 0 20px 0; color: var(--text-secondary);">{about_text}</p>
            <a href="../analysis.html?symbol={symbol}&option=1&subOption=custom" class="cta-button">
                Analyze {symbol} Now →
            </a>
        </div>

        <!-- NEWS_SECTION_START -->
        <!-- NEWS_SECTION_END -->

        <!-- RELATED_SECTION_START -->
        <!-- RELATED_SECTION_END -->

    </main>

    <!-- SHARED_FOOTER_START: the footer, written by stockiq/shared_parts.py: change it there, not here -->
<footer class="footer site-footer">
<div class="sf-cols">
<div class="sf-brand"><a href="../index.html" class="sf-logo"><img src="../stockiq-logo.png" alt="" width="20" height="20" loading="lazy">StockIQ</a><p>Research tools for individual investors: scores, screeners and a practice portfolio.</p></div>
<div class="sf-col"><div class="sf-head">Tools</div><a href="../analysis.html?option=1">Stock analysis</a><a href="../screeners-today.html">Today&rsquo;s top 10s</a><a href="../analysis.html?option=3">All screeners</a><a href="../index.html#pricing">Pricing</a></div><div class="sf-col"><div class="sf-head">Learn</div><a href="../news.html">Market news</a><a href="../blog.html">Blog</a><a href="../faq.html">FAQ</a><a href="../about.html">About</a></div><div class="sf-col"><div class="sf-head">Help</div><a href="../support.html">Support</a><a href="../contact.html">Contact</a><a href="../terms.html">Terms of Service</a><a href="../privacy-policy.html">Privacy Policy</a><a href="../refunds.html">Refund Policy</a><a href="../data-deletion.html">Data Deletion</a></div>
</div>
<p class="sf-legal">General information only, not financial advice. Scores and signals are automated model outputs that do not take your personal circumstances into account, and past performance does not indicate future results. Market data comes from third parties (Yahoo Finance, Finnhub) and may be delayed or inaccurate.</p>
<p class="sf-copy">&copy; 2026 StockIQ &middot; <a href="https://instagram.com/stockiq.tech" target="_blank" rel="noopener noreferrer">Instagram</a></p>
</footer>
<!-- SHARED_FOOTER_END -->
    
    <script>
    function toggleMobileMenu() {{
        const menu = document.getElementById('mobile-menu');
        const overlay = document.getElementById('mobile-menu-overlay');
        const hamburger = document.querySelector('.hamburger-btn');
        
        menu.classList.toggle('open');
        overlay.classList.toggle('show');
        hamburger.classList.toggle('active');
        
        if (menu.classList.contains('open')) {{
            document.body.classList.add('menu-open');
            document.body.style.overflow = 'hidden';
            document.body.style.position = 'fixed';
            document.body.style.width = '100%';
        }} else {{
            document.body.classList.remove('menu-open');
            document.body.style.overflow = '';
            document.body.style.position = '';
            document.body.style.width = '';
        }}
    }}
    
    function closeMobileMenu() {{
        document.getElementById('mobile-menu').classList.remove('open');
        document.getElementById('mobile-menu-overlay').classList.remove('show');
        document.querySelector('.hamburger-btn').classList.remove('active');
        document.body.classList.remove('menu-open');
        document.body.style.overflow = '';
        document.body.style.position = '';
        document.body.style.width = '';
    }}
    
    // Hide nav and trial status on scroll down (mobile)
    if (window.innerWidth <= 768) {{
        let lastScroll = 0;
        window.addEventListener('scroll', function() {{
            const currentScroll = window.pageYOffset;
            const nav = document.querySelector('.top-nav');
            const trialDisplay = document.getElementById('trial-status-display');
            if (currentScroll > lastScroll && currentScroll > 100) {{
                nav.style.transform = 'translateY(-100%)';
                if (trialDisplay) trialDisplay.style.opacity = '0';
            }} else {{
                nav.style.transform = 'translateY(0)';
                if (trialDisplay) trialDisplay.style.opacity = '0.7';
            }}
            lastScroll = currentScroll;
        }});
    }}
    </script>
    <script src="../js/timezone-converter.js"></script>
    <script src="../stock-prices.js"></script>
    <script src="../ai-chat.js"></script>
</body>
</html>"""

def main():
    """Generate stock pages for all or a single symbol. Removes orphaned pages on full runs."""
    import sys

    # Create stocks directory
    stocks_dir = "/Users/dave/VSCODE/website/stocks"
    os.makedirs(stocks_dir, exist_ok=True)
    
    # Load stocks from file
    STOCKS = load_stocks()
    
    # Check for single stock flag
    single_stock = None
    if len(sys.argv) > 1:
        single_stock = sys.argv[1].upper()
        STOCKS = [s for s in STOCKS if s["symbol"] == single_stock]
        if not STOCKS:
            print(f"❌ Stock {single_stock} not found")
            return
    
    print(f"🚀 Generating {len(STOCKS)} stock page(s)...")
    
    # Safety check: count how many existing pages have news before wiping anything
    pages_with_news = 0
    if not single_stock:
        for s_ in STOCKS:
            p_ = os.path.join(stocks_dir, f"{s_['symbol']}.html")
            if os.path.exists(p_) and 'Read full article' in open(p_, encoding='utf-8').read():
                pages_with_news += 1
        print(f"📰 {pages_with_news} pages currently have news - will preserve all")

    # Skip orphan cleanup if running for single stock (flag mode)
    skip_cleanup = single_stock is not None
    
    for stock in STOCKS:
        symbol = stock["symbol"]
        filepath = os.path.join(stocks_dir, f"{symbol}.html")
        
        # Preserve existing news, related and analysis sections (and the values
        # update_stock_analysis.py maintains) if the file exists
        existing_news = ""
        existing_related = ""
        existing_analysis = ""
        robots = "noindex, follow"
        date_modified = "2026-09-25"
        old_content = ""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                old_content = f.read()
            match = re.search(r'<!-- NEWS_SECTION_START -->(.*?)<!-- NEWS_SECTION_END -->', old_content, re.DOTALL)
            if match:
                existing_news = match.group(1)
            elif 'Read full article' in old_content:
                # Old format without markers: don't silently wipe news just because markers are missing
                fallback = re.search(r'(<h2[^>]*>[^<]*[Nn]ews[^<]*</h2>.*?)(?=<!-- RELATED_SECTION_START -->|<!-- ANALYSIS_SECTION_START -->|</main>|</body>)', old_content, re.DOTALL)
                if fallback:
                    existing_news = fallback.group(1)
            match = re.search(r'<!-- RELATED_SECTION_START -->(.*?)<!-- RELATED_SECTION_END -->', old_content, re.DOTALL)
            if match:
                existing_related = match.group(1)
            match = re.search(r'<!-- ANALYSIS_SECTION_START -->(.*?)<!-- ANALYSIS_SECTION_END -->', old_content, re.DOTALL)
            if match:
                existing_analysis = match.group(1)
            match = re.search(r'<meta name="robots" content="([^"]*)">', old_content)
            if match:
                robots = match.group(1)
            match = re.search(r'"dateModified": "([0-9-]{10})', old_content)
            if match:
                date_modified = match.group(1)
        
        # Generate new HTML
        html = generate_stock_page(stock, robots, date_modified)
        
        # Insert preserved analysis section, and keep its data-based descriptions
        if existing_analysis.strip():
            html = html.replace(
                '<!-- ANALYSIS_SECTION_START -->\n        <!-- ANALYSIS_SECTION_END -->',
                f'<!-- ANALYSIS_SECTION_START -->{existing_analysis}<!-- ANALYSIS_SECTION_END -->'
            )
            for pattern in (r'<meta name="description" content="[^"]*">',
                            r'<meta property="og:description" content="[^"]*">',
                            r'<meta name="twitter:description" content="[^"]*">'):
                old_tag = re.search(pattern, old_content)
                if old_tag:
                    html = re.sub(pattern, lambda m: old_tag.group(0), html, count=1)
        
        # Insert preserved news section
        if existing_news:
            html = html.replace(
                '<!-- NEWS_SECTION_START -->\n        <!-- NEWS_SECTION_END -->',
                f'<!-- NEWS_SECTION_START -->{existing_news}<!-- NEWS_SECTION_END -->'
            )
        
        # Insert preserved related section
        if existing_related:
            html = html.replace(
                '<!-- RELATED_SECTION_START -->\n        <!-- RELATED_SECTION_END -->',
                f'<!-- RELATED_SECTION_START -->{existing_related}<!-- RELATED_SECTION_END -->'
            )
        
        # Write HTML file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ Created {symbol}.html")
    
    # Remove orphaned HTML files (only if running full generation, not single stock)
    if not skip_cleanup:
        valid_symbols = {s["symbol"] for s in STOCKS}
        removed = 0
        for f in os.listdir(stocks_dir):
            if f.endswith(".html"):
                symbol = f[:-5]
                if symbol not in valid_symbols:
                    os.remove(os.path.join(stocks_dir, f))
                    print(f"🗑️  Removed orphan: {f}")
                    removed += 1
        if removed:
            print(f"🗑️  Removed {removed} orphaned pages")

    # Post-generation safety check: verify news wasn't wiped
    if not single_stock:
        after_news = 0
        for s_ in STOCKS:
            p_ = os.path.join(stocks_dir, f"{s_['symbol']}.html")
            if os.path.exists(p_) and 'Read full article' in open(p_, encoding='utf-8').read():
                after_news += 1
        print(f"\n📰 News check: {after_news} pages have news after generation")
        if after_news < pages_with_news * 0.9:
            print(f"⚠️  WARNING: News dropped from {pages_with_news} to {after_news} pages!")
            print("   Run: python3 sync_news_to_stock_pages.py to recover")
        else:
            print("✅ News preserved correctly")

    print(f"\n✅ Generated {len(STOCKS)} stock pages in /stocks/ directory")

if __name__ == "__main__":
    main()
