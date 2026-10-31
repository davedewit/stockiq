// The market data on a page moves while someone looks at it (live-market.js, 18 Oct 2026). Opens pages of the site in headless
// Chrome at desktop size, with the price function and the market-data functions answered by a stand-in whose prices move at
// every call, moves the mouse now and then, and checks: the script loads; one request a round to the price function for every
// figure on show; the movers' prices and the side panel's figures change and flash; the side panel's small charts are today's
// line from the answer, not random; nothing is asked for while nobody moves; the gap grows when the prices stop moving.
//
//   node check-tools/live_market_check.js index.html dashboard.html stocks/AAPL.html
//   WEB=<folder> node ...    files found in that folder are served instead of the ones in ../website (a staged copy)
//   SHOTS=<folder> node ...  a picture of each page at the end
//   REAL_TIMES=1 node ...    the page's own gaps, not the test's shortened ones: about 40 s of use a page, then every gap between
//                            requests must lie inside the range live-market.js sets (update_interval.sh changes it), and every
//                            flash must come within half a second of the answer that caused it
//
// Nothing real is called: every request beyond the site's own files is answered here.
const { spawn } = require('child_process'); const os = require('os'), fs = require('fs'), path = require('path'), http = require('http');
const pages = process.argv.slice(2).length ? process.argv.slice(2) : ['index.html'];
const SITE = path.join(__dirname, '..', '..', 'website'), WEB = process.env.WEB || '', PORT = 9351, HTTP = 8795;
const BASE = `http://127.0.0.1:${HTTP}/`, PRICES = '2vl4la6od3vfgbkv6ycbj7ewry0yxvck';
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.txt': 'text/plain' };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const LISTS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN'];
const CATS = { us: [['S&P 500', '^GSPC', 7650], ['Dow Jones', '^DJI', 46000], ['Nasdaq', '^IXIC', 25000], ['Russell 2000', '^RUT', 2400], ['VIX', '^VIX', 20], ['10-Year', '^TNX', 4.1]] };
['europe', 'asia', 'cryptocurrencies', 'rates', 'commodities', 'currencies'].forEach(c => { CATS[c] = CATS.us.map(([n, s, v]) => [c + ' ' + n, s, v]); });
let calls = 0, frozen = false, priceRequests = [], lastData = {}, stockRequests = [];

const server = http.createServer((q, r) => {
  const name = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
  if (name.includes('..')) { r.writeHead(400); r.end(); return; }
  const staged = WEB && fs.existsSync(path.join(WEB, name)) ? path.join(WEB, name) : path.join(SITE, name);
  fs.readFile(staged, (err, body) => {
    if (err) { r.writeHead(404); r.end(''); return; }
    r.writeHead(200, { 'Content-Type': TYPES[path.extname(name)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); r.end(body);
  });
});

function priceAnswer(body) {
  let tickers = []; try { tickers = JSON.parse(body).tickers || []; } catch (e) { }
  if (!frozen) calls++;
  const data = {};
  tickers.forEach((t, i) => {
    const base = (CATS.us.find(x => x[1] === t) || [0, 0, 100 + i * 10])[2], price = +(base * (1 + calls * 0.001)).toFixed(2);
    data[t] = { name: t, price, change: +(price - base).toFixed(2), changePercent: +((price / base - 1) * 100).toFixed(2), error: false,
                spark: [base * 0.99, base * 1.004, base * 0.997, price], prev: base };
  });
  Object.assign(lastData, data);
  return { success: true, data };
}
function anyAnswer() {
  const out = { success: true, tickers: LISTS, timestamp: new Date().toISOString() };
  Object.keys(CATS).forEach(c => { out[c] = {}; CATS[c].forEach(([n, s, v]) => { out[c][n] = { value: v, change: 1, changePercent: 0.1, symbol: s }; }); });
  return out;
}

(async () => {
  await new Promise(r => server.listen(HTTP, '127.0.0.1', r));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'livecheck-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${dir}`, '--no-first-run', '--window-size=1600,1100'], { stdio: 'ignore' });
  let failed = 0, passed = 0;
  const check = (name, ok, extra) => { if (ok) passed++; else failed++; console.log((ok ? 'PASS ' : 'FAIL ') + name + (ok || extra === undefined ? '' : '  ' + JSON.stringify(extra).slice(0, 400))); };
  try {
    let targets = null;
    for (let i = 0; i < 40 && !targets; i++) { await sleep(250); try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); } catch (e) { } }
    const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl); await new Promise(r => { ws.onopen = r; });
    let id = 0; const waiting = {}; const errors = [];
    const send = (method, params = {}) => new Promise(r => { waiting[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
    const reply = (rid, obj, type) => send('Fetch.fulfillRequest', { requestId: rid, responseCode: 200,
      responseHeaders: [{ name: 'Content-Type', value: type || 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Access-Control-Allow-Headers', value: '*' }],
      body: Buffer.from(typeof obj === 'string' ? obj : JSON.stringify(obj)).toString('base64') });
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && waiting[d.id]) { waiting[d.id](d.result || d.error); delete waiting[d.id]; return; }
      if (d.method === 'Fetch.requestPaused') {
        const q = d.params.request;
        if (q.url.startsWith(BASE) && q.method === 'GET') { send('Fetch.continueRequest', { requestId: d.params.requestId }); return; }
        if (q.method === 'OPTIONS') { reply(d.params.requestId, ''); return; }
        if (q.url.includes(PRICES)) { const b = q.postData || ''; const rec = { at: Date.now(), body: b }; priceRequests.push(rec); reply(d.params.requestId, priceAnswer(b)).then(() => { rec.answered = Date.now(); }); return; }
        if (q.url.includes('vknfjazip3xpfwpfyd6ja6ui6q0lmxkw')) stockRequests.push(Date.now());   // a stock page's own price refresh (stock-prices.js)
        if (/lambda-url/.test(q.url)) { reply(d.params.requestId, anyAnswer()); return; }
        const js = /\.js(\?|$)/.test(q.url), css = /\.css(\?|$)|fonts\.googleapis/.test(q.url);
        reply(d.params.requestId, js || css ? '' : '{}', js ? 'application/javascript' : css ? 'text/css' : 'application/json');
      }
      if (d.method === 'Runtime.exceptionThrown') errors.push((d.params.exceptionDetails.exception && d.params.exceptionDetails.exception.description || d.params.exceptionDetails.text || '').split('\n')[0]);
    };
    const js = async (expression) => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : undefined; };
    await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
    await send('Network.enable'); await send('Network.setUserAgentOverride', { userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36' });
    await send('Page.addScriptToEvaluateOnNewDocument', { source: `try { localStorage.setItem('userId', 'live-check@example.com'); localStorage.setItem('userEmail', 'live-check@example.com');
      ${JSON.stringify(['gainersTickersList', 'losersTickersList', 'activeTickersList', 'trendingTickersList'])}.forEach(function (k) { localStorage.setItem(k, ${JSON.stringify(JSON.stringify(LISTS))}); });
      localStorage.setItem('marketDataSidebar', ${JSON.stringify(JSON.stringify(anyAnswer()))}); } catch (e) {}
      ${process.env.REAL_TIMES ? '' : 'window.LIVE_MARKET_TEST = { fast: [1500, 2000], slow: 6000, idle: 5000 };'}
      window.__flashes = 0; window.__flashAt = []; new MutationObserver(function (ms) { ms.forEach(function (m) { if (m.target.classList && (m.target.classList.contains('lm-up') || m.target.classList.contains('lm-down'))) { window.__flashes++; window.__flashAt.push(Date.now()); } }); })
        .observe(document, { subtree: true, attributes: true, attributeFilter: ['class'] });` });
    const mouse = async (n) => { for (let i = 0; i < n; i++) { await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 200 + (i % 7) * 30, y: 300 + (i % 5) * 20 }); await sleep(500); } };

    for (const pg of pages) {
      console.log(`\n== ${pg}`);
      calls = 0; frozen = false; priceRequests = []; errors.length = 0;
      await send('Page.navigate', { url: BASE + pg }); await sleep(4500);
      const first = await js(`(function () { var lm = window.liveMarket; return { loaded: !!lm, movers: lm ? lm.movers().length : 0, panel: lm ? lm.panelRows().length : 0,
        texts: lm ? lm.movers().map(function (m) { return m.price.textContent; }).concat(lm.panelRows().map(function (r) { var v = r.row.querySelector('.market-item-sidebar-value'); return v && v.textContent; })) : [] }; })()`);
      const has = await js(`!!(document.getElementById('market-data-sidebar-container') || document.querySelector('[id^="gainer-price-"],[id^="loser-price-"],[id^="active-price-"],[id^="trend-price-"]'))`);
      if (!has) {                                        // a page with no market data (a stock page: its own price has its own refresh)
        await mouse(8);
        check('a page with no market data does not load the script and asks for nothing', !first.loaded && priceRequests.length === 0, { loaded: first.loaded, asked: priceRequests.length });
        if (process.env.REAL_TIMES && /^stocks\//.test(pg)) {   // its price refreshes on its own clock, as update_interval.sh sets it
          const every = Number((fs.readFileSync(WEB && fs.existsSync(path.join(WEB, 'stock-prices.js')) ? path.join(WEB, 'stock-prices.js') : path.join(SITE, 'stock-prices.js'), 'utf8').match(/setInterval\(refreshPrices, (\d+)\)/) || [])[1]);
          const from = stockRequests.length; await mouse(70);
          const req = stockRequests.slice(from), gaps = req.slice(1).map((t, i) => t - req[i]);
          check(`the stock page's price is asked for every ${every / 1000} s (${gaps.length} gaps: ${gaps.map(g => (g / 1000).toFixed(1)).join(', ')} s)`,
            every && gaps.length >= 2 && gaps.every(g => Math.abs(g - every) <= 400), { every, gaps });
        }
        check('no script error on the page', errors.length === 0, errors);
        continue;
      }
      check('live-market.js is loaded on the page and finds its figures', first.loaded && first.movers + first.panel > 0, first);
      if (process.env.REAL_TIMES) {                      // the real gaps, as update_interval.sh sets them
        const src = fs.readFileSync(WEB && fs.existsSync(path.join(WEB, 'live-market.js')) ? path.join(WEB, 'live-market.js') : path.join(SITE, 'live-market.js'), 'utf8');
        const [lo, hi] = (src.match(/T\.fast \|\| \[(\d+), (\d+)\]/) || []).slice(1).map(Number);
        const from = priceRequests.length; await mouse(80);   // 40 seconds of someone using the page
        const req = priceRequests.slice(from), gaps = req.slice(1).map((r, i) => r.at - req[i].at);
        check(`every gap between price requests is inside the set ${lo / 1000}-${hi / 1000} s (${gaps.length} gaps: ${gaps.map(g => (g / 1000).toFixed(1)).join(', ')} s)`,
          lo && gaps.length >= Math.floor(35000 / hi) && gaps.every(g => g >= lo - 150 && g <= hi + 600), { lo, hi, gaps });
        const flashAt = await js('window.__flashAt'), answers = priceRequests.map(r => r.answered).filter(Boolean);
        const lag = flashAt.map(t => t - Math.max.apply(null, answers.filter(a => a <= t + 50).concat([0])));
        check(`each change flashes the moment its answer arrives (${flashAt.length} flashes, slowest ${lag.length ? Math.max.apply(null, lag) : '-'} ms after its answer)`,
          flashAt.length > 0 && lag.every(l => l <= 500), { lag: lag.slice(0, 20) });
        check('no script error on the page', errors.length === 0, errors);
        continue;
      }
      if (await js('!!window.marketPanel')) {             // the shared panel script (market-panel.js): tabs, arrows, lists, countdown
        const names = () => js(`Array.from(document.querySelectorAll('#market-data-sidebar-container .market-item-sidebar-name')).map(e => e.textContent)`);
        const tabNow = () => js(`(document.querySelector('.market-tab-sidebar.active') || {}).getAttribute && document.querySelector('.market-tab-sidebar.active').getAttribute('data-tab')`);
        const click = (sel) => js(`(function () { var e = document.querySelector(${JSON.stringify(sel)}); if (!e) return false; e.click(); return true; })()`);
        const opening = await js(`window.marketPanel.openTab ? window.marketPanel.openTab() : 'us'`);
        check('the panel opens on the tab of the market trading now (' + opening + '), with its figures', (await names()).join() === CATS[opening].map(x => x[0]).join() && await tabNow() === opening, [opening, await tabNow(), await names()]);
        await click('.market-tab-sidebar[data-tab="europe"]'); await sleep(300);
        check('a tab shows its own figures', (await names())[0] === 'europe S&P 500' && await tabNow() === 'europe', [await tabNow(), await names()]);
        const drawn = await js(`(function () { var l = document.querySelectorAll('#market-data-sidebar-container .market-item-sidebar-chart polyline'); return Array.from(l).filter(function (x) { return x.getAttribute('data-lm') && x.getAttribute('points'); }).length; })()`);
        check('a tab chosen later shows its small charts at once (every tab\'s lines were fetched in the background)', drawn === 6, drawn);
        const mismatch = await js(`(function () { return Array.from(document.querySelectorAll('#market-data-sidebar-container .market-item')).filter(function (r) { var l = r.querySelector('polyline[data-lm]'), c = r.querySelector('.market-item-sidebar-change'); if (!l || !c) return false; var down = c.classList.contains('negative') || /^\\s*[-\\u2212]/.test(c.textContent); return (l.getAttribute('stroke') === '#ef4444') !== down; }).map(function (r) { return r.textContent.replace(/\\s+/g, ' ').trim().slice(0, 60); }); })()`);
        if (/function shownUp/.test(fs.readFileSync(WEB && fs.existsSync(path.join(WEB, 'live-market.js')) ? path.join(WEB, 'live-market.js') : path.join(SITE, 'live-market.js'), 'utf8'))) check('every small chart is red or green as the change shown beside it is (a green line under -3.20% was seen, 23 Oct 2026)', Array.isArray(mismatch) && !mismatch.length, mismatch);
        const kept = await js(`Object.keys(JSON.parse(localStorage.getItem('lmSparks') || '{}')).length`);
        check('the lines are kept in the browser, so a reload shows them before any request (the stand-in tabs share their 6 symbols)', kept >= 6, kept);
        await click('#nav-right-sidebar'); await sleep(300);
        check('the arrow moves one tab on, not two', await tabNow() === 'asia' && (await names())[0] === 'asia S&P 500', await tabNow());
        await click('#nav-left-sidebar'); await click('#nav-left-sidebar'); await sleep(300);
        check('and back', await tabNow() === 'us', await tabNow());
        const lists = await js(`['trending', 'gainers', 'losers', 'active'].map(k => (document.getElementById(k + '-tickers-container') || { children: [] }).children.length)`);
        check('the four lists each show their five', lists.join() === '5,5,5,5', lists);
        const rows = await js(`Array.from(document.querySelectorAll('#gainers-tickers-container > *')).map(e => e.tagName + ' ' + (e.getAttribute('href') || ''))`);
        if (pg.indexOf('dashboard') >= 0) check('on the dashboard a list row still runs the analysis in the background (no link)', rows.every(r => r.startsWith('DIV')), rows);
        else check('on the home page a row runs the analysis, it is not a link to a stock page (the owner, 19 Oct 2026)', rows.length === 5 && rows.every(r => /^DIV/.test(r)), rows);
        if (pg === 'index.html') {
          const sec = await js(`(function () { var s = document.getElementById('stock-pages'); return s ? s.querySelectorAll('a[href^="stocks/"]').length : -1; })()`);
          check('the home page has its section of links to the largest companies\' stock pages', sec >= 20, sec);
        }
        check('the countdown says when the US market opens or closes', /U\.S\. markets (open|close) in/.test(await js(`document.getElementById('market-status-sidebar').textContent`)) && /\d+h \d+m/.test(await js(`document.getElementById('market-countdown-sidebar').textContent`)));
        const pos = await js(`(function () { var n = document.getElementById('news-panel'); var c = getComputedStyle(n); return [c.position, c.overflowY, !!document.getElementById('scroll-indicator')]; })()`);
        const daily = /screener/.test(pg);                 // the daily screener pages (24 Oct 2026): in view beside the list, scrolling inside itself, no arrow
        const want = pg.indexOf('dashboard') >= 0 ? 'fixed,auto,true' : daily ? 'fixed,auto,false' : 'absolute,visible,false';
        check(pg.indexOf('dashboard') >= 0 ? 'on the dashboard the panel stays in view and scrolls inside itself, with its arrow' : daily ? 'on a daily screener page the panel stays in view beside the list and scrolls inside itself' : 'on the home page the panel scrolls with the page', pos.join() === want, pos);
      }
      const before = priceRequests.length;
      await mouse(16);                                   // eight seconds of someone using the page
      const after = await js(`(function () { var lm = window.liveMarket; return { st: lm.state(), flashes: window.__flashes,
        texts: lm.movers().map(function (m) { return m.price.textContent; }).concat(lm.panelRows().map(function (r) { var v = r.row.querySelector('.market-item-sidebar-value'); return v && v.textContent; })),
        line: (function () { var r = lm.panelRows()[0]; var l = r && r.row.querySelector('.market-item-sidebar-chart polyline'); return l ? l.getAttribute('points') : null; })(),
        want: (function () { var r = lm.panelRows()[0]; return r ? r.sym : null; })() }; })()`);
      const n = priceRequests.length - before;
      check('while someone uses the page it asks for prices every few seconds, one request a round', n >= 3 && n <= 7, { n, st: after.st });
      const asked = priceRequests.length ? JSON.parse(priceRequests[priceRequests.length - 1].body) : {};
      check('one request covers every figure on show, at most 40, each once', asked.tickers && asked.tickers.length === new Set(asked.tickers).size && asked.tickers.length <= 40 && asked.spark === true, asked);
      const moved = after.texts.filter((t, i) => t !== first.texts[i]).length;
      check('the figures on show change, and changes flash', moved >= Math.min(3, first.texts.length) && after.flashes > 0, { moved, of: first.texts.length, flashes: after.flashes });
      { const flashAt = await js('window.__flashAt'), answers = priceRequests.map(r => r.answered).filter(Boolean);
        const lag = flashAt.map(t => t - Math.max.apply(null, answers.filter(a => a <= t + 50).concat([0])));
        check('each change flashes the moment its answer arrives (until 31 Oct 2026 each row waited up to 2.5 s)', flashAt.length > 0 && lag.every(l => l <= 500), { slowest: Math.max.apply(null, lag) }); }
      if (first.panel) {
        const want = await js(`(function () { var a = ${JSON.stringify(lastData[after.want])}; return window.liveMarket.sparkPoints(a.spark, a.prev); })()`);
        check('the side panel\'s small chart is today\'s line from the answer, not a random one', after.line === want, { line: after.line, want });
      }
      if (pg === 'index.html') {
        const cards = await js(`(function () { var lm = window.liveMarket, d = ${JSON.stringify(lastData)}; return (lm.cards ? lm.cards() : []).map(function (c) { var a = d[c.sym];
          return { sym: c.sym, value: c.value.textContent, line: c.line && c.line.getAttribute('points'), want: a ? lm.sparkPoints(a.spark, a.prev, 58) : 'no answer' }; }); })()`);
        check('the four index cards on the home page show figures and today\'s real line (it was a fixed up or down line)', cards.length === 4 && cards.every(c => /\d/.test(c.value) && c.line === c.want), cards);
      }
      await sleep(9000);                                 // nobody moves: past the (shortened) idle time
      const idleFrom = priceRequests.length; await sleep(6000);
      check('when nobody has moved for a while nothing more is asked for', priceRequests.length - idleFrom === 0, { asked: priceRequests.length - idleFrom });
      frozen = true; await mouse(30);                    // someone is back, but the prices have stopped moving (a market that is closed)
      const st = await js('window.liveMarket.state()');
      check('when the prices stop moving the gap between rounds grows (up to its longest)', st.gap > 2000, st);
      check('no script error on the page', errors.length === 0, errors);
      if (process.env.SHOTS) { const r = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(path.join(process.env.SHOTS, pg.replace(/\W+/g, '_') + '.png'), Buffer.from(r.data, 'base64')); }
      if (process.env.SHOTS && pg === 'index.html') { await js(`(function () { var e = document.getElementById('stock-pages'); if (e) { document.documentElement.style.scrollBehavior = 'auto'; e.scrollIntoView({ block: 'start' }); window.scrollBy(0, -120); } })()`); await sleep(400);
        const r2 = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(path.join(process.env.SHOTS, 'index_stock_pages.png'), Buffer.from(r2.data, 'base64')); }

    }
  } catch (e) { console.log('ERROR ' + e.stack); failed++; }
  finally { chrome.kill(); server.close(); console.log(`\n${failed ? 'SOME FAILED' : 'ALL PASS'} (${passed} passed, ${failed} failed)`); process.exit(failed ? 1 : 0); }
})();
