#!/bin/bash
# Creates the workers of two new screeners from the one share-screener package (workers/create_group.py):
# Hong Kong Hang Seng (10), Singapore STI (3). Each group's addresses go to urls.txt in its own folder.
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Create:                      bash deploy.sh        (safe to run twice: a function that exists is passed over)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
for pair in "stockiq-asia-5-8-worker:hangseng" "stockiq-asia-5-9-worker:sti"; do
    mkdir -p "$HERE/${pair##*:}"
    /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/create_group.py "${pair%%:*}" "$HERE/${pair##*:}"
done
