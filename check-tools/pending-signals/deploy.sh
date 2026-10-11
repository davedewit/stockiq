#!/bin/bash
# One-off deploy (11 Oct 2026): the two trading-signals functions, after the owner asked for the "junky" items under
# Trading Signals to be reviewed. Both now run ONE file kept in git (signals/lambda_function.py):
#  - stockiq-option-2-trading-signals ("Enter Symbols for Live Signals")
#  - stockiq-option-2-2-auto-signals  ("Auto-detect Top 5 Signals")
# What changes: RSI the standard way (these had a third way of working it out); one bar a day and the latest session
# from the quote, as everywhere else; each reading says its currency, the company's name, the day's change and WHY (one
# plain line per ingredient, with its points); levels are the last 20 sessions' high and low (they were 2% inside
# those, or an arbitrary 5% either side); the time is marked UTC (a browser read it as local); a symbol with no prices
# is named. The auto-detect scans the screener's whole S&P 100 list and returns the five strongest readings in either
# direction (it looked at the first 15 names of a list in the code and called its five "top performers").
# Every field the page reads today is still there, so the page works unchanged; the new fields wait for the page.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Safe to run twice. Roll back: ~/VSCODE/backup/<function>_before_onefile_20261011.zip (one for each function).
set -euo pipefail

ROOT=/Users/dave/VSCODE/stockiq
AWS=(aws --profile default --region us-east-1)
MIRROR=$ROOT/lambda-sync
BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"
TMP="$(mktemp -d)"
CUSTOM=stockiq-option-2-trading-signals; CUSTOM_WAS="ZhJZ8TcXkec/HOPrEEDpjwEchHr3gHTKrYzBWvA58hE="
AUTO=stockiq-option-2-2-auto-signals;    AUTO_WAS="PxphwkJy5X1w2kWRA7wiZcZs02Szg/6QwI3g/X+ufMY="
NEW="6nVDLm4/8G6K0A37aSb+3r7YukSxFUUsK8tvYmwNL9M="          # the package built from signals/ (the same zip every time)

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
sha()  { "${AWS[@]}" lambda get-function-configuration --function-name "$1" --query CodeSha256 --output text; }

if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "the package, built from signals/ and tested"
BUILT="$(python3 "$ROOT/signals/build.py" "$TMP/signals.zip" | cut -d' ' -f1)"
[ "$BUILT" = "$NEW" ] || stop "the package built here ($BUILT) is not the one that was tested"
echo "$(unzip -Z1 "$TMP/signals.zip" | tr '\n' ' ')fingerprint $BUILT"
python3 -W ignore "$ROOT/signals/test_signals.py" | tail -1 | tee "$TMP/t"; grep -q " 0 failed" "$TMP/t" || stop "the tests do not pass"
rm -rf "$ROOT/signals/__pycache__"

for pair in "$CUSTOM:$CUSTOM_WAS" "$AUTO:$AUTO_WAS"; do
    f="${pair%%:*}"; was="${pair#*:}"
    say "$f"
    have="$(sha "$f")"
    if [ "$have" = "$NEW" ]; then echo "already on the new package"; continue; fi
    [ "$have" = "$was" ] || stop "$f has other code than this was built against ($have)"
    mkdir -p "$TMP/$f"
    curl -s -o "$TMP/$f/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$f" --query Code.Location --output text)"
    unzip -q -o "$TMP/$f/live.zip" -d "$TMP/$f"
    [ "$(unzip -Z1 "$TMP/$f/live.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "$f's package holds other files than lambda_function.py"
    cmp -s "$TMP/$f/lambda_function.py" "$MIRROR/$f/lambda_function.py" || stop "the live $f is not the same as the local mirror"
    if [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/${f}_before_onefile_20261011.zip and update $f"; continue; fi
    [ -f "$BACKUP/${f}_before_onefile_20261011.zip" ] || cp "$TMP/$f/live.zip" "$BACKUP/${f}_before_onefile_20261011.zip"
    "${AWS[@]}" lambda update-function-code --function-name "$f" --zip-file "fileb://$TMP/signals.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$f"
    [ "$(sha "$f")" = "$NEW" ] || stop "$f does not report the new package"
    cp "$ROOT/signals/lambda_function.py" "$ROOT/signals/sp100.txt" "$MIRROR/$f/"; echo "live, and the mirror updated"
done

if [ "$DRY" != "true" ]; then
    say "the live functions"
    curl -s -m 60 -X POST https://bqsbauyuyo2fygbgeswaloqtse0oxtio.lambda-url.us-east-1.on.aws/ -H 'Content-Type: application/json' -d '{"symbols":["NVDA","BHP.AX","IMB.L","NOSUCHX"]}' | python3 -c "
import sys, json
d = json.load(sys.stdin); print('symbols:', d['symbols_analyzed'], 'readings; not found', d.get('not_found'), '; time', d['timestamp'])
for s in d['signals']: print('  ', s['symbol'], s['name'][:24], '|', round(s['current_price'], 2), s['currency'], '%+.2f%%' % s['change_pct'], '|', s['action'], s['confidence'], '%+d' % s['signal_strength'], '|', '; '.join(s['reasons']))"
    START=$(date +%s)
    curl -s -m 60 -X POST https://clyq2htkani2c6bivunbb5pjdy0wakhm.lambda-url.us-east-1.on.aws/ -H 'Content-Type: application/json' -d '{}' | python3 -c "
import sys, json
d = json.load(sys.stdin); print('auto-detect:', d['methodology']); print('   readings across the list:', d['readings'])
for s in d['signals']: print('  ', s['symbol'], '|', round(s['current_price'], 2), s['currency'], '|', s['action'], s['confidence'], '%+d' % s['signal_strength'], '|', '; '.join(s['reasons']))"
    echo "   (the scan took $(( $(date +%s) - START )) seconds)"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
