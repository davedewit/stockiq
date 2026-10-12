#!/bin/bash
# One-off deploy (12 Oct 2026): the autopilot trades a share only at a price that has traded lately.
# The trading hours in stockiq-ai-trader are fixed windows and know no public holidays: on 12 Oct 2026 (Sports Day in Japan)
# it bought a Tokyo share at the Friday's closing price. Every quote says when it last traded, so now:
#  - a share whose price last traded more than 3 hours ago is neither bought nor sold at that check-in (a holiday in its
#    market, or the first minutes of a session while the price source still shows the session before);
#  - the activity list says which shares were left alone and why; "Sell everything it holds" keeps such a holding and
#    lists it with the closed markets. Coins are not affected (they trade all the time).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice. Stops if the live function is not the code this was built from.
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_fresh_20261012.zip
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-ai-trader; BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-ai-trader
WAS="k2OocgJogAZjcF8LYC6WOtH0n7I3VaE5nb9EmxWzAnI="
OLD_FILE=a676821c7c0e1432040183ba93064e98041ad74418c9e16818c6da6977c46b29
NEW_FILE=c77da5a7b11a0995b3cb04f0f38e7a280e7b5251174851a79a123237a33d0fa2
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
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${F}_before_autopilot_fresh_20261012.zip and update the function"
else
    [ -f "$BACKUP/${F}_before_autopilot_fresh_20261012.zip" ] || cp "$TMP/live.zip" "$BACKUP/${F}_before_autopilot_fresh_20261012.zip"
    cp "$HERE/lambda/lambda_function.py" "$TMP/lambda_function.py"; (cd "$TMP" && zip -q -X new.zip lambda_function.py)
    "${AWS[@]}" lambda update-function-code --function-name "$F" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$F"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new.zip")" ] || stop "the function does not report the new package"
    cp "$HERE/lambda/lambda_function.py" "$MIRROR/lambda_function.py"; echo "live ($(zipsha "$TMP/new.zip")), and the mirror updated"
    say "the live function answers (the page's read-only question, for an address that has no autopilot: nothing is written)"
    "${AWS[@]}" lambda invoke --function-name "$F" --cli-binary-format raw-in-base64-out --payload '{"requestContext":{},"body":"{\\"action\\":\\"get\\",\\"userId\\":\\"nobody-deploy-check@example.com\\"}"}' "$TMP/out.json" --query StatusCode --output text
    python3 -c "import json; d = json.load(open('$TMP/out.json')); b = json.loads(d.get('body', '{}')); print('status', d.get('statusCode'), '| allowed', b.get('allowed'), '| locked', b.get('locked'))"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
