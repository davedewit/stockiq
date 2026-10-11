#!/bin/bash
# One-off deploy (11 Oct 2026): the bell's script is asked for beside the page, not at the top of the site's address.
# It was asked for at "/autopilot-bell.js". That is found on stockiq.tech and nowhere else: served from a folder (a local
# preview of ~/VSCODE/website, for one) the script never loaded and the bell showed the page's own list of reports with none
# of the autopilot's trades, on every page, which is what the owner kept reporting. (The dashboard had worked at first because
# its script tag was relative, and stopped when it was given the same absolute address as the other pages.)
#  - 18 pages: s.src='autopilot-bell.js?h=...' (relative).  - theme.js: beside itself.  - autopilot-bell.js (version 7): its
#    links and its look at theme.js are relative to where it was loaded from.
# Website files only; the copies in ~/VSCODE/website are what a local preview serves, so that changes at once.
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
check_web autopilot-bell.js a06579c9830418f16d80c42dadf27aa3ddc0930ea1b1c1de6d2d2fc02a993bc2
check_web theme.js ad5a9264d8758f2ed1e076e4c439edce9fdebff278f2297a29d1f091cfc4ad3c
check_web about.html e13a36d70371713a8102cb3fbead712768e4eaa3374638e22241a21d25b7fe74
check_web analysis.html 9a7aacee9e696bab72d56a95d6f9a763b41e265a894bcdeeaca765421c3284ec
check_web blog.html 0df1c5c49da7e4a466eb28c8da1b1394310e55ac13ffd6c17d94f6e214d6af52
check_web contact.html f685eed0683ab7d13fdc96456aab84cb7d695938066b9dc495da049dd781e989
check_web dashboard.html db74619b8fbc492df58b1e7c3175b7b98e78e0dc4894a3fa9ac48faec889852f
check_web data-deletion.html 2267339d89ced725929fd9aeac1b0ec014d821a6ab6db11447b32f73566c25c0
check_web faq.html cbe675df7cb32e91ec18d01d2aac0e0657e3fb7a5f0e434686f4cda667d5a1f0
check_web index.html cb085bd12244b941a935409dcfc7f6dc4b5b55611ed3b61f1fcf6974d8d2bb96
check_web investment-research-tools.html f7afc53a2396e8b18ebb70c08ace71d91316a7df1097e8619b70b3d166b5f359
check_web login.html 731c431fdb1582f7674115c089df4270b382c86686729cd9083305f79f194a40
check_web news.html 966ff291d0fd15200e250a6bc8856f309e5d1c574c36e3c31dd443ec8b4846b9
check_web privacy-policy.html c3dafd33e47b9076cf2132e623ea5f57960dc4a969e418042ab500fbb8c63b61
check_web refunds.html 8c155799065c1be9650ccae3506866146361ea485c0436fc2a595ba8bd95db0f
check_web stock-analysis-guide.html d316c742606dfa37222a92b8452b45f6e643663c86443df8414a346bf7edb320
check_web stock-screener-guide.html 0880eaf1bc6896487f3670c8a83e0552a13497c35716065cae952deaf03e4698
check_web support.html 8f4de839301930ee11e41d8270b29fb3fe9a8e7c3c7bba437bc49692bac6a10a
check_web technical-analysis-guide.html 6fe180bc709295f695ee5a589972af9b5b2f5103cbacf6b9ed3ec473da49d7f9
check_web terms.html c334472f4d126cbebe3cb107da8d319623af87a06d1565635492926cc9c01d1a
for f in autopilot-bell.js theme.js; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript"
done
for f in about.html analysis.html blog.html contact.html dashboard.html data-deletion.html faq.html index.html investment-research-tools.html login.html news.html privacy-policy.html refunds.html stock-analysis-guide.html stock-screener-guide.html support.html technical-analysis-guide.html terms.html; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=0, s-maxage=3600, must-revalidate" --content-type "text/html; charset=utf-8"
done
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /autopilot-bell.js /theme.js /about.html /analysis.html /blog.html /contact.html /dashboard.html /data-deletion.html /faq.html /index.html /investment-research-tools.html /login.html /news.html /privacy-policy.html /refunds.html /stock-analysis-guide.html /stock-screener-guide.html /support.html /technical-analysis-guide.html /terms.html --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
