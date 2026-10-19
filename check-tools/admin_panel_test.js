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
  check('it shows the month\'s goal with each figure against its target', /Month 1: in profit/.test(text) && /Finished trades in all 51/.test(text) && /target 100/.test(text) && /-1\.19%/.test(text) && (/\$99,334/.test(text) || /The practice account \(getting the latest prices\)/.test(text)) && /not forecasts/.test(text));
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
  check('before the Practice portfolio has its prices the account is not shown as a figure that changes a second later: "…" while the prices come', /Practice account … getting the latest prices/.test(plain()) && !/\$99,334/.test(plain()), plain().slice(0, 300));
  p.ctx.window.practicePortfolio = { figures: () => ({ accountValue: 99643.23, gainUsd: -356.77, gainPct: -0.36, startingCash: 100000 }) }; p.fire('practice-portfolio:figures');
  check('once it has them the Admin page shows the very figure the Practice portfolio tab shows, at the latest prices', /\$99,643/.test(plain()) && !/\$99,334/.test(plain()) && /▼ \$357 since the start/.test(plain()) && /The practice account, at the latest prices/.test(plain()) && !/an estimate/.test(plain()), plain().slice(0, 300));
  { const q = await page(200, 'dave@x.com'); await new Promise(r => setTimeout(r, 8300)); const pl = () => q.panel.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    check('if the prices never come, after a few seconds the function\'s estimate is shown, said to be one', /\$99,334/.test(pl()) && /an estimate: the latest prices did not come in/.test(pl()), pl().slice(0, 300)); }
  { const q = await page(200, 'dave@x.com'); const pl = q.panel.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    check('the settings chips name the level in words and leave out the AI review switch (always off now)', !/Level \d/.test(pl) && !/AI review's early sales/.test(pl) && /(Cautious|Careful|Balanced|Bold|Adventurous) level/.test(pl), pl.slice(pl.indexOf('Autopilot on'), pl.indexOf('Autopilot on') + 200)); }
  { const q = await page(200, 'dave@x.com'); const pl = () => q.panel.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    check('the AWS figures have a Refresh now button and say how often they are read by themselves', /data-ad="usage"/.test(q.panel.innerHTML) && /↻ Refresh now/.test(pl()) && /reads both about once a day/.test(pl()) && /Both are free to read/.test(pl()) && /calls read just now/.test(pl()));
    await q.click({ 'data-ad': 'usage' });
    check('pressing it asks the function for the figures (op usage) and says what was read', q.sent.at(-1).op === 'usage' && /Read just now, free/.test(pl()), q.sent.at(-1)); }
  if (/function auditHtml/.test(fs.readFileSync(process.argv[2], 'utf8'))) {
    ADMIN.plan = Object.assign({}, ADMIN.plan, { audit: { at: '2026-10-18T11:00:00Z', problems: 1, ideas: 1, new: 1, gone: 2, findings: [
      { check: 'seo-basics', level: 'problem', text: 'no meta description', where: 'analysis.html', new: true },
      { check: 'stock-links', level: 'idea', text: 'the guides link to no stock page', where: 'guides', new: false }] } });
    const q = await page(200, 'dave@x.com'); const pl = q.panel.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    check('the Overview has the nightly site check: its problems on show, new ones marked, the ideas folded, what was put right', /Site check/.test(pl) && /1 problem, 1 idea · 1 new · 2 put right/.test(pl)
      && /problem new no meta description analysis\.html/.test(pl) && /1 idea idea the guides link to no stock page/.test(pl), pl.slice(pl.indexOf('Site check') + 250, pl.indexOf('Site check') + 700));
  }
  { // What changed lately, and Answered straight under Decisions for you (18 Oct 2026)
    ADMIN.plan = Object.assign({}, ADMIN.plan, { changes: Array.from({ length: 7 }, (_, i) => ({ at: '2026-10-18', what: 'Change number ' + (i + 1) })) });
    ADMIN.answered = Array.from({ length: 5 }, (_, i) => ({ id: 20 + i, title: 'Answered item ' + (i + 1), status: 'done', answered: '2026-10-18T10:00:00Z' }));
    const q = await page(200, 'dave@x.com'); const h = q.panel.innerHTML, pl = h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    if (typeof check === 'function') {
      check('What changed lately shows the latest five and folds the rest', /What changed lately/.test(pl) && /Change number 5/.test(pl) && /2 earlier/.test(pl), pl.slice(pl.indexOf('What changed'), pl.indexOf('What changed') + 300));
      check('Answered comes straight after Decisions for you, before the site check and the goal, the latest three on show', h.indexOf('ad-answered') > h.indexOf('Decisions for you') && h.indexOf('ad-answered') < h.indexOf('ad-changes') && /2 earlier/.test(pl) && /Answered item 3/.test(pl));
    }
  }
  if (/costStockiq/.test(fs.readFileSync(process.argv[2], 'utf8'))) { // the bill split (19 Oct 2026)
    const keep = ADMIN.usage;
    ADMIN.usage = Object.assign({}, keep, { cost: 3.24, costStockiq: 0.48, costStockiqForecast: 0.77, costExplorer: 2.65, costExplorerKnown: 2.65, costOther: 0.11,
      costServices: { AWSCostExplorer: 2.65, AmazonDynamoDB: 0.28, AmazonS3: 0.18, AmazonCloudWatch: 0.02, AWSLambda: 0.0, AmazonCloudFront: 0.0 } });
    let q = await page(200, 'dave@x.com'); let h = q.panel.innerHTML, pl = h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    const bill = pl.slice(pl.indexOf('AWS this month'), pl.indexOf('AWS this month') + 1200);
    check('the whole AWS bill comes first, then StockIQ\'s part of it, then its running cost against the cost rule', /Your whole AWS bill this month so far: \$3\.24/.test(bill) && /StockIQ's part of it: \$3\.13/.test(bill)
      && /StockIQ's running cost: \$0\.48, on course for about \$0\.77 for the month/.test(bill) && /the cost rule: under \$1 a month/.test(bill) && bill.indexOf('whole AWS bill') < bill.indexOf("StockIQ's part"), bill);
    check('and each figure is explained: the whole bill split, the one-off Cost Explorer charge, every service with its cost and the free ones named', /Whole bill \$3\.24 = StockIQ \$3\.13 \+ your other projects \$0\.11/.test(bill)
      && /StockIQ \$3\.13 = \$2\.65 for Cost Explorer \(a one-off: about 265/.test(bill) && /DynamoDB \(the database\) \$0\.28, S3 \(file storage\) \$0\.18, CloudWatch \(logs\) \$0\.02/.test(bill) && /still inside the free allowances: (Lambda, CloudFront|CloudFront, Lambda)/.test(bill), bill);
    ADMIN.usage = Object.assign({}, ADMIN.usage, { costExplorer: 3.10 });
    q = await page(200, 'dave@x.com'); h = q.panel.innerHTML; pl = h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    check('a Cost Explorer charge beyond the known one is shown in red', /ad-pill bad">Cost Explorer is being asked again: \$0\.45 more/.test(h), pl.slice(pl.indexOf('AWS this month'), pl.indexOf('AWS this month') + 400));
    ADMIN.usage = keep;
  }
  if (/function confidenceHtml/.test(fs.readFileSync(process.argv[2], 'utf8'))) { // the confidence line (19 Oct 2026)
    const show = async (versus) => { const q = await page(200, 'dave@x.com'); q.ctx.window.practicePortfolio = { figures: () => ({ accountValue: 99856, gainUsd: -144, gainPct: -0.14, startingCash: 100000, versus }) }; q.fire('practice-portfolio:figures'); return q.panel.innerHTML.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' '); };
    let pl = await show({ days: 4, ahead: 3, avg: 0.63, se: 0.48 });
    check('under 30 trading days it says too early to tell, with the days so far and no percentage', /Ahead of an S&P 500 fund so far: how sure the record is Too early to tell 4 of 30 trading days/.test(pl) && /ahead of the fund on 3 of 4 days/.test(pl) && !/\d+% is how sure/.test(pl), pl.slice(pl.indexOf('Ahead of an S&P'), pl.indexOf('Ahead of an S&P') + 300));
    pl = await show({ days: 40, ahead: 26, avg: 0.2, se: 0.08 });
    check('with 30 days or more a level and how sure, said to be about the past only', /how sure the record is High 9[6-9]%/.test(pl) && /on 26 of 40 trading days, by \+0\.20% a day on average/.test(pl) && /not a forecast/.test(pl), pl.slice(pl.indexOf('Ahead of an S&P'), pl.indexOf('Ahead of an S&P') + 400));
    pl = await show({ days: 40, ahead: 18, avg: -0.05, se: 0.1 });
    check('a record behind the fund reads Low', /how sure the record is Low 3\d%/.test(pl), pl.slice(pl.indexOf('Ahead of an S&P'), pl.indexOf('Ahead of an S&P') + 200));
  }
  console.log(ok ? 'ALL PASS' : 'SOME FAILED'); process.exit(ok ? 0 : 1);
})();
