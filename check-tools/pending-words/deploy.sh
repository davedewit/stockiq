#!/bin/bash
# One-off deploy (12 Oct 2026, evening): the dashboard's wording brought into line with what the autopilot does.
# Found when the owner asked for every statement to be checked: the panel said "it buys at most 3 at a check-in" (with
# many holdings it is a fifth of them: 10 at 50); it said every holding is sold when its screener signal turns and is
# reviewed by the AI model (not so for the "patient" shares of the trial that began today); and the trial was not
# listed under "Improving its own rules". practice-autopilot.js v=43, practice-portfolio.js v=23 (a patient share's
# line under its name), dashboard.html (the two version numbers).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Safe to run twice. Stops if a live file is not what this was built from. Roll back: the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
FILES=(
 "practice-autopilot.js:4e98de55030387864edc39e3cae24a346d1bd9871adc9b7ab0e431564379830c:83dfb5e06e1b0886e676082d79a308da96c2382c563c647429c5b0c63c636d80:application/javascript:public, max-age=300, s-maxage=86400"
 "practice-portfolio.js:26eb5153d24a1c66f405449af98d6788424e9bf5420c74e1d4bec1f6ee4a4a09:490a1af9fa06aa6ebb16b27275858c84271554e9ab803a17d17878bacab2eb24:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:1c61cc5681a6248b8b65d3fc927d262751e3182524652f7bbcc10a708c7fe677:33310f5dc78f9847cb9471767a23a569e1676f4c711150feff56de1fa19823d6:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
node -c "$HERE/web/practice-autopilot.js"; node -c "$HERE/web/practice-portfolio.js"
sed 's#https://5c7pt7qurshld4cwaqyopfxcei0cuurj.lambda-url.us-east-1.on.aws/#__PRACTICE_API_URL__#' "$HERE/web/practice-portfolio.js" > "$TMP/pp.js"; grep -q "__PRACTICE_API_URL__" "$TMP/pp.js" || stop "the storage address was not taken out of the test copy"
[ "$(node "$ROOT/check-tools/practice_test.js" "$TMP/pp.js" 2>/dev/null | grep -c "^FAIL")" = "0" ] || stop "the portfolio tests do not pass on the staged script"
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
    curl -s -o "$TMP/v" "https://stockiq.tech/practice-autopilot.js?v=43"; cmp -s "$TMP/v" "$WEB/practice-autopilot.js" && echo "live /practice-autopilot.js?v=43 equals the local file" || stop "the versioned address does not give the new script"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
