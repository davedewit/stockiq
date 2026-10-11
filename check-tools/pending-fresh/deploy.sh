#!/bin/bash
# One-off deploy (11 Oct 2026): a browser no longer keeps an old copy of a page or a script. The owner kept seeing the old
# notification bell on the home and analysis pages after it was fixed on the site: his browser held its own copy of each page
# (the site allowed an hour) and of each script (a day), and only the dashboard, which he had reloaded, was current.
#  - Every root page: a browser must ask again each time (max-age=0; CloudFront keeps it an hour and is emptied here).
#  - Every root script and stylesheet, and js/: five minutes in a browser.
#  - 18 pages and theme.js: the bell's script is asked for under an address that changes every hour, not a version number,
#    so a later change to it needs no edit to any page.
# The stock pages are left as they are. deploy-to-s3.sh carries the same rules from now on (edited in the same commit).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#
# Safe to run twice; stops if a website file is not what this was built against.
# Roll back: git checkout the files in ~/VSCODE/website and deploy-to-s3.sh in ~/VSCODE/stockiq, then run the daily deploy.
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
HTML_CACHE="public, max-age=0, s-maxage=3600, must-revalidate"
ASSET_CACHE="public, max-age=300, s-maxage=86400"
NEWS_JS_CACHE="public, max-age=300, s-maxage=3600"
check_web theme.js d740eb5fe98427d5e6326bdb9bc9b3acfa67c23a7498c3e148af597bb3b7cac7
check_web about.html b3d7f540e59957636f4ba50a2d2d245fbd8c12cac10c8c206b792132c996b63c
check_web analysis.html 60238923f7292869b9204abc4866bc52d6d27233617d2474aeede8ce470e5e53
check_web blog.html ca6966f9c91071a116850ca7aa031f254d6f38856facd8bc0aa085911be4f84a
check_web contact.html 673eec8bb6848c9820ab7129b173e3194ada93a37bcd04c6b8e485b9a368d0ac
check_web dashboard.html a837a99ca0801b0890293f8a4d25b442805a1e4bac62c761e752750a44237e3d
check_web data-deletion.html fb99ba88210700464a9250654d9aa09b8ff7e7dd98dc8f0be0f074511b3467c1
check_web faq.html 26153f46c4ba3f7a174c084bbecf139b30f0644d09fcc251627f1a7317a134d0
check_web index.html ec0eda60ad296563cb08f7f8f82c8e5659a94f4907d12d52ddcb4cf0b75ccfa5
check_web investment-research-tools.html f58428f26998b2514f6040551c63a957150cf30e69f0f987d61df7a6abb5c96e
check_web login.html b3875412a104ea292764a34783451cc8040945529442f9b065163ed96ec134d6
check_web news.html 326f9198b1d016473beaa57a911242d6628f297b1cea0375e80b578bbc921f3d
check_web privacy-policy.html 82aabc7bc4b576bbcfe95d3c27d348105f7ff6b740d6b353d549f10ecb9c3204
check_web refunds.html 9db4c5345fd9820028a0425308ed5823b47f198f1af6d7a5dbaf7b4c58a079fc
check_web stock-analysis-guide.html a7adb4daf76258c15a2677941d8b92796723a997b343ec8a4831291c8032f0a8
check_web stock-screener-guide.html ec8621d780b4e4502492436c8c503c452efcff9753da021474c17df8671a6cde
check_web support.html 344908e5333ad680daed069baa789ce2a95a6db0e1bf9f07faebba9f73d4dd65
check_web technical-analysis-guide.html 1eba2165babe8eb0cc97efd32a8895eaf0ebee6c14d080e744aafca24bea37b6
check_web terms.html 07d490a39233d41b6dba72e08b056cf58528bcc93af67cf7038a704bc1f48fc5

say "the changed files, with the new rule for how long a browser may keep them"
run "${AWS[@]}" s3 cp "$WEB/theme.js" "s3://$BUCKET/theme.js" --cache-control "$ASSET_CACHE" --content-type "application/javascript"
for f in about.html analysis.html blog.html contact.html dashboard.html data-deletion.html faq.html index.html investment-research-tools.html login.html news.html privacy-policy.html refunds.html stock-analysis-guide.html stock-screener-guide.html support.html technical-analysis-guide.html terms.html; do
    run "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$HTML_CACHE" --content-type "text/html; charset=utf-8"
done

say "every other page, script and stylesheet: the same rule, their content left exactly as it is (a copy onto itself)"
relabel() {   # <key> <cache rule> <content type>: only if the file is there
    if "${AWS[@]}" s3api head-object --bucket "$BUCKET" --key "$1" >/dev/null 2>&1; then
        run "${AWS[@]}" s3 cp "s3://$BUCKET/$1" "s3://$BUCKET/$1" --metadata-directive REPLACE --cache-control "$2" --content-type "$3" --only-show-errors
    else echo "not on the site, left alone: $1"; fi
}
for f in clear-cache.html signup.html unsubscribe.html; do relabel "$f" "$HTML_CACHE" "text/html; charset=utf-8"; done
for f in ai-chat.js analysis-functions.js auth.js autopilot-bell.js crypto-filter-buttons.js practice-autopilot.js practice-portfolio.js script.js sidebar.js stock-prices.js js/analysis-core.js js/timezone-converter.js; do relabel "$f" "$ASSET_CACHE" "application/javascript"; done
relabel news.js "$NEWS_JS_CACHE" "application/javascript"
for f in styles.css; do relabel "$f" "$ASSET_CACHE" "text/css"; done
run "${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "/*" --query Invalidation.Status --output text

say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
