#!/bin/bash
# One-off deploy (23 Oct 2026): emails only for what changes how it trades (not the AI model's notes); a clear tick in the boxes the AI
# ticks; prices fetched at once when the Practice portfolio comes back into view; the chat's guide on emails and the coin score.
# stockiq-ai-trader, stockiq-ai-chat; practice-autopilot.js, practice-portfolio.js, dashboard.html.   Preview: DRY_RUN=true bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_mailfilter_20261023.zip, stockiq-ai-chat_before_mailfilter_20261023.zip;
# the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# function : staged folder : file : CodeSha256 it has : its file's fingerprint : the staged file's : the rollback zip's name
FUNCS=(
 "stockiq-ai-trader:lambda:lambda_function.py:nHBDYxpm9uoliTHv0bgvkA0y4mHPc+vUzm+2i1HqUaw=:1af2ecc17aa12a7db8d10e601a06d0bfe26081191386fbe00e3b557c4fc25f62:f920025acb2190cd1f00bcfb8353caadfa307b54ad7c80bbde3e2b24911ca5b7:before_autopilot_mailfilter_20261023"
 "stockiq-ai-chat:chat:lambda_function.py:ZeIoqtbC7nDkP4iwOk3qKMJ8OYukPlhEs054kT8m/9E=:bfb5416f8d710c3f89dc8782d8e97a3cc40c43b80ceb9be045030c553efc2a9e:942f6b9cdf5360645e6164d79935552e182e3924194603ff0d63254afcc8b15b:before_mailfilter_20261023"
)
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "practice-autopilot.js:5acef8e1d276d0e6b336c2d45f89b2943dae9402e2e0c818e3211ade9bab7089:8abb56d91f7f143000581a81e00678303ccf43dd51e6cfde6d808d265e1390dc:application/javascript:public, max-age=300, s-maxage=86400"
 "practice-portfolio.js:0be2ae98123eb788a95c7762117a60c06115dfb7c6f6ae128cb41d07644c8b54:a5482eb82493f68d6473c2c77c1a25f842ce6ed980f495682ce51730062cfd8f:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:095ab0c3cebe977fe77c3a59a43797b055a50c7eb9bc2907fde588225600c3fa:5971f55494f85c9a0dd52cb7a981d6dd27a3a159870704d55089c449a8a66c13:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
for j in practice-autopilot.js practice-portfolio.js; do node --check "$HERE/web/$j" || stop "the staged $j does not parse"; done
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
    for p in "/practice-autopilot.js" "/practice-portfolio.js" "/dashboard.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
