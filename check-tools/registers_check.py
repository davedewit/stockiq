#!/usr/bin/env python3
"""Do the improvement lists match what is live? (23 Oct 2026; the owner, after a look at the Admin page's Improvements tab found entries
missing and questions marked "open" whose trials were already running: "it seems you aren't asking the right questions to auto action
and fix these kind of things".) Read-only, a second or two; session_start.py runs it and makes every PROBLEM line a finding.

It compares:
  1. every on/off switch of the live autopilot (the mirror of stockiq-ai-trader: a top-level NAME = True/False) with the register
     (experiments.json): each trial or rule must have an entry, an entry taken out must not be switched on, one kept or running must
     not be switched off. A new switch with no line in SWITCHES below is a problem until it is given one.
  2. the settings switches a user can turn (the function's tuple of on/off settings) the same way.
  3. the questions (reviews/questions.md) with the register: every running profit trial must be named (`its-id`) by the question it
     answers; a question still "open" or "waiting" while the experiment it names is running; one "on trial" whose experiment has been
     decided (write the answer).
  4. how long things sit: a running experiment with no decision day; an idea not started for 21 days or more; questions open for 21
     days or more (test it, schedule it, or close it with the reason it is not worth testing). Lists that only grow are the failure.
  5. every page and script of the site (website/*.html, *.js, js/*.js) is named by a part of site_parts.json.

    python3 check-tools/registers_check.py            prints OK lines and PROBLEM lines
"""
import os, re, sys, json, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FUNC = os.path.join(ROOT, 'lambda-sync', 'stockiq-ai-trader', 'lambda_function.py')
STALE_DAYS = 21

# switch in the function -> experiment id, or 'infra: why it is not an experiment'. Add a line whenever a switch is added.
SWITCHES = {'DIARY': 'infra: the diary of every line and trade, a record, not a rule', 'CENTRAL': 'infra: one shared record every account learns from',
            'AI_SELL': 'ai-review-off', 'THEMES': 'theme-sleeve', 'GAP_WAIT': 'gap-wait', 'RANK_PICK': 'rank-pick', 'PATIENT': 'patient-shares',
            'STOP_WATCH': 'stop-watch'}
SETTINGS = {'selfTune': 'infra: the user lets it try changes to its own rules', 'emails': 'infra: emails', 'compound': 'compound', 'themes': 'theme-sleeve'}

def main():
    out, problem = [], lambda t: out.append('PROBLEM ' + t)
    ex = {e['id']: e for e in json.load(open(os.path.join(HERE, 'experiments.json')))['experiments']}
    today = datetime.date.today()

    # 1 and 2: the live autopilot's switches against the register
    try:
        src = open(FUNC, encoding='utf-8').read()
        live = dict(re.findall(r'^([A-Z_]{3,}) = (True|False)\b', src, re.M))
        for name, val in live.items():
            want = SWITCHES.get(name)
            if not want:
                problem(f'the autopilot has a switch {name} = {val} that no register entry covers: add it to experiments.json (and to SWITCHES in registers_check.py)'); continue
            if want.startswith('infra'): continue
            e = ex.get(want)
            if not e: problem(f'switch {name} points at experiment "{want}", which is not in experiments.json'); continue
            if e['status'] == 'removed' and val == 'True': problem(f'{name} is switched on, but experiment "{want}" was taken out on {e.get("decided")}')
            if e['status'] in ('running', 'kept') and val == 'False': problem(f'{name} is switched off, but experiment "{want}" is {e["status"]}: decide it or switch it on')
        m = re.search(r"for switch in \(([^)]*)\)", src)
        for s in re.findall(r"'(\w+)'", m.group(1) if m else ''):
            want = SETTINGS.get(s)
            if not want: problem(f'the autopilot has an on/off setting "{s}" that no register entry covers: add it (and to SETTINGS in registers_check.py)')
            elif not want.startswith('infra') and want not in ex: problem(f'setting "{s}" points at experiment "{want}", which is not in experiments.json')
        out.append(f'OK {len(live)} switches and the on/off settings of the live autopilot compared with the register')
    except OSError:
        problem('the autopilot mirror could not be read: ' + FUNC)

    # 3: the questions against the register
    rows = []
    for line in open(os.path.join(HERE, 'reviews', 'questions.md'), encoding='utf-8'):
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) >= 5 and c[0].isdigit(): rows.append(c)
    for c in rows:
        n, asked, ans = c[0], c[1], c[-1]
        word = (re.match(r'\*\*([^*]+)\*\*', ans) or [None, ans])[1].lower()
        status = 'answered' if word.startswith('answered') else 'trial' if 'trial' in word or word.startswith('running') else 'waiting' if word.startswith('waiting') else 'open'
        named = [i for i in re.findall(r'`([a-z0-9-]+)`', ' '.join(c)) if i in ex]
        for i in named:
            st = ex[i]['status']
            if status == 'open' and st == 'running' and i in ans: problem(f'question {n} reads "open" but experiment "{i}" is running: mark it On trial (or Waiting, with what it waits for)')
            if status == 'trial' and st in ('kept', 'removed') and i in ans: problem(f'question {n} reads "on trial" but experiment "{i}" was {st} on {ex[i].get("decided")}: write the answer')
        if status == 'open':
            d = asked_date(asked, today)
            if d and (today - d).days >= STALE_DAYS: problem(f'question {n} has been open {(today - d).days} days ({c[2][:70]}...): test it, schedule it, or close it with the reason')
    named_all = set(re.findall(r'`([a-z0-9-]+)`', ' '.join(' '.join(c) for c in rows)))
    for e in ex.values():
        if e['status'] == 'running' and e.get('angle', '').split(',')[0].strip() in ('profit', 'analysis') and e['id'] not in named_all:
            problem(f'the profit trial "{e["id"]}" is named by no question in questions.md: write `{e["id"]}` into the question it answers (or add one), so the two cannot drift apart')
    out.append(f'OK {len(rows)} questions compared with the register')

    # 4: what sits too long
    for e in ex.values():
        if e['status'] == 'running' and not e.get('decide'): problem(f'experiment "{e["id"]}" is running with no decision day')
        if e['status'] == 'idea':
            d = parse(e.get('added'))
            if not d: problem(f'idea "{e["id"]}" has no date it was added')
            elif (today - d).days >= STALE_DAYS and not re.search(r'[Ss]tarts (when|on|after)', e.get('measure', '')):
                problem(f'idea "{e["id"]}" has waited {(today - d).days} days: start it, give it a start condition ("Starts when ..."), or drop it with the reason')
    # 5: every page and script of the site belongs to a part of the review list (site_parts.json), so that no area is never looked at
    # (23 Oct 2026: 19 of 41 files were named by no part, the owner asked whether 45 parts were all there is)
    import glob
    parts = json.load(open(os.path.join(HERE, 'site_parts.json')))['parts']
    named = ' '.join((p['part'] + ' ' + p.get('where', '')).lower() for p in parts)
    web = os.path.join(os.path.dirname(ROOT), 'website')
    files = sorted(os.path.basename(f) for f in glob.glob(web + '/*.html') + glob.glob(web + '/*.js') + glob.glob(web + '/js/*.js'))
    loose = [f for f in files if f.lower() not in named]
    for f in loose: problem(f'{f} belongs to no part of site_parts.json: add it to a part\'s "where" (or a new part), so that it is reviewed in turn')
    out.append(f'OK {len(files) - len(loose)} of {len(files)} pages and scripts of the site belong to a part ({len(parts)} parts)')
    print('\n'.join(out))
    return sum(1 for l in out if l.startswith('PROBLEM'))

def parse(iso):
    try: return datetime.date.fromisoformat((iso or '')[:10])
    except ValueError: return None

def asked_date(text, today):
    m = re.match(r'(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', text)
    if not m: return None
    d = datetime.datetime.strptime(f'{m.group(1)} {m.group(2)} {today.year}', '%d %b %Y').date()
    return d.replace(year=d.year - 1) if d > today else d

if __name__ == '__main__':
    sys.exit(1 if main() else 0)
