#!/bin/bash
# One-off deploy: corrected "Top 10 Performance" (🎯) on the dashboard. Built and tested 10 Oct 2026.
# What and why: .kiro/steering/site-overview.md, section 11.
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: cd ~/VSCODE/website && git checkout dashboard.html, then upload it the same way.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
AWS=(aws --profile default --region us-east-1)
WEB=/Users/dave/VSCODE/website
BUCKET=stockiq-final-websitebucket-vqekic7enf9h
DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"
run()  { if [ "$DRY" = "true" ]; then echo "(dryrun) $*"; else "$@"; fi; }
stop() { printf '\nSTOPPED: %s\nNothing was changed.\n' "$*"; exit 1; }
if pgrep -f "deploy-to-s3.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"
if cmp -s "$WEB/dashboard.html" "$HERE/web/dashboard.html"; then
    echo "dashboard.html: already copied"
else
    have="$(shasum -a 256 "$WEB/dashboard.html" | cut -d' ' -f1)"
    [ "$have" = "f8a55948c75b017057f83971997798467fa7f7ae2c6de64c1170020179ecef3f" ] || stop "$WEB/dashboard.html has changed since this fix was built"
    run cp "$HERE/web/dashboard.html" "$WEB/dashboard.html"
fi
run "${AWS[@]}" s3 cp "$WEB/dashboard.html" "s3://$BUCKET/dashboard.html" --cache-control "public, max-age=3600" --content-type "text/html; charset=utf-8"
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /dashboard.html --query Invalidation.Status --output text
printf '\n== FINISHED%s\n' "$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
