#!/bin/bash
# One-off deploy (12 Oct 2026, evening): "Holding now" as a row a holding.
# Ten holdings were one paragraph nobody could read (the owner sent a picture), and there can be fifty. Now: a row a
# holding, newest first (bought, sold by, limits, and small tags for what is particular: market closed, the stop,
# a patient share, the AI review), the full plan folded under each, eight on show and the older ones folded away.
# Also "tests changes" for "tries changes" in two sentences. practice-autopilot.js v=44 and dashboard.html.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
FILES=(
 "practice-autopilot.js:83dfb5e06e1b0886e676082d79a308da96c2382c563c647429c5b0c63c636d80:8e6e07ce4eba2416252f08f735fc5ec3a07c018936d103fd9dccd04cb0d0d2ce:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:e816e88829d819d56595e49a85547f90df6727e1e330b6e0903f6b1026f3387f:f42017bf3366c30c80fa466a41395e447a63fdc2a747d0457457d75f93966789:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
node -c "$HERE/web/practice-autopilot.js"
node "$ROOT/check-tools/autopilot_test.js" "$HERE/web/practice-autopilot.js" 2>/dev/null | tail -1 | tee "$TMP/t2"; grep -q "ALL PASS" "$TMP/t2" || stop "the panel's tests do not pass on the staged script"

say "the website: the panel's script, then the page that asks for its new version"
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
    curl -s -o "$TMP/v" "https://stockiq.tech/practice-autopilot.js?v=44"; cmp -s "$TMP/v" "$WEB/practice-autopilot.js" && echo "live /practice-autopilot.js?v=44 equals the local file" || stop "the versioned address does not give the new script"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
