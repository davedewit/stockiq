#!/bin/bash
# One-off deploy (12 Oct 2026): the practice portfolio's buttons and wording, and the autopilot panel's button feedback.
#  - website/practice-portfolio.js: "Refresh prices" and "Reset fake money" beside the heading; every button a class with a
#    hover colour, a pressed look and a spinner while it works; "Prices updated 10:21:05" after a refresh; what is typed in
#    the buy row survives a refresh; "Whose result is whose" gives both parties the same sold / still-held split.
#  - website/practice-autopilot.js: the same hover, pressed and busy feedback on its buttons and two links.
#  - website/dashboard.html: a place beside the heading for the two buttons, and the two scripts' version numbers.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice. Stops if a live or local file is not what this was built from. Roll back: the three files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : sha256 before : sha256 after : content type : how long a copy may be kept (site-overview.md section 5, step 8)
FILES=(
 "practice-portfolio.js:2a3f8209d48e02881765d3bbee7941ee2a5be0497280d2b57d2e71a94dc38e73:d6ef1c451bb63add6b737938f2d14f36bbcf4c8792979114a899cac55888d007:application/javascript:public, max-age=300, s-maxage=86400"
 "practice-autopilot.js:43520270763f5de37688735588a80bd001df0ec035dfe9d1d8b99746f4b40593:11c9ae8cd83ef1bb63e0c560f66a4a0130771ea822ef2442d9d344f6abfbed51:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:b86167e4cc2355d39a1da6fd360668fa157ce260d8f2efe308ab7c26f0783d06:8b8c186a2028e1ed9b2027b52cf8b0240abd11cb625c6366b43abd45beeb31bc:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
node -c "$HERE/web/practice-portfolio.js"; node -c "$HERE/web/practice-autopilot.js"
say "the website: the two scripts first, then the page that asks for their new versions"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it ($ctype; $cache)"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    PATHS+=("/$f"); echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for p in "${PATHS[@]}"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB$p" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
    for v in "practice-portfolio.js?v=20" "practice-autopilot.js?v=39"; do curl -s -o "$TMP/v" "https://stockiq.tech/$v"; cmp -s "$TMP/v" "$WEB/${v%%\?*}" && echo "live /$v equals the local file" || stop "the versioned address /$v does not give the new script"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
