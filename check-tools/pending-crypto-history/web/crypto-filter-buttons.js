// Crypto Results Time Filter
// Adds a slider that narrows the top 10 to coins that have been in the top 10 for at least N hours.
// The hours come from the orchestrator (hours_in_top10), which records the top 10 on a schedule.

function addCryptoFilterButtons() {
    const resultsContent = document.getElementById('results-content');
    if (!resultsContent || !window.cryptoRawResults) return;
    
    // Check if slider already exists
    if (document.getElementById('crypto-filter-buttons')) return;
    
    // Store the existing pre or div element
    const existingPre = resultsContent.querySelector('pre') || resultsContent.querySelector('div[style*="monospace"]');
    if (!existingPre) return;
    
    // Store the original comprehensive report HTML for restoration
    if (!window.cryptoOriginalReport) {
        window.cryptoOriginalReport = existingPre.outerHTML;
    }
    
    // Create filter slider container with proper styling
    const filterContainer = document.createElement('div');
    filterContainer.id = 'crypto-filter-buttons';
    filterContainer.style.cssText = 'margin: 10px 0; padding: 15px; background: var(--card-bg); border-radius: 8px; border: 1px solid var(--border-color); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;';
    
    filterContainer.innerHTML = `<div style="font-weight: 600; font-size: 15px; color: var(--text-primary); margin-bottom: 8px;">⏱️ Time in the top 10</div><div style="margin-bottom: 12px; color: var(--text-secondary); font-size: 13px; line-height: 1.5;">Show only coins that have been in the top 10 for at least this long.<br>A longer time means the coin has held its ranking. It does not say where the price goes next.</div><div style="display: flex; align-items: center; gap: 10px; margin-top: 12px;"><span style="font-size: 12px; color: var(--text-secondary); min-width: 70px;">All Results</span><div style="position: relative; flex: 1; max-width: 200px; height: 30px; background: linear-gradient(to right, #bfdbfe, #2563eb); border-radius: 15px; cursor: pointer;" id="crypto-slider-track"><div id="crypto-slider-thumb" style="position: absolute; top: 2px; left: 2px; width: 26px; height: 26px; background: white; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.3); cursor: grab; transition: left 0.2s ease;"></div></div><span style="font-size: 12px; color: var(--text-secondary); min-width: 60px; text-align: right;">24+ Hours</span></div><div id="crypto-threshold-display" style="text-align: center; margin-top: 10px; font-size: 14px; font-weight: 600; color: var(--text-primary);">All Results</div>`;
    
    // Insert slider before the pre element
    resultsContent.insertBefore(filterContainer, existingPre);
    
    // Initialize slider
    initCryptoSlider();
}

function initCryptoSlider() {
    const track = document.getElementById('crypto-slider-track');
    const thumb = document.getElementById('crypto-slider-thumb');
    const display = document.getElementById('crypto-threshold-display');
    
    if (!track || !thumb || !display) return;
    
    let isDragging = false;
    let currentValue = 0; // 0=all, 1=1hr, 2=4hr, 3=24hr
    
    const positions = [0, 33.33, 66.66, 100];
    const labels = ['All Results', '1+ Hours', '4+ Hours', '24+ Hours'];
    const values = ['all', 1, 4, 24];
    
    function updateSlider(position) {
        // Snap to nearest position
        let nearest = 0;
        let minDist = Math.abs(position - positions[0]);
        for (let i = 1; i < positions.length; i++) {
            const dist = Math.abs(position - positions[i]);
            if (dist < minDist) {
                minDist = dist;
                nearest = i;
            }
        }
        
        currentValue = nearest;
        const snapPos = positions[nearest];
        thumb.style.left = snapPos === 0 ? '2px' : snapPos === 100 ? 'calc(100% - 28px)' : `calc(${snapPos}% - 13px)`;
        display.textContent = labels[nearest];
        
        // Only filter if not at position 0 (All Results)
        if (nearest !== 0) {
            filterCryptoResults(values[nearest]);
        } else {
            // Restore original comprehensive report
            restoreOriginalReport();
        }
    }
    
    function handleMove(clientX) {
        const rect = track.getBoundingClientRect();
        const x = clientX - rect.left;
        const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
        updateSlider(percentage);
    }
    
    thumb.addEventListener('mousedown', () => isDragging = true);
    track.addEventListener('mousedown', (e) => {
        isDragging = true;
        handleMove(e.clientX);
    });
    
    document.addEventListener('mousemove', (e) => {
        if (isDragging) handleMove(e.clientX);
    });
    
    document.addEventListener('mouseup', () => isDragging = false);
    
    // Touch support
    thumb.addEventListener('touchstart', (e) => {
        isDragging = true;
        e.preventDefault();
    });
    
    track.addEventListener('touchstart', (e) => {
        isDragging = true;
        handleMove(e.touches[0].clientX);
        e.preventDefault();
    });
    
    document.addEventListener('touchmove', (e) => {
        if (isDragging) {
            handleMove(e.touches[0].clientX);
            e.preventDefault();
        }
    });
    
    document.addEventListener('touchend', () => isDragging = false);
}

function restoreOriginalReport() {
    if (!window.cryptoOriginalReport) return;
    
    const resultsContent = document.getElementById('results-content');
    const filterButtons = document.getElementById('crypto-filter-buttons');
    const existingPre = resultsContent.querySelector('pre') || resultsContent.querySelector('div[style*="monospace"]');
    
    if (existingPre) {
        existingPre.outerHTML = window.cryptoOriginalReport;
    }
}

function filterCryptoResults(minHours) {
    if (!window.cryptoRawResults) return;
    
    // Filter results
    // Only top-10 coins carry hours_in_top10; the list arrives sorted by rank
    let filteredCoins = window.cryptoRawResults.slice(0, 10).filter(coin =>
        typeof coin.hours_in_top10 === 'number' && coin.hours_in_top10 >= minHours);
    
    // Regenerate display with filtered results
    const report = generateFilteredCryptoReport(filteredCoins, minHours);
    
    // Update display
    const resultsContent = document.getElementById('results-content');
    const existingPre = resultsContent.querySelector('pre') || resultsContent.querySelector('div[style*="monospace"]');
    
    if (existingPre) {
        existingPre.outerHTML = report;
    }
}

function generateFilteredCryptoReport(coins, filterHours) {
    // Same line layout as the orchestrator's report: "N. icon SYMBOL $price | label | Score" (the dashboard
    // tracker reads the symbol and price from that part of the line).
    const label = (code) => (typeof signalLabel === 'function' ? signalLabel(code) : 'Unrated');
    const fmtPrice = (p) => p >= 1 ? `$${p.toFixed(2)}` : p >= 0.001 ? `$${p.toFixed(6)}` : `$${p.toFixed(10).replace(/0+$/, '')}`;
    const icons = { ESTABLISHED: '🟢', RECENT: '🟡' };

    let report = `<div style='font-family: monospace; line-height: 1.4; white-space: pre-wrap; margin-top: 0;'>`;
    report += `${'='.repeat(60)}\n`;
    report += `₿ CRYPTO SCREENER RESULTS (TOP COINS BY MARKET CAP)\n`;
    report += `${'='.repeat(60)}\n\n`;
    report += `Filter: in the top 10 for ${filterHours}+ hours\n`;
    report += `Coins shown: ${coins.length} of the top 10\n`;
    report += `(🟢 = in the top 10 for an hour or more   🟡 = under an hour)\n\n`;
    report += `🔥 TOP 10 BY SCORE, FILTERED:\n\n`;

    if (coins.length === 0) {
        report += `No coin in the current top 10 has been there for ${filterHours}+ hours.\n`;
    }

    coins.forEach((coin, i) => {
        const icon = icons[coin.prediction_status] || '🔵';
        report += `${(i+1).toString().padStart(2)}. ${icon} ${coin.symbol.padEnd(8)} ${fmtPrice(coin.price).padEnd(12)} | ${label(coin.recommendation).padEnd(17)} | Score: ${coin.score >= 0 ? '+' : ''}${coin.score}\n`;
        if (coin.prediction_message) report += `     ${coin.prediction_message}\n`;
        if (coin.time_since_message) report += `     ${coin.time_since_message}\n`;
        if (coin.momentum_message) report += `     ${coin.momentum_message}\n`;
        report += `\n`;
    });

    report += `\nGeneral information only, not financial advice.\n`;
    report += `</div>`;

    return report;
}
