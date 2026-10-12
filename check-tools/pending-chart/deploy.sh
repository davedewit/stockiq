#!/bin/bash
# One-off deploy (12 Oct 2026): a graph of the account over time on the dashboard's Practice portfolio tab.
#  - website/practice-portfolio.js: under the four cards, a line of the account's value since it began (or of the user's own
#    buys, or of the autopilot's part), worked out in the browser from the holdings, the sold list and the month of daily
#    prices that already comes with every quote. No function is changed and no extra request is made.
#  - website/dashboard.html: only the script's version number (?v=19).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice. Stops if a live or local file is not what this was built from. Roll back: the two files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : sha256 before : sha256 after : content type : how long a copy may be kept (site-overview.md section 5, step 8)
FILES=(
 "practice-portfolio.js:b48ff650293ce09eb8c892ba53825b7f607d531f060f55970629351f5cac8123:/Users/dave/VSCODE/stockiq/check-tools/pending-chart/2a3f8209d48e02881765d3bbee7941ee2a5be0497280d2b57d2e71a94dc38e73pplication/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:bec16da1ef4cb2796e9505ba802994f44898f9a079139ac966a337a91d78a45d:a847afdbe81aa4602727b6a20177466f58e32f8d1d39f3a6e6dbea40cb4c398cext/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
node -c "$HERE/web/practice-portfolio.js"
say "the website: the script first, then the page that asks for its new version"
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
    curl -s -o "$TMP/v" "https://stockiq.tech/practice-portfolio.js?v=19"; cmp -s "$TMP/v" "$WEB/practice-portfolio.js" && echo "live /practice-portfolio.js?v=19 equals the local file" || stop "the versioned address does not give the new script"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
