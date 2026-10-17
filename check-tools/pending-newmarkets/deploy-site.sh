#!/bin/bash
# One-off deploy (17 Oct 2026): five more screeners, Euro Stoxx 50, Sweden OMX Stockholm 30, China CSI 300, Taiwan 50, New Zealand
# NZX 50 (their 48 workers were made by deploy.sh in this folder): the coordinator (lists, workers, names), the autopilot (the five
# screeners, hours for China, Taiwan and New Zealand), the AI chat's list; the page entries (screeners.js), the buttons
# (analysis.html), the dashboard's lines and a tracker that reads a symbol with two suffixes (SWED-A.ST), the panel's "Main index
# of every country", and the site's count (32) and lists of markets.
#   Preview (changes nothing):   DRY_RUN=true bash deploy-site.sh
#   Deploy:                      bash deploy-site.sh
# Roll back: the three ~/VSCODE/backup/<function>_before_newmarkets_20261017.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# function : staged folder : CodeSha256 it has : its file's fingerprint : the staged file's : the rollback zip's name
FUNCS=(
 "stockiq-screener-coordinator:coord:979X4yAm37f76T4RQfYT8ClqaR9P8NO0r+5LeqgDK7A=:ff6b492df0a1b77198115824fd6e5df0873a7cbe4027484cd8e4850304977283:b1a65c135d4e442ab971158fad393bdced9fa9bff6e8080cd9d707e773f2352b:before_newmarkets_20261017"
 "stockiq-ai-trader:lambda:jHXVkGaNAlj92uPa7W82PHVvodzxpnwkjimvEWJGbRs=:7ab71fd1e0527bd65f3b92489133ff77a95cd73f447189cfefa52f1c9ab297fc:6e79e94e8152977ce9883d8afcb2a9c5a8a9f75617dfc1f016f0b697aaa0bcb1:before_newmarkets_20261017"
 "stockiq-ai-chat:chat:p33YPRp7EbWNGY2KQ6ITt+UEOwUuTsBO+vshLVh1JlU=:746903c6471f5aae9cface44d2032fde885305ebb7c9ae28efe348566801b1c2:ae35a5e303b8c8d71fd4af2787e3f11544d52575b5c2eb126caa8da430f4bce4:before_newmarkets_20261017"
)
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "screeners.js:4512115ab38930ee43f7ad1c5c76a7e053147dc906a68a63000ebd44596fa844:30e1ebe71f36723dc0b9a4144d28a19ca0a39c97b7d8207c6dc3e224337efb77:application/javascript:public, max-age=300, s-maxage=86400"
 "practice-autopilot.js:f226a8756e6a1db62173ea42fe1d2011dd738e4d4cbc669f014bfb6e07aa5461:d162d82d142fb04a4ce5e929ca5e734ea8fe969b9383cf6778725b12271eacfd:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis.html:f214d39b01edff570a8eb48f7d9569e1673ff9500d3c4abc3480d7bca53abf11:b126149b2f17b3d3f018bafa74f7f488be8fdfe67c0f0e7a622bb844ccb9d706:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:6520922378e9aeeea6dd2d052e45bfffc6d7481f6cafe666c549d411d9d772e5:20b6161a4a8ac09c7a8cee6a3665d7995c1263f07a6fe05a49d3a88f2272a056:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "index.html:3f44e32b0403ba850a96023c1380ac2c3af39aa24e3b84354c796543cdd48bb2:90e5bdb3f40d8591efbf6edf92e05dda99d3fe979d1606451068b5e061e044a4:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "about.html:ee08eb2ac3fdbaec1e4fe7d6dcf0744a3316af64783d679d19731bbdd0151744:57b15b5bca0a3a155e1da3fd012db726b876874a7f7578324495b0aeb3491834:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "faq.html:eff02b2c2a534432f59e630c8a9e8abf9fb3c5d14932c9718c034b3d040d32f5:1871bd0a9a35ecff1b04a93b6c0978f405d3e018e238317cd7c88599b04181d9:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "investment-research-tools.html:19ac939ea2ec2862817474d88f687aa686ed64ed3709a3d95a14821522ea145d:7dfd44a86580cb211248c5f53dfd9bbc0322ae5487b4169f86059ee7c60b7da9:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "stock-screener-guide.html:1a8016d3e9d4ac59de981fbbdcdfecba27dbc29d19389732de71d9829b4fab03:1dc59dae8cbd7fc94ef3ba374ff065f34be392c9a2b3929202ee1a720fce6b0f:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
grep -q 'practice-autopilot.js?v=49' "$HERE/web/dashboard.html" || stop "the staged dashboard does not ask for the new versions"
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
    for p in "/screeners.js" "/practice-autopilot.js?v=49" "/analysis.html" "/dashboard.html" "/index.html" "/faq.html"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
