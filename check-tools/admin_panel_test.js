// The Admin page's script (website/admin-panel.js) against a stand-in for the autopilot's function: hidden for an account
// that is not one of the site's own, drawn for one that is, and "Yes" / "Not now" / "Write it now" send the right questions.
//   node check-tools/admin_panel_test.js <admin-panel.js>
const vm = require('vm'), fs = require('fs');
let ok = true; const check = (name, cond, info) => { console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + JSON.stringify(info))); if (!cond) ok = false; };
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const ADMIN = { usage: { at: new Date().toISOString(), cost: 0.56, calls: 451952, yesterday: 5182, free: 1000000, forecast: 853432 }, goal: { name: 'Month 1: in profit', due: '2026-11-12', daysLeft: 26, trades: 51, tradesGoal: 100, avg: -1.19, se: 0.42, n: 47, avgGoal: 0, value: 99334, valueGoal: 100000, met: false },
  review: { at: '2026-10-17T05:10:00Z', lines: ['Last 7 days: 39 trades finished.', 'Clearly losing: sales by the AI review, 31 trades.'] }, nextReview: '2026-10-24T05:10:00Z', plan: { at: '2026-10-17T06:00:00Z', parts: 44, reviewed: 3, reviews: [{ part: 'The bell', at: '2026-10-17', found: 'Polls less often.' }], items: [
    { id: 'trend', what: 'Trend score for every screener', angle: 'profit', measure: 'Top 10 against the list', status: 'running', started: '2026-10-15', decide: '2026-11-12', public: true },
    { id: 'mood', what: 'Hold fewer when the index is weak', angle: 'profit', measure: 'replay', status: 'idea', order: 1 },
    { id: 'ais', what: 'AI review early sales', angle: 'profit', measure: 'after', status: 'removed', decided: '2026-10-17', result: 'Lost money.', public: true },
    { id: 'old1', what: 'Old one A', angle: 'cost', measure: 'x', status: 'kept', decided: '2026-10-12', result: 'ok' },
    { id: 'old2', what: 'Old one B', angle: 'cost', measure: 'x', status: 'kept', decided: '2026-10-11', result: 'ok' },
    { id: 'old3', what: 'Old one C', angle: 'cost', measure: 'x', status: 'kept', decided: '2026-10-10', result: 'ok' }] },
  health: { at: new Date().toISOString(), ran: 1, on: 1, accounts: 2, paused: 0, waiting: 0, failed: 0 },
  open: [{ id: 3, key: 'aiSell-off', title: 'Switch off "Sell early on the AI model\'s review"', why: 'Its sales lose money.', kind: 'setting', status: 'open' }, { id: 4, key: 'goal-x', title: 'Month 1 at risk', why: 'Look at it.', kind: 'session', status: 'open' }],
  answered: [], settings: { enabled: true, risk: 3, holdings: 50, budgetUsd: 92786, everyHours: 3, maxHoldDays: 10, aiSell: true, selfTune: true }, screeners: ['S&P 500', 'ASX 200'] };
async function page(status, uid) {
  const els = {}, sent = [], listeners = {}; let clickHandler = null;
  const panel = { innerHTML: '', id: 'admin-panel' }, tab = { hidden: true }, menu = { children: [], firstChild: null, insertBefore(a) { this.children.unshift(a); } };
  const document = { readyState: 'complete', head: { appendChild() {} }, getElementById: id => id === 'admin-panel' ? panel : id === 'account-dropdown' ? menu : id === 'admin-link' ? (menu.children.find(c => c.id === 'admin-link') || null) : (els[id] || null),
    querySelector: sel => sel === '[data-dash-tab="admin"]' ? tab : null, createElement: () => ({}), addEventListener: (t, f) => { if (t === 'click') clickHandler = f; else listeners[t] = f; } };
  const shown = [];
  const ctx = { document, window: {}, location: { hash: '' }, localStorage: { getItem: k => k === 'userId' ? uid : null }, console, setTimeout, Date, JSON, Math, Number, String, Object, Array, isNaN, isFinite, Promise,
    fetch: async (url, opt) => { const b = JSON.parse(opt.body); sent.push(b); const answer = Object.assign({}, ADMIN);
      if (b.op === 'answer') { answer.open = ADMIN.open.filter(p => p.id !== b.id); answer.answered = [Object.assign({}, ADMIN.open.find(p => p.id === b.id), { status: b.answer === 'no' ? 'no' : b.id === 3 ? 'done' : 'yes', answered: new Date().toISOString() })]; }
      return { ok: status === 200, status, json: async () => status === 200 ? { success: true, admin: answer } : { success: false, error: 'Not available for this account.' } }; } };
  ctx.window = ctx; ctx.window.dashboardTabs = { show: n => shown.push(n) }; ctx.window.practiceAutopilot = { reload: () => shown.push('reloaded') };
  vm.createContext(ctx); vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx); await sleep(30);
  const click = async (attrs) => { clickHandler({ target: { closest: () => ({ getAttribute: k => attrs[k] === undefined ? null : attrs[k] }) }, preventDefault() {} }); await sleep(30); };
  return { panel, tab, menu, sent, click, shown, ctx, fire: t => listeners[t] && listeners[t]() };
}
(async () => {
  let p = await page(403, 'someone@else.com');
  check('for an account that is not one of the site\'s own nothing is shown: no tab, no menu link, an empty panel', p.tab.hidden === true && p.menu.children.length === 0 && p.panel.innerHTML === '' && p.sent.length === 1 && p.sent[0].action === 'admin');
  p = await page(200, 'dave@x.com');
  const h = p.panel.innerHTML, text = h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  check('for the owner the tab and the "Admin" link in the Account menu appear', p.tab.hidden === false && p.menu.children.length === 1 && p.menu.children[0].href === 'dashboard.html#admin');
  check('it shows the month\'s goal with each figure against its target', /Month 1: in profit/.test(text) && /Finished trades in all 51/.test(text) && /target 100/.test(text) && /-1\.19%/.test(text) && /\$99,334/.test(text) && /not forecasts/.test(text));
  check('what needs a yes: each proposal with its reason, what a yes does, and the two buttons', /Decisions for you/.test(text) && !/Needs your yes/.test(text) && /applied the moment you say yes/.test(text) && /done in your next session/.test(text) && (h.match(/data-ad-answer="yes"/g) || []).length === 2 && (h.match(/data-ad-answer="no"/g) || []).length === 2);
  check('the weekly review and how it is running', /Weekly review/.test(text) && /Clearly losing: sales by the AI review/.test(text) && /Write a fresh one now/.test(text) && /You never need to press this/.test(text) && /No errors\./.test(text) && /AWS bill this month so far: \$0\.56/.test(text) && /Lambda calls: 451,952 of 1,000,000 free \(45%\)/.test(text) && /on course for about 853k this month/.test(text) && /Show the 2 screeners it buys from/.test(text) && /probably between -2\.03% and -0\.35%/.test(text));
  await p.click({ 'data-ad-answer': 'yes', 'data-ad-id': '3' });
  check('"Yes" to a setting sends the answer, says it is done, and the autopilot panel is reloaded', p.sent.at(-1).op === 'answer' && p.sent.at(-1).id === 3 && p.sent.at(-1).answer === 'yes' && /Done: Switch off/.test(p.panel.innerHTML) && p.shown.includes('reloaded'), p.sent.at(-1));
  await p.click({ 'data-ad-answer': 'yes', 'data-ad-id': '4' });
  check('"Yes" to something that needs code says the next session will do it', /is for your next session/.test(p.panel.innerHTML));
  await p.click({ 'data-ad-answer': 'no', 'data-ad-id': '3' });
  check('"Not now" is sent as no', p.sent.at(-1).answer === 'no' && /Left as it is/.test(p.panel.innerHTML));
  await p.click({ 'data-ad': 'review' });
  check('"Write it now" asks for a review', p.sent.at(-1).op === 'review' && /The review is written from the latest figures/.test(p.panel.innerHTML));
  { const q = await page(200, 'dave@x.com'); const pl = () => q.panel.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    check('the Overview has a short Improvements card: the counts, what is tested, the latest three done, and a way to the full list', /1 being tested · 1 next · 3 kept · 1 taken out/.test(pl()) && /Testing: Trend score/.test(pl()) && /Taken out: AI review early sales/.test(pl()) && /Old one B/.test(pl()) && !/Old one C/.test(pl()) && !/Hold fewer/.test(pl()) && /See every improvement/.test(pl()), pl().slice(0, 400));
    await q.click({ 'data-ad-view': 'improvements' });
    check('the Improvements view has the whole list: next, every one done, the parts reviewed, and which users see', /Next, in order/.test(pl()) && /Hold fewer/.test(pl()) && /Old one C/.test(pl()) && /Parts of the site reviewed lately/.test(pl()) && /users see it/.test(pl()) && !/Needs your yes/.test(pl()));
    await q.click({ 'data-ad-view': 'overview' });
    check('and back to the Overview', /Decisions for you/.test(pl()) && !/Next, in order/.test(pl())); }
  p = await page(200, 'dave@x.com');
  const plain = () => p.panel.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  check('before the Practice portfolio has its prices the account is the function\'s estimate, and says so', /\$99,334/.test(plain()) && /an estimate until the prices are in/.test(plain()));
  p.ctx.window.practicePortfolio = { figures: () => ({ accountValue: 99643.23, gainUsd: -356.77, gainPct: -0.36, startingCash: 100000 }) }; p.fire('practice-portfolio:figures');
  check('once it has them the Admin page shows the very figure the Practice portfolio tab shows, at the latest prices', /\$99,643/.test(plain()) && !/\$99,334/.test(plain()) && /▼ \$357 since the start/.test(plain()) && /The practice account, at the latest prices/.test(plain()) && !/an estimate/.test(plain()), plain().slice(0, 300));
  { const q = await page(200, 'dave@x.com'); const pl = q.panel.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    check('the settings chips name the level in words and leave out the AI review switch (always off now)', !/Level \d/.test(pl) && !/AI review's early sales/.test(pl) && /(Cautious|Careful|Balanced|Bold|Adventurous) level/.test(pl), pl.slice(pl.indexOf('Autopilot on'), pl.indexOf('Autopilot on') + 200)); }
  console.log(ok ? 'ALL PASS' : 'SOME FAILED'); process.exit(ok ? 0 : 1);
})();
