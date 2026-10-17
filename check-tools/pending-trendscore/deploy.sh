#!/bin/bash
# The trend score for the share screeners (17 Oct 2026, the owner's yes): the one worker package with SCORE_VERSION 2 by default.
# groups.txt: the Dow 30 first, then all. Preview: DRY_RUN=true bash deploy.sh  Way back: ROLLBACK=true bash deploy.sh
set -euo pipefail
exec /opt/homebrew/bin/python3 /Users/dave/VSCODE/stockiq/workers/deploy.py "$(cd "$(dirname "$0")" \&\& pwd)"
