// The autopilot controls in a stand-in page with a stand-in API.
const vm = require('vm'), fs = require('fs'); const src = fs.readFileSync(process.argv[2], 'utf8');
let ok = true; const check = (n, c, x) => { ok = ok && !!c; console.log((c ? 'PASS ' : 'FAIL ') + n + (c ? '' : '  ' + JSON.stringify(x))); };
const OPTIONS = { screeners: { '3-8': { name: 'Dow 30', kind: 'stock' }, '3-100': { name: 'S&P 100', kind: 'stock' }, '7-1': { name: 'Crypto (top coins)', kind: 'crypto' } }, everyHours: [3, 6, 12, 24], holdDays: [2, 5, 10, 20, 60],
  risk: { 1: { name: 'Cautious', positions: 12, top: 5, stop: -5, take: 8, crypto: 0 }, 3: { name: 'Balanced', positions: 8, top: 10, stop: -10, take: 18, crypto: 0.25 }, 5: { name: 'Adventurous', positions: 4, top: 20, stop: -20, take: 45, crypto: 1 } } };
function page(server) {
  const els = {}, handlers = {}, calls = []; const container = { innerHTML: '' }; let boxes = [];
  const document = { readyState: 'complete', getElementById: id => id === 'practice-autopilot' ? container : (els[id] || null), addEventListener: (t, f) => { (handlers[t] = handlers[t] || []).push(f); }, querySelectorAll: () => boxes };
  const fetchFake = async (url, opts) => { const b = JSON.parse(opts.body); calls.push(b); const r = server(b); return { ok: r.status === 200, status: r.status, json: async () => r.body }; };
  const ctx = { document, localStorage: { getItem: () => 'tester@x.com' }, fetch: fetchFake, console, setTimeout, Date, JSON, Math, Object, String, Array, parseInt, parseFloat, isNaN, Promise };
  ctx.window = ctx; ctx.practicePortfolio = { reloaded: 0, reload() { this.reloaded++; } };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  const form = (d) => { Object.assign(els, { 'ap-enabled': { checked: d.enabled }, 'ap-risk': { value: String(d.risk) }, 'ap-budget': { value: String(d.budgetUsd) }, 'ap-period': { value: String(d.periodDays) }, 'ap-every': { value: String(d.everyHours) }, 'ap-hold': { value: String(d.maxHoldDays) }, 'ap-risk-text': { textContent: '' } }); boxes = Object.keys(OPTIONS.screeners).map(k => ({ checked: d.screeners.includes(k), getAttribute: () => k })); };
  const click = a => handlers.click.forEach(f => f({ target: { closest: s => s === '[data-ap]' ? { getAttribute: () => a, tagName: 'BUTTON' } : null }, preventDefault() {} }));
  const text = () => container.innerHTML.replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/\s+/g, ' ');
  return { container, handlers, calls, form, click, text, ctx, els };
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  let p = page(() => ({ status: 200, body: { success: true, allowed: false } })); await sleep(30);
  check('hidden for someone not allowed', p.container.innerHTML === '');
  const settings = { enabled: false, risk: 3, budgetUsd: 10000, periodDays: 10, everyHours: 24, maxHoldDays: 20, screeners: ['3-100'] };
  let stored = { settings: { ...settings }, state: {}, log: [] };
  const server = b => {
    if (b.action === 'get') return { status: 200, body: { success: true, allowed: true, options: OPTIONS, ...stored } };
    if (b.action === 'save') { stored.settings = b.settings; stored.log.push({ t: '2026-10-12T15:00:00Z', type: 'note', symbol: '', usd: 0, text: 'Autopilot on: Balanced level.' }); return { status: 200, body: { success: true, allowed: true, options: OPTIONS, ...stored } }; }
    if (b.action === 'run') { if (stored.fail) return { status: 429, body: { error: 'It checked in a moment ago. Try again in 10 minutes' } }; stored.state.lastRun = '2026-10-12T15:40:00Z'; stored.log.push({ t: '2026-10-12T15:40:00Z', type: 'buy', symbol: 'COP', usd: 1250, text: 'Rank 1 with <b>RSI 66</b> (S&P 100 rank 1, score +3.4; chosen by the AI model)' }, { t: '2026-10-12T15:40:00Z', type: 'sell', symbol: 'AMT', usd: 1100, text: 'Up +18.2% since it was bought. Put in $1,000.00, got back $1,182.00.' }); return { status: 200, body: { success: true, allowed: true, options: OPTIONS, summary: { bought: 1, sold: 1, decidedBy: 'ai' }, ...stored } }; }
  };
  p = page(server); await sleep(30);
  check('shows the controls, off by default', /AI autopilot/.test(p.text()) && /Balanced: spreads the budget over up to 8 holdings, looks at the top 10 of each screener, sells a holding at -10% or \+18%, up to 25% of the budget in coins\./.test(p.text()) && /Off\. Nothing is bought or sold automatically/.test(p.text()) && /<option value="24" selected>once a day/.test(p.container.innerHTML) && /data-ap="run"[^>]*disabled/.test(p.container.innerHTML), p.text().slice(0, 400));
  check('says plainly what it is', /fake money/.test(p.text()) && /Nothing here is advice/.test(p.text()));
  p.form({ ...settings, enabled: true, risk: 5, budgetUsd: 5000, periodDays: 5, everyHours: 12, maxHoldDays: 10, screeners: ['3-8', '7-1'] }); await p.ctx.practiceAutopilot.flush(); await sleep(30);
  const sent = p.calls.find(c => c.action === 'save');
  check('saves exactly what was set', JSON.stringify(sent.settings) === JSON.stringify({ enabled: true, risk: 5, budgetUsd: 5000, periodDays: 5, everyHours: 12, maxHoldDays: 10, screeners: ['3-8', '7-1'] }) && /Autopilot switched on/.test(p.text()) && /On\. First check-in at the next hourly check\./.test(p.text()) && /Adventurous/.test(p.text()) && !/data-ap="run"[^>]*disabled/.test(p.container.innerHTML), sent);
  { const keep = stored.settings; p.form({ ...stored.settings, screeners: [] }); await p.ctx.practiceAutopilot.flush(); await sleep(30); check('no screener ticked is saved as it is, and it says what is missing', stored.settings.screeners.length === 0 && /On, but no screener is chosen yet\. Tick at least one below/.test(p.text()) && /Tick at least one screener for it to start/.test(p.text()) && /id="ap-run"[^>]*disabled/.test(p.container.innerHTML), p.text().slice(0, 300)); p.form(keep); await p.ctx.practiceAutopilot.flush(); await sleep(30); }
  p.form(stored.settings); p.click('run'); await sleep(30);
  check('check in now: shows what happened and refreshes the portfolio', /Checked in: 1 bought, 1 sold/.test(p.text()) && /Bought COP with \$1,250\. Rank 1 with &lt;b&gt;RSI 66&lt;\/b&gt;/.test(p.text()) && /Sold AMT \. Up \+18\.2%/.test(p.text()) && p.ctx.practicePortfolio.reloaded === 1 && /Last check-in/.test(p.text()) && !/<b>RSI/.test(p.container.innerHTML), p.text().slice(-500));
  stored.fail = true; p.form(stored.settings); p.click('run'); await sleep(30); check('too soon: says so', /checked in a moment ago/.test(p.text()));
  // every screener in groups, and the record it learns from
  const OPT2 = { ...OPTIONS, screeners: { '3-100': { name: 'S&P 100', kind: 'stock', group: 'US shares' }, '3-6': { name: 'Russell 2000 (small)', kind: 'stock', group: 'US shares' }, '4-200': { name: 'ASX 200', kind: 'stock', group: 'Australian shares' }, '5-ftse100': { name: 'UK FTSE 100', kind: 'stock', group: 'UK shares' }, '7-1': { name: 'Crypto (top coins)', kind: 'crypto', group: 'Coins' } } };
  const G = (label, n, avg, vs, beat) => ({ label, n, avg, vs, beat, judged: n, up: beat });
  const full = { settings: { ...settings, enabled: true, screeners: ['3-100', '4-200'] }, state: { lastRun: '2026-10-12T15:40:00Z' }, log: [], minSample: 8, resting: { '3-100': '2026-10-26T15:40:00Z' },
    scorecard: { ...G('all', 12, 1.84, -0.62, 5), groups: { screener: [G('S&P 100', 9, 0.9, -1.7, 3), G('ASX 200', 3, 4.6, 2.6, 2)], rank: [G('rank 1 to 3', 12, 1.84, -0.62, 5)], rsi: [G('RSI 45 to 60', 12, 1.84, -0.62, 5)], chosen: [G('chosen by the AI model', 12, 1.84, -0.62, 5)], exit: [G('sold at the loss limit', 4, -10.5, -11, 0)] } },
    lessons: { at: '2026-10-20T15:40:00Z', n: 10, items: ['Buys ranked 1 to 3 lagged the market by 0.6% on average over 12 trades <b>.', 'Too few ASX trades (3) to compare.'] }, recent: [] };
  let q = page(() => ({ status: 200, body: { success: true, allowed: true, options: OPT2, ...full } })); await sleep(30);
  check('screeners are listed under their markets', /US shares S&P 100 \(resting until [^)]*26[^)]*\) Russell 2000 \(small\) Australian shares ASX 200 UK shares UK FTSE 100 Coins Crypto \(top coins\)/.test(q.text()), q.text().slice(q.text().indexOf('Screeners it buys from'), q.text().indexOf('Screeners it buys from') + 260));
  check('how it is doing: totals against the market', /How it is doing 12 closed trades: average \+1\.8% , -0\.6% against the S&P 500 over the same days, ahead in 5 of 12\./.test(q.text()) && !/too few to conclude/.test(q.text()), q.text().slice(q.text().indexOf('How it is doing'), q.text().indexOf('How it is doing') + 200));
  check('breakdown by screener, rank, RSI, who chose and how it was sold', ['By screener', 'S&P 100 9 \\+0\\.9% -1\\.7% 3 of 9', 'ASX 200 3 \\+4\\.6% \\+2\\.6% 2 of 3', 'By place in the ranking when bought', 'By RSI when bought', 'By who chose', 'By how it was sold', 'sold at the loss limit 4 -10\\.5% -11\\.0% 0 of 4', 'A group needs 8 trades'].every(x => new RegExp(x).test(q.text())), q.text().slice(q.text().indexOf('Breakdown'), q.text().indexOf('Breakdown') + 500));
  check('its notes are shown, safely, with what they rest on', /What it has noted from its record \(written by the AI model on [^)]*20[^)]* from 10 closed trades\)/.test(q.text()) && /lagged the market by 0\.6% on average over 12 trades &lt;b&gt;/.test(q.container.innerHTML) && /Too few ASX trades/.test(q.text()));
  q = page(() => ({ status: 200, body: { success: true, allowed: true, options: OPT2, ...full, scorecard: { ...G('all', 3, -2.0, -1.0, 1), groups: {} }, lessons: null, resting: {} } })); await sleep(30);
  check('with few trades it says they are too few', /3 closed trades: average -2\.0% , -1\.0% against the S&P 500 over the same days, ahead in 1 of 3\. Fewer than 8 trades: too few to conclude anything yet\./.test(q.text()) && !/What it has noted/.test(q.text()) && !/resting until/.test(q.text()), q.text().slice(q.text().indexOf('How it is doing'), q.text().indexOf('How it is doing') + 260));
  check('before any sale it explains what will appear', /Nothing it bought has been sold yet/.test(p.text()));
  // every change saves by itself: nothing to press, and a refresh shows what was last set
  { const st = { settings: { ...settings, screeners: [] }, state: {}, log: [], practiceCash: 100000 }; let saves = 0;
    const srv = b => { if (b.action === 'save') { saves++; if (st.down) return { status: 500, body: { error: 'Internal server error' } }; st.settings = { ...b.settings, budgetUsd: Math.round(b.settings.budgetUsd) }; } if (b.action === 'run') st.state.lastRun = '2026-10-12T15:40:00Z';
      const ready = st.settings.enabled && st.settings.screeners.length;
      return { status: 200, body: { success: true, allowed: true, options: OPTIONS, summary: { bought: 0, sold: 0 }, ...st, holding: ready ? { count: 3, investedUsd: 3750 } : { count: 0, investedUsd: 0 }, nextCheck: ready ? { at: '2026-10-12T14:40:00Z', markets: ['US'] } : null } }; };
    let w = page(srv); await sleep(30);
    const html = w.container.innerHTML;
    check('layout: a switch, labelled fields, level names, no save button', /class="ap-switch"/.test(html) && /id="ap-switch-text">Off</.test(html) && /<label class="ap-label" for="ap-budget">Budget for the AI<\/label>/.test(html) && /Build up to it over/.test(html) && /data-ap-level="3" class="now">Balanced</.test(html)
      && !/data-ap="save"/.test(html) && /id="ap-saved" class="ap-saved ">Changes are saved as you make them\. Use the switch at the top right to turn it on\.</.test(html) && /id="ap-run" data-ap="run" class="ap-btn " disabled title="Switch the autopilot on first"/.test(html), html.slice(html.indexOf('ap-actions'), html.indexOf('ap-actions') + 520));
    check('nothing is ticked for a new user', !/data-ap-screener="[^"]*" checked/.test(html) && /0 chosen/.test(w.text()));
    check('says what the budget means in practice', /Up to 8 holdings of about \$1,250 each, bought a few at a time: the whole \$10,000 is in use after about 10 days\. Money from a sale is used again\./.test(w.text()));
    const stub = () => ({ disabled: false, textContent: '', title: '', classList: { on: {}, toggle(c, v) { this.on[c] = v; } } });
    const fire = (type, id) => w.handlers[type].forEach(f => f({ type, target: { id, getAttribute: () => null } }));
    Object.assign(w.els, { 'ap-run': stub(), 'ap-saved': stub(), 'ap-plan': stub(), 'ap-chosen': stub(), 'ap-status': stub(), 'ap-switch-text': stub() });
    w.form({ ...st.settings, budgetUsd: 20000.4, risk: 5 }); fire('input', 'ap-budget');
    check('typing: it says "Saving…" and waits for a pause before sending', w.els['ap-saved'].textContent === 'Saving…' && saves === 0 && /Up to 4 holdings of about \$5,000 each/.test(w.els['ap-plan'].textContent), [w.els['ap-saved'].textContent, saves]);
    await sleep(1100);
    check('after the pause it is saved without pressing anything', saves === 1 && st.settings.budgetUsd === 20000 && st.settings.risk === 5 && /✓ Saved\./.test(w.text()), [saves, st.settings, w.text().slice(w.text().indexOf('Check in now'), w.text().indexOf('Check in now') + 90)]);
    w.form({ ...st.settings, budgetUsd: 20000.4, risk: 5 }); await w.ctx.practiceAutopilot.flush(); await sleep(30);
    check('a value the server tidied (20000.4 to 20000) is not saved over and over', saves === 1, saves);
    w.form({ ...st.settings, screeners: ['3-8', '7-1'] }); fire('change', 'ap-screener'); await sleep(250);
    check('ticking a screener is saved almost at once', saves === 2 && JSON.stringify(st.settings.screeners) === JSON.stringify(['3-8', '7-1']), [saves, st.settings.screeners]);
    w = page(srv); await sleep(30);
    check('after a refresh the panel shows exactly what was last set', /data-ap-screener="3-8" checked/.test(w.container.innerHTML) && /data-ap-screener="7-1" checked/.test(w.container.innerHTML) && !/data-ap-screener="3-100" checked/.test(w.container.innerHTML) && /value="20000"/.test(w.container.innerHTML) && /data-ap-level="5" class="now"/.test(w.container.innerHTML) && /2 chosen/.test(w.text()));
    Object.assign(w.els, { 'ap-run': stub(), 'ap-saved': stub(), 'ap-plan': stub(), 'ap-chosen': stub(), 'ap-status': stub(), 'ap-switch-text': stub() });
    w.form({ ...st.settings, budgetUsd: 2000000 }); await w.ctx.practiceAutopilot.flush(); await sleep(30);
    check('a budget that makes no sense is not saved, and it says why', saves === 2 && w.els['ap-saved'].textContent === 'Not saved: the budget cannot be more than $1,000,000.' && w.els['ap-saved'].classList.on.bad === true, w.els['ap-saved'].textContent);
    w.form({ ...st.settings, enabled: true }); w.handlers.change.forEach(f => f({ type: 'change', target: { id: 'ap-enabled', getAttribute: () => null } })); await sleep(30);
    check('the switch saves at once and the panel says what happens next', saves === 3 && st.settings.enabled === true && /id="ap-switch-text">On</.test(w.container.innerHTML) && /class="ap-status on"/.test(w.container.innerHTML)
      && /On\. Holding 3 of up to 4: \$3,750 of the \$20,000 budget is invested\. Next check-in about [^.]*, when the US market is open\./.test(w.text()) && /Autopilot switched on\. Press "Check in now"/.test(w.text()) && /id="ap-run" data-ap="run" class="ap-btn primary"  title="Runs one check-in now/.test(w.container.innerHTML), w.text().slice(w.text().indexOf('On.'), w.text().indexOf('On.') + 220));
    w.form({ ...st.settings, risk: 2 }); w.click('run'); await sleep(60);
    check('check in now first saves what was just changed', saves === 4 && st.settings.risk === 2 && w.calls.map(c => c.action).slice(-2).join() === 'save,run' && /Checked in: 0 bought, 0 sold/.test(w.text()), w.calls.map(c => c.action));
    st.down = true; w.form({ ...st.settings, risk: 4 }); await w.ctx.practiceAutopilot.flush(); await sleep(30);
    check('if a save fails it says so and does not pretend', /Not saved: Internal server error/.test(w.text()) && /class="ap-saved bad"/.test(w.container.innerHTML) && st.settings.risk === 2, w.text().slice(w.text().indexOf('Check in now'), w.text().indexOf('Check in now') + 80));
    st.down = false; w.form({ ...st.settings, risk: 4 }); await w.ctx.practiceAutopilot.flush(); await sleep(30); check('and the next try goes through', st.settings.risk === 4 && /✓ Saved\./.test(w.text()));
    w.form({ ...st.settings, enabled: false }); w.handlers.change.forEach(f => f({ type: 'change', target: { id: 'ap-enabled', getAttribute: () => null } })); await sleep(30);
    check('switching off says its holdings stay', st.settings.enabled === false && /Autopilot switched off\. What it holds stays in the practice portfolio until you sell it\./.test(w.text()) && /Off\. Nothing is bought or sold automatically/.test(w.text()));
    w.form({ ...st.settings, enabled: true, screeners: [] }); w.handlers.change.forEach(f => f({ type: 'change', target: { id: 'ap-enabled', getAttribute: () => null } })); await sleep(30);
    check('switched on with nothing ticked: it stays on, waits, and says what to do', st.settings.enabled === true && st.settings.screeners.length === 0 && /On, but no screener is chosen yet/.test(w.text()) && /Autopilot switched on\. Tick at least one screener below for it to start\./.test(w.text()) && /id="ap-run"[^>]*disabled title="Tick at least one screener first"/.test(w.container.innerHTML), w.text().slice(0, 260));
  }
  check('no broken values', !/undefined|NaN|\[object/.test(p.container.innerHTML), (p.container.innerHTML.match(/.{30}(undefined|NaN|\[object).{30}/) || [])[0]);
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
})();
