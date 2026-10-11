#!/bin/bash
# One-off deploy (11 Oct 2026): a real trading cost on every practice buy and sale, and the bar the autopilot's results must clear.
#  - A cost of 0.1% is taken off each practice buy and each sale, by hand (practice-portfolio.js, TRADE_COST_PCT) and by the
#    autopilot (stockiq-ai-trader, TRADE_COST), so that a result is not flattered. Trades made before keep their result; the
#    month's figures and the bar charge them the same cost.
#  - The bar, set down before the results are in (bar_of, BAR_TRADES): 300 finished trades whose average, after costs, is ahead
#    of an S&P 500 fund over the same days (zero for a coin) by more than twice the margin of error. Shown on the panel.
#  - The panel says when shares are kept two days or less that a replay of four years found that losing to costs.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice; stops if live code or a website file is not what this was built against.
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_costs_20261011.zip; git checkout the three website files and upload them.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AWS=(aws --profile default --region us-east-1)
WEB=/Users/dave/VSCODE/website
MIRROR=/Users/dave/VSCODE/stockiq/lambda-sync
BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h
DIST=EHXV50CPHY07R
TRADER=stockiq-ai-trader
TRADER_URL=https://qy6s553i647agmxthtecc24fje0zskms.lambda-url.us-east-1.on.aws/
DRY="${DRY_RUN:-false}"
TMP="$(mktemp -d)"

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
run()  { if [ "$DRY" = "true" ]; then echo "(dryrun) $*"; else "$@"; fi; }

if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

# deploy_lambda <function> <file inside the zip> <new file> <CodeSha256 the fix was built against>
deploy_lambda() {
    local name="$1" main="$2" new="$3" expected="$4" work="$TMP/$1"
    say "$name"
    mkdir -p "$work/live"
    curl -s -o "$work/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$name" --query Code.Location --output text)"
    unzip -q -o "$work/live.zip" -d "$work/live"
    if cmp -s "$work/live/$main" "$new"; then echo "already deployed, skipping"; return 0; fi
    local live_sha; live_sha="$("${AWS[@]}" lambda get-function-configuration --function-name "$name" --query CodeSha256 --output text)"
    [ "$live_sha" = "$expected" ] || stop "$name has changed on AWS since this was built (code $live_sha)"
    cmp -s "$work/live/$main" "$MIRROR/$name/$main" || stop "the live $name is not the same as the local mirror"
    run cp "$work/live.zip" "$BACKUP/${name}_before_autopilot_costs_20261011.zip"
    cp "$new" "$work/live/$main"
    (cd "$work/live" && zip -q -X "$work/new.zip" ./*.py)
    echo "new package: $(unzip -Z1 "$work/new.zip" | tr '\n' ' ')"
    run "${AWS[@]}" lambda update-function-code --function-name "$name" --zip-file "fileb://$work/new.zip" --query LastModified --output text
    run "${AWS[@]}" lambda wait function-updated --function-name "$name"
    run cp "$new" "$MIRROR/$name/$main"
}

# 1. The autopilot function
deploy_lambda "$TRADER" lambda_function.py "$HERE/lambda/lambda_function.py" "e6X8RM+wrRVbZAheFQfUr5uaKU1hUSGfjBHk1Q/W7xI="
if [ "$DRY" != "true" ]; then
    say "the live function answers the bell's question for an address with no plan (an empty list, no record made)"
    curl -s -m 60 -X POST "$TRADER_URL" -H 'Content-Type: application/json' -d '{"action":"bell","userId":"nobody-deploy-check@example.com","list":2}'; echo
fi

# 2. Website files
say "website files"
check_web() {   # <file> <sha256 of the version this was built against>
    local f="$1" expected="$2" have
    if cmp -s "$WEB/$f" "$HERE/web/$f"; then echo "$f: already copied"; return 0; fi
    have="$(shasum -a 256 "$WEB/$f" | cut -d' ' -f1)"
    [ "$have" = "$expected" ] || stop "$WEB/$f has changed since this was built"
    run cp "$HERE/web/$f" "$WEB/$f"
}
check_web practice-autopilot.js 57956b67cf2ba3785488a1567b2876596076d1d955913b0fa45e98d21c103b01
check_web practice-portfolio.js f7ddb505486a0e9e456c2ae0a7d5f7f63df13e0d331fd7974382fcf2b3acb365
check_web dashboard.html        9aa006cdf26ace69ba602bf42d3b8b592c29fbf9333aae8de873d5ffd7f787d3
for f in practice-autopilot.js practice-portfolio.js; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript"
done
run "${AWS[@]}" s3 cp "$WEB/dashboard.html" "s3://$BUCKET/dashboard.html" --cache-control "public, max-age=0, s-maxage=3600, must-revalidate" --content-type "text/html; charset=utf-8"
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /practice-autopilot.js /practice-portfolio.js /dashboard.html --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
