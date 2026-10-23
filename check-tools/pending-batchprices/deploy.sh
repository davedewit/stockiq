#!/bin/bash
# One-off deploy (23 Oct 2026): the price function answers many symbols in one request (?symbols=A,B,C), and the practice portfolio
# asks for its prices in six requests of up to 20 instead of one request each (a browser sends six at a time: 60 prices took about 15 seconds).
# stockiq-price-proxy (memory 128 -> 256 MB); practice-portfolio.js, dashboard.html.   Preview: DRY_RUN=true bash deploy.sh    Deploy: bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-price-proxy_before_batch_20261023.zip (and memory 128); the website files from git. The page
# falls back to single requests when the many-symbols form fails, so either half can be rolled back alone.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# function : staged folder : file : CodeSha256 it has : its file's fingerprint : the staged file's : the rollback zip's name
FUNCS=(
 "stockiq-price-proxy:lambda:lambda_function.py:lzqBC+6a/h51byePPZpa+e29ACnMZGPQp+TEt2SQJ8g=:778b43d3073b1e69ec24e92fc1fbedda735d55a0d594844266d3a4619d03498e:1c67c7343e6af6c51ad250d12b6dc9008744e9e7f0c275b31823972732964057:before_batch_20261023"
)
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "practice-portfolio.js:11d6abe0fd14277d48c0f90e9561cba82feece73f8137b3439303f764f879ab7:0be2ae98123eb788a95c7762117a60c06115dfb7c6f6ae128cb41d07644c8b54:application/javascript:public, max-age=300, s-maxage=86400"
 "dashboard.html:b6355ecd6622473e436924697b09bf539f048edef039f85d1486c56f27f762c2:7cb712f04c3ab482dffce26dc58b64edad43a1dc47ca7a5deb4180ad55c3ea98:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
node --check "$HERE/web/practice-portfolio.js" || stop "the staged practice-portfolio.js does not parse"
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
if [ "$DRY" = "true" ]; then echo "(dry run) would set stockiq-price-proxy to 256 MB"
else "${AWS[@]}" lambda update-function-configuration --function-name stockiq-price-proxy --memory-size 256 --query MemorySize --output text
     "${AWS[@]}" lambda wait function-updated --function-name stockiq-price-proxy
     B="$(curl -s 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/?symbols=AAPL,BHP.AX,AUDUSD%3DX')"
     echo "$B" | python3 -c 'import json,sys; r=json.load(sys.stdin)["results"]; assert all(r[k]["chart"]["result"][0]["meta"]["regularMarketPrice"]>0 for k in ("AAPL","BHP.AX","AUDUSD=X")); print("the many-symbols form answers: AAPL, BHP.AX, AUDUSD=X priced")' || stop "the live price function did not answer the many-symbols form"
     curl -s 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/?symbol=SPY&range=3mo' | python3 -c 'import json,sys; m=json.load(sys.stdin)["chart"]["result"][0]["meta"]; assert m["regularMarketPrice"]>0; print("the single form answers as before: SPY", m["regularMarketPrice"])' || stop "the single form no longer answers"
fi

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
    for p in "/practice-portfolio.js" "/dashboard.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
