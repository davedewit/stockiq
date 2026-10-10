// AI autopilot for the practice portfolio (dashboard). FAKE MONEY ONLY: no real trade is ever placed.
// This file is only the controls and what the autopilot reports. The decisions are made by the stockiq-ai-trader
// Lambda on a schedule (or "Check in now"), which writes its practice buys and sells into the same practice
// portfolio that practice-portfolio.js shows. Shown only to users that Lambda allows.
// How the controls behave: EVERY change is saved by itself (the switch at once, typing after a short pause), so a
// refresh always shows what was last set. There is no save button; a line beside "Check in now" says
// "Saving…", "Saved" or why something could not be saved.
// What it shows keeps itself up to date: while the page is open it asks the Lambda again every minute (not while
// something is being typed or saved), and tells practice-portfolio.js when the autopilot has bought or sold.
(function () {
    const API = 'https://qy6s553i647agmxthtecc24fje0zskms.lambda-url.us-east-1.on.aws/';
    const CSS = `
        #practice-autopilot .ap-wrap { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--border-color); color: var(--text-primary); font-size: 0.9rem; }
        #practice-autopilot .ap-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
        #practice-autopilot .ap-head h3 { margin: 0; font-size: 1.15rem; color: var(--text-primary); }
        #practice-autopilot .ap-sub { font-size: 0.8rem; font-weight: normal; color: var(--text-secondary); }
        #practice-autopilot .ap-switch { display: inline-flex; align-items: center; gap: 10px; cursor: pointer; font-weight: 600; position: relative; }
        #practice-autopilot .ap-switch input { position: absolute; opacity: 0; width: 46px; height: 26px; margin: 0; cursor: pointer; right: 0; }
        #practice-autopilot .ap-track { width: 46px; height: 26px; border-radius: 13px; background: #9ca3af; position: relative; transition: background 0.15s; flex: none; }
        #practice-autopilot .ap-track::after { content: ''; position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.3); transition: left 0.15s; }
        #practice-autopilot .ap-switch input:checked + .ap-track { background: #22c55e; }
        #practice-autopilot .ap-switch input:checked + .ap-track::after { left: 23px; }
        #practice-autopilot .ap-switch input:focus-visible + .ap-track { outline: 2px solid #007bff; outline-offset: 2px; }
        #practice-autopilot .ap-intro { color: var(--text-secondary); font-size: 0.85rem; line-height: 1.5; margin: 8px 0 0; }
        #practice-autopilot .ap-status { margin-top: 12px; padding: 10px 12px; border-radius: 8px; background: var(--bg-secondary); border-left: 4px solid #9ca3af; color: var(--text-secondary); font-size: 0.85rem; line-height: 1.55; }
        #practice-autopilot .ap-status.on { border-left-color: #22c55e; }
        #practice-autopilot .ap-status strong { color: var(--text-primary); }
        #practice-autopilot .ap-card { border: 1px solid var(--border-color); border-radius: 8px; padding: 14px 16px; margin-top: 12px; }
        #practice-autopilot .ap-label { font-weight: 600; display: block; margin-bottom: 6px; color: var(--text-primary); }
        #practice-autopilot .ap-help { color: var(--text-secondary); font-size: 0.82rem; line-height: 1.45; margin-top: 6px; }
        #practice-autopilot .ap-risk { width: 100%; margin: 0; accent-color: #007bff; }
        #practice-autopilot .ap-levels { display: flex; font-size: 0.78rem; color: var(--text-secondary); margin-top: 2px; }
        #practice-autopilot .ap-levels span { flex: 1; text-align: center; cursor: pointer; padding: 2px 0; }
        #practice-autopilot .ap-levels span:first-child { text-align: left; }
        #practice-autopilot .ap-levels span:last-child { text-align: right; }
        #practice-autopilot .ap-levels span.now { color: var(--text-primary); font-weight: 700; }
        #practice-autopilot .ap-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px 18px; }
        #practice-autopilot .ap-input { display: flex; align-items: center; gap: 8px; color: var(--text-secondary); white-space: nowrap; }
        #practice-autopilot .ap-input input, #practice-autopilot .ap-input select { flex: 1; min-width: 0; width: 100%; box-sizing: border-box; padding: 9px 10px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px; }
        #practice-autopilot .ap-group { display: grid; grid-template-columns: 150px 1fr; gap: 6px 12px; align-items: start; padding: 9px 0; border-top: 1px solid var(--border-color); }
        #practice-autopilot .ap-group.first { border-top: none; padding-top: 2px; }
        #practice-autopilot .ap-group-name { color: var(--text-secondary); padding-top: 6px; }
        #practice-autopilot .ap-chips { display: flex; flex-wrap: wrap; gap: 6px 8px; }
        #practice-autopilot .ap-chip { display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border: 1px solid var(--border-color); border-radius: 16px; cursor: pointer; white-space: nowrap; user-select: none; color: var(--text-primary); }
        #practice-autopilot .ap-chip:has(input:checked) { border-color: #007bff; background: rgba(0, 123, 255, 0.12); }
        #practice-autopilot .ap-chip input { margin: 0; }
        #practice-autopilot .ap-chip small { color: var(--text-secondary); }
        #practice-autopilot .ap-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 14px; }
        #practice-autopilot .ap-btn { border-radius: 6px; padding: 9px 16px; font-size: 0.9rem; cursor: pointer; white-space: nowrap; border: 1px solid var(--border-color); background: none; color: var(--text-primary); }
        #practice-autopilot .ap-btn.primary { background: #007bff; border-color: #007bff; color: #fff; }
        #practice-autopilot .ap-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        #practice-autopilot .ap-saved { color: var(--text-secondary); font-size: 0.85rem; }
        #practice-autopilot .ap-saved.bad { color: #d97706; }
        #practice-autopilot .ap-note { margin-top: 10px; padding: 9px 12px; border-radius: 6px; font-size: 0.85rem; color: var(--text-primary); }
        #practice-autopilot .ap-note.good { background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.4); }
        #practice-autopilot .ap-note.bad { background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.4); }
        #practice-autopilot .ap-section { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border-color); font-size: 0.85rem; color: var(--text-secondary); }
        #practice-autopilot .ap-section h4 { margin: 0 0 6px; font-size: 0.95rem; color: var(--text-primary); }
        #practice-autopilot .ap-log { padding: 8px 0; border-bottom: 1px solid var(--border-color); line-height: 1.45; }
        #practice-autopilot .ap-log time { white-space: nowrap; margin-right: 6px; }
        #practice-autopilot .ap-log details, #practice-autopilot .ap-section details { margin-top: 4px; }
        #practice-autopilot .ap-log summary, #practice-autopilot .ap-section summary { cursor: pointer; color: var(--text-primary); font-size: 0.8rem; }
        #practice-autopilot .ap-log ul, #practice-autopilot .ap-section ul { margin: 4px 0 0 18px; padding: 0; }
        #practice-autopilot .ap-fresh { float: right; font-size: 0.8rem; font-weight: normal; color: var(--text-secondary); }
        #practice-autopilot .ap-fresh a { margin-left: 8px; }
        #practice-autopilot a { color: #3b82f6; }
        @media (max-width: 640px) { #practice-autopilot .ap-group { grid-template-columns: 1fr; } #practice-autopilot .ap-group-name { padding-top: 0; } #practice-autopilot .ap-chip { white-space: normal; } #practice-autopilot .ap-input { white-space: normal; } }
    `;

    let data = null, draft = null, working = '', notice = null, showAll = false;
    let saveTimer = null, saving = false, saveError = null, savedOnce = false, breakdownOpen = false;
    let loadedAt = null, refreshing = false, openDetails = {};       // openDetails: which "Details" are unfolded, kept across redraws
    const REFRESH_MS = 60000;
    const userId = () => { const u = localStorage.getItem('userId'); return u && u !== 'anonymous' ? u : null; };
    const box = () => document.getElementById('practice-autopilot');
    const byId = (id) => document.getElementById(id);
    const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const usd0 = (n) => '$' + Math.round(n).toLocaleString('en-US');
    const when = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }); };
    const day = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }); };
    const pc = (n) => (n === null || n === undefined) ? '–' : (n >= 0 ? '+' : '') + n.toFixed(1) + '%';
    const usd2 = (n) => (n < 0 ? '-' : '+') + '$' + Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const clock = (d) => d ? d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
    const fold = (key, title, lines) => lines && lines.length ? `<details data-ap-fold="${esc(key)}" ${openDetails[key] ? 'open' : ''}><summary>${esc(title)}</summary><ul>${lines.map(x => `<li>${esc(x)}</li>`).join('')}</ul></details>` : '';
    const tint = (n) => (n === null || n === undefined) ? 'var(--text-secondary)' : n >= 0 ? '#22c55e' : '#ef4444';
    const everyText = (v) => v === 24 ? 'once a day' : v === 12 ? 'twice a day' : v === 1 ? 'every hour' : v < 1 ? `every ${Math.round(v * 60)} minutes` : `every ${v} hours`;
    // a holding time given in days: 30 minutes, 3 hours, 5 days
    const holdText = (d) => { const h = d * 24; return h < 0.75 ? `${Math.round(h * 60)} minutes` : h < 23.5 ? `${Math.round(h)} hour${Math.round(h) === 1 ? '' : 's'}` : `${Math.round(d)} day${Math.round(d) === 1 ? '' : 's'}`; };
    let accepted = null;                          // what was last sent and saved (the server may tidy a value, e.g. round the budget)
    const isDirty = () => { if (!data || !draft) return false; const now = JSON.stringify(draft); return now !== JSON.stringify(data.settings) && now !== accepted; };

    function ensureStyle() {
        if (!document.head || !document.createElement || byId('ap-style')) return;
        const style = document.createElement('style');
        style.id = 'ap-style'; style.textContent = CSS;
        document.head.appendChild(style);
    }

    async function api(action, extra, keepalive) {
        const res = await fetch(API, { method: 'POST', keepalive: !!keepalive, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.assign({ action, userId: userId() }, extra || {})) });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.error || 'The autopilot could not be reached');
        return body;
    }

    // ---------------------------------------------------------------- wording, from the numbers the Lambda sends
    // A level's rules. For the level in use these are the rules in force, which the autopilot may have changed itself.
    function levelRules(level) {
        const r = data.options.risk[String(level)];
        return r && data.rules && String(data.settings.risk) === String(level) ? Object.assign({}, r, { stop: data.rules.stop, take: data.rules.take, top: data.rules.top, trail: data.rules.trail }) : r;
    }
    function riskText(level) {
        const r = levelRules(level);
        if (!r) return '';
        return `${r.name}: spreads the budget over up to ${r.positions} holdings, looks at the top ${r.top} of each screener, sells a holding at ${r.stop}% or +${r.take}%`
            + (r.crypto > 0 ? `, up to ${Math.round(r.crypto * 100)}% of the budget in coins.` : ', no coins.');
    }
    // How much of the budget is in use, check-in by check-in, when every check-in finds enough to buy and nothing is sold
    // early. The same sums as the stockiq-ai-trader Lambda: allowance() (the budget is released in equal steps over the
    // chosen days, rounded up to whole holdings), the time rule in review_sells() (5 minutes' grace) and, in run_user(),
    // at most 3 buys a check-in, no buy under $25 and the coin share. Keep the two in step.
    function buildUp(d, r, limit) {
        const size = d.budgetUsd / r.positions, every = d.everyHours, hold = d.maxHoldDays * 24 - 5 / 60;
        const last = Math.ceil(d.periodDays * 24 / every) + r.positions + 2;    // the budget fully released, then time to settle
        let lots = [], first = 0, peak = 0, count = 0, hours = 0;
        for (let n = 1; n <= last; n++) {
            lots = lots.filter(l => (n - l.n) * every < hold - 1e-9);
            let invested = lots.reduce((s, l) => s + l.usd, 0);
            const pace = d.budgetUsd * Math.min(1, n * every / (d.periodDays * 24));
            const cap = Math.min(d.budgetUsd, Math.ceil(pace / size - 1e-9) * size);
            const buys = Math.min(3, Math.floor((cap - invested + 0.005) / size));
            for (let i = 0; i < buys; i++) {
                const usd = Math.min(size, limit - invested);
                if (usd < 25) break;
                lots.push({ n, usd }); invested += usd;
                if (n === 1) first++;
            }
            if (invested > peak + 0.01) { peak = invested; count = lots.length; hours = (n - 1) * every; }
        }
        return { first, peak, count, hours };
    }
    // What the chosen settings mean in practice: every sentence is built from what is selected right now
    function planText(d) {
        const r = data.options.risk[String(d.risk)];
        if (!r || !(d.budgetUsd > 0) || !(d.periodDays > 0) || !(d.everyHours > 0) || !(d.maxHoldDays > 0)) return '';
        const cash = data.practiceCash || 100000, size = d.budgetUsd / r.positions, start = `It checks in ${everyText(d.everyHours)}.`;
        const coinsOnly = d.screeners.length > 0 && d.screeners.every(k => (data.options.screeners[k] || {}).kind === 'crypto');
        const limit = coinsOnly ? d.budgetUsd * r.crypto : d.budgetUsd, up = buildUp(d, r, limit);
        if (!up.count) return start + (coinsOnly && !(r.crypto > 0)
            ? ` Only coin screeners are ticked and the ${r.name} level buys no coins, so it will buy nothing. Tick a share screener, or move the level up.`
            : ` The ${r.name} level spreads the budget over ${r.positions} holdings, which makes each about ${usd0(size)}: under the $25 smallest buy, so it will buy nothing. Raise the budget.`);
        const quickest = Math.min.apply(null, data.options.everyHours), oftener = d.everyHours > quickest && d.maxHoldDays * 24 > quickest + 1e-9;   // would checking in more often let it hold more?
        const many = up.count === 1 ? '1 holding' : `${up.count} holdings`, whole = up.peak >= d.budgetUsd - 0.01, byCoins = !whole && up.peak >= limit - 0.01;
        const steps = up.hours <= 0 ? ', bought at the first check-in.'
            : `: ${up.first} at the first check-in` + (up.count - up.first === 1 ? ' and one more' : `, then more as the budget is released, all ${up.count}`) + ` after about ${holdText(up.hours / 24)}.`;
        return `${start} Up to ${many} of about ${usd0(size)} each${whole || byCoins ? '' : ' at a time'}${steps}`
            + (whole ? ` Then the whole ${usd0(d.budgetUsd)} is in use.`
                : byCoins ? ` That is ${usd0(up.peak)} of the ${usd0(d.budgetUsd)}: only coin screeners are ticked, and the ${r.name} level puts at most ${Math.round(r.crypto * 100)}% of the budget in coins. Tick a share screener as well, or move the level up, for it to use more.`
                : ` That is ${usd0(up.peak)} of the ${usd0(d.budgetUsd)}: it buys at most 3 at a check-in and sells each holding after ${holdText(d.maxHoldDays)}. Keep holdings longer${oftener ? ', or check in more often,' : ''} for it to use more.`)
            + (d.budgetUsd > cash ? ` The practice portfolio starts with ${usd0(cash)}, so it can never invest more than the cash that is left.` : '');
    }
    function paceText(d) {
        const r = levelRules(d.risk);
        if (!r || !(d.maxHoldDays > 0) || !(d.everyHours > 0)) return '';
        const late = d.maxHoldDays * 24 < d.everyHours - 1e-9, quick = d.everyHours < 3 || d.maxHoldDays < 1;
        const shares = d.screeners.some(k => (data.options.screeners[k] || {}).kind !== 'crypto');
        return `It sells a holding once it has had it for ${holdText(d.maxHoldDays)}, whatever the price, and sooner at ${r.stop}% or +${r.take}%, to keep part of a gain once it has been up ${r.take / 2}%, or when its screener signal turns negative or it slips far down the ranking. The money is then free for the next buy.`
            + (late ? ` It only checks in ${everyText(d.everyHours)}, though, so in practice a holding is sold at the next check-in, about ${holdText(d.everyHours / 24)} after it was bought. Check in more often for it to be sold on time.` : '')
            + (quick && shares ? ' Shares are only traded while their market is open and their rankings change little within a day, so quick settings mostly make a difference for coins.' : '')
            + (quick ? ' No trading costs are taken off here: real trading this often would lose part of every trade to fees.' : '');
    }
    function statusText() {
        const s = data.settings, last = data.state && data.state.lastRun;
        if (!s.enabled) return 'Off. Nothing is bought or sold automatically.';
        if (!s.screeners.length) return 'On, but no screener is chosen yet. Tick at least one below and it will start at the next check-in.';
        const r = data.options.risk[String(s.risk)] || {};
        const holding = data.holding ? ` Holding ${data.holding.count} of up to ${r.positions}: ${usd0(data.holding.investedUsd)} of the ${usd0(s.budgetUsd)} budget is invested.` : '';
        const next = data.nextCheck && data.nextCheck.at
            ? ` Next check-in about ${when(data.nextCheck.at)}, when the ${data.nextCheck.markets.join(' and ')} market${data.nextCheck.markets.length > 1 ? 's are' : ' is'} open.`
            : (data.nextCheck === null ? ' No check-in is due in the next ten days.' : '');
        return 'On.' + holding + (last ? ` Last check-in ${when(last)}.` : (next ? '' : ' First check-in at the next hourly check.')) + next;
    }
    // The line beside the button: whether what is on screen is saved, and what to do next
    function savedState() {
        if (saveError) return { text: 'Not saved: ' + saveError, bad: true };
        if (saving || saveTimer || isDirty()) return { text: 'Saving…', bad: false };
        const s = data.settings;
        const next = !s.enabled ? ' Use the switch at the top right to turn it on.' : !s.screeners.length ? ' Tick at least one screener for it to start.' : '';
        return { text: (savedOnce ? '✓ Saved.' : 'Changes are saved as you make them.') + next, bad: false };
    }
    function screenerGroups(all) {
        const groups = [];
        Object.keys(all).forEach(k => { const g = all[k].group || 'Screeners'; let row = groups.find(x => x[0] === g); if (!row) groups.push(row = [g, []]); row[1].push(k); });
        return groups;
    }

    // ---------------------------------------------------------------- "How it is doing": its own closed trades
    function recordHtml() {
        const c = data.scorecard, need = data.minSample || 8, plans = data.plans || [], on = data.settings.enabled;
        const held = plans.length
            ? `<div>Holding now: ${plans.map(p => `<strong style="color: var(--text-primary);">${esc(p.label)}</strong> (bought ${esc(when(p.boughtAt))}; ${on ? `it sells it at the check-in around ${esc(when(p.sellBy))} at the latest, sooner at ${p.stop}% or +${p.take}%` : 'the autopilot is off, so it stays until you sell it'})`).join('; ')}.</div>`
            : `<div>Holding nothing right now.</div>`;
        const m = data.month && data.month.last30, before = data.month && data.month.before30;
        const month = m && m.n ? `<div style="margin-top: 4px;">Last 30 days: <span style="color: ${tint(m.usd)}; font-weight: 600;">${usd2(m.usd)}</span> from ${m.n} finished trade${m.n === 1 ? '' : 's'} (${m.up} up)${m.pct !== null ? `, which is <span style="color: ${tint(m.pct)}; font-weight: 600;">${(m.pct >= 0 ? '+' : '') + m.pct.toFixed(2)}%</span> of the ${usd0(data.settings.budgetUsd)} budget` : ''}.${before && before.n ? ` The 30 days before: ${usd2(before.usd)} from ${before.n}${before.pct !== null ? ' (' + (before.pct >= 0 ? '+' : '') + before.pct.toFixed(2) + '%)' : ''}.` : ''}</div>` : '';
        if (!c || !c.n) return `<div class="ap-section"><h4>How it is doing</h4>${held}<div style="margin-top: 4px;">No finished trades yet: nothing it bought has been sold. Each sale will be listed here with its result, and the autopilot uses that record at later check-ins.</div></div>`;
        const cell = 'padding: 4px 8px; text-align: right; white-space: nowrap;';
        const row = (g) => `<tr><td style="padding: 4px 8px 4px 0; color: var(--text-primary);">${esc(g.label)}</td><td style="${cell}">${g.n}</td><td style="${cell} color: ${tint(g.avg)};">${pc(g.avg)}</td><td style="${cell}">${g.up} of ${g.n}</td><td style="${cell} color: ${tint(g.vs)};">${pc(g.vs)}</td></tr>`;
        const section = (title, list) => list && list.length ? `<tr><td colspan="5" style="padding: 8px 0 2px; color: var(--text-secondary);">${title}</td></tr>` + list.map(row).join('') : '';
        const g = c.groups || {};
        const lessons = data.lessons && data.lessons.items && data.lessons.items.length ? `<div style="margin-top: 10px;"><strong style="color: var(--text-primary); font-size: 0.9rem;">What it has noted from its record</strong> <span style="font-size: 0.8rem;">(written by the AI model on ${esc(day(data.lessons.at))} from ${data.lessons.n} finished trades)</span><ul style="margin: 4px 0 0 18px; padding: 0;">${data.lessons.items.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : '';
        return `<div class="ap-section"><h4>How it is doing</h4>
            ${held}${month}
            <div style="margin-top: 4px;">${c.n} finished trade${c.n === 1 ? '' : 's'} in all: ${c.up} up, ${c.n - c.up} down or level, average <span style="color: ${tint(c.avg)}; font-weight: 600;">${pc(c.avg)}</span> each.${c.n < need ? ` Fewer than ${need} trades: too few to conclude anything yet.` : ''}</div>
            <details id="ap-breakdown" ${breakdownOpen ? 'open' : ''} style="margin-top: 6px;"><summary>Breakdown</summary><div style="overflow-x: auto;"><table style="border-collapse: collapse; font-size: 0.85rem;">
                <tr><td></td><td style="${cell}">Trades</td><td style="${cell}">Average</td><td style="${cell}">Up</td><td style="${cell}" title="The average result minus what an S&amp;P 500 index fund did over the same time">Against an index fund</td></tr>
                ${section('By screener', g.screener)}${section('By place in the ranking when bought', g.rank)}${section('By RSI when bought', g.rsi)}${section('By who chose', g.chosen)}${section('By how it was sold', g.exit)}
            </table></div><div style="font-size: 0.8rem; margin-top: 4px;">A group needs ${need} trades before the autopilot acts on it. A screener whose recent trades clearly lag an S&amp;P 500 index fund is rested for two weeks. Past results of fake-money trades; they say nothing certain about the future.</div></details>
            ${lessons}
        </div>`;
    }

    // ---------------------------------------------------------------- "Improving its own rules": what it has changed, is trying, has tried
    function ruleWords(r) {
        return `sells at ${r.stop}% or +${r.take}%; once a holding has been up ${r.arm}%, sells if it gives back ${Math.round(r.trail * 100)}% of its best gain; buys from the top ${r.top} of a ranking` + (r.max_rsi >= 100 ? '' : ` with RSI under ${r.max_rsi}`);
    }
    function tuneHtml() {
        const t = data.tune, r = data.rules;
        if (!t || !r) return '';
        const names = { stop: 'loss limit', take: 'gain mark', trail: 'share of a gain it gives back', top: 'how far down a ranking it buys', max_rsi: 'RSI limit' };
        const changed = Object.keys(r.changed || {});
        const trial = t.trial, group = t.group || 10;
        const side = (n, avg) => `${n} finished${n ? ' (average ' + pc(avg) + ')' : ''}`;
        const now = trial
            ? `<div style="margin-top: 6px;"><strong style="color: var(--text-primary);">Trying now</strong> (since ${esc(day(trial.since))}): ${esc(trial.text)}. Why: ${esc(trial.why)}. ${esc(trial.how)} So far: with the change ${side(trial.with, trial.avgWith)}, without it ${side(trial.without, trial.avgWithout)}. It decides after ${group} each way and keeps the change only if that group did clearly better.</div>`
            : `<div style="margin-top: 6px;">${t.nextReviewIn === 0 ? 'It reviews its rules at the next sale.' : `Next review of its rules after ${t.nextReviewIn} more finished trade${t.nextReviewIn === 1 ? '' : 's'}`}${t.nextReviewIn === 0 ? '' : ` (it reviews them every ${t.batch}).`} If the record suggests a change worth trying, it tries it beside the current rule over the same days.</div>`;
        const verdicts = { kept: 'kept', dropped: 'not kept', stopped: 'stopped' };
        const past = (t.past || []).slice().reverse();
        return `<div class="ap-section"><h4>Improving its own rules</h4>
            <div>Its rules now (${esc(r.name)} level): ${esc(ruleWords(r))}.${changed.length ? ` Changed by itself after a trial: ${esc(changed.map(k => names[k] + ' (the level starts at ' + r.changed[k] + ')').join(', '))}.` : ''}</div>
            ${now}
            ${past.length ? fold('past-trials', `Earlier trials (${past.length})`, past.map(p => `${day(p.since)} to ${day(p.ended)}: ${p.text}: ${verdicts[p.verdict] || p.verdict}. ${p.result ? p.result.charAt(0).toUpperCase() + p.result.slice(1) + '.' : ''}`)) : ''}
            <div style="font-size: 0.8rem; margin-top: 6px;">It can only change these five rules, inside fixed limits, for its own fake-money trades. It never changes your settings, the budget or anything else on the site. Each review is emailed to your account address.</div>
        </div>`;
    }

    // ---------------------------------------------------------------- the panel
    function render() {
        const el = box();
        if (!el) return;
        if (!data || !data.allowed) { el.innerHTML = ''; return; }
        ensureStyle();
        const breakdown = byId('ap-breakdown');
        if (breakdown && typeof breakdown.open === 'boolean') breakdownOpen = breakdown.open;
        if (document.querySelectorAll) Array.from(document.querySelectorAll('[data-ap-fold]')).forEach(x => { if (typeof x.open === 'boolean') openDetails[x.getAttribute('data-ap-fold')] = x.open; });
        const d = draft, o = data.options, on = data.settings.enabled, ready = on && data.settings.screeners.length > 0, state = savedState();
        const select = (id, list, value, label) => `<select id="${id}">${list.map(v => `<option value="${v}" ${v === value ? 'selected' : ''}>${label(v)}</option>`).join('')}</select>`;
        const icons = { buy: '🟢', sell: '🔴', note: 'ℹ️' };
        const log = (data.log || []).slice().reverse();
        const shown = showAll ? log : log.slice(0, 8);
        const levels = Object.keys(o.risk).sort();
        const chosen = d.screeners.length;
        el.innerHTML = `
            <div class="ap-wrap">
                <div class="ap-head">
                    <h3>🤖 AI autopilot <span class="ap-sub">fake money, an experiment to watch</span></h3>
                    <label class="ap-switch" title="Switch the autopilot on or off. This is saved straight away."><span id="ap-switch-text">${d.enabled ? 'On' : 'Off'}</span><input id="ap-enabled" type="checkbox" ${d.enabled ? 'checked' : ''} ${working ? 'disabled' : ''}><span class="ap-track"></span></label>
                </div>
                <p class="ap-intro">An AI model makes practice buys and sells for you from the latest results of the screeners you choose, inside the limits you set here. It uses the practice portfolio above. Nothing here is advice, and past screener results have not shown a reliable edge.</p>
                <div id="ap-status" class="ap-status ${on ? 'on' : ''}">${esc(statusText())}</div>

                <div class="ap-card">
                    <span class="ap-label">Risk level</span>
                    <input id="ap-risk" class="ap-risk" type="range" min="1" max="${levels.length || 5}" step="1" value="${d.risk}" aria-label="Risk level">
                    <div class="ap-levels">${levels.map(n => `<span data-ap-level="${n}" class="${String(d.risk) === n ? 'now' : ''}">${esc(o.risk[n].name)}</span>`).join('')}</div>
                    <div id="ap-risk-text" class="ap-help">${esc(riskText(d.risk))}</div>
                </div>

                <div class="ap-card">
                    <div class="ap-fields">
                        <div><label class="ap-label" for="ap-budget">Budget for the AI</label><div class="ap-input">$ <input id="ap-budget" type="number" min="100" step="500" value="${d.budgetUsd}"></div></div>
                        <div><label class="ap-label" for="ap-period">Build up to it over</label><div class="ap-input"><input id="ap-period" type="number" min="1" max="90" step="1" value="${d.periodDays}"> days</div></div>
                        <div><label class="ap-label" for="ap-every">Checks in</label><div class="ap-input">${select('ap-every', o.everyHours, d.everyHours, everyText)}</div></div>
                        <div><label class="ap-label" for="ap-hold">Keeps a holding at most</label><div class="ap-input">${select('ap-hold', o.holdDays, d.maxHoldDays, holdText)}</div></div>
                    </div>
                    <div id="ap-plan" class="ap-help">${esc(planText(d))}</div>
                    <div id="ap-pace" class="ap-help">${esc(paceText(d))}</div>
                </div>

                <div class="ap-card">
                    <span class="ap-label">Screeners it buys from <span id="ap-chosen" class="ap-sub">${chosen} chosen</span></span>
                    ${screenerGroups(o.screeners).map(([group, keys], i) => `<div class="ap-group ${i === 0 ? 'first' : ''}"><div class="ap-group-name">${esc(group)}</div><div class="ap-chips">${keys.map(k => `<label class="ap-chip"><input type="checkbox" data-ap-screener="${esc(k)}" ${d.screeners.includes(k) ? 'checked' : ''}> ${esc(o.screeners[k].name)}${data.resting && data.resting[k] ? ' <small title="Resting after its recent trades lagged the market">(resting until ' + esc(day(data.resting[k])) + ')</small>' : ''}</label>`).join('')}</div></div>`).join('')}
                    <div class="ap-help">Each share market is only traded while it is open; coins at any time. Bigger lists take a little longer to check.</div>
                </div>

                <div class="ap-actions">
                    <button id="ap-run" data-ap="run" class="ap-btn ${ready ? 'primary' : ''}" ${working || !ready || state.text === 'Saving…' ? 'disabled' : ''} title="${!on ? 'Switch the autopilot on first' : !ready ? 'Tick at least one screener first' : 'Runs one check-in now instead of waiting for the next one'}">${working === 'run' ? 'Checking in… this can take up to a minute' : 'Check in now'}</button>
                    <span id="ap-saved" class="ap-saved ${state.bad ? 'bad' : ''}">${esc(state.text)}</span>
                </div>
                <div id="ap-notice" class="${notice ? 'ap-note ' + (notice.bad ? 'bad' : 'good') : ''}" role="status">${notice ? esc(notice.text) : ''}</div>

                ${recordHtml()}
                ${tuneHtml()}
                <div class="ap-section"><h4>What it has done <span class="ap-fresh"><span id="ap-fresh">${loadedAt ? 'Up to date at ' + esc(clock(loadedAt)) + '. Refreshes by itself every minute.' : ''}</span><a href="#" data-ap="refresh">↻ Refresh now</a></span></h4>
                    ${log.length ? shown.map(e => `<div class="ap-log"><time>${icons[e.type] || ''} ${esc(when(e.t))}</time> ${e.type === 'buy' ? `<strong style="color: var(--text-primary);">Bought ${esc(e.symbol)}</strong> with ${usd0(e.usd)}. ` : e.type === 'sell' ? `<strong style="color: var(--text-primary);">Sold ${esc(e.symbol)}</strong>${typeof e.pct === 'number' ? ` <span style="color: ${tint(e.pct)}; font-weight: 600;">${pc(e.pct)}</span>` : ''}. ` : ''}${esc(e.text)}${e.n > 1 ? ` <span style="font-size: 0.8rem;">(the same at ${e.n} check-ins in a row, since ${esc(when(e.first))})</span>` : ''}${fold(e.type + e.t + e.symbol, e.type === 'sell' ? 'Why, and the details' : 'The plan for it', e.detail)}</div>`).join('') : '<div>Nothing yet. Its buys, sells and check-ins will be listed here.</div>'}
                    ${log.length > shown.length ? `<a href="#" data-ap="more" style="display: inline-block; margin-top: 8px;">Show all ${log.length}</a>` : ''}</div>
            </div>`;
    }

    function readDraft() {
        if (!byId('ap-risk')) return;
        draft = {
            enabled: !!byId('ap-enabled').checked, risk: parseInt(byId('ap-risk').value, 10) || 3,
            budgetUsd: parseFloat(byId('ap-budget').value) || 0, periodDays: parseInt(byId('ap-period').value, 10) || 1,
            everyHours: parseFloat(byId('ap-every').value), maxHoldDays: parseFloat(byId('ap-hold').value),
            screeners: Array.from(document.querySelectorAll('[data-ap-screener]')).filter(c => c.checked).map(c => c.getAttribute('data-ap-screener')).sort()
        };
    }
    // Bring the button, the "saved" line and the explanatory lines up to date without redrawing (typing keeps its place)
    function syncDraft() {
        readDraft();
        if (!draft || !data) return;
        const on = data.settings.enabled, ready = on && data.settings.screeners.length > 0, state = savedState(), set = (id, fn) => { const el = byId(id); if (el) fn(el); };
        set('ap-run', el => { el.disabled = !!working || !ready || state.text === 'Saving…'; el.title = !on ? 'Switch the autopilot on first' : !ready ? 'Tick at least one screener first' : 'Runs one check-in now instead of waiting for the next one'; if (el.classList) el.classList.toggle('primary', ready); });
        set('ap-saved', el => { el.textContent = state.text; if (el.classList) el.classList.toggle('bad', state.bad); });
        set('ap-status', el => { el.textContent = statusText(); if (el.classList) el.classList.toggle('on', on); });
        set('ap-switch-text', el => { el.textContent = draft.enabled ? 'On' : 'Off'; });
        set('ap-risk-text', el => { el.textContent = riskText(draft.risk); });
        set('ap-plan', el => { el.textContent = planText(draft); });
        set('ap-pace', el => { el.textContent = paceText(draft); });
        set('ap-chosen', el => { el.textContent = draft.screeners.length + ' chosen'; });
        if (document.querySelectorAll) Array.from(document.querySelectorAll('[data-ap-level]')).forEach(el => { if (el.classList) el.classList.toggle('now', el.getAttribute('data-ap-level') === String(draft.risk)); });
    }
    function validate(d) {
        const cash = data.practiceCash || 100000;
        if (!(d.budgetUsd >= 100)) throw new Error('the budget must be at least $100.');
        if (d.budgetUsd > cash * 10) throw new Error(`the budget cannot be more than ${usd0(cash * 10)}.`);
        if (!(d.periodDays >= 1 && d.periodDays <= 90)) throw new Error('spread the buying over 1 to 90 days.');
    }
    // Is the user in the middle of typing or dragging in the panel? Then the panel is updated in place, not redrawn.
    function editing() {
        const el = document.activeElement;
        return !!el && typeof el.id === 'string' && ['ap-budget', 'ap-period', 'ap-risk'].includes(el.id);
    }
    function queueSave(delay) {
        if (saveTimer) clearTimeout(saveTimer);
        saveTimer = setTimeout(() => { saveTimer = null; flush(); }, delay);
        syncDraft();
    }
    // Save what is on screen now. Each change is saved by itself; if more changes arrive meanwhile they are saved next.
    async function flush(leaving) {
        if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
        if (!data || !data.allowed) return;
        readDraft();
        if (!isDirty()) { syncDraft(); return; }
        if (saving) return;                               // the save in flight will pick the rest up when it lands
        try { validate(draft); } catch (e) { saveError = e.message; syncDraft(); return; }
        saving = true; saveError = null; syncDraft();
        const sent = JSON.stringify(draft), wasOn = data.settings.enabled;
        try {
            const result = await api('save', { settings: draft }, leaving);
            const unchangedSince = JSON.stringify(draft) === sent;
            data = result; loadedAt = new Date(); sharePlans();
            if (unchangedSince) draft = JSON.parse(JSON.stringify(result.settings));
            savedOnce = true; accepted = sent;
            const on = data.settings.enabled;
            if (on !== wasOn) notice = { text: on ? (data.settings.screeners.length ? 'Autopilot switched on. Press "Check in now" to see its first choices, or leave it to check in by itself.' : 'Autopilot switched on. Tick at least one screener below for it to start.')
                : 'Autopilot switched off. What it holds stays in the practice portfolio until you sell it.' };
        } catch (e) { saveError = e.message; }
        saving = false;
        if (!saveError && isDirty()) { queueSave(300); return; }
        if (editing()) syncDraft(); else render();
    }
    function take(result) { data = result; draft = JSON.parse(JSON.stringify(result.settings)); accepted = null; loadedAt = new Date(); sharePlans(); }
    // practice-portfolio.js marks the autopilot's holdings with when and at what they will be sold
    function sharePlans() { if (data && data.allowed && window.practicePortfolio && window.practicePortfolio.setPlans) window.practicePortfolio.setPlans(data.plans || []); }
    // What changes when the autopilot acts: its activity list and what it holds
    const stamp = (r) => JSON.stringify([r.log && r.log.length, r.log && r.log.slice(-1), r.plans, r.state, r.tune, r.scorecard && r.scorecard.n]);
    // Ask again without disturbing anything: not while a change is being typed, saved or run
    async function refresh(byHand) {
        if (!data || !data.allowed || refreshing || working || saving || saveTimer || isDirty() || (editing() && !byHand)) return;
        if (!byHand && document.visibilityState === 'hidden') return;
        refreshing = true;
        try {
            const r = await api('get');
            if (r.allowed && !working && !saving && !saveTimer && !isDirty()) {
                const traded = JSON.stringify([r.plans, r.scorecard && r.scorecard.n]) !== JSON.stringify([data.plans, data.scorecard && data.scorecard.n]);
                const changed = stamp(r) !== stamp(data) || JSON.stringify(r.settings) !== JSON.stringify(data.settings);
                take(r);
                if (changed || byHand) { if (editing()) syncDraft(); else render(); } else { const f = byId('ap-fresh'); if (f) f.textContent = 'Up to date at ' + clock(loadedAt) + '. Refreshes by itself every minute.'; }
                if (traded && window.practicePortfolio && window.practicePortfolio.reload) window.practicePortfolio.reload();
            }
        } catch (e) { if (byHand) { notice = { text: 'Could not refresh: ' + e.message, bad: true }; render(); } }
        refreshing = false;
    }

    async function load() {
        if (!userId() || !box()) return;
        try { const r = await api('get'); if (r.allowed) take(r); else data = r; } catch (e) { data = null; }
        render();
    }
    async function act(kind, task) {
        if (working) return;
        await flush();                                    // anything just changed is saved first
        if (saveError || isDirty()) { render(); return; }
        working = kind; notice = null; render();
        try { await task(); } catch (e) { notice = { text: e.message, bad: true }; }
        working = ''; render();
    }

    document.addEventListener('click', (e) => {
        const level = e.target.closest && e.target.closest('[data-ap-level]');
        if (level && data && byId('ap-risk')) { byId('ap-risk').value = level.getAttribute('data-ap-level'); saveError = null; queueSave(150); return; }
        const t = e.target.closest && e.target.closest('[data-ap]');
        if (!t || !data) return;
        if (t.tagName === 'A') e.preventDefault();
        const action = t.getAttribute('data-ap');
        if (action === 'more') { readDraft(); showAll = true; render(); }
        else if (action === 'refresh') refresh(true);
        else if (action === 'run') {
            act('run', async () => {
                const r = await api('run');
                take(r);
                const s = r.summary || {};
                notice = { text: s.conflict ? 'The portfolio was being changed at the same time, so nothing was traded. Try again.' : `Checked in: ${s.bought || 0} bought, ${s.sold || 0} sold. Details are listed below.` };
                if (window.practicePortfolio && window.practicePortfolio.reload) window.practicePortfolio.reload();
            });
        }
    });
    const changed = (e) => {
        if (!e.target || !data || !data.allowed) return;
        const id = e.target.id || '', inPanel = id.indexOf('ap-') === 0 || (e.target.getAttribute && e.target.getAttribute('data-ap-screener'));
        if (!inPanel) return;
        saveError = null;
        if (id === 'ap-enabled') { if (e.type === 'change') flush(); return; }           // the switch saves at once
        queueSave(e.type === 'change' ? 150 : 900);                                      // ticks and menus quickly; typing after a pause
    };
    document.addEventListener('input', changed);
    document.addEventListener('change', changed);

    // Leaving the page with a change still waiting: send it now
    const leaving = () => { if (data && data.allowed && (saveTimer || isDirty())) flush(true); };
    if (typeof window !== 'undefined' && window.addEventListener) window.addEventListener('pagehide', leaving);
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') leaving(); });

    if (typeof setInterval === 'function') setInterval(() => refresh(false), REFRESH_MS);
    window.practiceAutopilot = { reload: load, flush, refresh };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load); else load();
})();
