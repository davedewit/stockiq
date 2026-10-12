#!/bin/bash
# One-off deploy (12 Oct 2026): a diary of the autopilot that is never trimmed.
# The autopilot's record keeps the last 80 lines of its activity list (about three days of them for an account with many
# holdings) and the last 300 finished trades. For a review every week or two that is too little: why it bought and sold,
# what it left alone and which settings were in force at the time are gone before anyone reads them. From now on every
# activity line, every finished trade and every change of the settings is also written, once, to a table of its own,
# stockiq-ai-trader-journal (key: the account and the time; pay per request, a few hundred small rows a day).
# Nothing reads it while trading and no trading rule changes. The review tool reads it: check-tools/autopilot_review.py.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice. Stops if the live function is not the code this was built from.
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_journal_20261012.zip (the table can stay: the older
# function does not know it).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-ai-trader; BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-ai-trader; TABLE=stockiq-ai-trader-journal
WAS="dRaKpUf9FPnFzz/Y4owNWcfzqxX4Cq2pVZYBv0884Fs="
OLD_FILE=71d6ca2a8918e994f56db6748ab27e50dbf594924e8560c774ad4f73ae31e1cc
NEW_FILE=9ea294a219ca74a535c3842b7038a54968bdc5da92c6c71e67dc0d72dd315c4d
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"
M=$((10#$(date +%M)))
if [ "$DRY" != "true" ] && { { [ $M -ge 8 ] && [ $M -le 13 ]; } || { [ $M -ge 38 ] && [ $M -le 43 ]; }; }; then stop "it is within a few minutes of :10 or :40, when the autopilot's schedule runs: run this again in five minutes"; fi

say "checks before anything is changed"
[ "$(filesha "$HERE/lambda/lambda_function.py")" = "$NEW_FILE" ] || stop "the staged function is not the one that was tested"
curl -s -o "$TMP/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$F" --query Code.Location --output text)"
mkdir -p "$TMP/live"; unzip -q -o "$TMP/live.zip" -d "$TMP/live"
[ "$(unzip -Z1 "$TMP/live.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "the package holds other files than lambda_function.py"
if [ "$(filesha "$TMP/live/lambda_function.py")" = "$NEW_FILE" ]; then STATE=new; echo "the function already has the new code"
else
    STATE=old
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$WAS" ] && [ "$(filesha "$TMP/live/lambda_function.py")" = "$OLD_FILE" ] || stop "$F has changed on AWS since this was built"
    cmp -s "$TMP/live/lambda_function.py" "$MIRROR/lambda_function.py" || stop "the live function is not the same as the local mirror"
    echo "live is the code this was built from"
fi
python3 -W ignore "$ROOT/check-tools/ai_trader_test.py" "$HERE/lambda/lambda_function.py" 2>/dev/null | tail -1 | tee "$TMP/t"; grep -q "ALL PASS" "$TMP/t" || stop "the autopilot's tests do not pass on the staged function"

say "the table $TABLE (before the function, so that its first write finds it)"
if "${AWS[@]}" dynamodb describe-table --table-name "$TABLE" --query Table.TableStatus --output text >/dev/null 2>&1; then echo "exists already: $("${AWS[@]}" dynamodb describe-table --table-name "$TABLE" --query 'Table.[TableStatus,BillingModeSummary.BillingMode]' --output text)"
elif [ "$DRY" = "true" ]; then echo "(dry run) would create it: key userId + at, pay per request"
else
    "${AWS[@]}" dynamodb create-table --table-name "$TABLE" --attribute-definitions AttributeName=userId,AttributeType=S AttributeName=at,AttributeType=S \
        --key-schema AttributeName=userId,KeyType=HASH AttributeName=at,KeyType=RANGE --billing-mode PAY_PER_REQUEST --query Table.TableStatus --output text
    "${AWS[@]}" dynamodb wait table-exists --table-name "$TABLE"; echo "created: $("${AWS[@]}" dynamodb describe-table --table-name "$TABLE" --query Table.TableStatus --output text)"
fi

say "$F"
if [ "$STATE" = new ]; then echo "already deployed, skipping"
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${F}_before_autopilot_journal_20261012.zip and update the function"
else
    [ -f "$BACKUP/${F}_before_autopilot_journal_20261012.zip" ] || cp "$TMP/live.zip" "$BACKUP/${F}_before_autopilot_journal_20261012.zip"
    cp "$HERE/lambda/lambda_function.py" "$TMP/lambda_function.py"; (cd "$TMP" && zip -q -X new.zip lambda_function.py)
    "${AWS[@]}" lambda update-function-code --function-name "$F" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$F"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new.zip")" ] || stop "the function does not report the new package"
    cp "$HERE/lambda/lambda_function.py" "$MIRROR/lambda_function.py"; echo "live ($(zipsha "$TMP/new.zip")), and the mirror updated"
    say "the live function answers (the page's read-only question, for an address that has no autopilot: nothing is written)"
    python3 - <<'PY'
import boto3, json
lam = boto3.Session(profile_name='default', region_name='us-east-1').client('lambda')
r = lam.invoke(FunctionName='stockiq-ai-trader', Payload=json.dumps({'requestContext': {}, 'body': json.dumps({'action': 'get', 'userId': 'nobody-deploy-check@example.com'})}).encode())
d = json.loads(r['Payload'].read()); b = json.loads(d.get('body', '{}'))
print('status', d.get('statusCode'), '| allowed', b.get('allowed'), '| locked', b.get('locked'), '| error', r.get('FunctionError'))
PY
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
