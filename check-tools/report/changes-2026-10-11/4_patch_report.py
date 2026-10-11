"""Fourth step for the single-stock report function: the latest article's time in the visitor's own time zone, as the
stock pages show it (the report printed the page's UTC text), and the time zone named beside "Analysis Generated".
    python3 patch_report4.py <live lambda_function2.py> <out lambda_function2.py>"""
import sys
src = open(sys.argv[1]).read()
def swap(text, old, new):
    assert text.count(old) == 1, (text.count(old), old[:80])
    return text.replace(old, new)

src = swap(src, '''        date_match = re.search(r'data-timestamp="[^"]+"[^>]*>([^<]+)</p>', news_html)\n''',
           '''        date_match = re.search(r'data-timestamp="[^"]+"[^>]*>([^<]+)</p>', news_html)\n        stamp_match = re.search(r'data-timestamp="([^"]+)"', news_html)\n''')
src = swap(src, '''                'date': date_match.group(1).strip() if date_match else '',\n''',
           '''                'date': date_match.group(1).strip() if date_match else '',\n                'timestamp': stamp_match.group(1) if stamp_match else None,\n''')
src = swap(src, '''        if recent_news.get('date'):\n            analysis.append(f"\\n{recent_news['date']}")\n''',
           '''        if recent_news.get('date'):\n            analysis.append(f"\\n{local_news_date(recent_news, timezone_offset)}")\n''')
src = swap(src, '''    analysis.append(f"\\n🕐 Analysis Generated: {timestamp}")\n''',
           '''    analysis.append(f"\\n🕐 Analysis Generated: {timestamp} ({zone_label(timezone_offset)})")\n''')
src = swap(src, 'def fetch_recent_news_from_stock_page(symbol):', r'''def zone_label(timezone_offset):
    """The visitor's time zone as the site writes it: GMT+7, GMT-4, GMT+5:30. With no offset sent, the zone the
    report's own time falls back to (get_user_timezone_timestamp: five hours behind UTC)."""
    try:
        offset = float(timezone_offset) if timezone_offset is not None else -5.0
    except (TypeError, ValueError):
        offset = -5.0
    hours = int(abs(offset))
    minutes = int(round((abs(offset) - hours) * 60))
    return f"GMT{'+' if offset >= 0 else '-'}{hours}" + (f":{minutes:02d}" if minutes else '')

def local_news_date(recent_news, timezone_offset):
    """The article's time in the visitor's own time zone, written as the stock pages write it for him
    (js/timezone-converter.js): "Thu, October 8, 2026 at 8:31 PM GMT+7 4 min read". The report used to print the page's
    own text, which is UTC. Left as the page has it when the visitor's offset or the article's time is not known."""
    original = recent_news.get('date') or ''
    try:
        if timezone_offset is None or not recent_news.get('timestamp'):
            return original
        offset = float(timezone_offset)
        if not -14 <= offset <= 14:
            return original
        from datetime import timezone
        when = datetime.fromisoformat(str(recent_news['timestamp']).replace('Z', '+00:00'))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        local = when.astimezone(timezone(timedelta(hours=offset)))
        clock = f"{local.hour % 12 or 12}:{local.minute:02d} {'AM' if local.hour < 12 else 'PM'}"
        text = f"{local.strftime('%a')}, {local.strftime('%B')} {local.day}, {local.year} at {clock} {zone_label(offset)}"
        read_time = re.search(r'\d+ min read', original)
        return text + (' ' + read_time.group(0) if read_time else '')
    except Exception:
        return original

def fetch_recent_news_from_stock_page(symbol):''')
compile(src, 'lambda_function2.py', 'exec'); open(sys.argv[2], 'w').write(src); print('written:', len(src.split('\n')), 'lines')
