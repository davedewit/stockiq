#!/bin/bash
# One-off deploy (13 Oct 2026): the market-data sidebar on a phone (home page and dashboard). It follows the finger
# (a quarter of a swipe shows a quarter of it, and it can be pushed back in the same touch) and the page behind stays
# where it was: opening it used to give the page position: fixed, which threw it to the top. One new script for both
# pages, mobile-sidebar.js; each page keeps only what is its own (moving its panels in and out).
# Tested with check-tools/mobile_sidebar_check.js (a finger in headless Chrome at phone size), not on a real phone.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : what it was (- for a file that is new) : what it becomes : type : how long a copy may be kept
# The script goes up first: a page that asks for it must find it.
FILES=(
 "mobile-sidebar.js:-:c0b34a034eeaacf18d029d61b66b373d632816b39a348abc0e72bfee0d94c0db:application/javascript:public, max-age=300, s-maxage=86400"
 "index.html:220bfa35e7b65f1c83d8e8f5166bb7e2169b12c837b38e413fd670910da5f3e5:6f251b365a40dad0271b9abdeb9caa33926c369b9a2331e6630049831e977e3c:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:7513f0cf1622d4821dc083224212a3f29f67aa0569bc03021c342440ae5562d4:48444abcb5c4ed8a372246722796dc45441b49ce25b7258ad4dcb09980d25c51:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
        echo "$f: new; local $([ -e "$WEB/$f" ] && echo there || echo 'not there yet'), live $([ "$live_sha" = "$new" ] && echo there || echo 'not there yet')"
        continue
    fi
    local_sha="$(filesha "$WEB/$f")"
    [ "$local_sha" = "$was" ] || [ "$local_sha" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$live_sha" = "$was" ] || [ "$live_sha" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$local_sha" = "$new" ] && echo new || echo old), live $([ "$live_sha" = "$new" ] && echo new || echo old)"
done
for f in index.html dashboard.html; do
    grep -q '<script src="mobile-sidebar.js?v=1"></script>' "$HERE/web/$f" || stop "the staged $f does not ask for the sidebar script"
    grep -q 'function fillMobileSidebar' "$HERE/web/$f" && grep -q 'function emptyMobileSidebar' "$HERE/web/$f" || stop "the staged $f lacks its two sidebar functions"
    if grep -q "'fixed'" <(sed -n '/function fillMobileSidebar/,/function emptyMobileSidebar/p' "$HERE/web/$f"); then stop "the staged $f still freezes the page when the sidebar opens"; fi
done

say "the website: the sidebar script, then the two pages"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ -e "$WEB/$f" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
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
