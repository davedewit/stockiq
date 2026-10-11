#!/bin/bash
# One-off deploy (11 Oct 2026, late): the trading-signals writers, a comparison above several reports, a Currency column.
#  - website/analysis-functions.js:
#      the two trading-signals writers print each reading in its own currency, with the company's name, the day's change,
#      the reasons, the trend and the 20-day high and low; symbols with no prices are listed; the auto-detect says
#      "strongest readings" and shows how many shares were scanned and how the readings fell;
#      a run of several single-stock reports starts with a short side-by-side table;
#      the screener CSV has a Currency column after Price ("GBp (pence)" for London).
#  - stockiq-screener-coordinator: the same Currency column in the background CSV.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice. Stops if the live file or the live function is not what this was built from.
# Roll back: ~/VSCODE/backup/stockiq-screener-coordinator_before_csvcurrency_20261011.zip; the website file from git.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website
AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
MIRROR=$ROOT/lambda-sync/stockiq-screener-coordinator; BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
COORD=stockiq-screener-coordinator
COORD_WAS="CKR1cZ3wGz/t1HTm956K0TKptxEmns60XZmFKGezzF0="
COORD_URL=https://ls6j5jqwl5iitwjt5va3jd6mbm0zhgyr.lambda-url.us-east-1.on.aws/
# file : sha256 before : sha256 after : content type : how long a copy may be kept (site-overview.md section 5, step 8)
FILES=(
 "analysis-functions.js:a2fd5ef6c8a2191e3e21232fec7f3a1097b27f3362995209dec2a3b78d35497d:72975c8c108cc79ec9d6324c63ca4608bc3e722e8402b04e53416566a7103818:application/javascript:public, max-age=300, s-maxage=86400"
)
COORD_NEW_FILE=4d3246812eb7d8f92f6c0688966dbe5d959cfa29b87f0796d4cdf267bfb025d0

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

say "the website: the page's report writers"
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
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${COORD}_before_csvcurrency_20261011.zip and update the function"
else
    [ -f "$BACKUP/${COORD}_before_csvcurrency_20261011.zip" ] || cp "$TMP/live.zip" "$BACKUP/${COORD}_before_csvcurrency_20261011.zip"
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
