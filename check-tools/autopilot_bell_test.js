// Tests of autopilot-bell.js (the AI autopilot's buys and sells in the notification bell) with a stand-in page. Nothing real is called.
//   node check-tools/autopilot_bell_test.js ../website/autopilot-bell.js
const vm = require('vm'), fs = require('fs'); const src = fs.readFileSync(process.argv[2], 'utf8');
let ok = true; const check = (n, c, x) => { ok = ok && !!c; console.log((c ? 'PASS ' : 'FAIL ') + n + (c ? '' : '  ' + JSON.stringify(x))); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
function page({ user = 'tester@x.com', store = {}, dashboard = false, history = null, answer = null } = {}) {
  const kept = Object.assign(user ? { userId: user } : {}, store), calls = [];
  const mk = () => ({ textContent: '', style: { display: 'none' }, attrs: {}, getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }, setAttribute(k, v) { this.attrs[k] = String(v); }, removeAttribute(k) { delete this.attrs[k]; } });
  const els = { 'notification-badge': mk(), 'mobile-notification-badge': mk() }; if (dashboard) els['practice-autopilot'] = mk();
  const document = { readyState: 'complete', hidden: false, getElementById: id => els[id] || null, addEventListener() {} };
  const ctx = { document, console, setTimeout, setInterval: () => 0, Date, JSON, Math, Array, String, Set, isNaN, Promise,
    localStorage: { getItem: k => (k in kept ? kept[k] : null), setItem: (k, v) => { kept[k] = String(v); }, removeItem: k => { delete kept[k]; } },
    fetch: async (url, o) => { calls.push(JSON.parse(o.body)); return { ok: true, json: async () => answer }; }, addEventListener() {} };
  ctx.window = ctx; if (history) ctx.dashboardHistory = history;
  vm.createContext(ctx); vm.runInContext(src, ctx);
  return { bell: ctx.autopilotBell, kept, els, calls, ctx };
}
const plain = h => h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
const T = [{ t: '2026-10-10T10:00:00Z', type: 'buy', symbol: 'CFX-USD', name: 'Conflux', usd: 1250, gain: null, pct: null },
  { t: '2026-10-10T16:00:00Z', type: 'sell', symbol: 'CFX-USD', name: 'Conflux', usd: 1262.79, gain: 12.79, pct: 1.02 },
  { t: '2026-10-11T10:00:00Z', type: 'sell', symbol: 'ERG-USD', name: 'Ergo', usd: 6000, gain: -173.03, pct: -2.8 }];
(async () => {
  { const p = page(); p.bell.set(T.slice(0, 2), true);
    check('the first time, what is already there is not news: no red number, nothing unread', p.bell.unseen() === 0 && p.bell.unread() === 0 && p.els['notification-badge'].style.display === 'none');
    p.bell.set(T, true);
    check('a sale made since then is counted: the bell shows a red number, on the desktop and the phone bell', p.bell.unseen() === 1 && p.bell.unread() === 1 && p.els['notification-badge'].textContent === '1' && p.els['notification-badge'].style.display === 'flex' && p.els['mobile-notification-badge'].textContent === '1', p.els['notification-badge']);
    const h = p.bell.html(), t = plain(h);
    check('the list says clearly profit or loss and how much, with the code and the name, newest first, and marks the unread one',
      /Notifications 1 unread: 0 reports, 1 autopilot buy or sell \(practice, fake money\)/.test(t) && /Sold at a loss: ERG-USD ▼ \$173\.03 \(2\.8%\) 🤖 AI autopilot \(Beta\) · Ergo · /.test(t) && /Sold at a profit: CFX-USD ▲ \$12\.79 \(1\.0%\) 🤖 AI autopilot \(Beta\) · Conflux · /.test(t) && /Bought: CFX-USD \$1,250 🤖 AI autopilot \(Beta\) · Conflux · /.test(t)
      && t.indexOf('ERG-USD') < t.indexOf('Sold at a profit') && /aria-label="loss of \$173\.03 \(2\.8%\)"/.test(h) && (h.match(/border-radius: 50%/g) || []).length === 1 && !/undefined|NaN/.test(h), t);
    p.bell.markSeen();
    check('opening the bell clears the red number but the line stays unread, as a report does', p.bell.unseen() === 0 && p.bell.unread() === 1 && p.els['notification-badge'].style.display === 'none' && /1 unread/.test(plain(p.bell.html())));
    p.bell.markRead();
    check('clicking one marks them read', p.bell.unread() === 0 && /0 unread/.test(plain(p.bell.html())) && !/border-radius: 50%/.test(p.bell.html())); }
  { const p = page({ store: { 'unreadReports_tester@x.com': JSON.stringify(['a', 'b', 'b']), 'seenReports_tester@x.com': JSON.stringify(['a']) } });
    p.els['notification-badge'].textContent = '1'; p.els['notification-badge'].style.display = 'flex';       // as the page's own code set it for the one unseen report
    p.bell.set(T.slice(0, 1), true); check('with no new trade the page\'s own number is left alone', p.els['notification-badge'].textContent === '1' && p.els['notification-badge'].getAttribute('data-bell') === null);
    p.bell.set(T, true); check('new trades are added to the unseen reports in the one red number', p.bell.unseen() === 2 && p.els['notification-badge'].textContent === '3' && p.els['notification-badge'].style.display === 'flex', p.els['notification-badge'].textContent);
    p.bell.markSeen(); check('and once they are seen the number is the reports\' again', p.els['notification-badge'].textContent === '1' && p.els['notification-badge'].style.display === 'flex'); }
  { const older = page({ history: [{ analysisId: 'a', timestamp: '2026-10-09T08:00:00Z' }, { analysisId: 'gone', timestamp: '2026-10-12T08:00:00Z', deleted: true }] }); older.bell.set(T, true);
    const newer = page({ history: [{ analysisId: 'b', timestamp: '2026-10-11T12:00:00Z' }] }); newer.bell.set(T, true);
    const cached = page({ store: { 'dashboardHistoryCache_tester@x.com': JSON.stringify({ timestamp: 1, data: { history: [{ analysisId: 'c', timestamp: '2026-10-11T12:00:00Z' }] } }) } }); cached.bell.set(T, true);
    check('the newest item is known to be a trade when the last trade is newer than the last report (a deleted report does not count)', older.bell.onTop() === true);
    check('and a report when a report is newer, also when the page keeps its reports only in its cache', newer.bell.onTop() === false && cached.bell.onTop() === false); }
  { const mixed = page({ store: { 'unreadReports_tester@x.com': JSON.stringify(['mid']) }, history: [{ analysisId: 'late', companyName: 'ASX 50 Screener', timestamp: '2026-10-11T12:00:00Z' }, { analysisId: 'mid', companyName: 'Apple Inc.', symbol: 'AAPL', timestamp: '2026-10-10T12:00:00Z' },
      { analysisId: 'old', symbol: 'BHP.AX', timestamp: '2026-10-09T12:00:00Z' }, { analysisId: 'gone', companyName: 'Deleted one', timestamp: '2026-10-11T13:00:00Z', deleted: true }] });
    mixed.bell.set(T.slice(0, 1), true); mixed.bell.set(T, true); const h = mixed.bell.html(), t = plain(h), at = (x) => t.indexOf(x);
    check('ONE list, newest first whatever it is: a report, the newest sale, a sale, a report, the buy, the oldest report; a deleted report is left out',
      at('ASX 50 Screener') > 0 && at('ASX 50 Screener') < at('ERG-USD') && at('ERG-USD') < at('Sold at a profit: CFX-USD') && at('Sold at a profit: CFX-USD') < at('Apple Inc.') && at('Apple Inc.') < at('Bought: CFX-USD') && at('Bought: CFX-USD') < at('BHP.AX')
      && !/Deleted one/.test(t) && (h.match(/data-kind="report"/g) || []).length === 3 && (h.match(/data-kind="trade"/g) || []).length === 3, t);
    check('the heading counts both kinds of unread, each line says which kind it is, and the list ends with the way to the dashboard',
      /Notifications 3 unread: 1 report, 2 autopilot buys and sells \(practice, fake money\)/.test(t) && /Apple Inc\. 📊 Report · /.test(t) && /🤖 AI autopilot \(Beta\) · Ergo/.test(t) && /View Dashboard\s*$/.test(t) && /href="\/dashboard\.html"/.test(h), t.slice(0, 200));
    check('a report line opens the report the way the page does (or goes to the dashboard), and can only be run again where the page can do that', /data-id="mid" onclick="event\.stopPropagation\(\); autopilotBell\.report\(this\.getAttribute\('data-id'\)\)"/.test(h) && !/rerunFromNotification/.test(h));
    mixed.ctx.rerunFromNotification = () => {}; let opened = null; mixed.ctx.viewAnalysisFromNotification = (id) => { opened = id; }; mixed.bell.report('mid');
    check('where the page has them, the run-again button is shown and a click opens the report with the page\'s own routine', /rerunFromNotification\(this\.getAttribute\('data-id'\)\)/.test(mixed.bell.html()) && opened === 'mid'); }
  { const p = page({ answer: { success: true, allowed: true, trades: T } }); await sleep(20);
    check('on a page that is not the dashboard the list is asked for once, read-only, and then kept for two minutes', p.calls.length === 1 && p.calls[0].action === 'bell' && p.calls[0].list === 2 && p.calls[0].userId === 'tester@x.com' && p.bell.trades().length === 3, p.calls);
    p.bell.load(); await sleep(20); check('a second page view inside that time asks nothing', p.calls.length === 1);
    const again = page({ store: p.kept, answer: { success: true, allowed: true, trades: T } }); await sleep(20); check('nor does the next page (the list is shared through the browser)', again.calls.length === 0 && again.bell.trades().length === 3);
    const dash = page({ dashboard: true, answer: { success: true, allowed: true, trades: T } }); await sleep(20); check('the dashboard does not ask: its own panel hands the list over', dash.calls.length === 0);
    const anon = page({ user: null, answer: { success: true, allowed: true, trades: T } }); await sleep(20); check('a visitor who is not signed in is never asked about, and sees nothing', anon.calls.length === 0 && anon.bell.html() === '' && anon.bell.unseen() === 0);
    const free = page({ answer: { success: true, allowed: false, trades: [] } }); await sleep(20); free.bell.load(); await sleep(20);
    check('an account without the autopilot gets no trades, no number, a list of its reports alone, and is not asked about again for a while', free.calls.length === 1 && !/data-kind="trade"/.test(free.bell.html()) && /Nothing here yet/.test(free.bell.html()) && !/autopilot/.test(plain(free.bell.html())) && free.bell.unseen() === 0 && free.els['notification-badge'].style.display === 'none'); }
  { const store = { 'stockiqAutopilotTrades_tester@x.com': JSON.stringify({ at: 1, allowed: true, trades: T }), 'stockiqAutopilotBell_tester@x.com': '2026-10-10T12:00:00Z', 'stockiqAutopilotRead_tester@x.com': '2026-10-10T12:00:00Z' };
    const kept = Object.assign({ userId: 'tester@x.com' }, store), ctx0 = { older: { version: undefined, set() {}, trades: () => [] } };
    const p = page({ store }); // an older copy's leftovers are in the browser's store
    check('it takes over from an older copy: that copy\'s marks are kept, its list of trades is emptied so that it draws nothing', p.bell.version === 4 && !('stockiqAutopilotTrades_tester@x.com' in p.kept) && p.kept['stockiqBellBell_tester@x.com'] === '2026-10-10T12:00:00Z' && p.kept['stockiqBellRead_tester@x.com'] === '2026-10-10T12:00:00Z', Object.keys(p.kept));
    p.bell.set(T, true); check('and with the marks taken over, the two sales since then are new', p.bell.unseen() === 2 && p.bell.unread() === 2 && 'stockiqBellTrades_tester@x.com' in p.kept); }
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
})();
