#!/bin/bash
# Deploy (11 Oct 2026): one code base for the share screeners. Every share-screener worker gets the same package, built from
# workers/ in git (stock_worker.py and its lists). 669 functions in 13 groups; the groups to do in a run are in groups.txt
# beside this file, so it goes a group at a time, smallest first.
#
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Deploy:                      bash deploy.sh
#   Put a group back:            ROLLBACK=true bash deploy.sh        (the groups in groups.txt, from the copies kept below)
#
# For every function it checks that the live code is one of the copies this was built against, keeps that function's package
# in ~/VSCODE/backup/workers_before_onecode_20261011/<function>.zip, updates it, and checks the fingerprint AWS reports. Each
# group is then tried for real (its first and last worker); a group that fails the try is put back by itself. Safe to run
# twice: a function that already has the new package is passed over. Details and what it changes: deploy.py, and
# site-overview.md section 8b, "The worker groups".
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
if pgrep -x "deploy-to-s3.sh" >/dev/null || pgrep -f "bash .*/deploy-to-s3\.sh" >/dev/null; then printf '\nSTOPPED: the daily deploy is running; try again when it has finished\n'; exit 1; fi
exec /opt/homebrew/bin/python3 "$HERE/deploy.py"
