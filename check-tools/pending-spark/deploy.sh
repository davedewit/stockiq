#!/bin/bash
# One-off deploy (18 Oct 2026): the side panel's small charts for every item and at once.
#   - ticker-data-fetcher: a symbol whose one-day chart has no points yet (futures at a weekend: gold, oil, the 2- and 10-year
#     note futures) gets the last trading day's prices from the five-day chart.
#   - live-market.js (version 2): every tab's lines fetched once in the background (and every 5 minutes), so a tab chosen later
#     shows its line at once; the lines kept in the browser 20 minutes, so a reload shows them before any request.
#   Preview: DRY_RUN=true bash deploy.sh    Deploy: bash deploy.sh
# Roll back: ~/VSCODE/backup/ticker-data-fetcher_before_spark_20261018.zip; live-market.js from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# function : staged folder : CodeSha256 it has : its file's fingerprint : the staged file's : the rollback zip's name
FUNCS=(
 "ticker-data-fetcher:lambda:LA8h4BkcDRvy6Ex5bTgKhNe+ofsumN6GZ9nPvzvSCtA=:4bc7bf46ffa1d73ef8e73196faecf47bfafd0870664000b1ebea28029bff87c6:c58af934359dfad3b7a50c9e5f6cc5c476e483d626e5cfb9dad9505a06d60a14:before_spark_20261018"
)
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "live-market.js:218485da97a30cceeca8131ddb351c384f0c3a4d3ad84d6325931bb577a9bf37:07f470e87538123690f0e219584436f7884061be4808854d5cdb9af4e04c8d39:application/javascript:public, max-age=300, s-maxage=86400"
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
for js in live-market.js; do node --check "$HERE/web/$js" || stop "the staged $js does not parse"; done
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
    for p in "/live-market.js"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
