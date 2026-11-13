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


### 2026-10-30 · The longer-holds trial
- **Changed:** `stockiq-ai-trader` (`LONGER`, `LONGER_DAYS` 20, tag `lh` 0, 1, 1, 0 on share buys while `maxHoldDays` is automatic; `hold_days`).
- **Could break:** the budget filling up and buying slowing (tagged shares are held longer); a holding's plan showing 20 days where the
  owner set his own time (it must not: `hold_days` checks `auto`); the review tool's split missing.
- **Undo:** `LONGER = False` in the function (tagged shares then follow the level's time), or the rollback zip `…_before_autopilot_longer_20261030.zip`.
- **Remove after:** 2026-11-20

### 2026-10-31 · The daily run waits 20 hours after the last one
- **Changed:** `~/stockiq-daily.sh` (NOT in git): it also needs the newest `deploy-*.lock` to be 20 hours old (a run at 15:33 on 30 Oct was followed by one at 00:02).
- **Could break:** a day with no run at all (look: no daily email; `ls -la ~/.stockiq-locks/`).
- **Undo:** `cp ~/VSCODE/backup/stockiq-daily.sh_before_20hours_20261031 ~/stockiq-daily.sh`.
- **Remove after:** 2026-11-14

### 2026-10-31 · Market figures: how they flash, and one rule for the day's change
- **Changed:** `live-market.js` version 9 (flash only on a newer trade, in trade order, only the part that changed, soft tint, figure
  0.25 s after the colour, full speed 5 min without a touch); `ticker-data-fetcher` (sends `time`, prices to 4 decimals, 6 under $1);
  the seven `stockiq-market-data-*` functions (Yahoo's price against its reference close, not the last two daily bars).
- **Could break:** nothing flashes in an open market (no `time` in the answer: then every change flashes, as before); a tab of the
  panel empty (a function failing on the new request: `market_sources_check.py` says which); more Lambda calls from the 15-minute stop.
- **Undo:** website `git revert` the live-market.js commits of 31 Oct; the functions: their `~/VSCODE/backup/*_before_{time,decimals,reference}_20261031.zip`.
- **Remove after:** 2026-11-14

### 2026-10-31 · The home page's index cards: two links each; the Russell 2000 daily page
- **Changed:** `index.html` cards (name to `screener-<market>.html`, "Run screener" to the analysis, nofollow), `styles.css` (`.ic-link`);
  `update_screener_pages.py` adds the Russell 2000 (one more coordinator run a day, about 200 worker calls) and counts the markets;
  `market-panel.js` v4 draws rows only when their items change; `live-market.js` keeps trade times 2 minutes across a refresh.
- **Could break:** a card link to a page that is not there (the daily run failing for a market keeps yesterday's page); the Russell run
  timing out in the daily update (it took 26 s); panel rows not updating when the list of items changes (a tab with new items).
- **Undo:** website `git revert` the commits of 31 Oct evening; remove `'3-6'` from `SCREENERS` in update_screener_pages.py.
- **Remove after:** 2026-11-14

### 2026-10-31 · A month over $1.50 with a known, fixed cause no longer calls the owner in
- **Changed:** `cost_check.py` (`KNOWN_OVER` per month with its reason and an upper amount; `KNOWN_READS`; tables flag from 10 cents a month;
  cache clears flag 20 paths past the explained count); `session_start.py` and the Admin card (`admin-panel.js?v=56`, `plan.billKnown` from
  `admin.py sync`) read `KNOWN_OVER`. `stockiq-ai-trader`: no "may sell early again" while `AI_SELL` is off; `stockiq-ai-chat`: 25 daily pages.
- **Could break:** a real cost rise hidden (only up to `upTo`, only for the month named: check November reads under $1 with no entry);
  the card wrong on 1 Nov while AWS still reports October (the month comes from the bill's own reading time, `costAt`).
- **Undo:** `git revert` the commits of 31 Oct "Bill: a known overrun…"; functions: their `…_20261031.zip` in ~/VSCODE/backup/.
- **Remove after:** 2026-11-14

### 2026-10-31 · The daily hub compares each market with its own last trading session
- **Changed:** `update_screener_pages.py` (`session_sig`, `same_session`; state `_hubBase` per market, a `sig` and `base` in each market's
  page state; `_hubDate` / `_hubPrev` gone); the state was seeded from Thursday's backup (copy before it in the session's scratchpad only).
- **Could break:** the hub stuck on an old comparison (a market whose prices never change: look for the same arrows for days), "days in
  the top 10" not rising on a trading day, a market showing "–" for long. `site_audit.py` `hub-compare` catches "no change" everywhere.
- **Undo:** `git revert` the commit "Daily hub: each market against its last trading session"; the old state format is read back as before.
- **Remove after:** 2026-11-14

### 2026-11-01 · The directory of stock pages; true sitemap dates; IndexNow key
- **Changed:** `update_home_stock_links.py` writes `stock-pages.html` and a link to it in the home page's stock section; `update_sitemap.py`
  lists it and dates a stock URL by the later of its news and its data; IndexNow's key file `5d95459b….txt` (deploy-to-s3.sh uploads it).
- **Could break:** the home page's stock section (the script refuses under 20 links); stock-pages.html missing from the sitemap; a daily email
  with "IndexNow response: 403" (Bing has not accepted the new key: look at the key file on the site).
- **Undo:** `git revert` the commits of 1 Nov "Directory of stock pages…"; delete website/stock-pages.html and its line in the sitemap.
- **Remove after:** 2026-11-15


### 2026-11-01 · News summaries written from the article, not the headline
- **Changed:** `article_text.py` (new); `update_news.py` reads CNBC's four market feeds before Google News and summarises the article
  (every figure must be in it); `update_stock_news.py` summarises the stock article when it opens. Headline-only stories keep the
  no-percentage rule (general) or may use only the headline's figures (stock). `daily_report.py` counts every "Rejected (".
- **Could break:** no general news (CNBC's feeds moved: "CNBC feeds read: 0 of 4" in the log); the stock news step much slower
  (one page fetch a summary: look at its time in the daily email); "summary had figures not in the article" on most stories (the
  extractor reading the wrong part of a page: `python3 article_text.py <url>`); a summary that reads as advice.
- **Undo:** `git revert` the commit "News summaries from the article itself".
- **Remove after:** 2026-11-15

### 2026-11-01 · The AI model that chooses the buys takes turns (GPT-4o-mini and GPT-5)
- **Changed:** `stockiq-ai-trader`: `CHOOSE_MODELS` (who chooses, by share), `model_turn`, `ask_within_free` with a day's token count
  in item `_aiuse` (`FREE_DAILY`: 150,000 large-model tokens a day of the account's ~250,000 free), `mdl` on each buy the model chose;
  GPT-5 asked as a reasoning model (`reasoning_model`: no temperature, `max_completion_tokens`).
- **Could break:** an OpenAI charge (look at the OpenAI usage page: spend must stay $0; if not, the model's class is not in the free
  list: set `CHOOSE_MODELS` back to GPT-4o-mini alone); check-ins slower (GPT-5 takes about 8 s); "AI model gpt-5 not used" in the log.
- **Undo:** `CHOOSE_MODELS = [('gpt-4o-mini', 1)]`, or the zip `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_models_20261101.zip`.
- **Remove after:** 2026-11-15

### 2026-11-01 · The progress score and the daily AI summaries
- **Changed:** `stockiq-ai-trader` (`write_digests` after 21:10 UTC, item `_digest`, `state.digest`; `admin_view` and `public()` send them);
  `admin-panel.js?v=58` ("Today in 30 seconds"), `practice-autopilot.js?v=76` ("Your day in short").
- **Could break:** no summary by the morning ("daily summaries not written" or "daily summary not written for …" in the function's log);
  a summary that says something untrue (the figure check passes numbers only: read the first few); the score not moving on a trading
  day (the SPY quote not fresh at 21:10); the scheduled run taking longer (GPT-5 about 10 s a day).
- **Undo:** the zip `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_digest_20261101.zip`; the two scripts from git.
- **Remove after:** 2026-11-15

### 2026-11-01 · Practice portfolio top: the leader tagged, no "since the start" lines, cash on top
- **Changed:** `practice-portfolio.js?v=81` (`leads`, `.pp-cashline`, the cards' sub lines removed).
- **Could break:** the tag on two cards or on a card that is not highest; the weekly sums check (`sums_agree` reads the lines under the cards).
- **Undo:** `git revert` the website commit "Practice portfolio: the leader tagged …".
- **Remove after:** 2026-11-15

### 2026-11-01 · The sector funds' AI calls judged against the S&P 500 over the same days (Admin #16)
- **Changed:** `stockiq-ai-trader`: `theme_read(..., spy=)` keeps SPY's price with each call (`sv` 2); `rescore_theme_calls` judges the
  older calls again from daily closes, once (`themes.rescored`), at the first check-in with the US market open (Mon 2 Nov).
- **Could break:** "theme calls not rescored" in the log; the Practice/autopilot figures of the AI's calls showing none scored (prices not had).
- **Undo:** the zip `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_themecalls_20261101.zip`.
- **Remove after:** 2026-11-15

### 2026-11-01 · Reports kept 30 days by default; auto-deleted reports removed a week later (Admin #18)
- **Changed:** `stockiq-auto-delete-cleanup` (queries only reports older than the cut-off; sets `ttl` 7 days on with `deleted`),
  `stockiq-auto-delete-scheduler` and `stockiq-user-trial-manager` (default `autoDeleteDays` '30'), `dashboard.html` (30 days in the
  menu, the default; the setting loaded once). The table's TTL is on (attribute `ttl`).
- **Could break:** "Run Now" on the dashboard failing; reports a user wanted kept disappearing (pinned ones are skipped, as before);
  the trial-manager answer (it serves every signed-in page: a smoke test after the deploy answered normally).
- **Undo:** the zips `~/VSCODE/backup/stockiq-{auto-delete-cleanup,auto-delete-scheduler,user-trial-manager}_before_reports30_20261101.zip`.
- **Remove after:** 2026-11-15

### 2026-11-01 · A paying member's reports kept by default (the "Recently Deleted" switch was removed and put back the same day)
- **Changed:** `stockiq-auto-delete-scheduler` and `stockiq-user-trial-manager` (no stored choice: "never" for an active paid plan, else 30);
  `dashboard.html` (the switch and its code gone; `showDeleted` always false).
- **Could break:** the Reports tab's list or menu (the trial manager serves every signed-in page: smoke-tested after the deploy).
- **Undo:** the zips `~/VSCODE/backup/stockiq-{auto-delete-scheduler,user-trial-manager}_before_paidkeep_20261101.zip`; the page from git.
- **Remove after:** 2026-11-15

### 2026-11-06 · Rank-pick buys recorded as chosen by rank (Admin #8, first stage)
- **Changed:** `stockiq-ai-trader` (`remember_buy` result: `facts['chosen'] = 'rank'` when `_rp == 1`); `cost_check.py` reads a service with no recent figure by its last datapoint's month (October's $2.65 was read as November's twice) and now lists a jump of $0.10+ in another account on the bill; `site_audit.py` `stale-until` has KVUE.
- **Could break:** the review's "by who chose it" split showing a new line "by rank" (intended); a sale's story saying "chosen by rank" for these buys (correct now). Nothing else reads `chosen == 'ai'` except the `mdl` tag, which already excluded them.
- **Undo:** `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_rankchosen_20261106.zip`.
- **Remove after:** 2026-11-20

### 2026-11-06 · The AI model sees the record only from 30 trades a line, and only trades bought under the current score (Admin #8, second stage)
- **Changed:** `stockiq-ai-trader` (`CARD_MIN` 30, `SCORE_LIVE_FROM` 2026-10-17T10:55Z, `current_score`; used for the model's card of this account's record, of every account's, and for `write_lessons`). `MIN_SAMPLE` (8) still governs resting, tuning proposals and the AI-sell pause: those need a replay first (Admin #8's last stage).
- **Could break:** the model's prompt showing "Fewer than 30 trades" for a small record (intended); no new shared notes until 30 current-score trades exist (about 122 now: fine); a prompt error in the function's log after a check-in.
- **Undo:** `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_learnscore_20261106.zip`.
- **Remove after:** 2026-11-20

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
