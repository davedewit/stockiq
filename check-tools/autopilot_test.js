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
  p.form({ ...settings, enabled: true, risk: 5, budgetUsd: 5000, periodDays: 5, everyHours: 12, maxHoldDays: 10, screeners: ['3-8', '7-1'] }); p.click('save'); await sleep(30);
  const sent = p.calls.find(c => c.action === 'save');
  check('saves exactly what was set', JSON.stringify(sent.settings) === JSON.stringify({ enabled: true, risk: 5, budgetUsd: 5000, periodDays: 5, everyHours: 12, maxHoldDays: 10, screeners: ['3-8', '7-1'] }) && /Autopilot switched on/.test(p.text()) && /On\. First check-in at the next hourly check\. Stock screeners are checked on weekdays/.test(p.text()) && /Adventurous/.test(p.text()) && !/data-ap="run"[^>]*disabled/.test(p.container.innerHTML), sent);
  p.form({ ...stored.settings, screeners: [] }); p.click('save'); await sleep(30); check('needs at least one screener', /Choose at least one screener/.test(p.text()) && p.calls.filter(c => c.action === 'save').length === 1);
  p.form(stored.settings); p.click('run'); await sleep(30);
  check('check in now: shows what happened and refreshes the portfolio', /Checked in: 1 bought, 1 sold/.test(p.text()) && /Bought COP with \$1,250\. Rank 1 with &lt;b&gt;RSI 66&lt;\/b&gt;/.test(p.text()) && /Sold AMT \. Up \+18\.2%/.test(p.text()) && p.ctx.practicePortfolio.reloaded === 1 && /Last check-in/.test(p.text()) && !/<b>RSI/.test(p.container.innerHTML), p.text().slice(-500));
  stored.fail = true; p.form(stored.settings); p.click('run'); await sleep(30); check('too soon: says so', /checked in a moment ago/.test(p.text()));
  check('no broken values', !/undefined|NaN|\[object/.test(p.container.innerHTML), (p.container.innerHTML.match(/.{30}(undefined|NaN|\[object).{30}/) || [])[0]);
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
})();
