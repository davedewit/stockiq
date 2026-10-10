// Run the real page code (auth.js + analysis-functions.js) as an ANONYMOUS visitor.
// The usage tracker is simulated: it starts at USED (default 0, so 1 of 1 free use left) and counts increments.
// Analysis Lambdas are called for real. Usage: node anon_run.js 72 single   |   USED=1 node anon_run.js 72 single
const vm = require('vm'), fs = require('fs');
const [option, subOption] = process.argv.slice(2);
let usage = Number(process.env.USED || 0); const events = []; const t0 = Date.now(); const log = (m) => events.push(`${((Date.now() - t0) / 1000).toFixed(1)}s ${m}`);
const realFetch = fetch;
async function fakeFetch(url, opts = {}) {
  const u = String(url); let body = {}; try { body = JSON.parse(opts.body || '{}'); } catch (e) {}
  const json = (o) => ({ ok: true, status: 200, json: async () => o, text: async () => JSON.stringify(o) });
  if (u.includes('ipify')) return json({ ip: '203.0.113.7' });
  if (u.includes('dcegrxwikpuwup7qas24dubloq0ohurf')) {           // anonymous usage tracker
    if (body.action === 'increment_usage') { usage++; log(`tracker: increment -> usage ${usage}`); return json({ usage }); }
    log(`tracker: get_usage -> ${usage}`); return json({ usage });
  }
  if (/5fyemil3eipbwqyyb2kloijyhi0uvtct|uotf7ibcklwyuehblv7zsl7ney0ngmrl|5oqosafg2mflk7oyydkk3d3rdq0amufq/.test(u) || /worker|lambda-url/.test(u) && !/usage|trial|dashboard/.test(u)) {
    log(`analysis call start: ${u.slice(8, 30)}…`); const r = await realFetch(url, opts); const txt = await r.text(); log(`analysis call done (${r.status})`);
    return { ok: r.ok, status: r.status, json: async () => JSON.parse(txt), text: async () => txt };
  }
  log(`other fetch blocked: ${u.slice(0, 60)}`); return json({ success: true, usage: 0 });
}
const mkEl = (id) => ({ id, style: {}, innerHTML: '', textContent: '', value: id === 'coin-symbol-input' ? 'BTC' : id === 'symbols-input' ? 'AAPL' : id === 'signals-symbols' ? 'AAPL' : '', dataset: {}, children: [], onclick: null,
  classList: { add() {}, remove() {}, toggle() {}, contains: () => false }, appendChild() {}, remove() {}, setAttribute() {}, getAttribute: () => null, addEventListener() {}, scrollIntoView() {}, focus() {}, querySelectorAll: () => [], querySelector: () => null, closest: () => null, insertAdjacentHTML() {}, getContext: () => null, toDataURL: () => '' });
const els = {}; const store = {};
const document = { getElementById: (id) => els[id] || (els[id] = mkEl(id)), querySelectorAll: () => [], querySelector: () => null, createElement: (t) => mkEl('new-' + t), addEventListener() {}, body: mkEl('body'), head: mkEl('head'), cookie: '', title: '', readyState: 'complete', referrer: '' };
const loc = { _href: 'https://stockiq.tech/analysis.html?option=' + option, search: '?option=' + option, pathname: '/analysis.html', hostname: 'stockiq.tech', origin: 'https://stockiq.tech', reload() { log('location.reload()'); }, replace(u) { log('REDIRECT via replace -> ' + u); } };
Object.defineProperty(loc, 'href', { get() { return this._href; }, set(v) { const st = new Error().stack.split('\n').slice(2, 7).map(x => x.trim().replace(/^at /, '')).join(' <- '); log(`REDIRECT -> ${v}   [${st}]`); } });
const ctx = { console: { log() {}, warn() {}, error() {}, info() {} }, setTimeout, clearTimeout, setInterval: () => 0, clearInterval() {}, fetch: fakeFetch, document, navigator: { userAgent: 'Mozilla/5.0 (Macintosh) Chrome/120', onLine: true, language: 'en', hardwareConcurrency: 8, platform: 'MacIntel' },
  localStorage: { getItem: (k) => store[k] ?? null, setItem(k, v) { store[k] = String(v); }, removeItem(k) { delete store[k]; } }, sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  location: loc, URL, URLSearchParams, Blob: function () {}, alert(m) { log('ALERT: ' + m); }, gtag() {}, performance, AbortController, TextEncoder, TextDecoder, Intl, crypto: globalThis.crypto, atob, btoa, screen: { width: 1300, height: 900, colorDepth: 24 },
  addEventListener() {}, removeEventListener() {}, dispatchEvent() {}, innerWidth: 1300, innerHeight: 900, scrollTo() {}, scrollY: 0, open() {}, matchMedia: () => ({ matches: false, addEventListener() {} }), requestAnimationFrame: (f) => setTimeout(f, 0), history: { pushState() {}, replaceState() {} }, getComputedStyle: () => ({}) };
ctx.window = new Proxy(ctx, { get: (t, k) => (k in t ? t[k] : undefined), set: (t, k, v) => { t[k] = v; return true; } }); ctx.globalThis = ctx; ctx.self = ctx.window;
vm.createContext(ctx);
// class declarations are not visible across scripts unless exposed: load auth.js and make authManager global
vm.runInContext(fs.readFileSync('/Users/dave/VSCODE/website/auth.js', 'utf8') + '\n;try{globalThis.authManager = authManager;}catch(e){}', ctx, { filename: 'auth.js' });
vm.runInContext(fs.readFileSync('/Users/dave/VSCODE/website/analysis-functions.js', 'utf8'), ctx, { filename: 'analysis-functions.js' });
const out = {};
Object.assign(ctx, { displayResults: (r) => { out.result = r; log(`RESULT displayed (type ${r && r.type}, ${String(r && r.data || '').length} chars)`); }, displayError: (m) => { out.error = m; log('ERROR displayed: ' + m); }, saveAnalysisToHistory: () => log('saveAnalysisToHistory called'),
  showAnonymousUpgradeModal: () => log('showAnonymousUpgradeModal'), startCountdown() {}, clearCountdown() {} });
(async () => {
  log(`authManager present: ${typeof ctx.authManager !== 'undefined'} | authenticated: ${ctx.authManager && ctx.authManager.isAuthenticated ? ctx.authManager.isAuthenticated() : 'n/a'}`);
  try { await ctx.runAnalysis(Number(option), subOption, { target: mkEl('btn'), currentTarget: mkEl('btn'), preventDefault() {}, stopPropagation() {} }); } catch (e) { log('runAnalysis threw: ' + e.message); }
  await new Promise(r => setTimeout(r, 2500));
  console.log(`--- anonymous run of ${option}-${subOption}: result=${!!out.result} error=${out.error || 'none'} final usage=${usage}`);
  events.forEach(e => console.log('   ' + e.slice(0, 420)));
  process.exit(0);
})();
