// The practice account against the market, day by day (19 Oct 2026; the owner: "if the majority of market drops on bad days and we do
// well ... indicators like this are important and should be something AI thinks about"). Read-only: the portfolio's own "get" and the
// price function. Uses the dashboard's own sums (practice-portfolio.js valueSeries), so the account's figures are the graph's.
//   node check-tools/versus_market.js <account>          day by day at each US close: the account, an S&P 500 fund (SPY), an
//                                                         all-world fund (ACWI), and how the account did on the S&P's down and up days
// Read with care: the account holds cash (it does not fall with the market), most holdings are outside the US, and a few days
// say little. session_start.py prints it every session.
const pp = require(require('path').join(__dirname, '..', '..', 'website', 'practice-portfolio.js'));
const API = 'https://5c7pt7qurshld4cwaqyopfxcei0cuurj.lambda-url.us-east-1.on.aws/';
const PRICE = 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/?symbol=';
(async () => {
  const r = await (await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'get', userId: process.argv[2] }) })).json();
  const state = typeof r.data === 'string' ? JSON.parse(r.data) : (r.data || r.portfolio || r);
  const syms = new Set(['SPY', 'ACWI']);
  [...state.holdings, ...state.closed].forEach(h => { syms.add(h.symbol); const fx = pp.fxFor(h.currency || 'USD'); if (fx.symbol) syms.add(fx.symbol); });
  const quotes = {};
  await Promise.all([...syms].map(async s => {
    try { const rng = (s === 'SPY' || s === 'ACWI') ? pp.fundRange(state.createdAt, Date.now()) : null;      // the funds reach back to the start
      const j = await (await fetch(PRICE + encodeURIComponent(s) + (rng ? '&range=' + rng : ''))).json(); const res = j.chart.result[0], m = res.meta;
      quotes[s] = { price: m.regularMarketPrice, currency: m.currency, time: m.regularMarketTime, series: pp.seriesOf(res, s) }; } catch (e) {}
  }));
  const now = Date.now(), vs = pp.valueSeries(state, quotes, now, undefined, 0);
  const at = t => { const p = vs.points; let b = p[0]; for (const x of p) { if (x.t <= t) b = x; } return b; };
  const value = t => { const pts = vs.points; for (let i = 1; i < pts.length; i++) if (pts[i].t >= t) { const a = pts[i - 1], b = pts[i]; return a.value + (b.value - a.value) * (t - a.t) / ((b.t - a.t) || 1); } return pts.at(-1).value; };
  const closes = s => (quotes[s].series || []).filter(([t]) => t >= Date.parse(state.createdAt) - 4 * 864e5);
  const spy = closes('SPY'), acwi = closes('ACWI');
  
  console.log('day (US close)   account    day%   S&P500 day%  all-world day%');
  let prev = null, rows = [];
  for (const [t, p] of spy) {
    if (t < Date.parse(state.createdAt)) { prev = { t, v: 100000, s: p, a: (acwi.find(k => k[0] === t) || [])[1] }; continue; }
    const v = value(t), a = (acwi.find(k => Math.abs(k[0] - t) < 6 * 3600e3) || [])[1];
    if (prev) { const row = { day: new Date(t).toISOString().slice(0, 10), v, acc: (v / prev.v - 1) * 100, spy: (p / prev.s - 1) * 100, acwi: a && prev.a ? (a / prev.a - 1) * 100 : null }; rows.push(row);
      console.log(row.day, '  ', v.toFixed(0).padStart(7), row.acc.toFixed(2).padStart(7), row.spy.toFixed(2).padStart(10), row.acwi === null ? '' : row.acwi.toFixed(2).padStart(12)); }
    prev = { t, v, s: p, a };
  }
  const nowV = vs.points.at(-1).value, s0 = spy.find(([t]) => t >= Date.parse(state.createdAt)) ;
    const firstClose = k => { let b = null; for (const x of k) if (x[0] <= Date.parse(state.createdAt)) b = x; return b; };
  const sp0 = firstClose(spy), ac0 = firstClose(acwi);
  console.log('since start: account', ((nowV / 100000 - 1) * 100).toFixed(2) + '%', 'S&P 500', ((quotes.SPY.price / sp0[1] - 1) * 100).toFixed(2) + '%', 'all-world', ((quotes.ACWI.price / ac0[1] - 1) * 100).toFixed(2) + '%');
  const down = rows.filter(r => r.spy < 0), up = rows.filter(r => r.spy >= 0), avg = (a, f) => a.length ? (a.reduce((s, r) => s + r[f], 0) / a.length).toFixed(2) : '-';
  console.log(`S&P down days: ${down.length}, account avg ${avg(down, 'acc')}% vs S&P ${avg(down, 'spy')}%, all-world ${avg(down.filter(r => r.acwi !== null), 'acwi')}%`);
  console.log(`S&P up days:   ${up.length}, account avg ${avg(up, 'acc')}% vs S&P ${avg(up, 'spy')}%, all-world ${avg(up.filter(r => r.acwi !== null), 'acwi')}%`);
  const inv = state.holdings.reduce((s, h) => s + h.costUsd, 0), byCur = {};
  state.holdings.forEach(h => byCur[h.currency || 'USD'] = (byCur[h.currency || 'USD'] || 0) + h.costUsd);
  console.log('cash', state.cash.toFixed(0) + ` (${(state.cash / nowV * 100).toFixed(0)}% of the account: it does not move with the market)`, 'invested at cost', inv.toFixed(0), 'by currency', JSON.stringify(Object.fromEntries(Object.entries(byCur).map(([k, v]) => [k, Math.round(v)]))));
  const top = state.holdings.map(h => { const v = pp.valueOf(h, quotes); return [h.label, Math.round(v.valueUsd - h.costUsd)]; }).sort((a, b) => b[1] - a[1]);
  console.log('biggest gains held', JSON.stringify(top.slice(0, 5)), 'biggest losses held', JSON.stringify(top.slice(-4)));
})();
