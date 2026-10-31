#!/bin/bash
# Shared by the one-off website deploys (check-tools/pending-<name>/deploy.sh calls it): uploads the staged files in <folder>/web,
# after checking each is the tested one (its fingerprint) and that the local copy has not changed since the change was built.
#   ROWS="file:sha256 it was:sha256 it becomes ..."  bash web_deploy.sh <folder>      (DRY_RUN=true to preview; "none" for a new file)
# Scripts are kept 5 minutes by browsers, pages are asked for again every time (site-overview.md, section 5). Roll back: git.
set -euo pipefail
HERE="$1"; WEB=/Users/dave/VSCODE/website; AWS=(aws --profile default --region us-east-1)
BUCKET=stockiq-final-websitebucket-vqekic7enf9h; DIST=EHXV50CPHY07R; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then stop "the daily deploy is running"; fi
for row in $ROWS; do IFS=: read -r f was new <<< "$row"
  case "$f" in *.js) node --check "$HERE/web/$f" || stop "the staged $f does not parse";; esac
  [ "$(sha "$HERE/web/$f")" = "$new" ] || stop "the staged $f is not the one that was tested"
  if [ "$was" = "none" ]; then [ ! -e "$WEB/$f" ] || [ "$(sha "$WEB/$f")" = "$new" ] || stop "website/$f exists already (a new file was expected)"
  else l="$(sha "$WEB/$f")"; [ "$l" = "$was" ] || [ "$l" = "$new" ] || stop "website/$f has changed since this was built"; fi
done
# the site's checks on the staged files (pre_deploy.py), once per set of files: the dry run runs them, the real run trusts its stamp.
# SKIP_CHECKS="<the reason>" only for an emergency, and the reason is printed.
STAMP="$(printf '%s\n' $ROWS | shasum | cut -d' ' -f1)"
if [ -n "${SKIP_CHECKS:-}" ]; then echo "pre-deploy checks SKIPPED: $SKIP_CHECKS"
elif [ "$(cat "$HERE/.checked" 2>/dev/null)" != "$STAMP" ]; then
  /opt/homebrew/bin/python3 "$(dirname "$0")/pre_deploy.py" "$HERE" $(for r in $ROWS; do printf '%s ' "${r%%:*}"; done) || stop "the pre-deploy checks failed (above)"
  echo "$STAMP" > "$HERE/.checked"
else echo "pre-deploy checks: passed on the dry run for these same files"; fi
[ "$DRY" = "true" ] && { echo "(dry run) would upload: $(for r in $ROWS; do printf '%s ' "${r%%:*}"; done)"; exit 0; }
PATHS=()
for row in $ROWS; do IFS=: read -r f was new <<< "$row"
  cp "$HERE/web/$f" "$WEB/$f"
  case "$f" in *.js) "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=300, s-maxage=86400" --content-type application/javascript --only-show-errors; PATHS+=("/$f*");;
    *.css) "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=300, s-maxage=86400" --content-type "text/css" --only-show-errors; PATHS+=("/$f*");;
    *.txt) "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=0, s-maxage=3600, must-revalidate" --content-type "text/plain; charset=utf-8" --only-show-errors; PATHS+=("/$f");;
    *.xml) "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=0, s-maxage=3600, must-revalidate" --content-type "application/xml" --only-show-errors; PATHS+=("/$f");;
    *) "${AWS[@]}" s3 cp "$WEB/$f" "s3://$BUCKET/$f" --cache-control "public, max-age=0, s-maxage=3600, must-revalidate" --content-type "text/html; charset=utf-8" --only-show-errors; PATHS+=("/$f");; esac
done
# AWS gives 1,000 cleared paths a month free, then $0.005 a path ("/*" counts as one): one path per file cost $0.39 on 25 Oct 2026.
[ "${#PATHS[@]}" -gt 1 ] && PATHS=("/*")
INV="$("${AWS[@]}" cloudfront create-invalidation --distribution-id "$DIST" --paths "${PATHS[@]}" --query Invalidation.Id --output text)"
"${AWS[@]}" cloudfront wait invalidation-completed --distribution-id "$DIST" --id "$INV"
for row in $ROWS; do IFS=: read -r f was new <<< "$row"; curl -s -o "$TMP/after" "https://stockiq.tech/$f"; cmp -s "$TMP/after" "$WEB/$f" && echo "live $f equals the local file" || stop "the live $f is not the uploaded file"; done
echo FINISHED
