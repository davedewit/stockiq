// Every index the site compares with has daily prices at the price source (23 Oct 2026: the S&P 1000, the S&P 1500, the KOSPI 200
// and the CSI 300 had only today's price, so the dashboard's Top 10 tracker showed no index for them and the practice portfolio's
// "By market" list could not compare with them). Reads HOME_INDEX from practice-portfolio.js and TOP10_BENCHMARKS from dashboard.html.
//   node check-tools/index_check.js [practice-portfolio.js] [dashboard.html]      (read-only: one GET a symbol to the price function)
const vm = require('vm'), fs = require('fs'), path = require('path');
const WEB = path.join(__dirname, '..', '..', 'website');
const pp = process.argv[2] || path.join(WEB, 'practice-portfolio.js'), dash = process.argv[3] || path.join(WEB, 'dashboard.html');
const m = { exports: {} }; vm.runInNewContext(fs.readFileSync(pp, 'utf8'), { module: m, console });
const syms = new Set(Object.values(m.exports.HOME_INDEX || {}).map(x => x[0]));
const block = (fs.readFileSync(dash, 'utf8').match(/const TOP10_BENCHMARKS = \[([\s\S]*?)\];/) || ['', ''])[1];
(block.match(/,\s*'([^']+)'\s*,\s*'[^']*'\]/g) || []).forEach(x => syms.add(x.match(/'([^']+)'/)[1]));
const URL = 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/?symbol=';
(async () => {
  let ok = true;
  for (const s of [...syms].sort()) {
    let n = 0;
    try { const r = (await (await fetch(URL + encodeURIComponent(s))).json()).chart.result[0]; n = (r.indicators.quote[0].close || []).filter(c => c > 0).length; } catch (e) {}
    const good = n >= 10; ok = ok && good;
    console.log(`${good ? 'PASS' : 'FAIL'} ${s}: ${n} daily prices in the last month${good ? '' : ' (needs 10 or more to compare with)'}`);
  }
  console.log(ok ? 'ALL PASS' : 'SOME FAILED');
})();
