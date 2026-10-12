#!/bin/bash
# One-off deploy (12 Oct 2026, evening): a build-up that begins again paces out only what is not invested yet.
# The build-up of the budget begins again whenever the budget or "Build up to it over" is changed, and it counted the
# whole budget from nothing each time: with most of the budget already invested, nothing could be bought until the
# release had passed all of it again. That froze the owner's buying three times in one day (once for three days, the
# last time until the next afternoon, after the budget was saved $29 lower). Now what was invested when the build-up
# began (holdings bought before that moment and still held) is left out of the pacing: the steps release the rest, so
# the next check-in can buy at once. From nothing it behaves exactly as before. The panel's description is unchanged.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_buildup_20261012.zip
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-ai-trader; BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-ai-trader
WAS="tyvs5Au9Lo3Gvsx9WaTA/rUl+kc0k7dDFB4dMGIzpmw="
OLD_FILE=5d4591cd6b3966194474ff1305c801c50c57074326878337e9065c3ff345d80e
NEW_FILE=312255a58eef610036f40567fd89cd405fd4c31ba63976c33638e552c54bd78c
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

say "$F"
if [ "$STATE" = new ]; then echo "already deployed, skipping"
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${F}_before_autopilot_buildup_20261012.zip and update the function"
else
    [ -f "$BACKUP/${F}_before_autopilot_buildup_20261012.zip" ] || cp "$TMP/live.zip" "$BACKUP/${F}_before_autopilot_buildup_20261012.zip"
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
