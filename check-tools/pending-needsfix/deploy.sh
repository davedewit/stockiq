#!/bin/bash
# One-off deploy (23 Oct 2026): "Needs you" counts the sector funds (it warned of a budget too large / cash too small that were not);
# the screeners the AI ticks greyed out and locked, with a clear tick. stockiq-ai-trader; practice-autopilot.js, dashboard.html.
# Preview: DRY_RUN=true bash deploy.sh.  Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_needsfix_20261023.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# function : staged folder : file : CodeSha256 it has : its file's fingerprint : the staged file's : the rollback zip's name
FUNCS=(
 "stockiq-ai-trader:lambda:lambda_function.py:PbBzV+oyR/ycUNB3Qmzqqse39I1c3oIzo0hnBcRVCQw=:f920025acb2190cd1f00bcfb8353caadfa307b54ad7c80bbde3e2b24911ca5b7:798da3214e1adfa21cb54bef35c09a578a2816d82f290fce03a3f602d929d11d:before_autopilot_needsfix_20261023"
)
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "practice-autopilot.js:8abb56d91f7f143000581a81e00678303ccf43dd51e6cfde6d808d265e1390dc:15df3e74894fe2708c3c680cde80f83b29724fbf0c8ac56bcc4791eb831abb81:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:5971f55494f85c9a0dd52cb7a981d6dd27a3a159870704d55089c449a8a66c13:97bf3d5d69d28e3acc9d399d4d2461a798445f89bd4f9632f9b11b11b9d5b445:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
    IFS=: read -r f dir fn was old new keep <<< "$row"
    [ "$(filesha "$HERE/$dir/$fn")" = "$new" ] || stop "the staged $f is not the one that was tested"
    python3 -m py_compile "$HERE/$dir/$fn" || stop "the staged $f does not compile"
    curl -s -o "$TMP/$f.zip" "$("${AWS[@]}" lambda get-function --function-name "$f" --query Code.Location --output text)"
    mkdir -p "$TMP/$f"; unzip -q -o "$TMP/$f.zip" -d "$TMP/$f"
    [ "$(unzip -Z1 "$TMP/$f.zip" | tr '\n' ' ')" = "$fn " ] || stop "the package of $f holds other files than $fn"
    if [ "$(filesha "$TMP/$f/$fn")" = "$new" ]; then echo "$f already has the new code"
    else
        [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$f" --query CodeSha256 --output text)" = "$was" ] && [ "$(filesha "$TMP/$f/$fn")" = "$old" ] || stop "$f has changed on AWS since this was built"
        cmp -s "$TMP/$f/$fn" "$ROOT/lambda-sync/$f/$fn" || stop "the live $f is not the same as the local mirror"
        echo "the live $f is the code this was built from"
    fi
done
for j in practice-autopilot.js; do node --check "$HERE/web/$j" || stop "the staged $j does not parse"; done
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
    IFS=: read -r f dir fn was old new keep <<< "$row"
    if [ "$(filesha "$TMP/$f/$fn")" = "$new" ]; then echo "$f: already deployed, skipping"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${f}_$keep.zip and update $f"; continue; fi
    [ -f "$BACKUP/${f}_$keep.zip" ] || cp "$TMP/$f.zip" "$BACKUP/${f}_$keep.zip"
    mkdir -p "$TMP/new_$f"; cp "$HERE/$dir/$fn" "$TMP/new_$f/$fn"; (cd "$TMP/new_$f" && zip -q -X ../new_$f.zip $fn)
    "${AWS[@]}" lambda update-function-code --function-name "$f" --zip-file "fileb://$TMP/new_$f.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$f"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$f" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new_$f.zip")" ] || stop "$f does not report the new package"
    cp "$HERE/$dir/$fn" "$ROOT/lambda-sync/$f/$fn"; echo "$f: live ($(zipsha "$TMP/new_$f.zip")), and the mirror updated"
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
    for p in "/practice-autopilot.js" "/dashboard.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
