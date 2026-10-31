#!/usr/bin/env python3
"""Reads the dashboard as the owner sees it and flags what reads badly (17 Oct 2026). The owner, after pointing at one confusing
thing after another himself: "anything else confusing you want to optimise? and i'm tired of asking this!" The other checks read
logs and figures; this one reads the page. session_start.py runs it every session, and each flag becomes a finding.

    python3 check-tools/clarity_check.py            the account that has the autopilot switched on
    python3 check-tools/clarity_check.py --keep     also keeps the rendered text (in /tmp/clarity-*) to read in full

What it does: asks the live functions for the account's autopilot answer, its practice portfolio and the Admin page's answer;
draws the AI autopilot tab (both parts, Activity and Settings) and the Admin page in headless Chrome from the site's own
scripts with those answers; then reads only what is on show at first sight (the inside of a closed fold is skipped) and flags:
  - a list of near-identical lines (8 or more lines that differ only in names and numbers)
  - "A and B and C", "1 such moves", "1 holdings"
  - a switched-off feature still described as working (the AI review's early sales: off since 17 Oct 2026)
  - a menu of more than 20 choices
  - the same phrase twice in one line ("Not kept ... Not kept")
  - "undefined", "NaN", "null", "[object Object]"
A flag is a lead, not a verdict: read the line, decide, and either fix the page or teach this script that it is fine.

Writes nothing to the site's data except what the page's own "get" does (it notes a visit to the autopilot, at most every 6
hours). Never prints the account's address.
"""
import os, re, sys, json, html, tempfile, subprocess, urllib.request
from html.parser import HTMLParser
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__)); WEB = os.path.join(HERE, '..', '..', 'website')
STAGED = os.environ.get('CLARITY_WEB')           # a staging folder (check-tools/pending-<name>/web): its files are read first
def site(name):
    p = os.path.join(STAGED, name) if STAGED else ''
    return p if p and os.path.exists(p) else os.path.join(WEB, name)
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
KEEP = '--keep' in sys.argv

def api(name, pattern):
    src = open(site(name), encoding='utf-8').read()
    return re.search(pattern, src).group(0)
AP = api('practice-autopilot.js', r'https://[a-z0-9]+\.lambda-url\.us-east-1\.on\.aws/')
PP = api('practice-portfolio.js', r'https://5c7pt7q[a-z0-9]+\.lambda-url\.us-east-1\.on\.aws/')

def account():
    import boto3
    t = boto3.Session(profile_name='default', region_name='us-east-1').resource('dynamodb').Table('stockiq-ai-trader')
    more, ids = {}, []
    while True:
        page = t.scan(ProjectionExpression='userId, #e', ExpressionAttributeNames={'#e': 'enabled'}, **more)
        ids += [r['userId'] for r in page['Items'] if not r['userId'].startswith('_') and r.get('enabled')]
        if 'LastEvaluatedKey' not in page: break
        more = {'ExclusiveStartKey': page['LastEvaluatedKey']}
    return ids[0] if ids else None

def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

class Visible(HTMLParser):
    """The text a visitor sees before opening anything: a closed <details> keeps only its <summary>; scripts, styles and
    hidden parts (display: none, the hidden attribute) are skipped. Each block ends a line."""
    BLOCK = {'div', 'li', 'tr', 'p', 'h3', 'h4', 'summary', 'details', 'br', 'ul', 'ol', 'table', 'section'}
    def __init__(self):
        super().__init__(); self.out = []; self.stack = []; self.selects = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs); st = (a.get('style') or '').replace(' ', '')
        parent_closed = self.stack and self.stack[-1] == 'closed-details'
        hide = tag in ('script', 'style') or 'hidden' in a or 'display:none' in st
        if tag == 'details' and 'open' not in a: self.stack.append('closed-details'); return
        if tag == 'summary' and parent_closed: self.stack.append('summary'); return
        if tag == 'select': self.selects.append([a.get('aria-label') or a.get('id') or 'a menu', 0])
        if tag == 'option' and self.selects: self.selects[-1][1] += 1
        if tag in ('br', 'input', 'img', 'option', 'meta', 'link'):
            if tag == 'br': self.out.append('\n')
            return
        self.stack.append('hide' if hide else False)
        if tag in self.BLOCK: self.out.append('\n')
    def handle_endtag(self, tag):
        if tag in ('br', 'input', 'img', 'option', 'meta', 'link'): return
        if self.stack: self.stack.pop()
        if tag in self.BLOCK: self.out.append('\n')
    def handle_data(self, data):
        # inside a closed fold only its summary shows: the summary pushed False on top of 'closed-details'
        if any(x == 'hide' for x in self.stack): return
        # every closed fold on the way down must be passed through its summary (a fold inside a closed fold shows nothing,
        # its own summary included: found 18 Oct 2026, when the 34 older holdings inside "and 34 bought earlier" were counted)
        for i, x in enumerate(self.stack):
            if x == 'closed-details' and (i + 1 >= len(self.stack) or self.stack[i + 1] != 'summary'): return
        self.out.append(data)
    def text(self):
        t = html.unescape(''.join(self.out))
        return '\n'.join(l for l in (re.sub(r'\s+', ' ', x).strip() for x in t.splitlines()) if l)

def render(page_html, target_id, height=12000):
    d = tempfile.mkdtemp(prefix='clarity-'); p = os.path.join(d, 'page.html'); open(p, 'w', encoding='utf-8').write(page_html)
    dom = subprocess.run([CHROME, '--headless=new', '--hide-scrollbars', f'--window-size=1300,{height}', '--virtual-time-budget=15000',
                          '--dump-dom', 'file://' + p], capture_output=True, text=True, timeout=180).stdout
    i = dom.find(f'id="{target_id}"')
    v = Visible(); v.feed(dom[max(0, dom.rfind('<', 0, i)):] if i >= 0 else '')
    if KEEP: open(os.path.join(d, 'visible.txt'), 'w').write(v.text()); print(f'  ({target_id}: the visible text is in {d}/visible.txt)')
    return v.text(), v.selects, dom

def autopilot_page(ap, pp):
    S = tempfile.mkdtemp(prefix='clarity-')
    src = open(site('practice-portfolio.js'), encoding='utf-8').read().replace(PP, '__PRACTICE_API_URL__')
    open(os.path.join(S, 'pp.js'), 'w', encoding='utf-8').write(src)
    out = os.path.join(S, 'r.html')
    subprocess.run([sys.executable, os.path.join(HERE, 'dashboard_page.py'), os.path.join(S, 'pp.js'), site('practice-autopilot.js'),
                    out, 'dark', '', site('dashboard.html')], capture_output=True, timeout=120)
    s = open(out, encoding='utf-8').read()
    inj = ("<script>(function(){const AP=%s, PP=%s; const orig=window.fetch; window.fetch=async(url,opts)=>{const u=String(url);"
           "const json=(o)=>({ok:true,status:200,json:async()=>o}); let b={}; try{b=JSON.parse(opts&&opts.body||'{}')}catch(e){}"
           "if(u.includes('5c7pt7q')||u.includes('__PRACTICE')){ if(b.action==='get') return json({success:true,portfolio:PP.portfolio,version:PP.version}); }"
           "else if(!u.includes('?symbol=') && b.action==='get') return json(AP); return orig(url,opts);};})();</script>\n") % (json.dumps(ap), json.dumps(pp))
    i = s.find('const out = (m)'); j = s.rfind('<script>', 0, i)
    # both parts of the panel on show: the reader sees one at a time, the check reads both
    show = "<script>setTimeout(()=>{['activity','settings'].forEach(n=>{const e=document.getElementById('ap-pane-'+n); if(e) e.style.display='';});},9000)</script>"
    return s[:j] + inj + s[j:].replace('</body>', show + '</body>')

def admin_page(adm):
    css = open(site('styles.css'), encoding='utf-8').read(); js = open(site('admin-panel.js'), encoding='utf-8').read()
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body><div id="admin-panel"></div>'
            f"<script>localStorage.setItem('userId','owner@example.com'); const ADM={json.dumps(adm)};"
            f"window.fetch=async()=>({{ok:true,status:200,json:async()=>ADM}});</script><script>{js}</script></body></html>")

def flags(name, text, selects, settings):
    out = []
    lines = text.splitlines()
    # near-identical lines: names, codes and numbers taken out, what is left must differ
    shape = lambda l: re.sub(r'\b[A-Z0-9][A-Za-z0-9&.\-]*\b', 'X', re.sub(r'[\d$€£¥.,%+\-:()]+', '#', l))
    for sh, n in Counter(shape(l) for l in lines if len(l) > 40).most_common(3):
        if n >= 8:
            ex = next(l for l in lines if shape(l) == sh)
            out.append(f'{name}: {n} lines alike, e.g. "{ex[:110]}": group them or fold them')
    for m in re.finditer(r'\b([A-Z][\w-]+) and ([A-Z][\w-]+) and ([A-Z][\w-]+)\b', text):
        out.append(f'{name}: "{m.group(0)}": write "A, B and C"')
    for m in re.finditer(r'\b1 (such moves|holdings|trades|days|markets|coins|shares|checks)\b', text):
        out.append(f'{name}: "{m.group(0)}": singular')
    if settings and settings.get('aiSell') is not True:
        for pat in ('AI model also reviews each holding', "AI model's latest review", 'AI review: keep', 'may sell it earlier than these rules', 'may sell early again'):
            if pat in text: out.append(f'{name}: describes the AI review\'s early sales, which are switched off: "{pat}"')
    for label, n in selects:
        if n > 20: out.append(f'{name}: the menu "{label}" has {n} choices: offer fewer steps')
    for l in lines:
        m = re.search(r'\b([A-Z][a-z]+ [a-z]{3,})\b.{0,80}\b\1\b', l)
        if m: out.append(f'{name}: "{m.group(1)}" twice in one line: "{l[:110]}"')
    for m in re.finditer(r"(?<!')\b(undefined|NaN|null|\[object Object\]|Infinity)\b(?!')", text):      # a word in quotes is named, not shown (the full check's test names, 23 Oct 2026)
        out.append(f'{name}: "{m.group(0)}" on the page: "{text[max(0, m.start() - 50):m.end() + 30]}"')
    return list(dict.fromkeys(out))

if __name__ == '__main__':
    who = account()
    if not who: sys.exit('no account has the autopilot switched on: nothing to read')
    ap = post(AP, {'action': 'get', 'userId': who}); pp = post(PP, {'action': 'get', 'userId': who}); adm = post(AP, {'action': 'admin', 'userId': who})
    found = []
    t, sel, _ = render(autopilot_page(ap, pp), 'practice-autopilot')
    if len(t) < 500: found.append('the AI autopilot tab could not be drawn for the check (too little text): look at clarity_check.py')
    found += flags('AI autopilot tab', t, sel, ap.get('settings'))
    t2, sel2, _ = render(admin_page(adm), 'admin-panel', 5000)
    if len(t2) < 200: found.append('the Admin page could not be drawn for the check: look at clarity_check.py')
    found += flags('Admin page', t2, sel2, ap.get('settings'))
    # the card the owner opens the Admin page for, read as the page itself draws it (24 Oct 2026: a stale failure kept it at
    # "Yes, please check in" after a session had said all was well): the verdict and its reason, for session_start and the close-out
    lines = t2.splitlines()
    if 'Do you need to check in?' in t2:
        i = next(k for k, l in enumerate(lines) if 'Do you need to check in?' in l)
        print('CHECKIN ' + ' | '.join(lines[i + 1:i + 3]))
    else:
        print('CHECKIN not found on the Admin page')
    print(f'read: the AI autopilot tab ({len(t):,} characters on show) and the Admin page ({len(t2):,})')
    for f in found: print('FLAG ' + f)
    print('nothing reads badly by these tests' if not found else f'{len(found)} to look at')
