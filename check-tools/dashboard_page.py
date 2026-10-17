"""Writes a test page holding the two real dashboard scripts for the practice portfolio and its autopilot, the site's
stylesheet and a stand-in server (nothing live is called: every request is answered inside the page).
It starts with two holdings bought by hand and one by the autopilot, then performs the steps and prints what happened.

   python3 check-tools/dashboard_page.py <practice-portfolio.js> <practice-autopilot.js> <out.html> <light|dark> "<steps>"
   steps: type (types in the buy row), sale (the autopilot sells in the background, then the page refreshes itself),
          holdings (the autopilot's "Number of holdings" field: its hint, typing 20, that it is saved),
          refresh ("Refresh prices": where it sits, its busy and done feedback, that typing in the buy row is kept; the buttons' classes),
          chart (the graph of the account over time: its size, what it reads, the pointer; chart:ai or chart:own presses that
          button and says what the two lists under it then show; open the page with ?chart=1 for an account with a few weeks of history),
          trial (a trial of its own rules starts), off (the autopilot is switched off), open (unfolds the details),
          preset or undo (the shortcuts in "Screeners it buys from", a click on a market's name, the Undo), sellall (presses "Sell everything it holds" and says yes),
          limits (types your own loss limit), split (prints the line that says whose result is whose),
          cards (prints the summary cards and every account value shown since the page opened: there should be one),
          pace (hands the three pace settings to the risk level, moves the slider, sets one by hand, moves it again),
          trailstop (chooses the full trailing stop loss in "Your own limits"),
          tabs (needs the dashboard file as a sixth argument: presses each dashboard tab and the autopilot's two parts),
          shares (ticks three markets, sets a share by hand, tries to give out more than 100%, moves the risk level),
          progress (prints the table of progress per batch of 20 finished trades),
          breakdown (fills the record with the owner's four trades of 11 Oct and opens the breakdown table),
          locked (shows the autopilot tab as an account without a paid plan sees it),
          mobile (how it sits at the window's width: what sticks out past the screen, what scrolls sideways; use mobile_frame.py for a phone's width),
          budget (types a budget larger than the practice money and presses the link that puts it right),
          next (prints the countdown, "Needs you", the "What happens next" list and the email line, and sends a test email),
          listswitch (switches the list to "buys and sells only" and reloads the page to see that it is remembered)
Open the page with headless Chrome: --dump-dom for the printed results, --screenshot for the look (site-overview.md, section 12)."""
import json, sys
pp, ap, out, theme, steps = sys.argv[1:6]
# An optional sixth argument, the path of dashboard.html: its real tab bar, tab styles and tab script are put into the
# test page (between the DASH_TABS_* markers), so the tabs are tested as they are on the site. Step: tabs.
BAR = STYLE = SCRIPT = ''
if len(sys.argv) > 6:
    dash = open(sys.argv[6]).read()
    cut = lambda a, b: dash[dash.index(a) + len(a):dash.index(b)]
    BAR = cut('DASH_TABS_BAR_START', '<!-- DASH_TABS_BAR_END -->').split('-->', 1)[1]
    SCRIPT = cut('<!-- DASH_TABS_SCRIPT_START -->', '<!-- DASH_TABS_SCRIPT_END -->')
    STYLE = '<style>' + dash[dash.index("        /* The dashboard's own tabs"):dash.index('        .button-container {')] + '</style>'
page = '''<!doctype html><html data-theme="%s"><head><meta charset="utf-8"><title>running</title>
<link rel="stylesheet" href="https://stockiq.tech/styles.css">
<style>body{padding:20px;background:var(--bg-primary);margin:0} .history-section{background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;padding:20px;margin-bottom:20px} #out{font:12px monospace;white-space:pre-wrap;color:var(--text-primary)}</style></head><body>
TABS_GO_HERE<pre id="out"></pre>
<script>
localStorage.setItem('userId', 'owner@example.com'); window.CHART_DEMO = /chart/.test(location.search + location.hash);
// ?sidebar=1: the dashboard's own countdown to the US opening is on the page (the "For comparison" card must then show its figure, not work out its own)
if (/sidebar/.test(location.search)) document.body.insertAdjacentHTML('afterbegin', '<span style="display:none"><span id="market-status-sidebar">● U.S. markets open in</span><span id="market-countdown-sidebar">7h 7m</span></span>');
// every account value the page shows, in order: a figure that flashes up before the prices are in would be listed here
window.SEEN = []; new MutationObserver(() => { const m = document.getElementById('practice-portfolio').textContent.match(/Account value\\s*(\\$[\\d,.]+)/); if (m && SEEN[SEEN.length - 1] !== m[1]) SEEN.push(m[1]); }).observe(document.getElementById('practice-portfolio'), { childList: true, subtree: true });
const iso = (h) => new Date(Date.now() + h * 3600000).toISOString().slice(0, 19) + 'Z';
const PRICES = { 'BTC-USD': 83500, 'WEMIX-USD': 0.1946, 'SPY': 700 };
let portfolio = { v: 1, startingCash: 100000, cash: 15899.07 + (window.CHART_DEMO ? 351.4 : 0), createdAt: iso(window.CHART_DEMO ? -24 * 19 : -4), closed: !window.CHART_DEMO ? [] : [
  { id: 'c1', symbol: 'CFX-USD', label: 'CFX-USD', name: 'Conflux', currency: 'USD', qty: 10000, buyPrice: 0.125, buyFx: 1, costUsd: 1251.25, boughtAt: iso(-24 * 17), soldAt: iso(-24 * 15.5), sellPrice: 0.118, sellFx: 1, proceedsUsd: 1178.8, by: 'ai', spyAtBuy: 700, spyAtSell: 700 },
  { id: 'c2', symbol: 'ERG-USD', label: 'ERG-USD', name: 'Ergo', currency: 'USD', qty: 5000, buyPrice: 1.25, buyFx: 1, costUsd: 6256.25, boughtAt: iso(-24 * 13), soldAt: iso(-24 * 11), sellPrice: 1.21, sellFx: 1, proceedsUsd: 6043.9, by: 'ai', spyAtBuy: 700, spyAtSell: 700 },
  { id: 'c3', symbol: 'CKB-USD', label: 'CKB-USD', name: 'Nervos', currency: 'USD', qty: 800000, buyPrice: 0.0078, buyFx: 1, costUsd: 6246.2, boughtAt: iso(-24 * 8), soldAt: iso(-24 * 6), sellPrice: 0.0086, sellFx: 1, proceedsUsd: 6873.1, by: 'ai', spyAtBuy: 700, spyAtSell: 700 },
  { id: 'c4', symbol: 'AAPL', label: 'AAPL', name: 'Apple Inc.', currency: 'USD', qty: 6, buyPrice: 330, buyFx: 1, costUsd: 1982, boughtAt: iso(-24 * 10), soldAt: iso(-24 * 3), sellPrice: 342, sellFx: 1, proceedsUsd: 2049.9, spyAtBuy: 700, spyAtSell: 700 }], holdings: [
  { id: 'm1', symbol: 'BTC-USD', label: 'BTC-USD', name: 'Bitcoin USD', currency: 'USD', qty: 1, buyPrice: 82750.93, buyFx: 1, costUsd: 82750.93, boughtAt: iso(-3.1), spyAtBuy: 700, note: 'fun' },
  { id: 'm2', symbol: 'BTC-USD', label: 'BTC-USD', name: 'Bitcoin USD', currency: 'USD', qty: 100 / 82734.62, buyPrice: 82734.62, buyFx: 1, costUsd: 100, boughtAt: iso(-3), spyAtBuy: 700, note: '' },
  { id: 'a1', symbol: 'WEMIX-USD', label: 'WEMIX-USD', name: 'WEMIX USD', currency: 'USD', qty: 1250 / 0.1868991, buyPrice: 0.1868991, buyFx: 1, costUsd: 1250, boughtAt: iso(-2.9), spyAtBuy: 700, note: 'AI: rank 1, RSI 14, down 3.8%% in 7 days on 1.0x volume', by: 'ai', screener: '7-1' }] };
let version = 3;
const OPTIONS = %s;
let auto = { costEachWay: 0.1, bar: { need: 300, n: 45, avg: -0.31, margin: 0.42, met: false, shared: true }, central: { trades: 45, accounts: 3, level: 20, on: true, canChange: false }, settings: { holdings: null, enabled: true, risk: 3, budgetUsd: 10000, periodDays: 10, everyHours: 0.5, maxHoldDays: 0.25, screeners: ['7-1'], aiSell: true, selfTune: true, emails: true, stopPct: null, takePct: null, auto: [], trailMode: 'gains', shares: {} }, coinShare: 1, state: { lastRun: iso(-0.1) }, minSample: 8, practiceCash: 100000, lessons: null, resting: {}, recent: [],
  scorecard: { n: 0, groups: {} }, rules: { name: 'Balanced', stop: -10, take: 18, trail: 0.5, top: 10, max_rsi: 76, arm: 9, changed: {}, yours: [], level: { stop: -10, take: 18 } }, realizedUsd: 7.91,
  tune: { trial: null, past: [], nextReviewIn: 20, batch: 20, group: 10, finished: 0 }, month: { last30: { n: 0, up: 0, usd: 0, pct: 0 }, before30: { n: 0, up: 0, usd: 0, pct: 0 } },
  nextCheck: { at: iso(0.4), markets: ['coin'] }, holding: { count: 1, investedUsd: 1250 }, now: iso(0), needs: [], mail: null,
  progress: { batch: 20, batches: [{ no: 1, first: 1, last: 20, n: 20, full: true, from: iso(-400), to: iso(-200), up: 12, avg: 0.4, usd: 80, se: 0.3 }, { no: 2, first: 21, last: 40, n: 20, full: true, from: iso(-190), to: iso(-30), up: 9, avg: -0.35, usd: -70.5, se: 0.3, prev: 0.4, diff: -0.75, margin: 0.42, verdict: 'worse' }, { no: 3, first: 41, last: 44, n: 4, full: false, from: iso(-20), to: iso(-3), up: 3, avg: 0.5, usd: 35, se: 0.4 }],
    reports: [{ no: 1, at: iso(-200), trades: 20, avg: 0.4, usd: 80, up: 12, n: 20, verdict: 'first-up', prev: null, findings: [], actions: ['It carries on as it is.'] }, { no: 2, at: iso(-30), trades: 40, avg: -0.35, usd: -70.5, up: 9, n: 20, verdict: 'worse', prev: 0.4, findings: ['Trades sold at the loss limit: 6 of the 20, averaging -7.2%%.'], actions: ['It started a trial: sell at -5%% instead of the current "sell at -10%%". Why: 6 of the last 20 finished trades were down 5%% or more at some point while held.'] }] }, money: { cash: 6500, invested: 1250, reach: 7750 },
  coming: [{ at: iso(0.4), kind: 'check', text: 'Next check-in (coin market). It looks at the holding it has there (WEMIX-USD) and sells it if it has hit its loss limit, gain mark, stop or time limit, or if the AI review wants it out. It may buy up to 1 holding of about $1,250 from Crypto (top coins), if something on the shortlist passes its filters.' },
            { at: iso(2.1), kind: 'release', text: 'From this check-in more of the budget can be invested: $3,750 of the $10,000 ($2,500 until then; $1,250 is invested now). The budget is released in steps; a check-in is when it can be spent, in markets that are open.' },
            { at: iso(3.1), kind: 'sell', text: 'WEMIX-USD is sold at the latest: its 6 hours are up then.' },
            { at: iso(31), kind: 'open', text: 'First check-in after the US market opens. It can buy from S&P 100 if part of the budget is free then.' },
            { at: iso(24 * 9), kind: 'rest', text: 'The Dow 30 screener is tried again after its rest.' },
            { after: 17, kind: 'review', text: 'It reviews its own rules (3 of the 20 finished trades it waits for are in), may start a trial of one change beside the current rule, and emails you.' },
            { after: 2, kind: 'notes', text: 'The AI model writes fresh notes on what the record shows (under "How it is doing").' }],
  plans: [{ id: 'a1', label: 'WEMIX-USD', boughtAt: iso(-2.9), sellBy: iso(3.1), auto: true, stop: -10, take: 18, arm: 1, trail: 0.5, peak: 6.2, floor: 3.5, view: { t: iso(-0.1), sell: false, text: 'Up 4%% and still climbing', larger: true } }],
  log: [{ t: iso(-2.9), type: 'buy', symbol: 'WEMIX-USD', usd: 1250, text: 'rank 1, RSI 14, down 3.8%% in 7 days on 1.0x volume (Crypto (top coins) rank 1, score +4.0; chosen by the AI model)', detail: ['The plan for it: sell 6 hours after buying at the latest; sooner at -10%% or +18%%; once it has been up 9%%, sell if it gives back 50%% of its best gain; sell if its screener signal turns negative or it slips far down the ranking.'] },
        { t: iso(-0.1), first: iso(-2.4), n: 5, key: 'pace', type: 'note', symbol: '', usd: 0, text: 'Checked in. Nothing to spend yet: $1,250 of the $10,000 budget is invested. The rest is released in steps over the 10 days set under "Build up to it over"; the next $1,250 in about 21 hours.' }] };
const calls = [];
window.fetch = async (url, opts) => {
  const u = String(url); await new Promise(r => setTimeout(r, 60));
  const json = (o) => ({ ok: true, status: 200, json: async () => o });
  if (u.includes('?symbol=')) { const sym = decodeURIComponent(u.split('?symbol=')[1].split('&')[0]); const p = PRICES[sym]; const span = { '3mo': 90, '6mo': 180, '1y': 365 }[(u.split('&range=')[1] || '')] || 30; if (!p) return { ok: false, status: 500, json: async () => ({}) }; const nowS = Math.floor(Date.now() / 1000), day0 = Math.floor(nowS / 86400) * 86400, wave = (i) => p * (1 + 0.035 * Math.sin(i / 2.3 + sym.length) - 0.0012 * i);
    const ts = [], close = []; for (let i = span - 1; i >= 0; i--) { ts.push(day0 - i * 86400 + (sym.endsWith('-USD') ? 0 : 48600)); close.push(wave(i)); }
    return json({ chart: { result: [{ meta: { regularMarketPrice: p, regularMarketTime: nowS, currency: 'USD', longName: sym }, timestamp: ts, indicators: { quote: [{ close }] } }] } }); }
  const b = JSON.parse(opts.body); calls.push((b.settings ? 'autopilot-' : b.portfolio ? 'portfolio-' : '') + b.action);
  if (b.action === 'get' && !('settings' in b) && u.includes('5c7pt7q')) return json({ success: true, portfolio, version });
  if (b.action === 'save' && b.portfolio) { portfolio = b.portfolio; version++; return json({ success: true, version }); }
  if (window.LOCKED && !u.includes('5c7pt7q')) return b.action === 'get' ? json({ success: true, allowed: false, locked: 'plan', upgrade: 'dashboard.html#upgrade' }) : { ok: false, status: 402, json: async () => ({ error: 'The AI autopilot is part of the paid plans. Choose a plan to use it', locked: 'plan' }) };
  if (b.action === 'mailtest') { auto.mail = { t: iso(0), ok: true, subject: 'StockIQ autopilot (fake money): review emails are set up', why: null }; return json(Object.assign({ success: true, allowed: true, options: OPTIONS, summary: { sent: true } }, auto)); }
  if (b.action === 'save' && b.settings) { auto.settings = b.settings; auto.plans.forEach(p => { p.auto = b.settings.enabled; }); }
  if (b.action === 'sellall') { const n = auto.plans.length; portfolio.holdings.filter(h => h.by === 'ai').forEach(h => { portfolio.closed.push(Object.assign({}, h, { sellPrice: PRICES[h.symbol], sellFx: 1, proceedsUsd: h.qty * PRICES[h.symbol], soldAt: iso(0), spyAtSell: 700 })); portfolio.cash += h.qty * PRICES[h.symbol]; });
    portfolio.holdings = portfolio.holdings.filter(h => h.by !== 'ai'); version++; auto.plans = []; auto.holding = { count: 0, investedUsd: 0 };
    auto.log.push({ t: iso(0), type: 'sell', symbol: 'WEMIX-USD', usd: 1301.5, kind: 'hand', pct: 4.12, text: 'Sold because you pressed "Sell everything it holds". Put in $1,250.00, got back $1,301.50.' });
    return json(Object.assign({ success: true, allowed: true, options: OPTIONS, summary: { sold: n, skipped: [] } }, auto)); }
  return json(Object.assign({ success: true, allowed: true, options: OPTIONS }, auto));
};
</script>
<script>%s</script>
<script>%s</script>
<script>
const out = (m) => { document.getElementById('out').textContent += m + '\\n'; };
const wait = (ms) => new Promise(r => setTimeout(r, ms));
const q = (s) => document.querySelector(s);
const cellText = (label) => { const row = Array.from(document.querySelectorAll('#practice-portfolio tr')).find(r => r.textContent.includes(label)); return row ? row.cells[0].textContent.replace(/\\s+/g, ' ').trim() : '(no row)'; };
(async () => {
  await wait(900);
  out('loaded. headers: ' + Array.from(document.querySelectorAll('#practice-portfolio table tr:first-child th')).map(t => t.textContent).join(' | '));
  out('a holding bought by hand: ' + cellText('fun'));
  out('the autopilot holding: ' + cellText('WEMIX'));
  out('how it is doing: ' + Array.from(document.querySelectorAll('#practice-autopilot .ap-section')).map(x => x.textContent.replace(/\\s+/g, ' ').trim().slice(0, 330)).join('\\n   '));
  for (const step of %s) {
    if (step === 'chart' || step.startsWith('chart:')) {      // the graph of the account over time (give the page ?chart=1 for an account with a few weeks of history)
      const svg = q('#pp-chart-svg'); if (!svg) { out('chart: NO GRAPH on the page'); } else {
        const d = q('#pp-chart-svg .pp-line').getAttribute('d'), n = (d.match(/[ML]/g) || []).length, r = svg.getBoundingClientRect(), holder = q('#practice-portfolio').getBoundingClientRect();
        out('chart: ' + q('.pp-chart-title').textContent + ' | ' + n + ' points | drawn ' + Math.round(r.width) + ' x ' + Math.round(r.height) + ' in a section ' + Math.round(holder.width) + ' wide | tabs: ' + Array.from(document.querySelectorAll('.pp-chart-tabs button')).map(b => b.textContent + (b.getAttribute('aria-pressed') === 'true' ? '*' : '')).join(', '));
        out('chart reads: ' + q('#pp-chart-read').textContent.replace(/\\s+/g, ' ') + ' | card: ' + (q('#practice-portfolio').textContent.match(/Account value\\s*(\\$[\\d,.]+)/) || [])[1]);
        svg.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: r.left + r.width * 0.45, clientY: r.top + 40 })); out('chart, pointer at 45%%: ' + q('#pp-chart-read').textContent.replace(/\\s+/g, ' ') + ' | line shown: ' + (q('#pp-cross').style.display !== 'none'));
        const want = step.split(':')[1]; if (want) { const b = Array.from(document.querySelectorAll('.pp-chart-tabs button')).find(x => x.getAttribute('data-id') === want); if (b) { b.click(); await wait(200); out('chart, pressed ' + want + ': ' + q('.pp-chart-title').textContent + ' | ' + q('#pp-chart-read').textContent.replace(/\\s+/g, ' ')); } }
        if (want) { const part = q('#pp-part'), rowsNow = document.querySelectorAll('#practice-portfolio table.pp-stack [data-pp="sell"]').length, headNow = q('#practice-portfolio table.pp-stack tr.pp-head th');
          q('#pp-note').value = 'kept?'; const again = Array.from(document.querySelectorAll('.pp-chart-tabs button')).find(x => x.getAttribute('data-id') === want); if (again) { again.click(); await wait(150); }
          out('chart, the lists after pressing ' + want + ': ' + rowsNow + ' holding(s) listed | heading "' + (headNow ? headNow.textContent : '') + '" | line: "' + (part ? part.textContent.replace(/\\s+/g, ' ').trim() : 'none') + '" | sold: "' + ((q('#pp-sold summary') || {}).textContent || 'none') + '" | typing kept: ' + (q('#pp-note').value === 'kept?')); q('#pp-note').value = ''; }
        out('chart, wider than its section: ' + (q('#pp-chart-svg').getBoundingClientRect().width > holder.width + 1) + ' | NaN in the picture: ' + /NaN|undefined/.test(q('.pp-chart').innerHTML));
      } }
    if (step === 'refresh') {      // "Refresh prices": where it sits, that it says it is working and when it is done, and that what is typed in the buy row stays
      q('#pp-symbol').value = 'APPL'; q('#pp-amount').value = '500'; q('#pp-note').value = 'my note';
      const tools = q('#pp-tools'), head = tools && tools.closest('.pp-headrow'), btn = () => q('[data-pp="refresh"]');
      out('refresh: the two buttons sit ' + (head ? 'beside the heading' : 'at the bottom') + ': ' + Array.from(tools.querySelectorAll('button')).map(b => b.textContent.trim() + ' [' + b.className + ']').join(' | ') + ' | says: "' + q('#pp-updated').textContent + '"');
      const top = (el) => Math.round(el.getBoundingClientRect().top), h2 = document.querySelector('.pp-headrow h2'); if (h2) out('refresh: heading at ' + top(h2) + 'px, buttons at ' + top(btn()) + 'px from the top; first card at ' + top(q('.pp-card')) + 'px');
      btn().click(); await wait(30); out('refresh, just pressed: button "' + btn().textContent.trim() + '" [' + btn().className + '] disabled ' + btn().disabled + ' | says: "' + q('#pp-updated').textContent + '"');
      await wait(900); out('refresh, done: button "' + btn().textContent.trim() + '" [' + btn().className + '] | says: "' + q('#pp-updated').textContent + '" [' + q('#pp-updated').className + ']');
      out('refresh: what was typed is still there: ' + [q('#pp-symbol').value, q('#pp-amount').value, q('#pp-note').value].join(' / '));
      out('buttons with a class each: ' + Array.from(document.querySelectorAll('#practice-portfolio button, #pp-tools button')).filter(b => !b.closest('.pp-chart-tabs')).map(b => (b.getAttribute('data-pp') || '?') + ':' + (b.className || 'NO CLASS') + (b.getAttribute('style') ? ' INLINE STYLE' : '')).filter((v, i, a) => a.indexOf(v) === i).join(', '));
      const cs = getComputedStyle(btn()); out('refresh button look: background ' + cs.backgroundColor + ', border ' + cs.borderTopColor + ', cursor ' + cs.cursor);
      out('autopilot buttons: ' + Array.from(document.querySelectorAll('#practice-autopilot .ap-btn, #practice-autopilot a[data-ap="refresh"], #practice-autopilot a[data-ap="mailtest"]')).map(b => b.textContent.trim().slice(0, 26) + ' [' + b.className + ']').join(' | '));
      const link = q('#practice-autopilot a[data-ap="refresh"]'); if (link) { link.click(); await wait(20); const now = q('#practice-autopilot a[data-ap="refresh"]'); out('autopilot Refresh now, just pressed: "' + now.textContent + '" [' + now.className + ']'); await wait(900); const after = q('#practice-autopilot a[data-ap="refresh"]'); out('autopilot Refresh now, done: "' + after.textContent + '" [' + after.className + '] | "' + q('#ap-fresh').textContent.slice(0, 60) + '" [' + q('#ap-fresh').className + ']'); }
    }
    if (step === 'holdings') {      // the number of holdings as a setting of its own: the field, what typing a number says, that it is saved
      const part = q('[data-ap-part="settings"]'); if (part) { part.click(); await wait(200); }
      const box = q('#ap-holdings'); if (!box) out('holdings: NO FIELD on the page'); else {
        out('holdings: field with placeholder "' + box.placeholder + '", value "' + box.value + '", tag "' + q('#ap-tag-holdings').textContent + '" | ' + q('#ap-holdings-hint').textContent);
        box.focus(); box.value = '20'; box.dispatchEvent(new Event('input', { bubbles: true })); await wait(100);
        out('holdings, typed 20: tag "' + q('#ap-tag-holdings').textContent + '" | ' + q('#ap-holdings-hint').textContent); out('holdings, the plan in words: ' + q('#ap-plan').textContent.slice(0, 200));
        await wait(1400); out('holdings, saved: ' + JSON.stringify(auto.settings.holdings) + ' | the box still holds "' + q('#ap-holdings').value + '" | ' + (q('#ap-saved') ? q('#ap-saved').textContent : ''));
      } }
    if (step === 'type') { const b = q('#pp-symbol'); b.focus(); b.value = 'APPL'; q('#pp-amount').value = '500'; out('typed APPL and 500 in the buy row'); }
    if (step === 'sale') {
      portfolio.closed.push(Object.assign({}, portfolio.holdings[2], { sellPrice: 0.1946, sellFx: 1, proceedsUsd: 1301.5, soldAt: iso(0), spyAtSell: 700 })); portfolio.holdings.pop(); portfolio.cash += 1301.5; version++;
      auto.plans = []; auto.holding = { count: 0, investedUsd: 0 }; auto.scorecard = { label: 'all', n: 1, avg: 4.1, vs: 4.1, beat: 1, judged: 1, up: 1, groups: { exit: [{ label: 'sold at the time limit', n: 1, avg: 4.1, vs: 4.1, beat: 1, judged: 1, up: 1 }] } };
      auto.month.last30 = { n: 1, up: 1, usd: 51.5, pct: 0.52 }; auto.tune.nextReviewIn = 19;
      auto.log.push({ t: iso(0), type: 'sell', symbol: 'WEMIX-USD', usd: 1301.5, kind: 'time', pct: 4.12, text: 'Held 6 hours, the longest this autopilot keeps a holding (+4.1%%). Put in $1,250.00, got back $1,301.50.', detail: ['Bought at rank 1 of Crypto (top coins) (score +4.0, RSI 14), chosen by the AI model: rank 1, RSI 14, down 3.8%% in 7 days on 1.0x volume.', 'Held 6 hours. It was set to keep a holding at most 6 hours.', 'While it was held: +5.1%% at its best, -0.8%% at its worst (as seen at check-ins).', 'At the sale: rank 3, score +3.1, signal positive.', 'Its rules for this holding: sell at -10%% or +18%%; once up 9%%, sell if it gives back 50%% of its best gain; sell if the screener signal turns negative or it slips far down the ranking.'] });
      await window.practiceAutopilot.refresh(false); await wait(900);
      out('the autopilot sold in the background and the page refreshed itself. calls: ' + calls.slice(-4).join(', '));
      out('  WEMIX still in the holdings table: ' + (cellText('WEMIX') !== '(no row)' && !q('#pp-sold')) + ' | sold list: ' + (q('#pp-sold') ? q('#pp-sold').querySelector('summary').textContent : 'none'));
      out('  buy row after the refresh: symbol="' + q('#pp-symbol').value + '" amount="' + q('#pp-amount').value + '" focus kept=' + (document.activeElement === q('#pp-symbol')));
      out('  latest in the list: ' + q('#practice-autopilot .ap-log').textContent.replace(/\\s+/g, ' ').trim().slice(0, 420));
      out('  how it is doing: ' + q('#practice-autopilot .ap-section').textContent.replace(/\\s+/g, ' ').trim().slice(0, 300));
    }
    if (step === 'trial') {
      auto.tune = Object.assign({}, auto.tune, { nextReviewIn: null, trial: { id: 1, param: 'take', old: 18, new: 9, since: iso(0), why: '10 of the last 20 finished trades were up 9%% or more at some point while held, and ended at +1.0%% on average', how: 'Every second buy follows the changed rule, the others the current one, so both are tried over the same days.', text: 'sell at +9%% instead of "sell at +18%%"', with: 3, without: 2, avgWith: 2.1, avgWithout: -0.4 },
        past: [{ id: 0, param: 'stop', old: -10, new: -5, since: iso(-200), ended: iso(-80), verdict: 'dropped', text: 'sell at -5%% instead of "sell at -10%%"', result: '10 trades with the change averaged -0.40%%, 10 without it +0.10%% (difference -0.50, margin of error 0.62): no clear improvement' }] });
      await window.practiceAutopilot.refresh(false); await wait(500);
      out('a trial started: ' + Array.from(document.querySelectorAll('#practice-autopilot .ap-section')).find(x => x.textContent.includes('Improving its own rules')).textContent.replace(/\\s+/g, ' ').trim().slice(0, 900));
    }
    if (step === 'preset' || step === 'undo') {              // the shortcuts in "Screeners it buys from", a market's name, and the Undo
      const ticked = () => Array.from(document.querySelectorAll('[data-ap-screener]')).filter(c => c.checked).map(c => c.getAttribute('data-ap-screener')).join(',');
      const pace = () => 'level=' + q('#ap-risk').value + ' days=' + q('#ap-period').value + ' checks=' + q('#ap-every').value + ' keeps=' + q('#ap-hold').value;
      const before = ticked(), paceBefore = pace(), y = window.scrollY;
      out('old quick set-ups on the page: ' + document.querySelectorAll('[data-ap-preset]').length + ' | shortcuts: ' + Array.from(document.querySelectorAll('[data-ap-pick]')).map(x => x.textContent).join(' / '));
      q('[data-ap-group="US markets"]').click(); await wait(900); out('click on "US markets": ticked [' + ticked() + '] | notice: ' + (q('#ap-notice').textContent || '').slice(0, 60));
      q('[data-ap-group="US markets"]').click(); await wait(900); out('second click: ticked [' + ticked() + ']');
      q('[data-ap-pick="main"]').click(); await wait(900); out('"Main index of every country": ticked [' + ticked() + '] | notice: ' + (q('#ap-notice').textContent || '').slice(0, 110));
      out('  pace unchanged by all of that: ' + (pace() === paceBefore) + ' (' + pace() + '), page did not jump: ' + (window.scrollY === y));
      const link = q('[data-ap="undopreset"]'); out('  Undo offered: ' + !!link);
      if (link) { link.click(); await wait(900); out('  after Undo: ticked [' + ticked() + '], same as before the first click: ' + (ticked() === before) + ', notice: ' + (q('#ap-notice').textContent || '').slice(0, 60) + ', Undo still offered: ' + !!q('[data-ap="undopreset"]')); }
    }
    if (step === 'sellall') { window.confirm = (m) => { out('asked: ' + m.split(String.fromCharCode(10)).filter(Boolean).join(' / ')); return true; }; const b = q('#ap-sellall'); out('button: "' + b.textContent + '" disabled=' + b.disabled); b.click(); await wait(1200);
      out('  after: notice="' + q('#ap-notice').textContent + '" | button "' + q('#ap-sellall').textContent + '" disabled=' + q('#ap-sellall').disabled + ' | WEMIX still held in the table: ' + (cellText('WEMIX') !== '(no row)' && !!Array.from(document.querySelectorAll('#practice-portfolio button[data-pp="sell"]')).find(x => x.closest('tr').textContent.includes('WEMIX'))) + ' | calls: ' + calls.slice(-3).join(', ')); }
    if (step === 'limits') { const a = q('#ap-stop'); out('your own limits: fields empty, greyed hints "' + a.placeholder + '" and "' + q('#ap-take').placeholder + '"'); a.focus(); a.value = '6'; a.dispatchEvent(new Event('input', { bubbles: true })); await wait(200);
      out('  typed 6 as the loss limit: risk text now "' + q('#ap-risk-text').textContent.slice(0, 120) + '" | focus kept=' + (document.activeElement === a)); await wait(1500); out('  saved: stopPct=' + auto.settings.stopPct + ' takePct=' + auto.settings.takePct + ' | saved line "' + q('#ap-saved').textContent + '"'); }
    if (step === 'split') { const pl = document.querySelector('#practice-portfolio table.pp-pl');   // the profit-and-loss table (17 Oct 2026), or the older row
      out('whose result is whose: ' + (pl ? Array.from(pl.querySelectorAll('tr')).map(r => r.textContent.replace(/\\s+/g, ' ').trim()).join(' | ') : (Array.from(document.querySelectorAll('#practice-portfolio div')).map(x => x.textContent.replace(/\\s+/g, ' ').trim()).find(t => t.startsWith('Whose result is whose')) || '(no line)'))); }
    if (step === 'listswitch') {
      const rows = () => Array.from(document.querySelectorAll('#practice-autopilot .ap-log')).length, box = () => q('#ap-tradesonly');
      if (!sessionStorage.getItem('reloaded')) { localStorage.removeItem('stockiqAutopilotTradesOnly'); out('list switch: on=' + box().checked + ', lines listed=' + rows()); box().click(); await wait(300);
        out('  switched on: on=' + box().checked + ', lines listed=' + rows() + ', saves sent=' + calls.filter(c => c.includes('save')).length); sessionStorage.setItem('reloaded', document.getElementById('out').textContent); location.reload(); return; }
      document.getElementById('out').textContent = sessionStorage.getItem('reloaded') + document.getElementById('out').textContent; sessionStorage.removeItem('reloaded');
      out('  after a real page refresh: on=' + box().checked + ', lines listed=' + rows() + ', at y=' + Math.round(box().getBoundingClientRect().top + window.scrollY)); localStorage.removeItem('stockiqAutopilotTradesOnly'); }
    if (step === 'cards') { out('account values shown since the page opened: ' + JSON.stringify(SEEN)); Array.from(document.querySelectorAll('#practice-portfolio > div:first-child > div')).forEach(c => out('  card: ' + c.textContent.replace(/\\s+/g, ' ').trim())); }
    if (step === 'pace') {
      const show = (what) => out(what + ': build-up "' + q('#ap-period').value + '" (greyed ' + q('#ap-period').placeholder + '), checks in "' + q('#ap-every').selectedOptions[0].textContent + '", keeps "' + q('#ap-hold').selectedOptions[0].textContent + '" | tags ' + Array.from(document.querySelectorAll('#practice-autopilot .ap-auto')).map(x => x.textContent).join(', ') + ' | saved ' + JSON.stringify([auto.settings.risk, auto.settings.periodDays, auto.settings.everyHours, auto.settings.maxHoldDays, auto.settings.auto]));
      show('pace, as saved before (set by hand)');
      q('[data-ap="autopace"]').click(); await wait(900); show('pressed "Let the risk level set all three"');
      const r = q('#ap-risk'); r.value = '5'; r.dispatchEvent(new Event('input', { bubbles: true })); await wait(200); show('moved the slider to Adventurous (before it is saved)'); out('  it says: ' + q('#ap-plan').textContent.slice(0, 140));
      await wait(1400); show('  a moment later');
      const h = q('#ap-hold'); h.value = String(0.25); h.dispatchEvent(new Event('change', { bubbles: true })); await wait(900); show('chose 6 hours for the holding time myself');
      const r2 = q('#ap-risk'); r2.value = '1'; r2.dispatchEvent(new Event('input', { bubbles: true })); r2.dispatchEvent(new Event('change', { bubbles: true })); await wait(1500); show('moved the slider to Cautious');   // the panel was redrawn: take the slider afresh
      out('  it says: ' + q('#ap-pace').textContent.slice(0, 110)); }
    if (step === 'trailstop') { const t = q('#ap-trail'); out('trailing stop: "' + t.selectedOptions[0].textContent + '" | ' + q('#ap-trail-text').textContent.slice(0, 90)); t.value = 'full'; t.dispatchEvent(new Event('change', { bubbles: true })); await wait(900);
      out('  chose the full trailing stop loss: saved trailMode=' + auto.settings.trailMode + ' | "' + q('#ap-trail').selectedOptions[0].textContent + '" | ' + q('#ap-trail-text').textContent.slice(0, 110)); out('  it says: ' + q('#ap-pace').textContent.slice(60, 260)); }
    if (step === 'tabs') {
      const seen = () => Array.from(document.querySelectorAll('[data-dash-panel]')).filter(p => !p.hidden).map(p => p.getAttribute('data-dash-panel')).join(',') + ' | tabs offered: ' + Array.from(document.querySelectorAll('[data-dash-tab]')).filter(b => !b.hidden).map(b => b.textContent.trim() + (b.classList.contains('active') ? '*' : '')).join(' / ') + ' | address ' + (location.hash || '(none)');
      out('tabs at the start: showing ' + seen());
      for (const name of ['practice', 'autopilot', 'reports', 'autopilot']) { q('[data-dash-tab="' + name + '"]').click(); await wait(150); out('  pressed ' + name + ': showing ' + seen() + ' | remembered ' + localStorage.getItem('stockiqDashboardTab')); }
      out('  autopilot parts: ' + ['activity', 'settings'].map(n => n + (q('#ap-pane-' + n).style.display === 'none' ? ' hidden' : ' shown')).join(', ')); q('[data-ap-part="settings"]').click(); await wait(100);
      out('  pressed Settings inside the autopilot: ' + ['activity', 'settings'].map(n => n + (q('#ap-pane-' + n).style.display === 'none' ? ' hidden' : ' shown')).join(', ') + ' | page height now ' + document.documentElement.scrollHeight + 'px'); q('[data-ap-part="activity"]').click(); await wait(100);
      out('  back on Activity: page height ' + document.documentElement.scrollHeight + 'px'); localStorage.removeItem('stockiqDashboardTab'); localStorage.removeItem('stockiqAutopilotPart'); }
    if (step === 'next') {
      const line = (sel) => { const x = q(sel); return x ? x.textContent.replace(/\\s+/g, ' ').trim() : '(none)'; };
      out('countdown under the status: ' + line('#practice-autopilot .ap-countline')); out('needs you: ' + line('#ap-needs'));
      const sec = Array.from(document.querySelectorAll('#practice-autopilot .ap-section')).find(x => x.textContent.includes('What happens next'));
      out('what happens next: ' + (sec ? sec.textContent.replace(/\\s+/g, ' ').trim() : '(none)'));
      const first = q('#practice-autopilot [data-ap-until]'), was = first.textContent; await wait(2300); out('the countdown ticks: "' + was + '" then "' + q('#practice-autopilot [data-ap-until]').textContent + '"');
      q('[data-ap-part="settings"]').click(); await wait(200); document.documentElement.style.scrollBehavior = 'auto';   /* the site glides when it scrolls; a headless browser does not play the glide, so jump for this check */
      window.scrollTo(0, 0); await wait(100); q('#practice-autopilot .ap-countline a').click(); await wait(600);
      out('pressed "What happens then" from the Settings part at the top of the page: activity shown=' + (q('#ap-pane-activity').style.display !== 'none') + ' | page moved down to ' + Math.round(window.scrollY) + 'px | the list is ' + Math.round(q('#ap-coming').getBoundingClientRect().top) + 'px from the top of the window | address ' + (location.hash || '(none)') + ' | page height ' + document.documentElement.scrollHeight + ', window ' + window.innerHeight + ', scroller ' + (document.scrollingElement && document.scrollingElement.tagName));
      out('email line: ' + line('#ap-mail-state')); q('#practice-autopilot [data-ap="mailtest"]').click(); await wait(700); out('after "Send me a test email": ' + line('#ap-notice') + ' | ' + line('#ap-mail-state'));
      auto.needs = [{ kind: 'missed', at: iso(-1), text: 'A scheduled check-in was due and has not happened. Press "Check in now"; if that works, the schedule itself may be stopped and needs a look.' }];
      await window.practiceAutopilot.refresh(true); await wait(500); out('with something wrong: ' + line('#ap-needs') + ' | its tab reads: ' + line('[data-dash-tab="autopilot"]')); auto.needs = [];
      await window.practiceAutopilot.refresh(true); await wait(500); out('put right again: ' + line('#ap-needs').slice(0, 40) + ' | its tab reads: ' + line('[data-dash-tab="autopilot"]'));
    }
    if (step === 'budget') {
      const line = (sel) => { const x = q(sel); return x ? x.textContent.replace(/\\s+/g, ' ').trim() : '(none)'; };
      out('under the budget field (budget ' + q('#ap-budget').value + ', field max ' + q('#ap-budget').max + '): ' + line('#ap-budget-hint'));
      const b = q('#ap-budget'); b.focus(); b.value = '9000'; b.dispatchEvent(new Event('input', { bubbles: true })); await wait(1300);
      out('typed 9000: ' + line('#ap-saved') + ' | ' + line('#ap-budget-hint')); b.blur();
      q('[data-ap="maxbudget"]').click(); await wait(900); out('pressed the link: budget field ' + q('#ap-budget').value + ' | ' + line('#ap-notice') + ' | ' + line('#ap-budget-hint') + ' | saved budget ' + auto.settings.budgetUsd);
    }
    if (step === 'shares') {
      const line = (sel) => { const x = q(sel); return x ? x.textContent.replace(/\\s+/g, ' ').trim() : '(none)'; };
      const menus = () => Array.from(document.querySelectorAll('#practice-autopilot [data-ap-share]')).map(x => x.getAttribute('data-ap-share') + ': "' + x.selectedOptions[0].textContent + '" (' + x.parentNode.querySelector('.ap-auto').textContent + ')').join(' | ');
      out('one market ticked: ' + menus() + ' || ' + line('#ap-split'));
      for (const k of ['3-100', '4-200']) { q('[data-ap-screener="' + k + '"]').click(); await wait(700); }
      out('three markets ticked: ' + menus() + ' || ' + line('#ap-split'));
      const coins = q('[data-ap-share="Coins"]'); out('the coin menu offers: ' + Array.from(coins.options).map(o => o.textContent).join(' / '));
      coins.value = '50'; coins.dispatchEvent(new Event('change', { bubbles: true })); await wait(700);
      out('coins set to 50%%: ' + menus() + ' || ' + line('#ap-split') + ' || saved shares ' + JSON.stringify(auto.settings.shares));
      const us = q('[data-ap-share="US markets"]'); us.value = '75'; us.dispatchEvent(new Event('change', { bubbles: true })); await wait(700);
      out('then US set to 75%%: ' + line('#ap-saved') + ' || saved shares ' + JSON.stringify(auto.settings.shares));
      q('[data-ap-share="US markets"]').value = 'auto'; q('[data-ap-share="US markets"]').dispatchEvent(new Event('change', { bubbles: true })); await wait(700);
      const r = q('#ap-risk'); r.value = '5'; r.dispatchEvent(new Event('input', { bubbles: true })); await wait(1300);
      out('level moved to Adventurous (4 holdings): ' + menus() + ' || ' + line('#ap-split'));
      r.value = '3'; r.dispatchEvent(new Event('input', { bubbles: true })); await wait(1300); r.blur(); window.dashboardTabs && window.dashboardTabs.show('autopilot'); q('[data-ap-part="settings"]').click(); await wait(300); q('[data-ap-screener="4-200"]').click(); await wait(800); out('one market un-ticked again: ' + menus() + ' || bar: ' + line('#ap-splitbar')); window.scrollTo(0, 0);
    }
    if (step === 'progress') { const sec = Array.from(document.querySelectorAll('#practice-autopilot .ap-section')).find(x => x.textContent.includes('Progress, 20')); out('progress: ' + (sec ? sec.textContent.replace(/\\s+/g, ' ').trim() : '(none)')); if (sec) sec.scrollIntoView({ block: 'start' }); }
    if (step === 'breakdown') {
      const g = (label, n, avg, up, vs) => ({ label, n, avg, vs, up, beat: 0, judged: n });
      auto.scorecard = { n: 4, avg: -0.5, up: 2, vs: -0.5, beat: 0, judged: 4, label: 'all', groups: { screener: [g('Crypto (top coins)', 4, -0.5, 2, -0.5)], rank: [g('rank 1 to 3', 2, -1.1, 1, -1.1), g('rank 4 to 10', 2, 0.1, 1, 0.1)], rsi: [g('RSI under 45', 1, 0.6, 1, 0.6), g('RSI 45 to 60', 3, -0.8, 1, -0.8)],
        stay: [g('new to the shortlist', 2, -1.8, 0, -1.8), g('not recorded', 2, 0.8, 2, 0.8)], chosen: [g('chosen by the AI model', 4, -0.5, 2, -0.5)], exit: [g('sold to keep part of a gain', 2, 0.1, 1, 0.1), g('sold when the signal turned', 1, 0.6, 1, 0.6), g("sold early by the AI model's review", 1, -2.8, 0, -2.8)] } };
      await window.practiceAutopilot.refresh(true); await wait(500); const d = q('#ap-breakdown'); d.open = true; out('breakdown: ' + d.textContent.replace(/\\s+/g, ' ').trim().slice(0, 400)); d.scrollIntoView({ block: 'start' });
    }
    if (step === 'locked') {
      window.LOCKED = true; await window.practiceAutopilot.reload(); await wait(600); if (window.dashboardTabs) window.dashboardTabs.show('autopilot'); await wait(200);
      out('without a paid plan: tab "' + (q('[data-dash-tab="autopilot"]') || {}).textContent + '" | ' + q('#practice-autopilot').textContent.replace(/\\s+/g, ' ').trim().slice(0, 520));
      out('  the button: "' + q('#ap-upgrade').textContent + '" -> ' + q('#ap-upgrade').getAttribute('href') + ' | switch or run button on the page: ' + !!(q('#ap-enabled') || q('#ap-run')));
      q('#practice-autopilot').scrollIntoView({ block: 'start' });
    }
    if (step.indexOf('mobile') === 0) {
      // How it sits at this window's width (run the page inside a 390px frame for a phone: mobile_frame.py). Lists what sticks
      // out past the edge of the screen, and what has to be scrolled sideways inside its own box. "mobile:practice",
      // "mobile:activity" or "mobile:settings" leaves that view on show for a screenshot.
      const look = (name) => { const W = window.innerWidth, bad = [], inner = [];
        document.querySelectorAll('.dash-tabs, .dash-tabs *, #practice-portfolio *, #practice-autopilot *').forEach(x => {
          if (!x.offsetParent && x.tagName !== 'BODY') return; const r = x.getBoundingClientRect(); if (!r.width) return;
          const o = getComputedStyle(x).overflowX; const tag = (x.id ? '#' + x.id : x.className && typeof x.className === 'string' ? '.' + x.className.split(' ')[0] : x.tagName.toLowerCase());
          if ((o === 'auto' || o === 'scroll') && x.scrollWidth > x.clientWidth + 1) inner.push(tag + ' (' + x.scrollWidth + 'px of content in ' + x.clientWidth + 'px)');
          if (r.right > W + 1 || r.left < -1) { let p = x.parentElement, held = false; while (p && p !== document.body) { const po = getComputedStyle(p).overflowX; if (po === 'auto' || po === 'scroll' || po === 'hidden') { held = true; break; } p = p.parentElement; } if (!held) bad.push(tag + ' to ' + Math.round(r.right) + 'px'); } });
        out('mobile ' + name + ': screen ' + W + 'px, page ' + document.documentElement.scrollWidth + 'px wide | sticking out past the screen: ' + ([...new Set(bad)].slice(0, 10).join(', ') || 'nothing') + ' | scrolls sideways inside its own box: ' + ([...new Set(inner)].slice(0, 8).join(', ') || 'nothing')); };
      const want = step.split(':')[1] || 'all';
      window.dashboardTabs.show('practice'); await wait(300); if (want === 'all' || want === 'practice') look('practice portfolio');
      if (want !== 'practice') { window.dashboardTabs.show('autopilot'); await wait(300); q('[data-ap-part="activity"]').click(); await wait(200); document.querySelectorAll('#practice-autopilot details').forEach(d => { d.open = true; }); await wait(200);
        if (want === 'all' || want === 'activity') look('autopilot, Activity');
        if (want !== 'activity') { q('[data-ap-part="settings"]').click(); await wait(300); look('autopilot, Settings'); } }
      window.scrollTo(0, 0);
    }
    if (step === 'off') { q('#ap-enabled').click(); await wait(700); out('switched the autopilot off: ' + cellText('WEMIX')); }
    if (step === 'open') { document.querySelectorAll('#practice-autopilot details').forEach(d => { d.open = true; }); const s = q('#pp-sold'); if (s) s.open = true; out('unfolded the details'); }
  }
  out('broken values on the page: ' + ((q('#practice-portfolio').innerHTML + q('#practice-autopilot').innerHTML).match(/undefined|NaN|\\[object|Infinity/g) || []).length);
  if (window.parent !== window) window.parent.postMessage({ out: document.getElementById('out').textContent, height: document.documentElement.scrollHeight }, '*');   // inside a phone-width frame (mobile_frame.py)
  document.title = 'done';
})().catch(e => { out('ERROR ' + e.message); if (window.parent !== window) window.parent.postMessage({ out: document.getElementById('out').textContent, height: 2000 }, '*'); });
</script></body></html>''' % (theme, json.dumps({'holdings': {'min': 2, 'max': 50, 'buysEach': 3}, 'screeners': {'3-8': {'name': 'Dow 30', 'kind': 'stock', 'group': 'US markets'}, '3-100': {'name': 'S&P 100', 'kind': 'stock', 'group': 'US markets'}, '3-7': {'name': 'NASDAQ 100', 'kind': 'stock', 'group': 'US markets'}, '3-3': {'name': 'S&P 500', 'kind': 'stock', 'group': 'US markets'}, '3-2': {'name': 'S&P 400+600 (mid and small)', 'kind': 'stock', 'group': 'US markets'}, '3-4': {'name': 'S&P 1500', 'kind': 'stock', 'group': 'US markets'}, '3-5': {'name': 'Russell 1000', 'kind': 'stock', 'group': 'US markets'}, '3-6': {'name': 'Russell 2000 (small)', 'kind': 'stock', 'group': 'US markets'}, '5-ftse100': {'name': 'UK FTSE 100', 'kind': 'stock', 'group': 'Europe markets'}, '5-dax40': {'name': 'Germany DAX 40', 'kind': 'stock', 'group': 'Europe markets'}, '5-cac40': {'name': 'France CAC 40', 'kind': 'stock', 'group': 'Europe markets'}, '5-smi': {'name': 'Switzerland SMI', 'kind': 'stock', 'group': 'Europe markets'}, '5-aex': {'name': 'Netherlands AEX', 'kind': 'stock', 'group': 'Europe markets'}, '5-ftsemib': {'name': 'Italy FTSE MIB', 'kind': 'stock', 'group': 'Europe markets'}, '5-ibex35': {'name': 'Spain IBEX 35', 'kind': 'stock', 'group': 'Europe markets'}, '4-50': {'name': 'ASX 50', 'kind': 'stock', 'group': 'Asia-Pacific markets'}, '4-100': {'name': 'ASX 100', 'kind': 'stock', 'group': 'Asia-Pacific markets'}, '4-200': {'name': 'ASX 200', 'kind': 'stock', 'group': 'Asia-Pacific markets'}, '4-300': {'name': 'ASX 300', 'kind': 'stock', 'group': 'Asia-Pacific markets'}, '5-nikkei225': {'name': 'Japan Nikkei 225', 'kind': 'stock', 'group': 'Asia-Pacific markets'}, '5-hangseng': {'name': 'Hong Kong Hang Seng', 'kind': 'stock', 'group': 'Asia-Pacific markets'}, '5-sensex': {'name': 'India Sensex', 'kind': 'stock', 'group': 'Asia-Pacific markets'}, '5-kospi200': {'name': 'South Korea KOSPI 200', 'kind': 'stock', 'group': 'Asia-Pacific markets'}, '5-sti': {'name': 'Singapore STI', 'kind': 'stock', 'group': 'Asia-Pacific markets'}, '5-tsx60': {'name': 'Canada TSX 60', 'kind': 'stock', 'group': 'Americas markets'}, '5-bovespa': {'name': 'Brazil Bovespa', 'kind': 'stock', 'group': 'Americas markets'}, '7-1': {'name': 'Crypto (top coins)', 'kind': 'crypto', 'group': 'Coins'}}, 'groups': ['US markets', 'Europe markets', 'Asia-Pacific markets', 'Americas markets', 'Coins'],
    'everyHours': [0.5, 1, 3, 6, 12, 24], 'holdDays': [h / 24 for h in (0.5, 1, 3, 6, 12, 24, 48, 120, 240, 480, 1440)],
    'pace': {'1': dict(periodDays=10, everyHours=24, maxHoldDays=20), '2': dict(periodDays=7, everyHours=12, maxHoldDays=10), '3': dict(periodDays=5, everyHours=6, maxHoldDays=5), '4': dict(periodDays=2, everyHours=3, maxHoldDays=2), '5': dict(periodDays=1, everyHours=1, maxHoldDays=1)},
    'risk': {str(k): dict(name=n, positions=p, top=t, stop=s, take=g, crypto=c, trail=0.5, max_rsi=r) for k, (n, p, t, s, g, c, r) in {1: ('Cautious', 12, 5, -5, 8, 0, 68), 2: ('Careful', 10, 8, -7, 12, 0, 72), 3: ('Balanced', 8, 10, -10, 18, 0.25, 76), 4: ('Bold', 6, 15, -14, 28, 0.5, 82), 5: ('Adventurous', 4, 20, -20, 45, 1, 101)}.items()}}),
    open(pp).read().replace('</script>', '<\\/script>'), open(ap).read().replace('</script>', '<\\/script>'), json.dumps([x for x in steps.split(',') if x]))
one_section = '<div class="history-section"><h2 style="color:var(--text-primary);margin-top:0">Practice portfolio</h2><div id="practice-portfolio"></div><div id="practice-autopilot"></div></div>'
tabbed = (STYLE + BAR + '<div data-dash-panel="reports"><div class="history-section"><h2 style="color:var(--text-primary);margin-top:0">Report History</h2><p style="color:var(--text-secondary)">(the reports would be here)</p></div></div>'
          + '<div data-dash-panel="practice" hidden><div class="history-section"><div class="pp-headrow"><h2 style="color:var(--text-primary);margin-top:0">Practice Portfolio</h2><div id="pp-tools"></div></div><div id="practice-portfolio"></div></div></div>'
          + '<div data-dash-panel="autopilot" hidden><div class="history-section"><div id="practice-autopilot"></div></div></div>' + SCRIPT)
open(out, 'w').write(page.replace('TABS_GO_HERE', tabbed if BAR else one_section))
