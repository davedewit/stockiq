#!/bin/bash
# One-off deploy (11 Oct 2026): the dashboard's tabs, practice portfolio and AI autopilot (Beta) on a phone. The three tabs
# share the width (the third was half hidden); the holdings, sold and progress tables become cards with each figure on its
# own labelled line (they were 730-740px wide in a 308px box); the breakdown's headings wrap; the buy row, the trailing-stop
# menu and the main buttons fit the width. Nothing changes at desktop width.
# Website files only (practice-portfolio.js, practice-autopilot.js, dashboard.html).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice; stops if a website file is not what this was built against.
# Roll back: git checkout the three files in ~/VSCODE/website and upload them again.
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
check_web practice-portfolio.js 1481a9b94beb73509675b076cd840639ee11900e79624583335f6ce0c26a62e1
check_web practice-autopilot.js e7690b79175338fb4b3dab7ef04ea791d15c6041af9c392b2a4f9683d2742131
check_web dashboard.html        07c2d015f7a7309e2dab9c34ce566932266ad44b37e4b691b91bbc6bb641edc5
run "${AWS[@]}" s3 cp "$WEB/practice-portfolio.js" "s3://$BUCKET/practice-portfolio.js" --cache-control "public, max-age=86400"
run "${AWS[@]}" s3 cp "$WEB/practice-autopilot.js" "s3://$BUCKET/practice-autopilot.js" --cache-control "public, max-age=86400"
run "${AWS[@]}" s3 cp "$WEB/dashboard.html" "s3://$BUCKET/dashboard.html" --cache-control "public, max-age=3600" --content-type "text/html; charset=utf-8"
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /practice-portfolio.js /practice-autopilot.js /dashboard.html --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
