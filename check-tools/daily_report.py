#!/usr/bin/env python3
"""The daily update's email, written from its log (25 Oct 2026; the owner: "if they can include anything that fails or anything i need
to be aware of ... perhaps some log file in the email so i provide to you and you can easily figure it out and fix").

    python3 check-tools/daily_report.py <log> <exit code> <took> <started> <body file>
    python3 check-tools/daily_report.py --show <log>          read a kept log's list; saves nothing

Prints the subject on its first line and writes the body to <body file>. Keeps a copy of the log in ~/stockiq-logs/ (30 days):
daily-<date>.log, or daily-<date>-warn.log when something needs a look; session_start.py makes every -warn log of the last 7 days a
finding, and a session renames it -done.log once fixed. Read-only otherwise.
"""
import glob, os, re, shutil, sys, time
from datetime import datetime

LOGS = os.environ.get('DAILY_LOGS') or os.path.expanduser('~/stockiq-logs')   # DAILY_LOGS: a test folder
BENIGN = [r'IndexNow response', r'possibly delisted', r'Failed download', r'curl: \(', r'Retrying', r'Internet check failed \(attempt',
          r'No new items found', r'Yahoo rate limit hit', r'FX rate for .* unavailable', r'Price download failed for batch',
          r': no answer, yesterday']   # routine: the step retries, falls back to AWS for prices, or the summary above says it


def first(pat, text, group=1):
    m = re.search(pat, text, re.M)
    return m.group(group) if m else None


def main():
    show = sys.argv[1] == '--show'          # --show <log>: print the list only, save nothing (for a session reading a kept log)
    log_path, code, took, started, body_path = (sys.argv[2], '0', '-', '-', '/dev/stdout') if show else sys.argv[1:6]
    text = open(log_path, encoding='utf-8', errors='replace').read()
    did, look = [], []

    gen = sum(int(n) for n in re.findall(r'Updated news\.html with (\d+) new articles', text))
    stock = sum(int(n) for n in re.findall(r'Added (\d+) items to news\.html', text))
    did.append(f'News: {gen} general and {stock} stock articles added')
    if 'Internet connection OK' in text and gen == 0 and stock == 0:
        look.append('No news article was added today (the news steps may be failing): see update_news.py and update_stock_news.py in the log')
    pw = first(r'Pages written: (\d+)', text)
    if pw:
        nd, kept = first(r'No price data: (\d+)', text), first(r"kept yesterday's snapshot: (\d+)", text)
        did.append(f'Stock pages: {pw} updated' + (f' ({nd} had no fresh price, {kept} kept yesterday\'s figures)' if nd and nd != '0' else ''))
        ix = first(r'Indexable \(market cap >= \$10B\): \d+ this run, (\d+) total', text)
        if ix:
            did.append(f'Indexed stock pages: {ix}')
            if int(ix) < 800:
                look.append(f'Only {ix} stock pages are set to be indexed (normally about 950)')
    elif 'Stock analysis for' in text:
        look.append('The stock-page step did not finish: no stock page got today\'s figures')
    sp = re.search(r'Screener pages: (\d+) of (\d+) screeners answered', text)
    if sp:
        did.append(f'Daily screener pages: {sp.group(1)} of {sp.group(2)} markets')
        if int(sp.group(1)) < int(sp.group(2)):
            look.append(f'{int(sp.group(2)) - int(sp.group(1))} daily screener page(s) kept yesterday\'s list (their market did not answer)')
    sm = first(r'Updated sitemap\.xml .* = (\d+) total URLs', text)
    if sm:
        did.append(f'Sitemap: {sm} pages')
    sc = re.search(r'site check [^:]*:.*?(\d+) problems, (\d+) ideas', text)
    if sc:
        did.append(f'Site check: {sc.group(1)} problem(s), {sc.group(2)} idea(s)')
    for p in re.findall(r'\[problem, new\] (.+)', text)[:5]:
        look.append('New site-check problem: ' + p.strip()[:220])
    gh = [re.sub(r'^\s*\S+\s+', '', l) for l in re.findall(r'^\s+\S+\s+(?:stockiq|website): .*$', text, re.M)]
    if 'Skipping git push' in text:
        did.append('GitHub: not pushed today (pushed within the last 23 hours)')
    elif gh:
        did.append('GitHub: ' + '; '.join(gh))
    for l in re.findall(r'^.*(?:could not rebase|push failed).*$', text, re.M):
        look.append('GitHub: ' + l.strip()[:200])

    # crashes: the last line of each Python traceback says what went wrong
    for tb in re.finditer(r'^Traceback \(most recent call last\):\n(?:[ \t].*\n)+(.+)$', text, re.M):
        before = text[:tb.start()].strip().splitlines()[-1:] or ['']
        look.append(f'A step crashed: {tb.group(1).strip()[:200]}' + (f' (after: {before[0].strip()[:80]})' if before[0] else ''))
    for l in re.findall(r'^(?:❌|⚠️).*$|^.*\bError:.*$', text, re.M):   # top-level warnings only: indented ones are notes on one item
        if not any(re.search(b, l) for b in BENIGN) and 'Error:' not in ' '.join(look):
            look.append(l.strip()[:200])
    if code != '0':
        look.insert(0, f'The run stopped with exit code {code} before the end')
    elif 'All done' not in text:
        look.insert(0, 'The run did not reach its end ("All done" missing)')
    look = list(dict.fromkeys(look))[:12]

    if show:
        print('\n'.join(['To look at:'] + [f'  • {x}' for x in look] if look else ['Nothing to look at.']) + '\n' + '\n'.join(['What it did:'] + [f'  • {x}' for x in did]))
        return
    os.makedirs(LOGS, exist_ok=True)
    day = datetime.now().strftime('%Y-%m-%d')
    kept = os.path.join(LOGS, f'daily-{day}{"-warn" if look else ""}.log')
    for other in glob.glob(os.path.join(LOGS, f'daily-{day}*.log')):   # a re-run the same day replaces that day's copy
        os.remove(other)
    shutil.copyfile(log_path, kept)
    for old in glob.glob(os.path.join(LOGS, 'daily-*.log')):
        if time.time() - os.path.getmtime(old) > 30 * 86400:
            os.remove(old)

    icon = '❌' if code != '0' else ('⚠️' if look else '✅')
    lines = [f'Finished {datetime.now().strftime("%a %d %b, %I:%M %p")} (started {started}, took {took}).', '']
    if look:
        lines += [f'⚠️ {len(look)} thing(s) to look at:'] + [f'  • {x}' for x in look] + ['']
    else:
        lines += ['✅ Nothing needs you.', '']
    lines += ['What it did:'] + [f'  • {x}' for x in did]
    if look:
        lines += ['', f'The full log is kept on the Mac: {kept.replace(os.path.expanduser("~"), "~")}',
                  'To have it fixed: open a session and say "the daily email has a warning". The session reads that file itself;',
                  'nothing needs copying. (The next session\'s opening check lists it anyway.)']
    open(body_path, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'StockIQ Daily {icon} - {datetime.now().strftime("%a %b %d")} ({took})' + (f' - {len(look)} to look at' if look else ''))


if __name__ == '__main__':
    main()
