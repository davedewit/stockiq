"""Second step for the single-stock report function: company figures for shares outside the US from the file the site's
daily job publishes (the direct route to Yahoo, tried in the first step, is refused from AWS), and a trend line that
says "level with" for a price a hair from its average.
    python3 patch_report2.py <live lambda_function2.py> <out lambda_function2.py>"""
import sys
src = open(sys.argv[1]).read()

def swap(text, old, new):
    assert text.count(old) == 1, (text.count(old), old[:80])
    return text.replace(old, new)

a = src.index("_yahoo_session = {'opener': None, 'crumb': None, 'at': 0}"); b = src.index('def company_figure_lines(fundamentals):')
assert src.count('def fetch_yahoo_figures(symbol):') == 1 and a < src.index('def fetch_yahoo_figures(symbol):') < b
NEW = r'''COMPANY_FIGURES_BUCKET = 'stockiq-dynamic-stock-lists'
COMPANY_FIGURES_KEY = 'site-data/company_figures.json'
_site_figures = {'at': 0, 'figures': None}

def site_company_figures(symbol):
    """Company figures for a share from the file the site's daily job publishes (publish_company_figures.py): Yahoo's
    figures for every stock on the site, already in the units the score uses, with the day they were read ('as_of').
    {} when the share is not on the site or the file cannot be read: the report then says so and scores on price and
    volume alone. (Yahoo's own summary cannot be read from here: it answers "too many requests" to anything that is
    not a browser. Tried and taken out again on 11 Oct 2026.)"""
    try:
        if _site_figures['figures'] is None or time.time() - _site_figures['at'] > 6 * 3600:
            client = s3_client or boto3.client('s3')
            body = client.get_object(Bucket=COMPANY_FIGURES_BUCKET, Key=COMPANY_FIGURES_KEY)['Body'].read()
            _site_figures.update(figures=json.loads(body).get('figures') or {}, at=time.time())
        entry = _site_figures['figures'].get(symbol.upper()) or {}
    except Exception as e:
        print(f"Company figures file not read for {symbol}: {str(e)[:80]}")
        return {}
    return {k: v for k, v in entry.items() if k == 'as_of' or (isinstance(v, (int, float)) and not isinstance(v, bool))}

def fill_missing_figures(symbol, fundamentals):
    """Fill the company figures the first source did not have, for shares only (a fund has no profit margin), and note
    where the figures came from ('figures_source'; None when there are none at all)"""
    had = [k for k in FIGURE_KEYS if fundamentals.get(k) is not None]
    added, as_of = [], ''
    if len(had) < len(FIGURE_KEYS) and (_report_ctx.get('instrument') or 'EQUITY') == 'EQUITY':
        extra = site_company_figures(symbol)
        added = [k for k in FIGURE_KEYS if fundamentals.get(k) is None and extra.get(k) is not None]
        for k in added:
            fundamentals[k] = extra[k]
        try:
            day = datetime.strptime(str(extra.get('as_of')), '%Y-%m-%d')
            as_of = f" (as of {day.day} {day.strftime('%b %Y')})"
        except ValueError:
            as_of = ''
    second = f"Yahoo Finance{as_of}"
    fundamentals['figures_source'] = (f"Finnhub and {second}" if had and added else second if added
                                      else 'Finnhub' if had else None)
    return fundamentals

'''
src = src[:a] + NEW + src[b:]
src = swap(src, '''    side = lambda gap: f"{abs(gap):.1f}% {'above' if gap >= 0 else 'below'}"''',
           '''    side = lambda gap: 'level with' if abs(gap) < 0.05 else f"{abs(gap):.1f}% {'above' if gap > 0 else 'below'}"''')
assert 'yahoo_session' not in src and 'getcrumb' not in src and 'http.cookiejar' not in src
compile(src, 'lambda_function2.py', 'exec')
open(sys.argv[2], 'w').write(src)
print('written:', len(src.split('\n')), 'lines')
