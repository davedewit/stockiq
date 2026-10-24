// Does every public page fit a phone? (24 Oct 2026, the owner: "make sure mobile version of the site is good too ... most people do use
// mobile over desktop".) Opens each page in headless Chrome at a phone's size under an ordinary browser name, waits for it to fill in,
// and says whether the page can be scrolled sideways and which elements stick out past the screen. Since 24 Oct 2026 it also checks
// the header every page should have on a phone (the owner found the daily screener pages without it): the ☰ button on show and
// opening the menu, the bell, and the usage chip (site-header.js fills these in where a page's own markup lacks them). An element inside a box that scrolls
// sideways by itself (a wide table in its own scroller) does not count; nor do the panels that slide in from the side.
// Read-only: the site's own files and GETs go through, and the functions that only read market data; every other request is answered
// here with an empty reply, so nothing is written.
//
//   node check-tools/phone_check.js                          the live site, the usual pages, 390x844
//   node check-tools/phone_check.js index.html faq.html      only these
//   SIZE=360x740 node ...                                    another phone
//   WEB=<folder> node ...                                    a staged copy served locally (its files first, then website/)
//   SHOTS=<folder> node ...                                  a picture of the top of each page
const { spawn } = require('child_process'); const os = require('os'), fs = require('fs'), path = require('path'), http = require('http');
const SITE = path.join(__dirname, '..', '..', 'website'), WEB = process.env.WEB || '', PORT = 9355, HTTP = 8795;
const [W, H] = (process.env.SIZE || '390x844').split('x').map(Number);
const PAGES = process.argv.slice(2).length ? process.argv.slice(2) : ['index.html', 'analysis.html', 'screeners-today.html', 'screener-asx-200.html',
  'about.html', 'faq.html', 'blog.html', 'news.html', 'signup.html', 'login.html', 'stock-screener-guide.html', 'stocks/AAPL.html', 'contact.html', 'terms.html', 'screener-dax-40.html'];
const BASE = WEB ? `http://127.0.0.1:${HTTP}/` : 'https://stockiq.tech/';
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };
const sleep = ms => new Promise(r => setTimeout(r, ms));
let READS = [];
try { const map = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'lambda-url-mapping.json'), 'utf8'));
  READS = Object.keys(map).filter(n => /^(stockiq-market-data-|gainers-scraper|losers-scraper|most-active-scraper|trending-scraper|ticker-data-fetcher|stockiq-popular-prices|stockiq-price-proxy)/.test(n)).map(n => String(map[n])); } catch (e) { /* no map: nothing read for real */ }
const server = http.createServer((q, r) => {
  const name = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
  const file = WEB && fs.existsSync(path.join(WEB, name)) ? path.join(WEB, name) : path.join(SITE, name);
  fs.readFile(file, (err, body) => { if (err || name.includes('..')) { r.writeHead(404); r.end(''); return; } r.writeHead(200, { 'Content-Type': TYPES[path.extname(name)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); r.end(body); });
});
(async () => {
  if (WEB) await new Promise(r => server.listen(HTTP, '127.0.0.1', r));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'phonecheck-'));
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
        if (q.method === 'GET' || ((q.method === 'POST' || q.method === 'OPTIONS') && READS.some(u => q.url.startsWith(u)))) { send('Fetch.continueRequest', { requestId: d.params.requestId }); return; }
        send('Fetch.fulfillRequest', { requestId: d.params.requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' }], body: Buffer.from('{}').toString('base64') });
      }
    };
    const js = async (expression) => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : undefined; };
    await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
    await send('Emulation.setUserAgentOverride', { userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1' });
    await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 2, mobile: true });
    for (const page of PAGES) {
      await send('Page.navigate', { url: BASE + page }); await sleep(5000);
      const r = await js(`(function () {
        var vw = document.documentElement.clientWidth, out = [];
        // a box that scrolls by itself is fine; a box that hides what overflows cuts the element off, which is counted
        var scrolls = function (e) { for (var a = e.parentElement; a && a !== document.body; a = a.parentElement) { var c = getComputedStyle(a); if (/(auto|scroll)/.test(c.overflowX) && a.scrollWidth > a.clientWidth + 1) return true; if (c.position === 'fixed' && a.getBoundingClientRect().left >= vw - 1) return true; } return false; };
        var offCanvas = function (e) { for (var a = e; a; a = a.parentElement) { var c = getComputedStyle(a), b = a.getBoundingClientRect(); if ((c.position === 'fixed' || c.position === 'absolute') && (b.left >= vw - 1 || b.right <= 1)) return true; if (c.visibility === 'hidden' || c.display === 'none') return true; } return false; };
        document.querySelectorAll('body *').forEach(function (e) {
          var b = e.getBoundingClientRect(); if (!b.width || !b.height || b.right <= vw + 2) return;
          if (offCanvas(e) || scrolls(e)) return;
          var name = e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\\s+/).slice(0, 2).join('.') : '');
          out.push(name + ' to ' + Math.round(b.right) + 'px');
        });
        var deepest = out.filter(function (x, i) { return out.indexOf(x) === i; }).slice(-4);
        return { sideways: document.documentElement.scrollWidth > vw + 1, width: document.documentElement.scrollWidth, vw: vw, outside: out.length, examples: deepest, title: document.title.slice(0, 50) };
      })()`);
      if (!r) { console.log(`FAIL ${page}: did not load`); bad++; continue; }
      const head = await js(`(async function () {
        for (var w = 0; w < 30 && !document.getElementById('vb-chip'); w++) await new Promise(function (r) { setTimeout(r, 100); });   // the chip comes after three scripts in turn
        var miss = [], btn = document.querySelector('.hamburger-btn'), b = btn && btn.getBoundingClientRect();
        if (!btn || !b.width || !b.height) miss.push('no ☰ button on show');
        if (!/(login|signup)\\.html/.test(location.pathname) && !document.getElementById('mobile-notification-bell')) miss.push('no bell');   // nobody is signed in on the sign-in pages
        if (!document.getElementById('vb-chip')) miss.push('no usage chip');
        if (!document.querySelector('.mobile-section-title')) miss.push('no phone menu');
        if (btn && b.width) { btn.click(); await new Promise(function (r) { setTimeout(r, 500); });
          var m = document.getElementById('mobile-menu'), mb = m && m.getBoundingClientRect();
          if (!m || !m.classList.contains('open') || mb.right < 50) miss.push('the ☰ button does not open the menu');
          if (typeof closeMobileMenu === 'function') closeMobileMenu(); }
        return miss;
      })()`) || ['the header could not be read'];
      const ok = !r.sideways && r.outside === 0 && !head.length;
      if (!ok) bad++;
      console.log(`${ok ? 'PASS' : 'FAIL'} ${page}: ${r.sideways ? `scrolls sideways (${r.width}px on a ${r.vw}px screen)` : 'no sideways scroll'}${r.outside ? `; ${r.outside} element(s) past the edge, e.g. ${r.examples.join('; ')}` : ''}${head.length ? '; header: ' + head.join(', ') : '; header complete'}`);
      if (process.env.SHOTS) { const p = await send('Page.captureScreenshot', { format: 'png' }); fs.mkdirSync(process.env.SHOTS, { recursive: true }); fs.writeFileSync(path.join(process.env.SHOTS, page.replace(/\//g, '_') + '.png'), Buffer.from(p.data, 'base64')); }
    }
  } catch (e) { console.log('FAIL the check could not run: ' + e.message); bad++; }
  chrome.kill(); if (WEB) server.close();
  console.log(bad ? `${bad} page(s) fail on a ${W}px phone (fit or header)` : `ALL PASS: every page fits a ${W}px phone and has the whole header`);
  process.exit(bad ? 1 : 0);
})();
