#!/bin/bash
# Shared by the one-off Lambda deploys (24 Oct 2026; until then each check-tools/pending-<name>/deploy.sh carried 80 lines of its own).
# A pending folder's deploy.sh is three lines:
#   FUNCS="<function>:<staged dir>:<file>:<CodeSha256 it has now>:<sha256 of its file now>:<sha256 of the staged file>:<rollback name> ..." \
#     exec bash /Users/dave/VSCODE/stockiq/check-tools/lambda_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
# It checks that the staged file is the tested one and compiles, that the live function is the code the change was built from and
# equals the local mirror (lambda-sync/), keeps the live package as ~/VSCODE/backup/<function>_<rollback name>.zip, updates the code,
# confirms AWS reports the new package and copies the file into the mirror. Safe to run twice. DRY_RUN=true previews.
# The package's other files, if any, are kept as they are live. Away from :10 and :40 past the hour (the autopilot's scheduled runs).
set -euo pipefail
HERE="$1"; ROOT=/Users/dave/VSCODE/stockiq; AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup
DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
zipsha() { openssl dgst -sha256 -binary "$1" | openssl base64; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running"; fi
M=$((10#$(date -u +%M) % 30)); if [ "$DRY" != "true" ] && [ "$M" -ge 9 ] && [ "$M" -le 13 ]; then stop "the autopilot's scheduled run is at :10 and :40; run this a few minutes later"; fi
for row in $FUNCS; do
    IFS=: read -r f dir fn was old new keep <<< "$row"
    [ "$(filesha "$HERE/$dir/$fn")" = "$new" ] || stop "the staged $f is not the one that was tested"
    python3 -m py_compile "$HERE/$dir/$fn" || stop "the staged $f does not compile"
    curl -s -o "$TMP/$f.zip" "$("${AWS[@]}" lambda get-function --function-name "$f" --query Code.Location --output text)"
    mkdir -p "$TMP/$f"; unzip -q -o "$TMP/$f.zip" -d "$TMP/$f"
    unzip -Z1 "$TMP/$f.zip" | grep -qx "$fn" || stop "the package of $f holds no $fn"
    if [ "$(filesha "$TMP/$f/$fn")" = "$new" ]; then echo "$f: already has the new code"; continue; fi
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$f" --query CodeSha256 --output text)" = "$was" ] && [ "$(filesha "$TMP/$f/$fn")" = "$old" ] || stop "$f has changed on AWS since this was built"
    cmp -s "$TMP/$f/$fn" "$ROOT/lambda-sync/$f/$fn" || stop "the live $f is not the same as the local mirror"
    if [ "$DRY" = "true" ]; then echo "(dry run) $f: would keep the live package as $BACKUP/${f}_$keep.zip and update it"; continue; fi
    [ -f "$BACKUP/${f}_$keep.zip" ] || cp "$TMP/$f.zip" "$BACKUP/${f}_$keep.zip"
    # the package as it is live, with only <file> replaced (25 Oct 2026: a package may hold other files, which are kept as they are)
    cp -R "$TMP/$f" "$TMP/new_$f"; cp "$HERE/$dir/$fn" "$TMP/new_$f/$fn"; (cd "$TMP/new_$f" && zip -q -X -r "../new_$f.zip" .)
    "${AWS[@]}" lambda update-function-code --function-name "$f" --zip-file "fileb://$TMP/new_$f.zip" --query LastModified --output text >/dev/null
    "${AWS[@]}" lambda wait function-updated --function-name "$f"
    [ "$("${AWS[@]}" lambda get-function-configuration --function-name "$f" --query CodeSha256 --output text)" = "$(zipsha "$TMP/new_$f.zip")" ] || stop "$f does not report the new package"
    cp "$HERE/$dir/$fn" "$ROOT/lambda-sync/$f/$fn"; echo "$f: live ($(zipsha "$TMP/new_$f.zip")), mirror updated, rollback $BACKUP/${f}_$keep.zip"
done
echo FINISHED
