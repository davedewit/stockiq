#!/bin/bash
# One-off deploy (11 Oct 2026): the notification bell's list is ONE list, drawn the same on every page that opens one: reports
# and the AI autopilot's buys and sells together, newest first. Until now the autopilot's trades were a group above or below the
# page's own report list; with a report newer than the last trade they sat under seven reports, out of sight, which is why the
# owner saw nothing of them on the home page.
#  - autopilot-bell.js (v=3): draws the whole list; a page's own drawing of its report list gives way to it.
#  - 18 pages and theme.js: the new version number only.
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
check_web autopilot-bell.js 1e2d6e4eac1f14e777bf066d0866f433c1a9d5c3361e1fbed5288cc587a712e1
check_web theme.js 0e91190a9979e4c2d85d4d273c7ac808ba7c13a23f1a3c45a336f013a62a408b
check_web about.html 53162c0c0bec6152e3bd84104367c0b20f782f9155ddecc552df409ae277dd4a
check_web analysis.html 2823c1ce52c228f465d1241b7c0f2aca147115ff52f54b930343131b9ff3604b
check_web blog.html 0369307f2f80038238af80729efb86ad6005cb16a97488af4b2ffbac3a73ba07
check_web contact.html bb19f71b537d7d5d1856a46f48d2ae0ec77098efcd217cdef0059ebba98aa0a4
check_web dashboard.html f3029f6b31f0824bfd567fed768fe1c124fac474ca6b5d770da47495109034ae
check_web data-deletion.html 203e2984ed29a6867f7d7b7824b1115214ce278a7950ffbea14baadb3578bc38
check_web faq.html 2a5d0cd02e470f54cd027ac964e3626a143576084d7a74aab3ba4ff1313ba449
check_web index.html 42ec13cee960c1926313cac9a84dc37f8161982c8892300be157c0783418bcf6
check_web investment-research-tools.html ab8074c30a3bef6da1de645c765ddc924a5e477589b88a18c56481024df0b5d5
check_web login.html 6e42fb01801606fc3f9c977010abb16da24466590a3f9c0c47f6a6931ce8ae8b
check_web news.html 3b8a623d08ca46a73b6f8ad6204c891fdab9bb4a74c0829a68f221c9bb2e60dd
check_web privacy-policy.html 786b89e508a0b1098f3726e7487a8df9593dd1f2a40f561301a81868edaeb482
check_web refunds.html ced9dba479f2eaaa52ea79a6b786c49a8165c99985aca9dda0e95ec727129de0
check_web stock-analysis-guide.html c6979ee195ebfe7adb3367ea0439f51f24137b6ab86f6d13cf0c9b960cc73302
check_web stock-screener-guide.html 57eb04926876a515df29f07b3e334c26937ea9c36371f0a7ff4d1469d0424260
check_web support.html 0510ecaaa61ea198f356c9118eefeec1ab01828db1f600fd4f4c7d69ce2a8435
check_web technical-analysis-guide.html 650e92874f5117e2da7ba533e01a5efd0a03a085dde5adf491a0730d9936bf75
check_web terms.html faf8cdec38dde3a2428f606a1cac1cd29adb81d00be118ced0570b451bd8deb1
for f in autopilot-bell.js theme.js; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=86400"
done
for f in about.html analysis.html blog.html contact.html dashboard.html data-deletion.html faq.html index.html investment-research-tools.html login.html news.html privacy-policy.html refunds.html stock-analysis-guide.html stock-screener-guide.html support.html technical-analysis-guide.html terms.html; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=3600" --content-type "text/html; charset=utf-8"
done
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths /autopilot-bell.js /theme.js /about.html /analysis.html /blog.html /contact.html /dashboard.html /data-deletion.html /faq.html /index.html /investment-research-tools.html /login.html /news.html /privacy-policy.html /refunds.html /stock-analysis-guide.html /stock-screener-guide.html /support.html /technical-analysis-guide.html /terms.html --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
