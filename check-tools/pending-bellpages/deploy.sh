#!/bin/bash
# One-off deploy (11 Oct 2026): the notification bell's autopilot part no longer waits on theme.js's day-long cache. The owner did
# not see it on the home and analysis pages: his browser still had the copy of theme.js from before it fetched the bell's script.
#  - 17 hand-edited pages with a bell: one line after their theme.js tag (between AUTOPILOT_BELL comments) fetches
#    /autopilot-bell.js for signed-in visitors. Nothing else in those pages changes.
#  - autopilot-bell.js (v=2): when the report history is on top, a slim line at the top of the bell's list points down to the
#    autopilot's buys and sells; its click listener cannot be silenced by a page's own handler.
#  - theme.js and dashboard.html: the new version number.
# Website files only.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice; stops if a website file is not what this was built against.
# Roll back: git checkout the files in ~/VSCODE/website and upload them again.
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
check_web autopilot-bell.js 26e206d722c78e4ee97ca74d282d9a6601ad3bd94a90a0ef78ef38c53b236a2f
check_web theme.js 1688e4bc3adf95b783684674ae54c6a9dcbf63c5590ea6167569262f2ec837a5
check_web about.html 3622b561a64b7c7e44380bb6cbc5fea3559d77a75116a695e06449a7ab643222
check_web analysis.html 24bdd60e39766172d5b355832ba6ff667cb7d169ba5a3351b5218e80b8ddb515
check_web blog.html a99bfd8a6c5f0fc6e2fdd89490800ba9bd4301b1f987c9cadfedc86ed335d908
check_web contact.html 1cf45171666aa1bf125318baab28e0997d4a57f613948756d927a4b75d01a34d
check_web dashboard.html d8991e538fdb2f1268cc405b010ddc9d47b13d9a6dfcd9bba0f4c8922463977f
check_web data-deletion.html 97228c4830a903f9da9650e34e6b61ee45c92c555aeb0c777cedd4a62d1e91c6
check_web faq.html 831d130ac165406626a771de4724b6daad8e494acca4431d834802fb7181a543
check_web index.html 1a34d6a9f31bc59ffd36d1dc6bcb0b7ff518261d6231a0ee3b93a353a72d7e95
check_web investment-research-tools.html fe1fdc966e2f9e9a3e2b60a537d559c3f3fc69676fc27a01e382febcdc0863f2
check_web login.html bd82bad55f3aa194d3bb6d92488d7604f4160b4aa3d290a810208a29c77f8afd
check_web news.html f1dadd3b8447b2ab2cb76f8b07ebd477129ae6af439b34d9205cb68cc3f2fd24
check_web privacy-policy.html deec3f1cccd7a2efde165fd4b6b58ae47776fe35f2719c464d7a849bee49b3d8
check_web refunds.html 234ca8ae6f3b3acc644a4d0654ff787a45b95249a162e1a9de1871950a55d111
check_web stock-analysis-guide.html e475842ada089a85b0258a54784dbb3297402de641c84ef96e38028034aa74ba
check_web stock-screener-guide.html b52f963d2db6deaee807e59d12ead67ccbddce768c2f08340252b4634a39f581
check_web support.html 0180df5918787cccd14da8c7a128c91d999281dea3d19204ed0b3747a6603d7e
check_web technical-analysis-guide.html 8e3bf0c6769cd582df0931ce3adc6686072b4df7c0c5a9b4a1babd4eea89aa90
check_web terms.html 68f10fe42450037b3ee663cda149eadc0c85d71ef934705da47e05bc49633fc7
for f in autopilot-bell.js theme.js; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=86400"
done
for f in about.html analysis.html blog.html contact.html dashboard.html data-deletion.html faq.html index.html investment-research-tools.html login.html news.html privacy-policy.html refunds.html stock-analysis-guide.html stock-screener-guide.html support.html technical-analysis-guide.html terms.html; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=3600" --content-type "text/html; charset=utf-8"
done
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /autopilot-bell.js /theme.js /about.html /analysis.html /blog.html /contact.html /dashboard.html /data-deletion.html /faq.html /index.html /investment-research-tools.html /login.html /news.html /privacy-policy.html /refunds.html /stock-analysis-guide.html /stock-screener-guide.html /support.html /technical-analysis-guide.html /terms.html --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
