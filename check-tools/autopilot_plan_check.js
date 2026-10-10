// Used by autopilot_plan_check.py: prints what buildUp() in the panel script works out for a list of settings.
//   node autopilot_plan_check.js <practice-autopilot.js> <cases.json>
const fs = require('fs'); const src = fs.readFileSync(process.argv[2], 'utf8');
const fn = src.slice(src.indexOf('    function buildUp(d, r, limit) {'), src.indexOf('    // What the chosen settings mean in practice')); eval(fn.replace('function buildUp', 'globalThis.buildUp = function'));
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')); console.log(JSON.stringify(cases.map(c => buildUp(c, { positions: c.positions }, c.limit))));
