#!/bin/bash
# One-off deploy (18 Oct 2026): the Admin page's "Answered" list straight under "Decisions for you", the latest three on show
# (the owner: "so i can easily see without having to scroll down"; admin-panel.js?v=14); the contact page says the business is
# StockIQ, a sole trader (it said "StockIQ Pty Ltd"; the owner: "i have an abn ... its sole trader").
#   Preview: DRY_RUN=true bash deploy.sh    Deploy: bash deploy.sh
# Roll back: the files from git, uploaded the same way.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "admin-panel.js:4addac9c2c748a8174670f02437be3646bde1a69fa439c14154f2b9ba5706ca9:ec1747b63b07430b2d2bba3ee7b633093fd15ceba682664303aced78a923622d:application/javascript:public, max-age=300, s-maxage=86400"
 "contact.html:2b279daf256023e7f8e2de72d790f7c0eac89fd2748e86d89d623da1d385afde:1dc7cdffec9592deae55fa9f6c3e9379f27dd4bf4da3796a5946d699dda72e24:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:597d20754b799b57ff7e1dcb6d84974049097387133701b08efc9519b0221ffb:fadc06b573a9666ababe4a0c70d825a5e46dd4d09b3bd07dce20e3686976ef3c:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
)
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
M=$((10#$(date -u +%M) % 30)); if [ "$DRY" != "true" ] && { [ "$M" -ge 9 ] && [ "$M" -le 13 ]; }; then stop "the autopilot's scheduled run is at :10 and :40 past the hour; run this a few minutes later"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
node --check "$HERE/web/admin-panel.js" || stop "the staged admin-panel.js does not parse"
grep -q "admin-panel.js?v=14" "$HERE/web/dashboard.html" || stop "the staged dashboard does not ask for the new version"
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    l="$([ -f "$WEB/$f" ] && filesha "$WEB/$f" || echo none)"; code=$(curl -s -o "$TMP/live_$f" -w '%{http_code}' "https://stockiq.tech/$f"); v="$([ "$code" = 200 ] && filesha "$TMP/live_$f" || echo none)"; echo "$v" > "$TMP/sha_$f"
    [ "$l" = "$was" ] || [ "$l" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$v" = "$was" ] || [ "$v" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$l" = "$new" ] && echo new || echo old), live $([ "$v" = "$new" ] && echo new || echo old)"
done

say "the website (the scripts first, then the pages)"
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
    for row in "${FILES[@]}"; do IFS=: read -r p _r <<< "$row"; p="/$p"; curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
