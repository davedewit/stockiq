#!/bin/bash
# One-off deploy (13 Oct 2026): the Screeners menu's sections are named for what is in them, and the AI chat knows the
# 27 screeners.
#   - 19 pages: in the header's and the phone menu's Screeners list "Asia Markets" becomes "Asia-Pacific Markets"
#     (Australia is in it) and "Other Markets" becomes "Americas Markets" (Canada, Brazil). The links are unchanged
#     (analysis.html?option=5 and 6). On analysis.html also the two sections' headings and the option list, the
#     Australian and UK buttons written like the others, and six markets added as "Coming Soon" (Euro Stoxx 50, Sweden,
#     China, Taiwan, New Zealand, Mexico).
#   - stockiq-ai-chat: its list of screeners (it named ten), the autopilot's five groups and the quick set-ups' Undo.
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: ~/VSCODE/backup/stockiq-ai-chat_before_menus_20261013.zip; the website files from git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
F=stockiq-ai-chat; MIRROR=$ROOT/lambda-sync/$F; BACKUP=/Users/dave/VSCODE/backup; KEEP="$BACKUP/${F}_before_menus_20261013.zip"
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
WAS="Ogr84Q5NISc0OBpyR+I9rOLafnozV9VZRechmUvIoaw="; OLD_FILE=08204406a4b2947b4896bab941b0a1794287220ded3d81d2495745f941f4c56f; NEW_FILE=090bede3b333d114ce91872ce4289c6ceab50ef8731d368f0bf3916e0da67d53
# file : what it was : what it becomes
FILES=(
 "analysis.html:195cd61666ca9704146dd440d47887c760c6b864653fa340e6517123be872c91:f214d39b01edff570a8eb48f7d9569e1673ff9500d3c4abc3480d7bca53abf11"
 "about.html:315dd9f41d0c940db35129fb3fb74955de242d3dc5f1db722b6059001c1c9bae:8df22efcb545e7dc3839dda5bf273aefa04be8bf9bd4b1ce85979c89a761986b"
 "blog.html:b495f03a79159a3e248b0890ffae8abda96a32fa4634c3957053495f7d7781ba:a05767e40dc4728eeafc837757ac649a06a90b044809e8dc91a9a4de48fd459c"
 "contact.html:c387d6caf6a4d1fc3cfa5e5fce038856e2e8b7b90c68f08f003dea7af50e6f73:e001175b8cbe5bdc503f326f288d70c1b7ca2149ee3a1ee3c385e654696f5e6c"
 "dashboard.html:173ea27721ab17af9499d670dd22eee5022538b4fd75ccb3485e59b50b2445ac:519c12fdc6b8be830b070fd2db95de2caf38d8add183eac37d7b3a8f2838ab46"
 "data-deletion.html:b9a8423d2bc5b232a7795d1caba2d56c09c1ddf7dee8034654aa0cb3d18e5906:319078d59aeb3c8a0a4cada66febf2f47c084a415d1436c723ab480266570153"
 "faq.html:dcd9aa17dfce78372b04d2b1861b4ce52e3a30f48ddf0e661c22b97e3b4372ec:e4addb6cab6b33cde0a165f610dfeb2f8bc6d1aef90989320bdbf42757d524df"
 "index.html:d494290d2ba9dc78222e85f6fefe90c3910b0a0a27806a35f8f574b8ebf6cadf:5fcb3652b459460074f490a5dbf1efddfe64a44ffb160318528d641e116e1535"
 "investment-research-tools.html:94f2e55549f8d27c904d44dfe1f591f1759ab7cc2dfe30e8eae132f3c072c48b:39f70ac51d284db8eb7114dc59ea59b766b60d6ee5523a10fbc5a810e2b4e4d1"
 "login.html:520b4a0bff7d1753aaad08e94eb5a4e9d86fedceff52eddcfa93de66e430b57d:720290a7499027a3a4b0dd91b56254356cd560421b643e3cd52d38f9ba61ea1d"
 "news.html:1a95df67f093e0e42acde8b1dcad7db2f49a213a751db35bf3943409afb913ae:58ad4b664a7a90ad77e269619a22e19b543a3a1d48704f3d194bfad80dcc7982"
 "privacy-policy.html:5769cd292b786a7df914551cc80c408a76c573a8f87bc5d50651ab78a4f7b122:b7b9b6a9aa92b1e18c81daedc7f7abe0fdc92164bdd5c1b2746b919baad0edf9"
 "refunds.html:310cd6675896ac3d73cba06c73361a0c41fdde4f6d09bd1bee2cdf1317f7764f:4da20a22137cd541d029da80490a622d720f97435a138ab024bc8515d8592f61"
 "signup.html:59fe6c654d485df7685ec9254bfa31934089fb23f0806e72a459ce82e64ee20c:fd379e5d287a175de92ac626573a964257c969b164c90b2878d2d7710948f210"
 "stock-analysis-guide.html:f6ddd5e9bf1420783153a32d85f790d0fe5c4f47781f2cfdb3b2d781acd88a2b:e604988b408e0425b962f1b759e220ab6fc07995591b95f3cb54d0d3c0a041f1"
 "stock-screener-guide.html:7219619ebeffa47bb487a077b8693b37a1f6576706e8de1680cf33aa931e02dd:0c0720d1c7ec17afbe62e332e62b0011d4480dfd5f645eaf536d4ad68a8f0198"
 "support.html:3dcbb02495f8b1fe84011a30505ad3d2e2303ac2b79366a7ff840422e47f126d:c5e396ebd9d6f31d8ede1d455368ff1063be5f25b78c2fff2c81a4e467b9fc29"
 "technical-analysis-guide.html:69d5f35d07e6dbf476011de198df335b804ba9595493be6f10a0add3eab50aae:cb643096552a93fbab4559a1d8e5e93c5b0ca0f57a42fb1fb9b058dfb193e020"
 "terms.html:c2d17cd082dd9af4709b71037a8131d85c472e532f92369cefa1b0c961f92435:7e9b8a7f4c27ceffe30ff2f6699e2a4fd2dc4863299e9a3fb35ef82e0366c2d1"
)
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
[ "$(filesha "$HERE/chat/lambda_function.py")" = "$NEW_FILE" ] || stop "the staged chat function is not the one that was tested"
python3 -m py_compile "$HERE/chat/lambda_function.py" || stop "the staged chat function does not compile"
curl -s -o "$TMP/live.zip" "$("${AWS[@]}" lambda get-function --function-name "$F" --query Code.Location --output text)"
mkdir -p "$TMP/live"; unzip -q -o "$TMP/live.zip" -d "$TMP/live"
[ "$(unzip -Z1 "$TMP/live.zip" | tr '\n' ' ')" = "lambda_function.py " ] || stop "the package holds other files than lambda_function.py"
if [ "$(filesha "$TMP/live/lambda_function.py")" = "$NEW_FILE" ]; then STATE=new; echo "the chat function already has the new code"
else
    STATE=old
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$WAS" ] && [ "$(filesha "$TMP/live/lambda_function.py")" = "$OLD_FILE" ] || stop "$F has changed on AWS since this was built"
    cmp -s "$TMP/live/lambda_function.py" "$MIRROR/lambda_function.py" || stop "the live chat function is not the same as the local mirror"
    echo "the live chat function is the code this was built from"
fi
OLDN=0; NEWN=0
for row in "${FILES[@]}"; do
    IFS=: read -r f was new <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was checked"
    ! grep -q "Asia Markets\|Other Markets" "$HERE/web/$f" || stop "the staged $f still has an old menu name"
    l="$(filesha "$WEB/$f")"; curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; v="$(filesha "$TMP/live_$f")"
    [ "$l" = "$was" ] || [ "$l" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$v" = "$was" ] || [ "$v" = "$new" ] || stop "the live $f is neither the old nor the new file"
    if [ "$l" = "$new" ] && [ "$v" = "$new" ]; then NEWN=$((NEWN+1)); else OLDN=$((OLDN+1)); fi
done
echo "${#FILES[@]} pages checked: $OLDN to upload, $NEWN already live"

say "$F"
if [ "$STATE" = new ]; then echo "already deployed, skipping"
elif [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package as $KEEP and update the function"
else
    [ -f "$KEEP" ] || cp "$TMP/live.zip" "$KEEP"
    cp "$HERE/chat/lambda_function.py" "$TMP/lambda_function.py"; (cd "$TMP" && zip -q -X new.zip lambda_function.py)
    "${AWS[@]}" lambda update-function-code --function-name "$F" --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name "$F"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$F" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new.zip")" ] || stop "the function does not report the new package"
    cp "$HERE/chat/lambda_function.py" "$MIRROR/lambda_function.py"; echo "live ($(zipsha "$TMP/new.zip")), and the mirror updated"
fi

say "the website"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=0, s-maxage=3600, must-revalidate" --content-type "text/html; charset=utf-8" --only-show-errors
    PATHS+=("/$f*"); echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    BAD=0; for p in "${PATHS[@]}"; do p="${p%\*}"; curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB$p" || { BAD=$((BAD+1)); echo "the live $p is not the file that was uploaded"; }; done
    [ "$BAD" = 0 ] && echo "all ${#PATHS[@]} live pages equal the local files" || stop "$BAD live pages differ from what was uploaded"
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
