#!/bin/bash
# One-off deploy (12 Oct 2026, evening): on the Practice portfolio's holdings table the autopilot's plan for a holding
# (a long sentence, the same shape under every holding) is folded behind an arrow: "Autopilot: its plan for this". The
# name, the company and why it was bought stay on show; an opened plan stays open across redraws. A holding bought by
# the user keeps its one plain line. practice-portfolio.js v=28 and the version number in dashboard.html.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
FILES=(
 "practice-portfolio.js:3578ea993ebd9d68de411bc778c1589d0a660ad43a23529930ee4b324ceaedd4:9870da2098f0100a3f610aa2df26c2724ca6a5b380fbb84fdd883e06a20ebf11:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:cb705712607d86cc11dfbe715188bab64a47e87291ed6ede5c7bdc03de86f116:da1ce458d3b959aaefa1c44eb5d66db8c77e67251484a22f92982aae7443774a:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
    curl -s -o "$TMP/v" "https://stockiq.tech/practice-portfolio.js?v=28"; cmp -s "$TMP/v" "$WEB/practice-portfolio.js" && echo "live /practice-portfolio.js?v=28 equals the local file" || stop "the versioned address does not give the new script"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
