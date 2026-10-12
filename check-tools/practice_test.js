// Drives the real practice-portfolio.js in a stand-in page: real prices and name search, an in-memory copy of the storage API.
const vm = require('vm'), fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
// --- pure sums first
const pure = (() => { const m = { exports: {} }; vm.runInNewContext(src, { module: m, console, practiceTradeCostPct: 0 }); return m.exports; })();
let ok = true; const check = (name, cond, extra) => { ok = ok && !!cond; console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + JSON.stringify(extra))); };
if (pure.valueSeries) {      // the graph of the account over time (a copy of the script from before 12 Oct 2026 has none)
  const T = (s) => Date.parse(s), DAY = 86400, near = (a, b, e) => Math.abs(a - b) < (e || 0.01);
  // a stock: bars at 13:30 UTC, the last one still running; the quote is its figure
  const stock = pure.seriesOf({ timestamp: [1, 2, 3].map(d => T('2026-10-0' + (d + 4) + 'T13:30:00Z') / 1000), indicators: { quote: [{ close: [100, 102, 101] }] }, meta: { regularMarketTime: T('2026-10-07T15:00:00Z') / 1000, regularMarketPrice: 105 } }, 'AAA');
  check('daily prices of a share: each close six and a half hours after its bar, the running session from the quote', stock.length === 3 && stock[0][0] === T('2026-10-05T20:00:00Z') && stock[1][1] === 102 && stock[2][0] === T('2026-10-07T15:00:00Z') && stock[2][1] === 105, stock);
  const twice = pure.seriesOf({ timestamp: [T('2026-10-08T23:00:00Z') / 1000, T('2026-10-09T05:20:39Z') / 1000], indicators: { quote: [{ close: [60, 60] }] }, meta: { regularMarketTime: T('2026-10-09T05:20:39Z') / 1000, regularMarketPrice: 60 } }, 'BHP.AX');
  check('a session sent twice counts once', twice.length === 1 && twice[0][1] === 60, twice);
  const coin = pure.seriesOf({ timestamp: [T('2026-10-09T00:00:00Z') / 1000, T('2026-10-10T00:00:00Z') / 1000, T('2026-10-11T00:00:00Z') / 1000], indicators: { quote: [{ close: [10, 11, null] }] }, meta: { regularMarketTime: T('2026-10-11T06:00:00Z') / 1000, regularMarketPrice: 12 } }, 'XYZ-USD');
  check('a coin closes a day after its bar starts', coin.length === 3 && coin[0][0] === T('2026-10-10T00:00:00Z') && coin[1][0] === T('2026-10-11T00:00:00Z') && coin[2][1] === 12, coin);
  check('a value between two known points lies on the straight line', near(pure.valueAt([[0, 10], [10, 20]], 5), 15) && pure.valueAt([[0, 10]], -1) === null && pure.valueAt([[0, 10], [10, 20]], 99) === 20);

  // an account: one share bought and sold by the autopilot, one coin bought by hand and still held
  const st = pure.newState('2026-10-01T00:00:00Z');
  const a = pure.applyBuy(st, { symbol: 'AAA', currency: 'USD', price: 100, fx: 1, spy: 700, amountUsd: 1000, now: '2026-10-02T00:00:00Z' }); a.by = 'ai';
  pure.applySell(st, a.id, { price: 110, fx: 1, spy: 700, now: '2026-10-04T00:00:00Z' });
  pure.applyBuy(st, { symbol: 'XYZ-USD', currency: 'USD', price: 10, fx: 1, spy: 700, amountUsd: 2000, now: '2026-10-05T00:00:00Z' });
  const quotes = { 'XYZ-USD': { price: 12, series: [[T('2026-10-06T00:00:00Z'), 9], [T('2026-10-07T00:00:00Z'), 11], [T('2026-10-08T00:00:00Z'), 12]] }, SPY: { price: 700 } };
  const now = T('2026-10-08T00:00:00Z'), s = pure.valueSeries(st, quotes, now, null), at = (iso) => s.points.reduce((best, p) => Math.abs(p.t - T(iso)) < Math.abs(best.t - T(iso)) ? p : best);
  const sums = pure.summarize(st, quotes), last = s.points[s.points.length - 1];
  check('the graph ends on the account value the card shows', near(last.value, sums.accountValue) && near(last.all, sums.gainUsd) && last.t === now, [last, sums.accountValue]);
  check('it starts at the starting cash, when the account began', near(s.points[0].value, 100000) && s.points[0].t === T('2026-10-01T00:00:00Z') && near(s.undated, 0), s.points[0]);
  check('nothing moves before the first buy', near(at('2026-10-01T18:00:00Z').all, 0));
  check('a sold holding: half way between buying and selling it shows half its result, afterwards all of it', near(at('2026-10-03T00:00:00Z').ai, 50, 2) && near(at('2026-10-04T12:00:00Z').ai, 100) && near(at('2026-10-07T00:00:00Z').ai, 100), [at('2026-10-03T00:00:00Z'), at('2026-10-04T12:00:00Z')]);
  check('a holding still held follows its daily prices', near(at('2026-10-06T00:00:00Z').own, 200 * 9 - 2000) && near(at('2026-10-07T00:00:00Z').own, 200 * 11 - 2000) && near(last.own, 400), [at('2026-10-06T00:00:00Z'), last]);
  check('the user\'s part and the autopilot\'s add up to the whole, at every point', s.points.every(p => near(p.own + p.ai, p.all, 1e-6)) && s.anyAi);
  check('points are in time order and include the moments of buying and selling', s.points.every((p, i) => !i || p.t > s.points[i - 1].t) && [ '2026-10-02T00:00:00Z', '2026-10-04T00:00:00Z', '2026-10-05T00:00:00Z' ].every(iso => s.points.some(p => p.t === T(iso))));
  // the sold list cleared: its result has no dates left
  const cleared = JSON.parse(JSON.stringify(st)); pure.applyClearSold(cleared, null);
  const c = pure.valueSeries(cleared, quotes, now, 100);
  check('a cleared sold list: its result is counted from the start and said so, and stays the autopilot\'s', near(c.undated, 100) && near(c.undatedAi, 100) && near(c.points[0].all, 100) && near(c.points[c.points.length - 1].all, sums.gainUsd) && near(c.points[0].ai, 100), [c.undated, c.undatedAi, c.points[0]]);
  // a shorter stretch
  const week = pure.valueSeries(st, quotes, now, null, T('2026-10-06T00:00:00Z'));
  check('a shorter stretch starts where asked and ends on the same figure', week.points[0].t === T('2026-10-06T00:00:00Z') && near(week.points[0].all, 100 + 200 * 9 - 2000) && near(week.points[week.points.length - 1].all, sums.gainUsd), week.points[0]);
  // a holding in another currency uses that day's exchange rate
  const yen = pure.newState('2026-10-01T00:00:00Z'); pure.applyBuy(yen, { symbol: '7203.T', currency: 'JPY', price: 3000, fx: 1 / 150, spy: 700, amountUsd: 3000, now: '2026-10-02T00:00:00Z' });
  const yq = { '7203.T': { price: 3000, series: [[T('2026-10-03T06:00:00Z'), 3000], [T('2026-10-06T06:00:00Z'), 3000]] }, 'USDJPY=X': { price: 150, series: [[T('2026-10-03T06:00:00Z'), 160], [T('2026-10-06T06:00:00Z'), 150]] }, SPY: { price: 700 } };
  const ys = pure.valueSeries(yen, yq, T('2026-10-06T06:00:00Z'), null), day3 = ys.points.find(p => p.t === T('2026-10-03T06:00:00Z'));
  check('a yen holding is turned into dollars at that day\'s rate', day3 && near(day3.all, 150 * 3000 / 160 - 3000, 0.5), day3);
  // the picture
  const pic = pure.chartSvg(s, 'value', 700, 220), gains = pure.chartSvg(s, 'ai', 360, 180);
  check('the picture: one point placed per figure, left to right, inside the frame', pic.placed.length === s.points.length && pic.placed.every((p, i) => p.x >= 0 && p.x <= 700 && p.y >= 0 && p.y <= 220 && (!i || p.x >= pic.placed[i - 1].x)) && /<path class="pp-line" d="M/.test(pic.svg) && pic.base === 100000, pic.placed.slice(0, 2));
  check('the picture of one part is measured against zero and says so for a screen reader', gains.base === 0 && /aria-label="The autopilot/.test(gains.svg) && gains.width === 360 && !/NaN|undefined/.test(pic.svg + gains.svg));
  const flat = pure.valueSeries(pure.newState('2026-10-01T00:00:00Z'), {}, now, null);
  check('an account with nothing in it is a level line, not an error', flat.lots === 0 && flat.points.every(p => p.value === 100000) && !/NaN/.test(pure.chartSvg(flat, 'value', 700, 220).svg));
  // how long until the US stock market opens (New York was on summer time, four hours behind UTC, on these days)
  check('US market: nine and a half hours before a Monday opening, as the sidebar counts it', pure.usOpensIn(Date.parse('2026-10-12T04:00:00Z')) === '9h 30m', pure.usOpensIn(Date.parse('2026-10-12T04:00:00Z')));
  check('US market: open during the session, and Friday evening counts to Monday morning', pure.usOpensIn(Date.parse('2026-10-12T15:00:00Z')) === null && pure.usOpensIn(Date.parse('2026-10-09T21:00:00Z')) === '64h 30m' && pure.usOpensIn(Date.parse('2026-10-10T13:30:00Z')) === '48h 0m', [pure.usOpensIn(Date.parse('2026-10-09T21:00:00Z')), pure.usOpensIn(Date.parse('2026-10-10T13:30:00Z'))]);
  const ticks = pure.axisTicks(99870, 100130, 4).ticks;
  check('axis figures are round numbers', ticks.length >= 3 && ticks.every(v => v % 50 === 0), ticks);
}
{
  const st = pure.newState('2026-10-10T00:00:00Z');
  const h = pure.applyBuy(st, { symbol: 'IMB.L', currency: 'GBp', price: 2662, fx: 1.3233 / 100, spy: 778.57, amountUsd: 1000, now: '2026-10-10T00:00:00Z' });
  check('pence buy: quantity', Math.abs(h.qty - 1000 / (2662 * 0.013233)) < 1e-9 && st.cash === 99000, h);
  const q = { 'IMB.L': { price: 2795.1 }, 'GBPUSD=X': { price: 1.3233 }, SPY: { price: 794.14 } };
  const v = pure.valueOf(h, q); check('pence holding +5% in value', Math.abs(v.changePct - 5) < 0.01, v);
  const s = pure.summarize(st, q); check('summary adds up', Math.abs(s.accountValue - (99000 + 1050)) < 0.02 && Math.abs(s.marketPct - 2) < 0.01 && Math.abs(s.gainPct - 0.05) < 0.001, s);
  const q2 = { 'IMB.L': { price: 2662 }, 'GBPUSD=X': { price: 1.3233 * 1.1 } }; check('currency move alone changes the dollar value', Math.abs(pure.valueOf(h, q2).changePct - 10) < 0.01);
  check('no quote: shown at cost', pure.valueOf(h, {}).priced === false && pure.valueOf(h, {}).valueUsd === 1000);
  let err = ''; try { pure.applyBuy(st, { symbol: 'AAPL', price: 300, fx: 1, amountUsd: 99000.5, now: '2026-10-10T00:00:00Z' }); } catch (e) { err = e.message; } check('cannot spend more than the cash', /Not enough/.test(err), err);
  try { pure.applyBuy(st, { symbol: 'AAPL', price: 0, fx: 1, amountUsd: 10, now: '2026-10-10T00:00:00Z' }); err = ''; } catch (e) { err = e.message; } check('no price, no buy', /No price/.test(err), err);
  const proceeds = pure.applySell(st, h.id, { price: 2795.1, fx: 0.013233, spy: 794.14, now: '2026-10-11T00:00:00Z' });
  check('sell returns the money', Math.abs(proceeds - 1050) < 0.01 && Math.abs(st.cash - 100050) < 0.01 && st.holdings.length === 0 && st.closed.length === 1, { proceeds, cash: st.cash });
  { const s2 = pure.newState('2026-10-10T00:00:00Z');
    const a1 = pure.applyBuy(s2, { symbol: 'AAA', price: 10, fx: 1, spy: 100, amountUsd: 1000, now: '2026-10-10T00:00:00Z' }), b1 = pure.applyBuy(s2, { symbol: 'BBB', price: 10, fx: 1, spy: 100, amountUsd: 1000, now: '2026-10-10T00:00:00Z' });
    const live = pure.summarize(s2, { AAA: { price: 11 }, BBB: { price: 10.1 }, SPY: { price: 102 } }); check('a holding that has not moved is not judged against the market', pure.versusMarket(0, 0) === null && pure.versusMarket(0.01, -0.02) === null && pure.summarize(s2, { AAA: { price: 10 }, BBB: { price: 10 }, SPY: { price: 100 } }).compared === 0);
    check('ahead, behind and level are told apart', pure.versusMarket(3, 1) === 'ahead' && pure.versusMarket(-1, 2) === 'behind' && pure.versusMarket(2.02, 2) === 'level' && pure.versusMarket(0, 1.5) === 'behind' && pure.summarize(s2, { AAA: { price: 10.2 }, BBB: { price: 10 }, SPY: { price: 102 } }).level === 1);
    check('ahead-of-market count on open holdings', live.compared === 2 && live.ahead === 1, live);
    pure.applySell(s2, a1.id, { price: 11, fx: 1, spy: 102, now: '2026-10-12T00:00:00Z' }); pure.applySell(s2, b1.id, { price: 10.1, fx: 1, spy: 102, now: '2026-10-12T00:00:00Z' });
    const ss = pure.soldSummary(s2); check('sold summary adds up', ss.count === 2 && ss.cost === 2000 && Math.abs(ss.proceeds - 2110) < 0.01 && Math.abs(ss.gainPct - 5.5) < 0.01 && ss.compared === 2 && ss.ahead === 1, ss);
    const cashBefore = s2.cash; check('clearing one sold line', pure.applyClearSold(s2, a1.id) === 1 && s2.closed.length === 1 && s2.closed[0].symbol === 'BBB' && s2.cash === cashBefore);
    check('clearing the whole sold list', pure.applyClearSold(s2, null) === 1 && s2.closed.length === 0 && s2.cash === cashBefore && pure.soldSummary(s2).gainPct === null && pure.applyClearSold(s2, null) === 0); }
  { const yen = pure.fxFor('JPY'), pence = pure.fxFor('GBp'), aud = pure.fxFor('AUD');
    check('exchange rates: yen from the per-dollar quote, pence and Australian dollars direct', yen.symbol === 'USDJPY=X' && Math.abs(pure.fxRate(yen, 158.246) - 0.0063193) < 1e-7 && pence.symbol === 'GBPUSD=X' && Math.abs(pure.fxRate(pence, 1.3233) - 0.013233) < 1e-9 && aud.symbol === 'AUDUSD=X' && pure.fxRate(aud, 0.6988) === 0.6988 && pure.fxRate(pure.fxFor('USD'), 0) === 1 && pure.fxRate(yen, 0) === null, [yen, pence, aud]);
    const st = pure.newState('x'); const h = pure.applyBuy(st, { symbol: '7203.T', currency: 'JPY', price: 2910.5, fx: pure.fxRate(yen, 158.246), amountUsd: 1000, now: '2026-10-10T00:00:00Z' });
    check('a yen holding is valued with the same precise rate', Math.abs(pure.valueOf(h, { '7203.T': { price: 2910.5 }, 'USDJPY=X': { price: 158.246 } }).changePct) < 1e-9 && Math.abs(pure.valueOf(h, { '7203.T': { price: 2910.5 }, 'USDJPY=X': { price: 156.6792 } }).changePct - 1.0) < 0.001); }
  check('formatting', pure.usd(-1234.5) === '-$1,234.50' && pure.money(2662, 'GBp') === '2662.00p' && pure.money(60.94, 'AUD') === 'A$60.940' && pure.esc('<b>"x"') === '&lt;b&gt;&quot;x&quot;');
}
// --- the page
const store = {}; const apiCalls = [];
const els = {}; const handlers = {};
const mkEl = id => ({ id, value: '', innerHTML: '', style: {}, textContent: '', disabled: false });
const container = mkEl('practice-portfolio');
const document = { readyState: 'complete', getElementById: id => id === 'practice-portfolio' ? container : (els[id] || (els[id] = mkEl(id))), addEventListener: (t, f) => { (handlers[t] = handlers[t] || []).push(f); }, querySelector: () => null };
async function fakeFetch(url, opts = {}) {
  const u = String(url);
  if (u.includes('__PRACTICE_API_URL__')) {
    const b = JSON.parse(opts.body); apiCalls.push(b.action);
    const json = (status, o) => ({ ok: status === 200, status, json: async () => o });
    const cur = store[b.userId];
    if (b.action === 'get') return json(200, { success: true, portfolio: cur ? JSON.parse(cur.data) : null, version: cur ? cur.version : 0 });
    if (b.action === 'save') { if (cur && cur.version !== b.expectedVersion) return json(409, { error: 'Changed in another window', conflict: true }); if (!cur && b.expectedVersion !== 0 && false) return json(409, {}); store[b.userId] = { data: JSON.stringify(b.portfolio), version: b.expectedVersion + 1 }; return json(200, { success: true, version: b.expectedVersion + 1 }); }
    if (b.action === 'reset') { delete store[b.userId]; return json(200, { success: true }); }
  }
  return fetch(url, opts);
}
const ctx = { window: {}, document, localStorage: { getItem: k => k === 'userId' ? 'tester@example.com' : null }, fetch: fakeFetch, console, setTimeout, clearTimeout, confirm: () => true, alert: m => { ctx.lastAlert = m; }, Date, Math, JSON, Promise, parseFloat, isNaN, encodeURIComponent, Object, String, Set };
ctx.window = ctx; ctx.practiceTradeCostPct = 0; vm.createContext(ctx); vm.runInContext(src, ctx);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const click = (action, attrs = {}) => handlers.click.forEach(f => f({ target: { closest: sel => sel === '[data-pp]' ? { getAttribute: k => k === 'data-pp' ? action : attrs[k], tagName: 'BUTTON', style: {} } : null }, preventDefault() {} }));
const text = () => container.innerHTML.replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/\s+/g, ' ');
const bad = () => (container.innerHTML.match(/undefined|NaN|\[object|Infinity/g) || []);
const waitIdle = async () => { for (let i = 0; i < 120; i++) { await sleep(250); if (!/data-pp="buy"[^>]*disabled/.test(container.innerHTML) && !/Loading…/.test(container.innerHTML)) return; } };
(async () => {
  await waitIdle();
  check('opens empty with $100,000', /Account value \$100,000\.00/.test(text()) && /Nothing held yet/.test(text()) && !bad().length, text().slice(0, 200));
  const buy = async (sym, amt, note) => { document.getElementById('pp-symbol').value = sym; document.getElementById('pp-amount').value = String(amt); document.getElementById('pp-note').value = note || ''; click('buy'); await sleep(50); await waitIdle(); };
  await buy('aapl', 1000, 'score 68'); check('buy by code (AAPL)', /Practice buy recorded: \$1,000\.00 of AAPL/.test(text()) && /Apple Inc\./.test(text()) && /score 68/.test(text()), text().slice(0, 600));
  await buy('toyota', 2500); check('buy by name (toyota)', /Practice buy recorded: \$2,500\.00 of TM /.test(text()), (text().match(/Practice buy recorded[^.]*\.\d\d[^.]*\./) || [text().slice(300, 700)])[0]);
  await buy('BHP.AX', 500); check('Australian stock, converted', /A\$\d/.test(text()) && /BHP Group/.test(text()));
  await buy('IMB.L', 500); check('London stock in pence', /\d\.\d\dp/.test(text()));
  await buy('BTC-USD', 300); check('coin', /Bitcoin/.test(text()));
  await buy('ZZZZQQ', 100); check('unknown name refused with a message', /No price found for "ZZZZQQ"/.test(text()) && document.getElementById('pp-symbol').value === 'ZZZZQQ', [(text().match(/id=.pp-notice[^]*/) || [''])[0], (container.innerHTML.match(/pp-notice[^>]*>([^<]*)/) || [])[1], document.getElementById('pp-symbol').value]);
  await buy('MSFT', 999999); check('too large refused', /Not enough practice cash/.test(text()));
  const saved = JSON.parse(store['tester@example.com'].data);
  check('stored: 5 holdings, cash $95,200', saved.holdings.length === 5 && saved.cash === 95200 && store['tester@example.com'].version === 5, { n: saved.holdings.length, cash: saved.cash });
  check('page shows cash and no broken values', /Practice cash left \$95,200\.00/.test(text()) && !bad().length, bad());
  if (/Holding \(\d+\)/.test(text())) check('the holdings table says how many are held, as the sold list says how many were sold', /Holding \(5\) Bought/.test(text()), (text().match(/Holding[^B]{0,12}Bought/) || [''])[0]);
  console.log('   summary: ' + (text().match(/Account value.*?bought on the same days/) || [''])[0]);
  console.log('   rows: ' + (text().match(/Holding(?: \(\d+\))? Bought.*?(?=Fake money)/) || [''])[0].slice(0, 900));
  // company-name lookup, as on the home page
  const type = async (v) => { document.getElementById('pp-symbol').value = v; handlers.input.forEach(f => f({ target: document.getElementById('pp-symbol') })); };
  const sug = document.getElementById('pp-suggest');
  await type('apple'); await sleep(600); const checking = /Checking exchanges/.test(sug.innerHTML); for (let i = 0; i < 80 && /Checking/.test(sug.innerHTML); i++) await sleep(250);
  check('lookup: typing a company name lists codes', checking && sug.style.display === 'block' && /data-symbol="AAPL"/.test(sug.innerHTML) && /US Market/.test(sug.innerHTML) && document.getElementById('pp-clear').style.display === 'block', sug.innerHTML.slice(0, 300));
  click('pick', { 'data-symbol': 'AAPL' }); for (let i = 0; i < 80 && !/Apple/.test(document.getElementById('pp-notice').textContent || ''); i++) await sleep(250);
  check('lookup: picking shows the company and price', document.getElementById('pp-symbol').value === 'AAPL' && sug.style.display === 'none' && /^AAPL: Apple Inc\., latest price \$\d/.test(document.getElementById('pp-notice').textContent), document.getElementById('pp-notice').textContent);
  await type('qzqzqzq'); await sleep(600); for (let i = 0; i < 80 && /Checking/.test(sug.innerHTML); i++) await sleep(250);
  check('lookup: no match says so', /No matches found/.test(sug.innerHTML), sug.innerHTML);
  await type('BHP.AX'); await sleep(700); check('lookup: a full code needs no lookup', sug.style.display === 'none');
  click('clear'); check('lookup: clear button empties the box', document.getElementById('pp-symbol').value === '');
  // dollars or quantity: no default amount, and each fills in the other from the latest price
  check('no amount is pre-filled', /id="pp-amount"[^>]*placeholder="Enter \$"/.test(container.innerHTML) && !/id="pp-amount"[^>]*value=/.test(container.innerHTML) && /id="pp-qty"[^>]*placeholder="or quantity"/.test(container.innerHTML));
  const typeIn = (id, v) => { document.getElementById(id).value = String(v); handlers.input.forEach(f => f({ target: document.getElementById(id) })); };
  document.getElementById('pp-symbol').value = ''; document.getElementById('pp-amount').value = ''; document.getElementById('pp-qty').value = '';
  click('pick', { 'data-symbol': 'KO' }); for (let i = 0; i < 80 && !/Coca/.test(document.getElementById('pp-notice').textContent || ''); i++) await sleep(250);
  const koPrice = parseFloat((document.getElementById('pp-notice').textContent.match(/latest price \$([0-9.]+)/) || [])[1]);
  typeIn('pp-amount', 500); check('typing dollars fills in the quantity', koPrice > 0 && Math.abs(parseFloat(document.getElementById('pp-qty').value) - 500 / koPrice) < 0.001, [koPrice, document.getElementById('pp-qty').value]);
  typeIn('pp-qty', 3); check('typing a quantity fills in the dollars', Math.abs(parseFloat(document.getElementById('pp-amount').value) - 3 * koPrice) < 0.011, document.getElementById('pp-amount').value);
  const cashBefore = JSON.parse(store['tester@example.com'].data).cash; click('buy'); await sleep(50); await waitIdle();
  const koBuy = JSON.parse(store['tester@example.com'].data); const ko = koBuy.holdings.slice(-1)[0];
  check('buying by quantity buys exactly that many', ko.symbol === 'KO' && Math.abs(ko.qty - 3) < 1e-9 && Math.abs(cashBefore - koBuy.cash - ko.costUsd) < 0.011 && Math.abs(ko.costUsd - 3 * ko.buyPrice) < 0.011, ko);
  document.getElementById('pp-symbol').value = 'BHP.AX'; handlers.change.forEach(f => f({ target: document.getElementById('pp-symbol') })); for (let i = 0; i < 80 && !ctx.__q; i++) { await sleep(250); typeIn('pp-qty', 10); if (parseFloat(document.getElementById('pp-amount').value) > 0) ctx.__q = 1; }
  check('a code typed by hand in another currency: quantity gives US dollars', parseFloat(document.getElementById('pp-amount').value) > 100 && parseFloat(document.getElementById('pp-amount').value) < 2000, document.getElementById('pp-amount').value);
  document.getElementById('pp-amount').value = ''; document.getElementById('pp-qty').value = ''; document.getElementById('pp-symbol').value = 'KO'; click('buy'); await sleep(50);
  check('no dollars and no quantity: asks for one', /Enter how many practice dollars to put in, or a quantity/.test(text()) && JSON.parse(store['tester@example.com'].data).holdings.length === koBuy.holdings.length);
  { const sellId = JSON.parse(store['tester@example.com'].data).holdings.slice(-1)[0].id; click('sell', { 'data-id': sellId }); await sleep(50); await waitIdle(); click('clearsold'); await sleep(50); await waitIdle(); }
  check('reset is a visible button', /<button data-pp="reset"[^>]*title="[^"]*\$100,000\.00"[^>]*>Reset fake money<\/button>/.test(container.innerHTML) && /class="pp-btn ghost"/.test(container.innerHTML) && !/style="background: (none|#007bff)/.test(container.innerHTML) && /<button data-pp="refresh"/.test(container.innerHTML));
  // Top 10 popup button
  const btn = { disabled: false, textContent: '＋ Practice buy' }; await ctx.window.practiceBuyFromTop10(btn, 'IMX10603-USD', 'IMX-USD');
  check('Top 10 button adds a coin under its familiar name', /Added \$1,000\.00/.test(btn.textContent) && /IMX-USD/.test(text()) && JSON.parse(store['tester@example.com'].data).holdings.slice(-1)[0].symbol === 'IMX10603-USD', btn.textContent + ' ' + (ctx.lastAlert || ''));
  // sell
  const id = JSON.parse(store['tester@example.com'].data).holdings[0].id; click('sell', { 'data-id': id }); await sleep(50); await waitIdle();
  const after = JSON.parse(store['tester@example.com'].data); check('sell closes the line and returns cash', after.holdings.length === 5 && after.closed.length === 1 && /Sold AAPL for \$/.test(text()) && /Sold \(1\)/.test(text()), text().slice(0, 300));
  // sold list: summary, remove one line, clear all. None of it may change the money
  const id2 = after.holdings[0].id; click('sell', { 'data-id': id2 }); await sleep(50); await waitIdle();
  const two = JSON.parse(store['tester@example.com'].data);
  check('sold list has a summary and a clear button', two.closed.length === 2 && /2 sold: put in \$[\d,.]+, got back \$/.test(text()) && !/did better than the S&P 500/.test(text()) && /<button data-pp="clearsold"/.test(container.innerHTML), (text().match(/\d sold:[^.]*\.[^.]*\./) || [''])[0]);
  click('unsold', { 'data-id': two.closed[0].id }); await sleep(50); await waitIdle();
  const one = JSON.parse(store['tester@example.com'].data);
  check('removing one sold line leaves the money alone', one.closed.length === 1 && one.closed[0].id === two.closed[1].id && one.cash === two.cash && one.holdings.length === two.holdings.length && /removed from the sold list/.test(text()), { n: one.closed.length, cash: [two.cash, one.cash] });
  click('clearsold'); await sleep(50); await waitIdle();
  const none = JSON.parse(store['tester@example.com'].data);
  check('clear sold list empties it and leaves the money alone', none.closed.length === 0 && none.cash === two.cash && none.holdings.length === two.holdings.length && /Sold list cleared/.test(text()) && !/Sold \(/.test(text()) && !/data-pp="clearsold"/.test(container.innerHTML), { n: none.closed.length, cash: [two.cash, none.cash] });
  check('just bought, nothing has moved: no verdict against the market is shown', !/ahead of what an S&P 500 fund did/.test(text()) && !/0 of \d holding/.test(text()), (text().match(/\d of \d holding[^.]*\./) || [''])[0]);
  // whose holding it is: the autopilot's holdings say when and at what they will be sold (the plan comes from practice-autopilot.js)
  { const d = JSON.parse(store['tester@example.com'].data); d.holdings[0].by = 'ai'; d.holdings[0].screener = '7-1'; store['tester@example.com'].data = JSON.stringify(d);
    await ctx.window.practicePortfolio.reload(); await sleep(50); await waitIdle(); const hid = d.holdings[0].id;
    check('a holding is marked as bought by you or by the autopilot', /🤖 Bought by the autopilot\./.test(text()) && /Bought by you: it stays until you sell it\./.test(text()), text().slice(0, 500));
    ctx.window.practicePortfolio.setPlans([{ id: hid, auto: true, sellBy: '2026-10-10T16:42:41Z', stop: -10, take: 18, arm: 9 }]);
    check('with the autopilot on: when and at what it will be sold', /🤖 Autopilot: it sells this by itself, at the check-in around [^.]*\d\d:\d\d[^.]* at the latest, sooner if it falls to -10% or reaches \+18%\. While it rises it is kept; once it has been up 9% a stop follows it up, and it is sold only if it then falls back\. The AI model also reviews it at every check-in and may sell it earlier\./.test(text()), (text().match(/🤖 Autopilot:[^.]*\.[^.]*\./) || [''])[0]);
    ctx.window.practicePortfolio.setPlans([{ id: hid, auto: true, sellBy: '2026-10-10T16:42:41Z', stop: -10, take: 9, arm: 4.5, trial: true }]);
    check('a holding in a trial of its rules says so', /sooner if it falls to -10% or reaches \+9%\. While it rises it is kept; once it has been up 4\.5% a stop follows it up, and it is sold only if it then falls back\. Part of a trial of one of its own rules\./.test(text()));
    ctx.window.practicePortfolio.setPlans([{ id: hid, auto: false, sellBy: '2026-10-10T16:42:41Z', stop: -10, take: 18, arm: 9 }]);
    check('with the autopilot off: it says the holding now stays', /🤖 Bought by the autopilot, which is switched off: it stays until you sell it or switch the autopilot back on\./.test(text()));
    { const pat = pure.planLine({ by: 'ai' }, { auto: true, sellBy: '2026-10-22T14:40:00Z', stop: -10, take: 18, arm: 4, patient: true }), plain = pure.planLine({ by: 'ai' }, { auto: true, sellBy: '2026-10-22T14:40:00Z', stop: -10, take: 18, arm: 4, patient: false });
      if (/plan\.patient/.test(src)) check('a patient share says it is not sold on its signal nor reviewed; an ordinary one says the AI model reviews it', /A patient share, part of a trial: it is not sold because its screener signal turns, and the AI model does not review it\./.test(pat) && !/may sell it earlier/.test(pat) && /The AI model also reviews it at every check-in and may sell it earlier\./.test(plain) && !/patient/.test(plain), pat.slice(-160)); }
    if (/function versusFund/.test(src)) { const vf = (o, m) => { const f = new Function('pctHtml', 's', src.match(/function versusFund\(s\) \{[\s\S]*?\n    \}/)[0] + '; return versusFund(s);'); return f(n => (n >= 0 ? 'UP ' : 'DOWN ') + Math.abs(n).toFixed(2) + '%', { openGainPct: o, marketPct: m }); };
      check('the comparison card says in words who is ahead: behind the fund, ahead of it, level, and nothing when there is nothing to compare', /Your holdings: DOWN 0\.90%, so they are <strong>behind the fund by 0\.96(%| points)<\/strong>/.test(vf(-0.9, 0.06)) && /ahead of the fund by 1\.50(%| points)/.test(vf(2, 0.5)) && /level with the fund/.test(vf(0.5, 0.502)) && vf(null, 0.06) === '' && vf(1, null) === '', vf(-0.9, 0.06)); }
    check('the plan line itself', pure.planLine({ by: 'me' }, null) === 'Bought by you: it stays until you sell it.' && pure.planLine({ by: 'ai' }, undefined) === '🤖 Bought by the autopilot.');
  }
  // whose result is whose: the owner's real figures of 10 Oct 2026 (his own Bitcoin up $201.85, an autopilot sale +$7.91, an autopilot holding up $17.08)
  { const st = { startingCash: 100000, cash: 15906.98, closed: [{ id: 'c1', by: 'ai', costUsd: 1250, proceedsUsd: 1257.91 }], holdings: [
      { id: 'm1', symbol: 'BTC-USD', currency: 'USD', qty: 1, buyPrice: 82750.93, costUsd: 82750.93 }, { id: 'm2', symbol: 'BTC-USD', currency: 'USD', qty: 100 / 82734.62, buyPrice: 82734.62, costUsd: 100 },
      { id: 'a1', symbol: 'CFX-USD', currency: 'USD', qty: 1250 / 0.1, buyPrice: 0.1, costUsd: 1250, by: 'ai' }] };
    const q = { 'BTC-USD': { price: 82952.52 }, 'CFX-USD': { price: 0.1013664 } }; const sp = pure.splitGain(st, q, 7.91), near = (a, b) => Math.abs(a - b) < 0.02;
    check('the total since the start is split into your own buys and the autopilot\'s', near(sp.total, 226.84) && near(sp.yours, 201.85) && near(sp.autoSold, 7.91) && near(sp.autoOpen, 17.08) && near(sp.auto, 24.99) && near(sp.yours + sp.auto, sp.total) && sp.any === true, sp);
    check('both parties get the same split: sold and still held add up to each one\'s result, and across the two to the card\'s figures', sp.yoursSold !== undefined && near(sp.yoursSold + sp.yoursOpen, sp.yours) && near(sp.autoSold + sp.autoOpen, sp.auto) && near(sp.yoursOpen + sp.autoOpen, pure.summarize(st, q).openGainUsd) && near(sp.yours + sp.auto, sp.total), sp);
    st.closed = []; const cleared = pure.splitGain(st, q, 7.91); check('clearing the sold list does not move the autopilot\'s sales into your own result', near(cleared.autoSold, 7.91) && near(cleared.yours, 201.85) && cleared.any === true, cleared);
    const none = pure.splitGain({ startingCash: 100000, cash: 99900, closed: [], holdings: [st.holdings[1]] }, q, 0); check('with nothing of the autopilot\'s there is nothing to split', none.any === false && near(none.yours, none.total), none); }
  { const d = JSON.parse(store['tester@example.com'].data), mine = d.holdings.find(h => h.by === 'ai');
    ctx.window.practicePortfolio.setPlans([{ id: mine.id, auto: true, sellBy: '2026-10-10T16:42:41Z', stop: -10, take: 18, arm: 9 }], { realizedUsd: 7.91 });
    check('whose result is whose: your own buys and the autopilot, each as an arrow and an amount, each with what was sold and what is still held', /Whose result is whose Your own buys [▲▼–] \$[\d,.]+ \(sold [▲▼–] \$[\d,.]+ · still held [▲▼–] \$[\d,.]+ ?\) 🤖 AI autopilot [▲▼–] \$[\d,.]+ \(sold ▲ \$7\.91 · still held [▲▼–] \$[\d,.]+ ?\)/.test(text()) && /aria-label="up \$7\.91"/.test(container.innerHTML) && !/Of the [+-]?\$/.test(text()), (text().match(/Whose result.{0,160}/) || [text().slice(0, 300)])[0]); }
  { const st = { startingCash: 100000, cash: 16006.98, closed: [], holdings: [{ id: 'm1', symbol: 'BTC-USD', currency: 'USD', qty: 1, buyPrice: 82750.93, costUsd: 82750.93, spyAtBuy: 778.57 }, { id: 'a1', symbol: 'CFX-USD', currency: 'USD', qty: 12500, buyPrice: 0.1, costUsd: 1250, by: 'ai', spyAtBuy: 778.57 }] };
    const closed = pure.summarize(st, { 'BTC-USD': { price: 83000 }, 'CFX-USD': { price: 0.101 }, SPY: { price: 778.57 } }), open = pure.summarize(st, { 'BTC-USD': { price: 83000 }, 'CFX-USD': { price: 0.101 }, SPY: { price: 780 } });
    check('the S&P 500 fund has not traded since the buys (a weekend): that is told apart from a real 0.00%', closed.marketFlat === true && Math.abs(closed.marketPct) < 1e-9 && open.marketFlat === false && open.marketPct > 0.1, [closed.marketFlat, closed.marketPct, open.marketFlat, open.marketPct]);
    check('what was sold and what is still held add up to the change since the start', Math.abs((closed.gainUsd - closed.openGainUsd) + closed.openGainUsd - closed.gainUsd) < 1e-9 && Math.abs(closed.openGainUsd - (83000 - 82750.93 + 12.5)) < 0.01 && Math.abs((closed.gainUsd - closed.openGainUsd) - 7.91) < 0.01, [closed.gainUsd, closed.openGainUsd]);
    check('a holding that has been up enough says what it is sold at if it slips back', /It has been up enough for a stop to follow it: it is sold if it falls back to \+2\.3%\./.test(pure.planLine({ by: 'ai' }, { auto: true, sellBy: '2026-10-10T20:35:27Z', stop: -10, take: 18, arm: 1, floor: 2.3 })) && !/falls back to/.test(pure.planLine({ by: 'ai' }, { auto: true, sellBy: '2026-10-10T20:35:27Z', stop: -10, take: 18, arm: 1, floor: null }))); }
  { const shut = pure.planLine({ by: 'ai' }, { auto: true, sellBy: '2026-10-16T00:05:00Z', stop: -10, take: 18, arm: 2, market: 'Japanese', closed: true, opens: '2026-10-12T00:05:00Z' });
    check('a share whose market is closed says so, and when it opens', /The Japanese market is closed now, so nothing happens to it until it opens \(around [^)]*\d\d:\d\d[^)]*\)\.$/.test(shut), shut);
    const open = pure.planLine({ by: 'ai' }, { auto: true, sellBy: '2026-10-16T00:05:00Z', stop: -10, take: 18, arm: 2, market: 'Japanese', closed: false, opens: null });
    check('and nothing about a closed market while it is open, or for a plan from the older function', !/closed/.test(open) && !/closed/.test(pure.planLine({ by: 'ai' }, { auto: true, sellBy: '2026-10-16T00:05:00Z', stop: -10, take: 18, arm: 2 })), open); }
  { const base = { auto: true, sellBy: '2026-10-10T20:35:27Z', stop: -10, take: 18, arm: 1.9, peak: 0.4 };
    check('a holding with a full trailing stop says where the stop is; with the stop switched off it names only the limits', /sooner if it falls to -10% or reaches \+18%\. Its trailing stop is at -3\.5% now and follows the price up\./.test(pure.planLine({ by: 'ai' }, { ...base, floor: -3.5, mode: 'full' })) && /sooner if it falls to -10% or reaches \+18%\. The AI model also reviews it/.test(pure.planLine({ by: 'ai' }, { ...base, arm: null, floor: null, mode: 'off' })) && /It has been up enough for a stop to follow it: it is sold if it falls back to \+3\.4%\./.test(pure.planLine({ by: 'ai' }, { ...base, peak: 6.2, floor: 3.4, mode: 'full' }))); }
  { const sum = ctx.window.practicePortfolio.summary();
    check('the portfolio gives the AI chat a few plain lines on what it shows: the account, what the user bought, what the autopilot holds', /^PRACTICE PORTFOLIO \(fake money\): account value \$[\d,.]+, (?:level|(?:up|down) \$[\d,.]+) since the start of \$100,000\.00; practice cash left \$[\d,.]+\.\nBought by the user \(\d+\): [^\n]+\.\nBought by the autopilot and still held \(\d+\): [^\n]+\.\nSold so far: \d+\.$/.test(sum) && sum.length < 1500 && !/undefined|NaN/.test(sum), sum); }
  check('a result is put in words: up, down or level, never a bare sign', pure.moved(144.12) === 'up $144.12' && pure.moved(-202.6) === 'down $202.60' && pure.moved(0) === 'level' && pure.moved(-0.004) === 'level' && pure.moved(1234.5) === 'up $1,234.50');
  check('the account card shows how the account stands as an arrow, an amount and a percentage, and how much of it is from sales and how much on holdings still held', /Account value \$[\d,.]+ [▲▼–] \$[\d,.]+ \([\d.]+%\) since the start (?:Sold, yours and the autopilot’s together [▲▼–] \$[\d,.]+ Still held, together|Sold [▲▼–] \$[\d,.]+ · Still held) [▲▼–] \$[\d,.]+/.test(text()) && /class="pp-card(?: up| down)?"/.test(container.innerHTML), (text().match(/Account value.{0,160}/) || [text().slice(0, 200)])[0]);
  check('an arrow is green going up, red going down and grey when level, and a screen reader is still told in words', /color: #16a34a[^>]*>▲ /.test(container.innerHTML + pure.movedHtml(5)) && /aria-label="down \$58\.48 \(0\.06%\)"[^>]*color: #ef4444[^>]*>▼ \$58\.48 \(0\.06%\)</.test(pure.movedHtml(-58.48, -0.06)) && /aria-label="level"[^>]*>– \$0\.00</.test(pure.movedHtml(0)) && pure.moved(-58.48) === 'down $58.48', pure.movedHtml(-58.48, -0.06));
  { const html = container.innerHTML, table = (html.match(/<table class="pp-stack"[^]*?<\/table>/) || [''])[0], rowsHtml = table.split('<tr>').slice(1);
    check('for a phone: the holdings table can stack into cards (its heading row can be hidden, every figure carries its own label)', /<tr class="pp-head">/.test(table) && rowsHtml.length > 0 && rowsHtml.every(r => /<td class="pp-name"/.test(r) && ['Bought', 'Price then', 'Price now', 'Value', 'Change'].every(l => r.includes('data-label="' + l + '"')) && /<td class="pp-act"[^>]*><button data-pp="sell"/.test(r)), table.slice(0, 300));
    check('and the phone rules are in the script: cards under 640px, a full-width Sell button, a buy row that fits', /@media \(max-width: 640px\)/.test(src) && /table\.pp-stack tr\.pp-head \{ display: none !important; \}/.test(src) && /td\[data-label\]::before \{ content: attr\(data-label\)/.test(src) && /#pp-note \{ flex: 1 1 100% !important/.test(src) && ['Held', 'Price', 'Value', 'Result'].every(l => src.includes('<td data-label="' + l + '"')), ''); }
  check('no S&P columns or verdicts in the tables; one comparison figure in the summary', !/S&P 500 since|S&P 500 same time|ahead of what|did better than the S&P/.test(text()) && /For comparison/.test(text()) && /the same money in an S&P 500 index fund instead/.test(text()), text().slice(0, 300));
  // another window changed it
  store['tester@example.com'].version += 1; await buy('KO', 100); check('change from another window is caught, not overwritten', /changed in another window/i.test(text()), (text().match(/This portfolio[^.]*\./) || [''])[0]);
  await buy('KO', 100); check('and works after the reload', /Practice buy recorded: \$100\.00 of KO/.test(text()));
  click('reset'); await sleep(50); await waitIdle(); check('reset', !store['tester@example.com'] && /Account value \$100,000\.00/.test(text()) && /Practice portfolio reset/.test(text()));
  check('no broken values anywhere', !bad().length, bad());
  { const real = (() => { const m = { exports: {} }; vm.runInNewContext(src, { module: m, console }); return m.exports; })();      // as on the site: with the trading cost
    const st = real.newState(); const h = real.applyBuy(st, { symbol: 'KO', price: 50, fx: 1, amountUsd: 1000, now: '2026-10-12T15:00:00Z', spy: 500 });
    check('a trading cost of 0.1% is taken off a practice buy: the whole amount leaves the cash and the holding starts a little below it', real.TRADE_COST_PCT === 0.1 && st.cash === 99000 && h.costUsd === 1000 && Math.abs(h.qty - 19.98) < 1e-9 && Math.abs(real.valueOf(h, { KO: { price: 50 } }).valueUsd - 999) < 0.005, h);
    const got = real.applySell(st, h.id, { price: 50, fx: 1, now: '2026-10-12T16:00:00Z', spy: 500 });
    check('and off a sale: sold at the same price, $998.00 comes back of $1,000', got === 998 && st.cash === 99998, got);
    check('the page says so beside the fake-money line', /A trading cost of \$\{TRADE_COST_PCT\}% is taken off each practice buy and each sale/.test(src)); }
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
})();
