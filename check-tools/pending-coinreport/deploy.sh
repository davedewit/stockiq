#!/bin/bash
# One-off deploy (12 Oct 2026): the "single coin" button uses the single-stock report function.
# The button had a function of its own (stockiq-option-7-2-worker-1: a third copy of the old crypto worker, with its own
# scoring and its own RSI: 45 for Bitcoin where the report says 53). The report function already worked on a coin.
#  - stockiq-option-1-1-custom-analysis: a request with "asset": "crypto" names coins by their symbols; each is priced
#    by the crypto screener's ticker for it; a coin's report leaves out what belongs to a company or to the stock
#    market, says "since 00:00 UTC" for the day's change, and a background run is saved as "<SYMBOL> Coin Analysis".
#    A share's report does not change by a character (the tests compare every sample share with the live code).
#  - analysis-functions.js: the single-coin button asks that function; dashboard.html: so does "Run in Background" for
#    a single coin. stockiq-option-7-2-worker-1 is then called by nothing (it is left in place).
# Order: the function, then the staged page tried against it, then the two site files.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Safe to run twice. Roll back: the two site files from git (website e068768f), then
#   ~/VSCODE/backup/stockiq-option-1-1-custom-analysis_before_coin_20261012.zip
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq
WEB=/Users/dave/VSCODE/website
AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync
BACKUP=/Users/dave/VSCODE/backup
BUCKET=s3://stockiq-final-websitebucket-vqekic7enf9h
DRY="${DRY_RUN:-false}"
TMP="$(mktemp -d)"
REPORT=stockiq-option-1-1-custom-analysis; FILE=lambda_function2.py
REPORT_WAS="E906kJUM9eqAkd/JMlFFrIXjOsRXKKk6KDe8ib/h5t0="
OLD_FILE=f07f3e93904f293b3813c30526781976cc9fbf1c2f95bfbc04742bce7127cf7a      # sha256 of the files
NEW_FILE=9104a16b2a91e3bb74b84f180009d98c6023aec4352cf99db5f827ab40591879
WEB_COMMIT=e068768f                                                             # the page file the coin tickers are read from
JS_WAS=72975c8c108cc79ec9d6324c63ca4608bc3e722e8402b04e53416566a7103818; JS_NEW=96dbcb721ec1a3450513843bdc074434c2308b18f845b0092d90f3ab61c7c44f
DASH_WAS=bec16da1ef4cb2796e9505ba802994f44898f9a079139ac966a337a91d78a45d; DASH_NEW=df1c3b9835e483f6f6bb00dbc4940bd5e0840a68d49fe33354faf509c6481942

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
sha()  { "${AWS[@]}" lambda get-function-configuration --function-name "$1" --query CodeSha256 --output text; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }

if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "the report function: what is live, and the new code built from it and tested"
mkdir -p "$TMP/live" "$TMP/new" "$TMP/before"
curl -s -o "$TMP/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$REPORT" --query Code.Location --output text)"
unzip -q -o "$TMP/live.zip" -d "$TMP/live"
[ "$(unzip -Z1 "$TMP/live.zip" | tr '\n' ' ')" = "$FILE " ] || stop "the package holds other files than $FILE"
if [ "$(filesha "$TMP/live/$FILE")" = "$NEW_FILE" ]; then STATE=new; echo "the report function already has the new code"
else
    STATE=old
    [ "$(sha "$REPORT")" = "$REPORT_WAS" ] && [ "$(filesha "$TMP/live/$FILE")" = "$OLD_FILE" ] || stop "$REPORT has changed on AWS since this was built"
    cmp -s "$TMP/live/$FILE" "$MIRROR/$REPORT/$FILE" || stop "the live function is not the same as the local mirror"
    git -C "$WEB" show "$WEB_COMMIT:analysis-functions.js" > "$TMP/page.js"
    python3 "$HERE/patch_report5.py" "$TMP/live/$FILE" "$TMP/new/$FILE" "$MIRROR/stockiq-option-7-1-orchestrator/orchestrator.py" "$TMP/page.js"
    [ "$(filesha "$TMP/new/$FILE")" = "$NEW_FILE" ] || stop "the code built here is not the code that was tested"
    python3 "$ROOT/check-tools/report/patch_metrics.py" "$TMP/new/$FILE" "$ROOT/stock_metrics.py" "$TMP/new/stock_metrics.py" >/dev/null
    cmp -s "$TMP/new/stock_metrics.py" "$ROOT/stock_metrics.py" || stop "the scoring functions changed, which this step should not do"
    unzip -q -o "$BACKUP/stockiq-option-1-1-custom-analysis_before_report_20261011.zip" -d "$TMP/before"
    LIVE="$TMP/live/$FILE" python3 -W ignore "$ROOT/check-tools/report/report_test.py" "$TMP/before/$FILE" "$TMP/new/$FILE" | tail -1 | tee "$TMP/t1"; grep -q " 0 failed" "$TMP/t1" || stop "the report's tests do not pass"
    python3 -W ignore "$ROOT/check-tools/report/chart_test.py" "$MIRROR/stockiq-chart-generator/lambda_function_simple.py" "$TMP/new/$FILE" | tail -1 | tee "$TMP/t2"; grep -q " 0 failed" "$TMP/t2" || stop "the chart's tests do not pass"
fi

say "the site files: what is in website/ now"
JS_HAVE="$(filesha "$WEB/analysis-functions.js")"; DASH_HAVE="$(filesha "$WEB/dashboard.html")"
[ "$JS_HAVE" = "$JS_WAS" ] || [ "$JS_HAVE" = "$JS_NEW" ] || stop "website/analysis-functions.js has changed since this was built"
[ "$DASH_HAVE" = "$DASH_WAS" ] || [ "$DASH_HAVE" = "$DASH_NEW" ] || stop "website/dashboard.html has changed since this was built"
[ "$(filesha "$HERE/web/analysis-functions.js")" = "$JS_NEW" ] && [ "$(filesha "$HERE/web/dashboard.html")" = "$DASH_NEW" ] || stop "the staged site files are not the ones that were tested"
echo "analysis-functions.js: $([ "$JS_HAVE" = "$JS_NEW" ] && echo 'already the new one' || echo 'to be replaced'); dashboard.html: $([ "$DASH_HAVE" = "$DASH_NEW" ] && echo 'already the new one' || echo 'to be replaced')"

say "$REPORT"
if [ "$STATE" = new ]; then echo "already deployed, skipping"
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${REPORT}_before_coin_20261012.zip and update $REPORT ($(wc -l < "$TMP/live/$FILE" | tr -d ' ') lines -> $(wc -l < "$TMP/new/$FILE" | tr -d ' '))"
else
    cp "$TMP/new/$FILE" "$TMP/$FILE"; (cd "$TMP" && zip -q -X new.zip "$FILE")
    [ -f "$BACKUP/${REPORT}_before_coin_20261012.zip" ] || cp "$TMP/live.zip" "$BACKUP/${REPORT}_before_coin_20261012.zip"
    "${AWS[@]}" lambda update-function-code --function-name "$REPORT" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$REPORT"
    [ "$(sha "$REPORT")" = "$(zipsha "$TMP/new.zip")" ] || stop "$REPORT does not report the new package"
    cp "$TMP/new/$FILE" "$MIRROR/$REPORT/$FILE"; echo "live, and the mirror updated"
fi

if [ "$DRY" = "true" ]; then
    say "the site files"; echo "(dry run) would try the staged page against the live function, copy the two files into website/, upload them and clear them from CloudFront"
    say "FINISHED (dry run, nothing changed)"; exit 0
fi

say "the staged page's single-coin button against the live function (three coins and one that does not exist)"
cd "$ROOT/check-tools"
for coin in BTC SUI CKB NOSUCHCOINX; do
    FUNCS="$HERE/web/analysis-functions.js" node page_run.js 72 single "{\"coin-symbol-input\":\"$coin\"}" 2>&1 | tail -1 > "$TMP/run.json"
    python3 - "$TMP/run.json" "$coin" <<'PY' || stop "the staged page did not give a proper report for $coin"
import sys, json, re
d = json.load(open(sys.argv[1])); coin = sys.argv[2]
out = json.load(open('page_72-single.json')); t = re.sub(r'data:image/svg\+xml;base64,[A-Za-z0-9+/=]+', '<CHART>', out.get('text') or '')
line = lambda key: next((l.strip() for l in t.split('\n') if key in l), '-')
# (the tool's text has the picture's tag taken out: a report of tens of thousands of characters is one that carries its chart)
print(coin + ':', 'error', d['error'], '| flags', d['flags'], '|', line('Symbol:'), '|', line('STOCKIQ SCORE'), '|', line('Priced as')[:60], '|', line('No price data')[:50], '|', d['chars'], 'characters')
ok = d['error'] is None and (('STOCKIQ SCORE' in t and d['chars'] > 15000 and 'SINGLE COIN ANALYSIS: ' + coin in t) if coin != 'NOSUCHCOINX' else 'No price data was found' in t)
sys.exit(0 if ok else 1)
PY
done

say "the two site files"
for pair in "analysis-functions.js:$JS_NEW:application/javascript:public, max-age=300, s-maxage=86400" "dashboard.html:$DASH_NEW:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"; do
    f="${pair%%:*}"; rest="${pair#*:}"; want="${rest%%:*}"; rest="${rest#*:}"; ctype="${rest%%:*}"; cache="${rest#*:}"
    [ "$(filesha "$WEB/$f")" = "$want" ] || cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    echo "$f uploaded"
done
INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id EHXV50CPHY07R --paths "/analysis-functions.js" "/dashboard.html" --query Invalidation.Id --output text)"
"${AWS[@]}" cloudfront wait invalidation-completed --distribution-id EHXV50CPHY07R --id "$INV"
for f in analysis-functions.js dashboard.html; do
    [ "$(curl -s "https://stockiq.tech/$f" | shasum -a 256 | cut -d' ' -f1)" = "$(filesha "$WEB/$f")" ] && echo "https://stockiq.tech/$f is the new file" || stop "https://stockiq.tech/$f is not the new file yet"
done
say "FINISHED"
