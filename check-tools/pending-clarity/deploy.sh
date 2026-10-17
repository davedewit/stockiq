#!/bin/bash
# One-off deploy (17 Oct 2026): clearer profit and loss, and no budget held back for a resting screener.
#   - stockiq-ai-trader: a market whose every ticked screener is resting gets no share of the budget, so its part goes to the
#     markets that can buy (the rested coin screener had held a fifth back as cash, 15-17 Oct); the check-in note says so
#     (patch_lambda.py applied to the live code of 04:54 UTC, the Admin page).
#   - practice-autopilot.js: its copy of the split does the same, and a resting market's box and line say so.
#   - practice-portfolio.js: "The breakdown" is one profit-and-loss table (sold / still held / since the start, for your own
#     buys, the autopilot and together), where the money is, and the index fund in two plain lines; "Today" has one percentage.
#   - stockiq-ai-chat: its guide describes the new breakdown.  dashboard.html: the two scripts' version numbers only.
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_clarity_20261017.zip, stockiq-ai-chat_before_clarity_20261017.zip;
#   the three website files from git (website commit before this one).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# function : staged folder : CodeSha256 it has : its file's fingerprint : the staged file's : the rollback zip's name
FUNCS=(
 "stockiq-ai-trader:lambda:vSGWQgIB+lN7FUeW1WzrdslLoIz3KiY4aoeKPzxjYrM=:0140f46f8c65a30e8be23f470faa7a6611327447ee2172d74b74db0f8af77fba:9565f24ff825a4871a534346b92a57a26ee3bc169e71976957ba7a27ef754ed1:before_autopilot_clarity_20261017"
 "stockiq-ai-chat:chat:9K5HRpizpV9lHdwP8eOwKpB00IGaNRgUz2qQEQRi6rs=:2e103290b35f251a8db0b5206c7a24e6d6665e238be2e74801d19931750623d4:c7862caa95340dec93bc74217182b45af8e59f9945069649dfbfdfe36e55a45c:before_clarity_20261017"
)
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "practice-portfolio.js:77079a71f71af79fb27245080eaacdb1a3413c3a4e5118e8f61a0526b8488c35:8a329307a80e8310da9fc3866c5d2cc63a2a254f3222ef12daaaf107468fda82:application/javascript:public, max-age=300, s-maxage=86400"
 "practice-autopilot.js:15e2d0d78a1fc36bd90dce843d4502281e4c0a0f245272595c5332dd26b430f5:f226a8756e6a1db62173ea42fe1d2011dd738e4d4cbc669f014bfb6e07aa5461:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:5ee05cf4abf46f6f4396331d29441fd24a9ce332a081f5d730d2cab64dfeb896:702911486ae844f5d78382af8907dfcef7c612b38a568d71345286e4107aec41:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
)
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
M=$((10#$(date -u +%M) % 30)); if [ "$DRY" != "true" ] && { [ "$M" -ge 9 ] && [ "$M" -le 13 ]; }; then stop "the autopilot's scheduled run is at :10 and :40 past the hour; run this a few minutes later"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
for row in "${FUNCS[@]}"; do
    IFS=: read -r f dir was old new keep <<< "$row"
    [ "$(filesha "$HERE/$dir/lambda_function.py")" = "$new" ] || stop "the staged $f is not the one that was tested"
    python3 -m py_compile "$HERE/$dir/lambda_function.py" || stop "the staged $f does not compile"
    curl -s -o "$TMP/$f.zip" "$("${AWS[@]}" lambda get-function --function-name "$f" --query Code.Location --output text)"
    mkdir -p "$TMP/$f"; unzip -q -o "$TMP/$f.zip" -d "$TMP/$f"
    [ "$(unzip -Z1 "$TMP/$f.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "the package of $f holds other files than lambda_function.py"
    if [ "$(filesha "$TMP/$f/lambda_function.py")" = "$new" ]; then echo "$f already has the new code"
    else
        [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$f" --query CodeSha256 --output text)" = "$was" ] && [ "$(filesha "$TMP/$f/lambda_function.py")" = "$old" ] || stop "$f has changed on AWS since this was built"
        cmp -s "$TMP/$f/lambda_function.py" "$ROOT/lambda-sync/$f/lambda_function.py" || stop "the live $f is not the same as the local mirror"
        echo "the live $f is the code this was built from"
    fi
done
for js in practice-portfolio.js practice-autopilot.js; do node --check "$HERE/web/$js" || stop "the staged $js does not parse"; done
grep -q 'practice-portfolio.js?v=36' "$HERE/web/dashboard.html" && grep -q 'practice-autopilot.js?v=48' "$HERE/web/dashboard.html" || stop "the staged dashboard does not ask for the new versions"
grep -q '5c7pt7qurshld4cwaqyopfxcei0cuurj' "$HERE/web/practice-portfolio.js" || stop "the staged portfolio script lost its storage address"
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    l="$([ -f "$WEB/$f" ] && filesha "$WEB/$f" || echo none)"; code=$(curl -s -o "$TMP/live_$f" -w '%{http_code}' "https://stockiq.tech/$f"); v="$([ "$code" = 200 ] && filesha "$TMP/live_$f" || echo none)"; echo "$v" > "$TMP/sha_$f"
    [ "$l" = "$was" ] || [ "$l" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$v" = "$was" ] || [ "$v" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$l" = "$new" ] && echo new || echo old), live $([ "$v" = "$new" ] && echo new || echo old)"
done

say "the functions"
for row in "${FUNCS[@]}"; do
    IFS=: read -r f dir was old new keep <<< "$row"
    if [ "$(filesha "$TMP/$f/lambda_function.py")" = "$new" ]; then echo "$f: already deployed, skipping"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${f}_$keep.zip and update $f"; continue; fi
    [ -f "$BACKUP/${f}_$keep.zip" ] || cp "$TMP/$f.zip" "$BACKUP/${f}_$keep.zip"
    mkdir -p "$TMP/new_$f"; cp "$HERE/$dir/lambda_function.py" "$TMP/new_$f/lambda_function.py"; (cd "$TMP/new_$f" && zip -q -X ../new_$f.zip lambda_function.py)
    "${AWS[@]}" lambda update-function-code --function-name "$f" --zip-file "fileb://$TMP/new_$f.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$f"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$f" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new_$f.zip")" ] || stop "$f does not report the new package"
    cp "$HERE/$dir/lambda_function.py" "$ROOT/lambda-sync/$f/lambda_function.py"; echo "$f: live ($(zipsha "$TMP/new_$f.zip")), and the mirror updated"
done

say "the website (the script before the page that asks for its new version)"
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
    for p in "/practice-portfolio.js" "/practice-portfolio.js?v=36" "/practice-autopilot.js" "/practice-autopilot.js?v=48" "/dashboard.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
