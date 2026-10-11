#!/bin/bash
# One-off deploy (11 Oct 2026): the single-stock report and its chart, after the owner asked whether they could be improved.
#  - stockiq-chart-generator: drawn afresh. It draws the very prices the report scored (sent to it by the report), so the two
#    cannot differ; averages and RSI start when they have their days (they were flat lines, then a jump); the 200-day average
#    is on it; prices in the share's own currency; no background of its own, so it sits on a dark page; lettering that grows
#    when it is shown small (a phone); a quarter of the size.
#  - stockiq-option-1-1-custom-analysis: prices in the share's own currency (every share was in dollars, pence included);
#    one bar a day (ASX shares said "+0.00% today" after the close) and the latest session from the quote when its bar
#    arrives empty (London); RSI the standard way (the text said 47 under a chart that said 56); a trend factor that grows
#    with the distance (0.03% under an average read "Strong Downtrend: -12"); one explanation of the score instead of two
#    that disagreed; company figures from a second source when the first has none (it has none outside the US), and plain
#    words when there are none; "YTD" called the one-year change it is; part-day volume left out while a session is open.
#  - stock_metrics.py (the stock pages' copy of the scoring): the same functions copied across; the pages follow at the
#    next daily run.
# The functions' code is not in git (the report's holds a key), so this builds the new code from the live code with the
# patch scripts beside it, checks the result against the fingerprints below and runs the tests before changing anything.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice: a function that already has the new code is skipped; stops if live code is not what this was built against.
# Roll back: ~/VSCODE/backup/stockiq-chart-generator_before_report_20261011.zip and
#   ~/VSCODE/backup/stockiq-option-1-1-custom-analysis_before_report_20261011.zip (aws lambda update-function-code --zip-file),
#   and git checkout of stock_metrics.py.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq
AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync
BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"
TMP="$(mktemp -d)"
REPORT=stockiq-option-1-1-custom-analysis; REPORT_FILE=lambda_function2.py
CHART=stockiq-chart-generator;             CHART_FILE=lambda_function_simple.py
REPORT_WAS="d8P1lJehxVSgUiz4O380a5i3As6taX3f7n52fxfcpFQ="
CHART_WAS="6WRzMPlcb7gVW6ypuYnePUtUr3Dii7HBdXmc0EGDE9o="
REPORT_NEW=5a8ed58b8330a50631f6c73a1bf4833c868ad44efabb8a4988765021ed5c1287      # sha256 of the built files
CHART_NEW=612e9767e869fc0ac4eecea74931939bb188edbafadbec1fb45920f1d252e8e6
METRICS_WAS=25cc5fbc766086923b3f88d98b10fff5e9b9d38559e819c83b62b9bb0684ddf2
METRICS_NEW=f7cae9d0ebaf7c8f2df426ff9d7670b351862b98c19b1914945abecf5ec78c0a
REPORT_URL=https://5oqosafg2mflk7oyydkk3d3rdq0amufq.lambda-url.us-east-1.on.aws/
CHART_URL=https://6beqon56uidrwxtl52oycyn6kq0lyezp.lambda-url.us-east-1.on.aws/

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
sha()  { "${AWS[@]}" lambda get-function-configuration --function-name "$1" --query CodeSha256 --output text; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }

if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "what is live"
for pair in "$REPORT:$REPORT_FILE" "$CHART:$CHART_FILE"; do
    f="${pair%%:*}"; file="${pair##*:}"; mkdir -p "$TMP/$f/live"
    curl -s -o "$TMP/$f/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$f" --query Code.Location --output text)"
    unzip -q -o "$TMP/$f/live.zip" -d "$TMP/$f/live"
    [ "$(unzip -Z1 "$TMP/$f/live.zip" | tr '\n' ' ')" = "$file " ] || stop "$f's package holds other files than $file"
    echo "$f: $(sha "$f")"
done

say "build the new code from the code that is live, and test it"
state_of() {   # function, file, fingerprint it was built against, fingerprint of the new file -> "new" (already deployed) or "old"
    if [ "$(filesha "$TMP/$1/live/$2")" = "$4" ]; then echo new; return; fi
    [ "$(sha "$1")" = "$3" ] || stop "$1 has changed on AWS since this was built"
    cmp -s "$TMP/$1/live/$2" "$MIRROR/$1/$2" || stop "the live $1 is not the same as the local mirror"
    echo old
}
REPORT_STATE="$(state_of "$REPORT" "$REPORT_FILE" "$REPORT_WAS" "$REPORT_NEW")"; [ "$REPORT_STATE" = new ] || [ "$REPORT_STATE" = old ] || { echo "$REPORT_STATE"; exit 1; }
CHART_STATE="$(state_of "$CHART" "$CHART_FILE" "$CHART_WAS" "$CHART_NEW")";     [ "$CHART_STATE" = new ] || [ "$CHART_STATE" = old ] || { echo "$CHART_STATE"; exit 1; }
mkdir -p "$TMP/new"
if [ "$REPORT_STATE" = old ]; then python3 "$HERE/patch_report.py" "$TMP/$REPORT/live/$REPORT_FILE" "$TMP/new/$REPORT_FILE"; else cp "$TMP/$REPORT/live/$REPORT_FILE" "$TMP/new/$REPORT_FILE"; echo "the report function already has the new code"; fi
if [ "$CHART_STATE" = old ]; then python3 "$HERE/patch_chart.py" "$TMP/$CHART/live/$CHART_FILE" "$TMP/new/$CHART_FILE"; else cp "$TMP/$CHART/live/$CHART_FILE" "$TMP/new/$CHART_FILE"; echo "the chart function already has the new code"; fi
[ "$(filesha "$TMP/new/$REPORT_FILE")" = "$REPORT_NEW" ] || stop "the report code built here is not the code that was tested"
[ "$(filesha "$TMP/new/$CHART_FILE")" = "$CHART_NEW" ] || stop "the chart code built here is not the code that was tested"
if [ "$(filesha "$ROOT/stock_metrics.py")" = "$METRICS_NEW" ]; then cp "$ROOT/stock_metrics.py" "$TMP/new/stock_metrics.py"; echo "stock_metrics.py already has the new functions"
else
    [ "$(filesha "$ROOT/stock_metrics.py")" = "$METRICS_WAS" ] || stop "stock_metrics.py has changed since this was built"
    python3 "$HERE/patch_metrics.py" "$TMP/new/$REPORT_FILE" "$ROOT/stock_metrics.py" "$TMP/new/stock_metrics.py"
    [ "$(filesha "$TMP/new/stock_metrics.py")" = "$METRICS_NEW" ] || stop "the stock_metrics.py built here is not the one that was tested"
fi
if [ "$REPORT_STATE" = old ]; then
    python3 -W ignore "$HERE/report_test.py" "$MIRROR/$REPORT/$REPORT_FILE" "$TMP/new/$REPORT_FILE" | tail -1 | tee "$TMP/t1"; grep -q " 0 failed" "$TMP/t1" || stop "the report's tests do not pass"
fi
python3 -W ignore "$HERE/chart_test.py" "$TMP/new/$CHART_FILE" "$TMP/new/$REPORT_FILE" | tail -1 | tee "$TMP/t2"; grep -q " 0 failed" "$TMP/t2" || stop "the chart's tests do not pass"

update() {   # function, file, state: the chart first (the report that is live now works with either chart)
    say "$1"
    if [ "$3" = new ]; then echo "already deployed, skipping"; return; fi
    cp "$TMP/new/$2" "$TMP/$1/$2"; (cd "$TMP/$1" && zip -q -X new.zip "$2")
    if [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${1}_before_report_20261011.zip and update $1 ($(wc -l < "$TMP/$1/live/$2" | tr -d ' ') lines -> $(wc -l < "$TMP/new/$2" | tr -d ' '))"; return; fi
    [ -f "$BACKUP/${1}_before_report_20261011.zip" ] || cp "$TMP/$1/live.zip" "$BACKUP/${1}_before_report_20261011.zip"
    "${AWS[@]}" lambda update-function-code --function-name "$1" --zip-file "fileb://$TMP/$1/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$1"
    [ "$(sha "$1")" = "$(zipsha "$TMP/$1/new.zip")" ] || stop "$1 does not report the new package"
    cp "$TMP/new/$2" "$MIRROR/$1/$2"; echo "live, and the mirror updated"
}
update "$CHART" "$CHART_FILE" "$CHART_STATE"
update "$REPORT" "$REPORT_FILE" "$REPORT_STATE"

say "stock_metrics.py (the stock pages' copy of the scoring)"
if cmp -s "$TMP/new/stock_metrics.py" "$ROOT/stock_metrics.py"; then echo "already the new functions"
elif [ "$DRY" = "true" ]; then echo "(dry run) would copy the new functions in"
else cp "$TMP/new/stock_metrics.py" "$ROOT/stock_metrics.py"; echo "copied in (the stock pages follow at the next daily run)"; fi

if [ "$DRY" != "true" ]; then
    say "the live report for four symbols (nothing is saved to anyone's history)"
    for sym in AAPL BHP.AX IMB.L SPY; do
        curl -s -m 70 -X POST "$REPORT_URL" -H 'Content-Type: application/json' -d "{\"symbols\":[\"$sym\"],\"userId\":\"nobody-deploy-check@example.com\",\"skipHistorySave\":true}" | python3 -c "
import sys, json, re, base64
d = json.load(sys.stdin); r = (d.get('results') or [None])[0]
if not r: print('$sym: NO REPORT', str(d)[:200]); sys.exit()
t = r['comprehensive_analysis']; m = re.search(r'data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)', t); pic = base64.b64decode(m.group(1)).decode() if m else ''
line = lambda key: next((l.strip() for l in t.split('\n') if key in l), '-')
print('$sym:', line('Current Price'), '|', line('Prices for this share'), '| score', r['investment_score'], '| RSI text %.0f, chart %s' % (r['rsi'], (re.findall(r'RSI \(14\): (\d+)', pic) or ['-'])[0]))
print('   ', line('Trend:'), '|', line('Company figures from') if 'Company figures from' in t else line('were not available'), '| report %d KB, chart %d KB%s' % (len(t) // 1024, len(pic) // 1024, ', CHART ERROR' if 'Chart Generation Error' in pic else ''))"
    done
    say "a chart asked for by itself, as the pages do"
    curl -s -m 30 -X POST "$CHART_URL" -H 'Content-Type: application/json' -d '{"symbol":"MSFT"}' | python3 -c "
import sys; s = sys.stdin.read(); print('MSFT chart:', len(s), 'bytes, starts', s[:4], '| plain ASCII' if s.isascii() else '| NOT ASCII', '| error picture' if 'Chart Generation Error' in s else '| drawn')"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
