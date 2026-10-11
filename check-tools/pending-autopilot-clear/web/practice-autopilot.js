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
        #practice-autopilot .ap-wrap { color: var(--text-primary); font-size: 0.9rem; }
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
        #practice-autopilot .ap-mini { display: inline-flex; align-items: center; gap: 6px; margin-left: 12px; cursor: pointer; position: relative; color: var(--text-primary); }
        #practice-autopilot .ap-mini input { position: absolute; opacity: 0; width: 32px; height: 18px; margin: 0; cursor: pointer; left: 0; }
        #practice-autopilot .ap-mini .ap-dot { width: 32px; height: 18px; border-radius: 9px; background: #9ca3af; position: relative; transition: background 0.15s; flex: none; }
        #practice-autopilot .ap-mini .ap-dot::after { content: ''; position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%; background: #fff; transition: left 0.15s; }
        #practice-autopilot .ap-mini input:checked + .ap-dot { background: #22c55e; }
        #practice-autopilot .ap-mini input:checked + .ap-dot::after { left: 16px; }
        #practice-autopilot .ap-mini input:focus-visible + .ap-dot { outline: 2px solid #3b82f6; outline-offset: 2px; }
        #practice-autopilot a { color: #3b82f6; }
        #practice-autopilot .ap-views { display: flex; gap: 6px; margin-top: 16px; border-bottom: 1px solid var(--border-color); }
        #practice-autopilot .ap-view { padding: 9px 16px; border: 0; border-bottom: 3px solid transparent; margin-bottom: -1px; background: none; color: var(--text-secondary); font-size: 0.95rem; font-weight: 600; cursor: pointer; }
        #practice-autopilot .ap-view:hover { color: var(--text-primary); }
        #practice-autopilot .ap-view.now { color: #007bff; border-bottom-color: #007bff; }
        #practice-autopilot .ap-pane > .ap-section:first-child { border-top: 0; margin-top: 6px; }
        #practice-autopilot .ap-presets { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-top: 12px; font-size: 0.85rem; color: var(--text-secondary); }
        #practice-autopilot .ap-preset { padding: 6px 12px; border: 1px solid var(--border-color); border-radius: 16px; background: var(--bg-secondary); color: var(--text-primary); cursor: pointer; font-size: 0.85rem; }
        #practice-autopilot .ap-preset:hover { border-color: #3b82f6; }
        #practice-autopilot .ap-own { display: flex; gap: 8px 18px; flex-wrap: wrap; align-items: center; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border-color); font-size: 0.85rem; color: var(--text-secondary); }
        #practice-autopilot .ap-own strong { color: var(--text-primary); }
        #practice-autopilot .ap-own input { width: 70px; padding: 6px 8px; margin: 0 4px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px; }
        #practice-autopilot .ap-auto { font-size: 0.75rem; font-weight: normal; color: #22c55e; margin-left: 6px; }
        #practice-autopilot .ap-auto.own { color: var(--text-secondary); }
        #practice-autopilot .ap-may { display: block; padding: 6px 0; cursor: pointer; }
        #practice-autopilot .ap-may input { margin-right: 8px; }
        #practice-autopilot .ap-may small { display: block; margin-left: 24px; color: var(--text-secondary); font-size: 0.8rem; }
        @media (max-width: 640px) { #practice-autopilot .ap-group { grid-template-columns: 1fr; } #practice-autopilot .ap-group-name { padding-top: 0; } #practice-autopilot .ap-chip { white-space: normal; } #practice-autopilot .ap-input { white-space: normal; } }
    `;

    let data = null, draft = null, working = '', notice = null, showAll = false;
    let saveTimer = null, saving = false, saveError = null, savedOnce = false, breakdownOpen = false;
    // The activity list: everything, or only buys and sells. A way of looking at the list, not a setting of the autopilot:
    // it is remembered in this browser (localStorage), so a refresh keeps it.
    const VIEW_KEY = 'stockiqAutopilotTradesOnly';
    const remembered = () => { try { return localStorage.getItem(VIEW_KEY) === '1'; } catch (e) { return false; } };
    const remember = (on) => { try { localStorage.setItem(VIEW_KEY, on ? '1' : '0'); } catch (e) {} };
    let tradesOnly = remembered();
    // The panel is in two parts so that neither is a long scroll: "Activity" (what it holds, how it is doing, what it has
    // done) and "Settings". Both are always in the page; one is shown. The choice is remembered in this browser.
    const PART_KEY = 'stockiqAutopilotPart';
    let part = null;                                                // 'activity' | 'settings'; decided at the first draw
    const rememberedPart = () => { try { const v = localStorage.getItem(PART_KEY); return v === 'activity' || v === 'settings' ? v : null; } catch (e) { return null; } };
    function showPart(name, keep) {
        part = name === 'settings' ? 'settings' : 'activity';
        if (keep) { try { localStorage.setItem(PART_KEY, part); } catch (e) {} }
        ['activity', 'settings'].forEach(n => {
            const pane = byId('ap-pane-' + n), tab = byId('ap-view-' + n);
            if (pane && pane.style) pane.style.display = n === part ? '' : 'none';
            if (tab && tab.classList) tab.classList.toggle('now', n === part);
        });
    }
    // Quick set-ups: one press fills in the fields (never the budget or the on/off switch); anything can be changed afterwards
    const PRESETS = [
        { key: 'coins', name: '⚡ Quick coin trading', title: 'Coins only, checked every 30 minutes, each kept at most 6 hours, the whole budget in use within a day', set: { risk: 4, periodDays: 1, everyHours: 0.5, maxHoldDays: 0.25, screeners: ['7-1'] } },
        { key: 'shares', name: '🏛 Steady shares', title: 'S&P 100 shares, checked once a day, each kept at most 20 days, the budget built up over 10 days', set: { risk: 3, periodDays: 10, everyHours: 24, maxHoldDays: 20, screeners: ['3-100'] } },
        { key: 'mix', name: '🔀 Shares and coins', title: 'S&P 100 shares and coins, checked every 6 hours, each kept at most 5 days, the budget built up over 5 days', set: { risk: 3, periodDays: 5, everyHours: 6, maxHoldDays: 5, screeners: ['3-100', '7-1'] } }
    ];
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
    // A level's rules without the user's own limits: the level's own, with what the autopilot has changed itself for the level in use
    function autoRules(level) {
        const r = data.options.risk[String(level)];
        if (!r || !data.rules || String(data.settings.risk) !== String(level)) return r;
        return Object.assign({}, r, { top: data.rules.top, trail: data.rules.trail }, data.rules.level || { stop: data.rules.stop, take: data.rules.take });
    }
    // what an empty "your own limit" field falls back to, shown in grey inside it
    function hint(level, key) { const r = autoRules(level), n = r ? Math.abs(r[key]) : NaN; return isFinite(n) ? String(n) : ''; }
    // ... and with the user's own loss limit and gain mark, as they stand on screen: these come before everything else
    function levelRules(level) {
        const r = autoRules(level), d = draft || data.settings;
        if (!r) return r;
        return Object.assign({}, r, d.stopPct > 0 ? { stop: -d.stopPct } : {}, d.takePct > 0 ? { take: d.takePct } : {});
    }
    // The pace a level sets when the three pace fields are left to it ("Automatic"): days to build up, hours between check-ins,
    // days a holding is kept. PACE in the stockiq-ai-trader Lambda, sent as options.pace.
    function paceOf(level) { return (data.options.pace || {})[String(level)] || null; }
    const PACE_FIELDS = ['periodDays', 'everyHours', 'maxHoldDays'];
    const isAuto = (d, key) => Array.isArray(d.auto) && d.auto.includes(key);
    function paceWords(level) {
        const p = paceOf(level);
        return p ? ` Left to the level, it builds the budget up over ${p.periodDays} day${p.periodDays === 1 ? '' : 's'}, checks in ${everyText(p.everyHours)} and keeps a holding at most ${holdText(p.maxHoldDays)}.` : '';
    }
    function riskText(level) {
        const r = levelRules(level);
        if (!r) return '';
        return `${r.name}: spreads the budget over up to ${r.positions} holdings, looks at the top ${r.top} of each screener, sells a holding at ${r.stop}% or +${r.take}%`
            + (r.crypto >= 1 ? ', coins up to the whole budget.' : r.crypto > 0 ? `, up to ${Math.round(r.crypto * 100)}% of the budget in coins (the whole budget if only coin screeners are ticked).` : ', coins only if nothing but coin screeners is ticked.')
            + paceWords(level);
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
        const up = buildUp(d, r, d.budgetUsd);            // with only coin screeners ticked the whole budget may go into coins (coin_share in the Lambda)
        if (!up.count) return start + ` The ${r.name} level spreads the budget over ${r.positions} holdings, which makes each about ${usd0(size)}: under the $25 smallest buy, so it will buy nothing. Raise the budget.`;
        const quickest = Math.min.apply(null, data.options.everyHours), oftener = d.everyHours > quickest && d.maxHoldDays * 24 > quickest + 1e-9;   // would checking in more often let it hold more?
        const many = up.count === 1 ? '1 holding' : `${up.count} holdings`, whole = up.peak >= d.budgetUsd - 0.01;
        const steps = up.hours <= 0 ? ', bought at the first check-in.'
            : `: ${up.first} at the first check-in` + (up.count - up.first === 1 ? ' and one more' : `, then more as the budget is released, all ${up.count}`) + ` after about ${holdText(up.hours / 24)}.`;
        return `${start} Up to ${many} of about ${usd0(size)} each${whole ? '' : ' at a time'}${steps}`
            + (whole ? ` Then the whole ${usd0(d.budgetUsd)} is in use.`
                : ` That is ${usd0(up.peak)} of the ${usd0(d.budgetUsd)}: it buys at most 3 at a check-in and sells each holding after ${holdText(d.maxHoldDays)}. Keep holdings longer${oftener ? ', or check in more often,' : ''} for it to use more.`)
            + (mixed(d) && r.crypto < 1 ? ` Of that, at most ${Math.round(r.crypto * 100)}% (${usd0(d.budgetUsd * r.crypto)}) goes into coins at this level.` : '')
            + (d.everyHours <= 3 && d.screeners.some(k => (data.options.screeners[k] || {}).kind === 'crypto') ? ' A coin is only bought once it has been near the top at two check-ins running (coin rankings change fast and many drop out again within the hour), so coin buying starts one check-in later than this.' : '')
            + (d.budgetUsd > cash ? ` The practice portfolio starts with ${usd0(cash)}, so it can never invest more than the cash that is left.` : '');
    }
    // shares and coins both ticked? Then the level's coin share applies
    function mixed(d) {
        const kinds = d.screeners.map(k => (data.options.screeners[k] || {}).kind);
        return kinds.includes('crypto') && kinds.some(k => k !== 'crypto');
    }
    // The stop that follows a holding: the user's choice (settings.trailMode; TRAIL_MODES in the stockiq-ai-trader Lambda)
    const TRAILS = {
        gains: { name: 'Protects a gain (starts once a holding has risen)', says: 'when a stop that follows a rising holding is hit (a holding that keeps rising is kept: the stop starts once it has risen beyond its own normal wobble and sells only if it then falls back; how far it may fall is set from how much that holding normally moves: more for a jumpy coin, less when its screener figures weaken or time is short)',
                 help: 'The stop only starts once a holding has risen beyond its normal wobble; from then on it follows the price up and sells if it slips back too far. A holding that just drifts down is left to the loss limit, the time limit and its screener figures.' },
        full: { name: 'From the moment it is bought (a full trailing stop loss)', says: 'when its trailing stop is hit (the stop sits under the price from the moment of buying and follows it up, selling only on a fall-back; how far it may fall is set from how much that holding normally moves: more for a jumpy coin, less when its screener figures weaken or time is short)',
                help: 'The stop sits under the price from the moment of buying and follows it up, so a holding that falls is cut early as well. It loses less on a faller, but ordinary dips will shake it out more often.' },
        off: { name: 'Off', says: '', help: 'Nothing follows the price. It sells only at your loss limit and gain mark, at the time limit, and when its screener figures turn.' }
    };
    const trailOf = (d) => TRAILS[d.trailMode] ? d.trailMode : 'gains';
    function paceText(d) {
        const r = levelRules(d.risk);
        if (!r || !(d.maxHoldDays > 0) || !(d.everyHours > 0)) return '';
        const late = d.maxHoldDays * 24 < d.everyHours - 1e-9, quick = d.everyHours < 3 || d.maxHoldDays < 1;
        const shares = d.screeners.some(k => (data.options.screeners[k] || {}).kind !== 'crypto');
        return `It sells a holding once it has had it for ${holdText(d.maxHoldDays)}, whatever the price, and sooner at ${r.stop}% or +${r.take}%${TRAILS[trailOf(d)].says ? ', ' + TRAILS[trailOf(d)].says + ',' : ''} or when its screener signal turns negative or it slips far down the ranking. The money is then free for the next buy. At every check-in the AI model also reviews each holding against the latest screener figures and recent headlines, and may sell it earlier than these rules.`
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
            ? `<div>Holding now: ${plans.map(p => `<strong style="color: var(--text-primary);">${esc(p.label)}</strong> (bought ${esc(when(p.boughtAt))}; ${on ? `it sells it at the check-in around ${esc(when(p.sellBy))} at the latest, sooner at ${p.stop}% or +${p.take}%` : 'the autopilot is off, so it stays until you sell it'}${on && p.mode === 'full' && typeof p.floor === 'number' && !(p.peak >= p.arm) ? `; its trailing stop is at ${pc(p.floor)} and follows the price up` : on && typeof p.floor === 'number' ? `; it has been up ${pc(p.peak)} at its best and is sold if it slips back to ${pc(p.floor)}` : on && p.mode === 'off' ? '; no stop follows it' : on && typeof p.arm === 'number' ? `; while it rises it is kept, and once it has been up ${p.arm}% a stop follows it up and sells only on a fall-back` : ''}${on && typeof p.move === 'number' ? ` (it normally moves about ${p.move.toFixed(1)}% between check-ins and may slip ${p.room} such moves from its best${p.tight ? '; the AI review asked for a tighter stop' : ''})` : ''}${on && p.view ? `; the AI model's latest review, ${esc(when(p.view.t))}${p.view.larger ? ', by the larger model' : ''}: ${p.view.sell ? 'sell' : p.view.tighten ? 'keep, with a tighter stop' : 'keep'} (${esc(p.view.text)})` : ''})`).join('; ')}.</div>`
            : `<div>Holding nothing right now.</div>`;
        const m = data.month && data.month.last30, before = data.month && data.month.before30;
        const month = m && m.n ? `<div style="margin-top: 4px;">Last 30 days: <span style="color: ${tint(m.usd)}; font-weight: 600;">${usd2(m.usd)}</span> from ${m.n} finished trade${m.n === 1 ? '' : 's'} (${m.up} up)${m.pct !== null ? `, which is <span style="color: ${tint(m.pct)}; font-weight: 600;">${(m.pct >= 0 ? '+' : '') + m.pct.toFixed(2)}%</span> of the ${usd0(data.settings.budgetUsd)} budget` : ''}.${before && before.n ? ` The 30 days before: ${usd2(before.usd)} from ${before.n}${before.pct !== null ? ' (' + (before.pct >= 0 ? '+' : '') + before.pct.toFixed(2) + '%)' : ''}.` : ''}${typeof m.afterCosts === 'number' && data.costEachWay ? ` No trading costs are taken from the fake money: with a typical ${data.costEachWay}% on each buy and each sell that would be <span style="color: ${tint(m.afterCosts)}; font-weight: 600;">${usd2(m.afterCosts)}</span>.` : ''}</div>` : '';
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
                ${section('By screener', g.screener)}${section('By place in the ranking when bought', g.rank)}${section('By RSI when bought', g.rsi)}${section('By how long it had stayed near the top when bought', g.stay)}${section('By who chose', g.chosen)}${section('By how it was sold', g.exit)}
            </table></div><div style="font-size: 0.8rem; margin-top: 4px;">A group needs ${need} trades before the autopilot acts on it. A screener whose recent trades clearly lag an S&amp;P 500 index fund is rested for two weeks. Past results of fake-money trades; they say nothing certain about the future.</div></details>
            ${lessons}
        </div>`;
    }

    // ---------------------------------------------------------------- "Improving its own rules": what it has changed, is trying, has tried
    function ruleWords(r) {
        return `sells at ${r.stop}% or +${r.take}%; ${r.trailMode === 'off' ? 'no stop follows a holding (switched off)' : r.trailMode === 'full' ? 'a trailing stop follows each holding from the moment it is bought, set from how much that holding normally moves and from its screener figures now' : 'a stop follows a rising holding, set from how much that holding normally moves and from its screener figures now'}; buys from the top ${r.top} of a ranking` + (r.max_rsi >= 100 ? '' : ` with RSI under ${r.max_rsi}`);
    }
    function tuneHtml() {
        const t = data.tune, r = data.rules;
        if (!t || !r) return '';
        const names = { stop: 'loss limit', take: 'gain mark', trail: 'share of a gain it gives back', top: 'how far down a ranking it buys', max_rsi: 'RSI limit' };
        const changed = Object.keys(r.changed || {});
        const trial = t.trial, group = t.group || 10;
        const side = (n, avg) => `${n} finished${n ? ' (average ' + pc(avg) + ')' : ''}`;
        const now = trial
            ? `<div style="margin-top: 6px;"><strong style="color: var(--text-primary);">Trying now</strong> (since ${esc(day(trial.since))}): ${esc(trial.text)}. Why: ${esc(trial.why)}. ${esc(trial.how)} So far: with the change ${side(trial.with, trial.avgWith)}, without it ${side(trial.without, trial.avgWithout)}. It decides after ${group} each way and keeps the change only if that group did clearly better. <a href="#" data-ap="stoptrial">Stop this trial</a></div>`
            : `<div style="margin-top: 6px;">${t.nextReviewIn === 0 ? 'It reviews its rules at the next sale.' : `Next review of its rules after ${t.nextReviewIn} more finished trade${t.nextReviewIn === 1 ? '' : 's'}`}${t.nextReviewIn === 0 ? '' : ` (it reviews them every ${t.batch}).`} If the record suggests a change worth trying, it tries it beside the current rule over the same days.</div>`;
        const verdicts = { kept: 'kept', dropped: 'not kept', stopped: 'stopped' };
        const past = (t.past || []).slice().reverse();
        return `<div class="ap-section"><h4>Improving its own rules</h4>
            <div>Its rules now (${esc(r.name)} level): ${esc(ruleWords(r))}.${(r.yours || []).length ? ` Set by you: ${esc(r.yours.map(k => names[k]).join(' and '))}; its trials leave ${r.yours.length === 1 ? 'that' : 'those'} alone.` : ''}${changed.length ? ` Changed by itself after a trial: ${changed.map(k => esc(names[k] + ' (the level starts at ' + r.changed[k] + ')') + ` <a href="#" data-ap="restore" data-param="${esc(k)}">put it back</a>`).join(', ')}.` : ''}</div>
            ${now}
            ${data.aiSellPausedUntil ? `<div style="margin-top: 6px;">The AI model's early sells are paused until ${esc(day(data.aiSellPausedUntil))}: the holdings it had sold early went on rising afterwards. The fixed selling rules still apply.</div>` : ''}
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
        if (!part) part = rememberedPart() || (data.settings.enabled && data.settings.screeners.length ? 'activity' : 'settings');
        const breakdown = byId('ap-breakdown');
        if (breakdown && typeof breakdown.open === 'boolean') breakdownOpen = breakdown.open;
        if (document.querySelectorAll) Array.from(document.querySelectorAll('[data-ap-fold]')).forEach(x => { if (typeof x.open === 'boolean') openDetails[x.getAttribute('data-ap-fold')] = x.open; });
        const d = draft, o = data.options, on = data.settings.enabled, ready = on && data.settings.screeners.length > 0, state = savedState();
        const lvl = paceOf(d.risk);                        // what the level would set; null if the function does not send it
        const select = (id, key, list, value, label) => `<select id="${id}">${lvl ? `<option value="auto" ${isAuto(d, key) ? 'selected' : ''}>Automatic: ${label(lvl[key])}</option>` : ''}${list.map(v => `<option value="${v}" ${!isAuto(d, key) && v === value ? 'selected' : ''}>${label(v)}</option>`).join('')}</select>`;
        const tag = (key) => lvl ? `<span id="ap-tag-${key}" class="ap-auto ${isAuto(d, key) ? '' : 'own'}">${isAuto(d, key) ? 'automatic' : 'set by you'}</span>` : '';
        const icons = { buy: '🟢', sell: '🔴', note: 'ℹ️' };
        const all = (data.log || []).slice().reverse(), log = tradesOnly ? all.filter(e => e.type !== 'note') : all;
        const shown = showAll ? log : log.slice(0, 8);
        const holds = (data.plans || []).length;
        // with "Buys and sells only" on, the latest check-in's own line is still shown if it is newer than the last trade: it says why nothing happened
        const latest = tradesOnly && all.length && all[0].type === 'note' && all[0].key ? all[0] : null;
        const mayRow = (id, key, title, text) => `<label class="ap-may"><input id="${id}" type="checkbox" ${d[key] !== false ? 'checked' : ''}> <strong>${title}</strong><small>${text}</small></label>`;
        const levels = Object.keys(o.risk).sort();
        const chosen = d.screeners.length;
        el.innerHTML = `
            <div class="ap-wrap">
                <div class="ap-head">
                    <h3>🤖 AI autopilot <span class="ap-sub">fake money, an experiment to watch</span></h3>
                    <label class="ap-switch" title="Switch the autopilot on or off. This is saved straight away."><span id="ap-switch-text">${d.enabled ? 'On' : 'Off'}</span><input id="ap-enabled" type="checkbox" ${d.enabled ? 'checked' : ''} ${working ? 'disabled' : ''}><span class="ap-track"></span></label>
                </div>
                <p class="ap-intro">An AI model makes practice buys and sells for you from the latest results of the screeners you choose, inside the limits you set here. It uses the fake money of your <a href="#practice">practice portfolio</a>, where its holdings are listed with your own. Nothing here is advice, and past screener results have not shown a reliable edge.</p>
                <div id="ap-status" class="ap-status ${on ? 'on' : ''}">${esc(statusText())}</div>

                <div class="ap-actions">
                    <button id="ap-run" data-ap="run" class="ap-btn ${ready ? 'primary' : ''}" ${working || !ready || state.text === 'Saving…' ? 'disabled' : ''} title="${!on ? 'Switch the autopilot on first' : !ready ? 'Tick at least one screener first' : 'Runs one check-in now instead of waiting for the next one. If the budget is still being built up, pressing this releases the next part of it early'}">${working === 'run' ? 'Checking in… this can take up to a minute' : 'Check in now'}</button>
                    <button id="ap-sellall" data-ap="sellall" class="ap-btn" ${working || !holds ? 'disabled' : ''} title="${holds ? 'Sells every holding the autopilot bought, now, at the latest prices. Holdings you bought yourself are not touched' : 'It holds nothing right now'}">${working === 'sellall' ? 'Selling…' : 'Sell everything it holds' + (holds ? ' (' + holds + ')' : '')}</button>
                    <span id="ap-saved" class="ap-saved ${state.bad ? 'bad' : ''}">${esc(state.text)}</span>
                </div>
                <div id="ap-notice" class="${notice ? 'ap-note ' + (notice.bad ? 'bad' : 'good') : ''}" role="status">${notice ? esc(notice.text) : ''}</div>

                <div class="ap-views" role="tablist" aria-label="Autopilot">
                    <button type="button" id="ap-view-activity" class="ap-view ${part === 'activity' ? 'now' : ''}" data-ap-part="activity" role="tab">📋 Activity</button>
                    <button type="button" id="ap-view-settings" class="ap-view ${part === 'settings' ? 'now' : ''}" data-ap-part="settings" role="tab">⚙️ Settings</button>
                </div>

                <div id="ap-pane-activity" class="ap-pane" style="${part === 'activity' ? '' : 'display: none;'}">
                ${recordHtml()}
                ${tuneHtml()}
                <div class="ap-section"><h4>What it has done <span class="ap-fresh"><span id="ap-fresh">${loadedAt ? 'Up to date at ' + esc(clock(loadedAt)) + '. Refreshes by itself every minute.' : ''}</span><a href="#" data-ap="refresh">↻ Refresh now</a><label class="ap-mini" title="On: only its buys and sells are listed. Off: its check-ins and notes too. Remembered in this browser."><input id="ap-tradesonly" type="checkbox" ${tradesOnly ? 'checked' : ''}><span class="ap-dot"></span>Buys and sells only</label></span></h4>
                    ${latest ? `<div class="ap-log"><time>${icons.note} ${esc(when(latest.t))}</time> Latest check-in: ${esc(latest.text.replace(/^Checked in\. /, ''))}${latest.n > 1 ? ` <span style="font-size: 0.8rem;">(the same at ${latest.n} check-ins in a row)</span>` : ''}</div>` : ''}
                    ${log.length ? shown.map(e => `<div class="ap-log"><time>${icons[e.type] || ''} ${esc(when(e.t))}</time> ${e.type === 'buy' ? `<strong style="color: var(--text-primary);">Bought ${esc(e.symbol)}</strong> with ${usd0(e.usd)}. ` : e.type === 'sell' ? `<strong style="color: var(--text-primary);">Sold ${esc(e.symbol)}</strong>${typeof e.pct === 'number' ? ` <span style="color: ${tint(e.pct)}; font-weight: 600;">${pc(e.pct)}</span>` : ''}. ` : ''}${esc(e.text)}${e.n > 1 ? ` <span style="font-size: 0.8rem;">(the same at ${e.n} check-ins in a row, since ${esc(when(e.first))})</span>` : ''}${fold(e.type + e.t + e.symbol, e.type === 'sell' ? 'Why, and the details' : 'The plan for it', e.detail)}</div>`).join('') : `<div>${tradesOnly && all.length ? 'No buys or sells yet.' : 'Nothing yet. Its buys, sells and check-ins will be listed here.'}</div>`}
                    ${log.length > shown.length ? `<a href="#" data-ap="more" style="display: inline-block; margin-top: 8px;">Show all ${log.length}</a>` : ''}</div>
                </div>

                <div id="ap-pane-settings" class="ap-pane" style="${part === 'settings' ? '' : 'display: none;'}">
                <div class="ap-presets"><span>Quick set-ups:</span>${PRESETS.filter(p => p.set.screeners.every(k => o.screeners[k])).map(p => `<button type="button" class="ap-preset" data-ap-preset="${p.key}" title="${esc(p.title)}">${p.name}</button>`).join('')}<span>They fill in the fields below (not the budget or the on/off switch); change anything afterwards.</span></div>

                <div class="ap-card">
                    <span class="ap-label">Risk level</span>
                    <input id="ap-risk" class="ap-risk" type="range" min="1" max="${levels.length || 5}" step="1" value="${d.risk}" aria-label="Risk level">
                    <div class="ap-levels">${levels.map(n => `<span data-ap-level="${n}" class="${String(d.risk) === n ? 'now' : ''}">${esc(o.risk[n].name)}</span>`).join('')}</div>
                    <div id="ap-risk-text" class="ap-help">${esc(riskText(d.risk))}</div>
                    <div class="ap-own"><strong>Your own limits</strong>
                        <label>Sell at a loss of <input id="ap-stop" type="number" min="1.5" max="30" step="0.5" inputmode="decimal" placeholder="${hint(d.risk, 'stop')}" value="${d.stopPct || ''}" aria-label="Your own loss limit in percent">%</label>
                        <label>Sell at a gain of <input id="ap-take" type="number" min="2" max="80" step="0.5" inputmode="decimal" placeholder="${hint(d.risk, 'take')}" value="${d.takePct || ''}" aria-label="Your own gain mark in percent">%</label>
                        <span>Optional. Leave a field empty to use the level's (shown in grey). What you set here, its own trials leave alone.</span>
                        ${'trailMode' in data.settings ? `<label style="flex-basis: 100%;">Trailing stop <select id="ap-trail" style="padding: 6px 8px; margin: 0 4px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px; max-width: 100%;">${Object.keys(TRAILS).map(k => `<option value="${k}" ${trailOf(d) === k ? 'selected' : ''}>${TRAILS[k].name}</option>`).join('')}</select></label>
                        <span id="ap-trail-text" style="flex-basis: 100%;">${esc(TRAILS[trailOf(d)].help)}</span>` : ''}
                    </div>
                </div>

                <div class="ap-card">
                    <div class="ap-fields">
                        <div><label class="ap-label" for="ap-budget">Budget for the AI</label><div class="ap-input">$ <input id="ap-budget" type="number" min="100" step="500" value="${d.budgetUsd}"></div></div>
                        <div><label class="ap-label" for="ap-period">Build up to it over${tag('periodDays')}</label><div class="ap-input"><input id="ap-period" type="number" min="1" max="90" step="1" ${lvl ? `placeholder="${lvl.periodDays}"` : ''} value="${isAuto(d, 'periodDays') ? '' : d.periodDays}"> days</div></div>
                        <div><label class="ap-label" for="ap-every">Checks in${tag('everyHours')}</label><div class="ap-input">${select('ap-every', 'everyHours', o.everyHours, d.everyHours, everyText)}</div></div>
                        <div><label class="ap-label" for="ap-hold">Keeps a holding at most${tag('maxHoldDays')}</label><div class="ap-input">${select('ap-hold', 'maxHoldDays', o.holdDays, d.maxHoldDays, holdText)}</div></div>
                    </div>
                    ${lvl ? `<div class="ap-help">The last three follow the risk level while they are left on automatic (an empty box, or "Automatic" in a menu): move the slider and they move with it. Set one yourself and it stays where you put it.${(d.auto || []).length < 3 ? ' <a href="#" data-ap="autopace">Let the risk level set all three</a>' : ''}</div>` : ''}
                    <div id="ap-plan" class="ap-help">${esc(planText(d))}</div>
                    <div id="ap-pace" class="ap-help">${esc(paceText(d))}</div>
                </div>

                <div class="ap-card">
                    <span class="ap-label">Screeners it buys from <span id="ap-chosen" class="ap-sub">${chosen} chosen</span></span>
                    ${screenerGroups(o.screeners).map(([group, keys], i) => `<div class="ap-group ${i === 0 ? 'first' : ''}"><div class="ap-group-name">${esc(group)}</div><div class="ap-chips">${keys.map(k => `<label class="ap-chip"><input type="checkbox" data-ap-screener="${esc(k)}" ${d.screeners.includes(k) ? 'checked' : ''}> ${esc(o.screeners[k].name)}${data.resting && data.resting[k] ? ' <small title="Resting after its recent trades lagged the market">(resting until ' + esc(day(data.resting[k])) + ')</small>' : ''}</label>`).join('')}</div></div>`).join('')}
                    <div class="ap-help">Each share market is only traded while it is open; coins at any time. Bigger lists take a little longer to check.</div>
                </div>

                <div class="ap-card">
                    <span class="ap-label">What it may do by itself</span>
                    ${mayRow('ap-aisell', 'aiSell', 'Sell early on the AI model\'s review', 'At every check-in the AI model looks at each holding with the latest screener figures and recent headlines, and may sell it before the fixed rules would, or keep it with a tighter stop: for instance when a rise has stalled or turned. A larger model is asked when a gain is at stake (a few times a day at most). Off: only the fixed rules sell.')}
                    ${mayRow('ap-tune', 'selfTune', 'Try changes to its own rules', 'Every 20 finished trades it may try one change to a selling or buying rule beside the current one, and keeps it only if it did clearly better. Off: its rules stay exactly as they are.')}
                    ${mayRow('ap-mail', 'emails', 'Email me its reviews', 'An email to your account address each time it reviews its rules, starts a trial or finishes one.')}
                </div>
                </div>
            </div>`;
    }

    // one of the "what it may do by itself" switches: what is ticked on screen, or what is saved if it is not on screen
    function may(id, key) { const el = byId(id); return el && typeof el.checked === 'boolean' ? !!el.checked : (data.settings[key] !== false); }
    // the user's own loss limit or gain mark: the number typed, or null when the field is empty (the level's then applies)
    function ownLimit(id, key) { const el = byId(id); if (!el || typeof el.value !== 'string') return data.settings[key] || null; const n = Math.abs(parseFloat(el.value)); return n > 0 ? n : null; }
    function readDraft() {
        if (!byId('ap-risk')) return;
        const risk = parseInt(byId('ap-risk').value, 10) || 3, level = paceOf(risk), left = [];
        // a pace field left empty or on "Automatic" takes the level's own value, and is listed as left to the level
        const pace = (id, key, parse, fallback) => {
            const raw = String(byId(id).value);
            if (level && (raw === '' || raw === 'auto')) { left.push(key); return level[key]; }
            const n = parse(raw); return isFinite(n) ? n : fallback;
        };
        draft = {
            enabled: !!byId('ap-enabled').checked, risk,
            budgetUsd: parseFloat(byId('ap-budget').value) || 0, periodDays: pace('ap-period', 'periodDays', v => parseInt(v, 10), 1) || 1,
            everyHours: pace('ap-every', 'everyHours', parseFloat, NaN), maxHoldDays: pace('ap-hold', 'maxHoldDays', parseFloat, NaN),
            screeners: Array.from(document.querySelectorAll('[data-ap-screener]')).filter(c => c.checked).map(c => c.getAttribute('data-ap-screener')).sort(),
            aiSell: may('ap-aisell', 'aiSell'), selfTune: may('ap-tune', 'selfTune'), emails: may('ap-mail', 'emails'),
            stopPct: ownLimit('ap-stop', 'stopPct'), takePct: ownLimit('ap-take', 'takePct')
        };
        if ('auto' in data.settings) draft.auto = PACE_FIELDS.filter(k => left.includes(k));
        if ('trailMode' in data.settings) { const pick = byId('ap-trail'); draft.trailMode = pick && TRAILS[pick.value] ? pick.value : trailOf(data.settings); }
    }
    // Bring the button, the "saved" line and the explanatory lines up to date without redrawing (typing keeps its place)
    function syncDraft() {
        readDraft();
        if (!draft || !data) return;
        const on = data.settings.enabled, ready = on && data.settings.screeners.length > 0, state = savedState(), set = (id, fn) => { const el = byId(id); if (el) fn(el); };
        set('ap-run', el => { el.disabled = !!working || !ready || state.text === 'Saving…'; el.title = !on ? 'Switch the autopilot on first' : !ready ? 'Tick at least one screener first' : 'Runs one check-in now instead of waiting for the next one. If the budget is still being built up, pressing this releases the next part of it early'; if (el.classList) el.classList.toggle('primary', ready); });
        set('ap-saved', el => { el.textContent = state.text; if (el.classList) el.classList.toggle('bad', state.bad); });
        set('ap-status', el => { el.textContent = statusText(); if (el.classList) el.classList.toggle('on', on); });
        set('ap-switch-text', el => { el.textContent = draft.enabled ? 'On' : 'Off'; });
        set('ap-risk-text', el => { el.textContent = riskText(draft.risk); });
        set('ap-trail-text', el => { el.textContent = TRAILS[trailOf(draft)].help; });
        const lvl = paceOf(draft.risk);
        if (lvl) {
            set('ap-period', el => { el.placeholder = String(lvl.periodDays); });
            [['ap-every', 'everyHours', everyText], ['ap-hold', 'maxHoldDays', holdText]].forEach(([id, key, label]) => set(id, el => { const first = el.options && el.options[0]; if (first && first.value === 'auto') first.textContent = 'Automatic: ' + label(lvl[key]); }));
            PACE_FIELDS.forEach(key => set('ap-tag-' + key, el => { el.textContent = isAuto(draft, key) ? 'automatic' : 'set by you'; if (el.classList) el.classList.toggle('own', !isAuto(draft, key)); }));
        }
        set('ap-stop', el => { el.placeholder = hint(draft.risk, 'stop'); });
        set('ap-take', el => { el.placeholder = hint(draft.risk, 'take'); });
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
        if (d.stopPct !== null && d.stopPct !== undefined && !(d.stopPct >= 1.5 && d.stopPct <= 30)) throw new Error('your own loss limit must be between 1.5% and 30% (or empty).');
        if (d.takePct !== null && d.takePct !== undefined && !(d.takePct >= 2 && d.takePct <= 80)) throw new Error('your own gain mark must be between 2% and 80% (or empty).');
    }
    // Is the user in the middle of typing or dragging in the panel? Then the panel is updated in place, not redrawn.
    function editing() {
        const el = document.activeElement;
        return !!el && typeof el.id === 'string' && ['ap-budget', 'ap-period', 'ap-risk', 'ap-stop', 'ap-take'].includes(el.id);
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
    function sharePlans() { if (data && data.allowed && window.practicePortfolio && window.practicePortfolio.setPlans) window.practicePortfolio.setPlans(data.plans || [], { realizedUsd: data.realizedUsd }); }
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
        const view = e.target.closest && e.target.closest('[data-ap-part]');
        if (view && data) { showPart(view.getAttribute('data-ap-part'), true); return; }
        const preset = e.target.closest && e.target.closest('[data-ap-preset]');
        if (preset && data && byId('ap-risk')) {
            const p = PRESETS.find(x => x.key === preset.getAttribute('data-ap-preset'));
            if (!p) return;
            byId('ap-risk').value = String(p.set.risk); byId('ap-period').value = String(p.set.periodDays); byId('ap-every').value = String(p.set.everyHours);
            const hold = byId('ap-hold'), want = (data.options.holdDays || []).find(v => Math.abs(v - p.set.maxHoldDays) < 1e-6);
            if (hold && want !== undefined) hold.value = String(want);
            Array.from(document.querySelectorAll('[data-ap-screener]')).forEach(c => { c.checked = p.set.screeners.includes(c.getAttribute('data-ap-screener')); });
            saveError = null; notice = { text: `"${p.name.replace(/^\S+\s/, '')}" filled in: ${p.title.charAt(0).toLowerCase() + p.title.slice(1)}. Change anything you like; it is saved as you go.` };
            queueSave(150); return;
        }
        const t = e.target.closest && e.target.closest('[data-ap]');
        if (!t || !data) return;
        if (t.tagName === 'A') e.preventDefault();
        const action = t.getAttribute('data-ap');
        if (action === 'more') { readDraft(); showAll = true; render(); }
        else if (action === 'refresh') refresh(true);
        else if (action === 'autopace') {                   // hand all three pace settings back to the risk level
            if (byId('ap-period')) byId('ap-period').value = '';
            ['ap-every', 'ap-hold'].forEach(id => { if (byId(id)) byId(id).value = 'auto'; });
            saveError = null; notice = { text: 'The risk level now sets how fast it builds up, how often it checks in and how long it keeps a holding.' };
            queueSave(150);
        }
        else if (action === 'sellall') {
            const n = (data.plans || []).length;
            if (!n || !confirm(`Sell the ${n} holding${n === 1 ? '' : 's'} the autopilot bought, now, at the latest prices?\n\nHoldings you bought yourself are not touched. If the autopilot stays switched on it will buy again at its next check-in.`)) return;
            act('sellall', async () => {
                const r = await api('sellall');
                take(r);
                const s = r.summary || {};
                notice = { text: `Sold ${s.sold || 0} holding${s.sold === 1 ? '' : 's'}.` + (s.skipped && s.skipped.length ? ` No price right now for ${s.skipped.join(', ')}: still held.` : '') + (data.settings.enabled ? ' The autopilot is still on and will buy again at its next check-in.' : '') };
                if (window.practicePortfolio && window.practicePortfolio.reload) window.practicePortfolio.reload();
            });
        }
        else if (action === 'restore' || action === 'stoptrial') {
            act('tune', async () => { take(await api('tune', action === 'restore' ? { op: 'restore', param: t.getAttribute('data-param') } : { op: 'stop' })); notice = { text: action === 'restore' ? 'Put back to the level\'s own rule.' : 'Trial stopped. The rule stays as it was.' }; });
        }
        else if (action === 'run') {
            act('run', async () => {
                const r = await api('run');
                take(r);
                const s = r.summary || {};
                // when nothing was traded, say why here: the note with the reason may be hidden by "Buys and sells only"
                notice = { text: s.conflict ? 'The portfolio was being changed at the same time, so nothing was traded. Try again.'
                    : !(s.bought || s.sold) && s.why ? `Checked in: nothing bought or sold. ${s.why}`
                    : `Checked in: ${s.bought || 0} bought, ${s.sold || 0} sold. Details are listed below.` };
                if (window.practicePortfolio && window.practicePortfolio.reload) window.practicePortfolio.reload();
            });
        }
    });
    const changed = (e) => {
        if (!e.target || !data || !data.allowed) return;
        const id = e.target.id || '', inPanel = id.indexOf('ap-') === 0 || (e.target.getAttribute && e.target.getAttribute('data-ap-screener'));
        if (!inPanel) return;
        if (id === 'ap-tradesonly') {                                                    // how the list is shown: kept in this browser, not a setting of the autopilot
            if (e.type === 'change') { readDraft(); tradesOnly = !!e.target.checked; remember(tradesOnly); showAll = false; if (editing()) syncDraft(); else render(); }
            return;
        }
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
