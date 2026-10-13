"""Takes the header-bar usage chip out again and puts the home page's yellow bar back: the two files as they were
before 13 Oct 2026's change, whatever else has changed in them since.
   python3 undo.py <theme.js> <index.html> <yellow-bar.html>     rewrites the two files in place; prints what it did
Run by deploy.sh in this folder, which then uploads them."""
import re, sys
theme, index, bar = sys.argv[1:4]
s = open(theme, encoding='utf-8').read()
cut = re.sub(r'\n*// VISITOR_BAR_START.*?// VISITOR_BAR_END\n?', '\n', s, flags=re.S)
if cut != s:
    open(theme, 'w', encoding='utf-8').write(cut); print('theme.js: the switch for the header chip taken out')
else:
    print('theme.js: no switch in it (already undone)')
s = open(index, encoding='utf-8').read()
if 'id="limited-time-banner"' in s:
    print('index.html: the yellow bar is there (already undone)')
else:
    block = open(bar, encoding='utf-8').read()
    at = s.index('\n<main>')            # the bar sat straight before the blank line above the page's <main>
    open(index, 'w', encoding='utf-8').write(s[:at] + block + s[at:])
    print('index.html: the yellow bar put back')
