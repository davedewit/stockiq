// Where does "View Pricing Plans" on the home page stop? Opens the home page in headless Chrome under an ordinary
// browser name, clicks the link with a real mouse click, and says where the pricing section's heading ends up against
// the bottom of the fixed header (the strip and the menu). Read-only: the site's own files and GETs go through, every
// other request is answered here with an empty reply, except the market-data functions that only read (so the page fills in).
//
//   node check-tools/pricing_link_check.js                  the live site, as an anonymous visitor, 1440x900
//   SIZE=390x844 node ...                                    a phone's size
//   WEB=<folder> node ...                                    the files of that folder (a staged copy), served locally
//   SHOT=<file.png> node ...                                 a picture of where it stopped
//   WAIT=<ms> node ...                                       how long after the page loads the click comes (default 6000)
//   DIRECT=1 node ...                                        no click: the page is opened at index.html#pricing, as a link from another page does
//   PAID=paid|unpaid node ...                                as a signed-in visitor (a made-up address and session) with that note in the browser
//   PAGE=dashboard.html TARGET=upgrade DIRECT=1 PAID=… node ...   another page and section: where the dashboard stops at its plans
const { spawn } = require('child_process'); const os = require('os'), fs = require('fs'), path = require('path'), http = require('http');
const SITE = path.join(__dirname, '..', '..', 'website'), WEB = process.env.WEB || '', PORT = 9351, HTTP = 8793;
const [W, H] = (process.env.SIZE || '1440x900').split('x').map(Number), WAIT = +(process.env.WAIT || 6000);
const PAGE = process.env.PAGE || 'index.html', TARGET = process.env.TARGET || 'pricing';
const jwt = (o) => 'x.' + Buffer.from(JSON.stringify(o)).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '') + '.y';
const BASE = WEB ? `http://127.0.0.1:${HTTP}/` : 'https://stockiq.tech/';
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };
const sleep = ms => new Promise(r => setTimeout(r, ms));
// The functions that only read market data (the widgets and lists of the home page) are asked for real, so that the page
// fills in and moves as it does for a visitor; nothing else is.
let READS = [];
try { const map = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'lambda-url-mapping.json'), 'utf8'));
  READS = Object.keys(map).filter(n => /^(stockiq-market-data-|gainers-scraper|losers-scraper|most-active-scraper|trending-scraper|ticker-data-fetcher|stockiq-popular-prices|stockiq-price-proxy)/.test(n)).map(n => String(map[n])); } catch (e) { /* without the map the widgets stay empty */ }
const server = http.createServer((q, r) => {
  const name = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
  const file = WEB && fs.existsSync(path.join(WEB, name)) ? path.join(WEB, name) : path.join(SITE, name);
  fs.readFile(file, (err, body) => { if (err || name.includes('..')) { r.writeHead(404); r.end(''); return; } r.writeHead(200, { 'Content-Type': TYPES[path.extname(name)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); r.end(body); });
});
(async () => {
  if (WEB) await new Promise(r => server.listen(HTTP, '127.0.0.1', r));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pricingcheck-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${dir}`, '--no-first-run', `--window-size=${W},${H}`, 'about:blank'], { stdio: 'ignore' });
  let bad = 0;
  try {
    let targets = null;
    for (let i = 0; i < 40 && !targets; i++) { await sleep(250); try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); } catch (e) { /* not up yet */ } }
    const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl); await new Promise(r => { ws.onopen = r; });
    let id = 0; const waiting = {};
    const send = (method, params = {}) => new Promise(r => { waiting[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && waiting[d.id]) { waiting[d.id](d.result || d.error); delete waiting[d.id]; return; }
      if (d.method === 'Fetch.requestPaused') {
        const q = d.params.request;
        if (q.method === 'GET' || (q.method === 'POST' && READS.some(u => q.url.startsWith(u))) || q.method === 'OPTIONS' && READS.some(u => q.url.startsWith(u))) { send('Fetch.continueRequest', { requestId: d.params.requestId }); return; }
        send('Fetch.fulfillRequest', { requestId: d.params.requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Access-Control-Allow-Headers', value: '*' }], body: Buffer.from('{}').toString('base64') });
      }
    };
    const js = async (expression) => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : undefined; };
    await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
    await send('Emulation.setUserAgentOverride', { userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' });
    await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: W < 700 });
    const look = () => js(`(function () {
      var s = document.getElementById('${TARGET}'), h = s && s.querySelector('h2, h3'), top = 0;
      ['.top-nav', '#promo-banner', '.promo-banner'].forEach(function (q) { var e = document.querySelector(q); if (!e) return; var c = getComputedStyle(e), r = e.getBoundingClientRect(); if (c.display !== 'none' && c.position === 'fixed' && r.height) top = Math.max(top, r.bottom); });
      return { y: Math.round(scrollY), header: Math.round(top), section: s ? Math.round(s.getBoundingClientRect().top) : null, heading: h ? Math.round(h.getBoundingClientRect().top) : null,
        margin: s ? getComputedStyle(s).scrollMarginTop : null, height: document.documentElement.scrollHeight };
    })()`);
    if (process.env.PAID) { const who = 'pricing-check@example.com', store = { userId: who, userEmail: who, idToken: jwt({ email: who, exp: Math.floor(Date.now() / 1000) + 3600, 'custom:tier': 'free' }), accessToken: 'x', loginTime: String(Date.now()), ['userPaidStatus_' + who]: process.env.PAID };
      await send('Page.addScriptToEvaluateOnNewDocument', { source: `try { if (!localStorage.getItem('userId')) { const s = ${JSON.stringify(store)}; Object.keys(s).forEach(k => localStorage.setItem(k, s[k])); } } catch (e) {}` }); }
    if (process.env.DIRECT) {   // arriving from another page: the address already carries #pricing
      await send('Page.navigate', { url: BASE + PAGE + '#' + TARGET }); await sleep(WAIT);
      const now = await look(), gap = now.heading - now.header; console.log('opened at #' + TARGET + '', JSON.stringify(now));
      console.log(`the section's top is ${now.section - now.header}px below the header`); const why = judge(now); console.log(why ? 'FAIL: ' + why : 'PASS'); if (why) bad = 1;
      if (process.env.SHOT) { const p = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(process.env.SHOT, Buffer.from(p.data, 'base64')); }
      throw { done: true };
    }
    // Right when the section's top stops 10 to 40px under the header (the same whether the strip across the top shows or
    // not), or, where the header has slid away (a phone scrolling down), within 60px of the top of the window.
    function judge(at) {
      const room = at.section - at.header;
      if (at.heading < at.header) return 'the heading is hidden under the header';
      if (at.header > 0 ? (room < 10 || room > 40) : (room < 0 || room > 60)) return `the section stops ${room}px under ${at.header > 0 ? 'the header' : 'the top of the window'}, not just under it`;
      return '';
    }
    await send('Page.navigate', { url: BASE + PAGE }); await sleep(WAIT);
    const before = await look(); console.log('before the click', JSON.stringify(before));
    const at = await js(`(function () { var a = document.querySelector('a[href="#pricing"]'); if (!a) return null; a.scrollIntoView({ block: 'center', behavior: 'instant' }); var r = a.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, text: a.textContent.trim() }; })()`);
    if (!at) throw new Error('no link to #pricing on the page');
    for (const type of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type, x: at.x, y: at.y, button: 'left', clickCount: 1 });
    let last = null;
    for (let i = 1; i <= 16; i++) { await sleep(250); const now = await look(); if (!last || now.y !== last.y || now.height !== last.height) console.log(`  ${(i * 0.25).toFixed(2)}s`, JSON.stringify(now)); last = now; }
    const gap = last.heading - last.header;
    console.log(`"${at.text}": the section's top is ${last.section - last.header}px below the header, its heading ${gap}px below`);
    const why = judge(last); if (why) { bad = 1; console.log('FAIL: ' + why); } else console.log('PASS');
    if (process.env.SHOT) { const p = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(process.env.SHOT, Buffer.from(p.data, 'base64')); }
  } catch (e) { if (!e.done) { bad = 1; console.log('ERROR', e.message); } }
  chrome.kill(); server.close(); try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) { /* in use */ }
  process.exit(bad);
})();
