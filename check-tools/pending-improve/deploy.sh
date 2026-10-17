#!/bin/bash
# One-off deploy (17 Oct 2026): improvements in two places, each for its reader (the owner: "one is for everyone the other is just for
# me so perhaps the one for everyone a lighter version showing improvements only").
#   - The AI autopilot tab's "Improving its own rules" becomes "How it is improving": being tested now, improvements made (kept or
#     taken out, with dates), coming next; its rules and the trials in full folded under "The details". Besides its own trials it
#     lists the site's changes marked public in check-tools/experiments.json (stockiq-ai-trader sends them as `improvements`,
#     kept 15 minutes in the warm function).
#   - The Admin page has two views: Overview (as before, with a short Improvements card) and Improvements (the whole list and
#     its history, marking what users also see).
#   - stockiq-ai-chat: the section's new name; the buying-order trial ended on 17 Oct and was not kept.
#   practice-autopilot.js?v=54, admin-panel.js?v=7, dashboard.html.
#   Preview: DRY_RUN=true bash deploy.sh    Deploy: bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_improve_20261017.zip, stockiq-ai-chat_before_improve_20261017.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# function : staged folder : CodeSha256 it has : its file's fingerprint : the staged file's : the rollback zip's name
FUNCS=(
 "stockiq-ai-trader:lambda:FIDgcwIc/7pHk4IR9qmIvKE8+f5xAzLy2iuhO0iiB7M=:2fb385b38ddb8505146e7762971fcb025104500b15365f81a7bbde838d8a3dcc:ceef17ae8c38422ac7482b3c1901b6ff889924741d0d629c629d68b79e0a6474:before_autopilot_improve_20261017"
 "stockiq-ai-chat:chat:vbSJYa+xDmDxI3D2gIysxdmo1uCkhxcKgj8XpHxWaUQ=:02d759236b4f16049b392f89eca9fbda0a0e757b067223192d01280fd510f702:6799f1e5950d7605660fc287a4f20e406f0d4182d5b551e42e62992a70c6c9ff:before_improve_20261017"
)
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "practice-autopilot.js:20d9defda9bc93ed6ad540a1c0de5b3384277fedffddc381eb219664210a0085:e3ad3d2e4ef2da05a7c1a7ac76853913223b3f43f37f0138a2e7ee1d4b0642d3:application/javascript:public, max-age=300, s-maxage=86400"
 "admin-panel.js:3293daf4fe8cbe7406762cab3278dd36a010ca7841fcf27bd232024206ff193c:eb4fd9bd748d4f326767dc38c90d05f71ae2f735b9ef0a73284e1a813abb340d:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:779fb112d22e6372aae87ca88fad267a7e42790c889ac30c2d6a78a7d57bd90e:b5c3a5511006760f95a8879a3dcfd07261809380efda797fb537c907032b56f7:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
for js in practice-autopilot.js admin-panel.js; do node --check "$HERE/web/$js" || stop "the staged $js does not parse"; done
grep -q 'practice-autopilot.js?v=54' "$HERE/web/dashboard.html" && grep -q 'admin-panel.js?v=7' "$HERE/web/dashboard.html" || stop "the staged dashboard does not ask for the new versions"
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
    for p in "/practice-autopilot.js?v=54" "/admin-panel.js?v=7" "/dashboard.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
