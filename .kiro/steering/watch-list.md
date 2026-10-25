# Watch list: recent changes that could still break something

Short-lived notes (the owner, 25 Oct 2026: a temporary note of what a session did, in case it breaks something later, removed once
it has proved itself). **Read this when anything misbehaves: the cause is often a recent change.** One entry per change that touches
live behaviour: what changed, what could break and how it would show, how to undo it, and a date to remove the entry.

Rules:
- A session that changes live behaviour adds an entry here (in the same commit). Plain fixes of wording or layout with nothing to
  break need none.
- `session_start.py` lists entries past their "remove after" date. The session checks that nothing in "could break" happened
  (the daily emails, the opening check, the Admin page), then deletes the entry. If it did break: fix it, and move what was learned
  into site-overview.md (a pitfall in section 9, or the part of the site it concerns) before deleting the entry.
- Permanent facts belong in site-overview.md, not here. Keep each entry to a few lines.

---

### 2026-10-25 · The anonymous free analysis counted in the browser too
- **Changed:** `auth.js` (`getAnonymousUsageCount` takes the larger of the server's count by IP and `localStorage.stockiqAnonUsed`;
  `incrementAnonymousUsage` writes it); `dashboard.html` uses that count instead of asking the server itself.
- **Could break:** a visitor who is not signed in told "0 free today" without having used it (a stale note: it is keyed on the UTC
  date, so it should clear at 00:00 UTC); the dashboard's "remaining today" line blank or wrong.
- **Undo:** `git revert` the two website commits of 25 Oct ("auth.js: the browser also remembers…", "dashboard.html: anonymous…") and deploy.
- **Remove after:** 2026-11-25

### 2026-10-25 · Register page spacing and the menu's place
- **Changed:** `signup.html` (64px under the bar on a phone; the hidden 20px bell placeholder replaced by the real bell);
  `unsubscribe.html` got the bell. `header_room_check.js` now fails a page whose menu stands elsewhere.
- **Could break:** the register page's top under the bar on a phone; the bell showing on the register page for a signed-out visitor.
- **Undo:** `git revert` those website commits.
- **Remove after:** 2026-11-08

### 2026-10-25 · The auto-delete cleanup handles only its own user
- **Changed:** Lambda `stockiq-auto-delete-cleanup` (it scanned the whole report table and applied one user's setting to everyone,
  64 times a day). Now: only the `userId` it is given; no userId answers 400. `lambda_deploy.sh` now replaces one file in a package
  that holds others.
- **Could break:** old reports no longer hidden for some account (look: the dashboard's Report History growing past its setting);
  "Run cleanup now" on the dashboard answering an error. One report of another account stays hidden from before (restoring it was
  refused by the safety check: the owner's call).
- **Undo:** put back `~/VSCODE/backup/stockiq-auto-delete-cleanup_before_oneuser_20261025.zip` (`aws lambda update-function-code`).
- **Remove after:** 2026-11-25 (`cost_check.py`'s `FIXED_UNTIL` for that table ends 2026-10-27: check the reads have fallen)

### 2026-10-25 · Every website deploy runs checks first
- **Changed:** `check-tools/pre_deploy.py`, called by `web_deploy.sh` on the dry run (a stamp `.checked` lets the real run skip it).
- **Could break:** a deploy refused for a fault that is already live, or the browser checks failing on a port in use (another browser
  check running). `SKIP_CHECKS="<reason>"` is the emergency way past it.
- **Undo:** remove the block between the `STAMP=` line and the dry-run line in `web_deploy.sh`.
- **Remove after:** 2026-11-25

### 2026-10-25 · The daily email written from the log
- **Changed:** `~/stockiq-daily.sh` (NOT in git) now calls `check-tools/daily_report.py` and sends its body; logs kept in `~/stockiq-logs/`.
  `site_audit.py` gained `news-stale`, `one-count` and `cost` (`check-tools/cost_check.py`, CloudWatch only).
  Each run also writes one line to the Admin record (`admin.py runs`): "What runs by itself" shows the last three, "Coming up" the next.
- **Could break:** no daily email at all, or one that says "the report could not be written" (Monday 26 Oct is the first real one);
  a false ⚠️ from a routine line (add it to `BENIGN` in `daily_report.py`); a false cost alarm (thresholds in `cost_check.py`).
- **Undo:** `cp ~/VSCODE/backup/stockiq-daily.sh_before_report_20261025 ~/stockiq-daily.sh`.
- **Remove after:** 2026-11-15
