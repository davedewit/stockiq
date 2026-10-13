#!/bin/bash
# One-off deploy (13 Oct 2026): the practice portfolio's graph gets a second line, at the owner's idea: the same
# $100,000 put into an S&P 500 fund at the moment the account began and left there. The two lines above the graph give
# the account and the fund in dollars and say who is ahead; the one line under the three figures says the same.
#   - stockiq-price-proxy: an optional "range" (3mo, 6mo, 1y, 2y, 5y) so the fund's daily prices can reach back to the
#     account's start once the account is older than the month the function answers with by default. Without it, as before.
#   - stockiq-ai-chat: its guide to the dashboard knows the second line.
#   - practice-portfolio.js v=34, dashboard.html (the version number only).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-price-proxy_before_fund_20261013.zip, stockiq-ai-chat_before_fund_20261013.zip;
# the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# function : staged folder : CodeSha256 it was built from : the live file's fingerprint : the new file's fingerprint
LAMBDAS=(
 "stockiq-price-proxy:proxy:ChiaYEvFtFs/w1SvcpNRrmrpFEdjgXZZjC8z3BEhHwk=:76bbb93e786e5be122710abdda96c063b184f509d68f7a061af481c85f07c385:778b43d3073b1e69ec24e92fc1fbedda735d55a0d594844266d3a4619d03498e"
 "stockiq-ai-chat:chat:cQHzRlpev41uioqwNkos3CtAPA3oGOyOV2nsSn1BYU0=:e586af593d9d060d31a6550f9e83a5f252b365f9e4ac2674aef9df9577273621:08204406a4b2947b4896bab941b0a1794287220ded3d81d2495745f941f4c56f"
)
FILES=(
 "practice-portfolio.js:9e0b1dd9aa633c405566cfd88b60d1f967e4e40ec45f70255da9886fe321754d:4f100feea69d9b439ac4ad6fd8db29849f89c9720ba6666e7a504846bc300777:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:1dbb2a18c3a81e42f6ae1e41be76969dac84f03741748fdb2caa80cbb194438c:69a09a3328b5b1b16dc99a0fa0e74f32d39707a0aa03bbb1cca848fd303085ed:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
)
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
for row in "${LAMBDAS[@]}"; do
    IFS=: read -r F dir was old new <<< "$row"
    [ "$(filesha "$HERE/$dir/lambda_function.py")" = "$new" ] || stop "the staged $F is not the one that was tested"
    curl -s -o "$TMP/$dir.zip" "$("${AWS[@]}" lambda get-function --function-name "$F" --query Code.Location --output text)"
    mkdir -p "$TMP/$dir"; unzip -q -o "$TMP/$dir.zip" -d "$TMP/$dir"
    [ "$(unzip -Z1 "$TMP/$dir.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "the package of $F holds other files than lambda_function.py"
    if [ "$(filesha "$TMP/$dir/lambda_function.py")" = "$new" ]; then echo "new" > "$TMP/$dir.state"; echo "$F already has the new code"
    else
        echo "old" > "$TMP/$dir.state"
        [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$was" ] && [ "$(filesha "$TMP/$dir/lambda_function.py")" = "$old" ] || stop "$F has changed on AWS since this was built"
        cmp -s "$TMP/$dir/lambda_function.py" "$ROOT/lambda-sync/$F/lambda_function.py" || stop "the live $F is not the same as the local mirror"
        echo "the live $F is the code this was built from"
    fi
done
python3 -W ignore "$ROOT/check-tools/ai_chat_test.py" "$HERE/chat/lambda_function.py" 2>/dev/null | tail -1 | tee "$TMP/t"; grep -q "ALL PASS" "$TMP/t" || stop "the chat's tests do not pass on the staged function"
python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$HERE/proxy/lambda_function.py" || stop "the staged price function does not parse"
grep -q "range={span}" "$HERE/proxy/lambda_function.py" || stop "the staged price function has no range setting"
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    local_sha="$(filesha "$WEB/$f")"; curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; live_sha="$(filesha "$TMP/live_$f")"
    [ "$local_sha" = "$was" ] || [ "$local_sha" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$live_sha" = "$was" ] || [ "$live_sha" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$local_sha" = "$new" ] && echo new || echo old), live $([ "$live_sha" = "$new" ] && echo new || echo old)"
done
grep -q 'practice-portfolio.js?v=34' "$HERE/web/dashboard.html" || stop "the staged dashboard does not ask for version 34 of the script"
grep -q 'function fundKnots' "$HERE/web/practice-portfolio.js" || stop "the staged script does not have the fund's line"
grep -q '5c7pt7qurshld4cwaqyopfxcei0cuurj' "$HERE/web/practice-portfolio.js" || stop "the staged script has lost the storage address"

for row in "${LAMBDAS[@]}"; do
    IFS=: read -r F dir was old new <<< "$row"
    KEEP="$BACKUP/${F}_before_fund_20261013.zip"
    say "$F"
    if [ "$(cat "$TMP/$dir.state")" = new ]; then echo "already deployed, skipping"
    elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $KEEP and update the function"
    else
        [ -f "$KEEP" ] || cp "$TMP/$dir.zip" "$KEEP"
        mkdir -p "$TMP/new_$dir"; cp "$HERE/$dir/lambda_function.py" "$TMP/new_$dir/lambda_function.py"; (cd "$TMP/new_$dir" && zip -q -X ../new_$dir.zip lambda_function.py)
        "${AWS[@]}" lambda update-function-code --function-name "$F" --zip-file "fileb://$TMP/new_$dir.zip" --query LastModified --output text
        "${AWS[@]}" lambda wait function-updated --function-name "$F"
        [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new_$dir.zip")" ] || stop "$F does not report the new package"
        cp "$HERE/$dir/lambda_function.py" "$ROOT/lambda-sync/$F/lambda_function.py"; echo "live ($(zipsha "$TMP/new_$dir.zip")), and the mirror updated"
    fi
done

say "the website: the script, then the page that asks for it"
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
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
