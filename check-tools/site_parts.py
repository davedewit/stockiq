#!/usr/bin/env python3
"""Every part of the site, and when a session last looked at it for improvements (17 Oct 2026). The owner: "Its almost like you need
a list of all the parts of my website, and each 24 hours if not done already pick a few random ones to think about improvements or
fault finding. as thats literally what i do with you ... typically around improving ease of use understanding, and of course
investment positive opportunity". So session_start.py prints the three parts looked at longest ago, every session, and the session
reviews them without being asked: opens them (a picture, the live page as the owner's account read-only, the code), asks the
LENSES below, fixes what is plainly wrong, and brings the rest as numbered improvements.

    python3 check-tools/site_parts.py                    the parts, oldest review first
    python3 check-tools/site_parts.py next [n]           the n (3) to look at now
    python3 check-tools/site_parts.py done <id> fixed|improved|simplified|idea|question "<what>"     record a look: it must end in an
            improvement (23 Oct 2026, the owner: "each time around you have to find an improvement, not say ok i did a check its ok
            done"). fixed: a fault put right; improved: clearer, faster or more useful; simplified: something removed or merged (often
            the best one: the site must not just grow); idea: a profit idea in experiments.py (give its id); question: a new question in
            reviews/questions.md (give its number); fine (refined the same day: "some areas may just not need a change"): only for a part
            not in PROFIT, with its reason; it then waits until its code changes. A profit and growth part (PROFIT) must always end in an
            improvement: "a topic like figuring out how to make better profit ... can go on forever".
    python3 check-tools/site_parts.py add <id> "<part>" "<where to look>"          a part that is missing from the list

The list is research-data-free and in git (check-tools/site_parts.json): add a part whenever the site gains one.
"""
import os, sys, json, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); FILE = os.path.join(HERE, 'site_parts.json')
LENSES = ['Ease of use and understanding: could a first-time visitor use it without help? Any figure unexplained, any jargon?',
          'Faults: a figure that does not add up, two places that disagree, a stale count or date, a broken link, an error in a log?',
          'Accurate against what is live: does every line match the code and the record today? Is anything that is live missing, or anything taken out still shown? Is its history complete, so nothing is tried twice? (the Improvements tab, 23 Oct 2026, failed this)',
          'Visual appearance: does it look clean, professional and calm, on a phone and in dark mode? Is the important part the first thing seen?',
          'Profit: does it help the account beat an S&P 500 fund (what it buys, when it sells, how much it trades), or the site win paying users?',
          'Analysis of information: is the data behind it right, current and enough? Is there a better source or a better measure?',
          'AI use: would the AI model (ChatGPT) do this part better with a better prompt, more context, or a newer model version? Test it, do not assume',
          'Comparison over time: can it be tried as an experiment beside what is there now and kept only if it measurably helps? (experiments.py)',
          'Phone: at 390px wide, does every part fit, can every button be tapped, does a long list fold away? Most visitors are on a phone (the owner, 24 Oct 2026)',
          'What the viewer chose stays chosen: does an open fold, a ticked view or a typed value survive the page refreshing itself? Does a choice that should not outlive the visit (a range, a filter) reset on a fresh page? (24 Oct 2026: a fold closed at the minute\'s refresh)',
          'Said the same everywhere: after a change, do the FAQ, About, the AI chat\'s guide, the home page and the Admin page all say what is now true? (24 Oct 2026: the chat told a visitor the autopilot could not know about the Fed)',
          'New ideas: what would a smart competitor add here? Write the idea down as an experiment even if it waits']

def load():
    return json.load(open(FILE))

def save(d):
    json.dump(d, open(FILE, 'w'), indent=1, ensure_ascii=False)
    try:                     # the Admin page shows the last reviews (admin.py sync)
        import subprocess; subprocess.run([sys.executable, os.path.join(HERE, 'admin.py'), 'sync'], capture_output=True, timeout=60)
    except Exception:
        pass

# The parts that matter most for profit and sign-ups come up sooner (the priority since 19 Oct 2026: visitors and sign-ups first).
PROFIT = {'funnel', 'screener-pages', 'home-hero', 'home-pricing', 'plans', 'signup-login', 'usage-chip', 'seo', 'stock-pages', 'screener-score',
          'ap-buying', 'ap-selling', 'ap-learning', 'ap-themes', 'speed'}
KINDS = {'fixed': 'Fixed', 'improved': 'Improved', 'simplified': 'Simplified', 'idea': 'New idea to test', 'question': 'New question', 'fine': 'Fine as it is'}
ROOT = os.path.dirname(HERE); WEB = os.path.join(os.path.dirname(ROOT), 'website')

def files_of(part):
    """The files a part names in its "where": site pages and scripts, check scripts, and functions (their copies in lambda-sync)."""
    import re
    out = []
    for tok in re.findall(r'[\w./-]+\.(?:html|js|py|css|sh)\b|stockiq-[a-z0-9-]+', part.get('where', '') + ' ' + part['part']):
        for base in (WEB, ROOT, HERE, os.path.join(ROOT, 'lambda-sync')):
            path = os.path.join(base, tok)
            if os.path.exists(path):
                out.append(path); break
    return sorted(set(out))

def changes_since(part):
    """How many commits touched the part's files since it was last looked at (both repositories), and whether a function copy changed."""
    import subprocess
    last = part.get('last')
    if not last:
        return 0
    n = 0
    for repo in (WEB, ROOT):
        mine = [f for f in files_of(part) if f.startswith(repo + os.sep) and 'lambda-sync' not in f]
        if mine:
            r = subprocess.run(['git', '-C', repo, 'log', f'--since={last}T23:59:59', '--format=%h', '--'] + mine, capture_output=True, text=True)
            n += len([l for l in r.stdout.splitlines() if l.strip()])
    cut = datetime.datetime.fromisoformat(last + 'T23:59:59').timestamp()
    for f in files_of(part):                     # function copies are not in git: their files' dates
        if 'lambda-sync' in f and any(os.path.getmtime(os.path.join(dp, x)) > cut for dp, _, fs in os.walk(f) for x in fs if x.endswith('.py')):
            n += 1
    return n

def ranked(d):
    """Which parts to look at next (23 Oct 2026; the owner: "going through those parts more than once ... probably won't make it better
    ... AI should be thinking deeper"): a part never looked at; then one whose code changed since its last look (new code brings new
    faults); then the parts that matter most for profit; age last, so that nothing waits for ever. A part unchanged since a recent look
    comes last: looking again at the same thing in the same way finds nothing new."""
    today = datetime.date.today(); out = []
    for p in d['parts']:
        age = (today - datetime.date.fromisoformat(p['last'])).days if p.get('last') else None
        ch = changes_since(p)
        fine = ((p.get('log') or [{}])[-1].get('kind') == 'fine') and not ch      # "fine" and unchanged since: it waits (age counts a third)
        score = (100 if age is None else 0) + (30 + 5 * min(ch, 6) if ch else 0) + (15 if p['id'] in PROFIT else 0) + (age or 0) / (21 if fine else 7)
        why = 'never looked at' if age is None else (f'{ch} change{"s" if ch != 1 else ""} since its last look {age} days ago' if ch else f'unchanged since its last look {age} days ago')
        out.append((score, p, why + (', matters for profit and sign-ups' if p['id'] in PROFIT else '')))
    return sorted(out, key=lambda x: -x[0])

def pick(d, n=3):
    """The next n to look at: by ranked(), but at least two of every three a profit and growth part (23 Oct 2026, the owner: "you cycle
    through everything that is related to profit ... and it should.... profit"), so that most of each session goes where the money is."""
    r = ranked(d); want = max(0, n - n // 3)
    prof = [x for x in r if x[1]['id'] in PROFIT][:want]
    rest = [x for x in r if x not in prof][:n - len(prof)]
    return sorted(prof + rest, key=lambda x: -x[0])

def oldest(d, n=3):
    """The next parts to look at, by pick() (the name is kept for the scripts that call it)."""
    return [p for _, p, _ in pick(d, n)]

if __name__ == '__main__':
    d, a = load(), sys.argv[1:]
    if not a:
        for score, p, why in ranked(d): print(f"{score:6.1f}  {p.get('last') or 'never':10s}  {p['id']:20s} {why}")
    elif a[0] == 'next':
        for _, p, why in pick(d, int(a[1]) if len(a) > 1 else 3):
            before = (p.get('log') or [])[-1:]
            print(f"{p['id']}: {p['part']} (where: {p['where']}; {why})" + (f" | last time: {before[0]['found'][:220]}" if before else ''))
        print('Start from what was found last time and what changed since. A profit and growth part must end in an improvement: fixed, improved, '
              'simplified (remove or merge something), idea (in experiments.py) or question (in questions.md). Any other part may end "fine", '
              'with the reason. Real improvements only: nothing added for show. Ask of each: ' + ' / '.join(LENSES))
    elif a[0] == 'done' and len(a) >= 4 and a[2] == 'fine' and a[1] in PROFIT:
        sys.exit(f'{a[1]} is a profit and growth part: a look there must end in an improvement (fixed, improved, simplified, idea or question). '
                 'There is always another idea to test, measure or compare.')
    elif a[0] == 'done' and len(a) >= 4 and a[2] == 'fine' and len(a[3]) < 40:
        sys.exit('"Fine" needs its reason: what was checked, against what, and why nothing should change (at least a sentence).')
    elif a[0] == 'done' and len(a) >= 4 and a[2] in KINDS:
        import re
        if a[2] == 'idea':                       # an idea must be in the register, a question in the list: no empty promises
            ids = {e['id'] for e in json.load(open(os.path.join(HERE, 'experiments.json')))['experiments']}
            if not any(w in ids for w in re.findall(r'[a-z0-9-]+', a[3])): sys.exit('Name the idea\'s id in experiments.py (add it first: experiments.py idea <id> ...)')
        if a[2] == 'question':
            nums = set(re.findall(r'^\| (\d+) \|', open(os.path.join(HERE, 'reviews', 'questions.md'), encoding='utf-8').read(), re.M))
            if not any(n in nums for n in re.findall(r'\d+', a[3])): sys.exit('Name the question\'s number in reviews/questions.md (add it first)')
        p = next(x for x in d['parts'] if x['id'] == a[1])
        p['last'] = datetime.date.today().isoformat(); p.setdefault('log', []).append({'at': p['last'], 'kind': a[2], 'found': f"{KINDS[a[2]]}: {a[3]}"}); p['log'] = p['log'][-10:]
        save(d); print(f"{a[1]}: recorded")
    elif a[0] == 'done':
        sys.exit('site_parts.py done <id> fixed|improved|simplified|idea|question|fine "<what>"  (fine: not for a profit part, and with its reason)')
    elif a[0] == 'add' and len(a) >= 4:
        d['parts'].append({'id': a[1], 'part': a[2], 'where': a[3], 'last': None}); save(d); print(f"{a[1]}: added")
    else:
        sys.exit(__doc__)
