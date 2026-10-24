// Auto theme switching based on time
function getAutoTheme() {
    const hour = new Date().getHours();
    return (hour >= 18 || hour < 6) ? 'dark' : 'light';
}

let clickCount = 0;
let clickTimer = null;

function toggleTheme() {
    clickCount++;
    
    if (clickCount === 1) {
        clickTimer = setTimeout(() => {
            // Single click - toggle theme
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            localStorage.setItem('manualOverride', 'true');
            updateThemeIcon(newTheme);
            
            clickCount = 0;
        }, 300);
    } else if (clickCount === 2) {
        // Double click - reset to auto
        clearTimeout(clickTimer);
        resetToAutoTheme();
        clickCount = 0;
    }
}

// Double-click theme button to reset to automatic scheduling
function resetToAutoTheme() {
    localStorage.removeItem('manualOverride');
    localStorage.removeItem('theme');
    const autoTheme = getAutoTheme();
    document.documentElement.setAttribute('data-theme', autoTheme);
    localStorage.setItem('theme', autoTheme);
    updateThemeIcon(autoTheme);
    const timeRange = autoTheme === 'dark' ? '6PM-6AM' : '6AM-6PM';
    alert(`✅ Auto day/night mode restored!\n\nDark mode: 6PM-6AM\nLight mode: 6AM-6PM\nCurrent: ${autoTheme} (${timeRange})`);
}

function updateThemeIcon(theme) {
    const icons = document.querySelectorAll('.theme-icon');
    const mobileToggle = document.getElementById('mobile-theme-toggle');
    const manualOverride = localStorage.getItem('manualOverride') === 'true';
    const iconText = theme === 'dark' ? '☀️' : '🌙';
    const modeText = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
    const statusText = manualOverride ? ' (Manual)' : ' (Auto)';
    
    icons.forEach(icon => {
        icon.textContent = iconText;
        // Add visual indicator for manual override
        const button = icon.closest('button');
        if (button) {
            button.title = manualOverride ? 
                'Manual mode active. Double-click to restore auto day/night switching' : 
                'Auto day/night mode active. Click to override manually';
            button.style.opacity = manualOverride ? '0.8' : '1';
        }
    });
    
    if (mobileToggle) {
        mobileToggle.innerHTML = iconText + ' ' + modeText + statusText;
    }
}

function initTheme() {
    const manualOverride = localStorage.getItem('manualOverride');
    const savedTheme = localStorage.getItem('theme');
    
    let theme;
    if (manualOverride === 'true' && savedTheme) {
        theme = savedTheme;
    } else {
        theme = getAutoTheme();
        localStorage.setItem('theme', theme);
    }
    
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeIcon(theme);
    // Force icon update multiple times to ensure it shows
    setTimeout(() => updateThemeIcon(theme), 50);
    setTimeout(() => updateThemeIcon(theme), 200);
    setTimeout(() => updateThemeIcon(theme), 500);
}

function checkAutoTheme() {
    const manualOverride = localStorage.getItem('manualOverride');
    if (manualOverride !== 'true') {
        const autoTheme = getAutoTheme();
        const currentTheme = document.documentElement.getAttribute('data-theme');
        
        if (autoTheme !== currentTheme) {
            console.log(`Auto theme change: ${currentTheme} → ${autoTheme}`);
            document.documentElement.setAttribute('data-theme', autoTheme);
            localStorage.setItem('theme', autoTheme);
            updateThemeIcon(autoTheme);
        }
    }
}

// Ensure body scroll is restored when clicking any navigation link
function ensureBodyScrollEnabled() {
    document.body.classList.remove('menu-open');
    document.body.style.overflow = '';
    document.body.style.position = '';
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    
    // Initialize navigation position on page load
    if (window.innerWidth <= 768) {
        const nav = document.querySelector('.top-nav');
        const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
        if (currentScroll <= 100) {
            nav.style.transform = 'translateY(0)';
        } else {
            nav.style.transform = 'translateY(-100%)';
        }
    }
    
    // Add click listeners to all navigation links to ensure scroll is restored
    document.addEventListener('click', function(e) {
        if (e.target.matches('a[href], .nav-item, .mobile-section a')) {
            ensureBodyScrollEnabled();
        }
        
        // Also restore scroll when clicking outside the mobile menu
        const mobileMenu = document.getElementById('mobile-menu');
        const hamburgerBtn = document.querySelector('.hamburger-btn');
        
        if (mobileMenu && !mobileMenu.contains(e.target) && !hamburgerBtn.contains(e.target)) {
            ensureBodyScrollEnabled();
        }
    });
    
    // Restore scroll on window focus (when returning from another tab/app)
    window.addEventListener('focus', ensureBodyScrollEnabled);
    
    // Restore scroll on page visibility change
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            ensureBodyScrollEnabled();
        }
    });
});



// Mobile-only navigation scroll behavior
let lastScrollTop = 0;
let scrollTimeout;
let scrollStartPosition = 0;
let isScrollingUp = false;

function handleNavScroll() {
    // Only apply scroll behavior on mobile devices and when menu is not open
    if (window.innerWidth <= 768) {
        const nav = document.querySelector('.top-nav');
        const mobileMenu = document.getElementById('mobile-menu');
        const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
        
        // Don't hide nav when mobile menu is open
        if (mobileMenu && mobileMenu.classList.contains('open')) {
            nav.style.transform = 'translateY(0)';
            return;
        }
        
        // Always show nav when at or near top of page
        if (currentScroll <= 100) {
            nav.style.transform = 'translateY(0)';
        } else if (currentScroll > lastScrollTop && currentScroll > 100) {
            // Scrolling down - hide nav and reset scroll tracking
            nav.style.transform = 'translateY(-100%)';
            isScrollingUp = false;
            scrollStartPosition = currentScroll;
        } else if (currentScroll < lastScrollTop) {
            // Scrolling up - only show nav after significant upward movement
            if (!isScrollingUp) {
                scrollStartPosition = lastScrollTop;
                isScrollingUp = true;
            }
            
            // Require at least 150px of upward scroll before showing nav
            if (scrollStartPosition - currentScroll > 150) {
                nav.style.transform = 'translateY(0)';
            }
        }
        
        lastScrollTop = currentScroll <= 0 ? 0 : currentScroll;
    }
}

// Add scroll listener with throttling
window.addEventListener('scroll', function() {
    if (scrollTimeout) {
        clearTimeout(scrollTimeout);
    }
    scrollTimeout = setTimeout(handleNavScroll, 10);
});

// Check for auto theme changes every 30 seconds
setInterval(checkAutoTheme, 30000);

// Also check when page becomes visible (user returns to tab)
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        checkAutoTheme();
    }
});

// The notification bell also lists the AI autopilot's practice buys and sells (fake money). This file is the one script every
// page with a bell loads, so the small script that does it is fetched from here, for signed-in visitors only. (The hand-edited
// pages also fetch it themselves, between their AUTOPILOT_BELL comments, so that it does not wait on this file's day-long cache;
// this is what covers the generated stock pages.)
(function () {
    // The script is asked for beside this file, wherever the site is served from: at the top of its address on stockiq.tech,
    // below a folder in a local preview, one folder up from a stock page. (It was asked for at "/autopilot-bell.js", which is
    // nowhere unless the site sits at the top of its address: in a local preview the bell showed none of the trades.)
    var here = (document.currentScript && document.currentScript.src) || '';
    var beside = /theme\.js/.test(here) ? here.replace(/theme\.js.*$/, '') : '/';
    function go() {
        try {
            if (window.autopilotBell || !(document.getElementById('notification-bell') || document.getElementById('mobile-notification-bell'))) return;
            const user = localStorage.getItem('userId');
            if (!user || user === 'anonymous') return;
            const script = document.createElement('script');
            script.src = beside + 'autopilot-bell.js?h=' + Math.floor(Date.now() / 36e5); script.async = true;   // a new address every hour: a change to that script needs no version number anywhere
            document.head.appendChild(script);
        } catch (e) { /* the page works without it */ }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();

// VISITOR_BAR_START (check-tools/pending-banners-undo/deploy.sh takes everything from here to VISITOR_BAR_END out again)
// The visitor's usage count ("1 free today", "3/5 today", "Unlimited") is shown as a chip inside the header bar by
// visitor-bar.js. The pages still work the count out and write it into their own floating badge (#trial-status-display);
// this hides that badge before it is ever drawn, and the script reads it. The round "Start 3-Day Free Trial" and
// "Upgrade Plan" buttons, which the pages put in different corners, all sit bottom left.
// THIS BLOCK IS THE WHOLE SWITCH: without it every page shows its own badge and buttons exactly as it did before.
(function () {
    var here = (document.currentScript && document.currentScript.src) || '';
    var beside = /theme\.js/.test(here) ? here.replace(/theme\.js.*$/, '') : '/';
    function go() {
        try {
            if (window.visitorBar || document.getElementById('vb-old') || !document.querySelector('.top-nav .nav-container')) return;
            var old = document.createElement('style');
            old.id = 'vb-old';
            old.textContent = '#trial-status-display { display: none !important; } ' +
                '#sticky-register-btn a, #sticky-upgrade-btn a { left: 20px !important; right: auto !important; bottom: 20px !important; padding: 12px 20px !important; font-size: 0.9rem !important; }';
            document.head.appendChild(old);
            var script = document.createElement('script');
            script.src = beside + 'visitor-bar.js?h=' + Math.floor(Date.now() / 36e5); script.async = true;
            script.onerror = function () { old.remove(); };        // the script did not arrive: the page's own badge shows again
            document.head.appendChild(script);
        } catch (e) { /* the page works without it */ }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
// VISITOR_BAR_END

// LIVE_MARKET_START (18 Oct 2026; taking everything from here to LIVE_MARKET_END out switches it off on every page)
// The market data on the page (the side panel, the movers lists) is kept fresh by live-market.js while someone is looking at it:
// a request every 6 to 10 seconds while the tab is on screen and in use, slower when nothing changes, none when nobody is there.
(function () {
    var here = (document.currentScript && document.currentScript.src) || '';
    var beside = /theme\.js/.test(here) ? here.replace(/theme\.js.*$/, '') : '/';
    var tries = 0;
    function go() {
        try {
            if (window.liveMarket) return;
            var has = document.getElementById('market-data-sidebar-container') || document.querySelector('[id^="gainer-price-"],[id^="loser-price-"],[id^="active-price-"],[id^="trend-price-"]');
            if (!has) { if (++tries < 4) setTimeout(go, 2500); return; }      // the lists are drawn a moment after the page
            var script = document.createElement('script');
            script.src = beside + 'live-market.js?h=' + Math.floor(Date.now() / 36e5); script.async = true;
            document.head.appendChild(script);
        } catch (e) { /* the page works without it */ }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
// LIVE_MARKET_END

// SITE_HEADER_START (24 Oct 2026; taking everything from here to SITE_HEADER_END out switches it off on every page)
// The header's parts that a page lacks (the ☰ button, the phone menu and its swipe, the bell, the sign-in state and the
// usage count) are filled in by site-header.js, so the guides, the legal pages and the daily screener pages have the
// same header as the home page. A page that has its own keeps it.
(function () {
    var here = (document.currentScript && document.currentScript.src) || '';
    var beside = /theme\.js/.test(here) ? here.replace(/theme\.js.*$/, '') : '/';
    function go() {
        try {
            if (window.siteHeader || !document.querySelector('nav.top-nav .nav-container .desktop-nav')) return;
            var script = document.createElement('script');
            script.src = beside + 'site-header.js?h=' + Math.floor(Date.now() / 36e5); script.async = true;
            document.head.appendChild(script);
        } catch (e) { /* the page works without it */ }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
// SITE_HEADER_END
