#!/bin/bash
# One-off deploy (11 Oct 2026): the bell's script tells the site what it finds in a browser (which copy of itself is running,
# whether an older copy was on the page, what the bell's list holds, which theme.js the browser keeps), and replaces an old
# theme.js in the browser's store by the current one. The owner still sees none of the autopilot's trades in the bell while
# every test here shows them, so the facts have to come from his browser. Temporary: remove the report when it is solved.
#  - autopilot-bell.js (version 5).  - Function stockiq-ai-trader: action "belllog" writes the report to its log, for the
#    site's own accounts only.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_autopilot_report_20261011.zip; git checkout autopilot-bell.js in ~/VSCODE/website.
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
    run cp "$work/live.zip" "$BACKUP/${name}_before_autopilot_report_20261011.zip"
    cp "$new" "$work/live/$main"
    (cd "$work/live" && zip -q -X "$work/new.zip" ./*.py)
    echo "new package: $(unzip -Z1 "$work/new.zip" | tr '\n' ' ')"
    run "${AWS[@]}" lambda update-function-code --function-name "$name" --zip-file "fileb://$work/new.zip" --query LastModified --output text
    run "${AWS[@]}" lambda wait function-updated --function-name "$name"
    run cp "$new" "$MIRROR/$name/$main"
}

# 1. The autopilot function
deploy_lambda "$TRADER" lambda_function.py "$HERE/lambda/lambda_function.py" "PoZ2yvK1FdAVMmoAjS+7ZOu9TAfpXQXd24qiEXG6e3w="
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
check_web autopilot-bell.js 40950bb80f91a72ccd19853f07830ecc98023ec152702723c2211fb2b09222c3
run "${AWS[@]}" s3 cp "$WEB/autopilot-bell.js" "s3://$BUCKET/autopilot-bell.js" --cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript"
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /autopilot-bell.js --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
