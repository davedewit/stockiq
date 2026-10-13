"""Builds screeners.js and the shortened analysis-functions.js from the analysis script as it is live.
Nothing is typed again: every list and every worker address is copied out of the 14 branches of runAnalysis as text."""
import re, sys
src = open('/Users/dave/VSCODE/website/analysis-functions.js', encoding='utf-8').read()
lines = src.split('\n')

# the 14 branches, in the order they stand in runAnalysis: key, the test as written, what the branch is called
ORDER = [("3-3", "option === 3 && subOption === '3'", 'S&P 500'), ("3-2", "option === 3 && subOption === '2'", 'S&P 400 + 600'),
         ("3-100", "option === 3 && subOption === '100'", 'S&P 100'), ("3-4", "option === 3 && subOption === '4'", 'S&P 1500'),
         ("3-5", "option === 3 && subOption === '5'", 'Russell 1000'), ("3-7", "option === 3 && subOption === '7'", 'NASDAQ 100'),
         ("3-8", "option === 3 && subOption === '8'", 'Dow Jones 30'), ("3-6", "option === 3 && subOption === '6'", 'Russell 2000'),
         ("5-50", "option === 5 && subOption === '50'", 'ASX 50'), ("5-100", "option === 5 && subOption === '100'", 'ASX 100'),
         ("5-200", "option === 5 && subOption === '200'", 'ASX 200'), ("5-300", "option === 5 && subOption === '300'", 'ASX 300'),
         ("5-nikkei225", "option === 5 && subOption === 'nikkei225'", 'Japan Nikkei 225'), ("4-ftse100", "option === 4 && subOption === 'ftse100'", 'UK FTSE 100')]
starts = []
for key, test, name in ORDER:
    hits = [i for i, l in enumerate(lines) if l == f"        }} else if ({test}) {{"]
    assert hits, test
    starts.append(hits[0])          # the first one: a second (5,'50') further down can never be reached
assert starts == sorted(starts), starts
end = [i for i, l in enumerate(lines) if l == "        } else if (option === 5 && subOption === '50') {"][1]     # the unreachable one: where the 14 end
assert end > starts[-1]

def literal(text, start):
    """the [ ... ] that opens at text[start]"""
    assert text[start] == '[', text[start:start + 20]
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '[': depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0: return text[start:i + 1]
    raise ValueError('no end')

entries, ftse_format = [], None
for n, (key, test, name) in enumerate(ORDER):
    blk = '\n'.join(lines[starts[n]:(starts[n + 1] if n + 1 < len(ORDER) else end)])
    m = re.search(r'const (\w+Universe) = ', blk); assert m, key
    rest = blk[m.end():]
    lst = None if rest.startswith('null') else literal(blk, m.end())
    u = blk.index('const allWorkerUrls = ') + len('const allWorkerUrls = ')
    urls = literal(blk, u); count = len(re.findall(r"'https://[a-z0-9]+\.lambda-url\.us-east-1\.on\.aws/'", urls))
    loop = re.search(r'for \(let i = 0; i < (\d+|Math\.min\(allWorkerUrls\.length, (\d+)\)); i\+\+\)', blk); assert loop, key
    use = int(loop.group(2) or loop.group(1))
    if not loop.group(2): assert count >= use, (key, count, use)          # a plain number: there are at least that many addresses, so "the smaller of the two" is that number
    if lst is None: assert 'payload: { worker_id: i + 1, batch_size: 10 }' in blk, key
    else: assert re.search(r'payload: \{ stock_batch: stockBatch, worker_id: i \+ 1 \}', blk), key
    if 'if (workerResult.result && workerResult.result.success && workerResult.result.results)' in blk: merge = 'guarded'
    elif 'if (workerResult.result.success && workerResult.result.results)' in blk: merge = 'strict'
    elif 'if (workerResult.result && workerResult.result.results)' in blk: merge = 'loose'
    else: raise ValueError(key)
    text_time = "const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);" in blk
    assert text_time or 'const totalTime = (endTime - startTime) / 1000;' in blk, key
    size = int(re.search(r'universe_size: (\d+), processing_time: totalTime', blk).group(1))
    csv = re.search(r"generateExcelExport\(allResults, '([^']+)'\)", blk).group(1)
    f = re.search(r"result = (formatOption3Result|formatASXResult|formatNikkeiResult)\(apiData(?:, ('[^']*'|subOption))?\);", blk)
    if f:
        fmt = {'formatOption3Result': 'us', 'formatASXResult': 'asx', 'formatNikkeiResult': 'nikkei'}[f.group(1)]
        sub = key.split('-', 1)[1]
        arg = None if not f.group(2) else sub if f.group(2) == 'subOption' else f.group(2).strip("'")
        if fmt != 'nikkei': assert arg == sub, (key, arg)          # every one of them passes its own sub-option
    else:
        assert key == '4-ftse100'; fmt = 'ftse'
        a = blk.index("            let output = `"); b = blk.index("            result = { type: 'option_4_ftse100_screener', data: htmlOutput };")
        ftse_format = blk[a:b]
    assert sorted(set(re.findall(r'allResults\.sort\(\(a, b\) => \(b\.total_score \|\| b\.score \|\| 0\) - \(a\.total_score \|\| a\.score \|\| 0\)\);', blk))), key
    entries.append(dict(key=key, name=name, lst=lst, urls=urls, count=count, use=use, merge=merge, text_time=text_time, size=size, csv=csv, fmt=fmt))
    print(f'{key:13s} {name:17s} list {"none" if lst is None else str(len(re.findall(chr(39) + "[^" + chr(39) + "]+" + chr(39), lst))):>5s}  addresses {count:3d}  uses {use:3d}  {merge:7s} time {"text" if text_time else "number":6s} size {size:4d}  {csv:30s} {fmt}')

# ---------------------------------------------------------------- screeners.js
out = ["""// The share screeners of the analysis page, one entry each. analysis-functions.js runs every one of them with the same
// routine (runShareScreener): it splits the list over the workers, asks them all at once, puts the answers together,
// sorts by score and hands the result to the formatter named here.
//
//   key        the page's option and sub-option, as in runAnalysis(3, '8') -> '3-8'
//   name       what it is (for people reading this file)
//   list       the stocks, as Yahoo names them; null = the workers hold the list themselves (Russell 1000 / 2000: each
//              worker is sent its number and takes its own ten stocks)
//   workers    the worker functions' addresses, in order (worker 1 first)
//   use        how many of them a run uses (never more than there are)
//   size       the round number the reports print as the size of the list (not the real count: the reports use their own)
//   csv        the name of the CSV file
//   format     which formatter writes the report: 'us' formatOption3Result, 'asx' formatASXResult, 'nikkei'
//              formatNikkeiResult, 'ftse' formatFTSEResult
//   merge      which answers are counted: 'strict' / 'guarded' need the worker to say success, 'loose' only needs results
//              ('strict' also stops the run if a worker answers with nothing at all, as the page always did)
//   timeText   true = the run's time is handed to the formatter as text with one decimal ("3.2"), false = as a number
//
// THE SAME LISTS ARE IN THE COORDINATOR (stockiq-screener-coordinator, STOCK_UNIVERSES), which runs the screeners in the
// background from the dashboard: change a list in both places. To add a screener: an entry here, a button in
// analysis.html, and the steps in .kiro/steering/add-new-screener.md (stockiq repository).
// Made on 13 Oct 2026 from the 14 copies of this routine that stood in runAnalysis; every list and address was copied by script.
const SHARE_SCREENERS = {"""]
for e in entries:
    out.append(f"""    '{e['key']}': {{
        name: '{e['name']}', size: {e['size']}, use: {e['use']}, csv: '{e['csv']}', format: '{e['fmt']}', merge: '{e['merge']}', timeText: {'true' if e['text_time'] else 'false'},
        list: {'null' if e['lst'] is None else e['lst']},
        workers: {e['urls']}
    }},""")
out[-1] = out[-1].rstrip(',')
out.append("};\n")
open(sys.argv[1] + '/screeners.js', 'w', encoding='utf-8').write('\n'.join(out))

# ---------------------------------------------------------------- analysis-functions.js
routine = """// A screener's entry in SHARE_SCREENERS (screeners.js, a script tag in analysis.html), or null. Should the page in a
// visitor's browser be an older copy without that tag, the file is fetched here the first time a screener is asked for.
async function shareScreener(key) {
    if (typeof SHARE_SCREENERS === 'undefined') {
        try {
            await new Promise((done, failed) => {
                const tag = document.createElement('script');
                tag.src = 'screeners.js'; tag.onload = done; tag.onerror = failed;
                document.head.appendChild(tag);
                setTimeout(failed, 10000);
            });
        } catch (e) { return null; }
    }
    return typeof SHARE_SCREENERS !== 'undefined' && SHARE_SCREENERS[key] ? SHARE_SCREENERS[key] : null;
}

// Every share screener is run by this one routine; a screener is an entry in SHARE_SCREENERS (screeners.js): its list,
// its workers, its name. (Until 13 Oct 2026 runAnalysis held 14 copies of it, one a screener.)
async function runShareScreener(def, subOption) {
    const use = Math.min(def.workers.length, def.use);
    const startTime = Date.now();
    const workerPayloads = [];
    for (let i = 0; i < use; i++) {
        if (!def.list) {          // the workers hold the list: each is sent its number and takes its own ten stocks
            workerPayloads.push({ url: def.workers[i], payload: { worker_id: i + 1, batch_size: 10 }, workerId: i + 1 });
            continue;
        }
        // spread the list over the workers: 10 each, a few more only when the list is longer than workers x 10
        const perWorker = Math.max(10, Math.ceil(def.list.length / use));
        const stockBatch = def.list.slice(i * perWorker, i * perWorker + perWorker);
        // never send an empty batch
        if (stockBatch.length > 0) workerPayloads.push({ url: def.workers[i], payload: { stock_batch: stockBatch, worker_id: i + 1 }, workerId: i + 1 });
    }
    const allWorkerResults = await Promise.all(workerPayloads.map(async (workerData) => {
        const response = await fetch(workerData.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workerData.payload) });
        if (!response.ok) throw new Error(`Worker ${workerData.workerId} failed: ${response.status}`);
        const result = await response.json();
        return { result, workerId: workerData.workerId };
    }));
    const totalTime = def.timeText ? ((Date.now() - startTime) / 1000).toFixed(1) : (Date.now() - startTime) / 1000;
    let allResults = [];
    allWorkerResults.forEach((workerResult) => {
        const answer = workerResult.result;
        const counted = def.merge === 'loose' ? (answer && answer.results) : def.merge === 'guarded' ? (answer && answer.success && answer.results) : (answer.success && answer.results);
        if (counted) allResults = allResults.concat(answer.results);
    });
    allResults.sort((a, b) => (b.total_score || b.score || 0) - (a.total_score || a.score || 0));
    const apiData = { success: true, results: allResults, stocks_analyzed: allResults.length, universe_size: def.size, processing_time: totalTime };
    const csvData = generateExcelExport(allResults, def.csv);
    const result = def.format === 'us' ? formatOption3Result(apiData, subOption) : def.format === 'asx' ? formatASXResult(apiData, subOption)
        : def.format === 'nikkei' ? formatNikkeiResult(apiData) : formatFTSEResult(apiData);
    result.csvData = csvData;
    return result;
}

// The UK FTSE 100 report (it stood inside runAnalysis)
function formatFTSEResult(apiData) {
    const allResults = apiData.results;
""" + '\n'.join(l[8:] if l.startswith('        ') else l for l in ftse_format.rstrip('\n').split('\n')) + """
    return { type: 'option_4_ftse100_screener', data: htmlOutput };
}

"""
branch = """        } else if ((option === 3 || option === 4 || option === 5) && typeof subOption === 'string' && await shareScreener(option + '-' + subOption)) {
            // every share screener: one routine, its lists and workers in screeners.js
            result = await runShareScreener(await shareScreener(option + '-' + subOption), subOption);"""
new_lines = lines[:starts[0]] + branch.split('\n') + lines[end:]
new = '\n'.join(new_lines)
at = new.index('async function runAnalysis('); assert new.count('async function runAnalysis(') == 1
new = new[:at] + routine + new[at:]
open(sys.argv[1] + '/analysis-functions.js', 'w', encoding='utf-8').write(new)
print(f'\nrunAnalysis branches: lines {starts[0] + 1} to {end} ({end - starts[0]} lines) -> 3 lines; the file {len(src) // 1024} KB -> {len(new) // 1024} KB; screeners.js {len(chr(10).join(out)) // 1024} KB')

# ---------------------------------------------------------------- code that can never run, taken out
t = open(sys.argv[1] + '/analysis-functions.js', encoding='utf-8').read(); before = len(t)
# 1. a second (5,'50') branch, for a Shanghai screener that was never built (it asks 'YOUR_LAMBDA_URL'); the first (5,'50') is the ASX 50
a = t.index("        } else if (option === 5 && subOption === '50') {\n            console.log('🚀 SSE 50 Stock Screener');"); b = t.index("        } else if (option === 5 && subOption === '180') {", a)
assert "fetch('YOUR_LAMBDA_URL'" in t[a:b] and t[a:b].count('} else if') == 1; t = t[:a] + t[b:]
# 2. everything after the "return;" of the CSI 300 "coming soon" branch: a third copy of the ASX 300 routine
a = t.index("            alert('CSI 300 screener coming soon!');"); r = t.index("            return;\n", a) + len("            return;\n"); b = t.index("        } else if (option === 7 && (subOption === 'coinspot'", r)
assert 'ASX_300_Screener' in t[r:b] and t[r:b].count('} else if') == 0 and t[a:r].count('\n') == 5, (t[a:r].count('\n'),); t = t[:r] + t[b:]
# 3. two functions nothing calls: an older FTSE 100 screener and its report
for name, start in (('runFTSE100Screener', 'function runFTSE100Screener() {'), ('formatUKResult', 'function formatUKResult(apiData, subOption) {')):
    assert t.count(name) == 1, (name, t.count(name))                 # its own definition and nothing else, in this file
    a = t.index(start); m = re.search(r'\n\}\n', t[a:]); b = a + m.end()
    c = t.rfind('\n', 0, a)
    while t[t.rfind('\n', 0, c) + 1:c].lstrip().startswith('//'): c = t.rfind('\n', 0, c)     # and the comment lines above it
    t = t[:c + 1] + t[b:].lstrip('\n')
open(sys.argv[1] + '/analysis-functions.js', 'w', encoding='utf-8').write(t)
print(f'code that can never run: {(before - len(t)) // 1024} KB taken out; the file is now {len(t) // 1024} KB, {t.count(chr(10))} lines')
