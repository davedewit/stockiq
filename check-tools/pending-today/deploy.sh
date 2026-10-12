#!/bin/bash
# One-off deploy (12 Oct 2026, evening): "Today" on the practice portfolio.
# The owner: opening the dashboard in the middle of a day, the first thing he wants is what it has gained or lost today.
# Now the Account value and In holdings cards show "Today" above the total, and the holdings table has a Today column
# beside "Since bought" (it was "Change"). Today is each holding since its market's previous close (a coin: since
# 00:00 UTC), or since it was bought if later; with a market closed it is its last session; sales made today are not in
# it (the fine print says so). Worked out in the browser from the daily prices that already come with every quote.
# practice-portfolio.js v=27 and the version number in dashboard.html.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
FILES=(
 "practice-portfolio.js:da35f48fb9cdbfd6f6d7359d8ffa4aec6daf51c731867e7bc1f9338fbafa791e:3578ea993ebd9d68de411bc778c1589d0a660ad43a23529930ee4b324ceaedd4:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:f42017bf3366c30c80fa466a41395e447a63fdc2a747d0457457d75f93966789:17ee401332167e9d3f62fff1125add70d41fb12e7e42a5037ea2bbf9a39c03f1:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
    curl -s -o "$TMP/v" "https://stockiq.tech/practice-portfolio.js?v=27"; cmp -s "$TMP/v" "$WEB/practice-portfolio.js" && echo "live /practice-portfolio.js?v=27 equals the local file" || stop "the versioned address does not give the new script"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
