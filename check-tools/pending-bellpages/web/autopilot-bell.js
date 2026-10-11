/* The AI autopilot's buys and sells in the notification bell, on every page that has the bell.
   - Each line says whether a sale was a profit or a loss and how much, with the code and the name; a buy says how much went in.
   - New ones are counted in the bell's red number (with unread reports) until the bell is opened, and stay marked "unread"
     until one of them is clicked, like a report.
   - In the bell's list the group with the newest item is on top: the autopilot's trades, or the report history.
   Fake money only: these are practice trades. Loaded by theme.js for signed-in visitors (the one script every page with a bell
   has); the dashboard also loads it itself. On the dashboard the autopilot panel hands over its own list (set); on other pages
   the list is asked for from the autopilot function ("bell": read-only) at most every two minutes. */
(function () {
    'use strict';
    if (window.autopilotBell) return;
    const API = 'https://qy6s553i647agmxthtecc24fje0zskms.lambda-url.us-east-1.on.aws/';
    const FRESH_MS = 2 * 60 * 1000, LOCKED_MS = 30 * 60 * 1000, KEEP = 12, SHOW = 6;
    const get = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
    const put = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* a private window: it works for this page only */ } };
    const user = () => { const u = get('userId'); return u && u !== 'anonymous' ? u : null; };
    const key = (name) => 'stockiqAutopilot' + name + '_' + (user() || '');
    const esc = (s) => String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const ms = (t) => { const n = new Date(t).getTime(); return isNaN(n) ? 0 : n; };
    const when = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }); };
    const dollars = (n, cents) => '$' + Math.abs(n || 0).toLocaleString('en-US', { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 });

    // ---- the list, kept in the browser so that every page and tab shows the same
    function cache() { try { const c = JSON.parse(get(key('Trades')) || 'null'); return c && Array.isArray(c.trades) ? c : null; } catch (e) { return null; } }
    function trades() { const c = cache(); return c ? c.trades : []; }
    function set(list, allowed) {
        const next = (Array.isArray(list) ? list : []).filter(e => e && (e.type === 'buy' || e.type === 'sell') && e.t).slice(-KEEP);
        put(key('Trades'), JSON.stringify({ at: Date.now(), allowed: allowed !== false, trades: next }));
        refresh();
    }
    // two marks, as for reports: "seen" clears the red number when the bell is opened; "read" clears the unread mark when one is clicked
    function mark(name) {
        let at = get(key(name));
        if (at === null) {                                  // the first time: what is already there is not news
            const t = trades();
            if (!cache()) return null;
            at = t.length ? String(t[t.length - 1].t) : new Date(0).toISOString();
            put(key(name), at);
        }
        return at;
    }
    const after = (name) => { const at = mark(name); return at === null ? [] : trades().filter(e => String(e.t) > at); };
    const unseen = () => (user() ? after('Bell').length : 0);
    const unread = () => (user() ? after('Read').length : 0);
    function stamp(name) { const t = trades(); put(key(name), t.length ? String(t[t.length - 1].t) : new Date(0).toISOString()); }
    function markSeen() { stamp('Bell'); badge(); }
    function markRead() { stamp('Read'); stamp('Bell'); refresh(); }

    // ---- what the bell's list shows
    function delta(amount, percent) {
        const r = Math.round((amount || 0) * 100) / 100 || 0, p = typeof percent === 'number' ? ' (' + Math.abs(percent).toFixed(1) + '%)' : '';
        return `<span role="img" aria-label="${r === 0 ? 'level' : (r > 0 ? 'profit of ' : 'loss of ') + dollars(r, true)}${p}" style="color: ${r > 0 ? '#16a34a' : r < 0 ? '#ef4444' : 'var(--text-secondary)'}; font-weight: 700; white-space: nowrap;">${r > 0 ? '▲' : r < 0 ? '▼' : '–'} ${dollars(r, true)}${p}</span>`;
    }
    function html() {
        const all = trades();
        if (!user() || !all.length) return '';
        const readAt = mark('Read') || '', fresh = all.filter(e => String(e.t) > readAt).length;
        const rows = all.slice(-Math.max(SHOW, Math.min(fresh, KEEP))).reverse().map(e => {
            const isNew = String(e.t) > readAt, sold = e.type === 'sell', gain = sold && typeof e.gain === 'number' ? e.gain : null;
            const right = sold ? (gain === null ? (typeof e.pct === 'number' ? `<span style="font-weight: 700; color: ${e.pct >= 0 ? '#16a34a' : '#ef4444'};">${e.pct >= 0 ? '▲' : '▼'} ${Math.abs(e.pct).toFixed(1)}%</span>` : '') : delta(gain, e.pct))
                : `<span style="color: var(--text-secondary); white-space: nowrap;">${dollars(e.usd)}</span>`;
            const word = !sold ? 'Bought' : gain === null ? 'Sold' : gain > 0.004 ? 'Sold at a profit' : gain < -0.004 ? 'Sold at a loss' : 'Sold level';
            const edge = !isNew ? 'transparent' : !sold ? '#007bff' : gain !== null && gain < 0 ? '#ef4444' : '#16a34a';
            return `<div class="autopilot-bell-row" onclick="event.stopPropagation(); autopilotBell.open()" style="padding: 12px 15px; border-bottom: 1px solid var(--border-color); cursor: pointer; background: ${isNew ? 'var(--bg-secondary)' : 'var(--card-bg)'}; border-left: 3px solid ${edge};">
                <div style="display: flex; align-items: baseline; gap: 10px; font-size: 13px;">${isNew ? '<span style="width: 8px; height: 8px; background: #007bff; border-radius: 50%; flex-shrink: 0; align-self: center;"></span>' : '<span style="width: 8px; flex-shrink: 0;"></span>'}<span style="flex: 1; min-width: 0; font-weight: ${isNew ? 'bold' : '500'}; color: var(--text-primary);">${word}: ${esc(e.symbol)}</span>${right}</div>
                <div style="font-size: 11px; color: var(--text-secondary); margin: 2px 0 0 18px;">${e.name ? esc(e.name) + ' · ' : ''}${esc(when(e.t))}</div></div>`;
        }).join('');
        return `<div onclick="event.stopPropagation(); autopilotBell.open()" style="padding: 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary); cursor: pointer;">
                <h4 style="margin: 0; color: var(--text-primary); font-size: 14px;">🤖 AI autopilot (Beta): buys and sells</h4>
                <p style="margin: 5px 0 0 0; color: var(--text-secondary); font-size: 12px;">${fresh} unread · practice trades with fake money</p></div>${rows}`;
    }

    // ---- which group is newest: the autopilot's trades or the reports
    function newestReport() {
        let list = null;
        try { if (typeof analysisHistory !== 'undefined' && Array.isArray(analysisHistory)) list = analysisHistory; } catch (e) { /* this page keeps no such list */ }   // eslint-disable-line no-undef
        if (!list && Array.isArray(window.dashboardHistory)) list = window.dashboardHistory;
        if (!list) { try { const c = JSON.parse(get('dashboardHistoryCache_' + user()) || 'null'); list = c && c.data && c.data.history; } catch (e) { list = null; } }
        return (Array.isArray(list) ? list : []).reduce((best, i) => (i && !i.deleted ? Math.max(best, ms(i.timestamp)) : best), 0);
    }
    const newestTrade = () => { const t = trades(); return t.length ? ms(t[t.length - 1].t) : 0; };
    const onTop = () => newestTrade() >= newestReport();

    // ---- into the bell's list, wherever the page has drawn it
    function place() {
        const drop = document.getElementById('notification-dropdown');
        if (!drop) return;
        const old = document.getElementById('autopilot-bell-section'), markup = html();
        if (!markup) { if (old) old.remove(); const line = document.getElementById('autopilot-bell-pointer'); if (line) line.remove(); return; }
        const top = onTop(), sig = (top ? 'top' : 'end') + '|' + (cache() || {}).at + '|' + get(key('Read'));
        if (old && old.parentNode === drop && old.getAttribute('data-sig') === sig && (top ? drop.firstElementChild === old : !!document.getElementById('autopilot-bell-pointer'))) return;
        if (old) old.remove();
        const box = document.createElement('div');
        box.id = 'autopilot-bell-section'; box.setAttribute('data-sig', sig); box.setAttribute('data-place', top ? 'top' : 'end'); box.innerHTML = markup;
        if (!top) box.style.borderTop = '1px solid var(--border-color)';
        const foot = top ? null : Array.from(drop.children).reverse().find(c => c.tagName === 'A');     // the "view all" link stays last
        if (top) drop.insertBefore(box, drop.firstChild); else if (foot) drop.insertBefore(box, foot); else drop.appendChild(box);
        pointer(drop, top);
    }
    // When the report history is on top, the trades can be below a long list: a slim line stays at the top of the bell's list
    // and takes the reader down to them.
    function pointer(drop, top) {
        const old = document.getElementById('autopilot-bell-pointer');
        if (old) old.remove();
        if (top) return;
        const n = unread(), line = document.createElement('div');
        line.id = 'autopilot-bell-pointer';
        line.style.cssText = 'position: sticky; top: 0; z-index: 1; padding: 8px 15px; font-size: 12px; cursor: pointer; background: var(--card-bg); border-bottom: 1px solid var(--border-color); color: var(--text-secondary); display: flex; justify-content: space-between; gap: 10px;';
        line.innerHTML = `<span><strong style="color: var(--text-primary);">🤖 AI autopilot (Beta)</strong> · ${n ? n + ' unread buy' + (n === 1 ? ' or sell' : 's and sells') : 'buys and sells'}</span><span style="color: #007bff; white-space: nowrap;">below ↓</span>`;
        line.onclick = (e) => { e.stopPropagation(); const box = document.getElementById('autopilot-bell-section'); if (box && box.scrollIntoView) box.scrollIntoView({ block: 'start' }); };
        drop.insertBefore(line, drop.firstChild);
    }
    let watched = null;
    function watch(drop) {                                  // the page redraws its list now and then: put the trades back
        if (!drop || watched === drop || typeof MutationObserver === 'undefined') return;
        watched = drop;
        new MutationObserver(() => place()).observe(drop, { childList: true });
    }
    function open() {                                       // a click on one of them: to the autopilot's own list
        markRead();
        const drop = document.getElementById('notification-dropdown');
        if (drop) drop.remove();
        if (window.practiceAutopilot && window.practiceAutopilot.bellOpen) window.practiceAutopilot.bellOpen();
        else window.location.href = '/dashboard.html#autopilot';
    }

    // ---- the red number: unread reports plus the trades made since the bell was last opened
    function reportsUnseen() {
        try {
            const u = user(), unreadIds = Array.from(new Set(JSON.parse(get('unreadReports_' + u) || '[]'))), seen = JSON.parse(get('seenReports_' + u) || '[]');
            return unreadIds.filter(id => !seen.includes(id)).length;
        } catch (e) { return 0; }
    }
    function badge() {
        const mine = unseen();
        ['notification-badge', 'mobile-notification-badge'].forEach(id => {
            const b = document.getElementById(id);
            if (!b) return;
            if (!mine && !b.getAttribute('data-autopilot')) return;         // nothing of ours: the page's own count stands
            const total = reportsUnseen() + mine, text = total > 9 ? '9+' : String(total), show = total > 0 ? 'flex' : 'none';
            if (mine) b.setAttribute('data-autopilot', '1'); else b.removeAttribute('data-autopilot');
            if (b.textContent !== text) b.textContent = text;
            if (b.style.display !== show) b.style.display = show;
        });
    }
    function refresh() { badge(); place(); }

    // ---- asking for the list (not on the dashboard, where the panel has it)
    let asking = false;
    function load(force) {
        const u = user();
        if (!u) return;
        if (document.getElementById('practice-autopilot')) { if (window.practiceAutopilot && window.practiceAutopilot.bellFeed) window.practiceAutopilot.bellFeed(); return; }
        const c = cache(), age = c ? Date.now() - c.at : Infinity;
        if (asking || (!force && age < (c && c.allowed === false ? LOCKED_MS : FRESH_MS))) return;
        asking = true;
        fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'bell', userId: u }) })
            .then(r => (r.ok ? r.json() : null)).then(d => { if (d && d.success) set(d.trades, d.allowed); })
            .catch(() => { /* the bell works without it */ }).then(() => { asking = false; });
    }

    window.autopilotBell = { set, trades, unseen, unread, markSeen, markRead, html, place, open, badge, load, onTop };

    function start() {
        document.addEventListener('click', (e) => {
            const t = e.target && e.target.closest ? e.target : null;
            if (!t || !t.closest('#notification-bell, #mobile-notification-bell') || t.closest('#notification-dropdown')) return;
            setTimeout(() => {                              // after the page has opened (or closed) its list
                const drop = document.getElementById('notification-dropdown');
                if (!drop) return;
                place(); watch(drop); markSeen();
            }, 0);
        }, true);                                           // on the way down: a page's own handler cannot stop it from being heard
        if (typeof MutationObserver !== 'undefined') {      // the page sets the number from its reports: add the trades to it
            ['notification-badge', 'mobile-notification-badge'].forEach(id => {
                const b = document.getElementById(id);
                if (b) new MutationObserver(() => badge()).observe(b, { attributes: true, attributeFilter: ['style'], childList: true, characterData: true, subtree: true });
            });
        }
        window.addEventListener('storage', (e) => { if (e.key && e.key.indexOf('stockiqAutopilot') === 0) refresh(); });
        refresh();
        load();
        setInterval(() => { if (!document.hidden) load(); }, FRESH_MS);
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
