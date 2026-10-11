#!/bin/bash
# One-off deploy (11 Oct 2026): the crypto worker after a review of its code, at the owner's request ("i built it with an
# old AI version, its been a long time since it was reviewed"). The 54 workers, one code. No score changes:
#  - one request to the price source per coin where there were two (the first was wholly contained in the second);
#  - a day's high, low, close and volume stay together (each was filtered for missing values by itself);
#  - the old mode is gone: called with no coin, a worker analysed ten coins of a 540-coin CoinSpot list written into its
#    code, with a table read and a table scan for each (the address is public; nothing on the site calls it so).
# The file goes from 1,134 lines to 689.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Safe to run twice. Roll back: ~/VSCODE/backup/stockiq-option-7-1-worker_before_clean_20261011.zip (the same to all 54).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AWS=(aws --profile default --region us-east-1)
MIRROR=/Users/dave/VSCODE/stockiq/lambda-sync
BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"
TMP="$(mktemp -d)"
WORKER_WAS="l49ar2i7T2ks9w3PzP84IFZ6+4LZYCpO+HnPcYDubl8="
ORCH_URL=https://5fyemil3eipbwqyyb2kloijyhi0uvtct.lambda-url.us-east-1.on.aws/

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
sha()  { "${AWS[@]}" lambda get-function-configuration --function-name "$1" --query CodeSha256 --output text; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
top() { curl -s -m 150 -X POST "$ORCH_URL" -H 'Content-Type: application/json' -d '{}' | python3 -c "import sys, json; d = json.load(sys.stdin); print(len(d['coins']), ' '.join(c['symbol'] + ':' + str(c['score']) for c in d['coins'][:10]))"; }

if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
MIN=$((10#$(date -u +%M) % 30)); if [ "$DRY" != "true" ] && [ "$MIN" -ge 6 ] && [ "$MIN" -le 12 ]; then stop "the crypto schedule (:08, :38) and the autopilot (:10, :40) run about now; try again in a few minutes"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

MIRROR_WORKER="$(ls -d "$MIRROR"/stockiq-option-7-1-worker-* | head -1)"
mkdir -p "$TMP/live" "$TMP/new"
curl -s -o "$TMP/live.zip" "$("${AWS[@]}" lambda get-function --function-name stockiq-option-7-1-worker-1 --query Code.Location --output text)"
unzip -q -o "$TMP/live.zip" -d "$TMP/live"
[ "$(unzip -Z1 "$TMP/live.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "a worker's package holds more than lambda_function.py"

say "the new code, built from the code that is live, against it on recorded answers of the price source"
if cmp -s "$TMP/live/lambda_function.py" "$HERE/worker/lambda_function.py"; then echo "worker-1 already has the new code"; cp "$TMP/live/lambda_function.py" "$TMP/new/lambda_function.py"
else
    cmp -s "$TMP/live/lambda_function.py" "$MIRROR_WORKER/lambda_function.py" || stop "the live worker-1 is not the same as the local mirror"
    python3 "$HERE/patch_worker.py" "$TMP/live/lambda_function.py" "$TMP/new/lambda_function.py"
    cmp -s "$TMP/new/lambda_function.py" "$HERE/worker/lambda_function.py" || stop "the code built here is not the code that was tested"
    python3 -W ignore "$HERE/worker_test.py" "$TMP/live/lambda_function.py" "$TMP/new/lambda_function.py" "$HERE/recorded.txt" | tail -1 | tee "$TMP/t"; grep -q " 0 failed" "$TMP/t" || stop "the tests do not pass"
    [ "$DRY" = "true" ] || [ -f "$BACKUP/stockiq-option-7-1-worker_before_clean_20261011.zip" ] || cp "$TMP/live.zip" "$BACKUP/stockiq-option-7-1-worker_before_clean_20261011.zip"
fi
[ "$DRY" = "true" ] || { echo "the live screener before: $(top)"; }

say "the 54 crypto workers"
(cd "$TMP/new" && zip -q -X new.zip lambda_function.py)
NEW="$(zipsha "$TMP/new/new.zip")"
done_n=0; skipped=0
for i in $(seq 1 54); do
    f="stockiq-option-7-1-worker-$i"; have="$(sha "$f")"
    if [ "$have" = "$NEW" ]; then skipped=$((skipped + 1)); continue; fi
    [ "$have" = "$WORKER_WAS" ] || stop "$f has other code than expected ($have)"
    if [ "$DRY" = "true" ]; then done_n=$((done_n + 1)); continue; fi
    "${AWS[@]}" lambda update-function-code --function-name "$f" --zip-file "fileb://$TMP/new/new.zip" --query CodeSha256 --output text >/dev/null
    done_n=$((done_n + 1))
done
echo "updated $done_n$([ "$DRY" = "true" ] && echo ' (dry run: would be)'), already new $skipped"
if [ "$DRY" != "true" ]; then
    "${AWS[@]}" lambda wait function-updated --function-name stockiq-option-7-1-worker-54
    same=0; for i in $(seq 1 54); do [ "$(sha "stockiq-option-7-1-worker-$i")" = "$NEW" ] && same=$((same + 1)); done
    echo "$same of 54 workers have the new code ($NEW)"
    [ "$same" = "54" ] || stop "not every worker has the new code: run this again"
    cp "$TMP/new/lambda_function.py" "$MIRROR_WORKER/lambda_function.py"
    W1="$("${AWS[@]}" lambda get-function-url-config --function-name stockiq-option-7-1-worker-1 --query FunctionUrl --output text)"
    say "a live worker, the three ways of calling it"
    curl -s -m 50 -X POST "$W1" -H 'Content-Type: application/json' -d '{"coin_list":["BTC","ETH","SUI20947","NOSUCHCOINX"]}' | python3 -c "
import sys, json; d = json.load(sys.stdin); print('a list:', [(r['ticker'], (r['coin'] or {}).get('score'), round((r['coin'] or {}).get('price', 0), 4)) for r in d['results']])"
    curl -s -m 50 -X POST "$W1" -H 'Content-Type: application/json' -d '{"single_coin":"BTC"}' | python3 -c "
import sys, json; d = json.load(sys.stdin); c = d['coins'][0]; print('one coin:', c['symbol'], c['score'], round(c['price'], 2), '|', '; '.join(c['score_breakdown'][:4]))"
    curl -s -m 50 -o /dev/null -w "no coin: HTTP %{http_code} in %{time_total} s\n" -X POST "$W1" -H 'Content-Type: application/json' -d '{}'
    START=$(date +%s); echo "the live screener after:  $(top)   ($(( $(date +%s) - START )) seconds)"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
