"""When each exchange's daily session has finished (12 Nov 2026, Admin #24).

The stock pages say "Data as of D close". The snapshot step used to take the last daily bar it was given as the close, and a bar
dated today is still part of a running session for any exchange that has not closed (BHP.AX and 7203.T read "10 Nov close" with
Sydney and Tokyo still trading). `session_closed(symbol, bar_date, when)` says whether the session of that bar had finished at
`when`; `update_stock_analysis.py` drops a last bar that had not, and `site_audit.py` (`part-day`) checks the pages against the time
they were written.

CLOSE_UTC is the hour (UTC, on the bar's own calendar date) after which the session has certainly finished, taking the later of
summer and winter time so that a bar is never called complete early; the cost of being late is only that a page shows the session
before for a few more hours. An exchange not listed gets DEFAULT_CLOSE (after every exchange has closed)."""
from datetime import datetime, timedelta, timezone

CLOSE_UTC = {
    '': 21.5,                 # US shares and funds (4pm New York: 21:00 UTC in winter)
    '.TO': 21.5, '.V': 21.5, '.MX': 21.5, '.SA': 21.5,
    '.L': 16.5,               # London (4:30pm: 16:30 UTC in winter)
    '.DE': 16.5, '.F': 16.5, '.PA': 16.5, '.AS': 16.5, '.BR': 16.5, '.MI': 16.5, '.MC': 16.5, '.SW': 16.5, '.ST': 16.5,
    '.HE': 16.5, '.CO': 16.5, '.OL': 16.5, '.LS': 16.5, '.VI': 16.5, '.IR': 16.5,
    '.JO': 15.5,              # Johannesburg
    '.AX': 6.5,               # Sydney (4pm: 05:00 UTC in summer, 06:00 in winter)
    '.NZ': 5.5,
    '.T': 7.0,                # Tokyo (3:30pm: 06:30 UTC)
    '.HK': 8.5, '.SS': 7.5, '.SZ': 7.5, '.TW': 6.5, '.TWO': 6.5, '.KS': 7.5, '.KQ': 7.5,
    '.SI': 9.5, '.NS': 10.5, '.BO': 10.5,
    '-USD': 24.0,             # coins: the UTC day is over at midnight
}
DEFAULT_CLOSE = 21.5


def suffix(symbol):
    s = str(symbol or '').upper()
    if s.endswith('-USD'):
        return '-USD'
    if '.' in s:
        return '.' + s.rsplit('.', 1)[1]
    return ''


def close_time(symbol, bar_date):
    """The UTC moment after which the session of `bar_date` (the exchange's own calendar date) has finished."""
    hour = CLOSE_UTC.get(suffix(symbol), DEFAULT_CLOSE)
    return datetime(bar_date.year, bar_date.month, bar_date.day, tzinfo=timezone.utc) + timedelta(hours=hour)


def session_closed(symbol, bar_date, when=None):
    when = when or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when >= close_time(symbol, bar_date)


def only_closed(symbol, dates, *series, when=None, keep=1):
    """(last date, *series) with the last bar dropped when its session had not finished at `when` (and there is more than `keep` left)."""
    if len(dates) > keep and not session_closed(symbol, dates[-1], when):
        dates, series = dates[:-1], tuple(x[:-1] for x in series)
    return (dates[-1],) + tuple(series)
