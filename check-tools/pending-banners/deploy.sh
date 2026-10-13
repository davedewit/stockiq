#!/bin/bash
# One-off deploy (13 Oct 2026): the visitor's usage count moves from the floating badge into the header bar, as a small
# chip on every page ("1 free today", "3/5 today", "Unlimited", "Trial ended"); a click says it in a sentence with the
# thing to do next. The round trial / upgrade buttons all sit bottom left. The home page loses its yellow "LIMITED
# TIME" bar. How the count is worked out is NOT touched: the pages' own code still does that, and visitor-bar.js shows
# what it writes. theme.js carries the switch (between VISITOR_BAR_START and VISITOR_BAR_END).
# Tested with check-tools/visitor_bar_check.js: seven kinds of visitor, five pages, four widths, 1,612 checks.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# TO GO BACK:                    bash /Users/dave/VSCODE/stockiq/check-tools/pending-banners-undo/deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : what it was (- for a file that is new) : what it becomes : type : how long a copy may be kept
# The script goes up before theme.js, which asks for it.
FILES=(
 "visitor-bar.js:-:f2ee45c47d72c36279c651e678ed17e94b4ab06dca7299370b3b1ea21099643f:application/javascript:public, max-age=300, s-maxage=86400"
 "index.html:81ce578a29583b1dcc1fced8b8bfab4ee7228fa8cc41eb033860629a37770844:281616ebd393316b3562d770dc3f5020e5c56b4f34aaed158cdaa5eaf07c187f:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "theme.js:66da2c7c26a1650cd664172e84f3fe94946494bd6a2929c9c1529695644cb79c:bb9a94a7e6c26887b627a97668fd02506ec6cb299b49c8d5445e83a127ceccf7:application/javascript:public, max-age=300, s-maxage=86400"
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
grep -q "VISITOR_BAR_START" "$HERE/web/theme.js" && grep -q "VISITOR_BAR_END" "$HERE/web/theme.js" || stop "the staged theme.js has no marked switch (the undo needs it)"
if grep -q 'id="limited-time-banner"' "$HERE/web/index.html"; then stop "the staged home page still has the yellow bar"; fi
# the way back must work on exactly these files before they go up
mkdir -p "$TMP/undo"; cp "$HERE/web/theme.js" "$HERE/web/index.html" "$TMP/undo/"
python3 "$ROOT/check-tools/pending-banners-undo/undo.py" "$TMP/undo/theme.js" "$TMP/undo/index.html" "$ROOT/check-tools/pending-banners-undo/yellow-bar.html" >/dev/null
for f in theme.js index.html; do IFS=: read -r _ was _ <<< "$(printf '%s\n' "${FILES[@]}" | grep "^$f:")"; [ "$(filesha "$TMP/undo/$f")" = "$was" ] || stop "the undo does not turn the staged $f back into the file that is live now"; done
echo "the undo turns both files back into the ones that are live now"

say "the website: the new script, the home page, then theme.js (the switch)"
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
