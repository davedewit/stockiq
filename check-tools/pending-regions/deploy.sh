#!/bin/bash
# One-off deploy (13 Oct 2026): the AI autopilot can buy from every screener of the site, grouped as the Screeners menu is.
#   - stockiq-ai-trader: 27 screeners (the 12 added on 13 Oct 2026 with the 15 before) in five groups, "US markets",
#     "Europe markets", "Asia-Pacific markets", "Americas markets", "Coins" (they were one group a country); trading
#     hours and names for the new exchanges; a share of the budget set under a country's old name is carried over.
#   - practice-autopilot.js: a quick set-up says what it replaced and offers "Undo: put my settings back" (pressing one
#     wiped the owner's ticked screeners with no way back); the locked view's sentence names the regions.
#     dashboard.html is NOT changed (another session has it staged): the script keeps its ?v=45, and browsers keep a
#     script five minutes.
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_regions_20261013.zip; practice-autopilot.js from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
F=stockiq-ai-trader; MIRROR=$ROOT/lambda-sync/$F; BACKUP=/Users/dave/VSCODE/backup; KEEP="$BACKUP/${F}_before_autopilot_regions_20261013.zip"
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
WAS="0tynNBjnvnTkUmLZGPBc+v6CGxabNKGgNCaQE95YYUE="; OLD_FILE=312255a58eef610036f40567fd89cd405fd4c31ba63976c33638e552c54bd78c; NEW_FILE=68af987e354dc6f517c756176416e4d4ba9098746ebc5166afdefe1e94c325c0
JS=practice-autopilot.js; JS_WAS=9b4aff9affdaeecc4ffe04e003e71232c88419dbe4fab70345be89ab1dbd0574; JS_NEW=1311fd196daa251488b9437a5718cf6ce8848f02b78f9197cea0fc2b5ce78abb
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
M=$((10#$(date -u +%M) % 30)); if [ "$DRY" != "true" ] && { [ "$M" -ge 9 ] && [ "$M" -le 13 ]; }; then stop "the autopilot's scheduled run is at :10 and :40 past the hour; run this a few minutes later"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
[ "$(filesha "$HERE/lambda/lambda_function.py")" = "$NEW_FILE" ] || stop "the staged function is not the one that was tested"
[ "$(filesha "$HERE/web/$JS")" = "$JS_NEW" ] || stop "the staged panel is not the one that was tested"
python3 -m py_compile "$HERE/lambda/lambda_function.py" || stop "the staged function does not compile"
node --check "$HERE/web/$JS" || stop "the staged panel does not parse"
curl -s -o "$TMP/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$F" --query Code.Location --output text)"
mkdir -p "$TMP/live"; unzip -q -o "$TMP/live.zip" -d "$TMP/live"
[ "$(unzip -Z1 "$TMP/live.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "the package holds other files than lambda_function.py"
if [ "$(filesha "$TMP/live/lambda_function.py")" = "$NEW_FILE" ]; then STATE=new; echo "the function already has the new code"
else
    STATE=old
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$WAS" ] && [ "$(filesha "$TMP/live/lambda_function.py")" = "$OLD_FILE" ] || stop "$F has changed on AWS since this was built"
    cmp -s "$TMP/live/lambda_function.py" "$MIRROR/lambda_function.py" || stop "the live function is not the same as the local mirror"
    echo "the live function is the code this was built from"
fi
L="$(filesha "$WEB/$JS")"; curl -s -o "$TMP/live_js" "https://stockiq.tech/$JS"; S="$(filesha "$TMP/live_js")"
[ "$L" = "$JS_WAS" ] || [ "$L" = "$JS_NEW" ] || stop "website/$JS has changed since this was built"
[ "$S" = "$JS_WAS" ] || [ "$S" = "$JS_NEW" ] || stop "the live $JS is neither the old nor the new file"
echo "$JS: local $([ "$L" = "$JS_NEW" ] && echo new || echo old), live $([ "$S" = "$JS_NEW" ] && echo new || echo old)"

say "$F (the function first: the panel lists whatever screeners and groups it sends)"
if [ "$STATE" = new ]; then echo "already deployed, skipping"
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $KEEP and update the function"
else
    [ -f "$KEEP" ] || cp "$TMP/live.zip" "$KEEP"
    cp "$HERE/lambda/lambda_function.py" "$TMP/lambda_function.py"; (cd "$TMP" && zip -q -X new.zip lambda_function.py)
    "${AWS[@]}" lambda update-function-code --function-name "$F" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$F"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new.zip")" ] || stop "the function does not report the new package"
    cp "$HERE/lambda/lambda_function.py" "$MIRROR/lambda_function.py"; echo "live ($(zipsha "$TMP/new.zip")), and the mirror updated"
fi

say "the panel"
if [ "$L" = "$JS_NEW" ] && [ "$S" = "$JS_NEW" ]; then echo "$JS: already live"
elif [ "$DRY" = "true" ]; then echo "(dry run) would copy $JS into website/ and upload it"
else
    cp "$HERE/web/$JS" "$WEB/$JS"
    "${AWS[@]}" s3 cp "$WEB/$JS" "s3://$BUCKET/$JS" --cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript" --only-show-errors
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "/$JS*" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for q in "" "?v=45"; do curl -s -o "$TMP/after" "https://stockiq.tech/$JS$q"; cmp -s "$TMP/after" "$WEB/$JS" && echo "live /$JS$q equals the local file" || stop "the live $JS$q is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
