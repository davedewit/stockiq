#!/usr/bin/env python3
"""What AWS costs, looked at every day, for free (25 Oct 2026; the owner: "if no cost probably no harm you doing a quick check on the
scripted runs daily? just to see if we have anomolies or higher cost"). Run by site_audit.py in the daily update, so a finding reaches
the daily email and the Admin page; also by hand: python3 check-tools/cost_check.py

Only CloudWatch's figures (GetMetricStatistics and ListMetrics: about 40 requests a day, inside its free million). NEVER Cost Explorer
(a cent a question: the owner's rule). What it flags:
  - a service whose spend yesterday was well above its usual day (the bill's own figures, by service)
  - the month's running cost over, or on course for over, the owner's $1 (Cost Explorer's known charge of 17 Oct left out)
  - any new Cost Explorer charge
  - a table whose reads or writes jumped, or that reads more than 40,000 units a day (25 Oct: a cleanup scanning a table 64 times a day)
  - Lambda calls jumping, or on course for the free million a month
"""
import datetime as dt
import statistics

ACCOUNT = '114366766218'
LIMIT, HARD = 1.00, 1.50              # the owner's monthly target for StockIQ's running cost, and his most in a heavy month
KNOWN_CE = {'2026-10': 2.65}          # Cost Explorer charge already explained (the session's tests of 17 Oct 2026)
# a finding already fixed, left out until its old days have passed (then checked again as usual)
FIXED_UNTIL = {'stockiq-dashboard-analysis-history': '2026-10-27',   # the cleanup's 64 scans a day, fixed 25 Oct 13:20 UTC
               'AmazonCloudFront': '2026-11-02',                     # one path per file, fixed 26 Oct; then each '/*' cost $0.005 while October was over the free 1,000 (KNOWN_PATHS)
               'AmazonS3': '2026-10-28'}                             # the one-off re-upload of ~3,000 stock pages on 24 Oct
# A month over the owner's $1.50 whose cause is found and fixed: known up to this amount, so it stops calling him in (31 Oct 2026, the owner:
# "seems suddenly alot to check on admin dashboard especially the bill?"). Beyond the amount it is a problem again. admin.py sync copies
# this to the Admin page, whose "Do you need to check in?" card reads it. Add a month only when its cause is fixed, with the reason.
KNOWN_OVER = {'2026-10': {'upTo': 1.65, 'why': "two faults of 23-26 Oct, both fixed: a cleanup that read the whole reports table 64 times a day, "
                                               "and a cache clear for every file deployed (125 paths over the free 1,000)"}}
# A table's reads with a known cause, as a note rather than a problem up to this many units a day
KNOWN_READS = {'stockiq-dashboard-analysis-history': (150000, 'about 400 read units each time the dashboard is loaded (it reads every report '
                                                               'with its text): idea history-light')}
TABLE_FLOOR = 0.10    # a table matters from about 10 cents a month: below that a busy day of page refreshes is not a problem
KNOWN_PATHS = {'2026-10': 1125}     # cache-clear paths already explained for the month (the per-file clears of 23-25 Oct, then one '/*' a deploy; resets 1 Nov)
TABLES = ['stockiq-dashboard-analysis-history', 'stockiq-ai-trader', 'stockiq-user-tracking', 'stockiq-paper-portfolios',
          'stockiq-ai-trader-journal', 'stockiq-coinspot-prediction-status', 'stockiq-coinspot-predictions', 'stockiq-usage-tracker',
          'stockiq-email-subscribers', 'stockiq-ai-chat-limits', 'stockiq-ai-chat-stats']


def daily(cw, ns, metric, dims, days=9, stat='Sum'):
    end = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    pts = cw.get_metric_statistics(Namespace=ns, MetricName=metric, Dimensions=dims, StartTime=end - dt.timedelta(days=days),
                                   EndTime=end, Period=86400, Statistics=[stat])['Datapoints']
    return [p[stat] for p in sorted(pts, key=lambda p: p['Timestamp'])]     # whole days, oldest first, yesterday last


def jumped(series, floor):
    """yesterday against the days before: True when well above the usual and above a floor that matters"""
    if len(series) < 4:
        return False
    last, usual = series[-1], statistics.median(series[:-1])
    return last >= floor and last > max(2.5 * usual, usual + floor)


def run():
    import boto3
    cw = boto3.Session(profile_name='default', region_name='us-east-1').client('cloudwatch')
    out = []
    now = dt.datetime.now(dt.timezone.utc)

    # 1. the bill by service (cumulative over the month, so a day's spend is the rise from one day to the next)
    running, ce = 0.0, 0.0
    for mt in cw.list_metrics(Namespace='AWS/Billing', MetricName='EstimatedCharges')['Metrics']:
        d = {x['Name']: x['Value'] for x in mt['Dimensions']}
        if d.get('LinkedAccount') != ACCOUNT or 'ServiceName' not in d:
            continue
        cum = daily(cw, 'AWS/Billing', 'EstimatedCharges', mt['Dimensions'], days=10, stat='Maximum')
        if not cum:
            continue
        latest = cw.get_metric_statistics(Namespace='AWS/Billing', MetricName='EstimatedCharges', Dimensions=mt['Dimensions'],
                                          StartTime=now - dt.timedelta(days=2), EndTime=now, Period=21600, Statistics=['Maximum'])['Datapoints']
        latest = max(latest, key=lambda p: p['Timestamp'])['Maximum'] if latest else cum[-1]   # the month so far, as the opening check reads it
        if d['ServiceName'] == 'AWSCostExplorer':
            ce = latest
            continue
        running += latest
        rises = [b - a for a, b in zip(cum, cum[1:]) if b >= a]          # a fall is the month starting again
        if jumped(rises, 0.02) and now.strftime('%Y-%m-%d') >= FIXED_UNTIL.get(d['ServiceName'], ''):
            out.append(('problem', f"{d['ServiceName']} cost ${rises[-1]:.2f} yesterday, against about ${statistics.median(rises[:-1]):.2f} a day "
                                   f"before: find what changed (CloudWatch usage of that service, the day's deploys)"))
    known = KNOWN_CE.get(now.strftime('%Y-%m'), 0)
    if ce > known + 0.01:
        out.append(('problem', f"Cost Explorer has been charged ${ce - known:.2f} this month beyond the known amount: something asks it "
                               f"(aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventSource,AttributeValue=ce.amazonaws.com)"))
    days_in = now.day + now.hour / 24
    month_days = ((now.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)).day
    on_course = running / max(days_in, 1) * month_days
    over = KNOWN_OVER.get(now.strftime('%Y-%m'))
    if running >= HARD and over and running <= over['upTo']:
        out.append(('idea', f"StockIQ's running AWS cost this month is ${running:.2f}, over the owner's ${HARD:.2f}: known ({over['why']}); "
                            f"a problem again above ${over['upTo']:.2f}"))
    elif running >= HARD:
        out.append(('problem', f"StockIQ's running AWS cost this month is ${running:.2f}, over the owner's ${HARD:.2f} at most"))
    elif running >= LIMIT:
        out.append(('idea', f"StockIQ's running AWS cost this month is ${running:.2f}, over the owner's ${LIMIT:.2f} target (his most is ${HARD:.2f})"))
    elif now.day >= 7 and on_course > LIMIT * 1.1:
        out.append(('idea', f"StockIQ's running AWS cost is on course for about ${on_course:.2f} this month (${running:.2f} so far), over the owner's ${LIMIT:.2f}"))

    # 2. the database, table by table
    for t in TABLES:
        for metric, word in (('ConsumedReadCapacityUnits', 'read'), ('ConsumedWriteCapacityUnits', 'write')):
            s = daily(cw, 'AWS/DynamoDB', metric, [{'Name': 'TableName', 'Value': t}])
            if not s or now.strftime('%Y-%m-%d') < FIXED_UNTIL.get(t, ''):
                continue
            price = 0.125 if word == 'read' else 0.625
            floor = TABLE_FLOOR * 1e6 / 30 / price           # units a day that cost TABLE_FLOOR a month
            if jumped(s, floor) or (word == 'read' and s[-1] > 40000) or (word == 'write' and s[-1] > 20000):
                known_r = KNOWN_READS.get(t) if word == 'read' else None
                level = 'idea' if known_r and s[-1] <= known_r[0] else 'problem'
                cause = f"known: {known_r[1]}" if level == 'idea' else 'find what does it (a scan in a loop?)'
                out.append((level, f"table {t}: {s[-1]:,.0f} {word} units yesterday (usual about {statistics.median(s[:-1] or [0]):,.0f}), "
                                   f"about ${s[-1] * 30 * price / 1e6:.2f} a month at that rate: {cause}"))

    # 3. Lambda calls for the whole account (one figure, no dimension)
    s = daily(cw, 'AWS/Lambda', 'Invocations', [], days=9)
    if s:
        if jumped(s, 5000):
            out.append(('problem', f"Lambda calls jumped to {s[-1]:,.0f} yesterday (usual about {statistics.median(s[:-1]):,.0f}): find which function"))
        if statistics.mean(s[-3:]) * 30 > 900000:
            out.append(('problem', f"Lambda calls on course for about {statistics.mean(s[-3:]) * 30:,.0f} a month, near the free million"))
    # 4. CloudFront cache clears: 1,000 paths a month free, then $0.005 a path ("/*" is one). 25 Oct 2026: one path per file in the
    # one-off deploys cost $0.39. Listing and reading clears is free; a clear never changes, so its count is kept (audit/cf_paths.json)
    try:
        import json, os
        keep = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audit', 'cf_paths.json')
        known = json.load(open(keep)) if os.path.exists(keep) else {}
        cf = boto3.Session(profile_name='default', region_name='us-east-1').client('cloudfront')
        month, paths = now.strftime('%Y-%m'), 0
        for page in cf.get_paginator('list_invalidations').paginate(DistributionId='EHXV50CPHY07R'):
            for i in page['InvalidationList'].get('Items', []):
                if i['CreateTime'].strftime('%Y-%m') != month:
                    continue
                if i['Id'] not in known:
                    known[i['Id']] = cf.get_invalidation(DistributionId='EHXV50CPHY07R', Id=i['Id'])['Invalidation']['InvalidationBatch']['Paths']['Quantity']
                paths += known[i['Id']]
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        json.dump(known, open(keep, 'w'))
        # beyond what is already explained, by more than a few deploys' '/*' (20 paths, 10 cents): it fired at exactly the known 1,125,
        # then at 1,126 for one deploy's half cent (31 Oct 2026). What it is for is a deploy clearing file by file again.
        if paths >= 700 and paths > KNOWN_PATHS.get(month, 0) + (20 if month in KNOWN_PATHS else 0):
            out.append(('problem' if paths >= 1000 else 'idea', f"{paths:,} CloudFront cache-clear paths this month (1,000 are free, then $0.005 each): "
                        f"a deploy should clear '/*' once, not each file (web_deploy.sh)"))
    except Exception as e:
        out.append(('idea', f'could not count the CloudFront cache clears: {e}'))
    return out, running


if __name__ == '__main__':
    found, running = run()
    print(f"StockIQ's running AWS cost this month: ${running:.2f}")
    for level, text in found:
        print(f'  [{level}] {text}')
    if not found:
        print('  nothing unusual')
