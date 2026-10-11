"""Creates the worker functions of a NEW share-screener group, each with the one package and a public address.

The group must already have its line in workers/groups.py (name, screener, number of functions, market). Run it through a
packaged script (the session may not create functions any other way):

    check-tools/pending-<name>/deploy.sh:
        #!/bin/bash
        set -euo pipefail
        exec /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/create_group.py stockiq-europe-4-2-worker "$(cd "$(dirname "$0")" && pwd)"

    DRY_RUN=true bash check-tools/pending-<name>/deploy.sh     what it would create; nothing is changed
    bash check-tools/pending-<name>/deploy.sh                  create

Each function is made like the Nikkei workers (read from AWS on 11 Oct 2026): Python 3.12, 256 MB, 60 seconds, handler
lambda_function.lambda_handler, role acp-lambda-role, an address anyone may POST to (the browser calls the workers
directly). A function that exists already is passed over, so it is safe to run twice. The package must be the one that is
live (workers/live.txt): a new group never gets code the other groups do not have. At the end it calls the first and the
last worker through their addresses with three stocks of the market, and writes the addresses, in order, to urls.txt in
the pending folder: they go into the page (allWorkerUrls) and the coordinator (WORKER_URLS).

Written on 11 Oct 2026; its dry run has been run, but it had not yet created a function when these lines were written:
read its output on first use. To remove a group made by mistake: aws lambda delete-function for each name (the owner's
decision; nothing here deletes).
"""
import os, sys, re, json, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); import build, groups as G, deploy
ROLE = 'arn:aws:iam::114366766218:role/acp-lambda-role'

def main():
    if len(sys.argv) < 3: sys.exit('usage: create_group.py <group> <pending folder>   (see the top of this file)')
    group, pending = sys.argv[1], sys.argv[2]; dry = os.environ.get('DRY_RUN', 'false') == 'true'; say = deploy.say
    try:
        if group not in G.GROUPS: raise deploy.Stop(f"{group} has no line in workers/groups.py")
        screener, count, market = G.GROUPS[group]
        zip_path = os.path.join(pending, 'workers.zip'); new = build.build(zip_path); data = open(zip_path, 'rb').read()
        live = open(deploy.LIVE_FILE).read().split()[0]
        if new != live: raise deploy.Stop(f"the package built from workers/ ({new}) is not the one that is live ({live}): deploy that change to the existing groups first")
        aws = deploy.Aws(); lam = aws.lam; listed = aws.functions(); names = [f"{group}-{i}" for i in range(1, count + 1)]
        stray = [n for n in listed if n.startswith(group + '-') and n not in names]
        if stray: raise deploy.Stop(f"functions exist under this group's name that groups.py does not count: {stray[:5]}")
        say(('DRY RUN: nothing will be changed\n' if dry else '') + f"{group} ({screener}): {count} functions wanted, {sum(1 for n in names if n in listed)} exist already")
        urls = []
        for n in names:
            if n in listed:
                if listed[n][0] != live: raise deploy.Stop(f"{n} exists and does not hold the live package")
            elif dry: say(f"   (dry run) would create {n}"); urls.append('(not created)'); continue
            else:
                lam.create_function(FunctionName=n, Runtime='python3.12', Role=ROLE, Handler='lambda_function.lambda_handler', Code={'ZipFile': data}, Timeout=60, MemorySize=256)
                lam.get_waiter('function_active_v2').wait(FunctionName=n)
            try: url = lam.get_function_url_config(FunctionName=n)['FunctionUrl']
            except lam.exceptions.ResourceNotFoundException:
                if dry: say(f"   (dry run) would give {n} an address"); urls.append('(no address yet)'); continue
                url = lam.create_function_url_config(FunctionName=n, AuthType='NONE', Cors={'AllowOrigins': ['*'], 'AllowMethods': ['POST'], 'AllowHeaders': ['*']})['FunctionUrl']
            try: has = 'AllowPublicAccess' in lam.get_policy(FunctionName=n)['Policy']
            except lam.exceptions.ResourceNotFoundException: has = False
            if not has and not dry:                                     # without this the address answers 403
                lam.add_permission(FunctionName=n, StatementId='AllowPublicAccess', Action='lambda:InvokeFunctionUrl', Principal='*', FunctionUrlAuthType='NONE')
            urls.append(url); say(f"   {n}  {url}" + ('' if has or dry else '  (made public)'))
        if dry: say('\nFINISHED (dry run, nothing changed)'); return
        time.sleep(5); batch = G.MARKETS[market]['try_with']
        for i in sorted({0, count - 1}):
            req = urllib.request.Request(urls[i], data=json.dumps({'stock_batch': batch, 'worker_id': i + 1}).encode(), headers={'Content-Type': 'application/json'})
            r = json.loads(urllib.request.urlopen(req, timeout=90).read()); rows = r.get('results') or []
            say(f"   {names[i]} through its address: {len(rows)} of {len(batch)} analysed: " + ', '.join(f"{x['symbol']} {x['price']} {x.get('currency')} score {x['score']:+.1f}" for x in rows))
            if len(rows) != len(batch) or any(x.get('currency') != G.MARKETS[market]['currency'] for x in rows):
                raise deploy.Stop(f"{names[i]} did not answer as expected through its address (a 403 means the public permission is missing; a wrong currency means groups.py names the wrong market)")
        open(os.path.join(pending, 'urls.txt'), 'w').write('\n'.join(urls) + '\n')
        say(f"\nthe {count} addresses, in order, are in {os.path.join(pending, 'urls.txt')}\nFINISHED")
    except deploy.Stop as e:
        say(f"\nSTOPPED: {e}\nNothing further was changed."); sys.exit(1)

if __name__ == '__main__':
    main()
