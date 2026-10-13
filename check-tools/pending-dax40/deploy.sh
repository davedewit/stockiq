#!/bin/bash
# Creates the 4 workers of the Germany DAX 40 screener from the one share-screener package (workers/create_group.py).
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Create:                      bash deploy.sh        (safe to run twice: a function that exists is passed over)
set -euo pipefail
exec /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/create_group.py stockiq-europe-4-2-worker "$(cd "$(dirname "$0")" && pwd)"
