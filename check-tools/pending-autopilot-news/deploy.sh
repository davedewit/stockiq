#!/bin/bash
# One-off deploy (10 Oct 2026): stockiq-ai-trader only. Headlines for a coin must be about the coin: on 10 Oct the
# model was shown share news about ERG S.p.A. (an Italian energy company) as headlines for the Ergo coin (ERG).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice: each step first checks whether it has already been done, and stops if the live
# code or a website file is not what this was built against.
#
# Roll back: the previous Lambda code is saved in ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_news_20261010.zip
#   aws lambda update-function-code --function-name stockiq-ai-trader --zip-file fileb://<that zip> --profile default --region us-east-1
# No website files are part of this.
# (The older function simply ignores what the newer one added to a user's record.)
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
    run cp "$work/live.zip" "$BACKUP/${name}_before_autopilot_news_20261010.zip"
    cp "$new" "$work/live/$main"
    (cd "$work/live" && zip -q -X "$work/new.zip" ./*.py)
    echo "new package: $(unzip -Z1 "$work/new.zip" | tr '\n' ' ')"
    run "${AWS[@]}" lambda update-function-code --function-name "$name" --zip-file "fileb://$work/new.zip" --query LastModified --output text
    run "${AWS[@]}" lambda wait function-updated --function-name "$name"
    run cp "$new" "$MIRROR/$name/$main"
}

# 1. The autopilot function
deploy_lambda "$TRADER" lambda_function.py "$HERE/lambda/lambda_function.py" "XB+eZv23WEoacU/z2dP5H45NFeaQrcI6+rWwKDroi40="
if [ "$DRY" != "true" ]; then
    say "the live function answers (a read-only call for someone not on the list)"
    curl -s -m 30 -X POST "$TRADER_URL" -H 'Content-Type: application/json' -d '{"action":"get","userId":"not-on-the-list@example.com"}'; echo
fi

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
