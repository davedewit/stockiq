#!/usr/bin/env python3
"""The notes against the files (25 Oct 2026; the owner: "priority is script things where possible"). Lists every file the steering
notes name that exists nowhere, unless the same line says it was removed: a note pointing at a file that is gone is out of date.
Run by session_start.py (each one a finding); by hand: python3 check-tools/notes_check.py. Read-only. The judgement part of tidying
the notes (out of date, said twice, too long) stays the weekly review's (site_parts "notes")."""
import glob, os, re

ROOT = '/Users/dave/VSCODE'
GONE = re.compile(r'git history|remov|delet|\bgone\b|no longer|was (?:a|an|the)|emptied|taken out|called by nothing|went', re.I)


def index():
    paths = set()
    for top in ('stockiq', 'website'):
        for d, dirs, files in os.walk(os.path.join(ROOT, top)):
            dirs[:] = [x for x in dirs if x not in ('stocks', '.git', 'node_modules', '__pycache__', 'research-data', 'backups')]
            for f in files:
                paths.add(os.path.relpath(os.path.join(d, f), ROOT))
    return paths


def missing():
    paths, out = index(), []
    names = {p.split('/')[-1] for p in paths}
    for md in sorted(glob.glob(os.path.join(ROOT, 'stockiq', '.kiro', 'steering', '*.md'))) + [os.path.join(ROOT, 'stockiq', 'CLAUDE.md')]:
        lines = open(md, encoding='utf-8', errors='replace').read().split('\n')
        if md.endswith('site-overview.md') and '## 13. Change log' in lines:
            lines = lines[:lines.index('## 13. Change log')]          # the change log is history: files named there may be gone
        for i, line in enumerate(lines):
            if GONE.search(line + ' ' + (lines[i + 1] if i + 1 < len(lines) else '')):
                continue
            for n in re.findall(r'`(\.?/?[\w.-]+(?:/[\w.-]+)*\.(?:py|js|sh|html|css))`', line):
                if n.startswith('/') or n.startswith('~'):
                    if os.path.exists(os.path.expanduser(n)):
                        continue
                ref = re.sub(r'^\./', '', n.replace(ROOT + '/', ''))
                if '<' in ref or '*' in ref or ref.split('/')[-1] in names and '/' not in ref:
                    continue
                if any(p == ref or p.endswith('/' + ref) for p in paths):
                    continue
                out.append((os.path.basename(md), n))
    return sorted(set(out))


if __name__ == '__main__':
    m = missing()
    for md, n in m:
        print(f'  {md}: `{n}` exists nowhere')
    print(f'{len(m)} reference(s) to files that do not exist')
