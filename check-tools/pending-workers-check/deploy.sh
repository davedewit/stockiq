#!/bin/bash
# A check, not a change: the package built from workers/ is the one that is live (workers/live.txt), so this only reads every
# share-screener worker on AWS and confirms each holds it. See workers/deploy.py.
set -euo pipefail
exec /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/deploy.py "$(cd "$(dirname "$0")" && pwd)"
