#!/bin/bash
# One-off deploy (11 Oct 2026): the clean-up after the notification bell was settled, and the AI chat brought up to date.
#  - autopilot-bell.js (version 8): the temporary report of what it finds in a browser is taken out.
#  - Function stockiq-ai-trader: "belllog" no longer writes anything (older copies of the script are still answered).
#  - Function stockiq-ai-chat: its guide to the dashboard knows the arrows, the bell's one list, that a release of the budget is
#    listed at a check-in, and that the autopilot learns from every account.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice; stops if live code or the website file is not what this was built against.
# Roll back: ~/VSCODE/backup/stockiq-ai-trader_before_sweep_20261011.zip and stockiq-ai-chat_before_sweep_20261011.zip;
# git checkout autopilot-bell.js in ~/VSCODE/website and upload it again.
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
    run cp "$work/live.zip" "$BACKUP/${name}_before_sweep_20261011.zip"
    cp "$new" "$work/live/$main"
    (cd "$work/live" && zip -q -X "$work/new.zip" ./*.py)
    echo "new package: $(unzip -Z1 "$work/new.zip" | tr '\n' ' ')"
    run "${AWS[@]}" lambda update-function-code --function-name "$name" --zip-file "fileb://$work/new.zip" --query LastModified --output text
    run "${AWS[@]}" lambda wait function-updated --function-name "$name"
    run cp "$new" "$MIRROR/$name/$main"
}

# 1. The two functions
deploy_lambda stockiq-ai-trader lambda_function.py "$HERE/lambda/lambda_function.py" "Gy2rNaAXaIYsQIoSxw9U5OjBOHy2ei6PHr0tAcOZOTU="
deploy_lambda stockiq-ai-chat lambda_function.py "$HERE/chat/lambda_function.py" "LFyuyhd1ivEYAXqSqVkEk+Deq2H+rG9IhzSYdpho+w8="
if [ "$DRY" != "true" ]; then
    say "the live functions answer (the bell for an address with no plan; the chat an empty message, which it refuses without asking the AI model)"
    curl -s -m 60 -X POST "$TRADER_URL" -H 'Content-Type: application/json' -d '{"action":"bell","userId":"nobody-deploy-check@example.com","list":2}'; echo
    curl -s -m 30 -X POST "https://qkxnxpxsk5dxin7pagolehsqyy0iigpe.lambda-url.us-east-1.on.aws/" -H 'Content-Type: application/json' -d '{"message":"","userId":"anon_deploycheck"}'; echo
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
check_web autopilot-bell.js 1a2d14f5ff58ac224d40533ebbb007938f6cd4127177c9ffb15fbb60ee9247e2
run "${AWS[@]}" s3 cp "$WEB/autopilot-bell.js" "s3://$BUCKET/autopilot-bell.js" --cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript"
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /autopilot-bell.js --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
