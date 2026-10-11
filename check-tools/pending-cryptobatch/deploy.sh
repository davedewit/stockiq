#!/bin/bash
# One-off deploy (11 Oct 2026): the crypto job asks for ten coins a call instead of one.
# The owner wants to stay inside Lambda's free allowance (a million calls a month). The crypto screener called a worker
# once per coin: 540 calls a run, 48 scheduled runs a day for the top-10 history, about 0.8 million calls a month by
# itself. Measured the same day: its computing time is small (about 70k of the 400k free GB-seconds a month; the rebuild
# of 10 Oct cut it by two thirds), so the number of calls is the only thing near the limit.
#  - The 54 workers (stockiq-option-7-1-worker-N, one code): a new mode {"coin_list": [...]} that analyses each coin
#    exactly as the single-coin mode does and answers one result per coin. Single-coin mode is unchanged.
#  - The orchestrator: sends the 540 coins in 54 batches of ten, one batch to each worker function, and asks once more
#    (on other functions) for any coin that did not come back. Same coins, same scores, same order, same report.
# Workers first: the orchestrator needs the new mode.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Safe to run twice. Roll back: ~/VSCODE/backup/stockiq-option-7-1-orchestrator_before_batch_20261011.zip first (the old
# orchestrator works with the new workers), then, if wanted, stockiq-option-7-1-worker_before_batch_20261011.zip to all 54.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AWS=(aws --profile default --region us-east-1)
MIRROR=/Users/dave/VSCODE/stockiq/lambda-sync
BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"
TMP="$(mktemp -d)"
WORKER_WAS="NmXC9dcsA6p5tXJl+u6VZIfdsrvM3ERN/DmMSQ9zalI="
ORCH_WAS="Tyyx+Pb2l+sy7avfCncwduEtmFtYn6Lws+5g6dj9Kc0="
ORCH_URL=https://5fyemil3eipbwqyyb2kloijyhi0uvtct.lambda-url.us-east-1.on.aws/

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
sha()  { "${AWS[@]}" lambda get-function-configuration --function-name "$1" --query CodeSha256 --output text; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }

if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
MIN=$((10#$(date -u +%M) % 30)); if [ "$DRY" != "true" ] && [ "$MIN" -ge 6 ] && [ "$MIN" -le 12 ]; then stop "the crypto schedule (:08, :38) and the autopilot (:10, :40) run about now; try again in a few minutes"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

MIRROR_WORKER="$(ls -d "$MIRROR"/stockiq-option-7-1-worker-* | head -1)"
say "the new code against the code that is live, on a stand-in for the workers"
python3 -W ignore "$HERE/batch_test.py" "$MIRROR/stockiq-option-7-1-orchestrator/orchestrator.py" "$HERE/orchestrator/orchestrator.py" "$MIRROR_WORKER/lambda_function.py" "$HERE/worker/lambda_function.py" "$HERE/btc_template.json" 2>/dev/null | tail -1 | tee "$TMP/t" || true
if cmp -s "$MIRROR/stockiq-option-7-1-orchestrator/orchestrator.py" "$HERE/orchestrator/orchestrator.py"; then echo "(the mirror already holds the new code: the comparison is of the new code with itself)"; else grep -q " 0 failed" "$TMP/t" || stop "the tests do not pass"; fi

say "the 54 crypto workers"
mkdir -p "$TMP/w/live"
curl -s -o "$TMP/w/live.zip" "$("${AWS[@]}" lambda get-function --function-name stockiq-option-7-1-worker-1 --query Code.Location --output text)"
unzip -q -o "$TMP/w/live.zip" -d "$TMP/w/live"
[ "$(unzip -Z1 "$TMP/w/live.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "a worker's package holds more than lambda_function.py"
if cmp -s "$TMP/w/live/lambda_function.py" "$HERE/worker/lambda_function.py"; then
    echo "worker-1 already has the new code"
else
    cmp -s "$TMP/w/live/lambda_function.py" "$MIRROR_WORKER/lambda_function.py" || stop "the live worker-1 is not the same as the local mirror"
    [ "$DRY" = "true" ] || [ -f "$BACKUP/stockiq-option-7-1-worker_before_batch_20261011.zip" ] || cp "$TMP/w/live.zip" "$BACKUP/stockiq-option-7-1-worker_before_batch_20261011.zip"
fi
cp "$HERE/worker/lambda_function.py" "$TMP/w/lambda_function.py"
(cd "$TMP/w" && zip -q -X new.zip lambda_function.py)
NEW="$(zipsha "$TMP/w/new.zip")"
done_n=0; skipped=0
for i in $(seq 1 54); do
    f="stockiq-option-7-1-worker-$i"; have="$(sha "$f")"
    if [ "$have" = "$NEW" ]; then skipped=$((skipped + 1)); continue; fi
    [ "$have" = "$WORKER_WAS" ] || stop "$f has other code than expected ($have)"
    if [ "$DRY" = "true" ]; then done_n=$((done_n + 1)); continue; fi
    "${AWS[@]}" lambda update-function-code --function-name "$f" --zip-file "fileb://$TMP/w/new.zip" --query CodeSha256 --output text >/dev/null
    done_n=$((done_n + 1))
done
echo "updated $done_n$([ "$DRY" = "true" ] && echo ' (dry run: would be)'), already new $skipped"
if [ "$DRY" != "true" ]; then
    "${AWS[@]}" lambda wait function-updated --function-name stockiq-option-7-1-worker-54
    same=0; for i in $(seq 1 54); do [ "$(sha "stockiq-option-7-1-worker-$i")" = "$NEW" ] && same=$((same + 1)); done
    echo "$same of 54 workers have the new code"
    [ "$same" = "54" ] || stop "not every worker has the new code: run this again"
    cp "$HERE/worker/lambda_function.py" "$MIRROR_WORKER/lambda_function.py"
    W1="$("${AWS[@]}" lambda get-function-url-config --function-name stockiq-option-7-1-worker-1 --query FunctionUrl --output text)"
    curl -s -m 50 -X POST "$W1" -H 'Content-Type: application/json' -d '{"coin_list":["BTC","ETH","SUI20947","NOSUCHCOINX"]}' | python3 -c "
import sys, json
d = json.load(sys.stdin); print('a live worker, four coins in one call:', [(r['ticker'], (r['coin'] or {}).get('score'), round((r['coin'] or {}).get('price', 0), 4)) for r in d['results']])"
fi

say "the orchestrator"
mkdir -p "$TMP/o/live"
curl -s -o "$TMP/o/live.zip" "$("${AWS[@]}" lambda get-function --function-name stockiq-option-7-1-orchestrator --query Code.Location --output text)"
unzip -q -o "$TMP/o/live.zip" -d "$TMP/o/live"
if cmp -s "$TMP/o/live/orchestrator.py" "$HERE/orchestrator/orchestrator.py"; then
    echo "already deployed, skipping"
else
    [ "$(sha stockiq-option-7-1-orchestrator)" = "$ORCH_WAS" ] || stop "the orchestrator has changed on AWS since this was built"
    for f in orchestrator.py orchestrator_simple.py prediction_memory.py; do cmp -s "$TMP/o/live/$f" "$MIRROR/stockiq-option-7-1-orchestrator/$f" || stop "the live orchestrator's $f is not the same as the local mirror"; done
    if [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $BACKUP/stockiq-option-7-1-orchestrator_before_batch_20261011.zip and update the orchestrator"
    else
        BEFORE="$(curl -s -m 150 -X POST "$ORCH_URL" -H 'Content-Type: application/json' -d '{}' | python3 -c "import sys, json; d = json.load(sys.stdin); print(len(d['coins']), ' '.join(c['symbol'] for c in d['coins'][:10]))")"
        [ -f "$BACKUP/stockiq-option-7-1-orchestrator_before_batch_20261011.zip" ] || cp "$TMP/o/live.zip" "$BACKUP/stockiq-option-7-1-orchestrator_before_batch_20261011.zip"
        cp "$HERE/orchestrator/orchestrator.py" "$TMP/o/live/orchestrator.py"
        (cd "$TMP/o/live" && zip -q -X "$TMP/o/new.zip" orchestrator.py orchestrator_simple.py prediction_memory.py)
        "${AWS[@]}" lambda update-function-code --function-name stockiq-option-7-1-orchestrator --zip-file "fileb://$TMP/o/new.zip" --query LastModified --output text
        "${AWS[@]}" lambda wait function-updated --function-name stockiq-option-7-1-orchestrator
        cp "$HERE/orchestrator/orchestrator.py" "$MIRROR/stockiq-option-7-1-orchestrator/orchestrator.py"
        say "one run of the live screener before and after (a visitor's run: it reads, and records nothing)"
        START=$(date +%s)
        AFTER="$(curl -s -m 150 -X POST "$ORCH_URL" -H 'Content-Type: application/json' -d '{}' | python3 -c "import sys, json; d = json.load(sys.stdin); print(len(d['coins']), ' '.join(c['symbol'] for c in d['coins'][:10]))")"
        echo "before: $BEFORE"; echo "after:  $AFTER   ($(( $(date +%s) - START )) seconds)"
    fi
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
