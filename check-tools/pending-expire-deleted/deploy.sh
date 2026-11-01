#!/bin/bash
# Admin #19: remove for good the reports already marked deleted (the owner's yes, 1 Nov 2026). DRY_RUN=true first.
exec /opt/homebrew/bin/python3 "$(cd "$(dirname "$0")" && pwd)/expire.py"
