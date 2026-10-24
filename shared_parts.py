#!/usr/bin/env python3
"""The site's menu and footer, defined once and written into every page (24 Oct 2026).

The owner: "make sure we don't create silly code that requires us having to update the same thing on multiple pages". Until this
script the desktop menu existed in 9 versions and the footer in 13 (hand copies that had drifted: the disclaimer missing on some
pages, "Blog" pointing at two different pages, the stock pages with old wording). Now:
  - MENU and FOOTER below are the one definition;
  - this script writes them between markers into every page that has the site's header (website/*.html, the 3,467 stock pages,
    and the stock-page template in generate-stock-pages.py, so a regeneration keeps them); the daily screener pages copy the
    screener guide's menu and footer (update_screener_pages.py), so they follow by themselves;
  - pages are plain HTML as before (search engines read the links); site-header.js builds a phone menu from the desktop menu only
    on a page that has none of its own.

    python3 shared_parts.py              write the parts into every page (prints what changed)
    python3 shared_parts.py --check      read-only: which pages differ from the definition (site_audit.py runs this)
    python3 shared_parts.py --dry-run    say what would change, write nothing
    SHARED_OUT=<folder> python3 ...      write into copies in that folder instead (website/ pages only; for staging)

Markers: <!-- SHARED_MENU_START/END --> inside .desktop-nav, <!-- SHARED_PHONE_MENU_START/END --> inside .mobile-menu-content,
<!-- SHARED_FOOTER_START/END --> around the footer. On a page without them yet, the existing block is replaced and the markers put in.
Keep the markup free of curly braces: the stock-page template is a Python f-string.
"""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(HERE), 'website')
TEMPLATE = os.path.join(HERE, 'generate-stock-pages.py')
SKIP = re.compile(r'^(screener-.+|screeners-today|clear-cache)\.html$')     # written from one place already, or no header

# ---------------------------------------------------------------- the one definition
# A plain link, or a menu with its links. The Account menu is the signed-out one: auth.js rewrites it for a signed-in visitor.
MENU = [
    ('link', 'Home', 'index.html', '🏠'),
    ('menu', 'Analysis', 'analysis-dropdown', [('Stock &amp; ETF Analysis', 'analysis.html?option=1'),
                                               ('Trading Signals', 'analysis.html?option=2')]),
    ('menu', 'Screeners', 'screeners-dropdown', [('📊 Today&rsquo;s top 10s', 'screeners-today.html'),
                                                 ('🇺🇸 US Markets', 'analysis.html?option=3'),
                                                 ('🇪🇺 Europe Markets', 'analysis.html?option=4'),
                                                 ('🌏 Asia-Pacific Markets', 'analysis.html?option=5'),
                                                 ('🌎 Americas Markets', 'analysis.html?option=6'),
                                                 ('🪙 Crypto (540 coins)', 'analysis.html?option=7')]),
    ('link', 'Pricing', 'index.html#pricing', '💳'),
    ('menu', 'Account', 'account-dropdown', [('Register', 'signup.html'), ('Login', 'login.html')]),
]
FOOTER_COLUMNS = [
    ('Tools', [('Stock analysis', 'analysis.html?option=1'), ('Today&rsquo;s top 10s', 'screeners-today.html'),
               ('All screeners', 'analysis.html?option=3'), ('Pricing', 'index.html#pricing')]),
    ('Learn', [('Market news', 'news.html'), ('Blog', 'blog.html'), ('FAQ', 'faq.html'), ('About', 'about.html')]),
    ('Help', [('Support', 'support.html'), ('Contact', 'contact.html'), ('Terms of Service', 'terms.html'),
              ('Privacy Policy', 'privacy-policy.html'), ('Refund Policy', 'refunds.html'), ('Data Deletion', 'data-deletion.html')]),
]
DISCLAIMER = ('General information only, not financial advice. Scores and signals are automated model outputs that do not take your '
              'personal circumstances into account, and past performance does not indicate future results. Market data comes from '
              'third parties (Yahoo Finance, Finnhub) and may be delayed or inaccurate.')
NOTE = 'written by stockiq/shared_parts.py: change it there, not here'
PLAIN = 'text-decoration: none !important; color: inherit; display: flex; align-items: center;'


def menu_html(p):
    out = [f'<!-- SHARED_MENU_START: the menu, {NOTE} -->']
    for item in MENU:
        if item[0] == 'link':
            out.append(f'<a href="{p}{item[2]}" class="nav-item home-link" style="{PLAIN}">{item[1]}</a>')
        else:
            _, title, mid, links = item
            extra = ' style="margin-left: auto;"' if mid == 'account-dropdown' else ''
            out.append(f'<div class="nav-item dropdown" onclick="showDropdown(\'{mid}\', event)"{extra}>{title} <span class="dropdown-arrow">▼</span>'
                       f'<div class="dropdown-menu" id="{mid}">' + ''.join(f'<a href="{p}{u}">{t}</a>' for t, u in links) + '</div></div>')
    out.append('<!-- SHARED_MENU_END -->')
    return '\n'.join(out)


def phone_menu_html(p):
    out = [f'<!-- SHARED_PHONE_MENU_START: the phone menu, {NOTE} -->']
    for item in MENU:
        if item[0] == 'link':
            out.append(f'<div class="mobile-section"><a href="{p}{item[2]}">{item[3]} {item[1]}</a></div>')
            if item[1] == 'Home':      # shown to a signed-in visitor (site-header.js, the pages' own code)
                out.append(f'<div class="mobile-section" id="mobile-dashboard-section" style="display: none;"><a href="{p}dashboard.html">📊 Dashboard</a></div>')
        else:
            _, title, _, links = item
            out.append(f'<div class="mobile-section"><div class="mobile-section-title">{title}</div>' + ''.join(f'<a href="{p}{u}">{t}</a>' for t, u in links) + '</div>')
    out.append('<div class="mobile-section"><div class="mobile-section-title">Theme</div><a href="#" onclick="event.preventDefault(); toggleTheme()" id="mobile-theme-toggle">🌙 Dark Mode</a></div>')
    out.append('<!-- SHARED_PHONE_MENU_END -->')
    return '\n'.join(out)


def footer_html(p):
    cols = ''.join(f'<div class="sf-col"><div class="sf-head">{h}</div>' + ''.join(f'<a href="{p}{u}">{t}</a>' for t, u in links) + '</div>'
                   for h, links in FOOTER_COLUMNS)
    return '\n'.join([
        f'<!-- SHARED_FOOTER_START: the footer, {NOTE} -->',
        '<footer class="footer site-footer">',
        '<div class="sf-cols">',
        f'<div class="sf-brand"><a href="{p}index.html" class="sf-logo"><img src="{p}stockiq-logo.png" alt="" width="20" height="20" loading="lazy">StockIQ</a>'
        '<p>Research tools for individual investors: scores, screeners and a practice portfolio.</p></div>',
        cols,
        '</div>',
        f'<p class="sf-legal">{DISCLAIMER}</p>',
        '<p class="sf-copy">&copy; 2026 StockIQ &middot; <a href="https://instagram.com/stockiq.tech" target="_blank" rel="noopener noreferrer">Instagram</a></p>',
        '</footer>',
        '<!-- SHARED_FOOTER_END -->'])


# ---------------------------------------------------------------- writing it into a page
def between(s, name, new):
    """Replace what is between the markers; None when the page has no such markers."""
    m = re.search(rf'<!-- SHARED_{name}_START.*?<!-- SHARED_{name}_END -->', s, re.S)
    return None if not m else s[:m.start()] + new + s[m.end():]


def div_end(s, start):
    """The end of the <div> that opens at start (nested divs counted)."""
    depth, i = 0, start
    for m in re.finditer(r'<div\b|</div>', s[start:]):
        depth += 1 if m.group(0) == '<div' else -1
        if depth == 0:
            return start + m.end()
    return -1


def apply(s, p):
    """The page with the shared parts written in. Returns (text, what was done)."""
    done = []
    if '<nav class="top-nav"' not in s:
        return s, done
    # the desktop menu: from the Home link to the end of the Account menu (or the Home link alone)
    t = between(s, 'MENU', menu_html(p))
    if t is None:
        home = re.search(r'<a [^>]*class="nav-item[^"]*"[^>]*>\s*Home\s*</a>', s)
        if home:
            acc = re.search(r'<div class="nav-item dropdown" onclick="showDropdown\(\'account-dropdown\'', s[home.end():])
            end = div_end(s, home.end() + acc.start()) if acc else home.end()
            t = s[:home.start()] + menu_html(p) + s[end:]
            done.append('menu (markers put in)')
    elif t != s:
        done.append('menu')
    s = t if t is not None else s
    # the phone menu's content, on pages that have their own phone menu
    t = between(s, 'PHONE_MENU', phone_menu_html(p))
    if t is None:
        m = re.search(r'<div class="mobile-menu-content">', s)
        if m:
            end = div_end(s, m.start())
            t = s[:m.end()] + '\n' + phone_menu_html(p) + '\n</div>' + s[end:]
            done.append('phone menu (markers put in)')
    elif t != s:
        done.append('phone menu')
    s = t if t is not None else s
    # the footer (a usage counter some pages kept inside it stays, just after it)
    t = between(s, 'FOOTER', footer_html(p))
    if t is None:
        m = re.search(r'<footer\b[^>]*>.*?</footer>', s, re.S)
        if m:
            keep = re.search(r'<div id="usage-counter"[^>]*>.*?</div>', m.group(0), re.S)
            t = s[:m.start()] + footer_html(p) + ('\n' + keep.group(0) if keep else '') + s[m.end():]
            done.append('footer (markers put in)')
    elif t != s:
        done.append('footer')
    s = t if t is not None else s
    return s, done


def targets():
    pages = [(f, '') for f in sorted(glob.glob(os.path.join(WEB, '*.html'))) if not SKIP.match(os.path.basename(f))]
    stocks = [(f, '../') for f in sorted(glob.glob(os.path.join(WEB, 'stocks', '*.html')))]
    return pages, stocks


def main():
    check, dry, out = '--check' in sys.argv, '--dry-run' in sys.argv, os.environ.get('SHARED_OUT', '')
    pages, stocks = targets()
    differ, changed = [], 0
    for f, p in pages + ([] if out else stocks) + ([] if out else [(TEMPLATE, '../')]):
        s = open(f, encoding='utf-8').read()
        t, done = apply(s, p)
        if t == s:
            continue
        rel = os.path.relpath(f, os.path.dirname(HERE))
        differ.append(rel)
        if check or dry:
            if len(differ) <= 12 or not rel.startswith('website/stocks/'):
                print(f'{"differs" if check else "would change"}: {rel} ({", ".join(done) or "changed"})')
            continue
        if f == TEMPLATE and '{' in menu_html(p) + phone_menu_html(p) + footer_html(p):
            sys.exit('the shared markup holds a curly brace: the stock-page template is an f-string')
        dest = os.path.join(out, os.path.basename(f)) if out else f
        open(dest, 'w', encoding='utf-8').write(t)
        changed += 1
    stock_n = sum(1 for d in differ if d.startswith('website/stocks/'))
    print(f'{len(differ)} file(s) {"differ from the definition" if check else "would change" if dry else "written"}'
          + (f' ({stock_n} stock pages)' if stock_n else ''))
    sys.exit(1 if check and differ else 0)


if __name__ == '__main__':
    main()
