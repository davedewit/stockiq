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
        if (f) return Object.assign({}, g, { value: f.accountValue, live: true });
        const waiting = Date.now() - shownAt < LIVE_WAIT_MS;
        if (waiting && !waitTimer) waitTimer = setTimeout(() => { if (data) render(); }, LIVE_WAIT_MS - (Date.now() - shownAt) + 50);
        return Object.assign({}, g, { live: false, waiting });
    }

    function tilesHtml(d) {
        const g = withLive(d.goal), h = d.health, open = (d.open || []).length;
        const tile = (kind, label, value, sub) => `<div class="ad-tile ${kind}"><div class="ad-tile-label">${label}</div><div class="ad-tile-value">${value}</div><div class="ad-tile-sub">${sub}</div></div>`;
        const out = [];
        if (g) {
            const gain = g.value - 100000;
            out.push(g.waiting ? tile('', 'Practice account', '…', 'getting the latest prices') : tile(gain >= 0 ? 'good' : 'bad', 'Practice account', usd(g.value), `${money(gain)} since the start${g.live ? '' : ' (an estimate: the latest prices did not come in)'}`));
            const met = [g.trades >= g.tradesGoal, g.n > 0 && g.avg > g.avgGoal, g.value >= g.valueGoal].filter(Boolean).length;
            out.push(tile(met === 3 ? 'good' : met ? 'warn' : 'bad', esc(g.name), `${met} of 3 met`, `${g.daysLeft} days left (due ${esc(g.due)})`));
        }
        out.push(tile(open ? 'warn' : 'good', 'Decisions for you', open ? String(open) : '✓ None', open ? 'see below and answer' : 'nothing waiting'));
        if (h) {
            const late = Date.now() - Date.parse(h.at) > 70 * 60000;
            out.push(tile(h.failed ? 'bad' : late ? 'warn' : 'good', 'Running', h.failed ? `${h.failed} error${h.failed === 1 ? '' : 's'}` : late ? 'Late' : '✓ OK', `last run ${esc(ago(h.at))}`));
        } else out.push(tile('warn', 'Running', 'Not yet', 'no scheduled run recorded'));
        return `<div class="ad-tiles">${out.join('')}</div>`;
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
            ${row(g.live ? 'The practice account, at the latest prices' : g.waiting ? 'The practice account (getting the latest prices)' : 'The practice account, about (an estimate: the latest prices did not come in)', g.waiting ? '…' : `<span class="${g.value >= g.valueGoal ? 'ok' : 'red'}">${usd(g.value)}</span>`, usd(g.valueGoal), g.value >= g.valueGoal, g.value / g.valueGoal * 100)}
            <div class="ad-sub" style="margin-top: 8px;">Fake money. These targets are what would count as progress, set on 12 Oct before the results were in; they are not forecasts.</div></div>`;
    }

    function propsHtml(open) {
        const body = open.length ? open.map(p => `<div class="ad-prop"><b>${esc(p.title)}</b><span class="ad-tag">${p.kind === 'setting' ? 'applied the moment you say yes' : 'done in your next session'}</span>
            <div class="ad-sub" style="margin-top: 4px;">${esc(p.why)}</div>
            <button type="button" class="ad-btn yes" data-ad-answer="yes" data-ad-id="${p.id}" ${busy ? 'disabled' : ''}>Yes</button><button type="button" class="ad-btn" data-ad-answer="no" data-ad-id="${p.id}" ${busy ? 'disabled' : ''}>Not now</button></div>`).join('')
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
            chip(`Checks in every <b>${esc(s.everyHours)} h</b>`), chip(`Keeps a holding up to <b>${esc(s.maxHoldDays)} days</b>`), chip(`Tries changes to its rules <b>${s.selfTune ? 'on' : 'off'}</b>`, s.selfTune)].join('') : '';
        return `<div class="ad-card run${h && h.failed ? ' bad' : ''}"><span class="ad-label">⚙️ How it is running</span><div>${runs}</div>
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
        if (u.costForecast) chips.push(`<span class="ad-pill ${u.costForecast < 1 ? 'good' : u.costForecast < 1.5 ? 'warn' : 'bad'}">AWS forecasts about $${Number(u.costForecast).toFixed(2)} for the month</span>`);
        if (u.cost !== undefined) chips.unshift(`<span class="ad-pill ${u.cost < 1 ? 'good' : u.cost < 1.5 ? 'warn' : 'bad'}">AWS bill this month so far: $${Number(u.cost).toFixed(2)} <span style="font-weight:400;">(warning at $1, limit $1.50)</span></span>`);
        if (u.calls !== undefined) {
            const share = u.calls / (u.free || 1000000), f = u.forecast ? u.forecast / (u.free || 1000000) : share;
            chips.push(`<span class="ad-pill ${f < 0.7 ? 'good' : f < 1 ? 'warn' : 'bad'}">Lambda calls: ${Number(u.calls).toLocaleString('en-US')} of ${(u.free || 1000000).toLocaleString('en-US')} free (${Math.round(share * 100)}%)</span>`);
            if (u.forecast) chips.push(`<span class="ad-pill info">on course for about ${Math.round(u.forecast / 1000).toLocaleString('en-US')}k this month</span>`);
            if (u.yesterday) chips.push(`<span class="ad-pill info">yesterday ${Number(u.yesterday).toLocaleString('en-US')}</span>`);
        }
        const err = u.costError || u.callsError ? ` <span class="ad-sub">(${u.costError ? 'the bill could not be read' : ''}${u.costError && u.callsError ? '; ' : ''}${u.callsError ? 'the calls could not be read' : ''})</span>` : '';
        // each figure with its own age (17 Oct 2026: one "read 6 h ago" was the calls' age, while the bill could be 3 days old)
        const ages = [u.calls !== undefined ? `calls read ${esc(ago(u.at))}` : '', u.cost !== undefined && u.costAt ? `bill as AWS last updated it, ${esc(ago(u.costAt))}` : ''].filter(Boolean).join(' · ');
        return `<div style="margin-top: 12px;"><span class="ad-sub">AWS this month (${ages}):</span><div class="ad-chips">${chips.join('')}</div>${err}
            <button type="button" class="ad-btn" data-ad="usage" ${busy ? 'disabled' : ''}>${busy === 'usage' ? 'Reading…' : '↻ Refresh now'}</button>
            <div class="ad-sub" style="margin-top: 4px;">By itself it reads both about once a day; Refresh now reads them at once. Both are free to read: the bill comes from your AWS budget, which AWS updates a few times a day, and the calls from CloudWatch.</div></div>`;
    }

    // The improvements (17 Oct 2026; the owner: "put the list of future improvements to track them so i know which was run which is
    // next ... easily see if something was improved in the past"): check-tools/experiments.json and site_parts.json, copied here by
    // admin.py sync. Being tested (with how far to its decision), next in order, and done (kept or taken out, with the result).
    function planHtml(pl) {
        if (!pl || !pl.items) return '';
        const items = pl.items, by = (st) => items.filter(e => e.status === st);
        const running = by('running').sort((a, b) => (a.decide || '').localeCompare(b.decide || ''));
        const next = by('idea').sort((a, b) => (a.order || 99) - (b.order || 99));
        const done = items.filter(e => e.status === 'kept' || e.status === 'removed').sort((a, b) => (b.decided || '').localeCompare(a.decided || ''));
        const tags0 = (a) => (a || '').split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="ad-tag">${esc(t)}</span>`).join('');
        // the item itself is passed where it is known, so that one shown to every user carries 👥
        const tags = (a, e) => tags0(a) + (e && e.public ? '<span class="ad-tag pub" title="Also shown, in plain words, to every user on the AI autopilot tab">👥 users see it</span>' : '');
        const dayms = 86400000, todayMs = Date.now();
        const runRow = (e) => {
            const a = Date.parse(e.started), b = Date.parse(e.decide), pct = a && b && b > a ? Math.max(3, Math.min(100, (todayMs - a) / (b - a) * 100)) : 0;
            const left = b ? Math.ceil((b - todayMs) / dayms) : null;
            return `<div class="ad-goal"><div class="ad-goal-head"><span><b>${esc(e.what)}</b>${tags(e.angle, e)}</span><span class="ad-pill ${left !== null && left <= 0 ? 'warn' : 'info'}">${left === null ? '' : left <= 0 ? 'decide now' : 'decided in ' + left + ' day' + (left === 1 ? '' : 's')}</span></div>
                <div class="ad-bar"><span style="width: ${pct.toFixed(0)}%; background: var(--ad-blue);"></span></div><div class="ad-sub" style="margin-top: 4px;">Measured by: ${esc(e.measure)}</div></div>`;
        };
        const doneRow = (e) => `<li class="${e.status === 'kept' ? 'good' : ''}"><b>${e.status === 'kept' ? '✓ Kept' : 'Taken out'}</b> · ${esc(e.what)} <span class="ad-sub">${esc(e.decided || '')}</span><div class="ad-sub" style="margin-top: 2px;">${esc(e.result || '')}</div></li>`;
        const reviewed = (pl.reviews || []).map(r => `<li><b>${esc(r.part)}</b> <span class="ad-sub">${esc(r.at)}</span><div class="ad-sub">${esc(r.found)}</div></li>`).join('');
        return `<div class="ad-card plan"><span class="ad-label">🧭 Improvements <span class="ad-sub">${running.length} being tested · ${next.length} next · ${by('kept').length} kept · ${by('removed').length} taken out · ${pl.reviewed || 0} of ${pl.parts || 0} parts of the site reviewed</span></span>
            <div class="ad-sub" style="margin-bottom: 8px;">Every change whose worth is not certain is tested over a period, then kept or taken out on the figures. Each session also reviews three parts of the site and adds new ideas. Updated ${esc(day(pl.at))}.</div>
            <div class="ad-sub" style="margin-bottom: 8px;">This is the full list, for you only. Every user sees a short, plain version on the AI autopilot tab ("How it is improving"): only what affects their autopilot, marked here 👥.</div>
            ${running.length ? `<div class="ad-section">Being tested now</div>${running.map(runRow).join('')}` : ''}
            ${next.length ? `<div class="ad-section">Next, in order</div><ol class="ad-next">${next.map(e => `<li><b>${esc(e.what)}</b>${tags(e.angle, e)}</li>`).join('')}</ol>` : ''}
            ${done.length ? `<div class="ad-section">Done, newest first</div><ul class="ad-lines">${done.map(doneRow).join('')}</ul>` : ''}
            ${reviewed ? `<details class="ad-more"><summary>Parts of the site reviewed lately (${(pl.reviews || []).length})</summary><ul class="ad-plain">${reviewed}</ul></details>` : ''}</div>`;
    }

    // The short version for the Overview: how many, what is being tested (soonest decision first) and the latest three done
    function planSummaryHtml(pl) {
        if (!pl || !pl.items) return '';
        const items = pl.items, by = (st) => items.filter(e => e.status === st);
        const running = by('running').sort((a, b) => (a.decide || '').localeCompare(b.decide || ''));
        const done = items.filter(e => e.status === 'kept' || e.status === 'removed').sort((a, b) => (b.decided || '').localeCompare(a.decided || ''));
        const left = (e) => { const b = Date.parse(e.decide); if (!b) return ''; const d = Math.ceil((b - Date.now()) / 86400000); return d <= 0 ? 'decide now' : d + ' day' + (d === 1 ? '' : 's'); };
        return `<div class="ad-card plan"><span class="ad-label">🧭 Improvements <span class="ad-sub">${running.length} being tested · ${by('idea').length} next · ${by('kept').length} kept · ${by('removed').length} taken out</span></span>
            <ul class="ad-lines">${running.slice(0, 3).map(e => `<li><b>Testing:</b> ${esc(e.what)} <span class="ad-pill info">${esc(left(e))}</span></li>`).join('')}
            ${done.slice(0, 3).map(e => `<li class="${e.status === 'kept' ? 'good' : ''}"><b>${e.status === 'kept' ? '✓ Kept' : 'Taken out'}:</b> ${esc(e.what)} <span class="ad-sub">${esc(e.decided || '')}</span></li>`).join('')}</ul>
            <button type="button" class="ad-btn" data-ad-view="improvements">See every improvement: what is next and the history →</button></div>`;
    }

    // The site checked every night (check-tools/site_audit.py, run by the daily deploy; 18 Oct 2026, the owner: "why can't you
    // actively do this every 24+ hours"). Problems first; each new since the night before is marked. A session works through them.
    function auditHtml(a) {
        if (!a || !a.findings) return '';
        const row = (f) => `<li style="margin: 4px 0;"><span class="ad-pill ${f.level === 'problem' ? 'bad' : 'info'}" style="margin-right: 6px;">${f.level === 'problem' ? 'problem' : 'idea'}</span>${f.new ? '<strong style="color: var(--ad-amber);">new</strong> ' : ''}${esc(f.text)}${f.where ? ` <span class="ad-sub">${esc(f.where)}</span>` : ''}</li>`;
        const probs = a.findings.filter(f => f.level === 'problem'), ideas = a.findings.filter(f => f.level !== 'problem');
        return `<div class="ad-card${probs.length ? ' run bad' : ' run'}"><span class="ad-label">🔎 Site check <span class="ad-sub">every night, by itself · last ${esc(day(a.at))} · ${probs.length} problem${probs.length === 1 ? '' : 's'}, ${ideas.length} idea${ideas.length === 1 ? '' : 's'}${a.new ? ` · ${a.new} new` : ''}${a.gone ? ` · ${a.gone} put right` : ''}</span></span>
            <div class="ad-sub" style="margin: 4px 0 6px;">The site's pages and scripts tested for faults a person would otherwise have to spot: links, search basics, copied code, made-up visuals, pages that grew heavy. A session works through these; nothing here changes the site by itself.</div>
            ${probs.length ? `<ul style="margin: 0; padding-left: 18px;">${probs.map(row).join('')}</ul>` : '<div>✓ No problems found.</div>'}
            ${ideas.length ? `<details style="margin-top: 6px;"><summary class="ad-sub" style="cursor: pointer;">${ideas.length} idea${ideas.length === 1 ? '' : 's'}</summary><ul style="margin: 4px 0 0; padding-left: 18px;">${ideas.map(row).join('')}</ul></details>` : ''}</div>`;
    }
    function answeredHtml(list) {
        if (!list.length) return '';
        const word = { done: ['done', 'good'], yes: ['yes: for the next session', 'info'], no: ['not now', 'warn'] };
        return `<details class="ad-card"><summary class="ad-label" style="cursor: pointer; margin: 0;">Answered <span class="ad-sub">${list.length}</span></summary><ul class="ad-plain">${list.map(p => { const w = word[p.status] || [p.status, 'info']; return `<li>${esc(p.title)} <span class="ad-pill ${w[1]}">${esc(w[0])}</span> <span class="ad-sub">${p.answered ? esc(day(p.answered)) : ''}</span></li>`; }).join('')}</ul></details>`;
    }

    function render() {
        const el = box(); if (!el || !data) return;
        style();
        const n = ((data.plan || {}).items || []).length;
        const tabs = `<div class="ad-views"><button type="button" class="ad-view${view === 'overview' ? ' on' : ''}" data-ad-view="overview">Overview</button><button type="button" class="ad-view${view === 'improvements' ? ' on' : ''}" data-ad-view="improvements">🧭 Improvements${n ? ` (${n})` : ''}</button></div>`;
        if (view === 'improvements') {
            el.innerHTML = `<h3 style="margin: 0 0 4px;">🛠 Admin</h3>${tabs}${planHtml(data.plan) || '<div class="ad-card">No improvements recorded yet.</div>'}`;
            return;
        }
        el.innerHTML = `<h3 style="margin: 0 0 4px;">🛠 Admin</h3>${tabs}<div class="ad-sub">Only your account sees this page. The autopilot runs by itself; this is where it tells you how it is doing and asks you the big questions.</div>
            ${message ? `<div class="ad-msg${/^Not done/.test(message) ? ' bad' : ''}">${esc(message)}</div>` : ''}
            ${tilesHtml(data)}${propsHtml(data.open || [])}${auditHtml((data.plan || {}).audit)}${planSummaryHtml(data.plan)}${goalHtml(data.goal)}${reviewHtml(data.review, data.nextReview)}${healthHtml(data.health, data.settings, data.screeners || [])}${answeredHtml(data.answered || [])}`;
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
