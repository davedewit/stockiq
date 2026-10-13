#!/bin/bash
# Creates the workers of two new screeners from the one share-screener package (workers/create_group.py):
# Italy FTSE MIB (4), Spain IBEX 35 (4). Each group's addresses go to urls.txt in its own folder.
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Create:                      bash deploy.sh        (safe to run twice: a function that exists is passed over)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
for pair in "stockiq-europe-4-5-worker:ftsemib" "stockiq-europe-4-6-worker:ibex35"; do
    /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/create_group.py "${pair%%:*}" "$HERE/${pair##*:}"
done
