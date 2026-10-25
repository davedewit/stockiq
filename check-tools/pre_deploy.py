#!/usr/bin/env python3
"""The checks every website deploy passes before anything is uploaded (25 Oct 2026; the owner: "when we change things is it updated to
cross check it doesn't break something else"). Run by web_deploy.sh on its dry run; the real run only repeats it when the staged files
have changed since (a stamp in the folder). Read-only: pages are served from this machine, nothing is written to the site.

    python3 check-tools/pre_deploy.py <pending folder> <file> [<file> ...]

1. the daily site check on the staged copy: any problem the change adds stops it (problems already on the site do not)
2. every inline script of a staged page parses
3. in a browser, the changed pages and reference pages (a shared file: a sample of every kind of page): the header, the room under it,
   the menu standing where it stands on the other pages (header_room_check.js), then the phone layout (phone_check.js)
Pages behind a login (the dashboard) are drawn as a visitor sees them; their signed-in tabs have their own tests (section 8c).
"""
import os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = {'styles.css', 'theme.js', 'site-header.js', 'auth.js', 'visitor-bar.js', 'mobile-sidebar.js', 'market-panel.js',
          'live-market.js', 'autopilot-bell.js', 'ai-chat.js'}
SAMPLE = ['index.html', 'analysis.html', 'login.html', 'signup.html', 'about.html', 'faq.html', 'screeners-today.html',
          'screener-dow-jones-30.html', 'stock-screener-guide.html', 'stocks/AAPL.html']
REFERENCE = ['login.html', 'about.html']        # the menu's place is compared against these


def problems(stage):
    out = subprocess.run([sys.executable, os.path.join(HERE, 'site_audit.py')], capture_output=True, text=True,
                         env={**os.environ, 'AUDIT_WEB': stage}, timeout=900).stdout
    return {re.sub(r'\[problem(, new)?\] ', '', l.strip()) for l in out.splitlines() if l.strip().startswith('[problem')}


def main():
    folder, files = os.path.abspath(sys.argv[1]), sys.argv[2:]
    web, fails = os.path.join(folder, 'web'), []
    print('== pre-deploy checks:', ' '.join(files), flush=True)
    empty = tempfile.mkdtemp()
    before, after = problems(empty), problems(web)
    added = sorted(after - before)
    print(f'1. site check: {len(before)} problem(s) on the site now, {len(added)} added by this change')
    fails += ['site check: ' + a for a in added]
    for f in files:
        if not f.endswith('.html'):
            continue
        for i, block in enumerate(re.findall(r'<script(?![^>]*\bsrc=)(?![^>]*json)[^>]*>(.*?)</script>', open(os.path.join(web, f), errors='replace').read(), re.S)):
            t = os.path.join(empty, 'b.js'); open(t, 'w').write(block)
            r = subprocess.run(['node', '--check', t], capture_output=True, text=True)
            if r.returncode:
                fails.append(f'{f}: inline script {i + 1} does not parse: {r.stderr.strip().splitlines()[-1][:160]}')
    print(f'2. inline scripts of the staged pages: {"all parse" if not any("inline" in x for x in fails) else "FAULT"}')
    pages = [f for f in files if f.endswith('.html')]
    if any(os.path.basename(f) in SHARED for f in files):
        pages += SAMPLE
    if pages:
        pages = list(dict.fromkeys(pages + REFERENCE))
        for tool in ('header_room_check.js', 'phone_check.js'):     # never two browser checks at once: they share a port
            r = subprocess.run(['node', tool] + pages, cwd=HERE, capture_output=True, text=True, env={**os.environ, 'WEB': web}, timeout=1800)
            bad = [l for l in r.stdout.splitlines() if re.match(r'\s*(FAIL|ERROR)', l)]
            print(f'3. {tool} on {len(pages)} page(s): {"pass" if r.returncode == 0 and not bad else "FAIL"}')
            if r.returncode or bad:
                fails += [f'{tool}: ' + l.strip()[:300] for l in (bad or r.stdout.strip().splitlines()[-3:])]
    else:
        print('3. no page and no shared file changed: no browser check needed')
    if fails:
        print('\nPRE-DEPLOY CHECKS FAILED:\n  ' + '\n  '.join(fails))
        sys.exit(1)
    print('PRE-DEPLOY CHECKS PASSED')


if __name__ == '__main__':
    main()
