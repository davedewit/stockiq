#!/bin/bash
# One-off deploy (13 Oct 2026): found when the S&P 500 line on the practice portfolio's graph was reviewed on the owner's
# real figures. The card in "The breakdown" said his holdings were "ahead of the fund by 0.27%" while the graph and the
# line under the three figures said the account was "behind by $1,557.97". Both are true (the card counts only what is
# still held; the graph the whole account since the start), so the card now says which it is.
# practice-portfolio.js v=35, dashboard.html (the version number only). Wording only; no function changes.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
FILES=(
 "practice-portfolio.js:4f100feea69d9b439ac4ad6fd8db29849f89c9720ba6666e7a504846bc300777:77079a71f71af79fb27245080eaacdb1a3413c3a4e5118e8f61a0526b8488c35:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:6ef370d9ca0382b54372a3ea81b74ba223024f0db3429ee7a9aa3ee24180670d:9b3f65008a59ae81452a48b81446fea8cf0761cbbc3a33c489101fa0045ee6ce:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
    local_sha="$(filesha "$WEB/$f")"; curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; live_sha="$(filesha "$TMP/live_$f")"
    [ "$local_sha" = "$was" ] || [ "$local_sha" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$live_sha" = "$was" ] || [ "$live_sha" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$local_sha" = "$new" ] && echo new || echo old), live $([ "$live_sha" = "$new" ] && echo new || echo old)"
done
grep -q 'practice-portfolio.js?v=35' "$HERE/web/dashboard.html" || stop "the staged dashboard does not ask for version 35 of the script"
grep -q 'function fundKnots' "$HERE/web/practice-portfolio.js" || stop "the staged script does not have the fund's line"
grep -q 'Only what is still held is counted here' "$HERE/web/practice-portfolio.js" || stop "the staged script does not have the card's new wording"
grep -q '5c7pt7qurshld4cwaqyopfxcei0cuurj' "$HERE/web/practice-portfolio.js" || stop "the staged script has lost the storage address"

say "the website: the script, then the page that asks for it"
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
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
