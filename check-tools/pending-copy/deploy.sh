#!/bin/bash
# One-off deploy (13 Oct 2026): the site's wording brought up to date, at the owner's word ("you can update it however
# you like… would love an update of the site as alot has changed on the AI side").
# The home page says what the site does now (reports with every point of the score explained, 15 screeners, signals,
# the crypto screener, the AI chat, the practice portfolio, the AI autopilot (Beta), the dashboard) and what it is
# not; the claims that could not be stood behind are gone from it, the FAQ, the four guides and the contact page
# ("institutional-grade", "real-time", "2000+ stocks in seconds", the table against Bloomberg and Morningstar). The
# strip across the top has one new wording for each kind of visitor on the four pages that carry it.
# Words only: no script logic changes (the strip's two sentences sit inside each page's own small script).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# To go back: git revert the commit in website/ and upload the same files.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : what it was : what it becomes
FILES=(
 "index.html:daeec05a28104c0e137ad340da2f56fabcfe529f779dfc2383c370ecae58e42f:50c1c387520a21b39f99917b64db68a8c1e49961b5d3de5a92ffbbedb34cced2"
 "analysis.html:042cf9d0dd439540d77ee2c54bc6081d6d0cfec24ca672c2189c8c3fb0aea60e:0a647633748ec85f22a34f5c4c6c67118c07fcf438a8ec96002cdb5039314008"
 "dashboard.html:5f9b9b27945bce8084d75b3566a4b6950d7ad092f004394293d300118ae02d2a:1dbb2a18c3a81e42f6ae1e41be76969dac84f03741748fdb2caa80cbb194438c"
 "signup.html:d6f43fcb96c6bbf8985782af441c8e334336d7bf9d330fa3e9104ee16bd77a45:353c7b6d4eb1da2c1a82c2c9f8655571fa232160852e1adb26d43d2f76370eb2"
 "faq.html:ebb52e64b087304537b779009241796d3c2c804f2f85013570316749db4491d6:cfeda6c8ac60496890408e0e8186d196b248c592d37a56a9d97a4e030069c482"
 "about.html:636c1eefece30004c26e196abca92086287b41b52e6c95536b4ead26e0370378:4006ea82f8a5063dda1a95367adf7dd86c89e92145e1195d4d4aa5ddeb7fc4be"
 "contact.html:fde21bbefb79dbeb452df701c8b56bf944e885bf503b042ece8a551aa8c8d4de:c387d6caf6a4d1fc3cfa5e5fce038856e2e8b7b90c68f08f003dea7af50e6f73"
 "technical-analysis-guide.html:8d889697e04f2c007616270cb8f2cc2468d423f9d76f38792b1af05086391888:69d5f35d07e6dbf476011de198df335b804ba9595493be6f10a0add3eab50aae"
 "stock-screener-guide.html:9bdda5c14b59b0deb3143894ae6ffa2e6fa0f42c0817cee8c64bf7f390f458da:89aa18d31b4dbeae0414de6b0246824348dcb5a990606bc729da25706c3c6464"
 "stock-analysis-guide.html:138246348ca42b728f3bd15a19ec5e822ea9b30dd75a631e2d6b7945974f6fee:f6ddd5e9bf1420783153a32d85f790d0fe5c4f47781f2cfdb3b2d781acd88a2b"
 "investment-research-tools.html:e1692a200da1a813e9af8838e92d0273545b9f8ad4d371e3b5e039c2908fbcf5:24d8eb70d3d17c58c86f6324402e66ca3457a145e4c67e3cfe89e5fbee4c8ebb"
)
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
for row in "${FILES[@]}"; do
    IFS=: read -r f was new <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    local_sha="$(filesha "$WEB/$f")"; curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; live_sha="$(filesha "$TMP/live_$f")"
    [ "$local_sha" = "$was" ] || [ "$local_sha" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$live_sha" = "$was" ] || [ "$live_sha" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$local_sha" = "$new" ] && echo new || echo old), live $([ "$live_sha" = "$new" ] && echo new || echo old)"
done
if grep -l -i "institutional-grade\|2000+ stocks\|600+ parallel\|Bloomberg \$24,000" "$HERE"/web/index.html "$HERE"/web/faq.html "$HERE"/web/contact.html; then stop "a staged page still carries one of the old claims"; fi
grep -q 'id="pricing"' "$HERE/web/index.html" && grep -q 'id="features"' "$HERE/web/index.html" && grep -q 'mobile-sidebar.js?v=2' "$HERE/web/index.html" || stop "the staged home page has lost a section or its sidebar script"
grep -q 'practice-portfolio.js?v=33' "$HERE/web/dashboard.html" || stop "the staged dashboard does not ask for the current portfolio script"

say "the website: eleven pages (words only)"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=0, s-maxage=3600, must-revalidate" --content-type "text/html; charset=utf-8" --only-show-errors
    PATHS+=("/$f"); echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" "/" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for p in "${PATHS[@]}"; do curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB$p" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
    curl -s -o "$TMP/root" "https://stockiq.tech/"; cmp -s "$TMP/root" "$WEB/index.html" && echo "live / equals the local home page" || echo "NOTE: https://stockiq.tech/ does not yet equal index.html (look again in a minute)"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
