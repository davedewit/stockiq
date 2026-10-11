// Opens real pages of the live site in headless Chrome as a signed-in visitor would see them, and reports what the notification
// bell does there: is autopilot-bell.js loaded, what is the red number, what does the list hold after a click.
// Nothing is written anywhere: every call the page makes to the site's functions (Lambda URLs, Cognito) is answered here with
// an empty reply, except the bell's own question, which gets the made-up trades below. The "visitor" is a made-up address.
//   node check-tools/live_bell_check.js index.html analysis.html about.html
//   NO_THEME=1 node ... the same with theme.js withheld: do the pages bring the bell's script in by themselves?
const { spawn } = require('child_process'); const os = require('os'), fs = require('fs'), path = require('path');
const pages = process.argv.slice(2), PORT = 9337, U = 'bell-check@example.com';
const TRADES = [{ t: '2026-10-10T10:00:00Z', type: 'buy', symbol: 'CFX-USD', name: 'Conflux', usd: 1250, gain: null, pct: null },
  { t: '2026-10-11T08:00:00Z', type: 'sell', symbol: 'CFX-USD', name: 'Conflux', usd: 1262.79, gain: 12.79, pct: 1.02 }];
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'bellcheck-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${dir}`, '--window-size=1500,900', 'about:blank'], { stdio: 'ignore' });
  try {
    let targets = null;
    for (let i = 0; i < 40 && !targets; i++) { await sleep(250); try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); } catch (e) { /* not up yet */ } }
    const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl); await new Promise(r => { ws.onopen = r; });
    let id = 0; const waiting = {}, asked = [];
    const send = (method, params = {}) => new Promise(r => { waiting[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && waiting[d.id]) { waiting[d.id](d.result || d.error); delete waiting[d.id]; return; }
      if (d.method === 'Fetch.requestPaused') {
        const q = d.params.request, bell = /"action":\s*"bell"/.test(q.postData || '');
        asked.push((bell ? 'BELL ' : '') + q.method + ' ' + q.url.replace(/^https:\/\/([a-z0-9]{6})[a-z0-9]*\./, 'https://$1….').slice(0, 60));
        const body = /theme\.js/.test(q.url) ? '/* withheld: as if the browser still had the old copy without the loader */' : JSON.stringify(bell ? { success: true, allowed: true, trades: TRADES } : {});
        send('Fetch.fulfillRequest', { requestId: d.params.requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Access-Control-Allow-Headers', value: '*' }], body: Buffer.from(body).toString('base64') });
      }
    };
    await send('Page.enable'); await send('Runtime.enable');
    await send('Fetch.enable', { patterns: [...(process.env.NO_THEME ? [{ urlPattern: '*theme.js*' }] : []), { urlPattern: '*lambda-url*' }, { urlPattern: '*amazoncognito*' }, { urlPattern: '*cognito-idp*' }, { urlPattern: '*execute-api*' }] });
    await send('Page.addScriptToEvaluateOnNewDocument', { source: `try { if (location.hostname === 'stockiq.tech') { localStorage.setItem('userId', '${U}'); if (!localStorage.getItem('stockiqAutopilotBell_${U}')) { localStorage.setItem('stockiqAutopilotBell_${U}', '2026-10-10T12:00:00Z'); localStorage.setItem('stockiqAutopilotRead_${U}', '2026-10-10T12:00:00Z'); } } } catch (e) {}` });
    const run = async (expression) => { const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); return r && r.result ? r.result.value : JSON.stringify(r); };
    for (const page of pages) {
      asked.length = 0;
      await send('Page.navigate', { url: 'https://stockiq.tech/' + page + (page.includes('?') ? '&' : '?') + 'bellcheck=' + Date.now() }); await sleep(7000);
      const before = await run(`(() => { const b = document.getElementById('notification-bell'), n = document.getElementById('notification-badge'); return JSON.stringify({ at: location.pathname, user: localStorage.getItem('userId'), bell: b ? getComputedStyle(b).display : 'no bell', script: !!window.autopilotBell, themeLoader: Array.from(document.scripts).some(s => /autopilot-bell/.test(s.src)), trades: window.autopilotBell ? autopilotBell.trades().length : null, number: n ? (n.style.display === 'none' ? 'hidden' : n.textContent.trim()) : 'no badge' }); })()`);
      const after = await run(`(async () => { const b = document.getElementById('notification-bell'); if (!b) return 'no bell to click'; b.click(); await new Promise(r => setTimeout(r, 1200)); const d = document.getElementById('notification-dropdown'); if (!d) return 'no list opened (this page\\'s bell goes to ' + location.pathname + ')'; return Array.from(d.children).map(c => c.id === 'autopilot-bell-pointer' ? 'POINTER' : c.id === 'autopilot-bell-section' ? 'AUTOPILOT[' + c.textContent.replace(/\\s+/g, ' ').trim().slice(0, 150) + ']' : c.tagName === 'A' ? 'view-all link' : (c.querySelector && c.querySelector('h4') ? 'REPORTS heading' : (c.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 30))).join(' > '); })()`);
      console.log('\n== ' + page + '\n   after loading: ' + before + '\n   after a click on the bell: ' + after + '\n   calls the page made to the site\'s functions (all answered here, none reached the site): ' + asked.length + (asked.filter(a => a.startsWith('BELL')).length ? ', the bell\'s own question among them' : ', the bell\'s question NOT among them'));
    }
    ws.close();
  } finally { chrome.kill(); await sleep(300); fs.rmSync(dir, { recursive: true, force: true }); }
})().catch(e => { console.error('failed: ' + e.message); process.exit(1); });
