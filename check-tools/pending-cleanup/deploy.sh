#!/bin/bash
# Deletes 144 worker functions that nothing calls (see cleanup.py beside this file for what is checked first).
#   Preview (changes nothing):   DRY_RUN=true bash deploy.sh
#   Delete:                      bash deploy.sh
set -euo pipefail
exec /opt/homebrew/bin/python3 -W ignore "$(cd "$(dirname "$0")" && pwd)/cleanup.py"
