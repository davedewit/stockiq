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

### 2026-10-25 · Plan cards: true features ticked, unbuilt ones "Coming soon"
- **Changed:** `dashboard.html` "Upgrade Your Plan" (alerts, real-portfolio tracking, custom screeners, portfolio tools, white-label moved
  under "Coming soon", at the owner's word; a note under the cards); `index.html` Pricing shows "Choose a plan" (to `dashboard.html#upgrade`)
  to signed-in visitors, "Start Free Trial" to others. `site_audit.py` `plan-claims` fails a ticked item not in its `EXISTS` list.
- **Could break:** the Pricing section showing both buttons or neither (the `only-signed-in` / `only-signed-out` classes); a click on a card
  not starting checkout (the `subscribeToPlan` calls were left as they were). When a "Coming soon" feature is built: tick it and add it to `EXISTS`.
- **Undo:** `git revert` the website commit "Plan cards: …".
- **Remove after:** 2026-11-25


### 2026-11-12 · The model is no longer shown headlines for the shares it picks from (experiment `headlines` removed)
- **Changed:** `stockiq-ai-trader` (`CANDIDATE_HEADLINES = False`: the shortlist's per-share headlines are not fetched or put in the prompt; the market's
  calendar and general headlines stay; `heads` on a buy is 0 from now). Reason: 91 buys with a headline averaged -1.85% a trade, 138 with none -0.92%.
- **Could break:** a prompt error in the function's log after a check-in (none seen at the first run); the review tool's headline split showing only
  "none found" (intended); the model choosing worse without the headlines (its picks were already -3.29% against -2.08% by rank: `rank-pick`, `choose-models`).
- **Undo:** `CANDIDATE_HEADLINES = True`, or the zip `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_noheads_20261112.zip`.
- **Remove after:** 2026-11-26

### 2026-11-12 · The daily pages say "positive trend score", not "rising"
- **Changed:** `update_screener_pages.py` (the hub, the 25 daily pages, the home page's market week); `site_audit.py` `rising-claim` fails a page that says
  "in a rising trend" or "N% rising" of it again. The pages were regenerated on 12 Nov and go up with the next daily update.
- **Could break:** the daily pages' text running long in the hub's column (a table heading is longer); a `rising-claim` problem if a new writer brings the old words back.
- **Undo:** `git revert` the commit "Daily pages: positive trend score…".
- **Remove after:** 2026-11-26

### 2026-11-12 · The weekly full check: PATH, a missing program, the market-sources tolerance
- **Changed:** `weekly_check.py` (Homebrew first on PATH; a program it cannot start is a failed step; `--recheck` can re-run the sources check alone),
  `market_sources_check.py` (the % may differ by 0.2 points, was 0.05: ticks between the two calls failed it), `session_start.py` (a Traceback in
  `~/stockiq-weekly-check.log` newer than the last result is a finding).
- **Could break:** the automatic run (end of `deploy-to-s3.sh`) still dying: look at `~/stockiq-weekly-check.log` after the next daily update on or after 19 Nov.
- **Undo:** `git revert` the commit.
- **Remove after:** 2026-11-26

### 2026-11-14 · GPT-5.6 Luna replaces GPT-4o mini everywhere (OpenAI retires 4o mini on 14 Jan 2027)
- **Changed:** `stockiq-ai-trader` (`USUAL_MODEL`; `CHOOSE_MODELS` is now Luna and GPT-5; Luna counts in the small pool; priced $0.20/$1.20 in `AI_PRICES`),
  `stockiq-ai-chat` (`CHAT_MODEL`, `max_completion_tokens` = reply cap + 1,500, `reasoning_effort` low, no temperature), `stockiq-ai-chat-reporter`
  (prices), and on the Mac `update_news.py` (2 calls), `update_stock_news.py` (1 call) (`reasoning_effort` none, `max_completion_tokens`). Luna refuses
  `temperature`, `max_tokens` and `reasoning_effort` 'minimal'. The experiment `choose-models` restarts as Luna against GPT-5 (decide 20 Dec).
- **Could break:** a chat reply that is empty or cut (the thinking ate the cap: look for short replies in the chat's daily report); more "AI model … not
  used" lines in the trader's log; the news summaries rejected more often for invented figures (count "Rejected (" in the daily email: it was the
  routine level before); an OpenAI charge (Luna may not be in the account's free daily tokens: look at OpenAI's usage page, the Admin page's AI cost
  line shows the month's spend at Luna's prices); the chat slower (4-5 s a reply against 1-2 s).
- **Left on purpose:** `STRONG_MODEL = 'gpt-4o'` (the AI review's larger model: the review is off, `AI_SELL = False`; it also retires on 14 Jan 2027, so
  choose its replacement when that trial ever returns; until then the model test's "larger" answer will turn false on that day and mean nothing).
- **Undo:** the zips `~/VSCODE/backup/stockiq-{ai-trader,ai-chat,ai-chat-reporter}_before_luna_20261114.zip`; the news scripts from git. Not before 14 Jan 2027.
- **Remove after:** 2026-12-01

### 2026-11-14 · Payments: Stripe events believed only when Stripe confirms them; cancelling needs proof (Admin #15)
- **Changed:** `stockiq-payment-handler`, `stockiq-dashboard` (no subscription ids handed out), the dashboard's cancel flow, "Email support" on the plan cards.
- **Could break:** a real purchase not turning the member's plan on (look at the first real checkout's log: "Webhook signature: ok", and the plan on the
  account); a member refused when cancelling ("sign out and sign in again": Google sign-ins last an hour). Not done: a plan change is still a new checkout and
  the old subscription deleted (a downgrade loses the rest of the month); enforce the webhook signature once a real event shows it passing.
- **Undo:** the zips `~/VSCODE/backup/stockiq-{payment-handler,dashboard}_before_payments_20261112.zip`; the pages from git.
- **Remove after:** 2026-12-14

### 2026-11-14 · The account record is stored compressed; Mexico's hours; "1 day left" wording
- **Changed:** `stockiq-ai-trader` (`item_json`: a record in `z`, zlib and base64, 326 KB became 69 KB; read either way; Mexico 14:35-20:55 UTC; `left_text`).
- **Could break:** any reader of the table that reads `data` only (the scripts use `trader_record.py`; none found that do not); a save error in the
  trader's log; the account looking empty on the dashboard (it would be `get` failing: check at the next visit).
- **Undo:** the zip `~/VSCODE/backup/stockiq-ai-trader_before_luna_20261114.zip` (it reads `data` only: a record saved compressed would then look new, so
  put the record back from `z` first with `trader_record.py`).
- **Remove after:** 2026-12-01

### 2026-11-20 · The two coin-history tables are pay-per-request
- **Changed:** `stockiq-coinspot-predictions` (was 23 read / 2 write units provisioned) and `stockiq-coinspot-prediction-status` (2 / 2) switched to on-demand. Reason: on 18-19 Nov StockIQ's DynamoDB bill rose $0.15 with flat usage while another account in the organisation rose $0.09: the shared free provisioned allowance (25 units for the whole organisation) is gone, so those 25 read units began to bill (about $0.08 a day).
- **Could break:** the coin top-10 history (orchestrator's 30-minute run) failing on a throttle (it cannot: on demand); the DynamoDB cost not falling by 22 Nov (look at the Admin page's bill and `cost_check.py`).
- **Undo:** `aws dynamodb update-table --table-name <t> --billing-mode PROVISIONED --provisioned-throughput ReadCapacityUnits=23,WriteCapacityUnits=2` (once a day at most).
- **Remove after:** 2026-12-04


### 2026-11-20 · The news summaries use GPT-5.4 mini (small models: 2.5 million free tokens a day; Luna 250,000)
- **Changed:** `update_news.py` (two calls) and `update_stock_news.py` (one call) on this Mac: model `gpt-5.4-mini` (same parameters; tested). The chat and the autopilot stay on Luna.
- **Could break:** more "Rejected (" lines in the daily email (summaries with figures not in the article); a summary that reads worse.
- **Undo:** put `gpt-5.6-luna` back in those three places.
- **Remove after:** 2026-12-04
