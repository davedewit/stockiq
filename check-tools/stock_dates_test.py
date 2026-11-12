#!/usr/bin/env python3
"""Tests for the stock pages' data dates (Admin #24, 12 Nov 2026): session_hours.py (when a session has finished), the dropping of an
unfinished last bar, and the re-fetch of a share that is a session behind its exchange. Nothing is downloaded.
    python3 check-tools/stock_dates_test.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from datetime import date, datetime, timezone
from session_hours import session_closed, only_closed, suffix
fails = []
def check(name, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else '   ' + str(detail)[:200]))
    if not ok: fails.append(name)
t = lambda h, m=0, d=10: datetime(2026, 11, d, h, m, tzinfo=timezone.utc)
cases = [('BHP.AX', date(2026, 11, 10), t(3), False), ('BHP.AX', date(2026, 11, 10), t(7), True), ('7203.T', date(2026, 11, 10), t(6, 45), False),
         ('7203.T', date(2026, 11, 10), t(7, 5), True), ('AAPL', date(2026, 11, 9), t(1, 0, 10), True), ('AAPL', date(2026, 11, 10), t(17), False),
         ('AAPL', date(2026, 11, 10), t(22), True), ('SHEL.L', date(2026, 11, 10), t(15), False), ('SAP.DE', date(2026, 11, 10), t(17), True),
         ('BTC-USD', date(2026, 11, 10), t(23), False), ('BTC-USD', date(2026, 11, 9), t(1, 0, 10), True), ('0700.HK', date(2026, 11, 10), t(9), True),
         ('ODD.XX', date(2026, 11, 10), t(20), False), ('ODD.XX', date(2026, 11, 10), t(22), True), ('BRK-B', date(2026, 11, 10), t(20), False)]
bad = [c[:3] for c in cases if session_closed(c[0], c[1], c[2]) != c[3]]
check(f'{len(cases)} sessions are called finished or not at the right hour', not bad, bad)
check('a symbol\'s exchange is read from its ending', (suffix('AAPL'), suffix('BRK-B'), suffix('0700.HK'), suffix('SHEL.L'), suffix('SUI20947-USD')) == ('', '', '.HK', '.L', '-USD'))
d = [date(2026, 11, 9), date(2026, 11, 10)]
check('an unfinished last bar is dropped from every series and the date moves back', only_closed('BHP.AX', d, [1.0, 2.0], [3.0, 4.0], when=t(3)) == (date(2026, 11, 9), [1.0], [3.0]))
check('a finished last bar is kept', only_closed('BHP.AX', d, [1.0, 2.0], when=t(8)) == (date(2026, 11, 10), [1.0, 2.0]))
check('a lone bar is never dropped (nothing would be left)', only_closed('BHP.AX', [date(2026, 11, 10)], [1.0], when=t(3)) == (date(2026, 11, 10), [1.0]))

import update_stock_analysis as u
d1, d2 = date(2026, 11, 6), date(2026, 11, 9)
bar = lambda day, px=1: (day, [px], [px], [px], [px])
P = {'AAPL': bar(d1), 'MSFT': bar(d2), 'KO': bar(d1), 'SHEL.L': bar(d1), 'BP.L': bar(d1), 'TINY': bar(d1)}
asked = []
def fetch(syms):
    asked.append(sorted(syms)); return {'AAPL': bar(d2, 2), 'KO': bar(d1)}
r = u.refetch_behind(P, lambda s: s != 'TINY', skip={'KO'}, fetch=fetch)
check('only a near share that is behind its own exchange\'s newest bar is asked for', asked == [['AAPL']] and r == (1, 1), (asked, r))
check('a newer bar replaces the old one; the others stay', P['AAPL'][0] == d2 and P['AAPL'][1] == [2] and P['KO'][0] == d1 and P['SHEL.L'][0] == d1)
Q = {'A': bar(d1), 'B': bar(d2)}
u.refetch_behind(Q, lambda s: True, fetch=lambda syms: {'A': bar(d1)})
check('an answer that is no newer changes nothing', Q['A'][0] == d1)
check('a market where every share is level asks for nothing', u.refetch_behind({'X.L': bar(d1), 'Y.L': bar(d1)}, lambda s: True, fetch=lambda s: (_ for _ in ()).throw(AssertionError('asked'))) == (0, 0))
print('ALL PASS' if not fails else f'SOME FAILED ({len(fails)})'); sys.exit(1 if fails else 0)
