"""A stand-in page with a notification bell, run by the real autopilot-bell.js: does the red number count the autopilot's new
buys and sells, and is the newest group on top of the bell's list? Nothing live is called (the answer to "bell" is made up here).

   python3 check-tools/bell_page.py ../website/autopilot-bell.js /tmp/bell.html <light|dark> <trade|report>
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=900,900 \\
       --virtual-time-budget=8000 --dump-dom file:///tmp/bell.html        (and --screenshot=... for the look)

`trade`: the last trade is newer than the last report (the trades go on top). `report`: a report is newer (the reports do)."""
import sys
src, out, theme, case = open(sys.argv[1]).read(), sys.argv[2], sys.argv[3], sys.argv[4]
report_time = '2026-10-09T08:00:00Z' if case == 'trade' else '2026-10-11T12:00:00Z'
open(out, 'w').write('''<!doctype html><html data-theme="%s"><head><meta charset="utf-8"><title>bell</title>
<style>:root { --card-bg: #fff; --bg-secondary: #f6f7f9; --border-color: #dfe3e8; --text-primary: #111; --text-secondary: #5b6570; --hover-bg: #eef1f4; }
[data-theme="dark"] { --card-bg: #1c1f24; --bg-secondary: #262a31; --border-color: #3a404a; --text-primary: #f2f4f7; --text-secondary: #a3acb8; --hover-bg: #2f343c; }
body { font-family: -apple-system, 'Inter', sans-serif; margin: 0; background: var(--card-bg); color: var(--text-primary); } header { display: flex; justify-content: flex-end; padding: 14px 380px 14px 20px; border-bottom: 1px solid var(--border-color); }</style></head>
<body><header><button id="notification-bell" onclick="goToNotifications(event)" style="position: relative; background: none; border: 1px solid var(--border-color); border-radius: 8px; padding: 8px 10px; cursor: pointer; color: var(--text-primary);">🔔
<span id="notification-badge" style="display: none; position: absolute; top: -5px; right: -5px; background: #dc3545; color: white; border-radius: 50%%; width: 18px; height: 18px; font-size: 11px; align-items: center; justify-content: center;">0</span></button></header>
<pre id="out" style="white-space: pre-wrap; font: 12px monospace; padding: 12px; margin-top: 440px;"></pre>
<script>
const U = 'tester@x.com'; localStorage.clear(); localStorage.setItem('userId', U);
localStorage.setItem('stockiqAutopilotBell_' + U, '2026-10-10T12:00:00Z'); localStorage.setItem('stockiqAutopilotRead_' + U, '2026-10-10T12:00:00Z');
localStorage.setItem('unreadReports_' + U, JSON.stringify(['r1'])); localStorage.setItem('seenReports_' + U, '[]');
let analysisHistory = [{ analysisId: 'r1', companyName: 'S&P 500 Screener', timestamp: '%s' }, { analysisId: 'r0', companyName: 'Apple Inc.', timestamp: '2026-10-08T08:00:00Z' }];
window.fetch = async (url, o) => ({ ok: true, json: async () => ({ success: true, allowed: true, trades: [
  { t: '2026-10-10T10:00:00Z', type: 'buy', symbol: 'CFX-USD', name: 'Conflux', usd: 1250, gain: null, pct: null },
  { t: '2026-10-10T16:00:00Z', type: 'sell', symbol: 'CFX-USD', name: 'Conflux', usd: 1262.79, gain: 12.79, pct: 1.02 },
  { t: '2026-10-11T10:00:00Z', type: 'sell', symbol: 'ERG-USD', name: 'Ergo', usd: 6000, gain: -173.03, pct: -2.8 }] }) });
// the page's own bell, as the dashboard and the home page draw it: a heading, the reports, a "view all" link kept last
function content() { return `<div style="padding: 15px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary);"><h4 style="margin: 0; font-size: 14px;">📊 Recent Report History</h4><p style="margin: 5px 0 0; color: var(--text-secondary); font-size: 12px;">1 unread</p></div>`
  + analysisHistory.map(i => `<div onclick="void 0" style="padding: 12px 15px; border-bottom: 1px solid var(--border-color); font-size: 13px;"><b>${i.companyName}</b><div style="color: var(--text-secondary); font-size: 11px;">${new Date(i.timestamp).toLocaleString()}</div></div>`).join('')
  + `<a href="#" style="position: sticky; bottom: 0; display: block; padding: 15px; text-align: center; border-top: 1px solid var(--border-color); background: var(--bg-secondary);">View All Reports</a>`; }
function updateNotificationBell() { const unread = JSON.parse(localStorage.getItem('unreadReports_' + U)), seen = JSON.parse(localStorage.getItem('seenReports_' + U)), n = unread.filter(i => !seen.includes(i)).length, b = document.getElementById('notification-badge'); b.textContent = n; b.style.display = n ? 'flex' : 'none'; }
function goToNotifications(event) {
  const old = document.getElementById('notification-dropdown'); if (old) { old.remove(); return; }
  localStorage.setItem('seenReports_' + U, localStorage.getItem('unreadReports_' + U)); updateNotificationBell();
  const d = document.createElement('div'); d.id = 'notification-dropdown'; d.style.cssText = 'position: absolute; top: 100%%; right: 0; width: 350px; max-height: 400px; overflow-y: auto; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,.2); text-align: left; margin-top: 5px; z-index: 10;';
  d.innerHTML = content(); document.getElementById('notification-bell').appendChild(d); }
updateNotificationBell();
</script>
<script>%s</script>
<script>
const out = (t) => { document.getElementById('out').textContent += t + '\\n'; }, wait = (ms) => new Promise(r => setTimeout(r, ms));
const order = () => Array.from(document.getElementById('notification-dropdown').children).map(c => c.id === 'autopilot-bell-section' ? 'AUTOPILOT (' + (c.textContent.match(/\\d+ unread/) || [''])[0] + ')' : c.tagName === 'A' ? 'view-all link' : (c.querySelector('h4') ? 'REPORTS heading' : 'report')).join(' > ');
const badge = () => { const b = document.getElementById('notification-badge'); return b.style.display === 'none' ? 'hidden' : b.textContent; };
(async () => {
  await wait(300); out('case: %s (the newest report is ' + analysisHistory[0].timestamp + ', the newest trade 2026-10-11T10:00:00Z)');
  out('red number after the page loads (1 unseen report + 2 new trades): ' + badge());
  document.getElementById('notification-bell').click(); await wait(100);
  out('bell opened, order of the list: ' + order()); out('red number once the bell has been opened: ' + badge());
  out('the trades as listed: ' + document.getElementById('autopilot-bell-section').textContent.replace(/\\s+/g, ' ').trim());
  document.getElementById('notification-dropdown').innerHTML = content(); await wait(100); out('after the page redraws its list: ' + order());
  let went = null; window.practiceAutopilot = { bellOpen() { went = 'the autopilot list'; } };
  document.querySelector('.autopilot-bell-row').click(); await wait(50);
  out('a click on a trade: goes to ' + went + ', list closed: ' + !document.getElementById('notification-dropdown') + ', unread now ' + autopilotBell.unread());
  localStorage.setItem('stockiqAutopilotRead_' + U, '2026-10-10T12:00:00Z'); document.getElementById('notification-bell').click(); await wait(100);   // open again, unread, for the picture
  document.title = 'done';
})();
</script></body></html>''' % (theme, report_time, src, case))
