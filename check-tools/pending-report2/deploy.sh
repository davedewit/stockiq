#!/bin/bash
# One-off deploy (11 Oct 2026): autopilot-bell.js version 6. Whatever a browser has stored as its list of unread reports, the
# bell's list is still drawn (a stored value that is not a list made drawing fail without a word, leaving the page's own list),
# and a fault while drawing is included in the report the script sends. Website file only.
#   Preview: DRY_RUN=true bash deploy.sh      Deploy: bash deploy.sh      Roll back: git checkout autopilot-bell.js and upload it.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AWS=(aws --profile default --region us-east-1)
WEB=/Users/dave/VSCODE/website
BUCKET=stockiq-final-websitebucket-vqekic7enf9h
DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"

say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
run()  { if [ "$DRY" = "true" ]; then echo "(dryrun) $*"; else "$@"; fi; }

# the daily deploy, by its process name only (matching the whole command line would find this script's own text)
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "website files"
check_web() {   # <file> <sha256 of the version this was built against>
    local f="$1" expected="$2" have
    if cmp -s "$WEB/$f" "$HERE/web/$f"; then echo "$f: already copied"; return 0; fi
    have="$(shasum -a 256 "$WEB/$f" | cut -d' ' -f1)"
    [ "$have" = "$expected" ] || stop "$WEB/$f has changed since this was built"
    run cp "$HERE/web/$f" "$WEB/$f"
}
check_web autopilot-bell.js 9a6f65370b4564c2b72bc3e911c7f08e36c9ebcb4fb0149f26e48ba3a6983d80
run "${AWS[@]}" s3 cp "$WEB/autopilot-bell.js" "s3://$BUCKET/autopilot-bell.js" --cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript"
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /autopilot-bell.js --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
