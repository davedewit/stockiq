#!/bin/bash
# One-off deploy (12 Oct 2026): the number of holdings as a setting of its own in the AI autopilot.
#  - stockiq-ai-trader: settings.holdings (empty: the risk level's 12 / 10 / 8 / 6 / 4; or 2 to 50 set by the user). With the
#    user's number: each holding is the budget over that number, it buys up to a fifth of them at a check-in (3 could never
#    fill 50), looks further down each ranking when there are more holdings than the level looks at, and the shares of
#    the budget per market are counted in that number. Built on the "a market that showed only old prices stays due" fix.
#  - website/practice-autopilot.js: the field "Number of holdings" beside the budget, what the number means in words, and
#    the panel's own sums following it. website/dashboard.html: only the script's version (?v=40).
# The function goes first: the panel shows the field only when the function sends the setting.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice. Stops if the live function or a live file is not what this was built from.
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_holdings_20261012.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-ai-trader; BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-ai-trader
OLD_FILE=0016881066b167489934a65afb1ef8519afcd746e6c3b9da6393ca10b2b12c57
NEW_FILE=71d6ca2a8918e994f56db6748ab27e50dbf594924e8560c774ad4f73ae31e1cc
FILES=(
 "practice-autopilot.js:11c9ae8cd83ef1bb63e0c560f66a4a0130771ea822ef2442d9d344f6abfbed51:ce687dfa103f3bf3bf64a76ac7aca2c02aec1069b4471cd30099755978f60f4f:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:8459fbe0ee68fedbf4896e893667c16246a232fc1b790a7ef7df813e707cbfc5:5935f9fa829291dbfd6ef1f26f42c6604013a5c01403198ef0da2b016ed7b356:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
)
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
    [ "$(filesha "$TMP/live/lambda_function.py")" = "$OLD_FILE" ] || stop "$F is not the code this was built from (the fix that keeps a market due must be live first)"
    cmp -s "$TMP/live/lambda_function.py" "$MIRROR/lambda_function.py" || stop "the live function is not the same as the local mirror"
    echo "the function: live is the code this was built from"
fi
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    local_sha="$(filesha "$WEB/$f")"; curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; live_sha="$(filesha "$TMP/live_$f")"
    [ "$local_sha" = "$was" ] || [ "$local_sha" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$live_sha" = "$was" ] || [ "$live_sha" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$local_sha" = "$new" ] && echo new || echo old), live $([ "$live_sha" = "$new" ] && echo new || echo old)"
done
node -c "$HERE/web/practice-autopilot.js"
python3 -W ignore "$ROOT/check-tools/ai_trader_test.py" "$HERE/lambda/lambda_function.py" 2>/dev/null | tail -1 | tee "$TMP/t"; grep -q "ALL PASS" "$TMP/t" || stop "the autopilot's tests do not pass on the staged function"
node "$ROOT/check-tools/autopilot_test.js" "$HERE/web/practice-autopilot.js" 2>/dev/null | tail -1 | tee "$TMP/t2"; grep -q "ALL PASS" "$TMP/t2" || stop "the panel's tests do not pass on the staged script"

say "$F"
if [ "$STATE" = new ]; then echo "already deployed, skipping"
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${F}_before_autopilot_holdings_20261012.zip and update the function"
else
    [ -f "$BACKUP/${F}_before_autopilot_holdings_20261012.zip" ] || cp "$TMP/live.zip" "$BACKUP/${F}_before_autopilot_holdings_20261012.zip"
    cp "$HERE/lambda/lambda_function.py" "$TMP/lambda_function.py"; (cd "$TMP" && zip -q -X new.zip lambda_function.py)
    "${AWS[@]}" lambda update-function-code --function-name "$F" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$F"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new.zip")" ] || stop "the function does not report the new package"
    cp "$HERE/lambda/lambda_function.py" "$MIRROR/lambda_function.py"; echo "live ($(zipsha "$TMP/new.zip")), and the mirror updated"
fi

say "the website: the panel's script, then the page that asks for its new version"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it ($ctype; $cache)"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    PATHS+=("/$f"); echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for p in "${PATHS[@]}"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB$p" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
    curl -s -o "$TMP/v" "https://stockiq.tech/practice-autopilot.js?v=40"; cmp -s "$TMP/v" "$WEB/practice-autopilot.js" && echo "live /practice-autopilot.js?v=40 equals the local file" || stop "the versioned address does not give the new script"
fi
if [ "$DRY" != "true" ]; then
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
