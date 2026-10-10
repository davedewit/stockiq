// Runs the real page code (analysis-functions.js) for one button, with real network calls to the
// analysis Lambdas. Anything that would write user data (history, usage, trial) is blocked and logged.
const vm = require('vm'), fs = require('fs');
const [option, subOption, inputsJson] = process.argv.slice(2);
const inputs = Object.assign({ 'symbols-input': 'AAPL, KO', 'signals-symbols': 'NVDA, BA, KO', 'coin-symbol-input': 'BTC' }, JSON.parse(inputsJson || '{}'));
const map = JSON.parse(fs.readFileSync('/Users/dave/VSCODE/stockiq/lambda-url-mapping.json', 'utf8'));
const nameOf = {}; for (const [n, u] of Object.entries(map)) { const h = (u.match(/https:\/\/([a-z0-9]+)\./) || [])[1]; if (h) nameOf[h] = n; }
const BLOCK = /usage|trial|dashboard|tracker|email|payment|checkout|notification|ip-blocking|cognito|delete|csv-export/i;
const calls = [], blocked = [];
const realFetch = fetch;
async function loggedFetch(url, opts = {}) {
  const host = (String(url).match(/https:\/\/([a-z0-9]+)\./) || [])[1] || String(url).slice(0, 40);
  const name = nameOf[host] || (String(url).includes('ipify') ? 'ipify' : 'UNKNOWN:' + host);
  if (BLOCK.test(name) || name === 'ipify') { blocked.push(name); return { ok: true, status: 200, json: async () => ({ success: true, usage: 0, dailyLimit: 999999, allowed: true, canAnalyze: true }), text: async () => '{}' }; }
  const t0 = Date.now(); const rec = { name, ms: 0, status: 0, n: null }; calls.push(rec);
  try {
    const r = await realFetch(url, opts); rec.status = r.status; const txt = await r.text(); rec.ms = Date.now() - t0;
    let j = null; try { j = JSON.parse(txt); } catch (e) { rec.err = 'non-JSON: ' + txt.slice(0, 60); }
    if (j) { const res = j.results || j.signals || j.coins || (j.data && j.data.results); rec.n = Array.isArray(res) ? res.length : null; if (j.error) rec.err = String(j.error).slice(0, 80); }
    return { ok: r.ok, status: r.status, json: async () => { if (j === null) throw new Error('bad json'); return j; }, text: async () => txt };
  } catch (e) { rec.ms = Date.now() - t0; rec.err = 'fetch failed: ' + e.message; throw e; }
}
const mkEl = id => { const el = { style: {}, innerHTML: '', textContent: '', value: inputs[id] !== undefined ? inputs[id] : '', onclick: null, dataset: {}, children: [],
  classList: { add() {}, remove() {}, toggle() {}, contains: () => false }, appendChild() {}, remove() {}, setAttribute() {}, getAttribute: () => null, addEventListener() {}, scrollIntoView() {}, focus() {},
  querySelectorAll: () => [], querySelector: () => null, closest: () => null, insertAdjacentHTML() {} }; return el; };
const els = {}; const store = {};
const document = { getElementById: id => els[id] || (els[id] = mkEl(id)), querySelectorAll: () => [], querySelector: () => null, createElement: () => mkEl('new'), addEventListener() {}, body: mkEl('body'), head: mkEl('head'), cookie: '', title: '', readyState: 'complete' };
const stubFn = () => new Proxy(function () {}, { get: (t, k) => k === Symbol.toPrimitive ? () => '' : stubFn(), apply: () => stubFn() });
const out = { result: null, error: null };
const ctx = { console: { log() {}, warn() {}, error() {}, info() {} }, setTimeout, clearTimeout, setInterval: () => 0, clearInterval() {}, fetch: loggedFetch, document, navigator: { userAgent: 'Mozilla/5.0 Chrome/120', onLine: true },
  localStorage: { getItem: k => store[k] ?? null, setItem(k, v) { store[k] = String(v); }, removeItem(k) { delete store[k]; } }, sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  location: { href: 'https://stockiq.tech/analysis.html', search: '', pathname: '/analysis.html', hostname: 'stockiq.tech' }, URL, URLSearchParams, Blob: function () {}, alert() {}, gtag() {}, performance, AbortController, TextEncoder, TextDecoder, Intl, crypto: globalThis.crypto, addEventListener() {}, removeEventListener() {}, dispatchEvent() {}, innerWidth: 1300, innerHeight: 900, scrollTo() {}, scrollY: 0, open() {}, matchMedia: () => ({ matches: false, addEventListener() {} }), requestAnimationFrame: f => setTimeout(f, 0), history: { pushState() {}, replaceState() {} }, getComputedStyle: () => ({}) };
ctx.window = new Proxy(ctx, { get: (t, k) => k in t ? t[k] : undefined, set: (t, k, v) => { t[k] = v; return true; } }); ctx.globalThis = ctx; ctx.self = ctx.window;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('/Users/dave/VSCODE/website/analysis-functions.js', 'utf8'), ctx, { filename: 'analysis-functions.js' });
Object.assign(ctx, { displayResults: r => { out.result = r; }, displayError: m => { out.error = m; }, saveAnalysisToHistory: () => { blocked.push('saveAnalysisToHistory'); }, isBotOrCrawler: () => false,
  showAnonymousUpgradeModal() {}, showStickyUpgradeButton() {}, startCountdown() {}, clearCountdown() {} });
const opt = Number(option);
(async () => {
  const t0 = Date.now(); let thrown = null;
  try { await ctx.runAnalysis(opt, subOption, { target: mkEl('btn'), currentTarget: mkEl('btn'), preventDefault() {}, stopPropagation() {} }); } catch (e) { thrown = e.message; }
  const text = out.result ? String(out.result.data || '') : ''; const plain = text.replace(/<[^>]*>/g, '').replace(/&[^;]+;/g, ' ');
  const by = {}; for (const c of calls) { const g = c.name.replace(/-worker-\d+$/, '-worker-*'); (by[g] = by[g] || { calls: 0, ok: 0, results: 0, errs: {}, maxMs: 0 }); by[g].calls++; if (c.status === 200 && !c.err) by[g].ok++; by[g].results += c.n || 0; by[g].maxMs = Math.max(by[g].maxMs, c.ms); if (c.err || c.status !== 200) { const k = (c.err || 'HTTP ' + c.status); by[g].errs[k] = (by[g].errs[k] || 0) + 1; } }
  const trackA = plain.match(/\d+\.\s+\S+\s+([A-Z0-9]{2,10})\s+[$£€]([A-Z]*[0-9.]+)/g) || []; const trackB = plain.match(/^\s*\d+\.\s+([A-Z0-9]{1,10}(?:[.-][A-Z]+)?)\s+.{0,40}?[$£€¥]([A-Z]*[0-9.]+)/gm) || [];
  const flags = [...new Set(plain.match(/\bundefined\b|\bNaN\b|\[object Object\]|Unrated|\b(STRONG_BUY|MODERATE_BUY|MODERATE_SELL|STRONG_SELL|STRONG BUY|STRONG SELL|BUY|SELL|HOLD|AVOID|CONSIDER)\b|Take Profit|Stop Loss|Recommendation(?!s? to buy)|Infinity/g) || [])];
  const summary = { button: `${option}-${subOption}`, secs: +((Date.now() - t0) / 1000).toFixed(1), type: out.result && out.result.type, error: out.error || thrown, chars: text.length, lines: plain.split('\n').length,
    analyzed: (plain.match(/(?:Stocks? Analyzed|Symbols Analyzed|Total coins analyzed|Signals Generated|Screening Universe|Analysis: )[^\n]{0,60}/i) || [''])[0].trim(), trackerSymbols: (trackA.length || trackB.length), flags, lambdas: by, blocked: [...new Set(blocked)] };
  fs.writeFileSync(`page_${option}-${subOption}.json`, JSON.stringify({ summary, text: plain }));
  console.log(JSON.stringify(summary));
  process.exit(0);
})();
