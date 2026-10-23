// The owner's Admin page on the dashboard (17 Oct 2026). It asks the autopilot's function for action "admin", which answers
// only the site's own accounts; for anyone else the function says no and this script shows nothing at all. When it is
// answered it shows the "🛠 Admin" tab and an "Admin" link in the Account menu, and draws: the month's goal, what needs the
// owner's yes (proposals: a setting is applied the moment "Yes" is pressed; one that needs code is done by the next
// session, which reads the answers), the weekly review the function writes by itself, and how the scheduled runs are going.
(function () {
    const API = 'https://qy6s553i647agmxthtecc24fje0zskms.lambda-url.us-east-1.on.aws/';
    const box = () => document.getElementById('admin-panel');
    const userId = () => { try { return localStorage.getItem('userId') || ''; } catch (e) { return ''; } };
    const esc = (v) => String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const usd = (v) => '$' + Math.round(Number(v) || 0).toLocaleString('en-US');
    const day = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }); };
    const ago = (iso) => { const m = Math.round((Date.now() - Date.parse(iso)) / 60000); return !isFinite(m) ? '' : m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 48 * 60 ? Math.round(m / 60) + ' h ago' : Math.round(m / 1440) + ' days ago'; };
    let data = null, busy = '', message = '';
    // Two views (17 Oct 2026, the owner: "maybe make it a tab within admin page for the improvements? or have a minimal part of it
    // there then a tab for older stuff"): Overview (the status, what needs a yes, a short summary of the improvements) and
    // Improvements (all of them: being tested, next, done, the parts of the site reviewed). Remembered in the browser.
    let view = 'overview';
    try { view = localStorage.getItem('stockiqAdminView') === 'improvements' ? 'improvements' : 'overview'; } catch (e) {}

    async function call(extra) {
        const res = await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.assign({ action: 'admin', userId: userId() }, extra || {})) });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) { const e = new Error(body.error || 'The Admin page could not be reached'); e.status = res.status; throw e; }
        return body;
    }

    function style() {
        if (document.getElementById('admin-style')) return;
        const s = document.createElement('style'); s.id = 'admin-style';
        // Colour carries the meaning here: green is fine, amber wants a look, red is a problem, blue is information. Each
        // colour is a token with a pale background of its own, so the page reads in the light and the dark theme alike.
        s.textContent = `
        #admin-panel { --ad-green: #16a34a; --ad-amber: #d97706; --ad-red: #dc2626; --ad-blue: #2563eb; --ad-purple: #7c3aed;
            --ad-green-bg: rgba(22,163,74,0.10); --ad-amber-bg: rgba(217,119,6,0.12); --ad-red-bg: rgba(220,38,38,0.10); --ad-blue-bg: rgba(37,99,235,0.08); }
        #admin-panel .ad-tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 14px 0; }
        #admin-panel .ad-tile { border-radius: 10px; padding: 12px 14px; background: var(--card-bg); border: 1px solid var(--border-color); border-top: 4px solid var(--ad-blue); }
        #admin-panel .ad-tile.good { border-top-color: var(--ad-green); background: var(--ad-green-bg); }
        #admin-panel .ad-tile.warn { border-top-color: var(--ad-amber); background: var(--ad-amber-bg); }
        #admin-panel .ad-tile.bad { border-top-color: var(--ad-red); background: var(--ad-red-bg); }
        #admin-panel .ad-tile-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); font-weight: 700; }
        #admin-panel .ad-tile-value { font-size: 1.45rem; font-weight: 800; color: var(--text-primary); margin: 4px 0 2px; font-variant-numeric: tabular-nums; }
        #admin-panel .ad-tile-sub { font-size: 0.82rem; color: var(--text-secondary); }
        #admin-panel .ad-card { border: 1px solid var(--border-color); border-left: 5px solid var(--ad-blue); border-radius: 10px; padding: 16px 18px; margin: 14px 0; background: var(--card-bg); }
        #admin-panel .ad-card.goal { border-left-color: var(--ad-purple); }
        #admin-panel .ad-card.plan { border-left-color: var(--ad-blue); }
        #admin-panel .ad-tag.pub { background: rgba(37, 99, 235, 0.12); color: var(--ad-blue); }
        #admin-panel .ad-views { display: flex; gap: 6px; margin: 10px 0 12px; flex-wrap: wrap; }
        #admin-panel .ad-view { padding: 7px 16px; border-radius: 999px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-primary); cursor: pointer; font-weight: 600; font-size: 0.9rem; }
        #admin-panel .ad-view.on { background: var(--ad-blue); border-color: var(--ad-blue); color: #fff; }
        #admin-panel .ad-section { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; color: var(--text-secondary); margin: 14px 0 4px; }
        #admin-panel ol.ad-next { margin: 4px 0 0 20px; padding: 0; } #admin-panel ol.ad-next li { margin: 6px 0; color: var(--text-primary); }
        #admin-panel .ad-card.ask { border-left-color: var(--ad-green); } #admin-panel .ad-card.ask.waiting { border-left-color: var(--ad-amber); background: var(--ad-amber-bg); }
        #admin-panel .ad-card.run { border-left-color: var(--ad-green); } #admin-panel .ad-card.run.bad { border-left-color: var(--ad-red); }
        #admin-panel .ad-label { display: block; font-weight: 800; font-size: 1.05rem; margin-bottom: 10px; color: var(--text-primary); }
        #admin-panel .ad-sub { color: var(--text-secondary); font-size: 0.85rem; font-weight: 400; }
        #admin-panel .ad-goal { padding: 10px 0; border-top: 1px solid var(--border-color); } #admin-panel .ad-goal:first-of-type { border-top: none; padding-top: 2px; }
        #admin-panel .ad-goal-head { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; flex-wrap: wrap; }
        #admin-panel .ad-goal-name { color: var(--text-secondary); font-size: 0.9rem; }
        #admin-panel .ad-goal-now { font-weight: 800; font-size: 1.1rem; color: var(--text-primary); font-variant-numeric: tabular-nums; }
        #admin-panel .ad-bar { height: 8px; border-radius: 4px; background: var(--bg-secondary); margin-top: 6px; overflow: hidden; }
        #admin-panel .ad-bar > span { display: block; height: 100%; border-radius: 4px; background: var(--ad-amber); }
        #admin-panel .ad-bar.met > span { background: var(--ad-green); }
        #admin-panel .ad-pill { display: inline-block; font-size: 0.78rem; font-weight: 700; border-radius: 999px; padding: 2px 10px; white-space: nowrap; }
        #admin-panel .ad-pill.good { background: var(--ad-green-bg); color: var(--ad-green); } #admin-panel .ad-pill.warn { background: var(--ad-amber-bg); color: var(--ad-amber); }
        #admin-panel .ad-rows { margin-top: 14px; }
        #admin-panel .ad-row { border-top: 1px solid var(--border-color); }
        #admin-panel .ad-rows .ad-row:last-child { border-bottom: 1px solid var(--border-color); }
        #admin-panel .ad-row > summary { cursor: pointer; list-style: none; padding: 11px 2px; display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
        #admin-panel .ad-row > summary::-webkit-details-marker { display: none; }
        #admin-panel .ad-row > summary::before { content: "\\25B8"; color: var(--text-secondary); }
        #admin-panel .ad-row[open] > summary::before { content: "\\25BE"; }
        #admin-panel .ad-row-body > .ad-card { margin-top: 0; }
        #admin-panel .ad-row-body > .ad-card > .ad-label:first-child { display: none; }
        #admin-panel .ad-dial { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 18px; margin: 6px 0; }
        #admin-panel .ad-dial-side { display: flex; flex-direction: column; gap: 4px; font-size: 0.85rem; color: var(--text-secondary); max-width: 260px; }
        #admin-panel .ad-pill.bad { background: var(--ad-red-bg); color: var(--ad-red); } #admin-panel .ad-pill.info { background: var(--ad-blue-bg); color: var(--ad-blue); }
        #admin-panel .ok { color: var(--ad-green); font-weight: 700; } #admin-panel .no { color: var(--ad-amber); font-weight: 700; } #admin-panel .red { color: var(--ad-red); font-weight: 700; }
        #admin-panel .ad-prop { border-top: 1px solid var(--border-color); padding: 12px 0; } #admin-panel .ad-prop:first-of-type { border-top: none; padding-top: 4px; }
        #admin-panel .ad-prop b { color: var(--text-primary); font-size: 1rem; }
        #admin-panel .ad-tag { display: inline-block; font-size: 0.75rem; border-radius: 10px; padding: 1px 8px; margin-left: 6px; background: var(--ad-blue-bg); color: var(--ad-blue); font-weight: 600; }
        #admin-panel .ad-btn { padding: 7px 14px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-primary); cursor: pointer; margin: 8px 8px 0 0; font-size: 0.9rem; }
        #admin-panel .ad-btn.rec { box-shadow: 0 0 0 3px var(--ad-blue); }
        #admin-panel .ad-rec { margin-top: 6px; padding: 6px 10px; border-left: 3px solid var(--ad-blue); background: var(--bg-secondary); border-radius: 4px; font-size: 0.9rem; }
        #admin-panel .ad-btn.yes { background: var(--ad-green); border-color: var(--ad-green); color: #fff; font-weight: 700; }
        #admin-panel .ad-btn:hover { border-color: var(--ad-blue); } #admin-panel .ad-btn[disabled] { opacity: 0.6; cursor: default; }
        #admin-panel .ad-lines { list-style: none; margin: 4px 0 0; padding: 0; }
        #admin-panel .ad-lines li { margin: 6px 0; padding: 8px 12px; border-radius: 8px; background: var(--bg-secondary); color: var(--text-primary); border-left: 4px solid var(--border-color); line-height: 1.45; }
        #admin-panel .ad-lines li.bad { border-left-color: var(--ad-red); background: var(--ad-red-bg); } #admin-panel .ad-lines li.good { border-left-color: var(--ad-green); background: var(--ad-green-bg); }
        #admin-panel .ad-lines li.goal { border-left-color: var(--ad-purple); }
        #admin-panel .ad-lines .down { color: var(--ad-red); font-weight: 700; } #admin-panel .ad-lines .up { color: var(--ad-green); font-weight: 700; }
        #admin-panel .ad-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
        #admin-panel .ad-chip { font-size: 0.8rem; border: 1px solid var(--border-color); border-radius: 999px; padding: 3px 10px; color: var(--text-primary); background: var(--bg-secondary); }
        #admin-panel .ad-chip.off { color: var(--text-secondary); } #admin-panel .ad-chip b { font-weight: 700; }
        #admin-panel details.ad-more summary { cursor: pointer; color: var(--ad-blue); font-size: 0.85rem; margin-top: 10px; }
        #admin-panel ul.ad-plain { margin: 6px 0 0 18px; padding: 0; } #admin-panel ul.ad-plain li { margin: 4px 0; color: var(--text-primary); }
        #admin-panel .ad-msg { margin: 10px 0; padding: 10px 14px; border-radius: 8px; background: var(--ad-green-bg); border-left: 4px solid var(--ad-green); color: var(--text-primary); }
        #admin-panel .ad-msg.bad { background: var(--ad-red-bg); border-left-color: var(--ad-red); }
        @media (max-width: 900px) { #admin-panel .ad-tiles { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 420px) { #admin-panel .ad-tiles { grid-template-columns: 1fr; } }`;
        document.head.appendChild(s);
    }

    const signed = (n, dp) => (n >= 0 ? '+' : '-') + Math.abs(Number(n)).toFixed(dp);
    const money = (n) => (n >= 0 ? '▲ ' : '▼ ') + usd(Math.abs(n));

    // The four tiles answer at a glance: how is the account, is the month on course, is anything waiting for me, is it running.
    // The account as the Practice portfolio tab shows it, at the latest prices, when that tab's script has them; the function's
    // own figure (an estimate from the last check-in) only until then, and said to be one.
    function liveAccount() {
        try { const f = window.practicePortfolio && window.practicePortfolio.figures && window.practicePortfolio.figures(); return f && isFinite(f.accountValue) ? f : null; } catch (e) { return null; }
    }
    // The function's estimate showed for a second before the live figure replaced it ($99,411, then $99,642): the owner took it
    // for a fault. So for the first seconds "…" is shown while the Practice tab gets its prices; the estimate, said to be one,
    // only if they do not come.
    const LIVE_WAIT_MS = 8000, shownAt = Date.now();
    let waitTimer = null;
    function withLive(g) {
        const f = liveAccount();
        if (!g) return g;
        if (f) return Object.assign({}, g, { value: f.accountValue, live: true, versus: f.versus || null });
        const waiting = Date.now() - shownAt < LIVE_WAIT_MS;
        if (waiting && !waitTimer) waitTimer = setTimeout(() => { if (data) render(); }, LIVE_WAIT_MS - (Date.now() - shownAt) + 50);
        return Object.assign({}, g, { live: false, waiting });
    }


    // How sure the record is that the account has been ahead of an S&P 500 fund SO FAR (19 Oct 2026, agreed with the owner): from the
    // daily gap between the account and the fund since it began (the Practice portfolio's own sums). Nothing under 30 trading days:
    // a few days swing it wildly. Never a forecast: owner only, and it says "so far".
    const CONFIDENCE_DAYS = 30;
    const sureOf = (t) => 1 / (1 + Math.exp(-1.702 * t));     // the chance the true daily gap is above zero, from its t (a close fit to the normal curve)
    // The chance the lead is real, from a list of daily gaps (their average over its margin of error)
    function sureFrom(gaps) {
        const n = gaps.length; if (n < 2) return null;
        const avg = gaps.reduce((a, x) => a + x, 0) / n, se = Math.sqrt(gaps.reduce((a, x) => a + (x - avg) ** 2, 0) / (n - 1) / n);
        return se > 0 ? sureOf(avg / se) : (avg > 0 ? 1 : 0);
    }
    // A dial like a fire-danger sign (19 Oct 2026, the owner: "i like seeing a visual ... i just want to see your confidence grow or
    // fall"): red under 50% (a coin flip), yellow to 90%, green from 90%; the needle at the chance the lead over the fund is real so far. Faded, with a
    // grey needle, until 30 trading days: an early reading. Under it, how the reading has moved day by day.
    function dialSvg(p, early) {
        const cx = 110, cy = 100, r = 80, pt = (q, rad) => [cx + rad * Math.cos(Math.PI * (1 - q)), cy - rad * Math.sin(Math.PI * (1 - q))];
        const arc = (q1, q2, color) => { const [x1, y1] = pt(q1, r), [x2, y2] = pt(q2, r); return `<path d="M${x1.toFixed(1)},${y1.toFixed(1)} A${r},${r} 0 0 1 ${x2.toFixed(1)},${y2.toFixed(1)}" stroke="${color}" stroke-width="18" fill="none"/>`; };
        const [nx, ny] = pt(Math.max(0, Math.min(1, p)), r - 22), op = early ? 0.35 : 1, needle = early ? 'var(--text-secondary)' : 'var(--text-primary)';
        return `<svg viewBox="0 0 220 136" width="220" height="136" role="img" aria-label="Confidence ${Math.round(p * 100)}%${early ? ', an early reading' : ''}">
            <g opacity="${op}">${arc(0, 0.5, 'var(--ad-red)')}${arc(0.5, 0.9, 'var(--ad-amber)')}${arc(0.9, 1, 'var(--ad-green)')}</g>
            <line x1="${cx}" y1="${cy}" x2="${nx.toFixed(1)}" y2="${ny.toFixed(1)}" stroke="${needle}" stroke-width="4" stroke-linecap="round"${early ? ' stroke-dasharray="6 4"' : ''}/>
            <circle cx="${cx}" cy="${cy}" r="6" fill="${needle}"/>
            <text x="30" y="116" font-size="11" fill="var(--text-secondary)" text-anchor="middle">Low</text><text x="190" y="116" font-size="11" fill="var(--text-secondary)" text-anchor="middle">High</text>
            <text x="${cx}" y="130" font-size="20" font-weight="700" text-anchor="middle" fill="${early ? 'var(--text-secondary)' : 'var(--text-primary)'}">${Math.round(p * 100)}%</text></svg>`;
    }
    function trailSvg(gaps) {
        const pts = []; for (let i = 2; i <= gaps.length; i++) { const q = sureFrom(gaps.slice(0, i)); if (q !== null) pts.push(q); }
        if (pts.length < 2) return '';
        const w = 220, h = 46, x = (i) => 4 + i * (w - 8) / (pts.length - 1), y = (q) => h - 4 - q * (h - 8);
        return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="How the confidence has moved, day by day">
            <line x1="4" x2="${w - 4}" y1="${y(0.9).toFixed(1)}" y2="${y(0.9).toFixed(1)}" stroke="var(--ad-green)" stroke-dasharray="3 3" opacity="0.6"/>
            <line x1="4" x2="${w - 4}" y1="${y(0.5).toFixed(1)}" y2="${y(0.5).toFixed(1)}" stroke="var(--ad-amber)" stroke-dasharray="3 3" opacity="0.6"/>
            <polyline points="${pts.map((q, i) => x(i).toFixed(1) + ',' + y(q).toFixed(1)).join(' ')}" fill="none" stroke="var(--ad-blue)" stroke-width="2"/></svg>`;
    }
    function confidenceHtml(v) {
        if (!v || !(v.days >= 0)) return '';
        // Two different numbers stood near each other (23 Oct 2026, the owner: "one part you say 30% chance we win, the other 57%"): this
        // one is the record so far, not a forecast, so it shows no percentage until 30 trading days; the forecast is Claude's (estimateHtml)
        const head = 'So far against an S&P 500 fund (what has happened)';
        const gaps = Array.isArray(v.gaps) ? v.gaps : null;
        const p = gaps ? sureFrom(gaps) : (v.se > 0 ? sureOf(v.avg / v.se) : null);
        const early = v.days < CONFIDENCE_DAYS;
        const level = p === null ? null : p >= 0.9 ? ['Clearly ahead', 'good'] : p >= 0.5 ? ['Leaning ahead', 'warn'] : ['More likely behind', 'bad'];   // 50% is a coin flip (the owner, 19 Oct 2026)
        const word = early ? 'Too early to tell' : level ? level[0] : '…';
        const pill = early ? `<span class="ad-pill info">${v.days} of ${CONFIDENCE_DAYS} trading days</span>` : level ? `<span class="ad-pill ${level[1]}">${Math.round(p * 100)}%</span>` : '';
        const visual = p === null ? '' : `<div class="ad-dial">${dialSvg(p, early)}<div class="ad-dial-side">${early ? `<div><strong>Early reading</strong>: needs ${CONFIDENCE_DAYS - v.days} more trading day${CONFIDENCE_DAYS - v.days === 1 ? '' : 's'} before it counts.</div>` : ''}${gaps ? trailSvg(gaps) : ''}${gaps && gaps.length > 2 ? '<div class="ad-sub">How it has moved, day by day (dashed: 50%, a coin flip, and 90%).</div>' : ''}</div></div>`;
        const f = liveAccount(), gapNow = f && f.fundValue > 0 ? f.accountValue - f.fundValue : null;
        const lines = [gapNow === null ? '' : `<li>Right now: <strong class="${gapNow >= 0 ? 'ok' : 'red'}">${gapNow >= 0 ? 'ahead of' : 'behind'} the fund by ${usd(Math.abs(gapNow))}</strong></li>`,
            `<li>Days it beat the fund: ${v.ahead} of ${v.days}</li>`,
            p === null ? '' : `<li>The dial, ${Math.round(p * 100)}%: how sure these days make it that the account is really ahead of the fund, not luck. It is not the share of days it won. Under 50% means more likely behind; it counts once there are ${CONFIDENCE_DAYS} trading days (faded until then).</li>`].join('');
        const why = early ? `<ul style="margin: 4px 0 0 18px; padding: 0;">${lines}</ul>`
            : `Ahead of the fund on ${v.ahead} of ${v.days} trading days, by ${signed(v.avg, 2)}% a day on average (give or take ${v.se.toFixed(2)}%). ${Math.round(p * 100)}% is how sure these days make it that the lead is real so far, not luck: under 50% more likely behind than ahead (red), 50 to 90% leaning ahead (yellow), 90% or more clearly ahead (green). About the past only, not a forecast.`;
        return `<div class="ad-goal"><div class="ad-goal-head"><span class="ad-goal-name">${head}</span><span><span class="ad-goal-now">${word}</span> ${pill}</span></div>${visual}<div class="ad-sub">${why}</div></div>`;
    }
    const START = 100000;      // the practice account's starting money: the account's bar runs from here to the target (19 Oct 2026; it ran from 0 and looked 99% done)
    // Real money: the decision (19 Oct 2026, the owner: "i need something to make a decision ... a combination"). One verdict from four
    // checks, judged on a day fixed in advance so that nobody acts on a lucky reading: a full year of results, the confidence dial at
    // 90% or more, a lead over the S&P 500 fund of at least 5% a year (the owner's bar), and still ahead with its three largest gains
    // taken out. Before the day: how each check stands now. Never more than a small trial; never financial advice.
    const JUDGE_ON = '2027-10-11', JUDGE_WORDS = '11 Oct 2027', LEAD_A_YEAR = 5;
    // Claude's own estimate (19 Oct 2026, the owner: "it tells me through the site"): the chance the account is ahead of an S&P 500 fund
    // after a year, written at every weekly session with the reason (admin.py estimate), and how it has moved.
    function estimateHtml() {
        const list = ((data && data.plan) || {}).estimates || [];
        if (!list.length) return '';
        const last = list[list.length - 1], prev = list.length > 1 ? list[list.length - 2] : null;
        const move = prev ? (last.pct > prev.pct ? ` <span class="ok">▲ from ${prev.pct}%</span>` : last.pct < prev.pct ? ` <span class="red">▼ from ${prev.pct}%</span>` : ` <span class="ad-sub">unchanged</span>`) : '';
        const when = (iso) => new Date(iso + 'T12:00:00Z').toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
        return `<div style="margin-top: 8px;"><b>Claude's forecast for the year ahead:</b> <span style="font-size: 1.1rem; font-weight: 800;">${last.pct}%</span> chance the account ends the year ahead of an S&P 500 fund${move} <span class="ad-sub">(${esc(when(last.at))}; updated every weekly session)</span>
            <details class="ad-sub" style="margin-top: 2px;"><summary>Why</summary>${esc(last.why)}</details>
            ${list.length > 1 ? `<div class="ad-sub" style="margin-top: 2px;">Earlier: ${list.slice(0, -1).reverse().slice(0, 6).map(e => `${esc(when(e.at))} ${e.pct}%`).join(' · ')}</div>` : ''}</div>`;
    }
    function decisionHtml() {
        const f = liveAccount();
        if (!f || !f.versus || !(f.fundValue > 0) || !f.createdAt) return '';
        const now = Date.now(), days = (now - Date.parse(f.createdAt)) / 86400000, due = now >= Date.parse(JUDGE_ON + 'T00:00:00Z');
        const p = Array.isArray(f.versus.gaps) ? sureFrom(f.versus.gaps) : null;
        const ratio = f.accountValue / f.fundValue, yearly = days >= 30 ? (Math.pow(ratio, 365 / days) - 1) * 100 : null;
        const gap = f.accountValue - f.fundValue, without = gap - (f.topGains || 0);
        const checks = [
            [days >= 365, 'A full year of results', `${Math.floor(days)} of 365 days`],
            [p !== null && p >= 0.9 && f.versus.days >= CONFIDENCE_DAYS, 'Confidence dial at 90% or more', p === null ? 'no reading yet' : `${Math.round(p * 100)}%${f.versus.days < CONFIDENCE_DAYS ? ', early reading' : ''}`],
            [yearly !== null && yearly >= LEAD_A_YEAR, `Ahead of the S&P 500 fund by ${LEAD_A_YEAR}% a year or more`, yearly === null ? `${gap >= 0 ? 'ahead' : 'behind'} by ${usd(Math.abs(gap))} so far; a yearly rate from 30 days` : `${signed(yearly, 1)}% a year so far (${gap >= 0 ? 'ahead' : 'behind'} by ${usd(Math.abs(gap))})`],
            [without > 0, 'Still ahead without its 3 biggest winning trades', `${without >= 0 ? 'ahead' : 'behind'} by ${usd(Math.abs(without))} without them`]];
        const met = checks.filter(c => c[0]).length;
        const verdict = !due ? ['Not yet', 'info', `Decided on ${JUDGE_WORDS}. Until then, how each check stands today (${met} of 4 met):`]
            : met === 4 ? ['Ready for a small real-money trial', 'good', 'All four checks pass. Start with about 10% of what you would invest, keep the rest in an S&P 500 fund, run the two side by side for 6 months, and move it back if the real account falls 10% behind the fund.']
            : ['Keep your money in an S&P 500 fund', 'bad', `${4 - met} of the 4 checks did not pass on the day.`];
        const row = (c) => `<li><span class="${c[0] ? 'ok' : 'red'}" style="font-weight: 700;">${c[0] ? '✓' : '✗'}</span> ${esc(c[1])} <span class="ad-sub">(${esc(c[2])})</span></li>`;
        return `<div class="ad-card goal"><span class="ad-label">💵 Real money: the decision</span>
            <div class="ad-goal-head" style="margin-top: 6px;"><span class="ad-goal-now">${verdict[0]}</span> <span class="ad-pill ${verdict[1]}">${due ? 'decided ' + JUDGE_WORDS : met + ' of 4 so far'}</span></div>
            <div class="ad-sub" style="margin-top: 4px;">${verdict[2]}</div>
            <ul style="list-style: none; padding: 0; margin: 8px 0 0; line-height: 1.7;">${checks.map(row).join('')}</ul>
            <div style="margin-top: 6px;"><b>The money it needs on the day:</b> at least what the same $100,000 in an S&P 500 fund is worth then, plus ${LEAD_A_YEAR}%. If the day were today: the fund ${usd(f.fundValue)} → at least <b>${usd(f.fundValue * (1 + LEAD_A_YEAR / 100))}</b>; the account is <span class="${f.accountValue >= f.fundValue * (1 + LEAD_A_YEAR / 100) ? 'ok' : 'red'}">${usd(f.accountValue)}</span>. <span class="ad-sub">In a year the S&P rises 10%, that is about $115,500.</span></div>
            ${estimateHtml()}
            ${confidenceHtml(f.versus)}
            <div class="ad-sub" style="margin-top: 6px;">Fixed in advance on 19 Oct 2026, so a lucky stretch cannot decide it. Practice money cannot show real fills, fees, currency costs or tax; a licensed adviser is worth a short session before real money. Not financial advice.</div></div>`;
    }
    function goalHtml(g) {
        g = withLive(g);
        if (!g) return '';
        const row = (name, now, goal, met, fill) => `<div class="ad-goal"><div class="ad-goal-head"><span class="ad-goal-name">${name}</span>
            <span><span class="ad-goal-now">${now}</span> <span class="ad-pill ${met ? 'good' : 'warn'}">${met ? '✓ target ' : 'target '}${goal}</span></span></div>
            ${fill === null ? '' : `<div class="ad-bar${met ? ' met' : ''}"><span style="width: ${Math.max(2, Math.min(100, fill)).toFixed(0)}%;"></span></div>`}</div>`;
        const avgOk = g.n > 0 && g.avg > g.avgGoal;
        return `<div class="ad-card goal"><span class="ad-label">🎯 ${esc(g.name)} <span class="ad-sub">due ${esc(g.due)}, ${g.daysLeft} days left</span></span>
            ${row('Finished trades in all', String(g.trades), g.tradesGoal, g.trades >= g.tradesGoal, g.trades / g.tradesGoal * 100)}
            ${row('Average a trade this month, after costs', `<span class="${avgOk ? 'ok' : 'red'}">${signed(g.avg, 2)}%</span> <span class="ad-sub">(${g.n} trades; the real average is probably between ${signed(g.avg - 2 * g.se, 2)}% and ${signed(g.avg + 2 * g.se, 2)}%)</span>`, `above ${signed(g.avgGoal, 1)}%`, avgOk, null)}
            ${row(g.live ? 'The practice account, at the latest prices' : g.waiting ? 'The practice account (getting the latest prices)' : 'The practice account, about (an estimate: the latest prices did not come in)', g.waiting ? '…' : `<span class="${g.value >= g.valueGoal ? 'ok' : 'red'}">${usd(g.value)}</span>`, usd(g.valueGoal), g.value >= g.valueGoal, g.waiting ? null : Math.max(0, (g.value - START) / (g.valueGoal - START) * 100))}
            ${g.waiting ? '' : `<div class="ad-sub" style="margin: -4px 0 6px;">${g.value >= START ? `${usd(g.value - START)} above the ${usd(START)} it started with` : `<span class="red">${usd(START - g.value)} below the ${usd(START)} it started with</span>`}${g.value < g.valueGoal ? ` · ${usd(g.valueGoal - g.value)} to go` : ' · target reached'}. The bar runs from the start to the target.</div>`}
            <div class="ad-sub" style="margin-top: 8px;">Fake money. These targets are what would count as progress, set on 12 Oct before the results were in; they are not forecasts.</div></div>`;
    }

    function propsHtml(open) {
        const rec = (p) => p.recommend === 'yes' || p.recommend === 'no' ? `<div class="ad-rec">Claude recommends: <b>${p.recommend === 'yes' ? 'Yes' : 'Not now'}</b>${p.recommendWhy ? ' · ' + esc(p.recommendWhy) : ''}</div>` : '';
        const body = open.length ? open.map(p => `<div class="ad-prop"><b>${esc(p.title)}</b><span class="ad-tag">${p.kind === 'setting' ? 'applied the moment you say yes' : 'done in your next session'}</span> <span class="ad-sub">raised ${esc(day(p.at))}</span>
            ${rec(p)}<details class="ad-sub" style="margin-top: 4px;"><summary>The details</summary>${esc(p.why)}</details>
            <button type="button" class="ad-btn yes${p.recommend === 'yes' ? ' rec' : ''}" data-ad-answer="yes" data-ad-id="${p.id}" ${busy ? 'disabled' : ''}>Yes${p.recommend === 'yes' ? ' (recommended)' : ''}</button><button type="button" class="ad-btn${p.recommend === 'no' ? ' rec' : ''}" data-ad-answer="no" data-ad-id="${p.id}" ${busy ? 'disabled' : ''}>Not now${p.recommend === 'no' ? ' (recommended)' : ''}</button></div>`).join('')
            : '<div class="ok">✓ No decisions waiting.</div><div class="ad-sub" style="margin-top: 4px;">A change to the site or its settings that the weekly review or a session thinks worth making is put here for your yes or no. Anything wrong with the autopilot itself (no cash, a failed check-in) shows on the AI autopilot tab, as it does for every user.</div>';
        return `<div class="ad-card ask${open.length ? ' waiting' : ''}"><span class="ad-label">${open.length ? '⚠️' : '✅'} Decisions for you ${open.length ? `<span class="ad-pill warn">${open.length}</span>` : ''}</span>${body}</div>`;
    }

    // A review line is marked by what it says: "clearly down" / "Clearly losing" red, "clearly up" / "Clearly making" green;
    // dollar amounts and percentages with a sign are coloured as they point.
    function lineHtml(text) {
        const kind = /clearly down|clearly losing/i.test(text) ? 'bad' : /clearly up|clearly making|clearly ahead/i.test(text) ? 'good' : /^Month \d/i.test(text) ? 'goal' : '';
        const body = esc(text).replace(/([+-]\$[\d,]+(?:\.\d+)?|[+-]\d+(?:\.\d+)?%)/g, (m) => !/[1-9]/.test(m) ? m : `<span class="${m[0] === '-' ? 'down' : 'up'}">${m}</span>`);   // a zero is a target, not a result
        return `<li class="${kind}">${body}</li>`;
    }

    function reviewHtml(r, next) {
        return `<div class="ad-card"><span class="ad-label">📋 Weekly review <span class="ad-sub">${r ? 'written by the autopilot ' + esc(day(r.at)) + (next ? '; the next one ' + esc(day(next)) : '') : 'not written yet: the scheduled run writes one every 7 days'}</span></span>
            ${r ? '<ul class="ad-lines">' + r.lines.map(lineHtml).join('') + '</ul>' : ''}
            <button type="button" class="ad-btn" data-ad="review" ${busy ? 'disabled' : ''}>${busy === 'review' ? 'Writing…' : 'Write a fresh one now'}</button>
            <div class="ad-sub" style="margin-top: 6px;">You never need to press this: the autopilot writes the review by itself every 7 days. Pressing it writes it again straight away from the latest figures. It buys, sells and changes nothing; it may add a question under "Decisions for you"; and the next automatic review then comes 7 days after your press.</div>
            <div class="ad-sub" style="margin-top: 8px;">A group of trades is only called losing or making money from 30 trades, and only when it is beyond twice its margin of error. Past practice results; nothing here is advice.</div></div>`;
    }

    function healthHtml(h, s, screeners) {
        const runs = h ? `Last scheduled run ${esc(ago(h.at))} (${esc(day(h.at))}): ` + (h.ran ? `${h.ran} of ${h.on} switched-on account${h.on === 1 ? '' : 's'} checked in` : 'nothing was due (its markets were closed, or its next check-in had not come)') + `${h.waiting ? ', ' + h.waiting + ' left for the next run' : ''}${h.paused ? ', ' + h.paused + ' paused' : ''}. ` + (h.failed ? `<span class="red">${h.failed} check-in${h.failed === 1 ? '' : 's'} stopped on an error.</span>` : '<span class="ok">✓ No errors.</span>') : 'No scheduled run recorded yet (it runs at :10 and :40 past every hour).';
        const chip = (text, on) => `<span class="ad-chip${on === false ? ' off' : ''}">${text}</span>`;
        const chips = s ? [chip(`Autopilot <b>${s.enabled ? 'on' : 'off'}</b>`, s.enabled), chip(`<b>${esc(({ 1: 'Cautious', 2: 'Careful', 3: 'Balanced', 4: 'Bold', 5: 'Adventurous' })[s.risk] || 'Level ' + s.risk)}</b> level`), chip(`<b>${esc(s.holdings || "the level's")}</b> holdings`), chip(`Budget <b>${usd(s.budgetUsd)}</b>`),
            chip(`Checks in every <b>${esc(s.everyHours)} h</b>`), chip(`Keeps a holding up to <b>${esc(s.maxHoldDays)} days</b>`), chip(`Tries changes to its rules <b>${s.selfTune ? 'on' : 'off'}</b>`, s.selfTune), ...('pickMode' in s ? [chip(`Markets chosen by <b>${s.pickMode === 'manual' ? 'you' : 'the AI'}</b>`)] : [])].join('') : '';
        // the last run is in "What runs by itself" (23 Oct 2026: it stood here as well); here only when something failed
        return `<div class="ad-card run${h && h.failed ? ' bad' : ''}"><span class="ad-label">⚙️ Settings in force, and the AWS bill</span>${h && h.failed ? `<div>${runs}</div>` : ''}
            ${chips ? `<div class="ad-chips">${chips}</div>` : ''}
            ${s ? `<details class="ad-more"><summary>Show the ${screeners.length} screeners it buys from</summary><div class="ad-sub" style="margin-top: 6px;">${screeners.length ? esc(screeners.join(', ')) : 'none'}.</div></details>` : ''}
            ${usageHtml(data.usage)}</div>`;
    }

    // AWS this month (17 Oct 2026): the bill so far and Lambda's calls against the free million, read once a day by the function
    function usageMessage(u) {
        if (!u) return 'Not done: the figures could not be read.';
        return u.costError ? 'Read just now: the calls. The bill could not be read just now; the figure shown is the last one read.' : 'Read just now, free: the calls and the bill (as AWS last updated it).';
    }
    function usageHtml(u) {
        if (!u) return '<div class="ad-sub" style="margin-top: 10px;">AWS this month: not read yet (the scheduled run reads it once a day).</div>';
        const chips = [];
        const money = v => '$' + Number(v).toFixed(2), tone = v => v < 1 ? 'good' : v < 1.5 ? 'warn' : 'bad';
        let billNote = '';
        if (u.costStockiq !== undefined) {
            // 19 Oct 2026, the owner: "i'd like to see my full aws bill, as well as that specific stockiq bill ... make it clear what i'm
            // looking at". So: the whole bill first, then StockIQ's part of it (its one-off Cost Explorer charge counted in), then the
            // running cost, which is what the cost rule (under $1 a month) is about, with every service listed.
            const svcName = { AmazonDynamoDB: 'DynamoDB (the database)', AmazonS3: 'S3 (file storage)', AWSLambda: 'Lambda (the functions)', AmazonCloudWatch: 'CloudWatch (logs)',
                AmazonCloudFront: 'CloudFront (serving the site)', AWSDataTransfer: 'data transfer out', AmazonSES: 'SES (email)', AmazonSNS: 'SNS', AmazonCognito: 'Cognito (sign-in)',
                awskms: 'KMS (keys)', AWSEvents: 'EventBridge (schedules)', AWSGlue: 'Glue', AWSMarketplace: 'Marketplace' };
            const stockiqAll = (u.costStockiq || 0) + (u.costExplorer || 0);
            if (u.cost !== undefined) chips.push(`<span class="ad-pill ${tone(u.cost)}">Your whole AWS bill this month so far: ${money(u.cost)} <span style="font-weight:400;">(your AWS budget warns at $1 and $1.50)</span></span>`);
            chips.push(`<span class="ad-pill info">StockIQ's part of it: ${money(stockiqAll)}</span>`);
            chips.push(`<span class="ad-pill ${tone(u.costStockiq)}">StockIQ's running cost: ${money(u.costStockiq)}${u.costStockiqForecast ? `, on course for about ${money(u.costStockiqForecast)} for the month` : ''} <span style="font-weight:400;">(the cost rule: under $1 a month)</span></span>`);
            const extra = (u.costExplorer || 0) - (u.costExplorerKnown || 0);
            if (extra > 0.02) chips.push(`<span class="ad-pill bad">Cost Explorer is being asked again: ${money(extra)} more this month. A session will find what asks it.</span>`);
            const svc = Object.entries(u.costServices || {}).filter(([k]) => k !== 'AWSCostExplorer').sort((a, b) => b[1] - a[1]);
            const paid = svc.filter(([, v]) => v >= 0.01).map(([k, v]) => `${svcName[k] || k} ${money(v)}`);
            const free = svc.filter(([, v]) => v < 0.01).map(([k]) => (svcName[k] || k).replace(/ \(.*\)$/, ''));
            const lines = [];
            if (u.cost !== undefined) lines.push(`<b>Whole bill ${money(u.cost)}</b> = StockIQ ${money(stockiqAll)} + your other projects ${money(u.costOther || 0)}${u.costOther >= 0.01 ? ' (their storage, on another AWS account)' : ''}.`);
            if (u.costExplorer >= 0.01) lines.push(`<b>StockIQ ${money(stockiqAll)}</b> = ${money(u.costExplorer)} for Cost Explorer${u.costExplorerKnown ? ' (a one-off: about 265 questions at $0.01 each on 17 Oct, nearly all from a session\'s test runs; stopped that evening, nothing asks it now)' : ''} + ${money(u.costStockiq)} to run the site.`);
            lines.push(`<b>Running the site ${money(u.costStockiq)}</b>: ${paid.length ? paid.join(', ') : 'nothing yet'}${free.length ? `; still inside the free allowances: ${free.join(', ')}` : ''}.`);
            billNote = `<div class="ad-sub" style="margin-top: 6px; line-height: 1.5;">${lines.join('<br>')}</div>`;
        } else {
            if (u.costForecast) chips.push(`<span class="ad-pill ${tone(u.costForecast)}">AWS forecasts about ${money(u.costForecast)} for the month</span>`);
            if (u.cost !== undefined) chips.unshift(`<span class="ad-pill ${tone(u.cost)}">AWS bill this month so far: ${money(u.cost)} <span style="font-weight:400;">(warning at $1, limit $1.50)</span></span>`);
        }
        if (u.calls !== undefined) {
            const share = u.calls / (u.free || 1000000), f = u.forecast ? u.forecast / (u.free || 1000000) : share;
            chips.push(`<span class="ad-pill ${f < 0.7 ? 'good' : f < 1 ? 'warn' : 'bad'}">Lambda calls: ${Number(u.calls).toLocaleString('en-US')} of ${(u.free || 1000000).toLocaleString('en-US')} free (${Math.round(share * 100)}%)</span>`);
            if (u.forecast) chips.push(`<span class="ad-pill info">on course for about ${Math.round(u.forecast / 1000).toLocaleString('en-US')}k this month</span>`);
            if (u.yesterday) chips.push(`<span class="ad-pill info">yesterday ${Number(u.yesterday).toLocaleString('en-US')}</span>`);
        }
        const err = u.costError || u.callsError ? ` <span class="ad-sub">(${u.costError ? 'the bill could not be read' : ''}${u.costError && u.callsError ? '; ' : ''}${u.callsError ? 'the calls could not be read' : ''})</span>` : '';
        // each figure with its own age (17 Oct 2026: one "read 6 h ago" was the calls' age, while the bill could be 3 days old)
        const ages = [u.calls !== undefined ? `calls read ${esc(ago(u.at))}` : '', u.cost !== undefined && u.costAt ? `bill as AWS last updated it, ${esc(ago(u.costAt))}` : ''].filter(Boolean).join(' · ');
        return `<div style="margin-top: 12px;"><span class="ad-sub">AWS this month (${ages}):</span><div class="ad-chips">${chips.join('')}</div>${billNote}${err}
            <button type="button" class="ad-btn" data-ad="usage" ${busy ? 'disabled' : ''}>${busy === 'usage' ? 'Reading…' : '↻ Refresh now'}</button>
            <div class="ad-sub" style="margin-top: 4px;">By itself it reads both about once a day; Refresh now reads them at once. Both are free to read: the bill comes from your AWS budget, which AWS updates a few times a day, and the calls from CloudWatch.</div></div>`;
    }

    // The improvements (17 Oct 2026; the owner: "put the list of future improvements to track them so i know which was run which is
    // next ... easily see if something was improved in the past"): check-tools/experiments.json and site_parts.json, copied here by
    // admin.py sync. Being tested (with how far to its decision), next in order, and done (kept or taken out, with the result).
    function planHtml(pl) {
        if (!pl || !pl.items) return '';
        const items = pl.items, by = (st) => items.filter(e => e.status === st);
        // newest first everywhere, each line dated (23 Oct 2026, the owner: "most recent improvements at the top and dated ... unsure when
        // the improvement was created or started"): being tested by the day it started, ideas by the day they were added
        const begun = (e) => e.started || e.added || '';
        const running = by('running').sort((a, b) => begun(b).localeCompare(begun(a)));
        const next = by('idea').sort((a, b) => (b.added || '').localeCompare(a.added || '') || (a.order || 99) - (b.order || 99));
        const dated = (iso) => { const t = Date.parse(iso || ''); return t ? new Date(t + 43200000).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : ''; };
        const done = items.filter(e => e.status === 'kept' || e.status === 'removed').sort((a, b) => (b.decided || '').localeCompare(a.decided || ''));
        const tags0 = (a) => (a || '').split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="ad-tag">${esc(t)}</span>`).join('');
        // the item itself is passed where it is known, so that one shown to every user carries 👥
        const tags = (a, e) => tags0(a) + (e && e.public ? '<span class="ad-tag pub" title="Also shown, in plain words, to every user on the AI autopilot tab">👥 users see it</span>' : '');
        const dayms = 86400000, todayMs = Date.now();
        const runRow = (e) => {
            const a = Date.parse(e.started), b = Date.parse(e.decide), pct = a && b && b > a ? Math.max(3, Math.min(100, (todayMs - a) / (b - a) * 100)) : 0;
            const left = b ? Math.ceil((b - todayMs) / dayms) : null;
            return `<div class="ad-goal"><div class="ad-goal-head"><span><b>${esc(e.what)}</b>${tags(e.angle, e)}</span><span class="ad-pill ${left !== null && left <= 0 ? 'warn' : 'info'}">${left === null ? '' : left <= 0 ? 'decide now' : 'decided in ' + left + ' day' + (left === 1 ? '' : 's')}</span></div>
                <div class="ad-sub" style="margin-top: 2px;">Started ${esc(dated(begun(e)))}${b ? ` · decided by ${esc(dated(e.decide))}` : ''}</div>
                <div class="ad-bar"><span style="width: ${pct.toFixed(0)}%; background: var(--ad-blue);"></span></div><div class="ad-sub" style="margin-top: 4px;">Measured by: ${esc(e.measure)}</div></div>`;
        };
        const doneRow = (e) => `<li class="${e.status === 'kept' ? 'good' : ''}"><b>${e.status === 'kept' ? '✓ Kept' : 'Taken out'}</b> · ${esc(e.what)} <span class="ad-sub">${begun(e) && begun(e) !== e.decided ? `started ${esc(dated(begun(e)))}, ` : ''}decided ${esc(dated(e.decided) || e.decided || '')}</span><div class="ad-sub" style="margin-top: 2px;">${esc(e.result || '')}</div></li>`;
        const reviewed = (pl.reviews || []).map(r => `<li><b>${esc(r.part)}</b> <span class="ad-sub">${esc(r.at)}</span><div class="ad-sub">${esc(r.found)}</div></li>`).join('');
        return `<div class="ad-card plan"><span class="ad-label">🧭 Improvements <span class="ad-sub">${running.length} being tested · ${next.length} next · ${by('kept').length} kept · ${by('removed').length} taken out · ${pl.reviewed || 0} of ${pl.parts || 0} parts of the site reviewed</span></span>
            <div class="ad-sub" style="margin-bottom: 8px;">Every change whose worth is not certain is tested over a period, then kept or taken out on the figures. Each session also reviews three parts of the site and adds new ideas. This list was last brought up to date ${esc(day(pl.at))}.</div>
            <div class="ad-sub" style="margin-bottom: 8px;">This is the full list, for you only. Every user sees a short, plain version on the AI autopilot tab ("How it is improving"): only what affects their autopilot, marked here 👥.</div>
            <div class="ad-sub" style="margin-bottom: 8px;">Jump to: ${[['ad-sec-running', 'Being tested', running.length], ['ad-sec-next', 'Ideas', next.length], ['ad-sec-done', 'Done', done.length], ['ad-sec-fixes', 'Fixes and changes', (pl.changes || []).length], ['ad-sec-questions', 'Questions asked', (pl.questions || []).length], ['ad-sec-parts', 'Parts of the site', (pl.siteParts || []).length]].filter(x => x[2]).map(([id, name, k]) => `<a href="#${id}" data-ad-jump="${id}">${name} (${k})</a>`).join(' · ')}</div>
            ${running.length ? `<div class="ad-section" id="ad-sec-running">Being tested now, newest first</div>${running.map(runRow).join('')}` : ''}
            ${next.length ? `<div class="ad-section" id="ad-sec-next">Ideas not started yet, newest first</div><ol class="ad-next">${next.map(e => `<li><b>${esc(e.what)}</b>${tags(e.angle, e)}${e.added ? ` <span class="ad-sub">added ${esc(dated(e.added))}</span>` : ''}${e.measure ? `<div class="ad-sub" style="margin-top: 2px;">${esc(e.measure)}</div>` : ''}</li>`).join('')}</ol>` : ''}
            ${done.length ? `<div class="ad-section" id="ad-sec-done">Done, newest first</div><ul class="ad-lines">${done.map(doneRow).join('')}</ul>` : ''}
            ${fixesHtml(pl.changes)}
            ${questionsHtml(pl.questions)}
            ${partsHtml(pl.siteParts) || (reviewed ? `<details class="ad-more"><summary>Parts of the site reviewed lately (${(pl.reviews || []).length})</summary><ul class="ad-plain">${reviewed}</ul></details>` : '')}</div>`;
    }

    // Every part of the site (check-tools/site_parts.json), each looked at in turn, the one looked at longest ago first: three each
    // session (23 Oct 2026, the owner: "have a massive list of every part of the site ... tick if its been selected and on what date it
    // was checked, then expand it to see what was improved"). Oldest first rather than at random, so that every part comes round.
    function partsHtml(parts) {
        if (!parts || !parts.length) return '';
        const days = (iso) => iso ? (Date.now() - Date.parse(iso + 'T12:00:00Z')) / 86400000 : Infinity;
        const fresh = parts.filter(p => days(p.last) <= 30).length, never = parts.filter(p => !p.last).length;
        const order = parts.slice().sort((a, b) => (a.last || '').localeCompare(b.last || ''));
        const when = (iso) => { const t = Date.parse((iso || '') + 'T12:00:00Z'); return t ? new Date(t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : ''; };
        const row = (p) => (p.log && p.log.length
            ? `<details class="ad-more"><summary>✓ <b>${esc(p.part)}</b> <span class="ad-sub">looked at ${esc(when(p.last))}${p.log.length > 1 ? ', ' + p.log.length + ' times' : ''}</span></summary><ul class="ad-plain">${p.log.slice().reverse().map(l => `<li><span class="ad-sub">${esc(when(l.at))}</span> ${esc(l.found)}</li>`).join('')}</ul></details>`
            : `<div class="ad-sub" style="padding: 3px 0;">○ <b>${esc(p.part)}</b> · not looked at yet</div>`);
        return `<div class="ad-section" id="ad-sec-parts">Every part of the site, looked at in turn (${parts.length})</div>
            <div class="ad-sub" style="margin-bottom: 6px;">${fresh} looked at in the last 30 days, ${never} not yet. Each session takes the three looked at longest ago and checks them for faults, clarity, accuracy against what is live, profit and new ideas. Next: ${order.slice(0, 3).map(p => esc(p.part.split(':')[0])).join(', ')}.</div>
            ${order.slice().reverse().map(row).join('')}`;
    }

    // Every fix and change, newest first, with who found the problem behind it (23 Oct 2026, the owner: "note how you found many problems
    // simply by me saying simple things i see on the page"). The count of those he found is the one to bring down: the checks and the
    // sessions should find them first.
    function fixesHtml(list) {
        if (!list || !list.length) return '';
        const days = (iso) => (Date.now() - Date.parse(iso + 'T12:00:00Z')) / 86400000, recent = list.filter(c => days(c.at) <= 30);
        const by = (w) => recent.filter(c => c.found === w).length;
        const tag = (c) => c.found === 'owner' ? '<span class="ad-tag" style="border-color: var(--ad-amber, #d97706);">you pointed it out</span>' : c.found === 'check' ? '<span class="ad-tag pub">found by a check</span>' : c.found === 'session' ? '<span class="ad-tag">found by a session</span>' : '';
        const when = (iso) => { const t = Date.parse(iso + 'T12:00:00Z'); return t ? new Date(t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : ''; };
        const li = (c) => `<li>${esc(c.what)} ${tag(c)} <span class="ad-sub">${esc(when(c.at))}</span></li>`;
        return `<div class="ad-section" id="ad-sec-fixes">Fixes and changes, newest first (${list.length})</div>
            <div class="ad-sub" style="margin-bottom: 6px;">Last 30 days: ${recent.length} changes. The problem behind ${by('owner')} of them was pointed out by you, ${by('check')} found by a check, ${by('session')} by a session${recent.length - by('owner') - by('check') - by('session') ? ` (${recent.length - by('owner') - by('check') - by('session')} not marked: from before 23 Oct 2026)` : ''}. The aim is that the checks and sessions find problems before you do; each one you point out also becomes a check.</div>
            <ul class="ad-plain">${list.slice(0, 8).map(li).join('')}</ul>${list.length > 8 ? `<details class="ad-more"><summary>${list.length - 8} earlier</summary><ul class="ad-plain">${list.slice(8).map(li).join('')}</ul></details>` : ''}`;
    }

    // Every question asked about making it better (check-tools/reviews/questions.md, copied by admin.py sync), so that what was already
    // tried is seen and not tried again (23 Oct 2026, the owner: "i'm guessing history is kept so its not repeated"). Answered first.
    function questionsHtml(qs) {
        if (!qs || !qs.length) return '';
        const groups = [['answered', 'Answered'], ['trial', 'Being tried live'], ['waiting', 'Waiting for enough trades or data'], ['open', 'Not tested yet']];
        const count = (st) => qs.filter(q => q.status === st).length;
        const row = (q) => `<li><b>${q.n}. ${esc(q.q)}</b> <span class="ad-sub">${esc(q.asked)}</span><div class="ad-sub" style="margin-top: 2px;">${esc(q.answer)}</div></li>`;
        return `<div class="ad-section" id="ad-sec-questions">Questions asked (${qs.length})</div>
            <div class="ad-sub" style="margin-bottom: 6px;">${groups.map(([st, name]) => `${count(st)} ${name.toLowerCase()}`).join(' · ')}. Each is tested on past prices or on the live record before anything changes; "tried, no difference" is kept as an answer so that it is not tried again.</div>
            ${groups.filter(([st]) => count(st)).map(([st, name]) => `<details class="ad-more"${st === 'answered' ? ' open' : ''}><summary>${name} (${count(st)})</summary><ul class="ad-plain">${qs.filter(q => q.status === st).sort((a, b) => b.n - a.n).map(row).join('')}</ul></details>`).join('')}`;
    }

    // The short version for the Overview: how many, what is being tested (soonest decision first) and the latest three done

    // The site checked every night (check-tools/site_audit.py, run by the daily deploy; 18 Oct 2026, the owner: "why can't you
    // actively do this every 24+ hours"). Problems first; each new since the last run is marked. A session works through them.
    // The full check of the site, every 7 days or more (weekly_check.py; 19 Oct 2026, the owner: "consistency and confidence everything
    // is good"): every test suite on the live code, the figures agreeing across pages, real buttons. One line; the failures if any.
    // "Do you need to check in?" (19 Oct 2026, the owner: "something like do i need to check in with you AI or are we good ... then i
    // can go there on my phone see if you need me"). One answer from what the page already knows: the last session (its latest line in
    // "What changed lately"), the full check, decisions waiting, the scheduled runs, the site check, the bill.
    // What comes next, soonest first (19 Oct 2026, the owner: "where do i see where things are at eg whats happening next when i need to
    // check in with you"): his next check-in, the next full check and weekly review, the next trials decided, the month's goal, the
    // real-money decision.
    function comingUp(d, needNow, last) {
        const plan = d.plan || {}, now = Date.now(), DAY = 86400000, at = (iso) => Date.parse(iso.length === 10 ? iso + 'T12:00:00Z' : iso);
        const fmt = (t) => new Date(t).toLocaleDateString(undefined, Object.assign({ weekday: 'short', day: 'numeric', month: 'short' }, new Date(t).getFullYear() !== new Date().getFullYear() ? { year: 'numeric' } : {}));
        const items = [];
        if (needNow === 'urgent') items.push([now, '<b>Your next check-in: now</b> (see above)']);
        else if (last) items.push([Math.max(now, at(last.at) + 7 * DAY), needNow ? '<b>Your next check-in</b>: when you can, by this day at the latest (see above)' : '<b>Your next check-in</b>: say hi by then (7 days after the last session)']);
        else items.push([now, '<b>Your next check-in</b>: when you can']);
        if (plan.weekly) items.push([at(plan.weekly.at) + 7 * DAY, 'The next full check of the site, by itself (with the daily update), emailed to you']);
        if (d.nextReview) items.push([at(d.nextReview), "The autopilot's next weekly review, by itself"]);
        (plan.items || []).filter(x => x.status === 'running' && x.decide).sort((a, b) => a.decide.localeCompare(b.decide)).slice(0, 2)
            .forEach(x => items.push([at(x.decide), 'Decision due: ' + esc(String(x.what).split(/[:(]/)[0].trim().slice(0, 80))]));
        if (d.goal && d.goal.due) items.push([at(d.goal.due), esc(d.goal.name) + ' is due']);
        const label = (t) => t <= now ? 'Today' : fmt(t), byDay = [];
        items.filter(([t]) => t >= now - DAY).sort((a, b) => a[0] - b[0]).forEach(([t, text]) => {      // two things on one day share its line (23 Oct 2026)
            const last = byDay[byDay.length - 1];
            if (last && label(last[0]) === label(t)) last[1] += ' · ' + text; else byDay.push([t, text]);
        });
        const rows = byDay.slice(0, 6), li = ([t, text]) => `<li><span class="ad-sub" style="display: inline-block; min-width: 92px;">${esc(label(t))}</span> ${text}</li>`;
        return `<div style="margin-top: 10px; font-weight: 600; font-size: 0.9rem;">Coming up</div><ul style="list-style: none; margin: 2px 0 0; padding: 0; line-height: 1.55; font-size: 0.88rem;">`
            + rows.map(li).join('') + '</ul>'
            + `<div class="ad-sub" style="margin-top: 8px; padding-top: 6px; border-top: 1px dashed var(--border-color); font-size: 0.85rem;">Further off: <b>${esc(fmt(at(JUDGE_ON)))}</b>, real money: the decision</div>`;
    }
    function needMeHtml(d) {
        const plan = d.plan || {}, now = Date.now(), daysSince = (iso) => iso ? Math.floor((now - Date.parse(iso)) / 86400000) : null;
        const urgent = [], soon = [], good = [];
        const h = d.health, late = h && now - Date.parse(h.at) > 2 * 3600000;
        if (h && h.failed) urgent.push(`the autopilot's last scheduled run had ${h.failed} failed check-in${h.failed === 1 ? '' : 's'}`);
        else if (late) urgent.push(`the autopilot has not run for ${Math.round((now - Date.parse(h.at)) / 3600000)} hours`);
        else if (h) good.push('the autopilot is running normally');
        const w = plan.weekly, wAge = w ? daysSince(w.at) : null;
        if (w && w.passed < w.total) urgent.push(`the full check found ${w.total - w.passed} problem${w.total - w.passed === 1 ? '' : 's'}`);
        else if (w && wAge > 8) soon.push(`the full check is ${wAge} days old (it runs by itself when the daily update runs: is the laptop on?)`);
        else if (w) good.push(`the full check passed all ${w.total} (${wAge === 0 ? 'today' : wAge + ' day' + (wAge === 1 ? '' : 's') + ' ago'})`);
        else soon.push('the full check has not run yet');
        const u = d.usage || {};
        if (u.costStockiq >= 1.5 || ((u.costExplorer || 0) - (u.costExplorerKnown || 0)) > 0.02) urgent.push('the AWS bill needs a look');
        else if (typeof u.costStockiq === 'number') good.push(`the bill is in order (StockIQ's running cost $${Number(u.costStockiq).toFixed(2)} this month)`);
        const open = (d.open || []).length;
        if (open) soon.push(`${open} decision${open === 1 ? '' : 's'} waiting for your yes or no below`);
        const a = plan.audit;
        if (a && a.problems) soon.push(`the site check has ${a.problems} problem${a.problems === 1 ? '' : 's'}`);
        const last = (plan.changes || [])[0], since = last ? daysSince(last.at) : null;
        if (since === null || since >= 7) soon.push(since === null ? 'no session has made a change yet' : `the last session was ${since} days ago: the weekly review and new improvements are due`);
        else good.push(`the last session was ${since === 0 ? 'today' : since + ' day' + (since === 1 ? '' : 's') + ' ago'}`);
        const [word, tone, say] = urgent.length ? ['Yes, please check in', 'bad', 'Open a session and say hi: '] : soon.length ? ['When you can', 'warn', 'Nothing is broken, but a session would help: '] : ['No, all good', 'good', 'Nothing needs you: '];
        const why = (urgent.length ? urgent : soon.length ? soon : good);
        return `<div class="ad-card run${tone === 'bad' ? ' bad' : ''}" style="padding-top: 12px; padding-bottom: 12px;"><span class="ad-label">🤖 Do you need to check in?</span>
            <div style="margin-top: 4px;"><span class="${tone === 'good' ? 'ok' : tone === 'bad' ? 'red' : ''}" style="font-weight: 800; font-size: 1.15rem;${tone === 'warn' ? ' color: var(--ad-amber);' : ''}">${word}</span></div>
            <div class="ad-sub" style="margin-top: 4px;">${say}${esc(why.join('; '))}.${(urgent.length || soon.length) && good.length ? ' Otherwise ' + esc(good.join(', ')) + '.' : ''}</div>
            ${comingUp(d, urgent.length ? 'urgent' : soon.length ? 'soon' : '', last)}</div>`;
    }
    // The Overview, since 19 Oct 2026 (the owner: "are things overlapping and just gone crazy ... i just want the site fucking good and to
    // see progress"): his two questions first (do you need me; how is it doing: the real-money card with the dial, the month's goal),
    // decisions only when there are some, what changed; the rest one row each that opens in place. The four tiles (they repeated the
    // goal and the check-in answer) and the improvements summary (it repeated the Improvements tab) went.
    const adOpen = new Set();
    function adRow(key, summary, inner, open) {
        if (!inner) return '';
        return `<details class="ad-row" data-ad-row="${key}" ${adOpen.has(key) || open ? 'open' : ''}><summary><span>${summary}</span></summary><div class="ad-row-body">${inner}</div></details>`;
    }
    function rowsHtml(d) {
        const plan = d.plan || {}, w = plan.weekly, a = plan.audit, day2 = (iso) => { const x = new Date(iso); return isNaN(x) ? '' : x.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }); };
        const wOk = w && w.passed === w.total, probs = a ? (a.findings || []).filter(f => f.level === 'problem').length : 0;
        return adRow('weekly', w ? `🧪 <b>Full check</b> (every test, run on the live site): <span class="${wOk ? 'ok' : 'red'}">${wOk ? 'all ' + w.total + ' passed' : (w.total - w.passed) + ' of ' + w.total + ' failed'}</span> <span class="ad-sub">${esc(day2(w.at))}, every 7 days</span>` : '🧪 <b>Full check</b> (every test, run on the live site): not run yet', weeklyHtml(w), w && !wOk)
            + adRow('audit', a ? `🔎 <b>Page scan</b> (links, descriptions, stale or broken pages): <span class="${probs ? 'red' : 'ok'}">${probs ? probs + ' problem' + (probs === 1 ? '' : 's') : 'no problems'}</span> <span class="ad-sub">${esc(day2(a.at))}, with the daily update</span>` : '', auditHtml(a))
            + adRow('answered', `✅ <b>Decisions you answered</b> <span class="ad-sub">${(d.answered || []).length}</span>`, answeredHtml(d.answered || []))
            + adRow('review', `📋 <b>The autopilot's weekly review</b> (its trades and results) <span class="ad-sub">${d.review ? esc(day2(d.review.at)) : 'not written yet'}</span>`, reviewHtml(d.review, d.nextReview))
            + adRow('selfrun', '🔁 <b>What runs by itself</b>, and when each last ran', selfRunHtml(d))
            + adRow('health', `⚙️ <b>The autopilot's settings and how its runs went, and the AWS bill in full</b>`, healthHtml(d.health, d.settings, d.screeners || []));
    }
    if (document.addEventListener) document.addEventListener('toggle', (e) => { const k = e.target && e.target.getAttribute && e.target.getAttribute('data-ad-row'); if (k) { if (e.target.open) adOpen.add(k); else adOpen.delete(k); } }, true);
    // What runs without anyone (19 Oct 2026, the owner: "so i know whats going on where its at"): each job, how often, and when it
    // last ran, with a green or red dot by whether that is as recent as it should be.
    function selfRunHtml(d) {
        const plan = d.plan || {}, now = Date.now(), h = d.health, w = plan.weekly, a = plan.audit, r = d.review;
        const ago = (iso) => { if (!iso) return 'not yet'; const m = (now - Date.parse(iso)) / 60000; return m < 90 ? Math.max(1, Math.round(m)) + ' min ago' : m < 48 * 60 ? Math.round(m / 60) + ' h ago' : Math.round(m / 1440) + ' days ago'; };
        const fresh = (iso, hours) => iso && now - Date.parse(iso) <= hours * 3600000;
        const trials = ((plan.items || []).filter(x => x.status === 'running')).length;
        const jobs = [
            [fresh(h && h.at, 2), 'The autopilot: trades, with the half-hourly stop watch; its budget follows its results', 'every 30 minutes', h && h.at],
            [fresh(a && a.at, 4 * 24), 'The site check: links, search basics, stale pages, made-up figures', 'with every daily update (Mon to Sat, while your Mac is on)', a && a.at],
            [fresh(plan.dailyReview ? plan.dailyReview + 'T23:59:00Z' : null, 4 * 24), 'The daily review by Claude: reads the site, puts proposals here', 'once a day, after the daily update', plan.dailyReview ? plan.dailyReview + 'T12:00:00Z' : null],
            [fresh(w && w.at, 9 * 24) && w && w.passed === w.total, 'The full check of the site: test suites, figures across pages, a rotating set of buttons; emailed to you', 'every 7 days, with the daily update', w && w.at],
            [fresh(r && r.at, 8 * 24), 'The autopilot\'s weekly review: written by itself, shown in the row above', 'every 7 days', r && r.at],
            [true, `Its trials and improvements: ${trials} being tested now (the Improvements tab)`, 'each decided on its day', null]];
        return `<div class="ad-card"><span class="ad-label">🔁 What runs by itself</span><ul style="list-style: none; margin: 4px 0 0; padding: 0; line-height: 1.6;">`
            + jobs.map(([ok, what, how, at]) => `<li><span style="color: ${ok ? 'var(--ad-green)' : 'var(--ad-red)'};">●</span> ${esc(what)} <span class="ad-sub">· ${esc(how)}${at ? ' · last ' + esc(ago(at)) : ''}</span></li>`).join('')
            + `</ul><div class="ad-sub" style="margin-top: 6px;">"Do you need to check in?" at the top turns amber or red when one of these fails or is late, when a decision waits, or when 7 days pass without a session. Nothing changes the site's code by itself: fixes and improvements are made in a session, when you say hi.</div></div>`;
    }
    function weeklyHtml(w) {
        if (!w) return '';
        const age = (Date.now() - Date.parse(w.at)) / 86400000, ok = w.passed === w.total, late = age > 8;
        const groupName = { '1': 'Test suites on the live code', '2': 'The figures agree across the site', '3': 'Analysis buttons, end to end (six screeners in turn)', '4': 'The background run, visitors\' limits and your live pages' };
        const items = w.items || [], groups = {};
        items.forEach(([g, name, pass]) => { (groups[g] = groups[g] || []).push([name, pass]); });
        const list = Object.keys(groups).sort().map(g => `<div style="margin-top: 8px; font-weight: 600; color: var(--text-primary);">${esc(groupName[g] || g)} <span class="ad-sub">${groups[g].filter(x => x[1]).length} of ${groups[g].length}</span></div>`
            + `<ul style="list-style: none; margin: 2px 0 0; padding: 0; line-height: 1.55;">${groups[g].map(([n, p]) => `<li><span class="${p ? 'ok' : 'red'}" style="font-weight: 700;">${p ? '✓' : '✗'}</span> ${esc(n)}</li>`).join('')}</ul>`).join('');
        return `<div class="ad-card ${ok && !late ? 'run' : 'run bad'}" style="padding-top: 10px; padding-bottom: 10px;"><span class="ad-label">🧪 Full check of the site</span>
            <div style="margin-top: 4px;"><span class="${ok ? 'ok' : 'red'}" style="font-weight: 700;">${ok ? '✓ All ' + w.total + ' checks passed' : (w.total - w.passed) + ' of ' + w.total + ' checks failed'}</span> <span class="ad-sub">${esc(new Date(w.at).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }))}${late ? ' · due again: it runs every 7 days with the daily update' : ' · runs by itself every 7 days, with the daily update'}</span></div>
            ${w.covered ? `<div class="ad-sub" style="margin-top: 4px;">It covers ${w.covered} of the ${w.parts} parts of the site. Left to a person: ${esc((w.uncovered || []).join('; '))}.</div>` : ''}
            ${!ok && !items.length ? `<ul style="margin: 6px 0 0 18px; padding: 0;">${(w.failed || []).map(f => `<li>${esc(f)}</li>`).join('')}</ul>` : ''}
            ${list}</div>`;
    }
    function auditHtml(a) {
        if (!a || !a.findings) return '';
        const row = (f) => `<li style="margin: 4px 0;"><span class="ad-pill ${f.level === 'problem' ? 'bad' : 'info'}" style="margin-right: 6px;">${f.level === 'problem' ? 'problem' : 'idea'}</span>${f.new ? '<strong style="color: var(--ad-amber);">new</strong> ' : ''}${esc(f.text)}${f.where ? ` <span class="ad-sub">${esc(f.where)}</span>` : ''}</li>`;
        const probs = a.findings.filter(f => f.level === 'problem'), ideas = a.findings.filter(f => f.level !== 'problem');
        return `<div class="ad-card${probs.length ? ' run bad' : ' run'}"><span class="ad-label">🔎 Site check <span class="ad-sub">with the daily update (Mon to Sat, while your Mac is on) · last ${esc(day(a.at))} · ${probs.length} problem${probs.length === 1 ? '' : 's'}, ${ideas.length} idea${ideas.length === 1 ? '' : 's'}${a.new ? ` · ${a.new} new` : ''}${a.gone ? ` · ${a.gone} put right` : ''}</span></span>
            <div class="ad-sub" style="margin: 4px 0 6px;">The site's pages and scripts tested for faults a person would otherwise have to spot: links, search basics, copied code, made-up visuals, pages that grew heavy. A session works through these; nothing here changes the site by itself.</div>
            ${probs.length ? `<ul style="margin: 0; padding-left: 18px;">${probs.map(row).join('')}</ul>` : '<div>✓ No problems found.</div>'}
            ${ideas.length ? `<details style="margin-top: 6px;"><summary class="ad-sub" style="cursor: pointer;">${ideas.length} idea${ideas.length === 1 ? '' : 's'}</summary><ul style="margin: 4px 0 0; padding-left: 18px;">${ideas.map(row).join('')}</ul></details>` : ''}</div>`;
    }
    // What the sessions changed, in plain words (check-tools/changes.json, copied in by admin.py; 18 Oct 2026, the owner: "easy for
    // me to read on admin page what is going on")
    function changesHtml(list) {
        if (!list || !list.length) return '';
        const when = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }); };
        const li = c => `<li>${esc(c.what)} <span class="ad-sub">${esc(when(c.at))}</span></li>`;
        return `<div class="ad-card" id="ad-changes"><span class="ad-label">🔧 What changed lately</span><ul class="ad-plain">${list.slice(0, 5).map(li).join('')}</ul>`
            + (list.length > 5 ? `<details><summary class="ad-sub" style="cursor: pointer;">${list.length - 5} earlier</summary><ul class="ad-plain">${list.slice(5).map(li).join('')}</ul></details>` : '') + '</div>';
    }
    function answeredHtml(list) {
        if (!list.length) return '';
        const word = { done: ['done', 'good'], yes: ['yes: for the next session', 'info'], no: ['not now', 'warn'] };
        // Straight under "Decisions for you" (18 Oct 2026, the owner: "so i can easily see without having to scroll down"):
        // the latest three on show, the rest folded
        const li = p => { const w = word[p.status] || [p.status, 'info']; return `<li>${esc(p.title)} <span class="ad-pill ${w[1]}">${esc(w[0])}</span> <span class="ad-sub">${p.answered ? esc(day(p.answered)) : ''}</span></li>`; };
        const recent = list.slice(0, 3), older = list.slice(3);
        return `<div class="ad-card" id="ad-answered"><span class="ad-label">Answered <span class="ad-sub">${list.length}</span></span><ul class="ad-plain">${recent.map(li).join('')}</ul>`
            + (older.length ? `<details><summary class="ad-sub" style="cursor: pointer;">${older.length} earlier</summary><ul class="ad-plain">${older.map(li).join('')}</ul></details>` : '') + '</div>';
    }

    function render() {
        const el = box(); if (!el || !data) return;
        style();
        const n = ((data.plan || {}).items || []).filter(e => e.status === 'running').length;      // the tab's number: being tested now
        const tabs = `<div class="ad-views"><button type="button" class="ad-view${view === 'overview' ? ' on' : ''}" data-ad-view="overview">Overview</button><button type="button" class="ad-view${view === 'improvements' ? ' on' : ''}" data-ad-view="improvements">🧭 Improvements${n ? ` (${n} being tested)` : ''}</button></div>`;
        if (view === 'improvements') {
            el.innerHTML = `<h3 style="margin: 0 0 4px;">🛠 Admin</h3>${tabs}${planHtml(data.plan) || '<div class="ad-card">No improvements recorded yet.</div>'}`;
            return;
        }
        el.innerHTML = `<h3 style="margin: 0 0 4px;">🛠 Admin</h3>${tabs}<div class="ad-sub">Only your account sees this page. The autopilot runs by itself; this is where it tells you how it is doing and asks you the big questions.</div>
            ${message ? `<div class="ad-msg${/^Not done/.test(message) ? ' bad' : ''}">${esc(message)}</div>` : ''}
            ${needMeHtml(data)}${decisionHtml()}${goalHtml(data.goal)}${(data.open || []).length ? propsHtml(data.open) : ''}${changesHtml((data.plan || {}).changes)}
            <div class="ad-rows">${rowsHtml(data)}</div>`;
    }

    function reveal() {
        const tab = document.querySelector('[data-dash-tab="admin"]'); if (tab) tab.hidden = false;
        const menu = document.getElementById('account-dropdown');
        const add = () => { if (menu && !document.getElementById('admin-link')) { const a = document.createElement('a'); a.id = 'admin-link'; a.href = 'dashboard.html#admin'; a.textContent = '🛠 Admin'; menu.insertBefore(a, menu.firstChild); } };
        add();
        if (menu && window.MutationObserver) new MutationObserver(add).observe(menu, { childList: true });    // the account menu is redrawn at sign-in
        let last = ''; try { last = localStorage.getItem('stockiqDashboardTab') || ''; } catch (e) {}
        if (window.dashboardTabs && ((location.hash || '') === '#admin' || (last === 'admin' && !location.hash))) window.dashboardTabs.show('admin');   // the tab appears after the page: come back to it
    }

    async function load() {
        if (!userId() || !box()) return;
        try { const r = await call(); data = r.admin; reveal(); render(); }
        catch (e) { /* not one of the site's own accounts, or not reachable: nothing is shown */ }
    }

    document.addEventListener('click', async (e) => {
        const v = e.target.closest && e.target.closest('#admin-panel [data-ad-view]');
        const vName = v && v.getAttribute('data-ad-view');
        if (vName === 'overview' || vName === 'improvements') { e.preventDefault(); view = vName; try { localStorage.setItem('stockiqAdminView', view); } catch (x) {} render(); return; }
        // the jump links at the top of the Improvements view: scroll there, without changing the address (the dashboard's tabs read it)
        const j = e.target.closest && e.target.closest('#admin-panel [data-ad-jump]');
        const jid = j && j.getAttribute ? j.getAttribute('data-ad-jump') : null;
        if (jid) { e.preventDefault(); const to = document.getElementById(jid); if (to) { const d = to.closest('details'); if (d) d.open = true; to.scrollIntoView({ behavior: 'smooth', block: 'start' }); } return; }
        const t = e.target.closest && e.target.closest('#admin-panel [data-ad-answer], #admin-panel [data-ad]');
        if (!t || busy) return;
        e.preventDefault();
        const id = t.getAttribute('data-ad-id'), answer = t.getAttribute('data-ad-answer');
        const what = answer ? 'answer' : t.getAttribute('data-ad') === 'usage' ? 'usage' : 'review';
        busy = what; render();
        try {
            const r = await call(answer ? { op: 'answer', id: Number(id), answer } : { op: what });
            data = r.admin;
            const p = answer ? (data.answered || []).find(x => String(x.id) === String(id)) : null;
            message = what === 'usage' ? usageMessage(data.usage) : !answer ? 'The review is written from the latest figures. Nothing was bought, sold or changed; the next automatic one is 7 days from now.' : !p ? '' : p.status === 'done' ? `Done: ${p.title}. It is in force now (the autopilot's activity list says so too).` : p.status === 'yes' ? `Noted: "${p.title}" is for your next session, which will do it and tell you.` : `Left as it is: ${p.title}.`;
            if (p && p.status === 'done' && window.practiceAutopilot && window.practiceAutopilot.reload) window.practiceAutopilot.reload();
        } catch (err) { message = 'Not done: ' + err.message; }
        busy = ''; render();
    });

    document.addEventListener('practice-portfolio:figures', () => { if (data) render(); });     // redraw with the same figure the tab shows
    window.adminPanel = { load, render, state: () => data };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load); else load();
})();
