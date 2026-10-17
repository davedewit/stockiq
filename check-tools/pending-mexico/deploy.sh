#!/bin/bash
# Creates the 4 workers of the Mexico IPC screener (17 Oct 2026) from the one share-screener package.
set -euo pipefail
exec /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/create_group.py stockiq-americas-6-3-worker "$(cd "$(dirname "$0")" && pwd)"
