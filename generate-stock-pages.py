#!/usr/bin/env python3
"""
Generate individual HTML stock pages for SEO.

Reads stocks.txt (3,467 stocks) and generates /website/stocks/{SYMBOL}.html for each.
Preserves existing news (<!-- NEWS_SECTION_START/END -->) and related sections
(<!-- RELATED_SECTION_START/END -->) when regenerating.

Usage:
    python3 generate-stock-pages.py           # Regenerate all 3,467 pages
    python3 generate-stock-pages.py AAPL      # Single stock only

Input:  /Users/ddewit/VSCODE/website/stocks.txt
Output: /Users/ddewit/VSCODE/website/stocks/*.html

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
    stocks_file = "/Users/ddewit/VSCODE/website/stocks.txt"
    
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



def generate_stock_page(stock):
    """Generate full HTML page for a stock including SEO metadata, JSON-LD schemas, nav, and CTA."""
    symbol = stock["symbol"]
    name = stock["name"]
    sector = stock["sector"]
    
    # Handle generic "Stock" sector
    if sector == "Stock":
        meta_desc = f"Analyze {name} ({symbol}) stock with AI-powered insights, technical indicators, and real-time data. Free stock analysis tool."
        sector_display = "General"
        about_text = f"{name} ({symbol}) is a publicly traded company. Use StockIQ's free analysis tool to get comprehensive insights into {symbol} stock performance, technical indicators, and AI-powered trading recommendations."
    else:
        meta_desc = f"Analyze {name} ({symbol}) stock with AI-powered insights, technical indicators, and real-time data. Free stock analysis tool for {sector} sector."
        sector_display = sector
        about_text = f"{name} ({symbol}) is a leading company in the {sector} sector. Use StockIQ's free analysis tool to get comprehensive insights into {symbol} stock performance, technical indicators, and AI-powered trading recommendations."
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} ({symbol}) Stock Analysis - Free AI-Powered Research | StockIQ</title>
    <meta name="description" content="{meta_desc}">
    <meta name="keywords" content="{symbol} stock analysis, {name} analysis, {symbol} technical analysis">
    <meta name="robots" content="index, follow">
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
      "@type": "NewsArticle",
      "headline": "{name} ({symbol}) Stock Analysis - Free AI-Powered Research",
      "description": "{meta_desc}",
      "image": "https://stockiq.tech/og-image.png",
      "datePublished": "2026-03-14T00:00:00Z",
      "dateModified": "2026-03-14T00:00:00Z",
      "author": {{
        "@type": "Organization",
        "name": "StockIQ",
        "url": "https://stockiq.tech"
      }},
      "publisher": {{
        "@type": "Organization",
        "name": "StockIQ",
        "logo": {{
          "@type": "ImageObject",
          "url": "https://stockiq.tech/stockiq-logo.png"
        }}
      }},
      "mainEntity": {{
        "@type": "FinancialInstrument",
        "name": "{name}",
        "ticker": "{symbol}",
        "industry": "{sector}"
      }}
    }}
    </script>
    
    <!-- Financial Instrument Schema -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "FinancialInstrument",
      "name": "{name}",
      "ticker": "{symbol}",
      "industry": "{sector}",
      "url": "https://stockiq.tech/stocks/{symbol}.html"
    }}
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
    <div id="sticky-banner" style="display: none; position: fixed; top: 0; left: 0; right: 0; background: var(--card-bg); color: var(--text-primary); text-align: center; padding: 10px 20px; z-index: 9999; font-size: 0.95rem; font-weight: 500; border-bottom: 1px solid var(--border-color);"></div>
<script>
(function() {{
if (window.innerWidth > 768) {{
const userId = localStorage.getItem('userId');
const cacheKey = 'userPaidStatus_' + (userId || 'anonymous');
const hasPaid = localStorage.getItem(cacheKey) === 'paid';
const banner = document.getElementById('sticky-banner');
if (hasPaid) {{
  banner.remove();
  document.documentElement.style.setProperty('--nav-top', '0');
}} else if (userId && userId !== 'anonymous') {{
  banner.style.display = 'block';
  banner.innerHTML = 'Professional Stock Analysis starting at <strong style="color: #22c55e;">$4.99/month</strong> - Get institutional-grade tools at accessible pricing';
  document.documentElement.style.setProperty('--nav-top', '41px');
}} else {{
  banner.style.display = 'block';
  banner.innerHTML = 'Sign up FREE to get <strong style="color: #22c55e;">15 free analyses</strong> - Professional tools at your fingertips';
  document.documentElement.style.setProperty('--nav-top', '41px');
}}
}} else {{
  document.getElementById('sticky-banner').remove();
  document.documentElement.style.setProperty('--nav-top', '0');
}}
}})();
</script>
    <nav class="top-nav" style="top: var(--nav-top, 41px);">
        <div class="nav-container">
            <div class="nav-brand">
                <a href="../index.html" style="display: flex; align-items: center; gap: 8px; text-decoration: none; color: inherit;">
                    <img src="../stockiq-logo.png" alt="StockIQ Logo" class="brand-logo" style="width: 24px; height: 24px;" width="24" height="24">
                    <span class="brand-text">StockIQ</span>
                </a>
            </div>

            <div class="desktop-nav">
                <a href="../index.html" class="nav-item home-link">Home</a>
                <div class="nav-item dropdown" onclick="showDropdown('analysis-dropdown', event)">
                    Analysis <span class="dropdown-arrow">▼</span>
                    <div class="dropdown-menu" id="analysis-dropdown">
                        <a href="../analysis.html?option=1">Stock & ETF Analysis</a>
                        <a href="../analysis.html?option=2">Trading Signals</a>
                    </div>
                </div>
                <div class="nav-item dropdown" onclick="showDropdown('screeners-dropdown', event)">
                    Screeners <span class="dropdown-arrow">▼</span>
                    <div class="dropdown-menu" id="screeners-dropdown">
                        <a href="../analysis.html?option=3">🇺🇸 US Markets</a>
                        <a href="../analysis.html?option=4">🇪🇺 Europe Markets</a>
                        <a href="../analysis.html?option=5">🌏 Asia Markets</a>
                        <a href="../analysis.html?option=6">🌏 Other Markets</a>
                    </div>
                </div>
                <div class="nav-item dropdown" onclick="showDropdown('crypto-dropdown', event)">
                    Crypto <span class="dropdown-arrow">▼</span>
                    <div class="dropdown-menu" id="crypto-dropdown">
                        <a href="../analysis.html?option=7">Crypto Universe Screener</a>
                    </div>
                </div>
                <div class="nav-item dropdown" onclick="showDropdown('account-dropdown', event)" style="margin-left: auto;">
                    Account <span class="dropdown-arrow">▼</span>
                    <div class="dropdown-menu" id="account-dropdown">
                        <a href="../signup.html" class="auth-link signup-link">Register</a>
                        <a href="../login.html" class="auth-link login-link">Login</a>
                        <a href="../dashboard.html" class="auth-link dashboard-link" style="display: none;">Dashboard</a>
                        <a href="#" class="auth-link signout-link" style="display: none;" onclick="signOut(event)">Sign Out</a>
                    </div>
                </div>
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
            <div class="mobile-section">
                <a href="../index.html">🏠 Home</a>
            </div>
            <div class="mobile-section">
                <div class="mobile-section-title">Analysis</div>
                <a href="../analysis.html?option=1">Stock & ETF Analysis</a>
                <a href="../analysis.html?option=2">Trading Signals</a>
            </div>
            <div class="mobile-section">
                <div class="mobile-section-title">Screeners</div>
                <a href="../analysis.html?option=3">🇺🇸 US Markets</a>
                <a href="../analysis.html?option=4">🇪🇺 Europe Markets</a>
                <a href="../analysis.html?option=5">🌏 Asia Markets</a>
                <a href="../analysis.html?option=6">🌏 Other Markets</a>
            </div>
            <div class="mobile-section">
                <div class="mobile-section-title">Crypto</div>
                <a href="../analysis.html?option=7">Crypto Universe Screener</a>
            </div>
            <div class="mobile-section">
                <div class="mobile-section-title">Account</div>
                <a href="../signup.html">Register</a>
                <a href="../login.html">Login</a>
            </div>
            <div class="mobile-section">
                <div class="mobile-section-title">Theme</div>
                <a href="#" onclick="toggleTheme()" id="mobile-theme-toggle">🌙 Dark Mode</a>
            </div>
        </div>
    </div>

    <main style="max-width: 1200px; margin: 0 auto; padding: 5px 20px 20px;">
        <div style="text-align: center; margin-bottom: 40px;">
            <h1>{name} ({symbol}) Stock Analysis</h1>
            <p style="font-size: 1.2rem; color: var(--text-secondary); margin-top: 10px;">
                Free AI-powered analysis and research for {name} stock
            </p>
            <p style="color: var(--text-secondary); margin-top: 10px;">
                Sector: {sector_display}
            </p>
        </div>

        <div style="background: var(--card-bg); border-radius: 12px; padding: 40px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="margin: 0;">Analyze {name} ({symbol}) Stock</h2><p style="margin: 0 0 20px 0; color: var(--text-secondary);">{about_text}</p>
            <p style="margin-bottom: 20px; color: var(--text-secondary);">
                Get instant AI-powered analysis including technical indicators, fundamental analysis, 
                risk assessment, and trading insights for {name} stock.
            </p>
            <a href="../analysis.html?symbol={symbol}&option=1&subOption=custom" class="cta-button">
                Analyze {symbol} Now →
            </a>
        </div>

        <!-- NEWS_SECTION_START -->
        <!-- NEWS_SECTION_END -->

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 40px;">
            <div style="background: var(--card-bg); border-radius: 12px; padding: 30px;">
                <h3>📈 Technical Analysis</h3>
                <p style="color: var(--text-secondary); margin-top: 10px;">
                    RSI, MACD, moving averages, support/resistance levels, and momentum indicators for {name} ({symbol}) stock.
                </p>
            </div>
            <div style="background: var(--card-bg); border-radius: 12px; padding: 30px;">
                <h3>🤖 AI Insights</h3>
                <p style="color: var(--text-secondary); margin-top: 10px;">
                    AI-powered analysis of {name} ({symbol}) fundamentals, growth prospects, and market position.
                </p>
            </div>
            <div style="background: var(--card-bg); border-radius: 12px; padding: 30px;">
                <h3>⚠️ Risk Assessment</h3>
                <p style="color: var(--text-secondary); margin-top: 10px;">
                    Comprehensive risk analysis including volatility, sector risks, and market conditions for {name} stock.
                </p>
            </div>
        </div>

        <div style="background: var(--card-bg); border-radius: 12px; padding: 40px;">
            <h2>Why Analyze {name} ({symbol}) with StockIQ?</h2>
            <ul style="list-style: none; padding: 0; margin-top: 20px;">
                <li style="padding: 10px 0; border-bottom: 1px solid var(--border-color);">
                    ✅ Free AI-powered analysis of {name} ({symbol}) stock
                </li>
                <li style="padding: 10px 0; border-bottom: 1px solid var(--border-color);">
                    ✅ Real-time technical indicators for {name} stock
                </li>
                <li style="padding: 10px 0; border-bottom: 1px solid var(--border-color);">
                    ✅ Comprehensive risk assessment for {symbol}
                </li>
                <li style="padding: 10px 0;">
                    ✅ No credit card required
                </li>
            </ul>
            <div style="margin-top: 30px; text-align: center;">
                <a href="../analysis.html?symbol={symbol}&option=1&subOption=custom" class="cta-button">
                    Start Analyzing {symbol} Free →
                </a>
            </div>
        </div>

        <!-- RELATED_SECTION_START -->
        <!-- RELATED_SECTION_END -->

    </main>

    <footer class="footer">
        <p>&copy; 2026 StockIQ - Professional Investment Research Platform</p>
        <p>Powered by AI • Real-time Data • Comprehensive Analysis</p>
        <p>
            <a href="../terms.html" style="color: #007bff; text-decoration: none;">Terms</a> • 
            <a href="../privacy-policy.html" style="color: #007bff; text-decoration: none;">Privacy</a> • 
            <a href="../support.html" style="color: #007bff; text-decoration: none;">Support</a>
        </p>
        <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border-color);">
            <p style="font-weight: 600; margin-bottom: 10px;">Popular Stocks:</p>
            <p style="line-height: 1.8;">
                <a href="AAPL.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">AAPL</a> •
                <a href="TSLA.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">TSLA</a> •
                <a href="NVDA.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">NVDA</a> •
                <a href="MSFT.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">MSFT</a> •
                <a href="GOOGL.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">GOOGL</a> •
                <a href="AMZN.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">AMZN</a> •
                <a href="META.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">META</a> •
                <a href="JPM.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">JPM</a> •
                <a href="V.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">V</a> •
                <a href="JNJ.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">JNJ</a> •
                <a href="WMT.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">WMT</a> •
                <a href="PG.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">PG</a> •
                <a href="XOM.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">XOM</a> •
                <a href="BAC.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">BAC</a> •
                <a href="DIS.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">DIS</a> •
                <a href="NFLX.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">NFLX</a> •
                <a href="ORCL.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">ORCL</a> •
                <a href="AMD.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">AMD</a> •
                <a href="INTC.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">INTC</a> •
                <a href="CSCO.html" style="color: #007bff; text-decoration: none; margin: 0 8px;">CSCO</a>
            </p>
        </div>
        <p style="margin-top: 15px;">
            <a href="https://instagram.com/stockiq.tech" target="_blank" style="color: #E4405F; text-decoration: none; font-size: 24px;" title="Follow us on Instagram">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                </svg>
            </a>
        </p>
    </footer>
    
    <script src="../sidebar.js"></script>
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
    <script src="../ai-chat.js"></script>
</body>
</html>"""

def main():
    """Generate stock pages for all or a single symbol. Removes orphaned pages on full runs."""
    import sys

    # Create stocks directory
    stocks_dir = "/Users/ddewit/VSCODE/website/stocks"
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
    
    # Skip orphan cleanup if running for single stock (flag mode)
    skip_cleanup = single_stock is not None
    
    for stock in STOCKS:
        symbol = stock["symbol"]
        filepath = os.path.join(stocks_dir, f"{symbol}.html")
        
        # Preserve existing news section if file exists
        existing_news = ""
        existing_related = ""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                old_content = f.read()
            match = re.search(r'<!-- NEWS_SECTION_START -->(.*?)<!-- NEWS_SECTION_END -->', old_content, re.DOTALL)
            if match:
                existing_news = match.group(1)
            match = re.search(r'<!-- RELATED_SECTION_START -->(.*?)<!-- RELATED_SECTION_END -->', old_content, re.DOTALL)
            if match:
                existing_related = match.group(1)
        
        # Generate new HTML
        html = generate_stock_page(stock)
        
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

    print(f"\n✅ Generated {len(STOCKS)} stock pages in /stocks/ directory")

if __name__ == "__main__":
    main()
