#!/bin/bash
# One-off deploy (13 Oct 2026): three small things seen while the banners were mapped.
# 1. The header on a narrow desktop window or a tablet (769 to 1150px): the menu sits in the row beside the name; centred
#    on the page it ran over the name from about 1100px down. styles.css.
# 2. The main button of a section (.cta-primary: "Try StockIQ Analysis Tool" on the home page) is the site's blue like
#    its other main buttons and has no underline; it was red and underlined. styles.css.
# 3. The pop-up after the free analysis says "15 free analyses? That is 5 a day for 3 days", the same count as the strip
#    and the other pop-up; it said "5 Free Reports per day". analysis-functions.js (one line).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# To go back: git revert the commit in website/ and upload the two files.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
FILES=(
 "styles.css:3f2f0f83e1429f7e84c90960b214a69b94dca26d930f37b0083d99ed975512bf:d6493ce17b8d988b5d81ef231e4e1ac95e70b2d04b357dcf186f2c91e63553b9:text/css:public, max-age=300, s-maxage=86400"
 "analysis-functions.js:2ef8631a9e8f2353702b7e59552a259e94c06905279e1ad25d61b323cc715e8b:3b7efa2f0cc68a74673a4b5f081dec21a4ced70f41bbb1229ec4e7d12355dd84:application/javascript:public, max-age=300, s-maxage=86400"
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
node --check "$HERE/web/analysis-functions.js" || stop "the staged analysis script does not parse"
[ "$(diff "$WEB/analysis-functions.js" "$HERE/web/analysis-functions.js" | grep -c '^[<>]')" -le 2 ] || stop "the staged analysis script differs from the live one in more than its one line"
grep -q "position: relative !important" "$HERE/web/styles.css" || stop "the staged stylesheet has lost the menu's fix of this morning"

say "the website"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it ($ctype; $cache)"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    PATHS+=("/$f*"); echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for p in "${PATHS[@]}"; do p="${p%\*}"; curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB$p" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
    for q in "styles.css?v=1760537999" "styles.css?v=1760536562" "styles.css?v=20260226001"; do curl -s -o "$TMP/after" "https://stockiq.tech/$q"; cmp -s "$TMP/after" "$WEB/styles.css" && echo "live /$q equals the local file" || stop "the live /$q is still an older copy"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
