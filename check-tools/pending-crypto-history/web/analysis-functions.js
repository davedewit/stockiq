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
        'Rank', 'Symbol', 'Price', 'Score', 'Signal', 'Support', 'Resistance', 'Lower_Level', 'Upper_Level', 'Model_Probability_%', 'Horizon', 'Horizon_Days', 'Timeframe', 'Confidence_%',
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

async function updateRemainingToday() {
    if (jobRunning) {
        console.log('📊 Skipping updateRemainingToday - job running');
        return; // Don't update during job execution
    }
    if (window.location.pathname.includes('signup.html')) {
        return; // Don't show on signup page
    }
    if (typeof authManager !== 'undefined') {
        try {
            console.log('📊 Getting stock analysis status for display update...');
            const status = await authManager.getStockAnalysisStatus();
            console.log('📊 Status received:', status);
            const trialDisplay = document.getElementById('trial-status-display');
            if (trialDisplay) {
                // Get current number
                const currentText = trialDisplay.innerHTML;
                const currentMatch = currentText.match(/(\d+)/);
                const newMatch = status.message.match(/(\d+)/);
                
                if (currentMatch && newMatch) {
                    const currentNum = parseInt(currentMatch[1]);
                    const newNum = parseInt(newMatch[1]);
                    
                    if (currentNum > newNum) {
                        // Animate countdown with visual effects
                        trialDisplay.style.backgroundColor = '#ffeb3b';
                        trialDisplay.style.color = '#000';
                        trialDisplay.style.transform = 'scale(1.2)';
                        trialDisplay.style.transition = 'all 0.3s ease';
                        
                        let current = currentNum;
                        const interval = setInterval(() => {
                            current--;
                            trialDisplay.innerHTML = status.message.replace(/\d+/, current);
                            
                            if (current <= newNum) {
                                clearInterval(interval);
                                setTimeout(() => {
                                    trialDisplay.style.backgroundColor = 'var(--card-bg)';
                                    trialDisplay.style.color = status.unlocked ? '#22c55e' : '#ef4444';
                                    trialDisplay.style.transform = 'scale(1)';
                                }, 800);
                            }
                        }, 400);
                        return;
                    }
                }
                
                // Default update
                trialDisplay.innerHTML = status.message;
                trialDisplay.style.color = status.unlocked ? '#22c55e' : '#ef4444';
            }
            console.log('📊 Updated remaining usage display:', status.message);
        } catch (error) {
            console.warn('Failed to update remaining usage display:', error);
        }
    }
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
                Want <strong style="color: #007bff;">5 Free Reports per day</strong>?<br>
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

function showStickyRegisterButton() {
    const modal = document.getElementById('anonymous-upgrade-modal');
    if (modal) modal.remove();
    localStorage.setItem('showStickyRegister', 'true');
    const stickyBtn = document.createElement('div');
    stickyBtn.id = 'sticky-register-btn';
    stickyBtn.innerHTML = `
        <a href="signup.html" style="position: fixed; bottom: 20px; right: 20px; background: #007bff; color: white; padding: 16px 28px; border-radius: 50px; text-decoration: none; font-weight: 600; font-size: 1rem; box-shadow: 0 4px 12px rgba(0,123,255,0.4); z-index: 9999; display: flex; align-items: center; gap: 8px; transition: all 0.3s;" onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 6px 16px rgba(0,123,255,0.5)'" onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 12px rgba(0,123,255,0.4)'">
            🚀 Start 3-Day Free Trial
        </a>
    `;
    document.body.appendChild(stickyBtn);
}

function showStickyUpgradeButton() {
    if (document.getElementById('sticky-upgrade-btn')) return;
    const stickyBtn = document.createElement('div');
    stickyBtn.id = 'sticky-upgrade-btn';
    stickyBtn.innerHTML = `
        <a href="dashboard.html?redirect=upgrade" style="position: fixed; bottom: 20px; right: 20px; background: #007bff; color: white; padding: 16px 28px; border-radius: 50px; text-decoration: none; font-weight: 600; font-size: 1rem; box-shadow: 0 4px 12px rgba(0,123,255,0.4); z-index: 9999; display: flex; align-items: center; gap: 8px; transition: all 0.3s;" onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 6px 16px rgba(0,123,255,0.5)'" onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 12px rgba(0,123,255,0.4)'">
            🚀 Upgrade Plan
        </a>
    `;
    document.body.appendChild(stickyBtn);
}

// Show sticky button on page load for users who need to upgrade
setTimeout(async () => {
    const userId = localStorage.getItem('userId');
    const showSticky = localStorage.getItem('showStickyRegister');
    
    // Check if anonymous user
    if (!userId || userId === 'anonymous') {
        let shouldShow = showSticky === 'true';
        
        // Also check actual usage status from authManager
        if (typeof authManager !== 'undefined') {
            try {
                const status = await authManager.getStockAnalysisStatus();
                // If they have 0 remaining, show the button
                if (status && !status.unlocked) {
                    shouldShow = true;
                    localStorage.setItem('showStickyRegister', 'true');
                }
            } catch (e) {}
        }
        
        if (shouldShow && !document.getElementById('sticky-register-btn')) {
            const stickyBtn = document.createElement('div');
            stickyBtn.id = 'sticky-register-btn';
            stickyBtn.innerHTML = `
                <a href="signup.html" style="position: fixed; bottom: 20px; right: 20px; background: #007bff; color: white; padding: 16px 28px; border-radius: 50px; text-decoration: none; font-weight: 600; font-size: 1rem; box-shadow: 0 4px 12px rgba(0,123,255,0.4); z-index: 9999; display: flex; align-items: center; gap: 8px; transition: all 0.3s;" onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 6px 16px rgba(0,123,255,0.5)'" onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 12px rgba(0,123,255,0.4)'">
                    🚀 Start 3-Day Free Trial
                </a>
            `;
            document.body.appendChild(stickyBtn);
        }
    } else if (userId && typeof authManager !== 'undefined') {
        // Check if registered free user has 0 remaining
        try {
            const status = await authManager.getStockAnalysisStatus();
            if (status && !status.unlocked) {
                showStickyUpgradeButton();
            } else {
                // Remove button if they have analyses available
                const existingBtn = document.getElementById('sticky-upgrade-btn');
                if (existingBtn) existingBtn.remove();
            }
        } catch (e) {}
    }
}, 1000);

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
    
    // Display trial status immediately (hide on signup page)
    if (typeof authManager !== 'undefined' && !window.location.pathname.includes('signup.html')) {
        const status = await authManager.getStockAnalysisStatus();
        let trialDisplay = document.getElementById('trial-status-display');
        if (!trialDisplay) {
            trialDisplay = document.createElement('div');
            trialDisplay.id = 'trial-status-display';
            document.body.appendChild(trialDisplay);
        }
        const isMobile = window.innerWidth <= 768;
        const userId = localStorage.getItem('userId') || 'anonymous';
        const cacheKey = `userPaidStatus_${userId}`;
        const isPaid = localStorage.getItem(cacheKey) === 'paid';
        const topPos = isMobile ? '70px' : (isPaid ? '60px' : '105px');
        trialDisplay.innerHTML = status.message;
        trialDisplay.style.cssText = `position: fixed; top: ${topPos}; right: 20px; background: var(--card-bg); border-radius: 6px; padding: 4px 8px; font-size: 0.85rem; z-index: 1000; box-shadow: 0 2px 10px rgba(0,0,0,0.3); opacity: 1;`;
        trialDisplay.style.color = status.unlocked ? '#22c55e' : '#ef4444';
        setTimeout(() => { if (trialDisplay) trialDisplay.style.opacity = '0.7'; }, 3000);
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
            const trialDisplay = document.getElementById('trial-status-display');
            if (currentScroll > lastScroll && currentScroll > 100) {
                nav.style.transform = 'translateY(-100%)';
                if (trialDisplay) trialDisplay.style.top = '10px';
            } else {
                nav.style.transform = 'translateY(0)';
                if (trialDisplay) trialDisplay.style.top = '70px';
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
        
        // Update display after increment with a small delay
        if (typeof authManager !== 'undefined') {
            setTimeout(async () => {
                const status = await authManager.getStockAnalysisStatus(true);
                const trialDisplay = document.getElementById('trial-status-display');
                if (trialDisplay) {
                    // Brief highlight animation to show change
                    trialDisplay.style.backgroundColor = '#ffeb3b';
                    trialDisplay.style.color = '#000';
                    trialDisplay.style.transform = 'scale(1.1)';
                    trialDisplay.style.transition = 'all 0.3s ease';
                    
                    setTimeout(() => {
                        trialDisplay.innerHTML = status.message;
                        trialDisplay.style.backgroundColor = 'var(--card-bg)';
                        trialDisplay.style.color = status.unlocked ? '#22c55e' : '#ef4444';
                        trialDisplay.style.transform = 'scale(1)';
                    }, 1200);
                }
            }, 500);
        }
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
            
            // Update display after increment with a small delay
            if (typeof authManager !== 'undefined') {
                setTimeout(async () => {
                    const status = await authManager.getStockAnalysisStatus(true);
                    const trialDisplay = document.getElementById('trial-status-display');
                    if (trialDisplay) {
                        // Brief highlight animation to show change
                        trialDisplay.style.backgroundColor = '#ffeb3b';
                        trialDisplay.style.color = '#000';
                        trialDisplay.style.transform = 'scale(1.1)';
                        trialDisplay.style.transition = 'all 0.3s ease';
                        
                        setTimeout(() => {
                            trialDisplay.innerHTML = status.message;
                            trialDisplay.style.backgroundColor = 'var(--card-bg)';
                            trialDisplay.style.color = status.unlocked ? '#22c55e' : '#ef4444';
                            trialDisplay.style.transform = 'scale(1)';
                        }, 1200);
                    }
                }, 500);
            }
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
            
            // Update display after increment with a small delay
            if (typeof authManager !== 'undefined') {
                setTimeout(async () => {
                    const status = await authManager.getStockAnalysisStatus(true);
                    const trialDisplay = document.getElementById('trial-status-display');
                    if (trialDisplay) {
                        // Brief highlight animation to show change
                        trialDisplay.style.backgroundColor = '#ffeb3b';
                        trialDisplay.style.color = '#000';
                        trialDisplay.style.transform = 'scale(1.1)';
                        trialDisplay.style.transition = 'all 0.3s ease';
                        
                        setTimeout(() => {
                            trialDisplay.innerHTML = status.message;
                            trialDisplay.style.backgroundColor = 'var(--card-bg)';
                            trialDisplay.style.color = status.unlocked ? '#22c55e' : '#ef4444';
                            trialDisplay.style.transform = 'scale(1)';
                        }, 1200);
                    }
                }, 500);
            }
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
        } else if (option === 3 && subOption === '3') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 3.3 SMART SCALING - S&P 500 Complete Stock Screener');
            const sp500Universe = ['MMM','AOS','ABT','ABBV','ACN','ADBE','AMD','AES','AFL','A','APD','ABNB','AKAM','ALB','ARE','ALGN','ALLE','LNT','ALL','GOOGL','GOOG','MO','AMZN','AMCR','AEE','AEP','AXP','AIG','AMT','AWK','AMP','AME','AMGN','APH','ADI','AON','APA','APO','AAPL','AMAT','APP','APTV','ACGL','ADM','ARES','ANET','AJG','AIZ','T','ATO','ADSK','ADP','AZO','AVY','AXON','BKR','BALL','BAC','BAX','BDX','BRK-B','BBY','TECH','BIIB','BLK','BX','XYZ','BE','BNY','BA','BKNG','BSX','BMY','AVGO','BR','BRO','BF-B','BG','BXP','CHRW','CDNS','CPT','COF','CAH','CCL','CARR','CVNA','CASY','CAT','CBOE','CBRE','CDW','COR','CNC','CNP','CF','CRL','SCHW','CHTR','CVX','CMG','CB','CHD','CIEN','CI','CINF','CTAS','CSCO','C','CFG','CLX','CME','CMS','KO','CTSH','COHR','COIN','CL','CMCSA','FIX','COP','ED','STZ','CEG','COO','CPRT','GLW','CPAY','CSGP','COST','CRH','CRWD','CCI','CSX','CMI','CVS','DHR','DRI','DDOG','DVA','DECK','DE','DELL','DAL','DVN','DXCM','FANG','DLR','DG','DLTR','D','DPZ','DASH','DOV','DOW','DHI','DTE','DUK','DD','ETN','EBAY','ECHO','ECL','EIX','EW','ELV','EME','EMR','ETR','EOG','EQT','EFX','EQIX','ERIE','ESS','EL','EG','EVRG','P','ES','EXC','EXE','EXPE','EXPD','EXR','XOM','FFIV','FDS','FICO','FAST','FRT','FDX','FDXF','FERG','FIS','FITB','FSLR','FE','FISV','FLEX','F','FTNT','FTV','FOXA','FOX','BEN','FCX','GRMN','IT','GE','GEHC','GEV','GEN','GNRC','GD','GIS','GM','GPC','GILD','GPN','GL','GDDY','GS','HAL','HIG','HAS','HCA','DOC','HSIC','HSY','HPE','HLT','HD','HONA','HON','HRL','HST','HWM','HPQ','HUBB','HUM','HBAN','HII','IBM','IEX','IDXX','ITW','ILMN','INCY','IR','PODD','INTC','IBKR','ICE','IFF','IP','INTU','ISRG','IVZ','INVH','IQV','IRM','JBHT','JBL','JKHY','J','JNJ','JCI','JPM','KVUE','KDP','KEY','KEYS','KMB','KIM','KMI','KKR','KLAC','KHC','KR','LHX','LH','LRCX','LVS','LDOS','LEN','LII','LLY','LIN','LYV','LMT','L','LOW','LULU','LITE','LYB','MTB','MPC','MAR','MRSH','MLM','MRVL','MAS','MA','MKC','MCD','MCK','MDT','MRK','META','MET','MTD','MGM','MCHP','MU','MSFT','MAA','MRNA','MDLZ','MPWR','MNST','MCO','MS','MOS','MSI','MSCI','NDAQ','NTAP','NFLX','NEM','NWSA','NWS','NEE','NKE','NI','NDSN','NSC','NTRS','NOC','NCLH','NRG','NUE','NVDA','NVR','NXPI','ORLY','OXY','ODFL','OMC','ON','OKE','ORCL','OTIS','PCAR','PKG','PLTR','PANW','PH','PAYX','PYPL','PNR','PEP','PFE','PCG','PM','PSX','PNW','PNC','PPG','PPL','PFG','PG','PGR','PLD','PRU','PEG','PTC','PSA','PHM','PWR','QCOM','DGX','Q','RL','RJF','RDDT','RTX','O','REG','REGN','RF','RSG','RMD','RVTY','HOOD','ROK','ROL','ROP','ROST','RCL','SPGI','CRM','SNDK','SBAC','SLB','STX','SRE','NOW','SHW','SPG','SKYD','SWKS','SJM','SW','SNA','SOLV','SO','LUV','SWK','SBUX','STT','STLD','STE','SYK','SMCI','SYF','SNPS','SYY','TMUS','TROW','TTWO','TPR','TRGP','TGT','TEL','TDY','TER','TSLA','TXN','TPL','TXT','TMO','TJX','TKO','TSCO','TT','TDG','TRV','TRMB','TFC','TWLO','TYL','TSN','USB','UBER','UDR','ULTA','UNP','UAL','UPS','URI','UNH','UHS','VLO','VEEV','VTR','VLTO','VRSN','VRSK','VZ','VRTX','VRT','VTRS','VICI','V','VST','VMRK','VMC','WRB','GWW','WAB','WMT','DIS','WM','WAT','WEC','WFC','WELL','WST','WDC','WY','WSM','WMB','WTW','WDAY','WYNN','XEL','XYL','YUM','ZBRA','ZBH','ZTS'];
            const allWorkerUrls = [
  'https://sumuq55x4kzehluvsbjllokgt40sqziy.lambda-url.us-east-1.on.aws/',
  'https://4kxcesof3axkxjwxr7ppvxaufy0wxerx.lambda-url.us-east-1.on.aws/',
  'https://qdtaabefjq2uaxt7eolajnrpkq0cyjhp.lambda-url.us-east-1.on.aws/',
  'https://rnkpysopxjipqtwavfjox5gqji0fgkke.lambda-url.us-east-1.on.aws/',
  'https://okmwdoc56yby4ictlmccqlbji40jgrvt.lambda-url.us-east-1.on.aws/',
  'https://wtasa3lx3ui4o7p45ialc4jdwy0gubly.lambda-url.us-east-1.on.aws/',
  'https://tpsdzbraynuj2xugqwueofxxlq0dswgm.lambda-url.us-east-1.on.aws/',
  'https://mld3e7rdgljjoearp37f2rh4gq0jtdjd.lambda-url.us-east-1.on.aws/',
  'https://tv3puew6c5hn35lvdx4tiyhsbu0lalgg.lambda-url.us-east-1.on.aws/',
  'https://7yadzqcqosh6yptpoq4mw33uji0zzhaw.lambda-url.us-east-1.on.aws/',
  'https://ng5nhwpsdvaw32oljuoqwmyupe0gpuns.lambda-url.us-east-1.on.aws/',
  'https://fryd75bfv3vhpl4y7wk5axwkla0gdbmq.lambda-url.us-east-1.on.aws/',
  'https://y4udgwckvq5g4cyp4wuel72qn40bxaqn.lambda-url.us-east-1.on.aws/',
  'https://vun2rgrkvulfkp6bgpfgwre36m0majwy.lambda-url.us-east-1.on.aws/',
  'https://knwl34plyohgwqv654qaghtdiy0xxtfl.lambda-url.us-east-1.on.aws/',
  'https://j57tzdb336qy4rvn5ccqkjgxfy0whzkg.lambda-url.us-east-1.on.aws/',
  'https://lcydaogtuez3fakjbhzpvfqtuy0loywk.lambda-url.us-east-1.on.aws/',
  'https://2sep5fjrlbtyclb45hglcmxhay0uacnj.lambda-url.us-east-1.on.aws/',
  'https://brbz4bzc32kpiwy4fq3cvu4bzq0tvtob.lambda-url.us-east-1.on.aws/',
  'https://pilagfzilbgluzuvm35onlibm40makmv.lambda-url.us-east-1.on.aws/',
  'https://wisfookpyzku2ydy2dg2hk6hva0wfkag.lambda-url.us-east-1.on.aws/',
  'https://bkdbv3s2ld7saduhbi4yvzhrki0vgout.lambda-url.us-east-1.on.aws/',
  'https://6y6nufkvvp23chbr52fhmb5xoi0bgoej.lambda-url.us-east-1.on.aws/',
  'https://rkekhafr4cfw2vipdvnaktscqi0qxnze.lambda-url.us-east-1.on.aws/',
  'https://cqtjlp3eq6ndkor4tpdgos234m0qjwqo.lambda-url.us-east-1.on.aws/',
  'https://np2ybzlvwdtlozeyiz6k7eybdu0dcutk.lambda-url.us-east-1.on.aws/',
  'https://swoztkmizkdrgo6kwqnubx7zqy0axqne.lambda-url.us-east-1.on.aws/',
  'https://bruu4ufxhynlqtnbhczv3mdxpq0ckkvm.lambda-url.us-east-1.on.aws/',
  'https://wxgjriaxwe3zwpx7qwfyfbbizi0srlvr.lambda-url.us-east-1.on.aws/',
  'https://2fyrvclcxmg5xjaga35pr76vhm0lyqws.lambda-url.us-east-1.on.aws/',
  'https://b4ymcbihbumuu4vjcj3skunug40zhjtd.lambda-url.us-east-1.on.aws/',
  'https://izqjvti6fv4nudhyopaeiksku40drdtu.lambda-url.us-east-1.on.aws/',
  'https://bhguocquvafpnheauoup7ylzba0kbfov.lambda-url.us-east-1.on.aws/',
  'https://cyc67g4bqes5fgcnglkevk4ytm0ntesv.lambda-url.us-east-1.on.aws/',
  'https://edyuklsnhlosrxr6fmotkfkoi40yzdut.lambda-url.us-east-1.on.aws/',
  'https://uylcsrvc2jrfvavusaww3d2iui0haprp.lambda-url.us-east-1.on.aws/',
  'https://eia6ugy35abq74qkzh4tea5mfy0uzqlg.lambda-url.us-east-1.on.aws/',
  'https://6jpb4qa76l3t6tg4atl42wjqdi0sahyo.lambda-url.us-east-1.on.aws/',
  'https://bscu2mkvp7sabovzpa66g7jhiu0waakd.lambda-url.us-east-1.on.aws/',
  'https://auyg6ifl2okkforyps6akdl2nu0cdtpx.lambda-url.us-east-1.on.aws/',
  'https://krfqvkj2xot3yweyhcbarrwwfy0pdiap.lambda-url.us-east-1.on.aws/',
  'https://edfmppbagwitqpcelejfyqoski0yanmx.lambda-url.us-east-1.on.aws/',
  'https://mc6mev6tq56fqfvmdkkhxidb6e0ujymq.lambda-url.us-east-1.on.aws/',
  'https://gpardfscnzctwj2lau5cltp3nm0grpro.lambda-url.us-east-1.on.aws/',
  'https://bej54is7mwvzh33rc7nc2cloim0yhztv.lambda-url.us-east-1.on.aws/',
  'https://ar6uiuqa6itnfh7zk4eu6j2klq0yqblj.lambda-url.us-east-1.on.aws/',
  'https://lsqk6sqqdhychyajeeqrnj2tiu0ydnde.lambda-url.us-east-1.on.aws/',
  'https://xogt75owsex4uksgrltxgfr4sq0dyhss.lambda-url.us-east-1.on.aws/',
  'https://tftb664a3u34ilzny2hjrdp4jm0gpkcr.lambda-url.us-east-1.on.aws/',
  'https://ujx3d42fokwn3m2gno3sknrhp40itbij.lambda-url.us-east-1.on.aws/',
  'https://i6tfywm4gk4sxjloimv42hfrvq0ktcxt.lambda-url.us-east-1.on.aws/',
  'https://rau7mjwzjxaisfubfuxxfceyoy0rynwu.lambda-url.us-east-1.on.aws/',
  'https://jyuidstmkxpffknys3mjztpcsu0dydil.lambda-url.us-east-1.on.aws/',
  'https://owtnqz25cmftlt26mcgskjmrxi0fqvur.lambda-url.us-east-1.on.aws/',
  'https://kv3ep67fwnct7ftlo2j6qahz7i0njgnn.lambda-url.us-east-1.on.aws/',
  'https://p7ztcr2nqnbq7alysq4hdrjy7y0yjkyy.lambda-url.us-east-1.on.aws/',
  'https://uycmsfifmuih2aylrzguejfkre0ysluv.lambda-url.us-east-1.on.aws/',
  'https://22gzanhpgv7ljpbjogjhjjuxae0fcvvd.lambda-url.us-east-1.on.aws/',
  'https://6i2qyx4bmyu5v7nbwti56z5smq0kotnw.lambda-url.us-east-1.on.aws/',
  'https://s7u7jjytf22fqewdwaruw63xfi0opcrl.lambda-url.us-east-1.on.aws/',
  'https://2zaepuzdli5yyt3plivfr5mohy0bpvbz.lambda-url.us-east-1.on.aws/',
  'https://fv3uhmwhq562psoimkknhcupum0lafed.lambda-url.us-east-1.on.aws/',
  'https://vyieo7w4xkwldyyzibkosc3u3q0jring.lambda-url.us-east-1.on.aws/',
  'https://ndb3d6hx2lfy5h6ax3mo2olsse0bhfyl.lambda-url.us-east-1.on.aws/',
  'https://qt3dmjxqemixgh5twtdz556aoy0nxjwx.lambda-url.us-east-1.on.aws/',
  'https://ujcf6bivxmdvqlm36epvwclsxi0huktt.lambda-url.us-east-1.on.aws/',
  'https://eu5lczeod5fl73novqodrakdbi0qmcnq.lambda-url.us-east-1.on.aws/',
  'https://w5fvhnyhv3fhy7cndz5vdoydaq0szcwy.lambda-url.us-east-1.on.aws/',
  'https://dx753fhtfdpjihebd74xfyr34i0exlro.lambda-url.us-east-1.on.aws/',
  'https://ziunjxonxlign2zesbutq3pe6y0itpqr.lambda-url.us-east-1.on.aws/',
  'https://tyg7zmtcj7fv6vh6kbzdd2gozm0ntpck.lambda-url.us-east-1.on.aws/',
  'https://eheedmye3mtc2eneyymzxjrqma0frdqm.lambda-url.us-east-1.on.aws/',
  'https://bvkwdkexywwtluj7yz3j4bu4qy0jytnf.lambda-url.us-east-1.on.aws/',
  'https://ql7rwn4pvfaek2thm7kuoyjt6a0boxur.lambda-url.us-east-1.on.aws/',
  'https://uoryr63elb67f23qienmafrc2m0shzvp.lambda-url.us-east-1.on.aws/',
  'https://rxszrydv4gwne3bhrmliccwxny0qpoxe.lambda-url.us-east-1.on.aws/',
  'https://mil2hqrdriytpibnihqj2qntd40oiuqh.lambda-url.us-east-1.on.aws/',
  'https://rtlhpfpk3hx7edhdibx3lh5ykq0crvlh.lambda-url.us-east-1.on.aws/',
  'https://3m7ck5hzvbfqtgenqkutw3yv4q0vujyz.lambda-url.us-east-1.on.aws/',
  'https://mspa4fvbo6gr65g2j3ldjznnyi0jzzpm.lambda-url.us-east-1.on.aws/',
  'https://wxheo4k3evo4ex6xjofjaxf4eu0pjjcl.lambda-url.us-east-1.on.aws/',
  'https://kuxwn7tpbzxf6iulac4trmr6ka0jghfp.lambda-url.us-east-1.on.aws/',
  'https://tg5f6xt7g5iiz7vlueoa64cuxm0jviom.lambda-url.us-east-1.on.aws/',
  'https://t27b657p7vrtwxhnhrzpijauvy0wxvjt.lambda-url.us-east-1.on.aws/',
  'https://v5vcaxrdncm3vlyepecabcucky0iermr.lambda-url.us-east-1.on.aws/',
  'https://m52jy7arfz4ah6ywf4cvbft3ha0lebpo.lambda-url.us-east-1.on.aws/',
  'https://t24gezyz2mp5rhz466b2o47gb40btvhs.lambda-url.us-east-1.on.aws/',
  'https://ouzc2jyjxhp2nhmqtmtczdlmre0dedam.lambda-url.us-east-1.on.aws/',
  'https://zmi7ubxjxmbyaulge62ispypai0zcrsm.lambda-url.us-east-1.on.aws/',
  'https://xj3wt6vqdxiq4nezy4oo4nr72e0simpn.lambda-url.us-east-1.on.aws/',
  'https://tbgrkvqniwriv5h4rq37dmp2me0wfksg.lambda-url.us-east-1.on.aws/',
  'https://vyu6fwryqf3z54sw7jjunrdz2i0ezrsr.lambda-url.us-east-1.on.aws/',
  'https://dloq6dsorbklhfvos7alx5qoma0cjajy.lambda-url.us-east-1.on.aws/',
  'https://xavyejicavl4dkynlpwzw4nxuq0hfqho.lambda-url.us-east-1.on.aws/',
  'https://pj244ufrc76skxopfffwejpyem0gwdzn.lambda-url.us-east-1.on.aws/',
  'https://s5btea5ckuzo7n2mwc4zlbcoou0epfiu.lambda-url.us-east-1.on.aws/',
  'https://xhxplwpnpwy23dh3kdyeitilca0nbmse.lambda-url.us-east-1.on.aws/',
  'https://3p65jslba6kc67m224wtdkgtke0wcnxj.lambda-url.us-east-1.on.aws/',
  'https://czidgeo5bjycsea5idb2jzpeoq0rqcia.lambda-url.us-east-1.on.aws/',
  'https://ciqq2tj2vumroy23y2qaqbqc2i0owyfe.lambda-url.us-east-1.on.aws/',
];
            console.log('🧠 Dynamic allocation: 500 base stocks → 50 workers × 10 stocks each');
            console.log('📊 Processing 500 stocks (50 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 50 workers for 500 S&P 500 stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 50; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(sp500Universe.length / (50)));
                const startIdx = i * perWorker;
                const stockBatch = sp500Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 50/50 workers for 500 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.batch_size} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 50 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 S&P 500 Complete Analysis: ${allResults.length}/500 stocks (${((allResults.length/500)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 500, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'SP500_Complete_Screener');
            result = formatOption3Result(apiData, '3');
            result.csvData = csvData;
        } else if (option === 3 && subOption === '2') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 3.2 SMART SCALING - S&P 400+600 (Mid+SmallCap) Stock Screener');
            const sp400_600Universe = ['AA','AAL','AAON','ACI','ACM','ADC','AEIS','AFG','AGCO','AGNC','AHR','AIT','ALGM','ALK','ALLY','ALSN','ALV','AM','AMG','AMH','AMKR','AN','ANF','APG','APPF','AR','ARMK','ARW','ARWR','ASB','ASH','ATI','ATR','AVAV','AVNT','AVT','AVTR','AXTA','AYI','BAH','BBWI','BC','BCO','BDC','BHF','BILL','BIO','BJ','BKH','BMRN','BRKR','BROS','BRX','BSY','BTSG','BURL','BWA','BWXT','BYD','CACI','CAR','CART','CAVA','CBSH','CBT','CCK','CDE','CDP','CELH','CFR','CG','CGNX','CHDN','CHE','CHH','CHRD','CHWY','CLF','CLH','CMC','CNH','CNM','CNO','CNX','COKE','COLB','COLM','CORT','CR','CRBG','CROX','CRS','CRUS','CSL','CTRE','CTVA','CUBE','CUZ','CVLT','CW','CXT','CYTK','DAR','DBX','DCI','DINO','DKS','DLB','DOCN','DOCS','DOCU','DT','DTM','DUOL','DY','EAT','EEFT','EGP','EHC','ELAN','ELF','ELS','ENS','ENSG','ENTG','EPR','EQH','ESAB','ESNT','EVR','EWBC','EXEL','EXLS','EXP','EXPO','FAF','FBIN','FCFS','FCN','FFIN','FHI','FHN','FIVE','FLG','FLR','FLS','FN','FNB','FND','FNF','FORM','FOUR','FR','FTI','G','GAP','GATX','GBCI','GEF','GGG','GHC','GLPI','GME','GMED','GNTX','GPK','GWRE','GXO','H','HAE','HALO','HGV','HIMS','HL','HLI','HLNE','HOG','HOMB','HQY','HR','HRB','HUBS','HWC','HXL','IBOC','IDA','IDCC','IESC','INGR','IPGP','IRT','ITT','JAZZ','JEF','JLL','KBH','KBR','KD','KEX','KNF','KNSL','KNX','KRC','KRG','KRYS','KTOS','LAD','LAMR','LEA','LECO','LFUS','LIVN','LNTH','LOPE','LPX','LSCC','LSTR','M','MANH','MAT','MEDP','MIDD','MKSI','MLI','MMS','MOG-A','MOH','MORN','MP','MSA','MSM','MTDR','MTG','MTN','MTSI','MTZ','MUR','MUSA','MZTI','NBIX','NEU','NFG','NJR','NLY','NNN','NOV','NOVT','NTNX','NVST','NVT','NWE','NXST','NXT','NYT','OC','OGE','OGS','OHI','OKTA','OLED','OLLI','ONB','ONTO','OPCH','ORA','ORI','OSK','OVV','OZK','PAG','PATH','PB','PBF','PCTY','PEGA','PEN','PFGC','PII','PINS','PK','PLNT','PNFP','POR','POST','PPC','PR','PRI','PSN','PVH','QLYS','R','RBA','RBC','REXR','RGA','RGEN','RGLD','RH','RLI','RMBS','RNR','ROIV','ROKU','RPM','RRC','RRX','RS','RYAN','RYN','SAIA','SAIC','SANM','SARO','SBRA','SCI','SEIC','SF','SFM','SGI','SHC','SIGI','SIRI','SITM','SLAB','SLGN','SLM','SMG','SMTC','SN','SNX','SOLS','SON','SPXC','SR','SSB','SSD','ST','STAG','STRL','STWD','SUI','SWX','SYNA','TCBI','TEX','THC','THG','THO','TKR','TLN','TNL','TOL','TOST','TREX','TRU','TTC','TTEK','TTMI','TXNM','TXRH','UBSI','UFPI','UGI','ULS','UMBF','UNM','USFD','UTHR','VAL','VC','VFC','VIAV','VICR','VLY','VMI','VNO','VNOM','VNT','VOYA','VVV','WAL','WCC','WEX','WFRD','WH','WHR','WING','WLK','WMG','WMS','WPC','WSO','WTFC','WTRG','WTS','WWD','XPO','XRAY','YETI','ZION','AAMI','AAP','AAT','ABCB','ABG','ABM','ABR','ACA','ACAD','ACHC','ACIW','ACLS','ACMR','ACT','ADAM','ADEA','ADIG','ADMA','ADNT','ADT','ADUS','AEO','AESI','AGNT','AGO','AGX','AGYS','AHCO','AIN','AIR','AKR','ALG','ALGT','ALHC','ALKS','ALRM','AMN','AMPH','AMR','AMRX','AMSF','AMTM','ANDE','ANIP','AORT','AOSL','APAM','APLE','APOG','ARCB','ARLO','AROC','ARR','ASO','ASTE','ASTH','ATEN','ATMU','AUB','AVA','AWI','AWR','AX','AZTA','AZZ','BANC','BANF','BANR','BBT','BCC','BCPC','BFAM','BFH','BFS','BGC','BHE','BJRI','BKE','BKU','BL','BLKB','BMI','BNL','BOH','BOOT','BOX','BRC','BTU','BXMT','CACC','CAG','CAKE','CALM','CALX','CALY','CARG','CASH','CATY','CBRL','CBU','CC','CCOI','CCS','CE','CENT','CENTA','CENX','CERT','CFFN','CHCO','CHEF','CLSK','CNK','CNMD','CNR','CNS','CNXC','CNXN','COCO','COHU','COLL','CON','COTY','CPB','CPF','CPK','CRC','CRGY','CRI','CRK','CRSR','CRVL','CSR','CSW','CTS','CUBI','CURB','CVBF','CVCO','CVI','CVSA','CWEN','CWK','CWST','CWT','CXM','CXW','CZR','DAN','DAVE','DBD','DCH','DCOM','DEA','DEI','DFH','DFIN','DGII','DIOD','DLX','DMC','DNOW','DORM','DRH','DV','DXC','DXPE','EBC','ECG','ECPG','EFC','EFOR','EGBN','EIG','EMN','ENOV','ENPH','ENR','ENVA','EPAC','EPAM','EPC','EPRT','ESE','ESI','ETSY','EVTC','EXTR','EYE','EZPW','FA','FBK','FBNC','FBP','FBRT','FCF','FCPT','FELE','FFBC','FG','FHB','FIBK','FIVN','FIZZ','FLO','FMC','FOXF','FRPT','FSS','FTDR','FTRE','FUL','FULT','FUN','GBX','GEO','GFF','GIII','GKOS','GNL','GNW','GO','GOLF','GPI','GPOR','GRBK','GSHD','GT','GTES','GTM','GTY','GVA','HAFC','HASI','HAYW','HCC','HCI','HCSG','HE','HFWA','HIW','HLIT','HMN','HNI','HOPE','HP','HRMY','HSTM','HTH','HTLD','HTO','HUBG','HWKN','HZO','IART','IBP','ICHR','ICUI','IIPR','INDB','INDV','INSP','INSW','INVA','INVX','IOSP','IPAR','IRDM','ITGR','ITRI','IVT','JBGS','JBLU','JBSS','JBTM','JJSF','JOE','JXN','KAI','KALU','KFY','KGS','KLIC','KMPR','KMT','KMX','KN','KNTK','KOP','KRMN','KSS','KTB','KWR','LAUR','LAZ','LBRT','LCII','LEU','LFST','LGIH','LIF','LGND','LKFN','LKQ','LMAT','LNC','LNN','LPG','LQDA','LQDT','LRN','LTC','LTH','LUMN','LW','LXP','LYFT','LZ','LZB','MAC','MAN','MARA','MATW','MATX','MBC','MBGL','MBIN','MC','MCRI','MCY','MD','MDU','MFP','MGEE','MGY','MHK','MHO','MIR','MKTX','MLKN','MMI','MMSI','MPT','MRCY','MRP','MRTN','MSEX','MSGS','MTCH','MTH','MTRN','MTUS','MTX','MWA','MXL','MYRG','NABL','NATL','NAVI','NBHC','NBTB','NE','NEO','NEOG','NGVT','NHC','NHI','NIC','NMIH','NOG','NPK','NPO','NSIT','NSP','NSSC','NTCT','NTST','NWBI','NWL','NWN','NX','NXRT','OFG','OGN','OI','OII','OMCL','OPLN','OSIS','OSW','OTTR','OUT','PAHC','PARR','PAYC','PAYO','PATK','PBH','PBI','PCRX','PDFS','PEB','PECO','PENG','PENN','PFBC','PFS','PGNY','PHIN','PI','PIPR','PJT','PLAB','PLMR','PLUS','PLXS','PMT','POOL','POWI','POWL','PPLI','PRDO','PRG','PRGO','PRGS','PRIM','PRK','PRKS','PRLB','PRSU','PRVA','PSMT','PTCT','PTEN','PTGX','PTON','PZZA','QDEL','QNST','QTWO','RAMP','RAL','RCUS','RDN','RDNT','RELY','RES','REYN','REX','REZI','RHI','RHP','RITM','RNG','RNST','ROAD','ROCK','ROG','RRR','RSI','RUN','RUSHA','RXO','SAFE','SABR','SAFT','SAH','SBCF','SBH','SBSI','SCHL','SCL','SCSC','SDGR','SEDG','SEI','SEZL','SFBS','SFNC','SHAK','SHEN','SHO','SHOO','SIG','SKT','SKY','SKYW','SLG','SLVM','SM','SMP','SMPL','SNDR','SNEX','SONO','SPHR','SPNT','SPSC','SRPT','STAA','STBA','STC','STEP','STRA','SUPN','SXI','SXT','TALO','TBBK','TDC','TDS','TDW','TFIN','TFX','TGTX','THRM','TILE','TMDX','TMP','TNC','TNDM','TPC','TR','TRIP','TRMK','TRN','TRNO','TRST','TRUP','UA','UAA','UCB','UCTT','UE','UFCS','UFPT','UNF','UNFI','UNIT','UPBD','UPWK','URBN','USLM','USPH','UTI','UTL','UVV','VAC','VCEL','VCTR','VCYT','VECO','VGNT','VIR','VIRT','VRRM','VRTS','VSAT','VSEC','VSH','VSNT','VSTS','VSXY','VTOL','VVX','VYX','WABC','WAFD','WAY','WD','WDFC','WEN','WERN','WGO','WHD','WINA','WKC','WLY','WOR','WRBY','WRLD','WS','WSBC','WSC','WSFS','WT','WU','WWW','XHR','XNCR','XPEL','YELP','YOU','ZD','ZWS'];
            const allWorkerUrls = [
                'https://z2uvmjn3atygvi3q4lzeavjn2u0kafxs.lambda-url.us-east-1.on.aws/',
                'https://rvhpejzgjfnhnsrgkf67d4cdem0tuprx.lambda-url.us-east-1.on.aws/',
                'https://nvt3fsj6w7jqt3w7eta6cdvd3a0jgunp.lambda-url.us-east-1.on.aws/',
                'https://pmnvy5np7rxsa6iy4kablleysm0zebkn.lambda-url.us-east-1.on.aws/',
                'https://z6v74ptw3ygwyzgz3mdbwvndyq0zwzpz.lambda-url.us-east-1.on.aws/',
                'https://oakylw54tibnnyuebcg2v6htfm0urgob.lambda-url.us-east-1.on.aws/',
                'https://jdsb672fhg52t6cog4ayya7mwq0vsygm.lambda-url.us-east-1.on.aws/',
                'https://ftou3qvsl74sjjwyybhghzieum0yrojo.lambda-url.us-east-1.on.aws/',
                'https://26xvk6gleal2i7r4zukr6eeiqy0kksqj.lambda-url.us-east-1.on.aws/',
                'https://3wc2xgg2xmuizs7anh3kchngyu0ljtkt.lambda-url.us-east-1.on.aws/',
                'https://cnzqyg6ql2mtgagdrrweji3wc40ftqkx.lambda-url.us-east-1.on.aws/',
                'https://2efokdsjzbkp66n27lvmpqjslq0zfoei.lambda-url.us-east-1.on.aws/',
                'https://2sneyqqfilfygin5dqr5hlduhu0zmakl.lambda-url.us-east-1.on.aws/',
                'https://4ki6pxopyheronpvij7glyqb4y0hkeuc.lambda-url.us-east-1.on.aws/',
                'https://kfls7jxvqusucgy6i7ysblrebi0dnagf.lambda-url.us-east-1.on.aws/',
                'https://iucm2ec36y27hvk2kib4ailc2e0fmkls.lambda-url.us-east-1.on.aws/',
                'https://uo3xljx6iux6qtc6wiwvazqgzi0pgnnh.lambda-url.us-east-1.on.aws/',
                'https://uypvmog6bmmtbgkzrq6phwjnzm0fjjzg.lambda-url.us-east-1.on.aws/',
                'https://ftzduqjsfyfs4mfvpfveubqzom0joaty.lambda-url.us-east-1.on.aws/',
                'https://worhw5uqotvwrjgirzcpn7gepi0jruke.lambda-url.us-east-1.on.aws/',
                'https://ziwm7xzillgzdhdaax7w6nys6e0eveah.lambda-url.us-east-1.on.aws/',
                'https://m63ulgrrhv6q7dajq2jbov4plm0blswb.lambda-url.us-east-1.on.aws/',
                'https://g6xc4gbczm5yog7re4vtptugpe0yxkyk.lambda-url.us-east-1.on.aws/',
                'https://wvjpnlcvpn4bqbwpk7u3iemxw40einnm.lambda-url.us-east-1.on.aws/',
                'https://ujrpvzvq3jnkh6gbtaov44ps6i0llcuv.lambda-url.us-east-1.on.aws/',
                'https://vdna3gpoe35begeqyezlxlbi4a0qlboo.lambda-url.us-east-1.on.aws/',
                'https://herh3dn5zwe2kplf2fl2b7hq2e0kwnvu.lambda-url.us-east-1.on.aws/',
                'https://m7hqpxn2u2luautwlhddalb6om0nshmh.lambda-url.us-east-1.on.aws/',
                'https://6gw6mu4ypt62j2ml3b6bltmfmu0liwqv.lambda-url.us-east-1.on.aws/',
                'https://2yz3poakqilfjrfdwokxjefazq0lbmls.lambda-url.us-east-1.on.aws/',
                'https://pxrgmwg26zkfxv5554t2s7psii0gwwat.lambda-url.us-east-1.on.aws/',
                'https://yxe5dkp7fombm25y3yb6zfbzvi0xpnsr.lambda-url.us-east-1.on.aws/',
                'https://tifouiewoeqhq2nnzjnkclosqy0zktxt.lambda-url.us-east-1.on.aws/',
                'https://z5klxtguvzsvjmj3xvfrhunixm0vcriy.lambda-url.us-east-1.on.aws/',
                'https://oyrqj3d4m6v5lm2rg4jvwlpbra0ebvnz.lambda-url.us-east-1.on.aws/',
                'https://vw46xed7fpf67mpu6bkdddimjm0cziqr.lambda-url.us-east-1.on.aws/',
                'https://iz52u7tjwqfy4froxnrkg3fymu0qjevh.lambda-url.us-east-1.on.aws/',
                'https://mhp2aqwzvga67ct5dcbpf3xnoi0wdkpw.lambda-url.us-east-1.on.aws/',
                'https://fvmdtquzd2rh6vdyqyyqcieuma0wpogn.lambda-url.us-east-1.on.aws/',
                'https://epkgxvwfsxx57jomyx72rmb7hq0nihcb.lambda-url.us-east-1.on.aws/',
                'https://wdxzr6tmuttghwe3ihcgxmej6i0reevm.lambda-url.us-east-1.on.aws/',
                'https://egtkwpmxjt7kkxo2n6esanv5wa0dzied.lambda-url.us-east-1.on.aws/',
                'https://2og55wlbpnfhsm2rkdq6mh4ohy0peyrx.lambda-url.us-east-1.on.aws/',
                'https://56s6nviw54mepjohwdsw742ppi0fbpvt.lambda-url.us-east-1.on.aws/',
                'https://i5yh2sehcdmcfsvthpjvwgzgju0jzgbd.lambda-url.us-east-1.on.aws/',
                'https://nbgx7cizykt2d2ftqwukxszqou0jfuws.lambda-url.us-east-1.on.aws/',
                'https://zdkdahxzcj4abphuut4rs7uacy0mrqht.lambda-url.us-east-1.on.aws/',
                'https://pms4hqcfw7bk5izqqrzy5y2qda0jocly.lambda-url.us-east-1.on.aws/',
                'https://gnd54yetmjqbu3guxvijegvhs40fzhvo.lambda-url.us-east-1.on.aws/',
                'https://ujnqnanks545spk6cw3gqxha4i0okmgm.lambda-url.us-east-1.on.aws/',
                'https://vjhwvp4eh64iyoyamfj2yovtba0ingfq.lambda-url.us-east-1.on.aws/',
                'https://bx3qcuedcotz23dnqd2se6ktx40khfze.lambda-url.us-east-1.on.aws/',
                'https://c6walrka5arxutj4jp47qq67ma0cngpm.lambda-url.us-east-1.on.aws/',
                'https://wadzrxsetgpzuevtqqbqfz3zju0ekavy.lambda-url.us-east-1.on.aws/',
                'https://ncmfcqdsqgtw5idnbyrc45wm4u0phffu.lambda-url.us-east-1.on.aws/',
                'https://ztsjyvkfmkrh4ifydxzt3fnw240gjphy.lambda-url.us-east-1.on.aws/',
                'https://bkadcvyhjexv663oznj5idy2we0dfelq.lambda-url.us-east-1.on.aws/',
                'https://nc7ogpmmeturbtm6mhvgznf4hu0gdogs.lambda-url.us-east-1.on.aws/',
                'https://f2jo46hudri7jnkloc74iwbosm0oskit.lambda-url.us-east-1.on.aws/',
                'https://6oqqp5q4phq7clz4vuorhlycye0nilnc.lambda-url.us-east-1.on.aws/',
                'https://v5tgvksgvdffbl65zysh2bcwti0fsash.lambda-url.us-east-1.on.aws/',
                'https://5wk34ksv34kjfd3233uapjwynq0frblg.lambda-url.us-east-1.on.aws/',
                'https://6minzcwo3pddzfeqppfenqpeqi0knjfz.lambda-url.us-east-1.on.aws/',
                'https://wkqbxddtmlbm4whnntlu3fxfum0oovpe.lambda-url.us-east-1.on.aws/',
                'https://uvf2bpw4kd644m5i2nt7qmsqim0fgwva.lambda-url.us-east-1.on.aws/',
                'https://5f3yqmxoqqygrwu4rsm5uwy4h40wcgnf.lambda-url.us-east-1.on.aws/',
                'https://syz6aayztrekwqofkva3pktfwi0ulxfl.lambda-url.us-east-1.on.aws/',
                'https://cnhve7wumhht6tbkexcefdr6be0fbfef.lambda-url.us-east-1.on.aws/',
                'https://hf7vbvombskuosan4afqbxx5fy0nbazn.lambda-url.us-east-1.on.aws/',
                'https://xvx2xwztst4cwj52mrnobsdhgm0ndiwp.lambda-url.us-east-1.on.aws/',
                'https://wrfvhixucxseeun2tezodr32qq0kstqn.lambda-url.us-east-1.on.aws/',
                'https://a67h5mgmx3ihdkrzfmyhutaany0oiynf.lambda-url.us-east-1.on.aws/',
                'https://gaxarhm3e7mrv6xuohtakjbppy0tvfxw.lambda-url.us-east-1.on.aws/',
                'https://yognynooiegu4o6k3cdjktcmre0dgpqs.lambda-url.us-east-1.on.aws/',
                'https://mdh4xti5v7ftfhfnco4hv7cb3i0ejskk.lambda-url.us-east-1.on.aws/',
                'https://4vnl7yi7cmaofh6x2swdg3w2540gdbgc.lambda-url.us-east-1.on.aws/',
                'https://iddjdhf2lq6az6hp5wmf2bnu3m0okwyi.lambda-url.us-east-1.on.aws/',
                'https://2pf6qkvwxiluxa6zzix53fsv340tvszp.lambda-url.us-east-1.on.aws/',
                'https://m6logq2mmvjasu5bqj2xgpqvj40arssw.lambda-url.us-east-1.on.aws/',
                'https://iinjspd3qb5yuo5ccsdiadlzve0fsmbs.lambda-url.us-east-1.on.aws/',
                'https://rmvnn447kwypu4shnyxmt2e7ze0oglks.lambda-url.us-east-1.on.aws/',
                'https://tnyas6svmb2xi7wn64szpyvkj40svnxs.lambda-url.us-east-1.on.aws/',
                'https://gznqas23tjdav6tmzpcpgu3mr40kfgck.lambda-url.us-east-1.on.aws/',
                'https://fopmu3zule5uvuuuurd7lzpcjy0wsutj.lambda-url.us-east-1.on.aws/',
                'https://bg5pyya6jy7l733dobfjfpcrvy0acicp.lambda-url.us-east-1.on.aws/',
                'https://kp4hbtl7odq2lw4w622yyvkvhq0vykkt.lambda-url.us-east-1.on.aws/',
                'https://gjr3tn3wjdm74jwvlaizoorh440oceia.lambda-url.us-east-1.on.aws/',
                'https://kctcghznhd73w3iucictz74nby0geqxa.lambda-url.us-east-1.on.aws/',
                'https://gmr7qwpxictsvtocsbfprrenkm0bookf.lambda-url.us-east-1.on.aws/',
                'https://xyyavzlmhf2th233aotk3ix3he0tzixr.lambda-url.us-east-1.on.aws/',
                'https://f5zp6nn6c2aouuvhvrlb3naezm0iacnp.lambda-url.us-east-1.on.aws/',
                'https://g4zhdv2ft4mebive3vlk5qch5a0ndfrx.lambda-url.us-east-1.on.aws/',
                'https://w5vzwdzpj7ytayhn5kzfnhjuz40ergyj.lambda-url.us-east-1.on.aws/',
                'https://jvymk4spd4franoyitxn2433vy0puqmw.lambda-url.us-east-1.on.aws/',
                'https://ufr7nkbsf7qdvsq6z25iuuruoy0qdmho.lambda-url.us-east-1.on.aws/',
                'https://qmqafl5d27wg4xsxnyr42gzive0gxose.lambda-url.us-east-1.on.aws/',
                'https://mvprfbxmbovchf65cswo3jithy0njpaa.lambda-url.us-east-1.on.aws/',
                'https://k4xpknbxq5otq6ihaed3biydgq0whfev.lambda-url.us-east-1.on.aws/',
                'https://byl2moeijrtft3ytxqjyzcdo4a0thzlg.lambda-url.us-east-1.on.aws/',
                'https://hb52ymfij5mqf52fledjv5yksq0nvoxf.lambda-url.us-east-1.on.aws/',
                'https://z2uvmjn3atygvi3q4lzeavjn2u0kafxs.lambda-url.us-east-1.on.aws/',
                'https://rvhpejzgjfnhnsrgkf67d4cdem0tuprx.lambda-url.us-east-1.on.aws/',
                'https://nvt3fsj6w7jqt3w7eta6cdvd3a0jgunp.lambda-url.us-east-1.on.aws/',
                'https://pmnvy5np7rxsa6iy4kablleysm0zebkn.lambda-url.us-east-1.on.aws/',
                'https://z6v74ptw3ygwyzgz3mdbwvndyq0zwzpz.lambda-url.us-east-1.on.aws/',
                'https://oakylw54tibnnyuebcg2v6htfm0urgob.lambda-url.us-east-1.on.aws/',
                'https://jdsb672fhg52t6cog4ayya7mwq0vsygm.lambda-url.us-east-1.on.aws/',
                'https://ftou3qvsl74sjjwyybhghzieum0yrojo.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 1000 base stocks → 100 workers × 10 stocks each');
            console.log('📊 Processing 1000 stocks (100 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling workers for S&P 400+600 stocks...');
            const workerPayloads = [];
            for (let i = 0; i < Math.min(allWorkerUrls.length, 100); i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(sp400_600Universe.length / (Math.min(allWorkerUrls.length, 100))));
                const startIdx = i * perWorker;
                const stockBatch = sp400_600Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log(`📊 Using ${workerPayloads.length} workers for ${workerPayloads.length * 10} stocks`);
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.batch_size} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All ${workerPayloads.length} workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 S&P 400+600 Analysis: ${allResults.length}/${workerPayloads.length * 10} stocks`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 1000, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'SP400_600_Complete_Screener');
            result = formatOption3Result(apiData, '2');
            result.csvData = csvData;
        } else if (option === 3 && subOption === '100') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 3.1 SMART SCALING - S&P 100 (OEX) Stock Screener');
            const sp100Universe = ['AAPL','ABBV','ABT','ACN','ADBE','AMAT','AMD','AMGN','AMT','AMZN','ANET','AVGO','AXP','BA','BAC','BKNG','BLK','BMY','BNY','BRK-B','C','CAT','CMCSA','COF','COP','COST','CRM','CSCO','CVS','CVX','DE','DELL','DHR','DIS','DUK','EMR','FDX','GD','GE','GEV','GILD','GM','GOOG','GOOGL','GS','HD','IBM','INTC','INTU','ISRG','JNJ','JPM','KO','LIN','LLY','LMT','LOW','LRCX','MA','MCD','MDLZ','MDT','META','MMM','MO','MRK','MS','MSFT','MU','NEE','NFLX','NOW','NVDA','ORCL','PANW','PEP','PFE','PG','PLTR','PM','QCOM','RTX','SBUX','SCHW','SNDK','SO','T','TMO','TMUS','TSLA','TXN','UBER','UNH','UNP','UPS','USB','V','VZ','WFC','WMT','XOM'];
            const allWorkerUrls = [
                'https://tlpr2rgptntfwqvkcvwanx2giq0pttcu.lambda-url.us-east-1.on.aws/',
                'https://wr5phqprzpgdyc3e7jcxxndq440pxwdf.lambda-url.us-east-1.on.aws/',
                'https://hbbglzpw54g23zptuvjtpts7ji0akrzr.lambda-url.us-east-1.on.aws/',
                'https://ncr2kjqw5cgitmungtfhsjkpwu0lilnp.lambda-url.us-east-1.on.aws/',
                'https://mp43hke65xzp25zsgh7erv6ife0yiqds.lambda-url.us-east-1.on.aws/',
                'https://6orjqd6qpypkwnuu4oi6aghdv40belov.lambda-url.us-east-1.on.aws/',
                'https://3pvvrvhqy37bxx5yqplg33zk7i0vslsv.lambda-url.us-east-1.on.aws/',
                'https://2sggq4bqgcpu7tqhdlliorfpli0jdnae.lambda-url.us-east-1.on.aws/',
                'https://3pihnd5pesa4kudjzypvy2wcyi0hhjcp.lambda-url.us-east-1.on.aws/',
                'https://o3mxcz7qnfklw4mmazxjqlplke0balsi.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 100 base stocks → 10 workers × 10 stocks each');
            console.log('📊 Processing 100 stocks (10 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 10 workers for 100 S&P 100 (OEX) stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 10; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(sp100Universe.length / (10)));
                const startIdx = i * perWorker;
                const stockBatch = sp100Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 10/10 workers for 100 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.batch_size} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 10 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 S&P 100 (OEX) Analysis: ${allResults.length}/100 stocks (${((allResults.length/100)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 100, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'SP100_OEX_Screener');
            result = formatOption3Result(apiData, subOption);
            result.csvData = csvData;

        } else if (option === 3 && subOption === '4') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 3.4 SMART SCALING - S&P 1500 Stock Screener');
            const sp1500Universe = ['MMM','AOS','ABT','ABBV','ACN','ADBE','AMD','AES','AFL','A','APD','ABNB','AKAM','ALB','ARE','ALGN','ALLE','LNT','ALL','GOOGL','GOOG','MO','AMZN','AMCR','AEE','AEP','AXP','AIG','AMT','AWK','AMP','AME','AMGN','APH','ADI','AON','APA','APO','AAPL','AMAT','APP','APTV','ACGL','ADM','ARES','ANET','AJG','AIZ','T','ATO','ADSK','ADP','AZO','AVY','AXON','BKR','BALL','BAC','BAX','BDX','BRK-B','BBY','TECH','BIIB','BLK','BX','XYZ','BE','BNY','BA','BKNG','BSX','BMY','AVGO','BR','BRO','BF-B','BG','BXP','CHRW','CDNS','CPT','COF','CAH','CCL','CARR','CVNA','CASY','CAT','CBOE','CBRE','CDW','COR','CNC','CNP','CF','CRL','SCHW','CHTR','CVX','CMG','CB','CHD','CIEN','CI','CINF','CTAS','CSCO','C','CFG','CLX','CME','CMS','KO','CTSH','COHR','COIN','CL','CMCSA','FIX','COP','ED','STZ','CEG','COO','CPRT','GLW','CPAY','CSGP','COST','CRH','CRWD','CCI','CSX','CMI','CVS','DHR','DRI','DDOG','DVA','DECK','DE','DELL','DAL','DVN','DXCM','FANG','DLR','DG','DLTR','D','DPZ','DASH','DOV','DOW','DHI','DTE','DUK','DD','ETN','EBAY','ECHO','ECL','EIX','EW','ELV','EME','EMR','ETR','EOG','EQT','EFX','EQIX','ERIE','ESS','EL','EG','EVRG','P','ES','EXC','EXE','EXPE','EXPD','EXR','XOM','FFIV','FDS','FICO','FAST','FRT','FDX','FDXF','FERG','FIS','FITB','FSLR','FE','FISV','FLEX','F','FTNT','FTV','FOXA','FOX','BEN','FCX','GRMN','IT','GE','GEHC','GEV','GEN','GNRC','GD','GIS','GM','GPC','GILD','GPN','GL','GDDY','GS','HAL','HIG','HAS','HCA','DOC','HSIC','HSY','HPE','HLT','HD','HONA','HON','HRL','HST','HWM','HPQ','HUBB','HUM','HBAN','HII','IBM','IEX','IDXX','ITW','ILMN','INCY','IR','PODD','INTC','IBKR','ICE','IFF','IP','INTU','ISRG','IVZ','INVH','IQV','IRM','JBHT','JBL','JKHY','J','JNJ','JCI','JPM','KVUE','KDP','KEY','KEYS','KMB','KIM','KMI','KKR','KLAC','KHC','KR','LHX','LH','LRCX','LVS','LDOS','LEN','LII','LLY','LIN','LYV','LMT','L','LOW','LULU','LITE','LYB','MTB','MPC','MAR','MRSH','MLM','MRVL','MAS','MA','MKC','MCD','MCK','MDT','MRK','META','MET','MTD','MGM','MCHP','MU','MSFT','MAA','MRNA','MDLZ','MPWR','MNST','MCO','MS','MOS','MSI','MSCI','NDAQ','NTAP','NFLX','NEM','NWSA','NWS','NEE','NKE','NI','NDSN','NSC','NTRS','NOC','NCLH','NRG','NUE','NVDA','NVR','NXPI','ORLY','OXY','ODFL','OMC','ON','OKE','ORCL','OTIS','PCAR','PKG','PLTR','PANW','PH','PAYX','PYPL','PNR','PEP','PFE','PCG','PM','PSX','PNW','PNC','PPG','PPL','PFG','PG','PGR','PLD','PRU','PEG','PTC','PSA','PHM','PWR','QCOM','DGX','Q','RL','RJF','RDDT','RTX','O','REG','REGN','RF','RSG','RMD','RVTY','HOOD','ROK','ROL','ROP','ROST','RCL','SPGI','CRM','SNDK','SBAC','SLB','STX','SRE','NOW','SHW','SPG','SKYD','SWKS','SJM','SW','SNA','SOLV','SO','LUV','SWK','SBUX','STT','STLD','STE','SYK','SMCI','SYF','SNPS','SYY','TMUS','TROW','TTWO','TPR','TRGP','TGT','TEL','TDY','TER','TSLA','TXN','TPL','TXT','TMO','TJX','TKO','TSCO','TT','TDG','TRV','TRMB','TFC','TWLO','TYL','TSN','USB','UBER','UDR','ULTA','UNP','UAL','UPS','URI','UNH','UHS','VLO','VEEV','VTR','VLTO','VRSN','VRSK','VZ','VRTX','VRT','VTRS','VICI','V','VST','VMRK','VMC','WRB','GWW','WAB','WMT','DIS','WM','WAT','WEC','WFC','WELL','WST','WDC','WY','WSM','WMB','WTW','WDAY','WYNN','XEL','XYL','YUM','ZBRA','ZBH','ZTS','AA','AAL','AAON','ACI','ACM','ADC','AEIS','AFG','AGCO','AGNC','AHR','AIT','ALGM','ALK','ALLY','ALSN','ALV','AM','AMG','AMH','AMKR','AN','ANF','APG','APPF','AR','ARMK','ARW','ARWR','ASB','ASH','ATI','ATR','AVAV','AVNT','AVT','AVTR','AXTA','AYI','BAH','BBWI','BC','BCO','BDC','BHF','BILL','BIO','BJ','BKH','BMRN','BRKR','BROS','BRX','BSY','BTSG','BURL','BWA','BWXT','BYD','CACI','CAR','CART','CAVA','CBSH','CBT','CCK','CDE','CDP','CELH','CFR','CG','CGNX','CHDN','CHE','CHH','CHRD','CHWY','CLF','CLH','CMC','CNH','CNM','CNO','CNX','COKE','COLB','COLM','CORT','CR','CRBG','CROX','CRS','CRUS','CSL','CTRE','CTVA','CUBE','CUZ','CVLT','CW','CXT','CYTK','DAR','DBX','DCI','DINO','DKS','DLB','DOCN','DOCS','DOCU','DT','DTM','DUOL','DY','EAT','EEFT','EGP','EHC','ELAN','ELF','ELS','ENS','ENSG','ENTG','EPR','EQH','ESAB','ESNT','EVR','EWBC','EXEL','EXLS','EXP','EXPO','FAF','FBIN','FCFS','FCN','FFIN','FHI','FHN','FIVE','FLG','FLR','FLS','FN','FNB','FND','FNF','FORM','FOUR','FR','FTI','G','GAP','GATX','GBCI','GEF','GGG','GHC','GLPI','GME','GMED','GNTX','GPK','GWRE','GXO','H','HAE','HALO','HGV','HIMS','HL','HLI','HLNE','HOG','HOMB','HQY','HR','HRB','HUBS','HWC','HXL','IBOC','IDA','IDCC','IESC','INGR','IPGP','IRT','ITT','JAZZ','JEF','JLL','KBH','KBR','KD','KEX','KNF','KNSL','KNX','KRC','KRG','KRYS','KTOS','LAD','LAMR','LEA','LECO','LFUS','LIVN','LNTH','LOPE','LPX','LSCC','LSTR','M','MANH','MAT','MEDP','MIDD','MKSI','MLI','MMS','MOG-A','MOH','MORN','MP','MSA','MSM','MTDR','MTG','MTN','MTSI','MTZ','MUR','MUSA','MZTI','NBIX','NEU','NFG','NJR','NLY','NNN','NOV','NOVT','NTNX','NVST','NVT','NWE','NXST','NXT','NYT','OC','OGE','OGS','OHI','OKTA','OLED','OLLI','ONB','ONTO','OPCH','ORA','ORI','OSK','OVV','OZK','PAG','PATH','PB','PBF','PCTY','PEGA','PEN','PFGC','PII','PINS','PK','PLNT','PNFP','POR','POST','PPC','PR','PRI','PSN','PVH','QLYS','R','RBA','RBC','REXR','RGA','RGEN','RGLD','RH','RLI','RMBS','RNR','ROIV','ROKU','RPM','RRC','RRX','RS','RYAN','RYN','SAIA','SAIC','SANM','SARO','SBRA','SCI','SEIC','SF','SFM','SGI','SHC','SIGI','SIRI','SITM','SLAB','SLGN','SLM','SMG','SMTC','SN','SNX','SOLS','SON','SPXC','SR','SSB','SSD','ST','STAG','STRL','STWD','SUI','SWX','SYNA','TCBI','TEX','THC','THG','THO','TKR','TLN','TNL','TOL','TOST','TREX','TRU','TTC','TTEK','TTMI','TXNM','TXRH','UBSI','UFPI','UGI','ULS','UMBF','UNM','USFD','UTHR','VAL','VC','VFC','VIAV','VICR','VLY','VMI','VNO','VNOM','VNT','VOYA','VVV','WAL','WCC','WEX','WFRD','WH','WHR','WING','WLK','WMG','WMS','WPC','WSO','WTFC','WTRG','WTS','WWD','XPO','XRAY','YETI','ZION','AAMI','AAP','AAT','ABCB','ABG','ABM','ABR','ACA','ACAD','ACHC','ACIW','ACLS','ACMR','ACT','ADAM','ADEA','ADIG','ADMA','ADNT','ADT','ADUS','AEO','AESI','AGNT','AGO','AGX','AGYS','AHCO','AIN','AIR','AKR','ALG','ALGT','ALHC','ALKS','ALRM','AMN','AMPH','AMR','AMRX','AMSF','AMTM','ANDE','ANIP','AORT','AOSL','APAM','APLE','APOG','ARCB','ARLO','AROC','ARR','ASO','ASTE','ASTH','ATEN','ATMU','AUB','AVA','AWI','AWR','AX','AZTA','AZZ','BANC','BANF','BANR','BBT','BCC','BCPC','BFAM','BFH','BFS','BGC','BHE','BJRI','BKE','BKU','BL','BLKB','BMI','BNL','BOH','BOOT','BOX','BRC','BTU','BXMT','CACC','CAG','CAKE','CALM','CALX','CALY','CARG','CASH','CATY','CBRL','CBU','CC','CCOI','CCS','CE','CENT','CENTA','CENX','CERT','CFFN','CHCO','CHEF','CLSK','CNK','CNMD','CNR','CNS','CNXC','CNXN','COCO','COHU','COLL','CON','COTY','CPB','CPF','CPK','CRC','CRGY','CRI','CRK','CRSR','CRVL','CSR','CSW','CTS','CUBI','CURB','CVBF','CVCO','CVI','CVSA','CWEN','CWK','CWST','CWT','CXM','CXW','CZR','DAN','DAVE','DBD','DCH','DCOM','DEA','DEI','DFH','DFIN','DGII','DIOD','DLX','DMC','DNOW','DORM','DRH','DV','DXC','DXPE','EBC','ECG','ECPG','EFC','EFOR','EGBN','EIG','EMN','ENOV','ENPH','ENR','ENVA','EPAC','EPAM','EPC','EPRT','ESE','ESI','ETSY','EVTC','EXTR','EYE','EZPW','FA','FBK','FBNC','FBP','FBRT','FCF','FCPT','FELE','FFBC','FG','FHB','FIBK','FIVN','FIZZ','FLO','FMC','FOXF','FRPT','FSS','FTDR','FTRE','FUL','FULT','FUN','GBX','GEO','GFF','GIII','GKOS','GNL','GNW','GO','GOLF','GPI','GPOR','GRBK','GSHD','GT','GTES','GTM','GTY','GVA','HAFC','HASI','HAYW','HCC','HCI','HCSG','HE','HFWA','HIW','HLIT','HMN','HNI','HOPE','HP','HRMY','HSTM','HTH','HTLD','HTO','HUBG','HWKN','HZO','IART','IBP','ICHR','ICUI','IIPR','INDB','INDV','INSP','INSW','INVA','INVX','IOSP','IPAR','IRDM','ITGR','ITRI','IVT','JBGS','JBLU','JBSS','JBTM','JJSF','JOE','JXN','KAI','KALU','KFY','KGS','KLIC','KMPR','KMT','KMX','KN','KNTK','KOP','KRMN','KSS','KTB','KWR','LAUR','LAZ','LBRT','LCII','LEU','LFST','LGIH','LIF','LGND','LKFN','LKQ','LMAT','LNC','LNN','LPG','LQDA','LQDT','LRN','LTC','LTH','LUMN','LW','LXP','LYFT','LZ','LZB','MAC','MAN','MARA','MATW','MATX','MBC','MBGL','MBIN','MC','MCRI','MCY','MD','MDU','MFP','MGEE','MGY','MHK','MHO','MIR','MKTX','MLKN','MMI','MMSI','MPT','MRCY','MRP','MRTN','MSEX','MSGS','MTCH','MTH','MTRN','MTUS','MTX','MWA','MXL','MYRG','NABL','NATL','NAVI','NBHC','NBTB','NE','NEO','NEOG','NGVT','NHC','NHI','NIC','NMIH','NOG','NPK','NPO','NSIT','NSP','NSSC','NTCT','NTST','NWBI','NWL','NWN','NX','NXRT','OFG','OGN','OI','OII','OMCL','OPLN','OSIS','OSW','OTTR','OUT','PAHC','PARR','PAYC','PAYO','PATK','PBH','PBI','PCRX','PDFS','PEB','PECO','PENG','PENN','PFBC','PFS','PGNY','PHIN','PI','PIPR','PJT','PLAB','PLMR','PLUS','PLXS','PMT','POOL','POWI','POWL','PPLI','PRDO','PRG','PRGO','PRGS','PRIM','PRK','PRKS','PRLB','PRSU','PRVA','PSMT','PTCT','PTEN','PTGX','PTON','PZZA','QDEL','QNST','QTWO','RAMP','RAL','RCUS','RDN','RDNT','RELY','RES','REYN','REX','REZI','RHI','RHP','RITM','RNG','RNST','ROAD','ROCK','ROG','RRR','RSI','RUN','RUSHA','RXO','SAFE','SABR','SAFT','SAH','SBCF','SBH','SBSI','SCHL','SCL','SCSC','SDGR','SEDG','SEI','SEZL','SFBS','SFNC','SHAK','SHEN','SHO','SHOO','SIG','SKT','SKY','SKYW','SLG','SLVM','SM','SMP','SMPL','SNDR','SNEX','SONO','SPHR','SPNT','SPSC','SRPT','STAA','STBA','STC','STEP','STRA','SUPN','SXI','SXT','TALO','TBBK','TDC','TDS','TDW','TFIN','TFX','TGTX','THRM','TILE','TMDX','TMP','TNC','TNDM','TPC','TR','TRIP','TRMK','TRN','TRNO','TRST','TRUP','UA','UAA','UCB','UCTT','UE','UFCS','UFPT','UNF','UNFI','UNIT','UPBD','UPWK','URBN','USLM','USPH','UTI','UTL','UVV','VAC','VCEL','VCTR','VCYT','VECO','VGNT','VIR','VIRT','VRRM','VRTS','VSAT','VSEC','VSH','VSNT','VSTS','VSXY','VTOL','VVX','VYX','WABC','WAFD','WAY','WD','WDFC','WEN','WERN','WGO','WHD','WINA','WKC','WLY','WOR','WRBY','WRLD','WS','WSBC','WSC','WSFS','WT','WU','WWW','XHR','XNCR','XPEL','YELP','YOU','ZD','ZWS'];
            const allWorkerUrls = [
                'https://u3wkw5y63uq4jgwpwpgtdfmhry0yicex.lambda-url.us-east-1.on.aws/',
                'https://swukj3gonetxh7iuuvukczd5vq0xxcph.lambda-url.us-east-1.on.aws/',
                'https://6dj64n7kbkjbukbo6midrgeybu0glkbe.lambda-url.us-east-1.on.aws/',
                'https://wwqlxjkypz6m5o2bgtw5f263o40msjip.lambda-url.us-east-1.on.aws/',
                'https://wjru7jffcx2j3p4o5chkag4kn40fxgda.lambda-url.us-east-1.on.aws/',
                'https://swj7ba5vlmyoqymgi4xkkmmgdy0vesxn.lambda-url.us-east-1.on.aws/',
                'https://v6ei73dr4onca2faemp6o4wpiq0lanxd.lambda-url.us-east-1.on.aws/',
                'https://zhxey4y6ts5u5cmx7axy5ml4jq0nnnpp.lambda-url.us-east-1.on.aws/',
                'https://yksb7u2go2omgu4lcehs5km6fu0edmmg.lambda-url.us-east-1.on.aws/',
                'https://tk3ewaethm6w3xdxh2xcn5ryzy0tgwms.lambda-url.us-east-1.on.aws/',
                'https://ctmwlpcprrh3qo2r7h4qhthqwu0hywpr.lambda-url.us-east-1.on.aws/',
                'https://mkzxhhq5cvoleym3tlbu5lzeie0mabbm.lambda-url.us-east-1.on.aws/',
                'https://xmw67mnxjnxsxuqgbcqvzq5zwm0lspzj.lambda-url.us-east-1.on.aws/',
                'https://3247arrc6rjtbymboia7lf3l7a0mudqe.lambda-url.us-east-1.on.aws/',
                'https://4xis6p2grocs2lo6ryqzp3dwe40nwwov.lambda-url.us-east-1.on.aws/',
                'https://xb2cldv57s6uf7n5wbqfav3epu0asziy.lambda-url.us-east-1.on.aws/',
                'https://r6rt2qhcrlauukdqun2avsiidu0zodmw.lambda-url.us-east-1.on.aws/',
                'https://4kbmkhosj7mu3e6xejzvf2vvcq0yqkhn.lambda-url.us-east-1.on.aws/',
                'https://3oxlccrrerkaeccw3own2lpyo40ysuyx.lambda-url.us-east-1.on.aws/',
                'https://vabirciithqrrtho7hznhqd6oq0abrgs.lambda-url.us-east-1.on.aws/',
                'https://skoxtqzi6nwoq2bxpnzundwhgq0cdfaa.lambda-url.us-east-1.on.aws/',
                'https://kxhborfc7gxclyokkbkiogszde0jaekj.lambda-url.us-east-1.on.aws/',
                'https://q44runlokawe6zunnk4o2w7lpu0habjn.lambda-url.us-east-1.on.aws/',
                'https://i2ska7t4h4gbgquuaomeule5hi0brprb.lambda-url.us-east-1.on.aws/',
                'https://6fyzw4e6xr3lixseroteibddx40azpcz.lambda-url.us-east-1.on.aws/',
                'https://uf6x4nnn6gsnmgnfyhpnyzjy540ciddv.lambda-url.us-east-1.on.aws/',
                'https://hrvhgx5gpdg4xmpj4jj7mzovfa0jmryo.lambda-url.us-east-1.on.aws/',
                'https://vrubnmgbcj53seqlmqlob22czi0enuul.lambda-url.us-east-1.on.aws/',
                'https://vpfgte4czwh76ki4mndpg5ru4y0rmcfv.lambda-url.us-east-1.on.aws/',
                'https://hvlncqph5aywufkjeedccz4s5u0yczoe.lambda-url.us-east-1.on.aws/',
                'https://b3aojd5xobatiwjqroyr75gwzq0gcsjq.lambda-url.us-east-1.on.aws/',
                'https://zuknyuouni3flykfc7miyq4kdy0atgdd.lambda-url.us-east-1.on.aws/',
                'https://azxesc7iuiapl7y6dsh35eh7mq0xybld.lambda-url.us-east-1.on.aws/',
                'https://tjgukcwshhkyyyvsquthblhv2u0bpdya.lambda-url.us-east-1.on.aws/',
                'https://ciqc4ngosvqnxykigwqiu3odbe0uzkqk.lambda-url.us-east-1.on.aws/',
                'https://rhed5sjehicoj4yhx3prhzjvdy0ipkox.lambda-url.us-east-1.on.aws/',
                'https://gwpueayq6fcaad25t4c643yzuq0hyvwm.lambda-url.us-east-1.on.aws/',
                'https://qzncoswd2ae6uzk67quh5beyiu0xakhp.lambda-url.us-east-1.on.aws/',
                'https://f7eaab7qgdnkdkgd34ywukolpq0najnp.lambda-url.us-east-1.on.aws/',
                'https://y5ltvchlrtcpil6a23wvgg7kru0pwylh.lambda-url.us-east-1.on.aws/',
                'https://vgzxdocri37tnxh3cxqykaaa2y0oxzjy.lambda-url.us-east-1.on.aws/',
                'https://fq3fuu7gpzqht6n3nxqzjvkzgq0bcjac.lambda-url.us-east-1.on.aws/',
                'https://ziywqihl32tshtugqemljxffgq0agieu.lambda-url.us-east-1.on.aws/',
                'https://kealsdv6nljfizjqrsbr5thvoa0czhbx.lambda-url.us-east-1.on.aws/',
                'https://62q2gcflzosmahhqjmbtsv2s2i0zjran.lambda-url.us-east-1.on.aws/',
                'https://ox3ygtyel7r43dfhszciofhtdm0glpka.lambda-url.us-east-1.on.aws/',
                'https://3qxymbcf7fn6mg7ucchvjvj5m40iwsed.lambda-url.us-east-1.on.aws/',
                'https://jjsvelygsdwxd7a7qqs64cahwy0bugdf.lambda-url.us-east-1.on.aws/',
                'https://q5yc2fdruz4asuwsrtoexexvgy0cwowd.lambda-url.us-east-1.on.aws/',
                'https://ay4mpjekoxhkntr5ri2mumbib40gfhlf.lambda-url.us-east-1.on.aws/',
                'https://haypna4jtg2ladtkthgjwgchq40kixqr.lambda-url.us-east-1.on.aws/',
                'https://yhvpwbhwzf4brnebnhcg2gzas40dxjlp.lambda-url.us-east-1.on.aws/',
                'https://rsb6tzu5pdwchjydvqvyerv75u0xjsfo.lambda-url.us-east-1.on.aws/',
                'https://3zwmpjl3e2q26ooz6gyzdzmui40zwqkn.lambda-url.us-east-1.on.aws/',
                'https://susr3twvufx6g3bgxccs2rei2i0nyjez.lambda-url.us-east-1.on.aws/',
                'https://kn3krfncn63dnwgbdpkp2zqizm0mciaf.lambda-url.us-east-1.on.aws/',
                'https://qkbbvj6o432mnsr3pin2lo5w2m0nxgkf.lambda-url.us-east-1.on.aws/',
                'https://3h7uik275mxy5mxic3xvv24oqm0iuhko.lambda-url.us-east-1.on.aws/',
                'https://yewxedwnlkhjb7ajlaxg5e5jpe0xmmxt.lambda-url.us-east-1.on.aws/',
                'https://wb3deoztvvnqaggyqhxkhjfhiq0cegoq.lambda-url.us-east-1.on.aws/',
                'https://d7v2b7ncsp6srjbjpbw5h2bmuy0eztzb.lambda-url.us-east-1.on.aws/',
                'https://uejnvhske7637lkiezdmoaiutq0cwonc.lambda-url.us-east-1.on.aws/',
                'https://7elv67lsifvlf5tg2cayjm7b2m0enofx.lambda-url.us-east-1.on.aws/',
                'https://gcdhscj3n7pwj2gnngqrxuurta0qnlis.lambda-url.us-east-1.on.aws/',
                'https://lxb3yjmggw5y7xdj2vzzbf6nmi0lciis.lambda-url.us-east-1.on.aws/',
                'https://2ulyk2cdqwqnzntscm66oschnq0gisvz.lambda-url.us-east-1.on.aws/',
                'https://re2phso654y2jhho2ac7w7thc40jkpwe.lambda-url.us-east-1.on.aws/',
                'https://6uvwopaspo5ifdys7s5x5pe56u0dewhb.lambda-url.us-east-1.on.aws/',
                'https://tevaymjfq7yn6a6t2zsdmmuaz40hwxwk.lambda-url.us-east-1.on.aws/',
                'https://vq7ftgkn7t5wieov62rzez37ey0bnijw.lambda-url.us-east-1.on.aws/',
                'https://bawbsymjryhg46zvyeuqpazkee0idqvu.lambda-url.us-east-1.on.aws/',
                'https://7es2eev2jsrjyltsxploonzrvy0vhrcb.lambda-url.us-east-1.on.aws/',
                'https://e7xgtyltk4rohkviyld3qetdzi0zlfwq.lambda-url.us-east-1.on.aws/',
                'https://3edh2hzo7smfrtwroc2fz45efa0sdxnn.lambda-url.us-east-1.on.aws/',
                'https://dg4ibhew5qtuwsxntdp3admkv40hotci.lambda-url.us-east-1.on.aws/',
                'https://6g5z54gqoffpa3xxf3kklb4jnq0yiuar.lambda-url.us-east-1.on.aws/',
                'https://43rav5cocorieqduqtzjffle5q0khqbi.lambda-url.us-east-1.on.aws/',
                'https://pfgrhmetpm4hxhogxvedfz6fwu0vhroa.lambda-url.us-east-1.on.aws/',
                'https://3xqxlsnn225xglpkklivm7d2sq0gkbgp.lambda-url.us-east-1.on.aws/',
                'https://zqnbej5qq5ez2zv3plae6apj7e0hvumf.lambda-url.us-east-1.on.aws/',
                'https://3qesskk57356v6iiu2q75mwdjm0xfcwg.lambda-url.us-east-1.on.aws/',
                'https://prqtr664tujal2ucw3o4qsnksq0vgomw.lambda-url.us-east-1.on.aws/',
                'https://s5xdw4p7gi2jk5kfzldlexzy5a0iuzsf.lambda-url.us-east-1.on.aws/',
                'https://jns6qmqbvlxehklr6n75axxat40lzahl.lambda-url.us-east-1.on.aws/',
                'https://nddynu2zmgwuxquvqnhklgcx3y0jtouf.lambda-url.us-east-1.on.aws/',
                'https://cl3xksykrebouett4xpzrtb2re0gucic.lambda-url.us-east-1.on.aws/',
                'https://ias3kqtkqlz3da75qpj4fx4v2y0cvbjs.lambda-url.us-east-1.on.aws/',
                'https://xxgvwo62nkernx5zxxytixeomy0raqmn.lambda-url.us-east-1.on.aws/',
                'https://2zc5yt5f5uhkq6fuomlca2b64u0oqxac.lambda-url.us-east-1.on.aws/',
                'https://ov7y6lu3nuuebkoe7xr3ahw3yq0kthsp.lambda-url.us-east-1.on.aws/',
                'https://nsaumwxh52t2cin7xmt7xx2qsq0vjjft.lambda-url.us-east-1.on.aws/',
                'https://ya5llpruf7hdf524o5qe22knby0bxjdm.lambda-url.us-east-1.on.aws/',
                'https://vpqlqlfbxp3peh65mwcp6d5epe0kmsfo.lambda-url.us-east-1.on.aws/',
                'https://oyltieycwyg22wurgnvu2e5pfy0tcodw.lambda-url.us-east-1.on.aws/',
                'https://cz2ldfzcs4tbfj2h7g4oryxqpu0kwive.lambda-url.us-east-1.on.aws/',
                'https://kaiizwtptnzncob6w7tn4ah5yi0dakyo.lambda-url.us-east-1.on.aws/',
                'https://kig5dzhyzxgtissg2hoj4bb2g40dsafz.lambda-url.us-east-1.on.aws/',
                'https://dpkn4shjf4hfm76hwk4xtlw7fe0leztp.lambda-url.us-east-1.on.aws/',
                'https://ujqkpbhpztrxmwrvkqdeaeddai0hfefe.lambda-url.us-east-1.on.aws/',
                'https://asfe2h45miogla4owwytv3rnni0nsdnt.lambda-url.us-east-1.on.aws/',
                'https://72cebqbyymvf5e2njbtt5tnlqi0eznzg.lambda-url.us-east-1.on.aws/',
                'https://wi2bsokn5i6hejupyu2kdalvpi0mtosw.lambda-url.us-east-1.on.aws/',
                'https://33pr7bl4plwyy4enfgpz7eyjpe0ppvqr.lambda-url.us-east-1.on.aws/',
                'https://4cripvtg6mq4rcpbonesulojr40uvfav.lambda-url.us-east-1.on.aws/',
                'https://7262ugjdh4jv7g6aa63lm2ukbm0mcvtc.lambda-url.us-east-1.on.aws/',
                'https://no4ytk5ir3cwnfag3ihslmipke0lvzxm.lambda-url.us-east-1.on.aws/',
                'https://pepdlkmwokp2ten7ncvss3qsbi0quaue.lambda-url.us-east-1.on.aws/',
                'https://wm7l3x2qp5ap5d52flp66rvp740oqygr.lambda-url.us-east-1.on.aws/',
                'https://5btsrkgkd3eml6ysrpuk5ghtfu0yqmyb.lambda-url.us-east-1.on.aws/',
                'https://zwinvfdiqb7dfg4vzrcfjpeasm0lacvg.lambda-url.us-east-1.on.aws/',
                'https://4glxfsoflhidrmylvvnwkucqza0ivnnj.lambda-url.us-east-1.on.aws/',
                'https://rars5jlwz7x5gd6snbjmul7y740hlhfk.lambda-url.us-east-1.on.aws/',
                'https://a3dtxmbukvzzvsejwrd6j4l72a0bldjh.lambda-url.us-east-1.on.aws/',
                'https://qqhldu4g5gdubqhsqwka7ncevq0czyqu.lambda-url.us-east-1.on.aws/',
                'https://d3c7xyvyjvzvbwzfhos227tvge0ginti.lambda-url.us-east-1.on.aws/',
                'https://vljaqioycufzvbgpuq2g4nvhia0zrrsj.lambda-url.us-east-1.on.aws/',
                'https://rkuizric7bvhh46kvpsekc3tha0ghvkv.lambda-url.us-east-1.on.aws/',
                'https://3v7snvevq3yxsdso3bv7ntz5ku0chyzn.lambda-url.us-east-1.on.aws/',
                'https://263jol2fnyhb2c3trqh57qv4au0rxmvb.lambda-url.us-east-1.on.aws/',
                'https://jt5qpxt2x6sfnksq6yftucm7kq0dbfoi.lambda-url.us-east-1.on.aws/',
                'https://xdjuefxll5iqckb2qupmpd2bpi0jlllz.lambda-url.us-east-1.on.aws/',
                'https://cusnpuyy32an7hn7bf2jjw4cqu0esdil.lambda-url.us-east-1.on.aws/',
                'https://6lggwxqlj3ci3dzvscx5ls25v40ubxnt.lambda-url.us-east-1.on.aws/',
                'https://vfpygb5xctohtbrpzzcj7xajri0tfqfd.lambda-url.us-east-1.on.aws/',
                'https://7f7yudngzsatpew57fr3bvkaee0bfnzm.lambda-url.us-east-1.on.aws/',
                'https://4szjvwuvnyoqc7y5wnthvlgmue0ypupj.lambda-url.us-east-1.on.aws/',
                'https://vtegbt3rtdki7hhtffvzwewyfa0hkegn.lambda-url.us-east-1.on.aws/',
                'https://nupgyd4cwdxwojpqt4wro2iab40uanuj.lambda-url.us-east-1.on.aws/',
                'https://66tbvtnxyuxpio6daxvfcdwlle0btkow.lambda-url.us-east-1.on.aws/',
                'https://akequ4mc6o5ktw5jfhndx3gnki0pyuba.lambda-url.us-east-1.on.aws/',
                'https://dpnjm4tk3uk3jryu3lj4z3qhzi0wulty.lambda-url.us-east-1.on.aws/',
                'https://htfcflbvfyxavhcn5xma7yfe4m0vivph.lambda-url.us-east-1.on.aws/',
                'https://4kbmkhosj7mu3e6xejzvf2vvcq0xofsr.lambda-url.us-east-1.on.aws/',
                'https://ueph6alrk4tg4e223pp6v5q72e0ebqrz.lambda-url.us-east-1.on.aws/',
                'https://zwnfudwyijwq2paigkpmpihzgu0jsckt.lambda-url.us-east-1.on.aws/',
                'https://5eih3vvfvac5frev4qfozpxiqe0poxmb.lambda-url.us-east-1.on.aws/',
                'https://vagn5bqnyy3s4ppdjhrlnwfpy40fbwip.lambda-url.us-east-1.on.aws/',
                'https://edec4xjhadqevqgiemvcpuv5fy0gpnns.lambda-url.us-east-1.on.aws/',
                'https://y3cdluruk2yf3snhyho3mg56bm0kbbnr.lambda-url.us-east-1.on.aws/',
                'https://4hqltapvlixrcldkvvlhaxe6o40ttflw.lambda-url.us-east-1.on.aws/',
                'https://todsqmuutqb2oxqe3a5a7dwqg40icwdd.lambda-url.us-east-1.on.aws/',
                'https://xugrzjr3dwpnzaezsirigbbdeu0ozgmr.lambda-url.us-east-1.on.aws/',
                'https://2e6yfaqqdt3gp7js5e3mrizh7a0rsfub.lambda-url.us-east-1.on.aws/',
                'https://l6ncjdonaj7eih5bhodaksiukq0dybje.lambda-url.us-east-1.on.aws/',
                'https://l7hvn5kt35j65orhvxv5sjcopy0wjhlk.lambda-url.us-east-1.on.aws/',
                'https://npvolhzyxdfftc5onzg26ccnci0pflwp.lambda-url.us-east-1.on.aws/',
                'https://fps7uzndhbikumaxfj6jgvdrsi0voiux.lambda-url.us-east-1.on.aws/',
                'https://2pqhjqvafdagcog66lchjf4af40niomv.lambda-url.us-east-1.on.aws/',
                'https://blxsgjwaqdz7tz37ocjembgqhq0wpchy.lambda-url.us-east-1.on.aws/',
                'https://iyh6bvisox3pupto54vwerhifi0gcujs.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 1500 base stocks → 150 workers × 10 stocks each');
            console.log('📊 Processing 1500 stocks (150 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling workers for S&P 1500 stocks...');
            const workerPayloads = [];
            for (let i = 0; i < Math.min(allWorkerUrls.length, 150); i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(sp1500Universe.length / (Math.min(allWorkerUrls.length, 150))));
                const startIdx = i * perWorker;
                const stockBatch = sp1500Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log(`📊 Using ${workerPayloads.length} workers for ${workerPayloads.length * 10} stocks`);
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.batch_size} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const results = await Promise.all(promises);
            const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
            let allResults = [];
            results.forEach(workerResult => {
                if (workerResult.result && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 S&P 1500 Analysis: ${allResults.length}/${workerPayloads.length * 10} stocks`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 1500, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'SP1500_Complete_Screener');
            result = formatOption3Result(apiData, '4');
            result.csvData = csvData;

        } else if (option === 3 && subOption === '5') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 3.5 SMART SCALING - Russell 1000 Large-Cap Stock Screener');
            // Russell 1000 uses worker_id to determine which stocks to process
            const russell1000Universe = null; // Workers load their own stock batches
            const allWorkerUrls = [
                'https://sumuq55x4kzehluvsbjllokgt40sqziy.lambda-url.us-east-1.on.aws/',
                'https://4kxcesof3axkxjwxr7ppvxaufy0wxerx.lambda-url.us-east-1.on.aws/',
                'https://qdtaabefjq2uaxt7eolajnrpkq0cyjhp.lambda-url.us-east-1.on.aws/',
                'https://rnkpysopxjipqtwavfjox5gqji0fgkke.lambda-url.us-east-1.on.aws/',
                'https://okmwdoc56yby4ictlmccqlbji40jgrvt.lambda-url.us-east-1.on.aws/',
                'https://wtasa3lx3ui4o7p45ialc4jdwy0gubly.lambda-url.us-east-1.on.aws/',
                'https://tpsdzbraynuj2xugqwueofxxlq0dswgm.lambda-url.us-east-1.on.aws/',
                'https://mld3e7rdgljjoearp37f2rh4gq0jtdjd.lambda-url.us-east-1.on.aws/',
                'https://tv3puew6c5hn35lvdx4tiyhsbu0lalgg.lambda-url.us-east-1.on.aws/',
                'https://7yadzqcqosh6yptpoq4mw33uji0zzhaw.lambda-url.us-east-1.on.aws/',
                'https://ng5nhwpsdvaw32oljuoqwmyupe0gpuns.lambda-url.us-east-1.on.aws/',
                'https://fryd75bfv3vhpl4y7wk5axwkla0gdbmq.lambda-url.us-east-1.on.aws/',
                'https://y4udgwckvq5g4cyp4wuel72qn40bxaqn.lambda-url.us-east-1.on.aws/',
                'https://vun2rgrkvulfkp6bgpfgwre36m0majwy.lambda-url.us-east-1.on.aws/',
                'https://knwl34plyohgwqv654qaghtdiy0xxtfl.lambda-url.us-east-1.on.aws/',
                'https://j57tzdb336qy4rvn5ccqkjgxfy0whzkg.lambda-url.us-east-1.on.aws/',
                'https://lcydaogtuez3fakjbhzpvfqtuy0loywk.lambda-url.us-east-1.on.aws/',
                'https://2sep5fjrlbtyclb45hglcmxhay0uacnj.lambda-url.us-east-1.on.aws/',
                'https://brbz4bzc32kpiwy4fq3cvu4bzq0tvtob.lambda-url.us-east-1.on.aws/',
                'https://pilagfzilbgluzuvm35onlibm40makmv.lambda-url.us-east-1.on.aws/',
                'https://wisfookpyzku2ydy2dg2hk6hva0wfkag.lambda-url.us-east-1.on.aws/',
                'https://bkdbv3s2ld7saduhbi4yvzhrki0vgout.lambda-url.us-east-1.on.aws/',
                'https://6y6nufkvvp23chbr52fhmb5xoi0bgoej.lambda-url.us-east-1.on.aws/',
                'https://rkekhafr4cfw2vipdvnaktscqi0qxnze.lambda-url.us-east-1.on.aws/',
                'https://cqtjlp3eq6ndkor4tpdgos234m0qjwqo.lambda-url.us-east-1.on.aws/',
                'https://np2ybzlvwdtlozeyiz6k7eybdu0dcutk.lambda-url.us-east-1.on.aws/',
                'https://swoztkmizkdrgo6kwqnubx7zqy0axqne.lambda-url.us-east-1.on.aws/',
                'https://bruu4ufxhynlqtnbhczv3mdxpq0ckkvm.lambda-url.us-east-1.on.aws/',
                'https://wxgjriaxwe3zwpx7qwfyfbbizi0srlvr.lambda-url.us-east-1.on.aws/',
                'https://2fyrvclcxmg5xjaga35pr76vhm0lyqws.lambda-url.us-east-1.on.aws/',
                'https://b4ymcbihbumuu4vjcj3skunug40zhjtd.lambda-url.us-east-1.on.aws/',
                'https://izqjvti6fv4nudhyopaeiksku40drdtu.lambda-url.us-east-1.on.aws/',
                'https://bhguocquvafpnheauoup7ylzba0kbfov.lambda-url.us-east-1.on.aws/',
                'https://cyc67g4bqes5fgcnglkevk4ytm0ntesv.lambda-url.us-east-1.on.aws/',
                'https://edyuklsnhlosrxr6fmotkfkoi40yzdut.lambda-url.us-east-1.on.aws/',
                'https://uylcsrvc2jrfvavusaww3d2iui0haprp.lambda-url.us-east-1.on.aws/',
                'https://eia6ugy35abq74qkzh4tea5mfy0uzqlg.lambda-url.us-east-1.on.aws/',
                'https://6jpb4qa76l3t6tg4atl42wjqdi0sahyo.lambda-url.us-east-1.on.aws/',
                'https://bscu2mkvp7sabovzpa66g7jhiu0waakd.lambda-url.us-east-1.on.aws/',
                'https://auyg6ifl2okkforyps6akdl2nu0cdtpx.lambda-url.us-east-1.on.aws/',
                'https://krfqvkj2xot3yweyhcbarrwwfy0pdiap.lambda-url.us-east-1.on.aws/',
                'https://edfmppbagwitqpcelejfyqoski0yanmx.lambda-url.us-east-1.on.aws/',
                'https://mc6mev6tq56fqfvmdkkhxidb6e0ujymq.lambda-url.us-east-1.on.aws/',
                'https://gpardfscnzctwj2lau5cltp3nm0grpro.lambda-url.us-east-1.on.aws/',
                'https://bej54is7mwvzh33rc7nc2cloim0yhztv.lambda-url.us-east-1.on.aws/',
                'https://ar6uiuqa6itnfh7zk4eu6j2klq0yqblj.lambda-url.us-east-1.on.aws/',
                'https://lsqk6sqqdhychyajeeqrnj2tiu0ydnde.lambda-url.us-east-1.on.aws/',
                'https://xogt75owsex4uksgrltxgfr4sq0dyhss.lambda-url.us-east-1.on.aws/',
                'https://tftb664a3u34ilzny2hjrdp4jm0gpkcr.lambda-url.us-east-1.on.aws/',
                'https://ujx3d42fokwn3m2gno3sknrhp40itbij.lambda-url.us-east-1.on.aws/',
                'https://i6tfywm4gk4sxjloimv42hfrvq0ktcxt.lambda-url.us-east-1.on.aws/',
                'https://rau7mjwzjxaisfubfuxxfceyoy0rynwu.lambda-url.us-east-1.on.aws/',
                'https://jyuidstmkxpffknys3mjztpcsu0dydil.lambda-url.us-east-1.on.aws/',
                'https://owtnqz25cmftlt26mcgskjmrxi0fqvur.lambda-url.us-east-1.on.aws/',
                'https://kv3ep67fwnct7ftlo2j6qahz7i0njgnn.lambda-url.us-east-1.on.aws/',
                'https://p7ztcr2nqnbq7alysq4hdrjy7y0yjkyy.lambda-url.us-east-1.on.aws/',
                'https://uycmsfifmuih2aylrzguejfkre0ysluv.lambda-url.us-east-1.on.aws/',
                'https://22gzanhpgv7ljpbjogjhjjuxae0fcvvd.lambda-url.us-east-1.on.aws/',
                'https://6i2qyx4bmyu5v7nbwti56z5smq0kotnw.lambda-url.us-east-1.on.aws/',
                'https://s7u7jjytf22fqewdwaruw63xfi0opcrl.lambda-url.us-east-1.on.aws/',
                'https://2zaepuzdli5yyt3plivfr5mohy0bpvbz.lambda-url.us-east-1.on.aws/',
                'https://fv3uhmwhq562psoimkknhcupum0lafed.lambda-url.us-east-1.on.aws/',
                'https://vyieo7w4xkwldyyzibkosc3u3q0jring.lambda-url.us-east-1.on.aws/',
                'https://ndb3d6hx2lfy5h6ax3mo2olsse0bhfyl.lambda-url.us-east-1.on.aws/',
                'https://qt3dmjxqemixgh5twtdz556aoy0nxjwx.lambda-url.us-east-1.on.aws/',
                'https://ujcf6bivxmdvqlm36epvwclsxi0huktt.lambda-url.us-east-1.on.aws/',
                'https://eu5lczeod5fl73novqodrakdbi0qmcnq.lambda-url.us-east-1.on.aws/',
                'https://w5fvhnyhv3fhy7cndz5vdoydaq0szcwy.lambda-url.us-east-1.on.aws/',
                'https://dx753fhtfdpjihebd74xfyr34i0exlro.lambda-url.us-east-1.on.aws/',
                'https://ziunjxonxlign2zesbutq3pe6y0itpqr.lambda-url.us-east-1.on.aws/',
                'https://tyg7zmtcj7fv6vh6kbzdd2gozm0ntpck.lambda-url.us-east-1.on.aws/',
                'https://eheedmye3mtc2eneyymzxjrqma0frdqm.lambda-url.us-east-1.on.aws/',
                'https://bvkwdkexywwtluj7yz3j4bu4qy0jytnf.lambda-url.us-east-1.on.aws/',
                'https://ql7rwn4pvfaek2thm7kuoyjt6a0boxur.lambda-url.us-east-1.on.aws/',
                'https://uoryr63elb67f23qienmafrc2m0shzvp.lambda-url.us-east-1.on.aws/',
                'https://rxszrydv4gwne3bhrmliccwxny0qpoxe.lambda-url.us-east-1.on.aws/',
                'https://mil2hqrdriytpibnihqj2qntd40oiuqh.lambda-url.us-east-1.on.aws/',
                'https://rtlhpfpk3hx7edhdibx3lh5ykq0crvlh.lambda-url.us-east-1.on.aws/',
                'https://3m7ck5hzvbfqtgenqkutw3yv4q0vujyz.lambda-url.us-east-1.on.aws/',
                'https://mspa4fvbo6gr65g2j3ldjznnyi0jzzpm.lambda-url.us-east-1.on.aws/',
                'https://wxheo4k3evo4ex6xjofjaxf4eu0pjjcl.lambda-url.us-east-1.on.aws/',
                'https://kuxwn7tpbzxf6iulac4trmr6ka0jghfp.lambda-url.us-east-1.on.aws/',
                'https://tg5f6xt7g5iiz7vlueoa64cuxm0jviom.lambda-url.us-east-1.on.aws/',
                'https://t27b657p7vrtwxhnhrzpijauvy0wxvjt.lambda-url.us-east-1.on.aws/',
                'https://v5vcaxrdncm3vlyepecabcucky0iermr.lambda-url.us-east-1.on.aws/',
                'https://m52jy7arfz4ah6ywf4cvbft3ha0lebpo.lambda-url.us-east-1.on.aws/',
                'https://t24gezyz2mp5rhz466b2o47gb40btvhs.lambda-url.us-east-1.on.aws/',
                'https://ouzc2jyjxhp2nhmqtmtczdlmre0dedam.lambda-url.us-east-1.on.aws/',
                'https://zmi7ubxjxmbyaulge62ispypai0zcrsm.lambda-url.us-east-1.on.aws/',
                'https://xj3wt6vqdxiq4nezy4oo4nr72e0simpn.lambda-url.us-east-1.on.aws/',
                'https://tbgrkvqniwriv5h4rq37dmp2me0wfksg.lambda-url.us-east-1.on.aws/',
                'https://vyu6fwryqf3z54sw7jjunrdz2i0ezrsr.lambda-url.us-east-1.on.aws/',
                'https://dloq6dsorbklhfvos7alx5qoma0cjajy.lambda-url.us-east-1.on.aws/',
                'https://xavyejicavl4dkynlpwzw4nxuq0hfqho.lambda-url.us-east-1.on.aws/',
                'https://pj244ufrc76skxopfffwejpyem0gwdzn.lambda-url.us-east-1.on.aws/',
                'https://s5btea5ckuzo7n2mwc4zlbcoou0epfiu.lambda-url.us-east-1.on.aws/',
                'https://xhxplwpnpwy23dh3kdyeitilca0nbmse.lambda-url.us-east-1.on.aws/',
                'https://3p65jslba6kc67m224wtdkgtke0wcnxj.lambda-url.us-east-1.on.aws/',
                'https://czidgeo5bjycsea5idb2jzpeoq0rqcia.lambda-url.us-east-1.on.aws/',
                'https://ciqq2tj2vumroy23y2qaqbqc2i0owyfe.lambda-url.us-east-1.on.aws/',
            ];
            console.log('🧠 Dynamic allocation: 1000 base stocks → 100 workers × 10 stocks each');
            console.log('📊 Processing 1000 stocks (100 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling workers for Russell 1000 stocks...');
            const workerPayloads = [];
            for (let i = 0; i < Math.min(allWorkerUrls.length, 100); i++) { // Use all 100 workers for 1000 stocks
                workerPayloads.push({ url: allWorkerUrls[i], payload: { worker_id: i + 1, batch_size: 10 }, workerId: i + 1 });
            }
            console.log(`📊 Using ${workerPayloads.length} workers for ${workerPayloads.length * 10} stocks`);
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.batch_size} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const results = await Promise.all(promises);
            const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
            let allResults = [];
            results.forEach(workerResult => {
                if (workerResult.result && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 Russell 1000 Analysis: ${allResults.length}/${workerPayloads.length * 10} stocks`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 1000, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'Russell1000_Complete_Screener');
            result = formatOption3Result(apiData, '5');
            result.csvData = csvData;

        } else if (option === 3 && subOption === '7') {
            console.log('🚀 OPTION 3.7 SMART SCALING - NASDAQ 100 Tech Stock Screener');
            const nasdaq100Universe = ['NVDA','AAPL','MSFT','AMZN','GOOGL','SPCX','GOOG','META','AVGO','TSLA','MU','AMD','WMT','ASML','INTC','PLTR','CSCO','COST','AMAT','LRCX','PANW','NFLX','ARM','CRWD','TXN','KLAC','MRVL','SNDK','AMGN','LIN','SHOP','ADI','GILD','QCOM','STX','PEP','TMUS','ISRG','WDC','FTNT','VRTX','BKNG','PDD','ADP','CEG','DDOG','SBUX','LITE','ABNB','SNPS','CDNS','MELI','MAR','ADBE','APP','MRNA','CSX','MNST','DASH','INTU','CTAS','MDLZ','REGN','CMCSA','ROST','ORLY','MPWR','AEP','HON','TER','MSTR','NBIS','ALAB','FAST','NXPI','PCAR','BKR','FANG','HONA','ADSK','PYPL','XEL','CCEP','CRWV','WDAY','TRI','RKLB','KDP','EXC','MCHP','IDXX','TTWO','ODFL','PAYX','FER','ROP','AXON','DXCM','ALNY','GEHC','CPRT'];
            const allWorkerUrls = [
                'https://522jr4z2s7sxppxjpxsxs3wbaq0ifsve.lambda-url.us-east-1.on.aws/',
                'https://argv7wfeqoxd63pjvlk2btgu6y0ikqkl.lambda-url.us-east-1.on.aws/',
                'https://achfptgbrn5t2godpzbc2ukbve0fufie.lambda-url.us-east-1.on.aws/',
                'https://evc43jaybk4ibkkkbbjslrmfrm0qccbo.lambda-url.us-east-1.on.aws/',
                'https://4bnwvfcnbbeoh6yckzu5gdfcse0wgnkl.lambda-url.us-east-1.on.aws/',
                'https://6jz4q6ubw6ggwrlfksid7b6z2q0lkbjw.lambda-url.us-east-1.on.aws/',
                'https://mzia3uzyzwqdgji57hpzillmpa0vlwmo.lambda-url.us-east-1.on.aws/',
                'https://u637oomkd52o57kxz5izekfnpi0dpbiq.lambda-url.us-east-1.on.aws/',
                'https://saecx4cms7zq655v47pheflzga0fator.lambda-url.us-east-1.on.aws/',
                'https://nht4utoktc2apuxaokqqmvauvi0vassn.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 100 base stocks → 10 workers × 10 stocks each');
            console.log('📊 Processing 100 stocks (10 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 10 workers for 100 NASDAQ stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 10; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(nasdaq100Universe.length / (10)));
                const startIdx = i * perWorker;
                const stockBatch = nasdaq100Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 10/10 workers for 100 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.stock_batch.length} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 10 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 NASDAQ 100 Analysis: ${allResults.length}/100 stocks (${((allResults.length/100)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 100, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'NASDAQ_100_Tech_Screener');
            result = formatOption3Result(apiData, '7');
            result.csvData = csvData;
        } else if (option === 3 && subOption === '8') {
            console.log('🎆 OPTION 3.8 SMART SCALING - Dow Jones 30 Blue Chip Screener');
            const dow30Universe = ['GS','CAT','MSFT','AMGN','V','UNH','TRV','GOOGL','AAPL','JPM','SHW','AXP','HD','AMZN','JNJ','MCD','NVDA','CRM','IBM','CVX','HON','BA','MMM','PG','MRK','CSCO','WMT','DIS','KO','NKE'];
            const allWorkerUrls = [
                'https://5tuk56sksvrka5m56epcchxciy0yhsvo.lambda-url.us-east-1.on.aws/',
                'https://et6use2hjiidm3xxt2xidrhx2m0rogyr.lambda-url.us-east-1.on.aws/',
                'https://uhrbaqx53y4fyfvy3xc2wcuvoe0csuby.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 30 base stocks → 3 workers × 10 stocks each');
            console.log('📊 Processing 30 stocks (3 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 3 workers for 30 Dow Jones stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 3; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(dow30Universe.length / (3)));
                const startIdx = i * perWorker;
                const stockBatch = dow30Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 3/3 workers for 30 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.stock_batch.length} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 3 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 Dow Jones 30 Analysis: ${allResults.length}/30 stocks (${((allResults.length/30)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 30, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'Dow_Jones_30_Screener');
            result = formatOption3Result(apiData, '8');
            result.csvData = csvData;
        } else if (option === 3 && subOption === '6') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 3.6 SMART SCALING - Russell 2000 Small-Cap Stock Screener');
            // Russell 2000 uses worker_id to determine which stocks to process
            const russell2000Universe = null; // Workers load their own stock batches
            const allWorkerUrls = [
                'https://dajebkuzzhxelqjyqox2yamzpi0bdwng.lambda-url.us-east-1.on.aws/',
                'https://zqekaidwcsozg5nzdajokbsena0gktek.lambda-url.us-east-1.on.aws/',
                'https://q5kxtni3logikmuhhwa7hx6uwy0mjivl.lambda-url.us-east-1.on.aws/',
                'https://ek57cyfcilzzyrupnjdirody4i0dybzc.lambda-url.us-east-1.on.aws/',
                'https://et7gfs355jzl6zpm2euwohs7oe0aymtb.lambda-url.us-east-1.on.aws/',
                'https://mzgkofeebyqdqkz4ysf6r4kmha0pxguu.lambda-url.us-east-1.on.aws/',
                'https://6zfzrbzezxoqpvwnthgx3ew56u0prxnr.lambda-url.us-east-1.on.aws/',
                'https://qlj3cr6xeeiilyeupuiass5opq0ptuji.lambda-url.us-east-1.on.aws/',
                'https://e2isagh5xiqfk5x6zhivccocsm0tzwps.lambda-url.us-east-1.on.aws/',
                'https://nkeq47jhevudeqvoex3cxqiugy0vcydl.lambda-url.us-east-1.on.aws/',
                'https://khzjq7uiryqf5imk74ahufq3cm0wjzdf.lambda-url.us-east-1.on.aws/',
                'https://4owrbukhttgx3qig3ba5srfgv40dcuzr.lambda-url.us-east-1.on.aws/',
                'https://ue632bwjgnsvg53ur2q4ddtwue0ulupo.lambda-url.us-east-1.on.aws/',
                'https://lidspryi3hcw3ftca5qmcnytsi0smhra.lambda-url.us-east-1.on.aws/',
                'https://u5caktkutp7ksjj5duifxdnypi0wbnes.lambda-url.us-east-1.on.aws/',
                'https://hsnyrtlwse2udyxnmjyalwma3u0sviln.lambda-url.us-east-1.on.aws/',
                'https://ptuime4ad4kxskdu4ielqkafsu0gljqu.lambda-url.us-east-1.on.aws/',
                'https://dab2xzhyq3lf5wczgacbnbrrsm0klvme.lambda-url.us-east-1.on.aws/',
                'https://mjh5woagnhjf6hw66ivmdvvkfu0hcyzu.lambda-url.us-east-1.on.aws/',
                'https://qq6lp75rq3sh5ygu456agb2vsa0clqko.lambda-url.us-east-1.on.aws/',
                'https://hi6vfo2kjurzoef55p2no6bhda0uujyx.lambda-url.us-east-1.on.aws/',
                'https://3q3p5ndazd3kvuz74lcyuosvyq0rnpji.lambda-url.us-east-1.on.aws/',
                'https://s6o7xki32y5w6eiih4uiwkpduu0pyeis.lambda-url.us-east-1.on.aws/',
                'https://e6wl6c55pu5zqhctpj3eqlbzu40hwjsa.lambda-url.us-east-1.on.aws/',
                'https://lvfpkbk2itejrs4hd4h22ha3740yjbuz.lambda-url.us-east-1.on.aws/',
                'https://pweouzmop4jevvwvebe3ctto2m0hqepa.lambda-url.us-east-1.on.aws/',
                'https://m27jy56avlx7uzz3fwaghvhynm0tiodd.lambda-url.us-east-1.on.aws/',
                'https://sy5gky3chuokwtw3v3t2bmhjh40cjrep.lambda-url.us-east-1.on.aws/',
                'https://tiktkzosmixugvom4dtlk2ygia0ppfrm.lambda-url.us-east-1.on.aws/',
                'https://g56wyyyy4crnujmfjn6q3cpdyu0fakyn.lambda-url.us-east-1.on.aws/',
                'https://boa2krwbztgiod7t73xpir3jhu0jhqcs.lambda-url.us-east-1.on.aws/',
                'https://bwifsbjnhqersrmjqa3eacauly0ggbuh.lambda-url.us-east-1.on.aws/',
                'https://bt6jrmvntbptrtnuupmr2jfnpm0uaici.lambda-url.us-east-1.on.aws/',
                'https://acnoqhbhvjpdo5dd4yp63qyfve0twfhw.lambda-url.us-east-1.on.aws/',
                'https://mycqbbaayn7nmv5nlvri2d5acq0csrdl.lambda-url.us-east-1.on.aws/',
                'https://lpox3ef4tm26wetjmgwwfnhuja0skzds.lambda-url.us-east-1.on.aws/',
                'https://lwwk63z7o3ebv2qfhl7c6xc4ce0wpada.lambda-url.us-east-1.on.aws/',
                'https://tamees4gszomcy5ijyjdcrcbb40aigqe.lambda-url.us-east-1.on.aws/',
                'https://jkpmfm34glimfrvfwrxfsmaktu0kfhem.lambda-url.us-east-1.on.aws/',
                'https://xmotrhb4ujouhu5celm7epaet40shqmm.lambda-url.us-east-1.on.aws/',
                'https://kykz3gypjqft56aputsrfb77xm0yqzkx.lambda-url.us-east-1.on.aws/',
                'https://ubaeyafyrtwev7olc26iyeey6u0jxvna.lambda-url.us-east-1.on.aws/',
                'https://ubz4qpawk7xc7p5xiqxdmv42ea0kbbmq.lambda-url.us-east-1.on.aws/',
                'https://q6uv2pzimgmjqs5oyi4nwerawm0ejttt.lambda-url.us-east-1.on.aws/',
                'https://js64dp6dnysqvebgyuc6xf5t3i0dlrlv.lambda-url.us-east-1.on.aws/',
                'https://y2sh6byeyzhqrv5spuztd5ohwu0dwsfs.lambda-url.us-east-1.on.aws/',
                'https://46hydns4q637lg2cfuwitzmrmu0syofa.lambda-url.us-east-1.on.aws/',
                'https://7dw3el4komu5zxq66knig23xia0yyhic.lambda-url.us-east-1.on.aws/',
                'https://q7gy2rxjkz3kkclg47lfkcv3am0bzcpi.lambda-url.us-east-1.on.aws/',
                'https://ufgttmrqpq34exwt2hrghcza2a0cwrxo.lambda-url.us-east-1.on.aws/',
                'https://qsismttxbmrkqnfszdtna6xg7i0szafr.lambda-url.us-east-1.on.aws/',
                'https://xt2r7xlfys5y25yaqs3n7zi7iq0nwrvr.lambda-url.us-east-1.on.aws/',
                'https://flzdlkpdvtneyycezj66xlioue0nndjp.lambda-url.us-east-1.on.aws/',
                'https://zswpm34g2fnytcqu775s3deyxu0qcwbw.lambda-url.us-east-1.on.aws/',
                'https://zimir5qddnmcl5f4chlhkv4xiy0diofi.lambda-url.us-east-1.on.aws/',
                'https://sfb7awtd6znp6aofhrvkijdugq0bevfg.lambda-url.us-east-1.on.aws/',
                'https://e6nk2syytmknvfaougjx7qagza0bbacl.lambda-url.us-east-1.on.aws/',
                'https://i2k6futdfz2yyatkbzocaahrmu0wfxir.lambda-url.us-east-1.on.aws/',
                'https://bfzjjzu56ha7fssg6xduhzsmnm0gcjjm.lambda-url.us-east-1.on.aws/',
                'https://iucm2ec36y27hvk2kib4ailc2e0xefbj.lambda-url.us-east-1.on.aws/',
                'https://emo5ueafuazgwupfa7k26ksxu40ampus.lambda-url.us-east-1.on.aws/',
                'https://tvu4t5uimnbk46muxc62n4yiqu0adqml.lambda-url.us-east-1.on.aws/',
                'https://nifn6jpeyuasipitvnp7djiqiq0xmvvd.lambda-url.us-east-1.on.aws/',
                'https://hwuvllkpycg3zagxxe5az7cz5q0iqynm.lambda-url.us-east-1.on.aws/',
                'https://wnjh7s2yl45we4nnl36gsjtgye0rezjb.lambda-url.us-east-1.on.aws/',
                'https://uxogwdpeilpbbtjx2bkd7w3uda0ivloe.lambda-url.us-east-1.on.aws/',
                'https://emd7mcxksgsrbeqt7ms3zxdkpa0ozvli.lambda-url.us-east-1.on.aws/',
                'https://7c763is4f5gwehjydi2q6xdh5u0fsaou.lambda-url.us-east-1.on.aws/',
                'https://xqb3xobwk3w3l7pinqq4jz2o4m0muhrp.lambda-url.us-east-1.on.aws/',
                'https://h5srfkg43mkmsmg6h73eotme7e0hgtcx.lambda-url.us-east-1.on.aws/',
                'https://whjsrynn25y3u7wiv4zb4pfjju0zmull.lambda-url.us-east-1.on.aws/',
                'https://rf3huiezkqi5i54db5pkozz7te0ygegi.lambda-url.us-east-1.on.aws/',
                'https://df5625qfykcbfl5rrv3kxdnx6e0yamep.lambda-url.us-east-1.on.aws/',
                'https://77styax2uwqkwa2mek3kvq44la0usbtm.lambda-url.us-east-1.on.aws/',
                'https://g5munbz4x2meg5tkm4hx2xhzxq0pbyeo.lambda-url.us-east-1.on.aws/',
                'https://7fcw7ksdlffe2v4cn7mot2t63e0ewrkh.lambda-url.us-east-1.on.aws/',
                'https://v6xxv3lajfkasw4ymtlivjmlkq0rxzxa.lambda-url.us-east-1.on.aws/',
                'https://fpwlggsctuqc7xnez6tyytruum0wkbsp.lambda-url.us-east-1.on.aws/',
                'https://vnxi6i3xtrwtlzytvyt4ygoo4q0cshas.lambda-url.us-east-1.on.aws/',
                'https://vtrjx4bserpo3dg3bj42sxbkzq0ctoxe.lambda-url.us-east-1.on.aws/',
                'https://mdov7hxbndxbwvqfmnxu2zumpi0tzuse.lambda-url.us-east-1.on.aws/',
                'https://crllbkwlkb6n3mlnzizxajx7xm0lqydq.lambda-url.us-east-1.on.aws/',
                'https://xqgussoemrg57qezewg23axn4m0rrkkb.lambda-url.us-east-1.on.aws/',
                'https://gdzouvcgs2osnlfuhbpv37m55y0afhwy.lambda-url.us-east-1.on.aws/',
                'https://ntskpubnvhr7ifd47s2omwo2tm0yaovb.lambda-url.us-east-1.on.aws/',
                'https://eb74dt32psuwbznhza7l6sr63u0uhhyj.lambda-url.us-east-1.on.aws/',
                'https://gz7fwwiwrrxdykzcl6yfql2tbe0tduui.lambda-url.us-east-1.on.aws/',
                'https://n7z6caxke7ruav2wq4bj4f4tem0uhewx.lambda-url.us-east-1.on.aws/',
                'https://rs67dxtgvli7ya6xgi3t6lzw7e0olrkr.lambda-url.us-east-1.on.aws/',
                'https://3q77sge6pofekixewb2a4egmre0rypfb.lambda-url.us-east-1.on.aws/',
                'https://6sq2npvl7pkjrlupijty5eebum0kmztw.lambda-url.us-east-1.on.aws/',
                'https://guqawoabz2m4ve7x2cj7467sym0ubweg.lambda-url.us-east-1.on.aws/',
                'https://xtmksdolz2ojc46wcczko3atpa0huwee.lambda-url.us-east-1.on.aws/',
                'https://46glwnwijaqyuiad5nmt66zkvi0xriuc.lambda-url.us-east-1.on.aws/',
                'https://z5eejvdnnyb5csypc25w5yqzgy0tgwwx.lambda-url.us-east-1.on.aws/',
                'https://zi6c6njmkdafbak2v3xbf2ub2i0tewrs.lambda-url.us-east-1.on.aws/',
                'https://fbekdzuazk22bcbzy3zjk6ohzu0ymecc.lambda-url.us-east-1.on.aws/',
                'https://duiaqs7yg5wt3hremjbndpdreq0ewkcp.lambda-url.us-east-1.on.aws/',
                'https://2lp3yohrtngqduund5asdsajpm0efydq.lambda-url.us-east-1.on.aws/',
                'https://lpmtm7y7bbgeiv7g3ls6eowcoq0ieiur.lambda-url.us-east-1.on.aws/',
                'https://pplyivvk42yfpbhpdzhlk26i4a0lwtum.lambda-url.us-east-1.on.aws/',
                'https://eeckjync5pqjd3f4y3j32psacu0eniju.lambda-url.us-east-1.on.aws/',
                'https://p764duvdrcuv7spynexyaugzhm0pllya.lambda-url.us-east-1.on.aws/',
                'https://oqhdrlfve6vfieerlqss6e2poy0jqgzt.lambda-url.us-east-1.on.aws/',
                'https://2qoc2j35kbbdr73tmhm6zfyvze0rptsi.lambda-url.us-east-1.on.aws/',
                'https://3uwe56zoq3irfmddxjmzgflime0xsfnb.lambda-url.us-east-1.on.aws/',
                'https://oe64fgrhuvgto5idadgwsbdia40kxomc.lambda-url.us-east-1.on.aws/',
                'https://qz7ue52wd5d4hoifb3y2h4rpxq0wwcut.lambda-url.us-east-1.on.aws/',
                'https://sz3emnpr3kyxutwp43l3hpnuly0woilu.lambda-url.us-east-1.on.aws/',
                'https://udwnzjalgujpzp7npesfn5mvzu0lwipl.lambda-url.us-east-1.on.aws/',
                'https://mom47kvzcyifoeree7p6knqnqe0xtqla.lambda-url.us-east-1.on.aws/',
                'https://77im5mgxop6nunha7kuk2mwt4m0qupyh.lambda-url.us-east-1.on.aws/',
                'https://rel4su5csxeyirwg5z3ugfp6xy0lozfm.lambda-url.us-east-1.on.aws/',
                'https://otv2xjy7h3voji75rnnmlvfl2i0qlltp.lambda-url.us-east-1.on.aws/',
                'https://oqyvcdtcjszixgkfwtevblqavq0ojnlw.lambda-url.us-east-1.on.aws/',
                'https://uat7din5m3qz7fadutclo7ufv40kucxw.lambda-url.us-east-1.on.aws/',
                'https://32y6f2zzvuvqnvo23vvqkmixi40agaiq.lambda-url.us-east-1.on.aws/',
                'https://zk75ta2x42ro3rpp6zdbatvhvq0fupre.lambda-url.us-east-1.on.aws/',
                'https://t5ldzxjpady3xsqksnzqhftlbq0xzaes.lambda-url.us-east-1.on.aws/',
                'https://n5qrpckvdjsg6jmglgkp24i6iy0dlead.lambda-url.us-east-1.on.aws/',
                'https://xh7y7ectbqsghxkfgbnn7xfvl40wkczh.lambda-url.us-east-1.on.aws/',
                'https://uksf3uicx4fq6btyypzmumy34u0ukbxu.lambda-url.us-east-1.on.aws/',
                'https://csexutjqgpdmzjhe745amy4w7i0hvlpf.lambda-url.us-east-1.on.aws/',
                'https://woshuvuwi255mfnamkkb4rjbue0jqqgr.lambda-url.us-east-1.on.aws/',
                'https://jyinqhfhv4fmyvvopx6pddn37a0tnjpm.lambda-url.us-east-1.on.aws/',
                'https://xxcz4bc46lt37v5uvev4fw3cqe0mowux.lambda-url.us-east-1.on.aws/',
                'https://eoqqb25fts4evhw3hcyayavyva0oxsot.lambda-url.us-east-1.on.aws/',
                'https://ccvmnyymwoikh6azv6hctoof2y0nhkml.lambda-url.us-east-1.on.aws/',
                'https://abnkh3ee37pdyre7e2vki4l7bi0qqynt.lambda-url.us-east-1.on.aws/',
                'https://fz2pwqmwgnrt4d4dr3ch3ubkxi0gooki.lambda-url.us-east-1.on.aws/',
                'https://saz423nh4np2l6ywjily5ao6440wkwvf.lambda-url.us-east-1.on.aws/',
                'https://pne7zcief5h7r56ep4eebo2uay0dhfvy.lambda-url.us-east-1.on.aws/',
                'https://qw7eaiejpf4vy4e37isaz2xu240ecxmz.lambda-url.us-east-1.on.aws/',
                'https://xpbwx4hjvh5ik6qdomt24o5d3q0okggp.lambda-url.us-east-1.on.aws/',
                'https://xglha5p2ub7qihzjt6cgpghwei0dhqpa.lambda-url.us-east-1.on.aws/',
                'https://ucsbq7ssiyve3mrounjfvwnoaa0ndwof.lambda-url.us-east-1.on.aws/',
                'https://7ilvonzspkrkqleb2jlfrjdb2i0mbvwt.lambda-url.us-east-1.on.aws/',
                'https://yygni2gskhrr3jvqduvoefypei0ldrzb.lambda-url.us-east-1.on.aws/',
                'https://y53bl6bka4mc7rmbsv5meq5ssu0nlwsn.lambda-url.us-east-1.on.aws/',
                'https://jg74cxsot3ptdzu4gmcv6cw7uy0pqgma.lambda-url.us-east-1.on.aws/',
                'https://xnqd5t2df7zx4l2pck7qmwiqfy0amqxn.lambda-url.us-east-1.on.aws/',
                'https://6mhivsl3hqx6axhrozvsptrjae0chaqs.lambda-url.us-east-1.on.aws/',
                'https://dzk6n2wkefjglztyrwwzcjn6ku0bscqa.lambda-url.us-east-1.on.aws/',
                'https://v3m57rx5lfzpd3gljfk762csri0gnvse.lambda-url.us-east-1.on.aws/',
                'https://goormqpugvzfh3vvfemkqm2ika0pnvbz.lambda-url.us-east-1.on.aws/',
                'https://vjc4pvrox62ibvxxfysvg5aguq0ulwzv.lambda-url.us-east-1.on.aws/',
                'https://sslqwtqhkx3swjbuphiitvu3740wpfxy.lambda-url.us-east-1.on.aws/',
                'https://5ca2va7m7qpuwfmc7caudn3pmi0dwrqr.lambda-url.us-east-1.on.aws/',
                'https://htft6wtwrjhlxh2vgxgl4sq2m40btorv.lambda-url.us-east-1.on.aws/',
                'https://v326wsm6kqgvw24tsg3ssrwgjm0qalqj.lambda-url.us-east-1.on.aws/',
                'https://7lgzudncllzzc362lkcdhmrzkm0vjexg.lambda-url.us-east-1.on.aws/',
                'https://zvehfywgyx23cp2uc3j4yrwvwy0rvnxn.lambda-url.us-east-1.on.aws/',
                'https://7gcpsylgu2ena3d3ogsrobzmau0mfxbl.lambda-url.us-east-1.on.aws/',
                'https://ujjkbjuty6ai5z34fuo3xpjhvy0pvtqy.lambda-url.us-east-1.on.aws/',
                'https://n5sgmkch257n5k3lk7pv7sgzq40kuytz.lambda-url.us-east-1.on.aws/',
                'https://cqyf6ybtokfoojvjwnyg4we2qe0poxwb.lambda-url.us-east-1.on.aws/',
                'https://zbfgrzaspsloguvkuoywz7vt2i0wputv.lambda-url.us-east-1.on.aws/',
                'https://pom37mqpivu7syaeuow75mrppq0vmbuy.lambda-url.us-east-1.on.aws/',
                'https://qk4ri4nu4tsbcindncz3uk2ceq0mrgva.lambda-url.us-east-1.on.aws/',
                'https://o2hm6fsndf4r7v5vhdeshrjrw40rmnfg.lambda-url.us-east-1.on.aws/',
                'https://fty3skzv4fxw42innqbyt2ykfe0svwva.lambda-url.us-east-1.on.aws/',
                'https://cmeoo7ixwwgi5vtiakl7pqelvi0kksqc.lambda-url.us-east-1.on.aws/',
                'https://brtadcjcplnxqb24pnyadu2p7i0xachz.lambda-url.us-east-1.on.aws/',
                'https://mukgtiyplrfmxlf3zvhv36kxx40ddvyw.lambda-url.us-east-1.on.aws/',
                'https://ro3ruf2he27kwc3i3tozrbrk540jkwwt.lambda-url.us-east-1.on.aws/',
                'https://2hmiynokkryw5ywclbs4ymepwi0mdedw.lambda-url.us-east-1.on.aws/',
                'https://ykfnx32crzbrxdjdqggo7jz4xa0yfutg.lambda-url.us-east-1.on.aws/',
                'https://l3zksq7yi3j7ggevu5ja3rja7e0rywim.lambda-url.us-east-1.on.aws/',
                'https://daeiqqoafink5rhqqunfvl67xa0hzfon.lambda-url.us-east-1.on.aws/',
                'https://tegawl376z7qo3ycg666vjnkjy0vivvl.lambda-url.us-east-1.on.aws/',
                'https://j7grsoxbfbhtufvpbdpybx6r3m0lmpsl.lambda-url.us-east-1.on.aws/',
                'https://btm4fiji2zsqwygh7qpcqkhrvq0yfhir.lambda-url.us-east-1.on.aws/',
                'https://7wz4l46iabzvkoxc37s4iesseu0wzhir.lambda-url.us-east-1.on.aws/',
                'https://tkwxv3fxml7hoflphu6g7r732u0szdwf.lambda-url.us-east-1.on.aws/',
                'https://gimn4etl3ntsfkbdo2ujqrotvq0ktwqn.lambda-url.us-east-1.on.aws/',
                'https://k4e5rd44ofpitd667gl7nr2gzy0lvohc.lambda-url.us-east-1.on.aws/',
                'https://2qqlzd37pehhdpqciovdkr7xvm0fcojn.lambda-url.us-east-1.on.aws/',
                'https://nczrm2cynn7ungggjmxpflpy2i0odytb.lambda-url.us-east-1.on.aws/',
                'https://zqfskhw5hipxkurc4gz56eby2q0dmufl.lambda-url.us-east-1.on.aws/',
                'https://cbfc6e57gcxxyz6yxd6jufp4wi0qpimy.lambda-url.us-east-1.on.aws/',
                'https://b3ti43iif4hjn22uj373ku7ufq0tpura.lambda-url.us-east-1.on.aws/',
                'https://4kvlzkkmv6dqml3qk4hzxohcuu0mmiei.lambda-url.us-east-1.on.aws/',
                'https://zqmltdjkmzxcum3fwv4rpa7umu0gnjvt.lambda-url.us-east-1.on.aws/',
                'https://c2qq3yynynwtgmtymtrlkx35sm0fhltc.lambda-url.us-east-1.on.aws/',
                'https://nyholcuvv6pxt4d4yowrjm5swi0jydav.lambda-url.us-east-1.on.aws/',
                'https://qmatr3ot6j7jfeyh2netfqygla0mdtqq.lambda-url.us-east-1.on.aws/',
                'https://uofsbujllyfmjpq7a4ugeh4opy0jwmdy.lambda-url.us-east-1.on.aws/',
                'https://fdgw65qcmmlueva4kzny24l3vq0hdzyq.lambda-url.us-east-1.on.aws/',
                'https://wdlldiprda7v3zvoivm5gqlxzu0byyla.lambda-url.us-east-1.on.aws/',
                'https://bfrrgmbh6jptlqtkeqng5sqkgm0boakc.lambda-url.us-east-1.on.aws/',
                'https://fa6ubaw25gvuu74brhgajysuem0irygc.lambda-url.us-east-1.on.aws/',
                'https://gsqmf5mxgokwyqtc6alsehgpqi0uwlzv.lambda-url.us-east-1.on.aws/',
                'https://h47dmhxdewngq4mwsxwzf5zhli0tgzpa.lambda-url.us-east-1.on.aws/',
                'https://dxiflcmixstffy5l2eoq52jimy0bjpkv.lambda-url.us-east-1.on.aws/',
                'https://7gx6g2svnlqoyhdkdvh754hu640xuujf.lambda-url.us-east-1.on.aws/',
                'https://l23driap7o63b3htelnmrclc7e0bfnen.lambda-url.us-east-1.on.aws/',
                'https://fu7zl3h244yof6pfk3wmnbcoii0edfbp.lambda-url.us-east-1.on.aws/',
                'https://roh4tytowbhtsufkqqqw5wy5du0mfnil.lambda-url.us-east-1.on.aws/',
                'https://kfci3noufdpt3i6noxuv4njqri0tlytc.lambda-url.us-east-1.on.aws/',
                'https://zg2tdoctonrbqb4rejudoabwci0adbjs.lambda-url.us-east-1.on.aws/',
            ];
            console.log('🧠 Dynamic allocation: 2000 base stocks → 200 workers × 10 stocks each');
            console.log('📊 Processing 2000 stocks (200 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling workers for Russell 2000 stocks...');
            const workerPayloads = [];
            for (let i = 0; i < Math.min(allWorkerUrls.length, 200); i++) { // Use 200 workers for 2000 stocks
                workerPayloads.push({ url: allWorkerUrls[i], payload: { worker_id: i + 1, batch_size: 10 }, workerId: i + 1 });
            }
            console.log(`📊 Using ${workerPayloads.length} workers for ${workerPayloads.length * 10} stocks`);
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.batch_size} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const results = await Promise.all(promises);
            const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
            let allResults = [];
            results.forEach(workerResult => {
                if (workerResult.result && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 Russell 2000 Analysis: ${allResults.length}/${workerPayloads.length * 10} stocks`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 2000, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'Russell2000_Complete_Screener');
            result = formatOption3Result(apiData, '6');
            result.csvData = csvData;

        } else if (option === 5 && subOption === '50') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 5.1 SMART SCALING - ASX 50 Stock Screener');
            const asx50Universe = ['ALL.AX','AMC.AX','ANZ.AX','BHP.AX','BXB.AX','CAR.AX','CBA.AX','COH.AX','COL.AX','CPU.AX','CSL.AX','EVN.AX','FMG.AX','FPH.AX','GMG.AX','IAG.AX','JBH.AX','JHX.AX','LYC.AX','MPL.AX','MQG.AX','NAB.AX','NEM.AX','NST.AX','NWS.AX','ORG.AX','PME.AX','QAN.AX','QBE.AX','REA.AX','RIO.AX','RMD.AX','S32.AX','SCG.AX','SGH.AX','SGP.AX','SIG.AX','SOL.AX','STO.AX','SUN.AX','TCL.AX','TLS.AX','VAS.AX','WBC.AX','WES.AX','WDS.AX','WOW.AX','XRO.AX','XYZ.AX'];
            const allWorkerUrls = [
                'https://ph2koddgkibjl3wujln3zlde6q0vahci.lambda-url.us-east-1.on.aws/',
                'https://cfkugbbpzftz2sydotebdfbp2u0wthxz.lambda-url.us-east-1.on.aws/',
                'https://mfsznkzz5segvhk67tbx4mk6w40zzlvg.lambda-url.us-east-1.on.aws/',
                'https://ivbqyey3lpsin3xn5w56sxklvq0ladtw.lambda-url.us-east-1.on.aws/',
                'https://226ww6ocvpgd446wct3xhsqsgu0wgowy.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 50 base stocks → 5 workers × 10 stocks each');
            console.log('📊 Processing 50 stocks (5 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 5 workers for 50 ASX stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 5; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(asx50Universe.length / (5)));
                const startIdx = i * perWorker;
                const stockBatch = asx50Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 5/5 workers for 50 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.batch_size} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 5 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 ASX 50 Analysis: ${allResults.length}/50 stocks (${((allResults.length/50)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 50, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'ASX_50_Screener');
            result = formatASXResult(apiData, subOption);
            result.csvData = csvData;
        } else if (option === 5 && subOption === '100') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 5.2 SMART SCALING - ASX 100 Stock Screener');
            const asx100Universe = ['CBA.AX','BHP.AX','WBC.AX','ANZ.AX','WES.AX','MQG.AX','NAB.AX','CSL.AX','WDS.AX','FMG.AX','TLS.AX','RIO.AX','GMG.AX','WOW.AX','TCL.AX','QBE.AX','NST.AX','BXB.AX','SIG.AX','COL.AX','ALL.AX','EVN.AX','STO.AX','ORG.AX','REA.AX','S32.AX','LYC.AX','RMD.AX','FPH.AX','SCG.AX','IAG.AX','SUN.AX','SGH.AX','PLS.AX','CPU.AX','SOL.AX','NEM.AX','APA.AX','QAN.AX','WTC.AX','XRO.AX','PME.AX','MPL.AX','TLC.AX','JHX.AX','BSL.AX','AIA.AX','COH.AX','VCX.AX','YAL.AX','ALQ.AX','MIN.AX','ASX.AX','SGP.AX','SHL.AX','LNW.AX','IFT.AX','ORI.AX','RHC.AX','TNE.AX','CHC.AX','GGP.AX','CAR.AX','GPT.AX','AMC.AX','AFI.AX','REH.AX','TPG.AX','ALD.AX','JBH.AX','SFR.AX','WHC.AX','MCY.AX','NXT.AX','PRU.AX','RMS.AX','AZJ.AX','A2M.AX','MGR.AX','GMD.AX','APE.AX','AGL.AX','HUB.AX','ARG.AX','DXS.AX','ALX.AX','IGO.AX','HVN.AX','MEZ.AX','BEN.AX','CDA.AX','EDV.AX','CGF.AX','WGX.AX','DNL.AX','WOR.AX','LTR.AX','GQG.AX','NWL.AX'];
            const allWorkerUrls = [
                'https://pt6gjtfjbmvd5gvzzgpr7exyq40jdgft.lambda-url.us-east-1.on.aws/',
                'https://y6w3gnwzwyylnrffntv4jltxga0ayscs.lambda-url.us-east-1.on.aws/',
                'https://u4rw4bf25qouie2r4x4t3te6ty0zkefj.lambda-url.us-east-1.on.aws/',
                'https://fpt5i57mdacde2c7i4d424crqe0pplxx.lambda-url.us-east-1.on.aws/',
                'https://v2dphlet5zpjgs4n2zdyszneaq0gnwgf.lambda-url.us-east-1.on.aws/',
                'https://jmjxar6kkiwxy2nlvkaawyniby0itfoh.lambda-url.us-east-1.on.aws/',
                'https://qdtxs3h2u42hloqisbluv25xqq0riyrn.lambda-url.us-east-1.on.aws/',
                'https://pwsecih7aybzcjweigzdqemkoq0yidng.lambda-url.us-east-1.on.aws/',
                'https://m7brwtlpgosupso2be5mtwjmgu0ztctq.lambda-url.us-east-1.on.aws/',
                'https://voabf7i5mfv4hxfskfxstmty5m0onvwc.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 100 base stocks → 10 workers × 10 stocks each');
            console.log('📊 Processing 100 stocks (10 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 10 workers for 100 ASX stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 10; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(asx100Universe.length / (10)));
                const startIdx = i * perWorker;
                const stockBatch = asx100Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i % allWorkerUrls.length], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 10/10 workers for 100 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.batch_size} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 10 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 ASX 100 Analysis: ${allResults.length}/100 stocks (${((allResults.length/100)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 100, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'ASX_100_Screener');
            result = formatASXResult(apiData, subOption);
            result.csvData = csvData;
        } else if (option === 5 && subOption === '200') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 5.3 SMART SCALING - ASX 200 Stock Screener');
            const asx200Universe = ['360.AX','4DX.AX','A2M.AX','AAI.AX','AFI.AX','AGL.AX','AIA.AX','ALD.AX','ALK.AX','ALL.AX','ALQ.AX','ALX.AX','AMC.AX','AMP.AX','ANN.AX','ANZ.AX','APA.AX','APE.AX','ARB.AX','ARG.AX','ASB.AX','ASX.AX','AUB.AX','AZJ.AX','BEN.AX','BFL.AX','BGA.AX','BGL.AX','BHP.AX','BOQ.AX','BPT.AX','BRG.AX','BSL.AX','BWP.AX','BXB.AX','CAR.AX','CBA.AX','CDA.AX','CEN.AX','CGF.AX','CHC.AX','CIA.AX','CIP.AX','CLW.AX','CMM.AX','CNU.AX','COH.AX','COL.AX','CPU.AX','CQR.AX','CSC.AX','CSL.AX','CTD.AX','CWY.AX','CYL.AX','DBI.AX','DNL.AX','DOW.AX','DRO.AX','DRR.AX','DXS.AX','DYL.AX','EBO.AX','EDV.AX','EMR.AX','EOS.AX','EVN.AX','EVT.AX','FBU.AX','FLT.AX','FMG.AX','FPH.AX','FRW.AX','GDG.AX','GGP.AX','GMD.AX','GMG.AX','GNE.AX','GPT.AX','GQG.AX','HDN.AX','HUB.AX','HVN.AX','IAG.AX','IFT.AX','IGO.AX','ILU.AX','IMD.AX','JBH.AX','JHX.AX','L1G.AX','LLC.AX','LNW.AX','LOV.AX','LSF.AX','LTR.AX','LYC.AX','MCY.AX','MEZ.AX','MFF.AX','MFG.AX','MGR.AX','MIN.AX','MND.AX','MPL.AX','MQG.AX','MSB.AX','MTS.AX','MXT.AX','NAB.AX','NEM.AX','NHC.AX','NHF.AX','NIC.AX','NST.AX','NWH.AX','NWL.AX','NWS.AX','NXG.AX','NXT.AX','OBM.AX','ORA.AX','ORG.AX','ORI.AX','PDI.AX','PDN.AX','PLS.AX','PME.AX','PMV.AX','PNI.AX','PPT.AX','PRN.AX','PRU.AX','PXA.AX','QAN.AX','QBE.AX','RDX.AX','REA.AX','REG.AX','REH.AX','RGN.AX','RHC.AX','RIO.AX','RMD.AX','RMS.AX','RRL.AX','RSG.AX','RWC.AX','RYM.AX','S32.AX','SCG.AX','SDF.AX','SEK.AX','SFR.AX','SGH.AX','SGM.AX','SGP.AX','SHL.AX','SIG.AX','SMR.AX','SNZ.AX','SOL.AX','SPK.AX','STO.AX','SUL.AX','SUN.AX','TAH.AX','TCL.AX','TLC.AX','TLS.AX','TLX.AX','TNE.AX','TPG.AX','TUA.AX','TWE.AX','VAU.AX','VCX.AX','VEA.AX','VGN.AX','VNT.AX','WAF.AX','WAM.AX','WBC.AX','WDS.AX','WES.AX','WGX.AX','WHC.AX','WLE.AX','WOR.AX','WOW.AX','WTC.AX','XRO.AX','YAL.AX','ZIM.AX','ZIP.AX'];
            const allWorkerUrls = [
                'https://zdmbi2py4r4ve2c2qktlew4fhm0zewvz.lambda-url.us-east-1.on.aws/',
                'https://eq5p62fptsiohcplc6rni6ynmu0flxbc.lambda-url.us-east-1.on.aws/',
                'https://g5srxjsnywgv5dpq346fe5bjzy0pjrbc.lambda-url.us-east-1.on.aws/',
                'https://dfbi7p5zyfdw2ts6eq7sykspwu0bhwee.lambda-url.us-east-1.on.aws/',
                'https://oa2jwfnf3bdkfdtpkoqylkzglm0qcmug.lambda-url.us-east-1.on.aws/',
                'https://ceruwdnkbl3rq6pdy3ttm4w4ty0jxnai.lambda-url.us-east-1.on.aws/',
                'https://qj23e6w4szjz4mlxnr6vaxy3eq0tkoks.lambda-url.us-east-1.on.aws/',
                'https://xkfzof47xqcfvagj7kmogve2e40juauq.lambda-url.us-east-1.on.aws/',
                'https://z7im4wlhmnuehbpo5xsor6adr40pwsit.lambda-url.us-east-1.on.aws/',
                'https://7zdpmqcgcxl6y55pcnjchgby5u0jhcim.lambda-url.us-east-1.on.aws/',
                'https://4nsyylypuzscrnuwbmvhmshgc40hvdkf.lambda-url.us-east-1.on.aws/',
                'https://wxbbxlikfmmhsxgwqhps4k2iuq0wuukb.lambda-url.us-east-1.on.aws/',
                'https://tr5ak3x54hjpmekmwah3ipw4de0neqbz.lambda-url.us-east-1.on.aws/',
                'https://a4l3kgi4efmoi6wzan7yx3fbti0ecffs.lambda-url.us-east-1.on.aws/',
                'https://ljyzdni5qkl7nhwatcogo6h5am0xbjaj.lambda-url.us-east-1.on.aws/',
                'https://bwdfqojou5k4fw56o546b7lkm40yfjpk.lambda-url.us-east-1.on.aws/',
                'https://7y4suxzwnilygsuhpu4grsmq4u0mmjar.lambda-url.us-east-1.on.aws/',
                'https://dix4r6zsygayuvp3gloeyfa7oy0pydit.lambda-url.us-east-1.on.aws/',
                'https://z3fcgzcux4jnte2ywnnoe63qu40jkjuy.lambda-url.us-east-1.on.aws/',
                'https://djcngojfo2e6rr5sq6unuwnwcu0ngbwy.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 200 base stocks → 20 workers × 10 stocks each');
            console.log('📊 Processing 200 stocks (20 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 20 workers for 200 ASX stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 20; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(asx200Universe.length / (20)));
                const startIdx = i * perWorker;
                const stockBatch = asx200Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 20/20 workers for 200 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.batch_size} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 20 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 ASX 200 Analysis: ${allResults.length}/200 stocks (${((allResults.length/200)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 200, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'ASX_200_Screener');
            result = formatASXResult(apiData, subOption);
            result.csvData = csvData;
        } else if (option === 5 && subOption === '300') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 5.4 SMART SCALING - ASX 300 Stock Screener');
            const asx300Universe = ['360.AX','4DX.AX','A2M.AX','AAI.AX','AFI.AX','AGL.AX','AIA.AX','ALD.AX','ALK.AX','ALL.AX','ALQ.AX','ALX.AX','AMC.AX','AMP.AX','ANN.AX','ANZ.AX','APA.AX','APE.AX','ARB.AX','ARG.AX','ASB.AX','ASX.AX','AUB.AX','AZJ.AX','BEN.AX','BFL.AX','BGA.AX','BGL.AX','BHP.AX','BOQ.AX','BPT.AX','BRG.AX','BSL.AX','BWP.AX','BXB.AX','CAR.AX','CBA.AX','CDA.AX','CEN.AX','CGF.AX','CHC.AX','CIA.AX','CIP.AX','CLW.AX','CMM.AX','CNU.AX','COH.AX','COL.AX','CPU.AX','CQR.AX','CSC.AX','CSL.AX','CTD.AX','CWY.AX','CYL.AX','DBI.AX','DNL.AX','DOW.AX','DRO.AX','DRR.AX','DXS.AX','DYL.AX','EBO.AX','EDV.AX','EMR.AX','EOS.AX','EVN.AX','EVT.AX','FBU.AX','FLT.AX','FMG.AX','FPH.AX','FRW.AX','GDG.AX','GGP.AX','GMD.AX','GMG.AX','GNE.AX','GPT.AX','GQG.AX','HDN.AX','HUB.AX','HVN.AX','IAG.AX','IFT.AX','IGO.AX','ILU.AX','IMD.AX','JBH.AX','JHX.AX','L1G.AX','LLC.AX','LNW.AX','LOV.AX','LSF.AX','LTR.AX','LYC.AX','MCY.AX','MEZ.AX','MFF.AX','MFG.AX','MGR.AX','MIN.AX','MND.AX','MPL.AX','MQG.AX','MSB.AX','MTS.AX','MXT.AX','NAB.AX','NEM.AX','NHC.AX','NHF.AX','NIC.AX','NST.AX','NWH.AX','NWL.AX','NWS.AX','NXG.AX','NXT.AX','OBM.AX','ORA.AX','ORG.AX','ORI.AX','PDI.AX','PDN.AX','PLS.AX','PME.AX','PMV.AX','PNI.AX','PPT.AX','PRN.AX','PRU.AX','PXA.AX','QAN.AX','QBE.AX','RDX.AX','REA.AX','REG.AX','REH.AX','RGN.AX','RHC.AX','RIO.AX','RMD.AX','RMS.AX','RRL.AX','RSG.AX','RWC.AX','RYM.AX','S32.AX','SCG.AX','SDF.AX','SEK.AX','SFR.AX','SGH.AX','SGM.AX','SGP.AX','SHL.AX','SIG.AX','SMR.AX','SNZ.AX','SOL.AX','SPK.AX','STO.AX','SUL.AX','SUN.AX','TAH.AX','TCL.AX','TLC.AX','TLS.AX','TLX.AX','TNE.AX','TPG.AX','TUA.AX','TWE.AX','VAU.AX','VCX.AX','VEA.AX','VGN.AX','VNT.AX','WAF.AX','WAM.AX','WBC.AX','WDS.AX','WES.AX','WGX.AX','WHC.AX','WLE.AX','WOR.AX','WOW.AX','WTC.AX','XRO.AX','YAL.AX','ZIM.AX','ZIP.AX','AAC.AX','AAJ.AX','AAP.AX','AAR.AX','AAU.AX','ABB.AX','ABY.AX','ACF.AX','ACL.AX','ACQ.AX','ACR.AX','ACS.AX','ACW.AX','ADH.AX','ADN.AX','ADO.AX','ADR.AX','ADS.AX','ADX.AX','AEF.AX','AEI.AX','AEL.AX','AER.AX','AEV.AX','AFG.AX','AFL.AX','AFP.AX','AGC.AX','AGD.AX','AGE.AX','AGI.AX','AGN.AX','AGR.AX','AGY.AX','AHF.AX','AHK.AX','AHL.AX','AHN.AX','AIM.AX','AIQ.AX','AIS.AX','AIV.AX','AIZ.AX','AJL.AX','AJX.AX','ALC.AX','ASL.AX','ATX.AX','AUG.AX','AVH.AX','AXP.AX','BAP.AX','BEL.AX','BKI.AX','BRN.AX','BRU.AX','BUX.AX','CCX.AX','CIN.AX','CMW.AX','CNI.AX','CRB.AX','CUV.AX','DMP.AX','DTL.AX','ELD.AX','EML.AX','GDF.AX','GNC.AX','GOZ.AX','GWA.AX','HMC.AX','IDX.AX','IMU.AX','IRE.AX','KGN.AX','KLS.AX','KMD.AX','LIC.AX','LKE.AX','MYR.AX','NAN.AX','NEC.AX','NUF.AX','NVX.AX','PAB.AX','PBH.AX','PNV.AX','SBM.AX','SCP.AX','SGR.AX','SMI.AX','SPN.AX','STX.AX','TYR.AX','URF.AX','VAS.AX','WEB.AX','WPR.AX'];
            const allWorkerUrls = [
                'https://jfbmkyluzunuoamftazpkijegm0ljegs.lambda-url.us-east-1.on.aws/',
                'https://kkb773jiw72ftsofcnfbrgftp40rhfjy.lambda-url.us-east-1.on.aws/',
                'https://ionfnx6iewltqwmrvedfn3owie0afihf.lambda-url.us-east-1.on.aws/',
                'https://7tfypws4nqb3iqr7olibawmbfm0jlzjs.lambda-url.us-east-1.on.aws/',
                'https://ezp5mxhvwmy6qhy3r4acsuwm4m0dglyt.lambda-url.us-east-1.on.aws/',
                'https://xremswiroprvjuto6vxndbybnm0xkrsy.lambda-url.us-east-1.on.aws/',
                'https://rvkyl4td6a42d7dfjlyskdyisa0eptwf.lambda-url.us-east-1.on.aws/',
                'https://pluquaig762ddynuskdtzhqgqm0sohcb.lambda-url.us-east-1.on.aws/',
                'https://qz5piciswsf5pvpetmp4kq24wu0yuort.lambda-url.us-east-1.on.aws/',
                'https://4mb2o5ond47etn3jsctl4nu42a0yapsj.lambda-url.us-east-1.on.aws/',
                'https://3wxulmrsrkmahjst5nsi2eucqa0vssvl.lambda-url.us-east-1.on.aws/',
                'https://b5lvrk5jaa5ap6lnsx62b34uai0bunpm.lambda-url.us-east-1.on.aws/',
                'https://wkripfsvmcefrnc5ndfrrieecq0mdecc.lambda-url.us-east-1.on.aws/',
                'https://r2pkfsogy4k6coqmhah7hydu3u0rgazz.lambda-url.us-east-1.on.aws/',
                'https://gzz4mfxgjgbdah5umv3rnl2cuu0jxzlq.lambda-url.us-east-1.on.aws/',
                'https://pyrcu4gmwasuhou3uypi44xxom0rwfad.lambda-url.us-east-1.on.aws/',
                'https://s6x3eewnmt6ziqez5zengtgyvu0gjwgo.lambda-url.us-east-1.on.aws/',
                'https://s6iixoj2z4iincdic7j2pzesny0cfgbp.lambda-url.us-east-1.on.aws/',
                'https://jxq3qwsck6f3b3s2jejhfxqsf40kezta.lambda-url.us-east-1.on.aws/',
                'https://wmmvyxqsn4ub4vymsgvbrbhvni0sqafe.lambda-url.us-east-1.on.aws/',
                'https://7xfnmowroamq3pzxe2765iwa5y0npnwn.lambda-url.us-east-1.on.aws/',
                'https://23gujxpbnniygjodznwrtcn6be0eqjfj.lambda-url.us-east-1.on.aws/',
                'https://ldigoeb33fphdfcpfaqjgibbdu0htetb.lambda-url.us-east-1.on.aws/',
                'https://gxasl2yhcvk3apym7azkonv6xy0ypwoh.lambda-url.us-east-1.on.aws/',
                'https://xt3uhsu2jlb4w3j4hhgrup46oa0oeosu.lambda-url.us-east-1.on.aws/',
                'https://cnnpxpsvwjmwu5ubkhjddptyoq0nxllx.lambda-url.us-east-1.on.aws/',
                'https://fhltlxnqv3c74ykqnwhciqvdri0fduon.lambda-url.us-east-1.on.aws/',
                'https://m6hbjbtnrzirqq3njul3ca57ru0wydar.lambda-url.us-east-1.on.aws/',
                'https://mxyh4ed7lqdhokwkjap55vezcu0grnui.lambda-url.us-east-1.on.aws/',
                'https://tzwthsohhoj2nifkjw5gcftyxq0hwhut.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 300 base stocks → 30 workers × 10 stocks each');
            console.log('📊 Processing 300 stocks (30 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 30 workers for 300 ASX stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 30; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(asx300Universe.length / (30)));
                const startIdx = i * perWorker;
                const stockBatch = asx300Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 30/30 workers for 300 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.stock_batch.length} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 30 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result && workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 ASX 300 Analysis: ${allResults.length}/300 stocks (${((allResults.length/300)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 300, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'ASX_300_Screener');
            result = formatASXResult(apiData, subOption);
            result.csvData = csvData;

        } else if (option === 5 && subOption === 'nikkei225') {
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 5.5 SMART SCALING - Japan Nikkei 225 Stock Screener');
            const nikkei225Universe = ['8035.T','9202.T','9201.T','543A.T','7267.T','7202.T','7261.T','7211.T','7201.T','7270.T','7269.T','7203.T','7272.T','8304.T','8331.T','8354.T','8306.T','8411.T','8308.T','5831.T','8316.T','8309.T','7186.T','3407.T','4061.T','4901.T','4452.T','3405.T','4188.T','4183.T','4021.T','6988.T','4004.T','4063.T','4911.T','4005.T','4043.T','4042.T','4208.T','9433.T','9432.T','9434.T','9984.T','1721.T','1925.T','1808.T','1963.T','1812.T','1802.T','1928.T','1803.T','1801.T','6857.T','6770.T','7751.T','6902.T','6954.T','6504.T','6702.T','6501.T','6861.T','285A.T','6971.T','6920.T','6479.T','6503.T','6981.T','6701.T','6594.T','6645.T','6752.T','6723.T','7752.T','6963.T','7735.T','6724.T','6753.T','6758.T','6526.T','6976.T','6762.T','6506.T','6841.T','9502.T','9503.T','9501.T','1332.T','2802.T','2502.T','2914.T','2801.T','2503.T','2269.T','2282.T','2871.T','2002.T','2501.T','9532.T','9531.T','5201.T','5333.T','5214.T','5233.T','5301.T','5332.T','8750.T','8725.T','8630.T','8795.T','8766.T','9147.T','9064.T','6113.T','6367.T','6361.T','6305.T','7004.T','7013.T','5631.T','6473.T','6301.T','6326.T','7011.T','6471.T','6472.T','6103.T','6302.T','6273.T','9107.T','9104.T','9101.T','1605.T','5714.T','5803.T','5801.T','5711.T','5706.T','3436.T','5802.T','5713.T','8253.T','8697.T','8591.T','7832.T','7912.T','7911.T','7951.T','5020.T','5019.T','4503.T','4519.T','4568.T','4523.T','4151.T','4578.T','4506.T','4507.T','4502.T','6146.T','7741.T','4902.T','7731.T','7733.T','4543.T','3861.T','9022.T','9020.T','9008.T','9009.T','9007.T','9001.T','9005.T','9021.T','8802.T','8801.T','8830.T','8804.T','3289.T','8267.T','9983.T','3099.T','3086.T','8252.T','7453.T','9843.T','7532.T','3382.T','8233.T','3092.T','5108.T','5101.T','8601.T','8604.T','6532.T','4751.T','2432.T','4324.T','6178.T','9766.T','4689.T','4385.T','2413.T','3659.T','7974.T','4307.T','4661.T','4755.T','6098.T','9735.T','3697.T','9602.T','4704.T','7012.T','5411.T','5406.T','5401.T','3401.T','3402.T','8001.T','8002.T','8058.T','8031.T','2768.T','8053.T','8015.T'];
            const allWorkerUrls = [
                'https://2g3hj5stpbtprg63efqstjrboy0mwpog.lambda-url.us-east-1.on.aws/',   // stockiq-asia-5-5-worker-1
                'https://5yzugqqawscfvx5kyqict6x7ha0samau.lambda-url.us-east-1.on.aws/',   // stockiq-asia-5-5-worker-2
                'https://wfeof7dr5inqc4xhohtdu6n6bi0epuqg.lambda-url.us-east-1.on.aws/',   // stockiq-asia-5-5-worker-3
                'https://itrpfcyqqn6yzjqn6ky7dynnoe0ixzfk.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-4
                'https://s6kwr3a6j7u4x2a6gbqnrjj6s40nunos.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-5
                'https://t4uvfpm7ewvvdfn7xpu7hhj6ua0edjse.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-6
                'https://76pscw2vi3chb2dxjqtuqrha740gvxwu.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-7
                'https://4bjpk7ivpav7hoalmiphib4twm0vuwmr.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-8
                'https://knvjsgs77qj6k7zlpe2jqo2vle0sdtju.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-9
                'https://hx6hgfuntjvk5tmhqsrywvy5a40wtuyq.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-10
                'https://uullmljyan3vuybanguja2h5py0jevfr.lambda-url.us-east-1.on.aws/',   // stockiq-asia-5-5-worker-11
                'https://td2j3copshrmq4vehgpujezsvy0mcwtm.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-12
                'https://6utz7752pa3l54lujtsnq4gh240oepjs.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-13
                'https://7fqznbw7547jehwmg5har3zh4q0pdzcq.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-14
                'https://xxjl5khbatuobsoxwe4csx6bgy0tmkse.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-15
                'https://ueqire27pt3nzwkgzlal5nnlau0mxnxr.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-16
                'https://sla4c77w4je62je2p7igbsm76i0tgafz.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-17
                'https://76vbcb5lp4yp5hgwy3xn72nbm40oofqx.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-18
                'https://i5vrx42zdwq7yt777ii4nqqgem0ngayb.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-19
                'https://g3vxxlz4p6s7dum3c6cwwguawe0jladz.lambda-url.us-east-1.on.aws/',  // stockiq-asia-5-5-worker-20
                'https://3dmddgt36bvz2hqsqj3mghd2540drkom.lambda-url.us-east-1.on.aws/'   // stockiq-asia-5-5-worker-21
            ];
            console.log('🧠 Dynamic allocation: 210 base stocks → 21 workers × 10 stocks each');
            console.log('📊 Processing 210 stocks (21 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 21 workers for 210 Japan Nikkei stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 21; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(nikkei225Universe.length / (21)));
                const startIdx = i * perWorker;
                const stockBatch = nikkei225Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 21/21 workers for 210 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.stock_batch.length} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 21 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result && workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 Japan Nikkei 225 Analysis: ${allResults.length}/210 stocks (${((allResults.length/210)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 210, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'Japan_Nikkei225_Screener');
            result = formatNikkeiResult(apiData);
            result.csvData = csvData;

        } else if (option === 4 && subOption === 'ftse100') {
            console.log('🚀 OPTION 5.1 SMART SCALING - UK FTSE 100 Stock Screener');
            const ftse100Universe = ['III.L','ABDN.L','ADM.L','AAF.L','ALW.L','AAL.L','ANTO.L','ABF.L','AZN.L','AUTO.L','AV.L','BAB.L','BA.L','BBY.L','BARC.L','BTRW.L','BP.L','BATS.L','BLND.L','BT-A.L','BNZL.L','BRBY.L','CNA.L','CCEP.L','CCH.L','CPG.L','CCC.L','CTEC.L','CRDA.L','DCC.L','DGE.L','DPLM.L','EZJ.L','EDV.L','EXPN.L','FCIT.L','FRES.L','GAW.L','GLEN.L','GSK.L','HLN.L','HLMA.L','HSX.L','HWDN.L','HSBA.L','ICG.L','IGG.L','IHG.L','IMI.L','IMB.L','INF.L','IAG.L','ITRK.L','INVP.L','ITH.L','JD.L','BGEO.L','KGF.L','LAND.L','LGEN.L','LLOY.L','LMP.L','LSEG.L','MNG.L','MKS.L','MRO.L','MTLN.L','NG.L','NWG.L','NXT.L','PSON.L','PSH.L','PCT.L','PRU.L','RKT.L','REL.L','RTO.L','RIO.L','RR.L','SGE.L','SBRY.L','SMT.L','SGRO.L','SVT.L','SHEL.L','SMIN.L','SN.L','SPX.L','SSE.L','STAN.L','SDLF.L','STJ.L','TSCO.L','BBOX.L','ULVR.L','UU.L','VOD.L','WEIR.L','WTB.L','WPP.L'];
            const allWorkerUrls = [
                'https://jj3bbmgmeqab6zeksees37cute0tncvs.lambda-url.us-east-1.on.aws/',
                'https://rxsr5ewpafmciqetbdjh4senta0kliqw.lambda-url.us-east-1.on.aws/',
                'https://cmrjcsekzumxpiic7curdzt3im0qeycx.lambda-url.us-east-1.on.aws/',
                'https://hkdsj5m5ylokvom7hxeqw34say0xigse.lambda-url.us-east-1.on.aws/',
                'https://7o7sh53vljvmerskx5xxj5sgwu0hunbt.lambda-url.us-east-1.on.aws/',
                'https://kptbydm2z6vnzxcehdono4wgmm0msidt.lambda-url.us-east-1.on.aws/',
                'https://f7erkcsokxbgux7grz2matjnme0ydaie.lambda-url.us-east-1.on.aws/',
                'https://4ovkozqbxggwdldbwlghptuwfm0mkibm.lambda-url.us-east-1.on.aws/',
                'https://rxobsfprrrlv2x2ta5eim7q5oa0azgpk.lambda-url.us-east-1.on.aws/',
                'https://pbfu2jxvnkle2zzzmm7czrdgum0xnhkm.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 100 base stocks → 10 workers × 10 stocks each');
            console.log('📊 Processing 100 stocks (10 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 10 workers for 100 UK FTSE stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 10; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(ftse100Universe.length / (10)));
                const startIdx = i * perWorker;
                const stockBatch = ftse100Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 10/10 workers for 100 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.stock_batch.length} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 10 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 UK FTSE 100 Analysis: ${allResults.length}/100 stocks (${((allResults.length/100)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 100, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'UK_FTSE_100_Screener');
            
            // Custom UK formatting with pounds
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
                    const price = `£${(stock.current_price || stock.price || 0).toFixed(2)}`.padStart(8);
                    const score = (stock.total_score || stock.score || 0) >= 0 ? `+${(stock.total_score || stock.score || 0).toFixed(1)}` : `${(stock.total_score || stock.score || 0).toFixed(1)}`;
                    const rsi = (stock.rsi || 0).toFixed(1).padStart(5);
                    const ytd = (stock.ytd_change || 0) >= 0 ? `+${(stock.ytd_change || 0).toFixed(1)}%` : `${(stock.ytd_change || 0).toFixed(1)}%`;
                    const vol = `${(stock.volume_ratio || 1).toFixed(1)}x`;
                    output += `${(i+1).toString().padStart(2)}. ${symbol} ${price} | Score: ${score} | RSI: ${rsi} | YTD: ${ytd}, Vol: ${vol}\n`;
                });
                
                output += '\n</pre><div style="margin: 20px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;">📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.</div><pre style="white-space: pre-wrap; font-family: monospace;">\n🎯 TOP 3 DETAILED ANALYSIS:\n';
                output += '================================================================\n';
                allResults.slice(0, 3).forEach((stock, i) => {
                    output += `${i+1}. ${stock.symbol}: £${(stock.price || 0).toFixed(2)} | ${signalLabel(stock.recommendation)} | Score: ${(stock.total_score || stock.score || 0) >= 0 ? '+' : ''}${(stock.total_score || stock.score || 0).toFixed(1)}\n`;
                    
                    if (stock.score_breakdown && stock.score_breakdown.length > 0) {
                        output += '   📊 Score Breakdown:\n';
                        stock.score_breakdown.forEach(breakdown => {
                            output += `      ${breakdown}\n`;
                        });
                    }
                    
                    output += `   📈 Technical: RSI ${(stock.rsi || 50).toFixed(1)} | MACD ${stock.macd_signal || 'NEUTRAL'}\n`;
                    output += `   💰 Levels: Support £${(stock.support || 0).toFixed(2)} | Resistance £${(stock.resistance || 0).toFixed(2)}\n`;
                    output += `   📏 Reference levels: Lower £${(stock.stop_loss || 0).toFixed(2)} | Upper £${(stock.take_profit || 0).toFixed(2)}\n`;
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
            
            result = { type: 'option_4_ftse100_screener', data: htmlOutput };
            result.csvData = csvData;
        } else if (option === 5 && subOption === '50') {
            console.log('🚀 SSE 50 Stock Screener');
            const sse50Universe = ['600519.SS','601318.SS','600036.SS','600276.SS','600030.SS','601166.SS','600887.SS','600016.SS','601328.SS','600000.SS','601288.SS','600585.SS','601398.SS','600031.SS','601668.SS','600048.SS','601888.SS','600050.SS','601601.SS','600104.SS','601012.SS','600690.SS','601088.SS','600837.SS','601857.SS','600028.SS','601818.SS','600009.SS','601628.SS','600019.SS','601988.SS','600029.SS','601211.SS','600547.SS','601336.SS','600606.SS','601688.SS','600196.SS','601390.SS','600745.SS','601919.SS','600588.SS','601766.SS','600150.SS','601899.SS','600703.SS','601989.SS','600438.SS','601998.SS','600900.SS'];
            const startTime = Date.now();
            const response = await fetch('YOUR_LAMBDA_URL', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({stock_batch: sse50Universe})
            });
            const apiData = await response.json();
            const totalTime = (Date.now() - startTime) / 1000;
            const csvData = generateExcelExport(apiData.results, 'SSE_50_Screener');
            result = formatASXResult(apiData, '50');
            result.csvData = csvData;
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
            // Access was already checked, and this use already counted, at the top of runAnalysis.
            // Checking again here made the last free use of the day redirect to signup/upgrade with no result.
            console.log('🚀 OPTION 4.4 SMART SCALING - ASX 300 Stock Screener');
            const asx300Universe = ['360.AX','4DX.AX','A2M.AX','AAI.AX','AFI.AX','AGL.AX','AIA.AX','ALD.AX','ALK.AX','ALL.AX','ALQ.AX','ALX.AX','AMC.AX','AMP.AX','ANN.AX','ANZ.AX','APA.AX','APE.AX','ARB.AX','ARG.AX','ASB.AX','ASX.AX','AUB.AX','AZJ.AX','BEN.AX','BFL.AX','BGA.AX','BGL.AX','BHP.AX','BOQ.AX','BPT.AX','BRG.AX','BSL.AX','BWP.AX','BXB.AX','CAR.AX','CBA.AX','CDA.AX','CEN.AX','CGF.AX','CHC.AX','CIA.AX','CIP.AX','CLW.AX','CMM.AX','CNU.AX','COH.AX','COL.AX','CPU.AX','CQR.AX','CSC.AX','CSL.AX','CTD.AX','CWY.AX','CYL.AX','DBI.AX','DNL.AX','DOW.AX','DRO.AX','DRR.AX','DXS.AX','DYL.AX','EBO.AX','EDV.AX','EMR.AX','EOS.AX','EVN.AX','EVT.AX','FBU.AX','FLT.AX','FMG.AX','FPH.AX','FRW.AX','GDG.AX','GGP.AX','GMD.AX','GMG.AX','GNE.AX','GPT.AX','GQG.AX','HDN.AX','HUB.AX','HVN.AX','IAG.AX','IFT.AX','IGO.AX','ILU.AX','IMD.AX','JBH.AX','JHX.AX','L1G.AX','LLC.AX','LNW.AX','LOV.AX','LSF.AX','LTR.AX','LYC.AX','MCY.AX','MEZ.AX','MFF.AX','MFG.AX','MGR.AX','MIN.AX','MND.AX','MPL.AX','MQG.AX','MSB.AX','MTS.AX','MXT.AX','NAB.AX','NEM.AX','NHC.AX','NHF.AX','NIC.AX','NST.AX','NWH.AX','NWL.AX','NWS.AX','NXG.AX','NXT.AX','OBM.AX','ORA.AX','ORG.AX','ORI.AX','PDI.AX','PDN.AX','PLS.AX','PME.AX','PMV.AX','PNI.AX','PPT.AX','PRN.AX','PRU.AX','PXA.AX','QAN.AX','QBE.AX','RDX.AX','REA.AX','REG.AX','REH.AX','RGN.AX','RHC.AX','RIO.AX','RMD.AX','RMS.AX','RRL.AX','RSG.AX','RWC.AX','RYM.AX','S32.AX','SCG.AX','SDF.AX','SEK.AX','SFR.AX','SGH.AX','SGM.AX','SGP.AX','SHL.AX','SIG.AX','SMR.AX','SNZ.AX','SOL.AX','SPK.AX','STO.AX','SUL.AX','SUN.AX','TAH.AX','TCL.AX','TLC.AX','TLS.AX','TLX.AX','TNE.AX','TPG.AX','TUA.AX','TWE.AX','VAU.AX','VCX.AX','VEA.AX','VGN.AX','VNT.AX','WAF.AX','WAM.AX','WBC.AX','WDS.AX','WES.AX','WGX.AX','WHC.AX','WLE.AX','WOR.AX','WOW.AX','WTC.AX','XRO.AX','YAL.AX','ZIM.AX','ZIP.AX','AAC.AX','AAJ.AX','AAP.AX','AAR.AX','AAU.AX','ABB.AX','ABY.AX','ACF.AX','ACL.AX','ACQ.AX','ACR.AX','ACS.AX','ACW.AX','ADH.AX','ADN.AX','ADO.AX','ADR.AX','ADS.AX','ADX.AX','AEF.AX','AEI.AX','AEL.AX','AER.AX','AEV.AX','AFG.AX','AFL.AX','AFP.AX','AGC.AX','AGD.AX','AGE.AX','AGI.AX','AGN.AX','AGR.AX','AGY.AX','AHF.AX','AHK.AX','AHL.AX','AHN.AX','AIM.AX','AIQ.AX','AIS.AX','AIV.AX','AIZ.AX','AJL.AX','AJX.AX','ALC.AX','ASL.AX','ATX.AX','AUG.AX','AVH.AX','AXP.AX','BAP.AX','BEL.AX','BKI.AX','BRN.AX','BRU.AX','BUX.AX','CCX.AX','CIN.AX','CMW.AX','CNI.AX','CRB.AX','CUV.AX','DMP.AX','DTL.AX','ELD.AX','EML.AX','GDF.AX','GNC.AX','GOZ.AX','GWA.AX','HMC.AX','IDX.AX','IMU.AX','IRE.AX','KGN.AX','KLS.AX','KMD.AX','LIC.AX','LKE.AX','MYR.AX','NAN.AX','NEC.AX','NUF.AX','NVX.AX','PAB.AX','PBH.AX','PNV.AX','SBM.AX','SCP.AX','SGR.AX','SMI.AX','SPN.AX','STX.AX','TYR.AX','URF.AX','VAS.AX','WEB.AX','WPR.AX'];
            const allWorkerUrls = [
                'https://jfbmkyluzunuoamftazpkijegm0ljegs.lambda-url.us-east-1.on.aws/',
                'https://kkb773jiw72ftsofcnfbrgftp40rhfjy.lambda-url.us-east-1.on.aws/',
                'https://ionfnx6iewltqwmrvedfn3owie0afihf.lambda-url.us-east-1.on.aws/',
                'https://7tfypws4nqb3iqr7olibawmbfm0jlzjs.lambda-url.us-east-1.on.aws/',
                'https://ezp5mxhvwmy6qhy3r4acsuwm4m0dglyt.lambda-url.us-east-1.on.aws/',
                'https://xremswiroprvjuto6vxndbybnm0xkrsy.lambda-url.us-east-1.on.aws/',
                'https://rvkyl4td6a42d7dfjlyskdyisa0eptwf.lambda-url.us-east-1.on.aws/',
                'https://pluquaig762ddynuskdtzhqgqm0sohcb.lambda-url.us-east-1.on.aws/',
                'https://qz5piciswsf5pvpetmp4kq24wu0yuort.lambda-url.us-east-1.on.aws/',
                'https://4mb2o5ond47etn3jsctl4nu42a0yapsj.lambda-url.us-east-1.on.aws/',
                'https://3wxulmrsrkmahjst5nsi2eucqa0vssvl.lambda-url.us-east-1.on.aws/',
                'https://b5lvrk5jaa5ap6lnsx62b34uai0bunpm.lambda-url.us-east-1.on.aws/',
                'https://wkripfsvmcefrnc5ndfrrieecq0mdecc.lambda-url.us-east-1.on.aws/',
                'https://r2pkfsogy4k6coqmhah7hydu3u0rgazz.lambda-url.us-east-1.on.aws/',
                'https://gzz4mfxgjgbdah5umv3rnl2cuu0jxzlq.lambda-url.us-east-1.on.aws/',
                'https://pyrcu4gmwasuhou3uypi44xxom0rwfad.lambda-url.us-east-1.on.aws/',
                'https://s6x3eewnmt6ziqez5zengtgyvu0gjwgo.lambda-url.us-east-1.on.aws/',
                'https://s6iixoj2z4iincdic7j2pzesny0cfgbp.lambda-url.us-east-1.on.aws/',
                'https://jxq3qwsck6f3b3s2jejhfxqsf40kezta.lambda-url.us-east-1.on.aws/',
                'https://wmmvyxqsn4ub4vymsgvbrbhvni0sqafe.lambda-url.us-east-1.on.aws/',
                'https://7xfnmowroamq3pzxe2765iwa5y0npnwn.lambda-url.us-east-1.on.aws/',
                'https://23gujxpbnniygjodznwrtcn6be0eqjfj.lambda-url.us-east-1.on.aws/',
                'https://ldigoeb33fphdfcpfaqjgibbdu0htetb.lambda-url.us-east-1.on.aws/',
                'https://gxasl2yhcvk3apym7azkonv6xy0ypwoh.lambda-url.us-east-1.on.aws/',
                'https://xt3uhsu2jlb4w3j4hhgrup46oa0oeosu.lambda-url.us-east-1.on.aws/',
                'https://cnnpxpsvwjmwu5ubkhjddptyoq0nxllx.lambda-url.us-east-1.on.aws/',
                'https://fhltlxnqv3c74ykqnwhciqvdri0fduon.lambda-url.us-east-1.on.aws/',
                'https://m6hbjbtnrzirqq3njul3ca57ru0wydar.lambda-url.us-east-1.on.aws/',
                'https://mxyh4ed7lqdhokwkjap55vezcu0grnui.lambda-url.us-east-1.on.aws/',
                'https://tzwthsohhoj2nifkjw5gcftyxq0hwhut.lambda-url.us-east-1.on.aws/'
            ];
            console.log('🧠 Dynamic allocation: 300 base stocks → 30 workers × 10 stocks each');
            console.log('📊 Processing 300 stocks (30 workers × 10 stocks each)');
            const startTime = Date.now();
            console.log('📊 Calling 30 workers for 300 ASX stocks...');
            const workerPayloads = [];
            for (let i = 0; i < 30; i++) {
                // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
                const perWorker = Math.max(10, Math.ceil(asx300Universe.length / (30)));
                const startIdx = i * perWorker;
                const stockBatch = asx300Universe.slice(startIdx, startIdx + perWorker);
                // never send an empty batch: some workers fall back to their own built-in list
                if (stockBatch.length > 0) workerPayloads.push({ url: allWorkerUrls[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
            }
            console.log('📊 Using 30/30 workers for 300 stocks');
            const promises = workerPayloads.map(async (workerData) => {
                console.log(`🔄 Starting Worker ${workerData.workerId} (${workerData.payload.batch_size} stocks)...`);
                const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
                if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
                const result = await response.json();
                console.log(`✅ Worker ${workerData.workerId} completed: ${result.results ? result.results.length : 0} stocks`);
                return { result, workerId: workerData.workerId };
            });
            const allWorkerResults = await Promise.all(promises);
            const endTime = Date.now();
            const totalTime = (endTime - startTime) / 1000;
            console.log(`⚡ All 30 workers completed in ${totalTime}s`);
            let allResults = [];
            allWorkerResults.forEach((workerResult) => {
                if (workerResult.result.success && workerResult.result.results) {
                    allResults = allResults.concat(workerResult.result.results);
                    console.log(`📊 Worker ${workerResult.workerId}: ${workerResult.result.results.length} stocks`);
                }
            });
            allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            console.log(`📊 ASX 300 Analysis: ${allResults.length}/300 stocks (${((allResults.length/300)*100).toFixed(1)}%)`);
            const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: 300, processing_time: totalTime };
            const csvData = generateExcelExport(allResults, 'ASX_300_Screener');
            result = formatASXResult(apiData, subOption);
            result.csvData = csvData;
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
            
            // Use dedicated single coin analysis function
            const singleCoinUrl = 'https://uotf7ibcklwyuehblv7zsl7ney0ngmrl.lambda-url.us-east-1.on.aws/';
            
            console.log(`🔍 Analyzing ${coinSymbol} with dedicated single coin function`);
            
            const response = await fetch(singleCoinUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    // some coins need the price source's numbered ticker (e.g. SUI is SUI20947); the plain symbol is a different coin
                    single_coin: (typeof CRYPTO_TICKER_MAP !== 'undefined' && CRYPTO_TICKER_MAP[coinSymbol]) || coinSymbol,
                    timestamp: new Date().toISOString() 
                })
            });
            
            if (!response.ok) throw new Error(`API Error: ${response.status}`);
            const singleCoinResult = await response.json();
            
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
        dashboardMsg.innerHTML = '📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.';
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
            companyName = subNames[subOption] || 'ASX Stock Screener';
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

function formatOption2Result(apiData) {
    const signals = apiData.signals;
    let output = `
============================================================
⚡ TRADING SIGNALS GENERATOR RESULTS (REAL-TIME DATA)
============================================================

Signals Generated: ${apiData.symbols_analyzed}
Analysis Date: ${new Date(apiData.timestamp).toLocaleString()}

🎯 TRADING SIGNALS:
ℹ️ General information only. Signals and levels are calculated automatically and are not recommendations to buy or sell.

`;
    signals.forEach((signal, i) => {
        const actionEmoji = signal.action === 'BUY' ? '🟢' : signal.action === 'SELL' ? '🔴' : '⚪';
        output += `${i + 1}. ${signal.symbol} - $${signal.current_price.toFixed(2)}\n`;
        // The two calculated levels sit either side of the price; which one is higher depends on the signal
        const tpIsUpper = signal.take_profit >= signal.stop_loss;
        const upper = tpIsUpper ? [signal.take_profit, signal.take_profit_pct] : [signal.stop_loss, signal.stop_loss_pct];
        const lower = tpIsUpper ? [signal.stop_loss, signal.stop_loss_pct] : [signal.take_profit, signal.take_profit_pct];
        output += `   ${actionEmoji} ${signalLabel(signal.action)} signal (${signal.confidence} confidence)\n`;
        output += `   📍 Price when calculated: $${signal.entry_price.toFixed(2)}\n`;
        output += `   📏 Upper reference level: $${upper[0].toFixed(2)} (${upper[1] >= 0 ? '+' : ''}${upper[1].toFixed(1)}%)\n`;
        output += `   📏 Lower reference level: $${lower[0].toFixed(2)} (${lower[1] >= 0 ? '+' : ''}${lower[1].toFixed(1)}%)\n\n`;
    });
    return { type: 'option_21_custom_signals', data: output };
}

function formatOption22Result(apiData) {
    const signals = apiData.signals;
    let output = `
============================================================
⚡ AUTO-DETECT TRADING SIGNALS RESULTS (REAL-TIME DATA)
============================================================

Methodology: ${apiData.methodology}
Top Performers Found: ${apiData.top_performers.join(', ')}
Signals Generated: ${apiData.symbols_analyzed}

🎯 TRADING SIGNALS FOR TOP PERFORMERS:
ℹ️ General information only. Signals and levels are calculated automatically and are not recommendations to buy or sell.

`;
    signals.forEach((signal, i) => {
        const actionEmoji = signal.action === 'BUY' ? '🟢' : signal.action === 'SELL' ? '🔴' : '⚪';
        output += `${i + 1}. ${signal.symbol} - $${signal.current_price.toFixed(2)}\n`;
        output += `   ${actionEmoji} ${signalLabel(signal.action)} signal (${signal.confidence} confidence)\n`;
        output += `   📍 Price when calculated: $${signal.entry_price.toFixed(2)}\n`;
        output += `   📏 Reference level: $${signal.take_profit.toFixed(2)} (${signal.take_profit_pct >= 0 ? '+' : ''}${signal.take_profit_pct.toFixed(1)}%)\n\n`;
    });
    return { type: 'option_22_auto_signals', data: output };
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
            const price = `$${(stock.current_price || stock.price || 0).toFixed(2)}`.padStart(8);
            const score = (stock.total_score || stock.score || 0) >= 0 ? `+${(stock.total_score || stock.score || 0).toFixed(1)}` : `${(stock.total_score || stock.score || 0).toFixed(1)}`;
            const rsi = (stock.rsi || 0).toFixed(1).padStart(5);
            const ytd = (stock.ytd_change || 0) >= 0 ? `+${(stock.ytd_change || 0).toFixed(1)}%` : `${(stock.ytd_change || 0).toFixed(1)}%`;
            const vol = `${(stock.volume_ratio || 1).toFixed(1)}x`;
            output += `${(i+1).toString().padStart(2)}. ${symbol} ${price} | Score: ${score} | RSI: ${rsi} | YTD: ${ytd}, Vol: ${vol}\n`;
        });
        
        output += '</table><div style="margin: 20px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;">📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.</div><table class="results-table">\n';
        
        if (subOption === '3' || subOption === '2' || subOption === '4' || subOption === '5' || subOption === '6' || subOption === '7' || subOption === '8' || subOption === '100') {
            output += '\n🎯 TOP 3 DETAILED ANALYSIS:\n';
            output += '================================================================\n';
            sortedResults.slice(0, 3).forEach((stock, i) => {
                output += `${i+1}. ${stock.symbol}: $${(stock.price || 0).toFixed(2)} | ${signalLabel(stock.recommendation)} | Score: ${(stock.total_score || stock.score || 0) >= 0 ? '+' : ''}${(stock.total_score || stock.score || 0).toFixed(1)}\n`;
                
                if (stock.score_breakdown && stock.score_breakdown.length > 0) {
                    output += '   📊 Score Breakdown:\n';
                    stock.score_breakdown.forEach(breakdown => {
                        output += `      ${breakdown}\n`;
                    });
                }
                
                output += `   📈 Technical: RSI ${(stock.rsi || 50).toFixed(1)} | MACD ${stock.macd_signal || 'NEUTRAL'}\n`;
                output += `   💰 Levels: Support $${(stock.support || 0).toFixed(2)} | Resistance $${(stock.resistance || 0).toFixed(2)}\n`;
                output += `   📏 Reference levels: Lower $${(stock.stop_loss || 0).toFixed(2)} | Upper $${(stock.take_profit || 0).toFixed(2)}\n`;
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
    let output = `
============================================================
🔍 SINGLE COIN ANALYSIS: ${coinSymbol}
============================================================

Coin: ${coinSymbol}
Analysis Date: ${new Date().toLocaleString()}
📊 Technical Analysis: MACD, RSI, Bollinger Bands, Stochastic, Volume, Momentum

`;
    
    if (apiData.coins && apiData.coins.length > 0) {
        const coin = apiData.coins[0];
        const price = coin.price >= 1 ? `$${coin.price.toFixed(2)}` : `$${coin.price.toFixed(8)}`;
        
        output += `💰 CURRENT ANALYSIS:
`;
        output += `Price: ${price} USD
`;
        output += `Signal: ${signalLabel(coin.recommendation)}
`;
        output += `Score: ${coin.score >= 0 ? '+' : ''}${coin.score || 0}
`;
        output += `Confidence: ${coin.confidence || 'LOW'}
`;
        output += `Horizon: ${horizonLabel(coin.timeframe)}

`;
        
        output += `📊 PERFORMANCE:
`;
        output += `24h Change: ${coin.change_24h >= 0 ? '+' : ''}${(coin.change_24h || 0).toFixed(2)}%
`;
        output += `7d Change: ${coin.change_7d >= 0 ? '+' : ''}${(coin.change_7d || 0).toFixed(2)}%
`;
        output += `30d Change: ${coin.change_30d >= 0 ? '+' : ''}${(coin.change_30d || 0).toFixed(2)}%

`;
        
        output += `📊 TECHNICAL INDICATORS:
`;
        output += `RSI: ${(coin.rsi || 50).toFixed(1)} - ${(coin.rsi_signal || 'NEUTRAL').split(' - ')[0]}
`;
        output += `MACD: ${coin.macd_signal || 'No data'}
`;
        output += `Bollinger Bands: ${coin.bb_signal || 'NEUTRAL'}
`;
        output += `Momentum: ${coin.momentum_signal || 'NEUTRAL'}
`;
        output += `Stochastic: ${(coin.stoch_k || 50).toFixed(1)} - ${coin.stoch_signal || 'NEUTRAL'}
`;
        output += `
`;
        
        output += `🔄 CONFIDENCE:
`;
        output += `Confidence: ${coin.confidence || 'LOW'}
`;
        output += `Model probability estimate: ${(coin.profit_probability || 50).toFixed(0)}%

`;
        
        if (coin.stop_loss && coin.take_profit) {
            const stopStr = coin.stop_loss >= 1 ? `$${coin.stop_loss.toFixed(2)}` : `$${coin.stop_loss.toFixed(8)}`;
            const tpStr = coin.take_profit >= 1 ? `$${coin.take_profit.toFixed(2)}` : `$${coin.take_profit.toFixed(8)}`;
            const supportStr = coin.support >= 1 ? `$${coin.support.toFixed(2)}` : `$${coin.support.toFixed(8)}`;
            const resistanceStr = coin.resistance >= 1 ? `$${coin.resistance.toFixed(2)}` : `$${coin.resistance.toFixed(8)}`;
            
            output += `📏 REFERENCE LEVELS (calculated automatically, not instructions):
`;
            output += `Lower reference level: ${stopStr}
`;
            output += `Upper reference level: ${tpStr}
`;
            output += `Support Level: ${supportStr}
`;
            output += `Resistance Level: ${resistanceStr}
`;
            output += `Model probability estimate: ${(coin.profit_probability || 50).toFixed(0)}%

`;
        }
        
        // Signals section (like 7.1 format)
        if (coin.confidence_factors && coin.confidence_factors.length > 0) {
            output += `🎯 SIGNALS:
`;
            output += `   ${coin.confidence_factors.join(', ')}
`;
            output += `
`;
        }
        
        // Confidence factors section (like 7.2 format)
        if (coin.confidence_factors && coin.confidence_factors.length > 0) {
            output += `🎯 CONFIDENCE FACTORS:
`;
            coin.confidence_factors.forEach(factor => {
                output += `• ${factor}
`;
            });
            output += `
`;
        } else {
            output += `🎯 CONFIDENCE FACTORS:
`;
            output += `• No specific confidence factors identified
`;
            output += `• Analysis based on standard technical indicators
`;
            output += `
`;
        }
        
        if (coin.score_breakdown && coin.score_breakdown.length > 0) {
            output += `Score Breakdown:
`;
            coin.score_breakdown.forEach(breakdown => {
                output += `   ${breakdown}
`;
            });
            output += `
🧮 Total Score: ${coin.score >= 0 ? '+' : ''}${coin.score || 0}

`;
            output += `📊 SCORE RANGES:
`;
            output += `   +7 and above: Strongly positive
`;
            output += `   +4 to +6: Positive
`;
            output += `   +2 to +3: Slightly positive
`;
            output += `   -1 to +1: Mixed
`;
            output += `   -3 to -2: Slightly negative
`;
            output += `   -5 to -4: Negative
`;
            output += `   Below -5: Strongly negative
`;
        }
    } else {
        output += `❌ No data available for ${coinSymbol}
`;
        output += `This coin may not be available on Yahoo Finance or may have a different symbol.
`;
        output += `Try using common symbols like: BTC, ETH, ADA, SOL, DOGE, etc.
`;
    }
    
    output += `
✅ Single coin analysis complete!
`;
    
    // Prices come from Yahoo Finance as SYMBOL-USD, and some symbols are shared by more than one coin.
    // These were confirmed (9 Oct 2026, against CoinGecko) to be priced as a different coin; keep in step with
    // MISMATCHED_SYMBOLS in the stockiq-option-7-1-orchestrator Lambda.
    const mismatchedCoinSymbols = ["ACT", "ALPHA", "BEAM", "CAT", "CORE", "CYBER", "FLM", "FRONT", "G", "GFI", "GOAT", "KMD", "LOOM", "MBOX", "MNT", "ONE", "ORN", "PYR", "QUICK", "RFOX", "SCR", "SOLO", "SXP", "TON", "TRIAS", "TRU", "ZCX"];
    if (mismatchedCoinSymbols.includes(String(coinSymbol || '').toUpperCase())) {
        output += `\n⚠️ ${coinSymbol}: the price source lists a different coin under this symbol, so this analysis is probably not for the coin you mean.\n`;
    }
    output += `\nℹ️ Prices come from Yahoo Finance. Some symbols are shared by more than one coin, so check the price matches the coin you mean.\nGeneral information only, not financial advice.\n`;
    return { type: 'single_coin_analysis', data: output };
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
            const price = `$AUD${(stock.current_price || stock.price || 0).toFixed(2)}`.padStart(10);
            const score = (stock.total_score || stock.score || 0) >= 0 ? `+${(stock.total_score || stock.score || 0).toFixed(1)}` : `${(stock.total_score || stock.score || 0).toFixed(1)}`;
            const rsi = (stock.rsi || 0).toFixed(1).padStart(5);
            const ytd = (stock.ytd_change || 0) >= 0 ? `+${(stock.ytd_change || 0).toFixed(1)}%` : `${(stock.ytd_change || 0).toFixed(1)}%`;
            const vol = `${(stock.volume_ratio || 1).toFixed(1)}x`;
            output += `${(i+1).toString().padStart(2)}. ${symbol} ${price} | Score: ${score} | RSI: ${rsi} | YTD: ${ytd}, Vol: ${vol}\n`;
        });
        
        output += '</table><div style="margin: 20px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;">📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.</div><table class="results-table">\n';
        
        // Add detailed analysis for top 3 stocks
        output += '\n🎯 TOP 3 DETAILED ANALYSIS:\n';
        output += '================================================================\n';
        sortedResults.slice(0, 3).forEach((stock, i) => {
            output += `${i+1}. ${stock.symbol}: $AUD${(stock.price || 0).toFixed(2)} | ${signalLabel(stock.recommendation)} | Score: ${(stock.total_score || stock.score || 0) >= 0 ? '+' : ''}${(stock.total_score || stock.score || 0).toFixed(1)}\n`;
            
            if (stock.score_breakdown && stock.score_breakdown.length > 0) {
                output += '   📊 Score Breakdown:\n';
                stock.score_breakdown.forEach(breakdown => {
                    output += `      ${breakdown}\n`;
                });
            }
            
            output += `   📈 Technical: RSI ${(stock.rsi || 50).toFixed(1)} | MACD ${stock.macd_signal || 'NEUTRAL'}\n`;
            output += `   💰 Levels: Support $AUD${(stock.support || 0).toFixed(2)} | Resistance $AUD${(stock.resistance || 0).toFixed(2)}\n`;
            output += `   📏 Reference levels: Lower $AUD${(stock.stop_loss || 0).toFixed(2)} | Upper $AUD${(stock.take_profit || 0).toFixed(2)}\n`;
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

function runFTSE100Screener() {
    console.log('🇬🇧 UK FTSE 100 Screener');
    
    document.getElementById('results').style.display = 'block';
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results-content').innerHTML = '';
    
    fetch('https://jj3bbmgmeqab6zeksees37cute0tncvs.lambda-url.us-east-1.on.aws/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('loading').style.display = 'none';
        
        if (data.success && data.results) {
            let output = `
============================================================
🇬🇧 UK FTSE 100 RESULTS (REAL-TIME DATA)
============================================================

Screening Universe: ${data.results.length} FTSE stocks
Market Type: London Stock Exchange
Universe Size: ${data.results.length}
Analysis Date: ${new Date().toLocaleString()}

🟢 TOP ${Math.min(10, data.results.length)} BY SCORE:

`;
            
            const sortedResults = [...data.results].sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
            
            sortedResults.slice(0, Math.min(10, data.results.length)).forEach((stock, i) => {
                const symbol = (stock.symbol || 'N/A').padEnd(8);
                const price = `£${(stock.current_price || stock.price || 0).toFixed(2)}`.padStart(8);
                const score = (stock.total_score || stock.score || 0) >= 0 ? `+${(stock.total_score || stock.score || 0).toFixed(1)}` : `${(stock.total_score || stock.score || 0).toFixed(1)}`;
                const rsi = (stock.rsi || 0).toFixed(1).padStart(5);
                const ytd = (stock.ytd_change || 0) >= 0 ? `+${(stock.ytd_change || 0).toFixed(1)}%` : `${(stock.ytd_change || 0).toFixed(1)}%`;
                const vol = `${(stock.volume_ratio || 1).toFixed(1)}x`;
                output += `${symbol} ${price} | Score: ${score} | RSI: ${rsi} | YTD: ${ytd}, Vol: ${vol}\n\n`;
            });
            
            output += '🎯 TOP 3 DETAILED ANALYSIS:\n';
            sortedResults.slice(0, 3).forEach((stock, i) => {
                output += `${stock.symbol}: £${(stock.price || 0).toFixed(2)} | ${signalLabel(stock.recommendation)} | Score: ${(stock.total_score || stock.score || 0) >= 0 ? '+' : ''}${(stock.total_score || stock.score || 0).toFixed(1)}\n`;
                
                if (stock.score_breakdown && stock.score_breakdown.length > 0) {
                    output += '📊 Score Breakdown:\n';
                    stock.score_breakdown.forEach(breakdown => {
                        output += `${breakdown}\n`;
                    });
                }
                
                output += `📈 Technical: RSI ${(stock.rsi || 50).toFixed(1)} | MACD ${stock.macd_signal || 'BULLISH'}\n`;
                output += `💰 Levels: Support £${(stock.support || 0).toFixed(2)} | Resistance £${(stock.resistance || 0).toFixed(2)}\n`;
                output += `📏 Reference levels: Lower £${(stock.stop_loss || 0).toFixed(2)} | Upper £${(stock.take_profit || 0).toFixed(2)}\n`;
                output += `📊 Horizon: ${horizonLabel(stock.strategy_type)} | Confidence: ${(stock.confidence || 70).toFixed(0)}%\n\n`;
            });
            
            const positiveStocks = sortedResults.filter(s => (s.total_score || s.score || 0) > 0).length;
            const negativeStocks = sortedResults.filter(s => (s.total_score || s.score || 0) < 0).length;
            const avgScore = sortedResults.reduce((sum, s) => sum + (s.total_score || s.score || 0), 0) / sortedResults.length;
            
            output += `📊 ANALYSIS SUMMARY:\n`;
            output += `• Total stocks analyzed: ${sortedResults.length}\n`;
            output += `• Stocks with positive scores: ${positiveStocks}\n`;
            output += `• Stocks with negative scores: ${negativeStocks}\n`;
            output += `• Average score: ${avgScore.toFixed(1)}\n`;
            output += `• Success rate: ${((positiveStocks/sortedResults.length)*100).toFixed(1)}%\n\n`;
            
            output += `✅ Real-time UK FTSE 100 complete!\n`;
            
            document.getElementById('results-content').innerHTML = output;
        } else {
            document.getElementById('results-content').innerHTML = 'Error: Unable to fetch UK FTSE 100 data';
        }
    })
    .catch(error => {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('results-content').innerHTML = `Error: ${error.message}`;
    });
}

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
function formatNikkeiResult(apiData) {
    const universeSize = 225;  // real list size (refreshed 10 Oct 2026)
    let output = `
============================================================
🇯🇵 JAPAN NIKKEI 225 RESULTS (REAL-TIME DATA)
============================================================
Screening Universe: ${universeSize} Japan Nikkei stocks
Market Type: Tokyo Stock Exchange
Universe Size: ${universeSize}
Analysis Date: ${new Date().toLocaleString()}
`;
    if (apiData.results && apiData.results.length > 0) {
        const sortedResults = [...apiData.results].sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
        const topCount = Math.min(10, sortedResults.length);
        output += `🟢 TOP ${topCount} BY SCORE:\n`;
        sortedResults.slice(0, topCount).forEach((stock, i) => {
            const symbol = (stock.symbol || 'N/A').padEnd(8);
            const name = NIKKEI_COMPANY_NAMES[stock.symbol] || stock.symbol;
            const price = `\u00A5${(stock.current_price || stock.price || 0).toFixed(0)}`.padStart(10);
            const scoreVal = stock.total_score || stock.score || 0;
            const score = scoreVal >= 0 ? `+${scoreVal.toFixed(1)}` : `${scoreVal.toFixed(1)}`;
            const rsi = (stock.rsi || 0).toFixed(1).padStart(5);
            const ytdVal = stock.ytd_change || 0;
            const ytd = ytdVal >= 0 ? `+${ytdVal.toFixed(1)}%` : `${ytdVal.toFixed(1)}%`;
            const vol = `${(stock.volume_ratio || 1).toFixed(1)}x`;
            output += `${(i+1).toString().padStart(2)}. ${symbol} ${name.slice(0, 22).padEnd(22)} ${price} | Score: ${score} | RSI: ${rsi} | YTD: ${ytd}, Vol: ${vol}\n`;
        });
        output += '\n</pre><div style="margin: 20px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;">📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html" style="color: #007bff; text-decoration: underline; cursor: pointer;">dashboard</a>.</div><pre style="white-space: pre-wrap; font-family: monospace;">\n🎯 TOP 3 DETAILED ANALYSIS:\n';
        output += '================================================================\n';
        sortedResults.slice(0, 3).forEach((stock, i) => {
            const priceVal = stock.price || 0;
            const scoreVal = stock.total_score || stock.score || 0;
            output += `${i+1}. ${stock.symbol}: \u00A5${priceVal.toFixed(0)} | ${signalLabel(stock.recommendation)} | Score: ${scoreVal >= 0 ? '+' : ''}${scoreVal.toFixed(1)}\n`;
            if (stock.score_breakdown && stock.score_breakdown.length > 0) {
                output += '   📊 Score Breakdown:\n';
                stock.score_breakdown.forEach(breakdown => {
                    output += `      ${breakdown}\n`;
                });
            }
            output += `   📈 Technical: RSI ${(stock.rsi || 50).toFixed(1)} | MACD ${stock.macd_signal || 'NEUTRAL'}\n`;
            output += `   💰 Levels: Support \u00A5${(stock.support || 0).toFixed(0)} | Resistance \u00A5${(stock.resistance || 0).toFixed(0)}\n`;
            output += `   📏 Reference levels: Lower \u00A5${(stock.stop_loss || 0).toFixed(0)} | Upper \u00A5${(stock.take_profit || 0).toFixed(0)}\n`;
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
    output += `\n\u2705 Real-time Japan Nikkei 225 complete!`;
    const htmlOutput = `<pre style="white-space: pre-wrap; font-family: monospace;">${output}</pre>`;
    return { type: 'option_5nikkei225_screener', data: htmlOutput };
}

function formatUKResult(apiData, subOption) {
    const results = apiData.results || [];
    
    let output = `
============================================================
🌍 MORE MARKETS - UK FTSE 100 RESULTS (REAL-TIME DATA)
============================================================

Screening Universe: ${results.length} UK stocks
Analysis Date: ${new Date().toLocaleString()}
Currency: GBP (£)

`;
    
    // Sort by score descending
    results.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
    
    results.forEach((stock, i) => {
        const symbol = stock.symbol || 'N/A';
        const price = stock.price ? `£${stock.price.toFixed(2)}` : 'N/A';
        const change = stock.change_pct ? `${stock.change_pct > 0 ? '+' : ''}${stock.change_pct.toFixed(2)}%` : 'N/A';
        const score = stock.total_score || stock.score || 0;
        const recommendation = signalLabel(stock.recommendation);
        
        output += `${i + 1}. ${symbol}\n`;
        output += `   Price: ${price} | Change: ${change}\n`;
        output += `   Score: ${score}/100 | Signal: ${recommendation}\n`;
        
        if (stock.support && stock.resistance) {
            output += `   Support: £${stock.support.toFixed(2)} | Resistance: £${stock.resistance.toFixed(2)}\n`;
        }
        if (stock.rsi) {
            output += `   RSI: ${stock.rsi.toFixed(1)} | Volume Ratio: ${(stock.volume_ratio || 1).toFixed(2)}\n`;
        }
        if (stock.macd_signal) {
            output += `   MACD: ${stock.macd_signal} | BB Signal: ${stock.bb_signal || 'NEUTRAL'}\n`;
        }
        output += `\n`;
    });
    
    // Summary statistics
    if (results.length > 0) {
        const avgScore = results.reduce((sum, stock) => sum + (stock.total_score || stock.score || 0), 0) / results.length;
        const positiveStocks = results.filter(stock => (stock.total_score || stock.score || 0) >= 60).length;
        
        output += `\n============================================================\n`;
        output += `📊 SUMMARY STATISTICS:\n`;
        output += `• Total stocks analyzed: ${results.length}\n`;
        output += `• Average score: ${avgScore.toFixed(1)}\n`;
        output += `• Success rate: ${((positiveStocks/results.length)*100).toFixed(1)}%\n\n`;
        
        output += `✅ Real-time UK FTSE 100 complete!\n`;
    } else {
        output += 'No results available.\n';
    }
    
    const htmlOutput = `<pre style="white-space: pre-wrap; font-family: monospace;">${output}</pre>
<div style="margin-top: 20px; padding: 15px; background: var(--card-bg); border-radius: 8px; text-align: center; font-size: 1rem;">
    📊 Showing top 10 results. For the complete screener report, download from your <a href="dashboard.html" style="color: #007bff; text-decoration: underline;">dashboard</a>.
</div>`;
    
    return {
        type: 'uk_ftse_analysis',
        data: htmlOutput
    };
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
