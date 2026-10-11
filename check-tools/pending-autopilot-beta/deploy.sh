#!/bin/bash
# One-off deploy (11 Oct 2026): the practice portfolio says results in words ("up $144.12", "down $202.60", "level") where
# a mix of plus and minus figures had read like a riddle, and the AI autopilot is labelled Beta wherever it is named
# (panel, dashboard tab, plan cards, home page pricing, FAQ). Website files only.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice; stops if a website file is not what this was built against.
# Roll back: git checkout the five files in ~/VSCODE/website and upload them again.
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
check_web practice-autopilot.js bc2c3aac1c2eded6c53dbff5bff191e2c992348e5afa132c6c3b006fbd21bb23
check_web practice-portfolio.js ad1c1372002e0a9b890d4e3f71f7350d631ab115f800d7984b0beaae88c435ce
check_web dashboard.html        376d4cd1e1016c8963bd14556d16849be99e5f267f37e64a4b34bf657de8d8e3
check_web index.html            127ada45f087534e0dd4b2137d676c5256bfe41fe3016890967b38f0dff0c884
check_web faq.html              30a813bf4fbaed5c0f22f5018b0187419ab2d185828e8182a625b31eb3707c14
for f in practice-autopilot.js practice-portfolio.js; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=86400"
done
for f in dashboard.html index.html faq.html; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=3600" --content-type "text/html; charset=utf-8"
done
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /practice-autopilot.js /practice-portfolio.js /dashboard.html /index.html /faq.html / --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
