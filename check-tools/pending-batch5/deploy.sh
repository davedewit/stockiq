#!/bin/bash
# Creates the workers of the last four screeners from the one share-screener package (workers/create_group.py):
# Switzerland SMI (2), India Sensex (3), South Korea KOSPI 200 (21), Brazil Bovespa (8). Each group's addresses go to
# urls.txt in its own folder.
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Create:                      bash deploy.sh        (safe to run twice: a function that exists is passed over)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
for pair in "stockiq-europe-4-7-worker:smi" "stockiq-asia-5-6-worker:sensex" "stockiq-asia-5-7-worker:kospi200" "stockiq-americas-6-2-worker:bovespa"; do
    mkdir -p "$HERE/${pair##*:}"
    /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/create_group.py "${pair%%:*}" "$HERE/${pair##*:}"
done
