// Does a page start the same distance under the header whether the strip across the top is showing or not? Opens each
// page of the site as three kinds of visitor (anonymous, signed in without a plan, signed in with the "paid" note), at
// desktop and phone size, and measures at the top of the page: where the strip and the menu bar sit, and how far under
// the header the page's first heading starts. A page fails when the bar is not flush (a gap above it, or more than the
// usual 4px of the strip under it) or when its content starts at a different distance for one kind of visitor than for another.
//
//   node check-tools/header_room_check.js                      every page with the header, and one stock page
//   node check-tools/header_room_check.js dashboard.html       those pages only
//   WEB=<folder> node ...     files found in that folder are served instead of the ones in ../website (a staged copy)
//   SHOTS=<folder> node ...   a picture of the top of each page for each visitor
//
// Nothing is written anywhere: the pages are served from this machine and every request beyond the site's own files is
// answered here (a signed-in visitor is a made-up address with a made-up session, as in visitor_bar_check.js).
const { spawn } = require('child_process'); const os = require('os'), fs = require('fs'), path = require('path'), http = require('http');
const SITE = path.join(__dirname, '..', '..', 'website'), WEB = process.env.WEB || '', PORT = 9353, HTTP = 8795, BASE = `http://127.0.0.1:${HTTP}/`;
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.txt': 'text/plain' };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const WHO = 'room-check@example.com', trial = { success: true, isTrialActive: true, dailyLimit: 5, daysRemaining: 2, hoursRemaining: 52 }, sub = { success: true, isTrialActive: true, dailyLimit: 15, daysRemaining: 20, hoursRemaining: 483 };
const VISITORS = { anonymous: {}, 'no plan': { in: true, paid: 'unpaid', status: trial }, paid: { in: true, paid: 'paid', status: sub } };
const SIZES = [['desktop', 1440, 900, false], ['phone', 390, 844, true]];
const all = fs.readdirSync(SITE).filter(f => f.endsWith('.html') && /class="top-nav"/.test(fs.readFileSync(path.join(SITE, f), 'utf8'))).sort().concat(['stocks/AAPL.html']);
const PAGES = process.argv.slice(2).length ? process.argv.slice(2) : all;
const jwt = (o) => 'x.' + Buffer.from(JSON.stringify(o)).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '') + '.y';
const server = http.createServer((q, r) => {
  const name = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
  if (name.includes('..')) { r.writeHead(400); r.end(); return; }
  const file = WEB && fs.existsSync(path.join(WEB, name)) ? path.join(WEB, name) : path.join(SITE, name);
  fs.readFile(file, (err, body) => { if (err) { r.writeHead(404); r.end(''); return; } r.writeHead(200, { 'Content-Type': TYPES[path.extname(name)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); r.end(body); });
});
const MENU_AT = {};
(async () => {
  await new Promise(r => server.listen(HTTP, '127.0.0.1', r));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'roomcheck-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${dir}`, '--no-first-run', '--window-size=1440,900', 'about:blank'], { stdio: 'ignore' });
  let failed = 0, now = {};
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
      const reply = b.action === 'check_trial_status' ? (now.status || {}) : (b.action === 'get_usage' || b.action === 'increment_usage') ? { usage: 0, success: true } : {};
      const js = /\.js(\?|$)/.test(q.url), css = /\.css(\?|$)|fonts\.googleapis/.test(q.url);
      send('Fetch.fulfillRequest', { requestId: d.params.requestId, responseCode: 200,
        responseHeaders: [{ name: 'Content-Type', value: js ? 'application/javascript' : css ? 'text/css' : 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Access-Control-Allow-Headers', value: '*' }],
        body: Buffer.from(js || css ? '' : JSON.stringify(reply)).toString('base64') });
    };
    const js = async (expression) => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : undefined; };
    await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
    // the menu must not move while the page loads (24 Oct 2026: the bell, shown late by the page's code, shifted the centred menu 31px)
    await send('Page.addScriptToEvaluateOnNewDocument', { source: "window.__navx=[];(function rec(){var d=document.querySelector('.desktop-nav > .nav-item');if(d){var x=Math.round(d.getBoundingClientRect().left);if(window.__navx[window.__navx.length-1]!==x)window.__navx.push(x);}if(performance.now()<3000)requestAnimationFrame(rec);})();" });
    const look = () => js(`(function () { var process_env_dump = ${process.env.DUMP ? 1 : 0};
      var shown = function (e) { if (!e) return null; var c = getComputedStyle(e), r = e.getBoundingClientRect(); return c.display !== 'none' && c.visibility !== 'hidden' && r.height > 0 && r.bottom > 0 ? r : null; };
      var strip = shown(document.getElementById('promo-banner')) || shown(document.getElementById('sticky-banner')) || shown(document.getElementById('site-strip')), nav = shown(document.querySelector('.top-nav'));
      var header = Math.max(strip ? strip.bottom : 0, nav ? nav.bottom : 0), first = null, hs = document.querySelectorAll('h1, h2');
      for (var i = 0; i < hs.length && !first; i++) { var r = shown(hs[i]); if (r && !hs[i].closest('.top-nav, #mobile-menu, #mobile-sidebar-modal, .modal, [role=dialog]') && getComputedStyle(hs[i]).position !== 'fixed') first = { top: r.top, text: hs[i].textContent.trim().slice(0, 28) }; }
      return { at: location.pathname, y: Math.round(scrollY), strip: strip ? Math.round(strip.bottom) : 0, navTop: nav ? Math.round(nav.top) : null, navBottom: nav ? Math.round(nav.bottom) : null, header: Math.round(header),
        pad: Math.round(parseFloat(getComputedStyle(document.body).paddingTop) || 0), first: first ? Math.round(first.top) : null, text: first ? first.text : '', navx: window.__navx || [], items: process_env_dump ? Array.prototype.map.call(document.querySelectorAll('.desktop-nav > *, .nav-container > *'), function (e) { var r = e.getBoundingClientRect(); return (e.className || e.tagName).toString().slice(0, 28) + ':' + Math.round(r.left) + '+' + Math.round(r.width) + ':' + getComputedStyle(e).display; }).join(' | ') + ' || nav ' + JSON.stringify((function(n){var r=n.getBoundingClientRect(),c=getComputedStyle(n);return [Math.round(r.left),Math.round(r.width),c.position,c.left,c.transform,document.documentElement.clientWidth];})(document.querySelector('.desktop-nav'))) : '' };
    })()`);
    for (const page of PAGES) {
      for (const [size, w, h, mobile] of SIZES) {
        const rows = [];
        for (const who of Object.keys(VISITORS)) {
          const v = now = VISITORS[who];
          await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: mobile ? 2 : 1, mobile });
          await send('Emulation.setUserAgentOverride', { userAgent: mobile ? 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' });
          await send('Page.navigate', { url: BASE + 'robots.txt' }); await sleep(200);
          const store = v.in ? { userId: WHO, userEmail: WHO, idToken: jwt({ email: WHO, exp: Math.floor(Date.now() / 1000) + 3600, 'custom:tier': 'free' }), accessToken: 'x', loginTime: String(Date.now()), ['userPaidStatus_' + WHO]: v.paid } : {};
          await js(`localStorage.clear(); sessionStorage.clear(); const s = ${JSON.stringify(store)}; Object.keys(s).forEach(k => localStorage.setItem(k, s[k])); 1`);
          await send('Page.navigate', { url: BASE + page }); await sleep(2600);
          const s = await look() || {};
          if (process.env.SHOTS) { fs.mkdirSync(process.env.SHOTS, { recursive: true }); const p = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: w, height: Math.min(h, 420), scale: 1 } }); fs.writeFileSync(path.join(process.env.SHOTS, `${page.replace(/[\/.]/g, '_')}_${size}_${who.replace(' ', '')}.png`), Buffer.from(p.data, 'base64')); }
          rows.push(Object.assign({ who, moved: !String(s.at || '').endsWith(page.split('/').pop()) }, s));
        }
        const there = rows.filter(r => !r.moved && r.navBottom !== null), why = [];
        // the bar has always covered the strip's last 4px (the strip is 45px tall, the bar starts at 41): noted, not a fault
        there.forEach(r => { const flush = r.navTop - r.strip; if (flush > 1 || flush < -5) why.push(`${r.who}: the menu bar is ${flush > 0 ? flush + 'px below ' + (r.strip ? 'the strip' : 'the top of the window') : (-flush) + 'px under the strip'}`); });
        there.forEach(r => { if (r.first !== null && r.first < r.header - 1) why.push(`${r.who}: "${r.text}" starts ${r.header - r.first}px under the header`); });
        if (size === 'desktop') there.forEach(r => { if (r.navx && r.navx.length) (MENU_AT[r.who] = MENU_AT[r.who] || []).push([page, r.navx[r.navx.length - 1]]); });
        if (size === 'desktop') there.forEach(r => { if (r.navx && r.navx.length > 1) why.push(`${r.who}: the menu moved while the page loaded (its first item at ${r.navx.join(' then ')}px)`); });
        const rooms = there.filter(r => r.first !== null).map(r => r.first - r.header);
        if (rooms.length > 1 && Math.max(...rooms) - Math.min(...rooms) > 3) why.push('the first heading starts ' + there.filter(r => r.first !== null).map(r => `${r.first - r.header}px under the header for ${r.who}`).join(', '));
        if (why.length) failed++;
        console.log(`${why.length ? 'FAIL' : 'PASS'} ${page} · ${size}: ` + rows.map(r => r.moved ? `${r.who} → ${String(r.at).split('/').pop()}` : `${r.who} strip ${r.strip} bar ${r.navTop}-${r.navBottom} room ${r.first === null ? '?' : r.first - r.header}`).join(' | ') + (process.env.DUMP ? '\n   ' + rows.map(r => r.items).join('\n   ') : '') + (why.length ? '\n       ' + why.join('\n       ') : ''));
      }
    }
  } catch (e) { failed++; console.log('ERROR', e.message); }
  chrome.kill(); server.close(); try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) { /* in use */ }
  // the menu stands in the same place on every page, so switching pages does not move it (25 Oct 2026, the owner: sign-up and log in differed)
  for (const [who, list] of Object.entries(MENU_AT)) {
    const xs = list.map(l => l[1]), common = xs.slice().sort((a, b) => xs.filter(v => v === b).length - xs.filter(v => v === a).length)[0];
    const odd = list.filter(l => Math.abs(l[1] - common) > 1);
    if (odd.length) { failed++; console.log(`FAIL the menu is not where it is on the other pages (${who}, desktop, first item at ${common}px): ` + odd.map(l => `${l[0]} ${l[1]}px`).join(', ')); }
  }
  console.log(failed ? `\n${failed} page views FAIL` : '\nALL PASS'); process.exit(failed ? 1 : 0);
})();
