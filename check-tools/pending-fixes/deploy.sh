#!/bin/bash
# One-off deploy (18 Oct 2026): the nightly site check's findings fixed, at the owner's word ("sure fix the issues"). Website only.
#   - a description for search results on nine pages that had none (analysis, contact, data deletion, sign in, privacy, refunds,
#     sign up, terms, unsubscribe); the unsubscribe page is kept out of search (noindex) and has its canonical address
#   - the home page's four index cards: their small charts are today's real line (live-market.js version 3), not a fixed "up" or
#     "down" shape; their figures are kept fresh like the side panel's; a dash instead of "Loading..." until the figures are in;
#     the side panel's "Loading..." is the site's spinner
#   - sidebar.js emptied: an old copy of the side panel's code with charts from random numbers, run by no page (the stock pages
#     ask for it and use nothing in it)
#   - the four guides each link to eight real stock pages
#   Preview: DRY_RUN=true bash deploy.sh    Deploy: bash deploy.sh
# Roll back: the website files from git (website commit before this one), uploaded the same way.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
# file : what it was : what it becomes : type : how long a copy may be kept
FILES=(
 "live-market.js:07f470e87538123690f0e219584436f7884061be4808854d5cdb9af4e04c8d39:04d908f221ff10b9e7143866a43515c287ea88a697c68e0530b6334c76fd08fa:application/javascript:public, max-age=300, s-maxage=86400"
 "sidebar.js:4d9200a8de71baf842c6deeaeae116fd245edfc89d51494e376687b7a3f41c6b:dca752afbd54d0894c687fe59ea35dc762cbec3f6ecaa78b86ec698221d4b2a3:application/javascript:public, max-age=300, s-maxage=86400"
 "analysis.html:54fad8753604817c315c3e1e0f759d1c0c20c65d52a747ff3fd70a6dafa3c551:e5127248a90637621921f50b45d4f122ba5092fe049ae7493aad77add621fd58:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "contact.html:e001175b8cbe5bdc503f326f288d70c1b7ca2149ee3a1ee3c385e654696f5e6c:2b279daf256023e7f8e2de72d790f7c0eac89fd2748e86d89d623da1d385afde:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "data-deletion.html:319078d59aeb3c8a0a4cada66febf2f47c084a415d1436c723ab480266570153:654e456b5fa63bd272ac61c89f17a9056dca0732bc64b8662c8f8089f2c51604:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "investment-research-tools.html:52fab6954494cf1007199546b99b2bc4d3ce3bb805eea726c71082b5c265d5f3:05ed7202d9f15daee8f88bfb9036a5e5240402203ced11c9abaec9a029f15bc4:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "login.html:720290a7499027a3a4b0dd91b56254356cd560421b643e3cd52d38f9ba61ea1d:8d99f6f2ab2202bf99870f69316931021b633723e783bcbdabfa87c285ee59da:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "privacy-policy.html:b7b9b6a9aa92b1e18c81daedc7f7abe0fdc92164bdd5c1b2746b919baad0edf9:c6499e75120e1f074c1c25a13f683778f7f6893ecb8139c5469fdb9c243ee442:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "refunds.html:4da20a22137cd541d029da80490a622d720f97435a138ab024bc8515d8592f61:163d8e14a721da4d7d9a35601d357d3f7a73887785bf279ea0c4cdd00e45845d:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "signup.html:fd379e5d287a175de92ac626573a964257c969b164c90b2878d2d7710948f210:fd4e91c0818cf692cc296247a03f794d24bc6b8d59ede2ad44ca20a0bd67a404:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "stock-analysis-guide.html:b44feb0d88da3abe1516afbbfd5c536253fbbc95cbd6eb1732f267201e3a3e80:3b024a32c356506389564797990263cd436ec361d3cae12347efe7d5c878054c:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "stock-screener-guide.html:3f25d690cbba003db81304d572c4b79d229f6352431c8813b52c0291b79f7f2a:028dda9d5c4303997369d3e09a27379cc7490fe6ae5a080e46252dec8d6e1e1c:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "technical-analysis-guide.html:cb643096552a93fbab4559a1d8e5e93c5b0ca0f57a42fb1fb9b058dfb193e020:c1bafd6e3756554c213d1e404fe347e5d98e5a0dd5e6f2067580a9b795df26e8:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "terms.html:7e9b8a7f4c27ceffe30ff2f6699e2a4fd2dc4863299e9a3fb35ef82e0366c2d1:20bb045b43c1220c0360d4144100c5cf01f50fc1dd82022712a8275d4377f220:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "unsubscribe.html:9668787fd95a8410801a4eea9538ec34631943f9a5237e398bbb4ac3b11be71e:8ff4a6204546c13d7ec141948375d87c8d164a5abfdbb43372546cdaaab4afe8:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "index.html:f12e766f31c4358f23fedc415fa86b33e93dee5ab0381344e2e33f9e4849cb8d:ed056ed31e592560b1b6e0ade8d380a76b767c09c49fb7de50e54c0fad469bdc:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
)
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
M=$((10#$(date -u +%M) % 30)); if [ "$DRY" != "true" ] && { [ "$M" -ge 9 ] && [ "$M" -le 13 ]; }; then stop "the autopilot's scheduled run is at :10 and :40 past the hour; run this a few minutes later"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
for js in live-market.js sidebar.js; do node --check "$HERE/web/$js" || stop "the staged $js does not parse"; done
grep -q "var VERSION = 3" "$HERE/web/live-market.js" || stop "the staged live-market.js is not version 3"
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    l="$([ -f "$WEB/$f" ] && filesha "$WEB/$f" || echo none)"; code=$(curl -s -o "$TMP/live_$f" -w '%{http_code}' "https://stockiq.tech/$f"); v="$([ "$code" = 200 ] && filesha "$TMP/live_$f" || echo none)"; echo "$v" > "$TMP/sha_$f"
    [ "$l" = "$was" ] || [ "$l" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$v" = "$was" ] || [ "$v" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$l" = "$new" ] && echo new || echo old), live $([ "$v" = "$new" ] && echo new || echo old)"
done

say "the website (the scripts first, then the pages)"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(cat "$TMP/sha_$f")" = "$new" ] && [ -f "$WEB/$f" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    case "$f" in *.js) PATHS+=("/$f*");; *) PATHS+=("/$f");; esac; echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for row in "${FILES[@]}"; do IFS=: read -r p _r <<< "$row"; p="/$p"; curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB${p%%\?*}" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
