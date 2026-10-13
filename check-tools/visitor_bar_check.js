// The usage chip in the header bar (visitor-bar.js), tried as every kind of visitor: opens pages of the site in headless
// Chrome as an anonymous visitor, one on the free trial, one whose trial is over, a paying one with a daily count and
// one with no limit, at desktop and phone widths, and checks that the chip is in the bar, says the right thing, covers
// nothing, that the old floating badge is gone, and that a click opens the sentence with the right thing to do next.
//
//   node check-tools/visitor_bar_check.js                      every kind of visitor on the usual pages
//   node check-tools/visitor_bar_check.js index.html stocks/AAPL.html
//   WEB=<folder> node ...    files found in that folder are served instead of the ones in ../website (a staged copy)
//   SHOTS=<folder> node ...  a picture of every page tried, with the chip's sentence open
//   ONLY=trial3,anon0 node ...   only those visitors (names below)
//
// Nothing is written anywhere and nothing outside this machine is asked: the pages come from a server started here.
// A "signed-in" visitor is a made-up address with a made-up session; what the site's functions would answer about
// trials and counts is answered here, per kind of visitor, and every other request gets an empty reply. The pages' own
// code (auth.js and its copies) then works the count out as it does for a real visitor, and the chip shows it.
const { spawn } = require('child_process'); const os = require('os'), fs = require('fs'), path = require('path'), http = require('http');
const SITE = path.join(__dirname, '..', '..', 'website'), WEB = process.env.WEB || '', PORT = 9353, HTTP = 8793, BASE = `http://127.0.0.1:${HTTP}/`;
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.txt': 'text/plain' };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const WHO_AT = 'visitor-check@example.com';
const sub = { success: true, isTrialActive: true, daysRemaining: 20, hoursRemaining: 483 }, trial = { success: true, isTrialActive: true, dailyLimit: 5, daysRemaining: 2, hoursRemaining: 52 };
// name: who (signed in or not, the plan in the session, the cached "paid" note), what the functions answer, what the chip must say, the action in its card
const VISITORS = {
  anon1:     { pill: null, used: 0, chip: /^1 free( today)?$/, bad: false, says: /1 of 1 free analysis left today/, act: /signup\.html$/ },
  anon0:     { pill: [/Start 3-Day Free Trial/, /signup\.html$/], used: 1, chip: /^0 free( today)?$/, bad: true, says: /Today’s free analysis is used/, act: /signup\.html$/ },
  trial3:    { pill: null, in: true, paid: 'unpaid', status: trial, used: 2, chip: /^3\/5( today)?$/, bad: false, says: /3 of 5 analyses left today.*Free trial: 2d 4h left/, act: /dashboard\.html\?redirect=upgrade#upgrade$/ },
  trial0:    { pill: [/Upgrade Plan/, /dashboard\.html\?redirect=upgrade$/], in: true, paid: 'unpaid', status: trial, used: 5, chip: /^0\/5( today)?$/, bad: true, says: /0 of 5 analyses left today/, act: /dashboard\.html\?redirect=upgrade#upgrade$/ },
  expired:   { pill: [/Upgrade Plan/, /dashboard\.html\?redirect=upgrade$/], in: true, paid: 'unpaid', status: { success: true, isTrialActive: false }, used: 0, chip: /^(Trial ended|Expired)$/, bad: true, says: /Your free trial has ended/, act: /dashboard\.html\?redirect=upgrade#upgrade$/ },
  paid12:    { pill: null, in: true, paid: 'paid', status: Object.assign({ dailyLimit: 15 }, sub), used: 3, chip: /^12\/15( today)?$/, bad: false, says: /12 of 15 analyses left today.*Subscription: 20d 3h left/, act: null },
  unlimited: { pill: null, in: true, paid: 'paid', status: Object.assign({ dailyLimit: 999999 }, sub), used: 40, chip: /^(Unlimited|∞)$/, bad: false, says: /Unlimited analyses/, act: null }
};
const args = process.argv.slice(2), PAGES = args.length ? args : ['index.html', 'analysis.html', 'dashboard.html', 'stocks/AAPL.html', 'blog.html'];
const SIZES = [['desktop', 1500, 900, false], ['narrow', 1024, 800, false], ['phone', 390, 844, true], ['small phone', 320, 640, true]];
const ONLY = (process.env.ONLY || '').split(',').filter(Boolean);
const jwt = (o) => 'x.' + Buffer.from(JSON.stringify(o)).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '') + '.y';

const server = http.createServer((q, r) => {
  const name = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
  if (name.includes('..')) { r.writeHead(400); r.end(); return; }
  const file = WEB && fs.existsSync(path.join(WEB, name)) ? path.join(WEB, name) : path.join(SITE, name);
  fs.readFile(file, (err, body) => { if (err) { r.writeHead(404); r.end(''); return; } r.writeHead(200, { 'Content-Type': TYPES[path.extname(name)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); r.end(body); });
});

(async () => {
  await new Promise(r => server.listen(HTTP, '127.0.0.1', r));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'visitorbar-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${dir}`, '--no-first-run', '--window-size=1500,900', 'about:blank'], { stdio: 'ignore' });
  let failed = 0, passed = 0, now = null;
  try {
    let targets = null;
    for (let i = 0; i < 40 && !targets; i++) { await sleep(250); try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); } catch (e) { /* not up yet */ } }
    const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl); await new Promise(r => { ws.onopen = r; });
    let id = 0; const waiting = {}; const errors = [];
    const send = (method, params = {}) => new Promise(r => { waiting[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
    const answer = (q) => {                                   // what the site's functions would say to this kind of visitor
      let b = {}; try { b = JSON.parse(q.postData || '{}'); } catch (e) { /* not JSON */ }
      if (b.action === 'check_trial_status') return now.status || {};
      if (b.action === 'get_usage' || b.action === 'increment_usage') return { usage: now.used, success: true };
      return {};
    };
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && waiting[d.id]) { waiting[d.id](d.result || d.error); delete waiting[d.id]; return; }
      if (d.method === 'Fetch.requestPaused') {
        const q = d.params.request;
        if (q.url.startsWith(BASE) && q.method === 'GET') { send('Fetch.continueRequest', { requestId: d.params.requestId }); return; }
        const js = /\.js(\?|$)/.test(q.url), css = /\.css(\?|$)|fonts\.googleapis/.test(q.url);
        send('Fetch.fulfillRequest', { requestId: d.params.requestId, responseCode: 200,
          responseHeaders: [{ name: 'Content-Type', value: js ? 'application/javascript' : css ? 'text/css' : 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Access-Control-Allow-Headers', value: '*' }],
          body: Buffer.from(js || css ? '' : JSON.stringify(q.method === 'POST' ? answer(q) : {})).toString('base64') });
      }
      if (d.method === 'Runtime.exceptionThrown') errors.push((d.params.exceptionDetails.exception && d.params.exceptionDetails.exception.description || d.params.exceptionDetails.text || '').split('\n')[0]);
    };
    const js = async (expression) => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); return r.result ? r.result.value : undefined; };
    await send('Page.enable'); await send('Runtime.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
    const check = (name, ok, detail) => { if (ok) passed++; else { failed++; console.log('  FAIL ' + name + '   ' + JSON.stringify(detail).slice(0, 700)); } };

    const look = () => js(`(function () {
      const box = (e) => { if (!e) return null; const r = e.getBoundingClientRect(), c = getComputedStyle(e); return c.display === 'none' || c.visibility === 'hidden' || r.width === 0 ? null : { l: Math.round(r.left), t: Math.round(r.top), r: Math.round(r.right), b: Math.round(r.bottom) }; };
      const one = (q) => box(document.querySelector(q));
      const chip = document.getElementById('vb-chip'), card = document.getElementById('vb-card'), act = card && card.querySelector('a.vb-act'), old = document.getElementById('trial-status-display');
      return { at: location.pathname, w: window.innerWidth, script: !!window.visitorBar, state: window.visitorBar && window.visitorBar.state(), chip: one('#vb-chip'), text: chip ? chip.textContent : null, cls: chip ? chip.className : null,
        nav: one('.top-nav'), brand: one('.nav-brand'), menu: one('.top-nav .desktop-nav'), burger: one('.hamburger-btn'), bell: one('#mobile-notification-bell'),
        old: old ? { shown: !!box(old), text: old.textContent.replace(/\\s+/g, ' ').trim().slice(0, 70) } : null, yellow: !!document.getElementById('limited-time-banner'),
        oldButtons: document.querySelectorAll('#sticky-register-btn, #sticky-upgrade-btn').length, pill: one('#vb-pill'), pillText: (document.getElementById('vb-pill') || {}).textContent || null, pillHref: (document.getElementById('vb-pill') || {}).href || null, h: window.innerHeight,
        card: one('#vb-card'), says: card ? card.textContent.replace(/\\s+/g, ' ').trim() : null, act: act ? act.href : null, strip: one('#promo-banner') || one('#sticky-banner') };
    })()`);
    const apart = (a, b) => !a || !b || a.r <= b.l || b.r <= a.l || a.b <= b.t || b.b <= a.t;

    for (const [who, v] of Object.entries(VISITORS)) {
      if (ONLY.length && !ONLY.includes(who)) continue;
      now = v;
      for (const page of PAGES) {
        if (!v.in && /dashboard/.test(page)) continue;                                  // the dashboard sends an anonymous visitor to Sign In
        for (const [size, w, h, mobile] of SIZES) {
          const label = `${who} · ${page} · ${size} (${w}px)`;
          errors.length = 0;
          await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: mobile ? 2 : 1, mobile });
          await send('Emulation.setTouchEmulationEnabled', { enabled: mobile });
          // an ordinary browser's name: the site takes headless Chrome for a crawler and skips its sign-in check
          await send('Emulation.setUserAgentOverride', { userAgent: mobile ? 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' });
          await send('Page.navigate', { url: BASE + 'robots.txt' }); await sleep(250);
          const store = v.in ? { userId: WHO_AT, userEmail: WHO_AT, idToken: jwt({ email: WHO_AT, exp: Math.floor(Date.now() / 1000) + 3600, 'custom:tier': 'free' }), accessToken: 'x', loginTime: String(Date.now()), ['userPaidStatus_' + WHO_AT]: v.paid } : {};
          await js(`localStorage.clear(); sessionStorage.clear(); const s = ${JSON.stringify(store)}; Object.keys(s).forEach(k => localStorage.setItem(k, s[k])); 1`);
          await send('Page.navigate', { url: BASE + page });
          let s = null;
          for (let i = 0; i < 24; i++) { await sleep(500); s = await look(); if (s && s.chip && v.chip.test(s.text || '')) break; }
          await sleep(700); s = await look();
          if (!s || !s.at.endsWith(page)) { check(label + ': the page opened', false, s && s.at); continue; }
          check(label + ': the chip is there and says the right thing', !!s.chip && v.chip.test(s.text || ''), { text: s.text, old: s.old, script: s.script });
          if (!s.chip) continue;
          check(label + ': it is marked as a warning only when it should be', /vb-bad/.test(s.cls) === v.bad, s.cls);
          const inBar = s.nav && s.chip.t >= s.nav.t && s.chip.b <= s.nav.b, under = /vb-under/.test(s.cls);
          check(label + ': it sits inside the header bar', inBar, { chip: s.chip, nav: s.nav, cls: s.cls, fitted: s.state && s.state.fitted, menu: s.menu, brand: s.brand, burger: s.burger, bell: s.bell });
          check(label + ': it is on the screen', s.chip.l >= 0 && s.chip.r <= s.w, s.chip);
          check(label + ': it covers nothing in the bar (name, menu, menu button, bell)', apart(s.chip, s.brand) && apart(s.chip, s.menu) && apart(s.chip, s.burger) && apart(s.chip, s.bell), { chip: s.chip, brand: s.brand, menu: s.menu, burger: s.burger, bell: s.bell });
          check(label + ': the old floating badge is not shown', !s.old || !s.old.shown, s.old);
          if (/index/.test(page)) check(label + ': the yellow LIMITED TIME bar is gone', !s.yellow, s.yellow);
          const pillPage = /index|analysis/.test(page), wantPill = pillPage ? v.pill : null;
          check(label + ': the round button is ' + (wantPill ? 'there, bottom left, and goes to the right place' : 'not shown'), wantPill ? !!s.pill && wantPill[0].test(s.pillText || '') && wantPill[1].test(s.pillHref || '') && s.pill.l <= 24 && s.pill.b <= s.h && s.pill.b >= s.h - 80 : !s.pill, { pill: s.pill, text: s.pillText, href: s.pillHref });
          check(label + ': none of the old round buttons is made any more', s.oldButtons === 0, s.oldButtons);
          // the sentence behind it
          await js(`document.getElementById('vb-chip').click(); 1`); await sleep(250); s = await look();
          check(label + ': a click opens the sentence, on the screen', !!s.card && s.card.l >= 0 && s.card.r <= s.w && s.card.t >= 0, s.card);
          check(label + ': the sentence is right', v.says.test(s.says || ''), s.says);
          check(label + ': the thing to do next is right, and its address exists', v.act ? v.act.test(s.act || '') && /^http:\/\/127\.0\.0\.1:\d+\/[a-z]+\.html/.test(s.act || '') : s.act === null, s.act);
          if (process.env.SHOTS) { const p = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(path.join(process.env.SHOTS, `${who}_${page.replace(/[^a-z0-9]/gi, '_')}_${w}.png`), Buffer.from(p.data, 'base64')); }
          await js(`document.body.click(); 1`); await sleep(120); s = await look();
          check(label + ': a click elsewhere shuts it', !s.card, s.card);
          if (/analysis/.test(page) && size === 'desktop' && typeof await js(`typeof refreshUsageCount`) === 'string' && await js(`typeof refreshUsageCount`) === 'function') {
            if (who === 'trial3') {                               // one more use is counted: the functions now answer 3 used
              now = Object.assign({}, v, { used: 3 }); await js(`refreshUsageCount(); 1`); await sleep(1600); s = await look(); now = v;
              check(label + ': after a use is counted the chip says one fewer', /^2\/5( today)?$/.test(s.text || ''), s.text);
            }
            if (who === 'anon1') {                                // the pop-up's "Maybe Later"
              await js(`showStickyRegisterButton(); 1`); await sleep(300); s = await look();
              check(label + ': "Maybe Later" in the pop-up leaves the round button', !!s.pill && /Start 3-Day Free Trial/.test(s.pillText || ''), s.pillText);
            }
          }
          check(label + ': no script error on the page', errors.length === 0, errors.slice(0, 2));
        }
      }
    }
    console.log(failed ? failed + ' check(s) failed, ' + passed + ' passed' : 'all ' + passed + ' checks passed');
  } finally { chrome.kill(); server.close(); try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) { /* Chrome may still hold it */ } }
  process.exit(failed ? 1 : 0);
})();
