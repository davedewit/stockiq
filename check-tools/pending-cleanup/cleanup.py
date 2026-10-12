"""Deletes worker functions that nothing calls (12 Oct 2026, at the owner's word: "if you are 100% never used… go ahead and delete").

Two groups only: stockiq-option-7-4-worker-1..139 (no call at all in the 455 days CloudWatch keeps) and
stockiq-option-3-worker-1..5 (called on three days in September 2025, when they were made, and never since). Neither
group's addresses or names appear in any page or script of the site, in the scripts repository or in any other function's
code. NOT touched, on purpose: stockiq-option-3-3-worker (60: the old S&P 500 path, called about once a month until 11
Sep 2026), stockiq-option-7-2-worker-1 and stockiq-coinspot-predictions-updater (in use until this month).

Before a function is deleted this checks, for that function, now: its name is on the list; it has had no call in the last
365 days; no schedule or event source points at it; its code is in the full copy of 11 Oct 2026 with the same
fingerprint. Its settings, address and permissions are written to ~/VSCODE/backup/deleted_functions_20261012/, so it
can be made again (the README there says how). Any check that fails stops the run before anything more is deleted.

    DRY_RUN=true bash check-tools/pending-cleanup/deploy.sh     what it would delete; nothing is changed
    bash check-tools/pending-cleanup/deploy.sh                  delete
Safe to run twice (a function already gone is passed over).
"""
import os, sys, json, csv, datetime as dt
import boto3
DRY = os.environ.get('DRY_RUN', 'false') == 'true'
FULL = os.path.expanduser('~/VSCODE/backup/lambda_full_20261011_before_one_worker_code')
KEEP = os.path.expanduser('~/VSCODE/backup/deleted_functions_20261012')
NAMES = [f'stockiq-option-7-4-worker-{i}' for i in range(1, 140)] + [f'stockiq-option-3-worker-{i}' for i in range(1, 6)]

def stop(why): print(f'\nSTOPPED: {why}\nNothing further was changed.'); sys.exit(1)

def main():
    s = boto3.Session(profile_name='default', region_name='us-east-1'); lam, cw, ev = s.client('lambda'), s.client('cloudwatch'), s.client('events')
    print(('DRY RUN: nothing will be changed\n' if DRY else '') + f'{len(NAMES)} functions on the list')
    saved = {r['function']: r for r in csv.DictReader(open(os.path.join(FULL, 'functions.tsv')), delimiter='\t')}
    live = {}
    for page in lam.get_paginator('list_functions').paginate():
        for f in page['Functions']: live[f['FunctionName']] = f
    print(f'{len(live)} functions in the account before')
    targets = set()
    for page in ev.get_paginator('list_rules').paginate():
        for rule in page['Rules']:
            for t in ev.list_targets_by_rule(Rule=rule['Name'])['Targets']: targets.add(t['Arn'].split(':function:')[-1].split(':')[0])
    sources = set()
    for page in lam.get_paginator('list_event_source_mappings').paginate():
        for m in page['EventSourceMappings']: sources.add(m['FunctionArn'].split(':function:')[-1].split(':')[0])
    print(f'schedules point at: {sorted(targets)}; event sources at: {sorted(sources) or "none"}')
    end = dt.datetime.now(dt.timezone.utc); start = end - dt.timedelta(days=365); todo = []
    for n in NAMES:
        if n not in live: continue
        f = live[n]
        if n in targets or n in sources: stop(f'{n} is the target of a schedule or an event source')
        r = cw.get_metric_statistics(Namespace='AWS/Lambda', MetricName='Invocations', Dimensions=[{'Name': 'FunctionName', 'Value': n}], StartTime=start, EndTime=end, Period=86400, Statistics=['Sum'])
        calls = sum(p['Sum'] for p in r['Datapoints'])
        if calls: stop(f'{n} was called {int(calls)} times in the last 365 days')
        b = saved.get(n)
        if not b or b['CodeSha256'] != f['CodeSha256'] or not os.path.exists(os.path.join(FULL, 'packages', b['package'])): stop(f'{n}: its code is not in the full copy of 11 Oct 2026 with the same fingerprint')
        todo.append(n)
    print(f'{len(todo)} still exist and pass every check (no call in 365 days, nothing points at them, code kept); {len(NAMES) - len(todo)} are gone already')
    if DRY:
        for n in todo[:3] + todo[-2:]: print('   (dry run) would delete', n)
        print(f'   … {len(todo)} in all\nFINISHED (dry run, nothing changed)'); return
    os.makedirs(KEEP, exist_ok=True); done = 0
    for n in todo:
        cfg = lam.get_function_configuration(FunctionName=n); cfg.pop('ResponseMetadata', None)
        try: url = lam.get_function_url_config(FunctionName=n); url.pop('ResponseMetadata', None)
        except lam.exceptions.ResourceNotFoundException: url = None
        try: policy = json.loads(lam.get_policy(FunctionName=n)['Policy'])
        except lam.exceptions.ResourceNotFoundException: policy = None
        json.dump({'configuration': cfg, 'url': url, 'policy': policy, 'package': saved[n]['package']}, open(os.path.join(KEEP, n + '.json'), 'w'), indent=1, default=str)
        lam.delete_function(FunctionName=n); done += 1                 # its address and permissions go with it
        if done % 25 == 0: print(f'   {done} deleted')
    open(os.path.join(KEEP, 'README.txt'), 'w').write(
        "Functions deleted on 12 Oct 2026 because nothing called them (see stockiq/.kiro/steering/site-overview.md, section 8b).\n"
        "One .json per function: its settings, its address and permissions as they were, and the name of its code package in\n"
        "~/VSCODE/backup/lambda_full_20261011_before_one_worker_code/packages/. To make one again: aws lambda create-function with\n"
        "the runtime, role, handler, memory and timeout from 'configuration' and --zip-file fileb://<that package>; then\n"
        "create-function-url-config and add-permission as in 'url' and 'policy'. Its address will be a new one.\n")
    after = sum(len(p['Functions']) for p in lam.get_paginator('list_functions').paginate())
    print(f'{done} deleted; their settings are in {KEEP}\n{after} functions in the account now\nFINISHED')

if __name__ == '__main__':
    main()
