#!/bin/bash
# One-off deploy (18 Oct 2026): the market data on a page moves while someone looks at it (the owner: "they should update often
# so when users on the page they see its active ... only if user is active on page").
#   - ticker-data-fetcher: the symbols fetched side by side (26 in 0.6 s instead of 9), each with a time limit, at most 40 a
#     call; with "spark": true a short line of today's prices for each (older callers get exactly what they got before).
#   - live-market.js (new, loaded by theme.js on every page with market data): a request every 6 to 10 seconds while the tab is
#     on screen and in use, the figures flash when they move, the side panel's charts are today's real line.
#   - index.html, dashboard.html: their own loops every 5 minutes (they only keep the lists up to date now).
#   Preview: DRY_RUN=true bash deploy.sh    Deploy: bash deploy.sh
# Roll back: ~/VSCODE/backup/ticker-data-fetcher_before_live_20261018.zip; the website files from git. To switch the live
# figures off alone: take the lines between LIVE_MARKET_START and LIVE_MARKET_END out of theme.js.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# function : staged folder : CodeSha256 it has : its file's fingerprint : the staged file's : the rollback zip's name
FUNCS=(
 "ticker-data-fetcher:lambda:1v0pxbTHMDjRNngeNCyNYHAp1alsuSGCbANcLkUFm1s=:d67ed90f819d8ce6fc1f8b5bfb4d4977e5622004eb88e7434aa78647786f86d9:9d157d6f3988cef3bc242c5ffd501ea8aa1f43cbbc62ae9f83905652fd023795:before_live_20261018"
)
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "live-market.js:none:218485da97a30cceeca8131ddb351c384f0c3a4d3ad84d6325931bb577a9bf37:application/javascript:public, max-age=300, s-maxage=86400"
 "theme.js:bb9a94a7e6c26887b627a97668fd02506ec6cb299b49c8d5445e83a127ceccf7:2c37dab4e23a2737e520e1c1140768e93bb216bc7daa38162968968e19c988a6:application/javascript:public, max-age=300, s-maxage=86400"
 "index.html:b62fbbea593b0f45d59c3dcbab3440662a56502b1544866a9f382767bc4b7d46:6ffaf6a1d6d6fefaad5ebe8053ee7b7a90b0757823b38e1c3965bb2005ef1088:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:fa8fe359a74b6b36fc4b41ac6bb1c50eea1fdae0907d8af0d1a290aa31870ad8:2aab536c91d30d64eb8d35ab46109db6b06eecf838f959d725cd148f4a545891:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
    [ "$(filesha "$HERE/$dir/lambda-ticker-data.py")" = "$new" ] || stop "the staged $f is not the one that was tested"
    python3 -m py_compile "$HERE/$dir/lambda-ticker-data.py" || stop "the staged $f does not compile"
    curl -s -o "$TMP/$f.zip" "$("${AWS[@]}" lambda get-function --function-name "$f" --query Code.Location --output text)"
    mkdir -p "$TMP/$f"; unzip -q -o "$TMP/$f.zip" -d "$TMP/$f"
    [ "$(unzip -Z1 "$TMP/$f.zip" | tr '\n' ' ')" = "lambda-ticker-data.py " ] || stop "the package of $f holds other files than lambda-ticker-data.py"
    if [ "$(filesha "$TMP/$f/lambda-ticker-data.py")" = "$new" ]; then echo "$f already has the new code"
    else
        [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$f" --query CodeSha256 --output text)" = "$was" ] && [ "$(filesha "$TMP/$f/lambda-ticker-data.py")" = "$old" ] || stop "$f has changed on AWS since this was built"
        cmp -s "$TMP/$f/lambda-ticker-data.py" "$ROOT/lambda-sync/$f/lambda-ticker-data.py" || stop "the live $f is not the same as the local mirror"
        echo "the live $f is the code this was built from"
    fi
done
for js in live-market.js theme.js; do node --check "$HERE/web/$js" || stop "the staged $js does not parse"; done
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
    if [ "$(filesha "$TMP/$f/lambda-ticker-data.py")" = "$new" ]; then echo "$f: already deployed, skipping"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${f}_$keep.zip and update $f"; continue; fi
    [ -f "$BACKUP/${f}_$keep.zip" ] || cp "$TMP/$f.zip" "$BACKUP/${f}_$keep.zip"
    mkdir -p "$TMP/new_$f"; cp "$HERE/$dir/lambda-ticker-data.py" "$TMP/new_$f/lambda-ticker-data.py"; (cd "$TMP/new_$f" && zip -q -X ../new_$f.zip lambda-ticker-data.py)
    "${AWS[@]}" lambda update-function-code --function-name "$f" --zip-file "fileb://$TMP/new_$f.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$f"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$f" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new_$f.zip")" ] || stop "$f does not report the new package"
    cp "$HERE/$dir/lambda-ticker-data.py" "$ROOT/lambda-sync/$f/lambda-ticker-data.py"; echo "$f: live ($(zipsha "$TMP/new_$f.zip")), and the mirror updated"
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
    for p in "/live-market.js" "/theme.js" "/index.html" "/dashboard.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
