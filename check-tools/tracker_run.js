// Runs the dashboard's real "Top 10 Performance" code (popup + the on-load average) on saved report text,
// with live prices from the price proxy. Nothing is saved: the dashboard API calls are answered locally.
const vm = require('vm'), fs = require('fs');
const dash = fs.readFileSync(process.env.DASH || '/Users/dave/VSCODE/website/dashboard.html', 'utf8');
const grab = (start, end) => dash.slice(dash.indexOf(start), dash.indexOf(end, dash.indexOf(start)));
const code = grab('function parseCryptoTickers', 'async function trackPerformance(');
const [label, file, when] = process.argv.slice(2);
let report = JSON.parse(fs.readFileSync(file, 'utf8')); report = report.report || report.text;
const priceCalls = [], saved = [];
const realFetch = fetch;
async function fakeFetch(url, opts = {}) {
  const u = String(url);
  if (u.includes('nwdjnlcbtj34ywy6sgawmwhcx40ologt')) {
    const b = JSON.parse(opts.body || '{}');
    if (b.action === 'save_avg_change') saved.push(b.avgChange);
    return { ok: true, status: 200, json: async () => ({ analysis: { report } }) };
  }
  const sym = decodeURIComponent(u.split('symbol=')[1]); const r = await realFetch(url); const txt = await r.text();
  let j; try { j = JSON.parse(txt); } catch (e) { j = null; }
  priceCalls.push({ sym, status: r.status, ok: !!j?.chart?.result?.[0], cur: j?.chart?.result?.[0]?.meta?.regularMarketPrice, ccy: j?.chart?.result?.[0]?.meta?.currency });
  return { ok: r.ok, status: r.status, json: async () => { if (j === null) throw new Error('bad json'); return j; } };
}
let popup = '';
const mk = () => ({ style: {}, set innerHTML(v) { popup = v; }, get innerHTML() { return popup; }, appendChild() {}, remove() {}, onclick: null });
const item = { analysisId: 'a1', timestamp: when, companyName: process.env.NAME || '' };   // NAME picks the index, e.g. NAME='Dow Jones 30 Blue Chip Screener'
const ctx = { console: { log() {}, error() {}, warn() {} }, fetch: fakeFetch, document: { createElement: mk, body: mk() }, localStorage: { getItem: () => 'tester' }, analysisHistory: [item], displayHistory() {}, Date, Math, JSON, parseFloat, Promise, setTimeout, isFinite, Number, String, Object, encodeURIComponent };
vm.createContext(ctx); vm.runInContext(code, ctx);
(async () => {
  await ctx.updateScreenerAvgChange('a1', when); const onLoad = item.avgChange; priceCalls.length = 0;
  await ctx.trackScreenerPerformance('a1', when);
  const text = popup.replace(/<style>.*?<\/style>/g, '').replace(/<[^>]+>/g, '|').replace(/\|+/g, '|');
  const rows = [...text.matchAll(/\|([A-Z0-9^=.\-]+)\|([^|]*→[^|]*)\|([+\-][0-9.]+%)/g)].map(m => `${m[1]} ${m[2]} ${m[3]}`);
  const head = (text.match(/Average Change\|([^|]+)\|Gainers\|(\d+)\|Losers\|(\d+)\|([^|]+)/) || []).slice(1);
  console.log(`\n=== ${label}: popup average ${head[0]} | gainers ${head[1]} losers ${head[2]} | "${head[3]}" | on-load badge ${typeof onLoad === 'number' ? onLoad.toFixed(2) + '%' : onLoad}`);
  if (!head.length) console.log('   POPUP: ' + text.slice(0, 200));
  console.log('   lookups: ' + priceCalls.map(p => `${p.sym}${p.ok ? '' : '(NO DATA ' + p.status + ')'}`).join(' ') + ' | currencies: ' + [...new Set(priceCalls.map(p => p.ccy))].join(','));
  const cmp = text.match(/Top 10 and the index over the same time\|(.*?)\|(The index comparison|Index figures)/); if (cmp) console.log('   comparison: ' + cmp[1].replace(/\|/g, '  '));
  rows.forEach(r => console.log('   ' + r)); const nodata = (text.match(/\|[^|]*: (No data|Price does not match the report|No price in the report)[^|]*/g) || []); if (nodata.length) console.log('   ' + nodata.join(' '));
})();
