#!/bin/bash
# One-off deploy (13 Oct 2026): three more screeners go live: France CAC 40, Netherlands AEX, Canada TSX 60. Their 13
# workers were created before this (check-tools/pending-batch2/deploy.sh: stockiq-europe-4-3-worker-1..4,
# stockiq-europe-4-4-worker-1..3, stockiq-americas-6-1-worker-1..6). This puts the three
#   - into the coordinator (background runs): workers, stocks, names, sizes, currencies;
#   - on the analysis page: an entry each in screeners.js and a button each in place of "Coming Soon" (no change to
#     analysis-functions.js: a market screener is data only since the DAX 40);
#   - on the dashboard: names, "run again", "Run in Background", an index each for the Top 10 comparison;
#   - into the site's wording: 19 screeners, the three in the lists (five pages).
# The staged files are in ../pending-batch2/ (lambda/, web/).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-screener-coordinator_before_batch2_20261013.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../pending-batch2" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-screener-coordinator; BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-screener-coordinator; KEEP="$BACKUP/${F}_before_batch2_20261013.zip"
WAS="ofFfnb/mZHi1cJpM0lRQdu6FKWTKPfk4AG0oqK6wZZE="
OLD_FILE=19ee6d9b68253eb3d2ba8e1928e7e8bcb25346db662138cf08317d7c6c4fffa4
NEW_FILE=cf33b37dff47769658f49fed43b24f3e47ee2c712ad77c0fe342dd569dfe59a3
# file : what it was : what it becomes : type : how long a copy may be kept.  The data first, the script that reads it, then the pages.
FILES=(
 "screeners.js:e3266e5d47049774ac105c3ab81c5ea6cc11be00ce4cc9f6f0dbe13f492a01f1:7f131afab142a2c9c64082c4f41e04f811186180a0f4a9efcefe2c4b75e833dc:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis.html:1328370647930436f9f23814f5608950be92a9e02ba882062ee32b5eaa5b3334:d35dd08a8f285e5e10dce3510835de123467bdb07cb5feacebaae2891951946e:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:4fa17b8157f4a186d076b803e833952220cee6efbe131a46e3e25bae8acf92af:6ef370d9ca0382b54372a3ea81b74ba223024f0db3429ee7a9aa3ee24180670d:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "index.html:a05879103ed2048a20725a881b8603491c58a5a586d2bf80930e272ee45e6fd2:b67e8d1c2f92705fb2ca3d4a56e1caa941fd53db794a790594d5ba92d188f6f2:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "about.html:cbda2620374326e4a6577d59736a09a6369751343d2cee92724caa1530995c4b:405d1c59ade07ba0816f8b9b2ab11e069998daca8580d4aa1c70ea950e1c6e9f:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "faq.html:cde2ea4c7bf0b2065450280f0b8ea40a47a71db44821422217a94f5e357fedc3:1733d31fc1bceb80bdcfd8e71df149a8d5acc2c87894931ba95e3d95e2fa89b0:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "stock-screener-guide.html:9726f850e32554b9c9600197b81f5c5c37e7611cc39be514ca78bff8c6c8b35b:70bf6156352a17bcd19a300f4a91ea5c0b30baf73c4a8dea7da8d4fc5b747a4e:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "investment-research-tools.html:9662421404e883838fd861663f09a750ea3baf359fed1ba3cede59470cf7f6b5:b77bc7819e984e9a8ee3d72694f05fd7d34c814bf1fecbf806b5d73e38141ad1:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
)
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
[ "$(filesha "$HERE/lambda/lambda_function.py")" = "$NEW_FILE" ] || stop "the staged coordinator is not the one that was tested"
curl -s -o "$TMP/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$F" --query Code.Location --output text)"
mkdir -p "$TMP/live"; unzip -q -o "$TMP/live.zip" -d "$TMP/live"
[ "$(unzip -Z1 "$TMP/live.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "the package holds other files than lambda_function.py"
if [ "$(filesha "$TMP/live/lambda_function.py")" = "$NEW_FILE" ]; then STATE=new; echo "the coordinator already has the new code"
else
    STATE=old
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$WAS" ] && [ "$(filesha "$TMP/live/lambda_function.py")" = "$OLD_FILE" ] || stop "$F has changed on AWS since this was built"
    cmp -s "$TMP/live/lambda_function.py" "$MIRROR/lambda_function.py" || stop "the live coordinator is not the same as the local mirror"
    echo "the live coordinator is the code this was built from"
fi
python3 -m py_compile "$HERE/lambda/lambda_function.py" || stop "the staged coordinator does not compile"
for u in $(cat "$HERE"/cac40/urls.txt "$HERE"/aex/urls.txt "$HERE"/tsx60/urls.txt); do grep -q "$u" "$HERE/lambda/lambda_function.py" && grep -q "$u" "$HERE/web/screeners.js" || stop "a worker address is missing from the coordinator or from screeners.js: $u"; done
python3 - "$HERE" <<'PY' || stop "a screener's list in the coordinator and on the page are not the same list"
import re, sys
c = open(sys.argv[1] + '/lambda/lambda_function.py', encoding='utf-8').read(); p = open(sys.argv[1] + '/web/screeners.js', encoding='utf-8').read()
for key, n in (('5-cac40', 40), ('5-aex', 30), ('5-tsx60', 60), ('5-dax40', 40)):
    cl = re.findall(r"'([A-Z0-9-]+\.[A-Z]{2})'", c[c.index("    '%s': ['" % key):].split('\n')[0]); e = p[p.index("'%s': {" % key):]; pl = re.findall(r"'([A-Z0-9-]+\.[A-Z]{2})'", e[e.index('list: ['):e.index('workers: [')])
    assert cl == pl and len(cl) == n == len(set(cl)), (key, len(cl), len(pl))
PY
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    local_sha="$(filesha "$WEB/$f")"; curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; live_sha="$(filesha "$TMP/live_$f")"
    [ "$local_sha" = "$was" ] || [ "$local_sha" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$live_sha" = "$was" ] || [ "$live_sha" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$local_sha" = "$new" ] && echo new || echo old), live $([ "$live_sha" = "$new" ] && echo new || echo old)"
done
node --check "$HERE/web/screeners.js" || stop "the staged data file does not parse"
cmp -s "$HERE/web/analysis-functions.js" "$WEB/analysis-functions.js" || stop "the page script the staged data was tested with is not the one on the site"
for k in cac40 aex tsx60 dax40; do grep -q "runAnalysis(5, '$k', event)" "$HERE/web/analysis.html" || stop "the staged analysis page lacks the button for $k"; done
for k in france_screener netherlands_screener canada_screener germany_screener; do grep -q "$k" "$HERE/web/dashboard.html" || stop "the staged dashboard lacks $k"; done

say "$F (the coordinator first: a background run asked from the new dashboard must find the screener)"
if [ "$STATE" = new ]; then echo "already deployed, skipping"
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $KEEP and update the function"
else
    [ -f "$KEEP" ] || cp "$TMP/live.zip" "$KEEP"
    cp "$HERE/lambda/lambda_function.py" "$TMP/lambda_function.py"; (cd "$TMP" && zip -q -X new.zip lambda_function.py)
    "${AWS[@]}" lambda update-function-code --function-name "$F" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$F"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new.zip")" ] || stop "the function does not report the new package"
    cp "$HERE/lambda/lambda_function.py" "$MIRROR/lambda_function.py"; echo "live ($(zipsha "$TMP/new.zip")), and the mirror updated"
fi

say "the website"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it ($ctype; $cache)"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    PATHS+=("/$f*"); echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for p in "${PATHS[@]}"; do p="${p%\*}"; curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB$p" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
