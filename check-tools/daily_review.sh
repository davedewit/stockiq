#!/bin/bash
# The daily review by Claude, unattended (18 Oct 2026, a two-week trial at the owner's yes). launchd starts this every 30 minutes
# (~/Library/LaunchAgents/com.stockiq.review.plist); it runs the review once a day, after the daily deploy, and never changes
# the live site: the session may only read, run the read-only checks, write its report (check-tools/reviews/daily/) and add
# proposals to the Admin page. Everything else is refused without asking (--permission-mode dontAsk with a list of allowed tools).
# Its report is allowed as Edit(check-tools/reviews/daily/**): Claude Code's file rules count writing a new file as an edit, so a
# Write(...) rule never matched, and a blocked "Edit" refused the report too (first run, 18 Oct 2026). Edits anywhere else are
# refused because nothing allows them.
#
#   bash check-tools/daily_review.sh --now    run it now, whatever the time (still once a day)
#   log: ~/stockiq-review.log    switch off: launchctl unload ~/Library/LaunchAgents/com.stockiq.review.plist
#
# The trial ends by itself after 1 Nov 2026 unless check-tools/reviews/daily/KEEP exists (experiments.py: daily-review).
set -u
ROOT=/Users/dave/VSCODE/stockiq
LOG="$HOME/stockiq-review.log"
TODAY=$(date +%Y%m%d)
LOCK="/tmp/stockiq-review-$TODAY.lock"
NOW_ARG="${1:-}"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

[ -f "$LOCK" ] && exit 0                                             # once a day
if [ "$(date +%Y%m%d)" -gt 20261101 ] && [ ! -f "$ROOT/check-tools/reviews/daily/KEEP" ]; then exit 0; fi
if [ "$NOW_ARG" != "--now" ]; then
    HOUR=$((10#$(date +%H))); DOW=$(date +%u)
    [ "$HOUR" -lt 13 ] || [ "$HOUR" -ge 22 ] && exit 0               # afternoon or evening on this Mac's clock
    # after the daily deploy (Monday to Saturday it runs from 11:00; there is none on Sunday), and never during it
    if [ "$DOW" -ne 7 ] && [ ! -f "/tmp/stockiq-deploy-$TODAY.lock" ] && [ "$HOUR" -lt 18 ]; then exit 0; fi
fi
pgrep -f "deploy-to-s3\.sh" >/dev/null && exit 0
CLAUDE=$(ls -d "$HOME"/.kiro/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | sort -V | tail -1)
[ -x "$CLAUDE" ] || { echo "$(date): no Claude tool found under ~/.kiro/extensions" >> "$LOG"; exit 0; }
touch "$LOCK"
mkdir -p "$ROOT/check-tools/reviews/daily"
{
  echo "=== $(date): daily review starts ($CLAUDE)"
  cd "$ROOT" || exit 1
  "$CLAUDE" -p "$(cat check-tools/daily_review_prompt.md)" \
    --permission-mode dontAsk --no-session-persistence \
    --allowedTools "Read" "Grep" "Glob" \
      "Bash(python3 check-tools/session_start.py)" "Bash(python3 check-tools/site_audit.py)" "Bash(python3 check-tools/admin.py)" \
      "Bash(python3 check-tools/clarity_check.py --keep)" "Bash(python3 check-tools/clarity_check.py)" \
      "Bash(python3 check-tools/autopilot_review.py:*)" "Bash(python3 check-tools/site_parts.py:*)" \
      "Bash(python3 check-tools/admin.py add session:*)" "Bash(python3 check-tools/admin.py recommend:*)" \
      "Bash(git log:*)" "Bash(git diff:*)" "Bash(git status:*)" \
      "Edit(check-tools/reviews/daily/**)" \
    --disallowedTools "NotebookEdit" "Bash(bash:*)" "Bash(sh:*)" "Bash(aws:*)" "Bash(git push:*)" "Bash(git commit:*)" "Bash(rm:*)" &
  PID=$!
  ( sleep 3000; kill "$PID" 2>/dev/null && echo "$(date): stopped at its 50-minute limit" ) &
  WATCH=$!
  wait "$PID"; STATUS=$?
  kill "$WATCH" 2>/dev/null
  echo "=== $(date): daily review ended (exit $STATUS); report: $(ls -t check-tools/reviews/daily/*.md 2>/dev/null | head -1)"
} >> "$LOG" 2>&1
