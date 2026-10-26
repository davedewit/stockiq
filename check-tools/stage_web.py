#!/usr/bin/env python3
"""Stage website files for a deploy in one command (24 Oct 2026: each deploy of the day built its folder and fingerprints by hand).

    python3 check-tools/stage_web.py <name> <file> [<file> ...]          the files as they are now in website/
    python3 check-tools/stage_web.py <name> --from <folder> <file> ...   the files from a staging folder (e.g. pages written with PAGES_OUT)
    python3 check-tools/stage_web.py <name> --changed                    every file git sees changed in website/ (stocks/ is not in git)

It copies the files into check-tools/pending-<name>/web/ and writes pending-<name>/deploy.sh: three lines that hand web_deploy.sh each
file with the fingerprint it has before (git's last commit for a tracked file, the file in website/ for a generated one, "none" for a new
one) and the staged one's. Then: DRY_RUN=true bash .../pending-<name>/deploy.sh, and the same without DRY_RUN. Remove the folder after.
Stock pages are not staged this way (3,467 files): the daily deploy's sync, or a sync in a deploy.sh of its own.
"""
import hashlib, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); WEB = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'website')


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def before(f):
    """The fingerprint the file has now: git's last commit when git tracks it, else the file in website/, else none."""
    r = subprocess.run(['git', '-C', WEB, 'show', f'HEAD:{f}'], capture_output=True)
    if r.returncode == 0:
        return hashlib.sha256(r.stdout).hexdigest()
    # not in git: a generated page git ignores keeps its fingerprint in website/; any other file is new (26 Oct 2026: symbol-news.js,
    # new and not yet committed, read as "unchanged" and was left out of the deploy)
    ignored = subprocess.run(['git', '-C', WEB, 'check-ignore', '-q', f]).returncode == 0
    return sha(os.path.join(WEB, f)) if ignored and os.path.exists(os.path.join(WEB, f)) else 'none'


def main(a):
    if len(a) < 2:
        sys.exit(__doc__)
    name, rest = a[0], a[1:]
    src = WEB
    if rest[0] == '--from':
        src, rest = rest[1], rest[2:]
    if rest == ['--changed']:
        out = subprocess.run(['git', '-C', WEB, 'status', '--porcelain'], capture_output=True, text=True).stdout.splitlines()
        rest = [l[3:] for l in out if l[3:] and not l[3:].startswith('stocks/')]
    folder = os.path.join(HERE, f'pending-{name}'); os.makedirs(os.path.join(folder, 'web'), exist_ok=True)
    rows = []
    for f in rest:
        os.makedirs(os.path.dirname(os.path.join(folder, 'web', f)), exist_ok=True)      # a file in a folder (js/...)
        shutil.copy2(os.path.join(src, f), os.path.join(folder, 'web', f))
        was, new = before(f), sha(os.path.join(folder, 'web', f))
        if was == new and src == WEB:
            print(f'{f}: unchanged since the last commit, left out'); continue
        rows.append(f'{f}:{was}:{new}')
    with open(os.path.join(folder, 'deploy.sh'), 'w') as fh:
        fh.write('#!/bin/bash\n# Written by check-tools/stage_web.py: ' + ', '.join(r.split(':')[0] for r in rows) + '\n'
                 f'ROWS="{" ".join(rows)}" exec bash /Users/dave/VSCODE/stockiq/check-tools/web_deploy.sh "$(cd "$(dirname "$0")" && pwd)"\n')
    print(f'{len(rows)} file(s) staged in {folder}\n  DRY_RUN=true bash {folder}/deploy.sh\n  bash {folder}/deploy.sh')


if __name__ == '__main__':
    main(sys.argv[1:])
