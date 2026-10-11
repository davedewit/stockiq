/* The AI autopilot's buys and sells in the notification bell, on every page that has the bell.
   - Each line says whether a sale was a profit or a loss and how much, with the code and the name; a buy says how much went in.
   - New ones are counted in the bell's red number (with unread reports) until the bell is opened, and stay marked "unread"
     until one of them is clicked, like a report.
   - The bell's list is ONE list, drawn here for every page that opens one: reports and the autopilot's buys and sells together,
     newest first (each page used to draw its own list of reports, in its own way; that drawing now gives way to this one).
   Fake money only: these are practice trades. Loaded by theme.js for signed-in visitors (the one script every page with a bell
   has); the dashboard also loads it itself. On the dashboard the autopilot panel hands over its own list (set); on other pages
   the list is asked for from the autopilot function ("bell": read-only) at most every two minutes. */
(function () {
    'use strict';
    // A browser can still hold an older copy of this script (and of the theme.js that asks for it): scripts used to be kept for
    // a day. That older copy may run first. It must not shut this one out (it did: the owner saw no trades anywhere), so this one
    // always takes over, and the older one is left with nothing to draw: it reads its trades from its own place in the browser's
    // store (emptied below), is told nothing by the function (which answers only the question marked "list: 2"), and its marks
    // and its sign on the red number have other names than the ones used here.
    const VERSION = 8;
    if (window.autopilotBell && window.autopilotBell.version >= VERSION) return;
    const hadOlder = window.autopilotBell ? 'version ' + (window.autopilotBell.version || 'before 4') : 'none';
    const API = 'https://qy6s553i647agmxthtecc24fje0zskms.lambda-url.us-east-1.on.aws/';
    // Where the site's own pages and files are: beside this script, wherever the site is served from (the top of its address on
    // stockiq.tech, below a folder in a local preview). Never "/something": that is nowhere unless the site is at the top.
    const SITE = (() => { try { const me = document.currentScript && document.currentScript.src; return me && /autopilot-bell\.js/.test(me) ? me.replace(/autopilot-bell\.js.*$/, '') : '/'; } catch (e) { return '/'; } })();
    const FRESH_MS = 2 * 60 * 1000, LOCKED_MS = 30 * 60 * 1000, KEEP = 12, SHOW = 6;
    const get = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
    const put = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* a private window: it works for this page only */ } };
    const user = () => { const u = get('userId'); return u && u !== 'anonymous' ? u : null; };
    const key = (name) => 'stockiqBell' + name + '_' + (user() || '');
    const oldKey = (name) => 'stockiqAutopilot' + name + '_' + (user() || '');      // where the copies before version 4 kept theirs
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
        mark('Bell'); mark('Read');                         // both marks start with the first list: what is there then is not news
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
    // ---- one list for the bell, the same on every page: the reports and the autopilot's buys and sells together, newest first
    function reports() {                                    // the page's own list of reports, as its own bell uses it
        let list = null;
        try { if (typeof analysisHistory !== 'undefined' && Array.isArray(analysisHistory)) list = analysisHistory; } catch (e) { /* this page keeps no such list */ }   // eslint-disable-line no-undef
        if (!list && Array.isArray(window.dashboardHistory)) list = window.dashboardHistory;
        if (!list) { try { const c = JSON.parse(get('dashboardHistoryCache_' + user()) || 'null'); list = c && c.data && c.data.history; } catch (e) { list = null; } }
        return (Array.isArray(list) ? list : []).filter(i => i && !i.deleted && i.analysisId).slice(0, 10);
    }
    const unreadReportIds = () => { try { const ids = JSON.parse(get('unreadReports_' + user()) || '[]'); return Array.isArray(ids) ? ids : []; } catch (e) { return []; } };      // whatever is stored there, a list comes back
    const has = (name) => { try { return typeof window[name] === 'function'; } catch (e) { return false; } };
    function tradeRow(e, readAt) {
        const isNew = String(e.t) > readAt, sold = e.type === 'sell', gain = sold && typeof e.gain === 'number' ? e.gain : null;
        const right = sold ? (gain === null ? (typeof e.pct === 'number' ? `<span style="font-weight: 700; color: ${e.pct >= 0 ? '#16a34a' : '#ef4444'}; white-space: nowrap;">${e.pct >= 0 ? '▲' : '▼'} ${Math.abs(e.pct).toFixed(1)}%</span>` : '') : delta(gain, e.pct))
            : `<span style="color: var(--text-secondary); white-space: nowrap;">${dollars(e.usd)}</span>`;
        const word = !sold ? 'Bought' : gain === null ? 'Sold' : gain > 0.004 ? 'Sold at a profit' : gain < -0.004 ? 'Sold at a loss' : 'Sold level';
        const edge = !isNew ? 'transparent' : !sold ? '#007bff' : gain !== null && gain < 0 ? '#ef4444' : '#16a34a';
        return `<div class="bell-row" data-kind="trade" onclick="event.stopPropagation(); autopilotBell.open()" style="padding: 12px 15px; border-bottom: 1px solid var(--border-color); cursor: pointer; background: ${isNew ? 'var(--bg-secondary)' : 'var(--card-bg)'}; border-left: 3px solid ${edge};">
            <div style="display: flex; align-items: baseline; gap: 10px; font-size: 13px;">${isNew ? '<span style="width: 8px; height: 8px; background: #007bff; border-radius: 50%; flex-shrink: 0; align-self: center;"></span>' : '<span style="width: 8px; flex-shrink: 0;"></span>'}<span style="flex: 1; min-width: 0; font-weight: ${isNew ? 'bold' : '500'}; color: var(--text-primary);">${word}: ${esc(e.symbol)}</span>${right}</div>
            <div style="font-size: 11px; color: var(--text-secondary); margin: 2px 0 0 18px;">🤖 AI autopilot (Beta) · ${e.name ? esc(e.name) + ' · ' : ''}${esc(when(e.t))}</div></div>`;
    }
    function reportRow(r, unreadIds) {
        const isNew = unreadIds.includes(r.analysisId), name = (r.companyName && r.companyName !== 'undefined') ? r.companyName : r.symbol;
        const again = has('rerunFromNotification') ? `<button data-id="${esc(r.analysisId)}" onclick="event.stopPropagation(); rerunFromNotification(this.getAttribute('data-id'))" title="Run this analysis again" aria-label="Run this analysis again" style="background: none; border: 1px solid var(--border-color); border-radius: 50%; width: 28px; height: 28px; cursor: pointer; flex-shrink: 0; color: var(--text-secondary); font-size: 13px; line-height: 1;">↻</button>` : '';
        return `<div class="bell-row" data-kind="report" data-id="${esc(r.analysisId)}" onclick="event.stopPropagation(); autopilotBell.report(this.getAttribute('data-id'))" style="padding: 12px 15px; border-bottom: 1px solid var(--border-color); cursor: pointer; background: ${isNew ? 'var(--bg-secondary)' : 'var(--card-bg)'}; border-left: 3px solid ${isNew ? '#007bff' : 'transparent'};">
            <div style="display: flex; align-items: center; gap: 10px;">${isNew ? '<span style="width: 8px; height: 8px; background: #007bff; border-radius: 50%; flex-shrink: 0;"></span>' : '<span style="width: 8px; flex-shrink: 0;"></span>'}
            <div style="flex: 1; min-width: 0;"><div style="font-size: 13px; font-weight: ${isNew ? 'bold' : '500'}; color: var(--text-primary);">${esc(name)}</div>
            <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">📊 Report · ${esc(when(r.timestamp))}</div></div>${again}</div></div>`;
    }
    function html() {
        if (!user()) return '';
        const readAt = mark('Read') || '', unreadIds = unreadReportIds(), mine = trades(), theirs = reports();
        const items = theirs.map(r => ({ at: ms(r.timestamp), row: () => reportRow(r, unreadIds) })).concat(mine.map(e => ({ at: ms(e.t), row: () => tradeRow(e, readAt) })));
        items.sort((x, y) => y.at - x.at);                  // whatever is newest is at the top, report or trade
        const newReports = theirs.filter(r => unreadIds.includes(r.analysisId)).length, newTrades = mine.filter(e => String(e.t) > readAt).length;
        const count = (n, one, many) => n + ' ' + (n === 1 ? one : many);
        const head = `<div style="padding: 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary);">
                <h4 style="margin: 0; color: var(--text-primary); font-size: 14px;">🔔 Notifications</h4>
                <p style="margin: 5px 0 0 0; color: var(--text-secondary); font-size: 12px;">${newReports + newTrades} unread${mine.length ? ': ' + count(newReports, 'report', 'reports') + ', ' + count(newTrades, 'autopilot buy or sell', 'autopilot buys and sells') + ' (practice, fake money)' : ''}</p></div>`;
        const body = items.length ? items.map(i => i.row()).join('')
            : `<div style="padding: 20px; text-align: center; color: var(--text-secondary);"><p style="margin: 0 0 6px;">Nothing here yet</p><a href="${SITE}analysis.html" style="color: #007bff; text-decoration: none;">Start your first analysis</a></div>`;
        return head + body + `<a href="${SITE}dashboard.html" onclick="event.stopPropagation();" style="position: sticky; bottom: 0; display: block; padding: 13px 15px; text-align: center; border-top: 1px solid var(--border-color); background: var(--bg-secondary); color: #007bff; text-decoration: none; font-size: 13px; font-weight: 500; z-index: 2;">View Dashboard</a>`;
    }
    const newestTrade = () => { const t = trades(); return t.length ? ms(t[t.length - 1].t) : 0; };
    const newestReport = () => reports().reduce((best, r) => Math.max(best, ms(r.timestamp)), 0);
    const onTop = () => newestTrade() >= newestReport();      // is the newest item one of the autopilot's?

    // ---- into the bell's list, wherever the page has opened one: the page's own drawing of it gives way to the one list
    // What a version-3 copy still on the page would work out as the state of the list (from its own places in the store). The
    // list carries it too, so that copy finds "its" list up to date and does not draw its own (without the trades) over this one.
    function olderSig() {
        let at;
        try { const c = JSON.parse(get(oldKey('Trades')) || 'null'); at = c && Array.isArray(c.trades) ? c.at : undefined; } catch (e) { at = undefined; }
        return [at, get(oldKey('Read')), get('unreadReports_' + user()), reports().map(r => r.analysisId + '@' + r.timestamp).join(','), has('rerunFromNotification')].join('|');
    }
    let draws = [], gaveUp = false, fault = null;
    function place() {
        const drop = document.getElementById('notification-dropdown');
        if (!drop || !user() || gaveUp) return;
        // an older copy on the page has put its own group of trades into the list, or has fetched itself a list of trades again:
        // empty its store, so that it has nothing to put back when this list is drawn
        if (get(oldKey('Trades')) !== null) { try { localStorage.removeItem(oldKey('Trades')); } catch (e) { /* a private window */ } }
        const first = drop.firstElementChild;
        const sig = [(cache() || {}).at, get(key('Read')), get('unreadReports_' + user()), reports().map(r => r.analysisId + '@' + r.timestamp).join(','), has('rerunFromNotification')].join('|'), older = olderSig();
        if (first && first.id === 'bell-list' && drop.children.length === 1 && first.getAttribute('data-mine') === sig && first.getAttribute('data-sig') === older) return;
        const now = Date.now();
        draws = draws.filter(t => now - t < 2000).concat(now);
        if (draws.length > 12) { gaveUp = true; return; }    // something keeps undoing it: leave the list as it is rather than fight over it
        let markup = '';
        try { markup = html(); } catch (e) { fault = String(e && e.message || e).slice(0, 160); return; }      // on any fault the page's own list stays as it is
        if (!markup) return;
        const box = document.createElement('div');
        box.id = 'bell-list'; box.setAttribute('data-mine', sig); box.setAttribute('data-sig', older); box.setAttribute('data-version', VERSION);
        box.style.cssText = 'text-align: left; font-weight: normal; line-height: 1.35;'; box.innerHTML = markup;
        const at = drop.scrollTop;
        drop.innerHTML = ''; drop.appendChild(box); drop.scrollTop = at;
        drop.style.maxHeight = 'min(72vh, 560px)';          // room for more than four lines (the pages give their own list 400px)
    }
    let watched = null;
    function watch(drop) {                                  // the page redraws its own list when its reports arrive: draw the one list again
        if (!drop || watched === drop || typeof MutationObserver === 'undefined') return;
        watched = drop;
        new MutationObserver(() => place()).observe(drop, { childList: true });
    }
    function open() {                                       // a click on a buy or sell: to the autopilot's own list
        markRead();
        const drop = document.getElementById('notification-dropdown');
        if (drop) drop.remove();
        if (window.practiceAutopilot && window.practiceAutopilot.bellOpen) window.practiceAutopilot.bellOpen();
        else window.location.href = SITE + 'dashboard.html#autopilot';
    }
    function report(id) {                                   // a click on a report: what the page itself does with it, or the dashboard
        if (has('viewAnalysisFromNotification')) window.viewAnalysisFromNotification(id);
        else window.location.href = SITE + 'dashboard.html';
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
            if (!mine && !b.getAttribute('data-bell')) return;         // nothing of ours: the page's own count stands
            const total = reportsUnseen() + mine, text = total > 9 ? '9+' : String(total), show = total > 0 ? 'flex' : 'none';
            if (mine) b.setAttribute('data-bell', '1'); else b.removeAttribute('data-bell');
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
        fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'bell', userId: u, list: 2 }) })
            .then(r => (r.ok ? r.json() : null)).then(d => { if (d && d.success) set(d.trades, d.allowed); })
            .catch(() => { /* the bell works without it */ }).then(() => { asking = false; });
    }

    // the marks of the copies before this one are taken over once; their list of trades is emptied so that they draw nothing
    ['Bell', 'Read'].forEach(name => { const was = get(oldKey(name)); if (user() && get(key(name)) === null && was && was > '2000') put(key(name), was); });
    try { if (user()) localStorage.removeItem(oldKey('Trades')); } catch (e) { /* a private window */ }
    window.autopilotBell = { version: VERSION, set, trades, reports, unseen, unread, markSeen, markRead, html, place, open, report, badge, load, onTop, state: () => ({ version: VERSION, site: SITE, draws: draws.length, gaveUp, fault }) };

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
        window.addEventListener('storage', (e) => { if (e.key && e.key.indexOf('stockiqBell') === 0) refresh(); });
        refresh();
        load();
        setInterval(() => { if (!document.hidden) load(); }, FRESH_MS);
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
