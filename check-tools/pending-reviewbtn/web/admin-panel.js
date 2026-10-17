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
        s.textContent = `
        #admin-panel .ad-card { border: 1px solid var(--border-color); border-radius: 10px; padding: 16px 18px; margin: 14px 0; background: var(--card-bg); }
        #admin-panel .ad-label { display: block; font-weight: 700; margin-bottom: 8px; color: var(--text-primary); }
        #admin-panel .ad-sub { color: var(--text-secondary); font-size: 0.85rem; }
        #admin-panel .ad-row { display: grid; grid-template-columns: 1fr auto auto; gap: 6px 14px; padding: 6px 0; border-top: 1px solid var(--border-color); align-items: baseline; }
        #admin-panel .ad-row:first-of-type { border-top: none; }
        #admin-panel .ok { color: #16a34a; font-weight: 700; } #admin-panel .no { color: #d97706; font-weight: 700; }
        #admin-panel .ad-prop { border-top: 1px solid var(--border-color); padding: 12px 0; } #admin-panel .ad-prop:first-of-type { border-top: none; padding-top: 4px; }
        #admin-panel .ad-prop b { color: var(--text-primary); }
        #admin-panel .ad-tag { display: inline-block; font-size: 0.75rem; border: 1px solid var(--border-color); border-radius: 10px; padding: 1px 8px; margin-left: 6px; color: var(--text-secondary); }
        #admin-panel .ad-btn { padding: 7px 14px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-primary); cursor: pointer; margin: 8px 8px 0 0; font-size: 0.9rem; }
        #admin-panel .ad-btn.yes { background: #2563eb; border-color: #2563eb; color: #fff; }
        #admin-panel .ad-btn:hover { border-color: #3b82f6; } #admin-panel .ad-btn[disabled] { opacity: 0.6; cursor: default; }
        #admin-panel ul { margin: 6px 0 0 18px; padding: 0; } #admin-panel li { margin: 4px 0; color: var(--text-primary); }
        #admin-panel .ad-msg { margin: 10px 0; padding: 8px 12px; border-radius: 8px; background: var(--bg-secondary); }
        @media (max-width: 640px) { #admin-panel .ad-row { grid-template-columns: 1fr; } }`;
        document.head.appendChild(s);
    }

    function goalHtml(g) {
        if (!g) return '';
        const row = (name, now, goal, met) => `<div class="ad-row"><span>${name}</span><span>${now}</span><span class="${met ? 'ok' : 'no'}">${met ? '✓ ' : ''}target ${goal}</span></div>`;
        return `<div class="ad-card"><span class="ad-label">${esc(g.name)} <span class="ad-sub">due ${esc(g.due)}, ${g.daysLeft} days left</span></span>
            ${row('Finished trades in all', g.trades, g.tradesGoal, g.trades >= g.tradesGoal)}
            ${row('Average a trade this month, after costs', `${g.avg >= 0 ? '+' : ''}${Number(g.avg).toFixed(2)}% <span class="ad-sub">(± ${Number(g.se).toFixed(2)}, ${g.n} trades)</span>`, `above ${g.avgGoal >= 0 ? '+' : ''}${g.avgGoal}%`, g.n > 0 && g.avg > g.avgGoal)}
            ${row('The practice account, about', usd(g.value), usd(g.valueGoal), g.value >= g.valueGoal)}
            <div class="ad-sub" style="margin-top: 8px;">Fake money. These targets are what would count as progress, set on 12 Oct before the results were in; they are not forecasts.</div></div>`;
    }

    function propsHtml(open) {
        const body = open.length ? open.map(p => `<div class="ad-prop"><b>${esc(p.title)}</b><span class="ad-tag">${p.kind === 'setting' ? 'applied the moment you say yes' : 'done in your next session'}</span>
            <div class="ad-sub" style="margin-top: 4px;">${esc(p.why)}</div>
            <button type="button" class="ad-btn yes" data-ad-answer="yes" data-ad-id="${p.id}" ${busy ? 'disabled' : ''}>Yes</button><button type="button" class="ad-btn" data-ad-answer="no" data-ad-id="${p.id}" ${busy ? 'disabled' : ''}>Not now</button></div>`).join('')
            : '<div class="ad-sub">Nothing needs your yes right now. Proposals appear here when the weekly review finds something, or when a session has something for you to decide.</div>';
        return `<div class="ad-card"><span class="ad-label">Needs your yes ${open.length ? `<span class="ad-sub">${open.length}</span>` : ''}</span>${body}</div>`;
    }

    function reviewHtml(r, next) {
        return `<div class="ad-card"><span class="ad-label">Weekly review <span class="ad-sub">${r ? 'written by the autopilot ' + esc(day(r.at)) + (next ? '; the next one ' + esc(day(next)) : '') : 'not written yet: the scheduled run writes one every 7 days'}</span></span>
            ${r ? '<ul>' + r.lines.map(l => `<li>${esc(l)}</li>`).join('') + '</ul>' : ''}
            <button type="button" class="ad-btn" data-ad="review" ${busy ? 'disabled' : ''}>${busy === 'review' ? 'Writing…' : 'Write a fresh one now'}</button>
            <div class="ad-sub" style="margin-top: 6px;">You never need to press this: the autopilot writes the review by itself every 7 days. Pressing it writes it again straight away from the latest figures. It buys, sells and changes nothing; it may add a question under "Needs your yes"; and the next automatic review then comes 7 days after your press.</div>
            <div class="ad-sub" style="margin-top: 8px;">A group of trades is only called losing or making money from 30 trades, and only when it is beyond twice its margin of error. Past practice results; nothing here is advice.</div></div>`;
    }

    function healthHtml(h, s, screeners) {
        const runs = h ? `Last scheduled run ${esc(ago(h.at))} (${esc(day(h.at))}): ${h.ran} of ${h.on} switched-on account${h.on === 1 ? '' : 's'} checked in${h.waiting ? ', ' + h.waiting + ' left for the next run' : ''}${h.paused ? ', ' + h.paused + ' paused' : ''}. ` + (h.failed ? `<span class="no">${h.failed} check-in${h.failed === 1 ? '' : 's'} stopped on an error.</span>` : '<span class="ok">No errors.</span>') : 'No scheduled run recorded yet (it runs at :10 and :40 past every hour).';
        const set = s ? `Autopilot ${s.enabled ? 'on' : 'off'}; level ${s.risk}; ${s.holdings || 'the level\'s'} holdings; budget ${usd(s.budgetUsd)}; checks in every ${s.everyHours} h; keeps a holding up to ${s.maxHoldDays} days; AI review's early sales ${s.aiSell ? 'on' : 'off'}; tries changes to its rules ${s.selfTune ? 'on' : 'off'}. Screeners: ${screeners.length ? esc(screeners.join(', ')) : 'none'}.` : '';
        return `<div class="ad-card"><span class="ad-label">How it is running</span><div>${runs}</div><div class="ad-sub" style="margin-top: 8px;">${set}</div>
            <div class="ad-sub" style="margin-top: 8px;">AWS usage against the free allowance: in your daily usage email (this page cannot read it yet).</div></div>`;
    }

    function answeredHtml(list) {
        if (!list.length) return '';
        const word = { done: 'done', yes: 'yes: for the next session', no: 'not now' };
        return `<details class="ad-card"><summary class="ad-label" style="cursor: pointer; margin: 0;">Answered <span class="ad-sub">${list.length}</span></summary><ul>${list.map(p => `<li>${esc(p.title)} <span class="ad-sub">(${esc(word[p.status] || p.status)}${p.answered ? ', ' + esc(day(p.answered)) : ''})</span></li>`).join('')}</ul></details>`;
    }

    function render() {
        const el = box(); if (!el || !data) return;
        style();
        el.innerHTML = `<h3 style="margin: 0 0 4px;">🛠 Admin</h3><div class="ad-sub">Only your account sees this page. The autopilot runs by itself; this is where it tells you how it is doing and asks you the big questions.</div>
            ${message ? `<div class="ad-msg">${esc(message)}</div>` : ''}
            ${goalHtml(data.goal)}${propsHtml(data.open || [])}${reviewHtml(data.review, data.nextReview)}${healthHtml(data.health, data.settings, data.screeners || [])}${answeredHtml(data.answered || [])}`;
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
