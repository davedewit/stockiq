// site-header.js: the header every page should have, filled in where a page lacks a part of it (24 Oct 2026).
//
// Loaded by theme.js (between SITE_HEADER_START and SITE_HEADER_END: take those lines out to switch it off everywhere).
// The home page, the analysis page, the dashboard and the stock pages have the whole header in their own markup; the
// guides, the legal pages and the daily screener pages had only the desktop menu: no ☰ button or bell on a phone, no
// swipe, and no sign-in state or usage count anywhere (they never loaded auth.js). This script adds, only where missing:
//   1. the phone bar: the ☰ button and the bell (.mobile-nav inside the header bar);
//   2. the phone menu (#mobile-menu and its overlay), built from the page's own desktop menu, so the two always agree;
//   3. toggleMobileMenu() / closeMobileMenu(), and on these pages a bell that opens the one list (autopilot-bell.js fills it);
//   4. auth.js: the visitor's name in the Account menu, the bell for a signed-in visitor, and the usage count
//      (visitor-bar.js turns that into the chip in the bar);
//   5. mobile-sidebar.js: the menu follows a swipe from the left, as on the home page.
// Nothing here is drawn for a page that has its own: a page's own code always wins.
(function () {
    'use strict';
    if (window.siteHeader) return;
    var VERSION = 1;
    var here = (document.currentScript && document.currentScript.src) || '';
    var beside = /theme\.js/.test(here) ? here.replace(/theme\.js.*$/, '') : (/site-header\.js/.test(here) ? here.replace(/site-header\.js.*$/, '') : '/');
    var added = [];

    var BELL_SVG = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' +
        '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>';
    var BADGE = 'position: absolute; top: -5px; right: -5px; background: #dc3545; color: white; border-radius: 50%; width: 18px; height: 18px; ' +
        'font-size: 11px; font-weight: bold; display: none; align-items: center; justify-content: center;';

    function el(tag, attrs, html) {
        var e = document.createElement(tag);
        Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
        if (html) e.innerHTML = html;
        return e;
    }
    function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
    function signedIn() { try { var u = localStorage.getItem('userId'); return !!u && u !== 'anonymous'; } catch (e) { return false; } }
    function hasScript(name) { return !!document.querySelector('script[src*="' + name + '"]'); }
    function load(name, then) {
        var s = document.createElement('script');
        s.src = beside + name + '?h=' + Math.floor(Date.now() / 36e5);
        s.async = true;
        if (then) s.onload = then;
        document.head.appendChild(s);
        added.push(name);
    }

    // ---- 1. the phone bar
    var PHONE_BELL = '<button class="notification-bell" id="mobile-notification-bell" onclick="goToNotifications(event)" title="Notifications" ' +
        'aria-label="View notifications" style="display: none; position: relative; background: none; border: none; font-size: 20px; ' +
        'cursor: pointer; color: var(--text-primary); margin-left: 10px;">' + BELL_SVG +
        '<span class="notification-badge" id="mobile-notification-badge" style="' + BADGE + '"></span></button>';
    function phoneBar(container) {
        var own = container.querySelector('.mobile-nav');
        if (own || container.querySelector('.hamburger-btn')) {
            // the page has its own phone bar; the stock pages' has no bell: add it beside the ☰ button
            if (own && !document.getElementById('mobile-notification-bell') && document.getElementById('notification-bell')) {
                own.insertAdjacentHTML('beforeend', PHONE_BELL);
                added.push('phone bell');
            }
            return false;
        }
        var bar = el('div', { 'class': 'mobile-nav' });
        bar.innerHTML =
            '<button class="hamburger-btn" onclick="toggleMobileMenu()" aria-label="Open menu" aria-expanded="false">' +
            '<span class="hamburger-line"></span><span class="hamburger-line"></span><span class="hamburger-line"></span></button>' +
            (document.getElementById('mobile-notification-bell') ? '' : PHONE_BELL);
        container.appendChild(bar);
        added.push('phone bar');
        return true;
    }

    // ---- 2. the phone menu, from the desktop menu's own links
    function phoneMenu(desk) {
        if (document.getElementById('mobile-menu')) return false;
        var prefix = /\/stocks\//.test(location.pathname) ? '../' : '';
        var parts = [];
        var home = desk.querySelector('a.home-link');
        parts.push('<div class="mobile-section"><a href="' + esc(home ? home.getAttribute('href') : prefix + 'index.html') + '">🏠 Home</a></div>');
        parts.push('<div class="mobile-section" id="mobile-dashboard-section" style="display: none;"><a href="' + prefix + 'dashboard.html">📊 Dashboard</a></div>');
        Array.prototype.forEach.call(desk.querySelectorAll('.nav-item.dropdown'), function (item) {
            var title = '';
            Array.prototype.forEach.call(item.childNodes, function (n) { if (n.nodeType === 3) title += n.textContent; });
            title = title.replace(/\s+/g, ' ').trim();
            if (!title) return;
            var links;
            if (/^Account$/i.test(title)) {
                // auth.js rewrites this section for a signed-in visitor (name, Sign Out), so it starts as the signed-out one
                links = '<a href="' + prefix + 'signup.html">Register</a><a href="' + prefix + 'login.html">Login</a>';
            } else {
                links = Array.prototype.map.call(item.querySelectorAll('.dropdown-menu a'), function (a) {
                    return '<a href="' + esc(a.getAttribute('href') || '#') + '">' + esc(a.textContent.trim()) + '</a>';
                }).join('');
            }
            parts.push('<div class="mobile-section"><div class="mobile-section-title">' + esc(title) + '</div>' + links + '</div>');
        });
        var dark = document.documentElement.getAttribute('data-theme') === 'dark';
        parts.push('<div class="mobile-section"><div class="mobile-section-title">Theme</div>' +
            '<a href="#" onclick="event.preventDefault(); toggleTheme()" id="mobile-theme-toggle">' + (dark ? '☀️ Light Mode' : '🌙 Dark Mode') + '</a></div>');

        var overlay = el('div', { 'class': 'mobile-menu-overlay', id: 'mobile-menu-overlay', onclick: 'closeMobileMenu()' });
        var menu = el('div', { 'class': 'mobile-menu', id: 'mobile-menu' });
        menu.innerHTML =
            '<div class="mobile-menu-header"><span class="mobile-brand"><img src="' + prefix + 'stockiq-logo.png" alt="StockIQ" ' +
            'style="width: 20px; height: 20px; margin-right: 8px; vertical-align: middle;" width="20" height="20">StockIQ.tech</span>' +
            '<div class="mobile-header-controls"><button class="close-btn" onclick="closeMobileMenu()" aria-label="Close menu">×</button></div></div>' +
            '<div class="mobile-menu-content">' + parts.join('') + '</div>';
        var nav = document.querySelector('nav.top-nav');
        nav.parentNode.insertBefore(menu, nav.nextSibling);
        nav.parentNode.insertBefore(overlay, nav.nextSibling);
        added.push('phone menu');
        return true;
    }

    // ---- 3. what the buttons call
    function functions(light) {
        if (typeof window.toggleMobileMenu !== 'function') {
            window.toggleMobileMenu = function () {
                var menu = document.getElementById('mobile-menu'), overlay = document.getElementById('mobile-menu-overlay'), btn = document.querySelector('.hamburger-btn');
                if (!menu) return;
                var open = !menu.classList.contains('open');
                menu.classList.toggle('open', open);
                if (overlay) overlay.classList.toggle('show', open);
                if (btn) { btn.classList.toggle('active', open); btn.setAttribute('aria-expanded', open ? 'true' : 'false'); }
                document.body.classList.toggle('menu-open', open);         // styles.css stops the page scrolling, without moving it
            };
        }
        if (typeof window.closeMobileMenu !== 'function') {
            window.closeMobileMenu = function () {
                var menu = document.getElementById('mobile-menu'), overlay = document.getElementById('mobile-menu-overlay'), btn = document.querySelector('.hamburger-btn');
                if (menu) menu.classList.remove('open');
                if (overlay) overlay.classList.remove('show');
                if (btn) { btn.classList.remove('active'); btn.setAttribute('aria-expanded', 'false'); }
                document.body.classList.remove('menu-open');
            };
        }
        // These pages' bell went to the dashboard. Now it opens the one list, as on the home page: autopilot-bell.js puts
        // the reports and the autopilot's buys and sells into the #notification-dropdown opened here.
        if (light || typeof window.goToNotifications !== 'function') {
            window.goToNotifications = function (event) {
                var old = document.getElementById('notification-dropdown');
                if (old) { old.remove(); return; }
                var prefix = /\/stocks\//.test(location.pathname) ? '../' : '';
                if (!signedIn()) { location.href = prefix + 'login.html'; return; }
                var bell = (event && event.currentTarget && event.currentTarget.closest) ? event.currentTarget : document.getElementById('notification-bell');
                if (!bell) { location.href = prefix + 'dashboard.html'; return; }
                var phone = bell.id === 'mobile-notification-bell' || window.innerWidth <= 768;
                var drop = el('div', { id: 'notification-dropdown' });
                drop.style.cssText = 'position: ' + (phone ? 'fixed' : 'absolute') + '; top: ' + (phone ? '60px' : '100%') + '; ' +
                    (phone ? 'left: 50%; transform: translateX(-50%); width: calc(100vw - 40px);' : 'right: 0; width: 350px;') +
                    ' max-width: 350px; max-height: 400px; overflow-y: auto; background: var(--card-bg); border: 1px solid var(--border-color);' +
                    ' border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); z-index: 10000; margin-top: 5px; text-align: left;';
                drop.innerHTML = '<div style="padding: 15px; color: var(--text-secondary); font-size: 14px;">No notifications yet. ' +
                    '<a href="' + prefix + 'dashboard.html" style="color: #007bff;">View Dashboard</a></div>';
                bell.style.position = 'relative';
                bell.appendChild(drop);
                setTimeout(function () {
                    document.addEventListener('click', function shut(e) {
                        if (!bell.contains(e.target)) { drop.remove(); document.removeEventListener('click', shut); }
                    });
                }, 100);
            };
        }
    }

    // ---- 4. sign-in state and the usage count
    function auth() {
        if (typeof window.authManager !== 'undefined' || hasScript('auth.js')) return;
        load('auth.js', function () {
            // auth.js does its work on DOMContentLoaded, which has passed by now: do the same here
            try { if (window.authManager || typeof authManager !== 'undefined') authManager.checkAuthStatus(); } catch (e) { /* signed out */ }   // eslint-disable-line no-undef
            setTimeout(function () {
                try { if (typeof displayTrialStatus === 'function') displayTrialStatus(); } catch (e) { /* the count is not shown */ }   // eslint-disable-line no-undef
                try { if (signedIn() && typeof updateNotificationBell === 'function') updateNotificationBell(); } catch (e) { /* no bell */ }   // eslint-disable-line no-undef
                var dash = document.getElementById('mobile-dashboard-section');
                if (dash && signedIn()) dash.style.display = 'block';
            }, 200);
        });
    }

    // A list opened from the phone bell is centred under the bar (some pages place it as on a desktop, off the screen's edge)
    function centrePhoneList() {
        document.addEventListener('click', function (e) {
            if (!e.target || !e.target.closest || !e.target.closest('#mobile-notification-bell')) return;
            setTimeout(function () {
                var drop = document.getElementById('notification-dropdown');
                if (!drop || !drop.closest('#mobile-notification-bell')) return;
                drop.style.position = 'fixed'; drop.style.top = '60px'; drop.style.left = '50%'; drop.style.right = 'auto';
                drop.style.transform = 'translateX(-50%)'; drop.style.width = 'calc(100vw - 40px)'; drop.style.maxWidth = '350px';
            }, 0);
        }, true);
    }

    function go() {
        try {
            centrePhoneList();
            var container = document.querySelector('nav.top-nav .nav-container');
            var desk = container && container.querySelector('.desktop-nav');
            if (!container || !desk) return;
            var light = phoneBar(container);
            phoneMenu(desk);
            functions(light);
            auth();
            if (!window.mobileSidebar && !hasScript('mobile-sidebar.js') && document.getElementById('mobile-menu')) load('mobile-sidebar.js');
        } catch (e) { window.siteHeader && (window.siteHeader.fault = String(e)); }
    }

    window.siteHeader = { version: VERSION, added: added, fault: null };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
