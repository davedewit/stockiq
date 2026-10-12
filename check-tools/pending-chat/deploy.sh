#!/bin/bash
# One-off deploy (12 Oct 2026): the AI chat is told about the dashboard as it is now.
# Its guide to the dashboard did not yet know the graph of the account over time, the "Refresh prices" and "Reset fake
# money" buttons beside the heading, the split of both parties' results into sold and still held, the comparison card's
# opening time, the Number of holdings setting, or that a share is only traded at a price under 3 hours old.
# Only the guide's text changes: no rule of the chat, no limit, nothing on the site.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice. Stops if the live function is not the code this was built from.
# Roll back: ~/VSCODE/backup/stockiq-ai-chat_before_guide_20261012.zip
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-ai-chat; BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-ai-chat
WAS="cTz2ks6BStwoDLEIod20m/pzvn59WP2VHo9Hc/RtEV8="
OLD_FILE=b9357d9de8ed316abb98abbf3773e24ac068bc9a94f6f38ade63d94df63933de
NEW_FILE=c18e5056e055db50635a99a30c73f8d0695b9827d05b953b424167adaddd7071
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

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
python3 -W ignore "$ROOT/check-tools/ai_chat_test.py" "$HERE/lambda/lambda_function.py" 2>/dev/null | tail -1 | tee "$TMP/t"; grep -q "ALL PASS" "$TMP/t" || stop "the chat's tests do not pass on the staged function"

say "$F"
if [ "$STATE" = new ]; then echo "already deployed, skipping"
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${F}_before_guide_20261012.zip and update the function"
else
    [ -f "$BACKUP/${F}_before_guide_20261012.zip" ] || cp "$TMP/live.zip" "$BACKUP/${F}_before_guide_20261012.zip"
    cp "$HERE/lambda/lambda_function.py" "$TMP/lambda_function.py"; (cd "$TMP" && zip -q -X new.zip lambda_function.py)
    "${AWS[@]}" lambda update-function-code --function-name "$F" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$F"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new.zip")" ] || stop "the function does not report the new package"
    cp "$HERE/lambda/lambda_function.py" "$MIRROR/lambda_function.py"; echo "live ($(zipsha "$TMP/new.zip")), and the mirror updated"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
