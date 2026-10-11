#!/bin/bash
# One-off deploy (11 Oct 2026): three faults in the crypto screener, found when the owner asked whether its top 10 is in the
# right order (it is: by score, equal scores largest coin first).
#  - The 54 crypto workers (stockiq-option-7-1-worker-N, all the same code): MACD was never worked out. It needs 35 days of
#    prices and 30 were asked for, so every one of the 540 coins was scored "MACD Bear: -2". 90 days are now asked for, for
#    MACD alone (everything else still uses the last 30), and too little history counts as neutral, not as a bear.
#  - The orchestrator: a coin whose price does not move (too small for the price source's digits) is left out of the ranking
#    (a flat line read as "extremely oversold" and one such coin stood 5th); and the report says when coins tie at the cut.
# Every coin's score can change by a few points with MACD at work, so the top 10 will be partly different after this.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice: a function that already has the new code is skipped; stops if live code is not what this was built against.
# Roll back: ~/VSCODE/backup/stockiq-option-7-1-worker_before_macd_20261011.zip (the same zip to all 54) and
#   ~/VSCODE/backup/stockiq-option-7-1-orchestrator_before_macd_20261011.zip
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AWS=(aws --profile default --region us-east-1)
MIRROR=/Users/dave/VSCODE/stockiq/lambda-sync
BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"
TMP="$(mktemp -d)"
WORKER_WAS="rV+ursmQ/+dZYzbAFzr7RDX86ZTkyLLwiax7jpoO2RY="
ORCH_WAS="1n+2nBT+/Uop5KKuaZeIYmlcvNHN3srLPVsBAy4M4hM="
ORCH_URL=https://5fyemil3eipbwqyyb2kloijyhi0uvtct.lambda-url.us-east-1.on.aws/

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
run()  { if [ "$DRY" = "true" ]; then echo "(dryrun) $*"; else "$@"; fi; }
sha()  { "${AWS[@]}" lambda get-function-configuration --function-name "$1" --query CodeSha256 --output text; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }

if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "the 54 crypto workers"
MIRROR_WORKER="$(ls -d "$MIRROR"/stockiq-option-7-1-worker-* | head -1)"
mkdir -p "$TMP/w/live"
curl -s -o "$TMP/w/live.zip" "$("${AWS[@]}" lambda get-function --function-name stockiq-option-7-1-worker-1 --query Code.Location --output text)"
unzip -q -o "$TMP/w/live.zip" -d "$TMP/w/live"
[ "$(unzip -Z1 "$TMP/w/live.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "a worker's package holds more than lambda_function.py"
if cmp -s "$TMP/w/live/lambda_function.py" "$HERE/worker/lambda_function.py"; then
    echo "worker-1 already has the new code"
else
    cmp -s "$TMP/w/live/lambda_function.py" "$MIRROR_WORKER/lambda_function.py" || stop "the live worker-1 is not the same as the local mirror"
    run cp "$TMP/w/live.zip" "$BACKUP/stockiq-option-7-1-worker_before_macd_20261011.zip"
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
    run cp "$TMP/o/live.zip" "$BACKUP/stockiq-option-7-1-orchestrator_before_macd_20261011.zip"
    cp "$HERE/orchestrator/orchestrator.py" "$TMP/o/live/orchestrator.py"
    (cd "$TMP/o/live" && zip -q -X "$TMP/o/new.zip" orchestrator.py orchestrator_simple.py prediction_memory.py)
    echo "new package: $(unzip -Z1 "$TMP/o/new.zip" | tr '\n' ' ')"
    run "${AWS[@]}" lambda update-function-code --function-name stockiq-option-7-1-orchestrator --zip-file "fileb://$TMP/o/new.zip" --query LastModified --output text
    run "${AWS[@]}" lambda wait function-updated --function-name stockiq-option-7-1-orchestrator
    run cp "$HERE/orchestrator/orchestrator.py" "$MIRROR/stockiq-option-7-1-orchestrator/orchestrator.py"
fi

if [ "$DRY" != "true" ]; then
    say "one run of the live screener (as a visitor's run: it reads, and records nothing)"
    curl -s -m 150 -X POST "$ORCH_URL" -H 'Content-Type: application/json' -d '{}' | python3 -c "
import sys, json, collections
d = json.load(sys.stdin); c = d.get('coins', [])
print(len(c), 'coins ranked; MACD now says:', dict(collections.Counter(str(x.get('macd_signal'))[:11] for x in c).most_common(5)))
print('top 10:', [(x['symbol'], x['score']) for x in c[:10]])
print('coins with a stuck price still in the list:', [x['symbol'] for x in c if x.get('change_24h') == x.get('change_7d') == x.get('change_30d')])"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
