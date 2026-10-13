#!/bin/bash
# THE WAY BACK from the header-bar usage chip of 13 Oct 2026 (kept on purpose; not a leftover).
# It takes the switch out of theme.js (the lines between VISITOR_BAR_START and VISITOR_BAR_END) and puts the yellow bar
# back on the home page, in the files as they are today, and uploads the two. Every page then shows its own floating
# badge and round buttons exactly as before. visitor-bar.js stays on the site, asked for by nothing.
#
#   Preview (changes nothing):   DRY_RUN=true bash /Users/dave/VSCODE/stockiq/check-tools/pending-banners-undo/deploy.sh
#   Go back:                     bash /Users/dave/VSCODE/stockiq/check-tools/pending-banners-undo/deploy.sh
# To switch it on again afterwards: `git revert` the commit this leaves in website/, and upload theme.js and index.html.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"
# Since the clean-up of 13 Oct the round buttons are drawn by visitor-bar.js alone: going back to before the chip needs the clean-up undone first.
grep -q "sticky-register-btn" "$WEB/index.html" || stop "the clean-up is still in place: run check-tools/pending-cleanup-undo/deploy.sh first, then this one"

say "what it would do"
cp "$WEB/theme.js" "$WEB/index.html" "$TMP/"
python3 "$HERE/undo.py" "$TMP/theme.js" "$TMP/index.html" "$HERE/yellow-bar.html"
node --check "$TMP/theme.js" || stop "theme.js would not be a working script after the undo"
if grep -q "VISITOR_BAR\|visitor-bar" "$TMP/theme.js"; then stop "something of the switch would be left in theme.js"; fi
grep -q 'id="limited-time-banner"' "$TMP/index.html" || stop "the yellow bar would not be back on the home page"
CHANGED=(); for f in theme.js index.html; do cmp -s "$TMP/$f" "$WEB/$f" || CHANGED+=("$f"); done
if [ ${#CHANGED[@]} -eq 0 ]; then
    for f in theme.js index.html; do curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; cmp -s "$TMP/live_$f" "$WEB/$f" || CHANGED+=("$f"); done
    [ ${#CHANGED[@]} -eq 0 ] && { say "nothing to do: it is undone already, here and on the site"; exit 0; }
fi
echo "to upload: ${CHANGED[*]}"
if [ "$DRY" = "true" ]; then say "FINISHED (dry run, nothing changed)"; exit 0; fi

say "the website"
PATHS=()
for f in "${CHANGED[@]}"; do
    cp "$TMP/$f" "$WEB/$f"
    if [ "$f" = "theme.js" ]; then "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript" --only-show-errors
    else "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=0, s-maxage=3600, must-revalidate" --content-type "text/html; charset=utf-8" --only-show-errors; fi
    PATHS+=("/$f*"); echo "$f: uploaded"
done
INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
"${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
for f in "${CHANGED[@]}"; do curl -s -o "$TMP/after" "https://stockiq.tech/$f"; cmp -s "$TMP/after" "$WEB/$f" && echo "live /$f equals the local file" || stop "the live /$f is not the file that was uploaded"; done
git -C "$WEB" commit -q -m "Undo: the usage count back in each page's own floating badge; the home page's yellow bar back (check-tools/pending-banners-undo)" -- "${CHANGED[@]}" && echo "committed in website/ (not pushed)"
say "FINISHED: the pages are as they were before the header chip. A browser may keep theme.js for up to five minutes."
