#!/bin/bash
# One-off deploy (17 Oct 2026): the Mexico IPC screener (its 4 workers were made by deploy.sh in this folder; the 35 members from the
# NAFTRAC fund's holdings of 15 Oct 2026): the coordinator, the autopilot (13:35-19:55 UTC), the chat's list; the page entry, the button,
# the dashboard's lines (^MXX), the panel's "Main index of every country", the site's count (33) and lists of markets.
#   Preview (changes nothing):   DRY_RUN=true bash deploy-site.sh
#   Deploy:                      bash deploy-site.sh
# Roll back: the three ~/VSCODE/backup/<function>_before_mexico_20261017.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# function : staged folder : CodeSha256 it has : its file's fingerprint : the staged file's : the rollback zip's name
FUNCS=(
 "stockiq-screener-coordinator:coord:9VfBPSmU+lMrvofqJIS4GT9jafVM6ab2bhpopSFO53E=:b1a65c135d4e442ab971158fad393bdced9fa9bff6e8080cd9d707e773f2352b:618d2357e3eb554b1888f223a770742d86ef4a5a1afc0172fd99fb9e7f6666d6:before_mexico_20261017"
 "stockiq-ai-trader:lambda:CqxupGXMa9rtv6ovxUNwLpx7mJav7ulHKGiD9XQJIYo=:6e79e94e8152977ce9883d8afcb2a9c5a8a9f75617dfc1f016f0b697aaa0bcb1:b5d5c7d9963a0cef3f2d0b375b1c4422f1c925bdf5100b51103d0ddbef2b2aee:before_mexico_20261017"
 "stockiq-ai-chat:chat:ortNRYBkU84TUKnBBPQN4h+0VpmC1WvDWtOzfYD04WA=:ae35a5e303b8c8d71fd4af2787e3f11544d52575b5c2eb126caa8da430f4bce4:84176fb6df2653fc2c760a830d880c34a1eecf8569c75a5f18a1ff281b0ad9a6:before_mexico_20261017"
)
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "screeners.js:30e1ebe71f36723dc0b9a4144d28a19ca0a39c97b7d8207c6dc3e224337efb77:eb55e436ab6fdf7c0e2d868b2c50af57db0e2b808bfb73620d274d23ade6dbe7:application/javascript:public, max-age=300, s-maxage=86400"
 "practice-autopilot.js:d162d82d142fb04a4ce5e929ca5e734ea8fe969b9383cf6778725b12271eacfd:f202e4deac3a60c49d6b7273d5efe011636cbc7e11f2cc3ae72533387af46784:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis.html:b126149b2f17b3d3f018bafa74f7f488be8fdfe67c0f0e7a622bb844ccb9d706:54fad8753604817c315c3e1e0f759d1c0c20c65d52a747ff3fd70a6dafa3c551:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:20b6161a4a8ac09c7a8cee6a3665d7995c1263f07a6fe05a49d3a88f2272a056:fd65b455455d6a52f2413344a33b628df214a82db595664b488326af813d2fc7:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "index.html:90e5bdb3f40d8591efbf6edf92e05dda99d3fe979d1606451068b5e061e044a4:ff468934f0d1e314e60c7951ff252149747ae03f3f7afd5393a4d27a85ceb846:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "about.html:57b15b5bca0a3a155e1da3fd012db726b876874a7f7578324495b0aeb3491834:f4f72bf444efb119a1bac2bd7ae6d0e6c48ab5c12f9768194958e13864748f9b:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "faq.html:1871bd0a9a35ecff1b04a93b6c0978f405d3e018e238317cd7c88599b04181d9:30665d8f94b1090e81be59056506ad9e3bba2844f806ae5a177fd5805a07a3d4:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "investment-research-tools.html:7dfd44a86580cb211248c5f53dfd9bbc0322ae5487b4169f86059ee7c60b7da9:52fab6954494cf1007199546b99b2bc4d3ce3bb805eea726c71082b5c265d5f3:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "stock-screener-guide.html:1dc59dae8cbd7fc94ef3ba374ff065f34be392c9a2b3929202ee1a720fce6b0f:3f25d690cbba003db81304d572c4b79d229f6352431c8813b52c0291b79f7f2a:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
for js in screeners.js practice-autopilot.js; do node --check "$HERE/web/$js" || stop "the staged $js does not parse"; done
grep -q 'practice-autopilot.js?v=50' "$HERE/web/dashboard.html" || stop "the staged dashboard does not ask for the new versions"
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
    for p in "/screeners.js" "/practice-autopilot.js?v=50" "/analysis.html" "/dashboard.html" "/index.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
