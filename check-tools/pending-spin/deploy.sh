#!/bin/bash
# One-off deploy (13 Oct 2026): the Practice portfolio shows the site's spinner while it loads, not the word "Loading…",
# and loads sooner after a refresh: the prices of what it held last time (remembered in the browser) are asked for at
# once, together with the portfolio, instead of only after it has arrived. Measured on the owner's account: 3.5 s
# became 2.3 s on a first load, 1.4 s became 1.1 s after that. practice-portfolio.js v=31 and dashboard.html.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
FILES=(
 "practice-portfolio.js:762467a62af654f1a62d52db79266a2a52574fb03d67fd5f29b9a1eed5353086:c411bbe97abad6044d611361f4779b969099552d6975c409808d6e6105773f05:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:1cf1b90a7de36c4e26cb098f3b966f8e99a3aaf0327ed85faa82c18be7335a66:27ad373a26c2397d6d244f7d6ec02f8fbc266a984d06ab38fd6ce159064d55c4:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
sed 's#https://5c7pt7qurshld4cwaqyopfxcei0cuurj.lambda-url.us-east-1.on.aws/#__PRACTICE_API_URL__#' "$HERE/web/practice-portfolio.js" > "$TMP/pp.js"   # never the real storage address in a test
grep -q "__PRACTICE_API_URL__" "$TMP/pp.js" || stop "the storage address was not taken out of the test copy"
node "$ROOT/check-tools/practice_test.js" "$TMP/pp.js" 2>/dev/null | grep -c "^FAIL" | tee "$TMP/t2" >/dev/null || true; [ "$(cat "$TMP/t2")" = "0" ] || stop "the portfolio's tests do not pass on the staged script"; echo "portfolio tests: $(node "$ROOT/check-tools/practice_test.js" "$TMP/pp.js" 2>/dev/null | grep -c "^PASS") pass, 0 fail"

say "the website: the portfolio's script, then the page that asks for its new version"
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
    curl -s -o "$TMP/v" "https://stockiq.tech/practice-portfolio.js?v=31"; cmp -s "$TMP/v" "$WEB/practice-portfolio.js" && echo "live /practice-portfolio.js?v=31 equals the local file" || stop "the versioned address does not give the new script"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
