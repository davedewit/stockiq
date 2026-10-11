#!/bin/bash
# One-off deploy (11 Oct 2026): the notification bell's script takes over from any older copy of itself that a browser still
# holds. The owner saw no autopilot trades in the bell on any page: his browser still had an old theme.js (kept a day under the
# old rule), which asked for the first version of the bell's script out of the browser's own store; that old copy ran first and
# shut the current one out. Reproduced by playing those old copies back to the live pages (live_bell_check.js, OLD_THEME / OLD_BELL).
#  - autopilot-bell.js (version 4): always takes over; empties the older copies' store so that they draw nothing; other names
#    for its own store, marks and sign on the red number; carries the signature a version-3 copy expects, so that copy leaves
#    the list alone; a brake if something keeps undoing the list.
#  - Function stockiq-ai-trader: the bell's question is answered only when marked "list": 2 (an older copy is told nothing).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice; stops if the live code or the website file is not what this was built against.
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_takeover_20261011.zip
#   aws lambda update-function-code --function-name stockiq-ai-trader --zip-file fileb://<that zip> --profile default --region us-east-1
# Website: git checkout autopilot-bell.js in ~/VSCODE/website and upload it again.
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
    run cp "$work/live.zip" "$BACKUP/${name}_before_autopilot_takeover_20261011.zip"
    cp "$new" "$work/live/$main"
    (cd "$work/live" && zip -q -X "$work/new.zip" ./*.py)
    echo "new package: $(unzip -Z1 "$work/new.zip" | tr '\n' ' ')"
    run "${AWS[@]}" lambda update-function-code --function-name "$name" --zip-file "fileb://$work/new.zip" --query LastModified --output text
    run "${AWS[@]}" lambda wait function-updated --function-name "$name"
    run cp "$new" "$MIRROR/$name/$main"
}

# 1. The autopilot function
deploy_lambda "$TRADER" lambda_function.py "$HERE/lambda/lambda_function.py" "+Z5scAfikqPIEcGPDlARJVC/f3NOcIGjmSZ7YK4YGoc="
if [ "$DRY" != "true" ]; then
    say "the live function: an address with no plan gets an empty list, and so does a question from an older copy of the script"
    curl -s -m 60 -X POST "$TRADER_URL" -H 'Content-Type: application/json' -d '{"action":"bell","userId":"nobody-deploy-check@example.com","list":2}'; echo
    curl -s -m 60 -X POST "$TRADER_URL" -H 'Content-Type: application/json' -d '{"action":"bell","userId":"nobody-deploy-check@example.com"}'; echo
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
check_web autopilot-bell.js 9065d8d9662f35a215892c23970981ef5750ccb47d7d3849d2d5776a54334920
run "${AWS[@]}" s3 cp "$WEB/autopilot-bell.js" "s3://$BUCKET/autopilot-bell.js" --cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript"
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /autopilot-bell.js --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
