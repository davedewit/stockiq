#!/bin/bash
# One-off deploy (17 Oct 2026), website files only:
#   - practice-portfolio.js?v=40: the holdings table shows the latest 10, the rest behind "Show all N"; the gap to the S&P 500
#     fund in percent as well as dollars (both started with the same money, so it is the difference between the two returns).
#   - practice-autopilot.js?v=55: "Nothing needs you right now" says only what it means for this user's own autopilot.
#   - admin-panel.js?v=8: "Needs your yes" is "Decisions for you", and says how it differs from the autopilot tab's box.
#   Preview: DRY_RUN=true bash deploy.sh    Deploy: bash deploy.sh
# Roll back: the four website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "practice-portfolio.js:d9904ad7293960025624a0a5bb320fd7323acaee697d62b5a5c81f3323e461f4:b241758ca512dbbce09904d6f043cd06c9b639b8aab716cc8c25e06b74759d7c:application/javascript:public, max-age=300, s-maxage=86400"
 "practice-autopilot.js:e3ad3d2e4ef2da05a7c1a7ac76853913223b3f43f37f0138a2e7ee1d4b0642d3:17916d3bdc051a69d2d81aa55aca7404601ea25ea5dcbf9f5ea2de4d32c07204:application/javascript:public, max-age=300, s-maxage=86400"
 "admin-panel.js:eb4fd9bd748d4f326767dc38c90d05f71ae2f735b9ef0a73284e1a813abb340d:2d02a1cb69d00f4fc148fc3c7f13899532a2bfb84a07f888f740b59fe3b37322:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:b5c3a5511006760f95a8879a3dcfd07261809380efda797fb537c907032b56f7:edcdc42f5d42c9fc4dabeabafdf7ab75d76bf1425cd642f0bd1b89b855fe2388:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
)
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
M=$((10#$(date -u +%M) % 30)); if [ "$DRY" != "true" ] && { [ "$M" -ge 9 ] && [ "$M" -le 13 ]; }; then stop "the autopilot's scheduled run is at :10 and :40 past the hour; run this a few minutes later"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
for js in practice-portfolio.js practice-autopilot.js admin-panel.js; do node --check "$HERE/web/$js" || stop "the staged $js does not parse"; done
grep -q 'practice-portfolio.js?v=40' "$HERE/web/dashboard.html" && grep -q 'practice-autopilot.js?v=55' "$HERE/web/dashboard.html" && grep -q 'admin-panel.js?v=8' "$HERE/web/dashboard.html" && grep -q '5c7pt7qurshld4cwaqyopfxcei0cuurj' "$HERE/web/practice-portfolio.js" || stop "the staged dashboard does not ask for the new versions"
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    l="$([ -f "$WEB/$f" ] && filesha "$WEB/$f" || echo none)"; code=$(curl -s -o "$TMP/live_$f" -w '%{http_code}' "https://stockiq.tech/$f"); v="$([ "$code" = 200 ] && filesha "$TMP/live_$f" || echo none)"; echo "$v" > "$TMP/sha_$f"
    [ "$l" = "$was" ] || [ "$l" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$v" = "$was" ] || [ "$v" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$l" = "$new" ] && echo new || echo old), live $([ "$v" = "$new" ] && echo new || echo old)"
done

say "the website (the script before the page that asks for its new version)"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(cat "$TMP/sha_$f")" = "$new" ] && [ -f "$WEB/$f" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    case "$f" in *.js) PATHS+=("/$f*");; *) PATHS+=("/$f");; esac; echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for p in "/practice-portfolio.js?v=40" "/practice-autopilot.js?v=55" "/admin-panel.js?v=8" "/dashboard.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
