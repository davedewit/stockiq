#!/bin/bash
# One-off deploy (13 Oct 2026): the menu on the left on a phone works like the sidebar on the right. It follows the
# finger on the pages that have the swipe (home page, analysis page, dashboard), and on every page with a menu the page
# behind stays where it was: styles.css no longer gives the body position: fixed and a height while the menu is open
# (that threw the page to the top), and it overrides the position: fixed that older page code still writes.
# mobile-sidebar.js (v=2) now moves both panels; the three pages lose their own swipe code.
# Tested with check-tools/mobile_sidebar_check.js (a finger in headless Chrome at phone size), not on a real phone.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : what it was : what it becomes : type : how long a copy may be kept
# The stylesheet and the script go up first: a page that asks for them must find the new ones.
FILES=(
 "styles.css:653c70819bc4ae24ba214ab603c6c1f3383c686b5a6dfef47580d15bb45649fa:3f2f0f83e1429f7e84c90960b214a69b94dca26d930f37b0083d99ed975512bf:text/css:public, max-age=300, s-maxage=86400"
 "mobile-sidebar.js:28652e48d85653907e8cc2602e2e83431ebf2460f3fc9d230834cc4409477697:19512615d3e8dbd6d68c1748f9d45bf0dc1e818bffb15711f64028dd75b9f344:application/javascript:public, max-age=300, s-maxage=86400"
 "index.html:6f251b365a40dad0271b9abdeb9caa33926c369b9a2331e6630049831e977e3c:81ce578a29583b1dcc1fced8b8bfab4ee7228fa8cc41eb033860629a37770844:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:b2b7a5019289424580aae0215ecb48a7eaf4f2a57484e95bf1787446e1eb3c00:5f9b9b27945bce8084d75b3566a4b6950d7ad092f004394293d300118ae02d2a:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "analysis.html:b38d466bea6d0a431a2a6d66b544a794dc51e28ad0cfe08fe011d1773073bc0b:1e8e226ceaa90d16e5abe34bcc01401bd3cb4ce525be1312147e9926c59cbbb5:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
for f in index.html dashboard.html analysis.html; do
    grep -q '<script src="mobile-sidebar.js?v=2"></script>' "$HERE/web/$f" || stop "the staged $f does not ask for version 2 of the script"
    if grep -q "handleSwipe\|touchStartX" "$HERE/web/$f"; then stop "the staged $f still has its own swipe code"; fi
done
if sed -n '/^body.menu-open {/,/^}/p' "$HERE/web/styles.css" | grep -q "fixed\|100vh"; then stop "the staged stylesheet still freezes the page when the menu opens"; fi
grep -q "name: 'menu'" "$HERE/web/mobile-sidebar.js" || stop "the staged script does not handle the menu"

say "the website: the stylesheet and the script, then the three pages"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it ($ctype; $cache)"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    PATHS+=("/$f*"); echo "$f: uploaded"       # the * also clears the copies kept under a ?v= address (pages ask for styles.css?v=...)
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for p in "${PATHS[@]}"; do p="${p%\*}"; curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB$p" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
    for q in "styles.css?v=1760537999" "styles.css?v=1760536562" "styles.css?v=20260226001" "mobile-sidebar.js?v=2"; do
        curl -s -o "$TMP/after" "https://stockiq.tech/$q"; cmp -s "$TMP/after" "$WEB/${q%%\?*}" && echo "live /$q equals the local file" || stop "the live /$q is still an older copy"
    done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
