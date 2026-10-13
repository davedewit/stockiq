#!/bin/bash
# THE WAY BACK from the analysis page's one screener routine of 13 Oct 2026 (kept on purpose, not a leftover).
# It reverts the one commit in website/ that replaced the 14 copies of the screener routine with one (e0d47f15), which
# gives back analysis.html and analysis-functions.js as they were before it, keeping anything changed in them since,
# and uploads the two. screeners.js then stays on the site, asked for by nothing. git stops if a later change collides
# (a screener added to screeners.js since is such a change: it would have to be put back into the old code by hand).
#
#   Preview (changes nothing):   DRY_RUN=true bash /Users/dave/VSCODE/stockiq/check-tools/pending-screeners-undo/deploy.sh
#   Go back:                     bash /Users/dave/VSCODE/stockiq/check-tools/pending-screeners-undo/deploy.sh
# The undo for the usage chip's clean-up (pending-cleanup-undo) touches the same script: run THIS one first if both are wanted.
set -euo pipefail
WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; COMMIT=e0d47f15
FILES=(analysis.html analysis-functions.js)
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"
git -C "$WEB" cat-file -e "$COMMIT^{commit}" || stop "the commit $COMMIT is not in website/"
if git -C "$WEB" log --format=%s | grep -q "^Revert \"Analysis page: one routine for the 14 share screeners"; then say "nothing to do: it is reverted already"; exit 0; fi
git -C "$WEB" diff --quiet -- "${FILES[@]}" screeners.js || stop "one of the files has uncommitted changes in website/: commit or put them aside first"

say "what it would do"
git -C "$WEB" show --stat --format='reverts: %h %s' "$COMMIT" | cut -c1-110
# tried on a copy of the repository first, so that a collision is found before anything real is touched
git clone -q "$WEB" "$TMP/try" 2>/dev/null && git -C "$TMP/try" -c user.name=check -c user.email=check@example.com revert --no-edit "$COMMIT" >/dev/null 2>&1 || stop "git cannot revert the clean-up cleanly: something changed in the same lines since. It needs a session"
node --check "$TMP/try/analysis-functions.js" || stop "the script would not parse after the revert"
[ "$(grep -c "lambda-url.us-east-1.on.aws" "$TMP/try/analysis-functions.js")" -gt 800 ] && ! grep -q 'src="screeners.js"' "$TMP/try/analysis.html" || stop "the old code would not be back after the revert"
echo "the revert applies cleanly and the script parses"
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
say "FINISHED: the analysis page runs its screeners from the 14 copies again (committed in website/, not pushed). A browser may keep a script for up to five minutes."
