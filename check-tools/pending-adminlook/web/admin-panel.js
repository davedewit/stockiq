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
        #admin-panel .ad-pill.bad { background: var(--ad-red-bg); color: var(--ad-red); } #admin-panel .ad-pill.info { background: var(--ad-blue-bg); color: var(--ad-blue); }
        #admin-panel .ok { color: var(--ad-green); font-weight: 700; } #admin-panel .no { color: var(--ad-amber); font-weight: 700; } #admin-panel .red { color: var(--ad-red); font-weight: 700; }
        #admin-panel .ad-prop { border-top: 1px solid var(--border-color); padding: 12px 0; } #admin-panel .ad-prop:first-of-type { border-top: none; padding-top: 4px; }
        #admin-panel .ad-prop b { color: var(--text-primary); font-size: 1rem; }
        #admin-panel .ad-tag { display: inline-block; font-size: 0.75rem; border-radius: 10px; padding: 1px 8px; margin-left: 6px; background: var(--ad-blue-bg); color: var(--ad-blue); font-weight: 600; }
        #admin-panel .ad-btn { padding: 7px 14px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-primary); cursor: pointer; margin: 8px 8px 0 0; font-size: 0.9rem; }
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
    function tilesHtml(d) {
        const g = d.goal, h = d.health, open = (d.open || []).length;
        const tile = (kind, label, value, sub) => `<div class="ad-tile ${kind}"><div class="ad-tile-label">${label}</div><div class="ad-tile-value">${value}</div><div class="ad-tile-sub">${sub}</div></div>`;
        const out = [];
        if (g) {
            const gain = g.value - 100000;
            out.push(tile(gain >= 0 ? 'good' : 'bad', 'Practice account', usd(g.value), `${money(gain)} since the start`));
            const met = [g.trades >= g.tradesGoal, g.n > 0 && g.avg > g.avgGoal, g.value >= g.valueGoal].filter(Boolean).length;
            out.push(tile(met === 3 ? 'good' : met ? 'warn' : 'bad', esc(g.name), `${met} of 3 met`, `${g.daysLeft} days left (due ${esc(g.due)})`));
        }
        out.push(tile(open ? 'warn' : 'good', 'Needs your yes', open ? String(open) : '✓ Nothing', open ? 'see below and answer' : 'nothing to decide'));
        if (h) {
            const late = Date.now() - Date.parse(h.at) > 70 * 60000;
            out.push(tile(h.failed ? 'bad' : late ? 'warn' : 'good', 'Running', h.failed ? `${h.failed} error${h.failed === 1 ? '' : 's'}` : late ? 'Late' : '✓ OK', `last run ${esc(ago(h.at))}`));
        } else out.push(tile('warn', 'Running', 'Not yet', 'no scheduled run recorded'));
        return `<div class="ad-tiles">${out.join('')}</div>`;
    }

    function goalHtml(g) {
        if (!g) return '';
        const row = (name, now, goal, met, fill) => `<div class="ad-goal"><div class="ad-goal-head"><span class="ad-goal-name">${name}</span>
            <span><span class="ad-goal-now">${now}</span> <span class="ad-pill ${met ? 'good' : 'warn'}">${met ? '✓ target ' : 'target '}${goal}</span></span></div>
            ${fill === null ? '' : `<div class="ad-bar${met ? ' met' : ''}"><span style="width: ${Math.max(2, Math.min(100, fill)).toFixed(0)}%;"></span></div>`}</div>`;
        const avgOk = g.n > 0 && g.avg > g.avgGoal;
        return `<div class="ad-card goal"><span class="ad-label">🎯 ${esc(g.name)} <span class="ad-sub">due ${esc(g.due)}, ${g.daysLeft} days left</span></span>
            ${row('Finished trades in all', String(g.trades), g.tradesGoal, g.trades >= g.tradesGoal, g.trades / g.tradesGoal * 100)}
            ${row('Average a trade this month, after costs', `<span class="${avgOk ? 'ok' : 'red'}">${signed(g.avg, 2)}%</span> <span class="ad-sub">(± ${Number(g.se).toFixed(2)}, ${g.n} trades)</span>`, `above ${signed(g.avgGoal, 1)}%`, avgOk, null)}
            ${row('The practice account, about', `<span class="${g.value >= g.valueGoal ? 'ok' : 'red'}">${usd(g.value)}</span>`, usd(g.valueGoal), g.value >= g.valueGoal, g.value / g.valueGoal * 100)}
            <div class="ad-sub" style="margin-top: 8px;">Fake money. These targets are what would count as progress, set on 12 Oct before the results were in; they are not forecasts.</div></div>`;
    }

    function propsHtml(open) {
        const body = open.length ? open.map(p => `<div class="ad-prop"><b>${esc(p.title)}</b><span class="ad-tag">${p.kind === 'setting' ? 'applied the moment you say yes' : 'done in your next session'}</span>
            <div class="ad-sub" style="margin-top: 4px;">${esc(p.why)}</div>
            <button type="button" class="ad-btn yes" data-ad-answer="yes" data-ad-id="${p.id}" ${busy ? 'disabled' : ''}>Yes</button><button type="button" class="ad-btn" data-ad-answer="no" data-ad-id="${p.id}" ${busy ? 'disabled' : ''}>Not now</button></div>`).join('')
            : '<div class="ok">✓ Nothing needs your yes right now.</div><div class="ad-sub" style="margin-top: 4px;">Proposals appear here when the weekly review finds something, or when a session has something for you to decide.</div>';
        return `<div class="ad-card ask${open.length ? ' waiting' : ''}"><span class="ad-label">${open.length ? '⚠️' : '✅'} Needs your yes ${open.length ? `<span class="ad-pill warn">${open.length}</span>` : ''}</span>${body}</div>`;
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
            <div class="ad-sub" style="margin-top: 6px;">You never need to press this: the autopilot writes the review by itself every 7 days. Pressing it writes it again straight away from the latest figures. It buys, sells and changes nothing; it may add a question under "Needs your yes"; and the next automatic review then comes 7 days after your press.</div>
            <div class="ad-sub" style="margin-top: 8px;">A group of trades is only called losing or making money from 30 trades, and only when it is beyond twice its margin of error. Past practice results; nothing here is advice.</div></div>`;
    }

    function healthHtml(h, s, screeners) {
        const runs = h ? `Last scheduled run ${esc(ago(h.at))} (${esc(day(h.at))}): ` + (h.ran ? `${h.ran} of ${h.on} switched-on account${h.on === 1 ? '' : 's'} checked in` : 'nothing was due (its markets were closed, or its next check-in had not come)') + `${h.waiting ? ', ' + h.waiting + ' left for the next run' : ''}${h.paused ? ', ' + h.paused + ' paused' : ''}. ` + (h.failed ? `<span class="red">${h.failed} check-in${h.failed === 1 ? '' : 's'} stopped on an error.</span>` : '<span class="ok">✓ No errors.</span>') : 'No scheduled run recorded yet (it runs at :10 and :40 past every hour).';
        const chip = (text, on) => `<span class="ad-chip${on === false ? ' off' : ''}">${text}</span>`;
        const chips = s ? [chip(`Autopilot <b>${s.enabled ? 'on' : 'off'}</b>`, s.enabled), chip(`Level <b>${esc(s.risk)}</b>`), chip(`<b>${esc(s.holdings || "the level's")}</b> holdings`), chip(`Budget <b>${usd(s.budgetUsd)}</b>`),
            chip(`Checks in every <b>${esc(s.everyHours)} h</b>`), chip(`Keeps a holding up to <b>${esc(s.maxHoldDays)} days</b>`), chip(`AI review's early sales <b>${s.aiSell ? 'on' : 'off'}</b>`, s.aiSell), chip(`Tries changes to its rules <b>${s.selfTune ? 'on' : 'off'}</b>`, s.selfTune)].join('') : '';
        return `<div class="ad-card run${h && h.failed ? ' bad' : ''}"><span class="ad-label">⚙️ How it is running</span><div>${runs}</div>
            ${chips ? `<div class="ad-chips">${chips}</div>` : ''}
            ${s ? `<details class="ad-more"><summary>Screeners it buys from (${screeners.length})</summary><div class="ad-sub" style="margin-top: 6px;">${screeners.length ? esc(screeners.join(', ')) : 'none'}.</div></details>` : ''}
            <div class="ad-sub" style="margin-top: 8px;">AWS usage against the free allowance: in your daily usage email (this page cannot read it yet).</div></div>`;
    }

    function answeredHtml(list) {
        if (!list.length) return '';
        const word = { done: ['done', 'good'], yes: ['yes: for the next session', 'info'], no: ['not now', 'warn'] };
        return `<details class="ad-card"><summary class="ad-label" style="cursor: pointer; margin: 0;">Answered <span class="ad-sub">${list.length}</span></summary><ul class="ad-plain">${list.map(p => { const w = word[p.status] || [p.status, 'info']; return `<li>${esc(p.title)} <span class="ad-pill ${w[1]}">${esc(w[0])}</span> <span class="ad-sub">${p.answered ? esc(day(p.answered)) : ''}</span></li>`; }).join('')}</ul></details>`;
    }

    function render() {
        const el = box(); if (!el || !data) return;
        style();
        el.innerHTML = `<h3 style="margin: 0 0 4px;">🛠 Admin</h3><div class="ad-sub">Only your account sees this page. The autopilot runs by itself; this is where it tells you how it is doing and asks you the big questions.</div>
            ${message ? `<div class="ad-msg${/^Not done/.test(message) ? ' bad' : ''}">${esc(message)}</div>` : ''}
            ${tilesHtml(data)}${propsHtml(data.open || [])}${goalHtml(data.goal)}${reviewHtml(data.review, data.nextReview)}${healthHtml(data.health, data.settings, data.screeners || [])}${answeredHtml(data.answered || [])}`;
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
        const t = e.target.closest && e.target.closest('#admin-panel [data-ad-answer], #admin-panel [data-ad]');
        if (!t || busy) return;
        e.preventDefault();
        const id = t.getAttribute('data-ad-id'), answer = t.getAttribute('data-ad-answer');
        busy = answer ? 'answer' : 'review'; render();
        try {
            const r = await call(answer ? { op: 'answer', id: Number(id), answer } : { op: 'review' });
            data = r.admin;
            const p = answer ? (data.answered || []).find(x => String(x.id) === String(id)) : null;
            message = !answer ? 'The review is written from the latest figures. Nothing was bought, sold or changed; the next automatic one is 7 days from now.' : !p ? '' : p.status === 'done' ? `Done: ${p.title}. It is in force now (the autopilot's activity list says so too).` : p.status === 'yes' ? `Noted: "${p.title}" is for your next session, which will do it and tell you.` : `Left as it is: ${p.title}.`;
            if (p && p.status === 'done' && window.practiceAutopilot && window.practiceAutopilot.reload) window.practiceAutopilot.reload();
        } catch (err) { message = 'Not done: ' + err.message; }
        busy = ''; render();
    });

    window.adminPanel = { load, render, state: () => data };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load); else load();
})();
