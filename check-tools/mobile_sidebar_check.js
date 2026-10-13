// The market-data sidebar on a phone, tried with a finger: opens a page of the site in headless Chrome at phone size with
// touch switched on, scrolls down, drags the sidebar in and out, and checks that the sidebar follows the finger and that
// the page behind never moves (it used to jump to the top).
//
//   node check-tools/mobile_sidebar_check.js index.html dashboard.html
//   WEB=<folder> node ...    files found in that folder are served instead of the ones in ../website (a staged copy)
//   SHOT=<file.png> node ... a picture of the last page with the sidebar a quarter out
//
// Nothing is written anywhere and nothing outside this machine is asked: the pages come from a server started here, and
// every other request a page makes (the site's functions, fonts, analytics) is answered here with an empty reply. The
// "visitor" is a made-up address, which is enough for the dashboard to draw itself.
const { spawn } = require('child_process'); const os = require('os'), fs = require('fs'), path = require('path'), http = require('http');
const pages = process.argv.slice(2).length ? process.argv.slice(2) : ['index.html'];
const SITE = path.join(__dirname, '..', '..', 'website'), WEB = process.env.WEB || '', PORT = 9347, HTTP = 8791, START = 1200;
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.txt': 'text/plain' };
const sleep = ms => new Promise(r => setTimeout(r, ms));

const server = http.createServer((q, r) => {
  const name = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
  if (name.includes('..')) { r.writeHead(400); r.end(); return; }
  const staged = WEB && fs.existsSync(path.join(WEB, name)) ? path.join(WEB, name) : path.join(SITE, name);
  fs.readFile(staged, (err, body) => {
    if (err) { r.writeHead(404); r.end(''); return; }
    r.writeHead(200, { 'Content-Type': TYPES[path.extname(name)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); r.end(body);
  });
});

(async () => {
  await new Promise(r => server.listen(HTTP, '127.0.0.1', r));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sidebarcheck-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${dir}`, '--no-first-run', '--window-size=390,844', 'about:blank'], { stdio: 'ignore' });
  let failed = 0;
  try {
    let targets = null;
    for (let i = 0; i < 40 && !targets; i++) { await sleep(250); try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); } catch (e) { /* not up yet */ } }
    const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl); await new Promise(r => { ws.onopen = r; });
    let id = 0; const waiting = {}; const errors = [];
    const send = (method, params = {}) => new Promise(r => { waiting[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && waiting[d.id]) { waiting[d.id](d.result || d.error); delete waiting[d.id]; return; }
      if (d.method === 'Fetch.requestPaused') {
        const q = d.params.request;
        if (q.url.startsWith(`http://127.0.0.1:${HTTP}/`)) { send('Fetch.continueRequest', { requestId: d.params.requestId }); return; }
        const js = /\.js(\?|$)/.test(q.url), css = /\.css(\?|$)|fonts\.googleapis/.test(q.url);
        send('Fetch.fulfillRequest', { requestId: d.params.requestId, responseCode: 200,
          responseHeaders: [{ name: 'Content-Type', value: js ? 'application/javascript' : css ? 'text/css' : 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Access-Control-Allow-Headers', value: '*' }],
          body: Buffer.from(js || css ? '' : '{}').toString('base64') });
      }
      if (d.method === 'Runtime.exceptionThrown') errors.push((d.params.exceptionDetails.exception && d.params.exceptionDetails.exception.description || d.params.exceptionDetails.text || '').split('\n')[0]);
    };
    const js = async (expression) => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : undefined; };
    await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
    await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 });
    await send('Page.addScriptToEvaluateOnNewDocument', { source: `try { localStorage.setItem('userId', 'sidebar-check@example.com'); localStorage.setItem('userEmail', 'sidebar-check@example.com'); } catch (e) {}` });

    const touch = (type, x, y) => send('Input.dispatchTouchEvent', { type, touchPoints: type === 'touchEnd' ? [] : [{ x, y, id: 1 }] });
    // One finger from (x0, y0) to (x1, y1) over about `ms`; `hold` leaves it down, `after` runs with the finger still down.
    const swipe = async (x0, y0, x1, y1, ms, o = {}) => {
      const steps = o.steps || Math.max(4, Math.round(ms / 16));
      if (!o.resume) await touch('touchStart', x0, y0);
      for (let i = 1; i <= steps; i++) { await touch('touchMove', x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps); if (!o.steps) await sleep(16); }
      if (o.pause) await sleep(o.pause);
      if (!o.hold) { await touch('touchEnd'); await sleep(o.rest === undefined ? 450 : o.rest); }
    };
    const look = () => js(`(function () {
      var m = document.getElementById('mobile-sidebar-modal'), o = document.getElementById('mobile-sidebar-overlay'), c = document.getElementById('mobile-sidebar-content');
      var r = m.getBoundingClientRect(), menu = document.getElementById('mobile-menu'), q = document.getElementById('quick-analysis-panel');
      return { y: Math.round(window.scrollY), shown: m.style.display === 'block', left: Math.round(r.left), width: Math.round(r.width), onScreen: m.style.display === 'block' ? Math.max(0, Math.round(window.innerWidth - r.left)) : 0,
        dim: o.style.display === 'block' ? +(+getComputedStyle(o).opacity).toFixed(2) : 0, body: getComputedStyle(document.body).position, panels: c.children.length,
        panelHome: !!q && q.parentElement !== c, menu: !!(menu && menu.classList.contains('open')), script: !!window.mobileSidebar, path: location.pathname, last: window.mobileSidebar && window.mobileSidebar.last && window.mobileSidebar.last(),
        under: [[300, 500], [320, 500], [330, 500], [150, 500]].map(function (xy) { var e = document.elementFromPoint(xy[0], xy[1]), out = []; for (; e && e !== document.body && out.length < 4; e = e.parentElement) out.push(e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.scrollWidth > e.clientWidth + 1 ? '(wider ' + getComputedStyle(e).overflowX + ')' : '')); return xy[0] + ': ' + out.join(' < '); }) };
    })()`);
    const check = (name, ok, detail) => { console.log((ok ? '  PASS ' : '  FAIL ') + name + (ok ? '' : '   ' + JSON.stringify(detail))); if (!ok) failed++; };
    const near = (a, b, by) => Math.abs(a - b) <= by;

    for (const page of pages) {
      console.log(page);
      errors.length = 0;
      await send('Page.navigate', { url: `http://127.0.0.1:${HTTP}/${page}` }); await sleep(3500);
      await js(`document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, ${START}); 1`); await sleep(300);
      let s = await look();
      check('the page is the one asked for, with the sidebar script', s.path.endsWith(page) && s.script, s);
      if (!s.path.endsWith(page)) continue;
      const y0 = s.y, W = Math.min(390 * 0.9, 400), Y = 500;
      check('it is scrolled down before anything is tried (' + y0 + 'px)', y0 > 300, s);
      const still = (what, t) => check(what + ': the page has not moved', t.y === y0 && t.body !== 'fixed', { y: t.y, was: y0, body: t.body });

      // 1. A quarter out with the finger still down, then pushed back in the same touch
      await swipe(300, Y, 300 - W / 4 - 10, Y, 500, { hold: true }); s = await look();
      check('dragged a quarter: about a quarter of the sidebar is on screen (' + s.onScreen + ' of ' + s.width + 'px)', s.shown && near(s.onScreen, W / 4, 14), s);
      check('the page behind is dimmed in step (' + s.dim + ')', near(s.dim, 0.25, 0.08), s);
      still('with a quarter showing', s);
      if (process.env.SHOT && page === pages[pages.length - 1]) { const p = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(process.env.SHOT, Buffer.from(p.data, 'base64')); }
      await swipe(300 - W / 4 - 10, Y, 300, Y, 500, { resume: true, hold: true }); s = await look();
      check('pushed back with the same finger: nothing of it is on screen', s.onScreen <= 2, s);
      await touch('touchEnd'); await sleep(500); s = await look();
      check('let go: it is gone and the panels are back on the page', !s.shown && s.panels === 0 && s.panelHome, s);
      still('after hiding it again', s);

      // 2. A quarter out and let go: it goes back
      await swipe(300, Y, 300 - W / 4 - 10, Y, 500, { pause: 150 }); s = await look();
      check('a quarter out and let go: it slides back', !s.shown, s); still('after that', s);

      // 3. Well over a third and let go: it comes out fully
      await swipe(320, Y, 320 - W * 0.6, Y, 500, { pause: 150 }); s = await look();
      check('60% out and let go: it comes out fully', s.shown && near(s.onScreen, W, 3) && s.dim > 0.95, s); still('with the sidebar out', s);

      // 4. Out: a finger moving up and down on the dark part does not scroll the page
      await swipe(15, 300, 15, 650, 300, { rest: 300 }); await swipe(15, 650, 15, 250, 300, { rest: 300 }); s = await look();
      check('still out after touching the dark part', s.shown, s); still('after a finger moved up and down beside the sidebar', s);

      // 5. Out: pushed a little to the right and let go stays; pushed far goes
      await swipe(150, Y, 150 + W * 0.2, Y, 500, { pause: 150 }); s = await look();
      check('pushed back a fifth and let go: it stays out', s.shown && near(s.onScreen, W, 3), s);
      await swipe(150, Y, 150 + W * 0.55, Y, 500, { pause: 150 }); s = await look();
      check('pushed back more than half: it hides', !s.shown && s.panelHome, s); still('after hiding it by hand', s);

      // 6. A quick short flick is enough
      await swipe(330, Y, 250, Y, 0, { steps: 3, rest: 500 }); s = await look();
      check('a quick short flick to the left brings it out (' + (s.last && -s.last.speed) + ' px a ms)', s.shown && near(s.onScreen, W, 3), s);
      await swipe(150, Y, 230, Y, 0, { steps: 3, rest: 500 }); s = await look();
      check('a quick short flick to the right hides it', !s.shown, s); still('after the two flicks', s);

      // 7. The buttons
      await js(`toggleMobileSidebar(); 1`); await sleep(500); s = await look();
      check('the green button opens it', s.shown && near(s.onScreen, W, 3), s); still('opened by the button', s);
      await js(`closeMobileSidebar(); 1`); await sleep(500); s = await look();
      check('the close button hides it', !s.shown && s.panelHome, s); still('closed by the button', s);

      // 8. Up and down on the page itself still scrolls it, and does not bring the sidebar out
      await swipe(200, 600, 200, 300, 300, { rest: 600 }); s = await look();
      check('a finger moving up the page scrolls it (' + y0 + ' to ' + s.y + ') and no sidebar appears', s.y > y0 + 100 && !s.shown, s);

      // 9. The other direction still opens the menu on the left (the page's own code), not the sidebar
      await swipe(60, Y, 220, Y, 200, { rest: 500 }); s = await look();
      check('a swipe to the right opens the menu, not the sidebar', s.menu && !s.shown, s);
      check('no script error on the page', errors.length === 0, errors.slice(0, 3));
    }
    console.log(failed ? failed + ' check(s) failed' : 'all checks passed');
  } finally { chrome.kill(); server.close(); try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) { /* Chrome may still hold it */ } }
  process.exit(failed ? 1 : 0);
})();
