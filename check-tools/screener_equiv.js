// Does a changed analysis-functions.js give the same reports as the one it replaces? For each screener button it runs
// the OLD page code once for real (the workers are really called, and their answers kept), then runs OLD and NEW again
// on those kept answers with the clock stopped, and compares what each asked the workers and what each produced: the
// report text, its type and the CSV, character for character.
//
//   node check-tools/screener_equiv.js <old analysis-functions.js> <new analysis-functions.js> [button ...]
//   PRE=<file> node ...       a file the NEW side loads first (screeners.js)
//   PRE_OLD=<file> node ...   the same for the OLD side, when the old code already has one
//   buttons: 3-8 3-100 ... (default: the 14 share screeners)
//
// Nothing is saved to anyone's history and no usage is counted: as in page_run.js, everything but the analysis workers
// is answered here. The workers themselves are read-only.
const vm = require('vm'), fs = require('fs');
const [oldFile, newFile, ...rest] = process.argv.slice(2);
const BUTTONS = rest.length ? rest : ['3-8', '3-100', '3-7', '3-3', '3-2', '3-4', '3-5', '3-6', '5-50', '5-100', '5-200', '5-300', '5-nikkei225', '4-ftse100'];
const map = JSON.parse(fs.readFileSync('/Users/dave/VSCODE/stockiq/lambda-url-mapping.json', 'utf8'));
const nameOf = {}; for (const [n, u] of Object.entries(map)) { const h = (u.match(/https:\/\/([a-z0-9]+)\./) || [])[1]; if (h) nameOf[h] = n; }
const BLOCK = /usage|trial|dashboard|tracker|email|payment|checkout|notification|ip-blocking|cognito|delete|csv-export/i;
const FIXED = Date.UTC(2026, 9, 13, 12, 0, 0);
class StoppedDate extends Date { constructor(...a) { if (a.length) super(...a); else super(FIXED); } static now() { return FIXED; } }

// One run of one button with the given page code. `kept` = the workers' answers: filled when `record`, replayed otherwise.
async function run(file, pre, option, subOption, kept, record) {
  const asked = [];
  async function pageFetch(url, opts = {}) {
    const host = (String(url).match(/https:\/\/([a-z0-9]+)\./) || [])[1] || String(url).slice(0, 40);
    const name = nameOf[host] || (String(url).includes('ipify') ? 'ipify' : 'UNKNOWN:' + host);
    if (BLOCK.test(name) || name === 'ipify') return { ok: true, status: 200, json: async () => ({ success: true, usage: 0, dailyLimit: 999999, allowed: true, canAnalyze: true }), text: async () => '{}' };
    const key = String(url) + ' ' + (opts.body || '');
    asked.push(key);
    if (record) { const r = await fetch(url, opts); kept[key] = { status: r.status, ok: r.ok, text: await r.text() }; }
    const k = kept[key];
    if (!k) return { ok: false, status: 599, json: async () => { throw new Error('not asked in the first run'); }, text: async () => '' };
    return { ok: k.ok, status: k.status, json: async () => JSON.parse(k.text), text: async () => k.text };
  }
  const typed = { 'symbols-input': 'AAPL, KO', 'signals-symbols': 'NVDA, BA, KO', 'coin-symbol-input': 'BTC' };
  const mkEl = id => ({ style: {}, innerHTML: '', textContent: '', value: typed[id] !== undefined ? typed[id] : '', onclick: null, dataset: {}, children: [], classList: { add() {}, remove() {}, toggle() {}, contains: () => false }, appendChild() {}, remove() {},
    setAttribute() {}, getAttribute: () => null, addEventListener() {}, scrollIntoView() {}, focus() {}, querySelectorAll: () => [], querySelector: () => null, closest: () => null, insertAdjacentHTML() {} });
  const els = {}, store = {};
  const document = { getElementById: id => els[id] || (els[id] = mkEl(id)), querySelectorAll: () => [], querySelector: () => null, createElement: () => Object.assign(mkEl('new'), { download: '' }), addEventListener() {}, body: mkEl('body'), head: mkEl('head'), cookie: '', title: '', readyState: 'complete' };
  const stubFn = () => new Proxy(function () {}, { get: (t, k) => k === Symbol.toPrimitive ? () => '' : stubFn(), apply: () => stubFn() });
  const out = { result: null, error: null };
  const ctx = { console: { log() {}, warn() {}, error() {}, info() {} }, setTimeout, clearTimeout, setInterval: () => 0, clearInterval() {}, fetch: pageFetch, document, navigator: { userAgent: 'Mozilla/5.0 Chrome', language: 'en-US' },
    localStorage: { getItem: k => store[k] ?? null, setItem(k, v) { store[k] = String(v); }, removeItem(k) { delete store[k]; } }, sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { href: 'https://stockiq.tech/analysis.html', search: '', pathname: '/analysis.html', hostname: 'stockiq.tech' }, URL, URLSearchParams, Blob, alert() {}, gtag() {}, performance, AbortController, TextEncoder, TextDecoder,
    Date: record ? Date : StoppedDate, Math, JSON, Promise, parseInt, parseFloat, isNaN, Number, String, Array, Object, Intl, authManager: undefined, innerWidth: 1400, scrollTo() {}, addEventListener() {}, requestAnimationFrame: f => setTimeout(f, 0), history: { replaceState() {}, pushState() {} }, matchMedia: () => ({ matches: false, addEventListener() {} }) };
  ctx.window = new Proxy(ctx, { get: (t, k) => k in t ? t[k] : undefined, set: (t, k, v) => { t[k] = v; return true; } }); ctx.globalThis = ctx; ctx.self = ctx.window;
  vm.createContext(ctx);
  if (pre) vm.runInContext(fs.readFileSync(pre, 'utf8'), ctx, { filename: 'screeners.js' });
  vm.runInContext(fs.readFileSync(file, 'utf8'), ctx, { filename: 'analysis-functions.js' });
  Object.assign(ctx, { displayResults: r => { out.result = r; }, displayError: m => { out.error = m; }, saveAnalysisToHistory() {}, isBotOrCrawler: () => false, showAnonymousUpgradeModal() {}, showStickyUpgradeButton() {}, startCountdown() {}, clearCountdown() {}, refreshUsageCount() {} });
  let thrown = null;
  try { await ctx.runAnalysis(Number(option), subOption, { target: mkEl('btn'), currentTarget: mkEl('btn'), preventDefault() {}, stopPropagation() {} }); } catch (e) { thrown = e.message; }
  const r = out.result || {};
  return { asked, type: r.type || null, data: String(r.data || ''), csv: JSON.stringify(r.csvData === undefined ? null : r.csvData), error: out.error || thrown };
}

const firstDiff = (a, b) => { let i = 0; while (i < a.length && i < b.length && a[i] === b[i]) i++; return `at character ${i}: old "${a.slice(Math.max(0, i - 40), i + 60).replace(/\n/g, '\\n')}" | new "${b.slice(Math.max(0, i - 40), i + 60).replace(/\n/g, '\\n')}"`; };

(async () => {
  let failed = 0;
  for (const b of BUTTONS) {
    const [option, ...subParts] = b.split('-'), sub = subParts.join('-'), kept = {};
    const t0 = Date.now();
    const live = await run(oldFile, process.env.PRE_OLD, option, sub, kept, true);
    const n = Object.keys(kept).length, okN = Object.values(kept).filter(k => k.ok).length;
    const o = await run(oldFile, process.env.PRE_OLD, option, sub, kept, false), w = await run(newFile, process.env.PRE, option, sub, kept, false);
    const stocks = (o.data.match(/^\s*\d+\.\s+\S+/gm) || []).length;
    const same = { asked: JSON.stringify(o.asked) === JSON.stringify(w.asked), type: o.type === w.type, report: o.data === w.data, csv: o.csv === w.csv, error: String(o.error) === String(w.error) };
    const all = Object.values(same).every(Boolean) && o.data.length > 500 && !o.error;
    console.log(`${all ? 'SAME ' : 'DIFFERENT '} ${b.padEnd(13)} ${String(n).padStart(3)} worker calls (${okN} answered), report ${o.data.length} characters, CSV ${o.csv.length}, ${((Date.now() - t0) / 1000).toFixed(0)}s` +
      (all ? '' : '\n     ' + Object.entries(same).filter(([, v]) => !v).map(([k]) => k).join(', ') + ' differ' + (o.error || w.error ? ` | errors: old ${o.error} new ${w.error}` : '') + (same.report ? '' : '\n     report ' + firstDiff(o.data, w.data)) + (same.asked ? '' : `\n     asked ${o.asked.length} / ${w.asked.length}: ` + firstDiff(o.asked.join('\n'), w.asked.join('\n'))) + (same.csv ? '' : '\n     csv ' + firstDiff(o.csv, w.csv))));
    if (!all) failed++;
    if (live.error) console.log('     (the first, real run ended with: ' + live.error + ')');
  }
  console.log(failed ? `${failed} of ${BUTTONS.length} differ` : `all ${BUTTONS.length} screeners: the same requests, the same report, the same CSV`);
  process.exit(failed ? 1 : 0);
})();
