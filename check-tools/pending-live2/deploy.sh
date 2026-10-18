#!/bin/bash
# One-off deploy (18 Oct 2026): ticker-data-fetcher asks for five-minute prices (a fifth of the data, the same current price) and
# gets 512 MB of memory (it had 128: 26 symbols took 7.6 s on Lambda, 0.6 s on the Mac). Lambda bills memory x time, so a call
# that finishes in about a second at 512 MB costs less than 7.6 s at 128 MB.
#   Preview: DRY_RUN=true bash deploy.sh    Deploy: bash deploy.sh
# Roll back: ~/VSCODE/backup/ticker-data-fetcher_before_live2_20261018.zip, and --memory-size 128.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; F=ticker-data-fetcher; FILE=lambda-ticker-data.py
AWS=(aws --profile default --region us-east-1); BACKUP=/Users/dave/VSCODE/backup; MIRROR=/Users/dave/VSCODE/stockiq/lambda-sync/$F
WAS=uhm8WRpQIHbeOW2XY3SHFXn+x+88q8XUf+LGiXpxCa8=; OLD=9d157d6f3988cef3bc242c5ffd501ea8aa1f43cbbc62ae9f83905652fd023795; NEW=4bc7bf46ffa1d73ef8e73196faecf47bfafd0870664000b1ebea28029bff87c6; DRY="${DRY_RUN:-false}"; TMP="$(mktemp -d)"
stop() { printf '\nSTOPPED: %s\nNothing further was changed.\n' "$*"; exit 1; }
filesha() { shasum -a 256 "$1" | cut -d' ' -f1; }
[ "$DRY" = "true" ] && echo "DRY RUN: nothing will be changed"
[ "$(filesha "$HERE/lambda/$FILE")" = "$NEW" ] || stop "the staged file is not the one that was tested"
python3 -m py_compile "$HERE/lambda/$FILE" || stop "the staged file does not compile"
curl -s -o "$TMP/live.zip" "$("${AWS[@]}" lambda get-function --function-name $F --query Code.Location --output text)"
unzip -q -o "$TMP/live.zip" -d "$TMP/live"
if [ "$(filesha "$TMP/live/$FILE")" = "$NEW" ]; then echo "$F already has the new code"
else
  [ "$("${AWS[@]}" lambda get-function-configuration --function-name $F --query CodeSha256 --output text)" = "$WAS" ] && [ "$(filesha "$TMP/live/$FILE")" = "$OLD" ] || stop "$F has changed on AWS since this was built"
  if [ "$DRY" = "true" ]; then echo "(dry run) would keep the live package and update the code"
  else
    [ -f "$BACKUP/${F}_before_live2_20261018.zip" ] || cp "$TMP/live.zip" "$BACKUP/${F}_before_live2_20261018.zip"
    mkdir -p "$TMP/new"; cp "$HERE/lambda/$FILE" "$TMP/new/$FILE"; (cd "$TMP/new" && zip -q -X ../new.zip $FILE)
    "${AWS[@]}" lambda update-function-code --function-name $F --zip-file "fileb://$TMP/new.zip" --query LastModified --output text
    "${AWS[@]}" lambda wait function-updated --function-name $F
    cp "$HERE/lambda/$FILE" "$MIRROR/$FILE"; echo "$F: new code live, mirror updated"
  fi
fi
MEM=$("${AWS[@]}" lambda get-function-configuration --function-name $F --query MemorySize --output text)
if [ "$MEM" = "512" ]; then echo "memory already 512 MB"
elif [ "$DRY" = "true" ]; then echo "(dry run) would set the memory from $MEM to 512 MB"
else "${AWS[@]}" lambda update-function-configuration --function-name $F --memory-size 512 --query MemorySize --output text; "${AWS[@]}" lambda wait function-updated --function-name $F; fi
echo; echo "== FINISHED$([ "$DRY" = "true" ] && echo ' (dry run, nothing changed)')"
