#!/usr/bin/env python3
"""Links to the stock pages from the home page, and the list of shares that have a page (18 Oct 2026).

No page of the site linked to the ~960 indexed stock pages, the pages meant to bring visitors from search: Google finds pages and
weighs them partly by the links to them, the home page's most of all. This writes, between the markers
<!-- STOCK_LINKS_START --> and <!-- STOCK_LINKS_END --> in website/index.html, a section of links to the largest indexed
companies of each market (by market value in US dollars, as update_stock_analysis.py last worked it out), and
website/stock-pages.js, every share that has a stock page, which market-panel.js reads to make a share in the home page's
four lists a link to its page.

    python3 update_home_stock_links.py            write both
    python3 update_home_stock_links.py --dry-run  say what it would write

Run by deploy-to-s3.sh in the daily run, straight after update_stock_analysis.py. It refuses to write the section with fewer
than 20 links (the snapshot step's figures missing), and leaves the page as it was. Only the text between the markers is ever
changed (the rule for every script that writes into a page).
"""
import csv, glob, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, '..', 'website')
OUT = os.environ.get('LINKS_OUT') or WEB          # a staging folder to write into instead (its index.html), for a test
INDEX = os.path.join(OUT, 'index.html')
START, END = '<!-- STOCK_LINKS_START -->', '<!-- STOCK_LINKS_END -->'
# market, suffixes, how many links
MARKETS = [('United States', [''], 16), ('Canada', ['TO'], 4), ('United Kingdom', ['L'], 4), ('Europe', ['PA', 'DE', 'AS', 'MI', 'MC', 'SW'], 6),
           ('Japan', ['T'], 4), ('Hong Kong', ['HK'], 4), ('Australia', ['AX'], 4), ('India', ['NS', 'BO'], 2)]
MIN_LINKS = 20
SUFFIX_WORDS = r'\b(Inc|Incorporated|Corp|Corporation|Company|Co|Ltd|Limited|plc|PLC|SE|SA|S\.A|AG|NV|N\.V|Holdings?|Group|Class [A-C]|The)\b\.?'


def short(name, sym):
    n = (name or '').split(' - ')[0]                       # "LVMH Moët Hennessy - Louis Vuitton" -> its first part
    n = re.sub(SUFFIX_WORDS + r'|\bAktiengesellschaft\b|\bKabushiki Kaisha\b', '', n).replace(',', ' ')
    n = re.sub(r'\s+', ' ', n).strip(' .&-')
    n = re.sub(r'\s+(and|of|&)$', '', n).strip()              # "Eli Lilly and (Company)"
    n = n or sym
    if len(n) > 26:                                          # at a word, with an ellipsis
        n = n[:26].rsplit(' ', 1)[0].rstrip(' ,.&-') + '…'
    return n


def main(dry):
    indexable = [l.strip() for l in open(os.path.join(HERE, 'indexable_stocks.txt')) if l.strip()]
    names = {}
    with open(os.path.join(WEB, 'stocks.txt'), encoding='utf-8') as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                names[row[0].strip()] = row[1].strip()
    pages = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(WEB, 'stocks', '*.html')))
    mcap = {}
    for sym in indexable:
        try:
            v = json.load(open(os.path.join(HERE, '.analysis_cache', 'info', sym + '.json'))).get('last_mcap_usd')
            if v:
                mcap[sym] = float(v)
        except Exception:
            pass
    groups, total = [], 0
    for market, suffixes, n in MARKETS:
        mine = [s for s in indexable if (s.rsplit('.', 1)[1] if '.' in s else '') in suffixes and s in mcap and s in pages]
        seen, one = set(), []
        for s_ in sorted(mine, key=lambda s: -mcap[s]):       # one share a company (GOOGL and GOOG are both Alphabet)
            key = short(names.get(s_), s_).lower()
            if key not in seen:
                seen.add(key); one.append(s_)
        mine = one[:n]
        if mine:
            groups.append((market, mine)); total += len(mine)
    chip = ('display: inline-flex; gap: 6px; align-items: baseline; padding: 6px 10px; margin: 0 6px 6px 0; border: 1px solid var(--border-color); '
            'border-radius: 6px; background: var(--card-bg); text-decoration: none; font-size: 0.85rem;')
    body = '\n'.join(
        f'<div style="margin-top: 14px;"><h3 style="color: var(--text-primary); font-size: 0.95rem; margin: 0 0 8px 0;">{html.escape(market)}</h3><div>'
        + ''.join(f'<a href="stocks/{html.escape(s)}.html" style="{chip}"><strong style="color: #3b82f6;">{html.escape(s)}</strong>'
                  f'<span style="color: var(--text-secondary);">{html.escape(short(names.get(s), s))}</span></a>' for s in syms)
        + '</div></div>' for market, syms in groups)
    section = (f'{START}\n<section id="stock-pages" style="background: var(--bg-secondary); padding: 40px 30px; border-radius: 12px; margin: 40px 0;">\n'
               f'<h2 style="text-align: center; color: var(--text-primary); margin-bottom: 10px; font-size: 1.8rem;">📄 Stock Pages</h2>\n'
               f'<p style="text-align: center; color: var(--text-secondary); max-width: 760px; margin: 0 auto 10px; line-height: 1.6;">Every stock page has the '
               f'latest figures, its 0-100 score with every point explained, recent news and the shares people also watch. These are the largest '
               f'companies on StockIQ by market value, refreshed every day; search above for any of the {len(pages):,} shares.</p>\n'
               f'{body}\n</section>\n{END}')
    page = open(INDEX, encoding='utf-8').read()
    if page.count(START) != 1 or page.count(END) != 1:
        sys.exit(f'index.html must hold {START} and {END} once each: nothing written')
    new = page[:page.find(START)] + section + page[page.find(END) + len(END):]
    js = ('// Every share that has a stock page, for market-panel.js (a share in the home page\'s lists links to its page).\n'
          '// Written by stockiq/update_home_stock_links.py in the daily run: do not edit by hand.\n'
          f'window.STOCK_PAGES = "{",".join(pages)}";\n')
    print(f'{total} links in {len(groups)} markets: ' + '; '.join(f'{m} {len(s)}' for m, s in groups) + f'; {len(pages):,} shares with a page')
    if total < MIN_LINKS:
        sys.exit(f'fewer than {MIN_LINKS} links (the snapshot figures are missing?): the page is left as it was')
    if dry:
        print('(dry run) nothing written'); return
    if new != page:
        open(INDEX, 'w', encoding='utf-8').write(new); print('index.html: the stock links written')
    else:
        print('index.html: the stock links unchanged')
    path = os.path.join(OUT, 'stock-pages.js')
    if not os.path.exists(path) or open(path, encoding='utf-8').read() != js:
        open(path, 'w', encoding='utf-8').write(js); print('stock-pages.js written')


if __name__ == '__main__':
    main('--dry-run' in sys.argv)
