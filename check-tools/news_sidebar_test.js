// Does the "Market News" list on the home page show the newest articles?
//
//   node check-tools/news_sidebar_test.js [news.js]        (default: ../website/news.js)
//
// Runs the file's own display code (renderNewsItems) against a stand-in page and compares what it
// puts on the page with the newest general article and the four newest stock articles by timestamp.
// Read-only. Until 13 Oct 2026 the list was not sorted at all: the display code sorted on the date
// text ("Mon, October 12, 2026 at 9:49 PM UTC 4 min read"), which a browser cannot read as a date,
// so the page showed whatever the daily run happened to write first, often days old.
const fs = require('fs'), path = require('path'), vm = require('vm');

const file = process.argv[2] || path.join(__dirname, '..', '..', 'website', 'news.js');
const source = fs.readFileSync(file, 'utf8');

const box = { innerHTML: '' };
const page = {
    readyState: 'complete',
    getElementById: id => (id === 'news-items' ? box : null),
    addEventListener: () => {}
};
const context = { document: page, window: {}, console };
vm.createContext(context);
vm.runInContext(source + '\n;globalThis.__items = newsItems;', context);

const items = context.__items;
const shown = [...box.innerHTML.matchAll(/data-timestamp="([^"]*)"/g)].map(m => m[1]);
const stamp = item => Date.parse(item.timestamp || '');
const newest = list => [...list].sort((a, b) => stamp(b) - stamp(a));
const general = newest(items.filter(item => !item.stockSymbol));
const stock = newest(items.filter(item => item.stockSymbol));
const wanted = [...general.slice(0, 1), ...stock.slice(0, 4)].map(item => item.timestamp);

let failed = 0;
const check = (name, ok, detail) => {
    console.log((ok ? 'PASS ' : 'FAIL ') + name + (ok || !detail ? '' : '\n     ' + detail));
    if (!ok) failed++;
};

check('the file has items (' + items.length + ')', items.length > 0);
check('every item has a timestamp a browser can read',
    items.every(item => !isNaN(stamp(item))),
    items.filter(item => isNaN(stamp(item))).slice(0, 3).map(item => item.id + ': "' + item.timestamp + '"').join(', '));
check('the page shows ' + wanted.length + ' items', shown.length === wanted.length, 'it shows ' + shown.length);
// Compared as times, so that two articles of the same minute in either order still pass.
check('they are the newest general article and the newest stock articles',
    shown.length === wanted.length && shown.every((t, i) => Date.parse(t) === Date.parse(wanted[i])),
    'shown:  ' + shown.join('  ') + '\n     newest: ' + wanted.join('  '));

console.log(failed ? failed + ' check(s) failed' : 'all checks passed');
process.exit(failed ? 1 : 0);
