// Opens the live dashboard's Practice portfolio tab in headless Chrome as a real account and reports what it shows:
// the three figures, the one line under them, the graph (its two key lines, whether the S&P 500 fund's line is drawn),
// and anything that looks broken. READ-ONLY: only two kinds of request reach the site, the portfolio's own "get" (it
// reads one row) and the price function's GETs; every other call the page makes (the autopilot's, the trial function,
// reports, usage, Cognito) is answered here with an empty reply, so nothing is written and it does not count as a visit.
// Without the autopilot's answer the holdings carry no plan lines and the autopilot tab is empty: that is this tool, not a fault.
//   REAL_USER=<address> node check-tools/live_practice_check.js            (the address is never printed)
//   WIDTH=390 ...      a phone's width            SHOT=<file.png> ...   a picture of the tab (OPEN_MORE=1: with the breakdown unfolded)
//   TIME=1 ...        only the seconds until "Prices as of" shows and the number of price requests
//   LOCAL_PP=<file> ... the page is given that file as practice-portfolio.js: a staged copy tried on the live page before deploying
const { spawn } = require('child_process'); const os = require('os'), fs = require('fs'), path = require('path');
const REAL = process.env.REAL_USER || '', PORT = 9338, WIDTH = parseInt(process.env.WIDTH || '1400', 10);
if (!REAL) { console.error('REAL_USER=<address> is needed'); process.exit(1); }
const hide = (t) => String(t).split(REAL).join('<the account>');
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'practicecheck-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${dir}`, `--window-size=${Math.max(WIDTH, 500)},1000`, 'about:blank'], { stdio: 'ignore' });
  try {
    let targets = null;
    for (let i = 0; i < 40 && !targets; i++) { await sleep(250); try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); } catch (e) { /* not up yet */ } }
    const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl); await new Promise(r => { ws.onopen = r; });
    let id = 0; const waiting = {}, passed = [], answered = [];
    const send = (method, params = {}) => new Promise(r => { waiting[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && waiting[d.id]) { waiting[d.id](d.result || d.error); delete waiting[d.id]; return; }
      if (d.method !== 'Fetch.requestPaused') return;
      const q = d.params.request, short = q.url.replace(/^https:\/\/([a-z0-9]{6})[a-z0-9]*\./, 'https://$1….').slice(0, 70);
      if (/practice-portfolio\.js/.test(q.url)) { send('Fetch.fulfillRequest', { requestId: d.params.requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/javascript' }], body: Buffer.from(fs.readFileSync(process.env.LOCAL_PP, 'utf8')).toString('base64') }); return; }
      const portfolioGet = q.method === 'POST' && /5c7pt7qurshld4cwaqyopfxcei0cuurj/.test(q.url) && /"action":\s*"get"/.test(q.postData || '');
      const price = q.method === 'GET' && /dohdeb4vpu67fa2tq3ax56ls4i0rshvm/.test(q.url);
      if (portfolioGet || price || (q.method === 'OPTIONS' && /5c7pt7qurshld4cwaqyopfxcei0cuurj|dohdeb4vpu67fa2tq3ax56ls4i0rshvm/.test(q.url))) { passed.push(q.method + ' ' + short); send('Fetch.continueRequest', { requestId: d.params.requestId }); return; }
      answered.push(q.method + ' ' + short);
      send('Fetch.fulfillRequest', { requestId: d.params.requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Access-Control-Allow-Headers', value: '*' }], body: Buffer.from('{}').toString('base64') });
    };
    await send('Page.enable'); await send('Runtime.enable');
    await send('Emulation.setDeviceMetricsOverride', { width: WIDTH, height: 1000, deviceScaleFactor: 1, mobile: WIDTH < 700 });
    await send('Fetch.enable', { patterns: [...(process.env.LOCAL_PP ? [{ urlPattern: '*practice-portfolio.js*' }] : []), { urlPattern: '*lambda-url*' }, { urlPattern: '*amazoncognito*' }, { urlPattern: '*cognito-idp*' }, { urlPattern: '*execute-api*' }] });
    await send('Page.addScriptToEvaluateOnNewDocument', { source: `try { if (location.hostname === 'stockiq.tech') { localStorage.setItem('userId', '${REAL}'); window.__errors = []; window.addEventListener('error', function (e) { window.__errors.push(String(e.message).slice(0, 160)); }); } } catch (e) {}` });
    const run = async (expression) => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (r && r.exceptionDetails) return 'PAGE ERROR: ' + ((r.exceptionDetails.exception || {}).description || r.exceptionDetails.text); return r && r.result ? r.result.value : JSON.stringify(r); };
    await send('Page.navigate', { url: 'https://stockiq.tech/dashboard.html?practicecheck=' + Date.now() + '#practice' });
    // TIME=1: only how long after the page starts loading "Prices as of" appears, and how many price requests it took (23 Oct 2026)
    // It is timed twice: a first visit, then a second in the same browser, which already knows the symbols it needs (a return visit).
    if (process.env.TIME) { for (const visit of ['first visit', 'second visit']) { const t0 = Date.now(), n0 = passed.length; let txt = '';
      if (visit === 'second visit') await send('Page.navigate', { url: 'https://stockiq.tech/dashboard.html?practicecheck=' + Date.now() + '#practice' });
      for (let i = 0; i < 160 && !/Prices as of/.test(txt); i++) { await sleep(250); txt = await run(`(document.getElementById('pp-updated') || {}).textContent || ''`); }
      console.log(`${visit}: "${txt || 'no Prices as of line'}" after ${((Date.now() - t0) / 1000).toFixed(1)} s, ${passed.slice(n0).filter(r => /^GET .*dohdeb/.test(r)).length} price requests`); } if (process.env.TIME === '2') console.log(await run(`JSON.stringify({ html: Math.round(performance.getEntriesByType('navigation')[0].responseEnd), domReady: Math.round(performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd), loaded: Math.round(performance.getEntriesByType('navigation')[0].loadEventEnd), calls: performance.getEntriesByType('resource').filter(e => /lambda-url|practice-portfolio/.test(e.name)).map(e => e.name.replace(/^https:\\/\\/(.{6}).*?(\\?.{0,24}|practice-portfolio.*)$/, '$1 $2') + ' ' + Math.round(e.startTime) + '-' + Math.round(e.responseEnd)) })`));
      ws.close(); return; }
    for (let i = 0; i < 40; i++) { await sleep(500); if (await run(`!!document.querySelector('#practice-portfolio .pp-top')`) === true) break; }
    await sleep(6000);          // the prices arrive after the portfolio
    // MARKETS=<file of the screeners as the autopilot sends them> [MARKET=<g:… or s:…>]: hand the page the screener list (the
    // autopilot's answer is withheld here) and choose one market in its menu, to see the menu and a market's view (23 Oct 2026)
    if (process.env.MARKETS) {
      const info = fs.readFileSync(process.env.MARKETS, 'utf8');
      await run(`window.practicePortfolio.setPlans([], { realizedUsd: null, screeners: ${info} }); true`); await sleep(500);
      const menu = await run(`(() => { const b = document.querySelector('[data-pp="mkt-toggle"]'); if (!b) return 'no menu'; b.click(); return new Promise(done => setTimeout(() => done(JSON.stringify(Array.from(document.querySelectorAll('.pp-mkt-sum, .pp-mkt-row')).map(o => (o.classList.contains('sub') ? '   ' : '') + o.textContent.replace(/\\s+/g, ' ').trim()))), 4000)); })()`);      // 4 s: the indexes are fetched when the list opens
      console.log('market menu:', hide(menu));
      if (process.env.MARKET) { await run(`(() => { const r = document.querySelector('[data-pp="market"][data-id=' + JSON.stringify(${JSON.stringify(process.env.MARKET)}) + ']'); if (!r) { const b = document.querySelector('[data-pp="mkt-toggle"]'); if (b) b.click(); } const q = document.querySelector('[data-pp="market"][data-id=' + JSON.stringify(${JSON.stringify(process.env.MARKET)}) + ']'); if (q) q.click(); return !!q; })()`); await sleep(500); }
    }
    const report = await run(`(async () => {
      const box = document.getElementById('practice-portfolio'), t = (el) => el ? el.textContent.replace(/\\s+/g, ' ').trim() : null, q = (s) => box.querySelector(s);
      if (!box) return JSON.stringify({ fault: 'no practice portfolio on the page', at: location.href });
      const out = { script: (Array.from(document.scripts).map(s => s.src).find(s => /practice-portfolio/.test(s)) || '').replace(/^.*\\//, ''), theme: document.documentElement.getAttribute('data-theme'), shown: getComputedStyle(box).display !== 'none' && box.offsetWidth > 0, width: box.offsetWidth };
      out.figures = Array.from(box.querySelectorAll('.pp-top .pp-card')).map(t);
      out.oneLine = t(q('.pp-facts'));
      out.graphTitle = t(q('.pp-chart-title')); out.buttons = Array.from(box.querySelectorAll('.pp-chart-tabs button')).map(b => b.textContent.trim() + (b.getAttribute('aria-pressed') === 'true' ? '*' : ''));
      out.above = t(q('#pp-chart-read')); out.fundLine = !!q('#pp-chart-svg .pp-fund'); out.fundDot = !!q('#pp-dot-fund');
      const svg = q('#pp-chart-svg');
      if (svg) { const r = svg.getBoundingClientRect(), holder = box.getBoundingClientRect(); out.picture = Math.round(r.width) + ' x ' + Math.round(r.height) + (r.width > holder.width + 1 ? ' WIDER THAN ITS SECTION' : ''); out.axis = Array.from(svg.querySelectorAll('.pp-axis')).map(a => a.textContent); out.label = svg.getAttribute('aria-label');
        const colour = (sel) => { const el = q(sel); return el ? getComputedStyle(el).stroke : null; }; out.colours = { account: colour('.pp-line'), fund: colour('.pp-fund') };
        svg.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: r.left + r.width * 0.5, clientY: r.top + 40 })); out.pointerAtHalf = t(q('#pp-chart-read'));
        svg.dispatchEvent(new MouseEvent('mouseout', { bubbles: true, relatedTarget: document.body })); out.afterLeaving = t(q('#pp-chart-read')) === out.above; }
      out.note = t(q('.pp-chart-note'));
      const fig = q('.pp-chart > details'); if (fig) { fig.open = true; out.figuresTable = Array.from(fig.querySelectorAll('tr')).slice(0, 5).map(tr => Array.from(tr.children).filter(c => getComputedStyle(c).display !== 'none').map(t).join(' | ')); out.tableScrolls = fig.querySelector('div').scrollWidth > fig.querySelector('div').clientWidth + 1; fig.open = false; }
      const more = q('#pp-more'); if (more) { more.open = true; out.breakdownCard = Array.from(more.querySelectorAll('.pp-card')).map(t).find(x => /For comparison/.test(x)); out.breakdown = Array.from(more.querySelectorAll('tr, .pp-pl-line')).map(t); more.open = false; }
      out.holdings = (t(Array.from(box.querySelectorAll('th')).find(th => /^Holding/.test(th.textContent))) || ''); out.sold = t(q('#pp-sold summary')); out.rowsShown = box.querySelectorAll('td[data-label="Bought"]').length; out.heldMore = t(q('#pp-held-more'));
      out.bad = (box.innerHTML.match(/NaN|undefined|Infinity/g) || []).length; out.sticksOut = document.documentElement.scrollWidth > window.innerWidth + 1;
      for (const key of ['own', 'ai', 'value']) { const b = Array.from(box.querySelectorAll('.pp-chart-tabs button')).find(x => x.getAttribute('data-id') === key); if (!b) continue; b.click(); await new Promise(r => setTimeout(r, 250)); out['view_' + key] = { title: t(q('.pp-chart-title')), above: t(q('#pp-chart-read')), fundLine: !!q('#pp-chart-svg .pp-fund'), oneLine: t(q('.pp-facts')).replace(/^.*In holdings \\S+ · /, '') }; }
      out.chat = window.practicePortfolio && practicePortfolio.summary ? practicePortfolio.summary().split('\\n').filter(l => !/^Bought by/.test(l)) : null;
      out.remembered = Object.keys(localStorage).filter(k => /^stockiqPractice/.test(k)).map(k => k.replace(/_.*$/, '_…') + '=' + (/FundRange/.test(k) ? JSON.stringify(localStorage.getItem(k)) : '…'));
      { const sold = q('#pp-sold'); if (sold) sold.open = true; const btns = Array.from(box.querySelectorAll('[data-pp="analyse"]')); out.analyseButtons = btns.length;
        out.analyseInSold = sold ? sold.querySelectorAll('[data-pp="analyse"]').length : 0;
        const was = window.runSidebarAnalysis; let asked = null; window.runSidebarAnalysis = (sym) => { asked = sym; };      // stood in: nothing is run
        if (btns[0]) btns[0].click(); out.analyseClick = asked; window.runSidebarAnalysis = was; }
      out.errors = window.__errors; return JSON.stringify(out, null, 1);
    })()`);
    console.log(hide(report));
    console.log('\nreached the site (read-only): ' + passed.length + ' requests: ' + [...new Set(passed.map(p => p.replace(/\?symbol=.*/, '?symbol=…')))].join('; '));
    console.log('range asked for the fund: ' + (passed.filter(p => /SPY/.test(p)).join(' , ') || 'SPY not seen in the shortened addresses'));
    console.log('answered here, never reached the site: ' + answered.length + ' (' + [...new Set(answered.map(a => a.split(' ')[0]))].join(', ') + ')');
    if (process.env.SHOT) {
      // MOVES=1 (24 Oct 2026): press All markets, Your own buys and AI autopilot in turn; where the range buttons, the By-market
      // button and the picture sit each time, and which ranges are offered (the owner: "when i click ... things move alot")
      if (process.env.MOVES) {
        for (const key of ['value', 'own', 'ai', 'value']) {
          console.log('moves ' + key + ': ' + await run(`(() => { const b = document.querySelector('[data-pp="chart-key"][data-id="${key}"]'); if (!b) return 'no button'; b.click();
            return new Promise(r => setTimeout(() => { const y = (q) => { const e = document.querySelector(q); return e ? Math.round(e.getBoundingClientRect().top + window.scrollY) : '-'; };
              r('tabs ' + y('.pp-chart-tabs') + ', by-market ' + y('.pp-mkt-btn') + ', read ' + y('#pp-chart-read') + ', picture ' + y('#pp-chart svg') + '; ranges: ' + [...document.querySelectorAll('[data-pp="chart-range"]')].map(x => x.textContent).join(' ')); }, 400)); })()`));
        }
      }
      if (process.env.MARKET) { console.log('chosen before the picture: ' + await run(`(() => { const b = document.querySelector('[data-pp="mkt-toggle"]'); if (!b) return 'no menu'; if (!document.querySelector('.pp-mkt.open')) b.click(); ${process.env.MARKET_OPEN ? '' : `const q = document.querySelector('[data-pp="market"][data-id=' + JSON.stringify(${JSON.stringify(process.env.MARKET)}) + ']'); if (q) q.click();`} return (document.querySelector('.pp-mkt-btn') || {}).textContent; })()`)); await sleep(500); }
      await run(`(() => { const c = document.querySelector('#practice-portfolio'); if (${process.env.OPEN_MORE ? 1 : 0}) { const m = document.querySelector('#pp-more'); if (m) m.open = true; } c.scrollIntoView(); window.scrollBy(0, -80); return 1; })()`); await sleep(400);
      const rect = JSON.parse(await run(`(() => { const r = document.querySelector('#practice-portfolio').getBoundingClientRect(); return JSON.stringify({ x: 0, y: Math.max(0, r.top + window.scrollY - 70), width: window.innerWidth, height: Math.min(1500, r.height + 90) }); })()`));
      const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: Object.assign(rect, { scale: 1 }) });
      if (shot && shot.data) { fs.writeFileSync(process.env.SHOT, Buffer.from(shot.data, 'base64')); console.log('picture: ' + process.env.SHOT); }
    }
    ws.close();
  } finally { chrome.kill(); await sleep(300); fs.rmSync(dir, { recursive: true, force: true }); }
})().catch(e => { console.error('failed: ' + hide(e.message)); process.exit(1); });
