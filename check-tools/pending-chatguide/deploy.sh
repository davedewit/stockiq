#!/bin/bash
# One-off deploy (12 Oct 2026, evening): the AI chat's guide to the dashboard is told of the two standing trials for
# shares (which share to buy; "patient" shares that are not sold on the signal nor reviewed by the AI model), so that it
# does not tell a user that every holding is sold when its signal turns. Only the guide's text changes.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-ai-chat_before_guide3_20261012.zip
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-ai-chat; BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-ai-chat
WAS="f6vB7CzN3cQAt9ZbTUS7+eYrFRsp75L46Xks8kx5rn4="
OLD_FILE=e126c1503bfd056e4eb80a67fd1bf7cd7e6ff9ad64afe62764eabb93dff44367
NEW_FILE=413158ab8c2b31dc267c378e84cee3f0771af06e76bdf68a7466b3bef7e514f3
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
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${F}_before_guide3_20261012.zip and update the function"
else
    [ -f "$BACKUP/${F}_before_guide3_20261012.zip" ] || cp "$TMP/live.zip" "$BACKUP/${F}_before_guide3_20261012.zip"
    cp "$HERE/lambda/lambda_function.py" "$TMP/lambda_function.py"; (cd "$TMP" && zip -q -X new.zip lambda_function.py)
    "${AWS[@]}" lambda update-function-code --function-name "$F" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$F"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new.zip")" ] || stop "the function does not report the new package"
    cp "$HERE/lambda/lambda_function.py" "$MIRROR/lambda_function.py"; echo "live ($(zipsha "$TMP/new.zip")), and the mirror updated"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
