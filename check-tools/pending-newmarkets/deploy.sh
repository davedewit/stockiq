#!/bin/bash
# Creates the workers of five new screeners (17 Oct 2026) from the one share-screener package (workers/create_group.py), one
# folder each for its urls.txt: Euro Stoxx 50 (5), Sweden OMX 30 (3), China CSI 300 (30), Taiwan 50 (5), NZX 50 (5).
# Preview: DRY_RUN=true bash deploy.sh. Safe to run twice (a function that exists is passed over).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
for g in stockiq-europe-4-8-worker stockiq-europe-4-9-worker stockiq-asia-5-10-worker stockiq-asia-5-11-worker stockiq-asia-5-12-worker; do
    mkdir -p "$HERE/$g"
    /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/create_group.py "$g" "$HERE/$g"
done
