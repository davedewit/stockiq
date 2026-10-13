// Global goBack function - accessible from HTML onclick
function goBack() {
    // Clear URL parameters
    window.history.pushState({}, '', window.location.pathname);
    
    for (let i = 1; i <= 8; i++) {
const section = document.getElementById(`option-${i}`);
if (section) {
    section.style.display = 'none';
}
    }
    
    // Hide ASX sub-options
    const asxOptions = ['option-41', 'option-42', 'option-43'];
    asxOptions.forEach(optionId => {
const section = document.getElementById(optionId);
if (section) {
    section.style.display = 'none';
}
    });
    
    const results = document.getElementById('results');
    const backBtn = document.getElementById('back-btn');
    const mainMenu = document.getElementById('main-menu');
    const stockInput = document.getElementById('stock-input');
    const presets = document.getElementById('presets');
    const signalInput = document.getElementById('signal-input');
    
    if (results) results.style.display = 'none';
    if (backBtn) backBtn.style.display = 'none';
    if (mainMenu) mainMenu.style.cssText = 'display: block !important';
    if (stockInput) stockInput.style.display = 'none';
    if (presets) presets.style.display = 'none';
    if (signalInput) signalInput.style.display = 'none';
}

// Global variables
let activeDropdown = null;
let jobRunning = false;
let trialStatusTimeout = null;



// Handle URL parameters on page load
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const option = urlParams.get('option');
    if (option) {
        selectOption(parseInt(option));
    }
});

// Crypto CSV Export Function - comprehensive crypto data
function generateCryptoCSVExport(results, filename) {
    if (!results || results.length === 0) {
        console.warn('No crypto results to export');
        return null;
    }
    
    try {
        const headers = [
            'Rank', 'Symbol', 'Price', 'Score', 'Signal', 'Timeframe', 'Confidence',
            'RSI', '24h_Change_%', '7d_Change_%', '30d_Change_%', 'Volume_Ratio', 'Model_Probability_%',
            'MACD_Signal', 'BB_Signal', 'Momentum_Signal', 'Lower_Level', 'Upper_Level', 
            'Support', 'Resistance', 'ATR', 'Stoch_K', 'MACD_Trend', 'Top10_Status'
        ];
        
        const csvRows = [headers.join(',')];
        
        results.forEach((coin, index) => {
            const row = [
                index + 1,
                coin.symbol || 'N/A',
                (coin.price || 0).toFixed(8),
                coin.score || 0,
                signalLabel(coin.recommendation),
                horizonLabel(coin.timeframe),
                coin.confidence || 'LOW',
                (coin.rsi || 50).toFixed(1),
                (coin.change_24h || 0).toFixed(2),
                (coin.change_7d || 0).toFixed(2),
                (coin.change_30d || 0).toFixed(2),
                (coin.volume_ratio || 1).toFixed(2),
                (coin.profit_probability || 50).toFixed(0),
                `"${coin.macd_signal || 'No data'}"`,
                `"${coin.bb_signal || 'NEUTRAL'}"`,
                `"${coin.momentum_signal || 'NEUTRAL'}"`,
                (coin.stop_loss || 0).toFixed(8),
                (coin.take_profit || 0).toFixed(8),
                (coin.support || 0).toFixed(8),
                (coin.resistance || 0).toFixed(8),
                (coin.atr || 0).toFixed(8),
                (coin.stoch_k || 50).toFixed(1),
                coin.macd_trend || 'NEUTRAL',
                coin.prediction_status || ''
            ];
            csvRows.push(row.join(','));
        });
        
        const csvContent = csvRows.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        
        link.href = url;
        link.download = `${filename}_${new Date().toISOString().split('T')[0]}.csv`;
        link.style.display = 'none';
        
        console.log(`📊 Crypto CSV generated: ${filename}_${new Date().toISOString().split('T')[0]}.csv`);
        
        // Return CSV content for dashboard storage (no auto-download)
        return csvContent;
    } catch (error) {
        console.error('CSV export failed:', error);
        return null;
    }
}

// CSV Export Function - comprehensive stock analysis data
function generateExcelExport(results, filename) {
    if (!results || results.length === 0) {
        console.warn('No results to export');
        return null;
    }
    
    const headers = [
        'Rank', 'Symbol', 'Price', 'Currency', 'Score', 'Signal', 'Support', 'Resistance', 'Lower_Level', 'Upper_Level', 'Model_Probability_%', 'Horizon', 'Horizon_Days', 'Timeframe', 'Confidence_%',
        '24h_Change_%', '5d_Change_%', '7d_Change_%', '10d_Change_%', '30d_Change_%', '90d_Change_%', '200d_Change_%', 'YTD_Change_%',
        'RSI', 'MACD_Signal', 'BB_Signal', 'Momentum_Signal', 'Volume_Ratio', 'Stoch_K', 'ATR',
        'Price_vs_MA20_%', 'Price_vs_MA50_%', 'Price_vs_MA200_%',
        'Distance_52W_High_%', 'Distance_From_Low_%', '52W_High', '52W_Low',
        // PE_Ratio, Market_Cap, Beta, Dividend_Yield_%, Sector and Earnings_Risk are not exported: the screener
        // workers do not fetch them (they return fixed estimates), so they were not real data
        'Market_Regime', 'SPY_20d_Change_%', 'Score_Breakdown'
    ];
    
    const csvRows = [headers.join(',')];
    
    results.forEach((stock, index) => {
        const row = [
            index + 1,
            stock.symbol || 'N/A',
            (stock.price || 0).toFixed(2),
            screenerCurrencyName(stock),      // what the row's prices are in: London figures are pence
            stock.total_score || 0,
            `"${signalLabel(stock.recommendation)}"`,
            (stock.support || 0).toFixed(2),
            (stock.resistance || 0).toFixed(2),
            (stock.stop_loss || 0).toFixed(2),
            (stock.take_profit || 0).toFixed(2),
            (stock.profit_probability || 50).toFixed(0),
            `"${horizonLabel(stock.strategy_type)}"`,
            stock.hold_days || 'N/A',
            `"${horizonLabel(stock.timeframe)}"`,
            (stock.confidence || 50).toFixed(0),
            (stock.change_24h ?? stock.change_pct ?? 0).toFixed(2),  // workers call it change_24h
            (stock.change_5d || 0).toFixed(2),
            (stock.change_7d || 0).toFixed(2),
            (stock.change_10d || 0).toFixed(2),
            (stock.change_30d || 0).toFixed(2),
            (stock.change_90d || 0).toFixed(2),
            (stock.change_200d || 0).toFixed(2),
            (stock.ytd_change || 0).toFixed(2),
            (stock.rsi || 50).toFixed(1),
            `"${stock.macd_signal || 'NEUTRAL'}"`,
            `"${stock.bb_signal || 'NEUTRAL'}"`,
            `"${stock.momentum_signal || 'NEUTRAL'}"`,
            (stock.volume_ratio || 1).toFixed(2),
            (stock.stoch_k || 50).toFixed(1),
            (stock.atr || 0).toFixed(2),
            (stock.price_vs_ma20 || 0).toFixed(2),
            (stock.price_vs_ma50 || 0).toFixed(2),
            (stock.price_vs_ma200 || 0).toFixed(2),
            (stock.distance_from_52w_high || 0).toFixed(2),
            (stock.distance_from_52w_low ?? stock.distance_from_low ?? 0).toFixed(2),  // workers call it distance_from_52w_low
            (stock.high_52w || stock['52w_high'] || 0).toFixed(2),
            (stock.low_52w || stock['52w_low'] || 0).toFixed(2),
            `"${stock.market_regime || 'NEUTRAL'}"`,
            (stock.spy_change_20d || 0).toFixed(1),
            `"${(stock.score_breakdown || []).join(' | ')}"`
        ];
        csvRows.push(row.join(','));
    });
    
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        console.log(`📊 CSV generated: ${filename}_${new Date().toISOString().split('T')[0]}.csv`);
        
        // Return CSV content for dashboard storage (no auto-download)
        return csvContent;
    }
}

// Access Control Functions
function checkAccess(optionNumber) {
    console.log('checkAccess called for option:', optionNumber);
    console.log('authManager exists:', typeof authManager !== 'undefined');
    console.log('isAuthenticated:', typeof authManager !== 'undefined' ? authManager.isAuthenticated() : 'N/A');
    
    if (typeof authManager !== 'undefined' && authManager.isAuthenticated()) {
        console.log('Access granted - proceeding to option', optionNumber);
        selectOption(optionNumber);
    } else {
        console.log('Access denied - redirecting to registration');
        window.location.href = 'signup.html';
    }
}

// Navigation Functions

function showDropdown(dropdownId, event) {
    // Prevent dropdown from opening if clicking on home link
    if (event && event.target.closest('.home-link')) {
        return;
    }
    
    if (activeDropdown && activeDropdown !== dropdownId) {
        document.getElementById(activeDropdown).classList.remove('show');
    }
    
    const dropdown = document.getElementById(dropdownId);
    if (dropdown) {
        dropdown.classList.toggle('show');
        activeDropdown = dropdown.classList.contains('show') ? dropdownId : null;
    }
}

function toggleMobileMenu(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    const mobileMenu = document.getElementById('mobile-menu');
    const overlay = document.getElementById('mobile-menu-overlay');
    const hamburgerBtn = document.querySelector('.hamburger-btn');
    
    if (mobileMenu) mobileMenu.classList.toggle('open');
    if (overlay) overlay.classList.toggle('show');
    if (hamburgerBtn) hamburgerBtn.classList.toggle('active');
    document.body.classList.toggle('menu-open');
    
    // Scroll mobile menu to top when opening
    if (mobileMenu && mobileMenu.classList.contains('open')) {
        const menuContent = mobileMenu.querySelector('.mobile-menu-content');
        if (menuContent) {
            menuContent.scrollTop = 0;
        }
    }
}

function closeMobileMenu() {
    const mobileMenu = document.getElementById('mobile-menu');
    const overlay = document.getElementById('mobile-menu-overlay');
    const hamburgerBtn = document.querySelector('.hamburger-btn');
    
    if (mobileMenu) mobileMenu.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
    if (hamburgerBtn) hamburgerBtn.classList.remove('active');
    document.body.classList.remove('menu-open');
}

// Main menu navigation
function selectOption(optionNumber) {
    if (activeDropdown) {
        document.getElementById(activeDropdown).classList.remove('show');
        activeDropdown = null;
    }
    
    document.getElementById('main-menu').style.display = 'none';
    
    // Hide all option sections
    for (let i = 1; i <= 8; i++) {
        const section = document.getElementById(`option-${i}`);
        if (section) {
            section.style.display = 'none';
        }
    }
    
    // Handle ASX sub-options by redirecting to main ASX option
    if (optionNumber >= 41 && optionNumber <= 44) {
        const selectedSection = document.getElementById('option-4');
        if (selectedSection) {
            selectedSection.style.display = 'block';
        }
    } else {
        const selectedSection = document.getElementById(`option-${optionNumber}`);
        if (selectedSection) {
            selectedSection.style.display = 'block';
        }
    }
    
    // Update usage display for Stock & ETF Analysis
    if (optionNumber === 1 && typeof authManager !== 'undefined') {
        console.log('📊 Usage display updated for option 1');
    }
    
    // Initialize threshold slider when option 7 is shown
    if (optionNumber === 7) {
        setTimeout(() => initThresholdSlider(), 50);
    }
    
    document.getElementById('back-btn').style.display = 'block';
}

async function checkDailyUsageLimit() {
    // Skip for bots/crawlers
    if (isBotOrCrawler()) {
        console.log('🤖 Bot detected, skipping usage limit check');
        return true;
    }
    
    if (typeof authManager !== 'undefined') {
        // Force fresh check by refreshing usage data first
        await authManager.refreshUsageData();
        return await authManager.checkStockAnalysisAccess();
    }
    return true; // Allow if authManager not available
}

async function incrementDailyUsage() {
    if (typeof authManager !== 'undefined') {
        if (authManager.isAuthenticated()) {
            console.log('📊 Incrementing usage for user:', authManager.currentUser?.email);
            try {
                const result = await authManager.incrementUsage();
                console.log('📊 Usage increment result:', result);
                return result;
            } catch (error) {
                console.error('❌ Usage increment failed:', error);
                return null;
            }
        } else {
            console.log('📊 Incrementing anonymous usage');
            try {
                const result = await authManager.incrementAnonymousUsage();
                console.log('📊 Anonymous usage increment result:', result);
                return result;
            } catch (error) {
                console.error('❌ Anonymous usage increment failed:', error);
                return null;
            }
        }
    }
    console.warn('⚠️ authManager not available for usage increment');
    return null;
}

// The visitor's count ("3/5 today") is worked out by authManager.getStockAnalysisStatus (auth.js), written into the
// hidden #trial-status-display that auth.js's displayTrialStatus() makes on every page, and shown from there as the chip
// in the header bar by visitor-bar.js. This page only has to write the new count after a use has been counted.
function refreshUsageCount() {
    if (typeof authManager === 'undefined') return;
    setTimeout(async () => {
        try {
            const status = await authManager.getStockAnalysisStatus(true);
            const badge = document.getElementById('trial-status-display');
            if (badge && status && status.message) badge.innerHTML = status.message;
        } catch (e) { /* the count is shown again at the next page load */ }
    }, 500);
}

function showStockInput() {
    document.getElementById('stock-input').style.display = 'block';
    document.getElementById('presets').style.display = 'none';
}

function showPresets() {
    document.getElementById('presets').style.display = 'block';
    document.getElementById('stock-input').style.display = 'none';
}

function showSignalInput() {
    document.getElementById('signal-input').style.display = 'block';
}

function showCoinSearch() {
    const coinSearch = document.getElementById('coin-search');
    const cryptoScreener = document.getElementById('crypto-screener');
    if (coinSearch) coinSearch.style.display = 'block';
    if (cryptoScreener) cryptoScreener.style.display = 'none';
}



// Notification system functions


function showAnalysisModal(analysis) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.8); z-index: 10000; display: flex;
        align-items: center; justify-content: center; padding: 20px;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
        background: var(--card-bg); border-radius: 10px; padding: 30px;
        max-width: 800px; max-height: 80vh; overflow-y: auto; position: relative;
    `;
    
    content.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="color: var(--text-primary);">${analysis.symbol} Analysis Report</h2>
            <button onclick="this.closest('.modal').remove()" 
                    style="background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-primary);">×</button>
        </div>
        <div style="white-space: pre-wrap; font-family: monospace; font-size: 14px; color: var(--text-primary);">
            ${analysis.report}
        </div>
    `;
    
    modal.appendChild(content);
    modal.className = 'modal';
    document.body.appendChild(modal);
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

function showAnonymousUpgradeModal() {
    const modal = document.createElement('div');
    modal.id = 'anonymous-upgrade-modal';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.3); z-index: 99999; display: none; align-items: center; justify-content: center; backdrop-filter: blur(2px);';
    modal.innerHTML = `
        <div style="background: var(--card-bg); padding: 40px 30px; border-radius: 16px; max-width: 480px; width: 90%; text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
            <div style="font-size: 48px; margin-bottom: 20px;">🎉</div>
            <h2 style="color: var(--text-primary); margin-bottom: 15px; font-size: 1.8rem;">You've Used Your Free Daily Analysis!</h2>
            <p style="color: var(--text-secondary); margin-bottom: 25px; font-size: 1.1rem; line-height: 1.6;">
                Want <strong style="color: #007bff;">15 free analyses</strong>? That is 5 a day for 3 days.<br>
                Create a free account in 30 seconds.
            </p>
            <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                <a href="signup.html" style="background: #007bff; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 1.1rem;">
                    Create Free Account
                </a>
                <button onclick="showStickyRegisterButton()" style="background: transparent; color: var(--text-secondary); padding: 14px 32px; border: 2px solid var(--border-color); border-radius: 8px; font-weight: 600; font-size: 1.1rem; cursor: pointer;">
                    Maybe Later
                </button>
            </div>
            <p style="color: var(--text-secondary); margin-top: 20px; font-size: 0.9rem;">
                ✓ No credit card required &nbsp;•&nbsp; ✓ 3-day free trial
            </p>
        </div>
    `;
    document.body.appendChild(modal);
    
    let modalShown = false;
    const showModalOnScroll = () => {
        if (modalShown) return;
        const scrollPosition = window.scrollY;
        const pageHeight = document.documentElement.scrollHeight - window.innerHeight;
        if (scrollPosition > pageHeight * 0.3) {
            modal.style.display = 'flex';
            modalShown = true;
            window.removeEventListener('scroll', showModalOnScroll);
        }
    };
    window.addEventListener('scroll', showModalOnScroll);
}

// The round "Start 3-Day Free Trial" / "Upgrade Plan" button is drawn by visitor-bar.js, from the visitor's count.
// These two names stay because the pop-up's "Maybe Later" and the access check call them.
function showStickyRegisterButton() {
    const modal = document.getElementById('anonymous-upgrade-modal');
    if (modal) modal.remove();
    localStorage.setItem('showStickyRegister', 'true');
    if (window.visitorBar) window.visitorBar.refresh();
}

function showStickyUpgradeButton() {
    if (window.visitorBar) window.visitorBar.refresh();
}

function formatDate(timestamp) {
    // Ensure timestamp is treated as UTC if no timezone specified
    let dateStr = timestamp;
    if (!timestamp.includes('Z') && !timestamp.includes('+') && !timestamp.includes('-', 10)) {
        dateStr = timestamp + 'Z';  // Add UTC indicator
    }
    return new Date(dateStr).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}

function getRerunUrl(item, timestamp) {
    const companyName = item.companyName || '';
    const symbol = item.symbol || '';
    
    // Check if it's a single coin analysis
    if (companyName.includes('Coin Analysis')) {
        return `analysis.html?option=72&subOption=single&coinSymbol=${encodeURIComponent(symbol)}&autorun=true&refresh=true&t=${timestamp}`;
    }
    
    if (symbol === 'COINSPOT_SCREENER' || symbol.includes('COINSPOT')) {
        return `analysis.html?option=7&subOption=1&autorun=true&refresh=true&t=${timestamp}`;
    }
    
    if (symbol === 'UK_FTSE_100' || symbol.trim() === 'UK_FTSE_100' || companyName === 'UK FTSE 100 Screener') {
        return `analysis.html?option=5&subOption=ftse100&autorun=true&refresh=true&t=${timestamp}`;
    }
    
    const screenerMappings = {
        'S&P 100 (LargeCap)': 'analysis.html?option=3&subOption=100&autorun=true',
        'S&P 400+600 (Mid+SmallCap)': 'analysis.html?option=3&subOption=2&autorun=true',
        'S&P 500 Complete Screener': 'analysis.html?option=3&subOption=3&autorun=true',
        'S&P Composite 1500': 'analysis.html?option=3&subOption=4&autorun=true',
        'Russell 1000 Large-Cap Screener': 'analysis.html?option=3&subOption=5&autorun=true',
        'Russell 2000 Small-Cap Screener': 'analysis.html?option=3&subOption=6&autorun=true',
        'NASDAQ 100 Tech Screener': 'analysis.html?option=3&subOption=7&autorun=true',
        'Dow Jones 30 Blue Chip Screener': 'analysis.html?option=3&subOption=8&autorun=true',
        'ASX 50 Screener': 'analysis.html?option=5&subOption=50&autorun=true',
        'ASX 100 Screener': 'analysis.html?option=5&subOption=100&autorun=true',
        'ASX 200 Screener': 'analysis.html?option=5&subOption=200&autorun=true',
        'ASX 300 Screener': 'analysis.html?option=5&subOption=300&autorun=true',
        'Japan Nikkei 225 Screener': 'analysis.html?option=5&subOption=nikkei225&autorun=true',
        'UK FTSE 100 Screener': 'analysis.html?option=4&subOption=ftse100&autorun=true',
        'Crypto Universe Screener': 'analysis.html?option=7&subOption=1&autorun=true'
    };
    
    // screeners that carry their own name in screeners.js (the Germany DAX 40 and later markets)
    if (typeof SHARE_SCREENERS !== 'undefined') Object.keys(SHARE_SCREENERS).forEach(key => {
        const r = SHARE_SCREENERS[key].report, at = key.indexOf('-');
        if (r) screenerMappings[r.title] = `analysis.html?option=${key.slice(0, at)}&subOption=${key.slice(at + 1)}&autorun=true`;
    });
    if (screenerMappings[companyName]) {
        return `${screenerMappings[companyName]}&refresh=true&t=${timestamp}`;
    }
    
    if (companyName.includes('Crypto') || companyName.includes('CoinSpot') || companyName.includes('coinspot')) {
        return `analysis.html?option=7&subOption=1&autorun=true&refresh=true&t=${timestamp}`;
    }
    
    return `analysis.html?symbol=${encodeURIComponent(symbol)}&option=1&subOption=custom&autorun=true&refresh=true&t=${timestamp}`;
}

function rerunFromNotification(analysisId) {
    console.log('🔄 rerunFromNotification called with:', analysisId);
    console.log('📊 analysisHistory:', analysisHistory);
    const item = analysisHistory.find(analysis => analysis.analysisId === analysisId);
    console.log('📌 Found item:', item);
    if (!item) {
        console.error('❌ Item not found for analysisId:', analysisId);
        return;
    }
    
    const timestamp = Date.now();
    const url = getRerunUrl(item, timestamp);
    console.log('🔗 Opening URL:', url);
    window.location.href = url;
}

// Initialize notification system on page load
document.addEventListener('DOMContentLoaded', async function() {
    const userId = localStorage.getItem('userId');
    if (userId && userId !== 'anonymous') {
        const bell = document.getElementById('notification-bell');
        const mobileBell = document.getElementById('mobile-notification-bell');
        if (bell) bell.style.display = 'block';
        if (mobileBell) mobileBell.style.display = 'block';
        updateNotificationBell();
        preloadNotifications();
    }
    
    // Show promotional banner for non-paying users and adjust spacing
    setTimeout(async () => {
        const currentUserId = localStorage.getItem('userId');
        const cacheKey = `userPaidStatus_${currentUserId || 'anonymous'}`;
        const cachedStatus = localStorage.getItem(cacheKey);
        if (cachedStatus === 'paid') return;
        let isPaid = false;
        
        if (!currentUserId || currentUserId === 'anonymous') {
            isPaid = false;
        } else if (typeof authManager !== 'undefined') {
            try {
                const subStatus = await authManager.getSubscriptionStatus();
                isPaid = subStatus.hasPaid;
            } catch (e) {
                isPaid = false;
            }
        }
        
        localStorage.setItem(cacheKey, isPaid ? 'paid' : 'unpaid');
        if (isPaid) location.reload();
    }, 0);
    
    // Check for autorun parameter
    const urlParams2 = new URLSearchParams(window.location.search);
    const autorun = urlParams2.get('autorun');
    const symbol = urlParams2.get('symbol');
    const coinSymbol = urlParams2.get('coinSymbol');
    const option = urlParams2.get('option');
    const subOption = urlParams2.get('subOption');
    
    if (autorun === 'true' && isBotOrCrawler()) {
        console.log('🤖 Bot detected, skipping autorun analysis');
    } else if (autorun === 'true' && option === '72' && coinSymbol) {
        // Auto-run single coin analysis
        selectOption(7);
        requestAnimationFrame(() => {
            const coinSearch = document.getElementById('coin-search');
            const cryptoScreener = document.getElementById('crypto-screener');
            if (coinSearch) coinSearch.style.display = 'block';
            if (cryptoScreener) cryptoScreener.style.display = 'none';
            const coinInput = document.getElementById('coin-symbol-input');
            if (coinInput) coinInput.value = coinSymbol;
            requestAnimationFrame(() => runAnalysis(72, 'single'));
        });
    } else if (autorun === 'true' && option && subOption) {
        // Auto-run analysis after a short delay
        setTimeout(() => {
            if (option === '1' && subOption === 'custom' && symbol) {
                document.getElementById('symbols-input').value = symbol;
                selectOption(1);
                showStockInput();
                setTimeout(() => {
                    const btn = document.querySelector('.run-btn');
                    if (btn) btn.classList.add('active');
                    window.activeAnalysisButton = btn;
                    runAnalysis(1, 'custom');
                }, 1000);
            } else if (option === '7' && subOption) {
                selectOption(7);
                setTimeout(() => {
                    const btn = document.querySelector('.sub-btn');
                    if (btn) btn.classList.add('active');
                    window.activeAnalysisButton = btn;
                    runAnalysis(7, subOption);
                }, 1000);
            } else {
                selectOption(parseInt(option));
                setTimeout(() => {
                    console.log(`🔍 Autorun: Looking for button with option=${option}, subOption=${subOption}`);
                    const buttons = document.querySelectorAll('.screener-btn');
                    buttons.forEach(btn => {
                        const onclickStr = btn.onclick ? btn.onclick.toString() : '';
                        const pattern1 = `runAnalysis(${option}, '${subOption}',`;
                        const pattern2 = `runAnalysis(${option}, '${subOption}')`;
                        if (onclickStr.includes(pattern1) || onclickStr.includes(pattern2)) {
                            console.log(`✅ Found matching button:`, btn.textContent.trim());
                            btn.classList.add('active');
                            window.activeAnalysisButton = btn;
                        }
                    });
                    console.log(`🚀 Running analysis: option=${option}, subOption=${subOption}`);
                    runAnalysis(parseInt(option), subOption);
                }, 1000);
            }
        }, 2000);
    }
    
    // Hide nav on scroll down (mobile only) - delay to prevent race condition
    let lastScroll = 0;
    let scrollEnabled = false;
    setTimeout(() => { scrollEnabled = true; }, 1000);
    window.addEventListener('scroll', function() {
        if (scrollEnabled && window.innerWidth <= 768) {
            const currentScroll = window.pageYOffset;
            const nav = document.querySelector('.top-nav');
            if (currentScroll > lastScroll && currentScroll > 100) {
                nav.style.transform = 'translateY(-100%)';
            } else {
                nav.style.transform = 'translateY(0)';
            }
            lastScroll = currentScroll;
        }
    });
});

// Show notification bell immediately if user is logged in
const userId = localStorage.getItem('userId');
if (userId && userId !== 'anonymous') {
    setTimeout(() => {
        const bell = document.getElementById('notification-bell');
        if (bell) {
            bell.style.display = 'block';
        }
        updateNotificationBell();
        preloadNotifications();
    }, 0);
}

// Check for URL parameters on page load
const urlParams3 = new URLSearchParams(window.location.search);
const option3 = urlParams3.get('option');
const symbol3 = urlParams3.get('symbol');
const subOption3 = urlParams3.get('subOption');

if (option3 && symbol3 && subOption3) {
    // Pre-fill form based on URL parameters
    setTimeout(() => {
        if (option3 === '1' && subOption3 === 'custom') {
            document.getElementById('symbols-input').value = symbol3;
            selectOption(1);
            showStockInput();
        }
    }, 500);
}

// Bot detection helper function
function isBotOrCrawler() {
    const userAgent = navigator.userAgent.toLowerCase();
    const botPatterns = [
        'googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider',
        'yandexbot', 'facebookexternalhit', 'twitterbot', 'rogerbot',
        'linkedinbot', 'embedly', 'quora link preview', 'showyoubot',
        'outbrain', 'pinterest', 'developers.google.com/+/web/snippet',
        'crawler', 'spider', 'bot', 'headless'
    ];
    return botPatterns.some(pattern => userAgent.includes(pattern));
}

// A screener's entry in SHARE_SCREENERS (screeners.js, a script tag in analysis.html), or null. Should the page in a
// visitor's browser be an older copy without that tag, the file is fetched here the first time a screener is asked for.
async function shareScreener(key) {
    if (typeof SHARE_SCREENERS === 'undefined') {
        try {
            await new Promise((done, failed) => {
                const tag = document.createElement('script');
                tag.src = 'screeners.js'; tag.onload = done; tag.onerror = failed;
                document.head.appendChild(tag);
                setTimeout(failed, 10000);
            });
        } catch (e) { return null; }
    }
    return typeof SHARE_SCREENERS !== 'undefined' && SHARE_SCREENERS[key] ? SHARE_SCREENERS[key] : null;
}

// The `report` of a screener that carries its own (screeners.js; the Germany DAX 40 and later markets), or null
function marketReport(option, subOption) {
    const def = typeof SHARE_SCREENERS !== 'undefined' ? SHARE_SCREENERS[option + '-' + subOption] : null;
    return def && def.report ? def.report : null;
}

// Every share screener is run by this one routine; a screener is an entry in SHARE_SCREENERS (screeners.js): its list,
// its workers, its name. (Until 13 Oct 2026 runAnalysis held 14 copies of it, one a screener.)
async function runShareScreener(def, subOption) {
    const use = Math.min(def.workers.length, def.use);
    const startTime = Date.now();
    const workerPayloads = [];
    for (let i = 0; i < use; i++) {
        if (!def.list) {          // the workers hold the list: each is sent its number and takes its own ten stocks
            workerPayloads.push({ url: def.workers[i], payload: { worker_id: i + 1, batch_size: 10 }, workerId: i + 1 });
            continue;
        }
        // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
        const perWorker = Math.max(10, Math.ceil(def.list.length / use));
        const stockBatch = def.list.slice(i * perWorker, i * perWorker + perWorker);
        // never send an empty batch
        if (stockBatch.length > 0) workerPayloads.push({ url: def.workers[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
    }
    const allWorkerResults = await Promise.all(workerPayloads.map(async (workerData) => {
        const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
        if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
        const result = await response.json();
        return { result, workerId: workerData.workerId };
    }));
    const totalTime = def.timeText ? ((Date.now() - startTime) / 1000).toFixed(1) : (Date.now() - startTime) / 1000;
    let allResults = [];
    allWorkerResults.forEach((workerResult) => {
        const answer = workerResult.result;
        const counted = def.merge === 'loose' ? (answer && answer.results) : def.merge === 'guarded' ? (answer && answer.success && answer.results) : (answer.success && answer.results);
        if (counted) allResults = allResults.concat(answer.results);
    });
    allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
    const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: def.size, processing_time: totalTime };
    const csvData = generateExcelExport(allResults, def.csv);
    const result = def.format === 'us' ? formatOption3Result(apiData, subOption) : def.format === 'asx' ? formatASXResult(apiData, subOption)
        : def.format === 'nikkei' ? formatNikkeiResult(apiData) : def.format === 'market' ? formatMarketResult(apiData, def.report, def.list.length) : formatFTSEResult(apiData);
    result.csvData = csvData;
    return result;
}

// The UK FTSE 100 report (it stood inside runAnalysis)
function formatFTSEResult(apiData) {
    const allResults = apiData.results;
    let output = `
============================================================
🇬🇧 UK FTSE 100 RESULTS (REAL-TIME DATA)
============================================================

Screening Universe: 100 FTSE stocks
Market Type: London Stock Exchange
Universe Size: 100
Analysis Date: ${new Date().toLocaleString()}

`;
    
    if (allResults && allResults.length > 0) {
        const topCount = Math.min(10, allResults.length);
        output += `🟢 TOP ${topCount} BY SCORE:\n`;
        allResults.slice(0, topCount).forEach((stock, i) => {
            const symbol = (stock.symbol || 'N/A').padEnd(8);
            const price = `${screenerMoney(stock, stock.current_price || stock.price, 'GBp')}`.padStart(8);
            const score = (stock.total_score || stock.score || 0) >= 0 ? `+${(stock.total_score || stock.score || 0).toFixed(1)}` : `${(stock.total_score || stock.score || 0).toFixed(1)}`;
            const rsi = (stock.rsi || 0).toFixed(1).padStart(5);
            const ytd = (stock.ytd_change || 0) >= 0 ? `+${(stock.ytd_change || 0).toFixed(1)}%` : `${(stock.ytd_change || 0).toFixed(1)}%`;
            const vol = `${(stock.volume_ratio || 1).toFixed(1)}x`;
            output += `${(i+1).toString().padStart(2)}. ${symbol} ${price} | Score: ${score} | RSI: ${rsi} | YTD: ${ytd}, Vol: ${vol}\n`;
        });
        
        output += '\n</pre><div style="margin: 20px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;">📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html#reports" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.</div><pre style="white-space: pre-wrap; font-family: monospace;">\n🎯 TOP 3 DETAILED ANALYSIS:\n';
        output += '================================================================\n';
        allResults.slice(0, 3).forEach((stock, i) => {
            output += `${i+1}. ${stock.symbol}: ${screenerMoney(stock, stock.price, 'GBp')} | ${signalLabel(stock.recommendation)} | Score: ${(stock.total_score || stock.score || 0) >= 0 ? '+' : ''}${(stock.total_score || stock.score || 0).toFixed(1)}\n`;
            
            if (stock.score_breakdown && stock.score_breakdown.length > 0) {
                output += '   📊 Score Breakdown:\n';
                stock.score_breakdown.forEach(breakdown => {
                    output += `      ${breakdown}\n`;
                });
            }
            
            output += `   📈 Technical: RSI ${(stock.rsi || 50).toFixed(1)} | MACD ${stock.macd_signal || 'NEUTRAL'}\n`;
            output += `   💰 Levels: Support ${screenerMoney(stock, stock.support, 'GBp')} | Resistance ${screenerMoney(stock, stock.resistance, 'GBp')}\n`;
            output += `   📏 Reference levels: Lower ${screenerMoney(stock, stock.stop_loss, 'GBp')} | Upper ${screenerMoney(stock, stock.take_profit, 'GBp')}\n`;
            output += `   📊 Horizon: ${horizonLabel(stock.strategy_type)} | Confidence: ${(stock.confidence || 0).toFixed(0)}%\n\n`;
        });
        
        const positiveStocks = allResults.filter(s => (s.total_score || s.score || 0) > 0).length;
        const negativeStocks = allResults.filter(s => (s.total_score || s.score || 0) < 0).length;
        const avgScore = allResults.reduce((sum, s) => sum + (s.total_score || s.score || 0), 0) / allResults.length;
        
        output += `\n📊 ANALYSIS SUMMARY:\n`;
        output += `• Total stocks analyzed: ${allResults.length}\n`;
        output += `• Stocks with positive scores: ${positiveStocks}\n`;
        output += `• Stocks with negative scores: ${negativeStocks}\n`;
        output += `• Average score: ${avgScore.toFixed(1)}\n`;
        output += `• Success rate: ${((allResults.length/100)*100).toFixed(1)}%\n`;
    }
    
    output += `\n✅ Real-time UK FTSE 100 complete!`;
    
    const htmlOutput = `<pre style="white-space: pre-wrap; font-family: monospace;">${output}</pre>`;
    
    return { type: 'option_4_ftse100_screener', data: htmlOutput };
}

async function runAnalysis(option, subOption, event) {
    console.log('🔍 runAnalysis called with option:', option, 'subOption:', subOption);
    
    // Skip all access checks for bots/crawlers
    if (isBotOrCrawler()) {
        console.log('🤖 Bot detected in runAnalysis, skipping all checks');
        return;
    }
    
    // Prevent double execution
    if (window.analysisInProgress) {
        console.log('🔍 Analysis already in progress, ignoring...');
        return;
    }
    window.analysisInProgress = true;
    window.analysisActivelyRunning = false; // Track if analysis is actively running vs just checking
    
    // Add active class to clicked button IMMEDIATELY
    if (event && event.target) {
        // Clear all active buttons first
        document.querySelectorAll('.screener-btn, .menu-btn, .sub-btn, .preset-btn, .run-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        window.activeAnalysisButton = event.target;
    } else if (!window.activeAnalysisButton) {
        // If no event (autorun), find and highlight the button immediately
        const buttons = document.querySelectorAll('.screener-btn, .menu-btn, .sub-btn, .preset-btn, .run-btn');
        buttons.forEach(btn => {
            const onclickStr = btn.onclick ? btn.onclick.toString() : '';
            if (onclickStr.includes(`runAnalysis(${option}, '${subOption}',`) || onclickStr.includes(`runAnalysis(${option}, '${subOption}')`)) {
                btn.classList.add('active');
                window.activeAnalysisButton = btn;
            }
        });
    }
    
    // Show UI immediately
    document.getElementById('results').style.display = 'block';
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results-content').innerHTML = '';
    jobRunning = true;
    window.analysisActivelyRunning = true; // Mark as actively running
    
    // Update loading text based on option type
    const loadingText = document.getElementById('loading-text');
    if (loadingText) {
        if (option >= 3 && option <= 8) {
            loadingText.textContent = 'Screening in progress...';
        } else {
            loadingText.textContent = 'Analysis in progress...';
        }
    }
    
    // Clear any pending trial status updates
    if (trialStatusTimeout) {
        clearTimeout(trialStatusTimeout);
        trialStatusTimeout = null;
    }
    document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
    
    // Check daily usage limits for Stock & ETF Analysis (option 1)
    if (option === 1) {
        // For custom stock analysis, check how many symbols first
        let symbolCount = 1; // Default to 1
        if (subOption === 'custom') {
            const symbols = document.getElementById('symbols-input').value;
            if (!symbols.trim()) {
                document.getElementById('loading').style.display = 'none';
                jobRunning = false;
                window.analysisInProgress = false; 
                if (window.activeAnalysisButton) window.activeAnalysisButton.classList.remove("active");
                // Validation removed to prevent popup
                return;
            }
            symbolCount = symbols.split(',').map(s => s.trim()).filter(s => s.length > 0).length;
        }
        
        // Check if user has enough remaining analyses for all symbols
        const canAccess = await checkDailyUsageLimit();
        if (!canAccess) {
            document.getElementById('loading').style.display = 'none';
            jobRunning = false;
            window.analysisInProgress = false; 
            if (window.activeAnalysisButton) window.activeAnalysisButton.classList.remove("active");
            return;
        }
        
        // Check if user has enough remaining analyses for the number of symbols
        if (typeof authManager !== 'undefined') {
            const status = await authManager.getStockAnalysisStatus();
            const remaining = status.message.match(/(\d+)/);
            const remainingCount = remaining ? parseInt(remaining[1]) : 0;
            
            if (remainingCount < symbolCount) {
                document.getElementById('loading').style.display = 'none';
                jobRunning = false;
                window.analysisInProgress = false;
                if (window.activeAnalysisButton) window.activeAnalysisButton.classList.remove("active");
                // Only show alert if analysis is not actively running (prevents popup when clicking out)
                if (!window.analysisActivelyRunning) {
                    alert(`You need ${symbolCount} analyses but only have ${remainingCount} remaining today.`);
                }
                return;
            }
        }
        
        // Show user how many analyses will be used if more than 1
        if (symbolCount > 1) {
            console.log(`📊 Using ${symbolCount} analyses for ${symbolCount} stocks`);
        }
        
        // Increment usage counter for each symbol
        for (let i = 0; i < symbolCount; i++) {
            await incrementDailyUsage();
        }
        
        refreshUsageCount();        // the count after this use, for the chip in the header bar
    }
    
    // Check daily usage limits for all options (2-8, 72) for non-authenticated users
    if ((option >= 2 && option <= 8) || option === 72) {
        // For option 2 (Trading Signals), check symbol count only for custom input
        var symbolCount = 1; // Default to 1 - use var so it's available in else block
        if (option === 2 && subOption === 'custom') {
            const symbolsInput = document.getElementById('signals-symbols');
            if (symbolsInput && symbolsInput.value && symbolsInput.value.trim()) {
                symbolCount = symbolsInput.value.split(',').map(s => s.trim()).filter(s => s.length > 0).length;
            }
        }
        // For option 2 with 'auto' subOption, always count as 1 regardless of input field
        
        // For non-authenticated users, check daily limit
        if (typeof authManager === 'undefined' || !authManager.isAuthenticated()) {
            const canAccess = await checkDailyUsageLimit();
            if (!canAccess) {
                document.getElementById('loading').style.display = 'none';
                jobRunning = false;
                return;
            }
            
            // Increment usage counter for each symbol (for option 2) or once (for others)
            for (let i = 0; i < symbolCount; i++) {
                await incrementDailyUsage();
            }
            
            refreshUsageCount();        // the count after this use, for the chip in the header bar
        } else {
            // For authenticated users (including Facebook/Google), increment usage for premium features
            // Check if user has remaining uses (only for authenticated users)
            if (typeof authManager !== 'undefined' && authManager.isAuthenticated()) {
                const canAccess = await checkDailyUsageLimit();
                if (!canAccess) {
                    document.getElementById('loading').style.display = 'none';
                    jobRunning = false;
                    return;
                }
            }
            
            // Check if user has enough remaining analyses for the number of symbols (option 2 only)
            if (option === 2 && typeof authManager !== 'undefined') {
                const status = await authManager.getStockAnalysisStatus();
                const remaining = status.message.match(/(\d+)/);
                const remainingCount = remaining ? parseInt(remaining[1]) : 0;
                
                if (remainingCount < symbolCount) {
                    document.getElementById('loading').style.display = 'none';
                    jobRunning = false;
                    window.analysisInProgress = false;
                    if (window.activeAnalysisButton) window.activeAnalysisButton.classList.remove("active");
                    // Only show alert if analysis is not actively running (prevents popup when clicking out)
                    if (!window.analysisActivelyRunning) {
                        alert(`You need ${symbolCount} analyses but only have ${remainingCount} remaining today.`);
                    }
                    return;
                }
            }
            
            // Increment usage counter for each symbol (for option 2) or once (for others)
            for (let i = 0; i < symbolCount; i++) {
                await incrementDailyUsage();
            }
            
            refreshUsageCount();        // the count after this use, for the chip in the header bar
        }
    }
    
    // Update UI after successful usage increment for all options
    if (typeof authManager !== 'undefined') {
        setTimeout(() => {
            if (typeof updatePadlockIcons === 'function') {
                updatePadlockIcons();
            }
        }, 100);
    }
    
    // Increment analysis counter
    incrementAnalysisCounter(option, subOption);
    
    try {
        let requestData = { option: option, subOption: subOption };
        
        let result;
        
        const userId = localStorage.getItem('userId');
        
        if (option === 1 && subOption === 'custom') {
            const symbols = document.getElementById('symbols-input').value;
            if (!symbols.trim()) throw new Error('Please enter at least one stock symbol');
            
            const payload = { 
                symbols: symbols.split(',').map(s => s.trim().toUpperCase()),
                timezone_offset: -new Date().getTimezoneOffset() / 60,
                skipHistorySave: true
            };
            if (userId) payload.userId = userId;
            const response = await fetch('https://5oqosafg2mflk7oyydkk3d3rdq0amufq.lambda-url.us-east-1.on.aws/', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error(`API Error: ${response.status}`);
            result = await formatOption11Result(await response.json());
        } else if (option === 1 && (subOption === 'mag7' || subOption === 'dow30' || subOption === 'sp500' || subOption === 'etf')) {
            const presets = { mag7: ['AAPL','MSFT','GOOGL','AMZN','NVDA','TSLA','META'], dow30: ['AAPL','MSFT','UNH','GS','HD'], sp500: ['AAPL','MSFT','GOOGL','AMZN','NVDA'], etf: ['SPY','QQQ','VTI','IWM'] };
            const payload = { 
                symbols: presets[subOption],
                timezone_offset: -new Date().getTimezoneOffset() / 60,
                skipHistorySave: true  // Web UI handles history saving
            };
            if (userId) payload.userId = userId; // Only include if logged in
            const response = await fetch('https://5oqosafg2mflk7oyydkk3d3rdq0amufq.lambda-url.us-east-1.on.aws/', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error(`API Error: ${response.status}`);
            result = await formatOption11Result(await response.json());
        } else if (option === 2 && subOption === 'custom') {
            const symbols = document.getElementById('signals-symbols').value;
            if (!symbols.trim()) throw new Error('Please enter at least one stock symbol');
            const payload = { symbols: symbols.split(',').map(s => s.trim().toUpperCase()) };
            const response = await fetch('https://bqsbauyuyo2fygbgeswaloqtse0oxtio.lambda-url.us-east-1.on.aws/', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error(`API Error: ${response.status}`);
            result = formatOption2Result(await response.json());
        } else if (option === 2 && subOption === 'auto') {
            const response = await fetch('https://clyq2htkani2c6bivunbb5pjdy0wakhm.lambda-url.us-east-1.on.aws/', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({})
            });
            if (!response.ok) throw new Error(`API Error: ${response.status}`);
            result = formatOption22Result(await response.json());
        } else if ((option === 3 || option === 4 || option === 5) && typeof subOption === 'string' && await shareScreener(option + '-' + subOption)) {
            // every share screener: one routine, its lists and workers in screeners.js
            result = await runShareScreener(await shareScreener(option + '-' + subOption), subOption);
        } else if (option === 5 && subOption === '180') {
            console.log('🚀 SSE 180 Stock Screener');
            alert('SSE 180 screener coming soon!');
            document.getElementById('loading').style.display = 'none';
            jobRunning = false;
            window.analysisInProgress = false; if (window.activeAnalysisButton) window.activeAnalysisButton.classList.remove("active");
            return;
        } else if (option === 5 && subOption === 'csi300') {
            console.log('🚀 CSI 300 Stock Screener');
            alert('CSI 300 screener coming soon!');
            document.getElementById('loading').style.display = 'none';
            jobRunning = false;
            window.analysisInProgress = false; if (window.activeAnalysisButton) window.activeAnalysisButton.classList.remove("active");
            return;
        } else if (option === 7 && (subOption === 'coinspot' || subOption === '1' || subOption === 1)) {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 CRYPTO ORCHESTRATOR - Analyzing ALL coins with proper ranking');
            console.log('📊 System: CoinSpot Australia (AUD) - 55 Workers × 10 coins each = 550 total');
            console.log('🧠 Dynamic allocation: 548 base coins → 55 workers × 10 coins each');
            console.log('📊 Processing 548 coins (55 workers × 10 coins each)');
            console.log('🧠 PREDICTION MEMORY: 🟢=PREDICTIVE (identified before move) 🔴=REACTIVE (after move) 🟡=RECENT (first run)');
            
            // Use the new orchestrator function
            const orchestratorUrl = 'https://5fyemil3eipbwqyyb2kloijyhi0uvtct.lambda-url.us-east-1.on.aws/';
            
            const startTime = Date.now();
            console.log('📊 Calling orchestrator to aggregate all 55 workers...');
            
            // Show worker progress in batches
            console.log('🔄 Starting Workers 1-10 (100 coins)...');
            console.log('🔄 Starting Workers 11-20 (100 coins)...');
            console.log('🔄 Starting Workers 21-30 (100 coins)...');
            console.log('🔄 Starting Workers 31-40 (100 coins)...');
            console.log('🔄 Starting Workers 41-50 (100 coins)...');
            console.log('🔄 Starting Workers 51-55 (48 coins)...');
            
            // Get settings from slider
            const threshold = window.currentThreshold || 0.25;
            
            // Start countdown
            startCountdown(15);
            
            const response = await fetch(orchestratorUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    timestamp: new Date().toISOString(),
                    threshold: threshold
                })
            });
            
            if (!response.ok) throw new Error(`Orchestrator failed: ${response.status}`);
            const orchestratorResult = await response.json();
            
            // Show worker completion in batches
            console.log('✅ Workers 1-10 completed: 100 coins');
            console.log('✅ Workers 11-20 completed: 100 coins');
            console.log('✅ Workers 21-30 completed: 100 coins');
            console.log('✅ Workers 31-40 completed: 100 coins');
            console.log('✅ Workers 41-50 completed: 100 coins');
            console.log('✅ Workers 51-55 completed: 48 coins');
            
            const totalTime = (Date.now() - startTime) / 1000;
            console.log(`⚡ All ${orchestratorResult.successful_workers} workers completed in ${totalTime.toFixed(1)}s`);
            console.log(`📊 CoinSpot Analysis: ${orchestratorResult.total_coins}/548 coins (${((orchestratorResult.total_coins/548)*100).toFixed(1)}%)`);
            console.log(`📊 Final result: ${orchestratorResult.total_coins} coins analyzed from ${orchestratorResult.successful_workers} workers`);
            console.log('📊 Orchestrator aggregation complete - generating comprehensive report...');
            console.log('✅ Comprehensive report generated!');
            console.log(`📊 Total coins in final ranking: ${orchestratorResult.total_coins}`);
            
            result = { type: 'coinspot_comprehensive', data: orchestratorResult.report };
            
            // Store raw results for refiltering
            window.cryptoRawResults = orchestratorResult.coins;
            
            // Generate CSV export and store data
            const csvData = generateCryptoCSVExport(orchestratorResult.coins, 'Crypto_Universe');
            result.csvData = csvData;
        } else if (option === 72 && subOption === 'single') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🔍 SINGLE COIN ANALYSIS');
            const coinSymbol = document.getElementById('coin-symbol-input').value.trim().toUpperCase();
            if (!coinSymbol) throw new Error('Please enter a cryptocurrency symbol');
            
            // The single-stock report function reports on a coin too (since 12 Oct 2026): it is sent the coin's symbol and
            // prices it by the ticker the crypto screener uses for it (SUI is SUI20947-USD). Until then this button had a
            // function of its own, with its own scoring and its own RSI.
            console.log(`🔍 Analyzing ${coinSymbol} with the report function`);
            const coinPayload = { symbols: [coinSymbol], asset: 'crypto', timezone_offset: -new Date().getTimezoneOffset() / 60, skipHistorySave: true };
            if (userId) coinPayload.userId = userId;
            const response = await fetch('https://5oqosafg2mflk7oyydkk3d3rdq0amufq.lambda-url.us-east-1.on.aws/', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(coinPayload)
            });
            // 404 is the function's answer for a symbol the price source does not know: shown as such, not as a failure
            if (!response.ok && response.status !== 404) throw new Error(`API Error: ${response.status}`);
            const singleCoinResult = await response.json().catch(() => ({}));
            
            result = formatSingleCoinResult(singleCoinResult, coinSymbol);
        } else {
            result = await simulateAnalysis(requestData);
        }
        
        displayResults(result);
        
        // Save analysis to dashboard history for all options (non-blocking)
        console.log('🔍 Checking if should save to history - option:', option, 'subOption:', subOption, 'result.type:', result.type);
        console.log('✅ Calling saveAnalysisToHistory for option', option);
        saveAnalysisToHistory(result, subOption, option); // Fire and forget - don't wait
        

        
    } catch (error) {
        displayError(error.message);
    } finally {
        document.getElementById('loading').style.display = 'none';
        clearCountdown();
        jobRunning = false;
        window.analysisInProgress = false;
        window.analysisActivelyRunning = false; // Reset the flag
        if (window.activeAnalysisButton) window.activeAnalysisButton.classList.remove("active");
        
        // Show upgrade modal/button for users who need to upgrade
        setTimeout(async () => {
            const userId = localStorage.getItem('userId');
            if (!userId || userId === 'anonymous') {
                showAnonymousUpgradeModal();
            } else if (typeof authManager !== 'undefined') {
                // Check if registered free user has 0 remaining
                const status = await authManager.getStockAnalysisStatus();
                if (status && !status.unlocked) {
                    showStickyUpgradeButton();
                }
            }
        }, 1500);
    }
}

async function generateChart(symbol) {
    try {
        const response = await fetch('https://6beqon56uidrwxtl52oycyn6kq0lyezp.lambda-url.us-east-1.on.aws/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol })
        });
        
        if (!response.ok) return null;
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('image/svg+xml')) {
            const svgText = await response.text();
            return 'data:image/svg+xml;base64,' + btoa(svgText);
        } else {
            const result = await response.json();
            return result.success ? result.chart_url : null;
        }
    } catch (error) {
        return null;
    }
}

async function formatOption11Result(apiData) {
    const results = apiData.results;
    const userId = localStorage.getItem('userId');
    
    // Check if comprehensive_analysis already has a header (for anonymous users)
    const hasComprehensiveAnalysis = results.length > 0 && results[0].comprehensive_analysis;
    
    let output = '';
    
    // Only add frontend header if comprehensive_analysis doesn't have one
    if (!hasComprehensiveAnalysis) {
        output = `
============================================================
📝 CUSTOM STOCK ANALYSIS RESULTS (REAL-TIME DATA)
============================================================

Analysis Type: Custom Symbols
Symbols Analyzed: ${apiData.symbols_analyzed}
Analysis Date: ${apiData.timestamp}

`;
    }

    // Several reports in one run (Magnificent 7, Popular ETFs, several typed symbols): a short comparison first.
    // The price is taken as the report itself writes it (it knows the share's currency; the result carries no currency field).
    if (results.length > 1) {
        const rows = results.map(stock => {
            const written = String(stock.comprehensive_analysis || '').match(/Current Price: (.+?) \(/);
            const price = written ? written[1] : (typeof stock.current_price === 'number' ? `$${stock.current_price.toFixed(2)}` : 'N/A');
            const day = typeof stock.daily_change_pct === 'number' ? `${stock.daily_change_pct >= 0 ? '+' : ''}${stock.daily_change_pct.toFixed(2)}%` : 'N/A';
            const score = typeof stock.investment_score === 'number' ? `${Math.round(stock.investment_score)}/100` : 'N/A';
            return [reportText(stock.symbol || 'N/A'), price, day, score, reportText(stock.clear_recommendation || signalLabel(stock.recommendation))];
        });
        const head = ['Symbol', 'Price', 'Today', 'Score', 'Signal'];
        const width = head.map((h, c) => Math.max(h.length, ...rows.map(r => r[c].length)));
        const line = (r) => r.map((cell, c) => c === 0 || c === 4 ? cell.padEnd(width[c]) : cell.padStart(width[c])).join('   ').trimEnd();
        output += `============================================================\n📋 SIDE BY SIDE: ${results.length} SYMBOLS IN THIS RUN\n============================================================\n\n`;
        output += line(head) + '\n' + rows.map(line).join('\n') + '\n\n';
        output += `ℹ️ The score is each report's own 0-100 score; the full reports follow. General information only, not financial advice.\n\n`;
    }

    results.forEach((stock, i) => {
        if (stock.comprehensive_analysis) {
            output += stock.comprehensive_analysis + "\n";
        } else {
            output += `${i + 1}. ${stock.symbol}
`;
            output += `   Current Price: $${stock.current_price.toFixed(2)}
`;
            output += `   Daily Change: $${stock.daily_change.toFixed(2)} (${stock.daily_change_pct.toFixed(2)}%)
`;
            output += `   Signal: ${signalLabel(stock.recommendation)}
`;
            output += `   Technical Score: ${stock.technical_score}/10
`;
            output += `   Fundamental Score: ${stock.fundamental_score}/10

`;
        }
    });
    
    // Charts are generated by Lambda and embedded in comprehensive_analysis text

    if (!hasComprehensiveAnalysis) {
        output += `

✅ Real-time analysis complete!

💡 PROFESSIONAL ANALYSIS FEATURES:
• Multi-section detailed reports
• Real-time technical indicators
• Support and resistance levels
• Volume analysis and momentum indicators
• Professional scoring system
• Performance metrics and volatility assessment
    `;
    }

    return {
        type: 'option_11_analysis',
        data: output
    };
}

async function simulateAnalysis(requestData) {
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    return {
        type: 'mock_analysis',
        data: `
============================================================
📊 ANALYSIS RESULTS
============================================================

Option: ${requestData.option}
Sub-option: ${requestData.subOption}
Analysis Date: ${new Date().toLocaleString()}

✅ Mock analysis complete!

⚠️ This is a demo version. Real analysis requires API configuration.
        `
    };
}

function displayResults(result) {
    const resultsContent = document.getElementById('results-content');
    resultsContent.innerHTML = result.data;
    
    // Inject user's local timestamp for crypto results
    if (result.type === 'coinspot_comprehensive') {
        const timestampEl = document.getElementById('analysis-timestamp');
        if (timestampEl) {
            const now = new Date();
            const formatted = now.toLocaleString('en-AU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
            timestampEl.textContent = formatted;
        }
    }
    
    // Add filter buttons for crypto results
    if (result.type === 'coinspot_comprehensive' && window.cryptoRawResults) {
        setTimeout(() => addCryptoFilterButtons(), 100);
        
        // Add dashboard message for crypto (remove existing first)
        const existingMsg = document.getElementById('crypto-dashboard-msg');
        if (existingMsg) existingMsg.remove();
        
        const dashboardMsg = document.createElement('div');
        dashboardMsg.id = 'crypto-dashboard-msg';
        dashboardMsg.style.cssText = 'margin: 20px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;';
        dashboardMsg.innerHTML = '📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html#reports" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.';
        resultsContent.appendChild(dashboardMsg);
    }
    
    // Keep only the option parameter, remove others to prevent re-running on refresh
    const url = new URL(window.location);
    const option = url.searchParams.get('option');
    url.search = '';
    if (option) {
        url.searchParams.set('option', option);
    }
    window.history.replaceState({}, '', url);
}

function displayError(message) {
    const resultsContent = document.getElementById('results-content');
    resultsContent.innerHTML = `❌ ERROR: ${message}

Please try again or contact support if the issue persists.`;
}

async function saveAnalysisToHistory(result, subOption, option) {
    const userId = localStorage.getItem('userId') || 'anonymous';
    console.log('🔍 saveAnalysisToHistory called - userId:', userId, 'option:', option);
    console.log('🔍 authManager exists:', typeof authManager !== 'undefined');
    console.log('🔍 isAuthenticated:', typeof authManager !== 'undefined' ? authManager.isAuthenticated() : 'N/A');
    
    // Skip saving for anonymous users since they can't access dashboard anyway
    if (!userId || userId === 'anonymous') {
        console.log('❌ Skipping history save - anonymous user');
        return;
    }
    
    // Only save for authenticated users
    if (typeof authManager === 'undefined' || !authManager.isAuthenticated()) {
        console.log('❌ Skipping history save - not authenticated');
        return;
    }
    
    try {
        let symbols = [];
        let uniqueSymbolsCount = 0;
        
        if (option === 1) {
            if (subOption === 'custom') {
                const symbolsInput = document.getElementById('symbols-input').value;
                symbols = symbolsInput.split(',').map(s => s.trim().toUpperCase());
                uniqueSymbolsCount = symbols.length;
            } else if (subOption === 'mag7') {
                symbols = ['AAPL','MSFT','GOOGL','AMZN','NVDA','TSLA','META'];
                uniqueSymbolsCount = 7;
            } else if (subOption === 'dow30') {
                symbols = ['AAPL','MSFT','UNH','GS','HD'];
                uniqueSymbolsCount = 5;
            } else if (subOption === 'sp500') {
                symbols = ['AAPL','MSFT','GOOGL','AMZN','NVDA'];
                uniqueSymbolsCount = 5;
            } else if (subOption === 'etf') {
                symbols = ['SPY','QQQ','VTI','IWM'];
                uniqueSymbolsCount = 4;
            }
        } else if (option === 2) {
            if (subOption === 'custom') {
                const symbolsInput = document.getElementById('signals-symbols').value;
                symbols = symbolsInput.split(',').map(s => s.trim().toUpperCase());
                uniqueSymbolsCount = symbols.length;
            } else if (subOption === 'auto') {
                // For auto signals, use a single combined symbol identifier
                symbols = ['AUTO_SIGNALS'];
                uniqueSymbolsCount = 5; // Auto-detect returns 5 signals
            }
        } else if (option === 3) {
            symbols = ['US_SCREENER'];
            // Set unique symbols count based on sub-option
            if (subOption === '100') {
                uniqueSymbolsCount = 100;
            } else if (subOption === '2') {
                uniqueSymbolsCount = 1000;
            } else if (subOption === '3') {
                uniqueSymbolsCount = 500;
            } else if (subOption === '4') {
                uniqueSymbolsCount = 1500;
            } else if (subOption === '5') {
                uniqueSymbolsCount = 1000;
            } else if (subOption === '6') {
                uniqueSymbolsCount = 2000;
            } else if (subOption === '7') {
                uniqueSymbolsCount = 100;
            } else if (subOption === '8') {
                uniqueSymbolsCount = 30;
            }
        } else if (option === 4) {
            if (subOption === 'ftse100') {
                symbols = ['UK_FTSE_100'];
                uniqueSymbolsCount = 100;
            } else {
                symbols = ['OTHER_MARKETS'];
                uniqueSymbolsCount = 100;
            }
        } else if (option === 5) {
            if (subOption === '50') {
                symbols = ['ASX_SCREENER'];
                uniqueSymbolsCount = 50;
            } else if (subOption === '100') {
                symbols = ['ASX_SCREENER'];
                uniqueSymbolsCount = 100;
            } else if (subOption === '200') {
                symbols = ['ASX_SCREENER'];
                uniqueSymbolsCount = 200;
            } else if (subOption === '300') {
                symbols = ['ASX_SCREENER'];
                uniqueSymbolsCount = 300;
            } else if (subOption === 'nikkei225') {
                symbols = ['JAPAN_SCREENER'];
                uniqueSymbolsCount = 210;
            } else if (marketReport(5, subOption)) {
                symbols = [marketReport(5, subOption).symbol];
                uniqueSymbolsCount = SHARE_SCREENERS['5-' + subOption].list.length;
            } else {
                symbols = ['ASIA_MARKETS'];
                uniqueSymbolsCount = 100;
            }
        } else if (option === 6) {
            symbols = ['CRYPTO_ANALYSIS'];
            uniqueSymbolsCount = 50; // Top crypto coins
        } else if (option === 7) {
            symbols = ['COINSPOT_SCREENER'];
            uniqueSymbolsCount = 548; // All CoinSpot coins
        } else if (option === 72) {
            // For single coin analysis, use the actual coin symbol
            const coinInput = document.getElementById('coin-symbol-input');
            const coinSymbol = coinInput ? coinInput.value.trim().toUpperCase() : 'CRYPTO';
            symbols = [coinSymbol];
            uniqueSymbolsCount = 1;
        } else if (option === 8) {
            symbols = ['BATCH_MODE'];
            uniqueSymbolsCount = 2098; // Turbo (1550) + Crypto (50) + CoinSpot (548)
        } else {
            symbols = [`OPTION_${option}`];
            uniqueSymbolsCount = 1;
        }
        
        // Get the descriptive name for display
        let companyName = '';
        if (option === 1) {
            if (subOption === 'custom') {
                companyName = `Analysis ${symbols.join(', ')}`; // For custom stocks, show "Analysis MSFT, GOOGL"
            } else {
                companyName = symbols.join(', '); // For presets, show just the symbols
            }
        } else if (option === 2) {
            if (subOption === 'custom') {
                companyName = `Signal ${symbols.join(',')}`; // For custom signals, show "Signal MSFT,GOOGL"
            } else {
                companyName = 'Top 5 Trading Signals'; // For auto signals
            }
        } else if (option === 3) {
            const subNames = {
                '100': 'S&P 100 (LargeCap)',
                '2': 'S&P 400+600 (Mid+SmallCap)',
                '3': 'S&P 500 Complete Screener', 
                '4': 'S&P Composite 1500',
                '5': 'Russell 1000 Large-Cap Screener',
                '6': 'Russell 2000 Small-Cap Screener',
                '7': 'NASDAQ 100 Tech Screener',
                '8': 'Dow Jones 30 Blue Chip Screener'
            };
            companyName = subNames[subOption] || 'US Stock Screener';
        } else if (option === 4) {
            if (subOption === 'ftse100') {
                companyName = 'UK FTSE 100 Screener';
            } else {
                companyName = 'Europe Stock Screener';
            }
        } else if (option === 5) {
            const subNames = {
                '50': 'ASX 50 Screener',
                '100': 'ASX 100 Screener',
                '200': 'ASX 200 Screener',
                '300': 'ASX 300 Screener',
                'nikkei225': 'Japan Nikkei 225 Screener'
            };
            companyName = subNames[subOption] || (marketReport(5, subOption) || {}).title || 'ASX Stock Screener';
        } else if (option === 6) {
            if (false) {
                companyName = 'Other Markets Screener';
            }
        } else if (option === 6) {
            companyName = 'Crypto Market Overview';
        } else if (option === 7) {
            companyName = 'Crypto Universe Screener';
        } else if (option === 72) {
            // For single coin, show the coin symbol in the name
            const coinInput = document.getElementById('coin-symbol-input');
            const coinSymbol = coinInput ? coinInput.value.trim().toUpperCase() : 'Crypto';
            companyName = `${coinSymbol} Coin Analysis`;
        } else if (option === 8) {
            companyName = 'Batch Mode - All Reports';
        } else {
            companyName = `Analysis Option ${option}`;
        }
        
        // Save analysis - for custom symbols (option 1 & 2) and auto signals (option 2 auto), save as single combined analysis
        console.log('💾 Saving analysis for symbols:', symbols, 'uniqueSymbolsCount:', uniqueSymbolsCount);
        
        if (((option === 1 || option === 2) && subOption === 'custom' && symbols.length > 1) || (option === 2 && subOption === 'auto')) {
            // For multiple custom symbols, save as one combined analysis
            const combinedSymbol = symbols.join(',');
            console.log('💾 Saving combined analysis for:', combinedSymbol, 'option:', option);
            
            const saveData = {
                action: 'save_analysis',
                userId: userId,
                symbol: combinedSymbol,
                companyName: companyName,
                report: result.data,
                uniqueSymbolsAnalyzed: uniqueSymbolsCount
            };
            
            // Include CSV data if available
            if (result.csvData) {
                saveData.csvData = result.csvData;
                console.log('📊 Including CSV data for combined analysis - Size:', result.csvData.length, 'characters');
            }
            
            const response = await fetch('https://nwdjnlcbtj34ywy6sgawmwhcx40ologt.lambda-url.us-east-1.on.aws/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(saveData)
            });
            
            if (response.ok) {
                const saveResult = await response.json();
                console.log('✅ Saved combined analysis - Response:', saveResult);
                
                // Mark as unread for notification system and clear cache
                if (saveResult.analysisId) {
                    const userId = localStorage.getItem('userId');
                    let unreadReports = JSON.parse(localStorage.getItem(`unreadReports_${userId}`) || '[]');
                    if (!unreadReports.includes(saveResult.analysisId)) {
                        unreadReports.push(saveResult.analysisId);
                        localStorage.setItem(`unreadReports_${userId}`, JSON.stringify(unreadReports));
                    }
                    
                    // Remove from seenReports so it shows as unseen
                    let seenReports = JSON.parse(localStorage.getItem(`seenReports_${userId}`) || '[]');
                    seenReports = seenReports.filter(id => id !== saveResult.analysisId);
                    localStorage.setItem(`seenReports_${userId}`, JSON.stringify(seenReports));
                    
                    console.log('🔔 Marked analysis as unread:', saveResult.analysisId);
                    
                    // Invalidate caches so fresh data is fetched
                    localStorage.setItem('dashboardCacheInvalidated', 'true');
                    localStorage.removeItem(`notificationCache_${userId}`);
                    localStorage.removeItem(`notificationCacheTimestamp_${userId}`);
                    localStorage.removeItem(`dashboardHistoryCache_${userId}`);
                    localStorage.removeItem(`dashboardCache_${userId}`);
                    localStorage.removeItem(`dashboardCacheTimestamp_${userId}`);
                    
                    // Store pending notification for when dropdown opens
                    localStorage.setItem('pendingNotification', JSON.stringify({
                        name: companyName || combinedSymbol,
                        time: Date.now()
                    }));
                    
                    // Update bell immediately and after a short delay to ensure DOM is ready
                    updateNotificationBell();
                    setTimeout(() => updateNotificationBell(), 100);
                    
                    // Add temporary item to analysisHistory immediately
                    if (typeof analysisHistory === 'undefined') {
                        window.analysisHistory = [];
                    }
                    const tempItem = {
                        analysisId: saveResult.analysisId,
                        symbol: combinedSymbol,
                        companyName: companyName || 'Analysis',
                        timestamp: new Date().toISOString(),
                        loading: true
                    };
                    window.analysisHistory.unshift(tempItem);
                    
                    // If dropdown is open, add loading notification immediately after header
                    const dropdown = document.getElementById('notification-dropdown');
                    if (dropdown) {
                        const loadingHtml = `<div style="padding: 12px 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); opacity: 0.7; border-left: 3px solid #007bff;"><div style="display: flex; align-items: center; gap: 10px;"><div style="width: 8px; height: 8px; background: #007bff; border-radius: 50%;"></div><div style="flex: 1;"><div style="font-weight: 600; color: var(--text-primary); font-size: 13px;">${companyName || combinedSymbol} (Loading...)</div><div style="color: var(--text-secondary); font-size: 11px;">Just now</div></div></div></div>`;
                        // Insert after the header (first child)
                        const header = dropdown.firstElementChild;
                        if (header) {
                            header.insertAdjacentHTML('afterend', loadingHtml);
                        } else {
                            dropdown.insertAdjacentHTML('afterbegin', loadingHtml);
                        }
                    }
                    
                    preloadNotifications();
                }
            } else {
                console.log('❌ Failed to save combined analysis - Status:', response.status);
            }
        } else {
            // For single symbols, other options, or non-custom suboptions, save each symbol individually
            for (const symbol of symbols) {
                console.log('💾 Saving symbol:', symbol, 'with name:', companyName);
                
                const saveData = {
                    action: 'save_analysis',
                    userId: userId,
                    symbol: symbol,
                    companyName: companyName,
                    report: result.data,
                    uniqueSymbolsAnalyzed: uniqueSymbolsCount
                };
                
                // Include CSV data if available
                if (result.csvData) {
                    saveData.csvData = result.csvData;
                    console.log('📊 Including CSV data for', symbol, '- Size:', result.csvData.length, 'characters');
                } else {
                    console.log('❌ No CSV data available for', symbol);
                }
                
                const response = await fetch('https://nwdjnlcbtj34ywy6sgawmwhcx40ologt.lambda-url.us-east-1.on.aws/', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(saveData)
                });
                
                if (response.ok) {
                    const saveResult = await response.json();
                    console.log('✅ Saved', symbol, '- Response:', saveResult);
                    
                    // Mark as unread for notification system and clear cache (only once for multiple symbols)
                    if (saveResult.analysisId) {
                        const userId = localStorage.getItem('userId');
                        let unreadReports = JSON.parse(localStorage.getItem(`unreadReports_${userId}`) || '[]');
                        if (!unreadReports.includes(saveResult.analysisId)) {
                            unreadReports.push(saveResult.analysisId);
                            localStorage.setItem(`unreadReports_${userId}`, JSON.stringify(unreadReports));
                        }
                        
                        // Remove from seenReports so it shows as unseen
                        let seenReports = JSON.parse(localStorage.getItem(`seenReports_${userId}`) || '[]');
                        seenReports = seenReports.filter(id => id !== saveResult.analysisId);
                        localStorage.setItem(`seenReports_${userId}`, JSON.stringify(seenReports));
                        
                        console.log('🔔 Marked analysis as unread:', saveResult.analysisId);
                        
                        // Only invalidate caches and update notifications once (for the first symbol)
                        if (symbol === symbols[0]) {
                            localStorage.setItem('dashboardCacheInvalidated', 'true');
                            localStorage.removeItem(`notificationCache_${userId}`);
                            localStorage.removeItem(`notificationCacheTimestamp_${userId}`);
                            localStorage.removeItem(`dashboardHistoryCache_${userId}`);
                            localStorage.removeItem(`dashboardCache_${userId}`);
                            localStorage.removeItem(`dashboardCacheTimestamp_${userId}`);
                            
                            // Store pending notification for when dropdown opens
                            localStorage.setItem('pendingNotification', JSON.stringify({
                                name: companyName || symbol,
                                time: Date.now()
                            }));
                            
                            // Update bell immediately and after a short delay to ensure DOM is ready
                            updateNotificationBell();
                            setTimeout(() => updateNotificationBell(), 100);
                            
                            // If dropdown is open, add loading notification immediately after header
                            const dropdown = document.getElementById('notification-dropdown');
                            if (dropdown) {
                                const loadingHtml = `<div style="padding: 12px 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); opacity: 0.7; border-left: 3px solid #007bff;"><div style="display: flex; align-items: center; gap: 10px;"><div style="width: 8px; height: 8px; background: #007bff; border-radius: 50%;"></div><div style="flex: 1;"><div style="font-weight: 600; color: var(--text-primary); font-size: 13px;">${companyName || symbol} (Loading...)</div><div style="color: var(--text-secondary); font-size: 11px;">Just now</div></div></div></div>`;
                                // Insert after the header (first child)
                                const header = dropdown.firstElementChild;
                                if (header) {
                                    header.insertAdjacentHTML('afterend', loadingHtml);
                                } else {
                                    dropdown.insertAdjacentHTML('afterbegin', loadingHtml);
                                }
                            }
                            
                            setTimeout(() => preloadNotifications(), 100);
                        }
                    }
                } else {
                    console.log('❌ Failed to save', symbol, '- Status:', response.status);
                }
            }
        }
        
        console.log('📊 Analysis saved to dashboard history');
    } catch (error) {
        console.warn('Failed to save analysis to history:', error);
    }
}

// Display wording for model output codes. StockIQ gives general information, not advice,
// so codes such as BUY / SELL are used internally but never shown: they are mapped to
// neutral signal labels (the same ones the public stock pages use).
function signalLabel(code) {
    const labels = {
        'STRONG BUY': 'Strongly positive', 'BUY': 'Positive', 'MODERATE BUY': 'Slightly positive', 'CONSIDER': 'Slightly positive',
        'HOLD': 'Mixed', 'NEUTRAL': 'Mixed',
        'MODERATE SELL': 'Slightly negative', 'AVOID': 'Slightly negative', 'SELL': 'Negative', 'STRONG SELL': 'Strongly negative'
    };
    // Stock workers use underscores (STRONG_BUY, MODERATE_BUY ...), crypto workers use spaces
    const key = String(code || 'HOLD').replace(/_/g, ' ').trim().toUpperCase();
    // An unknown code is shown as "Unrated" rather than guessed
    return labels[key] || 'Unrated';
}

// The model's holding-period codes describe a time horizon; show them as that, not as instructions.
function horizonLabel(code) {
    const labels = {
        'IMMEDIATE': 'Very short term', 'SHORT_TERM': 'Short term', 'SHORT-TERM': 'Short term',
        'MEDIUM_TERM': 'Medium term', 'MEDIUM-TERM': 'Medium term', 'LONG_TERM': 'Long term', 'LONG-TERM': 'Long term',
        'DAY TRADE': 'Intraday', 'HOLD': 'n/a', 'AVOID': 'n/a'
    };
    const raw = String(code || '').trim();
    if (!raw || raw === 'N/A') return 'n/a';
    return labels[raw.toUpperCase()] || raw;
}

// One reading of the trading signals (options 2.1 and 2.2) as text. Its first line stays "N. SYMBOL - name - price": the
// dashboard's tracker reads the symbol and the price from it (parseScreenerTop10 in dashboard.html), which is why the
// name is cut to 30 characters and set off with " - ". Prices go through screenerMoney, from the reading's own currency.
// Text from outside (a company's name, a typed symbol, the function's own sentences) goes into a report that the page shows
// as HTML: "AT&T" must be written "AT&amp;T". (Unescaped, the dashboard's tracker also lost the line: it clears
// everything from an "&" to the next ";".)
function reportText(value) { return String(value == null ? '' : value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

function signalBlock(signal, i) {
    const money = (value) => screenerMoney(signal, value, 'USD');
    const signed = (value, places) => `${value >= 0 ? '+' : ''}${(Number(value) || 0).toFixed(places)}`;
    const price = Number(signal.current_price) || 0;
    const name = String(signal.name || '').replace(/\s+/g, ' ').trim().slice(0, 30).trim();
    const change = typeof signal.change_pct === 'number' ? ` (${signed(signal.change_pct, 2)}% today)` : '';
    const emoji = signal.action === 'BUY' ? '🟢' : signal.action === 'SELL' ? '🔴' : '⚪';
    const strength = typeof signal.signal_strength === 'number' ? `${signed(signal.signal_strength, 0)} on the scale, ` : '';
    let out = `${i + 1}. ${reportText(signal.symbol)} - ${name ? reportText(name) + ' - ' : ''}${money(price)}${change}\n`;
    out += `   ${emoji} ${signalLabel(signal.action)} signal (${strength}${reportText(signal.confidence)} confidence)\n`;
    (Array.isArray(signal.reasons) ? signal.reasons : []).forEach(reason => { out += `      • ${reportText(reason)}\n`; });
    if (signal.trend) out += `   📈 Trend: ${reportText(signal.trend)}\n`;
    // The two levels are facts, not aims: the highest and the lowest price of the last 20 sessions
    const levels = [signal.take_profit, signal.stop_loss].map(Number).filter(isFinite);
    const high = isFinite(Number(signal.resistance)) && signal.resistance != null ? Number(signal.resistance) : Math.max(...levels);
    const low = isFinite(Number(signal.support)) && signal.support != null ? Number(signal.support) : Math.min(...levels);
    const away = (level) => price ? ` (${signed((level - price) / price * 100, 1)}% from the price)` : '';
    if (isFinite(high)) out += `   📏 20-day high: ${money(high)}${away(high)}\n`;
    if (isFinite(low)) out += `   📏 20-day low: ${money(low)}${away(low)}\n`;
    return out + '\n';
}

function formatOption2Result(apiData) {
    const signals = apiData.signals || [];
    const notFound = Array.isArray(apiData.not_found) ? apiData.not_found : [];
    let output = `
============================================================
⚡ TRADING SIGNALS GENERATOR RESULTS (REAL-TIME DATA)
============================================================

Signals Generated: ${apiData.symbols_analyzed}
Analysis Date: ${new Date(apiData.timestamp).toLocaleString()}
${apiData.scale ? `How to read it: ${reportText(apiData.scale)}\n` : ''}${apiData.levels ? `Levels shown: ${reportText(apiData.levels)}\n` : ''}
🎯 TRADING SIGNALS:
ℹ️ General information only. Signals and levels are calculated automatically and are not recommendations to buy or sell.

`;
    signals.forEach((signal, i) => { output += signalBlock(signal, i); });
    if (notFound.length > 0) {
        output += `⚠️ No prices were found for: ${notFound.map(reportText).join(', ')}\n   Check the spelling. A share outside the US needs its exchange's ending (for example BHP.AX, IMB.L, 7203.T).\n`;
    }
    return { type: 'option_21_custom_signals', data: output };
}

function formatOption22Result(apiData) {
    const signals = apiData.signals || [];
    const readings = apiData.readings || null;
    const strongest = Array.isArray(apiData.top_performers) ? apiData.top_performers : signals.map(s => s.symbol);
    let output = `
============================================================
⚡ AUTO-DETECT TRADING SIGNALS RESULTS (REAL-TIME DATA)
============================================================

Methodology: ${reportText(apiData.methodology)}
${apiData.scanned != null ? `Scanned: ${apiData.scanned}${apiData.universe_size != null ? ` of ${apiData.universe_size}` : ''}${apiData.universe ? ` ${reportText(apiData.universe)} shares` : ' shares'}\n` : ''}${readings ? `Readings across the list: ${readings.positive} positive, ${readings.negative} negative, ${readings.mixed} mixed\n` : ''}Strongest readings: ${strongest.map(reportText).join(', ')}
Signals Generated: ${apiData.symbols_analyzed}
${apiData.timestamp ? `Analysis Date: ${new Date(apiData.timestamp).toLocaleString()}\n` : ''}${apiData.scale ? `How to read it: ${reportText(apiData.scale)}\n` : ''}${apiData.levels ? `Levels shown: ${reportText(apiData.levels)}\n` : ''}
🎯 THE STRONGEST READINGS, IN EITHER DIRECTION:
ℹ️ General information only. Signals and levels are calculated automatically and are not recommendations to buy or sell.

`;
    signals.forEach((signal, i) => { output += signalBlock(signal, i); });
    return { type: 'option_22_auto_signals', data: output };
}

// A price in the currency the share trades in, as the workers report it (stock.currency: 'USD', 'AUD', 'JPY', 'GBp' = pence;
// fallback: the currency of the screener's market, for a result without the field). The same rule as the single-stock report
// (money() in stockiq-option-1-1-custom-analysis) and the coordinator's money(): keep the three alike. The dashboard's 🎯
// tracker reads the price from these lines (a leading sign, or a number followed by "p"): parseScreenerTop10 in dashboard.html.
const SCREENER_MONEY_SIGNS = { USD: '$', AUD: 'A$', CAD: 'C$', NZD: 'NZ$', HKD: 'HK$', SGD: 'S$', GBP: '£', EUR: '€', JPY: '¥', CNY: 'CN¥', INR: '₹', KRW: '₩' };
const SCREENER_MINOR_UNITS = { GBp: 'p', GBX: 'p', ZAc: 'c', ZAC: 'c', ILA: ' agorot' };
// What a CSV row's prices are in: the currency code as the workers report it, with pence spelled out. The coordinator's
// currency_name() writes the same.
function screenerCurrencyName(stock) {
    const cur = (stock && stock.currency) || '';
    return cur === 'GBp' || cur === 'GBX' ? `${cur} (pence)` : cur;
}
function screenerMoney(stock, value, fallback) {
    const cur = (stock && stock.currency) || fallback || 'USD';
    const number = (Number(value) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (SCREENER_MINOR_UNITS[cur]) return number + SCREENER_MINOR_UNITS[cur];
    return SCREENER_MONEY_SIGNS[cur] !== undefined ? SCREENER_MONEY_SIGNS[cur] + number : cur + ' ' + number;
}

function formatOption3Result(apiData, subOption) {
    const titles = { '100': 'S&P 100 (LARGECAP)', '2': 'S&P 400+600 (MID+SMALLCAP)', '3': 'S&P 500 COMPLETE', '4': 'S&P COMPOSITE 1500', '5': 'RUSSELL 1000 LARGE-CAP', '6': 'RUSSELL 2000 SMALL-CAP', '7': 'NASDAQ 100 TECH', '8': 'DOW JONES 30 BLUE CHIP' };
    const universeSize = { '100': 101, '2': 995, '3': 502, '4': 1497, '5': 877, '6': 1829, '7': 101, '8': 30 };  // real list sizes (refreshed 10 Oct 2026)
    
    let output = `
============================================================
🎯 ${titles[subOption]} STOCK SCREENER RESULTS (REAL-TIME DATA)
============================================================

Screening Universe: ${universeSize[subOption]} ${titles[subOption]} stocks
Market Type: ${titles[subOption]} Stocks (Dynamic)
Universe Size: ${universeSize[subOption]}
Analysis Date: ${new Date().toLocaleString()}

`;
    
    if (apiData.results && apiData.results.length > 0) {
        const sortedResults = [...apiData.results].sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
        
        output += '🟢 TOP 10 BY SCORE:\n';
        sortedResults.slice(0, 10).forEach((stock, i) => {
            const symbol = (stock.symbol || 'N/A').padEnd(5);
            const price = `${screenerMoney(stock, stock.current_price || stock.price, 'USD')}`.padStart(8);
            const score = (stock.total_score || stock.score || 0) >= 0 ? `+${(stock.total_score || stock.score || 0).toFixed(1)}` : `${(stock.total_score || stock.score || 0).toFixed(1)}`;
            const rsi = (stock.rsi || 0).toFixed(1).padStart(5);
            const ytd = (stock.ytd_change || 0) >= 0 ? `+${(stock.ytd_change || 0).toFixed(1)}%` : `${(stock.ytd_change || 0).toFixed(1)}%`;
            const vol = `${(stock.volume_ratio || 1).toFixed(1)}x`;
            output += `${(i+1).toString().padStart(2)}. ${symbol} ${price} | Score: ${score} | RSI: ${rsi} | YTD: ${ytd}, Vol: ${vol}\n`;
        });
        
        output += '</table><div style="margin: 20px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;">📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html#reports" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.</div><table class="results-table">\n';
        
        if (subOption === '3' || subOption === '2' || subOption === '4' || subOption === '5' || subOption === '6' || subOption === '7' || subOption === '8' || subOption === '100') {
            output += '\n🎯 TOP 3 DETAILED ANALYSIS:\n';
            output += '================================================================\n';
            sortedResults.slice(0, 3).forEach((stock, i) => {
                output += `${i+1}. ${stock.symbol}: ${screenerMoney(stock, stock.price, 'USD')} | ${signalLabel(stock.recommendation)} | Score: ${(stock.total_score || stock.score || 0) >= 0 ? '+' : ''}${(stock.total_score || stock.score || 0).toFixed(1)}\n`;
                
                if (stock.score_breakdown && stock.score_breakdown.length > 0) {
                    output += '   📊 Score Breakdown:\n';
                    stock.score_breakdown.forEach(breakdown => {
                        output += `      ${breakdown}\n`;
                    });
                }
                
                output += `   📈 Technical: RSI ${(stock.rsi || 50).toFixed(1)} | MACD ${stock.macd_signal || 'NEUTRAL'}\n`;
                output += `   💰 Levels: Support ${screenerMoney(stock, stock.support, 'USD')} | Resistance ${screenerMoney(stock, stock.resistance, 'USD')}\n`;
                output += `   📏 Reference levels: Lower ${screenerMoney(stock, stock.stop_loss, 'USD')} | Upper ${screenerMoney(stock, stock.take_profit, 'USD')}\n`;
                output += `   📊 Horizon: ${horizonLabel(stock.strategy_type)} | Confidence: ${(stock.confidence || 0).toFixed(0)}%\n\n`;
            });
        }
        
        const positiveStocks = sortedResults.filter(s => (s.total_score || s.score || 0) > 0).length;
        const negativeStocks = sortedResults.filter(s => (s.total_score || s.score || 0) < 0).length;
        const avgScore = sortedResults.reduce((sum, s) => sum + (s.total_score || s.score || 0), 0) / sortedResults.length;
        
        output += `\n📊 ANALYSIS SUMMARY:\n`;
        output += `• Total stocks analyzed: ${sortedResults.length}\n`;
        output += `• Stocks with positive scores: ${positiveStocks}\n`;
        output += `• Stocks with negative scores: ${negativeStocks}\n`;
        output += `• Average score: ${avgScore.toFixed(1)}\n`;
        output += `• Success rate: ${((sortedResults.length/universeSize[subOption])*100).toFixed(1)}%\n`;
    } else {
        output += 'No results available\n';
    }
    
    output += `\n✅ Real-time ${titles[subOption]} stock screening complete!`;
    
    return { type: `option_3${subOption}_screener`, data: output };
}

// Price-source tickers for coins whose plain symbol belongs to a different coin there (checked 10 Oct 2026).
// Keep in step with COINS in the stockiq-option-7-1-orchestrator Lambda.
const CRYPTO_TICKER_MAP = {"HYPE":"HYPE32196","CC":"CC37263","UNI":"UNI7083","SUI":"SUI20947","BTW":"BTW39158","TAO":"TAO22974","PUMP":"PUMP36507","WLFI":"WLFI33251","MORPHO":"MORPHO34104","PEPE":"PEPE24478","ARB":"ARB11841","VVV":"VVV35509","LIT":"LIT39125","AERO":"AERO29270","ZRO":"ZRO26997","STX":"STX4847","APT":"APT21794","DRV":"DRV35014","KAU":"KAU24382","TRUMP":"TRUMP35336","PENGU":"PENGU34466","GRASS":"GRASS32956","HASH":"HASH19960","FF":"FF38482","UB":"UB38339","SPX":"SPX28081","BP":"BP39686","APEPE":"APEPE27048","GRT":"GRT6719","CARDS":"CARDS38283","MET":"MET38353","USELESS":"USELESS36828","NPC":"NPC27960","XCN":"XCN18679","IMX":"IMX10603","SENT":"SENT38868","BR":"BR36063","ZK":"ZK24091","SUPER":"SUPER8290","JPYC":"JPYC40123","META":"META38146","ATH":"ATH30083","EDGE":"EDGE39720","BC":"BC35067","SKR":"SKR39377","DBR":"DBR31528","OPEN":"OPEN37456","DOG":"DOG30933","MELANIA":"MELANIA35347","AI":"AI40925","WAL":"WAL36119","COW":"COW19269","UAI":"UAI38841","RED":"RED21707","ESP":"ESP39548","OMI":"OMI19075","FT":"FT38544","TAG":"TAG34958","DATA":"DATA35626","GAL":"GAL11877","BABY":"BABY32198","AXL":"AXL17799","BAN":"BAN33881","METAL":"METAL21769","ARC":"ARC34926","IO":"IO29835","BIO":"BIO34812","SNEK":"SNEK25264","PC":"PC36834","EDU":"EDU24613","ID":"ID21846","COAI":"COAI38489","ARX":"ARX39970","ALT":"ALT29073","CX":"CX35735","BRETT":"BRETT29743","DEEP":"DEEP33391","RAVE":"RAVE38967","HOLO":"HOLO38309","MEGA":"MEGA38770","MASK":"MASK8536","ACU":"ACU36492","NIL":"NIL35702","ME":"ME32197","FB":"FB32941","LION":"LION35954","ONG":"ONG3217","SYN":"SYN12147","MEW":"MEW30126","MOODENG":"MOODENG33093","MOCA":"MOCA31526","UP":"UP39665","BFC":"BFC7817","MOOLAH":"MOOLAH36818","GIGGLE":"GIGGLE38470","NEIRO":"NEIRO32521","BULLA":"BULLA36769","AT":"AT38757","BNKR":"BNKR37545","BEAT":"BEAT38837","ZORA":"ZORA35931","ACX":"ACX22620","DIME":"DIME39656","GPT":"GPT36614","TRUTH":"TRUTH38178","XP":"XP36056","SPACE":"SPACE38136","EDEL":"EDEL38966","EDEN":"EDEN38513","TIG":"TIG34102","EV":"EV39394","BUCK":"BUCK31225","ZBT":"ZBT38427","CYS":"CYS39071","BSB":"BSB38889","TAKE":"TAKE38175","HYPER":"HYPER36281","BROCCOLI":"BROCCOLI35749","AIC":"AIC32968","BILL":"BILL39545","BURN":"BURN30460","BANK":"BANK36296","ACE":"ACE28674","SHARE":"SHARE39955","SBC":"SBC26456"};

function formatCoinSpotResult(results, processingTime, workerDetails = []) {
    let output = `
============================================================
₿ CRYPTO SCREENER RESULTS (TOP COINS BY MARKET CAP)
============================================================

Screening Universe: CoinSpot Australia
Coins Analyzed: ${results.length}
Processing Time: ${processingTime.toFixed(2)}s
Analysis Date: ${new Date().toLocaleString()}
📈 Technical Analysis: MACD, RSI, Bollinger Bands, Stochastic, Volume, Momentum

`;
    
    if (results && results.length > 0) {
        const sortedResults = [...results].sort((a, b) => (b.score || 0) - (a.score || 0));
        
        output += '🔥 TOP 10 CRYPTO BY SCORE:\n';
        sortedResults.slice(0, 10).forEach((coin, i) => {
            const symbol = (coin.symbol || 'N/A').padEnd(8);
            const price = coin.price >= 1 ? `$${coin.price.toFixed(2)}` : `$${coin.price.toFixed(6)}`;
            const recommendation = signalLabel(coin.recommendation);
            const score = coin.score >= 0 ? `+${coin.score}` : `${coin.score}`;
            output += `${(i+1).toString().padStart(2)}. ${symbol} ${price.padStart(12)} | ${recommendation.padEnd(17)} | Score: ${score}\n`;
        });
        
        output += '\n';
        
        // Detailed analysis for top 5
        output += '\n🎯 TOP 5 DETAILED ANALYSIS:\n';
        output += '==================================================\n';
        sortedResults.slice(0, 5).forEach((coin, i) => {
            const price = coin.price >= 1 ? `$${coin.price.toFixed(2)}` : `$${coin.price.toFixed(6)}`;
            output += `${i+1}. ${coin.symbol.toUpperCase()}: ${price} | ${signalLabel(coin.recommendation)} | ${horizonLabel(coin.timeframe)} | Score: ${coin.score >= 0 ? '+' : ''}${coin.score}\n`;
            output += '\n';
            
            // Performance section
            output += '📊 Performance:\n';
            output += `   24h: ${coin.change_24h >= 0 ? '+' : ''}${coin.change_24h.toFixed(1)}% | 7d: ${coin.change_7d >= 0 ? '+' : ''}${coin.change_7d.toFixed(1)}% | 30d: ${coin.change_30d >= 0 ? '+' : ''}${coin.change_30d.toFixed(1)}%\n`;
            output += '\n';
            
            // Indicators section
            if (coin.macd_signal || coin.rsi_signal || coin.bb_signal) {
                output += '📈 Indicators:\n';
                if (coin.macd_signal) output += `   MACD: ${coin.macd_signal}\n`;
                if (coin.rsi && coin.rsi_signal) output += `   RSI: ${coin.rsi.toFixed(1)} - ${coin.rsi_signal.split(' - ')[0]}\n`;
                if (coin.bb_signal) output += `   Bollinger Bands: ${coin.bb_signal}\n`;
                if (coin.momentum_signal) output += `   Momentum: ${coin.momentum_signal}\n`;
                output += '\n';
            }
            
            // Confidence section
            if (coin.confidence || coin.profit_probability) {
                output += '🔄 Confidence:\n';
                if (coin.confidence) output += `   Confidence: ${coin.confidence}\n`;
                if (coin.profit_probability) output += `   Model probability estimate: ${coin.profit_probability.toFixed(0)}%\n`;
                output += '\n';
            }
            
            // Confidence factors section (matching 7.2 format)
            if (coin.confidence_factors && coin.confidence_factors.length > 0) {
                output += '🎯 CONFIDENCE FACTORS:\n';
                coin.confidence_factors.forEach(factor => {
                    output += `• ${factor}\n`;
                });
                output += '\n';
            }
            
            // Risk Management section
            if (coin.stop_loss && coin.take_profit) {
                const stopStr = coin.stop_loss >= 1 ? `$${coin.stop_loss.toFixed(2)}` : `$${coin.stop_loss.toFixed(6)}`;
                const tpStr = coin.take_profit >= 1 ? `$${coin.take_profit.toFixed(2)}` : `$${coin.take_profit.toFixed(6)}`;
                output += '📏 Reference levels (calculated automatically, not instructions):\n';
                output += `   Lower reference level: ${stopStr}\n`;
                output += `   Upper reference level: ${tpStr}\n`;
                if (coin.buy_limit) {
                    const buyLimitStr = coin.buy_limit >= 1 ? `$${coin.buy_limit.toFixed(2)}` : `$${coin.buy_limit.toFixed(6)}`;
                    output += `   Pullback level: ${buyLimitStr}\n`;
                }
                if (coin.buy_stop) {
                    const buyStopStr = coin.buy_stop >= 1 ? `$${coin.buy_stop.toFixed(2)}` : `$${coin.buy_stop.toFixed(6)}`;
                    output += `   Breakout level: ${buyStopStr}\n`;
                }
                if (coin.support && coin.resistance) {
                    const supportStr = coin.support >= 1 ? `$${coin.support.toFixed(2)}` : `$${coin.support.toFixed(6)}`;
                    const resistanceStr = coin.resistance >= 1 ? `$${coin.resistance.toFixed(2)}` : `$${coin.resistance.toFixed(6)}`;
                    output += `   Support: ${supportStr}\n`;
                    output += `   Resistance: ${resistanceStr}\n`;
                }
                output += '\n';
            }
            
            // Score breakdown
            if (coin.score_breakdown && coin.score_breakdown.length > 0) {
                output += '📊 Score Breakdown:\n';
                coin.score_breakdown.forEach(breakdown => {
                    if (breakdown.includes(': ')) {
                        const [component, value] = breakdown.split(': ');
                        output += `   ${component}: ${value}\n`;
                    }
                });
                output += `\n🧮 Total Score: ${coin.score >= 0 ? '+' : ''}${coin.score}\n\n`;
                output += '📊 SCORE RANGES:\n';
                output += '   +7 and above: Strongly positive\n';
                output += '   +4 to +6: Positive\n';
                output += '   +2 to +3: Slightly positive\n';
                output += '   -1 to +1: Mixed\n';
                output += '   -3 to -2: Slightly negative\n';
                output += '   -5 to -4: Negative\n';
                output += '   Below -5: Strongly negative\n';
            }
            
            output += '\n' + '-'.repeat(50) + '\n\n';
        });
        
        const buyRecommendations = sortedResults.filter(c => c.recommendation === 'BUY' || c.recommendation === 'STRONG BUY').length;
        const holdRecommendations = sortedResults.filter(c => c.recommendation === 'HOLD' || c.recommendation === 'CONSIDER').length;
        const avoidRecommendations = sortedResults.filter(c => c.recommendation === 'AVOID' || c.recommendation === 'SELL').length;
        
        output += '📊 MARKET OVERVIEW\n';
        output += '==============================\n';
        output += `Positive signals: ${buyRecommendations} | Mixed: ${holdRecommendations} | Negative: ${avoidRecommendations}\n`;
        const marketSentiment = buyRecommendations > avoidRecommendations ? 'BULLISH' : avoidRecommendations > buyRecommendations ? 'BEARISH' : 'NEUTRAL';
        output += `Market Sentiment: ${marketSentiment}\n\n`;
        
        // Best performers (7d)
        const bestPerformers = sortedResults.sort((a, b) => (b.change_7d || 0) - (a.change_7d || 0)).slice(0, 5);
        output += '🏆 BEST PERFORMERS (7D)\n';
        output += '==============================\n';
        bestPerformers.forEach((coin, i) => {
            const price = coin.price >= 1 ? `$${coin.price.toFixed(2)}` : `$${coin.price.toFixed(6)}`;
            output += `${i+1}. ${coin.symbol.toUpperCase().padEnd(12)} ${(coin.change_7d || 0) >= 0 ? '+' : ''}${(coin.change_7d || 0).toFixed(1)}% (${price}) - ${signalLabel(coin.recommendation)}\n`;
        });
        output += '\n';
        
        // Worst performers (7d)
        const worstPerformers = sortedResults.sort((a, b) => (a.change_7d || 0) - (b.change_7d || 0)).slice(0, 5);
        output += '📉 WORST PERFORMERS (7D)\n';
        output += '==============================\n';
        worstPerformers.forEach((coin, i) => {
            const price = coin.price >= 1 ? `$${coin.price.toFixed(2)}` : `$${coin.price.toFixed(6)}`;
            output += `${i+1}. ${coin.symbol.toUpperCase().padEnd(12)} ${(coin.change_7d || 0) >= 0 ? '+' : ''}${(coin.change_7d || 0).toFixed(1)}% (${price}) - ${signalLabel(coin.recommendation)}\n`;
        });
        output += '\n';
        
        // Technical analysis summary
        output += '🔬 TECHNICAL ANALYSIS SUMMARY\n';
        output += '==============================\n';
        output += 'Indicators Used:\n';
        output += '• MACD (12,26,9) - Trend and momentum\n';
        output += '• RSI (14) - Overbought/oversold conditions\n';
        output += '• Bollinger Bands (20,2) - Volatility and mean reversion\n';
        output += '• Stochastic (14) - Price momentum\n';
        output += '• Volume Analysis - Confirmation of moves\n';
        output += '• Momentum (5d/10d) - Short-term trend strength\n\n';
        
        // Top 5 recommendations table
        output += '🎯 TOP 5 BY SCORE\n';
        output += '=================================================================\n';
        output += `${'#'.padEnd(3)} ${'COIN'.padEnd(6)} ${'PRICE'.padEnd(10)} ${'LOWER LVL'.padEnd(10)} ${'UPPER LVL'.padEnd(12)} ${'SIGNAL'.padEnd(10)}\n`;
        output += '-----------------------------------------------------------------\n';
        sortedResults.slice(0, 5).forEach((coin, i) => {
            const priceStr = coin.price >= 1 ? `$${coin.price.toFixed(2)}` : `$${coin.price.toFixed(4)}`;
            const stopStr = coin.stop_loss >= 1 ? `$${coin.stop_loss.toFixed(2)}` : `$${coin.stop_loss.toFixed(4)}`;
            const tpStr = coin.take_profit >= 1 ? `$${coin.take_profit.toFixed(2)}` : `$${coin.take_profit.toFixed(4)}`;
            output += `${(i+1).toString().padEnd(3)} ${coin.symbol.toUpperCase().padEnd(6)} ${priceStr.padEnd(10)} ${stopStr.padEnd(10)} ${tpStr.padEnd(12)} ${signalLabel(coin.recommendation)}\n`;
        });
        output += '\n';
        
        // Disclaimer
        output += '⚠️ DISCLAIMER\n';
        output += '==============================\n';
        output += 'This analysis is automated, general information only. It is not financial advice\n';
        output += 'and not a recommendation to buy or sell. StockIQ is not a licensed financial adviser.\n';
        output += 'Always do your own research before investing.\n';
        output += 'Cryptocurrency trading involves significant risk.\n\n';
        
        output += '📊 ANALYSIS SUMMARY:\n';
        output += `• Total coins analyzed: ${sortedResults.length}\n`;
        if (workerDetails.length > 0) {
            workerDetails.forEach(worker => {
                output += `• Worker ${worker.worker}: ${worker.coins} coins\n`;
            });
        }
        output += `• Positive signals: ${buyRecommendations}\n`;
        output += `• Mixed signals: ${holdRecommendations}\n`;
        output += `• Negative signals: ${avoidRecommendations}\n`;
        output += `• Processing time: ${processingTime.toFixed(2)} seconds\n`;
    } else {
        output += 'No results available\n';
    }
    
    output += `\n✅ Real-time CoinSpot comprehensive crypto analysis complete!`;
    
    const htmlOutput = `<pre style="white-space: pre-wrap; font-family: monospace;">${output}</pre>`;
    
    return { type: 'coinspot_screener', data: htmlOutput };
}

function formatSingleCoinResult(apiData, coinSymbol) {
    // The report comes ready-made from the single-stock report function (its coin form): chart, 0-100 score, the
    // points behind it, levels and the note on which ticker the coin was priced by.
    const report = apiData && apiData.results && apiData.results[0] && apiData.results[0].comprehensive_analysis;
    if (report) return { type: 'single_coin_analysis', data: report + '\n' };
    const shown = reportText(String(coinSymbol || '').toUpperCase());
    return { type: 'single_coin_analysis', data: `
============================================================
🔍 SINGLE COIN ANALYSIS: ${shown}
============================================================

⚠️ No price data was found for ${shown}.
Check the symbol (for example BTC, ETH, SOL). Prices come from Yahoo Finance, and a coin it does not list cannot be analysed.

ℹ️ General information only, not financial advice.
` };
}



function formatASXResult(apiData, subOption) {
    const titles = { '50': 'ASX TOP 50', '100': 'ASX TOP 100', '200': 'ASX 200', '300': 'ASX 300' };
    const universeSize = { '50': 49, '100': 99, '200': 195, '300': 294 };  // real list sizes (refreshed 10 Oct 2026)
    
    let output = `
============================================================
🇦🇺 ${titles[subOption]} RESULTS (REAL-TIME DATA)
============================================================

Screening Universe: ${universeSize[subOption]} ASX stocks
Market Type: Australian Securities Exchange
Universe Size: ${universeSize[subOption]}
Analysis Date: ${new Date().toLocaleString()}

`;
    
    if (apiData.results && apiData.results.length > 0) {
        const sortedResults = [...apiData.results].sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
        
        const topCount = Math.min(10, sortedResults.length);
        output += `🟢 TOP ${topCount} BY SCORE:\n`;
        sortedResults.slice(0, topCount).forEach((stock, i) => {
            const symbol = (stock.symbol || 'N/A').padEnd(8);
            const price = `${screenerMoney(stock, stock.current_price || stock.price, 'AUD')}`.padStart(10);
            const score = (stock.total_score || stock.score || 0) >= 0 ? `+${(stock.total_score || stock.score || 0).toFixed(1)}` : `${(stock.total_score || stock.score || 0).toFixed(1)}`;
            const rsi = (stock.rsi || 0).toFixed(1).padStart(5);
            const ytd = (stock.ytd_change || 0) >= 0 ? `+${(stock.ytd_change || 0).toFixed(1)}%` : `${(stock.ytd_change || 0).toFixed(1)}%`;
            const vol = `${(stock.volume_ratio || 1).toFixed(1)}x`;
            output += `${(i+1).toString().padStart(2)}. ${symbol} ${price} | Score: ${score} | RSI: ${rsi} | YTD: ${ytd}, Vol: ${vol}\n`;
        });
        
        output += '</table><div style="margin: 20px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;">📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html#reports" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.</div><table class="results-table">\n';
        
        // Add detailed analysis for top 3 stocks
        output += '\n🎯 TOP 3 DETAILED ANALYSIS:\n';
        output += '================================================================\n';
        sortedResults.slice(0, 3).forEach((stock, i) => {
            output += `${i+1}. ${stock.symbol}: ${screenerMoney(stock, stock.price, 'AUD')} | ${signalLabel(stock.recommendation)} | Score: ${(stock.total_score || stock.score || 0) >= 0 ? '+' : ''}${(stock.total_score || stock.score || 0).toFixed(1)}\n`;
            
            if (stock.score_breakdown && stock.score_breakdown.length > 0) {
                output += '   📊 Score Breakdown:\n';
                stock.score_breakdown.forEach(breakdown => {
                    output += `      ${breakdown}\n`;
                });
            }
            
            output += `   📈 Technical: RSI ${(stock.rsi || 50).toFixed(1)} | MACD ${stock.macd_signal || 'NEUTRAL'}\n`;
            output += `   💰 Levels: Support ${screenerMoney(stock, stock.support, 'AUD')} | Resistance ${screenerMoney(stock, stock.resistance, 'AUD')}\n`;
            output += `   📏 Reference levels: Lower ${screenerMoney(stock, stock.stop_loss, 'AUD')} | Upper ${screenerMoney(stock, stock.take_profit, 'AUD')}\n`;
            output += `   📊 Horizon: ${horizonLabel(stock.strategy_type)} | Confidence: ${(stock.confidence || 0).toFixed(0)}%\n\n`;
        });
        
        const positiveStocks = sortedResults.filter(s => (s.total_score || s.score || 0) > 0).length;
        const negativeStocks = sortedResults.filter(s => (s.total_score || s.score || 0) < 0).length;
        const avgScore = sortedResults.reduce((sum, s) => sum + (s.total_score || s.score || 0), 0) / sortedResults.length;
        
        output += `\n📊 ANALYSIS SUMMARY:\n`;
        output += `• Total stocks analyzed: ${sortedResults.length}\n`;
        output += `• Stocks with positive scores: ${positiveStocks}\n`;
        output += `• Stocks with negative scores: ${negativeStocks}\n`;
        output += `• Average score: ${avgScore.toFixed(1)}\n`;
        output += `• Success rate: ${((sortedResults.length/universeSize[subOption])*100).toFixed(1)}%\n`;
    } else {
        output += 'No results available\n';
    }
    
    output += `\n✅ Real-time ${titles[subOption]} complete!`;
    
    return { type: `option_4${subOption}_screener`, data: output };
}


// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
    if (!event.target.closest('.dropdown')) {
        if (activeDropdown) {
            const dropdown = document.getElementById(activeDropdown);
            if (dropdown) {
                dropdown.classList.remove('show');
            }
            activeDropdown = null;
        }
    }
});

// Universal usage counter functions (database-connected)
async function incrementAnalysisCounter(option, subOption) {
    try {
        const response = await fetch('https://nwdlozuwzebth3lxjjd3tik62a0pebhw.lambda-url.us-east-1.on.aws/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                action: 'increment'
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log(`📊 Analysis counter: ${data.count || 0}`);
            updateCounterDisplay(data.count || 0);
        }
    } catch (error) {
        console.warn('Analysis counter failed:', error);
    }
}

async function getAnalysisCounter() {
    try {
        const response = await fetch('https://nwdlozuwzebth3lxjjd3tik62a0pebhw.lambda-url.us-east-1.on.aws/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                action: 'get'
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            return data.count || 0;
        }
    } catch (error) {
        console.warn('Failed to get analysis counter:', error);
    }
    return 0;
}

function updateCounterDisplay(count = null) {
    const counterElement = document.getElementById('usage-counter');
    if (counterElement) {
        if (count !== null) {
            counterElement.textContent = `Analysis Executions: ${count}`;
        } else {
            getAnalysisCounter().then(count => {
                counterElement.textContent = `Analysis Executions: ${count}`;
            });
        }
    }
}

// Countdown functionality
let countdownInterval;

function startCountdown(seconds) {
    const countdownEl = document.getElementById('countdown');
    if (!countdownEl) return;
    
    let remaining = seconds;
    countdownEl.textContent = `Estimated time: ${remaining}s`;
    
    countdownInterval = setInterval(() => {
        remaining--;
        if (remaining > 0) {
            countdownEl.textContent = `Estimated time: ${remaining}s`;
        } else {
            countdownEl.textContent = 'Finishing up...';
        }
    }, 1000);
}

function clearCountdown() {
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }
    const countdownEl = document.getElementById('countdown');
    if (countdownEl) {
        countdownEl.textContent = '';
    }
}

// Threshold slider functionality
window.currentThreshold = 0.25;

function initThresholdSlider() {
    const track = document.getElementById('threshold-slider-track');
    const thumb = document.getElementById('threshold-slider-thumb');
    const display = document.getElementById('threshold-display');
    
    if (!track || !thumb || !display) return;
    
    const thresholds = [0.25, 1, 4, 24];
    const labels = ['15 minutes', '1 hour', '4 hours', '24 hours'];
    
    function updateSlider(position) {
        const trackWidth = track.offsetWidth - thumb.offsetWidth;
        const percentage = Math.max(0, Math.min(1, position / trackWidth));
        const index = Math.round(percentage * (thresholds.length - 1));
        
        thumb.style.left = (index / (thresholds.length - 1)) * trackWidth + 'px';
        window.currentThreshold = thresholds[index];
        display.textContent = labels[index];
        localStorage.setItem('cryptoThresholdIndex', index);
    }
    
    let isDragging = false;
    
    thumb.addEventListener('mousedown', (e) => {
        isDragging = true;
        thumb.style.cursor = 'grabbing';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const rect = track.getBoundingClientRect();
        const position = e.clientX - rect.left - thumb.offsetWidth / 2;
        updateSlider(position);
    });
    
    document.addEventListener('mouseup', () => {
        isDragging = false;
        thumb.style.cursor = 'grab';
    });
    
    track.addEventListener('click', (e) => {
        if (e.target === thumb) return;
        const rect = track.getBoundingClientRect();
        const position = e.clientX - rect.left - thumb.offsetWidth / 2;
        updateSlider(position);
    });
    
    // Touch events for mobile
    thumb.addEventListener('touchstart', (e) => {
        isDragging = true;
        e.preventDefault();
    });
    
    document.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        const rect = track.getBoundingClientRect();
        const touch = e.touches[0];
        const position = touch.clientX - rect.left - thumb.offsetWidth / 2;
        updateSlider(position);
        e.preventDefault();
    });
    
    document.addEventListener('touchend', () => {
        isDragging = false;
    });
    
    // Load saved threshold with delay to ensure proper dimensions
    setTimeout(() => {
        const savedIndex = localStorage.getItem('cryptoThresholdIndex');
        if (savedIndex !== null) {
            const trackWidth = track.offsetWidth - thumb.offsetWidth;
            const index = parseInt(savedIndex);
            if (trackWidth > 0) {
                thumb.style.left = (index / (thresholds.length - 1)) * trackWidth + 'px';
                window.currentThreshold = thresholds[index];
                display.textContent = labels[index];
            }
        }
    }, 10);
}

// Handle URL parameters for direct navigation
function showLoginModal() {
    window.location.href = 'login.html';
}

// Notification functions - same as index.html
preloadedNotificationContent = `
    <div style="padding: 40px; text-align: center; color: var(--text-secondary); display: flex; flex-direction: column; align-items: center; gap: 10px;">
        <div style="width: 30px; height: 30px; border: 3px solid var(--border-color); border-top-color: #007bff; border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
    </div>
    <style>
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
`;
const CACHE_DURATION = Infinity; // Cache indefinitely until invalidated cache

// Listen for cache invalidation from other tabs/pages
window.addEventListener('storage', function(e) {
    if (e.key === 'dashboardCacheInvalidated' && e.newValue === 'true') {
        console.log('📊 Cache invalidated, refreshing notifications...');
        const userId = localStorage.getItem('userId') || 'anonymous';
        localStorage.removeItem(`notificationCache_${userId}`);
        localStorage.removeItem(`notificationCacheTimestamp_${userId}`);
        localStorage.removeItem(`dashboardHistoryCache_${userId}`);
        preloadNotifications();
        updateNotificationBell();
    }
    if (e.key && (e.key.startsWith('seenReports_') || e.key.startsWith('unreadReports_'))) {
        updateNotificationBell();
    }
});

function getNotificationCache() {
    try {
        const userId = localStorage.getItem('userId') || 'anonymous';
        const cached = localStorage.getItem(`dashboardHistoryCache_${userId}`);
        return cached ? JSON.parse(cached) : null;
    } catch {
        return null;
    }
}

function isNotificationCacheValid() {
    const cached = getNotificationCache();
    const cacheInvalidated = localStorage.getItem('dashboardCacheInvalidated');
    
    if (cacheInvalidated) {
        const userId = localStorage.getItem('userId') || 'anonymous';
        localStorage.removeItem('dashboardCacheInvalidated');
        localStorage.removeItem(`notificationCache_${userId}`);
        localStorage.removeItem(`notificationCacheTimestamp_${userId}`);
        return false;
    }
    
    return cached && (Date.now() - cached.timestamp < CACHE_DURATION);
}


function viewPricingPlans() {
    const userId = localStorage.getItem('userId');
    if (userId && userId !== 'anonymous') {
        // Logged in user - redirect to dashboard and scroll to upgrade
        window.location.href = 'dashboard.html?redirect=upgrade';
    } else {
        // Not logged in - redirect to register page
        window.location.href = 'signup.html';
    }
}

function goToNotifications(event) {
    const existingDropdown = document.getElementById('notification-dropdown');
    if (existingDropdown) {
        existingDropdown.remove();
        return;
    }
    
    // Mark all current unread reports as seen by adding them to seenReports
    const unreadReports = JSON.parse(localStorage.getItem(`unreadReports_${localStorage.getItem('userId')}`) || '[]');
    const seenReports = JSON.parse(localStorage.getItem(`seenReports_${localStorage.getItem('userId')}`) || '[]');
    unreadReports.forEach(id => {
        if (!seenReports.includes(id)) seenReports.push(id);
    });
    localStorage.setItem(`seenReports_${localStorage.getItem('userId')}`, JSON.stringify(seenReports));
    updateNotificationBell();
    
    const dropdown = document.createElement('div');
    dropdown.id = 'notification-dropdown';
    const isMobileBell = event?.currentTarget?.id === 'mobile-notification-bell';
    const isMobile = window.innerWidth <= 768;
    const userId = localStorage.getItem('userId');
    const isLoggedOut = !userId || userId === 'anonymous';
    
    dropdown.style.cssText = `
        position: ${isMobileBell ? 'fixed' : 'absolute'};
        top: ${isMobileBell ? '60px' : '100%'};
        ${isMobileBell ? 'left: 50%; transform: translateX(-50%);' : 'right: 0;'}
        width: ${isMobile ? 'calc(100vw - 40px)' : (isLoggedOut ? '240px' : '350px')};
        max-width: ${isLoggedOut ? '240px' : '350px'};
        max-height: 400px;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        box-shadow: 0 4px 20px #cccccc;
        z-index: 10000;
        overflow-y: auto;
        margin-top: 5px;
    `;
    
    // Check for pending notification - always use it if it exists
    const pendingNotif = localStorage.getItem('pendingNotification');
    let content;
    
    if (pendingNotif) {
        const pending = JSON.parse(pendingNotif);
        // Get header from preloaded content or create default
        let header = `<div onclick="window.location.href='dashboard.html'" style="padding: 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); cursor: pointer;" onmouseover="this.style.background='var(--hover-bg)'" onmouseout="this.style.background='var(--bg-secondary)'"><h4 style="margin: 0; color: var(--text-primary); font-size: 14px;">📊 Recent Analysis Reports</h4></div>`;
        
        // Start with header, then loading notification
        content = header + `
            <div style="padding: 12px 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); opacity: 0.7; cursor: default; border-left: 3px solid #007bff;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 8px; height: 8px; background: #007bff; border-radius: 50%; flex-shrink: 0;"></div>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: var(--text-primary); font-size: 13px; margin-bottom: 2px;">
                            ${pending.name} (Loading...)
                        </div>
                        <div style="color: var(--text-secondary); font-size: 11px;">Just now</div>
                    </div>
                </div>
            </div>
        `;
        // Add existing notifications below if available
        if (preloadedNotificationContent) {
            // Extract just the notification items (skip the header which has onclick to dashboard)
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = preloadedNotificationContent;
            // Skip first div (header) and get all notification items
            const allDivs = tempDiv.querySelectorAll('div[onclick]');
            allDivs.forEach((item, index) => {
                // Skip first item (header with dashboard.html)
                if (index > 0) {
                    content += item.outerHTML;
                }
            });
            // Add the footer link
            const footer = tempDiv.querySelector('a[href="dashboard.html"]');
            if (footer) content += footer.outerHTML;
        }
    } else {
        content = preloadedNotificationContent;
    }
    
    dropdown.innerHTML = content || `
        <div style="padding: 40px; text-align: center; color: var(--text-secondary); display: flex; flex-direction: column; align-items: center; gap: 10px;">
            <div style="width: 30px; height: 30px; border: 3px solid var(--border-color); border-top-color: #007bff; border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
            <p>Loading notifications...</p>
        </div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
    `;
    
    // Invalidate cache and refresh notifications (only if logged in)
    const currentUserId = localStorage.getItem('userId');
    if (currentUserId && currentUserId !== 'anonymous') {
        localStorage.setItem('dashboardCacheInvalidated', 'true');
        preloadNotifications().then(() => {
            if (dropdown.parentNode && pendingNotif) {
                // Reconstruct with header + loading + new content
                const pending = JSON.parse(pendingNotif);
                let header = `<div onclick="window.location.href='dashboard.html'" style="padding: 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); cursor: pointer;" onmouseover="this.style.background='var(--hover-bg)'" onmouseout="this.style.background='var(--bg-secondary)'"><h4 style="margin: 0; color: var(--text-primary); font-size: 14px;">📊 Recent Analysis Reports</h4></div>`;
                let loadingNotif = `
                    <div style="padding: 12px 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); opacity: 0.7; cursor: default; border-left: 3px solid #007bff;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="width: 8px; height: 8px; background: #007bff; border-radius: 50%; flex-shrink: 0;"></div>
                            <div style="flex: 1;">
                                <div style="font-weight: 600; color: var(--text-primary); font-size: 13px; margin-bottom: 2px;">
                                    ${pending.name} (Loading...)
                                </div>
                                <div style="color: var(--text-secondary); font-size: 11px;">Just now</div>
                            </div>
                        </div>
                    </div>
                `;
                // Extract just notification items from preloaded content
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = preloadedNotificationContent;
                const items = tempDiv.querySelectorAll('div[onclick]:not([onclick*="dashboard.html"])');
                let itemsHtml = '';
                items.forEach(item => { itemsHtml += item.outerHTML; });
                const footer = tempDiv.querySelector('a[href="dashboard.html"]');
                dropdown.innerHTML = header + loadingNotif + itemsHtml + (footer ? footer.outerHTML : '');
                localStorage.removeItem('pendingNotification');
            } else if (dropdown.parentNode) {
                dropdown.innerHTML = preloadedNotificationContent;
            }
        });
    }
        const bell = event?.currentTarget || document.getElementById('notification-bell') || document.getElementById('mobile-notification-bell');
    if (bell) {
        if (isMobileBell) {
            document.body.appendChild(dropdown);
        } else {
            bell.style.position = 'relative';
            bell.appendChild(dropdown);
        }
    }
    
    setTimeout(() => {
        document.addEventListener('click', function closeOnClickOutside(e) {
            if (!bell.contains(e.target)) {
                dropdown.remove();
                document.removeEventListener('click', closeOnClickOutside);
            }
        });
    }, 100);
}

function updateNotificationBell() {
    const userId = localStorage.getItem('userId');
    if (!userId || userId === 'anonymous') return;
    
    let unreadReports = JSON.parse(localStorage.getItem(`unreadReports_${userId}`) || '[]');
    unreadReports = [...new Set(unreadReports)];
    localStorage.setItem(`unreadReports_${userId}`, JSON.stringify(unreadReports));
    
    const seenReports = JSON.parse(localStorage.getItem(`seenReports_${userId}`) || '[]');
    const bell = document.getElementById('notification-bell');
    const badge = document.getElementById('notification-badge');
    
    const unseenCount = unreadReports.filter(id => !seenReports.includes(id)).length;
    
    if (bell) {
        bell.style.display = 'block';
        if (badge) {
            if (unseenCount > 0) {
                badge.style.display = 'flex';
                badge.textContent = unseenCount > 9 ? '9+' : unseenCount;
            } else {
                badge.style.display = 'none';
            }
        }
    }
    
    // Update mobile bell
    const mobileBell = document.getElementById('mobile-notification-bell');
    const mobileBadge = document.getElementById('mobile-notification-badge');
    if (mobileBell) {
        mobileBell.style.display = 'block';
        if (mobileBadge) {
            if (unseenCount > 0) {
                mobileBadge.style.display = 'flex';
                mobileBadge.textContent = unseenCount > 9 ? '9+' : unseenCount;
            } else {
                mobileBadge.style.display = 'none';
            }
        }
    }
}

function rerunAnalysis(symbol) {
    window.location.href = `analysis.html?symbol=${encodeURIComponent(symbol)}&option=1&subOption=custom`;
}

function getNotificationCache() {
    try {
        const userId = localStorage.getItem('userId') || 'anonymous';
        const cached = localStorage.getItem(`dashboardHistoryCache_${userId}`);
        return cached ? JSON.parse(cached) : null;
    } catch {
        return null;
    }
}

function isNotificationCacheValid() {
    const cached = getNotificationCache();
    const cacheInvalidated = localStorage.getItem('dashboardCacheInvalidated');
    
    if (cacheInvalidated) {
        const userId = localStorage.getItem('userId') || 'anonymous';
        localStorage.removeItem('dashboardCacheInvalidated');
        localStorage.removeItem(`notificationCache_${userId}`);
        localStorage.removeItem(`notificationCacheTimestamp_${userId}`);
        localStorage.removeItem(`dashboardHistoryCache_${userId}`);
        return false;
    }
    
    return cached && (Date.now() - cached.timestamp < CACHE_DURATION);
}

// Preload notifications in background
async function preloadNotifications() {
    try {
        // Check if we can use cached data
        if (isNotificationCacheValid()) {
            const cached = getNotificationCache();
            window.analysisHistory = cached.data.history || [];
            console.log('📊 Using cached notification data');
        } else {
            // Clear cache invalidation flag
            localStorage.removeItem('dashboardCacheInvalidated');
            
            // Fetch fresh data
            const userId = localStorage.getItem('userId') || 'anonymous';
            const response = await fetch('https://nwdjnlcbtj34ywy6sgawmwhcx40ologt.lambda-url.us-east-1.on.aws/?v=' + Date.now(), {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    action: 'get_history',
                    userId: userId,
                    showDeleted: false
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                window.analysisHistory = data.history || [];
                
                // Cache the fresh data
                try {
                    const userId = localStorage.getItem('userId') || 'anonymous';
                    const cacheData = {
                        data: { history: window.analysisHistory || [] },
                        timestamp: Date.now()
                    };
                    localStorage.setItem(`dashboardHistoryCache_${userId}`, JSON.stringify(cacheData));
                } catch (e) {
                    // Storage quota exceeded, clear some space
                    const userId = localStorage.getItem('userId') || 'anonymous';
                    localStorage.removeItem(`dashboardHistoryCache_${userId}`);
                }
                
                console.log('📊 Fetched and cached fresh notification data');
            }
        }
        
        // Generate preloaded content
        let unreadReports = JSON.parse(localStorage.getItem(`unreadReports_${localStorage.getItem('userId')}`) || '[]');
        
        const recentAnalyses = (window.analysisHistory || []).slice(0, 10);
        
        let dropdownContent = `
            <div onclick="window.location.href='dashboard.html'" style="padding: 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); cursor: pointer;" onmouseover="this.style.background='var(--hover-bg)'" onmouseout="this.style.background='var(--bg-secondary)'">
                <h4 style="margin: 0; color: var(--text-primary); font-size: 14px;">📊 Recent Analysis Reports</h4>
                <p style="margin: 5px 0 0 0; color: var(--text-secondary); font-size: 12px;">${unreadReports.length} unread</p>
            </div>
        `;
        
        if (recentAnalyses.length === 0) {
            // Check if there's a pending notification
            const pendingNotif = localStorage.getItem('pendingNotification');
            if (pendingNotif) {
                const pending = JSON.parse(pendingNotif);
                dropdownContent += `
                    <div style="padding: 12px 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); opacity: 0.7; border-left: 3px solid #007bff; cursor: default;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="width: 8px; height: 8px; background: #007bff; border-radius: 50%;"></div>
                            <div style="flex: 1;">
                                <div style="font-weight: 600; color: var(--text-primary); font-size: 13px;">${pending.name} (Loading...)</div>
                                <div style="color: var(--text-secondary); font-size: 11px;">Just now</div>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                dropdownContent += `
                    <div style="padding: 20px; text-align: center; color: var(--text-secondary);">
                        <p>No analysis reports yet</p>
                        <a href="analysis.html" style="color: #007bff; text-decoration: none;">Start your first analysis</a>
                    </div>
                `;
            }
        } else {
            recentAnalyses.forEach(item => {
                const isUnread = unreadReports.includes(item.analysisId);
                const isDeleted = item.deleted;
                const isLoading = item.loading;
                const bgColor = isUnread && !isDeleted ? 'var(--bg-secondary)' : 'var(--card-bg)';
                const hoverHandlers = (isDeleted || isLoading) ? '' : `onmouseover="this.style.background='var(--hover-bg)'" onmouseout="this.style.background='${bgColor}'"`;
                
                dropdownContent += `
                    <div onclick="${(isDeleted || isLoading) ? '' : `viewAnalysisFromNotification('${item.analysisId}')`}" style="
                        padding: 12px 15px;
                        border-bottom: 1px solid var(--border-color);
                        cursor: ${(isDeleted || isLoading) ? 'default' : 'pointer'};
                        background: ${bgColor};
                        opacity: ${isLoading ? '0.6' : '1'};
                        ${isUnread && !isDeleted ? 'border-left: 3px solid #007bff;' : ''}
                    " ${hoverHandlers}>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            ${isUnread && !isDeleted ? '<div style="width: 8px; height: 8px; background: #007bff; border-radius: 50%; flex-shrink: 0;"></div>' : '<div style="width: 8px;"></div>'}
                            <div style="flex: 1; min-width: 0;">
                                <div style="font-weight: ${isUnread && !isDeleted ? 'bold' : '500'}; color: var(--text-primary); font-size: 13px; margin-bottom: 2px;">
                                    ${(item.companyName && item.companyName !== 'undefined') ? item.companyName : item.symbol} ${isDeleted ? '(Deleted)' : isLoading ? '(Loading...)' : ''}
                                </div>
                                <div style="color: var(--text-secondary); font-size: 11px;">
                                    ${formatDate(item.timestamp)}
                                </div>
                            </div>
                            ${!isDeleted ? `<button onclick="event.stopPropagation(); rerunFromNotification('${item.analysisId}')" style="background: none; border: 1px solid var(--border-color); border-radius: 50%; width: 28px; height: 28px; cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); font-size: 14px;" title="Rerun analysis">🔄</button>` : ''}
                        </div>
                    </div>
                `;
            });
            
            dropdownContent += `
                </div><a href="dashboard.html" style="position: sticky; bottom: 0; padding: 15px; text-align: center; border-top: 1px solid var(--border-color); background: var(--bg-secondary); z-index: 10; display: block; color: #007bff; text-decoration: none; font-size: 14px; font-weight: 500; cursor: pointer; transition: background 0.2s;" onmouseover="this.style.background='var(--hover-bg)'" onmouseout="this.style.background='var(--bg-secondary)'">View Dashboard</a>
            `;
        }
        
        preloadedNotificationContent = dropdownContent;
        localStorage.removeItem('pendingNotification');
        console.log('📊 Notifications preloaded successfully');
        
        // Update any open dropdown with new content while preserving scroll position
        const openDropdown = document.getElementById('notification-dropdown');
        if (openDropdown) {
            const scrollTop = openDropdown.scrollTop;
            // Remove any loading notifications before updating
            const loadingItems = openDropdown.querySelectorAll('[style*="Loading..."]');
            loadingItems.forEach(item => {
                const parent = item.closest('div[style*="padding: 12px"]');
                if (parent) parent.remove();
            });
            openDropdown.innerHTML = preloadedNotificationContent;
            openDropdown.scrollTop = scrollTop;
        }
        
    } catch (error) {
        console.error('Failed to preload notifications:', error);
        preloadedNotificationContent = `
            <div style="padding: 20px; text-align: center; color: var(--text-secondary);">
                <p>Failed to load notifications</p>
                <a href="dashboard.html" style="color: #007bff; text-decoration: none;">View Dashboard</a>
            </div>
        `;
        
        // Update any open dropdown with error content while preserving scroll position
        const openDropdown = document.getElementById('notification-dropdown');
        if (openDropdown) {
            const scrollTop = openDropdown.scrollTop;
            openDropdown.innerHTML = preloadedNotificationContent;
            openDropdown.scrollTop = scrollTop;
        }
    }
}

function formatDate(timestamp) {
    // Ensure timestamp is treated as UTC if no timezone specified
    let dateStr = timestamp;
    if (!timestamp.includes('Z') && !timestamp.includes('+') && !timestamp.includes('-', 10)) {
        dateStr = timestamp + 'Z';  // Add UTC indicator
    }
    return new Date(dateStr).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}

async function viewAnalysisFromNotification(analysisId) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    const unreadReports = JSON.parse(localStorage.getItem(`unreadReports_${localStorage.getItem('userId')}`) || '[]');
    if (unreadReports.includes(analysisId)) {
        const updatedUnread = unreadReports.filter(id => id !== analysisId);
        localStorage.setItem(`unreadReports_${localStorage.getItem('userId')}`, JSON.stringify(updatedUnread));
        
        // Reset bellSeen if all items are now read
        if (updatedUnread.length === 0) {
            localStorage.removeItem('bellSeen');
        }
        
        // Immediate visual update
        const clickedItem = event?.target?.closest('div[onclick*="viewAnalysisFromNotification"]');
        if (clickedItem) {
            clickedItem.style.background = 'var(--card-bg)';
            clickedItem.style.borderLeft = 'none';
            const blueDot = clickedItem.querySelector('div[style*="background: #007bff"]');
            if (blueDot) blueDot.style.display = 'none';
            const symbolText = clickedItem.querySelector('div[style*="font-weight"]');
            if (symbolText) symbolText.style.fontWeight = '500';
        }
        
        updateNotificationBell();
        preloadNotifications();
    }
    
    try {
        const userId = localStorage.getItem('userId') || 'anonymous';
        const response = await fetch('https://nwdjnlcbtj34ywy6sgawmwhcx40ologt.lambda-url.us-east-1.on.aws/?v=' + Date.now(), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                action: 'get_analysis',
                analysisId: analysisId,
                userId: userId
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            showAnalysisModal(data.analysis);
        } else {
            alert('Analysis report not found or no longer available.');
        }
    } catch (error) {
        console.error('Error loading analysis:', error);
        alert('Error loading analysis report.');
    }
}

function showAnalysisModal(analysis) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.8); z-index: 10000; display: flex;
        align-items: center; justify-content: center; padding: 20px;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
        background: var(--card-bg); border-radius: 10px; padding: 30px;
        max-width: 800px; max-height: 80vh; overflow-y: auto; position: relative;
    `;
    
    content.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="color: var(--text-primary);">${analysis.symbol} Analysis Report</h2>
            <button onclick="this.closest('.modal').remove()" 
                    style="background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-primary);">×</button>
        </div>
        <div style="white-space: pre-wrap; font-family: monospace; font-size: 14px; color: var(--text-primary);">
            ${analysis.report}
        </div>
    `;
    
    modal.appendChild(content);
    modal.className = 'modal';
    document.body.appendChild(modal);
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}


document.addEventListener('DOMContentLoaded', function() {
    updateCounterDisplay();
    initThresholdSlider();
    setTimeout(displayTrialStatus, 100);
    
    // Force auth check and UI update on page load
    if (typeof authManager !== 'undefined') {
        authManager.checkAuthStatus();
    }
    
    // Initialize notifications
    updateNotificationBell();
    
    const userId = localStorage.getItem('userId');
    if (userId && userId !== 'anonymous') {
        preloadNotifications();
    } else {
        preloadedNotificationContent = `
            <div onclick="window.location.href='login.html'" style="padding: 15px; text-align: center; color: var(--text-secondary); cursor: pointer;">
                <p style="margin: 0 0 10px 0; font-size: 14px;">Please log in to view notifications</p>
                <a href="login.html" style="color: #007bff; text-decoration: none; font-size: 15px; font-weight: 600;">Login</a>
            </div>
        `;
    }
    

    
    const urlParams4 = new URLSearchParams(window.location.search);
    const symbol4 = urlParams4.get('symbol');
    const option4 = urlParams4.get('option');
    const subOption4 = urlParams4.get('subOption');
    const autorun4 = urlParams4.get('autorun');
    
    // Handle autorun from index page clicks (but not option 72 - handled above)
    if (autorun4 === 'true' && option4 && subOption4 && option4 !== '72') {
        selectOption(parseInt(option4));
        setTimeout(() => {
            runAnalysis(parseInt(option4), subOption4);
        }, 500);
        return;
    }
    
    if (symbol4 && option4 === '1' && subOption4 === 'custom') {
        selectOption(1);
        showStockInput();
        
        setTimeout(() => {
            const symbolInput = document.getElementById('symbols-input');
            if (symbolInput) {
                symbolInput.value = symbol4;
                runAnalysis(1, 'custom');
            }
        }, 500);
    } else if (option4 && !symbol4) {
        selectOption(parseInt(option4));
    }
});

const NIKKEI_COMPANY_NAMES = {
    '6758.T': 'Sony Group', '6861.T': 'Keyence', '6902.T': 'Denso', '6954.T': 'Fanuc',
    '6971.T': 'Kyocera', '6976.T': 'Murata Mfg', '8035.T': 'Tokyo Electron', '6857.T': 'Advantest',
    '6920.T': 'Lasertec', '6723.T': 'Renesas Electronics', '6762.T': 'TDK', '6841.T': 'Yokogawa Electric',
    '6869.T': 'Sysmex', '6963.T': 'Rohm', '6506.T': 'Yaskawa Electric', '6645.T': 'Omron',
    '6702.T': 'Fujitsu', '6701.T': 'NEC', '6752.T': 'Panasonic Holdings', '6501.T': 'Hitachi',
    '6503.T': 'Mitsubishi Electric', '6504.T': 'Fuji Electric', '6526.T': 'Socionext',
    '6770.T': 'Alps Alpine', '6724.T': 'Seiko Epson', '6967.T': 'Shinko Electric',
    '6844.T': 'Shindengen Electric', '6845.T': 'Azbil', '6849.T': 'Nihon Kohden', '6674.T': 'GS Yuasa',
    '6707.T': 'Sanken Electric', '7735.T': 'Screen Holdings', '4704.T': 'Trend Micro',
    '4812.T': 'NTT Data', '6807.T': 'Japan Aviation Electronics', '9432.T': 'NTT',
    '9433.T': 'KDDI', '9984.T': 'SoftBank Group', '4689.T': 'Z Holdings', '4755.T': 'Rakuten Group',
    '6098.T': 'Recruit Holdings', '4385.T': 'Mercari', '2413.T': 'M3 Inc', '7751.T': 'Canon',
    '7731.T': 'Nikon', '7974.T': 'Nintendo', '7832.T': 'Bandai Namco', '9766.T': 'Konami',
    '7752.T': 'Ricoh', '4901.T': 'Fujifilm Holdings', '7203.T': 'Toyota Motor',
    '7267.T': 'Honda Motor', '7269.T': 'Suzuki Motor', '7270.T': 'Subaru',
    '7201.T': 'Nissan Motor', '7202.T': 'Isuzu Motors', '7205.T': 'Hino Motors',
    '7211.T': 'Mitsubishi Motors', '7261.T': 'Mazda Motor', '7272.T': 'Yamaha Motor',
    '5108.T': 'Bridgestone', '5110.T': 'Sumitomo Rubber', '7011.T': 'Mitsubishi Heavy Ind',
    '7013.T': 'IHI Corporation', '7012.T': 'Kawasaki Heavy Ind', '6301.T': 'Komatsu',
    '6326.T': 'Kubota', '6361.T': 'Ebara', '6471.T': 'NSK', '6481.T': 'THK',
    '8306.T': 'MUFG', '8316.T': 'SMFG', '8411.T': 'Mizuho Financial',
    '8308.T': 'Resona Holdings', '8309.T': 'SMBC Trust', '8331.T': 'Chiba Bank',
    '8354.T': 'Fukuoka Financial', '7186.T': 'Concordia Financial', '8604.T': 'Nomura Holdings',
    '8601.T': 'Daiwa Securities', '8630.T': 'Sompo Holdings', '8725.T': 'MS&AD Insurance',
    '8750.T': 'Dai-ichi Life', '8795.T': 'T&D Holdings', '8766.T': 'Tokio Marine',
    '8697.T': 'Japan Exchange Group', '8802.T': 'Mitsubishi Estate', '8830.T': 'Sumitomo Realty',
    '3289.T': 'Tokyu Fudosan', '3003.T': 'Hulic', '1925.T': 'Daiwa House', '1928.T': 'Sekisui House',
    '8905.T': 'AEON Mall', '4502.T': 'Takeda Pharmaceutical', '4503.T': 'Astellas Pharma',
    '4507.T': 'Shionogi', '4519.T': 'Chugai Pharmaceutical', '4523.T': 'Eisai',
    '4528.T': 'Ono Pharmaceutical', '4543.T': 'Terumo', '4578.T': 'Otsuka Holdings',
    '4568.T': 'Daiichi Sankyo', '4151.T': 'Kyowa Kirin', '4506.T': 'Sumitomo Pharma',
    '4063.T': 'Shin-Etsu Chemical', '4183.T': 'Mitsui Chemicals', '4188.T': 'Mitsubishi Chemical',
    '4208.T': 'UBE Industries', '4452.T': 'Kao Corporation', '4911.T': 'Shiseido',
    '3407.T': 'Asahi Kasei', '3436.T': 'SUMCO', '5201.T': 'AGC', '5214.T': 'Nippon Electric Glass',
    '5232.T': 'Sumitomo Osaka Cement', '5233.T': 'Taiheiyo Cement', '5301.T': 'Tokai Carbon',
    '5332.T': 'TOTO', '5333.T': 'NGK Insulators', '5401.T': 'Nippon Steel',
    '5406.T': 'Kobe Steel', '5411.T': 'JFE Holdings', '5713.T': 'Sumitomo Metal Mining',
    '5711.T': 'Mitsubishi Materials', '5706.T': 'Mitsui Mining & Smelting',
    '5714.T': 'DOWA Holdings', '5802.T': 'Sumitomo Electric', '5801.T': 'Furukawa Electric',
    '5803.T': 'Fujikura', '2502.T': 'Asahi Group', '2503.T': 'Kirin Holdings',
    '2801.T': 'Kikkoman', '2802.T': 'Ajinomoto', '2914.T': 'Japan Tobacco',
    '2269.T': 'Meiji Holdings', '2282.T': 'NH Foods', '2501.T': 'Sapporo Holdings',
    '2871.T': 'Nichirei', '2270.T': 'Megmilk Snow Brand', '9983.T': 'Fast Retailing',
    '9843.T': 'Nitori Holdings', '3382.T': 'Seven & i Holdings', '8267.T': 'AEON',
    '3099.T': 'Isetan Mitsukoshi', '3086.T': 'J.Front Retailing', '7453.T': 'Ryohin Keikaku',
    '3197.T': 'Skylark Holdings', '3543.T': 'Colowide', '8136.T': 'Sanrio',
    '1605.T': 'Inpex', '5019.T': 'Idemitsu Kosan', '5020.T': 'ENEOS Holdings',
    '9501.T': 'Tokyo Electric Power', '9502.T': 'Chubu Electric Power',
    '9503.T': 'Kansai Electric Power', '9531.T': 'Tokyo Gas', '9532.T': 'Osaka Gas',
    '9020.T': 'JR East', '9021.T': 'JR West', '9022.T': 'JR Central',
    '9202.T': 'ANA Holdings', '9201.T': 'Japan Airlines', '9064.T': 'Yamato Holdings',
    '9147.T': 'Nippon Express', '9101.T': 'NYK Line', '9104.T': 'Mitsui OSK Lines',
    '9107.T': 'Kawasaki Kisen', '1801.T': 'Taisei Corporation', '1802.T': 'Obayashi',
    '1803.T': 'Shimizu Corporation', '1812.T': 'Kajima', '1963.T': 'JGC Holdings',
    '8001.T': 'Itochu', '8002.T': 'Marubeni', '8015.T': 'Toyota Tsusho',
    '8031.T': 'Mitsui & Co', '8053.T': 'Sumitomo Corporation', '8058.T': 'Mitsubishi Corporation',
    '2768.T': 'Sojitz', '7911.T': 'Toppan Holdings', '7912.T': 'Dai Nippon Printing',
    '4661.T': 'Oriental Land', '6178.T': 'Japan Post Holdings', '4739.T': 'Itochu Techno',
    '6367.T': 'Daikin Industries', '6302.T': 'Sumitomo Heavy Ind', '6305.T': 'Hitachi Construction',
    '6363.T': 'Tsurumi Mfg', '6370.T': 'Kurita Water', '6473.T': 'JTEKT',
    '6588.T': 'Toshiba Tec', '6703.T': 'Oki Electric', '6708.T': 'Eizo Corporation',
    '6853.T': 'Kyowa Electronic', '7004.T': 'Hitachi Zosen', '7003.T': 'Mitsui Engineering',
    '5631.T': 'Japan Steel Works', '5541.T': 'Pacific Metals', '1808.T': 'Haseko',
    '6366.T': 'Chiyoda Corporation', '6756.T': 'Hitachi Kokusai', '6755.T': 'Fujitsu General',
    '6753.T': 'Sharp Corporation', '6767.T': 'Mitsumi Electric', '6773.T': 'Pioneer',
    '9681.T': 'Tokyo Dome', '4565.T': 'Sosei Group', '8616.T': 'Tokai Tokyo Financial',
    '8698.T': 'Monex Group', '3034.T': 'Qol Holdings',
    '543A.T': 'Archion',
    '8304.T': 'Aozora Bank',
    '5831.T': 'Shizuoka Financial Group',
    '4061.T': 'Denka',
    '3405.T': 'Kuraray',
    '4021.T': 'Nissan Chemical Industries',
    '6988.T': 'Nitto Denko',
    '4004.T': 'Resonac',
    '4005.T': 'Sumitomo Chemical',
    '4043.T': 'Tokuyama',
    '4042.T': 'Tosoh',
    '9434.T': 'SoftBank',
    '1721.T': 'Comsys Holdings',
    '285A.T': 'Kioxia Holdings',
    '6479.T': 'MinebeaMitsumi',
    '6981.T': 'Murata Manufacturing',
    '6594.T': 'Nidec',
    '1332.T': 'Nissui',
    '2002.T': 'Nisshin Seifun Group',
    '6113.T': 'Amada',
    '6472.T': 'NTN',
    '6103.T': 'Okuma Holdings',
    '6273.T': 'SMC',
    '8253.T': 'Credit Saison',
    '8591.T': 'Orix Co',
    '7951.T': 'Yamaha',
    '6146.T': 'Disco Corporation',
    '7741.T': 'Hoya',
    '4902.T': 'Konica Minolta Holdings',
    '7733.T': 'Olympus',
    '3861.T': 'Oji Holdings',
    '9008.T': 'Keio',
    '9009.T': 'Keisei Electric Railway',
    '9007.T': 'Odakyu Electric Railway',
    '9001.T': 'Tobu Railway',
    '9005.T': 'Tokyu',
    '8801.T': 'Mitsui Fudosan',
    '8804.T': 'Tokyo Tatemono',
    '8252.T': 'Marui Group',
    '7532.T': 'Pan Pacific International Holdings',
    '8233.T': 'Takashimaya',
    '3092.T': 'ZOZO',
    '5101.T': 'The Yokohama Rubber',
    '6532.T': 'Baycurrent',
    '4751.T': 'CyberAgent',
    '2432.T': 'Dena',
    '4324.T': 'Dentsu',
    '3659.T': 'Nexon',
    '4307.T': 'Nomura Research Institute',
    '9735.T': 'Secom',
    '3697.T': 'SHIFT',
    '9602.T': 'Toho',
    '3401.T': 'Teijin',
    '3402.T': 'Toray Industries'
};
// The report of a share screener that has no formatter of its own: the words that differ between markets come from `r`
// (the Nikkei's below; any later market's from its entry in screeners.js: `report`).
function formatMarketResult(apiData, r, universeSize) {
    let output = `
============================================================
${r.heading} RESULTS (REAL-TIME DATA)
============================================================
Screening Universe: ${universeSize} ${r.stocks}
Market Type: ${r.exchange}
Universe Size: ${universeSize}
Analysis Date: ${new Date().toLocaleString()}
`;
    if (apiData.results && apiData.results.length > 0) {
        const sortedResults = [...apiData.results].sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
        const topCount = Math.min(10, sortedResults.length);
        output += `🟢 TOP ${topCount} BY SCORE:\n`;
        sortedResults.slice(0, topCount).forEach((stock, i) => {
            const symbol = reportText((stock.symbol || 'N/A').padEnd(8));        // a symbol can hold an "&" (M&M.NS), and the report is HTML
            const name = (r.names || {})[stock.symbol] || reportText(stock.symbol);
            const price = `${screenerMoney(stock, stock.current_price || stock.price, r.currency)}`.padStart(10);
            const scoreVal = stock.total_score || stock.score || 0;
            const score = scoreVal >= 0 ? `+${scoreVal.toFixed(1)}` : `${scoreVal.toFixed(1)}`;
            const rsi = (stock.rsi || 0).toFixed(1).padStart(5);
            const ytdVal = stock.ytd_change || 0;
            const ytd = ytdVal >= 0 ? `+${ytdVal.toFixed(1)}%` : `${ytdVal.toFixed(1)}%`;
            const vol = `${(stock.volume_ratio || 1).toFixed(1)}x`;
            output += `${(i+1).toString().padStart(2)}. ${symbol} ${name.slice(0, 22).padEnd(22)} ${price} | Score: ${score} | RSI: ${rsi} | YTD: ${ytd}, Vol: ${vol}\n`;
        });
        output += '\n</pre><div style="margin: 20px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;">📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html#reports" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.</div><pre style="white-space: pre-wrap; font-family: monospace;">\n🎯 TOP 3 DETAILED ANALYSIS:\n';
        output += '================================================================\n';
        sortedResults.slice(0, 3).forEach((stock, i) => {
            const priceVal = stock.price || 0;
            const scoreVal = stock.total_score || stock.score || 0;
            output += `${i+1}. ${reportText(stock.symbol)}: ${screenerMoney(stock, priceVal, r.currency)} | ${signalLabel(stock.recommendation)} | Score: ${scoreVal >= 0 ? '+' : ''}${scoreVal.toFixed(1)}\n`;
            if (stock.score_breakdown && stock.score_breakdown.length > 0) {
                output += '   📊 Score Breakdown:\n';
                stock.score_breakdown.forEach(breakdown => {
                    output += `      ${breakdown}\n`;
                });
            }
            output += `   📈 Technical: RSI ${(stock.rsi || 50).toFixed(1)} | MACD ${stock.macd_signal || 'NEUTRAL'}\n`;
            output += `   💰 Levels: Support ${screenerMoney(stock, stock.support, r.currency)} | Resistance ${screenerMoney(stock, stock.resistance, r.currency)}\n`;
            output += `   📏 Reference levels: Lower ${screenerMoney(stock, stock.stop_loss, r.currency)} | Upper ${screenerMoney(stock, stock.take_profit, r.currency)}\n`;
            output += `   📊 Horizon: ${horizonLabel(stock.strategy_type)} | Confidence: ${(stock.confidence || 0).toFixed(0)}%\n\n`;
        });
        const positiveStocks = sortedResults.filter(s => (s.total_score || s.score || 0) > 0).length;
        const negativeStocks = sortedResults.filter(s => (s.total_score || s.score || 0) < 0).length;
        const avgScore = sortedResults.reduce((sum, s) => sum + (s.total_score || s.score || 0), 0) / sortedResults.length;
        output += `\n📊 ANALYSIS SUMMARY:\n`;
        output += `\u2022 Total stocks analyzed: ${sortedResults.length}\n`;
        output += `\u2022 Stocks with positive scores: ${positiveStocks}\n`;
        output += `\u2022 Stocks with negative scores: ${negativeStocks}\n`;
        output += `\u2022 Average score: ${avgScore.toFixed(1)}\n`;
        output += `\u2022 Success rate: ${((sortedResults.length/universeSize)*100).toFixed(1)}%\n`;
    } else {
        output += 'No results available\n';
    }
    output += `\n\u2705 Real-time ${r.done} complete!`;
    const htmlOutput = `<pre style="white-space: pre-wrap; font-family: monospace;">${output}</pre>`;
    return { type: r.type, data: htmlOutput };
}

function formatNikkeiResult(apiData) {
    return formatMarketResult(apiData, { heading: '🇯🇵 JAPAN NIKKEI 225', stocks: 'Japan Nikkei stocks', exchange: 'Tokyo Stock Exchange', currency: 'JPY',
        done: 'Japan Nikkei 225', type: 'option_5nikkei225_screener', names: NIKKEI_COMPANY_NAMES }, 225);        // 225: the real list size (refreshed 10 Oct 2026)
}

// Coming Soon popup function
function showComingSoonPopup() {
    const modal = document.createElement('div');
    modal.id = 'coming-soon-modal';
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); z-index: 10000; display: flex;
        align-items: center; justify-content: center; padding: 20px;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
        background: var(--card-bg); border-radius: 12px; padding: 30px;
        max-width: 400px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    `;
    
    content.innerHTML = `
        <div style="font-size: 48px; margin-bottom: 20px;">🚧</div>
        <h3 style="color: var(--text-primary); margin-bottom: 15px;">Coming Soon!</h3>
        <p style="color: var(--text-secondary); margin-bottom: 25px; line-height: 1.5;">
            This market screener is currently under development. We're working hard to bring you comprehensive analysis for this region.
        </p>
        <button onclick="document.getElementById('coming-soon-modal').remove()" 
                style="background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
            Got it
        </button>
    `;
    
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}


// Symbol suggestions with exchange suffixes
document.addEventListener('DOMContentLoaded', function() {
    const symbolsInput = document.getElementById('symbols-input');
    const suggestionsDiv = document.getElementById('symbol-suggestions');
    
    if (symbolsInput && suggestionsDiv) {
        let debounceTimer;
        
        symbolsInput.addEventListener('input', function(e) {
            clearTimeout(debounceTimer);
            const value = e.target.value.trim().toUpperCase();
            
            // Show/hide clear button
            const clearBtn = document.getElementById('symbols-clear');
            if (clearBtn) clearBtn.style.display = e.target.value ? 'block' : 'none';
            
            if (!value || value.includes(',')) {
                suggestionsDiv.style.display = 'none';
                return;
            }
            
            debounceTimer = setTimeout(async () => {
                if (value.includes('.')) {
                    suggestionsDiv.style.display = 'none';
                    return;
                }
                
                suggestionsDiv.innerHTML = '<div style="padding: 10px; color: var(--text-secondary);">Checking exchanges...</div>';
                suggestionsDiv.style.display = 'block';
                
                try {
                    const response = await fetch('https://3oaokynmssanpzz7bwomt7ft6i0qrwhk.lambda-url.us-east-1.on.aws/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ symbol: value })
                    });
                    
                    const data = await response.json();
                    const validSymbols = data.suggestions || [];
                    
                    if (validSymbols.length > 0) {
                        suggestionsDiv.innerHTML = validSymbols.map(s => 
                            `<div style="padding: 10px; cursor: pointer; border-bottom: 1px solid var(--border-color); transition: background 0.2s;" 
                                  onmouseover="this.style.background='rgba(0, 123, 255, 0.25)'" 
                                  onmouseout="this.style.background='transparent'"
                                  onclick="document.getElementById('symbols-input').value='${s.symbol}'; document.getElementById('symbol-suggestions').style.display='none';">
                                <strong>${s.symbol}</strong> - ${s.name}
                            </div>`
                        ).join('');
                    } else {
                        suggestionsDiv.innerHTML = '<div style="padding: 10px; color: var(--text-secondary);">No matches found. Try full symbol (e.g., TLS.AX)</div>';
                    }
                } catch (error) {
                    suggestionsDiv.innerHTML = '<div style="padding: 10px; color: var(--text-secondary);">Error checking symbol</div>';
                }
            }, 500);
        });
        
        document.addEventListener('click', function(e) {
            if (!symbolsInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
                suggestionsDiv.style.display = 'none';
            }
        });
    }
});


// Trading signals symbol suggestions
const signalsInput = document.getElementById('signals-symbols');
const signalsSuggestionsDiv = document.getElementById('signals-symbol-suggestions');

if (signalsInput && signalsSuggestionsDiv) {
    let debounceTimer;
    
    signalsInput.addEventListener('input', function(e) {
        clearTimeout(debounceTimer);
        const value = e.target.value.trim().toUpperCase();
        const lastSymbol = value.split(',').pop().trim();
        
        // Show/hide clear button
        const clearBtn = document.getElementById('signals-clear');
        if (clearBtn) clearBtn.style.display = e.target.value ? 'block' : 'none';
        
        if (!lastSymbol || lastSymbol.includes('.')) {
            signalsSuggestionsDiv.style.display = 'none';
            return;
        }
        
        debounceTimer = setTimeout(async () => {
            signalsSuggestionsDiv.innerHTML = '<div style="padding: 10px; color: var(--text-secondary);">Checking exchanges...</div>';
            signalsSuggestionsDiv.style.display = 'block';
            
            try {
                const response = await fetch('https://3oaokynmssanpzz7bwomt7ft6i0qrwhk.lambda-url.us-east-1.on.aws/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbol: lastSymbol })
                });
                
                const data = await response.json();
                const validSymbols = data.suggestions || [];
                
                if (validSymbols.length > 0) {
                    signalsSuggestionsDiv.innerHTML = validSymbols.map(s => {
                        const prefix = value.substring(0, value.lastIndexOf(',') + 1);
                        const newValue = prefix ? prefix + ' ' + s.symbol : s.symbol;
                        return `<div style="padding: 10px; cursor: pointer; border-bottom: 1px solid var(--border-color); transition: background 0.2s;" 
                              onmouseover="this.style.background='rgba(0, 123, 255, 0.25)'" 
                              onmouseout="this.style.background='transparent'"
                              onclick="document.getElementById('signals-symbols').value='${newValue}'; document.getElementById('signals-symbol-suggestions').style.display='none';">
                            <strong>${s.symbol}</strong> - ${s.name}
                        </div>`;
                    }).join('');
                } else {
                    signalsSuggestionsDiv.innerHTML = '<div style="padding: 10px; color: var(--text-secondary);">No matches found</div>';
                }
            } catch (error) {
                signalsSuggestionsDiv.innerHTML = '<div style="padding: 10px; color: var(--text-secondary);">Error checking symbol</div>';
            }
        }, 500);
    });
    
    document.addEventListener('click', function(e) {
        if (!signalsInput.contains(e.target) && !signalsSuggestionsDiv.contains(e.target)) {
            signalsSuggestionsDiv.style.display = 'none';
        }
    });
}
