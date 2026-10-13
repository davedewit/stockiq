#!/bin/bash
# One-off deploy (13 Oct 2026): the duplicate code behind the usage chip is taken out. The count is now written in one
# place (auth.js displayTrialStatus, on every page; the analysis page writes the new count after a use; the dashboard
# keeps its own, which also fills in its plan section) and shown in one place (visitor-bar.js, which now also draws the
# one round "Start 3-Day Free Trial" / "Upgrade Plan" button). Gone: the second badge the home page and the analysis
# script each made at page load, their five copies of the round-button code, three identical blocks and an unused
# function that animated the old badge, and the scroll code that moved it. auth.js and dashboard.html are not touched.
# Tested: check-tools/visitor_bar_check.js (1,746 checks), anon_run.js and trial_run.js old against new (same results and
# redirects, one request fewer per page), page_run.js, mobile_sidebar_check.js.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# TO GO BACK to before this clean-up: bash /Users/dave/VSCODE/stockiq/check-tools/pending-cleanup-undo/deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : what it was : what it becomes : type : how long a copy may be kept.  The shared script first: it draws the round button the pages stop drawing.
FILES=(
 "visitor-bar.js:f2ee45c47d72c36279c651e678ed17e94b4ab06dca7299370b3b1ea21099643f:dcabd7523aa2faa6a73067bb8d2ed458a41fba8d21e251e1e71b3af87a6e8fdf:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis-functions.js:96dbcb721ec1a3450513843bdc074434c2308b18f845b0092d90f3ab61c7c44f:2ef8631a9e8f2353702b7e59552a259e94c06905279e1ad25d61b323cc715e8b:application/javascript:public, max-age=300, s-maxage=86400"
 "index.html:281616ebd393316b3562d770dc3f5020e5c56b4f34aaed158cdaa5eaf07c187f:daeec05a28104c0e137ad340da2f56fabcfe529f779dfc2383c370ecae58e42f:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "analysis.html:1e8e226ceaa90d16e5abe34bcc01401bd3cb4ce525be1312147e9926c59cbbb5:042cf9d0dd439540d77ee2c54bc6081d6d0cfec24ca672c2189c8c3fb0aea60e:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
node --check "$HERE/web/analysis-functions.js" && node --check "$HERE/web/visitor-bar.js" || stop "a staged script does not parse"
grep -q "function refreshUsageCount" "$HERE/web/analysis-functions.js" || stop "the staged analysis script has no refreshUsageCount"
[ "$(grep -c "refreshUsageCount();" "$HERE/web/analysis-functions.js")" = "3" ] || stop "the staged analysis script does not refresh the count in its three places"
if grep -q "sticky-register-btn\|sticky-upgrade-btn" "$HERE/web/analysis-functions.js" "$HERE/web/index.html"; then stop "a staged file still draws a round button of its own"; fi
grep -q "vb-pill" "$HERE/web/visitor-bar.js" || stop "the staged shared script does not draw the round button"
git -C "$WEB" diff --quiet -- auth.js dashboard.html || stop "auth.js or dashboard.html has uncommitted changes (this deploy must not carry any)"

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
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
