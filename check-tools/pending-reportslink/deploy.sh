#!/bin/bash
# One-off deploy (13 Oct 2026): "For the complete screener report, download from your dashboard" under a screener's
# results now opens the dashboard's Reports tab (dashboard.html#reports), where the download is, whichever tab was
# open last. Five links in analysis-functions.js; the dashboard already opens Reports for that address and goes on
# remembering the last tab for a plain visit.
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: git checkout <the commit before> -- analysis-functions.js in website/, and upload it.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"; F=analysis-functions.js
WAS=317e4e43fc49b60a1e4556261ece227d80e6113b55978087a12c8544cf5ae6e0; NEW=9ed44ac08e95d3d2d536f369fa3cce34fbeff3033a13a9a92d880d36c472fe6c
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"
[ "$(filesha "$HERE/web/$F")" = "$NEW" ] || stop "the staged file is not the one that was tested"
node --check "$HERE/web/$F" || stop "the staged script does not parse"
[ "$(grep -c 'href="dashboard.html#reports"' "$HERE/web/$F")" = "5" ] || stop "the staged script does not have the five links"
L="$(filesha "$WEB/$F")"; curl -s -o "$TMP/live" "https://stockiq.tech/$F"; S="$(filesha "$TMP/live")"
[ "$L" = "$WAS" ] || [ "$L" = "$NEW" ] || stop "website/$F has changed since this was built"
[ "$S" = "$WAS" ] || [ "$S" = "$NEW" ] || stop "the live $F is neither the old nor the new file"
echo "$F: local $([ "$L" = "$NEW" ] && echo new || echo old), live $([ "$S" = "$NEW" ] && echo new || echo old)"
if [ "$L" = "$NEW" ] && [ "$S" = "$NEW" ]; then echo "already live"; exit 0; fi
if [ "$DRY" = "true" ]; then echo "(dry run) would copy $F into website/ and upload it"; echo "FINISHED (dry run, nothing changed)"; exit 0; fi
cp "$HERE/web/$F" "$WEB/$F"
"${AWS[@]}" s3 cp "$WEB/$F" "s3://$BUCKET/$F" --cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript" --only-show-errors
INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "/$F*" --query Invalidation.Id --output text)"
"${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
curl -s -o "$TMP/after" "https://stockiq.tech/$F"; cmp -s "$TMP/after" "$WEB/$F" && echo "live /$F equals the local file" || stop "the live file is not the one that was uploaded"
echo "FINISHED"
