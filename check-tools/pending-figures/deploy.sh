#!/bin/bash
# One-off deploy (11 Oct 2026), second step for the single-stock report: company figures for shares outside the US.
# The first step tried to read Yahoo's summary of a share from the function; Yahoo refuses anything that is not a
# browser ("too many requests", from AWS and from this Mac alike), so those reports said, honestly, that the score was
# from price and volume only. The daily job already keeps Yahoo's figures for every stock on the site. This:
#  - publishes them as one private file (publish_company_figures.py -> s3://stockiq-dynamic-stock-lists/site-data/
#    company_figures.json; the daily deploy now does the same after its snapshot step);
#  - stockiq-option-1-1-custom-analysis: reads that file for the figures its first source lacks, says where they came
#    from and from when; the direct route to Yahoo is taken out; a price a hair from its average reads "level with";
#  - stock_metrics.py: the same scoring functions copied across again (the one wording change).
#
#   Preview (changes nothing on AWS):   DRY_RUN=true bash deploy.sh
#   Deploy:                             bash deploy.sh
#
# Safe to run twice. Roll back: ~/VSCODE/backup/stockiq-option-1-1-custom-analysis_before_figures_20261011.zip; the file
# on S3 can stay (the older code does not read it).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq
AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync
BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"
TMP="$(mktemp -d)"
REPORT=stockiq-option-1-1-custom-analysis; FILE=lambda_function2.py
REPORT_WAS="a4Ud7RGxje2NIsFzH0yGw887gKBwab/o4kV/wsN1Yyg="
OLD_FILE=5a8ed58b8330a50631f6c73a1bf4833c868ad44efabb8a4988765021ed5c1287      # sha256 of the files
NEW_FILE=14618fd5af5f323cce3c28dd725b6ed96ee3081c44b97d2f62053d1f932f6b20
METRICS_WAS=f7cae9d0ebaf7c8f2df426ff9d7670b351862b98c19b1914945abecf5ec78c0a
METRICS_NEW=5c034782379b41001061172923eaf6f1a152c8741c663a401bb08c74229ce8ac
REPORT_URL=https://5oqosafg2mflk7oyydkk3d3rdq0amufq.lambda-url.us-east-1.on.aws/

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
sha()  { "${AWS[@]}" lambda get-function-configuration --function-name "$1" --query CodeSha256 --output text; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }

if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed on AWS"

say "what is live, and the new code built from it and tested"
mkdir -p "$TMP/live" "$TMP/new" "$TMP/before"
curl -s -o "$TMP/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$REPORT" --query Code.Location --output text)"
unzip -q -o "$TMP/live.zip" -d "$TMP/live"
[ "$(unzip -Z1 "$TMP/live.zip" | tr '\n' ' ')" = "$FILE " ] || stop "the package holds other files than $FILE"
if [ "$(filesha "$TMP/live/$FILE")" = "$NEW_FILE" ]; then STATE=new; cp "$TMP/live/$FILE" "$TMP/new/$FILE"; echo "the report function already has the new code"
else
    STATE=old
    [ "$(sha "$REPORT")" = "$REPORT_WAS" ] && [ "$(filesha "$TMP/live/$FILE")" = "$OLD_FILE" ] || stop "$REPORT has changed on AWS since this was built"
    cmp -s "$TMP/live/$FILE" "$MIRROR/$REPORT/$FILE" || stop "the live function is not the same as the local mirror"
    python3 "$HERE/patch_report2.py" "$TMP/live/$FILE" "$TMP/new/$FILE"
    [ "$(filesha "$TMP/new/$FILE")" = "$NEW_FILE" ] || stop "the code built here is not the code that was tested"
fi
if [ "$(filesha "$ROOT/stock_metrics.py")" = "$METRICS_NEW" ]; then cp "$ROOT/stock_metrics.py" "$TMP/new/stock_metrics.py"
else
    [ "$(filesha "$ROOT/stock_metrics.py")" = "$METRICS_WAS" ] || stop "stock_metrics.py has changed since this was built"
    python3 "$ROOT/check-tools/report/patch_metrics.py" "$TMP/new/$FILE" "$ROOT/stock_metrics.py" "$TMP/new/stock_metrics.py"
    [ "$(filesha "$TMP/new/stock_metrics.py")" = "$METRICS_NEW" ] || stop "the stock_metrics.py built here is not the one that was tested"
fi
unzip -q -o "$BACKUP/stockiq-option-1-1-custom-analysis_before_report_20261011.zip" -d "$TMP/before"
python3 -W ignore "$ROOT/check-tools/report/report_test.py" "$TMP/before/$FILE" "$TMP/new/$FILE" | tail -1 | tee "$TMP/t1"; grep -q " 0 failed" "$TMP/t1" || stop "the report's tests do not pass"
python3 -W ignore "$ROOT/check-tools/report/chart_test.py" "$MIRROR/stockiq-chart-generator/lambda_function_simple.py" "$TMP/new/$FILE" | tail -1 | tee "$TMP/t2"; grep -q " 0 failed" "$TMP/t2" || stop "the chart's tests do not pass"

say "the file of company figures"
DRY_RUN="$DRY" python3 "$ROOT/publish_company_figures.py" || stop "the company figures were not published"
if [ "$DRY" != "true" ]; then
    "${AWS[@]}" s3api head-object --bucket stockiq-dynamic-stock-lists --key site-data/company_figures.json --query '[ContentLength,LastModified]' --output text
    [ "$("${AWS[@]}" s3api get-public-access-block --bucket stockiq-dynamic-stock-lists --query 'PublicAccessBlockConfiguration.RestrictPublicBuckets' --output text)" = "True" ] || stop "the bucket is not private any more"
fi

say "$REPORT"
if [ "$STATE" = new ]; then echo "already deployed, skipping"
else
    cp "$TMP/new/$FILE" "$TMP/$FILE"; (cd "$TMP" && zip -q -X new.zip "$FILE")
    if [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${REPORT}_before_figures_20261011.zip and update $REPORT ($(wc -l < "$TMP/live/$FILE" | tr -d ' ') lines -> $(wc -l < "$TMP/new/$FILE" | tr -d ' '))"
    else
        [ -f "$BACKUP/${REPORT}_before_figures_20261011.zip" ] || cp "$TMP/live.zip" "$BACKUP/${REPORT}_before_figures_20261011.zip"
        "${AWS[@]}" lambda update-function-code --function-name "$REPORT" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
        "${AWS[@]}" lambda wait function-updated --function-name "$REPORT"
        [ "$(sha "$REPORT")" = "$(zipsha "$TMP/new.zip")" ] || stop "$REPORT does not report the new package"
        cp "$TMP/new/$FILE" "$MIRROR/$REPORT/$FILE"; echo "live, and the mirror updated"
    fi
fi

say "stock_metrics.py (the stock pages' copy of the scoring)"
if cmp -s "$TMP/new/stock_metrics.py" "$ROOT/stock_metrics.py"; then echo "already the same"
elif [ "$DRY" = "true" ]; then echo "(dry run) would copy the scoring functions across again"
else cp "$TMP/new/stock_metrics.py" "$ROOT/stock_metrics.py"; echo "copied across (the stock pages follow at the next daily run)"; fi

if [ "$DRY" != "true" ]; then
    say "the live report for five symbols (nothing is saved to anyone's history)"
    for sym in BHP.AX IMB.L 7203.T SHOP.TO AAPL; do
        curl -s -m 70 -X POST "$REPORT_URL" -H 'Content-Type: application/json' -d "{\"symbols\":[\"$sym\"],\"userId\":\"nobody-deploy-check@example.com\",\"skipHistorySave\":true}" | python3 -c "
import sys, json
d = json.load(sys.stdin); r = (d.get('results') or [None])[0]
if not r: print('$sym: NO REPORT', str(d)[:200]); sys.exit()
t = r['comprehensive_analysis']; line = lambda key: next((l.strip() for l in t.split('\n') if key in l), '-')
print('$sym:', line('Current Price'), '| score', r['investment_score'], '|', line('Company figures from') if 'Company figures from' in t else line('were not available'))
print('    P/E', r['pe_ratio'], '| margin', r['profit_margin'], '| debt/equity', r['debt_to_equity'], '| ROE', r['return_on_equity'], '|', line('Trend:'))"
    done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
