"""Builds a stand-alone test page: the real panel script, the site's stylesheet, and a stand-in server in the page.
After loading it performs clicks like a person would and writes what happened into the page."""
import sys, json
script_path, out, theme, steps = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
js = open(script_path, encoding='utf-8').read()
G = lambda label, n, avg, vs, beat: dict(label=label, n=n, avg=avg, vs=vs, beat=beat, judged=n, up=beat)
html = '''<!DOCTYPE html><html data-theme="%s"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://stockiq.tech/styles.css">
<style>body{padding:20px;background:var(--bg-primary);margin:0} .history-section{background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;padding:20px;margin-bottom:20px} #out{font:12px monospace;white-space:pre-wrap;color:var(--text-primary)}</style></head><body>
<div class="history-section"><div id="practice-autopilot"></div></div><pre id="out"></pre>
<script>
localStorage.setItem('userId', 'dave@dewit.com.au');
const OPTIONS = %s;
let stored = { settings: { enabled: false, risk: 3, budgetUsd: 10000, periodDays: 10, everyHours: 24, maxHoldDays: 20, screeners: ['3-100'] }, state: {}, log: [], scorecard: { n: 0, groups: {} }, lessons: null, resting: {}, recent: [], minSample: 8 };
const calls = [];
window.fetch = async (url, opts) => {
  const b = JSON.parse(opts.body); calls.push(b.action);
  await new Promise(r => setTimeout(r, 150));
  if (b.action === 'save') { stored.settings = b.settings; stored.log.push({ t: new Date().toISOString(), type: 'note', symbol: '', usd: 0, text: 'Autopilot on: Balanced level, $10,000 over 10 days, checking every 24 hours.' }); }
  if (b.action === 'run') { stored.state.lastRun = new Date().toISOString(); stored.log.push({ t: new Date().toISOString(), type: 'buy', symbol: 'COP', usd: 1250, text: 'Rank 1, RSI 52, up 3%% in 7 days on 1.4x volume (S&P 100 rank 1, score +3.4; chosen by the AI model)' });
    if (window.FULL) Object.assign(stored, window.FULL); }
  return { ok: true, status: 200, json: async () => Object.assign({ success: true, allowed: true, options: OPTIONS, summary: { bought: 1, sold: 0 } }, stored) };
};
window.FULL = %s;
window.practicePortfolio = { reload() { calls.push('portfolio-reload'); } };
</script>
<script>%s</script>
<script>
const out = (m) => { document.getElementById('out').textContent += m + '\\n'; };
const wait = (ms) => new Promise(r => setTimeout(r, ms));
const q = (s) => document.querySelector(s);
const state = () => 'status="' + (q('#ap-status') ? q('#ap-status').textContent.slice(0, 70) : '?') + '" notice="' + (q('#ap-notice') ? q('#ap-notice').textContent.slice(0, 90) : '?') + '" calls=' + JSON.stringify(calls);
(async () => {
  await wait(600); out('loaded: ' + state());
  const steps = %s;
  for (const step of steps) {
    if (step === 'tick-on') { q('#ap-enabled').click(); await wait(500); out('ticked Switched on: ' + state()); }
    if (step === 'save') { q('[data-ap="save"]').click(); await wait(600); out('clicked Save: ' + state()); }
    if (step === 'run') { const b = q('[data-ap="run"]'); out('Check in now disabled? ' + b.disabled); b.click(); await wait(700); out('clicked Check in now: ' + state()); }
    if (step === 'btn') { const sv = q('[data-ap="save"]'), rn = q('[data-ap="run"]'); out('buttons: save="' + sv.textContent + '" disabled=' + sv.disabled + ' | run disabled=' + rn.disabled + ' title="' + rn.title + '" | switch text=' + q('#ap-switch-text').textContent + ' | dirty="' + q('#ap-dirty').textContent + '"'); }
    if (step === 'budget') { const b = q('#ap-budget'); b.focus(); b.value = '20000'; b.dispatchEvent(new Event('input', { bubbles: true })); await wait(300); out('typed budget 20000: focus kept=' + (document.activeElement === b) + ' plan="' + q('#ap-plan').textContent.slice(0, 60) + '"'); }
    if (step === 'level') { q('[data-ap-level="1"]').click(); await wait(300); out('clicked the word Cautious: slider=' + q('#ap-risk').value + ' text="' + q('#ap-risk-text').textContent.slice(0, 40) + '"'); }
    if (step === 'tick-asx') { q('[data-ap-screener="4-200"]').click(); await wait(500); out('ticked ASX 200: ' + state() + ' saveButtonBlue=' + q('[data-ap="save"]').classList.contains('primary')); }
    if (step === 'slide') { const r = q('#ap-risk'); r.value = '5'; r.dispatchEvent(new Event('input', { bubbles: true })); r.dispatchEvent(new Event('change', { bubbles: true })); await wait(500); out('moved risk to 5: text="' + q('#ap-risk-text').textContent.slice(0, 60) + '" ' + state()); }
  }
  document.title = 'done';
})().catch(e => out('ERROR ' + e.message));
</script></body></html>''' % (theme, json.dumps({'screeners': {'3-8': {'name': 'Dow 30', 'kind': 'stock', 'group': 'US shares'}, '3-100': {'name': 'S&P 100', 'kind': 'stock', 'group': 'US shares'}, '3-7': {'name': 'NASDAQ 100', 'kind': 'stock', 'group': 'US shares'}, '3-3': {'name': 'S&P 500', 'kind': 'stock', 'group': 'US shares'}, '3-2': {'name': 'S&P 400+600 (mid and small)', 'kind': 'stock', 'group': 'US shares'}, '3-4': {'name': 'S&P 1500', 'kind': 'stock', 'group': 'US shares'}, '3-5': {'name': 'Russell 1000', 'kind': 'stock', 'group': 'US shares'}, '3-6': {'name': 'Russell 2000 (small)', 'kind': 'stock', 'group': 'US shares'}, '4-50': {'name': 'ASX 50', 'kind': 'stock', 'group': 'Australian shares'}, '4-100': {'name': 'ASX 100', 'kind': 'stock', 'group': 'Australian shares'}, '4-200': {'name': 'ASX 200', 'kind': 'stock', 'group': 'Australian shares'}, '4-300': {'name': 'ASX 300', 'kind': 'stock', 'group': 'Australian shares'}, '5-ftse100': {'name': 'UK FTSE 100', 'kind': 'stock', 'group': 'UK shares'}, '5-nikkei225': {'name': 'Japan Nikkei 225', 'kind': 'stock', 'group': 'Japanese shares'}, '7-1': {'name': 'Crypto (top coins)', 'kind': 'crypto', 'group': 'Coins'}},
      'everyHours': [3, 6, 12, 24], 'holdDays': [2, 5, 10, 20, 60],
      'risk': {str(k): dict(name=n, positions=p, top=t, stop=s, take=tk, crypto=c) for k, n, p, t, s, tk, c in [(1, 'Cautious', 12, 5, -5, 8, 0), (2, 'Careful', 10, 8, -7, 12, 0), (3, 'Balanced', 8, 10, -10, 18, 0.25), (4, 'Bold', 6, 15, -14, 28, 0.5), (5, 'Adventurous', 4, 20, -20, 45, 1)]}}),
     json.dumps({'scorecard': dict(G('all', 12, 1.84, -0.62, 5), groups={'screener': [G('S&P 100', 9, 0.9, -1.7, 3), G('ASX 200', 3, 4.6, 2.6, 2)], 'rank': [G('rank 1 to 3', 7, 2.4, 0.3, 4), G('rank 4 to 10', 5, 1.1, -1.9, 1)], 'rsi': [G('RSI 45 to 60', 12, 1.84, -0.62, 5)], 'chosen': [G('chosen by the AI model', 10, 2.0, -0.4, 5), G('chosen by rank', 2, 1.0, -1.7, 0)], 'exit': [G('sold at the loss limit', 4, -10.5, -11, 0), G('sold at the gain mark', 5, 18.4, 14.0, 5)]}),
                 'lessons': {'at': '2026-10-20T15:40:00Z', 'n': 10, 'items': ['Buys ranked 1 to 3 were ahead of the market in 4 of 7 trades; ranks 4 to 10 in 1 of 5.', 'Too few ASX trades (3) to compare with the S&P 100.']}, 'resting': {'3-100': '2026-10-26T15:40:00Z'}}) if 'full' in steps else 'null',
     js, json.dumps([x for x in steps.split(',') if x and x != 'full']))
open(out, 'w', encoding='utf-8').write(html)
