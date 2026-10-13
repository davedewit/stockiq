#!/bin/bash
# One-off deploy (13 Oct 2026): the Germany DAX 40 screener goes live. Its 4 workers were created before this
# (check-tools/pending-dax40/deploy.sh, stockiq-europe-4-2-worker-1..4). This puts the screener
#   - into the coordinator (background runs from the dashboard): its workers, its 40 stocks, its name and size;
#   - on the analysis page: an entry in screeners.js, a button in place of "Coming Soon", and a report writer that any
#     later market can use (formatMarketResult; the Nikkei's report is now a call to it, proved unchanged);
#   - on the dashboard: its name, "run again", "Run in Background", and the DAX index for the Top 10 comparison.
# The staged files are in ../pending-dax40/ (lambda/, web/).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-screener-coordinator_before_dax40_20261013.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../pending-dax40" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync/stockiq-screener-coordinator; BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=stockiq-screener-coordinator; KEEP="$BACKUP/${F}_before_dax40_20261013.zip"
WAS="pUBd8qCLYGjtVSoYQObSV8YVygyP8mBSfdCxxJ+ho9Y="
OLD_FILE=4d3246812eb7d8f92f6c0688966dbe5d959cfa29b87f0796d4cdf267bfb025d0
NEW_FILE=19ee6d9b68253eb3d2ba8e1928e7e8bcb25346db662138cf08317d7c6c4fffa4
# file : what it was : what it becomes : type : how long a copy may be kept.  The data first, the script that reads it, then the pages.
FILES=(
 "screeners.js:8c6ad16832c6319daa5d94b4888e4531796ead55a0b6304d1b8ca3cb2119aab5:e3266e5d47049774ac105c3ab81c5ea6cc11be00ce4cc9f6f0dbe13f492a01f1:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis-functions.js:af0a454dafc77cb36a4080b8552e9ccfabc2fff8678fb63b27b3dfa5f8565c45:317e4e43fc49b60a1e4556261ece227d80e6113b55978087a12c8544cf5ae6e0:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis.html:51af1bc0c0f98ace8881e19b8211e4ed2f9fd8587e4e70cb87920ea0fd474400:1328370647930436f9f23814f5608950be92a9e02ba882062ee32b5eaa5b3334:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "dashboard.html:69a09a3328b5b1b16dc99a0fa0e74f32d39707a0aa03bbb1cca848fd303085ed:4fa17b8157f4a186d076b803e833952220cee6efbe131a46e3e25bae8acf92af:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
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
for u in $(cat "$HERE/urls.txt"); do grep -q "$u" "$HERE/lambda/lambda_function.py" && grep -q "$u" "$HERE/web/screeners.js" || stop "a worker address is missing from the coordinator or from screeners.js: $u"; done
python3 - "$HERE" <<'PY' || stop "the coordinator's DAX list and the page's are not the same list"
import re, sys
c = open(sys.argv[1] + '/lambda/lambda_function.py', encoding='utf-8').read(); p = open(sys.argv[1] + '/web/screeners.js', encoding='utf-8').read()
cl = re.findall(r"'([A-Z0-9]+\.DE)'", c[c.index("    '5-dax40': ['"):].split('\n')[0]); e = p[p.index("'5-dax40': {"):]; pl = re.findall(r"'([A-Z0-9]+\.DE)'", e[e.index('list: ['):e.index('workers: [')])
assert cl == pl and len(cl) == 40 == len(set(cl)), (len(cl), len(pl))
PY
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    local_sha="$(filesha "$WEB/$f")"; curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; live_sha="$(filesha "$TMP/live_$f")"
    [ "$local_sha" = "$was" ] || [ "$local_sha" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$live_sha" = "$was" ] || [ "$live_sha" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$local_sha" = "$new" ] && echo new || echo old), live $([ "$live_sha" = "$new" ] && echo new || echo old)"
done
node --check "$HERE/web/analysis-functions.js" && node --check "$HERE/web/screeners.js" || stop "a staged script does not parse"
grep -q "runAnalysis(5, 'dax40', event)" "$HERE/web/analysis.html" && grep -q "germany_screener" "$HERE/web/dashboard.html" || stop "the staged pages lack the DAX button or the dashboard's entries"

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
