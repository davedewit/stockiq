#!/bin/bash
# One-off deploy (11 Oct 2026): in "What happens next", a release of the budget is listed at the check-in that can first
# spend it, not at the minute of the release (the owner read "more is released in 1 h 38 min" above "next check-in in
# 1 h 53 min" as two different next actions). Function stockiq-ai-trader only.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice; stops if the live code is not what this was built against.
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_release_20261011.zip
#   aws lambda update-function-code --function-name stockiq-ai-trader --zip-file fileb://<that zip> --profile default --region us-east-1
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
    run cp "$work/live.zip" "$BACKUP/${name}_before_autopilot_release_20261011.zip"
    cp "$new" "$work/live/$main"
    (cd "$work/live" && zip -q -X "$work/new.zip" ./*.py)
    echo "new package: $(unzip -Z1 "$work/new.zip" | tr '\n' ' ')"
    run "${AWS[@]}" lambda update-function-code --function-name "$name" --zip-file "fileb://$work/new.zip" --query LastModified --output text
    run "${AWS[@]}" lambda wait function-updated --function-name "$name"
    run cp "$new" "$MIRROR/$name/$main"
}

# 1. The autopilot function
deploy_lambda "$TRADER" lambda_function.py "$HERE/lambda/lambda_function.py" "5kK9DYb9C3iYOCR8CLMlYeiWswAlf7ixi7jCD8YDX1I="
if [ "$DRY" != "true" ]; then
    say "the live function answers (the page's own read-only call for an address with no plan: it must say the autopilot is locked, and makes no record)"
    curl -s -m 60 -X POST "$TRADER_URL" -H 'Content-Type: application/json' -d '{"action":"get","userId":"nobody-deploy-check@example.com"}' | cut -c1-300; echo
fi

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
