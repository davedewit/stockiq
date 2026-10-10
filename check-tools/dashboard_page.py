"""Writes a test page holding the two real dashboard scripts for the practice portfolio and its autopilot, the site's
stylesheet and a stand-in server (nothing live is called: every request is answered inside the page).
It starts with two holdings bought by hand and one by the autopilot, then performs the steps and prints what happened.

   python3 check-tools/dashboard_page.py <practice-portfolio.js> <practice-autopilot.js> <out.html> <light|dark> "<steps>"
   steps: type (types in the buy row), sale (the autopilot sells in the background, then the page refreshes itself),
          trial (a trial of its own rules starts), off (the autopilot is switched off), open (unfolds the details),
          preset (presses the "Quick coin trading" set-up), sellall (presses "Sell everything it holds" and says yes),
          limits (types your own loss limit), split (prints the line that says whose result is whose),
          cards (prints the summary cards and every account value shown since the page opened: there should be one),
          pace (hands the three pace settings to the risk level, moves the slider, sets one by hand, moves it again),
          listswitch (switches the list to "buys and sells only" and reloads the page to see that it is remembered)
Open the page with headless Chrome: --dump-dom for the printed results, --screenshot for the look (site-overview.md, section 12)."""
import json, sys
pp, ap, out, theme, steps = sys.argv[1:6]
page = '''<!doctype html><html data-theme="%s"><head><meta charset="utf-8"><title>running</title>
<link rel="stylesheet" href="https://stockiq.tech/styles.css">
<style>body{padding:20px;background:var(--bg-primary);margin:0} .history-section{background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;padding:20px;margin-bottom:20px} #out{font:12px monospace;white-space:pre-wrap;color:var(--text-primary)}</style></head><body>
<div class="history-section"><h2 style="color:var(--text-primary);margin-top:0">Practice portfolio</h2><div id="practice-portfolio"></div><div id="practice-autopilot"></div></div><pre id="out"></pre>
<script>
localStorage.setItem('userId', 'owner@example.com');
// every account value the page shows, in order: a figure that flashes up before the prices are in would be listed here
window.SEEN = []; new MutationObserver(() => { const m = document.getElementById('practice-portfolio').textContent.match(/Account value\\s*(\\$[\\d,.]+)/); if (m && SEEN[SEEN.length - 1] !== m[1]) SEEN.push(m[1]); }).observe(document.getElementById('practice-portfolio'), { childList: true, subtree: true });
const iso = (h) => new Date(Date.now() + h * 3600000).toISOString().slice(0, 19) + 'Z';
const PRICES = { 'BTC-USD': 83500, 'WEMIX-USD': 0.1946, 'SPY': 700 };
let portfolio = { v: 1, startingCash: 100000, cash: 15899.07, createdAt: iso(-4), closed: [], holdings: [
  { id: 'm1', symbol: 'BTC-USD', label: 'BTC-USD', name: 'Bitcoin USD', currency: 'USD', qty: 1, buyPrice: 82750.93, buyFx: 1, costUsd: 82750.93, boughtAt: iso(-3.1), spyAtBuy: 700, note: 'fun' },
  { id: 'm2', symbol: 'BTC-USD', label: 'BTC-USD', name: 'Bitcoin USD', currency: 'USD', qty: 100 / 82734.62, buyPrice: 82734.62, buyFx: 1, costUsd: 100, boughtAt: iso(-3), spyAtBuy: 700, note: '' },
  { id: 'a1', symbol: 'WEMIX-USD', label: 'WEMIX-USD', name: 'WEMIX USD', currency: 'USD', qty: 1250 / 0.1868991, buyPrice: 0.1868991, buyFx: 1, costUsd: 1250, boughtAt: iso(-2.9), spyAtBuy: 700, note: 'AI: rank 1, RSI 14, down 3.8%% in 7 days on 1.0x volume', by: 'ai', screener: '7-1' }] };
let version = 3;
const OPTIONS = %s;
let auto = { settings: { enabled: true, risk: 3, budgetUsd: 10000, periodDays: 10, everyHours: 0.5, maxHoldDays: 0.25, screeners: ['7-1'], aiSell: true, selfTune: true, emails: true, stopPct: null, takePct: null, auto: [] }, coinShare: 1, state: { lastRun: iso(-0.1) }, minSample: 8, practiceCash: 100000, lessons: null, resting: {}, recent: [],
  scorecard: { n: 0, groups: {} }, rules: { name: 'Balanced', stop: -10, take: 18, trail: 0.5, top: 10, max_rsi: 76, arm: 9, changed: {}, yours: [], level: { stop: -10, take: 18 } }, realizedUsd: 7.91,
  tune: { trial: null, past: [], nextReviewIn: 20, batch: 20, group: 10, finished: 0 }, month: { last30: { n: 0, up: 0, usd: 0, pct: 0 }, before30: { n: 0, up: 0, usd: 0, pct: 0 } },
  nextCheck: { at: iso(0.4), markets: ['coin'] }, holding: { count: 1, investedUsd: 1250 },
  plans: [{ id: 'a1', label: 'WEMIX-USD', boughtAt: iso(-2.9), sellBy: iso(3.1), auto: true, stop: -10, take: 18, arm: 1, trail: 0.5, peak: 6.2, floor: 3.5, view: { t: iso(-0.1), sell: false, text: 'Up 4%% and still climbing', larger: true } }],
  log: [{ t: iso(-2.9), type: 'buy', symbol: 'WEMIX-USD', usd: 1250, text: 'rank 1, RSI 14, down 3.8%% in 7 days on 1.0x volume (Crypto (top coins) rank 1, score +4.0; chosen by the AI model)', detail: ['The plan for it: sell 6 hours after buying at the latest; sooner at -10%% or +18%%; once it has been up 9%%, sell if it gives back 50%% of its best gain; sell if its screener signal turns negative or it slips far down the ranking.'] },
        { t: iso(-0.1), first: iso(-2.4), n: 5, key: 'pace', type: 'note', symbol: '', usd: 0, text: 'Checked in. Nothing to spend yet: $1,250 of the $10,000 budget is invested. The rest is released in steps over the 10 days set under "Build up to it over"; the next $1,250 in about 21 hours.' }] };
const calls = [];
window.fetch = async (url, opts) => {
  const u = String(url); await new Promise(r => setTimeout(r, 60));
  const json = (o) => ({ ok: true, status: 200, json: async () => o });
  if (u.includes('?symbol=')) { const sym = decodeURIComponent(u.split('?symbol=')[1]); const p = PRICES[sym]; if (!p) return { ok: false, status: 500, json: async () => ({}) }; return json({ chart: { result: [{ meta: { regularMarketPrice: p, currency: 'USD', longName: sym } }] } }); }
  const b = JSON.parse(opts.body); calls.push((b.settings ? 'autopilot-' : b.portfolio ? 'portfolio-' : '') + b.action);
  if (b.action === 'get' && !('settings' in b) && u.includes('5c7pt7q')) return json({ success: true, portfolio, version });
  if (b.action === 'save' && b.portfolio) { portfolio = b.portfolio; version++; return json({ success: true, version }); }
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
    if (step === 'preset') { q('[data-ap-preset="coins"]').click(); await wait(900);
      out('pressed "Quick coin trading": level=' + q('#ap-risk').value + ' days=' + q('#ap-period').value + ' checks=' + q('#ap-every').selectedOptions[0].textContent + ' keeps=' + q('#ap-hold').selectedOptions[0].textContent + ' ticked=' + Array.from(document.querySelectorAll('[data-ap-screener]')).filter(c => c.checked).map(c => c.getAttribute('data-ap-screener')).join(',') + ' | saved: ' + JSON.stringify(auto.settings));
      out('  it says: ' + q('#ap-plan').textContent + ' || notice: ' + q('#ap-notice').textContent); }
    if (step === 'sellall') { window.confirm = (m) => { out('asked: ' + m.split(String.fromCharCode(10)).filter(Boolean).join(' / ')); return true; }; const b = q('#ap-sellall'); out('button: "' + b.textContent + '" disabled=' + b.disabled); b.click(); await wait(1200);
      out('  after: notice="' + q('#ap-notice').textContent + '" | button "' + q('#ap-sellall').textContent + '" disabled=' + q('#ap-sellall').disabled + ' | WEMIX still held in the table: ' + (cellText('WEMIX') !== '(no row)' && !!Array.from(document.querySelectorAll('#practice-portfolio button[data-pp="sell"]')).find(x => x.closest('tr').textContent.includes('WEMIX'))) + ' | calls: ' + calls.slice(-3).join(', ')); }
    if (step === 'limits') { const a = q('#ap-stop'); out('your own limits: fields empty, greyed hints "' + a.placeholder + '" and "' + q('#ap-take').placeholder + '"'); a.focus(); a.value = '6'; a.dispatchEvent(new Event('input', { bubbles: true })); await wait(200);
      out('  typed 6 as the loss limit: risk text now "' + q('#ap-risk-text').textContent.slice(0, 120) + '" | focus kept=' + (document.activeElement === a)); await wait(1500); out('  saved: stopPct=' + auto.settings.stopPct + ' takePct=' + auto.settings.takePct + ' | saved line "' + q('#ap-saved').textContent + '"'); }
    if (step === 'split') out('whose result is whose: ' + (Array.from(document.querySelectorAll('#practice-portfolio div')).map(x => x.textContent.replace(/\\s+/g, ' ').trim()).find(t => t.startsWith('Of the ')) || '(no line)'));
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
    if (step === 'off') { q('#ap-enabled').click(); await wait(700); out('switched the autopilot off: ' + cellText('WEMIX')); }
    if (step === 'open') { document.querySelectorAll('#practice-autopilot details').forEach(d => { d.open = true; }); const s = q('#pp-sold'); if (s) s.open = true; out('unfolded the details'); }
  }
  out('broken values on the page: ' + ((q('#practice-portfolio').innerHTML + q('#practice-autopilot').innerHTML).match(/undefined|NaN|\\[object|Infinity/g) || []).length);
  document.title = 'done';
})().catch(e => out('ERROR ' + e.message));
</script></body></html>''' % (theme, json.dumps({'screeners': {'3-100': {'name': 'S&P 100', 'kind': 'stock', 'group': 'US shares'}, '4-200': {'name': 'ASX 200', 'kind': 'stock', 'group': 'Australian shares'}, '7-1': {'name': 'Crypto (top coins)', 'kind': 'crypto', 'group': 'Coins'}},
    'everyHours': [0.5, 1, 3, 6, 12, 24], 'holdDays': [h / 24 for h in (0.5, 1, 3, 6, 12, 24, 48, 120, 240, 480, 1440)],
    'pace': {'1': dict(periodDays=10, everyHours=24, maxHoldDays=20), '2': dict(periodDays=7, everyHours=12, maxHoldDays=10), '3': dict(periodDays=5, everyHours=6, maxHoldDays=5), '4': dict(periodDays=2, everyHours=3, maxHoldDays=2), '5': dict(periodDays=1, everyHours=1, maxHoldDays=1)},
    'risk': {str(k): dict(name=n, positions=p, top=t, stop=s, take=g, crypto=c, trail=0.5, max_rsi=r) for k, (n, p, t, s, g, c, r) in {1: ('Cautious', 12, 5, -5, 8, 0, 68), 2: ('Careful', 10, 8, -7, 12, 0, 72), 3: ('Balanced', 8, 10, -10, 18, 0.25, 76), 4: ('Bold', 6, 15, -14, 28, 0.5, 82), 5: ('Adventurous', 4, 20, -20, 45, 1, 101)}.items()}}),
    open(pp).read().replace('</script>', '<\\/script>'), open(ap).read().replace('</script>', '<\\/script>'), json.dumps([x for x in steps.split(',') if x]))
open(out, 'w').write(page)
