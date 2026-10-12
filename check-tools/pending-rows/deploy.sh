#!/bin/bash
# One-off deploy (12 Oct 2026, evening): "Holding now" rows tidied, and each holding's own stop shown from the start.
# From a picture of the owner's panel: the tags wrapped under the name, "the plan for it" jumped from right to left when
# opened, every row repeated the same dates and limits, and every new holding showed "a stop follows it once it has been
# up 6.4%". Now a row is the symbol, the company and why it was bought, with a tag only for what is particular to it, and
# a fixed "its plan" on the right that opens the rest. The 6.4% was the level's general figure, shown until the next
# check-in had looked at the holding: the function now keeps each holding's own stop (from how much it normally moves)
# with the buy. practice-autopilot.js v=45, dashboard.html, and stockiq-ai-trader.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_rows_20261012.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-ai-trader; BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-ai-trader
OLD_FILE=268c5d5869d82cb7bbeaa99a1c1c167d99cb5c205888b36a527ce2bc50c6d535
NEW_FILE=5d4591cd6b3966194474ff1305c801c50c57074326878337e9065c3ff345d80e
FILES=(
 "practice-autopilot.js:8e6e07ce4eba2416252f08f735fc5ec3a07c018936d103fd9dccd04cb0d0d2ce:9b4aff9affdaeecc4ffe04e003e71232c88419dbe4fab70345be89ab1dbd0574:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:17ee401332167e9d3f62fff1125add70d41fb12e7e42a5037ea2bbf9a39c03f1:cb705712607d86cc11dfbe715188bab64a47e87291ed6ede5c7bdc03de86f116:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
    [ "$(filesha "$TMP/live/lambda_function.py")" = "$OLD_FILE" ] || stop "$F is not the code this was built from"
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
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${F}_before_autopilot_rows_20261012.zip and update the function"
else
    [ -f "$BACKUP/${F}_before_autopilot_rows_20261012.zip" ] || cp "$TMP/live.zip" "$BACKUP/${F}_before_autopilot_rows_20261012.zip"
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
    curl -s -o "$TMP/v" "https://stockiq.tech/practice-autopilot.js?v=45"; cmp -s "$TMP/v" "$WEB/practice-autopilot.js" && echo "live /practice-autopilot.js?v=45 equals the local file" || stop "the versioned address does not give the new script"
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
