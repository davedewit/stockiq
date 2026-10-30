"""One check before any script writes news.html (30 Oct 2026).

On 26 Oct a pattern meant to find the end of the article list matched a </div> in the page's menu instead, so every
write put a whole copy of the page back in: news.html doubled every 10 articles and reached 5.8 GB, and the daily run
stalled on it. Every writer now calls check() first; a page that fails is not written and the old file stays.
"""
LIST = '<div class="blog-content">'
MAX_BYTES = 20 * 1024 * 1024        # the trimmed page is about 0.4 MB; even untrimmed it has never needed 20 MB


def check(new_html):
    """Return None when new_html is safe to write, else the reason it is not."""
    if new_html.count(LIST) != 1:
        return f'the article list appears {new_html.count(LIST)} times'
    if new_html.count('<footer') != 1:
        return f'the footer appears {new_html.count("<footer")} times'
    if len(new_html) > MAX_BYTES:
        return f'it would be {len(new_html) / 1e6:.0f} MB'
    return None
