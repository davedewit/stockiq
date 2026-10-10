// Drives the real practice-portfolio.js in a stand-in page: real prices and name search, an in-memory copy of the storage API.
const vm = require('vm'), fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
// --- pure sums first
const pure = (() => { const m = { exports: {} }; vm.runInNewContext(src, { module: m, console }); return m.exports; })();
let ok = true; const check = (name, cond, extra) => { ok = ok && !!cond; console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + JSON.stringify(extra))); };
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
ctx.window = ctx; vm.createContext(ctx); vm.runInContext(src, ctx);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const click = (action, attrs = {}) => handlers.click.forEach(f => f({ target: { closest: sel => sel === '[data-pp]' ? { getAttribute: k => k === 'data-pp' ? action : attrs[k], tagName: 'BUTTON', style: {} } : null }, preventDefault() {} }));
const text = () => container.innerHTML.replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/\s+/g, ' ');
const bad = () => (container.innerHTML.match(/undefined|NaN|\[object|Infinity/g) || []);
const waitIdle = async () => { for (let i = 0; i < 120; i++) { await sleep(250); if (!/Working…/.test(container.innerHTML) && !/Loading…/.test(container.innerHTML)) return; } };
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
  console.log('   summary: ' + (text().match(/Account value.*?bought on the same days/) || [''])[0]);
  console.log('   rows: ' + (text().match(/Holding Bought.*?(?=Fake money)/) || [''])[0].slice(0, 900));
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
  check('reset is a visible button', /<button data-pp="reset"[^>]*>Reset fake money to \$100,000\.00<\/button>/.test(container.innerHTML) && /<button data-pp="refresh"/.test(container.innerHTML));
  // Top 10 popup button
  const btn = { disabled: false, textContent: '＋ Practice buy' }; await ctx.window.practiceBuyFromTop10(btn, 'IMX10603-USD', 'IMX-USD');
  check('Top 10 button adds a coin under its familiar name', /Added \$1,000\.00/.test(btn.textContent) && /IMX-USD/.test(text()) && JSON.parse(store['tester@example.com'].data).holdings.slice(-1)[0].symbol === 'IMX10603-USD', btn.textContent + ' ' + (ctx.lastAlert || ''));
  // sell
  const id = JSON.parse(store['tester@example.com'].data).holdings[0].id; click('sell', { 'data-id': id }); await sleep(50); await waitIdle();
  const after = JSON.parse(store['tester@example.com'].data); check('sell closes the line and returns cash', after.holdings.length === 5 && after.closed.length === 1 && /Sold AAPL for \$/.test(text()) && /Sold \(1\)/.test(text()), text().slice(0, 300));
  // another window changed it
  store['tester@example.com'].version += 1; await buy('KO', 100); check('change from another window is caught, not overwritten', /changed in another window/i.test(text()), (text().match(/This portfolio[^.]*\./) || [''])[0]);
  await buy('KO', 100); check('and works after the reload', /Practice buy recorded: \$100\.00 of KO/.test(text()));
  click('reset'); await sleep(50); await waitIdle(); check('reset', !store['tester@example.com'] && /Account value \$100,000\.00/.test(text()) && /Practice portfolio reset/.test(text()));
  check('no broken values anywhere', !bad().length, bad());
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
})();
