#!/bin/bash
# One-off deploy (13 Oct 2026): the last four "Coming Soon" screeners go live: Switzerland SMI, India Sensex, South Korea
# KOSPI 200, Brazil Bovespa. Their 34 workers were created before this (check-tools/pending-batch5/deploy.sh:
# stockiq-europe-4-7-worker-1..2, stockiq-asia-5-6-worker-1..3, stockiq-asia-5-7-worker-1..21,
# stockiq-americas-6-2-worker-1..8). This puts the four
#   - into the coordinator (background runs): workers, stocks, names, sizes, currencies; and a symbol with an "&"
#     (India's M&M.NS) is written &amp; in its report, which the dashboard shows as HTML;
#   - on the analysis page: an entry each in screeners.js, a button each in place of "Coming Soon", and the market
#     report writes a symbol as text (analysis-functions.js: three lines, the same "&");
#   - on the dashboard: names, "run again", "Run in Background", an index each for the Top 10 comparison; and its Top 10
#     tracker reads a symbol with an "&" and a price written as a currency code and a number ("CHF 77.30", "BRL 56.86");
#   - into the site's wording: 27 screeners, the four in the lists (five pages).
# The staged files are in ../pending-batch5/ (lambda/, web/).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-screener-coordinator_before_batch5_20261013.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../pending-batch5" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-screener-coordinator; BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-screener-coordinator; KEEP="$BACKUP/${F}_before_batch5_20261013.zip"
WAS="UXE1lzC4BhuDBHm+4Fbo0jq9h8PX33ywmHCv8hpRnyE="
OLD_FILE=749d5ccd572161f4d56992a1829047ed27db4f1baf72774b5691fcecbc616f02
NEW_FILE=ff6b492df0a1b77198115824fd6e5df0873a7cbe4027484cd8e4850304977283
# file : what it was : what it becomes : type : how long a copy may be kept.  The data first, the script that reads it, then the pages.
FILES=(
 "screeners.js:c7baf843bc3b8f67d6a7eef03c6f242725d7b702d4749704df0854de9ca63ae3:4512115ab38930ee43f7ad1c5c76a7e053147dc906a68a63000ebd44596fa844:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis-functions.js:9ed44ac08e95d3d2d536f369fa3cce34fbeff3033a13a9a92d880d36c472fe6c:0207a09e771b869dbf3ad038bc587ec5a4aa9cdd5ab7d3043d040e38c00f3f5b:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis.html:19b6b70ca45e471984f6ef2a4138843883c2ee61526b8f7116e7e2b950600700:195cd61666ca9704146dd440d47887c760c6b864653fa340e6517123be872c91:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:68a16ffb0d2d3a921e844a121035a1eb51d409f3c886e781e1169a2455e63f98:72cb5b0dd16c67f14bed091c41eb3544b7598f1a533b42d61ca3acc420f33e6b:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "index.html:6a649fc2e74c294bee94d3e656ce1bcb08ced18d4c7909517a1068bbdbdd2d23:d494290d2ba9dc78222e85f6fefe90c3910b0a0a27806a35f8f574b8ebf6cadf:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "about.html:c7034b39a46b30eda7c7125508498a8cf273cb90fe4669d05c5831b08e007da1:315dd9f41d0c940db35129fb3fb74955de242d3dc5f1db722b6059001c1c9bae:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "faq.html:e68c5dbbefe7e946fbb20c19faaed24867ef85ab012690d5009a05607c40afec:dcd9aa17dfce78372b04d2b1861b4ce52e3a30f48ddf0e661c22b97e3b4372ec:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "investment-research-tools.html:227e21df39d6c3a1ae836e0cd3073c217416c7f82ba9c6b87f4e2a66d72c80cd:94f2e55549f8d27c904d44dfe1f591f1759ab7cc2dfe30e8eae132f3c072c48b:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "stock-screener-guide.html:1ed5e1bd544b5faa460d0abe8897f90f47c0ed1e35dff8ef7f714de5693f9c85:7219619ebeffa47bb487a077b8693b37a1f6576706e8de1680cf33aa931e02dd:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
for u in $(cat "$HERE"/smi/urls.txt "$HERE"/sensex/urls.txt "$HERE"/kospi200/urls.txt "$HERE"/bovespa/urls.txt); do grep -q "$u" "$HERE/lambda/lambda_function.py" && grep -q "$u" "$HERE/web/screeners.js" || stop "a worker address is missing from the coordinator or from screeners.js: $u"; done
python3 - "$HERE" <<'PY' || stop "a screener's list in the coordinator and on the page are not the same list"
import re, sys
c = open(sys.argv[1] + '/lambda/lambda_function.py', encoding='utf-8').read(); p = open(sys.argv[1] + '/web/screeners.js', encoding='utf-8').read()
for key, n in (('5-smi', 20), ('5-sensex', 30), ('5-kospi200', 200), ('5-bovespa', 76), ('5-hangseng', 95), ('5-sti', 30), ('5-ftsemib', 40), ('5-ibex35', 35), ('5-cac40', 40), ('5-aex', 30), ('5-tsx60', 60), ('5-dax40', 40)):
    cl = re.findall(r"'([A-Z0-9&-]+\.[A-Z]{2})'", c[c.index("    '%s': ['" % key):].split('\n')[0]); e = p[p.index("'%s': {" % key):]; pl = re.findall(r"'([A-Z0-9&-]+\.[A-Z]{2})'", e[e.index('list: ['):e.index('workers: [')])
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
node --check "$HERE/web/analysis-functions.js" || stop "the staged page script does not parse"
! grep -q "Coming Soon</button>" "$HERE/web/analysis.html" || stop "the staged analysis page still has a Coming Soon button"
for k in smi sensex kospi200 bovespa hangseng sti ftsemib ibex35 cac40 aex tsx60 dax40; do grep -q "runAnalysis(5, '$k', event)" "$HERE/web/analysis.html" || stop "the staged analysis page lacks the button for $k"; done
for k in switzerland_screener india_screener korea_screener brazil_screener hongkong_screener singapore_screener italy_screener spain_screener france_screener netherlands_screener canada_screener germany_screener; do grep -q "$k" "$HERE/web/dashboard.html" || stop "the staged dashboard lacks $k"; done

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
