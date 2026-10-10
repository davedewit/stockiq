#!/bin/bash
# One-off deploy of the crypto top-10 history fix (built and tested locally on 10 Oct 2026).
# What it is and why: .kiro/steering/site-overview.md, section 11 ("Crypto top-10 history").
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice: each step first checks whether it has already been done, and stops if the live
# code or a website file is not what this fix was built against.
#
# Roll back: the previous Lambda code is saved in ~/VSCODE/backup/<function>_before_top10_history_20261010.zip
#   aws lambda update-function-code --function-name <function> --zip-file fileb://<that zip> --profile default --region us-east-1
# Website files: git checkout the four files in ~/VSCODE/website and upload them again.
# Schedule: aws events put-targets --rule stockiq-coinspot-predictions-schedule \
#   --targets "Id=1,Arn=arn:aws:lambda:us-east-1:114366766218:function:stockiq-coinspot-predictions-updater" (and rate(15 minutes))
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AWS=(aws --profile default --region us-east-1)
WEB=/Users/dave/VSCODE/website
MIRROR=/Users/dave/VSCODE/stockiq/lambda-sync
BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h
DIST=EHXV50CPHY07R
ACCOUNT=114366766218
ORCH=stockiq-option-7-1-orchestrator
COORD=stockiq-screener-coordinator
RULE=stockiq-coinspot-predictions-schedule
ORCH_URL=https://5fyemil3eipbwqyyb2kloijyhi0uvtct.lambda-url.us-east-1.on.aws/
DRY="${DRY_RUN:-false}"
TMP="$(mktemp -d)"

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
run()  { if [ "$DRY" = "true" ]; then echo "(dryrun) $*"; else "$@"; fi; }

if pgrep -f "deploy-to-s3.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

# deploy_lambda <function> <file inside the zip> <new file> <CodeSha256 the fix was built against>
deploy_lambda() {
    local name="$1" main="$2" new="$3" expected="$4" work="$TMP/$1"
    say "$name"
    mkdir -p "$work/live"
    curl -s -o "$work/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$name" --query Code.Location --output text)"
    unzip -q -o "$work/live.zip" -d "$work/live"
    if cmp -s "$work/live/$main" "$new"; then echo "already deployed, skipping"; return 0; fi
    local live_sha; live_sha="$("${AWS[@]}" lambda get-function-configuration --function-name "$name" --query CodeSha256 --output text)"
    [ "$live_sha" = "$expected" ] || stop "$name has changed on AWS since this fix was built (code $live_sha)"
    run cp "$work/live.zip" "$BACKUP/${name}_before_top10_history_20261010.zip"
    cp "$new" "$work/live/$main"
    (cd "$work/live" && zip -q -X "$work/new.zip" ./*.py)
    echo "new package: $(unzip -Z1 "$work/new.zip" | tr '\n' ' ')"
    run "${AWS[@]}" lambda update-function-code --function-name "$name" --zip-file "fileb://$work/new.zip" --query LastModified --output text
    run "${AWS[@]}" lambda wait function-updated --function-name "$name"
    run cp "$new" "$MIRROR/$name/$main"
}

# 1. Crypto orchestrator: one coin list and ranking for both the user's run and the scheduled check
deploy_lambda "$ORCH" orchestrator.py "$HERE/lambda/orchestrator.py" "TExoKUEFBY8CMdMJMz2b3/7oECXMfJ205UD0uraBQck="

# 2. Schedule: run the orchestrator itself every 30 minutes (the old updater is left in place, unused)
say "schedule $RULE"
if "${AWS[@]}" lambda get-policy --function-name "$ORCH" --query Policy --output text 2>/dev/null | grep -q AllowTop10HistorySchedule; then
    echo "permission already in place"
else
    run "${AWS[@]}" lambda add-permission --function-name "$ORCH" --statement-id AllowTop10HistorySchedule \
        --action lambda:InvokeFunction --principal events.amazonaws.com \
        --source-arn "arn:aws:events:us-east-1:$ACCOUNT:rule/$RULE" --query Statement --output text
fi
run "${AWS[@]}" events put-rule --name "$RULE" --schedule-expression "rate(30 minutes)" --state ENABLED \
    --description "Record the crypto top 10 every 30 minutes (runs $ORCH)" --query RuleArn --output text
run "${AWS[@]}" events put-targets --rule "$RULE" \
    --targets "Id=1,Arn=arn:aws:lambda:us-east-1:$ACCOUNT:function:$ORCH" --query FailedEntryCount --output text

# 3. First history check now, so reports have something to show straight away
say "first top-10 history check"
run "${AWS[@]}" lambda invoke --function-name "$ORCH" --cli-binary-format raw-in-base64-out --cli-read-timeout 180 \
    --payload '{"scheduled_history_check": true}' "$TMP/first_check.json" --query StatusCode --output text
[ -f "$TMP/first_check.json" ] && cat "$TMP/first_check.json" && echo

# 4. Background coordinator: CSV column renamed to Top10_Status
deploy_lambda "$COORD" lambda_function.py "$HERE/lambda/coordinator_lambda_function.py" "SiObCBxPhxRP8ro5rHwdBK5N5m2UjRi6P+CyoraMqug="

# 5. Website files
say "website files"
check_web() {   # <file> <sha256 of the version the fix was built against>
    local f="$1" expected="$2" have
    if cmp -s "$WEB/$f" "$HERE/web/$f"; then echo "$f: already copied"; return 0; fi
    have="$(shasum -a 256 "$WEB/$f" | cut -d' ' -f1)"
    [ "$have" = "$expected" ] || stop "$WEB/$f has changed since this fix was built"
    run cp "$HERE/web/$f" "$WEB/$f"
}
check_web crypto-filter-buttons.js 9564217d66eea781a3977c2c7eb728b823a070825a143c33dd5df0051625441a
check_web analysis-functions.js    7dc48fa061451e28148d6893e1e36a36a34c7010382cd692e3f24c0526677b8b
check_web analysis.html            9850fe8e41d9239fda8b5be8137021a8df5b6f9dbefbe65da498bfdaacedd166
check_web dashboard.html           19b7d1344d535efc35dbbef3aede532b42bed09b7e0ee3d15d6307dd48461400
for f in crypto-filter-buttons.js analysis-functions.js; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=86400"
done
for f in analysis.html dashboard.html; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=3600" --content-type "text/html; charset=utf-8"
done
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" \
    --paths /crypto-filter-buttons.js /analysis-functions.js /analysis.html /dashboard.html --query Invalidation.Status --output text

# 6. A normal user run, to show what a report looks like now
if [ "$DRY" != "true" ]; then
    say "sample report (a normal user run)"
    curl -s -m 180 -X POST "$ORCH_URL" -H 'Content-Type: application/json' -d '{"threshold":0.25}' \
        | python3 -c "import sys,json,re; d=json.load(sys.stdin); r=re.sub(r'<[^>]+>','',d['report']); i=r.index('Processing Time'); print(d['total_coins'],'coins ranked'); print(r[i:i+900])"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
