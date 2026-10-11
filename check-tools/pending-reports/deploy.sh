#!/bin/bash
# One-off deploy (11 Oct 2026): each market's own currency in the screener reports, and whole symbols.
#  - website/dashboard.html: the 🎯 tracker reads a price written with a currency sign ("A$8.43", "¥5,613.00") or as
#    pence ("503.80p"), with thousands commas; older saved reports ("£2614.00", "$AUD8.43") are read as before.
#  - website/analysis-functions.js: the share-screener formatters print prices through one rule (screenerMoney) from the
#    currency each worker result carries: no pence shown as pounds, "A$" for Australia, yen with its decimals.
#  - stockiq-screener-coordinator (background reports): the same rule (it printed "$" for every market), and the symbol
#    is no longer cut to five characters ("TSCO." for TSCO.L), which the tracker could not read.
# The tracker goes first, so it can read the new lines before anything writes them.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice. Stops if a live file or the live function is not what this was built from.
# Roll back: ~/VSCODE/backup/stockiq-screener-coordinator_before_currency_20261011.zip; the two website files from git.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website
AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
MIRROR=$ROOT/lambda-sync/stockiq-screener-coordinator; BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
COORD=stockiq-screener-coordinator
COORD_WAS="SlVjJOCOssiypoOyfPAdQQycrePt9sqN5JI4mYoJh/0="
COORD_URL=https://ls6j5jqwl5iitwjt5va3jd6mbm0zhgyr.lambda-url.us-east-1.on.aws/
# file : sha256 before : sha256 after : content type : how long a copy may be kept (site-overview.md section 5, step 8)
FILES=(
 "dashboard.html:79986e57a7eea70897649a24e0bdc015746f3c0ee7fa2d2050a6f784282c573c:bec16da1ef4cb2796e9505ba802994f44898f9a079139ac966a337a91d78a45d:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "analysis-functions.js:6b0c4707270c48cf08116581bfc1c2f9c099f1a499deda2e887899db38f870f7:a2fd5ef6c8a2191e3e21232fec7f3a1097b27f3362995209dec2a3b78d35497d:application/javascript:public, max-age=300, s-maxage=86400"
)
COORD_NEW_FILE=ffc4fa5e50d554cdc836b0baf6568f1f0ca108503c61dae42ec703b69853f45c

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }

if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"
M=$((10#$(date +%M)))
if [ "$DRY" != "true" ] && { { [ $M -ge 8 ] && [ $M -le 13 ]; } || { [ $M -ge 38 ] && [ $M -le 43 ]; }; }; then stop "it is within a few minutes of :10 or :40, when the autopilot reads the screeners through the coordinator: run this again in five minutes"; fi

say "checks before anything is changed"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    local_sha="$(filesha "$WEB/$f")"; curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; live_sha="$(filesha "$TMP/live_$f")"
    [ "$local_sha" = "$was" ] || [ "$local_sha" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$live_sha" = "$was" ] || [ "$live_sha" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$local_sha" = "$new" ] && echo new || echo old), live $([ "$live_sha" = "$new" ] && echo new || echo old)"
done
[ "$(filesha "$HERE/lambda/lambda_function.py")" = "$COORD_NEW_FILE" ] || stop "the staged coordinator is not the one that was tested"
python3 -m py_compile "$HERE/lambda/lambda_function.py"; rm -rf "$HERE/lambda/__pycache__"; node -c "$HERE/web/analysis-functions.js"
curl -s -o "$TMP/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$COORD" --query Code.Location --output text)"
mkdir -p "$TMP/live"; unzip -q -o "$TMP/live.zip" -d "$TMP/live"
[ "$(unzip -Z1 "$TMP/live.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "the coordinator's package holds other files than lambda_function.py"
if [ "$(filesha "$TMP/live/lambda_function.py")" = "$COORD_NEW_FILE" ]; then COORD_STATE=new; echo "coordinator: already the new code"
else
    COORD_STATE=old
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$COORD" --query CodeSha256 --output text)" = "$COORD_WAS" ] || stop "the coordinator has changed on AWS since this was built"
    cmp -s "$TMP/live/lambda_function.py" "$MIRROR/lambda_function.py" || stop "the live coordinator is not the same as the local mirror"
    echo "coordinator: live is the code this was built from"
fi

say "the website: the tracker first, then the page's report writer"
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
fi

say "$COORD"
if [ "$COORD_STATE" = new ]; then echo "already deployed, skipping"
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${COORD}_before_currency_20261011.zip and update the function"
else
    [ -f "$BACKUP/${COORD}_before_currency_20261011.zip" ] || cp "$TMP/live.zip" "$BACKUP/${COORD}_before_currency_20261011.zip"
    cp "$HERE/lambda/lambda_function.py" "$TMP/lambda_function.py"; (cd "$TMP" && zip -q -X new.zip lambda_function.py)
    "${AWS[@]}" lambda update-function-code --function-name "$COORD" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$COORD"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$COORD" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new.zip")" ] || stop "the coordinator does not report the new package"
    cp "$HERE/lambda/lambda_function.py" "$MIRROR/lambda_function.py"; echo "live, and the mirror updated"
fi

if [ "$DRY" != "true" ]; then
    say "the live coordinator, called as the autopilot calls it (no user: nothing is saved to anyone's history)"
    for pair in "5:ftse100" "4:200" "5:nikkei225" "3:8"; do
        curl -s -m 120 -X POST "$COORD_URL" -H 'Content-Type: application/json' -d "{\"option\":\"${pair%%:*}\",\"subOption\":\"${pair##*:}\"}" | python3 -c "
import sys, json, collections
d = json.load(sys.stdin); r = d.get('results') or []
print('${pair}:', 'success', d.get('success'), '|', len(r), 'results | currencies', dict(collections.Counter(x.get('currency') for x in r)), '| first:', (r[0]['symbol'], r[0]['price']) if r else None)"
    done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
