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

### 2026-10-25 · Plan cards: true features ticked, unbuilt ones "Coming soon"
- **Changed:** `dashboard.html` "Upgrade Your Plan" (alerts, real-portfolio tracking, custom screeners, portfolio tools, white-label moved
  under "Coming soon", at the owner's word; a note under the cards); `index.html` Pricing shows "Choose a plan" (to `dashboard.html#upgrade`)
  to signed-in visitors, "Start Free Trial" to others. `site_audit.py` `plan-claims` fails a ticked item not in its `EXISTS` list.
- **Could break:** the Pricing section showing both buttons or neither (the `only-signed-in` / `only-signed-out` classes); a click on a card
  not starting checkout (the `subscribeToPlan` calls were left as they were). When a "Coming soon" feature is built: tick it and add it to `EXISTS`.
- **Undo:** `git revert` the website commit "Plan cards: …".
- **Remove after:** 2026-11-25


### 2026-10-26 · Stock news on the news page; one cache clear per deploy
- **Changed:** `update_stock_news.py` (its pattern for news.html allows a comment before `<footer>`; "Synced" only when written; the
  same fallback fixed in `Sync_stock_to_news.py`, `remove_news_duplicates.py`, `update_news.py`); `web_deploy.sh` clears `/*` once for
  2+ files; `site_audit.py` `news-stale` checks the stock news alone; `cost_check.py` counts the month's cache-clear paths.
- **Could break:** news.html written with a broken end (look: the page's footer missing or doubled after tomorrow's run); stock news
  stale again (the site check now says so); a CloudFront cost rise of more than a cent a day.
- **Undo:** `git revert` the commit "Stock news reaches news.html again; one cache clear per deploy".
- **Remove after:** 2026-11-09

### 2026-10-26 · Click and drag on the practice graph
- **Changed:** `practice-portfolio.js` (`dragStart`, `dragMove`, `dragEnd`, `showMeasure`, `reMeasure`; a band `#pp-band` in the picture):
  while held, a drag measures the stretch for the line on show and the S&P 500 fund; letting go clears it (as broker apps do).
- **Could break:** the read-out stuck on a stretch after letting go, a phone's page scroll caught by the graph, a swipe on the graph opening the menu.
- **Undo:** `git revert` the website commit "Practice portfolio: click and drag across the graph".
- **Remove after:** 2026-11-09

### 2026-10-26 · The home page's search shows a share's latest news
- **Changed:** `symbol-news.js` (new; `symbolNews.show/hide`), `index.html` (a box under each search, shown when a suggestion is picked or
  a code with a stock page is typed and no suggestions wait). Reads the share's stock page (its NEWS section): no new running cost.
  `stage_web.py` now stages a brand-new file (it read an uncommitted new file as unchanged).
- **Could break:** the box covering the suggestions, a stock page's news markup changing (`update_stock_news.py`) so no headlines are
  found (the box then says "No recent articles"), the side panel's search height. `search_news_check.js` (weekly) tests it.
- **Undo:** `git revert` the website commit "Home page search: a picked share's latest news" and deploy index.html.
- **Remove after:** 2026-11-09

### 2026-10-30 · news.html can no longer double itself
- **Changed:** the end-of-list pattern in `update_stock_news.py`, `update_news.py`, `Sync_stock_to_news.py`, `remove_news_duplicates.py` is
  searched from the article list onwards (the 26 Oct pattern matched a `</div>` in the menu and doubled the page every 10 articles, to
  5.8 GB by 27 Oct); `news_guard.py` makes every writer refuse a page with the list or footer twice, or over 20 MB. `daily_report.py`
  names a step killed by the system and a news.html over 20 MB.
- **Could break:** no stock news reaching news.html (a "❌ news.html not written: …" line in the log); the guard refusing a good page
  (the footer counted twice if a page ever has two `<footer`).
- **Undo:** `git revert 608fd71`.
- **Remove after:** 2026-11-13
