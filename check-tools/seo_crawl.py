#!/usr/bin/env python3
"""The live site as Google's crawler sees it (1 Nov 2026; the owner: "has there been a thorough check everything is setup as best as
possible for google to discover my pages", then "hope this kind of thing is done by you on autopilot moving forward"). Read-only; about
1,000 requests to stockiq.tech (inside CloudFront's free allowance); a few minutes. Run weekly by weekly_check.py.

Checks, each a PASS or FAIL line:
  - robots.txt lets crawlers in and names the sitemap
  - http:// and www. go to https://stockiq.tech/ with a permanent redirect; a missing page answers 404
  - every page in the sitemap answers 200 to Googlebot, without a redirect, is not noindex, names itself as canonical, has a title and
    a description of its own, and its JSON-LD parses
  - the sitemap's dates are not in the future, and a stock page's is not older than the data date on the page
  - the IndexNow key file that notify_search_engines.py names is on the site and holds the key
    python3 check-tools/seo_crawl.py
"""
import collections, concurrent.futures as cf, datetime as dt, json, os, re, urllib.request

UA = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
SITE = 'https://stockiq.tech/'
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'website')
ok_all = True


def say(ok, name, detail=''):
    global ok_all
    ok_all = ok_all and ok
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail and not ok else ''))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def get(u, follow=True):
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    try:
        r = opener.open(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=30)
        return r.status, r.geturl(), r.headers, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Location', u), e.headers, ''
    except Exception as e:
        return 0, u, {}, str(e)


# robots.txt and the ways in
st, _, _, robots = get(SITE + 'robots.txt')
say(st == 200 and 'Sitemap: https://stockiq.tech/sitemap.xml' in robots and not re.search(r'(?m)^Disallow:\s*/\s*$', robots),
    'robots.txt lets crawlers in and names the sitemap')
for u in ('http://stockiq.tech/', 'https://www.stockiq.tech/'):
    st, loc, _, _ = get(u, follow=False)
    say(st == 301 and loc.startswith('https://'), f'{u} redirects permanently', f'{st} {loc}')
st, _, _, _ = get(SITE + 'no-such-page-seo-check.html')
say(st == 404, 'a missing page answers 404', str(st))

# every page in the sitemap
st, _, _, sm = get(SITE + 'sitemap.xml')
pairs = re.findall(r'<(?:\w+:)?loc>([^<]+)</(?:\w+:)?loc>\s*<(?:\w+:)?lastmod>([^<]+)<', sm)
say(st == 200 and len(pairs) >= 500, f'the sitemap lists {len(pairs)} pages')
today = dt.datetime.now(dt.timezone.utc).date().isoformat()
probs, titles, descs = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)


def check(pair):
    u, lastmod = pair
    st, final, _, h = get(u)
    out = []
    if st != 200:
        out.append(('does not answer 200', str(st)))
    if final != u:
        out.append(('redirects', final))
    rb = re.search(r'<meta name="robots" content="([^"]*)"', h)
    if rb and 'noindex' in rb.group(1):
        out.append(('is noindex while in the sitemap', ''))
    cn = re.search(r'<link rel="canonical" href="([^"]*)"', h)
    if not cn or cn.group(1) != u:
        out.append(('does not name itself as canonical', cn.group(1) if cn else 'none'))
    for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            json.loads(blk)
        except ValueError:
            out.append(('has JSON-LD that does not parse', ''))
    if lastmod[:10] > today:
        out.append(('has a sitemap date in the future', lastmod))
    dm = re.search(r'"dateModified":\s*"(\d{4}-\d{2}-\d{2})', h)
    if '/stocks/' in u and dm and lastmod[:10] < dm.group(1):
        out.append(('has a sitemap date older than its data', f'{lastmod} < {dm.group(1)}'))
    t = re.search(r'<title>([^<]*)</title>', h)
    d = re.search(r'<meta name="description" content="([^"]*)"', h)
    return u, out, t.group(1) if t else None, d.group(1) if d else None


with cf.ThreadPoolExecutor(8) as ex:
    for u, out, t, d in ex.map(check, pairs):
        for k, v in out:
            probs[k].append(f'{u.replace(SITE, "")} {v}'.strip())
        if t is None:
            probs['has no title'].append(u.replace(SITE, ''))
        else:
            titles[t].append(u)
        if d is None:
            probs['has no description'].append(u.replace(SITE, ''))
        else:
            descs[d].append(u)
for k, name in (('does not answer 200', 'answers 200 to Googlebot'), ('redirects', 'loads without a redirect'),
                ('is noindex while in the sitemap', 'is open to indexing'), ('does not name itself as canonical', 'names itself as canonical'),
                ('has no title', 'has a title'), ('has no description', 'has a description'),
                ('has JSON-LD that does not parse', "has JSON-LD that parses"), ('has a sitemap date in the future', 'has a sitemap date not in the future'),
                ('has a sitemap date older than its data', 'has a sitemap date no older than its data')):
    v = probs.get(k, [])
    say(not v, f'every sitemap page {name}', f'{len(v)} {k}: ' + ', '.join(v[:5]))
dt_ = [t for t, u in titles.items() if len(u) > 1]
say(not dt_, 'every sitemap page has a title of its own', f'{len(dt_)} shared, e.g. {dt_[:2]}')
dd = [d for d, u in descs.items() if len(u) > 1]
say(not dd, 'every sitemap page has a description of its own', f'{len(dd)} shared, e.g. {[x[:60] for x in dd[:2]]}')

# the IndexNow key (1 Nov 2026: its file had never existed, so Bing refused every ping and blocked the key)
try:
    ns = open(os.path.join(WEB, 'notify_search_engines.py'), encoding='utf-8').read()
    key = re.search(r'"key":\s*"([^"]+)"', ns).group(1)
    loc = re.search(r'"keyLocation":\s*"([^"]+)"', ns).group(1)
    st, _, _, body = get(loc)
    say(st == 200 and body.strip() == key, 'the IndexNow key file is on the site and holds the key', f'{st} {loc}')
except Exception as e:
    say(False, 'the IndexNow key file is on the site and holds the key', f'{type(e).__name__}: {e}')

print('ALL PASS' if ok_all else 'SOME FAILED')
