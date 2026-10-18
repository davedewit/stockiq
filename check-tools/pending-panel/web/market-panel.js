/* market-panel.js: the market panel on the right of the home page and the dashboard, one script for both (18 Oct 2026).
 *
 * The owner: "is there a smarter way to set them up. the dashboard and index.html should match". Each page had its own copy of
 * the same code (the market tabs and their figures, the four lists: trending, top gainers, top losers, most active; the US
 * market countdown; the arrows), written again inside the page more than once (the home page switched tabs in three places).
 * The page keeps only its markup (`#news-panel` with `#market-tabs-sidebar`, `#market-data-sidebar-container`, the four
 * `#<kind>-tickers-container`, `#market-status-sidebar`, `#market-countdown-sidebar`); this script fills it and keeps it fresh.
 * live-market.js (loaded by theme.js) keeps the figures on show moving every few seconds while someone is looking; this
 * script asks for the lists and the panel's data itself every 5 minutes while someone is using the page.
 *
 * The names the pages' other code calls are kept: renderMarketDataSidebar(tab), fetchMarketDataSidebar(), switchToTab(tab),
 * updateMarketCountdownSidebar(), window.render<Trending|Gainers|Losers|Active>Tickers(list), fetchSidebarTickers(); and the
 * globals marketDataSidebar, currentTabSidebar, tabOrder, currentTabIndex. A click on a list's row runs the analysis in the
 * background where the page can (the dashboard: runSidebarAnalysis) and opens the analysis page otherwise (the home page).
 */
(function () {
    'use strict';
    if (window.marketPanel) return;
    var CATEGORIES = {
        us: 'https://xqma6tuoaeb5nd32gpdyk5uonm0yvgiy.lambda-url.us-east-1.on.aws/',
        europe: 'https://2azr7bjzjfvkadj2hzztk5icia0xnnoa.lambda-url.us-east-1.on.aws/',
        asia: 'https://kzspffs5uombzw73vudd3p57x40agikm.lambda-url.us-east-1.on.aws/',
        cryptocurrencies: 'https://x5xnafkpdtym4i7vezbhjaizry0leaxk.lambda-url.us-east-1.on.aws/',
        rates: 'https://ewowkcosbyc5rkk2b6ypvlx6la0pzfww.lambda-url.us-east-1.on.aws/',
        commodities: 'https://4ynwdgbmuf7jvxxxckmvu7plwa0gxnby.lambda-url.us-east-1.on.aws/',
        currencies: 'https://xdqiva3aoe4e4esa3cwdrkyt7i0izcvr.lambda-url.us-east-1.on.aws/'
    };
    // kind: [the rows' id prefix, the list's address, where the page keeps the list and its prices]
    var LISTS = {
        trending: ['trend', 'https://iz6jpzev3ty4q37anieqnckkxa0skisc.lambda-url.us-east-1.on.aws/', 'trendingTickersList', 'trendingTickerPrices'],
        gainers: ['gainer', 'https://hfya2wu77mjszyffeeqzvzhjh40iywvz.lambda-url.us-east-1.on.aws/', 'gainersTickersList', 'gainersTickerPrices'],
        losers: ['loser', 'https://dzzudu2sf6b2yh7j4utknjn33i0mhahj.lambda-url.us-east-1.on.aws/', 'losersTickersList', 'losersTickerPrices'],
        active: ['active', 'https://hd5z2yzvrksub43ihitf7ea3bq0opwxa.lambda-url.us-east-1.on.aws/', 'activeTickersList', 'activeTickerPrices']
    };
    var PRICES = 'https://2vl4la6od3vfgbkv6ycbj7ewry0yxvck.lambda-url.us-east-1.on.aws/';
    var EVERY = 5 * 60 * 1000, IDLE = 10 * 60 * 1000, SHOWN = 5;
    var lastInput = Date.now(), fetchedAt = {}, listsBusy = false;

    window.tabOrder = ['us', 'europe', 'asia', 'cryptocurrencies', 'rates', 'commodities', 'currencies'];
    window.currentTabSidebar = 'us';
    window.currentTabIndex = 0;
    window.marketDataSidebar = read('marketDataSidebar') || {};

    function read(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } }
    function write(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { } }
    function idOf(s) { return String(s).toLowerCase().replace(/[^a-z0-9]/g, ''); }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    function money(v) { return Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
    function changeText(c, p) { var s = p >= 0 ? '+' : ''; return s + Number(c).toFixed(2) + ' (' + s + Number(p).toFixed(2) + '%)'; }
    function inUse() { return !document.hidden && Date.now() - lastInput < IDLE; }
    function getJSON(url, body) {
        return fetch(body ? url : url + (url.indexOf('?') < 0 ? '?' : '&') + 't=' + Date.now(),
            body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : undefined).then(function (r) { return r.json(); });
    }

    // ---- the market tabs and their figures
    function container() {
        var modal = document.getElementById('mobile-sidebar-modal'), open = modal && modal.style.display === 'block';
        return (open && modal.querySelector('#market-data-sidebar-container')) || document.getElementById('market-data-sidebar-container');
    }
    function panelValue(v, cat) { return cat === 'cryptocurrencies' && v < 1000 ? Number(v).toFixed(4) : money(v); }
    window.renderMarketDataSidebar = function (tab) {
        tab = tab || window.currentTabSidebar;
        var box = container(), data = (window.marketDataSidebar || {})[tab];
        if (!box || !data) return;
        var loading = document.getElementById('loading-sidebar'); if (loading) loading.style.display = 'none';
        box.innerHTML = ''; box.style.display = 'grid';
        Object.keys(data).slice(0, 6).forEach(function (name) {
            var info = data[name]; if (!info || info.error || typeof info.value !== 'number') return;
            var up = info.change >= 0, sign = up ? '+' : '', symbol = info.symbol || name;
            var item = document.createElement('div');
            item.className = 'market-item-sidebar'; item.style.cursor = 'pointer'; item.title = 'Run Analysis';
            item.onclick = function () { window.location.href = 'analysis.html?symbol=' + encodeURIComponent(symbol) + '&option=1&subOption=custom'; };
            // the small chart: today's prices, drawn by live-market.js (until 18 Oct 2026 a random line); empty until then
            item.innerHTML = '<div class="market-item-sidebar-name">' + esc(name) + '</div>'
                + '<div class="market-item-sidebar-value">' + panelValue(info.value, tab) + '</div>'
                + '<svg class="market-item-sidebar-chart" width="100%" height="30" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline points="" stroke="' + (up ? '#22c55e' : '#ef4444') + '" stroke-width="1.5" fill="none" opacity="0.8"/></svg>'
                + '<div class="market-item-sidebar-change ' + (up ? 'positive' : 'negative') + '">' + sign + Number(info.change).toFixed(2) + ' (' + sign + Number(info.changePercent).toFixed(2) + '%)</div>';
            box.appendChild(item);
        });
    };
    window.fetchMarketDataSidebar = function (force) {
        var tab = window.currentTabSidebar;
        window.renderMarketDataSidebar(tab);                          // what was kept, at once
        if (document.hidden) return Promise.resolve();
        var due = function (c) { return force || !fetchedAt[c] || Date.now() - fetchedAt[c] >= EVERY - 1000; };
        var one = function (c) {
            if (!due(c)) return Promise.resolve();
            fetchedAt[c] = Date.now();
            return getJSON(CATEGORIES[c]).then(function (j) {
                var d = j && j[c];
                if (!d || !Object.keys(d).length) return;
                window.marketDataSidebar[c] = d; window.marketDataSidebar.timestamp = new Date().toISOString();
                write('marketDataSidebar', window.marketDataSidebar);
                if (c === window.currentTabSidebar) window.renderMarketDataSidebar(c);
                if (c === 'us' && typeof window.updateTopCardsFromData === 'function') window.updateTopCardsFromData(d);   // the home page's four cards
            }).catch(function () { fetchedAt[c] = 0; });
        };
        // the tab on show first, the others a moment later so that a click on another tab finds its figures ready
        return one(tab).then(function () { setTimeout(function () { Object.keys(CATEGORIES).forEach(function (c) { if (c !== tab) one(c); }); }, 1500); });
    };
    window.switchToTab = function (tab) {
        if (!CATEGORIES[tab]) return;
        window.currentTabSidebar = tab; window.currentTabIndex = window.tabOrder.indexOf(tab);
        document.querySelectorAll('.market-tab-sidebar').forEach(function (t) {
            var on = t.getAttribute('data-tab') === tab;
            t.classList.toggle('active', on);
            if (on && t.offsetParent && t.scrollIntoView) t.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        });
        window.renderMarketDataSidebar(tab);
        if (!fetchedAt[tab]) window.fetchMarketDataSidebar();
    };
    window.attachMarketTabListeners = function () { };                // the tabs and arrows are handled here, for every copy of them
    document.addEventListener('click', function (e) {
        var t = e.target && e.target.closest && e.target.closest('.market-tab-sidebar, #nav-left-sidebar, #nav-right-sidebar');
        if (!t) return;
        var n = window.tabOrder.length, i = window.currentTabIndex;
        if (t.id === 'nav-left-sidebar') window.switchToTab(window.tabOrder[(i - 1 + n) % n]);
        else if (t.id === 'nav-right-sidebar') window.switchToTab(window.tabOrder[(i + 1) % n]);
        else window.switchToTab(t.getAttribute('data-tab'));
    });

    // ---- the US market countdown
    window.updateMarketCountdownSidebar = function () {
        var ny = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' })), day = ny.getDay();
        var minutes = ny.getHours() * 60 + ny.getMinutes(), open = day >= 1 && day <= 5 && minutes >= 570 && minutes < 960;
        var target = new Date(ny);
        if (open) target.setHours(16, 0, 0, 0);
        else {
            target.setHours(9, 30, 0, 0);
            if (minutes >= 960 || day === 0 || day === 6) { do { target.setDate(target.getDate() + 1); } while (target.getDay() === 0 || target.getDay() === 6); }
        }
        var diff = target - ny, text = Math.floor(diff / 3600000) + 'h ' + Math.floor((diff % 3600000) / 60000) + 'm';
        var st = document.getElementById('market-status-sidebar'), cd = document.getElementById('market-countdown-sidebar');
        if (st) st.textContent = open ? '● U.S. markets close in' : '● U.S. markets open in';
        if (cd) cd.textContent = text;
    };

    // ---- the four lists
    function rowClick(ticker, div) {
        if (typeof window.runSidebarAnalysis === 'function') {
            div.style.background = 'var(--hover-bg)'; setTimeout(function () { div.style.background = 'transparent'; }, 2000);
            window.runSidebarAnalysis(ticker);
        } else window.location.href = 'analysis.html?symbol=' + encodeURIComponent(ticker) + '&option=1&subOption=custom';
    }
    function renderList(kind, tickers) {
        var L = LISTS[kind], box = document.getElementById(kind + '-tickers-container');
        if (!box) return;
        var prices = read(L[3]) || {}, back = typeof window.runSidebarAnalysis === 'function';
        box.innerHTML = '';
        (tickers || []).slice(0, SHOWN).forEach(function (ticker, i, all) {
            var p = prices[ticker] || {}, id = idOf(ticker), has = typeof p.price === 'number', up = p.changePercent >= 0;
            var div = document.createElement('div');
            div.style.cssText = 'display: flex; justify-content: space-between; align-items: flex-start; padding: 5px 0; cursor: pointer; transition: background 0.2s;'
                + (i < all.length - 1 ? ' border-bottom: 1px solid var(--border-color);' : '');
            div.title = back ? 'Run Analysis in Background' : 'Run Analysis';
            div.innerHTML = '<div style="flex: 1; pointer-events: none;"><div style="color: #3b82f6; font-size: 0.75rem; font-weight: 600; margin-bottom: 1px;">' + esc(ticker) + '</div>'
                + '<div id="' + L[0] + '-name-' + id + '" style="color: var(--text-secondary); font-size: 0.65rem;">' + esc(p.name || ticker) + '</div></div>'
                + '<div style="text-align: right; pointer-events: none;"><div id="' + L[0] + '-price-' + id + '" style="color: var(--text-primary); font-size: 0.75rem; font-weight: 600; margin-bottom: 1px;">' + (has ? money(p.price) : '--') + '</div>'
                + '<div id="' + L[0] + '-change-' + id + '" style="font-size: 0.65rem; color: ' + (has ? (up ? '#22c55e' : '#ef4444') : 'var(--text-secondary)') + ';">' + (has ? changeText(p.change, p.changePercent) : '') + '</div></div>';
            div.onmouseover = function () { div.style.background = 'var(--hover-bg)'; };
            div.onmouseout = function () { div.style.background = 'transparent'; };
            div.onclick = function () { rowClick(ticker, div); };
            box.appendChild(div);
        });
    }
    window.renderTrendingTickers = function (t) { renderList('trending', t); };
    window.renderGainersTickers = function (t) { renderList('gainers', t); };
    window.renderLosersTickers = function (t) { renderList('losers', t); };
    window.renderActiveTickers = function (t) { renderList('active', t); };
    function listOf(kind) { return (read(LISTS[kind][2]) || []).slice(0, SHOWN); }
    function renderLists() { Object.keys(LISTS).forEach(function (k) { renderList(k, listOf(k)); }); }
    // Which shares are on each list (four small requests), then their prices together (one request), then the lists drawn
    window.fetchSidebarTickers = function () {
        if (listsBusy || document.hidden) return Promise.resolve();
        listsBusy = true;
        var kinds = Object.keys(LISTS);
        return Promise.all(kinds.map(function (k) { return getJSON(LISTS[k][1]).catch(function () { return null; }); })).then(function (answers) {
            answers.forEach(function (a, i) { if (a && a.success && Array.isArray(a.tickers) && a.tickers.length) write(LISTS[kinds[i]][2], a.tickers); });
            var all = []; kinds.forEach(function (k) { listOf(k).forEach(function (t) { if (all.indexOf(t) < 0) all.push(t); }); });
            if (!all.length) return;
            return getJSON(PRICES, { tickers: all }).then(function (j) {
                if (!j || !j.success || !j.data) return;
                kinds.forEach(function (k) {
                    var cache = read(LISTS[k][3]) || {};
                    listOf(k).forEach(function (t) { var d = j.data[t]; if (d && !d.error) cache[t] = { name: d.name || t, price: d.price, change: d.change, changePercent: d.changePercent }; });
                    write(LISTS[k][3], cache);
                });
            });
        }).catch(function () { }).then(function () { listsBusy = false; renderLists(); });
    };
    ['fetchTrendingTickers', 'fetchTopGainers', 'fetchTopLosers', 'fetchMostActive'].forEach(function (n) { window[n] = function () { return window.fetchSidebarTickers(); }; });

    // ---- the panel's scroll hint (the arrow and the fade at its foot), on any page that has them
    function scrollHint() {
        var np = document.getElementById('news-panel'), arrow = document.getElementById('scroll-indicator');
        if (!np || !arrow || np.__mp) return; np.__mp = true;
        np.addEventListener('scroll', function () { var top = np.scrollTop > 50; arrow.style.display = top ? 'none' : 'block'; np.style.setProperty('--gradient-opacity', top ? '0' : '1'); });
    }

    function refresh() {
        window.renderMarketDataSidebar(window.currentTabSidebar); renderLists(); window.updateMarketCountdownSidebar();
        // in the phone sidebar the arrow and the fade at the panel's foot mean nothing: hidden there, shown again on the page
        var np = document.getElementById('news-panel'), arrow = document.getElementById('scroll-indicator');
        if (np && arrow) { var off = !!(np.closest && np.closest('#mobile-sidebar-content')) || np.scrollTop > 50; arrow.style.display = off ? 'none' : 'block'; np.style.setProperty('--gradient-opacity', off ? '0' : '1'); }
    }
    function start() {
        var np = document.getElementById('news-panel');
        if (np && !np.hasAttribute('data-desk-style')) np.setAttribute('data-desk-style', np.getAttribute('style') || '');   // put back after the phone sidebar
        scrollHint(); renderLists(); window.fetchMarketDataSidebar(true); window.fetchSidebarTickers();
        window.updateMarketCountdownSidebar(); setInterval(window.updateMarketCountdownSidebar, 60000);
        setInterval(function () { if (inUse()) { window.fetchMarketDataSidebar(); window.fetchSidebarTickers(); } }, EVERY);
    }
    ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(function (ev) { window.addEventListener(ev, function () { lastInput = Date.now(); }, { passive: true }); });
    document.addEventListener('visibilitychange', function () { if (!document.hidden && inUse()) { window.fetchMarketDataSidebar(); } });
    window.addEventListener('storage', function (e) {                // another tab of the site fetched newer figures
        if (e.key === 'marketDataSidebar' && e.newValue) { try { window.marketDataSidebar = JSON.parse(e.newValue); window.renderMarketDataSidebar(window.currentTabSidebar); } catch (x) { } }
    });
    window.marketPanel = { version: 1, refresh: refresh, renderLists: renderLists, deskStyle: function (np) { return np.getAttribute('data-desk-style'); } };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
