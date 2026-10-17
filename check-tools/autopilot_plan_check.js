// Used by autopilot_plan_check.py: prints what buildUp() in the panel script works out for a list of settings.
//   node autopilot_plan_check.js <practice-autopilot.js> <cases.json>
const fs = require('fs'); const src = fs.readFileSync(process.argv[2], 'utf8');
// the two small sums both parts lean on since 12 Oct 2026 (the user's own number of holdings): taken from the panel script too, where it has them
for (const m of [src.match(/^    function positionsOf\(d\) \{.*\}$/m), src.match(/^    const buysPerCheck = .*;$/m)]) if (m) eval(m[0].trim().replace('function positionsOf', 'globalThis.positionsOf = function').replace('const buysPerCheck', 'globalThis.buysPerCheck'));
if (typeof buysPerCheck === 'undefined') globalThis.buysPerCheck = () => 3;
const fn = src.slice(src.indexOf('    function buildUp(d, r, limit) {'), src.indexOf('    // What the chosen settings mean in practice')); eval(fn.replace('function buildUp', 'globalThis.buildUp = function'));
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
if (process.argv[4] === 'slots') {
  globalThis.data = { options: cases.options };
  const part = src.slice(src.indexOf('    // MARKET_SPLIT_START'), src.indexOf('    // MARKET_SPLIT_END'));
  eval(part.replace('function marketSplit', 'globalThis.marketSplit = function').replace('function marketSlots', 'globalThis.marketSlots = function'));
  console.log(JSON.stringify(cases.cases.map(c => { data.resting = c.resting || {}; return marketSlots(c); })));
} else console.log(JSON.stringify(cases.map(c => buildUp(c, { positions: c.positions }, c.limit))));
// With "slots" as a fourth argument the cases are {options, cases: [{risk, screeners, shares}]} instead, and what is printed is
// marketSlots() for each: how the panel spreads the budget over the markets ticked (the Lambda's market_slots()).
