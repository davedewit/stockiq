#!/bin/bash
# One-off deploy (13 Oct 2026): two more screeners go live: Hong Kong Hang Seng, Singapore STI. Their 13 workers were
# created before this (check-tools/pending-batch4/deploy.sh: stockiq-asia-5-8-worker-1..10,
# stockiq-asia-5-9-worker-1..3). This puts the two
#   - into the coordinator (background runs): workers, stocks, names, sizes, currencies;
#   - on the analysis page: an entry each in screeners.js and a button each in place of "Coming Soon" (no change to
#     analysis-functions.js: a market screener is data only);
#   - on the dashboard: names, "run again", "Run in Background", an index each for the Top 10 comparison;
#   - into the site's wording: 23 screeners, "Asian" indexes where it said "Japanese" (five pages).
# The staged files are in ../pending-batch4/ (lambda/, web/).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-screener-coordinator_before_batch4_20261013.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../pending-batch4" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-screener-coordinator; BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-screener-coordinator; KEEP="$BACKUP/${F}_before_batch4_20261013.zip"
WAS="8QIBorceltpX/4cbSNUU0x1uIhSXH6AF5x/5913hrjQ="
OLD_FILE=2645353e0d659a2247aa36b31e6d67bda48b4d484b8e15efea16ce0b6ea8ac48
NEW_FILE=749d5ccd572161f4d56992a1829047ed27db4f1baf72774b5691fcecbc616f02
# file : what it was : what it becomes : type : how long a copy may be kept.  The data first, the script that reads it, then the pages.
FILES=(
 "screeners.js:580aa752a9ab0a026069b332be7cf2fc19a51e5f86a17fba44f276a943723e76:c7baf843bc3b8f67d6a7eef03c6f242725d7b702d4749704df0854de9ca63ae3:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis.html:49e14dabdc1914e5c0cdbe42ed01b7d1e15aa23ca1f5677061b45901eece8d11:19b6b70ca45e471984f6ef2a4138843883c2ee61526b8f7116e7e2b950600700:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:9ff7238097a99984be63d6fcba1b23bf2039f32bb4049fb2d41c8e1a13102c35:68a16ffb0d2d3a921e844a121035a1eb51d409f3c886e781e1169a2455e63f98:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "index.html:4aa7a6bfa052b0ba64ae4fc523c6007204af4fcc8e6a1f0d3a19607d1cfa1ed7:54bf634024cc2fc010fe80af25f546ce134df221efb1071e9d8dc84f5f4bfbbd:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "about.html:1bb300f110a28186bc56d94f6b021a841fceb46df6ccbaf942bb396e69fcada4:c7034b39a46b30eda7c7125508498a8cf273cb90fe4669d05c5831b08e007da1:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "faq.html:864c5427f34bdb78f6d0830fc776993b8a2456ac01b342a042a13af9a713f394:e68c5dbbefe7e946fbb20c19faaed24867ef85ab012690d5009a05607c40afec:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "investment-research-tools.html:b77bc7819e984e9a8ee3d72694f05fd7d34c814bf1fecbf806b5d73e38141ad1:227e21df39d6c3a1ae836e0cd3073c217416c7f82ba9c6b87f4e2a66d72c80cd:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "stock-screener-guide.html:70bf6156352a17bcd19a300f4a91ea5c0b30baf73c4a8dea7da8d4fc5b747a4e:1ed5e1bd544b5faa460d0abe8897f90f47c0ed1e35dff8ef7f714de5693f9c85:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
for u in $(cat "$HERE"/hangseng/urls.txt "$HERE"/sti/urls.txt); do grep -q "$u" "$HERE/lambda/lambda_function.py" && grep -q "$u" "$HERE/web/screeners.js" || stop "a worker address is missing from the coordinator or from screeners.js: $u"; done
python3 - "$HERE" <<'PY' || stop "a screener's list in the coordinator and on the page are not the same list"
import re, sys
c = open(sys.argv[1] + '/lambda/lambda_function.py', encoding='utf-8').read(); p = open(sys.argv[1] + '/web/screeners.js', encoding='utf-8').read()
for key, n in (('5-hangseng', 95), ('5-sti', 30), ('5-ftsemib', 40), ('5-ibex35', 35), ('5-cac40', 40), ('5-aex', 30), ('5-tsx60', 60), ('5-dax40', 40)):
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
for k in hangseng sti ftsemib ibex35 cac40 aex tsx60 dax40; do grep -q "runAnalysis(5, '$k', event)" "$HERE/web/analysis.html" || stop "the staged analysis page lacks the button for $k"; done
for k in hongkong_screener singapore_screener italy_screener spain_screener france_screener netherlands_screener canada_screener germany_screener; do grep -q "$k" "$HERE/web/dashboard.html" || stop "the staged dashboard lacks $k"; done

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
