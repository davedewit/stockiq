// The home page's search boxes show a share's latest news (26 Oct 2026, the owner: "when users type in the search box for a company
// or stock, can it include to show related news articles?"). Opens the home page served from this machine, types a code that has a
// stock page and one that has none, picks a suggestion, clears the box, at desktop and phone size, and reads the news box each time.
//
//   node check-tools/search_news_check.js          WEB=<folder> serves a staged copy's files first; SHOT=<folder> takes pictures
//
// Nothing is written anywhere: the pages and stock pages are served from this machine and every other request is answered here
// (the symbol lookup with a made-up list of suggestions, everything else with {}).
const { spawn } = require('child_process'); const os = require('os'), fs = require('fs'), path = require('path'), http = require('http');
const SITE = path.join(__dirname, '..', '..', 'website'), WEB = process.env.WEB || '', PORT = 9363, HTTP = 8797, BASE = `http://127.0.0.1:${HTTP}/`;
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.txt': 'text/plain' };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const LOOKUP = '3oaokynmssanpzz7bwomt7ft6i0qrwhk';          // stockiq-validate-symbol: the suggestions under the search box
const server = http.createServer((q, r) => {
  const name = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
  if (name.includes('..')) { r.writeHead(400); r.end(); return; }
  const file = WEB && fs.existsSync(path.join(WEB, name)) ? path.join(WEB, name) : path.join(SITE, name);
  fs.readFile(file, (err, body) => { if (err) { r.writeHead(404); r.end(''); return; } r.writeHead(200, { 'Content-Type': TYPES[path.extname(name)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); r.end(body); });
});
(async () => {
  await new Promise(r => server.listen(HTTP, '127.0.0.1', r));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'searchnews-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${dir}`, '--no-first-run', '--window-size=1440,900'], { stdio: 'ignore' });
  let failed = 0;
  const check = (what, ok, detail) => { if (!ok) failed++; console.log(`${ok ? 'PASS' : 'FAIL'} ${what}${detail ? ': ' + detail : ''}`); };
  try {
    let targets = null;
    for (let i = 0; i < 40 && !targets; i++) { await sleep(250); try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); } catch (e) { /* not up yet */ } }
    const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl); await new Promise(r => { ws.onopen = r; });
    let id = 0; const waiting = {};
    const send = (method, params = {}) => new Promise(r => { waiting[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && waiting[d.id]) { waiting[d.id](d.result || d.error); delete waiting[d.id]; return; }
      if (d.method !== 'Fetch.requestPaused') return;
      const q = d.params.request;
      if (q.url.startsWith(BASE) && q.method === 'GET') { send('Fetch.continueRequest', { requestId: d.params.requestId }); return; }
      let b = {}; try { b = JSON.parse(q.postData || '{}'); } catch (e) { /* not JSON */ }
      const reply = q.url.includes(LOOKUP) ? { suggestions: b.symbol === 'APPLE' ? [{ symbol: 'AAPL', name: 'Apple Inc.' }, { symbol: 'APLE', name: 'Apple Hospitality REIT' }] : [] }
        : (b.action === 'get_usage' || b.action === 'increment_usage') ? { usage: 0, success: true } : {};
      const js = /\.js(\?|$)/.test(q.url), css = /\.css(\?|$)|fonts\.googleapis/.test(q.url);
      send('Fetch.fulfillRequest', { requestId: d.params.requestId, responseCode: 200,
        responseHeaders: [{ name: 'Content-Type', value: js ? 'application/javascript' : css ? 'text/css' : 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Access-Control-Allow-Headers', value: '*' }],
        body: Buffer.from(js || css ? '' : JSON.stringify(reply)).toString('base64') });
    };
    const js = async (expression) => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : undefined; };
    await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
    const box = (sel) => js(`(() => { const e = document.querySelector('${sel}'); if (!e) return { missing: true }; const r = e.getBoundingClientRect(); return { shown: getComputedStyle(e).display !== 'none' && r.height > 0, text: e.textContent.replace(/\\s+/g, ' ').trim().slice(0, 300), links: e.querySelectorAll('a.sn-item').length, page: (e.querySelector('a.sn-page') || {}).getAttribute ? e.querySelector('a.sn-page').getAttribute('href') : null, wide: Math.round(r.right) <= window.innerWidth }; })()`);
    const type = async (sel, text) => { await js(`(() => { const e = document.querySelector('${sel}'); e.focus(); e.value = ''; return 1; })()`); await send('Input.insertText', { text }); await js(`document.querySelector('${sel}').dispatchEvent(new Event('input', { bubbles: true })), 1`); await sleep(1600); };
    // the page under test needs a stock page with news: the first share in stock-pages.js whose page has a NEWS section with articles
    const list = (fs.readFileSync(path.join(SITE, 'stock-pages.js'), 'utf8').match(/"([^"]*)"/) || [])[1] || '';
    const withNews = ['AAPL'].concat(list.split(',')).find(s => { try { return /Read full article/.test(fs.readFileSync(path.join(SITE, 'stocks', s + '.html'), 'utf8')); } catch (e) { return false; } });
    for (const [size, w, h, mobile] of [['desktop', 1440, 900, false], ['phone', 390, 844, true]]) {
      await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile });
      await send('Emulation.setUserAgentOverride', { userAgent: mobile ? 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' });
      await send('Page.navigate', { url: BASE + 'index.html' }); await sleep(2500);
      await type('#stock-search', withNews);
      let b = await box('#home-symbol-news');
      check(`${size}: typing ${withNews} (it has a stock page with news) shows its headlines`, b.shown && b.links >= 1 && b.page === `stocks/${withNews}.html` && b.wide, JSON.stringify(b).slice(0, 220));
      const sug = await js(`getComputedStyle(document.getElementById('home-symbol-suggestions')).display`);
      check(`${size}: with the news on show, the empty suggestion list is closed (nothing covers the news)`, sug === 'none', sug);
      if (process.env.SHOT) {      // SHOT=<folder>: a picture of the search and its news box
        const r = JSON.parse(await js(`(() => { const e = document.querySelector('.search-container'); e.scrollIntoView({ block: 'start' }); const a = e.getBoundingClientRect(), b = document.getElementById('home-symbol-news').getBoundingClientRect(); return JSON.stringify({ x: 0, y: Math.max(0, a.top + scrollY - 20), width: innerWidth, height: b.bottom - a.top + 40 }); })()`));
        const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: Object.assign(r, { scale: 1 }) });
        fs.writeFileSync(path.join(process.env.SHOT, `search-news-${size}.png`), Buffer.from(shot.data, 'base64'));
      }
      await type('#stock-search', 'ZZQX');
      b = await box('#home-symbol-news');
      check(`${size}: typing a code with no stock page shows no news box`, !b.shown, JSON.stringify(b).slice(0, 120));
      await type('#stock-search', 'APPLE');
      const picked = await js(`(() => { const s = [...document.querySelectorAll('#home-symbol-suggestions div')].find(d => /AAPL/.test(d.textContent)); if (!s) return 'no suggestion'; s.click(); return 'clicked'; })()`); await sleep(1200);
      b = await box('#home-symbol-news');
      check(`${size}: picking Apple from the suggestions shows AAPL's news`, picked === 'clicked' && b.shown && /AAPL/.test(b.text), picked + ' ' + JSON.stringify(b).slice(0, 160));
      await js(`document.getElementById('stock-search-clear').click(), 1`); await sleep(300);
      b = await box('#home-symbol-news');
      check(`${size}: the × clears the news box`, !b.shown, JSON.stringify(b).slice(0, 100));
      if (!mobile) {
        const side = await js(`!!document.getElementById('side-stock-search') && getComputedStyle(document.getElementById('quick-analysis-panel') || document.body).display !== 'none'`);
        if (side) { await type('#side-stock-search', withNews); b = await box('#side-symbol-news'); check(`${size}: the side panel's search shows the news too`, b.shown && b.links >= 1, JSON.stringify(b).slice(0, 160)); }
      }
    }
    ws.close();
  } finally { chrome.kill(); server.close(); await sleep(300); fs.rmSync(dir, { recursive: true, force: true }); }
  console.log(failed ? `${failed} FAILED` : 'ALL PASS');
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error('failed: ' + e.message); process.exit(1); });
