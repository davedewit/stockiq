#!/bin/bash
# Creates the workers of three new screeners from the one share-screener package (workers/create_group.py):
# France CAC 40 (4), Netherlands AEX (3), Canada TSX 60 (6). Each group's addresses go to urls.txt in its own folder.
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Create:                      bash deploy.sh        (safe to run twice: a function that exists is passed over)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
for pair in "stockiq-europe-4-3-worker:cac40" "stockiq-europe-4-4-worker:aex" "stockiq-americas-6-1-worker:tsx60"; do
    /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/create_group.py "${pair%%:*}" "$HERE/${pair##*:}"
done
