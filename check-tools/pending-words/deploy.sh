#!/bin/bash
# One-off deploy (13 Oct 2026): words in the autopilot's breakdown and progress tables. "Ended up" is "Made money",
# "By place in the ranking when bought" names whose ranking, and a line under the breakdown says it counts only the
# autopilot's own finished trades (the owner looked for a trade he had made by hand). dashboard.html asks for ?v=47.
#   Preview: DRY_RUN=true bash deploy.sh      Deploy: bash deploy.sh      Roll back: the two files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
FILES=(
 "practice-autopilot.js:f3fee809abcdf59d8d9e1890857b1b2b30c563bd737bf2be4367cc5e108a6343:15e2d0d78a1fc36bd90dce843d4502281e4c0a0f245272595c5332dd26b430f5:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:7bc4f2a11c7030d12971f97a79cd3d821ce7a7553db1b852c07b2286ae829fc0:c50823acc18d52ef1c96752d0fd4ca0a8722c22fcdd390edbfd5f5a354e2e7c8:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
)
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"
node --check "$HERE/web/practice-autopilot.js" || stop "the staged panel does not parse"
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    l="$(filesha "$WEB/$f")"; curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; v="$(filesha "$TMP/live_$f")"
    [ "$l" = "$was" ] || [ "$l" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$v" = "$was" ] || [ "$v" = "$new" ] || stop "the live $f is neither the old nor the new file"
done
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    case "$f" in *.js) PATHS+=("/$f*");; *) PATHS+=("/$f");; esac; echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for p in "/practice-autopilot.js?v=47" "/dashboard.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
echo "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
