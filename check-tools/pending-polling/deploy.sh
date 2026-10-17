#!/bin/bash
# One-off deploy (17 Oct 2026): pages ask for market data far less often. The home page fetched each of its four movers
# lists every second and its market widgets every 10 seconds while a tab was open (about 17,000 calls an hour from one
# tab); the dashboard fetched its ticker every 10 seconds, twice over. Now once a minute, and not while the tab is hidden.
#   Preview: DRY_RUN=true bash deploy.sh      Deploy: bash deploy.sh      Roll back: the two files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
FILES=(
 "index.html:5fcb3652b459460074f490a5dbf1efddfe64a44ffb160318528d641e116e1535:9451afe8785930db91e68e7d64ee4916e13e15f79b1d3d2bb4ff61821a1ee9b5:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:c50823acc18d52ef1c96752d0fd4ca0a8722c22fcdd390edbfd5f5a354e2e7c8:80dfd6044a0aaaa1bc8504df339049501e1b54d023b62efaf1dea79e2d59e8db:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
)
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"
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
    for p in "/index.html" "/dashboard.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
echo "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
