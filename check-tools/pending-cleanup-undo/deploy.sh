#!/bin/bash
# THE WAY BACK from the clean-up of 13 Oct 2026 (the "second half" of the usage chip; kept on purpose, not a leftover).
# It reverts the one commit in website/ that took the duplicate badge and button code out (5b2a68d5), which gives back
# index.html, analysis.html, analysis-functions.js and visitor-bar.js as they were with the chip but before the
# clean-up, keeping anything changed in those files since, and uploads the four. git stops if a later change
# collides; nothing is uploaded then.
#
#   Preview (changes nothing):   DRY_RUN=true bash /Users/dave/VSCODE/stockiq/check-tools/pending-cleanup-undo/deploy.sh
#   Go back:                     bash /Users/dave/VSCODE/stockiq/check-tools/pending-cleanup-undo/deploy.sh
# To go further back, to before the chip itself: run this first, then check-tools/pending-banners-undo/deploy.sh.
set -euo pipefail
WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; COMMIT=5b2a68d5
FILES=(visitor-bar.js analysis-functions.js index.html analysis.html)
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"
git -C "$WEB" cat-file -e "$COMMIT^{commit}" || stop "the commit $COMMIT is not in website/"
if git -C "$WEB" log --format=%s | grep -q "^Revert \"Usage chip, second half"; then say "nothing to do: the clean-up is reverted already"; exit 0; fi
git -C "$WEB" diff --quiet -- "${FILES[@]}" || stop "one of the four files has uncommitted changes in website/: commit or put them aside first"

say "what it would do"
git -C "$WEB" show --stat --format='reverts: %h %s' "$COMMIT" | cut -c1-110
# tried on a copy of the repository first, so that a collision is found before anything real is touched
git clone -q "$WEB" "$TMP/try" 2>/dev/null && git -C "$TMP/try" -c user.name=check -c user.email=check@example.com revert --no-edit "$COMMIT" >/dev/null 2>&1 || stop "git cannot revert the clean-up cleanly: something changed in the same lines since. It needs a session"
node --check "$TMP/try/analysis-functions.js" && node --check "$TMP/try/visitor-bar.js" || stop "a script would not parse after the revert"
grep -q "sticky-register-btn" "$TMP/try/index.html" && grep -q "sticky-upgrade-btn" "$TMP/try/analysis-functions.js" || stop "the old code would not be back after the revert"
echo "the revert applies cleanly and both scripts parse"
if [ "$DRY" = "true" ]; then say "FINISHED (dry run, nothing changed)"; exit 0; fi

say "the website"
git -C "$WEB" revert --no-edit "$COMMIT" >/dev/null
PATHS=()
for f in "${FILES[@]}"; do
    case "$f" in *.html) ctype="text/html; charset=utf-8"; cache="public, max-age=0, s-maxage=3600, must-revalidate";; *) ctype="application/javascript"; cache="public, max-age=300, s-maxage=86400";; esac
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    PATHS+=("/$f*"); echo "$f: uploaded"
done
INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
"${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
for f in "${FILES[@]}"; do curl -s -o "$TMP/after" "https://stockiq.tech/$f"; cmp -s "$TMP/after" "$WEB/$f" && echo "live /$f equals the local file" || stop "the live /$f is not the file that was uploaded"; done
say "FINISHED: the pages are as they were with the chip, before the clean-up (committed in website/, not pushed). A browser may keep a script for up to five minutes."
