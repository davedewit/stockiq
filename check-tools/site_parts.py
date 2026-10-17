#!/usr/bin/env python3
"""Every part of the site, and when a session last looked at it for improvements (17 Oct 2026). The owner: "Its almost like you need
a list of all the parts of my website, and each 24 hours if not done already pick a few random ones to think about improvements or
fault finding. as thats literally what i do with you ... typically around improving ease of use understanding, and of course
investment positive opportunity". So session_start.py prints the three parts looked at longest ago, every session, and the session
reviews them without being asked: opens them (a picture, the live page as the owner's account read-only, the code), asks the
LENSES below, fixes what is plainly wrong, and brings the rest as numbered improvements.

    python3 check-tools/site_parts.py                    the parts, oldest review first
    python3 check-tools/site_parts.py next [n]           the n (3) to look at now
    python3 check-tools/site_parts.py done <id> "<what was found or changed>"     record a review
    python3 check-tools/site_parts.py add <id> "<part>" "<where to look>"          a part that is missing from the list

The list is research-data-free and in git (check-tools/site_parts.json): add a part whenever the site gains one.
"""
import os, sys, json, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); FILE = os.path.join(HERE, 'site_parts.json')
LENSES = ['Could a first-time visitor understand it without help? Is any figure unexplained, any word jargon?',
          'Is anything wrong: a figure that does not add up, two places that disagree, a stale count or date, a broken link?',
          'Does it look right on a phone and in dark mode?',
          'Does it help the account beat an S&P 500 fund, or the site win paying users? What would?',
          'Is there a simpler way: fewer clicks, fewer words, one place instead of two?']

def load():
    return json.load(open(FILE))

def save(d):
    json.dump(d, open(FILE, 'w'), indent=1, ensure_ascii=False)

def oldest(d, n=3):
    """The parts looked at longest ago; among equally old ones a different shuffle each day (the owner asked for random ones)."""
    import hashlib
    day = datetime.date.today().isoformat()
    return sorted(d['parts'], key=lambda p: (p.get('last') or '', hashlib.sha256((day + p['id']).encode()).hexdigest()))[:n]

if __name__ == '__main__':
    d, a = load(), sys.argv[1:]
    if not a:
        for p in oldest(d, len(d['parts'])): print(f"{p.get('last') or 'never':10s}  {p['id']:28s} {p['part']}")
    elif a[0] == 'next':
        for p in oldest(d, int(a[1]) if len(a) > 1 else 3): print(f"{p['id']}: {p['part']} (where: {p['where']}; last looked at {p.get('last') or 'never'})")
        print('Ask of each: ' + ' / '.join(LENSES))
    elif a[0] == 'done' and len(a) >= 3:
        p = next(x for x in d['parts'] if x['id'] == a[1])
        p['last'] = datetime.date.today().isoformat(); p.setdefault('log', []).append({'at': p['last'], 'found': a[2]}); p['log'] = p['log'][-10:]
        save(d); print(f"{a[1]}: recorded")
    elif a[0] == 'add' and len(a) >= 4:
        d['parts'].append({'id': a[1], 'part': a[2], 'where': a[3], 'last': None}); save(d); print(f"{a[1]}: added")
    else:
        sys.exit(__doc__)
