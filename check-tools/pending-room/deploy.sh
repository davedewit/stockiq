#!/bin/bash
# One-off deploy (13 Oct 2026): a page starts the same distance under the header whether the strip across the top is
# showing or not (the owner: "on the dashboard the 'your dashboard' is lower down when the banner isn't showing").
#   - dashboard.html: for a paying visitor (no strip) the page left room for the strip all the same: 41px of empty
#     space above "Your Dashboard" on a desktop. Also the room left when the page scrolls to its plans follows the header.
#   - styles.css: on stock pages it was the other way round (the title right under the bar when the strip shows): one rule.
#   - signup.html: for a paying visitor the menu bar hung 41px below the top with nothing above it.
# Measured before and after with check-tools/header_room_check.js. Phones are unchanged (they never have the strip).
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
# Roll back: the three files from git (website repo).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=/Users/dave/VSCODE/stockiq; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
FILES=(
 "styles.css:d6493ce17b8d988b5d81ef231e4e1ac95e70b2d04b357dcf186f2c91e63553b9:82d85fc4139c980ce8fa545eaab716bb350c1dbcd193109bbf030440f537db93:text/css:public, max-age=300, s-maxage=86400"
 "dashboard.html:72cb5b0dd16c67f14bed091c41eb3544b7598f1a533b42d61ca3acc420f33e6b:173ea27721ab17af9499d670dd22eee5022538b4fd75ccb3485e59b50b2445ac:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
 "signup.html:353c7b6d4eb1da2c1a82c2c9f8655571fa232160852e1adb26d43d2f76370eb2:59fe6c654d485df7685ec9254bfa31934089fb23f0806e72a459ce82e64ee20c:text/html; charset=utf-8:public, max-age=0, s-maxage=3600, must-revalidate"
)
say()  { printf '\n== %s\n' "$*"; }
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running; try again when it has finished"; fi
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"

say "checks before anything is changed"
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    [ "$(filesha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
    local_sha="$(filesha "$WEB/$f")"; curl -s -o "$TMP/live_$f" "https://stockiq.tech/$f"; live_sha="$(filesha "$TMP/live_$f")"
    [ "$local_sha" = "$was" ] || [ "$local_sha" = "$new" ] || stop "website/$f has changed since this was built"
    [ "$live_sha" = "$was" ] || [ "$live_sha" = "$new" ] || stop "the live $f is neither the old nor the new file"
    echo "$f: local $([ "$local_sha" = "$new" ] && echo new || echo old), live $([ "$live_sha" = "$new" ] && echo new || echo old)"
done
grep -q "setProperty('--body-padding', window.innerWidth > 768 ? '64px' : '105px')" "$HERE/web/dashboard.html" || stop "the staged dashboard does not carry the change"
grep -q 'main:has(> div > #live-ticker)' "$HERE/web/styles.css" || stop "the staged stylesheet does not carry the stock pages' rule"
for f in dashboard.html:7 signup.html:4 styles.css:8; do n="${f##*:}"; f="${f%%:*}"; [ "$(filesha "$WEB/$f")" = "$(filesha "$HERE/web/$f")" ] || [ "$(diff "$WEB/$f" "$HERE/web/$f" | grep -c '^[<>]')" = "$n" ] || stop "the staged $f differs from the site's in more than this change"; done
python3 - "$HERE/web/dashboard.html" "$HERE/web/signup.html" <<'PY' || stop "an inline script of a staged page does not parse"
import re, subprocess, sys, tempfile, os
for f in sys.argv[1:]:
    for m in re.finditer(r'<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>', open(f, encoding='utf-8').read(), re.S):
        if 'json' in m.group(1): continue
        t = tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8'); t.write(m.group(2)); t.close()
        r = subprocess.run(['node', '--check', t.name], capture_output=True, text=True); os.unlink(t.name)
        if r.returncode: print(f, r.stderr[:300]); sys.exit(1)
PY
WEB="$HERE/web" node "$ROOT/check-tools/header_room_check.js" dashboard.html signup.html stocks/AAPL.html index.html analysis.html | tail -1 | grep -q "ALL PASS" || stop "the staged pages do not start the same distance under the header for every kind of visitor"

say "the website: the stylesheet first, then the two pages"
PATHS=()
for row in "${FILES[@]}"; do
    IFS=: read -r f was new ctype cache <<< "$row"
    if [ "$(filesha "$TMP/live_$f")" = "$new" ] && [ "$(filesha "$WEB/$f")" = "$new" ]; then echo "$f: already live"; continue; fi
    if [ "$DRY" = "true" ]; then echo "(dry run) would copy $f into website/ and upload it ($ctype; $cache)"; continue; fi
    cp "$HERE/web/$f" "$WEB/$f"
    "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "$cache" --content-type "$ctype" --only-show-errors
    PATHS+=("/$f*"); echo "$f: uploaded"
done
if [ ${#PATHS[@]} -gt 0 ]; then
    INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
    "${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
    for p in "${PATHS[@]}"; do p="${p%\*}"; curl -s -o "$TMP/after" "https://stockiq.tech$p"; cmp -s "$TMP/after" "$WEB$p" && echo "live $p equals the local file" || stop "the live $p is not the file that was uploaded"; done
fi
say "FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
