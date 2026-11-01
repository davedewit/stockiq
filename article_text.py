"""The text of a news article, and a check that a summary's figures come from it.

Used by update_news.py (general market news) and update_stock_news.py (stock news) so that the AI summarises what an
article says instead of guessing it from the headline (the owner, 1 Nov 2026: "unless you have a way to pull the actual
article then summarise that using AI rather than AI guess the article based on the title").

  fetch_article_text(url)                  -> the article's paragraphs as plain text (at most MAX_WORDS words), or None
  unbacked_figures(summary, source_text)   -> figures in the summary that the source does not contain (empty: all backed)

No AWS: the pages are read from this Mac, as a browser would. A page that refuses, needs a login or holds too little text
gives None, and the caller falls back to the headline (with its stricter rules).
"""
import html
import re

import requests

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/130.0 Safari/537.36',
      'Accept-Language': 'en-US,en;q=0.9'}
MAX_WORDS = 800          # enough for a summary; about 1,100 tokens of gpt-4o-mini (a fiftieth of a US cent)
MIN_WORDS = 120          # less than this is a teaser or a paywall, not the article

# paragraphs that are page furniture, not the article
JUNK = re.compile(r'skip to (navigation|main|content|right)|sign up|subscribe|newsletter|cookie|all rights reserved|'
                  r'terms of (use|service)|privacy policy|advertis|has a disclosure policy|motley fool has positions|'
                  r'\bemail\b[^.]{0,40}(@|\[email)|click here|download the app|log ?in to|create (a free )?account|watchlist|follow us', re.I)


def _text(fragment):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', fragment))).strip()


def extract(page):
    """The article's paragraphs from a page's HTML."""
    # exact tag names only (Yahoo has custom tags such as <header-...>); not <form> or <header>: MarketBeat wraps its whole page in a form
    page = re.sub(r'<(script|style|noscript|svg|nav|footer|aside)(?:\s[^>]*)?>.*?</\1\s*>', ' ', page, flags=re.S | re.I)
    def paras_of(body):
        found = [_text(p) for p in re.findall(r'<p\b[^>]*>(.*?)</p>', body, flags=re.S | re.I)]
        return [p for p in found if len(p) > 60 and not JUNK.search(p)]
    count = lambda ps: sum(len(p.split()) for p in ps)
    # the <article> holding the most text (the Motley Fool has many small ones, cards for other stories); the whole page
    # when none holds an article's worth
    blocks = [paras_of(b) for b in re.findall(r'<article\b.*?</article>', page, flags=re.S | re.I)]
    best = max(blocks, key=count) if blocks else []
    paras = best if count(best) >= MIN_WORDS else paras_of(page)
    words, out = 0, []
    for p in paras:
        out.append(p)
        words += len(p.split())
        if words >= MAX_WORDS:
            break
    text = '\n\n'.join(out)
    return ' '.join(text.split(' ')[:MAX_WORDS * 2]) if words >= MIN_WORDS else None


def fetch_article_text(url, timeout=12):
    """The article at url as plain text, or None (refused, a login wall, too short, a Google News redirect)."""
    if not url or not url.startswith('http') or 'news.google.com' in url:
        return None          # Google News addresses do not open to a script (tested 1 Nov 2026)
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        if r.status_code != 200 or 'html' not in r.headers.get('Content-Type', 'html'):
            return None
        return extract(r.text)
    except Exception:
        return None


def _figures(text):
    """The numbers in a text, written the same way (commas out, a trailing .0 out)."""
    out = set()
    for n in re.findall(r'\d+(?:[.,]\d+)*', text or ''):
        n = n.replace(',', '')
        if '.' in n:
            n = n.rstrip('0').rstrip('.')
        out.add(n)
    return out


def unbacked_figures(summary, source_text):
    """Figures in the summary that are nowhere in the source: an invented number, or one moved from somewhere else."""
    return sorted(_figures(summary) - _figures(source_text))


if __name__ == '__main__':
    import sys
    for u in sys.argv[1:]:
        t = fetch_article_text(u)
        print(f"{u[:80]}\n   {len(t.split()) if t else 0} words | {(t or 'None')[:200]}\n")
