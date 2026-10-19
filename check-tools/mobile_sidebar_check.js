// The two panels that slide in on a phone, tried with a finger: the market-data sidebar on the right and the menu on the
// left. Opens a page of the site in headless Chrome at phone size with touch switched on, scrolls down, drags each panel
// in and out, and checks that it follows the finger and that the page behind never moves (it used to jump to the top).
//
//   node check-tools/mobile_sidebar_check.js index.html dashboard.html analysis.html blog.html stocks/AAPL.html
//   WEB=<folder> node ...    files found in that folder are served instead of the ones in ../website (a staged copy)
//   SHOT=<file.png> node ... a picture of the last page with its first panel a quarter out
//   LIVE=1 node ...          the pages and their files come from https://stockiq.tech itself (read only: plain GETs of the site's own files)
//
// A page is tried for what it has: the sidebar (home page, dashboard), the menu with a swipe (pages that load
// mobile-sidebar.js), or the menu by its ☰ button only (every other page with a menu: the stylesheet alone keeps the
// page in place there).
//
// Nothing is written anywhere: every request a page makes beyond the site's own files (the site's functions, fonts,
// analytics) is answered here with an empty reply. The "visitor" is a made-up address, which is enough for the
// dashboard to draw itself.
const { spawn } = require('child_process'); const os = require('os'), fs = require('fs'), path = require('path'), http = require('http');
const pages = process.argv.slice(2).length ? process.argv.slice(2) : ['index.html'];
const SITE = path.join(__dirname, '..', '..', 'website'), WEB = process.env.WEB || '', PORT = 9347, HTTP = 8791, START = 1200;
const BASE = process.env.LIVE ? 'https://stockiq.tech/' : `http://127.0.0.1:${HTTP}/`;
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
  let failed = 0, passed = 0;
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
        if (q.url.startsWith(BASE) && q.method === 'GET') { send('Fetch.continueRequest', { requestId: d.params.requestId }); return; }
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

    const touch = (type, x, y, at) => send('Input.dispatchTouchEvent', Object.assign({ type, touchPoints: type === 'touchEnd' ? [] : [{ x, y, id: 1 }] }, at ? { timestamp: at } : {}));
    // One finger from (x0, y0) to (x1, y1) over about `ms`; `hold` leaves it down, `resume` carries on with a finger that is down.
    const swipe = async (x0, y0, x1, y1, ms, o = {}) => {
      const steps = o.steps || Math.max(4, Math.round(ms / 16));
      // A flick (o.steps) is sent with a clock of its own, 12ms a step: a busy page must not turn it into a slow drag.
      const t0 = Date.now() / 1000, at = (i) => (o.steps ? t0 + i * 0.012 : undefined);
      if (!o.resume) await touch('touchStart', x0, y0, at(0));
      for (let i = 1; i <= steps; i++) { await touch('touchMove', x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps, at(i)); if (!o.steps) await sleep(16); }
      if (o.pause) await sleep(o.pause);
      if (!o.hold) { await touch('touchEnd', 0, 0, at(steps + 1)); await sleep(o.rest === undefined ? 450 : o.rest); }
    };
    const look = () => js(`(function () {
      var m = document.getElementById('mobile-sidebar-modal'), o = document.getElementById('mobile-sidebar-overlay'), c = document.getElementById('mobile-sidebar-content');
      var menu = document.getElementById('mobile-menu'), mo = document.getElementById('mobile-menu-overlay'), q = document.getElementById('quick-analysis-panel');
      var r = m ? m.getBoundingClientRect() : { left: 0, width: 0 }, mr = menu ? menu.getBoundingClientRect() : { right: 0, width: 0 }, shown = !!m && m.style.display === 'block';
      return { y: Math.round(window.scrollY), body: getComputedStyle(document.body).position, script: !!window.mobileSidebar && (window.mobileSidebar.version || 1), path: location.pathname,
        last: window.mobileSidebar && window.mobileSidebar.last && window.mobileSidebar.last(),
        hasSidebar: !!m, shown: shown, width: Math.round(r.width), onScreen: shown ? Math.max(0, Math.round(window.innerWidth - r.left)) : 0,
        dim: o && o.style.display === 'block' ? +(+getComputedStyle(o).opacity).toFixed(2) : 0, panels: c ? c.children.length : 0, panelHome: !q || !c || q.parentElement !== c,
        hasMenu: !!menu, menu: !!(menu && menu.classList.contains('open')), menuWidth: Math.round(mr.width), menuOnScreen: Math.max(0, Math.round(mr.right)),
        menuDim: mo && getComputedStyle(mo).visibility === 'visible' ? +(+getComputedStyle(mo).opacity).toFixed(2) : 0, menuInline: menu ? (menu.style.left || '') + (menu.style.transition || '') : '',
        locked: document.body.classList.contains('menu-open'), height: document.documentElement.scrollHeight, room: document.documentElement.scrollHeight - window.innerHeight };
    })()`);
    const check = (name, ok, detail) => { console.log((ok ? '  PASS ' : '  FAIL ') + name + (ok ? '' : '   ' + JSON.stringify(detail))); if (ok) passed++; else failed++; };
    const near = (a, b, by) => Math.abs(a - b) <= by;
    const shot = async () => { const p = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(process.env.SHOT, Buffer.from(p.data, 'base64')); };

    for (const page of pages) {
      console.log(BASE + page);
      errors.length = 0;
      await send('Page.navigate', { url: BASE + page }); await sleep(process.env.LIVE ? 6000 : 3500);
      await js(`document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, Math.min(${START}, Math.floor((document.documentElement.scrollHeight - window.innerHeight) / 2))); 1`); await sleep(300);
      let s = await look(), y0 = s.y, pictured = false;
      const last = page === pages[pages.length - 1], Y = 500;
      check('the page is the one asked for', s.path.endsWith(page), s);
      if (!s.path.endsWith(page)) continue;
      check('it is scrolled down before anything is tried (' + y0 + 'px)', y0 > 60, s);       // a short page (sign in) goes half way down
      const still = (what, t) => check(what + ': the page has not moved', t.y === y0 && t.body !== 'fixed', { y: t.y, was: y0, body: t.body });

      // ------------------------------------------------ the sidebar on the right (pages that have one)
      if (s.hasSidebar) {
        const W = Math.min(390 * 0.9, 400);
        check('the sidebar script is on the page', !!s.script, s);
        // 1. A quarter out with the finger still down, then pushed back in the same touch
        await swipe(300, Y, 300 - W / 4 - 10, Y, 500, { hold: true }); s = await look();
        check('sidebar dragged a quarter: about a quarter of it is on screen (' + s.onScreen + ' of ' + s.width + 'px)', s.shown && near(s.onScreen, W / 4, 14), s);
        check('the page behind is dimmed in step (' + s.dim + ')', near(s.dim, 0.25, 0.08), s);
        still('with a quarter of the sidebar showing', s);
        if (process.env.SHOT && last) { await shot(); pictured = true; }
        await swipe(300 - W / 4 - 10, Y, 300, Y, 500, { resume: true, hold: true }); s = await look();
        check('pushed back with the same finger: nothing of it is on screen', s.onScreen <= 2, s);
        await touch('touchEnd'); await sleep(500); s = await look();
        check('let go: it is gone and the panels are back on the page', !s.shown && s.panels === 0 && s.panelHome, s);
        still('after hiding the sidebar again', s);
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
        check('pushing the sidebar back did not pull the menu out', !s.menu && s.menuOnScreen <= 0, s);
        // 6. A quick short flick is enough
        await swipe(330, Y, 250, Y, 0, { steps: 3, rest: 500 }); s = await look();
        check('a quick short flick to the left brings it out (' + (s.last && -s.last.speed) + ' px a ms)', s.shown && near(s.onScreen, W, 3), s);
        await swipe(150, Y, 230, Y, 0, { steps: 3, rest: 500 }); s = await look();
        check('a quick short flick to the right hides it', !s.shown && !s.menu, s); still('after the two flicks', s);
        // 7. The buttons. The green button is tapped where it sits on screen (19 Oct 2026: on the dashboard it sat under the
        // AI chat button, which a call to toggleMobileSidebar() in code could never notice)
        const btn = JSON.parse(await js(`(() => { const b = document.getElementById('mobile-sidebar-toggle'); if (!b) return JSON.stringify(null); const r = b.getBoundingClientRect(); const x = r.left + r.width / 2, y = r.top + r.height / 2, top = document.elementFromPoint(x, y); return JSON.stringify({ x, y, mine: !!top && (top === b || b.contains(top)), over: top ? (top.id || top.tagName) : null }); })()`));
        check('the green button is not covered by anything (what is on top at its middle: ' + (btn && btn.over) + ')', btn && btn.mine, btn);
        if (btn && btn.mine) { await touch('touchStart', btn.x, btn.y); await touch('touchEnd', btn.x, btn.y); await sleep(600); }
        else { await js(`toggleMobileSidebar(); 1`); await sleep(500); }
        s = await look();
        check('the green button opens it', s.shown && near(s.onScreen, W, 3), s); still('opened by the button', s);
        await js(`closeMobileSidebar(); 1`); await sleep(500); s = await look();
        check('the close button hides it', !s.shown && s.panelHome, s); still('closed by the button', s);
      }

      // ------------------------------------------------ the menu on the left
      if (s.hasMenu && s.script) {
        const M = s.menuWidth;
        // 1. A quarter out with the finger still down, then pushed back in the same touch
        await swipe(60, Y, 60 + M / 4 + 10, Y, 500, { hold: true }); s = await look();
        check('menu dragged a quarter: about a quarter of it is on screen (' + s.menuOnScreen + ' of ' + M + 'px)', near(s.menuOnScreen, M / 4, 14) && !s.shown, s);
        check('the page behind is dimmed in step (' + s.menuDim + ')', near(s.menuDim, 0.25, 0.08), s);
        still('with a quarter of the menu showing', s);
        if (process.env.SHOT && last && !pictured) await shot();
        await swipe(60 + M / 4 + 10, Y, 60, Y, 500, { resume: true, hold: true }); s = await look();
        check('pushed back with the same finger: nothing of it is on screen', s.menuOnScreen <= 2, s);
        await touch('touchEnd'); await sleep(500); s = await look();
        check('let go: the menu is shut and nothing of the drag is left on it', !s.menu && !s.locked && s.menuInline === '' && s.menuOnScreen <= 0 && s.menuDim === 0, s);
        still('after shutting the menu again', s);
        // 2. A quarter out and let go: it goes back
        await swipe(60, Y, 60 + M / 4 + 10, Y, 500, { pause: 150 }); s = await look();
        check('a quarter out and let go: it slides back', !s.menu && s.menuOnScreen <= 0, s); still('after that', s);
        // 3. Well over a third and let go: it comes out fully
        await swipe(40, Y, 40 + M * 0.6, Y, 500, { pause: 150 }); s = await look();
        check('60% out and let go: it comes out fully', s.menu && s.locked && near(s.menuOnScreen, M, 3) && s.menuDim > 0.95 && s.menuInline === '', s); still('with the menu out', s);
        // 4. Out: a finger moving up and down on the dark part does not scroll the page
        await swipe(370, 300, 370, 650, 300, { rest: 300 }); await swipe(370, 650, 370, 250, 300, { rest: 300 }); s = await look();
        still('after a finger moved up and down beside the menu', s);
        if (!s.menu) { await js(`toggleMobileMenu(); 1`); await sleep(450); }        // some pages shut the menu when the dark part is touched
        // 5. Out: pushed a little to the left and let go stays; pushed far goes
        await swipe(250, Y, 250 - M * 0.2, Y, 500, { pause: 150 }); s = await look();
        check('pushed back a fifth and let go: it stays out', s.menu && near(s.menuOnScreen, M, 3), s);
        await swipe(250, Y, 250 - M * 0.55, Y, 500, { pause: 150 }); s = await look();
        check('pushed back more than half: it shuts', !s.menu && !s.locked && s.menuOnScreen <= 0, s); still('after shutting it by hand', s);
        check('pushing the menu back did not pull the sidebar out', !s.shown, s);
        // 6. A quick short flick is enough
        await swipe(60, Y, 140, Y, 0, { steps: 3, rest: 500 }); s = await look();
        check('a quick short flick to the right brings it out (' + (s.last && s.last.speed) + ' px a ms)', s.menu && near(s.menuOnScreen, M, 3), s);
        await swipe(250, Y, 170, Y, 0, { steps: 3, rest: 500 }); s = await look();
        check('a quick short flick to the left shuts it', !s.menu && !s.shown, s); still('after the two flicks', s);
      }
      if (s.hasMenu) {
        // The ☰ button (every page with a menu, with or without the script)
        await js(`toggleMobileMenu(); 1`); await sleep(500); s = await look();
        check('the ☰ button opens the menu', s.menu && s.menuOnScreen > 200, s); still('opened by the ☰ button', s);
        check('the page behind keeps its length while the menu is open (' + s.height + 'px)', s.room >= y0 * 2 - 2, s);
        await js(`closeMobileMenu(); 1`); await sleep(500); s = await look();
        check('its close button shuts it', !s.menu && !s.locked, s); still('shut by the button', s);
      }

      // ------------------------------------------------ an ordinary scroll still works and brings nothing out
      await swipe(200, 600, 200, 300, 300, { rest: 600 }); s = await look();
      check('a finger moving up the page scrolls it (' + y0 + ' to ' + s.y + ') and no panel appears', s.y > y0 + Math.min(100, (s.room - y0) / 2) && !s.shown && !s.menu, s);
      check('no script error on the page', errors.length === 0, errors.slice(0, 3));
    }
    console.log(failed ? failed + ' check(s) failed, ' + passed + ' passed' : 'all ' + passed + ' checks passed');
  } finally { chrome.kill(); server.close(); try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) { /* Chrome may still hold it */ } }
  process.exit(failed ? 1 : 0);
})();
