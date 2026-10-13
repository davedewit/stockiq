#!/bin/bash
# One-off deploy (13 Oct 2026): the analysis page's script made smaller and less repetitive.
# runAnalysis held 14 copies of the same routine, one for each share screener (1,468 lines). There is now one routine,
# runShareScreener, and one entry a screener in a new data file, screeners.js (its list, its workers, its name). The
# FTSE 100 report, which was written out inside runAnalysis, is a function like the others. Code that could never run
# is gone (a third copy of the ASX 300 routine after a "return", an unfinished Shanghai branch, two functions nothing
# called). analysis-functions.js: 324 KB -> 169 KB, 5,001 lines -> 3,416.
# PROVED THE SAME: check-tools/screener_equiv.js ran every screener and the other buttons through the old and the new
# code on the same worker answers: the same requests, the same report and the same CSV, character for character.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# TO GO BACK:                    bash /Users/dave/VSCODE/stockiq/check-tools/pending-screeners-undo/deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : what it was (- for a file that is new) : what it becomes : type : how long a copy may be kept
# In this order: the data, then the page that asks for it, then the script that needs it. (The new script also fetches
# the data by itself on a page that has no tag for it, so no order of arrival can leave a screener without its list.)
FILES=(
 "screeners.js:-:8c6ad16832c6319daa5d94b4888e4531796ead55a0b6304d1b8ca3cb2119aab5:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis.html:0a647633748ec85f22a34f5c4c6c67118c07fcf438a8ec96002cdb5039314008:51af1bc0c0f98ace8881e19b8211e4ed2f9fd8587e4e70cb87920ea0fd474400:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "analysis-functions.js:3b7efa2f0cc68a74673a4b5f081dec21a4ced70f41bbb1229ec4e7d12355dd84:af0a454dafc77cb36a4080b8552e9ccfabc2fff8678fb63b27b3dfa5f8565c45:application/javascript:public, max-age=300, s-maxage=86400"
)
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; live_sha="$(filesha "$TMP/live_$f")"
    if [ "$was" = "-" ]; then
        [ ! -e "$WEB/$f" ] || [ "$(filesha "$WEB/$f")" = "$new" ] || stop "website/$f exists already and is not this file"
        echo "$f: new; live $([ "$live_sha" = "$new" ] && echo there || echo 'not there yet')"; continue
    fi
    local_sha="$(filesha "$WEB/$f")"
    [ "$local_sha" = "$was" ] || [ "$local_sha" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$live_sha" = "$was" ] || [ "$live_sha" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$local_sha" = "$new" ] && echo new || echo old), live $([ "$live_sha" = "$new" ] && echo new || echo old)"
done
node --check "$HERE/web/analysis-functions.js" && node --check "$HERE/web/screeners.js" || stop "a staged script does not parse"
[ "$(grep -c "^    '[0-9]-[a-z0-9]*': {$" "$HERE/web/screeners.js")" = "14" ] || stop "the staged data file does not hold 14 screeners"
[ "$(grep -c "lambda-url.us-east-1.on.aws/'" "$HERE/web/screeners.js")" = "777" ] || stop "the staged data file does not hold the 777 worker addresses of the 14 screeners"
grep -q 'src="screeners.js"' "$HERE/web/analysis.html" || stop "the staged page does not ask for the data file"
grep -q "async function runShareScreener" "$HERE/web/analysis-functions.js" && grep -q "function refreshUsageCount" "$HERE/web/analysis-functions.js" || stop "the staged script lacks the screener routine or today's count refresh"

say "the website: the data file, the page, the script"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ -e "$WEB/$f" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it ($ctype; $cache)"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    PATHS+=("/$f*"); echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for p in "${PATHS[@]}"; do p="${p%\*}"; curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB$p" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
