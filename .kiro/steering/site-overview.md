<!--
  DAVE: to go through the autopilot in depth (what it lost and why, what to change), open a session and say:

      review the autopilot

  Every week or two is about right; the first one around 26 Oct 2026, or once 30 trades have finished.
  (This note is hidden in a preview; it shows when the file is opened as text.)
-->
# StockIQ Site Overview (read this first)

How stockiq.tech works end to end, what is generated vs hand-edited, the current SEO setup,
known pitfalls, and open ideas. **Last full sweep: 11 Oct 2026, evening; everything checked again on 12 Oct 2026** (live code against local copies, every test suite, 48 hours of logs: section 8c, "Start here when resuming") (every part of section 8c
rewritten or checked against the deployed code; the other steering files, the README files and the AI chat's
own guide brought into line). Section 8b holds what the 9–10 Oct end-to-end test of every screener, signal
and crypto path established; section 7b the backtests and the factor study of the screener score; **section 8c
is the dashboard (practice portfolio, AI autopilot, notification bell): to resume that work, read it from
"Start here when resuming"**.

Detailed references: `stockiq.md` (AWS resources, Cognito, Lambdas, AI chat),
`script-reference.md` (every script), `add-new-stocks.md`, `stock-matching-system.md`,
`stocks-txt-csv-format.md`, `roadmap-to-9.md`, `backlinks-progress.md`, `future-work.md`.

**THE FIRST COMMAND OF EVERY SESSION: `python3 check-tools/session_start.py`** (read-only, about a minute; built 17 Oct 2026 after
the owner had found problems himself that a session should have found: "You aren't smart or a good AI if i have to manually
find problems or think of improvements"). It prints the account against an S&P 500 fund and the month's goal, the Admin
page's answers, the AWS bill, whether the weekly review is due, error lines in the functions' logs, live code against the
mirrors, the site's key files against the local ones, both repositories, and ends with a numbered list of FINDINGS. **Act on
every finding** before or alongside whatever the owner asks; add a check to the script whenever a problem is found that it
missed.

**THE COST RULE (the owner, 17 Oct 2026): AWS under $1 a month, $1.50 at most in a heavy month.** An AWS budget, `stockiq-monthly`
($1.50), emails him at $1 spent, at $1.50 spent and when $1.50 is forecast; the Admin page shows the bill. What costs is not stored
data (every StockIQ table together was about 7 MB on 17 Oct, far inside the free 25 GB) but **requests**: database reads ($0.19 of
$0.56 that month, mostly the autopilot panel re-reading the record every minute while the dashboard was open: now every 5
minutes, the bell every 10), S3 requests from the daily deploy, and Cost Explorer questions ($0.01 each). **NEVER ASK COST
EXPLORER, FROM ANYTHING** (the owner, 17 Oct 2026: "i do not want to pay 1c just to check usage!"): on 17 Oct the autopilot's test
suite, run on this Mac, asked it 253 times through the function's own bill-reading code (about $2.53, the session's fault; found
in CloudTrail's free event history). The bill is read from the AWS budget instead, free: `aws budgets describe-budget
--account-id 114366766218 --budget-name stockiq-monthly` (spend so far and AWS's forecast); calls from CloudWatch (free). The
function's role has no Cost Explorer permission any more, and `ai_trader_test.py` refuses it. **A test must never reach a paid
AWS service: stand it in.** To see who asked Cost Explorer: `aws cloudtrail lookup-events --lookup-attributes
AttributeKey=EventSource,AttributeValue=ce.amazonaws.com` (free; the AWS website's own billing pages show as "AWS Internal"
or the console, and are free). About $0.09 a month is the owner's other projects' buckets (Sydney region): not StockIQ's, leave them.
**Before adding anything that runs on a timer or on every page view, work out its requests a month and its cost.** Data is kept
when it helps the learning (the record, the diary, the shared record, the coin entry log, the research prices on this Mac);
delete only with his yes to an exact list, and only when it costs something.

**THE SITE IS CHECKED EVERY NIGHT, WITH NO AI AND NO COST: `python3 check-tools/site_audit.py`** (18 Oct 2026; the owner, after
finding one weak spot after another himself: "why can't you actively do this every 24+ hours since a last check"). The daily
deploy runs it with `--admin`: its findings go onto the Admin page ("🔎 Site check", via `admin.py audit`, inside `_admin['plan']`)
and session_start prints them (part 1b; every problem is a finding). It tests concrete things a session had missed: links to the
stock pages, "Loading..." text a search engine reads, broken links, the same function in 3 or more files, `Math.random()` drawing
something, a fixed line written into a chart or figures written in to show when the data fails, indexed stock pages whose
data is more than 4 days behind (`stale-stock-pages`), scripts no page loads or that find nothing on a page, page weight and its growth, the home page's screener count,
titles / descriptions / canonicals, the sitemap, JSON-LD, console noise. **Each time a fault is found by hand, give this script a
check for that kind of fault**; something accepted on purpose goes into its `KNOWN` with the reason. Before a deploy,
`AUDIT_WEB=<staging folder>/web python3 check-tools/site_audit.py` reads the staged files first and saves nothing.
**A daily review by Claude, unattended, is built and NOT installed** (`check-tools/daily_review.sh`, instructions in
`daily_review_prompt.md`): once a day after the deploy, refused anything but reading, the read-only checks, its report
(`check-tools/reviews/daily/`) and up to three proposals on the Admin page; 50 minutes at most; a trial that ends by itself on
1 Nov 2026 unless `reviews/daily/KEEP` exists (experiments `daily-review`). Claude Code's safety check refused to set up its
launchd job from a session ("Create Unsafe Agents"), so only the owner can install it (the plist is in the change log of 18 Oct).

**THE PAGE IS READ AS THE OWNER READS IT, EVERY SESSION: `python3 check-tools/clarity_check.py`** (session_start runs it; built 17
Oct 2026 after the owner, having pointed at one confusing thing after another himself: "anything else confusing you want to
optimise? and i'm tired of asking this!"). It draws the AI autopilot tab and the Admin page from the site's own scripts with the
account's real answers and flags, in what is on show before anything is opened: lists of near-identical lines, "A and B and C",
"1 such moves", a switched-off feature still described as working, menus of more than 20 choices, a phrase twice in one line,
"undefined"/"NaN". `CLARITY_WEB=<staging folder>/web` reads staged files first (run it before a deploy), `--keep` saves the text.
**It is a floor, not the job:** each session also reads at least one tab in full (`--keep`) and fixes whatever confuses, then
teaches the script any new kind of fault it found. When the owner says "this is confusing" again, that is a fault in this routine.

**Two registers keep the improving going without the owner having to ask (17 Oct 2026, his ideas):**
- **`check-tools/site_parts.py`** lists every part of the site (44) with when a session last looked at it. Each session reviews the
  three looked at longest ago (session_start prints them), through every angle in its LENSES (ease of use, faults, appearance,
  profit, the analysis behind it, AI use and newer model versions, comparison over time, new ideas), fixes what is plainly
  wrong and brings the rest to the owner as numbered improvements; then `site_parts.py done <id> "<what was found>"`. His words:
  "pick a few random ones to think about improvements or fault finding. as thats literally what i do with you".
- **`check-tools/experiments.py`** holds every change whose worth is not certain as an experiment: what, which angle, how it is
  measured, the day it is decided. session_start lists those due; the session decides KEEP or REMOVE on the figures (or extends
  once, with a reason). At least one new idea of the session's own goes in every session. His words: "think of new ideas and
  add to it test over a period of time then keep it or remove it based on whether it improves".

**EVERY SESSION, WITHOUT BEING ASKED (the owner's instruction, 12 Oct 2026):** open with what has happened since the last
session, and **if the newest file in `stockiq/check-tools/reviews/` is seven or more days old, run the full review** (section
8c, "The diary, and the review every week or two") before anything else. **And read the Admin page's answers:
`python3 check-tools/admin.py`** (section 8c, "The owner's Admin page"): do what he said "Yes" to that needs a session, then
mark it done. Then give him, in plain words: the result in
dollars **and against the month's goal** (section 8c, "The goals, month by month"); **a numbered list of the improvements
found**, for profit first and for anything else on the site; and the question whether to go ahead with them. Change nothing on that list until he says yes. His words: "i jump on after 8 days
and it says oh we have these improvements to make, it lists them then asks if i want to continue and make the changes…
any improvement it found for the site in any way really but especially in making profit. There is no point having this
run if its not making profit. well over 100,000." If the reviews keep showing no edge, say that plainly and recommend
changing what it buys from, or stopping, instead of tuning without end.

**THE SEARCH FOR IMPROVEMENTS NEVER ENDS (the owner, 17 Oct 2026): "this needs to be continual never ending new ways to
improve, espeically as your AI gets smarter!"** Every session, not only the weekly review:
- Read "Improvements to come" (section 8c, the end of "Start here when resuming") and `check-tools/reviews/questions.md`:
  do what is due, close what the data now answers, and **add new ideas of your own every time** (at least five questions
  at a weekly review). An empty list is a failure of the session, not a sign that nothing is left.
- **Look again at what earlier sessions judged impossible or not worth it**, with fresh eyes: a newer, stronger model may see
  a better way, a better data source, or a flaw in an old conclusion. Say so when an earlier conclusion was wrong.
- **As AI models improve, retest the AI's own parts**: whether a stronger model chooses buys or reviews holdings better
  (question 24 in `questions.md`), and what it is told (`choose`, `ai_review`, `write_lessons` prompts).
- The test is always the same and does not soften: dollars, the average a trade after costs against an S&P 500 fund,
  30 trades a group, an idea replayed on past prices first and put live only as a trial beside the current rule.

---

## 1. What the site is

- AI-assisted stock/ETF/crypto research tool for individual investors: single-stock reports,
  trading signals, market screeners (US, Europe, Asia, other), crypto screener, AI chat.
- 3-day free trial (5 analyses/day = 15 total), then Starter $4.99, Pro $14.99, Elite $49.99 per month (Stripe).
  Every logged-in account has the practice portfolio (fake money, by hand); **paid plans add the AI
  autopilot** that runs it (section 8c).
- Traffic is very low (a few visits/day; 13 visitors/month in March 2026), revenue $0.
  The main goal is organic search traffic, then conversions.
- Owner edits in **Kiro** (not VS Code). The top folder is still named `/Users/dave/VSCODE`.

## 2. Architecture

```
Browser ──> CloudFront (EHXV50CPHY07R, www→apex redirect function)
              └─> S3 bucket stockiq-final-websitebucket-vqekic7enf9h (static files)
Browser ──> Lambda function URLs directly (no API Gateway; 1,056 functions, 1,041 with URLs, ~715 are screener workers)
              ├─ analysis-functions.js: single-stock report, signals, screener workers, charts
              ├─ index/dashboard/sidebar: market data, gainers/losers/trending, email capture
              └─ auth.js: usage/trial trackers
Browser ──> Cognito (user pool us-east-1_P4lqPzrlY, tokens in localStorage), Google/Facebook login, Stripe
Lambdas ──> Yahoo Finance + Finnhub (data), OpenAI gpt-4o-mini (AI chat), DynamoDB, S3
```

- S3 versioning is **Suspended**: an overwrite cannot be rolled back from S3. Rollback comes
  from the deploy script's daily backups in `~/VSCODE/backup/` (see section 3).
- `stockiq/lambda-sync/` is a local mirror of the deployed Lambda code, refreshed hourly by the
  deploy script. It is gitignored. Read it to see what production runs.

## 3. Folders and git repos

| Folder | GitHub repo | Notes |
|---|---|---|
| `/Users/dave/VSCODE/website/` | `davedewit/stockiq-website` | What is served. `stocks/` and `.last_*` markers are gitignored, so stock pages exist only locally and on S3 |
| `/Users/dave/VSCODE/stockiq/` | `davedewit/stockiq` | Scripts, Kiro steering, `check-tools/` (end-to-end test scripts, section 8b), **`workers/` (the one source file every share-screener worker runs, with its build, proof and deploy tools: section 8b)**. `lambda-sync/`, `.analysis_cache/`, `*.json` are gitignored |
| `~/VSCODE/backup/` | – | Daily backups made by every deploy: `website_backup_<UTC time>` and `stockiq_backup_<UTC time>`, 30-day retention. **This is the backup**, including `stocks/`, which GitHub does not have |

**Restoring:** folder names use UTC (`website_backup_20260925_034730` = 13:47 AEST on 25 Sep).
- Hand-edited files and scripts: `git checkout <commit> -- <file>` (both repos are on GitHub).
- Stock pages: copy back from a backup, e.g.
  `rsync -a ~/VSCODE/backup/website_backup_<time>/stocks/ ~/VSCODE/website/stocks/`,
  then deploy (dry run first).
- The live site is simply whatever the last deploy uploaded; restore locally, then redeploy.
- **The daily backup does not include Lambda code.** Both copies are made with `--exclude='lambda-sync'` (`deploy-to-s3.sh`),
  and `lambda-sync/` is not in git either, so a Lambda's old code exists only where someone kept it:
  - **`~/VSCODE/backup/lambda_full_20261011_before_one_worker_code/`**: every one of the 984 functions as it was live at
    12:20 UTC on 11 Oct 2026, before the share-screener workers were moved to one code base (`functions.tsv` names each
    function's zip and fingerprint, `packages/` holds the 385 distinct zips, `README.txt` has the restore command). Its
    name has no `_backup_` in it on purpose: the deploy deletes `*_backup_*` folders after 30 days.
  - `~/VSCODE/backup/workers_before_onecode_20261011/`: the same day's old package of each of the 669 share-screener workers.
  - the single zips kept before each Lambda change (`<function>_before_<name>_<date>.zip`, listed in section 8c).
  - The share-screener workers' code is the exception: it is in git (`stockiq/workers/`), and so in the daily backup too.

## 4. Generated vs hand-edited (most important rule)

**Never hand-edit generated output. Change the generator.**

| File | Owner | How to change it |
|---|---|---|
| `stocks/*.html` layout, head, footer | `generate-stock-pages.py` template | Edit the template, run the script (manual, not daily). It keeps the NEWS/RELATED/ANALYSIS sections, robots value, data descriptions and dateModified |
| `stocks/*.html` NEWS section | `update_stock_news.py` (daily) | Script only |
| `stocks/*.html` RELATED section ("People also watch") | `people_also_watch_stocks.py --missing` (daily) | Script only |
| `stocks/*.html` ANALYSIS section, robots, meta description | `update_stock_analysis.py` (daily) | Script only |
| `news.html` article list | `update_news.py`, `update_stock_news.py`, then trimmed by `finalize_news_html.py` | Head and footer are preserved by all writers, so hand edits there stick |
| `news.js` (sidebar, 100-item pool) | `update_news.py`, `update_stock_news.py` | Script only. **The file holds its own display code** (`renderNewsItems`, written into it by both scripts: change the two alike). It shows the newest general article and the four newest stock articles **by each item's `timestamp`**, whatever order the file is in. Check: `node check-tools/news_sidebar_test.js` |
| `sitemap.xml` | `update_sitemap.py` (daily), `generate_sitemap.py` (manual) | Scripts only |
| `index.html` "Stock Pages" section (between `<!-- STOCK_LINKS_START/END -->`) and `stock-pages.js` | `update_home_stock_links.py` (daily, after the snapshot step; since 18 Oct 2026) | Script only. The rest of `index.html` is hand-edited |
| `stocks.txt` (3,467 symbols, CSV) | Hand-edited + `fetch_stock_data.py` | See `stocks-txt-csv-format.md` |
| `index.html`, `about.html`, `faq.html`, `analysis.html`, `dashboard.html`, guides, legal pages, `*.js`, `styles.css` | Hand-edited, no generator | Edit directly |

Stock page lifecycle: `fetch_stock_data.py` → `stocks.txt` → `generate-stock-pages.py` →
section scripts fill NEWS / RELATED / ANALYSIS. Every section script only replaces text between
its own `<!-- X_SECTION_START/END -->` markers.

Stock page order: header, **ANALYSIS snapshot**, "Full report" CTA card, NEWS, RELATED, footer.

## 5. Daily pipeline

launchd `com.stockiq.reminder` fires every 10 min → `~/stockiq-daily.sh` runs once a day
**Mon–Sat, 11am–10pm** (lock `/tmp/stockiq-deploy-YYYYMMDD.lock`) → `deploy.sh` →
`deploy-to-s3.sh` with `UPDATE_STOCK_NEWS=true`. Log: `~/stockiq-daily.log` (cleared each run).
The hours are the **machine's own clock** (`date` in `~/stockiq-daily.sh`). On 11 Oct 2026 this Mac was
set to UTC+7, not Sydney time, so "11am–10pm" was 04:00–15:00 UTC; check `date` before working
out when the next run is.

Order inside `deploy-to-s3.sh`:
1. `update_news.py`: Yahoo/Google RSS → OpenAI summaries → news.html + news.js (2-hour cooldown)
2. `update_stock_news.py`: per-stock news into stock pages + news.html/news.js (23-hour cooldown per stock)
3. `update_stock_analysis.py` (**daily run only**: it sits inside the `UPDATE_STOCK_NEWS=true` block, so a plain `./deploy-to-s3.sh` prints "Skipping stock data snapshots"): data snapshots on all 3,467 stocks, sets index/noindex on large caps (≥$10B), writes `indexable_stocks.txt`. ~20 min, no API cost. 404s for delisted stocks are normal/cached. When Yahoo has no price for a stock it keeps yesterday's snapshot and does not de-index it. Then `update_home_stock_links.py` rewrites the home page's "Stock Pages" section and `stock-pages.js` (section 6). Straight after it, in the same block, `publish_company_figures.py` publishes the company figures the single-stock report uses for shares outside the US (section 7, "The single-stock report"); it never stops the deploy.
4. Backups (website + stockiq; prod_scripts every 23h)
5. `people_also_watch_stocks.py --missing`
6. `update_sitemap.py`: **rebuilds** stock URLs from `indexable_stocks.txt` (not all HTML files), updates lastmod on site pages. Refuses if list < 200 entries.
7. `cleanup_broken_links.py`, `remove_news_duplicates.py`, `finalize_news_html.py` (trim news.html to 240 stock + 60 general, keep noindex)
8. S3 upload:
   - `stocks/`: `aws s3 sync --delete` (size + mtime), 24h cache
   - `js/`: sync --delete
   - root `*.html`, `*.css`, root `*.js`: uploaded when the local MD5 differs from the S3 ETag
   - **How long a copy may be kept (since 11 Oct 2026; `HTML_CACHE`, `ASSET_CACHE`, `NEWS_JS_CACHE` in the script):** a
     browser must ask again for a root page every time (`max-age=0, s-maxage=3600, must-revalidate`) and keeps a root
     script, stylesheet or `js/` file for five minutes (`max-age=300, s-maxage=86400`; news.js `s-maxage=3600`).
     CloudFront keeps them for the `s-maxage` and is emptied by the invalidation that ends every deploy. Before that
     browsers kept pages an hour and scripts a day: see section 9, "A fix that is live but not seen". The stock pages
     are still 24h
   - images (7d), and `stocks.txt robots.txt sitemap.xml`
9. CloudFront invalidation `/*` (waits for completion), `notify_search_engines.py` (IndexNow; "202" means accepted)
10. `sync-all-lambdas.sh` (hourly cooldown)
11. Git: for **both** repos, commit if changed → `pull --rebase` → push, unless the last
    push by this step was under 23h ago. Full rules and timing examples in section 5b.

Preview without uploading or pushing: `cd stockiq && DRY_RUN=true ./deploy-to-s3.sh`.
It still runs the local steps (backups, sitemap, news trim), then prints `(dryrun)` lines.
The script lost this mode once (section 9): check `grep -c DRY_RUN deploy-to-s3.sh` is above 0 first.

## 5b. GitHub: how and when changes get pushed

**Short answer: yes, changes go to GitHub automatically.** Every deploy, whether it's the daily
launchd run or a manual `./deploy.sh` / `./deploy-to-s3.sh`, ends with the same git step.
There is only one push mechanism.

**Two repos, both on `main`, both handled by that step:**
- `website/` → `davedewit/stockiq-website`: site files, news.html, news.js, sitemap.xml.
  `stocks/*.html` is **not** in git (gitignored), so stock pages exist only locally, on S3 and in backups.
- `stockiq/` → `davedewit/stockiq`: scripts, `indexable_stocks.txt`, Kiro steering.
  `lambda-sync/` and `.analysis_cache/` are not in git.
- Before 25 Sep 2026 the step only handled `stockiq/`, which is why the website repo fell
  months behind. Both are handled now.

### The git step (end of `deploy-to-s3.sh`)

1. **Cooldown check:** reads `website/.last_git_push` (a Unix timestamp). If less than
   **23 hours** (82,800 s) have passed, it prints "Skipping git push (less than 23 hours ago)"
   and does **nothing**: no commit and no push. Local changes simply wait.
2. Otherwise, for `stockiq/` then `website/`:
   - If `git status --porcelain` shows changes: `git add -A` and commit
     `"Auto-update: <UTC time>"` (this includes any uncommitted hand edits)
   - `git pull --rebase` (brings in commits made elsewhere). On conflict: `git rebase --abort`
     and log "could not rebase onto GitHub (conflict) - not pushed, needs a manual look";
     that repo is skipped, the other still runs
   - If nothing is ahead of GitHub: "already up to date on GitHub". Otherwise `git push`
     ("pushed to GitHub", or "git push failed (will retry next deploy)")
3. The marker is rewritten with the current time **only if both repos succeeded** (pushed or
   already up to date) and it is not a dry run. After any failure it retries on the next deploy.

The git step runs last, after S3, CloudFront and the Lambda sync. If the deploy aborts earlier
(no internet, or an S3 command failing 3 times), there is no push that day.
`DRY_RUN=true` only prints what it would commit and push, and never touches the marker.

### Timing in practice

- The daily run happens once a day, **Mon–Sat, between 11am and 10pm** (whenever the 10-minute
  launchd check first lands in that window). **There is no run on Sunday.**
- On normal days the runs are ~24h apart, so each daily run clears the 23h cooldown and pushes.
- **Whichever deploy first runs after the cooldown clears does the push.** Any other deploy
  inside the 23h skips the git step and only does S3.
- **A push from a deploy at an unusual time delays the next automatic push.** Example: a
  manual deploy pushes on Friday at 6pm → Saturday's 11am run is only 17h later and skips →
  there is no Sunday run → Monday's run pushes. Commits made in between wait until then.
- A plain `git push` typed by hand does **not** touch the marker, so it doesn't delay anything.
  Only the deploy script's git step (or someone writing the file) updates it.
- Check the state:
  ```bash
  date -r $(cat /Users/dave/VSCODE/website/.last_git_push)    # last push by the deploy script
  git -C /Users/dave/VSCODE/stockiq status -sb                 # "ahead N" = N commits not yet pushed
  git -C /Users/dave/VSCODE/website status -sb
  grep -E "Skipping git push|pushed to GitHub|up to date on GitHub|could not rebase|push failed" ~/stockiq-daily.log
  ```
  (`~/stockiq-daily.log` is cleared at the start of each run, so it only shows the latest run.)

### When the owner asks to "push" or "update GitHub" now

The deploy's git step won't push during the cooldown, so push directly:
```bash
cd /Users/dave/VSCODE/stockiq && git status -sb      # then the same in ../website
git add -A && git commit -m "<what changed and why>"   # descriptive message, not "Auto-update"
git log @{u}..HEAD --oneline                           # show the owner what will go up
git pull --rebase && git push
```
- Do both repos if both have changes. This does not change the marker (see above).
- Pushing to GitHub **does not update the live site**. Only the deploy script uploads to S3.
  To update the site too: `DRY_RUN=true ./deploy-to-s3.sh`, get approval, then `./deploy-to-s3.sh`.

### Changes made elsewhere (Claude cloud sessions, GitHub web edits)

- They arrive as a branch (e.g. `claude/new-session-…`) or as commits on `main`. Commits on
  `main` are pulled in automatically by the next push (`pull --rebase`); branches are not.
- To bring a branch in: `git fetch`, check that the branch doesn't touch files with uncommitted
  local edits, then `git merge --ff-only origin/<branch>`. Then deploy to make it live.
- Generated files (news.html, news.js, sitemap.xml) change every day locally. If a remote
  commit also changed them, keep the **local** version; they are regenerated anyway. A remote
  edit to them is the most likely cause of a "could not rebase" warning.
- Cloud sessions cannot see `stocks/` or run the pipeline. Stock page changes must be made in
  `generate-stock-pages.py` or a section script, then run locally.

## 6. SEO setup (set up 25 Sep 2026; numbers as of 10 Oct 2026)

- **Indexed stock pages:** market cap ≥ **$10B USD** and fresh price data → `index, follow` + data
  snapshot. That was 962 pages on 25 Sep and **957 on 10 Oct 2026** (about two thirds US; the
  rest TO, L, T, HK, AX, PA, DE, NS). The number moves a little as market caps cross $10B.
  All others (2,510, including delisted/renamed symbols with no data) → `noindex, follow`,
  with an empty snapshot section. The threshold is `INDEX_MIN_MARKET_CAP_USD` in
  `update_stock_analysis.py`. The owner chose to keep $10B for now; review after 6–8 weeks of
  Search Console data ($2B ≈ 2,000 pages; "any stock with data" ≈ 3,300).
- **Sitemap:** 974 URLs on 10 Oct 2026 (957 stocks + 17 site pages incl. about.html). news.html is excluded.
  `update_sitemap.py` refuses to touch stock URLs if the indexable list has < 200 entries.
- **news.html:** `noindex, follow`, newest 240 stock + 60 general articles, summaries cut to
  2 sentences (~0.4 MB, was 5.2 MB with 3,578 articles). Separate limits matter: stock news
  floods in daily and would otherwise push out all general news.
- **Why:** 3,400+ near-identical template pages looked like mass-produced thin content, and
  the site was getting almost no search traffic (603 of 3,469 pages indexed in March).
- **Structured data on stock pages:** `WebPage` + `about: Corporation {tickerSymbol}`,
  `dateModified` = data date. (Was a fake `NewsArticle` dated 2026-03-14 on every page.)
- **Analytics:** GA4 `G-WVETNMPF8V` on all content pages and all stock pages (before Sep 2026
  only 5 pages were tagged, so older GA numbers undercount).
- **Links to the stock pages (18 Oct 2026):** until then no page of the site linked to any stock page (they were reached only
  through the sitemap and each other's "People also watch"). The home page has a "Stock Pages" section (`#stock-pages`, after
  the guides): the largest indexed companies of each market by market value in US dollars (US 16, Canada, UK, Japan, Hong Kong,
  Australia 4 each, Europe 6, India 2; one share a company), rewritten daily by `update_home_stock_links.py` (it refuses with
  fewer than 20 links and leaves the page as it was). On the home page a share in the four market lists links to its stock page
  (`market-panel.js`, from `stock-pages.js`); on the dashboard the click runs the analysis as before. Not done: links from the
  guides; real figures in place of the home page's nine "Loading..." placeholders; Google Analytics events.
- `robots.txt` allows all and points to the sitemap. Canonicals are set on all pages.
- Bot checks in `auth.js` / `js/analysis-core.js` only skip login redirects and auto-run for
  crawlers; they do not hide content.

### Anonymous usage limits and bot protection

- Anonymous visitors get **1 analysis per day**; trial users 5 per day for 3 days. The use is
  checked and counted once, at the top of `runAnalysis`; never re-check after counting (section 8b).
- For anonymous visitors the page (`auth.js` → `checkStockAnalysisAccess`)
  asks Lambda `stockiq-daily-usage-tracker-anonymous` for usage and redirects to signup when
  usage ≥ 1. The limit is enforced **in the page**; the analysis Lambdas themselves are open URLs.
- 26 Sep 2026: a scraper ran ~145 analyses from ~130 different IPs (Alibaba Cloud 47.82.x,
  Tencent Cloud 43.119.x), each IP once, in bursts at 3–4am Sydney, with a normal Chrome
  user agent. Per-IP limits and user-agent checks could not catch it.
- Fix in the anonymous tracker (Sep 2026): uses the real source IP from the request (not the
  one the browser reports), blocks `BLOCKED_IP_PREFIXES`, limits each /24 network to
  `SUBNET_DAILY_LIMIT` (5) anonymous analyses per day (DynamoDB keys `subnet_<net>@<date>`, "@" so the daily email ignores them),
  and adds headless/automation words to the user-agent check. Blocked requests are answered
  with usage = 1, so the page stops by itself.
- Registration abuse is handled separately by `stockiq-ip-blocking-service` (5 attempts/hour,
  one account per IP per 4 days).
- Daily usage email: `stockiq-usage-report-emailed` (03:00 AEST).

## 7. Scoring (two different systems)

| Where | Model | Code |
|---|---|---|
| Single-stock report (analysis option 1) and the stock page snapshots | 0–100 score: starts at 50, ± points for RSI, trend vs 20/50/200-day MA, MACD, P/E, P/B, revenue growth, margin, debt, liquidity, ROE, 1-year change, volume, 52-week position; clamped 0–100. Thresholds 75/60/40/25 | Lambda `stockiq-option-1-1-custom-analysis/lambda_function2.py` → `calculate_unified_investment_score` |
| Screeners (options 3–5, 7) | 12 weighted factors: RSI 20%, MACD 20%, short momentum 18%, volume 10%, medium 8%, long 6%, financial 6%, Bollinger 5%, sentiment 3%, market 3%, risk 2%, MA trend 1% | screener worker Lambdas |

- `stockiq/stock_metrics.py` is an **exact copy** of the Lambda's scoring functions. If the
  Lambda's scoring changes, copy the functions again or the pages will disagree with the app.
  (Breakdown label text was aligned on 9 Oct 2026; pages strip the trailing parenthesis anyway.)
  `python3 check-tools/report/patch_metrics.py <the Lambda's file> stock_metrics.py stock_metrics.py` copies the functions
  across and stops if the two differ afterwards.
- Stock pages use Yahoo fundamentals (converted to Finnhub units: %, D/E ratio) because the
  Finnhub free key is shared with the live Lambda. **Page and app scores can still differ**: the page uses
  the previous close and Yahoo's figures, the app the live price and Finnhub's figures first (Yahoo's, from the
  pages' own cache, only for what Finnhub lacks). The largest cause of big jumps, a trend factor of +12 or -12 on
  the sign alone, was replaced by a graded one on 11 Oct 2026 (next part); RSI, MACD and the one-year change still
  score in steps (AAPL once showed 71 on the page and 47 in the app a day later).
- **The screeners are price, momentum and volume only.** Their "financial", "sentiment" and "risk"
  factors do not use real company data, and the 12 weights total 102% in the code (section 8b).
- **Every share screener is scored by one file since 11 Oct 2026** (`stockiq/workers/stock_worker.py`, section 8b "The worker
  groups"), so a stock scores the same whichever screener lists it. Before that the US and London workers worked out RSI as a
  plain 14-day average, the ASX and Nikkei workers by Wilder's smoothing (the standard, what charting sites show), and the
  NASDAQ 100 and Dow 30 workers had a "financial" and a "risk" factor of their own. All now use Wilder's RSI and the common
  factors. Crypto is a different program (section 8b "Crypto").
- **Neutral wording everywhere**, public pages and the paid product: "Strongly positive …
  Strongly negative signals" plus "not financial advice". No BUY/SELL labels, targets or stop
  losses are shown anywhere (section 8b). Until 11 Oct 2026 the model called its 1-year change "YTD"; it now says
  "over 1 year" (the pages' relabelling of "YTD" is left in and does nothing).
- `about.html` documents both systems, including the 102% and the price-and-volume-only note.
  Keep it in sync if scoring changes.

### The single-stock report and its chart: how they work now (rebuilt 11 Oct 2026)

The owner asked whether the individual stock analysis could be improved ("it took a long time to create back in the day
with an older version of AI"). The live report was run for a US share, an Australian one, a UK one and a fund and read
line by line. What was wrong, and what it does now:

- **Two functions.** `stockiq-option-1-1-custom-analysis` (`lambda_function2.py`, about 2,440 lines) fetches a year of
  daily prices from Yahoo, company figures, dividends, the VIX and the latest news from the share's own stock page,
  scores the share and writes the report text. It calls `stockiq-chart-generator` (`lambda_function_simple.py`) for the
  picture, which comes back inside the report text as a `data:` address. The pages can also ask the chart function for
  a chart by itself (`script.js`, `analysis-functions.js`: they turn the SVG text into a picture with `btoa()`, so **the
  chart's text must be plain ASCII**: a pound or yen sign is written as a character code).
- **Prices in the share's own currency** (`money()`, `currency_note()`; the currency comes with Yahoo's prices). Every
  share was printed with a dollar sign: BHP.AX "$60.94" (Australian dollars), IMB.L "$2662.00" (2,662 pence). Now
  "A$60.94", "2,662.00p" with a line "Prices for this share are in pence: 2,662.00p is £26.62", "¥2,910.50", "C$243.83".
- **One bar a day, and the latest session from the quote** (`bars_from_chart`: the same rules as the screener workers).
  ASX shares said "+0.00% today" after the close (Yahoo sends the last session twice); a London share whose latest bar
  arrives empty showed the price of the day before.
- **One RSI** (Wilder's, as the chart and the screeners use). The text said 47.3 under a chart that said 56: the report
  used a plain 14-day average, the chart Wilder's smoothing.
- **A trend factor that grows with the distance** (`trend_points`): up to 6 points for where the price is against its
  20-day average and up to 6 for where the 20-day average is against the 50-day, each in full at 2% apart
  (`TREND_FULL_AT`). Names: Strong Uptrend (9 or more), Uptrend (3 or more), Flat Trend, Mixed Trend (two clear halves
  that point opposite ways: a bounce inside a decline), Downtrend, Strong Downtrend. It was +12 or -12 on the sign
  alone: BHP.AX, up 45% in a year, read "Strong Downtrend: -12" for being 0.03% under its 20-day average, and a move of
  a few cents swung a score by 24 points.
- **One explanation of the score.** Under the breakdown stood a "detailed scoring methodology" that used other points
  (a one-year gain +7 where the breakdown said +3), did not add up to the score and quoted 40% / 40% / 20% weights that
  do not exist. It is gone. "How the score is built" now adds the breakdown's own points: "50 + 41 - 28 = 63". The
  company-figure lines use the score's own thresholds (`company_figure_lines`): a figure could read "Weak" in the
  breakdown and "Adequate" below it.
- **Company figures for shares outside the US.** Finnhub (free plan) has them for US shares only, so every Australian,
  UK, Japanese, Canadian, European and Hong Kong share was scored on price alone while the report listed "fundamental
  metrics". **Yahoo's own summary cannot be read from AWS or from a script**: it answers "429 Too Many Requests" to
  anything that is not a browser (tried in the first deploy, taken out again). What works: `update_stock_analysis.py`
  already keeps Yahoo's figures for every stock on the site in `.analysis_cache/info/`.
  **`publish_company_figures.py`** puts them, in the score's units, into one private file,
  `s3://stockiq-dynamic-stock-lists/site-data/company_figures.json` (3,333 stocks, 570 KB; refuses to upload fewer
  than 1,000; leaves out figures older than 75 days). The daily deploy runs it straight after the snapshot step (it
  never stops a deploy; a dry run only builds the file). The function reads the file once per warm container and for six
  hours (`site_company_figures`), fills only the figures Finnhub did not have (`fill_missing_figures`), for shares only
  (a fund gets none), and the report says "Company figures from Yahoo Finance (as of 5 Oct 2026)" or "from Finnhub and
  Yahoo Finance (…)". A share that is not on the site, or a file that cannot be read: "Company figures were not
  available for this share. The score above is therefore built from price and volume only".
- **Smaller things:** "YTD" is called the one-year change it is; "Breaking news (last 24 hours)" is "Latest news" (the
  article can be days old); "Oversold (Buy signal)" / "Overbought (Sell signal)" lost their brackets (advice wording
  that the Oct 9 pass had missed); volume is compared with the 20-day average the score uses (a line labelled "20-day
  average" printed the year's); while a session is still open its part-day volume is left out of the score
  (`partial_day`; it read "Low Volume: -3" every morning); "Liquidity Crisis" is "Low Liquidity"; filler lines removed.
- **Times in the visitor's own zone** (the owner noticed: the latest article read "1:31 PM UTC" in the report and
  "8:31 PM GMT+7" on the share's stock page). The report took the page's own text, which is UTC until the page's script
  (`js/timezone-converter.js`) rewrites it in the browser. It now reads the article's `data-timestamp` and writes it in
  the visitor's zone, in that script's own format (`local_news_date`), from the `timezone_offset` the analysis page and
  the dashboard already send; with no offset it stays as the page has it. "Analysis Generated" names its zone
  (`zone_label`: "(GMT+7)"; with no offset the report's time is five hours behind UTC, as before, and now says so).
- **It reports on a coin too (12 Oct 2026), and the "single coin" button uses it.** The button had a function of its
  own, `stockiq-option-7-2-worker-1`: a third copy of the old crypto worker (1,133 lines) with its own scoring and its
  own RSI (45 for Bitcoin where this report says 53). Tried on Bitcoin, the report function already worked. Now a
  request with `"asset": "crypto"` names coins by their symbols (`{"symbols": ["SUI"], "asset": "crypto"}`): each is
  priced by the crypto screener's ticker for it (`coin_ticker`, `COIN_TICKERS`: SUI is `SUI20947-USD`; **the same
  pairs as `COINS` in the orchestrator and `CRYPTO_TICKER_MAP` on the page: keep the three in step**, `report_test.py`
  compares this one with the orchestrator's). A coin's report (`_report_ctx['coin']`; also for a ticker like `BTC-USD`
  typed as a stock) is headed "🔍 SINGLE COIN ANALYSIS: SUI", says which ticker it was priced by and warns for the
  27 symbols known to be another coin there (`COIN_WRONG_MATCH`), says "since 00:00 UTC" for the day's change (a
  coin's day runs from midnight UTC), measures volume on the last full day, and leaves out what belongs to a company
  or the stock market: company figures, dividends, the VIX, the stock page's news (none of them is even asked for:
  one request to the price source, then the chart). Its score is the technical part of the 0-100 score. A background
  run is saved as "`<SYMBOL>` Coin Analysis" with `analysisType` `crypto_single`, which is how the dashboard knows a
  single-coin entry. **A share's report is the same character for character** (the tests compare ten sample shares
  with the code that was live). Page: `runAnalysis(72, 'single')` and `formatSingleCoinResult` in
  `analysis-functions.js`; dashboard: the `crypto_single` branch of "Run in Background". **`stockiq-option-7-2-worker-1`
  is now called by nothing**; it is left in place and can be deleted with the other unused functions.
  Not checked: the dashboard's background run and the saved entry for a real signed-in account.
- **The chart** (`draw_chart`) is drawn from the very prices the report scored, sent to it by the report with its
  support and resistance (`series`, `currency`, `support`, `resistance` in the request), so picture and text cannot
  differ; asked by itself it fetches its own with the same rules. Averages and RSI start when they have their days (they
  were padded: flat lines, then a jump); the 200-day average is on it; it has no background of its own and mid-tone
  lettering, so it sits on a dark page; **lettering grows when the picture is shown small** (a rule inside the SVG:
  `@media (max-width:480px)`, which a browser applies to the size the picture is shown at); 21 KB (it was 79 KB, and a
  saved report 115 KB: now about 35 KB).
- **Scores moved, and the stock pages with them.** On saved prices for 106 US shares the page score moved 6 points on
  average (27 of them by 10 or more, no lean up or down), mostly from the RSI method. `stock_metrics.py` carries the
  same functions; the pages follow at the next daily run. **None of this makes the score better at predicting**
  (section 7b): it makes the report correct and consistent.
- **The functions' code is still not in git, and the report's cannot be yet: it holds the Finnhub key in the code.**
  What changed is kept as the scripts that made the change: `check-tools/report/changes-2026-10-11/` (run in order
  against the copies in the rollback zips they rebuild the live code exactly). Tests:
  `python3 check-tools/report/report_test.py <the file from ~/VSCODE/backup/stockiq-option-1-1-custom-analysis_before_report_20261011.zip> lambda-sync/stockiq-option-1-1-custom-analysis/lambda_function2.py`
  (103 checks: the old code and the new on the same saved prices, `--show SYMBOL` prints a whole report) and
  `python3 check-tools/report/chart_test.py lambda-sync/stockiq-chart-generator/lambda_function_simple.py lambda-sync/stockiq-option-1-1-custom-analysis/lambda_function2.py`
  (29 checks). A live report without saving anything: POST `{"symbols":["BHP.AX"],"userId":"nobody-deploy-check@example.com","skipHistorySave":true}`
  to the function's address (with no `userId` it is treated as a background run and **saved**).
- **Live** (03:16 UTC, 12 Oct 2026): `stockiq-option-1-1-custom-analysis` `I84SxSgLYNt7z4XcxPEOaFvZtYJhOT6qALoTeuZtXuo=`,
  `stockiq-chart-generator` `OIDrZ2W9G3lJ2sKarnoT4c7RvoLh1ApDX43NWjR72z4=`, both equal to their mirrors. Checked with
  the live report for AAPL, BHP.AX, IMB.L, 7203.T, SHOP.TO and SPY, through the page's own code (`page_run.js 1 custom`),
  and by looking at the live chart at desktop and phone width on light and dark. **Not checked:** the analysis page
  itself in a browser, a real phone, the dashboard's "Run in Background" for a single stock.
  Rollback zips, in order: `~/VSCODE/backup/stockiq-chart-generator_before_report_20261011.zip`,
  `stockiq-option-1-1-custom-analysis_before_report_…`, `…_before_figures_…`, `…_before_source_…`, `…_before_newstime_…`, `…_before_coin_20261012.zip`.
- **Left as it is:** the first line still says "(REAL-TIME DATA)", as every screener's does (one wording decision for
  the whole site); MACD still scores +8 or -8 on its sign and RSI in steps at 30 / 40 / 60 / 70; valuation is counted
  twice for a share with a high P/E and a high price-to-book; the Finnhub call is still made for shares it never has;
  the report's time is the visitor's only when the page sends its offset.

## 7b. Does the screener score predict anything? (backtest, 10 Oct 2026)

The owner asked for a way to see whether the analysis "works in his favour" using fake money. First
answer: a replay of the S&P 500 screener over two years (10 Oct 2024 – 9 Oct 2026, 501 trading days,
502 stocks), using the unchanged live worker code on the prices it would have had each day. The
replay reproduced that morning's live scores exactly (502 of 502). Tools and full output:
`stockiq/check-tools/backtest/`.

- **$100,000 following the top 10, bought at the next morning's open:** changed weekly $150,177
  with no costs, $141,786 at 0.03% per trade, $123,969 at 0.1%; changed daily $159,601 / $128,312 /
  $77,086 (almost the whole account is replaced every day, so costs decide it); changed monthly
  $132,153. Index fund (SPY) $134,752; an equal amount in every stock $129,823.
- **Against luck:** 6% (daily) and 11% (weekly) of 300 random 10-stock portfolios did better than the
  top 10 before costs; monthly, 43% did. The top 10's lead over the average stock is +0.07% a day,
  +0.12% a week, +1.05% a month, none of it statistically clear (t 1.2, 0.5, 0.4).
- **The score does not sort good from bad.** The bottom 10 also beat the average stock, and held for
  a month did best of all ($193,505). By label, "Strongly negative" stocks rose most over the next
  week (+0.62%), "Strongly positive" +0.32%, "Mixed" +0.29%: the labels carried no information in
  this period.
- **Conclusion:** a small, unproven edge at a day to a week before costs, nothing at a month, and
  no support for the signal labels or the "model probability" figure. Limits: today's index members
  used throughout, no dividends, one rising market.
- Not done yet: the same test for the other screeners and crypto, and a test of each of the 12
  factors separately (to find which ones help and re-weight the score). The live paper portfolio
  now exists: the dashboard's practice portfolio and its autopilot (section 8c), whose own record
  is the forward test.
  Do not publish any of this as a promise; if shown to users it is past performance with the limits.
- **This two-year test used the US workers' RSI of the time** (a plain 14-day average). Since 11 Oct 2026 every screener uses
  Wilder's RSI (section 7), which changes about a third of US signal labels and three or four of a day's top 10, so the dollar
  figures above describe the scorer as it was. It was not run again (its 502 price series are not on this machine); the
  studies that could be run again say the same thing as before (end of this section).

**Factor by factor (11 Oct 2026).** The owner asked whether the scoring that produces the screeners'
CSV could be improved to raise the chance of profit, with "70% profit, 30% loss" as the aim. Tool
and full output: `check-tools/paper-test/factor_study.py`, `results-factors-2026-10-11.txt` (the S&P
100 worker's own code replayed on saved prices, 101 stocks, 999 trading days, 17 Oct 2022 – 9 Oct
2026; no downloads; about 100 seconds).
- **None of the score's own factors had a reliable link with what a stock did next** (day, week or
  month): RSI, MACD, short / medium / long momentum, Bollinger, sentiment, MA trend all inside the
  margin of error, several with opposite signs in the two halves of the period. The final score:
  +0.19 points a week for its top fifth over its bottom fifth (t 1.3). The labels: nothing.
  Volume, Market and Risk are the same for nearly every stock on a day, so they cannot sort.
  The "Financial" factor looks clear (t 2.3–2.6) but **is an artefact**: it is the hard-coded guess
  per company name (section 8b), which happens to favour the companies that rose.
- **Two raw figures did point the right way in both halves:** how jumpy a stock is (`atr`, t 3.5)
  and how far it is above its 52-week low (t 2.6). The first is risk, not skill: a score built
  from the two had a top 10 that moved 2.2 times as far as the list in rising weeks and 1.4 times
  as far in falling weeks, worst month -32% against -12%, and half its lead went when the seven
  chip / AI names were left out. **The second kept a modest lead among equally jumpy stocks:**
  +0.40 points a week, +1.5 a month (t 2.0, same sign in both halves). That is the known momentum
  effect, flattered here by using today's index members.
- **A win rate is set by the selling rule, not by skill.** Under the autopilot's own rules 45–51%
  of trades ended up, for the score's top 10 and for any stock alike. A rule built to "win" (sell
  at +2%, loss limit -15%) ended up 76% of the time for the top 10 and 74% for any stock at all,
  and made no more per trade than the rest. **"70% up, 30% down" can be had by anyone and says
  nothing about profit**; what counts is the average per trade against the average stock, and
  there the top 10's lead was +0.02 to +0.22 points a trade, never clear (t under 1).
- **Quick trading in shares loses to costs:** with 0.2% a trade taken off, one-day holds averaged
  -0.14% a trade and two-day holds -0.02%; 20-day holds +0.86%, most of it the market's own rise.
- **What was done with it:** nothing in the screeners (re-weighting 650 worker functions to one
  rising market's winner would be fitting to the past, and it is a product-wide change that is the
  owner's to decide). The autopilot now records how far above its 52-week low each share was when
  bought and splits its record by it (section 8c), so its own fake-money trades test the one
  finding that survived. **If that split shows the same after 8 or more trades a band, the next
  step is a trial of buying shares in that order**, beside the current order, through its trial
  mechanism. Not covered: coins (no saved prices; the entry log of section 8b is their test).

**The same studies with the one worker file (11 Oct 2026, evening).** When every share screener was moved to one file with
Wilder's RSI, the studies that read the worker's code were pointed at `workers/stock_worker.py` and run again on the same
saved prices. Nothing in their conclusions moved:
- Factor study (`paper-test/results-factors-2026-10-11-one-worker.txt`): the score's top fifth over its bottom fifth +0.06
  points the next day (t 2.0), +0.19 a week (t 1.2), +0.75 a month (t 1.2); it was +0.04 / +0.19 / +0.84. The RSI factor has
  no reliable link with what a stock did next under either way of working it out; every other factor's line is identical,
  figure for figure, which is also a check that nothing else in the scoring changed.
- Fake-money tests (`paper-test/results-backtest-2026-10-11-one-worker.txt`): Dow 30 top 10 +12.2% a year against +18.4% for
  the whole list (it was +16.8%); S&P 100 top 10 +40.4% a year against +25.2% (it was +43%), still inside the margin of error
  from a week out. **Their top 10 for the last close equal the live Dow 30 and S&P 100 pages name for name**: the replay
  reproduces the live scores with the new file.
- Replay of the autopilot's rules (`replay/results-replay-2026-10-11-one-worker.txt`; the earlier run is kept beside it, and
  `replay/panel.json` now holds the new scores): the five levels still end behind the index fund after costs, quick trading
  still loses, and buying the share furthest above its 52-week low without selling on the signal is still what holds up on
  the part of the period the search never saw.
- So there is no evidence for or against either RSI: the choice was for one way everywhere and the standard definition.

**Would limits set for each share do better than the same two numbers for all? (12 Oct 2026.)** The owner noticed that every
holding's plan reads alike ("sooner if it falls to -7% or reaches +12%") and asked whether the autopilot could be smarter.
What is per holding already: the stop that follows a rise (from the holding's own daily movement), the AI model's review,
and the choice of what to buy. What is the same for all: the loss limit, the gain mark, the holding time, the size.
`python3 check-tools/replay/replay.py --limits` (two seconds; `results-limits-2026-10-12.txt`) sets the loss limit and the gain
mark as multiples of each share's own daily movement, picks the multiples on the first 60% of the period and judges them on
the last 40%:
- These 101 shares move 1.5% (calm), 2.3% (middling) to 4.0% (jumpy) a day: not far apart.
- **It made no real difference.** Per trade against the index fund on the unseen part: Cautious -0.69 fixed, -0.46 with the
  chosen multiples; Careful -0.26 and -0.25; Balanced -0.33 and -0.33; Bold -0.35 and -0.32. None of it clear, and every
  level stayed behind the fund either way.
- **What it says:** for large shares the selling limits are not what holds the autopilot back; what it buys is (the score
  has no reliable edge, above). The ideas that did hold up are the ones already on trial or queued: the share furthest
  above its 52-week low, longer holding times, not selling on the signal.
- **Not tested, and where it could matter:** coins. A coin can move 5 to 15% in a day, so a -7% limit is an ordinary dip
  for one and a real fall for another. There are no saved coin prices to replay; the honest route is a live trial in the
  autopilot (every second coin with limits scaled to its own movement, kept only if clearly better), through its trial
  mechanism. Offered to the owner on 12 Oct; not built.

**The screener score against momentum scores, on markets it was never tuned on (17 Oct 2026; the owner: "go ahead and look into
improving it").** `check-tools/scoring/score_study.py` (the S&P 100, from the replay's panel) and `wide_study.py` (five years of
daily prices for 1,750 shares fetched through the price function on AWS, `fetch_wide.py` → `research-data/prices/`, not in
git: S&P 400 + 600, FTSE 100, DAX 40, CAC 40, AEX, SMI, Nikkei 225, ASX 200, TSX 60). The candidates were written down before
the wide result was seen; the live score is the workers' own code run on each week's prices. Results:
`results-2026-10-17.txt`, `results-wide-2026-10-17.txt`. **$100,000 in the top 10, changed weekly, 0.1% off each trade, against
the same money spread over the whole list, in 18 half-periods (9 lists x 2 halves):**
- **The live score beat its own list once in 18, an average of 16.5% behind it a half-period** (Nikkei first half $64,680
  against $124,465; S&P 400+600 $74,063 against $138,603). Its top tenth did no better over 5 or 20 days, and in three
  lists clearly worse. On the S&P 100 it was behind an S&P 500 fund in both halves. **It is not neutral: it is worse than
  picking the whole list.** The likeliest reason, from its code: half its weight rewards shares that have just fallen (RSI
  oversold +, near the lower Bollinger band +, "contrarian opportunity" +), the opposite of what the data rewards.
- **Far above the 52-week low: 14 of 18, +29% a half-period; the year's rise without the last month: 12 of 18, +22%; the
  "trend" mix (both, plus the 200-day average, less when RSI is over 80): 12 of 18, +18%.** Their top tenth was ahead over
  20 days in nearly every list and half, several with t near 2 to 3 (DAX, TSX, ASX).
- "Close to the 52-week high" did worse on the S&P 100 (not tried wider).
- **Limits:** today's members (flatters buying what rose, most for small companies); a mostly rising period 2022-2026; a
  top 10 of momentum shares is jumpier than the list (drawdowns not yet measured); the live 10-a-side trial of "furthest
  above the low" lost (-2.64% against -0.68%: too few trades to read, but not to be forgotten).
- **LIVE SINCE 10:55 UTC ON 17 OCT 2026 on all 25 share-screener groups, at the owner's yes: the trend score (version 2)** in `workers/stock_worker.py` behind a switch,
  `SCORE_VERSION` (1 unless `STOCKIQ_SCORE=2` is set; the Lambda has no such setting, so live stays 1). `trend_score()` is the
  study's "trend" exactly: up to +2 for how far above the 52-week low (full at 100%), the year's rise without the last month
  (+-1.5, full at 60%), +-0.5 for the price against its 200-day average, +-0.5 for the 50-day against the 200-day, -0.5 when
  RSI is over 80; its positive side x 0.6 (`TREND_POSITIVE_SCALE`) so that the labels spread as before, and even steps for
  the negative labels (`SELL_BANDS`). Every other figure the workers return is unchanged. **Tests:** with the switch off
  `workers/prove.py` finds every figure identical on all 24,718 stock-days (so the file in git can be deployed as it is
  without changing anything); with it on, the wide study gives the worker's own score 13 of 18 half-periods ahead of its
  list (+17.6% a half-period; the written-down "trend" 12 of 18: the worker computes what was tested), but **a deeper worst
  fall than the list in 15 of 18** (typically -15 to -20% against -8 to -15%): a bumpier ride; the label spread on the S&P 100
  over four years: Strongly positive 8% (9% before), Positive 22%, Slightly positive 31%, Mixed 15%, Slightly negative 11%
  (2% before: the old bands hardly gave it), Negative 10%, Strongly negative 3%; on a live run AAPL +1.5 and BHP.AX +1.8.
  **What it changes for users:** about 82% of signal labels and on average 8 of each day's top 10 (prove.py). **The
  autopilot's rules replayed with it** (`replay/results-replay-2026-10-17-trend.txt` against `…-original.txt`, the same
  tool and rules): Cautious +59% (was +48%), Careful +129% (+78%), Balanced +131% (+83%), Bold +99% (+12%), Adventurous -34%
  (-50%), against the fund's +107.5%; per trade against the fund Careful +0.78 (t 3.3), Balanced +0.30 (t 2.1), where the old
  score gave +0.02 and +0.03; worst falls about the same (Careful -14% against -17%, Balanced -17% against -15%). The replay
  is the S&P 100, where the 52-week-low idea was first found: in-sample, so the wide study is the stronger evidence.
- **How it went live:** `SCORE_VERSION` 2 by default (fingerprint `7W1kLqzu…`, `workers/live.txt`); Dow 30 first, its page and background runs read, then
  every group (all 741 functions, each group tried for real); eight buttons through the page code and five through the
  coordinator afterwards: every worker answered, the tracker read 10 symbols each time. The six public pages that described
  the 12 factors now describe the trend score. **The autopilot's trades from about 11:00 UTC on 17 Oct 2026 are bought from the
  new rankings: a review compares them with the trades before, never pools them.** Way back: `ROLLBACK=true bash
  check-tools/pending-trendscore/deploy.sh` is gone with the folder; instead set `SCORE_VERSION` to '1', build and deploy with
  `workers/deploy.py` (groups.txt `all`); the old package is `~/VSCODE/backup/workers_package_q9ZXUvTBcszKxRPR.zip`. Was the plan:
  `python3 workers/prove.py` again, a `check-tools/pending-<name>/` with `deploy.py` (Dow 30 first, then `all`), the 14+
  buttons through the page and the coordinator, `workers/live.txt`; `about.html` and the FAQ, which describe the 12 factors,
  rewritten for the trend score (its structured data with it); the AI chat's prompt if it names factors. The autopilot's trades
  before and after are different experiments. Also left as they are under version 2: `confidence` and the "model probability"
  still come from the old factors' sums (labels and ranks do not use them). Fixed on the way: `replay.py` part 4 dropped four
  figures when it ranked again without the chip names, and failed.

**The autopilot's own rules, replayed (11 Oct 2026, evening).** The owner asked, honestly, whether this will ever make
more than it loses, and whether it could "run on some kind of rapid speed to learn faster". It can: `check-tools/replay/
replay.py` runs the autopilot's rules (imported from the deployed function) over the same four years of S&P 100 prices
in 20 seconds, with 0.1% taken off each buy and each sale, decisions once a day at the close and trades at the next
open. Full output: `check-tools/replay/results-replay-2026-10-11.txt`. To keep it honest an idea is found on the first
60% of the days and judged on the last 40%, and compared with the same rules buying at random.
- **The five levels as they are all finished behind an S&P 500 fund** (+107.5% over the period): Balanced +92%, Careful
  +55%, Cautious +44%, Bold +26%, Adventurous -17%. Per trade none is clearly ahead of the fund.
- **Holding time decides most of it.** Everything else as Balanced: kept 1 day -4%, 2 days +29%, 5 days +92%, 10 days
  +97%, 20 days and longer +103% to +106%; without selling on the screener's signal, 20 to 60 days gave +112% to +115%.
  **Shares kept a day or two lose to costs at every level**; the automatic pace of Bold (2 days) and Adventurous (1 day)
  is that. The panel now says so when shares are ticked with a holding time of two days or less.
- **Selling when the screener's signal turns cuts winners short** in this replay: holdings were kept 4 to 7 days on
  average whatever the time limit, because the signal sold them.
- **Ranking by something else than the screener's score** (same rules, 20-day holds; first part → second part, per trade
  against the fund): the score +0.33 → +0.58 (never clear, luck better in 6%); furthest above its 52-week low +1.96 →
  +2.33 (t about 3 both times, luck never better); biggest rise over 90 days +0.88 → +3.50; over a year +0.59 → +2.46;
  the jumpiest stocks +1.64 → +2.97; the calmest and the lowest RSI clearly behind. That is momentum, and risk.
- **Why this is still not a reason to believe it:** the whole period was a rising market led by a few chip and AI names;
  without the seven of them the best variants' lead falls inside the margin of error (t about 1); the list is today's
  members, which hands any "buy what has risen" rule the survivors; daily decisions, no AI model in the loop. Of 240
  variants of the rules, 208 looked ahead on the first part and 103 on the second.
- **What it changes:** nothing is adopted from it. It says what is worth a forward trial with the fake money: the order
  shares are bought in (already on trial, section 8c), longer holding times for shares, and not selling on the signal.
  It also gives the owner one plain piece of information for his own settings: with shares, a holding time of a week or
  more. **Not possible here:** inputs about the company itself (profit, debt, growth). There are no past figures of that
  kind on this machine, so they cannot be replayed; the way to test them is forward (record them with each share bought
  and split the record), and they need a data source the function does not have.
- **The owner's question, answered plainly to him:** as built, it is unlikely to learn its way to steady profit; the
  inputs have shown no edge beyond momentum in a rising market; real money should wait for the bar (section 8c) and then
  be small; the likelier income is subscriptions. He chose to carry on in the order: replay, real costs, better inputs,
  the bar in writing.

## 8. Front end

- `analysis.html`: options 1–7 (stock/ETF report, signals, US/EU/Asia/other screeners, crypto).
  Logic in `analysis-functions.js` (169 KB: `runAnalysis`, the formatters) and, **since 13 Oct 2026, `screeners.js`**
  (99 KB of data: each share screener's list and worker addresses; section 8b, "The page's one screener routine") +
  `js/analysis-core.js`. How the screeners, signals and crypto work: section 8b.
- `dashboard.html`: report history, favourites, plans/upgrade (Stripe), manage subscription,
  "Run in Background" (through `stockiq-screener-coordinator`), 🎯 performance tracker. **Since 10 Oct
  2026 it has tabs under the heading: Reports (the statistics, Report History, auto-delete),
  Practice portfolio, AI autopilot** (section 8c). The plan sections ("Upgrade Your Plan", "Manage
  Subscription") stay below every tab, because other pages link to `dashboard.html#upgrade` and
  code scrolls there.
- `index.html`: market overview widgets, guides, "How StockIQ Works", **Pricing section**
  (`#pricing`, three plans in USD), email signup ("Get Screener Highlights by Email", details in
  `stockiq.md`), **"What you can do with StockIQ"** (`#features`: eight cards, one for each thing the site does) and, last,
  "What StockIQ is, and what it is not". **The page's wording was rewritten on 13 Oct 2026** (section 13): keep to it.
- **Practice portfolio and AI autopilot** (dashboard, built 10 Oct 2026): a fake-money portfolio the
  owner buys and sells in by hand, and an autopilot that trades it from the screeners' results,
  reviews its holdings with the AI model and recent headlines, and tries bounded changes to its own
  rules. `practice-portfolio.js`, `practice-autopilot.js`, Lambdas `stockiq-paper-portfolio` and
  `stockiq-ai-trader`. **Everything about them, and how to work on them, is in section 8c.**
- Stock pages load `sidebar.js` (an empty file since 18 Oct 2026: it was an old copy of the market panel's code, used by nothing there; the template no longer asks for it, so the tag goes at the next regeneration, and the file can then be deleted), `stock-prices.js` (live ticker), `ai-chat.js`, `auth.js`, `theme.js`.
- **Notification bell** (🔔 in the header of 18 hand-edited pages and of the stock pages): one list, drawn by
  `autopilot-bell.js` for every page, of the reports and the AI autopilot's buys and sells (section 8c, "The notification
  bell").
- AI chat button: bottom-right on the pages that load `ai-chat.js` (the home page, blog, the dashboard and the stock pages); on the home page it moves left of the news panel
  only from 1401px wide (the panel is hidden below that).
- Every public page footer carries a "General information only, not financial advice …" line.
- Theme: light/dark by time of day unless the user overrides (`localStorage.theme`).
- **The visitor's usage count is a chip inside the header bar** (13 Oct 2026; every page with the header and `auth.js`,
  the stock pages included): "1 free today", "3/5 today", "12/15 today", "Unlimited", "Trial ended", red when nothing is
  left. A click opens a small card that says it in a sentence with the one thing to do next ("Start free trial",
  "See the plans", "Your plan"). On a desktop it sits at the right-hand end of the bar, on a phone between the bell and
  the name; in a crowded bar it uses a shorter wording ("3/5", "Expired"), and with no room at all it drops just under
  the bar (`fit`, `under`).
  - **One place works the count out, one place writes it, one place shows it** (since the clean-up of 13 Oct 2026):
    `authManager.getStockAnalysisStatus` (`auth.js`) works it out; `displayTrialStatus()` in `auth.js` writes it into
    a badge, `#trial-status-display`, on every page when the page loads; **`theme.js` hides that badge before it is
    drawn and loads `website/visitor-bar.js`** (`?h=<the hour>`, no version to raise; `window.visitorBar`: `version`
    (2), `read, state, refresh`), which reads the badge's text whenever it changes and shows it in the bar. The hidden
    badge is only the channel between the two. On the analysis page `refreshUsageCount()` (`analysis-functions.js`)
    writes the new count into it after each use (three calls inside `runAnalysis`), and the chip pulses once when the
    number goes down. **The texts the badge can hold are listed at the top of `visitor-bar.js` (`read`): a change to
    their wording in `auth.js` must be taught to `read`** (an unknown text is shown as it is; "Status unavailable"
    shows nothing).
  - **The dashboard keeps a `displayTrialStatus` of its own, on purpose:** the same answer from the trial function also
    fills in its plan section (current plan, renewal date, the cancel button, the upgrade buttons' wording) and is
    kept as `userTrialStatus_<address>`. It writes the same texts into the same badge, so the chip follows it too. It
    is not a duplicate that can simply go; taking it apart needs a real paying account to check against.
  - **The one round button** ("🚀 Start 3-Day Free Trial" for an anonymous visitor whose free analysis is used, or who
    chose "Maybe Later" in the pop-up; "🚀 Upgrade Plan" for a signed-in visitor with nothing left or whose trial is
    over) is drawn by `visitor-bar.js` (`pill`, `#vb-pill`), bottom left, on the home page and the analysis page only,
    as before. `showStickyRegisterButton()` / `showStickyUpgradeButton()` in `analysis-functions.js` are two-line
    stand-ins that the pop-up and the access check still call. The home page's yellow "LIMITED TIME" bar is gone: it
    repeated the strip above it and the offer is not limited in time.
  - **What went in the clean-up** (the home page and the analysis script): the second badge each made at page load,
    five copies of the round-button code, three identical blocks and an unused function (`updateRemainingToday`) that
    animated the old badge, the scroll code that moved or faded it. `analysis-functions.js` lost 188 lines, and a page
    load makes one request fewer to the trial function. `auth.js` and `dashboard.html` were not touched.
  - **THE WAY BACK, in two steps, both kept on purpose** (`DRY_RUN=true` in front of either to preview):
    1. `bash /Users/dave/VSCODE/stockiq/check-tools/pending-cleanup-undo/deploy.sh` undoes the clean-up: it reverts
       the one commit in `website/` and uploads the four files; the chip stays. It tries the revert on a copy first
       and stops if a later change collides.
    2. then `bash /Users/dave/VSCODE/stockiq/check-tools/pending-banners-undo/deploy.sh` undoes the chip itself: it
       takes the switch out of `theme.js` (the lines between `VISITOR_BAR_START` and `VISITOR_BAR_END`) and puts the
       yellow bar back. It refuses to run before step 1.
    **Do not delete those two folders or the two marker lines while the chip is live.**
  - Test: `node check-tools/visitor_bar_check.js` (about seven minutes): seven kinds of visitor (anonymous with a free
    analysis left and without; on the trial with some left and with none; trial over; a paid plan with a daily count;
    no limit) x five pages x four widths (1500, 1024, 390, 320): 1,746 checks (the chip, its card, the round button,
    the count after a use, "Maybe Later"), and `SHOTS=<folder>` for pictures. A "signed-in" visitor there is a made-up
    address with a made-up session (`idToken` = any text whose middle part is base64 JSON with `email`, `exp`,
    `custom:tier`; `loginTime`; `userId`), and what the trial function would answer is supplied per visitor. **The
    site takes headless Chrome for a crawler and skips its sign-in check ("Bot detected"): a test must give the
    browser an ordinary name** (`Emulation.setUserAgentOverride`). After any change to `analysis-functions.js` also
    run `anon_run.js` and `trial_run.js` (they take `FUNCS=<file>`): same results and redirects as before.
  - **Not checked: a real phone, a real signed-in account, a real paying account** (all were made-up sessions).
- **The header bar on a narrow desktop window or a tablet** (769 to 1150px; `styles.css`, the two `@media` blocks above
  "Home link specific styling"): the menu sits in the row beside the name, with tighter spacing below 900px. On a wide
  screen it is centred on the page (`.desktop-nav` is `position: absolute; left: 50%`), and until 13 Oct 2026 it stayed
  centred at every width, so it ran over the name from about 1100px down. Those rules say `.desktop-nav .nav-item`
  with two classes on purpose: the plain `.nav-item` rule comes later in the file and would win. Checked by
  `WIDTHS=1150,1024,900,780 node check-tools/visitor_bar_check.js` ("the name and the menu do not run into each other").
- **The two panels that slide in on a phone** (up to 768px wide): the **market-data sidebar on the right** (home page and
  dashboard only; the green round button, or a swipe to the left) and the **menu on the left** (the ☰ button on the
  eight kinds of page that have it: home, analysis, dashboard, blog, news, sign in, sign up, stock pages; a swipe to
  the right on the three pages that load the script). **One script moves both: `website/mobile-sidebar.js`** (`?v=2`;
  loaded by `index.html`, `dashboard.html`, `analysis.html`; `window.mobileSidebar`: `version, open, close, toggle,
  isOpen, busy, last`). No page has swipe code of its own any more.
  - **How a panel moves:** it follows the finger (a quarter of a swipe shows a quarter of it; it can be pushed back in
    the same touch); let go with a third or more out and it comes out fully, otherwise it slides back; a quick flick
    decides either way; pushing it back works the same in reverse. A sideways finger pushes back the panel that is
    out, or pulls out the one on that side when both are in (`choose`). A swipe is left to what is under the finger
    when that is a text box, the portfolio graph (`#pp-chart-svg`), a slider of the analysis page, anything marked
    `data-no-swipe`, or a row that scrolls sideways and has room to go; and to the page while one of its pop-ups is up.
  - **The page behind never moves, and must never be given `position: fixed` or a height: that was the old way of
    stopping it scrolling, and it threw the page to the top.** For the sidebar the script sets `overflow: hidden` on the
    body. For the menu `styles.css` does it: `body.menu-open { overflow: hidden; position: relative; top: auto; height:
    auto }`, all `!important`, **which also undoes the `position: fixed` that older page code still writes on the body
    when ☰ is pressed** (`blog.html`, `news.html`, the stock pages' template in `generate-stock-pages.py`, the home
    page's own toggle and pop-ups). Those lines were left where they are: the stylesheet wins, so the stock pages
    needed no regeneration. If a page ever sets it with `setProperty(..., 'important')`, as the dashboard did, the
    stylesheet loses: do not.
  - **What each side keeps:** sidebar: the page's `fillMobileSidebar()` / `emptyMobileSidebar()` (move its two panels in
    and out), and it counts as open while `#mobile-sidebar-modal` has `style.display === 'block'` (`renderMarketDataSidebar` in
    `market-panel.js` draws into the sidebar's copy then; the page's `fillMobileSidebar` / `emptyMobileSidebar` call
    `marketPanel.refresh()`); the page's own `toggleMobileSidebar()` / `closeMobileSidebar()` are a fallback
    that the script replaces. Menu: the pages' own `toggleMobileMenu()` / `closeMobileMenu()` stay as they are; the
    menu is open while `#mobile-menu` has the class `open`; the script drags it by inline `left`, and when it has
    stopped sets the classes the pages set (shutting goes through the page's `closeMobileMenu()`).
  - Test: `node check-tools/mobile_sidebar_check.js index.html dashboard.html analysis.html blog.html news.html
    login.html signup.html stocks/AAPL.html` (`LIVE=1` for the site itself): a finger in headless Chrome at phone
    size; after every step, that the page has not moved. **Not checked: a real phone; Safari on an iPhone.** The
    pages without the script (blog, news, sign in, sign up, stock pages) open the menu by ☰ only, as before.
- **The market panel on the right of the home page and the dashboard is drawn by one script: `website/market-panel.js`**
  (`?v=1`, loaded by both pages where their panel code was; 18 Oct 2026, the owner: "is there a smarter way to set them up. the
  dashboard and index.html should match"). The market tabs and their figures (the tab on show fetched first, the six others a
  moment later), the four lists (which shares are on them, four small requests, then their prices in one), the US market
  countdown, the arrows (one tab a click: the home page had three sets of handlers), the scroll arrow and fade at the panel's
  foot. Each page keeps only its markup in `#news-panel` (the same on both; the home page also has its sign-in box for an
  anonymous visitor). It keeps the names the pages' other code calls (`renderMarketDataSidebar`, `fetchMarketDataSidebar`,
  `switchToTab`, `updateMarketCountdownSidebar`, `render<Trending|Gainers|Losers|Active>Tickers`, `fetchSidebarTickers`, and the
  globals `marketDataSidebar`, `currentTabSidebar`, `tabOrder`, `currentTabIndex`); `window.marketPanel`: `version, refresh,
  renderLists, deskStyle, openTab`. **It opens on the tab of the market trading now** (`openTab`, version 2, 18 Oct 2026: the
  owner asked whether the items could rotate as Yahoo's do; Yahoo's summary is a fixed list a country, `v6/finance/quote/marketSummary`,
  so the items stayed and the opening tab follows the clock instead): weekdays the US (9:30-16:00 New York), else Europe
  (8:00-16:30 London), else Asia (Tokyo, Hong Kong, Sydney or Mumbai in session), each on its own clock; at a weekend Crypto;
  when nothing trades, the US. A tab picked later stays for the visit. A row's click runs the analysis in the background where the page can (`runSidebarAnalysis`, the
  dashboard); **on the home page a share that has a stock page is a link to it** (version 3, `stock-pages.js`: the visitor
  sees the page first instead of spending an anonymous visitor's one free analysis, and Google finds the link); otherwise it
  opens the analysis page. Every 5 minutes while the page is in use; live-market.js keeps the figures
  on show moving. The phone sidebar (`fillMobileSidebar` / `emptyMobileSidebar` on each page) moves the panel and calls
  `marketPanel.refresh()`; the panel is put back with the style it had at load (`data-desk-style`; both pages put it back
  as `position: absolute` before). **The layout is each page's own, on purpose:** on the home page the panel scrolls with the page
  (the owner: it gives a visitor more reason to scroll down the page), on the dashboard it stays in view and scrolls inside
  itself, with the arrow and fade at its foot (you look at it and at your portfolio together). It was made the same for an
  hour on 18 Oct 2026 and put back. About 60,000 characters of the home page and 46,000 of the dashboard went.
  **`sidebar.js` was a third copy, with charts from random numbers, loaded by the stock pages, which have no panel: it was
  emptied on 18 Oct 2026** (a comment only, so the 3,467 stock pages need no regeneration). **The way back, one command:** `bash /Users/dave/VSCODE/stockiq/check-tools/pending-panel-undo/deploy.sh`
  (keep that folder). Tests: `live_market_check.js` (the tabs, the arrows, the four lists, the countdown, the layout, 32
  checks), `mobile_sidebar_check.js`, `header_room_check.js`, `visitor_bar_check.js`.
- **The market data moves while someone is looking at it** (18 Oct 2026; the owner: "they should update often so when users on
  the page they see its active not a static site ... only if user is active on page"). **`website/live-market.js`**, loaded by
  `theme.js` (between `LIVE_MARKET_START` and `LIVE_MARKET_END`: take those lines out to switch it off everywhere) on any page with
  the market-data side panel (`#market-data-sidebar-container`) or the movers lists (rows `gainer-`, `loser-`, `active-`,
  `trend-price-<symbol>`): the home page and the dashboard (stock pages have neither; their own price refreshes every 5 s).
  One request a round to `ticker-data-fetcher` for every figure on show (the movers from the lists the page saved,
  `<kind>TickersList`; the side panel's symbols from `marketDataSidebar`; the open tab from `.market-tab-sidebar.active`),
  every 6 to 10 s at random, **only while the tab is on screen and someone has moved, scrolled, typed or touched in the last 90 s**;
  a round that changes nothing makes the next gap half as long again, up to a minute (a closed market costs almost nothing), and
  a change or a return to the page brings it back. A figure that moves flashes green or red (`lm-up`, `lm-down`), each row a
  moment apart (the owner's own random delay). **The side panel's small charts were random lines** (`generateSparkline`): each is
  now that item's real prices for its latest trading day (the price function's `spark`, about 30 points; a green line is
  up on the previous close, red down). Futures (the Rates tab's 2- and 10-year notes, every Commodities item: `=F`) have no
  points in Yahoo's one-day chart until their session reopens, so the function takes the last trading day from the five-day
  chart (`last_session`). **Every tab's lines are fetched once in the background** (`fetchAllSparks`, at most every 5
  minutes) **and kept in the browser 20 minutes** (`lmSparks`), so a tab chosen later or a reload shows them at once; a line
  stays hidden until its real prices are in. `window.liveMarket`: `version, round, apply, movers, panelRows, sparkPoints,
  state`. The rest is `market-panel.js`'s (next part): every 5
  minutes while the page is in use it fetches the 7 side-panel categories and which shares are on the four lists (they were
  once a minute, and before 17 Oct every second). About 6 requests a minute while someone watches, none
  otherwise. **Found on the way:** the home page fetched the side panel's data every minute and never drew it ("Don't
  re-render"), so it showed the figures of the moment the page was opened. Test: `node check-tools/live_market_check.js
  index.html dashboard.html stocks/AAPL.html` (`WEB=<folder>` for a staged copy; the price function answered by a stand-in
  whose prices move; with `market-panel.js` too: the tabs, the arrows, the four lists, the countdown, each page's layout;
  36 checks).
- Live prices on stock pages (main ticker + "People also watch" cards) come from
  `stock-prices.js` → Lambda `stockiq-popular-prices`, refreshed every 5 s. Pages opened from local files
  show `--` (the proxy only answers the live site), which is expected.
- Utility page with no footer, not in the sitemap: `clear-cache.html`. (`market-data-sidebar.html`
  and `market-data-widget.html` called a Lambda that no longer exists and were deleted 10 Oct 2026.)
- Lambda function URLs are hard-coded in the JS/HTML. `stockiq/lambda-url-mapping.json` maps
  each URL to its function name. Regenerate it with `bash generate-lambda-url-mappings.sh`
  (it rewrites the file in place over a few minutes; don't read it meanwhile).

## 8b. Screeners, signals and crypto: how they work now (verified end to end 9–10 Oct 2026)

Everything in this section was checked by running every analysis button with real data
(method at the end). Read it before touching `analysis-functions.js`, the coordinator, the
crypto orchestrator or any worker.

### Two code paths, one set of lists

- **On-page run:** `runAnalysis(option, subOption, event)` in `analysis-functions.js` calls the
  worker Lambdas straight from the browser and formats the text itself.
- **"Run in Background" (dashboard):** `stockiq-screener-coordinator` calls the same workers
  server-side, formats the report and CSV, and saves them to the user's history.
- The stock lists therefore live in **two places that must stay identical**: the `list` of each
  entry in `website/screeners.js` (until 13 Oct 2026 the `*Universe` arrays inside `runAnalysis`) and `STOCK_UNIVERSES` in the coordinator. Exception: on the
  page path Russell 1000/2000 send only `worker_id`, and each worker takes its own ten stocks from
  `lists.txt` inside the worker package. **That file is the coordinator's two Russell lists**
  (`workers/lists.txt`; `workers/build.py` refuses to build if they differ, `build.py --lists` writes it
  again), so a page run and a background run now cover the same stocks. A Russell list change is therefore
  the coordinator, `lists.txt` and a worker deploy.
- Wording is applied only in those two places (plus the report Lambda and the crypto
  orchestrator). **Workers return data only, so a wording or list change never needs a worker
  redeploy.**

| Screener | Page call | Coordinator key | Worker group (count) | List size | Source of the list |
|---|---|---|---|---|---|
| Dow 30 | `3, '8'` | `3-8` | `stockiq-option-3-8-worker-N` (3) | 30 | slickcharts.com |
| S&P 100 | `3, '100'` | `3-100` | `stockiq-option-3-1-worker-N` (10) | 101 | Wikipedia |
| NASDAQ 100 | `3, '7'` | `3-7` | `stockiq-option-3-7-worker-N` (10) | 101 | slickcharts.com |
| S&P 500 | `3, '3'` | `3-3` | first 50 of `stockiq-option-3-5-worker-N` | 502 | Wikipedia |
| S&P 400+600 | `3, '2'` | `3-2` | `stockiq-option-3-2-worker-N` (100) | 995 | Wikipedia (400 + 600) |
| S&P 1500 | `3, '4'` | `3-4` | `stockiq-option-3-4-worker-N` (150) | 1,497 | Wikipedia (500 + 400 + 600) |
| Russell 1000 | `3, '5'` | `3-5` | `stockiq-option-3-5-worker-N` (100) | 877 | old list, dead tickers removed |
| Russell 2000 | `3, '6'` | `3-6` | `stockiq-option-3-6-worker-N` (200) | 1,829 | old list, dead tickers removed |
| ASX 50 / 100 / 200 / 300 | `5, '50'` … `'300'` | `4-50` … `4-300` | `stockiq-asia-5-1` … `5-4-worker-N` (5 / 10 / 20 / 30) | 49 / 99 / 195 / 294 | Wikipedia ASX 50 and ASX 200; 100 = largest 100 of the 200; 300 = the 200 plus live members of the old list |
| UK FTSE 100 | `4, 'ftse100'` | `5-ftse100` | `stockiq-europe-4-1-worker-N` (10) | 100 | Wikipedia |
| Japan Nikkei 225 | `5, 'nikkei225'` | `5-nikkei225` | `stockiq-asia-5-5-worker-N` (21) | 225 | Wikipedia |
| **Germany DAX 40** (since 13 Oct 2026) | `5, 'dax40'` | `5-dax40` | `stockiq-europe-4-2-worker-N` (4) | 40 | German Wikipedia's DAX page (members as of the review of 22 June 2026) |
| **France CAC 40** (since 13 Oct 2026) | `5, 'cac40'` | `5-cac40` | `stockiq-europe-4-3-worker-N` (4) | 40 | Wikipedia (composition effective December 2025) |
| **Netherlands AEX** (since 13 Oct 2026) | `5, 'aex'` | `5-aex` | `stockiq-europe-4-4-worker-N` (3) | 30 | Dutch Wikipedia (composition of 22 June 2026; the index has had 30 members since Sept 2025) |
| **Canada TSX 60** (since 13 Oct 2026) | `5, 'tsx60'` | `5-tsx60` | `stockiq-americas-6-1-worker-N` (6) | 60 | Wikipedia (as of 31 January 2026) |
| **Italy FTSE MIB** (since 13 Oct 2026) | `5, 'ftsemib'` | `5-ftsemib` | `stockiq-europe-4-5-worker-N` (4) | 40 | Wikipedia (updated 8 April 2026) |
| **Spain IBEX 35** (since 13 Oct 2026) | `5, 'ibex35'` | `5-ibex35` | `stockiq-europe-4-6-worker-N` (4) | 35 | The Madrid exchange's own list of main-market companies (read 13 Oct 2026) |
| **Hong Kong Hang Seng** (since 13 Oct 2026) | `5, 'hangseng'` | `5-hangseng` | `stockiq-asia-5-8-worker-N` (10) | 95 | Chinese Wikipedia (composition of 7 September 2026; the English page still had the 88 of January) |
| **Singapore STI** (since 13 Oct 2026) | `5, 'sti'` | `5-sti` | `stockiq-asia-5-9-worker-N` (3) | 30 | Wikipedia (2 May 2026; FTSE Russell's June and September 2026 reviews changed no member) |
| **Switzerland SMI** (since 13 Oct 2026) | `5, 'smi'` | `5-smi` | `stockiq-europe-4-7-worker-N` (2) | 20 | German Wikipedia (13 Oct 2025) with the changes of 21 Sept 2026 (Galderma and Sandoz in, Swisscom and Kühne+Nagel out). Roche is `RO.SW` (its bearer share): the index holds the Genussschein, `ROG.SW`, which the price source did not answer for |
| **India Sensex** (since 13 Oct 2026) | `5, 'sensex'` | `5-sensex` | `stockiq-asia-5-6-worker-N` (3) | 30 | Wikipedia's list of Sensex companies (latest change Dec 2025; the June 2026 review changed nothing). **Priced by the NSE listings (`.NS`)**: with `.BO` the worker got no usable history for some members (RELIANCE.BO, M&M.BO) |
| **South Korea KOSPI 200** (since 13 Oct 2026) | `5, 'kospi200'` | `5-kospi200` | `stockiq-asia-5-7-worker-N` (21) | 200 | The holdings of the KODEX 200 index fund on 13 Oct 2026 (the exchange's own lists need a login now). One holding left out: `0220W0.KS`, a new spin-off with too little history to score |
| **Brazil Bovespa** (since 13 Oct 2026) | `5, 'bovespa'` | `5-bovespa` | `stockiq-americas-6-2-worker-N` (8) | 76 | The São Paulo exchange's own portfolio of the Ibovespa, 13 Oct 2026 |
| **Euro Stoxx 50** (since 17 Oct 2026) | `5, 'sx5e'` | `5-sx5e` | `stockiq-europe-4-8-worker-N` (5) | 50 | German Wikipedia's Euro Stoxx 50 page (as of September 2026); symbols on the home exchanges (`.DE .PA .AS .MI .MC .BR`, Nordea `NDA-FI.HE`) |
| **Sweden OMX Stockholm 30** (since 17 Oct 2026) | `5, 'omx30'` | `5-omx30` | `stockiq-europe-4-9-worker-N` (3) | 30 | Nasdaq's own index data for 16 Oct 2026 (`indexes.nasdaqomx.com/Index/WeightingData`, id OMXS30); `.ST`, share classes with a dash (`ATCO-A.ST`) |
| **China CSI 300** (since 17 Oct 2026) | `5, 'csi300'` | `5-csi300` | `stockiq-asia-5-10-worker-N` (30) | 300 | The index provider's own file for 16 Oct 2026 (`oss-ch.csindex.com.cn/.../cons/000300cons.xls`); Shanghai `.SS`, Shenzhen `.SZ`. One share returns no data on a run (299 of 300) |
| **Taiwan 50** (since 17 Oct 2026) | `5, 'tw50'` | `5-tw50` | `stockiq-asia-5-11-worker-N` (5) | 50 | Chinese Wikipedia (members of 30 Sep 2025 with every change through the review of September 2026 applied); `.TW`. Its Top 10 comparison uses the TAIEX (`^TWII`): the Taiwan 50 index has no symbol at the price source |
| **New Zealand NZX 50** (since 17 Oct 2026) | `5, 'nzx50'` | `5-nzx50` | `stockiq-asia-5-12-worker-N` (5) | 47 | English Wikipedia's S&P/NZX 50 table (undated; S&P's announcements show no change in June or September 2026); three members no longer have prices (Arvida and Manawa Energy taken over, Goodman Property Trust not at the price source) and their replacements are not in the list |
| **Mexico IPC** (since 17 Oct 2026) | `5, 'ipc'` | `5-ipc` | `stockiq-americas-6-3-worker-N` (4) | 35 | **The holdings of BlackRock's NAFTRAC fund, which follows the index** (15 Oct 2026; `blackrock.com/mx/intermediarios/productos/251895/ishares-naftrac-fund/1501904811835.ajax?fileType=csv&fileName=NAFTRAC_holdings&dataType=fund`): S&P and the exchange refuse scripts. Symbols are the exchange's tickers with `.MX` (asterisk dropped; `PE&OLES.MX`, Liverpool `LIVEPOLC-1.MX`). **The exchange trades 13:30-20:00 UTC**, with New York; its daily close is an auction price, a little off the last quote |
| Crypto universe | `7, 'coinspot'` | `7-1` | orchestrator + 54 `stockiq-option-7-1-worker-N` | 540 coins | CoinGecko top by market cap, price-checked |
| Single coin | `72, 'single'` | – | the single-stock report function, `"asset": "crypto"` (since 12 Oct 2026; section 7) | – | – |

- The option numbers are inconsistent for historical reasons (ASX is page option 5 but
  coordinator `4-…`; FTSE the reverse). New screeners: use `5` + the same subOption everywhere.
- Russell 1000/2000 were **not** refreshed: no complete free source a script can read (iShares
  holdings URLs return a web page, Wikipedia has no list). ASX 300 is an approximation.
- Do not use asx50list.com / asx100list.com / asx200list.com / asx300list.com: years out of date.
- Yahoo symbol format: US share classes use a dash (`BRK-B`, not `BRK.B`); FTSE adds `.L`
  (`BT.A` → `BT-A.L`); ASX `.AX`; Tokyo `.T`. A symbol Yahoo does not know is silently dropped.
- Every symbol in a list was checked against the price source before being included. To check a
  symbol, call `stockiq-price-proxy` (`?symbol=X`; it answers 500 for an unknown symbol).
  **Do not probe Yahoo in bulk from this machine**: after a few hundred calls it returns HTTP 429,
  and the daily run's snapshot step then gets no prices (section 9).
- Button labels in `analysis.html`, the `universeSize` constants in the formatters and the
  coordinator's `universe_sizes` all carry the real list sizes. Update all three with a list.
- `NIKKEI_COMPANY_NAMES` in `analysis-functions.js` supplies names for the Nikkei output.

### The page's one screener routine (13 Oct 2026)

The owner called the analysis page "insane and a very large page" and asked for a look at "splitting it up or just
less repetitive". The page itself (`analysis.html`) is 34 KB; the size was its script, and in it `runAnalysis`:
1,943 lines, 175 KB, holding **14 copies of the same routine**, one for each share screener, each with its list and
its worker addresses written inside it.

- **Now:** `runShareScreener(def, subOption)` in `analysis-functions.js` runs every share screener, and a screener is
  one entry in **`website/screeners.js`** (`SHARE_SCREENERS`, keyed `'<option>-<subOption>'`, e.g. `'3-8'`): `name,
  list` (null = the workers hold it: Russell 1000 / 2000), `workers` (addresses in order), `use` (how many of them a
  run uses), `size` (the round number the reports print), `csv` (the file's name), `format` (`us` / `asx` / `nikkei`
  / `ftse`), `merge` and `timeText` (two small habits each copy had and keeps: which worker answers are counted, and
  whether the run's time is handed on as a number or as text). The header of `screeners.js` explains every field.
  In `runAnalysis` the 14 branches are one: `shareScreener(key)` finds the entry.
- `analysis.html` loads `screeners.js` before `analysis-functions.js`. **Should a visitor's page be an older copy
  without that tag, `shareScreener` fetches the file itself** the first time a screener is asked for, so no order of
  arrival can leave a screener without its list.
- The FTSE 100 report, which was written out inside `runAnalysis`, is `formatFTSEResult(apiData)`, beside the others.
- **Code that could never run went with it:** a third copy of the ASX 300 routine standing after a `return`, a second
  `(5, '50')` branch for a Shanghai screener that was never built (it asked `'YOUR_LAMBDA_URL'`), and two functions
  nothing called (`runFTSE100Screener`, `formatUKResult`). The two "coming soon" alerts for `(5,'180')` and
  `(5,'csi300')` are still there.
- `analysis-functions.js`: 324 KB to 169 KB, 5,001 lines to 3,416. The crypto screener, the single report, the signals
  and the access check at the top of `runAnalysis` were not touched.
- **Proved the same, not assumed:** `check-tools/screener_equiv.js <old> <new>` (with `PRE=<screeners.js>`) runs each
  button through the old page code once for real, keeps the workers' answers, then runs old and new on those answers
  with the clock stopped and compares what each asked the workers and what each produced. All 14 screeners and the
  single report, both signals buttons and the single coin: the same requests, the same report, the same CSV,
  character for character; a copy broken on purpose (11 stocks a worker) was caught. (The crypto screener cannot be
  replayed that way, its request carries the time; it was run for real through the new code.) After the deploy six
  screeners were run for real through the deployed code: every worker answered.
- The files were **built by a script from the live code** (`make.py`, in git history with the staging folder: commit
  `7ea216d`): every list and address was copied as text and each branch checked against the pattern, so nothing was
  typed again.
- **The way back:** `bash /Users/dave/VSCODE/stockiq/check-tools/pending-screeners-undo/deploy.sh` (`DRY_RUN=true`
  first) reverts website commit `e0d47f15` and uploads the two files. **Once a screener has been added to
  `screeners.js`, that way back needs the new screener put into the old code by hand: decide before adding.**
- **To add a screener now:** an entry in `screeners.js` (list, workers, the fields above) with `format: 'market'` and a
  `report` block (the words of its report, its name and symbol in the history, short company names), a button in
  `analysis.html`, and the rest of `add-new-screener.md` (workers, coordinator, dashboard). **No formatter and no
  lookup to write:** `formatMarketResult(apiData, report, size)` writes the report of any market (the Nikkei's own
  `formatNikkeiResult` is a call to it), and `marketReport(option, subOption)` gives the history its name and symbol
  and "run again" its address. The Germany DAX 40 (13 Oct 2026) was the first added this way.
- **A company name in a `report.names` table must not be one word in capitals** ("SAP", "BASF", "BMW"): the dashboard's
  Top 10 tracker (`parseScreenerTop10`) tries its coin pattern first, `N. <anything> CAPS <sign>price`, and a line
  "2. SAP.DE  SAP  €195.14" matches it, so the whole report was read as coins (it looked up `SAP-USD`). Write "SAP SE",
  "BMW AG". Found by `tracker_run.js` on the page's DAX report before anything was live: **run it on the page's report
  and on the coordinator's for every new screener.** (`page_run.js`'s own "tracker symbols" count has the same quirk.)
- **The way back to the 14 copies no longer applies by itself:** with the DAX 40 in `screeners.js`,
  `pending-screeners-undo` stops at its trial revert ("needs a session"), as its notes said it would. `page_run.js`, `anon_run.js` and `trial_run.js` load `screeners.js` when it lies beside
  the page code they are given.
- Not done: the coordinator still has its own copy of the lists (a Lambda cannot read the site's file); the page's
  four formatters are still four; `saveAnalysisToHistory` (374 lines) and the notification code in the same script
  were not looked at.

### Batching

- Each worker gets 10 stocks, or a few more only when a list is longer than workers × 10:
  `perWorker = max(10, ceil(list / workers))`. Workers accept more than 10.
- An empty batch returns nothing (since 11 Oct 2026; before, the Russell and NASDAQ workers fell back to a
  built-in list and returned unrelated stocks). Both paths still skip empty batches. Only a call with **no
  `stock_batch` at all** to a Russell 1000 / 2000 worker takes that worker's ten stocks of `lists.txt`.
- No worker Lambda needs creating or deleting when a list changes; idle functions cost nothing.
- The coordinator de-duplicates results by symbol.

### The worker groups: one file for every share screener (done 11 Oct 2026)

The owner asked whether the screeners "all share the same function", and for it to be made simpler to manage. They did
not; now they do. **All 789 share-screener workers (30 groups since 17 Oct 2026, when the Euro Stoxx 50, OMX Stockholm 30, CSI 300, Taiwan 50 and NZX 50 added 48; before that 741 in 25 groups: 669 in 13 until 13 Oct 2026, when twelve screeners were added: DAX 40 four workers, CAC 40 four, AEX three, TSX 60 six, FTSE MIB four, IBEX 35 four, Hang Seng ten, STI three, SMI two, Sensex three, KOSPI 200 twenty-one, Bovespa eight) run the same package, built from `stockiq/workers/` in git.**
Checked at the end by downloading every package: one set of four files in all 669, byte for byte the files in git.

| In `stockiq/workers/` | What it is |
|---|---|
| `stock_worker.py` | **The code.** Prices from Yahoo, the indicators, the 12-factor score. Change the scoring here and nowhere else |
| `lambda_function.py`, `advanced_lambda.py` | Two lines each: the two handler names the functions are set up with (`advanced_lambda.lambda_handler` for the ten S&P 100 workers, `lambda_function.lambda_handler` for the rest) |
| `lists.txt` | The Russell 1000 and Russell 2000 lists (the coordinator's), for page runs that send a worker number and no stocks |
| `groups.py` | **The one table of groups and markets** (group, screener, number of functions, market; per market its currency and sample shares). `deploy.py`, `prove.py`, `build.py` and `check-tools/workers.py` all read it |
| `build.py` | Builds the package. The same input always gives the same zip, so every function shows one fingerprint |
| `prove.py` | What a change does: replays saved prices through the live copy (the mirror) and the changed file, lists every figure that differs, then how far scores, labels and each day's top 10 move. `--fetch` once for the non-US sample |
| `deploy.py` | Puts the package on the functions, a group at a time, through a `check-tools/pending-<name>/deploy.sh` (its header has the three-line template). `--selftest` plays its rules against a stand-in for AWS |
| `live.txt` | The fingerprint of the package that is live (`q9ZX/UvTB…` since 11 Oct 2026). The deploy accepts only this one or the new one on a function |
| `results-proof-2026-10-11.txt` | The proof run before the first deploy |

**To change the workers (scoring, a fault, real company figures one day):** edit `stock_worker.py`; `python3 workers/prove.py`
and read every difference (only the ones meant may remain); commit; make `check-tools/pending-<name>/` with `deploy.sh` (the
template) and `groups.txt` (one small group first, e.g. `stockiq-option-3-8-worker`, later the word `all`); dry run, deploy;
run that group's button through the page and the coordinator (end of this section); then the rest; commit `workers/live.txt`;
remove the folder. `python3 check-tools/workers.py` must show "one" for the 13 groups and the same code across them
(`--contents` downloads and compares, the honest count).

- **1,000 worker functions in 30 groups; 795 are called by the site** (741 share workers, 54 crypto workers; 928 / 18 / 723 before the twelve screeners of 13 Oct 2026). **205 are not
  called by the site now** (the single-coin worker since 12 Oct 2026, and `stockiq-option-3-3-worker` 60, `stockiq-option-7-4-worker` 139,
  `stockiq-option-3-worker` 5). They cost nothing idle, were not touched and hold old code. **"Not called by the site" is
  not "never used"**: counted on 12 Oct, the 3-3 group was the S&P 500 path until 11 Sep 2026; only the 7-4 group has no
  call at all on record (section 8c, "Start here when resuming", improvements, item 10). Nothing is deleted without the
  owner's yes to an exact list.
- **What the audit really found (the first table was misleading).** `workers.py` counts package fingerprints, and a zip's
  fingerprint changes with the dates of the files inside it. The "100 / 200 different versions" of the Russell groups were
  two programs zipped 300 times; FTSE's "9 different" were two files differing in one default number. Across the 669 share
  workers there were **seven code files**: S&P 100 / 400+600 / 1500 (one), Russell 1000, Russell 2000 (the same with a list
  file each), NASDAQ 100 / Dow 30 (one), ASX x4 / Nikkei (one), FTSE (two).
- **What the one file is:** the ASX / Nikkei copy (it had Wilder's RSI and the right 52-week formula) with the UK sector
  list, and these changes, each shown in `results-proof-2026-10-11.txt`:
  1. **One RSI: Wilder's smoothing, everywhere.** The US and London workers used a plain 14-day average. **This is not a
     small change** (the notes written before it said "a little"): on saved prices about 37% of US and London signal
     labels differ on a given day, the score moves by 0.5 or more (on a scale of about -2 to +3) on 46% of stock-days,
     and a day's top 10 keeps 6 or 7 of its 10 names. It is no better or worse at predicting anything (section 7b). ASX
     and Nikkei scores did not change from this.
  2. **NASDAQ 100 and Dow 30 lost their own company-figures tables.** Their copy gave bonus points to seven named tech
     companies and seven "growth leaders", used a wider "healthy" P/E band and its own P/E guesses, and counted earnings
     risk differently; the Dow 30 ran this "tech" copy by accident of copying. They now use the common factors, so AAPL
     scores the same in the Dow 30, NASDAQ 100, S&P 100 and S&P 500. With RSI held still this alone moves the score by
     0.5 or more on 11% of stock-days and changes 17% of labels for those two screeners.
  3. **A session Yahoo sends twice is kept once.** After the ASX closes Yahoo sends the day's bar and the closing quote as
     two bars (seen for 12 of 12 ASX shares on 9 Oct); the 24-hour change was 0 for every ASX stock and every look-back
     was a day short. Bars are now one per trading day on the exchange's own clock (`bars_from_chart`). On the day of the
     deploy the ASX top 10s kept 5 to 7 of 10 for this reason.
  4. **A latest session that arrives empty is taken from the quote** that comes with the chart (London, seen 10 Oct: prices
     a trading day old). **Tested on a real answer with its last session emptied (12 of 12 right), not yet seen live**: by
     11 Oct Yahoo had filled Friday's bar in. Look at a FTSE run on a morning after a London session.
  5. **SPY is fetched once per batch**, not once per stock (the market's state is the same for all ten): half the calls to Yahoo.
  6. **The Russell lists in the package are the coordinator's** (877 and 1,829). The old packages held 1,000 entries for the
     Russell 1000, **125 of them company names instead of tickers** ("Amazon", "Airbnb", "3M"), without BRK-B and BF-B, and
     1,977 for the Russell 2000 with 147 dead tickers; a page run and a background run covered different stocks.
  7. A fallback for the distance from the 52-week low that gave a wrong figure for a share more than 500% above its low
     (99 of 21,870 stock-days) is gone; an empty batch returns nothing; each stock carries a new field `currency` (as Yahoo
     gives it: `USD`, `AUD`, `JPY`, `GBp` for pence); the CSV writer and test block the function never ran were removed.
  With each copy's own RSI put back into the new file, everything else was identical: S&P family 99.5% of 21,870
  stock-days (the rest is item 7), Tokyo 600 of 600, London 624 of 624, ASX all but the day of the doubled bar.
- **How it was deployed:** a group at a time through a packaged script (Dow 30 first; it was then put back once to prove
  the way back, its fingerprint matching the independent copy, and deployed again), each group's first and last worker
  tried for real, and every one of the 14 share buttons run through the page code and the coordinator afterwards: every
  worker call answered, no flags, the tracker found 10 symbols each time, and a live worker's answer equalled the file
  in git run on this machine on all 480 figures of ten stocks.
- **The way back to before 11 Oct 2026:** every function's old package is in
  `~/VSCODE/backup/workers_before_onecode_20261011/<function>.zip` (669 files), and the deploy script of that day puts
  them back: `git show a6edbd9:check-tools/pending-workers/deploy.sh` and `deploy.py` into a `pending-` folder with a
  `groups.txt`, then `ROLLBACK=true bash …/deploy.sh`. A full copy of every Lambda function as it was at 12:20 UTC that
  day, with a README, is in `~/VSCODE/backup/lambda_full_20261011_before_one_worker_code/` (made outside this session).
  From now on `deploy.py` keeps one zip per deploy (`~/VSCODE/backup/workers_package_<fingerprint>.zip`).
- **Settings were not changed** and still differ a little by group (Python 3.11, 3.12 or 3.13; 128 or 256 MB; timeouts of
  30 to 900 s; a few unused environment variables). The code does not depend on any of it.
- **Left as they are, on purpose, because changing them would change labels again** (each is one line in the one file now,
  and the owner's to decide): `MODERATE_SELL` is only given at a score of exactly -0.8 (the test above it catches the
  rest as `HOLD`); `momentum_signal` can never say `STRONG_DOWN` (the `DOWN` test comes first); the line "PRE-SCALE
  TOTAL" prints the scaled score; the 12 weights total 102%; the market's state is the US market's (SPY) for every
  country; no real company figures.
- **Not part of the workers, found on the way and fixed the same evening** ("Dashboard performance tracker", below):
  London prices in pence were printed as pounds, and the coordinator's report cut every symbol to five characters and
  printed "$" for every market.
- **The crypto workers** (54, one version) are a different program; their MACD fault was fixed the same day ("Crypto",
  below). The single-coin worker asks for 60 days and does not have it.

### What the screener workers really do

- They return 48 data fields per stock (`currency` since 11 Oct 2026) and no report text. Codes: `STRONG_BUY`, `BUY`,
  `MODERATE_BUY`, `HOLD`, `MODERATE_SELL`, `SELL`, `STRONG_SELL` (underscores). Field names that
  matter for CSV: `change_24h`, `distance_from_52w_low`, `52w_high`, `52w_low`.
- **They do not fetch fundamentals.** `get_fundamentals()` returns hard-coded guesses for ~50
  large US stocks and defaults for everything else (P/E 25, beta 1.0, dividend 0, size "Mid",
  sector "OTHER"). "Earnings risk" is the calendar month (Jan/Apr/Jul/Oct = HIGH), "sentiment" is
  the day's price move. The "Financial health" factor therefore adds the same +0.12 to nearly
  every stock: **the screeners are price, momentum and volume only.** `about.html` says so, and
  the CSV no longer exports P/E, market cap, beta, dividend, sector or earnings risk.
- The 12 weights really total 102% in the code (0.18+0.08+0.06+0.20+0.20+0.10+0.06+0.05+0.03+
  0.03+0.02+0.01). The About and FAQ pages say so. Changing it would change every score.
- **ASX quirk (fixed 11 Oct 2026):** once the ASX has closed, Yahoo returns the last session bar twice, so the
  ASX workers computed a 24-hour change of 0 for every stock (also flattening their sentiment
  factor and `Momentum_Signal`). Bars are now one per trading day. Not checked during ASX hours.
- A worker returns nothing for WBD and PSKY because **Yahoo has no usable history for them** (11 Oct 2026: one bar
  for WBD, which stopped trading on 6 Oct; 42 of PSKY's 52 bars empty). The price source, not the worker.
- Real fundamentals are now one file and one deploy (`workers/`, above), once there is a source for them.

### Output wording: describe, don't advise

- Codes are used for logic but **never shown**. Everything printed goes through a label function:
  `signalLabel()` / `horizonLabel()` in `analysis-functions.js`, `signal_label()` /
  `horizon_label()` in the coordinator and crypto orchestrator, `signal_label()` in the report
  Lambda. Labels: Strongly positive, Positive, Slightly positive, Mixed, Slightly negative,
  Negative, Strongly negative. Both code styles are accepted (stock: underscores; crypto: spaces,
  plus `CONSIDER` and `AVOID`). An unknown code shows as **"Unrated"**: if that ever appears, a
  worker has a new code that must be added to all the label maps.
- Stop loss / take profit are shown as "Lower / Upper reference level"; buy limit / buy stop as
  "Pullback / Breakout level"; profit probability as "Model probability estimate"; strategy as
  "Horizon". Lists are headed "TOP N BY SCORE".
- The single-stock report (`stockiq-option-1-1-custom-analysis`) no longer prints BUY/SELL,
  "Buy immediately", position size, urgency or action steps; it prints a signal summary, "what
  the model sees", reference levels and a disclaimer. Scoring is unchanged.
- The dashboard performance popup reports the price change since the report (it used to say
  "The AI predicted upward movement" whenever the price was up).
- Any new formatter must follow this: no "buy", "sell", "target", "stop loss", "take profit",
  "position size", "recommendation", "picks" or "opportunities" in output.
- Not changed: the workers still return raw codes and a few descriptive breakdown strings
  ("RSI Buy Zone"); three Lambdas with old wording are not called by the site
  (`stockiq-option-3-1-us-screener`, `stockiq-option-3-1-sp100`,
  `stockiq-option-3-dynamic-coordinator`). Reports already saved in users' history keep the old
  wording until the 30/90-day auto-delete removes them.

### CSV exports

- Stock CSV columns (page `generateExcelExport` and coordinator): **`Currency` straight after `Price`** (since 11 Oct 2026:
  the code as the workers report it, `USD`, `AUD`, `JPY`, `EUR`, and `GBp (pence)` for London, so that a London figure is
  not a bare number; `screenerCurrencyName` on the page, `currency_name` in the coordinator; 40 columns in both),
  `Signal`, `Lower_Level`,
  `Upper_Level`, `Model_Probability_%`, `Horizon`, `Horizon_Days`, the change columns,
  indicators, `Distance_52W_High_%`, `Distance_From_Low_%`, `52W_High`, `52W_Low`,
  `Market_Regime`, `SPY_20d_Change_%`, `Score_Breakdown`. Several of these were always 0 before
  Oct 2026 because the code read field names the workers do not return.

### Trading signals and the presets (reviewed 11 Oct 2026)

The owner asked for the "junky" items to be looked at: "Choose from presets" and the two buttons under Trading Signals.

- **Presets** (`analysis.html`, `#presets`): "Magnificent 7" and "Popular ETFs" send their symbols to the single-stock
  report (7 and 4 full reports in one answer: 20 and 11 seconds, about 250 KB and 140 KB of text); "Dow Jones 30" and
  "S&P 500 Complete" simply run those screeners. They work, and they took on the report's fixes of the same day.
  **A run of several reports starts with a side-by-side table** (11 Oct, `formatOption11Result`): symbol, price, the day's
  change, the report's 0-100 score and its signal label, one line each; a single report has none. The price is taken as
  the report itself writes it (its "Current Price:" line), because the result carries no currency field.
- **The two signals functions run one file, kept in git: `stockiq/signals/lambda_function.py`** (no key in it).
  `stockiq-option-2-trading-signals` ("Enter Symbols for Live Signals", up to 10 symbols) and
  `stockiq-option-2-2-auto-signals` ("Auto-detect Top 5 Signals"); which of the two a call is, goes by the function's
  own name. Package: that file and `sp100.txt` (`python3 signals/build.py`; `--list` rewrites the list from the
  coordinator's S&P 100 and the build stops if the two differ). Fingerprint on both:
  `6nVDLm4/8G6K0A37aSb+3r7YukSxFUUsK8tvYmwNL9M=`. Memory 512 MB and 1024 MB (they were 128: the scan below took 33
  seconds at 128 MB and takes 5 at 1024; Lambda bills memory x time, so it costs about the same).
- **A reading** is short-term and technical only: RSI (Wilder's, the site's one RSI), MACD against its signal line, the
  price against its Bollinger bands. Points: RSI under 30 +2, under 40 +1, over 70 -2, over 60 -1; MACD above its signal
  +1, below -1; at or below the lower band +2, at or above the upper -2. **+2 or more is a positive reading (code `BUY`),
  -2 or less negative (`SELL`), between is mixed (`HOLD`); 3 or more either way is "HIGH" confidence.** It is not the
  report's 0-100 score, uses no company figures, and nobody has tested whether it predicts anything.
- **What was wrong:** a scoring of their own with RSI as a plain average (a third way of working it out on this site);
  every price in dollars; a time with no zone, which a browser read as local when it was UTC; levels 2% inside the
  20-day range or an arbitrary 5% either side of the price; reasons worked out and never shown; a symbol with no
  prices silently dropped. **The auto-detect looked at the first 15 names of a 30-name list written into its code,
  scored them with a fourth formula, and called its five "top performers"**: on 11 Oct that gave AAPL, NVDA, TSLA, PG
  and MSFT, four of them mixed readings.
- **Now:** one bar a day and the latest session from the quote (the same rules as the workers and the report); each
  reading carries `currency`, `name`, `change_pct`, `reasons` (one plain line per ingredient with its points: "RSI 71, in
  the overbought range (over 70): -2"), `trend` (the report's own words) and the levels as facts: the high and the low
  of the last 20 sessions. **The auto-detect scans the screener's whole S&P 100 list** (101 shares, 8 at a time) and
  returns **the five strongest readings in either direction**, with `scanned`, `universe`, `readings` (how many
  positive / negative / mixed) and an honest `methodology` line. On the same day: SBUX +5, VZ +3, PLTR -3, T +3, ABBV -3.
- **Every field the page read before is still there** (`symbol, current_price, action, confidence, entry_price,
  stop_loss, take_profit, …`; `top_performers` is kept as the name of the list of five), so the page works unchanged.
- **The page's two writers** (`formatOption2Result`, `formatOption22Result`, sharing `signalBlock`; 11 Oct, late): each
  reading is `N. SYMBOL - name - price (change today)`, then its label with the points and confidence, the reasons one a
  line, the trend, and "20-day high" / "20-day low" with how far each is from the price. Prices go through `screenerMoney`
  from the reading's own currency ("A$60.94", "2,662.00p", "¥2,910.50", "€48.76"). Symbols with no prices are listed at
  the end. The auto-detect says "Strongest readings", with how many shares were scanned and how the readings fell.
  **The first line is read by the dashboard's tracker**: the name is cut to 30 characters and set off with " - " for that.
  **Text from outside is escaped (`reportText`)**: reports are put on the page as HTML, so "AT&T" must be written
  "AT&amp;T". Unescaped, the tracker also lost the line, because it clears everything from an "&" to the next ";" and
  the trend line has a ";" (found by the test: 3 of 5 symbols read). Any new report line that prints a name or typed
  text needs the same.
- Tests: `python3 signals/test_signals.py` (42 checks on saved prices, beside the two old files; `--show` prints the
  readings). A run by hand against live prices: `python3 signals/lambda_function.py NVDA BHP.AX` or `--auto`.
  Checked live through both function addresses and through the page's own code (`page_run.js 2 custom`, `2 auto`).
  Rollback: `~/VSCODE/backup/stockiq-option-2-trading-signals_before_onefile_20261011.zip` and
  `stockiq-option-2-2-auto-signals_before_onefile_20261011.zip`; memory back with `update-function-configuration`.

### Dashboard performance tracker (🎯 button)

- `trackScreenerPerformance` in `dashboard.html` parses the saved report text: the symbol and
  price at the start of each numbered line. Do not change that part of a line.
- Stock pattern: `N. SYMBOL <up to 40 chars> PRICE`, symbols 1–10 characters with an optional `.XX` or `-X`
  suffix. **The price is either a currency sign and a number, or a number of pence** (since 11 Oct 2026): `$118.39`,
  `A$8.43`, `¥5,613.00`, `€48.76`, `503.80p`; thousands commas are allowed; signs read: `$ £ € ¥ ₹ ₩`. **Since 13 Oct 2026 also a currency code and a number, "CHF 77.30", "BRL 56.86"** (three capitals, a space, a number with two decimals: what the money rule writes for a currency it has no sign for), **and a symbol may hold an "&"** (`M&M.NS`; in the report it is written `M&amp;M.NS`, and the parser turns `&amp;` back into "&" before it clears other entities). Check for both parsers at once: the old and the new read every saved report in `check-tools/` alike. The older forms in
  saved reports are still read (`£2614.00`, which always meant pence, `$AUD8.43`, and a background ASX symbol cut to
  `AGL.A`). `check-tools/page_run.js` has a copy of this pattern for its own count: change the two together.
- **One money rule in three places that must stay alike:** `screenerMoney(stock, value, fallback)` in
  `analysis-functions.js` (every share-screener formatter), `money(stock, value, fallback)` in the coordinator, and
  `money()` in the single-stock report (section 7). Each takes the currency the worker result carries (`currency`, as
  Yahoo gives it): `GBp` is pence and is written `503.80p`, never with a pound sign; a market's own currency is only the
  fallback. Three FTSE 100 shares are not quoted in pence at all (CPG.L and IHG.L in US dollars, MTLN.L in euros, 11 Oct
  2026) and now print as such. The coordinator pads the symbol and never cuts it (it cut to five characters until then).
  CSV files carry bare numbers in the share's own unit, with a `Currency` column beside the price ("CSV exports", above).
- A company name between symbol and price must stay short (Nikkei names are cut to 22 chars).
- Rebuilt 10 Oct 2026: one parser (`parseScreenerTop10`) and one calculation
  (`screenerTop10Performance`) feed both the row badge and the popup. Before that the two had
  separate copies: the popup failed on every UK report, the badge never appeared for Nikkei, a
  symbol with no price still counted in the average, stocks under $1 showed false moves, every
  currency was shown as "$", and old crypto reports priced the wrong coin.
- The popup also shows "Top 10 and the index over the same time": the top-10 average 1 day, 1 week,
  2 and 3 weeks after the report and now, beside the index the list comes from (`TOP10_BENCHMARKS`
  keyed on the report's name; Bitcoin for crypto; add a line there for a new screener). The price
  source keeps about a month of daily closes, so index figures start from the close on the report
  day (approximate) and appear only after the next trading day.
- Test it without logging in: `check-tools/tracker_run.js` runs the page's real tracker code on a
  saved report text with live prices (`NAME='<report name>' DASH=<dashboard.html> node tracker_run.js <label> <report.json> <ISO time>`).

### Crypto

- **The orchestrator holds the coin list; the 54 workers analyse what they are sent.** (Until 11 Oct 2026 a
  worker called with no coin fell back to a 540-coin CoinSpot list written into its own code; that mode, its
  report writer and its database reads were removed that day, and a worker now answers "nothing to analyse".)
  `stockiq-option-7-1-orchestrator` holds the list (`COINS`:
  540 pairs of `(symbol shown, Yahoo ticker without -USD)`) and sends it out itself: **ten coins a
  call** (`{"coin_list": [<tickers>]}`, a mode added to the workers on 11 Oct 2026 that analyses each
  coin exactly as single-coin mode does and answers `results: [{ticker, coin}]`), 54 batches, one to
  each worker function, all at once; a batch whose function fails goes to the next one, and any coin
  that did not come back is asked for once more on other functions. About 10 s for 540 coins with
  2,048 MB. **From 10 to 11 Oct it called single-coin mode once per coin (540 calls a run): with the
  top-10 history every 30 minutes that was about 0.8 million calls a month against Lambda's free
  million.** Now a run is 54 calls (about 80,000 a month for the history). Single-coin mode
  (`{"single_coin": "<ticker>"}`) is unchanged. Test: `check-tools/crypto/batch_test.py` (the old
  orchestrator and the new against a stand-in for the workers: same coins, scores, order and report).
- The list is the top coins by market cap (CoinGecko, 10 Oct 2026) without stablecoins and
  wrapped/staked tokens. A coin is only included if Yahoo's price for its ticker was within
  0.8×–1.25× of CoinGecko's and it had 60+ days of history. **Many coins share a symbol on
  Yahoo**: 125 need Yahoo's numbered ticker (SUI is `SUI20947-USD`, ARB is `ARB11841-USD`);
  the plain symbol is a different coin. Before this, the top-ranked coin was often a wrong match
  (CORE priced as cVault.finance at $5,698) and 27% of coins had no data.
- `CRYPTO_TICKER_MAP` in `analysis-functions.js` holds the same symbol → ticker mapping for
  single-coin analysis. **Keep it in step with `COINS`.** `mismatchedCoinSymbols` in
  `formatSingleCoinResult` warns on symbols still known to be the wrong coin.
- To rebuild the list: CoinGecko `/coins/markets` by market cap; drop stablecoins and wrapped
  tokens; check `SYMBOL-USD` on Yahoo; if the price does not match, use Yahoo's search API
  (`query2.finance.yahoo.com/v1/finance/search?q=<coin name>`) to find the numbered ticker and
  check its price. Go slowly (429s).
- The orchestrator zip must contain `orchestrator.py`, `orchestrator_simple.py`,
  `prediction_memory.py`. Handler `orchestrator.lambda_handler`.
- The page shows the orchestrator's `report` text directly (`type: 'coinspot_comprehensive'`);
  internal names still say "coinspot" although the list is no longer CoinSpot's.
- Equal scores are ranked in coin-list order (largest market cap first), so the top 10 is the
  same on every run. (It used to depend on which worker answered first.)

**How a coin is scored and ordered, and three faults fixed on 11 Oct 2026.** The owner looked at a crypto export and asked
whether the top 10 is even in the right order (the 11th coin had the same score as the 9th and 10th).
- **The score** (`stockiq-option-7-1-worker-N`, in the code after "ADVANCED SCORING SYSTEM") is a whole number of points
  from yes/no rules: MACD (strong bull +3, bull +2, bear -2, strong bear -3), RSI (extremely oversold +3, oversold +2,
  overbought -2, extremely overbought -3), Bollinger band (oversold +2, bullish +1, bearish -1, overbought -2),
  stochastic (±1), volume (±1), momentum (strong ±2, ±1), the day's change (over 10% +2, over 5% +1, and the reverse),
  a breakout above the last 20 days' high (+2), a volume surge on a rising day (+2), 3- and 5-day rise together (+1),
  a +1 for ten named large coins, and penalties (RSI over 75 and falling -3; down more than 15% in a week -2). Labels by
  score: 7 or more Strongly positive, 4 Positive, 2 Slightly positive, -1 Mixed, -3 Slightly negative, -5 Negative.
  **It rewards opposite things at once** (being oversold, and breaking out upwards), and nobody has tested whether it
  predicts anything for coins (there are no saved coin prices to replay; the entry log below is the forward test).
- **The order** is by score, and **coins with the same score are listed largest first** (their place in `COINS`), so that
  the list is the same on every run. That was right in his export. But a whole-number score means many ties: at one run
  six coins had +3 and three of them were "in the top 10" by size alone. The report now says so under the list when coins
  tie at the cut ("4 coins have a score of +6; 2 of them are in this list…").
- **Fault 1: MACD was never worked out, for any coin.** The worker asked for 30 days of prices and MACD needs 35, so
  `calculate_macd` answered "not enough" every time, and that was read as "BEAR - Below signal line": all 540 coins got
  "MACD Bear: -2" (the export's MACD column said the same for every row). The order was not changed by it (the same -2
  for everyone) but every score was 2 too low, every label a notch lower, and the heaviest input was missing. Now 90 days
  are asked for, for MACD alone (`macd_closes`; everything else still uses the last 30 days, and each coin's other figures
  were compared before and after: identical), and too little history counts as "NEUTRAL - Not enough history", 0 points.
  After the fix one run gave: bear 289, strong bear 138, strong bull 71, bull 38; scores from -7 to +11 (they were -7 to
  +6); 8 coins Strongly positive (there were none).
- **Fault 2: a coin whose price does not move could stand in the top 10.** VVS (price $0.00000097, too small for the price
  source's digits) had the same change over 1, 7 and 30 days and an RSI of 0; a flat line reads as "extremely oversold"
  (+3, +2, +1), which put it 5th. The orchestrator now leaves such coins out of the ranking (`stuck`: no daily range, or
  the same change over 24 hours, 7 days and 30 days): three at the time (VVS, HTX, GEKKO), so 536 or so are ranked.
- **What follows from the fix:** the top 10 after 11:52 UTC on 11 Oct 2026 is partly different from before, so "in the top
  10 since" started again for the newcomers, and **rows of the entry log from before that time were ranked without MACD**:
  do not mix the two when the track record is measured. The autopilot buys coins by this ranking, so the same goes for
  its coin trades before and after.
- **Single-coin analysis no longer has code of its own** (12 Oct 2026): the page and the dashboard ask the single-stock
  report function, which reports on a coin (section 7, "The single-stock report", "It reports on a coin too").
  `stockiq-option-7-2-worker-1` is unused. The screener's rules themselves (what earns points) were not changed.
- **The worker's code reviewed (11 Oct 2026, evening; the owner: "i built it with an old AI version, its been a long time
  since it was reviewed").** Fixed, with no score changed (`check-tools/crypto/worker_test.py`: on the price source's
  recorded answers for ten coins every figure is the same before and after): **one request per coin where there were
  two** (30 days for the changes, then 90 days for everything else; the second holds all of the first, and the two
  could even disagree on the live price); **a day's high, low, close and volume stay together** (each list was
  filtered for missing values by itself, so one gap shifted it against the others); the unused old mode and everything
  only it used are gone (1,134 lines to 689; the database library with them, so a cold start is quicker). All 54:
  `DaTSp0Aqxq7x8iATvdBo2w4YUy1Eccd3azPN44xFhow=`. Rollback: `~/VSCODE/backup/stockiq-option-7-1-worker_before_clean_20261011.zip`.
- **Found in that review and NOT changed, because each would change scores (the owner's decision; they would also
  start the top-10 log afresh a third time):**
  1. **The ranking depends on the time of day.** Daily prices are UTC days and the last one is still running: "24h
     change" is really the change since 00:00 UTC (near zero for every coin just after midnight UTC), and today's
     part-day volume is compared with full days ("volume surge +2" can hardly fire in the morning, UTC). Up to about
     five points of a score that cuts its top 10 at +6 to +11. A fix needs hourly prices (one more request per coin, as
     many as before the clean-up) or a projected day's volume.
  2. **RSI is a plain average of the last 14 days** here; the rest of the site uses Wilder's (the screeners, the
     single-stock report, its chart, the trading signals). The figure differs from charting sites.
  3. The score rewards opposite things at once (oversold, and breaking out upwards); a "large cap" point goes to ten
     names written into the code (one of them, MATIC, has since been renamed); nothing in it has been tested against
     what coins did next (the entry log is that test, and it needs weeks).
  4. Its descriptive strings ("EXTREMELY OVERSOLD - Strong buy signal") still carry advice wording; the page shows only
     the part before the dash, so none of it is seen, but any new place that prints them must do the same.
- Deployed with a packaged script to all 54 workers (one zip, the same `CodeSha256` on each: `NmXC9dcsA6p5…`) and the
  orchestrator (`Tyyx+Pb2l+sy…`). Rollback zips: `~/VSCODE/backup/stockiq-option-7-1-worker_before_macd_20261011.zip`
  (the same to all 54) and `stockiq-option-7-1-orchestrator_before_macd_20261011.zip`.

**Top-10 history (rebuilt 10 Oct 2026).** Each top-10 coin in a report shows how long it has been
in the top 10 and what its price has done since: "In the top 10 since 10 Oct 06:02 UTC: $a → $b
(+5.0%)", the time, the score then and now, and "in the top 10 at N of M checks since then".
- EventBridge rule `stockiq-coinspot-predictions-schedule` (every 30 minutes) invokes **the
  orchestrator itself**. A scheduled run records the top 10; a user's run (through the Function
  URL, or the coordinator) only reads. One coin list and one ranking, so the history always
  describes the list the user sees. A URL call can never write: it always has `requestContext`.
- Table `stockiq-coinspot-prediction-status`: one row per coin (`streak_start`, `streak_price`,
  `streak_score`, `last_seen`, `checks_in_top10`, `ticker`) plus the marker row `_last_check`
  (`last_check`, `check_no`). A coin keeps its run across one missed check (65 minutes); after
  that a new run starts. If the last check is older than 100 minutes the report says history is
  not available. A check that ranked under 80% of the list is not recorded. Rows without
  `last_seen` are left over from the old updater and are ignored.
- **Track-record log:** every time a coin enters the top 10, a permanent row goes into
  `stockiq-coinspot-predictions` (`log_version` 2: entry time, ticker, price, score, rank, the
  coin's 24h / 7d / 30d change, RSI, volume ratio). Nothing reads it yet. Its purpose: after a
  few weeks, measure what coins did in the 24 hours / 7 days after entering the top 10 compared
  with the average coin. **Nobody knows yet whether the score predicts anything**; the owner's aim
  is to make it easier to see which coins tend to do well, and this log is the evidence for that.
  Present any result as past performance, never as "likely to profit".
- Icons: 🟢 an hour or more, 🟡 under an hour, 🔵 new or no history. Keep an emoji from the
  U+1F300–1F9FF range before the symbol: the dashboard uses it to recognise a crypto report.
- The report's wrapper carries `data-top10-tickers='IMX:IMX10603,…'`. The dashboard 🎯 tracker
  reads it to look up the right coin (old saved reports have none and fall back to `SYMBOL-USD`).
- `crypto-filter-buttons.js` adds the "Time in the top 10" slider to crypto results; it filters
  the top 10 on `hours_in_top10` and re-uses `signalLabel()`.
- What it replaced: `stockiq-coinspot-predictions-updater` ran every 15 minutes as an old copy
  of the orchestrator, ranking the workers' built-in list, so its history matched almost none of
  the coins users saw; "consistency" stars partly came from the letters of the coin's symbol and
  the report printed LOW / MEDIUM / HIGH RISK. That function is no longer triggered (still exists).

### Access checks and usage counting

- `runAnalysis` checks access (`checkDailyUsageLimit` → `authManager.checkStockAnalysisAccess`)
  and counts the use **once, at the top, for every option**. Anonymous: 1 per day. Trial: 5 per
  day for 3 days. Paid plans pass the check.
- **Never check access again after the use has been counted.** 14 handlers used to (crypto,
  single coin, six US screeners, ASX, Nikkei): the second check saw zero left, so an anonymous
  visitor's single-coin run went to signup.html and a trial user's last analysis of the day went
  to the upgrade page, both with the use spent and no result. Removed 10 Oct 2026.

### How to test every button end to end (no browser needed)

The scripts are in `stockiq/check-tools/` (see its `README.md` for one-line examples):
`page_run.js` (step 1), `anon_run.js` and `trial_run.js` (step 2), `run_all.py` and `analyse.py`
(step 3). `check-tools/lists/` holds the one-off scripts that rebuilt the index and crypto lists.
The method:
1. **Page path:** load `analysis-functions.js` in a Node `vm` context with a stub `document` /
   `window`, real `fetch`, and `displayResults`, `displayError`, `saveAnalysisToHistory`
   overridden to capture the result. Block fetches to usage / trial / dashboard Lambdas (answer
   them with a fake OK) so nothing is written. Call `runAnalysis(option, subOption, event)` per
   button and check: no error, every worker call 200, result count ≈ list size, no raw codes,
   no "Unrated", no `undefined` / `NaN`, and the tracker regex finds 10 symbols.
2. **Access rules:** also load `auth.js` (expose `authManager` on the global object) and
   simulate the usage tracker in the fake fetch; record every write to `location.href` with a
   stack trace. Test 1 use left (must get a result) and 0 left (must redirect before running).
3. **Coordinator path:** import the coordinator in Python, patch `urllib.request.urlopen` to
   intercept the dashboard save URL, call `lambda_handler` for each key. Needs
   `AWS_DEFAULT_REGION=us-east-1` for the `worker_id` screeners (`3-4`, `3-5`, `3-6`).
4. **Report Lambda and formatters:** run old and new code on identical cached inputs and diff:
   scores and numbers must not change when only wording changes.
5. Read a few outputs. Tests that only count lines miss wrong content.
Not testable this way: anything behind a real login (payments, dashboard screens, real trial
accounts). Say so when reporting.

## 8c. Dashboard: practice portfolio and AI autopilot (read this before working on the dashboard)

Built 10 Oct 2026 from the owner's idea of "fake money" to see whether the analysis works in his
favour, then extended the same day into an autopilot that trades it. **Everything here is fake
money: no real trade is ever placed, and nothing here may ever be connected to real money.** This
section is written from the code as deployed on the evening of 11 Oct 2026, and was swept in full then: the
function, the scripts and AWS were compared with it. **A new session starts at "Start here when resuming" near the
end of this section.** Verify against the code before relying on a detail (section 10).

### What the owner sees on the dashboard

The dashboard was one long page until the owner asked for it to be tidied (10 Oct). It now has
**three tabs** under the heading: 📈 Reports, 💵 Practice portfolio, 🤖 AI autopilot. One panel is
shown at a time; the choice is remembered in the browser (`localStorage` key
`stockiqDashboardTab`) and kept in the address (`dashboard.html#practice`, `#autopilot`), so a
refresh or a link lands on the same tab; any other address (`#upgrade`) opens Reports. Every signed-in account has all three tabs; without a paid plan the AI autopilot tab shows what it is and a button to the plans (its tab carries a 🔒). The markup is `data-dash-tab` buttons and `data-dash-panel` blocks, with a small inline
script between the `DASH_TABS_SCRIPT_START/END` comments in `dashboard.html`
(`window.dashboardTabs.show(name)` switches from code). **A link that must land on Reports whatever tab was open last
says so: `dashboard.html#reports`** (the link under a screener's results, "download from your dashboard", since 13 Oct
2026). The tab script opens Reports for it and does not change the remembered tab, so a plain visit still returns to
where the visitor left off. Report code keeps working while its panel
is hidden. **Keep the Reports panel first in the page**: one report routine finds "Recent Reports"
with `document.querySelector('h3')`.

**Practice portfolio** (its own tab, container `#practice-portfolio`):
- **The top is three figures** (`.pp-top`): **since 17 Oct 2026 Account value (with its change since the start under it, "▼ $356.77
  (0.36%) since the start"), Today, and Against the S&P 500** (the account against the same $100,000 put into an S&P 500 fund
  when it began, in dollars, with what the fund would be worth now: `fundCard`; without the fund's prices back to the start,
  what is still held against the fund over the same days). It was Account value, Today, Since the start, with the fund in the
  one line below, until the owner suggested folding "since the start" into the first card. Then one line (cash and in
  holdings: `.pp-facts`), then **"The breakdown" folded**
  (`#pp-more`, kept open across redraws by `moreOpen`). **Since 17 Oct 2026 the breakdown is one profit-and-loss table**
  (`breakdownHtml`, class `pp-stack pp-pl`): rows "Sold" (made or lost for good), "Still held" (on paper, at the latest
  prices), "Since the start" (the two together, in bold); columns "Your own buys", "🤖 AI autopilot", "Together" (one column
  "Result" until the autopilot has bought anything; `splitGain` gives the figures, and every row and column adds up). Under
  it one line, "Where the money is" (cash, in holdings, what was put in, together the account value), and two lines against
  an S&P 500 index fund: "The whole account" (as the graph: the starting $100,000 in the fund since the start, ahead or
  behind in dollars) and "What is still held" (since bought, against the same dollars in the fund on the same days,
  `versusFund`, which says that what was sold is not in it). On a phone each row is a card with the three columns labelled.
  It replaced the four cards and the "whose result is whose" row described below: the same "Today" stood there twice with
  two percentages (1.02% of the account on top, 1.29% of the holdings in a card), which the owner took for a fault. **The
  "Today" figure now has one percentage, of the account, at the top only.** The bullets below on the cards and the row are
  history. The owner, from a picture: "this is honestly confusing… its just too much": about seventeen
  figures had stood there at once, several of them twice. **When adding a figure to this tab, put it in the breakdown
  unless it answers "what is it worth, how is today, how is it overall".**
- Four cards: Account value (the cash plus every holding at its latest price; under it the change
  since the start, split into what has been sold and what is still held), Practice cash left, In
  holdings, and "For comparison" (the same money in an S&P 500 index fund instead; it says "no change
  yet" while the US stock market has not traded since the buys, e.g. a weekend: `marketFlat`).
  **Nothing is shown until the latest prices are in** (4 seconds at most; **the site's spinner meanwhile, not the word
  "Loading…", since 13 Oct 2026**: `.spinner` of `styles.css` inside `.pp-wait`, in `dashboard.html`'s first markup and in
  the script's `render`; and the wait is shorter: the symbols it needed last time are kept in the browser,
  `stockiqPracticeSymbols_<address>`, and their prices are asked for at once, alongside the portfolio, `knownSymbols`.
  Measured on the owner's account: 3.5 s → 2.3 s on a first load, 1.4 s → 1.1 s after. What is left is the prices
  themselves, fifteen calls to the price function: one call that answers for a list of symbols with their daily
  prices would be the next gain): before 10 Oct the page
  first showed holdings at what was paid, which the owner took for a second, "correct" account value.
- **"Today"** (12 Oct 2026, evening; the owner: "say i jump on in the middle of the day ideally what i probably want to know is
  how much has it gained or lost today"). The Account value and In holdings cards show "Today ▲ $198.49 (0.27%)" above the
  total, and the holdings table has a **Today** column beside **Since bought** (it was "Change"). `dayMove(h, quotes)`: each
  holding since its market's previous close (a coin: since 00:00 UTC), or since it was bought when that was later; while
  its market is closed it is its last session, as a broker shows it; `summarize` adds them up (`dayUsd`, `dayPct`,
  `dayCount`). From the daily prices that already come with every quote (`series`): no extra request. A share's session
  ends are worked out from a 6.5-hour session, so a point under five hours before the latest price is taken for the
  session still running (London's afternoon), not the one before. **What it leaves out, and the fine print says so: a
  sale made today** (its result is in "Sold"); the exchange rate's own move in the day. The chat's summary carries the
  day figure; its guide does not describe it yet.
- **A graph of the account over time, under the cards** (12 Oct 2026; the owner: "an easy way to see progress… if we lose
  money for a week or two then gain over a few weeks, its clear we are making progress"). One line: the account's value
  since it began against a dashed line at the $100,000 it started with. Buttons switch the line to "Your own buys" or
  "🤖 AI autopilot" (that part's gain or loss against zero; shown once the autopilot has traded) and, once the account is
  old enough, to the last week or month. The pointer (or a finger) reads off the moment and the figure; "Show the
  figures" unfolds a line a day. Remembered in the browser: `stockiqPracticeChartRange` (how far back) only.
  - **The same three buttons choose whose holdings are listed** (13 Oct 2026, the owner's idea; he wanted no second row of
    buttons): with "Your own buys" or "AI autopilot" pressed, the Holding table and the Sold list show only that party's
    (`partOf(list, key)`, exported for tests), the headings count "Holding (11 of 12)" / "Sold (3 of 4)", and a line above
    the table says "Showing the 🤖 AI autopilot's: 11 of 12 holdings. Show all" (`#pp-part`; "Show all" is the Account
    button as a link). The three figures at the top and the breakdown are always the whole account. **The choice is kept
    while the page is open (a refresh of prices and the minute-by-minute redraws leave it) and is not remembered:** a
    page opened afresh shows everything (`stockiqPracticeChartKey` is no longer written, and an old one is removed).
    While only a part is listed, "Clear sold list" is not offered (it empties the whole list). The buttons exist only
    once the autopilot has bought something; before that there is nothing to choose.
  - **Worked out in the browser, nothing stored and nothing extra fetched** (`valueSeries`, `seriesOf`, `chartSvg` in
    `practice-portfolio.js`): the price source answers every quote with a month of daily prices, which the page used to
    throw away. A holding still held is valued at those daily prices and at its latest price now. **A holding that was
    sold is a straight line from what was put in to what came back**: exact at both ends, a guess in between. The line
    always ends on the figure the Account value card shows, and the user's and the autopilot's parts always add up to it.
  - **Limits, say them when the graph is discussed:** daily prices, not hourly (a quick trade shows as a straight segment);
    a holding kept longer than the month the price source covers is a straight line before that month; the result of
    sales no longer in the sold list (cleared, or past the 200 the storage keeps) has no dates left and is counted from
    the start, which the note under the graph says with the amount; a "Reset fake money" starts the line again.
  - The line is one blue (checked against the light and dark backgrounds), never green or red: up and down are said by the
    arrow and amount above it. The picture is drawn to the width it has and again when that changes (`ResizeObserver`).
  - **A second line: the same $100,000 in an S&P 500 fund since the account began** (13 Oct 2026, the owner's idea: "add the s&p
    as if i was in at the same time with 100k… then i can see over time how i'm comparing"). On the Account view only (the
    two part views are a gain against zero). `fundKnots(state, quotes, now)`: the starting cash put into the fund (SPY) at
    `createdAt` and left there, built as a holding is (the fund's daily closes, then its latest price); **no trading cost
    is taken off it and no dividends are counted**, and the note under the graph says so. The fund's price at the start is
    the last close at or before it; or, when the US market was open at that moment and something was bought later in the
    same session, the `spyAtBuy` kept with that buy. `versusStart` gives the fund's worth now and the gap.
    - **Above the graph are two lines, each led by its colour (they are the key as well):** "Your account $98,463.27 ▼ $1,536.73
      (1.54%) since the start" and "The same $100,000 in an S&P 500 fund $99,939.63 ▼ $60.37 (0.06%) · your account is
      **behind it by $1,476.36**" (`chartRead`; who is ahead is said in words and in dollars; the pointer moves both dots).
      "Show the figures" has the fund and "Against the fund" a day.
    - **The one line under the three figures now says the same thing as the graph** ("Against the same $100,000 in an S&P 500
      fund since the start: behind by $1,476.36"). It used to give the breakdown card's figure (only what is still held,
      against the same dollars in the fund on the days they were put in, in percent): two different "behind the fund"
      figures on one screen would have been read as a contradiction. **The card in the breakdown still gives that other
      sum, and can point the other way**: on the owner's figures the day it went live it read "ahead of the fund by 0.27%"
      beside "behind by $1,557.97". So the card says which it is: "the money in what is still held, in an S&P 500 index
      fund instead… Only what is still held is counted here, not what was sold: the graph compares the whole account"
      (`versusFund`). Without the fund's prices back to the start, the one line keeps its old wording.
    - **Colours:** the account `--pp-line` blue, the fund `--pp-fund` `#c98500` (gold) in both themes; the pair was run
      through the dataviz skill's validator on the light and the dark background (colour-blind separation, contrast).
      Never green or red for a line.
    - **The fund's prices must reach back to the start.** The price function answers with a month of daily prices; it now takes
      an optional `&range=` (`3mo, 6mo, 1y, 2y, 5y`; anything else is the month, as before). `fundRange(createdAt, now)`
      says which is needed (none until the account is 24 days old), `refreshQuotes` asks for it for SPY only, and it is
      remembered in the browser (`stockiqPracticeFundRange_<address>`) so the first request of a visit is already the
      right one. **This path has not been seen live yet: the owner's account is 3 days old. Look at the graph after
      about 4 Nov 2026** (the fund's line must still start at $100,000 on 10 Oct). Past five years there is no line.
    - **Between two closes both lines are straight** (a holding's and the fund's alike, on purpose: built the same way, the
      gap between them is not distorted). So a figure for a moment in a weekend or a night is an in-between value: "Show
      the figures" gave the fund $99,992 for the Saturday the account began, when it was really still $100,000 until
      Monday's session. Exact at each close and now.
    - Limits: daily closes, so the fund's line is straight within a day; the two lines share one axis, so a large move
      of the fund flattens the look of the account's line; a "Reset fake money" starts both again.
  - Not built: an hourly line (the price source would need an `interval` setting).
    The AI chat knows the graph and the fund's line (its guide, and the page's `summary()` gives it the figures).
- **A result is an arrow and an amount**, as a broker's screen shows it: `▲ $801.50 (0.80%)` in green, `▼ $58.48 (0.06%)`
  in red, `– $0.00` in grey (`movedHtml`, `pctHtml` in `practice-portfolio.js`; `deltaHtml` in `practice-autopilot.js`).
  The words stay as each arrow's `aria-label` for screen readers, and `moved()` gives the words ("down $58.48") for the
  AI chat's summary. History: the owner could not make sense of bare signed figures ("Of the -$58.48 since the start: your
  own buys +$144.12…"), so they became words, and then at his request arrows ("look like a professional stock
  portfolio"). **Never a bare signed figure without an arrow.**
- One framed row, **whose result is whose**, with **the same split for both parties** (12 Oct 2026): "Your own buys ▲ $144.12
  (sold ▲ $144.12 · still held – $0.00) · 🤖 AI autopilot ▼ $1,138.16 (sold ▼ $202.60 · still held ▼ $935.56)" (`splitGain`,
  with `yoursSold` / `yoursOpen`; shown once the autopilot has bought anything). The Account value card's own two lines
  then read "Sold, yours and the autopilot's together ▼ …" and "Still held, together ▼ …". Before this the card said
  "Sold ▼ $58.48" and the row "sold ▼ $202.60", which add up but looked to the owner as if they disagreed. **Whenever one
  figure is a total of two others shown nearby, say so in its label.**
- **"↻ Refresh prices" and "Reset fake money" sit beside the heading** (12 Oct 2026; on a phone, under it), in a place the
  page holds for them (`#pp-tools` inside `.pp-headrow` in `dashboard.html`; `toolsHtml`). Without that place (an older
  page) they are drawn at the bottom as before. A refresh says "Getting the latest prices…" with a spinner on the button,
  then "✓ Prices updated 10:21:05" in green for a moment; afterwards the line reads "Prices as of …".
- **Buttons are classes, not inline styles** (`.pp-btn`, `.ghost`, `.big`, `.busy` in the `pp-style` block; `.ap-btn` and the
  two links "Refresh now" / "Send me a test email" in the autopilot's): a hover colour, a pressed look, a spinner and a
  word for what it is doing ("Buying…", "Selling…", "Clearing…", "Resetting…", "Refreshing…"). An inline style cannot
  change on hover, which is why nothing did. `busy` says which button is at work (`run(task, key)`).
- **The "For comparison" card says who is ahead** (12 Oct 2026, evening; `versusFund`; its title is now "For comparison: S&P 500
  fund", at the owner's suggestion from a screenshot, so that the percentage is understood at a glance): under the fund's figure it adds "over
  the same days. Your holdings: ▼ 0.69%, so they are **behind the fund by 0.72%**" (or ahead of, or level with; first worded
  "by 0.72 points", which he found odd: "shouldn't it say .72%?"; plain wording wins over the precise term here). The
  owner had read the fund's "▲ 0.06%" as his account beating the fund. He considered a dollar figure for the fund too and
  decided against it ("too confusing % is probably enough"). The figure compares the holdings still held with the fund on
  the same money over the same days, not the whole account.
- **The "For comparison" card says when there will be something to compare** (12 Oct 2026): while the US market has not
  traded since the buys it reads "…has not traded since you bought (it opens in 9h 35m)". The figure is the dashboard
  sidebar's own (`#market-countdown-sidebar`, read by `marketWait`) when that is on the page, so the two cannot disagree;
  without the sidebar the script works it out by the same rule (`usOpensIn`: 9:30 to 16:00 New York time, weekdays, no
  public holidays in either). It used to say "it is closed at weekends", which was wrong on a Monday morning.
- **A share is bought or sold by hand only while its market is open** (17 Oct 2026; the owner sold TLS.AX on a Saturday, at
  Friday's close, and asked for it to wait for the market): the same rule as the autopilot's, a price that has traded in the
  last 3 hours (`FRESH_HOURS` here and in `stockiq-ai-trader`: keep the two the same; `closedFor`, `closedText`). Coins and
  a quote that gives no time are never held back. A closed share's Sell button reads "Market closed" (greyed, the reason
  in its tooltip); a buy or a sale asked for anyway (the buy row, the 🎯 popup's "Practice buy") is refused with "<code>
  cannot be bought now: its market is closed. Its last price is from <time> (N hours ago)… Try again once its market is
  open."; picking a closed share in the search says so in red under the row. It does not know a market's opening time,
  only that the last trade is old. In the first minutes of a Sydney or Tokyo session (the price source is about 20 minutes
  behind there) a share also waits, as the autopilot's do. `practice_test.js`'s stand-in treats every real price as fresh,
  so the tests trade on any day; its made-up `SHUT.AX` opens and shuts on demand (7 checks).
- **What is typed in the buy row survives a refresh of prices** (it was wiped: only a completed buy or a reset clears it now).
- The cards have small capital labels and a green or red top edge on Account value; table headings are small capitals,
  rows highlight under the pointer, figures use tabular numerals.
- The notification bell in the page header lists the autopilot's buys and sells with the reports: its own part below,
  "The notification bell".
- The buy row: search box (code or company name, same lookup as the home page), "Enter $" **or**
  "or quantity" (the other is worked out from the latest price), an optional note, "Practice buy". The note is shown on
  a line of its own under the company's name ("Note: …"; the autopilot's reason, "AI: rank 1, …", likewise).
- The holdings table (its columns since 12 Oct: Holding, Bought, Price then, Price now, Value, Today, Since bought, Sell): Holding (with how many are held, "Holding (5)", as the sold list says "Sold (7)"; 12 Oct 2026, at the
  owner's word; on a phone the heading row is hidden, so the count shows on wider screens only), Bought (date and time), Price then, Price now, Value, Change, Sell.
  Under each name a line says whose it is: "Bought by you: it stays until you sell it", or for the
  autopilot's, **folded behind "🤖 Autopilot: its plan for this ▸" since 12 Oct 2026** (`details.pp-plan`; an opened one
  stays open across redraws, `openPlans`; the owner wanted the row down to the name, the company and why it was bought), when it will sell at the latest, at what loss or gain sooner, how the stop that
  follows it works, and, while its market is closed, that nothing happens to it until the market
  opens, with the time.
- **Only the latest 10 holdings are listed** (17 Oct 2026, the owner, at 39 holdings: "make it so this list only shows the most
  recent 10 ... then has option to show all"), newest first, then "Show all 39 (29 more)", which turns into "Show only the latest
  10" (`HELD_SHOWN`, `allHeld`, `#pp-held-more`; kept while the page is open, not remembered, as "What it has done" on the
  autopilot tab does with its 8). The heading still counts them all ("Holding (39)").
- **The gap to the S&P 500 fund is given in percent as well as dollars** ("▲ $1,610.28 (1.61%)", on the third figure at the top,
  in the breakdown's "The whole account" and above the graph; the owner asked whether a percent made sense, 17 Oct 2026). It
  does: both started with the same money, so the dollars over the starting amount are exactly the difference between the
  two returns (the account -0.36%, the fund -1.97%: 1.61%).
- "Sold (N)" folded list with a summary, "Clear sold list" and an × per line (clearing only tidies
  the list: what a sale brought in is already in the cash). "Refresh prices", "Reset fake money".

**AI autopilot (Beta)** (its own tab, container `#practice-autopilot`; every logged-in account sees the tab, accounts without a paid plan see the locked view). **It is labelled Beta wherever it is named to users** (the owner, 11 Oct: "more professional, as in under testing"): the panel heading (`ap-beta` badge), the dashboard tab ("🤖 AI autopilot (Beta)", also set by `markTab`), the plan cards, the home page pricing and the FAQ, each time with "new, and still being tested and changed". Keep the label when adding text about it. The
on/off switch, the status box (what it holds, last and next check-in, and **a live countdown to the
next check-in**), a **"Needs you"** line (green "Nothing needs you right now", or an amber box
listing what only the owner can put right) and the buttons "Check in now" / "Sell everything it
holds" sit at the top; below them the panel is in **two parts, Activity and Settings**, so neither is a long scroll (it opens on Settings until it is switched on with a
screener, then on Activity; the part last looked at is remembered, `stockiqAutopilotPart`). Both
parts are always in the page and one is hidden, so settings are read and saved whichever is on
show. Settings holds the first five items below, Activity the last five. **Since 18 Oct 2026 Activity opens on a short summary** (the
owner: "wondering if there is just too much going on in the site"; it showed about 13,000 characters before anything was opened):
the market-risk gauge, "What happens next" with 3 rows on show, "How it is doing" with 5 holdings on show (a row's reason cut
to 90 characters, all of it in the plan), the themes part in one line (`themesLine`, "Its detail" opens the fold), and the
latest 5 entries of "What it has done"; **the bar, the themes part in full, progress every 20 trades and "How it is improving"
are under one fold, "More detail"** (`data-ap-fold="more-all"`; a jump link opens any fold it lands in). About 6,400
characters on show. **The way back, one command:** `bash /Users/dave/VSCODE/stockiq/check-tools/pending-simple-undo/deploy.sh`
(keep that folder):
- (**The "Quick set-ups" are gone since 13 Oct 2026.** "Quick coin trading", "Steady shares" and "Shares and coins" each
  replaced the screeners ticked **and the pace and the level**; the owner lost his settings to them twice in one evening
  and a check-in traded on one of them: section 13. Their place is taken by the shortcuts in the screeners card, below,
  which change only what is ticked. In their place at the top of Settings stands one sentence: every change saves
  itself, a change by itself buys or sells nothing, and a scheduled check-in waits until the settings have been left
  alone for 10 minutes.)
- **Risk level** slider (Cautious … Adventurous) with a sentence of what the level means, and
  **Your own limits**: two optional fields, "Sell at a loss of __ %" and "Sell at a gain of __ %",
  and a **Trailing stop** menu (protects a gain / from the moment it is bought / off) with a line
  saying what the chosen kind does.
- Budget for the AI, and the three **pace** fields: Build up to it over (days), Checks in, Keeps a
  holding at most. Each pace field is tagged "automatic" (it follows the risk level and moves with
  the slider; shown as an empty box that reads "Automatic: 5" in grey, or "Automatic: …" in a menu; the bare grey number it showed until
  12 Oct 2026 read to the owner like a value typed in) or
  "set by you" (it stays put); a link hands all three back to the level. Then **two lines that
  describe what exactly these settings will do**.
- Screeners it buys from: all 27 of the site's, grouped as its Screeners menu is (US markets, Europe markets,
  Asia-Pacific markets, Americas markets, Coins). **Shortcuts** (`data-ap-pick`, `MAIN`): "🌍 Main index of every country"
  (one index a country, none inside another: S&P 500, FTSE 100, DAX 40, CAC 40, SMI, AEX, FTSE MIB, IBEX 35, ASX 200,
  Nikkei 225, Hang Seng, Sensex, KOSPI 200, STI, TSX 60, Bovespa; the coin screener is left as it is) and "Clear all";
  **a click on a market's name** (`data-ap-group`) ticks all of its screeners, or clears them when all are ticked. Each
  is followed by an "Undo" in the notice (`presetUndo`: what was ticked before the first of them). They never touch
  the pace, the level or the budget. **Never call them "picks" on the page or in the chat's guide** (the wording
  rule; the chat's own test refuses the word). The card also says that overlapping lists do no harm. Under each market with a ticked screener: a
  menu "Share of the budget" (automatic, or a step picked by hand), and under the card one line in
  words on how the budget is spread.
- **What it may do by itself**: two switches (try changes to its own rules, email me its reviews). **"Sell early on the AI
  model's review" was taken out on 17 Oct 2026**: 31 trades at -1.46% a trade against -0.62% for every other kind of sale, and
  the shares it sold early mostly went on rising. `AI_SELL = False` in the function makes the setting off for every account
  whatever a page sends; the panel says why in one line; the review's code stays, tested (`ai_trader_test.py` sets `AI_SELL`
  on), so that it can only return as a trial with a newer model (`experiments.json`, "ai-review-off" and "newer-model"). Under the email switch: what became of the last email
  ("accepted by the mail service", or "could not be sent" and why) and "Send me a test email".
- (At the top, beside the buttons: a line saying "Saving…" / "✓ Saved." / "Not saved: reason".
  There is no save button: every change saves itself.)
- **What happens next** (first under Activity, added 11 Oct): what is coming, soonest first, each
  with a countdown that ticks and its time: the next check-in and what it may do, the next release
  of the budget, the first check-in after each closed market opens, the latest each holding is
  kept; then what goes by the number of finished trades (its own review, the AI model's notes).
  A sentence under it says that reviews and trials happen by themselves and nothing has to be pushed.
  **Since 17 Oct 2026 the holdings' last days are one row** ("39 holdings reach the end of their holding time between Thu 22 Oct
  and Tue 27 Oct …", each of them folded under it; `comingRows`), and a release of the budget at the same minute as a check-in
  is left out (that check-in's row already says what it may buy). On the owner's real list it had been 51 rows, 39 of them
  "X is sold at the latest". Market names read "A, B and C" (`words_and` in the function, `andList` in the panel).
- **How it is doing** (**"Holding now" is a row a holding since 12 Oct 2026**, newest first: bought, sold by, its limits, and small tags for what is particular to it (market closed until…, where its stop stands, a patient share, the AI review's last word), with the full sentence of its plan folded under it; eight rows on show, the older ones folded away (`heldRow`, `heldPlan`, the `.ap-held` styles). **Tidied the same evening from a picture of his panel:** a row is now the symbol, the company and why it was bought (`boughtFor`, from the buy's line in the activity list), a tag only for what is particular to it (market closed, a gain already protected, a patient share, a review that said tighten or sell), and a fixed "its plan ▸" on the right that opens the rest in place; the dates, limits and the ordinary stop that every row repeated are in the plan only. Ten holdings had been one paragraph nobody could read, and there can be fifty. Its folded "Breakdown" table was laid out afresh on 11 Oct after the owner could not tell a group heading from the rows under it: each heading is a band of its own (`ap-bd-head`), its rows are indented, and the "Against an index fund" column is shown only when it differs from the average for some group; styles are the `.ap-bd` rules): what it holds now and when each will be sold, with the AI model's latest
  review of it; the last 30 days in dollars and as a share of the budget; finished trades (up /
  down, average); a folded breakdown. (**The AI model's notes are no longer shown there** since 17 Oct 2026: they restated the
  breakdown in words with the counts of the day they were written, so the page showed two different counts for the same
  group. The model still reads them when it chooses.)
- **Progress, 20 finished trades at a time** (added 11 Oct): a table with a row per batch of 20
  (trades, dates, how many ended up, average a trade, dollars, "better / worse / about the same"
  against the 20 before, and what it did about it), newest first, the batch still filling on top;
  what stood out in the last complete batch can be unfolded. Before the first 20 it says when the
  first report comes and what happens then.
- (Each line of "Improvements made" below says in a word what became of it: **Kept** (green), **Not kept**, **Taken out**
  (grey). It was ✓ / ✗, and the ✗ beside "The AI model no longer sells holdings early" read as a failure when it was a change
  for the better. The Admin page's list says the same words.)
- **How it is improving** (since 17 Oct 2026; it was "Improving its own rules"): a short list for every user, in three parts:
  **being tested now** (its own running trial of a rule, the patient-shares trial, and the site's changes marked public that are
  still being measured, each with its start and the day it is decided), **improvements made** (✓ kept / ✗ not kept or taken out,
  with the date: its own past trials, the ended buying-order trial, the public site changes decided; five shown, the rest folded)
  and **coming next** (public ideas). The rules in force, which are set by the owner, which it changed itself ("put it back"),
  the running trial in full ("Stop this trial") and earlier trials are folded under "The details". The site's items come from
  `check-tools/experiments.json`: an entry with `public: true` and a `publicText` (plain words, nothing private) is shown; the
  function sends them as `improvements` (`public_improvements`, kept 15 minutes in the warm function; copied there by
  `admin.py sync`). **The owner's full list, with everything private and the parts of the site reviewed, is on the Admin
  page's Improvements view** ("The owner's Admin page"): the user's version is the light one on purpose ("one is for everyone
  the other is just for me").
- **What it has done**: every buy, sell and check-in note, newest first; "Why, and the details" /
  "The plan for it" folded under each trade; "Refresh now"; a switch "Buys and sells only".

### Two boxes that look alike, and are not the same (17 Oct 2026)

The owner asked whether these were duplicates. They are not, and each now says what it is for:
- **"Needs you"** on the AI autopilot tab (every user who has the autopilot): what only the user can put right about their own
  autopilot: switched off while holding something, no screener ticked, every screener resting, too little practice cash, a
  check-in that failed or did not happen, a refused email (`needs()` in the function). Empty: "✓ Nothing needs you right now:
  its settings, cash and screeners are all in order, and it runs by itself." It used to add "nothing has to be approved or
  pushed", which was true for a user and read wrong beside the Admin page, where the owner does approve things.
- **"Decisions for you"** on the Admin page (the owner only): proposals to change the site or its settings that the weekly
  review or a session puts to him for a yes or no (`admin_propose`). Empty: "✓ No decisions waiting", and a line saying that
  anything wrong with the autopilot itself shows on its own tab, as for every user.
- So a problem with the autopilot appears in the first; a choice about how the site should change appears in the second.
  Never put the same item in both.

### The notification bell (one list, on every page)

Built on 11 Oct 2026 in several rounds; this is the state it ended in. The story of the rounds is in section 9.

- **What it shows.** The 🔔 in the page header opens one list headed "🔔 Notifications": the account's reports and the AI
  autopilot's buys and sells **together, newest first**, each line saying which it is ("📊 Report · time" / "🤖 AI
  autopilot (Beta) · name · time"); it ends with "View Dashboard". A trade reads "Sold at a profit: CFX-USD ▲ $12.79
  (1.0%)", "Sold at a loss: … ▼ …" or "Bought: … $1,250". Only real buys and sells, never check-in notes.
- **Unread and the red number.** Trades made since the bell was last opened are counted in the red number together with
  unseen reports; opening the bell clears the number, but a line stays marked unread (blue dot, bold, a coloured edge;
  the heading says "3 unread: 1 report, 2 autopilot buys and sells") until one is clicked. The first list a browser gets
  is not news. A click on a trade opens the autopilot tab's list "What it has done"; on a report it does what the page
  does with a report (`viewAnalysisFromNotification`), or goes to the dashboard.
- **Where.** Pages that open a list on the bell (dashboard, home page, analysis page, stock pages, login on a phone) show
  the one list. On the pages whose bell only goes to the dashboard (About, FAQ, the guides, legal pages) the red number
  shows and the click goes to the dashboard as before. Nothing is shown to a visitor who is not signed in.
- **One script draws it for every page: `website/autopilot-bell.js`** (`window.autopilotBell`: `version, set, trades,
  reports, unseen, unread, markSeen, markRead, html, place, open, report, badge, load, onTop, state`). Each page used to
  draw its own report list in its own code; the owner called that "a shit setup… would have been nice to have it all setup
  in one way". The script does not depend on how a page draws its bell: it listens for a click on `#notification-bell` /
  `#mobile-notification-bell`; if the page opened `#notification-dropdown` it empties it and puts the one list in
  (`#bell-list`, built by `html`, `reportRow`, `tradeRow`); it watches that list and draws it again when the page redraws
  its own; and it watches the two badge elements to add its count to whatever number the page sets. The page still
  opens, places and closes the list, and supplies the reports (`analysisHistory`) and what a click or "run again" does.
  If the script fails, the page's own list simply stays.
- **How it is loaded.** Signed-in visitors only. Each of the 17 hand-edited pages with a bell has one line after its
  `theme.js` tag, between the comments `AUTOPILOT_BELL_START/END`; `dashboard.html` has the same line near its other
  scripts; and `theme.js` asks for it too, which is what covers the generated stock pages. **The address is relative and
  has no version number**: `autopilot-bell.js?h=<the hour>` beside the page (`theme.js`: beside itself). **Never
  "/autopilot-bell.js"**: that exists only when the site is at the top of its address (section 9). Because the address
  changes every hour and browsers keep a script five minutes, **a change to the script needs no edit to any page**.
  Inside the script `SITE` is where it was loaded from; its links are built from that.
- **Where the trades come from.** On the dashboard the panel hands over its own list (`practiceAutopilot.bellFeed` →
  `autopilotBell.set`). On every other page the script asks the function's **read-only action `bell`** (`bell_trades`:
  the last 12 buys and sells with `t, type, symbol, name, usd, gain, pct`; it is not a visit and writes nothing; an
  account without the autopilot gets an empty list) at most every two minutes (30 for an account without it) and keeps
  the answer in the browser (`stockiqBellTrades_<address>`) so that every page and tab shows the same. A sale's dollars
  are the entry's `gain` (stored since 11 Oct) or are read from an older entry's words ("Put in $X, got back $Y");
  entries from before that have no name.
- **In the browser's store:** `stockiqBellTrades_`, `stockiqBellBell_` ("seen": clears the red number), `stockiqBellRead_`
  ("read": clears the unread marks); the reports' own keys `unreadReports_` and `seenReports_` belong to the pages.
- **It takes over from an older copy of itself** (`VERSION`, 8 at the sweep): a browser can run an older copy for a while
  after a change, and an older copy that ran first once shut the current one out. The current one always takes over,
  empties the store of the copies before version 4 (`stockiqAutopilotTrades_…`), marks its question to the function
  `list: 2` (**the function answers `bell` only then**), carries on its list the signature a version-3 copy expects
  (`olderSig`) so that copy leaves the list alone, and stops redrawing if something undoes the list more than 12 times in
  two seconds (`state()` says so, with any `fault` met while drawing). This part can be thinned out once no browser can
  still hold a copy from 11 Oct 2026 (a week is ample): keep the "newer version wins" guard.
- **Tests.** `node check-tools/autopilot_bell_test.js ../website/autopilot-bell.js` (22 checks); a stand-in page in a real
  browser: `python3 check-tools/bell_page.py ../website/autopilot-bell.js /tmp/bell.html light trade` (or `report`); and
  **the live pages as a real account**: `REAL_USER=<address> PASS_GET=1 SHOT=/tmp/bell.png node
  check-tools/live_bell_check.js dashboard.html index.html analysis.html` opens them in headless Chrome as that account,
  lets only its read-only questions through (everything else the page asks is answered locally, so nothing is written),
  and prints what the bell holds. Its other switches reproduce what a particular browser sees: `BASE_URL=` (the local copy
  served from a folder, as a local preview does), `OLD_THEME=` / `OLD_BELL=` (old copies played back), `NO_THEME=1`,
  `LOCAL_BELL=` (a staged copy tried on the live pages before deploying). Details in `check-tools/README.md`.
- **Limits:** a notice on the site, not an email or a phone notification. The 14 pages whose bell goes to the dashboard
  have no list of their own. Not checked on a phone.

### Files and services

| Thing | Where | Notes |
|---|---|---|
| Portfolio section | `website/practice-portfolio.js` (`?v=42` in `dashboard.html`) | Sums and page, and the graph of the account over time (`seriesOf, valueAt, valueSeries, axisTicks, chartSvg`, and for the S&P 500 fund's line `fundRange, fundKnots, versusStart`, also exported). Pure functions exported for tests: `newState, fxFor, fxRate, versusMarket, applyBuy, applySell, applyClearSold, soldSummary, valueOf, summarize, splitGain, planLine` |
| Autopilot panel | `website/practice-autopilot.js` (`?v=61`) | Controls and reports only; decisions are made by the Lambda |
| The bell (one list for every page) | `website/autopilot-bell.js` (asked for as `?h=<the hour>`, no version to raise; fetched by each hand-edited page with a bell, by `dashboard.html`, and by `theme.js` for the stock pages) | The autopilot's buys and sells in the notification bell |
| Page | `website/dashboard.html` | The tab bar, the three panels with the two containers in the second and third, the tab script before the footer, and the two script tags at the end. **Raise `?v=N` whenever a script changes** (since 11 Oct browsers keep a script only five minutes, so this is a belt on top of that, not the only way a change arrives) |
| Portfolio storage | Lambda `stockiq-paper-portfolio` (128 MB, 10 s), table `stockiq-paper-portfolios` | Actions `get`, `save` (with `expectedVersion`), `reset`. One item per user: `data` (JSON), `version` |
| Autopilot | Lambda `stockiq-ai-trader` (Python 3.12, 512 MB, 300 s, role `acp-lambda-role`), table `stockiq-ai-trader` | Actions `get`, `save`, `run`, `sellall`, `tune`, `mailtest`, `bell` (read-only, for the notification bell; `belllog` is answered and ignored, a leftover). Env `AI_TRADER_USERS` (accounts that may use it without a paid plan; everyone on a paid plan may use it; `*` would make it free for all) and `OPENAI_API_KEY` (never print it) |
| The diary | Table `stockiq-ai-trader-journal` (key `userId` + `at`, pay per request) | Every activity line, finished trade and change of settings, never trimmed; written by `keep_diary` at each save; read by `check-tools/autopilot_review.py` ("The diary, and the review every week or two") |
| Schedule | EventBridge `stockiq-ai-trader-schedule`, `cron(10,40 * * * ? *)` | Every 30 minutes; `SLOT_MINUTES` in the Lambda must match. **Disable this rule to stop everything** |
| Screener data | `stockiq-screener-coordinator` | Called with no `userId`, so nothing is saved to anyone's history |
| Prices | `stockiq-price-proxy` | Also exchange rates (`AUDUSD=X`, `USDJPY=X`) and the S&P 500 fund (`SPY`) |
| Headlines | Google News RSS (coins), Yahoo Finance RSS (shares) | Fetched by the Lambda; the AI model has no internet |
| AI model | OpenAI `gpt-4o-mini`, JSON replies; `gpt-4o` for the holdings review when a gain is at stake | Three uses: choose buys, review holdings, write notes. `aws lambda invoke … --payload '{"model_test": true}'` asks each one question and says which answered |
| Email | SES, from `autopilot@stockiq.tech` to the account's own address | The role has SES access; the owner's address is a verified identity (SES is still in sandbox) |

The Function URLs are written into the scripts. As everywhere on this site the `userId` is whatever the browser
sends. The autopilot acts for accounts on a paid plan and for the accounts listed in `AI_TRADER_USERS` (`allowed`).

### The practice portfolio in detail

- The browser does the sums and sends the whole portfolio; the Lambda checks shape and size and
  uses `version` so two tabs (or the autopilot) cannot overwrite each other. On a clash the page
  reloads and says so.
- A holding: `id, symbol, label, name, currency, qty, buyPrice, buyFx, costUsd, boughtAt,
  spyAtBuy, note`, and for the autopilot's `by: 'ai'` and `screener`. A sold one adds `sellPrice,
  sellFx, proceedsUsd, soldAt, spyAtSell`. `symbol` is what prices are looked up by (a coin may
  need Yahoo's numbered ticker); `label` is what is shown.
- Other currencies are valued in US dollars. **`fxFor` / `fxRate` here and `fx_pair` / `usd_rate`
  in the autopilot must follow the same rule**: AUD, GBP, EUR, NZD use the dollars-per-unit quote
  (`AUDUSD=X`); every other currency the per-dollar quote turned over (`USDJPY=X`), because Yahoo
  rounds `JPYUSD=X` to 0.0063. London prices are pence (÷100). A holding with no price shows at cost.
- `planLine(h, plan)` writes the "whose is it" line. The plans come from the autopilot panel through
  `practicePortfolio.setPlans(plans, { realizedUsd })`. `splitGain` uses that `realizedUsd` (the
  autopilot's own running total) so that clearing the sold list does not move its sales into "your
  own". `redraw()` re-renders without losing what is being typed in the buy row.
- `window.practiceBuyFromTop10` is the "＋ Practice buy" button on each line of the Top 10
  Performance popup (it uses the report's price-source ticker).
- **A trading cost is taken off every practice buy and every sale** (since 11 Oct 2026, evening): `TRADE_COST_PCT` 0.1 in
  `practice-portfolio.js` (by hand) and `TRADE_COST` 0.1 in the function (the autopilot); **keep the two the same**. The
  whole amount leaves the cash and a thousandth of it is the cost, so a holding starts a little below what was put in
  (`qty = amount × 0.999 / price`); a sale brings back `qty × price × 0.999`. No new field: the cost is inside `qty` and
  `proceedsUsd`, so every sum works as before. Holdings bought earlier have no buying cost in them. The line under the
  buttons says so. Reason: a record without costs flatters itself, most of all when trading often (section 7b).
- **The heading is just "💵 Practice Portfolio" since 13 Oct 2026**: the owner had the subtitle "fake money, no real trades" taken
  off ("it looks odd there and is obvious by the tab"). That it is fake money is still said on the Account value card
  ("fake money · it started with $100,000.00") and in the small print under the holdings; keep it in both.
- **Owner's decisions:** buying, selling and progress stay on the dashboard (no buy buttons on stock
  pages or reports). The S&P 500 columns and "N of M ahead" sentences were removed at his request;
  only the "For comparison" card remains. `spyAtBuy` / `spyAtSell` are still stored, because the
  autopilot's record uses them. Wording stays "practice", "fake money, no real trades".

### The autopilot: settings (table `stockiq-ai-trader`, cleaned by `clean_settings`)

| Setting | Values | Meaning |
|---|---|---|
| `enabled` | on / off (default off) | Only for accounts on a paid plan, or listed in `AI_TRADER_USERS` (`allowed`) |
| `risk` | 1–5 (default 3) | The level: see the table below |
| `budgetUsd` | 100 … the practice money there is (default 10,000) | The most it has invested at once. **It cannot be more than the practice cash plus what the autopilot itself has invested** (`money_of`, sent as `money`: `cash, invested, reach`). On 11 Oct the owner typed $200,000 against $100,000 of fake money and nothing objected; it would have bought one $50,000 holding and stalled. Now the panel says under the field how much there is (`budgetHint`), refuses a larger number ("Not saved: the budget can be at most …"), offers "Set it to $…" (`maxbudget`), and the `save` action sets a larger one to that amount and notes it (the backstop for an older cached script). An older, too-large budget does not block other settings from saving. **And a budget that is too large is put right wherever it is met** (`fit_budget`: when the page is opened (`get`), when settings are saved, at the start of every check-in), with the same line in the activity list: the owner had asked twice why $200,000 was still shown, because his saved figure predated the check. So the "Needs you" item `budget` should now never appear |
| `periodDays` | 1–90 | "Build up to it over": the budget is released in equal steps over this long. **Not the holding time** (the owner mixed them up twice) |
| `everyHours` | 0.5, 1, 3, 6, 12, 24 | How often it checks in |
| `maxHoldDays` | 0.5 h … 60 days, stored in days | The longest it keeps a holding |
| `auto` | any of `periodDays`, `everyHours`, `maxHoldDays` | **Which of those three are left to the risk level.** For a listed one `clean_settings` puts in the level's own value (`PACE`) every time, so the rest of the code only ever sees numbers. A new user leaves all three; settings saved before 10 Oct evening have none (all set by hand) |
| `screeners` | any of the 27 keys (default none) | Coordinator keys, every screener of the site since 13 Oct 2026: `3-8 3-100 3-7 3-3 3-2 3-4 3-5 3-6` (US), `5-ftse100 5-dax40 5-cac40 5-smi 5-aex 5-ftsemib 5-ibex35` (Europe), `4-50 4-100 4-200 4-300 5-nikkei225 5-hangseng 5-sensex 5-kospi200 5-sti` (Asia-Pacific), `5-tsx60 5-bovespa` (Americas), `7-1` (coins) |
| `aiSell`, `selfTune`, `emails` | on unless switched off | "What it may do by itself". **`aiSell` is always off since 17 Oct 2026** (`AI_SELL = False`, above) |
| `holdings` | empty, or 2–50 | **The number of equal holdings the budget is spread over** (12 Oct 2026). Empty: the risk level's own (12 / 10 / 8 / 6 / 4). With a number: each holding is the budget over it (`holdings_of`); it buys up to a fifth of them at a check-in instead of 3 (`buys_per_check`: 3 could never fill 50); it looks at least that far down each ranking, up to 30 (`rules_for` widens `top`); the shares of the budget per market are counted in that number (`market_slots`); never so many that one is under the $25 smallest buy. The panel: a field beside the budget, the level's number in grey, tagged automatic / set by you, with a line saying what the number means (`holdingsHint`; `positionsOf`, `buysPerCheck`, `withHoldings` are the panel's copies of the sums: `autopilot_plan_check.py` compares them). **A matter of how bumpy the ride is, not of profit** ("Ideas offered", the replay). Holdings bought at an earlier size stay their size until sold, so after a change the budget holds a mix |
| `stopPct`, `takePct` | empty, or 1.5–30 and 2–80 | The owner's own loss limit and gain mark, as sizes in percent |
| `shares` | `{market: percent}`, only for markets set by hand (default none) | A market's share of the budget. Markets are the groups of `SCREENERS` (`GROUPS`, since 13 Oct 2026 the regions of the site's Screeners menu: **US markets, Europe markets, Asia-Pacific markets, Americas markets, Coins**; until then one a country: US shares, Australian shares, UK shares, Japanese shares, Coins. A share saved under an old name is carried to its region, `OLD_GROUPS`). A market left out is automatic. Together at most 100 (`clean_settings` takes the excess off the later ones). See "How the budget is spread" below |
| `trailMode` | `gains` (default), `full`, `off` | The kind of stop that follows a holding. `gains`: it starts once the holding has risen beyond its normal wobble. `full`: a full trailing stop loss, under the price from the moment of buying, so a faller is cut early (exit kind `cut`). `off`: none |

| Level | Holdings | Buys from the top | RSI under | 30-day move within | Loss limit | Gain mark | Coins at most, on automatic with a share market ticked too |
|---|---|---|---|---|---|---|---|
| 1 Cautious | 12 | 5 | 68 | 20% | −5% | +8% | 0% |
| 2 Careful | 10 | 8 | 72 | 30% | −7% | +12% | 0% |
| 3 Balanced | 8 | 10 | 76 | 45% | −10% | +18% | 25% |
| 4 Bold | 6 | 15 | 82 | 70% | −14% | +28% | 50% |
| 5 Adventurous | 4 | 20 | no limit | no limit | −20% | +45% | 100% |

- **The pace each level sets** (`PACE`, sent to the panel as `options.pace`; added 10 Oct when the
  owner asked why the slider did not move these fields): Cautious 10 days / once a day / 20 days;
  Careful 7 / twice a day / 10; Balanced 5 / every 6 hours / 5; Bold 2 / every 3 hours / 2;
  Adventurous 1 day / every hour / 1 day (build-up / check-in / longest holding). So one slider can
  drive everything, and anything set by hand overrides it. The quick set-ups set these by hand.
- **How the budget is spread over the markets ticked** (11 Oct; the owner asked whether ticking
  several screeners spreads the money evenly, and proposed a share per market with an override).
  It did not: only coins had a limit, so whichever share market opened first could take the rest
  (with US and Australian screeners ticked, Sydney opens 14 hours before New York). Now:
  - `market_split(settings)`: each ticked market's share as a fraction. A share set by hand
    (`settings.shares`) stands. What is left is spread **evenly** over the other ticked markets,
    except that **coins never get more than the level's share** (last column of the table) while a
    share market is ticked too. One market ticked: all of it, coins included.
  - `market_slots(settings)`: the split in **whole holdings** of the level (each holding is the
    budget over the level's number of holdings), fractions to the largest remainders, a tie to the
    market listed first. Balanced with US, Australian and coin screeners: 3 / 3 / 2 of 8.
    Adventurous: 2 / 1 / 1 of 4. Several screeners of one market count as that one market.
  - At a check-in each market's room is its holdings times the holding size, less what it already
    holds there (`group_room`); a market with no room is not offered, the AI model is told a
    market's limit, `choose(..., limits)` passes over picks beyond it and fills from the others by
    rank, and no buy is larger than its market's room. Holdings from a market that is no longer
    ticked stay until sold and still count against the budget, not against any market.
  - `coin_share(settings)` is now the coin market's holdings over all (it was the level's figure).
  - **A market whose every ticked screener is resting gets no share** (17 Oct 2026; `market_split(settings, resting)`,
    `market_slots`, `coin_share` take `state['rest']` at every call; the panel's `marketSplit` reads `data.resting`;
    `autopilot_plan_check.py` compares the two with resting cases too). From 15 to 17 Oct the coin screener rested (its
    trades had lagged) while still ticked, and coins kept 10 of the owner's 50 holdings: about $18,500 sat as cash and 38
    check-ins said "markets already hold their share… The rest is for Coins, bought when that market is open", which could
    never happen. Now the other markets share that part until the rest ends; the check-in note says "Coins get no share
    for now: its screener is resting until 29 Oct, so that part of the budget goes to the other markets" (`resting_words`),
    and the panel shows it in the market's box and in the line under the screeners (`restedUntil`). A market with one of
    several ticked screeners resting keeps its share. When the rest ends the market's share comes back and the others,
    then over their share, simply stop buying until holdings are sold.
  - **Layout of the card (redone 11 Oct, v34):** the owner "didn't even see the dropdown boxes for
    a while", and took the absence of a menu under UK and Japan (nothing ticked there) for a fault.
    Now: one line saying what to do; a coloured bar (`splitBar`, `#ap-splitbar`) with one part per
    market as wide as its share, and a grey "cash" part when shares set by hand leave some out; each
    market is a row of three columns (`ap-group shared`): name with its colour dot, the screener
    chips, and its share in an outlined box of its own on the right (`ap-share`, in the market's
    colour, `MARKET_COLOURS`); a market with nothing ticked says "No share of the budget: nothing
    is ticked in this market". Under 980px the share box drops below the chips.
  - The panel shows it: a menu per ticked market, "Automatic: 38% (3 holdings, $18,750)" or one of
    the steps (0 to all holdings, each with its percent and dollars), tagged "automatic" / "set by
    you" (`shareRow`), and a line in words (`splitText`) that also says when a market gets nothing
    and why, and when shares set by hand leave part of the budget in cash. Shares adding up to more
    than 100% are not saved ("Not saved: the shares you picked add up to 125%…"). **A share is
    picked from steps, not typed, so nothing impossible can be entered**; "5% in UK" at Balanced
    is not possible (one holding is 12.5%): choose a level with more holdings for finer steps.
  - `marketSplit` / `marketSlots` in `practice-autopilot.js` are **a copy of the Lambda's two
    functions** (between `MARKET_SPLIT_START/END`): `autopilot_plan_check.py` compares them for
    2,915 combinations of level, markets and hand-set shares. Change one, change the other.
  - Within a market the choice among its screeners is as before: by place in each screener's own
    ranking, then the AI model's pick. There is no per-screener share.
- The rules in force for a user are `rules_for(settings, state)`: the level, then what the
  autopilot changed itself for that level (`state.tune.values`), then the owner's own limits.
- A screener belongs to a market and is only traded while that market is open (`MARKET_HOURS`,
  UTC, Mon–Fri: US and Canada 14:35–19:55, Brazil 13:05–19:55, Australia 00:05–04:55, Japan 00:05–05:55, Korea 00:05–06:25,
  Hong Kong 01:35–07:55, Singapore 01:05–08:55, India 03:50–09:55, UK 08:05–15:25, the rest of Europe (`eu`: Frankfurt, Paris,
  Amsterdam, Milan, Madrid, Zurich) 08:05–15:15; coins
  always). Each market keeps its own last-checked time, so a user with US and Australian screeners
  is checked in both sessions. **The markets of what it still holds count too** (`its_markets`):
  on 10 Oct the owner un-ticked the crypto screener while it held a coin, and because only the
  ticked screeners' markets were looked at, the coin was left unattended (no time limit, no stop)
  until that was fixed the same afternoon.
- **Trading hours hold by hand too** (11 Oct; the owner: "no point it buying something when the
  market isn't open… making it unrealistic"). "Check in now" (10-minute gap between presses) and
  "Sell everything it holds" trade only in markets that are open: a closed market's last price is
  not one anybody could trade at. A closed market is named in the answer and in the activity list
  with when it opens (`opens_in`); "Sell everything" keeps the holdings of a closed market and lists
  them (`summary.closed`). A longest-holding time that ends while the holding's market is closed is
  acted on at the next opening, and the dashboard is given that time (`when_open`). Before this, a
  Nikkei share (4307.T) was bought on a Saturday at Friday's closing price.
  **Limits:** the hours are fixed windows a little inside the real sessions and know no public holidays.
  **So a share is bought or sold only at a price that has traded in the last 3 hours** (12 Oct 2026; `fresh`,
  `price_age`, `FRESH_HOURS`; every quote now carries `time`, the price source's `regularMarketTime`). On 12 Oct 2026,
  Sports Day in Japan, the autopilot had bought 6976.T at the Friday's closing price. Now such a share is passed over as a
  buy, left alone as a holding (not sold by the rules, not put to the AI model's review, its best and worst not moved)
  and kept by "Sell everything it holds" (listed with the closed markets). It also covers the first minutes of a session,
  while the price source (delayed about 20 minutes for Sydney and Tokyo) still shows the session before: the buy comes a
  check-in later, at a real price. The activity list says which shares were left alone and how old their prices were, on
  the check-in's own closing line (key `…+stale`), so a holiday shows as one counted line, not one an hour. Coins are
  not affected. A quote that gives no time counts as fresh. **Not covered:** a share so thinly traded that three hours
  pass without a trade in an open market is left alone too (rare for index members; the note says why).
  **A market in which only old prices were seen stays due** (12 Oct, the same day; `untraded` in `run_user`): it is not
  counted as checked (its last check is put where the chosen gap is already over), so it comes up again at the next
  half-hourly run. Without this, a check-in every 12 or 24 hours would have looked at Tokyo once a day, ten minutes
  after its opening, found the session before every time, and never managed a Tokyo holding. On a real holiday the
  market is looked at every half hour of its session and left alone each time (one counted line). One old price in a
  market that is trading does not keep the whole market due.
- Add a screener: one line in `SCREENERS` (name, coordinator option and subOption, kind, market,
  group). The panel lists whatever the Lambda sends. **The market is whose trading hours it keeps (`MARKET_HOURS`,
  `MARKET_NAMES`); the group is the region whose share of the budget it draws on**, so several exchanges share one
  region's share (Sydney and Tokyo are both Asia-Pacific now: before, each had a share of its own).

### One check-in, step by step (`run_user`)

1. Load the user's practice portfolio. `settle`: anything sold since last time, also by hand, goes
   into the history. `look_back`: re-price holdings sold a while ago (see "learning").
   `review_ai_sells`: pause or un-pause the AI model's early sells.
2. Fetch the chosen screeners' results (`get_snapshot`: a fresh run through the coordinator unless a
   copy under 20 minutes old is stored as `_snapshot#<key>`, so **the data is fresh at every
   check-in**), the latest price of each of its holdings, and exchange rates.
3. **Fixed selling rules** (`review_sells`), first that applies: at the loss limit; at the gain
   mark; **keeping part of a gain** (see below: `gain_arm`, `gain_floor`); held the longest
   allowed time; the screener
   signal turned negative or its score fell below zero; **slipped down the ranking** (below 5 times
   the level's ranking limit with under half the score it was bought on: `FADE`). A check-in up to
   5 minutes early still counts for the time limit (`GRACE`). Each holding's best and worst change,
   as seen at check-ins, is kept (`peak`, `low`), and its path (`path`: hours held and change at
   each of the last 16 check-ins).
   **Keeping part of a gain: the stop that follows a rising holding** (`follow_stop`; reworked twice
   on 10 Oct). The gain mark is where it always sells, but waiting for +18% on a 6-hour holding
   hands back most quick rises, and the owner then rejected fixed distances as "a dumb static
   rule". So the stop is set from **that holding's own movement and its figures now**:
   - `daily_range`: how much it normally moves in a day, the average of its last 14 days' high-to-low
     range, from the daily prices `fetch_quote` already receives (CFX about 6.3%, Bitcoin 2.4%, a
     large share about 1.9%). `typical_move` scales that to the gap between check-ins by the square
     root of time (CFX: about 0.9% in 30 minutes).
   - Protection starts once it has risen 1.5 typical moves (`STOP_ARM`): beyond its normal wobble.
   - From then on it may slip a number of typical moves from its best before it is sold
     (`stop_room`): 2.5 as a rule (`STOP_ROOM`, scaled by the level's `trail`, which its own trials
     may change); +0.5 while its screener score and rank are as strong as when it was bought;
     −0.75 when they have weakened (score under 70% of then, or rank far lower); −0.5 when RSI is 80
     or more; −0.5 in the last quarter of its holding time; −1 when the AI review answered
     "tighten". Never under 1 or over 3.5, and it is always sold while a fifth of the best gain is
     left (`STOP_KEEP`). Example: CFX up 6.15% at its best with strong figures is sold if it slips to
     about +3.4%; with weakened figures at about +4.6%; a calm coin at about +5.3%.
   - **The owner chooses the kind** (`trailMode`, added after he asked "should this have a trailing
     stop loss?": it had one, but only for gains, and nothing on the panel showed it). `gains` is
     the above. `full` puts the stop under the price from the moment of buying
     (`best − room × typical move`, with the best starting at the buying price), so a holding that
     only falls is sold after that many typical moves instead of waiting for the loss limit; such a
     sale is exit kind `cut` ("sold by its trailing stop before it had risen"), so the record shows
     whether it saves more than normal dips cost. `off` sets no following stop. `stop_words` puts
     the chosen kind into the plan of a buy and the story of a sale.
   - **Wording rule (11 Oct): the point where the stop starts must never read like a selling
     price.** The first wording ("sooner at -10% or +18%; once it has been up 4.5%, sell if it
     slips back far enough…") was read by the owner as "it sells at +4.6%, so how would it get to
     +18%?". Every place now says the same three things in this order: rising is not a reason to
     sell (while it rises it is kept); once it has been up that much a stop starts following it;
     it is sold only if it then falls back. Places: the plan under a buy, the story under a sale,
     `planLine` on the portfolio, "Holding now", and the line under the Trailing stop menu
     (`TRAILS`). Keep them in step.
   - The reasons are kept and shown under the sale ("The stop that followed it: …") and the stop as
     last worked out is stored with the holding (`state.open[id].stop`) for the dashboard.
   - Without daily prices for a holding the simpler rule by holding time still applies (`gain_arm`,
     `gain_floor`: protection from half the gain mark at 20 days down to 1% at 6 hours; a small gain
     may give back half, one near the mark a quarter). The tuner's hindsight estimate for `trail`
     still uses that simpler rule.
4. **The AI model's review** (`ai_review`, if `aiSell` is on and not paused; **off for everyone since 17 Oct 2026**, `AI_SELL`): for each holding the
   rules are keeping it is given what it was bought on, the screener's figures now, how it has
   moved, **its path since buying**, what is protected, when the rules will sell it, and up to three
   recent headlines that name it. It is asked whether a rise is still building or has stalled or
   turned, weighed against the time left, and told how much the holding normally moves between
   check-ins (so a dip smaller than that is not taken for a turn). It answers **hold, tighten or
   sell** with a reason; "tighten" keeps the holding with a closer stop (`tight`). **A larger model
   (`STRONG_MODEL`, gpt-4o) does this review when a gain is at stake** (some holding is up enough
   for its gain to be protected), at most 8 times a day per user (`STRONG_PER_DAY`, `state.strong`;
   about 0.3 US cents a call, so under $1 a month; the owner's limit). Otherwise gpt-4o-mini. If the
   larger model cannot be reached the usual one answers. **It can only sell earlier than the rules, never keep past one.**
   A "keep" is stored with the holding (`view`) and shown on the panel.
5. The sales are made; each gets a log entry with its story (`sale_detail`).
6. What may be spent (`allowance`): **what was invested already when the build-up began is left out of the pacing**
   (`already_in`: its holdings bought before `startedAt` and still held; 12 Oct 2026). The build-up begins again whenever
   the budget or "Build up to it over" is changed, and it used to count the whole budget from nothing each time: with
   most of the budget invested, nothing could be bought until the release had passed all of it again. That froze the
   owner's buying three times on 12 Oct (emptying the build-up box: three days; setting it to 1 day: half a day; the
   budget saved $29 lower: until the next afternoon). Now `released(settings, state, now, base)` releases the rest in the
   same steps, so the next check-in can buy at once; an older holding that is sold has its money paced out with the
   rest. From nothing it is exactly as before (the panel's `buildUp()` describes that case and is unchanged).
   The rest of the budget is released in equal steps per check-in over
   `periodDays`, rounded up to whole holdings, never more than the budget or the practice cash; at
   most 3 buys a check-in; buys are in whole cents and the last one takes exactly what is left.
   **"Check in now" is a request to act**: when only the pace of the build-up stands in the way, a
   check-in asked for by hand releases the next part of the budget early (`state.ahead`, counted
   into the steps; reset when the build-up restarts) and notes it. The schedule then carries on
   from there, no faster. Added 10 Oct after the owner pressed the button expecting a buy and got
   none. The answer to `run` also carries `summary.why`, the reason when nothing was traded.
   It releases as many steps as one more holding takes (with hourly steps and 4 large holdings
   that is several; until 11 Oct it gave up after as many steps as the level has holdings).
   If the early release buys nothing after all (nothing fit to buy, its market closed), it is taken
   back, so pressing the button again and again cannot use up the build-up. Nor can it overshoot:
   each press releases one more step at most, never past the budget, the practice cash, the
   level's number of holdings or the coin share.
7. The shortlist (`shortlist`): the top of each chosen screener with a positive score and signal,
   not already held, not sold within two days (or twice the holding time if shorter), inside the
   level's RSI and 30-day-move limits; ordered by place in its own screener.
   **A coin must have stayed there** (`note_stays`, `STAY_CHECKS` = 2): when it checks in every
   3 hours or less, a coin is only bought once it has been on the shortlist at two check-ins
   running, so the first coin buy comes at the second check-in (note key `stay`). Reason, from the
   live data of 10 Oct: the site's own top-10 history showed 8 of 26 coins gone again after one
   30-minute check, and the owner's first coin went from rank 1 to rank 149 in four hours. Shares
   are never held back, and nor are coins when it checks in less often (a day is too long to wait).
   Each buy remembers how long it had stayed (`stay`), the model is told, and the record is split
   by it ("By how long it had stayed near the top when bought").
8. The AI model chooses among the first 12 (`choose`), each shown with recent headlines
   (`candidate_news`), and gives a reason naming the figures. **The code enforces every limit**: it
   can only pick from the shortlist; if it fails the top of the shortlist is bought and the log says
   "chosen by rank". A buy is recorded at the live price, and skipped if that is not within
   0.8–1.25 times the screener's price. `remember_buy` keeps the figures it was bought on.
9. If nothing was traded, one note says why (`key`): `pace` (waiting for the next step of the
   budget, with when), `full`, `cash`, `share` (the markets that are open already hold their share of the budget; it was `coins`), `shut` (by hand: "Nothing
   to do: none of its markets is open."), `none`, `nodata`, `same`.
   The same note at the next check-in is counted on that line, not added again (`add_log`).
10. The portfolio is saved with a version check. If the owner changed it at the same moment,
    nothing is traded and it tries again next time.
11. `settle` again, then `review_resting`, `write_lessons`, `review_tuning`.

### Headlines

`fetch_news` (holdings) and `candidate_news` (the shortlist): Google News RSS search for coins,
Yahoo Finance RSS by symbol for shares (a share's company name comes from its quote).
`pick_headlines` keeps at most three, under 72 hours old, that **name the holding** (its code or
the first real word of its name) and drops price, forecast and converter pages (`NEWS_JUNK`; the
first real headline to reach the model, at 15:10 UTC on 10 Oct, was a "price forecast" page).
**A coin's headline must be about the coin.** A coin's ticker is often also a company or a word:
on 10 Oct the model was shown share news about ERG S.p.A. (an Italian energy company, "ERG
(BIT:ERG) Stock Could Be Trading At A Premium…") as headlines for the Ergo coin. For a coin a
headline now counts only if it names the coin by its own name ("Ergo"; taken from its quote, also
for candidates), or by its ticker beside a crypto word (`COIN_WORDS`), or the ticker has five
letters or more; and never if it reads like share news (`SHARE_NEWS`: an exchange code in
brackets, "stock", "shares", "dividend", "earnings"). Share headlines are not touched by this. Kept two hours
(`state.news`, `state.seen`). **Whether headlines help is not known, so it is measured** (12 Oct 2026, the owner asked
"does it also review the news?"): a remembered buy carries `heads` (how many headlines the model was shown for it) and
`headAge` (hours, the newest); both go with the finished trade into the shared record (`POOL_FIELDS`), and
`autopilot_review.py` splits results by them (none found / newest under a day old / one to three days old). Of the
first 10 buys, 3 had any headline; none of the three share buys outside the US did (Yahoo's feed is asked with a US
region). What the model gets is headlines only, never an article's text, and it has no internet of its own. One that
slipped through the junk filter: "Why is Walrus price up 13.5% today?" (a price page). `NEWS_JUNK` takes "price up" / "price is down" since 10:29 UTC that day. Headlines are untrusted text: both prompts say so, and the model's
answer can only pick from a list or say hold / sell. Small coins usually have none; then it is the
figures alone. Only the deployed function fetches (`AWS_LAMBDA_FUNCTION_NAME`); a test run never
calls out.

### Learning from its own results

**Since 11 Oct 2026 these reviews run once, on every account's finished trades together** (next part, "Learning is shared
by every account"); an account's own check-in no longer runs them. What each review does is described here and is the
same code; read "its record" below as the shared record, or the shared record at the account's risk level.

- **The record.** Each finished trade goes into `history` (last 300): what it was bought on (rank,
  score, RSI, 7- and 30-day change, volume, who chose), result in percent and dollars, the S&P 500
  fund over the same time (`market`, `vs`), how long it was held, how it was sold (`exit`: `stop`,
  `take`, `trail`, `cut`, `time`, `signal`, `fade`, `ai`, `hand`), its best and worst while held, and,
  filled in later by `look_back`, **what it did after it was sold** (`after`: the further change
  once the same length of time had passed again).
- **Scorecard** (`scorecard`): overall and by screener, rank band, RSI band, who chose, exit, how long it had stayed, and, for shares, **how far above its 52-week low it was when bought** (`above` on the remembered buy, from the screener row's `from_low`; added 11 Oct after the factor study of section 7b, as a measurement and not a rule).
  Shown as "How it is doing" and given to the model at each decision (`memory_text`).
- **Resting a screener** (`review_resting`): when its last 12 trades (at least 8) average 1.5% or
  more behind the S&P 500 fund, it is rested 14 days, then tried again with a clean slate. **A coin
  screener is judged on its own results** (an average loss of 1.5% or more), not against the fund:
  the share market says nothing about a coin and is shut at weekends.
- **After costs.** A trading cost is taken off every buy and sale (above). A finished trade made that way carries `c`; the
  month's figures (`month_figures`, `afterCosts`) and the bar charge the same 0.1% each way (`COST_EACH_WAY`) only to
  trades without it, and the panel says when a figure includes such older trades.
- **The bar its record has to clear** (`bar_of`, `BAR_TRADES` 300; sent as `bar`: `need, n, avg, margin, met, shared`; on the
  panel as an amber-edged box at the top of "How it is doing", `barHtml`). Set down on 11 Oct 2026, before the results are
  in, so that a lucky run cannot be talked into a success: **300 finished trades whose average result, after trading
  costs, is ahead of the yardstick by more than twice the margin of error; the yardstick is an S&P 500 index fund over
  the same days for a share and zero for a coin.** It is measured on the shared record (every account). At the sweep: 4
  of 300, averaging -0.68 against the yardstick. Until it is cleared no result here is evidence of anything, and it must
  be cleared before real money is even discussed (and then discussed with a licensed adviser: section 11, "Legal").
  **The owner's own bar for real money is higher (18 Oct 2026): the account clearly ahead of an S&P 500 fund for more than a
  year, by at least 5% a year** ("it would have to beat it by atleast 5% as s&p also has dividends"; he thinks it unlikely,
  and says so). Clearing the 300-trade bar is only the start of that year. **Dividends:** the fund's line and the yardstick
  count price only (section 8c, "What the owner sees", the graph); an S&P 500 fund also pays about 1.2 to 1.5% a year, so a
  lead of under about that much is no lead at all. The practice holdings get no dividends either, but momentum shares
  usually pay less than the index, so price against price flatters the account a little. Say this whenever the account is
  said to be "ahead of the fund".
- **Notes** (`write_lessons`): after every 5 more finished trades the model writes up to four short
  notes on what the record shows, **but never from fewer than 30 finished trades** (`LESSONS_MIN`, 12 Oct 2026): notes that
  rest on fewer are dropped, and are shown neither to the model (`memory_text`, which now says how many trades a note rests
  on) nor on the page. After five coin trades it had written "trades with RSI around 50 did not perform well overall" and
  was being shown that at every choice.
- **Pausing the AI model's early sells** (`review_ai_sells`): when the last 8–12 holdings it sold
  early went on to rise 0.5% or more on average, its early sells are paused 14 days.
- **Trials of its own rules** (`review_tuning`, if `selfTune` is on). It may change only what is in
  `TUNABLE`, inside hard bounds: loss limit (−1.5 … −30), gain mark (2 … 80), share of a gain given
  back (0.2 … 0.8), how far down a ranking it buys (3 … 30), highest RSI it buys at (45 … none).
  Every 20 finished trades `propose` looks over up to 60 for the one change that would have helped
  most **in hindsight** (at least 0.2 points a trade): a nearer gain mark or loss limit from each
  trade's best and worst; a further one when holdings went on rising after such a sale; nearer or
  further down the ranking and a lower or higher RSI limit from how those groups of buys did.
  It does **not** adopt it. It runs a **trial beside the current rule over the same days**: for a
  selling rule every second buy follows the changed rule (`x`, `v` on the remembered buy,
  `own_rules`); for a buying rule it buys by the wider of the two and compares the groups. After
  10 finished trades each way it keeps the change only if that group's average beat the other by
  more than one standard error (`trial_figures`); otherwise the rule stays. A change dropped lately
  is not retried for three trials; a trial ends unchanged after 30 days, when the level changes,
  when the owner sets that rule himself, or when he stops it.
- **Progress, a batch at a time, and what it does when a batch is no better** (11 Oct; the owner:
  "if its doing well it continues improving as it is, if its doing worse or the same it needs
  investigating and fixing, ideally i'd prefer AI actively do this").
  - `batches(record)`: the finished trades in batches of `TUNE_BATCH` (20), numbered from the first
    trade ever (`closedCount` keeps counting when old trades drop off the 300 remembered; a batch
    cut off that way is left out). Per batch: `no, first, last, n, full, from, to, up, avg, usd,
    se`, and for a complete batch after the first `prev, diff, margin, verdict`: **better / worse /
    same, where "same" means the difference is inside the margin of error of the two averages**.
  - `review_progress(record, now, model, mail)` runs in `run_user` just before `review_tuning`,
    once per completed batch (`state.progress.done`). It writes a report (`state.progress.reports`,
    last 15: `no, at, trades, avg, usd, up, n, verdict, prev, findings, actions`), a line in the
    activity list ("Progress after 40 finished trades: …") and an email.
  - **Better (or a first batch that is up): "It carries on as it is."** The ordinary review of
    its rules (`review_tuning`) still runs on its own count.
  - **Worse, the same, or a first batch that is not up:** (1) `batch_findings` says what stands out
    in the batch's own figures (the kinds of sale and the screeners that did worst and best, what
    holdings did after they were sold); (2) if the verdict is "worse" and a change of its own was
    kept before this batch began, **that change is put back** (`undone` on the past trial);
    (3) unless a trial is already running, it starts **a trial of the most promising change to one
    of its five rules, with a lower bar than usual** (`propose(..., least=0.05)` instead of
    `TUNE_MIN_GAIN` 0.2), and **the AI model picks which** from up to four numbered candidates (it
    cannot invent one; an answer off the list is ignored and the first candidate is used);
    (4) `tune.mark` is set, so the ordinary review does not start a second change. With "Try
    changes to its own rules" off it reports and changes nothing. The trial still decides whether
    a change is kept, so nothing is adopted on hindsight.
  - What it cannot do stays the same: only the five rules in `TUNABLE`, inside their bounds. When
    nothing in them stands out it says so and points at the settings only the owner can change.
  - The panel's table is `progressHtml` (`data.progress`: `batch, batches, reports`).
- **Its own trial of which share to buy** (11 Oct, after the owner said the study had produced no
  improvement "to increase profit": he was right, it had only been measured). The factor study
  (section 7b) found no link between a screener's ranking and what shares did next, and a modest one
  for how far a share stands above its 52-week low. So the autopilot tests that itself:
  - `order_of(state, settings, now)`: `state.order` = `{mode, since, buys, ended, result, kept,
    undone}`; mode `trial` (running), `low52` (kept), `rank` (not kept, stopped, or put back). **It
    starts by itself at the first share buy** when "Try changes to its own rules" is on; never
    with that off.
  - `apply_order(order, picks, candidates)` runs straight after `choose`: on trial, **every second
    share pick is swapped for the share furthest above its 52-week low** (`from_low`) among the
    candidates of the same market (so the market shares still hold); once kept, every share pick
    is. Each share buy is tagged (`o`: `low52` or `rank` on the remembered buy; `chosen: 'order'`
    for a swapped one, shown in the record as "bought furthest above its 52-week low"). Coins are
    never touched: they have no such figure.
  - `review_order` judges it at check-ins: after `TUNE_GROUP` (10) finished each way, the new order
    is kept only if its average beat the other by more than the margin of error; otherwise shares
    go on being bought as ranked. It gives up unchanged after `ORDER_GIVE_UP_DAYS` (90), and ends
    when its trials are switched off. A note and an email either way.
  - The owner can stop it or put a kept order back: `tune` action with `op: 'stoporder'` /
    `'restoreorder'`. The page gets `order` (`mode, since, ended, result, kept, undone, group, why,
    with, without, avgWith, avgWithout`).
  - On the panel under "Improving its own rules": **"Improvements so far: N being tried now, N kept
    after a trial, N put back, N tried in all"** (`improvedLine`), and the trial itself
    (`orderHtml`: "Next, for shares…" before it has started, "Also trying, for shares…" with the
    two sides' figures and "Stop this trial", then kept with "put it back", or not kept).
  - Honest limits: ten trades a side is little; the study's edge was modest, from one rising
    market and today's index members. That is why it is a trial and not a rule.
- **Emails** (`send_mail`, if `emails` is on): one at each review (no change / trial started /
  trial finished) with the record so far and suggestions about settings only the owner can change.
  `aws lambda invoke --function-name stockiq-ai-trader --payload '{"mail_test": true}' …` sends one
  test email to every account that has the autopilot on.

**Deliberately not built, although the owner asked for it:** letting it "modify anything on my
site". It changes five numbers of its own, for fake-money trades, and nothing else: no code, no
page, no setting of the owner's, no budget. An unattended program rewriting live code cannot check
its own work. Bigger changes come through a session like this one, informed by its emails.
**And say this plainly whenever results come up:** the backtests (sections 7b and 11) found no
reliable edge in the screener scores, tuning on a few dozen trades is mostly noise, and a goal
like "70% a month" is not something this or anything else delivers. The trial design exists so
that it at least does not fool itself. The owner's later aim, "70% profit, 30% loss", needs the
same care: section 7b shows that share of winning trades comes from the selling rule (any stock
"wins" 74% of the time under a sell-at-+2% rule) and is not profit. Judge it by dollars and by
the average per trade, which the panel shows, never by the share of trades that ended up.

### Learning is shared by every account (11 Oct 2026, the last change of the session)

The owner: "it should be learning regardless of the user that runs something. so the more users… the smarter it gets. I
think the way you have done it is its going from scratch on each new user… It should be a smart AI that is learning in a
central location for all users". He was right about how it was built: every account kept its own record, trials and notes.
Now there is **one shared record**, and what follows replaces the per-account learning described under "Learning from its
own results" (those routines are the same; they now run once, on everyone's trades).

- **Where:** item `_brain` in table `stockiq-ai-trader` (one compressed attribute `z`; `load_brain`, `save_brain`,
  `new_brain`): `pool` (finished trades of every account, newest last, at most `POOL_KEEP` 3,000), `count` (all ever
  taken in), `counts` per risk level, `accounts` (8-character scrambled ids, only to count them), `state` (`rest`,
  `restSince`, `lessons`, `order`), `tunes` and `progress` per risk level (the same shapes an account's `state.tune` and
  `state.progress` had), `news` (the last 30 notes, numbered by `seq`). Switch: `CENTRAL = True` in the function.
- **What goes in, and privacy:** when an account's record is saved (`save_item` → `share_trades`), its finished trades that
  have not been sent yet are queued as one small item `_pool#<time>#<id>#<random>`: the figures it was bought on, the
  result, how it was sold, the level (`POOL_FIELDS`). **No address and no holding id**; a scrambled key (`k`) only stops
  a trade being counted twice. Sent rows are marked on the account's own history (`p`: 1 sent, 2 sent with what it did
  after it was sold; that later figure is sent on as `{k, after}`). The codes of the shares and coins are in it; nothing
  about who traded them.
- **The scheduled run, before the check-ins** (single writer, so accounts running side by side never write it):
  `gather` folds the queue into the pool and deletes the queue items once the record is saved; `think` reviews once for
  everyone: `review_resting` (a screener whose pooled trades lag is rested for every account), `write_lessons` (notes
  from every account's trades, every 5 more), `order_of` / `review_order` (the trial of which share to buy, over every
  account's share buys), and per risk level, through `mind_of(brain, level)` (the shared record seen as one account at
  that level), `review_progress` and `review_tuning`. Notes it produces go to `news` (`tell_all`), prefixed "Learned from
  every account…". If any of this fails the log says "shared learning failed" and the accounts work from the record as
  last saved.
- **What an account takes over** (`adopt`, at the start of every check-in and when the page is drawn): the rules changed
  after a trial and the running trial for its level, the trial of the buying order, the rested screeners and the notes.
  Which of its own buys follow a rule on trial is still counted per account (`buys`). New notes go into its activity list
  and one email ("what it has learned from every account"); an account that is new gets no backlog. **With "Try changes
  to its own rules" off, an account keeps the level's plain rules and takes no part in trials** (rests and notes still
  apply). In a check-in the per-account reviews no longer run (`solo` is false).
- **The AI model is shown both** when it chooses what to buy: this account's own finished trades, and every account's
  together (a summary of the latest `POOL_CARD` 600) with the shared notes.
- **Who can undo what is shared:** "put it back" and "Stop this trial" act on the shared record, for everyone, and only
  for the site's own accounts (`listed`, env `AI_TRADER_USERS`); any other account is answered HTTP 403 and pointed to
  its own switch, and the panel does not show those links to it (`central.canChange`).
- **What the page gets:** `central` = `{trades, accounts, level, on, canChange}`; `progress` and the figures of a trial
  are those of every account at the user's level (`progress.shared`); "How it is doing" stays the account's own record.
  The panel says so in a framed box at the top of "Improving its own rules" (`sharedHtml`). The chat's summary has a line.
- **Fixed on the way:** the schedule's table scan took only the first megabyte (the stored screener results are large, so
  with more accounts some would have been skipped without a word): it now pages through the table. Notes are refreshed by
  the count of trades ever finished, not by the length of a list that stops growing.
- **Does it need another AWS service or "machine learning"? No, and not yet** (the owner asked). What limits it is the
  number of finished trades and how little the screener figures have predicted so far (section 7b), not the tools: a
  statistical model fitted to a few dozen trades learns noise. The shared record is what any such model would be trained
  on, and it is being collected from now. When it holds some thousands of trades, the next step is a small model (a
  logistic regression or boosted trees on the bought-on figures, fitted inside this same function or a second small
  one, no SageMaker needed) that scores a candidate, tried the same way as every other change: beside the current rule,
  kept only if clearly better. The OpenAI model stays what it is: it weighs the figures and headlines of one decision; it
  does not learn from the record except through the summary and notes it is shown.
- **More that it could change** (the owner: "the more changes it can make the better"): still the five rules of `TUNABLE`
  and the buying order. Candidates once the pool has the trades to judge them: the automatic pace of each level (holding
  time, check-in gap), the stop's distances (`STOP_ARM`, `STOP_ROOM`), the wait for a coin to stay, per-screener ranking
  depth. Each needs a tag on the buy and a trial; none should be adopted from hindsight.
- **Limits, said plainly:** on 11 Oct there was one paying account with four finished trades, so today the shared record
  is that one account; the gain comes with accounts. Accounts at different risk levels pool separately for the rule
  trials (a level's rules differ), together for rests, notes and the buying order. A site account's "put it back" and the
  schedule could write the record in the same second (not guarded; the schedule runs at :10 and :40). The deploy's own
  check created a record for the deploy test account (switched off; harmless).
- **Tests:** the last part of `ai_trader_test.py` (17 checks) runs with `CENTRAL` on; the rest set it off at the top so
  that each review is tested on one record. `dashboard_page.py`'s stand-in says learning is shared.
- **Seen for real (09:10 UTC, 11 Oct):** the scheduled run logged "shared learning: 4 new finished trades, 4 in all from 1
  accounts, 0 notes": the owner's four trades are in the shared record and the queue is empty again.
  **Not yet seen for real:** a shared note reaching an activity list (the first comes with the first review, at 20
  finished trades at a level, or the first notes at 5 more trades), and the bell on the logged-in pages.
- The AI chat knows: its `DASHBOARD_GUIDE` says that learning is shared, and the page's summary gives it the numbers.
- Rollback zip: `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_central_20261011.zip`. The older function ignores
  `_brain` and `_pool#` items, as it does the stored screener results.

### The AI chat on the dashboard (added 11 Oct 2026)

The owner noticed the chat was on every page but the dashboard, and wanted it to "know everything"
there. Setting things up for the user by chat was judged too much for now and is not built.
- `dashboard.html` loads `ai-chat.js?v=2` (the other pages still load it without a version).
- **What the chat is told on the dashboard** (Lambda `stockiq-ai-chat`, `page: 'dashboard'`):
  `DASHBOARD_GUIDE`, a fixed description of the three tabs, every autopilot setting and every part
  of its Activity view; and **a summary of what this user's own dashboard shows**, built in the
  browser: `practicePortfolio.summary()` (account value, the user's holdings, the autopilot's
  holdings) and `practiceAutopilot.summary()` (on or off, level, budget, pace, screeners and the
  spread over markets, switches, next check-in, what is coming, "Needs you", holdings, results,
  trials, the last three entries), sent as `pageContext.dashboard`, cut to 2,500 characters and
  stripped of control characters. It is marked in the prompt as data from the user's browser,
  never instructions. Away from the dashboard the chat only knows that the practice portfolio is
  free and the AI autopilot (Beta) is in the paid plans.
- **Rules added to the prompt** (the no-advice rule stands): it cannot change anything for the
  user; it never says which settings, screeners or holdings will make money; it keeps to what the
  figures say and adds no steps, amounts or times; no "opportunities", "picks" or "recommend";
  results are "practice results with fake money". Replies on the dashboard may be a little longer
  (400 tokens instead of 300).
- **The risk-level numbers in `DASHBOARD_GUIDE` are a copy of `RISK` in `stockiq-ai-trader`**
  (holdings, loss limit, gain mark per level): `check-tools/ai_chat_test.py` compares them. They
  were added after the model told a test question that Cautious means "fewer" holdings.
- Test: `python3 check-tools/ai_chat_test.py lambda-sync/stockiq-ai-chat/lambda_function.py` (19
  checks; stand-ins for the database and the AI model). The guide was brought up to date in the evening sweep of 11 Oct
  (results as arrows, the bell's one list, a release of the budget listed at its check-in, learning shared by every
  account). Tried live with real questions on 11 Oct:
  it answered from the figures, pointed to the right controls, and declined "which settings will
  make the most money" and "should I switch to Cautious". It is still a small model: read a few
  answers after any change to the guide.
- When a dashboard feature changes, **update `DASHBOARD_GUIDE` and the two `summary()` functions**,
  or the chat will describe the old dashboard.
- Cost: about 1,600 tokens a dashboard question instead of 650 elsewhere, roughly $0.0003 each.
- Rollback zips: `~/VSCODE/backup/stockiq-ai-chat_before_dashboard_20261011.zip`, `…_wording_…`, `…_levels_…`, `…_before_sweep_…`, and 12 Oct `…_before_guide_20261012.zip`, `…_guide2_…`.
- **12 Oct 2026:** the guide was brought up to date (graph, buttons beside the heading, the split of both parties' results, Number of holdings, the 3-hour price rule); the numbers it quotes for those are compared with the autopilot's own by the test (19 checks). A number of holdings set by the user is said outright in the panel's `summary()`: the guide alone did not stop the model answering with the level's number.

### What the Lambda keeps per user, and what it sends the page

- Marks of the diary (12 Oct 2026): `j` on a line of `log` and on a trade in `history` (written to the diary; 2 on a trade once its `after` went too), `state.diary` (a fingerprint of the settings last written). They travel to the page with the rest and mean nothing there.
- The record: `settings`; `log` (last 80: `t, type` buy / sell / note, `symbol, usd, text`, and
  where relevant `kind, pct, detail[], key, n, first`); `history`; `state` with `startedAt`
  (when the budget's build-up began; reset when it is switched on or the budget or build-up
  changes), `lastRun`, `lastRunBy`, `open` (remembered buys), `exits`, `rest`, `restSince`,
  `lessons`, `tune` (`values`, `trial`, `past`, `mark`, `seq`, `reviewed`), `watch`, `news`, `seen`, `stay`,
  `strong`, `ahead`, `aiSell`, `closedCount`, `realizedUsd`, `progress` (`done`: batches reported, `reports`), `order` (the trial of which share to buy), `visit`, `pausedAt`, `pausedWhy`, `ai` (today's AI calls), `mail` (what became of the last email:
  `t, ok, subject, why`), `fail` (a scheduled check-in that stopped on an error; cleared by the next
  good one), `savedAt` (when the settings last changed).
- `public()` (every action returns it): `settings, state, log, scorecard, lessons, resting, recent,
  minSample, practiceCash, rules` (in force, with `yours`, `level`, `changed`, `arm`), `tune`
  (`trial` with its figures, `past`, `nextReviewIn`, `batch`, `group`), `aiSellPausedUntil`,
  `coinShare, realizedUsd, month` (`last30`, `before30`), `now, nextCheck, holding, plans` (per
  holding: `sellBy` (the end of its holding time, moved on to its market's next opening), `market,
  closed, opens, stop, take, arm, floor, move, room, tight, mode, trail, peak, trial, view, auto`) and `options` (screeners,
  check-in and holding-time choices, the level table, `groups`); `split` (per ticked market: `group, holdings, pct, usd, own`); `money`; `progress` (`batch, batches, reports`); `order`; and `coming`, `needs`, `mail`, `reviewed` (next section). **The panel is drawn from these; change the
  two together.**
- Other actions: `mailtest` (one test email to the account's own address, at most every 10 minutes), `sellall` (`sell_everything`: only the autopilot's holdings, recorded as sold by
  the owner; holdings of a closed market are kept; its `summary` has `sold`, `skipped`, `closed`) and `tune` (`tune_by_hand`: `op: 'restore', param` puts one rule back to the level's;
  `op: 'stop'` ends the running trial; `op: 'stoporder'` / `'restoreorder'` stop the trial of the buying order or put a kept order back; nothing else can be touched).

- **Added with the shared learning and the bell (11 Oct, evening):** a finished trade in `history` carries `p` once it has
  been sent to the shared record (1 sent, 2 sent with what it did afterwards); `state.brainSeen` is the number of the last
  shared note the account has had; what `adopt` takes over sits in `state.tune`, `state.order`, `state.rest`,
  `state.restSince` and `state.lessons` as before, but is now a copy of the shared record's. A buy or sell entry in `log`
  carries `name`, and a sell its `gain` in dollars. `public()` adds `central` (`trades, accounts, level, on, canChange`)
  and `progress.shared`. Action `bell` answers the notification bell (read-only).

### What happens next, and what needs the owner (added 11 Oct 2026)

The owner asked for "some kind of countdown timer to know when next action is going to occur… and
what future actions are going to take place", and "something on the site to tell me whats going on
so i'm aware of everything thats going on in the background or needing my assistance". He also was
not sure whether its improvements needed him to "push" them. They do not, and the panel now says so.

- **`coming(record, portfolio, now, plans)`** (sent as `coming`): a list of `{kind, text}` with
  either `at` (a time) or `after` (a number of finished trades), soonest first, timed ones before
  counted ones. Kinds: `check` (the next scheduled check-in: which market, which holdings it looks
  at, and what it may buy, worked out with the same `allowance` the check-in will use, including
  the coin share, a full budget and too little cash), `open` (the first check-in after each other
  market it has opens), `release` (the next step of the budget's build-up, with amounts:
  `released()`, which `allowance` now also uses; **listed at the check-in that can first spend it, not at the minute of
  the release**: the steps are counted from when the build-up began, so a release fell at 15:55 with the check-in at
  16:10, and the owner read "more is released in 1 h 38 min" above "next check-in in 1 h 53 min" as two different next
  actions and thought the countdown wrong), `sell` (the latest each holding is kept), `rest`
  (a rested screener or the AI model's paused early sells coming back), `trial` (the latest a
  running trial ends), `review` (trades to go until it reviews its own rules; or that this is
  switched off), `notes` (trades to go until the AI model writes fresh notes). **It is a forecast
  from the settings and the state: the check-in itself decides from the prices of the moment**, and
  the panel says so. Empty when switched off.
- **`needs(record, portfolio, now)`** (sent as `needs`): what only the owner can put right. Kinds:
  `off` (switched off while holding something), `noscreener`, `resting` (every ticked screener
  rested), `cash` (less practice cash than one holding), `budget` (the budget is more than the
  practice money there is: on 11 Oct the owner had set $200,000 against $100,000 of fake money),
  `fail` (the last scheduled check-in stopped on an error: the schedule's `except` now leaves
  `state.fail`), `missed` (`missed_check`: two scheduled slots in a row were due and did not
  happen, both since the settings last changed, `state.savedAt`; one miss is forgiven), `mail` (the
  mail service refused the last email). An empty list shows as "Nothing needs you right now".
  **Its reviews, trials and rule changes are never in this list: they happen by themselves.**
- **Email status.** `send_mail` answers True (the mail service accepted it), False (refused; the
  reason is kept in `MAIL_ERROR`) or None (not running as the function, nothing attempted);
  `note_mail` keeps the outcome in `state.mail`; `test_mail` is the one test email (the `mailtest`
  action from the panel, or `{"mail_test": true}` by hand). **"Accepted" is not "arrived"**: the
  panel says to look in junk. Checked 11 Oct: SES healthy and sending (still in sandbox, so only
  verified addresses), domain `stockiq.tech` verified with DKIM and its own MAIL FROM
  (`mail.stockiq.tech`), the owner's address verified, no bounces, complaints or suppressed
  addresses, and a test accepted at 03:00 UTC. Whether it reached his inbox only he can say.
- **The panel** (`practice-autopilot.js`): `leftText` words the time left ("in 1 h 48 min", "in 12
  min 05 s", "any moment now"); `tick` runs every second and only rewrites the text of elements
  carrying `data-ap-until`, so nothing is redrawn and typing is not disturbed; `skew` is the
  server's clock minus the browser's (from `now` in each answer), so a wrong computer clock does not
  spoil a countdown. `countLine`, `needsHtml`, `comingHtml` (four rows shown, the rest folded),
  `mailHtml`. `markTab` puts a ⚠ on the dashboard's own "AI autopilot" tab button while `needs` is
  not empty, so it is seen from the Reports or Practice portfolio tab too. An answer from an older function (none of these fields) shows as before.
- The review email's own description of the rules was the last place with the wording the owner had
  misread as a selling price; it now follows the wording rule above.
- Not done: the same kind of box for the rest of the site (the daily deploy runs on the owner's Mac
  and leaves nothing a web page can read); a summary email.

### How the panel script behaves (`practice-autopilot.js`)

- **Every change saves itself**: the switch at once, ticks and menus after 0.15 s, typing and the
  slider after 0.9 s, anything still waiting when the page is left. `accepted` stops a value the
  server tidied (20000.4 → 20000) being saved over and over. While something is being typed the
  panel is updated in place (`syncDraft`), not redrawn, so the cursor stays put.
- **It keeps itself up to date** (`refresh`, every minute while the page is visible, not while
  something is being typed or saved) and reloads the practice portfolio when the autopilot traded.
- The two description lines (`planText`, `paceText`) are built from what is selected. The sums in
  `buildUp()` are **a copy of the Lambda's rules** (`allowance`, the time rule, 3 buys a check-in,
  the $25 smallest buy), and `marketSplit` / `marketSlots` a copy of how it spreads the budget over
  markets: change one, change the other, and run `autopilot_plan_check.py` (it checks both).
- `levelRules` gives the rules to describe: the level's (`options.risk`), what it changed itself
  (`rules.level`), then the owner's own limits as typed. `readDraft` turns an empty build-up box or
  "Automatic" in a menu into the level's own value (`paceOf`) and lists the field in `auto`; while
  the slider moves, `syncDraft` updates the greyed value, the "Automatic: …" menu entries and the
  descriptions. `auto` is only sent if the Lambda sent it. The shortcuts for the screeners (`MAIN`, `data-ap-pick`, `data-ap-group`) only
  tick and untick boxes and then save like any other change.
- "Buys and sells only" is a way of looking at the list, not a setting: it is remembered in the
  browser (`localStorage` key `stockiqAutopilotTradesOnly`) and nothing is sent to the Lambda. With
  it on, the latest check-in's own line is still shown above the trades when it is newer than the
  last trade, and after "Check in now" the message itself gives the reason if nothing was traded
  (the owner had the switch on, so the note that explained an empty check-in was hidden from him).
- Styles are one `<style id="ap-style">` block the script adds.

### On a phone (added 11 Oct 2026)

The owner asked how the dashboard presents on a phone. Measured at 390px wide it did not: the third
tab was half hidden (the bar had to be scrolled sideways), the holdings table was 740px wide inside
a 308px box with its first column squeezed to a few letters a line, the progress table 729px, and
the trailing-stop menu stuck out past the screen. What was done, all in CSS that only applies on a
narrow screen (nothing changes at desktop width):
- **Tabs** (`dashboard.html`, `@media (max-width: 560px)`): the three tabs share the width and their
  names wrap onto two lines.
- **Tables become cards** (640px and under). The holdings and sold tables carry class `pp-stack`
  (heading row `pp-head`, name cell `pp-name`, button cell `pp-act`) and the progress table
  `ap-stack` (`ap-stack-head`, `ap-stack-title`, `ap-stack-wide`). Each figure cell has a
  `data-label` ("Bought", "Price then", "Price now", "Value", "Change"; "When", "Ended up", …) that
  the phone rule prints before the figure, so a row reads as a card with one labelled line per
  figure and a full-width Sell button. **A new column in one of these tables needs its
  `data-label`**, or it shows on a phone as a bare figure. The cells carry inline styles, hence the
  `!important` in those rules. `practice-portfolio.js` had no stylesheet before: it now adds one
  small `<style id="pp-style">` block (`ensureStyle`).
- **The breakdown** (`.ap-bd`) keeps its columns: headings and section titles wrap, padding shrinks,
  the name column loses its 240px minimum.
- The buy row (dollars and quantity side by side, note and button full width), the trailing-stop
  menu, "Check in now" / "Sell everything" and the Activity / Settings switch take the full width.
- Every box and menu was already 16px text, so a phone does not zoom in when one is tapped.
- **How to check:** `dashboard_page.py` step `mobile` (or `mobile:practice`, `mobile:activity`,
  `mobile:settings` to leave that view up for a screenshot) lists what sticks out past the screen
  and what has to be scrolled sideways inside its own box. Headless Chrome will not make its window
  as narrow as a phone, so wrap the test page first: `python3 check-tools/mobile_frame.py
  <page.html> <frame.html> [width]` puts it in a frame of that width (default 390) and shows what
  the page printed underneath. Checked at 320, 360, 390 and 430px, light and dark, with the
  breakdown open, and the locked view: nothing sticks out, nothing scrolls sideways.
- **Checked again at 390px on 13 Oct 2026, after the day's changes** (the owner: "i'm wondering how this will all work on
  mobile"): the three figures stack full width, the line of facts and "The breakdown" wrap, the holdings are cards with
  "Today" and "Since bought" labelled and the plan folded; on the autopilot tab the tabs fit, the buttons take the width,
  and a "Holding now" row keeps "its plan ▸" on the right with the reason under the name. One flaw found and fixed: four
  date labels under the graph ran into each other (three below 420px now, `practice-portfolio.js?v=30`). Looked at: the
  Practice portfolio tab and the autopilot's Activity part; Settings was rendered but not looked at again. **To switch to
  the autopilot tab the test page needs `dashboard.html` as its sixth argument** (without it the `mobile:activity` step
  stops with "Cannot read properties of undefined (reading 'show')" and the picture is of the wrong tab).
- **Not checked:** a real phone, and the logged-in dashboard itself. The Reports tab (statistics,
  Report History) was not part of this: it is the older page and has its own rules for 768px and
  under, which were not re-measured because its content needs a login.
- With `sips`, a crop offset of 0 means "centred": use `--cropOffset 1 0` for the top of a tall
  screenshot, and crop at the image's full width.

### Smaller facts worth knowing

- **Changing which screeners are ticked while it holds something** (the owner asked what happens
  on switching from crypto to the S&P; tested, `ai_trader_test.py` near "switches from coins"):
  there are no separate jobs per screener. One check-in looks after everything it holds, whatever
  screener it came from. Holdings from an un-ticked screener keep all their rules (time limit,
  loss limit, gain mark, the following stop, the AI review; that screener is still read for them)
  until they are sold; new buys come only from what is ticked, from the part of the budget that is
  not invested; a market drops out of the check-ins once nothing from it is held. With coin and
  share screeners both ticked, the level's coin share applies (Balanced: a quarter of the budget).
- No screener is ticked for a new user, and it can be switched on with none: it then waits and
  says so. "Check in now" is greyed out, with the reason, while it is off or nothing is ticked.
- The holding time and the check-in gap are stored in days and hours as fractions (1 hour is
  0.041666… days); the panel reads both with `parseFloat` and sends them back exactly.
- A burst of saved changes leaves one "Autopilot on: …" line in the activity list, not one per
  keystroke (the last such line is replaced if it is under 15 minutes old).
- Stored screener results keep the top 150 rows in full and the rest as score, signal and rank
  only. A cold Russell 2000 run takes about 35 s, a four-screener check-in about 45 s, a crypto
  check-in about 16 s (the Lambda has 300 s).
- The sell rules measure a holding's change in US dollars, as the dashboard shows it; with no
  exchange rate a buy is skipped.
- The schedule scans the table for items with `enabled` true and runs each user who is due
  (`due_markets`); `next_check` works out the next slot for the status box.
- In the portfolio's search box, picking a suggestion shows the company name and latest price
  before anything is bought ("Checking exchanges...", "No matches found", like the home page).
- `panel_page.py` is the older browser page for the autopilot panel alone; `dashboard_page.py`
  (both sections together) is the one to use.

### The owner's Admin page (17 Oct 2026)

He asked for "an admin account… so i can see status", with items to action, adding "i'd rather not do anything manual
unless you need me to make a big decision. i'd prefer it all run without me". Built lean, as decided by the session:
- **Where:** a "🛠 Admin" tab on the dashboard and an "Admin" link at the top of the dashboard's Account menu, shown only
  when the autopilot's function answers action `admin` for the account (`listed`: the site's own accounts, env
  `AI_TRADER_USERS`; anyone else gets HTTP 403 and the page shows nothing). `website/admin-panel.js` (`?v=12`), the tab,
  panel and `NAMES` entry in `dashboard.html`. The link is on the dashboard only, not yet on the other pages.
- **What it shows:** the month's goal, each figure against its target (`goal_standing`; the same numbers as `GOALS` in
  `check-tools/autopilot_review.py`: change the two together); **"Decisions for you"** (it was "Needs your yes" until 17 Oct 2026): proposals with "Yes" / "Not now"; the
  **weekly review**, which the scheduled run writes by itself every 7 days (`write_review`, `ADMIN_REVIEW_DAYS`), or at once
  with "Write it now"; **how it is running** (`health`, written by every scheduled run: when, how many checked in, paused,
  waiting, stopped on an error); the settings in force; answered proposals. The review's button reads "Write a fresh one now" and says under it that it is never needed, buys, sells and
  changes nothing, may add a proposal, and moves the next automatic review to 7 days after the press (`admin-panel.js?v=2`,
  17 Oct 2026, after the owner asked what the point of it was).
  **Since 17 Oct 2026 it is drawn in colour** (`admin-panel.js?v=3`; the owner: "just looks like alot of black text and my eyes
  don't target anything"): four tiles at the top (Practice account, the month's goal as "N of 3 met", Decisions for you, Running),
  each green, amber or red by its state; each card has a coloured left edge (purple goal, amber when something needs his yes,
  green or red for how it is running); the goal's rows have a progress bar and a pill "target …"; the review's lines are
  marked red for "clearly down / clearly losing", green for "clearly up", and signed dollars and percentages coloured as they
  point (a zero, a target, is left plain); the settings are chips, the screeners folded. Colour tokens are on `#admin-panel`
  with pale backgrounds that read in both themes.
  **Two views since 17 Oct 2026, evening** (`admin-panel.js?v=7`; the owner: "maybe make it a tab within admin page for the
  improvements? or have a minimal part of it there then a tab for older stuff"): **Overview** (the tiles, Decisions for you, a
  short Improvements card: the counts, up to three being tested with the days left, the last three decided, and a button to
  the full list; then the goal, the review, how it is running, the settings) and **🧭 Improvements** (the whole card below,
  every decided item, not folded; each item that users also see is tagged "👥 users see it"). The view is remembered in the
  browser (`stockiqAdminView`). Tests: `admin_panel_test.js` (14).
  **The Improvements card** (since 17 Oct 2026, the owner: "put the list of future improvements to track them so i know which was
  run which is next ... easily see if something was improved in the past"): being tested now (each with a bar to its decision
  day and how it is measured), next in order, and done (✓ kept / ✗ taken out, with the result), and the parts of the site
  reviewed lately. It is `check-tools/experiments.json` and `site_parts.json`, copied into `_admin['plan']` by
  `python3 check-tools/admin.py sync` (experiments.py and site_parts.py run it after every change; one small write). **The
  bill's colours:** green under $1, amber to $1.50, red beyond (the owner's warning and limit).
  **How often the AWS figures are read, and "↻ Refresh now"** (17 Oct 2026, the owner: "how often does this update and give me a
  manual refresh button"): by itself the scheduled run reads the Lambda calls about once a day (`USAGE_EVERY_HOURS` 20, CloudWatch,
  free) and the bill as often, **from the AWS budget `stockiq-monthly` (`BUDGET_NAME`), free**, with AWS's own forecast for the
  month. The button (admin `op: 'usage'`) reads both at once. Until the evening of 17 Oct 2026 the bill came from Cost Explorer
  ($0.01 a reading) every 3 days or on a press; the owner: "i do not want to pay 1c just to check usage!" The card gives each
  figure its own age ("calls read 2 h ago · bill as AWS last updated it, 3 h ago"; AWS updates the budget a few times a day).
  **The account value on it is the Practice portfolio tab's own** (17 Oct 2026, `admin-panel.js?v=4`; the owner saw $99,411 on
  the Admin page beside $99,643.23 on the tab): the portfolio script hands its live sum over (`practicePortfolio.figures()`, and
  an event `practice-portfolio:figures` at each redraw), and until it has its prices the Admin page shows the function's
  figure marked "an estimate until the prices are in". The function's `account_value(portfolio, record, quote)` values each
  holding at its latest price when given a price lookup (the weekly review does, running as the function) and keeps the old
  estimate otherwise (the autopilot's at its last check-in change, the owner's at cost). **The weekly review also says how the
  account stands against the same $100,000 in an S&P 500 fund since it began** (`fund_since_start`, the graph's rule: the last
  close at or before the start). Checked on his real account: $99,643.23, the fund $98,032.29, ahead by $1,610.94, the same
  as the tab. Rollback zip `stockiq-ai-trader_before_autopilot_adminvalue_20261017.zip`. AWS usage is not on it: the function's role
  can read no CloudWatch figures (it has DynamoDB, SES and logging only); that would be the next step, through the daily
  usage report's own function.
- **Proposals** (`admin_propose`; item `_admin` in `stockiq-ai-trader`, the last 60 kept): the weekly review proposes, from
  the account's own finished trades, switching off the AI review's early sales when they are clearly losing (30 or more
  trades, beyond twice the margin of error) and unticking a screener that is; and, ten days before a month's goal is
  due and not met, a session to look at it. **A proposal of kind `setting` is applied by the function the moment "Yes" is
  pressed** (`answer_proposal`: through `clean_settings`, noted in the activity list "Changed from the Admin page: …", and it
  counts as a change for the waiting rule); **one of kind `session` waits for a session**: `python3 check-tools/admin.py`
  lists what he said yes to; `admin.py done <id> "<what>"` marks it done; `admin.py add session|setting …` puts a question to
  him. The same proposal is not made again while open or for 30 days after an answer.
- **Deliberately not built:** anything that changes code by itself. Code changes only in a session.
- Tests: 8 in `ai_trader_test.py` (403 for others, the review and its proposals, yes and not now, no second answer, the
  scheduled run writing health every time and the review once a week); `check-tools/admin_panel_test.js` (9). Looked at
  in a headless browser with a stand-in answer.

### The diary, and the review every week or two (12 Oct 2026)

The owner asked how losses should be logged and how the autopilot will improve from here: "small changes could be
automated, but large improvements i may have to hop on like i am now to analyze in depth and look at improvements to make
every week or two". That is the arrangement. **When he opens a session for a review, run the routine below.**

**Who changes what**
- **The autopilot, by itself (as before, nothing added):** its five rules in `TUNABLE`, the order in which it buys shares,
  resting a screener, pausing the AI review's early sells. Each only through a trial beside the current rule, kept only
  when clearly better; never anything outside the function, never a setting of the owner's.
- **A session, every week or two:** everything else: what each level sets, the pace, the stop's distances, what the AI
  model is told, a new kind of trial, faults. It reads the review, picks **at most one or two** things, and follows
  "How to work on it" below. An idea about a trading rule is replayed on saved prices first
  (`check-tools/replay/replay.py`) and then goes live **as a trial beside the current rule**, not as the new rule.
- **The owner:** his settings, and yes or no to anything that changes the product (the screener scoring, section 7b).

**What is recorded, and for how long**
- **Each finished trade** (the record's `history`, last 300 an account; the shared record's `pool`, last 3,000 of all
  accounts): what it was bought on (screener, rank, score, RSI, 7- and 30-day change, volume, who chose, how long it had
  stayed, how far above its 52-week low), the level at the time, result in percent and dollars, the S&P 500 fund over the
  same days, how long it was held, how it was sold, its best and worst, its path, the stop as last worked out, the AI
  review's last word, its rank and score at the sale, and what it did in the same time again after the sale (`after`).
- **The diary, never trimmed** (new on 12 Oct): table `stockiq-ai-trader-journal`, key `userId` + `at`, pay per request.
  `keep_diary(user_id, record)` runs inside `save_item` and writes one row for **every line of the activity list**
  (`kind` `log`: buys, sales and notes with their reasons and details), **every finished trade** (`trade`: the whole row)
  and **every change of the settings** (`settings`: all of them, so a review knows which settings a trade was made
  under). Why: the activity list keeps 80 lines, which for an account with many holdings was under three days; the
  "why" of a sale was gone before anyone could read it. A row is written once (`j` on the line or the trade, `state.diary`
  for the settings); a note that is counted again and a trade whose `after` has arrived are written again under the same
  key. A write that fails is tried at the next save and never stops a save ("diary not written" in the log). **Seen for
  real:** the first save after the deploy (09:22 UTC, a visit to the dashboard) wrote 60 rows, all the record still held
  (54 lines from 10 Oct, 5 trades, the settings), with nothing in the function's log. Nothing reads the table while
  trading. It is keyed by the account's address like the other tables: **never copy its rows into git.**
- **Not recorded:** the shares and coins it passed over (for shares a replay rebuilds any day's ranking from saved prices;
  for coins the entry log of section 8b), prices between check-ins, and the full text sent to the AI model.

**The review tool:** `python3 check-tools/autopilot_review.py [--days 14] [--account <address>] [--out <file>]`.
Read-only (the record, the diary, the shared record, what each holding cost, the function's log); not a visit to the
dashboard; never prints the address. With no account named it takes the one account that has the autopilot switched on.
Eight parts: the settings and their changes; the result in dollars against the bar of 300 finished trades; where the
money went (by how it was sold, market, screener, rank, RSI, time held, who chose, level; the group that lost most
first, each with its margin of error and the words "too few to read" under 30 trades); the losses one by one with what
each was bought on and the AI review's last word, those that had been up 2% and still ended down, and what sold holdings
did afterwards; what it did and why it did nothing; what the shared record has learned and is trying; faults in the
function's log; the size of the record and of the diary.

**The routine for a review session**
1. "How to work on it", step 1 (both repos clean, live equals the mirror).
2. `python3 check-tools/autopilot_review.py --days <since the last review> --out check-tools/reviews/review-<date>.txt`
   and read all of it. Then `check-tools/reviews/questions.md`: answer what can now be answered, test the open ones that
   can be tested on saved prices, and add at least five new questions of your own. The files in `check-tools/reviews/` are the memory between reviews: read the last one first.
3. **Faults before figures** (parts 7 and 8): a fault is fixed whatever the sample size.
4. **The dollars** (part 2) against the bar. Say the number of finished trades with every figure. Under 30 in a group
   there is nothing to read; that is not a reason to invent something to change.
5. **The losses** (parts 3 and 4): is there a group of 30 or more that is clearly down (beyond twice its margin of
   error)? Did holdings go on rising after one kind of sale (sold too early) or falling (the sale saved money)? How many
   had been up and ended down (a stop only acts at a check-in)?
6. **The trials and the progress reports** (part 6): verdicts since the last review; anything that has not moved.
7. **The settings** (part 1): trades made under different settings are different experiments; do not pool them blindly.
8. **Decide, at most one or two things.** Each names the group and the figures it rests on; a trading rule is replayed
   first and built as a trial; a fault or a wording goes straight in. "Nothing to change yet" is a full answer.
9. Write the findings and the decision into the change log (section 13) and "Start here when resuming"; commit the
   review file.
10. Tell the owner in plain words: the dollars, what was found, what was changed, what waits for more trades. Section
    7b stands: the screener scores have shown no reliable edge, and the share of trades that ended up is not profit.

**Weak spots already seen, to look at in the first reviews** (12 Oct, from five finished trades: observations, not findings)
- **The AI model's notes were written from very few trades and shown back to it at every choice** (after five coin trades:
  "trades with RSI around 50 did not perform well overall"). **Fixed the same day at the owner's word** ("i'll go with advice
  you give"): no notes under 30 finished trades (`LESSONS_MIN`; "Learning from its own results"). Still thin and worth a look
  at a later review: the scorecard lines the model is shown for a group of 8 or more trades (`MIN_SAMPLE`); they are plain
  figures with their count, not conclusions.
- Both sales by the AI review were the two largest losses (-$985 together). Two trades say nothing; watch `after` for
  them: did they go on falling?
- CKB had been up 2.5% and ended down 0.8%: the stop was passed between two check-ins. With check-ins every 6 hours this
  will recur; the count is in part 4.
- **The size of the record.** A finished trade takes about 0.7 KB and a remembered holding about 1 KB, so 300 trades and
  50 holdings come to roughly 300 KB of the 400 KB a row can hold. The tool warns above 300 KB. If it does: drop `path`
  from the trades kept in `history` (the diary has it), or store the record compressed as `_brain` is.
- **When:** the first review around 26 Oct 2026, or sooner if 30 trades have finished or the tool shows a fault.

### How to work on it: the routine that held up

**Before building an idea about how it trades, replay it:** `python3 check-tools/replay/replay.py` (20 seconds; section 7b,
last part). An idea that is not ahead on both parts of the period, or that random buying beats, is not worth a deploy.

1. **Start from what is live.** Both repos clean (`git status -sb`), then check the live function is
   the mirror: download it, `cmp` with `lambda-sync/stockiq-ai-trader/lambda_function.py`, and note
   its `CodeSha256` and the `shasum -a 256` of the website files. Run one session at a time.
2. **Stage, do not edit in place**: copy the function and the website files to
   `check-tools/pending-<name>/lambda` and `/web`, and change the copies.
3. **Test the copies** (none of these touches anything real):
   ```bash
   cd /Users/dave/VSCODE/stockiq/check-tools
   python3 -W ignore ai_trader_test.py pending-<name>/lambda/lambda_function.py | grep -v '^PASS'   # 424 checks
   node autopilot_test.js pending-<name>/web/practice-autopilot.js | grep -v '^PASS'                 # 203 checks
   sed 's#https://5c7pt7qurshld4cwaqyopfxcei0cuurj.lambda-url.us-east-1.on.aws/#__PRACTICE_API_URL__#' \
     pending-<name>/web/practice-portfolio.js > /tmp/pp.js && node practice_test.js /tmp/pp.js | grep -v '^PASS'   # 95 checks
   python3 -W ignore autopilot_plan_check.py pending-<name>/lambda/lambda_function.py pending-<name>/web/practice-autopilot.js 150
   node autopilot_bell_test.js pending-<name>/web/autopilot-bell.js | grep -v '^PASS'                 # 22 checks (the notification bell)
   python3 ai_chat_test.py pending-<name>/chat/lambda_function.py | grep -v '^PASS'                 # 19 checks (the AI chat's function)
   ```
   `ai_trader_test.py` sets the pace by hand at its top (it patches `DEFAULTS`), as a user who chose
   his own values; the real defaults, where the level sets the pace, are tested in their own part.
   It also sets `STAY_CHECKS` to 1 so that older tests buy a coin at once; the real wait has its own part.
   **Never run `practice_test.js` on the real `practice-portfolio.js`**: it holds the live storage
   address and would write to the live table (it happened once). Add checks for what you change.
4. **See it in a browser** without a login: `dashboard_page.py` (both sections, stand-in server;
   give it `dashboard.html` as a sixth argument and it puts the page's real tab bar and tab script
   into the test page, step `tabs`). After any edit to `dashboard.html` also check that the
   sections still balance and that every inline script parses (`node --check` on each `<script>`
   block): the logged-in page itself cannot be opened from here, it redirects to Sign In.
   Steps such as `type,sale,trial,preset,sellall,limits,trailstop,split,cards,pace,listswitch,next,budget,shares,progress,breakdown,locked,mobile,open`) with headless
   Chrome; `--dump-dom` for what it printed, `--screenshot` for the look (section 12).
5. **Try the staged function on a copy of the real record**: read the owner's item from both tables
   (read-only), load it into stand-in storage under another name, run `run_user` / `public` with
   stand-in prices. This catches a record written by older code. Redact the email when printing.
6. **Deploy with `pending-<name>/deploy.sh`** (the owner's permission rule only allows that form:
   `bash /Users/dave/VSCODE/stockiq/check-tools/pending-<name>/deploy.sh`, absolute path, nothing
   else on the line). The script must: stop if the daily deploy is running; download the live
   function and stop unless its `CodeSha256` and its file equal what the change was built from;
   keep the old zip as `~/VSCODE/backup/<function>_before_<name>_<date>.zip`; update the code and
   copy it into `lambda-sync/`; check each website file's fingerprint before copying it in; upload
   with the cache headers of section 12; invalidate just those paths; support `DRY_RUN=true`; be
   safe to run twice. Copy the last one from git history (`git log --diff-filter=A --
   'check-tools/pending-*/deploy.sh'`). Run the dry run, then the real one, **away from :10 and :40
   past the hour**, when the schedule runs.
7. **Verify live**: `curl` the scripts with their new `?v=N` and `cmp` with the local files;
   download the function again and `cmp`; make the page's own read-only call (`action: get`) and
   read it; look at the function's log after the next scheduled run
   (`aws logs tail /aws/lambda/stockiq-ai-trader --since 10m`).
8. **Write it down and commit in steps**: update this section, commit and push each finished stage
   (the staging folder too, marked "work in progress, not live yet"), remove the folder after the
   deploy, commit the website files by name. The owner's sessions can stop mid-task.

Traps met on 10 Oct: a deploy script checking `pgrep -f deploy-to-s3.sh` finds its own text when it
is written and run in one command (run it on its own, or match the process as the last script
does); in zsh write `"${C}:path"` for `git show` (`$C:c…` is read as a modifier and left an empty
file once); a stand-in page that does not finish has a syntax error in its own script (check each
`<script>` block with `node --check`); in a browser step, take an element afresh after the panel
has redrawn (a kept reference is to the old one and nothing happens); **a link inside the panel
must not be a bare `href="#"` unless its click is cancelled** (`preventDefault`): "What happens then"
was one, handled by the part-switching branch that did not cancel it, so the browser went to the top
of the page (the owner: "it just stays at top of screen"); the site's stylesheet sets
`scroll-behavior: smooth`, and a headless browser does not play the glide, so a scroll looks like no
movement there unless the test sets `scrollBehavior = 'auto'` first (`dashboard_page.py`, step `next`); test expectations with dates must allow for the local time
zone; SES and the news feeds are only used when running as the Lambda, so tests need stand-ins
(`mail=`, `headlines=`); two sessions building at once collided (the fingerprint check caught it);
the panel test's `text()` leaves `&#39;` as it is, so a pattern that quotes a notice with an
apostrophe must allow for it; a test of an action that depends on the day (trading hours, `sellall`)
must set the function's clock (`m.datetime = at(when)` in `ai_trader_test.py`), or it passes on
weekdays and fails at the weekend.

### Start here when resuming (state at 17:45 UTC on 12 Oct 2026: the end of a three-day session)

**ADDED AT THE END OF 13 OCT 2026 (a long day on the screeners; read this before the older text below, which is of 12 Oct):**
- **27 screeners, none "Coming Soon" of the old twelve.** Twelve were added that day (section 8b's table; section 13 has
  each batch's story). Six further markets are listed as "Coming Soon" on the analysis page (Euro Stoxx 50, Sweden,
  China, Taiwan, New Zealand, Mexico): `add-new-screener.md` is the recipe, and it was used twelve times.
- **The autopilot buys from all 27**, grouped as the site's Screeners menu is: US markets, Europe markets, Asia-Pacific
  markets, Americas markets, Coins. **A group is a region now** (it was a country), so the budget's spread changed.
- **The quick set-ups are gone**; the screeners card has shortcuts that change only what is ticked. **A scheduled
  check-in waits until the settings have been left alone for 10 minutes** (`SETTLE_MINUTES`).
- **The owner's settings at the end of the day:** Balanced, 50 holdings, built up over 1 day, a check-in every 3 hours,
  holdings kept up to 10 days, 17 screeners (the main index of every country, and crypto), 10 holdings a region.
- **For the first review: 13 Oct from 16:11 UTC is not one experiment.** The settings changed about fifty times in an
  hour (quick set-ups pressed, a 6-hour holding limit in force at the 16:40 check-in, which sold five holdings), and
  the screeners and groups changed at 16:32. `autopilot_review.py` part 1 lists every change. 18 trades had finished
  by then, down about $1,818 in all; the first buy from a new screener was CVE.TO (Canada TSX 60) at 16:40.
- **Do not write his settings while he is at the page** (section 13, the entry on the regions): say what they are.
- **The breakdown table** heads its column "Made money" (it was "Ended up") and says that it counts only the autopilot's
  finished trades: **what the owner buys and sells by hand is on the Practice portfolio tab**, not there.
- Live at the end: `stockiq-ai-trader` `wLHHlexH…`, `stockiq-ai-chat` `9K5HRpiz…`, `stockiq-screener-coordinator`
  `979X4yAm…`, 741 share-screener workers in 25 groups on the one package, `practice-autopilot.js?v=47`. Tests: 451
  function, 216 panel, 22 chat. Kept on purpose: the three `pending-*-undo` folders.
- **Still to be seen for real:** "settings just changed, left for the next run" in the function's log; `M&M.NS` in a top
  10; the stock pages' menu (old two labels until regenerated); a signed-in browser and a phone for all of the day's work.

**FIRST THING IN EVERY SESSION: tell the owner, in plain words and before anything else, what has happened since the last
one, and when the last review is a week or more old run the review and bring him the list of improvements to say yes or
no to (the instruction at the top of this file).** (His words on 11 Oct: "next time i open a session… update me on how monday went and anything else"; Monday 12 Oct
was reported to him through that day.) Lead with dollars. All read-only:
1. `python3 check-tools/autopilot_review.py --days <since the last session>`: the result, the losses, faults, the trials.
2. `grep -a -E "Pages written|Indexable|No price data|Company figures|Sync complete|pushed|could not|failed|All done|Skipping git" ~/stockiq-daily.log`
   (the daily deploy), and `git status -sb` in both repos.
3. The "still to be seen" list below: say which of them has now been seen.

**WHEN THE OWNER SAYS "review the autopilot"** (every week or two; the first around 26 Oct 2026, or at 30 finished trades): run
the routine in "The diary, and the review every week or two" above. Read `check-tools/reviews/` first; the baseline is
`review-2026-10-12.txt` (five finished trades, down $1,014).

**What the owner is after, in his words:** "the goal is to pickup on patterns if we see patterns that are much more success
than failure its something to repeat, if we see consistent loss patterns we also steer away… end goal here is make money
we need it over 100,000"; earlier: "always be active ever changing and improving", "close to 70% profit 30% loss",
"seamless and straightforward so a dummy could figure it all out", "something on the site to tell me whats going on",
"a smart AI that is learning in a central location for all users", things "setup in one way not multiple ways". He goes
with the session's advice on changes ("sure i'll go with advice you give to make changes and improvements").
**The honest position, said to him each time results come up (section 7b):** the replays and backtests found no reliable
edge in the screener scores, only momentum in a rising market; quick share trading loses to costs; the share of trades
that end up is set by the selling rule and is not profit. Nothing here promises an account above $100,000. A pattern
counts from about 30 trades in a group and beyond twice its margin of error; judge by dollars and the average a trade.
**He asked whether code changes by itself in the background. It does not, and must not:** the autopilot changes five
numbers of its own and the order it buys shares in, through trials; code changes only in a session.

**THE MANDATE (the owner, 12 Oct 2026): "its like this is your playground, i want you to be smart and find ways to make
money that beat an index fund such as s&p".** So a session's job is not only to tend what exists but to **look for an
edge**, actively, every time. How, without fooling ourselves:
- **Shares first.** The owner, the same day: "i'm honestly not that interested in the crypto more so the stock screeners".
  The search, the trials and the reviews put the share screeners first; coins get what costs nothing (the entry study
  below runs by itself at a check) and no building of their own unless he asks.
- **The fast lane is the replay, not the live account.** `check-tools/replay/replay.py` tests an idea on four years of
  prices in about 20 seconds; the live account needs weeks for 30 trades. Every weekly check: think up a batch of new
  ideas (what to buy, when to sell, how long to hold, how much, which market), replay each, and keep only what passes
  **all four**: ahead of the index fund after costs on the first 60% of the days **and** on the last 40% it never saw;
  ahead of the same rules buying at random; still ahead with the seven chip / AI names left out; and a reason to
  believe it that was written down before the result. Write every idea tried into `check-tools/replay/` with its
  result, the failures too, so that nothing is tested twice and nobody counts only the winners.
- **The session asks the questions, it does not wait for them** (the owner: "what i'm after is for you to ask these
  questions and actively gather more ways to improve"). **`check-tools/reviews/questions.md` is the running list**: every
  question asked, by him or by a session, how to test it and what became of it. Each weekly check adds at least five
  new ones of its own from what the review shows, tests those that can be tested, and reports the answers to him with
  the improvements. Eighteen were in it on 12 Oct 2026 (ten of the session's own, shares first).
- **Survivors go live as trials** in the queue (below), never as rules. The live record is the judge.
- **Where an edge could plausibly come from** (the leads, best first): (1) momentum, the one thing that has held up
  (shares furthest above their 52-week low: about +2 points a trade against the fund in both parts of the replay),
  combined with longer holds and no selling on the signal alone; (2) trading less (costs are the surest loss);
  (3) real company figures (profit, debt, growth), never tested because there is no history of them here: start
  recording them with each buy; (4) the market's own state (stay out, or hold fewer, when the index is below its
  long average); (5) a model fitted to the shared record once it holds hundreds of trades.
- **The first lead found this way, the owner's own (12 Oct 2026): "i think alot of those are there because they did just rise
  up fast. typically stocks rise fast hit a high then drop".** For **shares** four years of prices say no: the screener's
  top 10 did about what the whole list did a day, a week and a month later, and a fast rise over 1, 5, 10 or 30 days was
  followed by neither a clear fall nor a clear rise (`paper-test/results-*-one-worker.txt`). For **coins** the first look
  says he may be right: `python3 check-tools/crypto/entry_study.py` (new; read-only; the entry log of section 8b against
  prices now) found that the 51 entries into the coin top 10 of 11–12 Oct were down 4.0% on average (± 0.8; 41 down, 10
  up) a median 16 hours later, while Bitcoin, Ethereum and Solana were down 0.4 to 1.5% over the day; **and the faster
  the rise before entering, the worse**: up 10% or more the day before, -5.4%; up 20% or more the week before, -7.4%;
  under 5% the week before, +0.2% (six entries). **One market day, 30 coins, entries that are not independent: a lead,
  not a finding.** Run it at every weekly check (results in `check-tools/crypto/results/`). If it shows the same over
  five or more separate days: tell him, and only if he wants coins worked on, a trial in the queue, "pass over a coin
  that has just risen fast" (the level's limit on
  the 30-day move is the nearest thing there is now; nothing looks at the last day or week). It would also say
  something about the crypto screener itself, whose score rewards exactly such a rise (section 8b, "How a coin is
  scored"): the owner's to decide, with the evidence.
- **What the search needs and does not have yet:** prices for more than the 101 shares on this machine (a list of
  today's members flatters every "buy what rose" rule; download a wider and older list slowly, away from the daily
  run, section 8b on Yahoo's limits), saved coin prices, and company figures over time.
- **The honest odds, as told to him the same day:** beating an index fund from public price data is something most
  professionals fail at; a rough one in ten. The mandate is to try properly and report truthfully, with the month-3
  stop rule (the goals, below) as the backstop.

**"GO PLAY" (the owner, 12 Oct 2026: "i want you running and me simply having to open a session and say go play").** When he
says it, or anything like it, the session works by itself for as long as it lasts, without asking between steps:
1. The opening report and, if a week has passed, the review and the standing against the month's goal.
2. **Grow the data**, because that is what limits how many questions are worth asking: prices for far more shares than
   the 101 here and further back (slowly, away from the daily run: section 8b on Yahoo's limits); a dated copy of
   `.analysis_cache/company_figures.json` each time (the company figures of 3,333 shares as they are today: kept week
   after week they become the history that does not exist yet); more recorded with each buy.
3. **Ask and test, in bulk.** Build up the test bench in `check-tools/replay/` so that it runs hundreds of variants of an
   idea by itself and prints only those that pass the four tests **after allowing for how many were tried** (of 1,000
   tries on 101 shares, dozens look good by luck: on 11 Oct, 208 of 240 variants looked ahead on the first part of the
   period and 103 on the second). Log every question in `check-tools/reviews/questions.md`, the failures too.
4. **Put survivors live as trials** in the queue, and add measurements to the function, through the usual staged deploy
   with tests, a dry run and a rollback copy. **Allowed without asking**: it is fake money, bounded, and a trial is
   kept only if clearly better.
5. End with a short report: what was asked, what was answered, what went live as a trial, what needs his yes.
**Could a session start by itself every night?** (He asked on 12 Oct; answered, not built.) Technically yes, the way the daily
deploy starts: a launchd job on this Mac that checks every ten minutes whether a day has passed and then runs Claude
Code without a window (`claude -p "<the instruction>"` in this folder, with the tools it may use allowed beforehand,
since nobody is there to approve). It needs the laptop open, awake and online; a cloud session cannot do it (no AWS
access, section 5b). **Not worth it yet, and told him so:** the autopilot finishes a handful of trades a day, so a nightly
session would mostly find nothing new; every run draws on the same usage allowance he works with (it ran out several
times on 12 Oct); and an unattended session should not deploy anything (twice that day a person or a check caught a
mistake before it went live). If it is built later: research only (the review, tests on past prices, findings written
to a file and committed), never a deploy, with a limit on how long it runs; changes go live when he is there.
**What needs no session at all is gathering data, and that started the same day:** the daily job keeps a dated copy of the
company figures once a week (`publish_company_figures.py` → `research-data/company-figures/`, not in git); next, slowly,
prices for more shares the same way.

**Still needs his yes, always:** deleting anything; his own settings; what the public site says or how the screeners
score; anything that costs more than cents; anything near real money (never). **What "go play" cannot be:** running with
no session open. Something that searches by itself between sessions (the test bench on a nightly schedule, feeding the
queue) is a possible later step once the bench has proved itself in sessions; say so if he asks, with its cost.

**The goals, month by month** (the owner, 12 Oct 2026: "perhaps we should have goals ie month 1 it improves x amount month 2
y amount… your primary task is to continue to fix and find improvement"). **Targets to steer by, not forecasts**; the
review tool prints where things stand against them (its part 9; the numbers are `GOALS` at the top of
`check-tools/autopilot_review.py`: change the two together). The start: 12 Oct 2026, five finished trades averaging -1.03%,
the account at about $98,600.

| Due | Goal | Finished trades in all | Average a trade in that month, after costs | The account |
|---|---|---|---|---|
| 12 Nov 2026 | **Month 1: in profit** | 100 | above 0% | $100,000 or more |
| 12 Dec 2026 | **Month 2: in profit, and more of it** | 300 (the bar's count) | +0.2% or better | $101,000 or more |
| 12 Jan 2027 | **Month 3: clearly ahead, or a decision** | 500 | +0.3% or better, and the bar cleared | $102,000 or more |

- **What a session owes each month besides the numbers:** month 1: the buying-order trial has its verdict and the trial
  queue (below) is built and running; a review every week. Month 2: at least one change kept after a trial, or a plain
  statement that none of them helped. Month 3: the answer to "does this make money", either way.
- **If a goal is missed:** say so first thing, say why (which groups lost the money), and bring the changes that follow.
  **If month 3 ends with the average a trade still not above zero: stop tuning this strategy.** Then the choice put to the
  owner is to change what it buys from (real company figures, a model fitted to its own record, other inputs) or to
  switch it off. His words: "There is no point having this run if its not making profit."
- **Every month's goal is a profit, at the owner's word** (12 Oct, on reading the first version, which asked month 1 only to
  stop losing, -0.2% a trade and $98,000: "this is negative? we want positive. profit not loss"). A goal here is the line
  that decides when a month counts as a miss and something has to change, not a forecast: set at profit, a losing
  month brings changes sooner, which is what he wants.
- These numbers are what would count as progress, chosen before the results are in so that nobody argues with them
  afterwards. Section 7b gives no reason to expect them to be met; they are the test.

**THE THEMES PART, a trial live since 03:19 UTC on 18 Oct 2026** (the owner, asking whether it could invest by what is in the news,
"AI is taking off or debt problems or inflation problems or oil crisis… or just that way as a % of portfolio", then: "do what you
think is best i'd like to get as much data i suppose as i'd be running this a year and hopefully within a few months we have enough
to optimise and see profit month on month").
- **Why this form:** a theme in the news shows up first as a whole sector moving, so it is traded through 14 US-listed sector and
  theme funds (`THEME_FUNDS`: XLK technology, XLE energy, XLF banks, XLV health care, XLI industry, XLY and XLP consumer, XLU
  utilities, XLB materials, XLRE property, XLC communication, SMH chip makers, GLD gold, TLT long-dated US government bonds), not
  single shares picked from headlines. Replayed first (`check-tools/replay/sector_study.py`, `results-sectors-2026-10-18.txt`): the
  3 strongest by their past year without the last month, changed monthly, were ahead of an S&P 500 fund in both halves of five
  years (+7.0% and +45.4%), **mostly through SMH; without it behind in 3 of 4 half-periods**. A lead, which is why it is a trial.
- **What it does** (`run_themes`, at a check-in while the US market is open; `themes_on`: "Try changes to its own rules" on and a
  share screener ticked): **20% of the budget** (`THEME_SHARE`; the shares get the rest, `share_part`) is held in the **3**
  strongest funds by `trend` (252 days less the last 21, `theme_ranking`, prices through the price proxy with `range=2y`); every
  **28 days** (`THEME_EVERY_DAYS`) the ones that dropped out are sold and the newcomers bought with equal parts of the room. A price
  must be fresh, as for any share. The funds are autopilot holdings (`by: 'ai'`, screener `themes`, `is_theme`), but are not in
  `state.open`: not sold by the shares' rules or time limit, not in "Holding now", not in the share budget's sums (`ai_holdings`
  leaves them out unless asked). A sale goes into `state.themes.trades` and `realizedUsd` (`theme_sold`); "Sell everything it holds"
  sells them too.
- **The AI model's daily read** (`theme_read`, every trading day since 18 Oct 2026, `THEME_AI_EVERY_DAYS` 0.8; it was every 7 days, only when headlines were found: `market_headlines`, Google News, only
  when deployed): it is given the 14 funds with their trends and the market's headlines (untrusted text, the prompt says so) and
  names the funds it expects to do better or worse than an S&P 500 fund over the next week (up to 900 tokens, `prompt['tokens']`).
  **Recorded, never acted on**: `score_theme_calls` scores each call a week later (`rel`, the fund against SPY in percent, `right`).
  It may be allowed to act only after 30 or more scored calls are right clearly more often than chance; that would be a trial of
  its own. First read, on a copy of the owner's record on 18 Oct: "Concerns about a potential stock market crash and volatility in
  tech stocks", XLE better, SMH and XLK worse.
- **Where else it is known** (18 Oct 2026, the owner: "i hope this is aware across the site"): the screeners card (the market
  shares are of the money for shares, and a line links to the themes part); the weekly review on the Admin page
  (`theme_review_lines`: what it holds and is worth, funds sold against the fund, the AI's calls scored); the session's review
  tool (part 6b) and opening check (`session_start.py`, with a finding if the monthly change is overdue); the notification bell
  (its buys and sells are ordinary log entries); the public pages (home page card, About, FAQ); the chat's guide; the
  experiments register (`theme-sleeve`, public, so it is listed under "How it is improving" and on the Admin page);
  `questions.md` 26 to 30; `lambda-reference.md`, `stockiq.md`. Not in it on purpose: the share record, the bar and the
  month's goals' trade counts (the funds' trades are kept apart in `state.themes.trades`); the account value includes them.
- **What the page shows:** a "Themes part" section under Activity (`themesHtml`: what it holds, the next monthly change, results
  against the fund, the AI's last read and its scored calls, the 14 funds as last ranked, folded); the descriptions say the shares
  get 80%; the portfolio's plan line for a fund ("themes part (a trial)… kept until the monthly change around…"); a row in "What
  happens next"; the chat's guide; `public()` sends `themes` (`theme_view`).
- **How it is judged:** the part's result against an S&P 500 fund over the same days, **for over a year** (the owner's bar for real
  money: at least 5% a year ahead), in the experiments register as `theme-sleeve` (decide by 19 Oct 2027; public). A monthly
  change is one data point a month: there will be about 12 changes and 36 fund holdings in a year, which is little, so read the
  weekly AI calls (about 50 a month) as the faster evidence, and the part only as a whole.
- **First buys: the first check-in after the US open on Monday 19 Oct 2026** (14:35 UTC); on the owner's record that day it would
  buy SMH, XLE and XLK for about $6,500 each, mostly from cash not yet invested. The shares then have $78,080 of the $97,600 budget
  and held $72,469, so they buy little until holdings are sold.
- To switch it off: `THEMES = False` in the function (the funds bought stay until sold by hand or by "Sell everything").
  Tests: 21 in `ai_trader_test.py` (the older tests set `THEMES` off at the top), a block in `autopilot_test.js`, one in
  `practice_test.js`, one in `ai_chat_test.py` (`TRADER=<staged function>` to compare with a staged copy).

**THE PATIENT-SHARES TRIAL, live since 13:47 UTC on 12 Oct 2026** (the owner the same day: "getting as optimal as possible now…
actively do things try things"). The replay's clearest lesson for shares, put to the test with the fake money:
- **What it does:** while "Try changes to its own rules" is on, shares are tagged in pairs as they are bought (`pt` on the
  remembered buy: 0, 0, 1, 1, …; `state.patient.n` counts). A **patient** share (`pt` 1) is sold only by its loss limit,
  its gain mark, the stop that follows a rise, or at the end of its holding time: **never because the screener's signal
  turned or it slipped down the ranking (`review_sells`), and it is not put to the AI model's review** (whose usual
  reason to sell is a fallen rank). An ordinary one (`pt` 0) is sold as before. Coins are not part of it. `PATIENT` is
  the switch; `patient(facts)`.
- **One thing is tested.** The first design also kept a patient share 30 days; the panel-versus-function comparison
  showed what that meant (22 of 60 replays differed): it overrode a holding time the user had set and tied up the
  budget of anyone trading quickly. So the holding time the user set stands for both groups (`PATIENT_DAYS` 0,
  `hold_days`). **The owner's is 10 days, set by hand; the replay says longer is better for shares, and with no selling on
  the signal his patient shares will mostly run to that limit. It is his setting to lengthen.**
- **Pairs, not every second**, so that it does not fall together with the buying-order trial (every second share): each
  share is one of four kinds (ranked or furthest-above-low, ordinary or patient), and every share counts in both comparisons.
- **No verdict in the code**: the weekly review compares the groups (the tool's breakdown by `pt`, and its line on what
  is still held). Count both what was sold and what is still held, for buys of the same weeks: patient shares finish
  later, so the first to finish are the ones a limit caught. If patient shares are clearly ahead after 30 finished each
  way: make it the rule for shares (a deploy); if clearly behind: switch `PATIENT` off.
- The buy's plan and the sale's story say which kind a share is; the page's plans carry `patient`. Since 15:08 UTC the same
  day the panel lists the trial under "Improving its own rules" (`patientHtml`, with how many patient shares it holds),
  its description of the selling rules and its two switches name the exception, a patient holding's line on the
  portfolio says so (`planLine`), and the AI chat's guide knows both standing trials.
- Tests: 12 in `ai_trader_test.py` (the older tests switch `PATIENT` off at the top). Rollback zip
  `…_before_autopilot_patient_20261012.zip`.

**What it does when the money does not quite fit (the owner asked, 12 Oct; read from the code):** a check-in buys only
whole holdings. How many: the room (the least of the practice cash, the budget less what is invested, and what the
build-up has released less what is invested) divided by the size of a holding, with a cent a holding of slack for
rounding; the last buy of a budget takes exactly what is left, so **a cent or two short still buys**. **Short by more
than that, it does not buy a smaller holding**: it buys nothing, the check-in says "Not enough practice cash for another
holding ($X left, a holding is $Y)" and "Needs you" shows it. A buy is smaller than a full holding only when its
market's own share has less room than that left (never under the $25 smallest buy). Because the budget is set to the
practice money there is at every check-in (`fit_budget`), a falling account makes each new holding a little smaller
instead of leaving the autopilot short. What stays unused: a remainder under one holding (under 2% at 50 holdings).

**EXPECT THIS AT THE NEXT SESSION: the owner wants to improve the screeners' own scoring** (his last words on 12 Oct: "its very
likely i'll want to improve the screener functions after a week or so"; the screeners' rankings are what the autopilot
buys from, and what every user sees). Until now the scoring was left alone as his decision (section 7b); he is now
saying he wants it changed. So come prepared, do not start from nothing:
- **Bring candidates that have been tested**, not opinions: before he asks, run the ideas on saved prices
  (`check-tools/paper-test/factor_study.py`, `check-tools/replay/replay.py`, the four tests of "THE MANDATE") and have
  ready what held up and what did not. What is known so far: none of the score's 12 factors sorted shares reliably;
  re-weighting them showed nothing; "Financial", "Sentiment" and "Risk" use no real company data; distance above the
  52-week low and the longer rises (90 days, a year) were the only figures that pointed the right way in both halves.
  So the likeliest real improvements are **replacing the three empty factors with real figures** (company figures now
  exist for 3,333 shares: `.analysis_cache/company_figures.json`, with a dated copy kept weekly) **and giving momentum
  over months its due**, not shuffling the weights. Wider prices than the 101 shares here are needed to test it fairly.
- **How it is done is built** (section 8b, "The worker groups"): one file, `workers/stock_worker.py`, scores all 669
  share-screener workers; `workers/prove.py` shows every score, label and top 10 that a change moves; `workers/deploy.py`
  rolls it out through a packaged script, one small group first (Dow 30). **Its path for updating a live package has not
  been used for a real change yet**: read its output on first use. The CSV is built by the page and by the coordinator
  from the workers' fields: a scoring change needs neither touched, a new column both. `about.html` and the FAQ describe
  the 12 factors and must follow a change. Crypto is a separate program (54 workers, one version).
- **Say what it changes for users**: every ranking and signal label on the site moves on the day (the RSI change of 11
  Oct moved a third of the labels); the autopilot's trades before and after are different experiments.

**FIRST JOB AT THE FIRST WEEKLY CHECK (on or after 19 Oct 2026): the trial queue.** Agreed on 12 Oct ("thats fine so long as
my goal is reached"); deliberately not built at the end of that day's long session, hours before the first buys at 50
holdings, with nothing for it to do until the buying-order trial ends. What to build: a list of trials the function works
through by itself, one at a time, each beside the current rule and kept only if clearly better, so that the end of one
starts the next without a session. In it (the ideas that held up in the replay, section 7b): (1) a longer holding time
for shares (only where the user left the time to the level); (2) not selling a share on the screener's signal alone:
**started ahead of the queue on 12 Oct as the patient-shares trial (above); fold it into the queue**; (3) for coins, a loss limit and gain
mark sized to each coin's own daily movement. Each needs a tag on the buy (as `o` for the buying order) and its verdict
by `trial_figures`. Read the first week's trades before fixing the order (if nearly every sale is "signal turned", (2)
goes first). Every review restocks the queue from what the losses show.

**Where it stands (12 Oct 2026, 17:45 UTC, when the owner closed the session to let it run; he changes settings often, so read
the record):**
- **The account: about $99,050** (down about $950 since the start): the autopilot's finished trades are down about $1,035
  (six now), the owner's own are up $144, and what is held was about level on the day. The dashboard has the live figure.
- **Six finished trades, two up, all but the last coins:** WEMIX +0.6%, CFX +1.0%, ERG -2.8%, WAL -3.25% (-$811.70), CKB
  -0.8%, and **HPE -1.1% (-$21), the first finished share trade**: bought at 14:38 UTC, sold at 17:40 by the AI review
  (its rank had dropped from 2 to 117 within three hours, the day down 4.6%). It was an ordinary share of the patient
  trial and the "furthest above its low" pick of the order trial.
- **It holds 11** (the practice portfolio 12: the owner bought TLS.AX by hand, $5,000, at 17:28 UTC): five older, larger
  ones (4307.T $12,500, MANTA-USD $24,985, ASX.AX and QBE.AX $9,994 each, 6976.T $7,488) and six at the new size of about
  $1,900: FANG, CTVA, DDOG, TSCO.L (14:38 UTC) and FTNT, LINC (17:40 UTC). $76,657 invested, cash $17,452.
- Settings: Balanced, **50 holdings set by hand**, budget $94,108 (all the practice money the autopilot can reach, set by
  the function after the owner's own buy), built up over 1 day, **a check-in every 3 hours**, holdings kept up to 10
  days (all three set by hand), trailing stop "protects a gain", all three switches on. Screeners: S&P 500, Russell
  1000, Russell 2000, NASDAQ 100, Dow 30, ASX 200, FTSE 100, Nikkei 225, crypto; shares of the budget automatic (10
  holdings a market). **His interest is the share screeners, not coins** (he leaves crypto ticked as a small part).
- **Three things are running by themselves:** the trial of which share to buy (`o`); the patient-shares trial (`pt`: of
  the six small holdings, CTVA, DDOG and LINC are patient); the count of headlines with each buy (`heads`). The diary
  keeps every line. Nothing else is to be changed in how it trades until there are trades to read.
- **Waiting for:** 30 finished trades for the first notes and the first real review; 20 at one level for the first
  progress report; 10 finished each way for the order trial's verdict, 30 for the patient trial's.
- **The month's goal** (12 Nov): 100 finished trades, an average above 0% a trade after costs, the account at $100,000 or more.

**Still to be seen for real** (strike each when seen): a "Left alone" line at a Tokyo opening with only old prices, then the
same market looked at again half an hour later; the first small buys at 50 holdings, up to 10 at a check-in, with
`heads` on the remembered buy; a FTSE run on a morning after a London session showing that session's prices; the
(the company figures published by the daily run itself: **seen on 13 Oct 2026**, "Company figures published for the
single-stock report", 3,332 stocks); a "tighten" answer; the larger model in a review; a coin held back until it has stayed; any trial of a rule; the
first progress report and its email; whether the test email reached the owner's inbox. **Opened by a session for the first time on 13 Oct 2026, read-only: the Practice portfolio tab as the owner's account**
(`REAL_USER=<address> node check-tools/live_practice_check.js`, with `WIDTH=390` for a phone's width, `SHOT=<file.png>` for a
picture, `LOCAL_PP=<file>` to try a staged script on the live page; only the portfolio's own "get" and the price
function's GETs reach the site, everything else is answered locally, so nothing is written and it is not a visit; the
autopilot's answer is withheld, so holdings carry no plan lines there). **Still never opened: the autopilot tab with real
data, the Reports tab, and a real phone. The owner sent a screenshot of the Practice
portfolio tab on 12 Oct (desktop, dark): heading with the two tools beside it, the four cards, the "whose result" row and
the sidebar all as intended; the usage badge still sits over the top right corner (section 11).**
**Seen for real at 17:40 UTC on 12 Oct (the first scheduled check-in on the day's last code):** the build-up fix let it buy at
once (FTNT and LINC, $1,883 each; before the fix there was no room until the next afternoon); new holdings carry their own
stop from the buy (FANG starts after +1.3%, CTVA +3.4%, DDOG +2.4%, FTNT +1.6%, LINC +2.4%; TSCO.L not yet, London being
shut); the patient tags went on in pairs (FTNT ordinary, LINC patient); the AI review sold HPE and left the patient
shares alone; the budget was fitted to the money after the owner's own buy. No fault in the log.
**Seen for real at 14:38 UTC on 12 Oct (a check-in the owner asked for by hand):** five shares bought at the new size ($1,982.58
each): FANG, HPE, CTVA, DDOG and TSCO.L, across the US and London. **Tagged in pairs for the patient-shares trial exactly as
designed (`pt` 0, 0, 1, 1, 0), crossed with the buying-order trial** (FANG ordinary and as ranked, HPE ordinary and
furthest above its low, CTVA patient and as ranked, DDOG patient and furthest above its low); each carries `heads` (0, 3,
1, 3, 0) and `headAge`; a patient share's plan says so. After it: 10 holdings, $74,875 invested, room for 12 more of this
size until the five older, larger ones are sold (by 20 Oct at the latest). Settings then: a check-in every 3 hours, the
build-up 1 day (both set by hand), all else as below.
**Seen for real so far:** clean scheduled check-ins on every version; buys spread over two share markets (12 Oct); the
fresh-price rule on live prices; headlines reaching the model; sales by the following stop and by the AI review; the
look-back; the shared record taking in trades, its notes reaching an activity list, and its five-trade notes dropped
again at 10:10 UTC on 12 Oct; the diary's first 60 rows; the bell confirmed by the owner; the chat answering from its guide.

**Limits to remember:** a stop only acts at a check-in; trading hours know no public holidays (covered by the 3-hour
price rule); a market's share is a number of whole holdings; holdings bought at an earlier size keep it until sold; the
trading cost is one typical figure (0.1% each way); with one account the shared learning is that account; headlines
are titles only, and most candidates have none. **Not known:** how the owner looks at the site (stockiq.tech, or a local
preview from Kiro): ask early when a change "does not show" (section 9).

**What is live, and how to confirm nothing has moved since** (all compared with the local copies on 12 Oct, 10:17 UTC):
- `stockiq-ai-trader` `K5Sj58IvkSa7DcNcSVsfZeidlJEimX8XnuA/6o/eQnU=` (since 03:19 UTC, 18 Oct 2026: the themes part; `stockiq-ai-chat` `snC0Sn/V…` the same minute; earlier `15k0lkcP…` 17:00 UTC, 17 Oct, the free bill; `vSGWQgIB…` from 04:54 UTC that day: the Admin page; `wLHHlexH…` from 16:59 UTC on 13 Oct: the waiting rule; `i9WtL7oP…` from 16:32 that day: 27 screeners in five regions; before that `0tynNBjn…`, 3,079 lines; after the check: the headline filter 10:29 UTC, the patient-shares trial 13:47 UTC, a holding's own stop kept with the buy 16:51 UTC, the build-up that leaves out what is invested 17:25 UTC); `stockiq-ai-chat`
  `9K5HRpizpV9lHdwP8eOwKpB00IGaNRgUz2qQEQRi6rs=` (since 13 Oct 2026, 17:00 UTC); `stockiq-price-proxy` `lzqBC+6a/h51byePPZpa+e29ACnMZGPQp+TEt2SQJ8g=`; `stockiq-screener-coordinator` `979X4yAm37f76T4RQfYT8ClqaR9P8NO0r+5LeqgDK7A=` (since 13 Oct 2026, 16:11 UTC, with the twelve screeners added that day);
  `stockiq-option-1-1-custom-analysis` `I84SxSgLYNt7…`; `stockiq-chart-generator` `OIDrZ2W9G3lJ…`; `stockiq-paper-portfolio`
  `s6IR+/80N/3k…`; the two signals functions `6nVDLm4/8G6K…`; the crypto orchestrator `yvmucU37gHJH…` and its 54 workers
  `DaTSp0Aqxq7x…`; all 669 share-screener workers `q9ZX/UvTBcsz…` (`workers/live.txt`; `python3 check-tools/workers.py`
  shows "one" for the 13 groups). Each equals its mirror in `lambda-sync/`.
- Tables made on 12 Oct: `stockiq-ai-trader-journal` (the diary).
- Website (sha256 starts): `practice-autopilot.js?v=47` (`15e2d0d78a1f`), `practice-portfolio.js?v=35` (`77079a71f71a`),
  `dashboard.html` (`5ee05cf4abf4`), `index.html` (`9451afe87859`), `theme.js` (`bb9a94a7e6c2`, with the switch for the header chip), `visitor-bar.js` version 2 (`dcabd7523aa2`), `analysis.html` (`f214d39b01ed`), `mobile-sidebar.js?v=2` (`19512615d3e8`), `styles.css` (`d6493ce17b8d`), `autopilot-bell.js` version 8 (`88119f40c022`),
  `analysis-functions.js` (`0207a09e771b`), `screeners.js` (`4512115ab389`), `ai-chat.js?v=2` (`87eaadf52197`). Live equals local for each.
- Tests on the live files: 451 function, 216 panel (13 Oct 2026, with the regions, the shortcuts and the waiting rule; they were 442 and 210), 130 portfolio, 22 chat (13 Oct 2026, after the fund's line; they were 118 and 21) (one of them, "buying by quantity buys exactly that many", fails on and off while the US market is open: improvements, item 0b), 22 bell, 20 chat, 42 signals; the panel-versus-function
  comparison clean (3,780 budgets, 4,166 spreads); the worker deploy tool's self-test passes.
- No fault line in 48 hours in the logs of 15 functions, no Lambda error in three days; both schedules enabled.
- Both repos pushed; **the only `check-tools/pending-*` folders left are the three ways back, kept on purpose:** `pending-screeners-undo` (the analysis page's one screener routine), then `pending-cleanup-undo` and `pending-banners-undo` (the two steps back from the header chip). Run them in that order if more than one is wanted: the first two touch the same script. `website/` carries the daily job's own three files
  uncommitted (news.html, news.js, sitemap.xml) until its next push.
- Rollback copies, one per deploy, in `~/VSCODE/backup/`: `stockiq-ai-trader_before_autopilot_<name>_<date>.zip`, in order:
  10 Oct `v2, fast, panel, autosave, desc, smart, review, controls, wording, limits, gains, pace, stop, orphan, steady,
  trail, now, news`; 11 Oct `clear, hours, next, budget, shares, low52, progress, order, idle, paid, central, release, bell,
  takeover, report`, `stockiq-ai-trader_before_sweep_20261011.zip`, `…_costs_…`; 12 Oct `fresh, due, holdings, journal,
  notes, heads, junk, patient, rows, buildup`; 13 Oct `regions, settle`; 17 Oct `admin`. `stockiq-ai-chat_before_{dashboard, wording, levels, sweep, costs}_20261011.zip`, `…_{guide, guide2, guide3}_20261012.zip`, `…_before_filter_20261013.zip`, `…_before_fund_20261013.zip`; `stockiq-price-proxy_before_fund_20261013.zip`.

**Improvements to come: one list. Take an item out when it is done; add ideas as the data suggests them, and new ones of
your own every session (the instruction at the top of this file).**
*Agreed with the owner on 17 Oct 2026 (state that day: 51 finished trades, -1.15% a trade after costs, clearly down; the whole
account ahead of the same $100,000 in an S&P 500 fund by about $1,600 after one week in which the fund fell 2%; the
buying-order trial finished and was not kept; the AI review's early sales switched off and coins unticked at his yes):*
- **At the first weekly review (on or after 19 Oct 2026), build: (A)** the trial queue, starting with **a longer holding
  time for shares** (question 6; the replay's clearest finding); **(B)** company figures (profit margin, debt, revenue
  growth) **recorded with every share bought** and the record split by them, from `site-data/company_figures.json` (3,333
  shares; question 18); **(C)** item 9b below (done the same day).
- **Prepare as tested options for his decision: (D)** a market-mood rule: hold fewer shares, or none, while the S&P 500 is
  below its 200-day average (question 9; replay first, the four tests of "THE MANDATE"); **(E)** the screeners' own scoring:
  the three factors that use no real data replaced by company figures, and momentum over months given its due (the part
  "EXPECT THIS AT THE NEXT SESSION" above). (E) changes every ranking on the site: his yes, after the evidence.
- **Watch, do not act yet:** shares bought at rank 1 to 3 did better (-0.6% a trade, 24 trades) than at rank 4 to 10 (-1.8%,
  10); with 50 holdings it buys further down each ranking (question 20).
*Waiting on finished trades (each has its trigger; nothing is adopted from hindsight, a trading idea goes live as a trial):*
1. (Done 15 Oct 2026: **the buying-order trial ended, not kept**: furthest above the 52-week low -2.64% a trade against -0.68%
   as ranked, 10 each way. Next in line: a longer holding time for shares, the plan above; not selling on the signal alone is
   the patient-shares trial, running.)
2. **Do headlines earn their place?** At 30 trades with and 30 without (`heads`; the review tool's split). If buys with
   headlines do no better: stop fetching them for candidates (fewer calls, shorter prompts). If better: widen them (the
   feed's summary text as well as the title; a feed that covers Sydney, Tokyo and London shares, which get none now).
3. **The AI review's early sales** (its two so far are the two largest losses): read `after` for them at 8 to 12 sales;
   the pause for sales that came too early is already built (`review_ai_sells`). **The owner asked on 12 Oct whether a sale
   like HPE's (sold by the review three hours after it was bought, -1.1%) is checked afterwards. It is: `look_back`
   prices every sold holding again after the holding time that was set, five days at most (`settle`: `later`), not
   after the time it was actually held, and writes the further change into the trade (`after`). For HPE that is about
   17 Oct. The review's part 4 lists it by kind of sale. Earlier wording in these notes ("the same length of time
   again") was loose: read it as this.**
4. **Stops passed between check-ins** (part 4 of the review counts them). If common: a light look at prices every half
   hour for holdings whose stop has started, with no screener run and no AI call.
5. **Coins: limits from each coin's own daily movement** instead of one loss limit and gain mark for all (a live trial,
   every second coin; only worth building while coins are being traded).
6. **Scorecard lines the model is shown from 8 trades a group** (`MIN_SAMPLE`): thin; consider 30, as for the notes.
7. **Company figures recorded with each share bought** (profit margin, debt, growth; the report function already has
   them) and the record split by them: a measurement first, as for the 52-week low and the headlines.
8. **What each level sets by itself** (holding time, check-in gap), the stop's distances, the wait for a coin to stay:
   each needs a tag on the buy and a trial. **A small fitted model** scoring a candidate once the shared record holds
   thousands of trades (no new AWS service). The screener scoring itself is the owner's decision (section 7b).
*Housekeeping, any session:*
0c. A sale's story says "chosen by rank" for a share that was the buying-order trial's pick (`sale_detail`: HPE on 12 Oct;
   the buy's own line and the record say it rightly: "bought as the share furthest above its 52-week low"). One line.
0b. **Buying by quantity is a hair off while a market is trading** (seen 12 Oct in the portfolio tests, which use live prices:
   3 shares asked for, 3.00006 bought). The page turns the quantity into dollars at the price it has, then buys at the
   price of that moment, which has moved. Cosmetic; the fix is to buy the quantity asked for at the price of the buy.
   The same thing makes the check "buying by quantity buys exactly that many" fail on and off during US hours.
9. (Done 17 Oct 2026: the pages' polling. See the change log of that day; measure the effect in his usage report.)
9b. (Done 17 Oct 2026: the weekly review's line against an S&P 500 fund since the start, `fund_since_start`.)
10. **Unused functions: nothing was deleted, and nothing is to be deleted without the owner seeing the exact list and saying
    yes to it.** On 12 Oct he first said to go ahead "if you are 100% never used", then stopped the dry run ("i don't
    think its right to delete workers. they must be used via the screeners?!"). What a check of every call in the 455
    days CloudWatch keeps showed: `stockiq-option-7-4-worker` (139) never called; `stockiq-option-3-worker` (5) called on
    4 to 7 Sep 2025 only; **`stockiq-option-3-3-worker` (60) was NOT unused: 50 of them were the old S&P 500 path, called
    about once a month until 11 Sep 2026** (the S&P 500 has used the first 50 `stockiq-option-3-5-worker` since). None of
    the three groups' addresses or names is in any page or script of the site, in the coordinator or in any other
    function's code (385 packages read). Idle functions cost nothing: the recommendation given was to leave them. The
    script that would have deleted the first two groups was never run and was taken out again the same day (it is in
    git history: commit `33588f1`, `check-tools/pending-cleanup/`). Also still there, in use
    until this month: `stockiq-option-7-2-worker-1`, `stockiq-coinspot-predictions-updater`. The local folder
    `website/stocks-backup-before-restore/` (118 MB) can go when he says.
11. Thin the bell script's handling of older copies (any time after 18 Oct 2026; keep "the newer version wins").
12. The report function holds the Finnhub key in its code: move it to the function's settings so the code can go into git.
13. The record's size (the review tool warns above 300 KB of the 400 KB a row can hold): drop `path` from finished
    trades kept in `history`, or store the record compressed.
13b. The screeners' top-10 lines still call the one-year change "YTD" (four writers in `analysis-functions.js`, one in the
    coordinator; the CSV column `YTD_Change_%` too): "1 yr". Words only; do it with the next change to those files.
14. Both GitHub repositories are public (section 11). The personal file in one is the owner's own business ("that youtube
    stuff is mine only focus on the repo for stockiq", 12 Oct): leave it alone and out of these lists.
15. Ideas offered and not built are in the next part ("Ideas offered and not built"); section 11 has the rest of the site.

**Who can use it, and what guards every account:**
- **The practice portfolio by hand is free for every signed-in account.** The AI autopilot (Beta) is for accounts on a paid
  plan, or listed in env `AI_TRADER_USERS` (the owner's account and the deploy test account; "may use it without
  paying"). Decided in the function: `allowed(user)` = `listed(user)` or `plan_of(user) == 'paid'`; `plan_of` reads table
  `stockiq-user-tracking`, item `<email>#registration`: paid = `subscriptionStatus` `active`, or `cancelled` with
  `expiryDate` not yet past; a free trial is `free`; a read that fails is `unknown` (cached 60 seconds). On 11 Oct: 66
  registered accounts, 1 paid (the owner's); one autopilot record besides his (the deploy test account's, off).
- **Without a paid plan:** `get` answers `{allowed: false, locked: 'plan', upgrade}` and no record is made; every other
  action is refused with HTTP 402 and the same pointer; the panel shows `lockedHtml` (what it is, that it is in every paid
  plan, that buying by hand stays free, "See the plans") and its tab a 🔒. `locked: 'unknown'`: "could not be checked,
  refresh in a moment" (HTTP 503 for actions); nobody is paused on an unknown.
- **A plan that ends:** the scheduled run pauses the autopilot (`pause_for_plan`, `pausedWhy: 'plan'`, a line and one
  email); it switches back on by itself when the account is on a paid plan again and its dashboard is opened.
- **Paused after two weeks without a visit** (`seen_now` writes `state.visit` at most every 6 hours; `pause_if_away`,
  `IDLE_DAYS` 14): switched off, a line and one email; back on at the next visit to the dashboard. The bell's question on
  other pages is not a visit. What it holds is neither sold nor watched while paused.
- **A scheduled check-in waits for the settings to settle** (`SETTLE_MINUTES` 10, `settling`; 13 Oct 2026): an account whose
  settings were changed less than 10 minutes before a scheduled run is left for the next run (the log says "settings
  just changed, left for the next run"), and `next_check` forecasts accordingly. The dashboard saves every click, so
  without this a check-in could trade on a setting someone was half-way through changing (it did, once). "Check in
  now" does not wait: that is a request to act on the settings as they are.
- **The schedule** runs every account that is due, up to `RUN_TOGETHER` (4) side by side, and starts no check-in with less
  than `RUN_RESERVE_SECONDS` (100) left; such an account runs at the next slot. This is not a limit on users. It scans
  the whole table page by page. If paying users ever number in the hundreds, give each account its own invocation.
- **A daily limit on AI calls per account:** `AI_CALLS_PER_DAY` (120); past it, buys go by rank and only the fixed rules
  sell. Screener results are shared between accounts for 20 minutes.
- **What the site says:** home page pricing (`index.html` `#pricing`), the dashboard's three plan cards and an FAQ entry
  name the practice portfolio (free) and the AI autopilot (Beta, paid plans). Wording rule: "practice", "fake money", "no
  real trade is placed", "not financial advice", "past screener results have not shown a reliable edge"; never "picks".
- **Still to weigh, and the owner knows:** an AI choosing what to buy for paying users, even with fake money, sits on the
  same unreviewed legal question as the signals (section 11). And the `userId` is whatever the browser sends: someone who
  knows a paying user's email could open that user's autopilot (fake money only).
- **Cost:** a crypto check-in is a full crypto screener run unless a copy under 20 minutes old exists: 54 worker calls
  since 11 Oct 2026 (it was 540), so one user on 30-minute check-ins adds about 80,000 Lambda calls a month, plus up to
  two small AI calls per check-in and at most 8 larger ones a day. What the whole site costs: section 11, "What AWS costs".

### Ideas offered and not built

**Real trades through a broker (asked 18 Oct 2026: "if i had api access to a market to buy for real, would it be possible…
i'm not looking to do this anytime soon"). Answered, not built.** Technically yes: the autopilot decides in one place and
"buys" by writing to the practice portfolio; that step could instead send an order to a broker with an API (Alpaca for US
shares, with a paper account that behaves like the real one; Interactive Brokers for most markets including the ASX). The
work is in what changes with real money: orders that fill at a different price or not at all, the broker's own cash and
holdings as the truth, real fees and exchange rates, holidays, a kill switch and daily limits, the broker key in AWS
Secrets Manager, and a separate function with no public address (today the `userId` is whatever a browser sends). **What
stands in the way is not the code:** the record is losing (51 trades, -1.15% a trade on 17 Oct) and the bar of section 8c is
far from met; offering it to paying users for their own money would need a financial services licence (section 11, "Legal");
for his own account only, with his own broker, the trades are his own (and taxable). **The sensible order, if he ever wants
it:** the bar cleared first; then a broker's paper account (real order handling, no money) beside the practice portfolio;
then a small amount, his account only. Until then the rule at the top of this section stands: nothing here touches real money.
**How to build until then (the owner, 18 Oct 2026: "i wouldn't want to be building the site just for testing and never live.
obviously for testing is in the small chance you do well and then go live"):** build so that a good practice result would
hold with real money, and build nothing that only real money needs. So: costs, fills, trading hours and holidays, prices that
have really traded, the size of holdings against what a market can take, all as real as they can be made (the 0.1% cost, the
3-hour price rule and the market hours are this; a trade must never be counted at a price nobody could have traded at); keep
the deciding apart from the recording of a trade, so that a broker could one day take the recording's place; judge by his bar
above, never by something easier. Not until the bar is cleared: a broker connection, keys, real orders, anything a user
could mistake for real trading.

**The number of holdings as a setting of its own (thought through on 12 Oct 2026 at the owner's question, and built the same day at his word: the settings table in "The autopilot: settings").** He saw
that it buys "say 10 stocks max across the 100,000", that the less risk he picks the more holdings it has, and wondered
about a second slider ("one customer would want to auto trade 50 stocks a day, another 2"). What is so today: the number of
holdings comes only from the risk level (12 / 10 / 8 / 6 / 4), each holding is the budget divided by that number, and a
check-in buys at most 3 (`MAX_BUYS_PER_CHECK`). Replayed on the saved share prices with 2 to 50 holdings under the Careful
and Balanced rules (four years, 101 US shares, costs taken off): **the number of holdings is a matter of how bumpy the ride
is, not of profit.** Fewer, larger holdings did better in that period (2 to 4 holdings: account +137% to +142% against the
fund's +107% at Careful) but not clearly (t 1.3 to 1.8) and with deeper falls (-17% to -21%); 10 to 20 holdings sat a
little behind the fund with shallower falls (-14% to -16%); **30 and 50 could not even be filled**, because of the 3 buys a
check-in, so much of the money sat idle (which is why their falls look small).
- **Recommended, if he wants it:** one optional field, "Number of holdings", left to the level or set by hand, in the same
  "automatic / set by you" pattern as the three pace fields, with the size of a holding shown beside it; and the buys per
  check-in made to follow it (3 cannot fill 50). A larger number also makes the shares of the budget per market finer.
- **Not recommended:** a minimum or maximum number of trades a day. How often it trades already follows from the number
  of holdings, the holding time and the check-in gap; a minimum would force buys that passed no filter. Say the
  consequence in words on the panel instead ("with these settings, about N trades a week").
- **To be honest about when building it:** more holdings means buying further down each screener's ranking (rank 30,
  not rank 8), and the ranking has shown no reliable edge at any depth (section 7b).
- Touches: `clean_settings`, `rules_for` (positions), `MAX_BUYS_PER_CHECK`, `market_slots` and its copy in the panel
  (`autopilot_plan_check.py`), the level table on the panel, `DASHBOARD_GUIDE`.

(A chart of the account and of the autopilot's result over time was built on 12 Oct 2026: "What the owner sees".) A weekly summary email even when
there is no review; a coin yardstick (Bitcoin) for coin trades in the breakdown; watching prices
between check-ins (a stop can only act at a check-in); trials that cover the owner's settings
(holding time, how often it checks in); selling part of a holding; sorting the tables; recording
which report a manual buy came from; dividends; per-user cost limits before opening it up;
public holidays for each market. **Separate pots** (offered 11 Oct, when the owner wondered about
"a better way to manage it all" after asking what happens on switching screeners): instead of one
budget across everything ticked, a few named pots, each with its own budget, screeners and pace
(say "Coins, quick" and "US shares, steady"), shown and judged separately. It would make a switch
of screeners a visible choice instead of a side effect, and show which kind of trading earns its
keep. Not asked for yet; it is a rework of the settings, the allowance and the panel. (The share
of the budget per market, built the same day, covers the "how much goes where" half of this; a
separate pace and record per market is the half that is not built.) Also not built: letting the
automatic split follow results (more to the market whose trades have done better); it needs far
more finished trades than there are, and would chase noise before then.

## 9. Pitfalls learned the hard way

- **"It does not show for me" (the notification bell, 11 Oct 2026): six rounds, one cause found late.** The owner asked
  for the autopilot's trades in the bell on every page. He then reported, round after round, that nothing showed ("no
  change", "something is overriding your changes"), while every check here passed. What was wrong, in the order found:
  1. *The trades sat out of sight.* The first forms put them as a group above or below each page's own report list,
     whichever had the newest item; with a report newer than the last trade they were under seven reports in a 400px
     list. Checks with a made-up account and no reports had passed. Fixed by one list, newest first.
  2. *Browsers kept old copies.* The site let a browser keep a page for an hour and a script for a day, so a fix was live
     and unseen. Fixed at the source (section 5, step 8: pages are asked for again every time, scripts kept five minutes).
  3. *An old copy outran the new one.* An old `theme.js` in a browser's store asked for the first version of the bell's
     script, which ran before the current one arrived; the current one then stood down ("if I am already here, do
     nothing"). Fixed: the newer version always takes over.
  4. **The one that fits everything he saw: the script was asked for at `/autopilot-bell.js`.** That address exists only
     when the site is at the top of its address. Served from a folder (a local preview of `~/VSCODE/website`), it is a
     404, the script never runs, and nothing on the page says so. The dashboard had worked at first because its script
     tag was relative, and stopped when it was given the same absolute address as the other pages. With relative
     addresses he confirmed at once that it worked.
  **Lessons, all learned the expensive way:**
  - **Ask where he is looking at the site, first** (stockiq.tech, a local preview, a phone, which browser), and reproduce
    *that*. A check in a clean browser on stockiq.tech proves the site, not what he sees.
  - **Reproduce with the real account's data** (`live_bell_check.js`, `REAL_USER`, read-only) before saying a thing works;
    do not say "fixed" on the strength of a made-up account.
  - **Never address the site's own files as "/file"** in a script or a loader line: relative to the page, or to the
    script itself (`document.currentScript.src`).
  - A script that may be loaded twice must let the newer version win, and its author must think through what an older
    copy still on the page will do.
  - When a deployed change "does not show": `curl -sI` the plain address (no `?something`) for `cache-control` and compare
    the body with the local file; that settles in a minute whether the site or the viewer is behind.
  - Change one thing per round and say what was and was not reproduced. Four deploys chasing guesses cost more than one
    question would have.
- **Template drift:** in Sep 2026 the live stock pages had a newer footer than the generator
  template, so running the generator would have reverted all 3,467 footers. Before running
  `generate-stock-pages.py` after template edits, test it on a copy of `stocks/` and diff.
- **`--size-only` S3 sync** skipped same-size edits (1,051 stale live pages). Now size + mtime.
- **Yahoo throttling:** `.info` lookups return false 404s ("Quote not found" for real tickers
  like BK) when too parallel. Use 2 threads. Failed lookups are cached for 1 day; fundamentals
  refresh weekly for stocks ≥ $5B, monthly otherwise; market cap is recomputed daily from
  cached shares × latest close × FX.
- **Currency units:** Yahoo prices for `.L` (GBp), `.JO` (ZAc), `.TA` (ILA) are in minor units
  (÷100), but Yahoo's `marketCap` is already in the major unit. ETFs have no market cap → noindex.
- `Sync_stock_to_news.py` re-adds ~3,000 articles to news.html. Harmless: the next deploy's
  `finalize_news_html.py` trims them. `check_news_sync.py` only compares within the time window
  news.html still covers, so do not "fix" its window logic back.
- `.kiro/steering/*` are real files now (the `.amazonq` mirror was removed Sep 2026).
  `stockiq/CLAUDE.md` (added 9 Oct 2026) only points Claude Code at these same files; keep the
  content here, not in `CLAUDE.md`. If a steering file is added or renamed, update its list.
- `website/.s3-excludes` is **not used** by any script; the deploy has its own include and
  exclude rules. Leftover local files that are never uploaded: `sitemap copy.xml`,
  `sitemap.xml.backup`, `sitemap_stocks.xml`, `blog.html.backup`, `Table.csv`,
  `company_names_dict.txt`, `robots-http.txt`, `*.py`.
- Running `generate-stock-pages.py` rewrites all 3,467 pages, so the next deploy uploads all
  of them (~110 MB). That's fine, just slower.
- **generate-stock-pages.py wipes news on pages without markers:** If stock pages were created before `<!-- NEWS_SECTION_START/END -->` markers existed, regenerating wipes their news silently. Fixed Oct 2026 — script now has a fallback to extract news from old-format pages, plus a pre-run count showing how many pages have news. If running after a long gap, check that count before and after. Always run `sync_news_to_stock_pages.py` after regenerating if news is lost.
- **Generator template reverted silently (found 9 Oct 2026):** the Oct 2 "Auto-update" commit (7e14c8f)
  rewrote `generate-stock-pages.py` back to the pre-Sep 25 template (no ANALYSIS markers, fake
  `NewsArticle` schema, no GA4, hardcoded `index, follow`). A regeneration on Oct 9 then rebuilt all
  3,467 pages with it and the deploy uploaded them, making every page indexable and removing every
  snapshot. Fixed by restoring the Sep 25 version (commit 2485162) plus the Oct 9 news-preservation
  fixes. **After ANY regeneration, run `update_stock_analysis.py`** (it sets index/noindex, snapshots and
  `indexable_stocks.txt`; with no ANALYSIS markers it silently writes nothing). **Before every deploy,
  sanity check:** `grep -l 'content="index, follow"' ../website/stocks/*.html | wc -l` should be ~950, not 3,467,
  and `wc -l indexable_stocks.txt` should be ~950. Also review `git diff --stat` on scripts after the
  "Auto-update" commits; they bundle everything and hide reverts.
- **The same Oct 2 commit also reverted `deploy-to-s3.sh`** (found 9 Oct 2026): `DRY_RUN` was gone
  (a "dry run" did a real deploy), stock pages synced with `--size-only` again, and only `stockiq/`
  was pushed to GitHub. Restored from commit 2485162 plus the `$PYTHON` variable. **Before trusting
  `DRY_RUN=true`, check the script still supports it:** `grep -c DRY_RUN deploy-to-s3.sh` must be > 0,
  and the output must contain `(dryrun)` lines and no `upload:` lines. That commit touched 24 scripts
  (`git diff --stat 2485162 7e14c8f`). All were compared with their Sep 25 versions on 9 Oct: the
  rest only had path changes, except `check_news_sync.py` (window logic lost; restored) and
  `update_sitemap.py` / `generate_sitemap.py` (rewritten in Oct on purpose; verified working).
- **News script wiped news on the current template (fixed 9 Oct 2026):** `update_stock_news.py`
  (`update_stock_page`) removed the page's NEWS section and then looked for a "features grid" to insert
  before. That grid only exists in the pre-Sep 25 template, so on current pages a new article **deleted the
  news section and its markers** and still returned success. This is why pages kept losing their markers and
  why "news in the sidebar but not on the stock page" kept happening. It now replaces the content between the
  NEWS markers in place, falls back to inserting before `RELATED_SECTION_START`, and returns False (page
  untouched) if neither exists. `sync_news_to_stock_pages.py` had the same fallback and is fixed too. The
  "History" heading is now only written when there is an older article under it (448 pages had an empty one;
  cleaned up). **Any script that writes into stock pages must anchor on the section markers, never on other
  template HTML.**
- If stock pages show old data dates, check `update_stock_analysis.py` is still in `deploy-to-s3.sh`
  (it went missing once) and look for a large "No price data" count in `~/stockiq-daily.log`.
- **Yahoo rate-limits this machine** (HTTP 429) after a few hundred chart requests. On 10 Oct 2026
  manual symbol checks caused the daily run's snapshot step to get no prices for 2,041 stocks. It
  kept yesterday's snapshots and de-indexed nothing; a re-run an hour later was clean.
- **A count of fingerprints is not a count of programs (11 Oct 2026).** The first audit of the screener workers said the
  Russell groups had "100 and 200 different versions" and planned a large clean-up around that. They were two programs
  zipped 300 times: a zip's `CodeSha256` changes with the dates of the files inside it. Compare what is inside
  (`check-tools/workers.py --contents`) before believing that functions differ.
- **"It will move a little" was a guess; measure (11 Oct 2026).** These notes said one RSI for all screeners would move US
  scores "a little". Replayed on saved prices it changed a third of the signal labels. `workers/prove.py` exists so that
  the size of a scoring change is known before it is deployed: run it and read it, whatever the change looks like.
- **A deploy by hand commits whatever is lying in both repos (11 Oct 2026).** A `./deploy-to-s3.sh` was run on a Sunday
  evening while a session was mid-task; its git step swept seven unfinished files into an "Auto-update" commit and
  pushed them (harmless that time). It also moved the 23-hour push marker. Another reason to commit finished stages
  promptly, and to check `git log` for an "Auto-update" when a file is unexpectedly already committed.
- **Lambda code is not in git** (`lambda-sync/` is a gitignored mirror; the one exception since 11 Oct 2026 is the
  share-screener workers' code, which lives in `stockiq/workers/`). The only history of a
  Lambda is whatever zip you keep before changing it.
- A worker address in the crypto orchestrator had a one-character typo for months and returned
  403; its coins were silently missing. Failed worker calls are easy to miss: count results.
- A stray `test-news-layout.html` was publicly live on S3 (deleted 25 Sep 2026). Check S3 for files with no local
  copy occasionally (`aws s3api list-objects-v2 --delimiter /`).

## 10. Working rules for AI assistants

- The owner (Dave) built this with AI help, works in **Kiro**, and is not going to read code.
  Explain in plain terms what will change and what you found. Lead with the result.
- **Correct the owner when he is wrong, and say so plainly** (his standing instruction, 17 Oct 2026: "ignore me if it makes
  no sense and is fine as is. same for everything i ask your in control here to make a good site and correct me when wrong
  ... no issue with hearing i'm wrong and you suggesting another option or skipping it completely"). For every request:
  is it a good idea? If not, say why and do the better thing, or skip it and say that it was skipped. When he points at two
  things that look alike, check whether they are a real duplicate or two different things, and if they are different,
  make the difference plain on the page (the two "needs" boxes, section 8c, "Two boxes that look alike").
- **Verify, don't assume, and don't trust these docs blindly.** On 9 Oct 2026 the docs said
  `DRY_RUN=true` worked; the script had lost it and a "dry run" deployed for real. Before relying
  on a script feature or a claim here, check the code. When something is fixed, say how it was
  checked; when something could not be tested (logged-in screens, a real phone), say that too.
- **Test with real data, end to end.** Spot checks missed real bugs repeatedly on 9–10 Oct
  (missing label codes, stocks never sent to a worker, a column that was always 0, a worker
  address with a typo). When asked to "check", run the whole thing (section 8b) and read the
  output. List every code, field or symbol a component can produce before mapping it.
- **The share-screener workers are changed in `stockiq/workers/`, never in the AWS console and never in `lambda-sync/`**:
  edit `stock_worker.py`, run `workers/prove.py` and read every difference, commit, deploy with `workers/deploy.py` through a
  packaged script, one small group first (section 8b, "The worker groups").
- **Before editing a Lambda:** download the live code and diff it with `lambda-sync/` (they must
  match). Lambda code is not in git, so keep the previous zip in `~/VSCODE/backup/` with a clear
  name as the rollback. After deploying, smoke-test the live function. If the daily run's Lambda
  sync is about to run, deploy straight after editing `lambda-sync/` so it does not overwrite you.
- **The daily deploy starts at 11:00** (Mon–Sat) and publishes and commits whatever is in
  `website/`. Near that time, stage edits in a scratch folder and copy them in only when
  verified. If the job's own files (news.html, news.js, sitemap.xml) are dirty, commit only your
  files by name, never `git add -A`.
- **Production deploys go through a packaged script.** Since 10 Oct 2026 the session's safety
  check refuses a direct Lambda or S3 deploy; the owner added one permission rule,
  `Bash(bash /Users/dave/VSCODE/stockiq/check-tools/pending-*/deploy.sh)`. So: stage the change in
  `check-tools/pending-<name>/` with a `deploy.sh`, run its dry run, then run it with exactly that
  command form. The full routine is in section 8c ("How to work on it"). If the rule is ever
  missing, only the owner can add it; say so plainly instead of trying another route.
- **When two sessions are in the repository at once, name the paths in the commit itself**: `git commit -m "…" -- <paths>`
  (and look at `git status --short` first). A plain `git commit` commits everything that is staged, whoever staged it, and
  an edit to a notes file is made on top of whatever another session has in it uncommitted. On 11 Oct 2026 commit
  `a0be314` (trading signals) took along the other session's notes in progress and its removal of
  `check-tools/pending-reports/`; nothing was lost, but that work sits under the wrong message. Better still: one session
  at a time, or tell the running one what changed.
- **Commit and push in steps** (owner, 10 Oct: "so long as you commit to github in steps and can
  track changes"). His sessions can stop mid-task when usage runs out: push each finished stage,
  marked "work in progress, not live yet" until it is deployed, and say what is live and what is
  only committed.
- Ask the owner before an S3 upload or GitHub push and show the `DRY_RUN=true` list. (On 9–10
  Oct the owner approved deploys as each fix was ready; a few hand-edited files can go up with
  `aws s3 cp` plus a CloudFront invalidation of just those paths, which avoids a full pipeline run.)
- No extra backups before changes: the daily backups in `~/VSCODE/backup/` (30 days, both
  folders incl. `stocks/`) plus GitHub are enough. The one exception is the Lambda rollback zip:
  **the daily backup leaves Lambda code out** (section 3), so the zip kept before a change is the only way back.
- Change generators and templates, not generated pages (section 4). Any script that writes into
  stock pages must anchor on the section markers, never on other template HTML.
- **Describe, don't advise** (owner's instruction; StockIQ holds no financial services licence).
  On pages, in emails, in product output and in the AI chat: no "you should buy/sell", "picks",
  "winning stocks", "recommendations", price targets or predictions presented as StockIQ's view.
  Say "scores", "signals", "screener rankings", "what the data shows". The AI chat prompt
  (`stockiq-ai-chat`) must keep its rule never to give buy/sell/hold calls, price targets or
  picks. Keep the footer disclaimer and the no-licence statement (terms.html, about.html).
  Educational text about how technical analysis works is fine. Details: section 8b.
- Verify claims against code or data before putting them on public pages. Don't promise what
  doesn't exist (the giveaway and "daily picks at 6 AM" were removed for that reason).
- Commit with a message that says what changed and why. The "Auto-update" commits bundle
  everything; one of them hid a revert of 24 scripts (section 9).
- Don't hit Yahoo in bulk from this machine (section 8b). Use `stockiq-price-proxy` or go slowly.
- **`analysis.html`, `analysis-functions.js`, `index.html` and `dashboard.html` are very large: never read them whole.**
  Search for what is needed (the owner's instruction for `analysis.html`), read the few lines around a match, edit by
  exact replacement and confirm with a diff or a line count that nothing else changed.
- **When the owner says a change does not show, ask where he is looking at the site and reproduce that** before changing
  anything; never address the site's own files as "/file" (section 9, the bell).
- **Both GitHub repositories are public** (checked 11 Oct 2026): nothing private belongs in a commit, in a commit message
  or in these notes: no keys, no customer addresses, nothing personal. An account is "the owner's account" here, not
  an address.

## 11. Open items and optimisation ideas

Needs the owner's decision or more work (nothing here is fixed):
- **Both GitHub repositories are public** (`davedewit/stockiq` and `davedewit/stockiq-website`; checked without signing
  in, 11 Oct 2026). Two things follow that only the owner can decide. (1) `stockiq/youtube-channel-plan.md` is a
  **personal** plan that has nothing to do with the site and can be read by anyone; taking it out of the repo does not
  take it out of the history, which needs a rewrite or the repo made private. (2) These notes describe how the site is
  built, including its weak points (the `userId` is whatever the browser sends; the analysis Lambdas are open URLs; the
  AWS account number and function addresses). Making `stockiq` private would cost nothing the site needs: only the
  deploy's `git push` uses it. He was told at the end of the session of 11 Oct; nothing was changed.
- **Practice portfolio and AI autopilot: what is open** is listed in section 8c, "Start here when
  resuming" (Monday's first trades across markets, the first progress report at 20 finished trades,
  a trial of buying shares by distance above the 52-week low if the record supports it, the
  screener scoring left untouched after the factor study of section 7b).
- **What AWS costs (measured 11 Oct 2026; the owner wants to stay inside the free allowances).** The bill for 1-11 Oct
  was **$0.34 in all** (S3 $0.17, DynamoDB $0.12, Lambda $0.00). Lambda's free allowance each month is one million calls
  and 400,000 GB-seconds. Before this week the account made about 6,000 calls a day; the old crypto updater alone used
  about 200,000 GB-seconds a month. After the rebuilds: the crypto job's computing time fell by two thirds (about 70,000
  GB-seconds a month for the crypto workers, the orchestrator, the autopilot and the coordinator together), but its
  one-call-per-coin design made about 0.8 million calls a month; ten coins a call (section 8b "Crypto") brought that to
  about 80,000. **What runs by itself:** the crypto top-10 history every 30 minutes (54 calls a run), the autopilot every
  30 minutes (real work only when an account is due), the daily deploy from the owner's Mac. Raising a function's
  memory does not raise its cost when the work is processor work (it finishes proportionally sooner): the signals
  functions went from 128 to 512 and 1024 MB for that reason. Not on the AWS bill: OpenAI (the daily news summaries, the
  chat, the autopilot's calls: at most about $2 a month for a heavy autopilot user). **To check:** `aws budgets
  describe-budget --account-id 114366766218 --budget-name stockiq-monthly` (free; never `aws ce`, which charges $0.01 a
  question: top of this file), and `aws cloudwatch get-metric-statistics --namespace
  AWS/Lambda --metric-name Invocations --period 86400 --statistics Sum …` for calls a day (free). If the calls ever
  near a million a month again: the crypto history could run hourly (the schedule, plus the 65- and 100-minute limits in
  the orchestrator).
  **Measured again on 12 Oct 2026 (10:00 UTC, the 24 hours before):** 55,430 calls. 13,246 were the sidebar's ticker (`ticker-data-fetcher`), 13,300 the four movers lists (gainers, losers, most active, trending), 8,500 the seven market
  widgets, 2,300 the usage tracker, 2,200 the price proxy: **the pages' own polling while a tab is open**, busiest when the owner had the dashboard open. The crypto workers were 11,500 that day only because the old one-call-per-coin
  design ran until the evening of 11 Oct; they are about 2,600 a day now. A tab left open around the clock is about a million calls a month by itself. Past the free million, calls cost 20 cents a million, so the money is cents; the
  computing time stayed far inside its allowance (the ticker used about 21,600 seconds that day). To bring it down: "Start here when resuming", improvements, item 9.
- **Legal.** The business is "StockIQ", online-only, no physical address, **no financial services
  licence**; billing is in USD ($4.99 / $14.99 / $49.99 per month, confirmed on the live Stripe
  prices). The terms, About page, pricing section and FAQ say all of this, and the product
  wording was neutralised (section 8b). Whether issuing automated signals to paying users
  without a licence is acceptable under Australian law is a question for a lawyer; the owner
  knows and has not had it reviewed. The owner trades as an individual (no company structure).
- **Screener reports, small things left after the currency fix of 11 Oct 2026** (section 8b, "Dashboard performance tracker"):
  the page pads a FTSE price to 8 characters, so a four-figure pence price ("1,835.00p") sits one place to the right of the
  others; equal scores are ordered differently by the page and by the coordinator, so the two top 10s can differ in a
  tied place; the Nikkei background report has no company names (the page's has); the single-stock result carries no
  currency field (the side-by-side table reads the price from the report's own text).
- **Share-screener workers** (section 8b, "The worker groups"): one code base since 11 Oct 2026. Open: no real company figures
  (one file to change now, once there is a source); the two fixes for Yahoo's oddities to be seen live (FTSE on a morning
  after a session, ASX during its hours); the oddities left on purpose (`MODERATE_SELL`, `STRONG_DOWN`); Russell 1000/2000
  lists not refreshed (7 and 27 of their symbols no longer have prices); ASX 300 approximate; the 204 unused worker
  functions to delete when the owner agrees.
- **Crypto scoring** (section 8b, "How a coin is scored"): the single-coin worker `stockiq-option-7-2-worker-1` is no longer used (12 Oct 2026: the
  single-stock report function reports on a coin); the score mixes opposite ideas and has never been tested for
  coins; whole-number scores tie often. A finer score, or a test of it, needs saved coin prices.
- **Crypto track record (review from early Nov 2026).** Entries from before 11:52 UTC on 11 Oct 2026 were ranked without
  MACD (section 8b): measure the two periods apart. The entry log (section 8b "Crypto") started
  10 Oct 2026. Once it holds a few hundred entries, compare each coin's price 24 hours and 7 days
  after entering the top 10 with the average coin over the same days. Leftovers that can be
  deleted when the owner agrees: Lambda `stockiq-coinspot-predictions-updater` (no longer
  triggered) and the old-format rows in both crypto tables.
- **UK FTSE screener showed prices one trading day old** (seen 10 Oct: Yahoo's latest daily bar empty for London stocks,
  IMB.L 2,614 in the report, 2,662 actual). Fixed in the one worker file on 11 Oct 2026 (the latest session is taken from the
  quote); **not yet seen live**, because Yahoo had filled the bar in by then. The pence shown as pounds is the item above.
- **Fake-money test of the screeners (owner's idea, 10 Oct 2026; first results in).** Tool:
  `stockiq/check-tools/paper-test/` (`python3 fetch.py && python3 backtest.py dow30|sp100 [start date]`).
  It replays the worker's own scoring code over daily prices (the screeners use nothing else), takes
  each day's top 10 and compares what they did next with the whole list and with SPY; it also runs
  a $10,000 paper account re-invested in the top 10 weekly. The replay's top 10 for 9 Oct matched
  the live Dow 30 and S&P 100 reports exactly. Results, 3 Jan 2023 – 9 Oct 2026 (946 trading days):
  - **Dow 30: no edge.** Top 10 +16.8% a year, whole list +18.4%, bottom 10 +19.3%, SPY +21.0%.
    No reliable difference at 1 day, 1 week, 1 month or 3 months. With 0.1% cost per trade: +10.3%.
  - **S&P 100: ahead, but not reliably.** Top 10 +43% a year (no costs; +31% with 0.1% costs)
    against +25% for the whole list; bottom 10 +16%. The gap is inside the margin of error at 1 week
    and longer, most of it came in 2026, and it disappears (+0.02% a week) when seven chip / AI
    stocks are left out (SNDK, MU, AMD, ANET, NVDA, PLTR, DELL). The score is a momentum score, and
    momentum paid in those names in this period. The list is today's membership, which flatters it.
  - The top 10 changes a lot: the account trades 57–84 times its own value a year.
  - **Do not publish these numbers as a track record.** The fair test is forward: the lists were
    frozen on 10 Oct 2026 (`frozen_lists.txt`); re-run with a start date of 2026-10-12 or later
    (suggested: early Dec 2026 and early Jan 2027). No scheduled job is needed for this, because the
    replay gives exactly what a daily automatic paper-trader would have recorded.
  - Not covered: the larger US lists (one price download per stock; Yahoo blocks this machine after
    a few hundred), ASX / FTSE / Nikkei (different worker code; same method would work), crypto
    (the entry log in section 8b does this job from 10 Oct). The practice portfolio and autopilot
    built the same day (section 8c) are the live counterpart: the autopilot's finished trades are a
    forward test of buying from the top of the rankings, with its own record on the dashboard.
- **Page score vs app score.** Same model, different inputs (once 71 vs 47 for AAPL): the page uses the previous
  close and Yahoo's figures, the app the live price and Finnhub's. Three of its causes were dealt with on 11 Oct 2026
  (section 7, "The single-stock report"): the trend factor is graded, part-day volume is left out, and figures Finnhub
  lacks come from the pages' own Yahoo cache. What is left: MACD (+8 or -8 on its sign) and RSI still score in steps.
- **Single-stock report, left open on 11 Oct 2026** (section 7): its code cannot go into git while the Finnhub key is
  written in it (move the key to the function's settings first; both repositories are public); company figures only for
  the 3,333 stocks the site's daily job keeps them for, up to a month old; the analysis page in a browser and on a real
  phone was not looked at; the first run of `publish_company_figures.py` inside the daily deploy (12 Oct) built the
  file and **could not upload it**: launchd's PATH has no Homebrew, so "aws" was not found. Fixed the same day (the full
  path, as `deploy-to-s3.sh` uses); run by hand on a bare PATH at 10:55 UTC it uploaded the file. Look for "Company
  figures" in `~/stockiq-daily.log` without a warning after it.
- **Dashboard plan cards** (the line "AI autopilot for your practice portfolio (fake money)" added on 11 Oct is real and the same on all three plans) list features that are not verified to differ by plan ("Advanced
  screening & alerts", "Portfolio tracking", "White-label options", "Dedicated support"), while
  the FAQ says all plans get the same features. Old accounts carry legacy limits (a cancelled
  Starter at 50/day, the owner's Pro at 200/day); new purchases get 15 / 50 / unlimited. One
  `@dewit.com.au` test account has a limit of 20, which is why a "19/20 today" badge can appear.
- **The banners, the usage badge and the sticky buttons: mapped on 13 Oct 2026, not changed.** The owner: "it was incredibly
  complicated… i think it was done very bad - but does seem to work". It works, and it is the same thing built several
  times over. **Read this before touching any of it.**
  - **Three kinds of visitor, told apart in the browser:** anonymous (no `userId` in `localStorage`), signed in and not
    paying (a trial, or a trial that has run out), paying. "Paying" is a cached note, `localStorage`
    `userPaidStatus_<address>` = `paid` / `unpaid`, written at sign-in (`auth.js`, only ever `paid`), by
    `analysis-functions.js` (which then **reloads the page** if it finds the visitor has paid) and by `dashboard.html`.
    Every page reads the note in its `<head>` to lay itself out before anything is drawn. A paying visitor whose note
    is missing sees the unpaid banner until one of those pages has put it right.
  - **What each sees.** *The strip across the top* (desktop only; `styles.css` hides it up to 768px): anonymous "Free
    3-day trial: 15 analyses, no credit card needed", signed in and not paying "Plans from $4.99/month: more analyses a
    day, and the AI autopilot (Beta) for your practice portfolio" (since 13 Oct 2026; the stock pages keep the older
    two sentences until they are next regenerated: the template has the new ones),
    paying none (the page moves up 41px: `--nav-top`, `--body-padding`, `--mobile-menu-top`, `--quick-panel-top`,
    `--news-panel-top`). It is `#promo-banner` in `index.html`, `analysis.html`, `dashboard.html` and `signup.html`,
    each with its own copy of the code, and a different element, `#sticky-banner`, with a third wording of the same
    code in the stock pages' template. *The yellow "LIMITED TIME: Get 15 free analyses" bar* (`#limited-time-banner`):
    home page, anonymous, desktop only; it says what the strip 250px above it says, and the offer is not limited in
    time. *The usage badge* (`#trial-status-display`, top right under the header, every visitor, every page that loads
    `auth.js`): "1/1 Analyses remaining today", "3/5 today (resets 00:00 UTC) • Trial: 2d 4h", "Trial expired -
    Upgrade", "Unlimited", "12/15 today • Subscription: 20d 3h" (`getStockAnalysisStatus` in `auth.js`). *After the
    free uses are gone:* anonymous: a pop-up on the analysis page once 30% of it is scrolled ("You've Used Your Free
    Daily Analysis!… 5 Free Reports per day"), then a round "🚀 Start 3-Day Free Trial" button (`#sticky-register-btn`;
    bottom left on the home page, bottom right on the analysis page; remembered as `showStickyRegister`); signed in
    with none left: "🚀 Upgrade Plan" (`#sticky-upgrade-btn`, bottom right).
  - **Why it is hard to work on:** the badge is created in four places with four sets of positions and styles
    (`displayTrialStatus` in `auth.js`; inline in `index.html`; in `analysis-functions.js`; `dashboard.html`, which
    defines a second `displayTrialStatus` over the first), and faded on scroll by a separate handler on each page; the
    sticky buttons in three and two places; the strip's layout sums in every page's head. A change to one copy leaves
    the others as they were.
  - **What looks wrong (seen in pictures of the live site as each kind of visitor, desktop and phone):** the badge floats
    over content (the corner of the search panel on a desktop, the index cards on a phone, the company name on a
    stock page); three different counts are shown to one anonymous visitor ("15 free analyses", "5 Free Reports per
    day", "1/1 Analyses remaining today"); on a phone the green sidebar button and the blue chat button sit on top of
    each other over the text, with the trial button as a third; a phone visitor never sees the sign-up strip at all.
    **`auth.js` also has the owner's own address written into it** (a rule for the "Unlimited" wording), in a public
    file of a public repository.
  - **Done the same day at his word ("if you want to improve the whole thing go ahead. but make it easy so we can revert
    back"):** the badge is a chip in the header bar, the round buttons sit in one corner, the yellow bar is gone
    (section 8, "The visitor's usage count is a chip inside the header bar", with the way back), and after he had
    looked at it ("the updates so far look great… then fix it up please") the duplicate code behind it went too.
    **What is still built more than once, and why it was left:** the dashboard's own `displayTrialStatus` (it also
    fills in the plan section: needs a real paying account to check); the top strip's code in four pages and the
    stock template (it has to run before the page is drawn, so it cannot move into a late script; its two wordings
    are his to decide); the anonymous pop-up, which exists in both `auth.js` and `analysis-functions.js`; a few lines
    in `blog.html`, `news.html` and the stock pages that fade the old badge on scroll (they find nothing and do
    nothing). **Also open:** the three floating round things on a phone (the green sidebar button, the blue chat
    button, the round trial button: each is where such buttons usually are; left as they are); his address in
    `auth.js`; the home page's own claims ("Institutional-Grade Tools", "600+ parallel AWS Lambda workers"), which
    are his wording to decide.
- **Mobile:** the owner reports the page zooms when tapping the AI chat input. The input is
  already 16px; cause not found. Need the phone model and browser to chase it. One candidate is
  the fixed 500px window height when the keyboard opens.
- **AI chat rate limit** is keyed on a browser-generated anonymous ID, so clearing site data
  resets it; the Lambda also looks up paid status from the `userId` the browser sends.
- **Email signup:** the endpoint is public (a bot could flood signups and notification emails),
  the Lambda has no CloudWatch log group, and nothing is sent to subscribers yet.
- **The site's wording (rewritten 13 Oct 2026; section 13): what it now says, so that it stays true.** The numbers on the
  home page are each checkable and must be changed with what they count: **27** screeners (15 until 13 Oct 2026, when twelve were added and the last "Coming Soon" button went; the table in section 8b),
  **1,800+** stocks in the largest (Russell 2000: 1,829), **540** coins, **$100,000** practice money; the FAQ says "more
  than 700 small programs working side by side" (723 worker functions are called by the site). The home page's cards
  and the About page list what the site does: add a card and a line when something is added. Gone, and not to come
  back: "institutional-grade", "professional-grade", "real-time", "2000+ stocks in seconds", "15+ indicators",
  "AI-generated signals", "pattern recognition", any table against named competitors. The FAQ's first two answers
  are also in its structured data (`FAQPage`), and `investment-research-tools.html` has four such pairs: **change the
  visible answer and the structured one together.** Still as they were: the guides' own body text (general education, not
  claims about StockIQ). `analysis.html` lists six markets as "Coming Soon" since 13 Oct 2026 (Euro Stoxx 50, Sweden, China, Taiwan, New Zealand, Mexico): the twelve it had before are all built.
- Guides are ~800 words of definitions with no worked examples.
- `uniqueSymbolsCount` constants in `saveAnalysisToHistory` (`analysis-functions.js`) still use
  the old list sizes (bookkeeping only).
- News `data-timestamp` values on stock pages get bumped past the article date (e.g. 0006.HK
  showed 16 Sep for a 10 Sep article). This inflates sitemap lastmod; cause not found (look in
  `update_stock_news.py`). Also seen 10 Oct: a page with one article sometimes ends with one
  article after a new one arrives (the old one is not carried into History); counts never drop.
- `website/stocks-backup-before-restore/` (118 MB, created 9 Oct, gitignored, not uploaded) can
  be deleted. Three rollback zips `~/VSCODE/backup/*_before_neutral_wording_20261009.zip` hold the
  pre-rewording code of the report Lambda, the coordinator and the crypto orchestrator.

Ideas:
- Review Search Console around 6 Nov 2026 (six weeks after 25 Sep): impressions and clicks on
  the ~957 indexed pages; consider the $2B threshold if they perform.
- Backlinks remain the biggest lever (see `backlinks-progress.md`).
- Link to indexed stock pages from index.html, the guides and analysis results (internal links).
- Home page market widgets are filled in by JavaScript; since 18 Oct 2026 a crawler sees a dash in the four index cards and the
  site's spinner in the side panel, not "Loading...". Writing the last close into the cards daily would give it figures.
- "People also watch" Fix 1 in `future-work.md`. India (BSE Sensex) is the next screener
  (`add-new-screener.md`). Price alerts are not built (`roadmap-to-9.md`).
- `fix_amazonq_chat.sh` is obsolete (Amazon Q is not used).
- `update_news.py` `MAX_BLOG_ARTICLES` stays commented out on purpose. Trimming is done by
  `finalize_news_html.py` with separate stock/general limits.

## 12. Quick checks

```bash
cd /Users/dave/VSCODE/stockiq
python3 check_news_sync.py                                   # news sync + coverage
python3 update_stock_analysis.py AAPL 7203.T --dry-run       # snapshot logic without writing
grep -c DRY_RUN deploy-to-s3.sh                              # must be > 0 before trusting a dry run
DRY_RUN=true ./deploy-to-s3.sh                               # prints (dryrun) lines; no "upload:" without it
curl -s https://stockiq.tech/sitemap.xml | grep -c '<loc>\|:loc>'   # live sitemap size (~975)
```

**Before every deploy** (after any regeneration these catch a broken template):
```bash
grep -l 'content="index, follow"' ../website/stocks/*.html | wc -l   # ~950-960, never 3,467
wc -l indexable_stocks.txt                                           # same number, never ~0
grep -l 'ANALYSIS_SECTION_START' ../website/stocks/*.html | wc -l    # 3,467
grep -l 'Read full article' ../website/stocks/*.html | wc -l         # ~3,150; should not fall
```

**After the daily run** (`~/stockiq-daily.log`, cleared each run):
```bash
grep -a -E "Pages written|Indexable|No price data|Sync complete|pushed|could not|failed|All done" ~/stockiq-daily.log
```
`node check-tools/news_sidebar_test.js` (read-only) says whether the home page's Market News list would show the newest
articles of the local `news.js`; give it a downloaded copy of the live file to check the site.
A large "No price data" number means Yahoo rate-limited this machine: nothing is de-indexed
(yesterday's snapshot is kept); re-run `python3 update_stock_analysis.py` later, then
`./deploy-to-s3.sh`.

**Upload a few hand-edited files without a full deploy:**
```bash
cd /Users/dave/VSCODE/website
aws s3 cp faq.html s3://stockiq-final-websitebucket-vqekic7enf9h/faq.html \
  --cache-control "public, max-age=0, s-maxage=3600, must-revalidate" --content-type "text/html; charset=utf-8" --profile default --region us-east-1
aws cloudfront create-invalidation --distribution-id EHXV50CPHY07R --paths "/faq.html" --profile default --region us-east-1
```
(`*.js`: `--cache-control "public, max-age=300, s-maxage=86400" --content-type "application/javascript"`. These are the values of
section 5, step 8: a page uploaded with the old "max-age=3600" would again be kept by browsers for an hour.)

**Test a template change safely** (before running `generate-stock-pages.py` for real):
```bash
T=$(mktemp -d); cp -R ../website/stocks $T/stocks; cp -R $T/stocks $T/orig
sed "s#/Users/dave/VSCODE/website/stocks\"#$T/stocks\"#" generate-stock-pages.py > $T/gen.py
python3 $T/gen.py && diff -r $T/orig $T/stocks | head -100    # check only intended lines change
```
Also check that every page's NEWS and RELATED sections are byte-identical before and after,
then run `update_stock_analysis.py` (it sets index/noindex and the snapshots).

**Screenshot a page** (headless Chrome; use the live URL, local files hang):
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
  --window-size=1300,2200 --virtual-time-budget=8000 --screenshot=/tmp/page.png https://stockiq.tech/stocks/AAPL.html
```
Run one at a time with a time limit; a tall capture can be sliced with `sips -c H W --cropOffset Y 1`.
Narrow window sizes look cut off in headless mode even for unchanged pages; that's a headless
quirk, not a layout bug. The home page shows its right-hand news panel only from 1401px wide.

**Check a logged-in panel in a real browser** (the dashboard cannot be opened without a login, but
a panel script can be run on its own): `python3 check-tools/panel_page.py <script.js> <out.html>
<light|dark> "<steps>"` writes a page holding the real script, the site's stylesheet and a stand-in
server, then performs the steps (clicks, typing) and prints what happened into the page. Open it with
headless Chrome using `--dump-dom` for the printed results and `--screenshot` for the look (a local
file with no site scripts does not hang). Nothing live is called. Written for the autopilot panel;
copy and adapt the stand-in answers for another panel.
`python3 check-tools/dashboard_page.py <practice-portfolio.js> <practice-autopilot.js> <out.html> <light|dark> "<steps>"`
does the same with **both** practice sections together (two holdings bought by hand, one by the
autopilot; steps `type`, `sale`, `trial`, `off`, `open`, `preset`, `sellall`, `limits`, `split` and more, listed in `check-tools/README.md`): use it to see how they work with each other,
for example that a sale made in the background appears without losing what is being typed.
A deploy script that checks `pgrep -f deploy-to-s3.sh` must be run as its own command: written and run
in one command, the check finds its own text and stops.

**Share-screener workers** (one file for all 13 groups, section 8b "The worker groups"):
```bash
cd /Users/dave/VSCODE/stockiq
python3 check-tools/workers.py            # every group "one", and the 13 share groups the same code as each other
python3 workers/build.py                  # prints the package's fingerprint: must equal workers/live.txt when nothing is being changed
python3 workers/prove.py                  # what a change to workers/stock_worker.py does, on saved prices (about 3 minutes)
python3 workers/deploy.py --selftest      # the deploy tool's rules against a stand-in for AWS
```

**Run every analysis button end to end:** section 8b, last part.
**Work on the dashboard's practice portfolio or autopilot:** section 8c, "How to work on it" (tests,
browser page, copy-of-the-live-record check, deploy script, verification).

## 13. Change log

- **25 Sep 2026** (Claude Code session, full review):
  - Merged cloud branch `claude/new-session-cuwqcx`: `about.html`, homepage testimonials
    replaced, About link in footers, FAQ accuracy claims removed.
  - About page scoring section corrected; GA4 added to content pages and all stock pages.
  - Stock pages: new template (WebPage schema, filler cards removed, footer fixed), daily data
    snapshot on 962 large caps (`update_stock_analysis.py` + `stock_metrics.py`), others noindex.
  - Sitemap 3,486 → 979 URLs; news.html trimmed and noindex (`finalize_news_html.py`).
  - `deploy-to-s3.sh`: stock pages uploaded by size+time (1,051 were stale), root html/css/js by
    MD5, root JS now uploaded, `DRY_RUN` mode, both repos pushed.
  - `.amazonq` mirror removed (Kiro only); steering docs reviewed; `verification-summary.md` removed.

- **Oct 2026** (Kiro session, new MacBook setup + Japan screener + SEO fixes):
  - Migrated all paths from `/Users/ddewit/` → `/Users/dave/` across 31 files.
  - Python deps installed: requests, openai, yfinance, pytz, bs4, dateutil.
  - Scheduled task converted from AppleScript to bash (`~/stockiq-daily.sh`), window extended to 11am–10pm.
  - Dropbox one-way sync configured (`~/dropbox-sync.sh`, daily launchd job).
  - Git identity updated to `dave@dewit.com.au`.
  - `deploy-to-s3.sh`: fixed `$PYTHON` path variable; added `update_stock_analysis.py` (was missing — stock data stale since Sep 25); added root JS sync loop; added `finalize_news_html.py` (was also missing).
  - `sync-all-lambdas.sh`: added `--profile default --region us-east-1`.
  - `update_sitemap.py`: fully rewritten to rebuild stock URLs from `indexable_stocks.txt` (old version never removed URLs — sitemap stuck at 3,485 instead of ~970).
  - `generate_sitemap.py`: fixed to use `indexable_stocks.txt` instead of all HTML files.
  - `generate-stock-pages.py`: fixed to preserve news/analysis from pages without NEWS_SECTION_START markers; added pre/post news count safety check.
  - `update_stock_news.py`: article fetch window extended 2 → 4 days (laptop sometimes off for days).
  - Ran `update_stock_analysis.py` manually — refreshed 953 large-cap pages (data was 11 days stale). Sitemap rebuilt to 970 URLs, resubmitted to Google Search Console.
  - Restored news from backup after generate-stock-pages.py wipe; ran `sync_news_to_stock_pages.py` to resync.
  - Cleaned up: sitemap copy.xml, blog.html.backup, stocks copy.txt, generate-stock-pages.py.backup, sitemap.xml.backup, github-repo/, stockiq/sitemap.xml, __pycache__.
  - **Japan Nikkei 225 screener** built end-to-end (21 workers, 210 stocks, full dashboard integration).
  - Added `add-new-screener.md` steering doc. Trimmed roadmap, backlinks, script-reference docs.

- **9–10 Oct 2026** (Claude Code session: recovery, full end-to-end check, lists and crypto rebuilt):
  - **Recovery.** The Oct 2 "Auto-update" commit had silently reverted `generate-stock-pages.py`,
    `deploy-to-s3.sh` and `check_news_sync.py` to pre-Sep 25 versions; a regeneration on Oct 9 then
    made all 3,467 pages indexable with no snapshot. Scripts restored from 2485162, pages
    regenerated, 957 indexable. `.gitignore` in both repos restored.
  - **News script:** `update_stock_news.py` was deleting the news section on current-template
    pages; fixed (anchors on markers). 448 empty "History" headings removed.
  - **Site text:** unsupported accuracy claims, "real-time" / "zero delay", conflicting counts and
    the giveaway removed; footer disclaimer on public pages; plan names and limits match the
    payment Lambda; pricing section added to the home page; signup Terms link fixed; terms and
    About state USD billing, online-only, no licence.
  - **Email signup:** reworded; `stockiq-email-capture` emails `noreply@stockiq.tech` per signup.
  - **Describe, don't advise:** AI chat prompt and suggested questions, the single-stock report,
    all screener / signal / crypto formatters, the coordinator, CSV headers, the dashboard popup
    and the FAQ no longer use BUY/SELL, targets, stop loss, picks or recommendations.
  - **Full end-to-end test of all 21 analysis buttons** through the page code and of all 15
    screeners through the coordinator. Fixed: missing `MODERATE_*` labels, `BRK.B` format, stocks
    never sent to a worker, duplicate rows, empty-batch fallback, CSV columns that were always 0,
    fake-fundamentals columns removed, tracker regex (single-letter tickers, long names), crypto
    legend, AI chat button position, a typo in crypto worker 26's address.
  - **Lists rebuilt** from current index members (all but Russell 1000/2000), every symbol
    verified; batching sizes itself to the list; labels and headers show real sizes.
  - **Crypto rebuilt:** new 540-coin list verified against CoinGecko, driven from the
    orchestrator through the workers' single-coin mode; orchestrator memory 512 → 2,048 MB.
  - **Access bug:** 14 handlers re-checked access after counting the use, eating the last free
    use of the day (anonymous single coin; trial users on 13 screeners). Removed.
  - Orphan pages `market-data-sidebar.html` / `market-data-widget.html` deleted;
    `lambda-url-mapping.json` regenerated (982 functions, 967 with URLs).
  - **Crypto top-10 history rebuilt** (section 8b "Crypto"): the 15-minute updater was tracking the old
    coin list; the schedule now runs the orchestrator itself every 30 minutes, risk labels and stars
    removed, results slider reworded, dashboard tracker uses the right ticker, permanent entry log
    added. Deployed by the owner with a packaged script, because the Claude Code session was not
    permitted to run production deploys (Lambda, S3); read-only AWS calls and git pushes were fine.
  - **Dashboard Top 10 Performance rebuilt** (section 8b): faults above fixed, over-time table against
    the index added. **Fake-money test** of the Dow 30 and S&P 100 screeners run (section 11).
  - **Practice portfolio** added to the dashboard (section 8c), with a new table and Lambda.
  - **AI autopilot upgraded** (section 8c): all 15 screeners with per-market hours and currencies,
    quick trading (check-ins from every 30 minutes, holds from 30 minutes),
    stored screener results, and a record of its own closed trades that it learns from (scorecard,
    resting a lagging screener, AI-written notes fed back into its choices). Dollars-or-quantity
    fields on the practice buy row. Two sessions built an autopilot at the same moment on 10 Oct;
    the deploy script's fingerprint check caught it and the second build was dropped. **Run one
    session on the site at a time.**
  - **Your own loss limit and gain mark; whose result is whose** (section 8c): two optional fields
    on the autopilot panel, and a line on the practice portfolio that separates the owner's own buys
    from the autopilot's. Rollback zip: `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_limits_20261010.zip`.
    In zsh, write `"${C}:path"` for `git show`: `$C:c…` is read as a modifier and fails (it left an
    empty deploy script in one work-in-progress commit, corrected in the next).
  - **Autopilot managed from the dashboard** (section 8c): quick set-ups, switches for what it may do
    by itself, "Sell everything it holds", undoing its own rule changes; headlines when choosing what
    to buy; coins use the whole budget when only coin screeners are ticked; a sale on a score below
    zero now says so (it said "signal turned negative"). Rollback zips:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_controls_20261010.zip` and `…_wording_…`.
  - **The AI model reviews each holding at every check-in** (section 8c): fresh screener figures and
    real headlines fetched by the function; it may sell earlier than the rules, and its early sells are
    paused if they prove too early. Rollback zip: `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_review_20261010.zip`.
  - **Autopilot made clearer and able to review itself** (section 8c): whose holding is whose and when
    the autopilot will sell; S&P columns removed from the practice portfolio; details under each buy
    and sale; the panel refreshes itself; two more selling rules; bounded trials of its own rules with
    an email at each step. Rollback zip: `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_smart_20261010.zip`.
  - **Autopilot description follows every setting** (section 8c): the two
    lines under the fields are built from the check-in, holding time, level, budget and ticked
    screeners. Checking them against the Lambda found a rounding fault (the last holding of an
    uneven budget was never bought); fixed in `stockiq-ai-trader`. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_desc_20261010.zip`.
  - **AI autopilot** for the practice portfolio (section 8c): new Lambda, table and hourly schedule.
  - **Deploy permission:** from the afternoon of 10 Oct the session's safety check refused production
    deploys and refused to let Claude change its own settings. The owner added the allow rule
    `Bash(bash /Users/dave/VSCODE/stockiq/check-tools/pending-*/deploy.sh)` himself; with it, a deploy
    packaged as `check-tools/pending-<name>/deploy.sh` runs without a hand-off. Keep packaging deploys
    that way (live-code check, rollback copy, `DRY_RUN=true`), run the dry run, then run it.
  - Autopilot activity list: "Buys and sells only" became a switch remembered in the browser.
  - **Headlines for a coin must be about the coin** (section 8c): share news about a company with the
    same letters as a coin's ticker had reached the model. Rollback zip: `…_before_autopilot_news_…`.
  - **Dashboard tidied into tabs** (sections 8 and 8c): Reports, Practice portfolio and AI autopilot
    each have a tab; the autopilot panel is split into Activity and Settings with its switch and
    buttons kept at the top. Website files only.
  - **"Check in now" acts, and says why when it cannot** (section 8c): a check-in asked for by hand
    releases the next part of the budget early; the reason for an empty check-in is in the message
    and stays visible with "Buys and sells only" on. When trying a staged function on a copy of the
    real record, give the stand-in prices the real buying price of what is held: a made-up price
    makes a holding look sold at a huge loss. Rollback zip: `…_before_autopilot_now_20261010.zip`.
  - **The kind of trailing stop is a choice** (section 8c): "Your own limits" gains a "Trailing stop"
    menu: protects a gain (as before), a full trailing stop loss from the moment of buying, or off.
    Rollback zip: `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_trail_20261010.zip`.
  - **Found in the live data and fixed** (section 8c): a holding whose screener had been un-ticked
    was left unattended (`its_markets`); a coin is now bought only once it has stayed near the top
    for two check-ins; coin screeners are rested on their own results; results are also shown after
    a typical trading cost. Rollback zips: `…_before_autopilot_orphan_…` and `…_steady_…`.
  - **The stop that follows a rising holding is set from the holding's own movement** (section 8c):
    its daily range scaled to the check-in gap, with room that widens or tightens with its screener
    figures, the time left and the AI review's new "tighten" answer. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_stop_20261010.zip`.
  - **The pace follows the risk level** (section 8c): the three pace settings can be left to the
    level ("automatic") or set by hand. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_pace_20261010.zip`.
  - **Gain protection reworked; clearer account figures** (section 8c): a gain is protected from a
    rise that follows the holding time, and a big gain gives back less; the AI review sees each
    holding's path and a larger model is used, capped, when a gain is at stake; the practice
    portfolio no longer flashes a figure before prices arrive, says what is from sales and what is
    on holdings still held, and says when the stock market has been closed. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_gains_20261010.zip`.
  - Docs consolidated: section 8b added, section 11 reduced to open items, `CLAUDE.md` (added
    9 Oct) loads these steering files into Claude Code sessions. On the evening of 10 Oct the
    practice portfolio and autopilot notes, which had grown in layers through the day, were rewritten
    from the deployed code as **section 8c**, with the working routine, so a new session can resume
    dashboard work from the notes alone.

- **11 Oct 2026** (same Claude Code session, continued):
  - **The plan for a holding in words nobody can misread** (section 8c, "Wording rule"): the owner
    read "once it has been up 4.5%, sell if it slips back…" as a selling price. Buy plans, sale
    stories, the portfolio's line under a holding, "Holding now" and the Trailing stop menu now say
    that rising is not a reason to sell and that the stop only starts following there.
  - **Trading hours hold by hand too** (section 8c): "Check in now" and "Sell everything it holds"
    only trade in markets that are open, and say which are closed and when they open; an early
    release of the budget is taken back when nothing was bought. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_clear_20261011.zip`.
  - **A share's "sold at the latest" time is its market's next opening** after the holding time
    ends, each holding's line says when its market is closed and when it opens, and the settings
    line in the activity list says "over 1 day". Rollback zip: `…_before_autopilot_hours_20261011.zip`.
    Live: function `CodeSha256` `yveoXxKn…`, `practice-portfolio.js?v=13`, `practice-autopilot.js?v=20`.
  - **Full check of these notes against the code**: all 282 code names in section 8c exist; the
    level table, pace table, market hours, bounds, limits and AWS settings match; test counts,
    script versions and "where things stood" brought up to date; the function count corrected to
    984 (the two functions made on 10 Oct were not counted) and `lambda-url-mapping.json` regenerated.
  - First real sale by the AI review (ERG, -2.8%) and first look-back result (CFX rose a further
    7.95% after the stop sold it) recorded in section 8c.
  - **"What happens next" and "Needs you" on the autopilot panel** (section 8c): a live countdown to
    the next check-in, a list of what is coming with what each check-in may do, what goes by the
    number of finished trades, a box for what only the owner can put right (a missed or failed
    check-in, a refused email, too little practice money, no screener), the last email's status and a
    "Send me a test email" link. Email set-up checked on AWS and one test accepted. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_next_20261011.zip`. The dashboard's AI autopilot tab
    carries a ⚠ while something needs the owner. Live: `practice-autopilot.js?v=22`.
  - **The budget cannot be more than the practice money there is** (section 8c, settings table): said
    at the field with a one-click fix, refused in plain words, and set right by the function as a
    backstop. A sale by the following stop that ends below the buying price now says the gain was
    gone before the stop could act (it had said "sold to keep part of the gain" on a -0.8% sale).
    Rollback zip: `…_before_autopilot_budget_20261011.zip`. Live: `practice-autopilot.js?v=23`.
  - **The budget is spread over the markets ticked** (section 8c, "How the budget is spread"): a
    share per market in whole holdings, even on automatic (coins held to the level's share) or
    picked from a menu under the market; enforced at every buy. Before this the first market to
    open could take most of the budget. "Check in now" now releases a whole holding's worth of the
    budget however small the steps. A local name `slots` had hidden the schedule helper of the same
    name (now `slot_times`): the "what happens next" list silently failed in tests until renamed,
    which is what its `except` and log line are for. Rollback zip:
    `~/VSCODE/backup/stockiq-ai-trader_before_autopilot_shares_20261011.zip`. Live: `practice-autopilot.js?v=24`.
  - **Factor study of the screener score** (section 7b): none of its own factors reliably sorted
    stocks; a win rate comes from the selling rule, not from skill; one raw figure (distance above
    the 52-week low) kept a modest lead. The autopilot now records that figure with each share it
    buys and splits its record by it: a measurement, not a rule. Rollback zip:
    `…_before_autopilot_low52_20261011.zip`. Live: `practice-autopilot.js?v=25`.
  - **Progress per batch of 20 finished trades, with its own investigation** (section 8c, "Learning"):
    a table on the panel; after each 20 it compares them with the 20 before and, if they did no
    better, says what stands out, puts back a change of its own that was followed by a clearly
    worse batch, and starts a trial of a change the AI model picks from its candidates. **A budget
    larger than the practice money is now put right wherever it is met**, not only refused when
    typed (the owner's saved $200,000 became $99,941 the moment the page was opened). Rollback zip:
    `…_before_autopilot_progress_20261011.zip`. Live: `practice-autopilot.js?v=26`.
  - **Its own trial of which share to buy** (section 8c, "Learning"): every second share is the one
    furthest above its 52-week low on the shortlist, kept only if clearly better after 10 finished
    each way; "Improvements so far" line on the panel. Built after the owner pointed out that the
    study had been measured and reported but not acted on. Rollback zip:
    `…_before_autopilot_order_20261011.zip`. Live: `practice-autopilot.js?v=28`.
  - **Safeguards for every account** (section 8c, "Start here"): paused after two weeks without a
    visit to the dashboard and back on at the next visit; check-ins of several accounts side by
    side; a daily limit on AI calls per account. The autopilot itself is still open to the two
    listed accounts only. Function only. Rollback zip: `…_before_autopilot_idle_20261011.zip`.
  - The breakdown table under "How it is doing" laid out more clearly (website only, `practice-autopilot.js?v=29`).
  - **The AI autopilot opened to every account on a paid plan** (section 8c, "Start here"): the
    function checks the plan itself; accounts without one see what it is and a button to the plans,
    and are refused and sent there if they try to use it; an ended plan pauses it. Home page
    pricing, dashboard plan cards and a new FAQ entry say what the plans include. Rollback zip:
    `…_before_autopilot_paid_20261011.zip`. Live: `practice-autopilot.js?v=30`.
  - **Results in words, and the Beta label** (section 8c, "What the owner sees"): the practice
    portfolio says "up", "down" or "level" instead of signed figures in its "whose result is whose"
    line and its Account value card; the AI autopilot is labelled Beta on the panel, the dashboard
    tab, the plan cards, the home page pricing and the FAQ. Website only:
    `practice-portfolio.js?v=14`, `practice-autopilot.js?v=31`.
  - **The AI chat is on the dashboard and knows it** (section 8c, "The AI chat on the dashboard"):
    how the dashboard works, and what the user's own practice portfolio and autopilot show, with
    rules against advice and against adding to the figures. Changing settings by chat is not built.
    Live: `ai-chat.js?v=2`, `practice-autopilot.js?v=32`, `practice-portfolio.js?v=15`.
  - "What happens then" beside the countdown now opens Activity and goes down to the list (it was a
    bare "#" link that sent the page to the top). Website only, `practice-autopilot.js?v=33`.
  - The "Screeners it buys from" card laid out afresh: a bar for the split, each market's share in
    a box of its own (website only, `practice-autopilot.js?v=34`).
  - **The dashboard on a phone** (section 8c "On a phone"): the tabs fit, the holdings, sold and
    progress tables become cards with a label on every figure, the breakdown wraps, the buy row,
    menus and main buttons take the full width. Website only: `practice-portfolio.js?v=16`,
    `practice-autopilot.js?v=35`, `dashboard.html`. New test tools: the `mobile` step of
    `dashboard_page.py` and `mobile_frame.py`. Checked in a phone-width frame in a headless
    browser, not on a real phone.
  - **Learning shared by every account; arrows; the bell** (section 8c, "Learning is shared by every account" and "What the
    owner sees"): every account's finished trades go, anonymously, into one record that the scheduled run reviews once
    for everyone and every autopilot uses; results are shown as green and red arrows with amounts; the dashboard's bell
    lists and counts the autopilot's buys and sells with profit or loss. The schedule's table scan now pages through the
    whole table. Rollback zip: `…_before_autopilot_central_20261011.zip`. Live: function `5kK9DYb9…`,
    `practice-portfolio.js?v=17`, `practice-autopilot.js?v=36`.
  - "What happens next": a release of the budget is listed at the check-in that can first spend it (it had its own,
    earlier time, which read like a second "next action"). Function only (`MMmJJ9M5…`). Rollback zip:
    `…_before_autopilot_release_20261011.zip`. First scheduled run of the shared learning seen in the log at 08:10 UTC
    ("shared learning: 0 new finished trades…", the record `_brain` written); the owner's four trades follow his next
    check-in.
  - **The notification bell** (section 8c, "The notification bell"; the story in section 9): the autopilot's buys and sells
    are in the bell with the reports, as one list, newest first, drawn by one script (`autopilot-bell.js`) for every page
    that has a bell; unread marks and the red number work as for reports. The function has a read-only action `bell`. It
    took six rounds: the trades first sat out of sight under the reports, browsers kept old copies, an old copy outran the
    new one, and finally the cause that fitted everything: the script was asked for at "/autopilot-bell.js", which is
    nowhere unless the site sits at the top of its address. The owner confirmed it works.
  - **Browsers no longer keep old copies** (section 5, step 8): root pages are asked for again every time, scripts and
    stylesheets are kept five minutes (`deploy-to-s3.sh`; the 36 files on the site relabelled, content untouched).
  - **Full sweep, evening:** the temporary diagnostics taken out of the bell's script and the function; the AI chat's guide
    to the dashboard brought up to date (arrows, the bell, shared learning) and tried live; section 8c's parts on the
    bell, "Start here when resuming" and who can use the autopilot rewritten from the deployed state; the other steering
    files and the two README files corrected; two superseded task plans removed (`.agents/tasks/nikkei225-*.md`);
    every code name these notes mention checked against the code. Found and passed to the owner: both repositories are
    public (section 11). Live at the end: `stockiq-ai-trader` `e6X8RM+w…`, `stockiq-ai-chat` `8QzCNJ8L…`,
    `autopilot-bell.js` version 8, `practice-autopilot.js?v=37`, `practice-portfolio.js?v=17`.
  - **After the sweep, at the owner's word ("go ahead with what you think is best in that order"):** the fast replay of the
    autopilot's rules (`check-tools/replay/replay.py`; findings in section 7b); **a trading cost of 0.1% on every practice
    buy and sale**, by hand and by the autopilot; **the bar its record has to clear**, set down and shown on the panel
    (300 finished trades, after costs, ahead of the yardstick by twice the margin of error); the panel's note on shares
    kept two days or less; the AI chat's guide told of the cost and the bar. Live: `stockiq-ai-trader` `k2OocgJo…`,
    `stockiq-ai-chat` `cTz2ks6B…`, `practice-portfolio.js?v=18`, `practice-autopilot.js?v=38`. Tests: 386 function,
    198 panel, 74 portfolio, 22 bell, 16 chat.
  - **Crypto screener: three faults** (section 8b, "How a coin is scored"), found when the owner asked whether the top 10 is
    in the right order. It is; but MACD had never been worked out for any coin (30 days of prices asked for, 35 needed:
    every coin scored "MACD Bear: -2"), a coin with a stuck price stood 5th, and ties at the cut went unsaid. The 54
    workers now ask for 90 days for MACD; the orchestrator leaves stuck coins out and states ties. Scores and the top 10
    changed at 11:52 UTC.
  - **Audit of the worker groups** (section 8b, "The worker groups"; `check-tools/workers.py`): 928 workers in 18 groups, 204
    never called; the share screeners are one code base with small drift (two ways of working out RSI, a file per function
    in the two Russell groups); a plan to make it one source file in git, written and not started.
  - **One code base for the share screeners (evening; section 8b, "The worker groups").** All 669 share-screener workers in
    13 groups run one package built from `stockiq/workers/` in git (fingerprint `q9ZX/UvTB…`); before, seven copies that had
    drifted. One RSI everywhere (Wilder's): **about a third of US and London signal labels and three or four of each top 10
    changed on the day**, far more than these notes had expected; the NASDAQ 100 and Dow 30 lost their own company-figures
    tables; the ASX 24-hour change of 0 and the London price a day old fixed at the source; the Russell lists in the
    packages replaced by the coordinator's (the old ones held 125 company names); SPY fetched once per batch. Proved on
    saved prices first (`workers/prove.py`, `workers/results-proof-2026-10-11.txt`), deployed a group at a time with the
    way back tested on the Dow 30, every share button run through the page and the coordinator afterwards. The studies of
    section 7b run again with the one file: same conclusions. New tools kept for good: `workers/build.py`, `prove.py`,
    `deploy.py` (with a self-test), `groups.py`; `check-tools/workers.py --contents`. Old packages:
    `~/VSCODE/backup/workers_before_onecode_20261011/`. About and FAQ pages checked: neither says how RSI is worked out,
    nothing to change. `add-new-screener.md` rewritten around the one package, with Germany (DAX 40) as its example.
    **Lessons: a count of zip fingerprints is not a count of programs; and measure a scoring change before describing its
    size** (section 9).
  - **The report writers and the tracker (13:46 UTC; section 8b, "Dashboard performance tracker").** Found during the worker
    job: London prices in pence printed as pounds on the page and as dollars in background reports, and the coordinator
    cutting every symbol to five characters, so that the 🎯 tracker read 6 of 10 symbols of a background FTSE report and
    none of a Nikkei one. Now one money rule in the page (`screenerMoney`), the coordinator (`money`) and the single-stock
    report, from the currency each worker result carries: "503.80p", "A$8.43", "¥5,613.00"; three FTSE shares that are
    quoted in dollars or euros print as such. The tracker reads a leading sign or a number of pence, with commas, and the
    older saved forms. Proved before and after the deploy by running the tracker on real FTSE, ASX 200 and Nikkei reports
    from both paths: 10 of 10 symbols each, 0.00% on closed markets. Rollback zip:
    `~/VSCODE/backup/stockiq-screener-coordinator_before_currency_20261011.zip`. `tracker_run.js` now reads a `res_*.json`,
    `run_all.py` takes `COORD=<file>`, `page_run.js` takes `FUNCS=<file>`.
  - **The owner approved the one RSI for every screener** (asked directly, 11 Oct): it stays.
  - **Trading-signals writers, a comparison above several reports, a Currency column (14:32 UTC; section 8b, "Trading signals
    and the presets" and "CSV exports").** The page's two signals writers print what the rebuilt functions send (currency,
    name, change, reasons, trend, the 20-day high and low, symbols not found; "strongest readings" with the scan's
    figures); a run of several single-stock reports starts with a side-by-side table; the screener CSV has a `Currency`
    column in both paths. Tested through the page code, the coordinator and the dashboard's tracker before and after
    the deploy (the tracker reads every symbol of both signals reports, 0.00% on closed markets). Found by the test and
    fixed: a name with "&" hid its line from the tracker. Rollback zip:
    `~/VSCODE/backup/stockiq-screener-coordinator_before_csvcurrency_20261011.zip`. `page_run.js` now keeps the
    screener's CSV in its result file.
  - Notes: section 8c ends with "Start here when resuming". Everything known is in these files.
  - **The single-stock report and its chart rebuilt** (section 7, "The single-stock report and its chart"), in the first
    session again, after the owner asked whether the individual analysis could be improved. Prices in the share's own
    currency (every share had a dollar sign, pence included); one bar a day (ASX "+0.00% today") and the latest session
    from the quote (London a day old); one RSI for text and chart (47 against 56); a trend factor that grows with the
    distance (0.03% under an average read "Strong Downtrend: -12"); one explanation of the score that adds up; company
    figures for shares outside the US from the pages' own cache, published by the new `publish_company_figures.py`
    (Yahoo's summary cannot be read from AWS: tried, refused, taken out); a chart drawn from the report's own prices,
    with clean lines, the 200-day average, no background and lettering that grows on a phone. Three deploys with dry
    runs (13:20, 13:27, 13:28 UTC); `stock_metrics.py` follows; tests kept in `check-tools/report/`. **Lesson: read the
    live output a second time after a deploy: the third deploy fixed a wrong source label that only a repeat report from
    a warm function showed.** A fourth (13:34 UTC), at the owner's word: the latest article's time in the visitor's own
    zone, as the stock pages show it, and the zone named beside the report's own time.
  - **Trading signals rebuilt and the presets reviewed** (section 8b, "Trading signals and the presets"), at the owner's
    word that they were "junky": the two signals functions now run one file in git (`signals/`), with the site's one
    RSI, readings that say why, real levels and a time a browser reads rightly; the auto-detect scans the whole S&P 100
    for the five strongest readings instead of calling five of fifteen megacaps "top performers". The page's writers
    still have to print the new fields. Memory raised (128 MB made the scan take 33 seconds). **Lesson: time a function
    after changing what it does; a function's processor share goes with its memory.**
  - Commit `a0be314` (trading signals) also carries the report-writers session's notes in progress and its removal of
    `check-tools/pending-reports/`: two sessions were committing at the same minute (section 10, "name the paths").
  - **What it all costs, and the crypto job brought inside the free allowance** (section 11, "What AWS costs"; section 8b
    "Crypto"): the owner asked whether the week's changes raise the AWS bill. Measured: 34 cents for eleven days, and
    less computing than before, but the crypto screener's one call per coin was heading for 0.8 million calls a month.
    The 54 workers now take ten coins a call and the orchestrator sends 54 batches: the same 536 coins and the same
    top 10 before and after, from a tenth of the calls. Rollback zips: `~/VSCODE/backup/stockiq-option-7-1-worker_before_batch_20261011.zip`
    (the same to all 54) and `stockiq-option-7-1-orchestrator_before_batch_20261011.zip`.
  - **The crypto worker's code reviewed** (section 8b, "How a coin is scored", last two items): one request to the price
    source per coin where there were two, a day's figures kept together, the unused old mode and its 540-coin list
    removed; no score changed (proved on recorded answers). Four things found that would change scores were written
    down and left for the owner: the ranking's dependence on the time of day, the RSI method, the score's design and
    leftover advice wording in strings nobody sees.

- **12 Oct 2026** (the same session, continued after a pause):
  - **Single-coin analysis through the single-stock report function** (section 7, "It reports on a coin too"): the owner
    asked whether a coin's analysis should use the function built for shares. Tried live on Bitcoin, it did the job
    better than the button's own function (a third copy of the old crypto worker): a chart, an explained 0-100 score,
    the site's one RSI. The report function got a coin form; the page's button and the dashboard's background run
    use it; a share's report is unchanged to the character. For the 30-minute screener the answer was no: the share
    screener's score has three factors that mean nothing for a coin, and neither score is proven.
    **Lesson: a test that replays recorded prices must also set the clock to the recording** (a coin check passed on
    the day of the recording and failed the next morning).
- **12 Oct 2026** (the session of 11 Oct, continued):
  - **A graph of the account over time on the Practice portfolio tab** (section 8c, "What the owner sees"), at the owner's
    wish. Worked out in the browser from the holdings, the sold list and the daily prices that already come with every
    quote: no function changed, nothing stored, no extra requests. Checked on stand-in data in a real browser (light,
    dark, phone width) and on the owner's real record with live prices, where it ended on the figure the Account value card
    shows. Live: `practice-portfolio.js?v=19`, `dashboard.html`. Tests: 92 portfolio checks (18 new); `dashboard_page.py` has
    a `chart` step and an account with a few weeks of history (`?chart=1`).
  - **Two sessions at once, again:** the other session deployed `dashboard.html` one minute after this one had staged its
    copy. The deploy script's fingerprint check refused the stale copy; it was staged again from the current file. And a
    reminder of the zsh trap in section 8c: `$NEW:application/…` inside a here-document is read as a modifier (`:a`, `:t`);
    write `${NEW}` or fill such lines in with Python.
  - **The holiday gap closed in the autopilot** (section 8c, "The autopilot: settings", "Limits"): a share is bought or sold
    only at a price that has traded in the last 3 hours. Function `1Wabeqp4…`; 8 new checks (394). Tried on live prices
    during the Japanese holiday before deploying. Rollback zip: `…_before_autopilot_fresh_20261012.zip`. **To see for
    real:** the owner's next check-in for Tokyo should write "Left alone: 4307.T …, 6976.T …" and sell neither.
  - **Practice portfolio buttons and wording** (section 8c, "What the owner sees"): the two tools beside the heading;
    hover, pressed and busy feedback on every button there and in the autopilot panel; "Prices updated <time>"; typing
    kept through a refresh (found by the new browser step: it had always been wiped); the same sold / still-held split
    for both parties. Live: `practice-portfolio.js?v=20`, `practice-autopilot.js?v=39`, `dashboard.html`.
    `dashboard_page.py` has a `refresh` step; 93 portfolio checks.
  - Not done: the AI chat's `DASHBOARD_GUIDE` does not yet mention the graph, the tools beside the heading or the
    fresh-price rule.
  - The "For comparison" card says when the US market opens, in the sidebar's own figure (`practice-portfolio.js?v=21`; 95
    portfolio checks; `dashboard_page.py` takes `?sidebar=1`).
  - **A market that showed only old prices stays due** (function `2gv02OdM…`, 04:47 UTC; section 8c, "Limits"): found the same
    morning when the owner's settings turned out to be a check-in every 12 hours. Rollback zip `…_before_autopilot_due_20261012.zip`.
  - **The number of holdings as a setting of its own** (function `dRaKpUf9…`, `practice-autopilot.js?v=40`, 04:50 UTC; the
    settings table in section 8c): asked for by the owner after a replay showed it changes the bumpiness, not the profit.
    Tests: 404 function, 202 panel, the panel-versus-function comparison with 3, 20 and 50 holdings (4,166 spreads); a
    `holdings` step in `dashboard_page.py`. Rollback zip `…_before_autopilot_holdings_20261012.zip`. **A slip caught by the
    tests:** a new variable named `waiting` overwrote an existing one in `run_user` (the coins "waiting to stay"); the
    2,970-line function has one namespace per check-in, so search for a name before using it.
  - **The AI chat knows the dashboard as it is now** (function `f6vB7CzN…`, 08:58 UTC; `practice-autopilot.js?v=41`, 09:00
    UTC): its guide has the account graph and its three views, "Refresh prices" / "Reset fake money" beside the heading,
    the sold / still-held split for both parties, the comparison card's opening time, the Number of holdings setting and
    the rule that a share is traded only at a price under 3 hours old; `ai_chat_test.py` compares those numbers with the
    autopilot's own (19 checks). **Found by asking it real questions:** told "up to 50 holdings" for a Balanced account it
    answered "it will aim for 8"; a clearer guide fixed one wording of the question and not the other, so the panel's
    `summary()` now says it outright ("it uses 50, not the level's own 8"). Then right three times of three. The lesson
    of 11 Oct again: read its answers, do not trust the guide alone. Rollback zips `stockiq-ai-chat_before_guide_20261012.zip`, `…_guide2_…`.
  - **A diary that is never trimmed, and a review tool** (function `tBSm1I3R…`, 09:17 UTC; section 8c, "The diary, and the
    review every week or two"): asked for by the owner as the way to log losses and improve, with a session every week or
    two doing the in-depth part. New table `stockiq-ai-trader-journal`; `keep_diary` in `save_item`; 415 function checks;
    `check-tools/autopilot_review.py`; the first review (the baseline, five finished trades) is
    `check-tools/reviews/review-2026-10-12.txt`. No trading rule changed. Rollback zip `…_before_autopilot_journal_20261012.zip`.
  - **The AI model's notes wait for 30 finished trades** (function `FObfjaG/…`, 09:49 UTC; "Learning from its own results"):
    the first thing the review tool's baseline showed, done at the owner's word. 422 function checks. Rollback zip
    `…_before_autopilot_notes_20261012.zip`. **Seen live:** the 10:10 UTC run dropped the
    shared record's five-trade notes ("shared learning: 0 new finished trades, 5 in all from 1 accounts, 0 notes"; no errors). **The owner's aim, in his words that day:** "pickup on patterns… much more
    success than failure its something to repeat, if we see consistent loss patterns we also steer away… end goal here is
    make money we need it over 100,000. currently its continually losing". Told plainly in answer: that is what the
    review routine does, with one condition, a pattern counts only from about 30 trades in a group and beyond its margin
    of error; five finished trades (-$1,014, most of it two $25,000 coin holdings) say nothing yet; and the backtests
    (section 7b) give no promise that it ends above $100,000.
  - **Each buy remembers how many headlines the model was shown** (function `E7OY2fUB…`, 10:14 UTC; "Headlines"): a
    measurement only, asked for by the owner's question whether the news adds anything. 424 function checks. Rollback
    zip `…_before_autopilot_heads_20261012.zip`.
  - **Everything checked at the owner's word before he left it to run ("make sure everything is up to date… nothing is
    erroring… go in depth")**, 10:17 to 10:30 UTC: seven functions and ten site files equal their local copies; all 13
    share-screener groups on one package; every test suite passes on the live code (424 function, 203 panel, 95
    portfolio, 22 bell, 19 chat, 42 signals, the panel-versus-function comparison, the worker deploy tool's self-test);
    no fault line in 48 hours in the logs of 15 functions and no Lambda error in three days; both schedules enabled.
    **Found and fixed:** the daily run could not publish the company figures (`publish_company_figures.py` called "aws"
    by its bare name, which launchd's PATH does not hold; now the full path). **Found and written down:** most Lambda
    calls come from open browser tabs polling the market widgets (section 11, "What AWS costs"). "Start here when
    resuming" rewritten from the day's state, with **one list of improvements to come**; a reminder for the owner at the
    very top of this file; the stale statements this check met were corrected (script versions, test counts, the
    single-coin function, fingerprints). Last of the day, off that list: the headline filter drops pages that only
    explain a price move (function `hkZjPYBD…`, 10:29 UTC, 425 checks; rollback zip `…_before_autopilot_junk_20261012.zip`).
  - **The patient-shares trial** (function `8bg71SuG…`, 13:47 UTC; "Start here when resuming"): every second pair of shares is
    sold by price or time only, not on the signal and not by the AI review. 436 function checks. **The comparison of
    the panel with the function caught the first design's side effect** (a 30-day hold of its own would have overridden
    the user's holding time): run it for every change to the function, not only for changes to the budget.
  - Asked whether "Check in now" and "Sell everything it holds" should sit beside the "Checks in" setting, then thought
    better of it ("maybe i'm wrong and current spot for it is ok"): they stay at the top, beside the countdown and reachable
    from both parts of the panel. A link under "Checks in" doing the same was staged and **not deployed** (commit `f4e5e81`,
    `check-tools/pending-link/`, if he ever wants it); its check in `autopilot_test.js` only applies when the link is there.
  - **Every statement on the dashboard checked against the code at the owner's word ("has to be accurate!")**, 15:08 UTC. Wrong
    and put right: "it buys at most 3 at a check-in" (a fifth of the holdings: 10 at 50); "every holding is sold when its
    signal turns and is reviewed by the AI model" (not the patient shares); the trial was not listed. Right as they
    stood: the schedule every 30 minutes (`cron(10,40 …)`, enabled), the check-in choices, the crypto history every 30
    minutes, prices on stock pages every 5 seconds, $100,000, the 0.1% cost, the public pages' sentences about the
    practice portfolio and the autopilot. `practice-autopilot.js?v=43`, `practice-portfolio.js?v=23`, the chat `rs1M0Dqa…`.
    **Left for the owner (what public pages say is his): "real-time market data" on `contact.html` and "15+ indicators,
    real-time charts, and AI-powered pattern recognition" on `technical-analysis-guide.html`**, which the site does not
    deliver (data is delayed; section 11).
  - The "For comparison" card says in words who is ahead, the holdings or the fund, and names the S&P 500 fund in its title (`practice-portfolio.js?v=26`; 98
    portfolio checks), after the owner read the fund's figure as his own lead.
  - **"Holding now" as a row a holding** with the plan folded under each, and "tests changes" for "tries changes" (the owner,
    from a picture of his own panel; `practice-autopilot.js?v=44`; 209 panel checks; looked at in a headless browser).
  - **"Today" on the practice portfolio**: for the holdings together on two cards, and a column a holding (`dayMove`;
    `practice-portfolio.js?v=27`; 106 portfolio checks; tried on the owner's real holdings with live prices and looked at
    in a headless browser).
  - **"Holding now" rows tidied, and each holding's own stop shown from the start** (function `tyvs5Au9…`, `practice-autopilot.js?v=45`,
    16:51 UTC): the owner disliked that every row read alike ("all saying 6.4% doesn't exactly look like smart AI"). Part of
    that was a display fault: a new holding's stop, worked out from its own daily movement when it is bought (the buy's
    note said 4%, 4.8%, 3.3%, 1.8%), was not kept with the buy, so the page showed the level's general figure until the
    next check-in (`facts['stop']` is now set at the buy). 437 function checks, 210 panel. Rollback zip
    `…_before_autopilot_rows_20261012.zip`. **He also asked why DDOG was bought at its high for the year: it was the
    buying-order trial's pick (the share furthest above its 52-week low), which is the idea under test.** His wider
    point stands and is on the list: the loss limit and gain mark are the same for every holding of a level.
  - The Practice portfolio's holdings table folds the autopilot's plan for a holding behind an arrow (`practice-portfolio.js?v=28`;
    107 portfolio checks). **The owner had meant this table when he asked for "minimal info and a drop down"; the session
    first changed the autopilot tab's list instead. When he describes a place on the page, find the exact words he
    quotes in the code before changing anything.** The flaky check "buying by quantity" stopped that deploy three
    times before it went through (improvements, item 0b: worth fixing next).
  - **The top of the Practice portfolio tab made simple** (13 Oct, `practice-portfolio.js?v=29`; 108 portfolio checks; looked
    at in a headless browser): three figures, one line, the rest folded under "The breakdown".
  - The dashboard checked at phone width after the day's changes; the graph's date labels no longer collide there
    (`practice-portfolio.js?v=30`).
  - The subtitle beside the Practice Portfolio heading taken off at the owner's word (13 Oct; `dashboard.html` only).
  - **A build-up that begins again paces out only what is not invested yet** (function `0tynNBjn…`, 17:25 UTC; "One check-in,
    step by step", 6): the third freeze of the owner's buying in one day, found when he asked why every holding still
    read alike. On his real record: no room for a new holding until the next afternoon before, room for 2 at the next
    check-in after. 442 function checks; the panel-versus-function comparison unchanged. Rollback zip
    `…_before_autopilot_buildup_20261012.zip`. **And a correction: the session had told him the five new shares' own stops
    "should already" show; their first check-in was still twenty minutes off. Read the record before saying what it shows.**
  - The Practice portfolio shows the site's spinner while it loads and loads sooner after a refresh (13 Oct;
    `practice-portfolio.js?v=31`, `dashboard.html`; 109 portfolio checks). The portfolio tests waited for the word
    "Loading…" to go: they wait for the spinner now (`waitIdle` in `practice_test.js`).
  - A holding's note sits on a line of its own under the company ("Note: …"; `practice-portfolio.js?v=32`; 110 portfolio
    checks), asked for after the owner's first buy by hand with a note.
  - **The session ended here (17:45 UTC, 12 Oct)**, the owner leaving it to run: "Start here when resuming" holds the state.
  - The daily job keeps a dated copy of the company figures once a week (`research-data/company-figures/`; the first is of
    12 Oct 2026): the start of a history to test ideas about company figures on. Scheduling a nightly session was asked
    about and judged not worth it yet ("GO PLAY", section 8c).
  - **Later that day:** the company-figures script run by hand on the scheduler's bare PATH: published (10:55 UTC). **A
    clean-up of unused worker functions was prepared and stopped by the owner before its dry run; nothing was deleted**
    ("Start here when resuming", improvements, item 10): the audit's "204 never called" was wrong for 60 of them, the old
    S&P 500 workers, which had calls until 11 Sep 2026. **Lesson: "the site does not call it" is not "nothing calls it";
    count the calls (CloudWatch keeps 455 days) before calling a function unused, and show the owner the list before
    preparing a delete.** The standing instruction for every session (review when a week has passed, list the
    improvements, ask) was written at the top of this file at his word.
  - **Goals month by month, and the trial queue agreed** (section 8c, "The goals, month by month"): targets for 12 Nov, 12
    Dec and 12 Jan with what happens when one is missed; the review tool prints the standing against them (part 9). The
    queue of trials that runs itself is the first job of the first weekly check (on or after 19 Oct).
  - **The mandate written down** (section 8c, "Start here when resuming"): the owner wants each session to look for ways to
    beat an index fund, as its own job ("this is your playground"); the method (replay first, four tests, survivors go
    live as trials) and the leads are set out there.
  - **The owner's hunch about fast risers, tested the same hour**: not so for shares (four years), possibly so for coins (one
    day of the entry log: entries into the top 10 fell about 4%, the fastest risers most). New tool
    `check-tools/crypto/entry_study.py`, to be run at every weekly check.
  - The holdings table's heading says how many are held (`practice-portfolio.js?v=22`, `dashboard.html`; 96 portfolio checks).
  - An empty "Build up to it over" or "Number of holdings" box reads "Automatic: 5", not a bare 5 (`autoWord`;
    `practice-autopilot.js?v=42`; 204 panel checks; measured in a browser: the text needs about 90px, the boxes have 136px or more).
  - Still not checked by a session: the logged-in dashboard itself and a real phone (neither can be opened from here).

- **13 Oct 2026** (a short session; the owner asked why the home page's Market News had nothing from the last two days):
  - **The Market News list was never sorted, and now is.** The display code inside `news.js` sorted on each item's date
    text ("Mon, October 12, 2026 at 9:49 PM UTC 4 min read"), which a browser cannot read as a date (the "at" and the
    "min read"), so the sort did nothing and the page showed the first general article and the first four stock
    articles in the order of the file. That order is the order the daily run met the stocks in, and it takes articles
    up to four days old: on the live file of 12 Oct the page showed articles of 9, 11, 10 and 11 Oct while eleven of 12
    Oct sat further down. The wording of the date has been this way since at least 27 Sep 2026. Both writers
    (`update_news.py`, `update_stock_news.py`) now write display code that sorts on the item's `timestamp` (the date
    text only as a fallback). Tested by running each writer on a copy of the live file with an old article added at
    the top: the page shows the newest five. New test: `check-tools/news_sidebar_test.js` (it fails on the old file).
  - **Not uploaded by hand, at the owner's word** ("i don't care about whether it shows up today"): the daily run of 13 Oct
    was under way with the old code in memory, so the site gets the corrected file from the run of 14 Oct. **To see
    then:** `node check-tools/news_sidebar_test.js` on the live `news.js` passes.
  - `clear_stock_news.py` writes an empty file with an older, simpler display code; the next daily run replaces it, so
    it was left. Not done: the check is not part of `deploy-to-s3.sh` (the script was running; a line there after the
    news steps would catch a script reverted by an "Auto-update" commit, as happened on 2 Oct).
  - **The market-data sidebar on a phone follows the finger and no longer throws the page to the top** (section 8, "The
    market-data sidebar on a phone"), at the owner's report from his own phone. Opening it gave the body
    `position: fixed`, which puts the page at the top, and closing left it there; the home page and the dashboard each
    had their own copy of that code. Now one script, `mobile-sidebar.js`, for both. Deployed after the daily run had
    finished (06:10 UTC): `index.html`, `dashboard.html`, the new script. **Checked** with a new test that drags a finger
    in headless Chrome at phone size, 27 checks a page, on the staged copies, on the local files and on the live site
    (`check-tools/mobile_sidebar_check.js`; it fails on the old pages with exactly the jump he described). **Not checked:
    a real phone, and Safari on an iPhone in particular**: his phone is the test. Lessons for that test: a made-up
    flick has to carry its own clock (a busy page slowed it into a drag, which read as a failure of the page), and one
    failed step cascades (a swipe to the right with the sidebar shut opens the menu, which still jumps to the top).
    Way back: `git checkout 65eb39f1~1 -- index.html dashboard.html` in `website/` and upload the two pages.
  - **The daily run of 13 Oct had Yahoo's limit again:** "No price data: 2021, kept yesterday's snapshot: 719", 957 still
    indexable, nothing de-indexed (section 9). Nothing in this session asked Yahoo for prices in bulk. Its other steps
    were clean and both repos were pushed. If the data dates on stock pages look a day old: `python3
    update_stock_analysis.py` later, then a deploy.
  - **The graph's three buttons also choose whose holdings are listed** (section 8c, "What the owner sees", under the graph):
    the owner's idea, offered two ways; built the way that adds no second row of buttons. `practice-portfolio.js?v=33`,
    `dashboard.html` (the version number), and one sentence in the AI chat's guide (`stockiq-ai-chat` `cQHzRlpe…`; rollback
    zip `…_before_filter_20261013.zip`). Tests: 118 portfolio checks (8 new: the three views, a refresh keeps the choice,
    not remembered), 21 chat checks, the stand-in page's `chart:ai` step now reports the lists; looked at in a headless
    browser, desktop and phone width, dark. The chat was asked a real question after the deploy and pointed to "Account"
    or "Show all". **Not checked: the logged-in dashboard itself.**
  - **The menu on the left works like the sidebar on the right** (section 8, "The two panels that slide in on a phone"), at
    the owner's word after trying the sidebar on his phone ("the right side is all good"). The menu froze the page the
    same way, on all eight kinds of page that have it. Fixed in one place, `styles.css` (`body.menu-open` no longer
    `position: fixed` with a height; its `!important` lines also undo what older page code still writes), so the 3,467
    stock pages needed no regeneration; `mobile-sidebar.js` (v2) now moves both panels, and `index.html`,
    `dashboard.html` and `analysis.html` lost their own swipe code. **Checked** with the finger test on the staged
    files, the local files and the live site: 183 checks over nine pages (home, dashboard, analysis, blog, news, sign
    in, sign up, two stock pages); the same test fails on the old pages with the jump. **Not checked: a real phone.**
    Found on the way: a pop-up of the home page uses the same class to stop the page scrolling, so it no longer throws
    the page to the top either; `script.js` holds a third copy of the menu's open and close code that no page loads.
    Way back: `git checkout 8074df1e~1 -- styles.css mobile-sidebar.js index.html dashboard.html analysis.html` in `website/`,
    then upload the five files (that state has the sidebar's fix and not the menu's).
  - **The banners, usage badge and sticky buttons mapped** (section 11, first item on them), at the owner's question
    whether the session understood them. Read from the code and looked at on the live site as an anonymous, a
    signed-in unpaid and a paying visitor, desktop and phone (GETs only; every POST answered locally). Nothing changed.
  - **The usage count moved into the header bar, with a kept way back** (section 8, "The visitor's usage count is a chip
    inside the header bar"). The owner: go ahead and improve the banners, "but make it easy so we can revert back… not
    sure you can test all those 3". Built as a takeover so that both hold: the pages' own code still decides who is on
    a trial, paid or out of analyses, and one new script only shows it; undoing is one command. All three kinds of
    visitor were tested through the site's own sign-in and trial code with made-up sessions (seven cases, 1,612
    checks) and looked at in pictures; the live site was looked at as an anonymous visitor. `visitor-bar.js` (new),
    `theme.js`, `index.html`. **Lessons:** the site skips its sign-in check for headless Chrome, so a test of a
    signed-in view needs an ordinary browser name; and an element measured while it is still in a flex row pushes the
    others aside (the chip first measured its own effect and found no room on a phone).
  - **The duplicate code behind the usage chip taken out** (section 8, same part), at the owner's word once he had seen the
    chip ("the updates so far look great… duplicate? then fix it up please!"). The home page and the analysis script
    no longer make a badge or round buttons of their own; `visitor-bar.js` (version 2) draws the one round button;
    `analysis-functions.js` is 188 lines shorter. **Checked:** the visitor test on the staged and the deployed files
    (1,746 checks); `anon_run.js` and `trial_run.js` on the old and the new analysis script side by side (the same
    results and redirects for an anonymous visitor and a trial user, with one request fewer); a screener and a
    single-stock report through the page code; the sliding-panel test; the live site as an anonymous visitor.
    **Left on purpose:** `auth.js` untouched; the dashboard's own copy (it also draws the plan section). Website
    commit `5b2a68d5`; its way back is `check-tools/pending-cleanup-undo/deploy.sh` (a `git revert` tried on a copy
    first). **Lesson: before calling a copy a duplicate, read to the end of it.** The dashboard's "badge function" turned
    out to be the function that draws a paying member's plan.
  - **Three small things seen while the banners were mapped** (the owner: "just keep doing your thing improving how it
    looks"). The header on narrow desktop widths (section 8, "The header bar on a narrow desktop window"); the main
    button of a section, `.cta-primary`, is the site's blue with no underline (it was red and underlined; only the home
    page uses it); the pop-up after the free analysis says "15 free analyses? That is 5 a day for 3 days", the count
    the strip and the other pop-up give (it said "5 Free Reports per day"). `styles.css`, `analysis-functions.js` (one
    line). Website commit `8e50ee53`; to go back, `git revert` it and upload the two files. Checked with the visitor
    test at the usual widths and at 1150, 1024, 900 and 780px, the sliding-panel test and an anonymous analysis run.
    **A trap met twice today: headless Chrome's `--screenshot` with `--virtual-time-budget` never finishes on a stock
    page** (the page asks for prices every five seconds); take pictures of stock pages through one of the test tools
    (`SHOTS=<folder>`), which wait a fixed time instead.
  - **The site's wording brought up to date** (section 11, "The site's wording"), at the owner's word: "for the wording you can
    update it however you like, it was originally done via AI anyway. would love an update of the site as alot has
    changed on the AI side". Eleven pages, words only. **Home page:** a new intro card ("Research tools for individual
    investors"), four numbers that can be checked, the three "How StockIQ Works" steps, a new section of eight cards
    ("What you can do with StockIQ": the report, the screeners, the signals, the crypto screener, the AI chat, the
    practice portfolio, the AI autopilot (Beta), the dashboard) above the pricing, and "What StockIQ is, and what it is
    not" at the end; the "Common Challenges" list and the table against Bloomberg and Morningstar are gone; new
    descriptions for search engines and shared links. **FAQ:** 14 answers rewritten and one question reworded ("What
    makes StockIQ's scoring methodology better?" is now "How are the scores calculated?"), with its structured data.
    **Guides, contact, About:** their sentences about StockIQ. **The strip across the top:** one new wording for each
    kind of visitor on the four pages that carry it, and in `generate-stock-pages.py` for the stock pages' next
    regeneration (not regenerated now). Checked: every page's scripts and structured data still parse; whole-page
    pictures at desktop and phone width with nothing sticking out sideways; the visitor test and the sliding-panel
    test on the reworded pages. Website commit `56224f83`; to go back, `git revert` it and upload the eleven pages.
  - **The analysis page's script: one screener routine in place of 14 copies, and the lists in a data file** (section 8b,
    "The page's one screener routine"), at the owner's word ("fix up the analysis.html and the logic in it all. its
    insane… take a look see if you can improve it"). He had also asked for the "Coming Soon" screeners (Germany's DAX 40
    first): **not started; this was done first because each new screener would otherwise have been a fifteenth copy.**
    `analysis-functions.js` 324 KB to 169 KB; new `screeners.js`; proved to give the same requests, reports and CSV for
    every button. Website commit `e0d47f15`. **A slip in a test command on the way:** `for b in "3 8" …; node
    page_run.js $b` passes "3 8" as one argument in zsh (it does not split words), and the tool then reports nonsense
    without saying why; pass the two arguments separately.
  - **The practice portfolio's graph shows the S&P 500 beside the account** (section 8c, "What the owner sees", under the graph),
    at the owner's idea: the same $100,000 put into an S&P 500 fund when the account began, as a second, gold line, with
    who is ahead said in dollars above the graph and on the one line under the three figures. `practice-portfolio.js?v=34`,
    `dashboard.html` (the version number), the price function (an optional `range`, so the fund's prices can reach back
    past a month) and a sentence in the AI chat's guide. Tests: 130 portfolio checks (12 new), 22 chat checks; looked at
    in a headless browser (desktop light and dark, phone width); run on a copy of the owner's real record with live
    prices before and after the deploy (fund $99,939.63, the account behind it by about $1,450); the live chat asked two
    questions (it explained the line and declined "should I just buy the fund"). **Not checked: the logged-in dashboard
    itself, a real phone, and the longer range in use** (needed from about 4 Nov 2026). Rollback zips
    `stockiq-price-proxy_before_fund_20261013.zip`, `stockiq-ai-chat_before_fund_20261013.zip`; the website files from
    git. Another session was building the DAX 40 screener at the same time: commits were made by path.
  - **Germany DAX 40: the first screener added since the Nikkei, and the first through the new routine** (section 8b, the
    screener table and "The page's one screener routine"; `add-new-screener.md`). The owner: "lets have a good adding
    more screeners… eg Germany (DAX 40) - Coming Soon", then, told that adding one ends the easy way back to the old
    analysis script, "thats fine we can undo if any issue". Done in this order, each step checked before the next:
    the 40 members (German Wikipedia, as of the index review of 22 June 2026: Hochtief in, Porsche SE out against the
    older English list), every symbol priced through the price proxy, all in euros; a line in `workers/groups.py` and
    the one worker file run by hand on three shares; **the four workers created by `workers/create_group.py`, its first
    real use** (settings as the Nikkei workers, each tried through its address); the coordinator (workers, list, name,
    size; rollback zip `stockiq-screener-coordinator_before_dax40_20261013.zip`); the page (entry, button, the report
    writer for any market); the dashboard (name, run again, background run, `^GDAXI` for the Top 10 comparison); then
    the site's wording ("16 screeners", Germany in the lists: five pages). **Checked:** the button through the page code
    and the coordinator, before and after the deploy (40 of 40, 4 of 4 workers, euro prices); the dashboard's tracker on
    both reports (10 symbols and the index); the history's name and symbol and "run again"; the access rules; **all 14
    existing screeners proved unchanged** with the shared report writer. **Not done:** the autopilot does not buy from
    it (a line in `SCREENERS` and market hours in `stockiq-ai-trader`, if the owner wants that); `prove.py`'s two-year
    replay for the new market (the worker code did not change; skipped to spare this machine's Yahoo allowance, which
    the daily run had already hit that morning); `lambda-url-mapping.json` was regenerated afterwards. **The other
    eleven "Coming Soon" buttons** are each the same steps: a list, a line in `groups.py`, the workers, the coordinator,
    an entry with a `report`, a button, five dashboard lines, the wording's count.
  - A second session worked on the practice portfolio at the same time (its own notes are above or below this). Its
    uncommitted files were left alone, and the dashboard's DAX entries were staged only after it had committed.
  - **Three more screeners the same evening: France CAC 40, Netherlands AEX, Canada TSX 60** (the owner: "sure go ahead",
    "do what makes sense to you"). The same steps as the DAX 40, and this time **the page needed data only**: three
    entries in `screeners.js`, three buttons, no change to `analysis-functions.js`. 13 workers created
    (`stockiq-europe-4-3-worker` 4, `stockiq-europe-4-4-worker` 3, `stockiq-americas-6-1-worker` 6); coordinator
    `0Fmz+0EN…` (rollback zip `…_before_batch2_20261013.zip`); the dashboard's lines; the wording now says 19 screeners
    and names the markets by region ("US, Canadian, UK, European, Australian and Japanese indexes"), so that a further
    European index changes only the count and the list on the home page's card. Website commit `7b5d4f05`.
    **What the lists taught:** the English Wikipedia page for the AEX still showed 25 members as of 2024, while the
    index has had 30 since September 2025: **check the page in the market's own language and the date it gives**; three
    of the 30 needed another symbol at the price source (`EXO.AS`, `SHELL.AS`, `WDP.BR`: the proxy answers 500 for a
    symbol it does not know, which is how they were found). The TSX 60's own index (`^TX60`) is not at the price
    source, so its Top 10 comparison uses the S&P/TSX Composite (`^GSPTSE`). Canadian share classes take a dash
    (`RCI-B.TO`, `BIP-UN.TO`). **Checked:** each button through the staged and the deployed page code and the
    coordinator (40 / 30 / 60 results, every worker answering, euros and Canadian dollars), the dashboard's tracker on
    the page's and the coordinator's report of each, the history names and "run again", the access rules, the browser
    tests. **A trap for the tools:** `generate-lambda-url-mappings.sh` takes about half an hour and rewrites
    `lambda-url-mapping.json` in place; while it runs `page_run.js` and `screener_equiv.js` cannot start. Do not start
    it before a batch of tests; the tracker check on a page report can be done without the map by letting through
    only the new workers' addresses (as was done here).
    **Still "Coming Soon" after that batch:** Switzerland, Italy, Spain, India, South Korea, Hong Kong, Singapore, Brazil
    (Italy and Spain followed the same day: the entry at the end of this log). The autopilot buys from none of the new ones.
  - **The S&P 500 line reviewed at the owner's word ("looks good review it make sure its ok").** Opened the live Practice
    portfolio tab as his account, read-only, at desktop and phone width (new tool `check-tools/live_practice_check.js`,
    kept): the line, the two key lines, the one line, the figures table, the three views, the chat summary all right on
    his real figures; no script error; nothing sticking out; the fund's prices asked for with no range, as they should
    be for an account three days old. **One thing found and fixed:** the breakdown's fund card read "ahead of the fund"
    while the graph read "behind it" (different sums, both true); the card now says it counts only what is still held
    (`practice-portfolio.js?v=35`, words only). Written down as a limit, not changed: between two closes both lines are
    straight, so a weekend figure is an in-between value. Seen and left (older than this change): the date labels under
    the graph repeat a day when the account is three to five days old ("11 Oct, 11 Oct"). **A slip in the session's own
    bookkeeping:** a notes edit stopped on a line the other session had changed, and the commands after it still ran, so
    commit `4e4556b` says "Notes" and holds none; they are in the commit after it. Put `set -e` or `&&` between a
    notes edit and the commit that depends on it.
  - **"View Pricing Plans" on the home page stopped too far down** (the owner sent a picture, 12 Oct; live 13 Oct 2026, 11:45
    UTC). The link is a plain anchor to `#pricing`, so the browser put the section's top at the top of the window, under
    the fixed trial banner and menu (41px + 64px = `--body-padding` 105px; 64px on a paid account): the heading and the
    first lines were hidden. One style on the section in `index.html`: `scroll-margin-top: 130px`. Live file equals the
    local one. **Not seen in a browser:** the home page comes out blank in headless Chrome here (served locally and
    live), so the landing place was first by the arithmetic only. **The owner then said it still went past the heading, so
    it was measured in a real browser** (new tool, kept: `node check-tools/pricing_link_check.js`; it opens the live home
    page under an ordinary browser name, clicks the link with a real mouse click and says where the heading stops against
    the header; `SIZE=390x844`, `DIRECT=1` (arriving at `index.html#pricing` from another page), `PAID=paid|unpaid`,
    `WEB=<folder>` for a staged or local copy, `WAIT=<ms>`, `SHOT=<file>`). On the live site the section stops 24px
    below the header and its heading 65px below, clicked 0.8 to 8 seconds after the page opens, at 1440 and 1100 wide,
    at phone size, opened directly at `#pricing`, signed in with and without the paid note, and from the local folder;
    the page as it was before the fix fails the same check with the heading 65px under the header (his picture). **Not
    reproduced: what he saw after the fix; he was asked to reload and, if it persists, to say which browser and whether
    it is stockiq.tech or a local preview** (section 9).
  - **What he had seen was this: "it scrolls down differently depending if the banner is showing or not"** (his words, later
    the same day; live 13 Oct 2026, about 15:55 UTC). A fixed 130px left 24px of room under the header with the strip
    showing and 65px without it (a paying visitor: 64px of header). The room now follows the header's own height: a rule
    in `index.html`'s first style block, `#pricing { scroll-margin-top: calc(var(--body-padding, 105px) + 24px); }`, and
    20px on a phone (up to 768px), where the header slides away while the page scrolls down; the inline 130px is gone.
    `--body-padding` is the height of the fixed header, set in the head of every page (section 11, the banners): **use it
    for any other in-page link to a section of a page with this header.** `pricing_link_check.js` now judges the room
    itself (15 to 40px under the header; where the header has slid away, within 60px of the top) and failed on the
    first fix for a paid visitor (65px). Live after the deploy: 23px with the strip, 23px without it, 20px on a phone,
    23px opened directly at `#pricing`. **Lesson: the first check passed because it only asked whether the heading was
    in view; he was looking at the size of the gap. And a visitor's state (strip or no strip) is a case to try every
    time on this site, since the header's height depends on it.** A second slip, in a test loop: zsh does not split
    `${c##*:}` into words, so "SIZE=… PAID=paid" went in as one setting and three cases silently repeated another's
    result; pass each setting by itself.
  - **A page starts the same distance under the header with or without the strip** (live 13 Oct 2026, 16:20 UTC), at the
    owner's word: "a few things change the location of things due to that banner showing or not, eg on the dashboard the
    'your dashboard' is lower down when the banner isn't showing". Every page with the header was measured for three
    kinds of visitor (anonymous, signed in without a plan, with the paid note), desktop and phone, with a new tool, kept:
    **`node check-tools/header_room_check.js [pages]`** (`WEB=<folder>` a staged copy, `SHOTS=<folder>` pictures of each
    top; pages served from this machine, every other request answered locally, nothing written). What it found, all on a
    desktop only (a phone never has the strip):
    - **Dashboard:** for a paying visitor the head script set `--body-padding` to 105px although the strip is hidden and
      the bar is 64px, so "Your Dashboard" stood 60px under the header instead of 19px. Now 64px above 768px wide
      (a phone's layout counts on the 105px: with 64px there the title went under the bar, which the tool caught before
      anything was live). The room left when the page scrolls to `#upgrade` or the history
      (`scroll-margin-top: 120px`) follows the header as well: `calc(var(--body-padding, 105px) + 15px)`.
    - **Stock pages, the other way round:** they leave 105px whoever is looking, so with the strip showing the title sat
      4px under the bar and without it 45px. Fixed without regenerating them: one rule in `styles.css`,
      `main:has(> div > #live-ticker) { margin-top: var(--nav-top, 0px) !important; }` (the pages' own script sets
      `--nav-top` to the strip's 41px or to 0; `#live-ticker` is only on stock pages). 45px either way now. **The
      template in `generate-stock-pages.py` was not changed and does not need to be; if it ever sets a top margin on
      its `<main>`, this rule still wins.** A browser without `:has()` (before 2022-23) shows it as before.
    - **Sign-up page:** for a paying visitor the bar hung 41px below the top with nothing above it; its script now sets
      `--nav-top` 0 and `--body-padding` 64px for that case on a desktop.
    - Right already: the home page, the analysis page, and the 15 pages without the strip.
    **The rule to keep:** the header is 105px tall with the strip and 64px without it, on a desktop; `--nav-top` and
    `--body-padding` must say so together, in every page's own head script (they have to be set before the page is
    drawn, which is why this is not in one shared script). Run `header_room_check.js` after any change to a page's top.
    **Seen and left:** the menu bar covers the last 4px of the strip on every page that has it (the strip is 45px tall,
    the bar starts at 41px); `#ap-coming` in `practice-autopilot.js` still has a fixed `scroll-margin-top: 120px`.
    `pricing_link_check.js` takes `PAGE=` and `TARGET=` now (`PAGE=dashboard.html TARGET=upgrade DIRECT=1 PAID=paid`: 14px
    under the header for both kinds of visitor). **Not checked: a real signed-in account (made-up sessions), a real phone.**
    Website commit `e6e1fd3a`; to go back, `git revert` it and upload the three files. **The other window deployed the
    last four screeners while this was staged, which changed `dashboard.html`: the fingerprint check would have stopped
    the stale copy; it was staged again on the new file.**
  - **Two more screeners: Italy FTSE MIB (40) and Spain IBEX 35 (35)**, live 11:47 UTC, 13 Oct 2026, by the same steps and
    again **data only on the page** (two entries in `screeners.js`, two buttons). 8 workers created
    (`stockiq-europe-4-5-worker-1..4`, `stockiq-europe-4-6-worker-1..4`); coordinator `8QIBorce…` (rollback zip
    `…_before_batch3_20261013.zip`); the dashboard's lines (keys `italy_screener`, `spain_screener`; indexes
    `FTSEMIB.MI` and `^IBEX`, both at the price source); the home page says 21 screeners, About and the FAQ name the
    two. Website commit `74a6947d`. **The Spanish list came from the exchange itself:** Wikipedia's IBEX 35 tables were
    of September 2024 (English) and October 2023 (Spanish). The Madrid exchange's site loads its tables from
    `https://apiweb.bolsasymercados.es/Market/v1/EQ/ListedCompanies?tradingSystem=SIBE&page=N&pageSize=50` (122 companies
    in three pages, read-only, no key), and each row's `indices` names the indexes the share is in ("IBEX 35®, …"):
    35 rows carried it. Yahoo's symbols are the exchange's tickers with `.MC` (ArcelorMittal is `MTS.MC` there, `MT.AS`
    in the CAC 40 and AEX lists). Italy's are the Wikipedia tickers as they stand (`.MI`; Stellantis `STLAM.MI`,
    STMicroelectronics `STMMI.MI`). All 75 symbols answered at the price source. **Checked:** both buttons through the
    staged and the deployed page code (40 and 35 results, every worker answering, euros), both through the coordinator
    run locally and then live (40 and 35, EUR), the dashboard's tracker on the page's and the coordinator's report of
    each (10 shares and the index every time), every inline script of the three pages. **Not checked:** the access
    rules and the browser tests were not run again (no code changed, only data); a real signed-in browser.
    **Nothing in the dashboard or the page tests the word "FTSE" alone** (the UK screener is matched on "UK FTSE" and
    its index on "FTSE 100"), so "Italy FTSE MIB" is not taken for it; keep it that way.
    **Still "Coming Soon" (six):** Switzerland (SMI), India (BSE Sensex), South Korea (KOSPI), Hong Kong (Hang Seng),
    Singapore (STI), Brazil (Bovespa). **Each of these needs more than data:** Swiss francs and Brazilian reais have no
    sign in the money rule (a price would print as "CHF 85.20" / "BRL 12.30", which the dashboard's tracker does not
    read: add a sign to the three money tables and to both tracker patterns, section 8b); Hong Kong symbols are numbers
    (`0700.HK`); "KOSPI" has about 900 members, so the button needs a decision on which list (KOSPI 50 or 200); India's
    shares are at two exchanges (`.BO` / `.NS`). `lambda-url-mapping.json` was regenerated after this batch (and again after the next).
  - **"Download from your dashboard" under a screener's results opens the Reports tab** (15:38 UTC), at the owner's word:
    the link went to `dashboard.html`, which opens the tab that was open last (he likes that for "View Dashboard"), so
    after a look at the practice portfolio the download was a tab away. The five links in `analysis-functions.js` now
    say `dashboard.html#reports`; the dashboard already opened Reports for that address without touching the
    remembered tab, so nothing changed there. Checked: the dashboard's own tab script run with a stand-in page (six
    cases: `#reports` with each other tab remembered opens Reports and the remembered tab stays; a plain visit opens
    the remembered tab); four kinds of screener through the changed script (reports as before); the live file has the
    five links. Website commit `b2740f4f`. **Not checked: the click itself in a signed-in browser.**
  - **Two more screeners: Hong Kong Hang Seng (95) and Singapore STI (30)**, live 15:40 UTC, 13 Oct 2026; data only again.
    13 workers created (`stockiq-asia-5-8-worker-1..10`, `stockiq-asia-5-9-worker-1..3`; `5-6` and `5-7` stay kept for
    India and Korea, as the guide names them); coordinator `UXE1lzC4…` (rollback zip `…_before_batch4_20261013.zip`);
    the dashboard's lines (`hongkong_screener`, `singapore_screener`; indexes `^HSI`, `^STI`); the home page says 23
    screeners and "Asia" where it said "Japan", and the sentences that list regions say "Asian" for "Japanese" (home
    page, two guides); About and the FAQ name the two. Website commit `f261a57b`.
    **The lists:** the Hang Seng has grown through 2026 (88 in January, 90 in March, 93 in June, 95 from 7 September);
    the English Wikipedia page still had January's 88, **the Chinese page (恒生指數) the 95 with the date**: the lesson of
    the AEX a second time. Hong Kong symbols are the stock code as four digits with `.HK` (`0005.HK`, `9988.HK`). The
    STI list is of 2 May 2026 and was confirmed against FTSE Russell's notices (no member changed at the June or the
    September review). **Three STI members are quoted in US dollars** (`D01.SI`, `H78.SI`, `J36.SI`): the money rule
    takes each share's own currency, so they print "$3.24" beside "S$6.52", as three FTSE 100 shares do. Names follow
    one more rule here: **no "&" in a name** ("J and T Global Express", "HK and China Gas"), because a report is put on
    the page as HTML and the tracker loses a line with an "&" in it (section 8b, "Trading signals"). All 125 symbols
    answered at the price source. **Checked:** both through the staged and the deployed page code (95 and 30 results,
    13 of 13 workers), the coordinator run locally and live (95 HKD; 30 SGD and USD), the tracker on the page's and the
    coordinator's report of each (10 shares and the index), two existing screeners through the live coordinator
    afterwards (FTSE MIB 40, Nikkei 225), every inline script of the three pages. The deploy waited for the autopilot's
    15:40 run to finish (its log line "scheduled check: … users were due"), since that run calls the coordinator.
    **Still "Coming Soon" (four), each needing code as well as data:**
    1. **India (BSE Sensex):** the list is ready and current (30; the December 2025 change, IndiGo for Tata Motors PV,
       is the latest; the June 2026 review changed nothing), every symbol answers with `.BO` in rupees, `^BSESN` is at
       the price source. **One symbol is `M&M.BO`:** the tracker's symbol pattern has no "&", the report would need it
       escaped, and a price lookup needs it encoded in the address; Yahoo has no other symbol for it (`500520.BO`
       answers nothing). So: escape the symbol where a report prints it, allow `&amp;` in both tracker patterns (and in
       `page_run.js`), encode the symbol in the tracker's and the practice portfolio's price requests, and test with
       `tracker_run.js` before anything else.
    2. **Switzerland (SMI, 20)** and 3. **Brazil (Bovespa):** the money rule has no sign for CHF or BRL, so a price would
       print "CHF 85.20" / "BRL 12.30", which the tracker does not read. Add a sign (or teach the tracker the
       "CODE number" form) in the three money tables and both tracker patterns.
    4. **South Korea (KOSPI):** the button says "KOSPI", which has about 900 members: decide the list first (KOSPI 50 or
       KOSPI 200; 200 would be 20 workers).
    The autopilot buys from none of the eight screeners added on 13 Oct.
  - **The last four screeners: Switzerland SMI (20), India Sensex (30), South Korea KOSPI 200 (200), Brazil Bovespa (76)**,
    live 16:11 UTC, 13 Oct 2026, at the owner's word ("please resume and complete all the screeners"). **No button says
    "Coming Soon" any more: 27 screeners** (26 share screeners and crypto). 34 workers created
    (`stockiq-europe-4-7-worker-1..2`, `stockiq-asia-5-6-worker-1..3`, `stockiq-asia-5-7-worker-1..21`,
    `stockiq-americas-6-2-worker-1..8`); coordinator `979X4yAm…` (rollback zip `…_before_batch5_20261013.zip`);
    website commit `25729035`. Unlike the eight before, these needed code:
    - **A symbol with an "&"** (India's `M&M.NS`). Reports are put on the page as HTML and the dashboard's tracker clears
      everything from an "&" to the next ";". Now `formatMarketResult` writes a symbol through `reportText` (three
      lines), the coordinator writes `&amp;` in its two report lines, and `parseScreenerTop10` reads `&amp;` as "&" and
      allows it in a symbol. Price requests were already encoded (`encodeURIComponent`), except one in
      `trackPerformance`, which is now. **The old parser read that line as "M" (another company).**
    - **Francs and reais.** The money rule has no sign for them and writes "CHF 77.30" / "BRL 56.86" (page,
      coordinator and single-stock report alike, untouched). The tracker now reads that form (section 8b, "Dashboard
      performance tracker"). **A sign for reais ("R$") would be one entry in each of the three money tables**; left
      for a time when the report function is being changed anyway (it holds a key in its code).
    - **Proved not to disturb what exists:** the old and the new parser run on the 52 saved reports of every existing
      screener in `check-tools/` (read the same), and on a made-up report with every price form (pence, A$, HK$, C$,
      €, ₹, ₩, CHF, BRL, a signals line with "AT&T"); seven existing screeners through the old and the new page script
      (`screener_equiv.js`: the same requests, reports and CSV). `page_run.js` carries the new pattern.
    - **The lists, and what they taught.** *SMI:* the newest full list was a year old; SIX's review of September 2026
      was found by a search and applied (two in, two out). Roche's Genussschein `ROG.SW` did not answer at the price
      source, so the list has the bearer share `RO.SW`: the same company, another share class; put `ROG.SW` back if it
      answers again. *Sensex:* **Yahoo's Bombay data is too patchy for the worker** (it returned nothing for
      RELIANCE.BO and M&M.BO while the price proxy answered for both: **a price at the proxy does not prove the worker
      can score a share; run `workers/stock_worker.py` on a few before choosing a suffix**); the NSE listings work for
      all 30. *KOSPI:* the button said "KOSPI" (about 900 shares); the exchange's lists need a login since some time in
      2026 and Wikipedia's KOSPI 50 is of 2022, so the list is **the KOSPI 200 as an index fund holds it today**
      (`https://www.samsungfund.com/api/v1/kodex/product-pdf/2ETF01.do?gijunYMD=<yyyymmdd>`: the KODEX 200's holdings,
      `itmNo` is the six-character code; add `.KS`). Codes can hold letters now (`0126Z0.KS`). *Bovespa:* the exchange's
      own portfolio (`sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/<base64 of
      {"language":"en-us","pageNumber":1,"pageSize":120,"index":"IBOV","segment":"1"}>`): codes with `.SA`.
      Korean and Brazilian company names were made from the price source's names by a rule (legal forms off, plain
      ASCII, 22 characters) with about forty put right by hand.
    - **Checked live:** the four buttons through the deployed page code (20, 30, 200, 76 results; every worker
      answering) and six older ones (DAX 40, Nikkei 225, Dow 30, FTSE 100, ASX 200, S&P 500); the live coordinator for
      the four and three older ones; the tracker on the page's and the coordinator's report of each of the four (10
      shares and the index: `^SSMI`, `^BSESN`, `^KS200`, `^BVSP`). **Not seen: `M&M.NS` in a real top 10** (it was not
      among the day's ten; the path was tested with a made-up line), **a signed-in browser, a phone.**
    - The home page says 27 screeners and "the Americas"; the sentences that list regions add "Brazilian"; About and
      the FAQ name the four. (The autopilot could buy from none of the twelve at that moment; it can since 16:32 UTC the same day: the entry below.)
      `lambda-url-mapping.json` regenerated once more afterwards (1,056 functions).
  - **The autopilot can buy from every screener, grouped by region; the Screeners menu renamed; quick set-ups have an Undo**
    (16:32 to 16:39 UTC, 13 Oct 2026), at the owner's word: "now we have more screeners the dashboard autopilot needs
    updating to include all screeners… maybe change it to US markets, then have a Europe markets etc."
    - **`stockiq-ai-trader` `i9WtL7oP…`** (rollback zip `…_before_autopilot_regions_20261013.zip`): `SCREENERS` has all 27,
      in five groups that are the menu's sections (section 8c, the settings table). **This changes how a budget is
      spread**: a group is a region now, so Sydney and Tokyo share Asia-Pacific's share where each had its own, and
      London shares Europe's with six other exchanges. Hours and names for seven new markets (`eu`, `hk`, `in`, `kr`,
      `sg`, `ca`, `br`); the new currencies need nothing (`fx_pair` already turned any other currency the yen's way;
      the seven rates are at the price source). Tests: 447 function (5 new: the groups, each exchange open in the
      middle of its session in summer and winter and shut outside, old share names carried over, an even spread over
      five regions, the currencies), 212 panel, the panel-versus-function comparison clean. `dashboard_page.py`'s
      stand-in has the real 27 screeners, and an `undo` step. **Seen live eight minutes later:** the 16:40 check-in
      bought CVE.TO from the Canada TSX 60, in Canadian dollars at the day's rate ($1,863.86 put in).
    - **The Screeners menu** (19 pages; website commit `509d502c`): "Asia Markets" is "Asia-Pacific Markets" (the owner
      asked whether Australia belongs under Asia: it is conventionally Asia-Pacific) and "Other Markets" is "Americas
      Markets" (Canada and Brazil; the US keeps its own section). **Only the labels changed: the links are still
      `analysis.html?option=5` and `?option=6`, and nothing in the code is keyed on the names.** On the analysis page the
      section headings and the option list follow, the Australian and UK buttons are written like the rest, and six
      markets are listed as "Coming Soon" (Euro Stoxx 50, Sweden OMX 30, China CSI 300, Taiwan TWSE 50, New Zealand NZX
      50, Mexico IPC). The stock pages' template has the new names; **the 3,467 stock pages keep the old two labels
      until they are next regenerated** (their links work).
    - **`stockiq-ai-chat` `1BYRMwTA…`** (rollback zip `…_before_menus_20261013.zip`; 22 checks): its list of screeners
      (it named ten), the autopilot's five groups, the quick set-ups' Undo. Asked two real questions afterwards:
      it knew Germany and Brazil are covered, and the Undo.
    - **The quick set-ups, and what happened to the owner's settings.** He sent a picture of the panel with only "Crypto"
      ticked: "i think you broke something". The diary showed the three quick set-up buttons pressed at 16:11:32 to
      16:11:40 UTC; each replaces the screeners ticked and the pace, and there was no way back ("i can't unclick
      it"). **The panel now says what a quick set-up replaced and offers "Undo: put my settings back".** His settings
      were put back twice from the diary's record (16:21: the nine screeners, every 3 hours, 10 days; 16:33: the pace
      only), and **both times his next click on the page saved over it within seconds: he was at the panel, pressing
      the quick set-ups again and ticking the new screeners.** He ended on the "Quick coin trading" pace (a check-in
      every 30 minutes, a holding kept at most 6 hours) with 17 screeners, and the 16:40 check-in sold five holdings
      under it (FANG, CTVA, DDOG, LINC at the 6-hour limit, DAVE by the AI review: about $18 down in all) and bought
      one. He was told what the pace is and how to set his own back. **Lessons: (1) do not write an account's settings
      while its owner is at the page: say what they are and what they do, and let him change them; a save from
      outside is undone by his next click, and he has to be told twice. (2) Trades made from 16:11 UTC on 13 Oct were
      made under changing settings: a review must not read them with the days before.** `autopilot_review.py`'s part 1
      lists the changes.
    - **A limit met on the way:** CloudFront allows 15 wildcard paths in progress at once; a cache clear for 19 pages
      written as `/page.html*` was refused after the uploads had been made. A page has no `?v=` forms: clear it by
      its plain path, and keep the `*` for scripts.
    - **Not checked:** the logged-in dashboard itself, a phone. **Not done:** `dashboard.html` still asks for
      `practice-autopilot.js?v=45` (another session had the page staged; browsers keep a script five minutes, so the
      change arrives anyway): raise it to 46 at the next change of that page.
  - **Shortcuts for the screeners in place of the quick set-ups; a scheduled check-in waits for settings to settle**
    (16:59 to 17:01 UTC, 13 Oct 2026), after the owner asked for a click on "US markets" to tick everything beside it,
    called the quick set-ups "pretty useless", wondered whether they belong near the screeners or should go, and asked
    whether his clicking about "breaks anything in the automation". **What was decided, since he left it to the
    session ("do what makes sense… keep it consistent and straight forward"):**
    - **The three quick set-ups are removed.** They changed the pace and the level as well as the screeners, which is
      what made them dangerous; the risk level already sets the pace by itself ("Let the risk level set all three").
      What a user does want quickly is to tick screeners, so the card "Screeners it buys from" has **shortcuts that
      change only what is ticked** (section 8c, "What the owner sees"): "Main index of every country", "Clear all", and
      a click on a market's name. An Undo follows each.
    - **`stockiq-ai-trader` `wLHHlexH…`: the waiting rule** (`SETTLE_MINUTES`; rollback zip
      `…_before_autopilot_settle_20261013.zip`). The honest answer to his question was: a click saves at once and
      trades nothing by itself, **but the next check-in acts on whatever the settings are at that minute**, and that
      had just cost him five sales. Now a scheduled check-in waits until the settings have been left alone for 10
      minutes. What a change still does at once: changing the budget or "Build up to it over" starts the build-up
      again; changing "Checks in" moves the next check-in; un-ticking a screener sells nothing (what it holds from it
      stays until sold).
    - **His other questions.** *Is the ASX right under Asia-Pacific?* Yes: that is the usual name for the region that
      takes in Australia. *Do the S&P 500 and the S&P 1500 overlap, and can it buy the same share twice?* They overlap
      (the 1500 holds every share of the 500, 400 and 600), and no: `shortlist` passes over a share it already holds
      and keeps a share that is on several ticked lists once, at its best place among them. Ticking both adds little;
      it does no harm. The card says so.
    - `stockiq-ai-chat` `9K5HRpiz…` (rollback zip `…_before_shortcuts_20261013.zip`): its guide describes the shortcuts,
      the waiting rule and the overlap. **A test caught a word on the way:** the buttons were first called "Quick
      picks", and the chat's own test refuses "picks" in its guide (the wording rule of section 10). They are "Shortcuts".
    - Tests: 451 function (4 new: settling, the scheduled run that waits and then runs, "Check in now" that does not),
      216 panel (the old quick set-up checks replaced by seven for the shortcuts, the market names, the Undo and the
      notes), 22 chat, the panel-versus-function comparison clean. Looked at in a headless browser at desktop width
      and in a 390px frame (nothing sticks out); the market-name column was widened for "Asia-Pacific markets".
      `dashboard_page.py`'s `preset` / `undo` step now exercises the shortcuts.
    - **The owner's settings at the end** (he asked for them "back how it was"): Balanced, 50 holdings, built up over 1
      day, a check-in every 3 hours, holdings kept up to 10 days, 17 screeners (one main index a country and crypto),
      10 holdings a region. Set from outside once more at his word, at 16:48 UTC, after he had stopped clicking.
    - **Not checked:** the logged-in dashboard itself; a phone. **To see for real:** the log line "settings just changed,
      left for the next run" the first time he changes a setting within ten minutes of :10 or :40.
  - **The breakdown's words** (13 Oct 2026, late; `practice-autopilot.js?v=47`, website commit `acceca8b`): the owner did not
    know what "Ended up" meant ("oh it means ended up made money. maybe change it to winners?") and looked in "By who
    chose" for a trade he had made by hand. The column is "Made money" in the breakdown and the progress table; "By
    place in the ranking when bought" is "By place in the screener ranking when bought"; a line under the breakdown says
    it counts only the autopilot's finished trades and where his own are. 216 panel checks. The chat's guide uses none
    of those words and needed no change. **The session ended here.**

- **17 Oct 2026** (a session opened four days later):
  - **The update given:** account about $99,334; 51 finished trades, 15 made money, average -1.13% a trade (± 0.40, clearly
    down); month 1 goal: trades on course (51 of 100), the average and the account not yet. No faults in four days. By
    itself it rested the crypto screener until 29 Oct (21 coin trades, -$1,819) and ended the buying-order trial without
    keeping it (furthest above the 52-week low -1.81% against -0.54% as ranked). The one group of 30 or more clearly down:
    sales by the AI review (31, -1.46%; the four looked at afterwards went on rising about 7%).
  - **At the owner's yes ("sure go ahead") to the four improvements offered:** (1) "Sell early on the AI model's review"
    switched off and (2) the coin screener unticked (his settings, through the function's save, at 04:31 UTC; the budget
    now goes over the four share regions, 13 / 13 / 12 / 12 holdings); (3) the pages' polling cut (the next entry); (4) the
    Admin page (section 8c, "The owner's Admin page").
  - **The pages ask for market data far less often** (04:53 UTC; `index.html`, `dashboard.html`). The home page fetched each of
    its four movers lists **every second** while a tab was open and in use (`setInterval(…, 1000)`: about 14,400 calls an
    hour from one tab) and its market widgets every 10 seconds; the dashboard fetched its ticker every 10 seconds, twice
    over (two timers). Now once a minute, and not while the tab is hidden (the home page's checks were kept; the dashboard
    gained one). `sidebar.js` (other pages, every 5 minutes) and `stock-prices.js` (stock pages, every 5 seconds, paused
    when hidden; few calls) were left. The phone-sidebar browser test passed on both pages (102 checks). **To see:** the
    owner's daily usage report over the next days (`ticker-data-fetcher` was 19,578 a day, the movers about 18,200).
  - **The Admin page is live** (04:54 UTC; `stockiq-ai-trader` `vSGWQgIB…`, rollback zip `…_before_autopilot_admin_20261017.zip`;
    `admin-panel.js?v=1`, `dashboard.html`). Checked live: another account gets 403; the owner's first weekly review was
    written through it (51 trades, -$2,268.78, clearly down; the AI review's sales the one clearly losing group; no
    proposal, as that switch was already off). 459 function checks, 9 page checks. **Not checked:** the signed-in
    dashboard itself (the tab appears only for his account); the health line, which the next scheduled run writes.
  - The daily deploy of that morning met Yahoo's limit again ("No price data: 2179, kept yesterday's snapshot: 774"); nothing
    was de-indexed (958 indexable).
  - **A second window, the same morning: "something is off" on the Practice portfolio, and clearer profit and loss.** The owner
    pasted the top of the tab. Every figure was checked against his record and live prices: all correct (the S&P 500 fund
    $98,032.29 is SPY's close of 9 Oct, $778.57, to 16 Oct, $763.25; "Today" +$1,005.52 is the sum of the 40 holdings' own
    day moves, each equal to the price source's day change, mostly 6532.T +17.25% at Tokyo's ¥1,500 daily limit and oil
    shares). What looked off: the same "Today" with two percentages (of the account and of the holdings), and the fund at
    -1.97% and -1.42% (the whole account since the start, and only what is still held). Found on the way, a real fault: a
    resting screener's market kept its share of the budget (section 8c, "How the budget is spread"). At his word ("go
    ahead with what makes sense… if that dashboard… can be more clear do that too"), live at 05:14 UTC (`stockiq-ai-trader` `6gcerpj3…`, rollback zip `…_before_autopilot_clarity_20261017.zip`; `stockiq-ai-chat` `pCq5uR9L…`, `…_before_clarity_20261017.zip`; the live answer for his account: 13 / 13 / 12 / 12, no error in the log): the budget
    fix (`stockiq-ai-trader`, built as `pending-clarity/patch_lambda.py` on the Admin version), the breakdown as one
    profit-and-loss table (`practice-portfolio.js?v=36`), the panel's copy of the split (`practice-autopilot.js?v=48`), the
    chat's guide (`stockiq-ai-chat`). Tests: 464 function, 217 panel, 130 portfolio, 22 chat, the comparison clean (5,077
    splits). Tried on the live page as his account before the deploy (`live_practice_check.js LOCAL_PP=… OPEN_MORE=1`, new),
    desktop and 390px. **Lesson: two windows staged the same function an hour apart; the second rebuilt its change as a
    patch script and applied it to the first one's live code, so neither undid the other.**
  - **Hand buys and sales wait for the share's market to open** (05:20 UTC; `practice-portfolio.js?v=37`, `stockiq-ai-chat`
    `hGAVqC3Y…`, rollback zip `…_before_closed_20261017.zip`), at the owner's word after he sold TLS.AX on the Saturday
    (section 8c, "What the owner sees"). Seen live on his account the same morning: all 39 holdings' buttons read "Market
    closed". 137 portfolio checks, 22 chat. **Not checked:** a signed-in browser, a phone, the 🎯 popup's button for real.
  - **The Admin page in colour, and the portfolio's top reworked** (05:49 UTC; `admin-panel.js?v=3`, `practice-portfolio.js?v=38`,
    `dashboard.html`, `stockiq-ai-chat` `p33YPRp7…`, rollback zip `…_before_adminlook_20261017.zip`), at the owner's word (section 8c,
    "The owner's Admin page" and "What the owner sees"). The review's button had been explained the same morning ("Write a
    fresh one now", v2). Tests: 9 Admin page, 137 portfolio, 22 chat. Looked at in a headless browser with the live Admin
    answer (light and dark) and on the live Practice portfolio tab as his account, read-only (account $99,643.23, ▲ $1,610.94
    against the S&P 500 fund's $98,032.29). **Not checked:** a signed-in browser, a phone width for the Admin tiles.
  - **THE SCREENERS' SCORE REPLACED** (the owner: "go ahead and look into improving it", then "my answer as almost always its a
    yes"). The study that found the old score worse than its own list, the trend score built and proved (section 7b), live on
    all 741 share-screener workers at 10:55 UTC and the six public pages reworded. Same day: the Admin page shows this month's
    AWS bill and Lambda calls (a read-only role policy `stockiq-usage-read` for Cost Explorer and CloudWatch; one Cost
    Explorer question a day, $0.01) and the margin of error in plain words ("the real average is probably between -1.93% and
    -0.37% a trade"); `check-tools/session_start.py`, the first command of every session (top of this file). The owner, on
    being asked things a session should have found: "You aren't smart or a good AI if i have to manually find problems or
    think of improvements" (the instruction at the top of this file). Bill on 17 Oct: $0.56 this month; Lambda calls 451,952,
    5,182 the day before (the polling cut: about 66,000 a day before it).
  - **Later the same evening:** the AI model's early sales taken out (section 8c, "What the owner sees"); the Admin page's
    Improvements card and its cost colours; `check-tools/lists_check.py` (every screener's list: page and coordinator alike, no
    duplicates; monthly, every symbol's prices and the members against the index's own source where a script can read it:
    Nasdaq for Stockholm, BlackRock's NAFTRAC holdings for Mexico, the KODEX 200 fund for Korea, B3 for Brazil, the Madrid
    exchange for Spain; first full run clean); the screener summaries in plain words ("Average score: +0.7 on a scale of about
    -3 to +3 (Slightly positive on average)", "Scored: 76 of the 76 stocks in the list (100%)"; the Nikkei report said 210 for
    225); the registers `site_parts.py` and `experiments.py` (top of this file); the cost cuts and the budget `stockiq-monthly`
    (top of this file, "THE COST RULE"); the AI chat knows the trend score (asked live, it described it rightly). Rollback zips
    `stockiq-ai-trader_before_autopilot_{plan,costs2,usage,adminvalue}_20261017.zip`, `stockiq-ai-chat_before_{plan,chatscore}_20261017.zip`,
    `stockiq-screener-coordinator_before_{summary,mexico,newmarkets}_20261017.zip`.
  - **Improvements in two places, each for its reader** (the owner: "does this overlap with Improving its own rules … one is for
    everyone the other is just for me so perhaps the one for everyone a lighter version showing improvements only?"). It did
    overlap, and neither was complete: the autopilot tab showed only its own rule trials, in detail; the Admin card showed the
    site's register and not those trials. Now the autopilot tab's section is "How it is improving" (tested now, made, next; the
    detail folded) and includes the register's public items; the Admin page has an Overview and an Improvements view. The chat's
    guide has the new name, and no longer says the buying-order trial is running (it ended on 17 Oct, not kept). Found on the
    way: the panel's refresh only redrew when its fingerprint of the answer changed, and that fingerprint did not include the new
    list (fixed: `stamp`). Tests: 473 function, 218 panel, 14 Admin page, 23 chat. Rollback zips
    `stockiq-ai-trader_before_autopilot_improve_20261017.zip`, `stockiq-ai-chat_before_improve_20261017.zip`.
  - **Two boxes made plainly different, the holdings list shortened, the gap to the fund in percent** (15:25 UTC; website only:
    `practice-portfolio.js?v=40`, `practice-autopilot.js?v=55`, `admin-panel.js?v=8`, `dashboard.html`). The owner asked whether
    the autopilot tab's "Nothing needs you right now" and the Admin page's "Needs your yes" were duplicates: they are not
    (section 8c, "Two boxes that look alike"), so the Admin one is "Decisions for you" and each says what it covers. He also
    asked whether the "ahead by $1,610.28" needed a percent: it makes sense (the difference between the two returns, since
    both started with $100,000), so it has one. And he asked for the holdings to show the latest 10 with a way to the rest.
    His standing instruction to be corrected when wrong is in section 10. Checked: 141 portfolio, 218 panel, 14 Admin page
    checks; the live tab opened as his account, read-only, at 390px: "Holding (39)", 10 rows, "Show all 39 (29 more)",
    "▲ $1,610.28 (1.61%)", nothing broken. `live_practice_check.js` now reports the rows shown and the link. **Not checked:**
    a signed-in browser for the Admin page's new wording.
  - **The autopilot tab and the Admin page read as the owner reads them, and what confused fixed** (15:54 UTC; `stockiq-ai-trader`
    `UCQwgKlM…`, rollback zip `…_before_autopilot_clarity2_20261017.zip`; `practice-autopilot.js?v=56`, `admin-panel.js?v=9`,
    `dashboard.html`). The owner: "anything else confusing you want to optimise? and i'm tired of asking this!" Both pages were
    drawn from the site's own scripts with his real answers and read line by line. **Wrong:** the selling description still said
    the AI model reviews each holding and may sell it (switched off that morning); 26 holding plans still showed the review's
    old verdict ("AI review: keep"); a check-in note said "every screener you chose is resting" when only the coin screener
    was, on a Saturday with only coins open; the weekly review listed the AI sales as clearly losing with no word that they
    were already switched off. **Confusing:** "What happens next" had 51 rows, 39 of them alike; a release of the budget
    repeated its check-in; "Australian and Japanese and Korean and New Zealand"; "1 such moves"; the AI model's notes beside
    the breakdown with older counts (11 of 24 against 9 of 24); ✗ for a good change; "Not kept … Not kept"; menus of 51
    choices for a market's share; "Level 3" for Balanced and a chip for a switch that is always off. All put right (section
    8c). **And the routine that missed them is mended**: `check-tools/clarity_check.py`, run by session_start every session
    (top of this file); on the live site after the deploy it reads clean. Tests: 475 function, 222 panel, 15 Admin page.
  - **"↻ Refresh now" for the Admin page's AWS figures, and each figure's own age** (16:52 UTC; `stockiq-ai-trader` op `usage`,
    rollback zip `…_before_autopilot_usage2_20261017.zip`; `admin-panel.js?v=10`, `dashboard.html`): section 8c, "The owner's
    Admin page". Pressed once live: the bill read again, $0.59 (it had read $0.56 earlier that day), 465,897 calls. Tests: 478
    function, 17 Admin page. **The slip of 13 and 17 Oct once more:** the notes edit missed its anchor and the commit after it
    ran anyway; the notes went in a commit of their own. Chain a notes edit and its commit with `&&`, always.
  - **The bill read for free, and Cost Explorer stopped** (17:00 UTC; `stockiq-ai-trader` `15k0lkcP…`, rollback zip
    `…_before_autopilot_freebill_20261017.zip`, the role's old policy beside it; `admin-panel.js?v=11`). The owner, seeing Cost
    Explorer on his bill: "confirm this has stopped". CloudTrail's free history: 253 questions on 17 Oct from Python on this
    Mac, every one from `ai_trader_test.py` running the function's Admin code with real credentials (about $2.53); 2 from the
    function itself; the rest the AWS website (free). Now: the bill from the budget, Cost Explorer out of the code, out of the
    role's permissions, and refused by the tests. The last Cost Explorer question from this Mac was at 16:53:31 UTC.
  - **Five more screeners, the "Coming Soon" ones that had current lists** (the owner: "set those up and make sure they are
    adding to the autopilot etc so its like other screeners"): Euro Stoxx 50, Sweden OMX Stockholm 30, China CSI 300, Taiwan 50,
    New Zealand NZX 50 (the table in section 8b). 48 workers by `workers/create_group.py`; the coordinator, the page's entries and
    buttons, the dashboard's five lines each (the Top 10 comparison: `^STOXX50E`, `^OMX`, `000300.SS`, `^TWII`, `^NZ50`), the
    autopilot (Euro Stoxx and Stockholm on the European hours; China 01:35-06:55 UTC, Taiwan 01:05-05:25, New Zealand
    00:05-03:40, the part of its day after midnight UTC in summer and winter; the currencies needed nothing), the panel's
    "Main index of every country" (four of them; the Euro Stoxx 50 is not a country's), the AI chat's list, and the site's
    count (32) and lists. **The dashboard's tracker reads a symbol with two suffixes now** (`SWED-A.ST`: it read 3 of the
    Swedish top 10); the 47 saved reports read the same as before. Checked live: each button through the page code and the
    coordinator (every worker answering, the tracker 10 symbols each). **Mexico IPC followed the same hour** (the table): its list
    from the holdings of the NAFTRAC fund, after S&P and the exchange refused; **no screener is "Coming Soon" any more: 33 in all.** Rollback zips
    `…_before_newmarkets_20261017.zip` for the coordinator, the autopilot and the chat.
    **The slip of 13 Oct again:** a notes edit stopped on a line that did not match and the commit after it still ran, so
    commit `99b495d` says "Notes" and holds none; they are in the commit after it.

- **18 Oct 2026** (the same session, after midnight UTC):
  - **The owner's bar for real money and how to build until then** written down (section 8c, the part on real trades): ahead of an
    S&P 500 fund for more than a year by at least 5% a year; build as if it might go live, with no real-money parts until then.
  - **The themes part of the AI autopilot, a trial** (03:19 UTC; `stockiq-ai-trader` `K5Sj58Iv…`, `stockiq-ai-chat` `snC0Sn/V…`,
    rollback zips `…_before_autopilot_themes_20261018.zip` and `stockiq-ai-chat_before_themes_20261018.zip`;
    `practice-autopilot.js?v=57`, `practice-portfolio.js?v=41`, `dashboard.html`): section 8c, "THE THEMES PART". Tried before the
    deploy on a read-only copy of the owner's record with live prices and the real AI model, the clock set to Monday's US open.
    Found on the way: the model's answers are capped at 500 tokens, too few for a call on each of 14 funds; this read asks only for
    the funds it has a view on and may use 900. Tests: 499 function, 227 panel, the portfolio's, 24 chat; the panel-versus-function
    comparison clean with the trial off; the clarity check clean on the staged and the live page. **Not checked:** the first real
    buys (Monday 14:35 UTC), a signed-in browser, a phone.
  - **The screeners card points to the themes part, and the first shortcut explains the Euro Stoxx 50** (03:45 UTC,
    `practice-autopilot.js?v=58`, `dashboard.html`). The owner looked for the themes part under "Screeners it buys from" and
    expected "Main index of every country" to tick the Euro Stoxx 50. The themes part is not a screener, so the card now
    says what share of the budget it takes and links to it under Activity. The shortcut leaves the Euro Stoxx 50 out on
    purpose (it is not one country's index, and 47 of its 50 shares are already in the DAX, CAC, AEX, FTSE MIB and IBEX
    lists; it adds only AB InBev, argenx and Nordea), and now says so beside the button. 229 panel checks.
  - **The market shares say what they are a share of** (03:55 UTC, `practice-autopilot.js?v=59`). The owner: "is it taking 20%?
    hows that work when screeners say they are taking 100%". It does take 20%: while the themes part runs, the markets' shares
    are of the budget less that 20% (`share_part` in the function, `sharePart` in the panel), so 30 / 30 / 30 / 10% of $78,080,
    and the funds $19,520: together the $97,600. The card called them "Share of the budget", which read as 120%. Now "Share of
    the $78,080 for shares", "How the $78,080 for shares is spread", and the themes line says it is the other 20% of the whole
    budget (`ofWhat`). Found on the way: the new label applied the 80% twice ($6,400 for $8,000 in the test); `sharePart` is
    now safe to repeat (`partOfShares`). 230 panel checks.
  - **The themes part known across the site** (05:01 UTC; `stockiq-ai-trader` `s8Spsvuj…`, rollback zip
    `…_before_autopilot_awareness_20261018.zip`; `index.html`, `about.html`, `faq.html`): the weekly review's line, the review
    tool, the opening check, the public pages, the reference notes and five new questions (section 8c, "THE THEMES PART",
    "Where else it is known"). 502 function checks.
  - **"Today" on a Sunday, and the Admin page's figure that changed a second later** (05:17 UTC; `practice-portfolio.js?v=42`,
    `admin-panel.js?v=12`, `dashboard.html`). The owner: why does it say "Today ▲ $1,059.10" when the market has been shut over
    a day; and the Admin page showed $99,411, then $99,642. The day figure was right (each holding's last session, as a broker
    shows it) but the label was not: with every market it holds closed it now reads **"Last trading day … its markets are
    closed now: each holding's last session (latest prices …)"** (`summarize`: `dayClosed`, `dayLast`; the chat's summary
    likewise); with any market trading it is "Today". The Admin page shows "…" for up to 8 seconds while the Practice tab gets
    its prices (`LIVE_WAIT_MS`), and the function's estimate, said to be one, only if they do not come. Tried on the live
    page as his account before the deploy. 141+ portfolio checks, 18 Admin page checks.
  - **Holding more cash when the market looks risky: tested, not built** (the owner's idea: a gauge from very low to very high
    risk, more cash when high, or a reserve to buy after a big drop). `check-tools/replay/cash_study.py`,
    `results-cash-2026-10-18.txt` (the S&P 500 fund and the VIX, Aug 2022 to Oct 2026, rules written down first): every rule
    was behind all in the fund in both halves, even with cash earning 4%; the worst fall 2 to 5 points smaller. The gauge
    itself is in the experiments register as an idea (`market-gauge`: shown and recorded with each buy, no cash held for
    it); `questions.md` 31.
  - **The market-risk gauge, and the themes part's news read every trading day** (06:36 UTC; `stockiq-ai-trader` `CXfWPnap…`,
    `stockiq-ai-chat` `5cj0jrg4…`, rollback zips `…_before_autopilot_gauge_20261018.zip`, `stockiq-ai-chat_before_gauge_20261018.zip`;
    `practice-autopilot.js?v=60`, `dashboard.html`, `faq.html`), at the owner's word ("yes i go with your recommendations").
    **The gauge** (`market_gauge`, `GAUGE_NAMES`, cached 6 hours in the warm function): 0 very low to 4 very high, a point each
    for the S&P 500 fund below its 200-day and its 50-day average and the VIX over 20 and over 30, from the price function
    (`SPY` a year, `^VIX` three months: two requests every 6 hours at most). Shown at the top of Activity ("Market risk now: low"
    with five steps and a fold that says what makes it up and why it holds no cash: `gaugeHtml`), sent as `gauge` in every
    answer, recorded with every buy (`mg`, in `POOL_FIELDS`), split by in the review tool; the chat knows it. Experiment
    `market-gauge` (public, decide by 18 Jan 2027): do buys at a high reading do worse? First live reading: low (the fund
    0.7% under its 50-day average, the VIX 19.99). **The news read**: the owner asked whether the themes part should be checked
    more often "to pickup on changes in market news". The funds: no (`replay/sector_pace.py`: faster changes were no better,
    the quick-reacting variant clearly worse; `questions.md` 28). The AI model's read of the headlines: yes, every trading day,
    each call still scored a week later and still never acted on: about five times the calls, so the 30 that decide whether it
    may act come in weeks, not months (the calls overlap in time, which a verdict must allow for). About 2 US cents a month of
    OpenAI. Tests: 509 function, 234 panel, 24 chat; looked at on the owner's real account through the staged function before
    the deploy.
  - **The AI autopilot's Activity part made shorter** (07:2x UTC; `practice-autopilot.js?v=61`, `dashboard.html`), at the owner's
    word after he asked whether there is too much going on. Nothing removed: a short summary on top, the rest under one "More
    detail" fold (section 8c, "What the owner sees", at the start of the autopilot part). On his real data the Activity part shows
    about 6,400 characters before anything is opened, half of before. "The details" of the rule trials were going to be shown to
    his account only; left for everyone, since they are a fold inside "More detail" now and hold lines every user should see.
    Settings (about 8,800) was not touched. **Found on the way:** `clarity_check.py` counted the text of a fold inside a closed
    fold as on show (the 34 older holdings), so earlier totals were too high; fixed. **The way back:**
    `check-tools/pending-simple-undo/deploy.sh`, dry run tried. 235 panel checks.
  - **Three parts of the site reviewed, two small fixes** (`site_parts.py`: presets, the portfolio graph, search). The sitemap
    was written with an `ns0:` prefix on every tag (valid XML, not the usual form search engines are written for):
    `update_sitemap.py` and `generate_sitemap.py` now write plain tags (the reader takes both; `generate_sitemap.py` follows
    whichever form the file has); checked twice locally, 975 entries; live at the next daily run. **A count of the live
    sitemap must use `grep -c '<loc>\|:loc>'`** until then. The news page's title and description said "Free Stock Analysis
    Guide & Investment Blog"; now "Market and Stock News" (published by the next daily run). The AWS budget read $2.10 this
    month: the 253 Cost Explorer questions of 17 Oct (the session's fault, stopped); since then only the owner's own billing
    pages have asked (CloudTrail: "AWS Internal", free).
  - **The market data moves while someone is on the page** (09:02 and 09:05 UTC; `ticker-data-fetcher` `uhm8WRpQ…` then the
    five-minute version at 512 MB, rollback zips `ticker-data-fetcher_before_live_20261018.zip`, `…_before_live2_20261018.zip`;
    `live-market.js` (new), `theme.js`, `index.html`, `dashboard.html`): section 8, "The market data moves while someone is
    looking at it". The price function fetched its symbols one after another (26 in 9 s); now side by side, five-minute prices
    (the same current price, a fifth of the data), 512 MB (128 gave it too little processor: 7.6 s on Lambda against 0.6 s on
    the Mac): about 1.8 s inside AWS, about the same compute a call as before. Older callers get the same answer. Cost: about
    20,000 calls and 20,000 GB-seconds a month for two hours of watching a day, inside the free allowances.
  - **One market panel script for the home page and the dashboard** (website only: `market-panel.js` new, `index.html`,
    `dashboard.html`), at the owner's word that the two "should match": section 8, "The market panel on the right". Found
    on the way: the home page switched tabs in three places and set its arrows twice; both pages put the panel back after
    the phone sidebar with another position than it started with. The way back: `pending-panel-undo/deploy.sh`, dry run tried.
  - **The side panel's small charts for every item, and at once** (`ticker-data-fetcher`, rollback zip
    `…_before_spark_20261018.zip`; `live-market.js` version 2). The owner saw no line on the Asia tab (they came seconds after
    the tab opened), and none for the 2- and 10-year notes or any commodity. **Futures** (`ZT=F`, `ZN=F`, `GC=F`, `CL=F` …) have
    no points in Yahoo's one-day chart until their session reopens (a weekend): the function then takes the last trading day's
    prices from the five-day chart (`last_session`). **The delay:** a tab's lines came only with the next round for that tab;
    now every tab's lines are fetched in one request in the background (`fetchAllSparks`, at most every 5 minutes) and kept in
    the browser 20 minutes (`lmSparks`), so a tab chosen later, or a reload, shows them at once. The lines are each item's
    real prices for its latest trading day (until this day they were random). 36 checks in `live_market_check.js`.
  - **Links to the stock pages** (website: `index.html`, `market-panel.js` version 3, `stock-pages.js` new; `stockiq`:
    `update_home_stock_links.py` new, a line in `deploy-to-s3.sh`'s daily block). The owner asked what the home page needs to
    get more visitors. No page linked to any of the 958 indexed stock pages: section 6, "Links to the stock pages". Also asked:
    should a click on a share in the side lists open its stock page instead of running the report? On the home page yes (more
    for the visitor than for Google: it no longer spends an anonymous visitor's one free analysis); the dashboard keeps its
    click. 44 links live, 37 checks in `live_market_check.js`. **The panel's way back (`pending-panel-undo`) would take the
    Stock Pages section and its markers out of the home page too** (it restores the page as it was before the shared panel):
    the daily script would then say "nothing written" until the markers are put back.
  - **The site checked every night, and a daily review by Claude prepared** (the owner: "why can't you actively do this every
    24+ hours since a last check"; the top of this file). Live: `check-tools/site_audit.py` in the daily deploy, its findings on
    the Admin page (`admin-panel.js?v=13`, "🔎 Site check") and in session_start. The first run found 11 problems and 5 ideas:
    no search description on 9 pages (`analysis.html`, `contact.html`, `terms.html` among them) and no canonical on
    `unsubscribe.html`; `sidebar.js` still draws random lines (it does nothing where it is loaded); `script.js` is loaded by no
    page; the 4 guides link to no stock page; 9 "Loading..." on the home page; 13 functions copied in 3 or more files
    (`goToNotifications` in 18); 192 console.log lines. Not fixed yet: for the owner's yes. The daily review
    (`check-tools/daily_review.sh`) is built but its schedule could not be installed from a session; to install it, the owner
    writes `~/Library/LaunchAgents/com.stockiq.review.plist` (Label `com.stockiq.review`, ProgramArguments `/bin/bash
    /Users/dave/VSCODE/stockiq/check-tools/daily_review.sh`, StartInterval 1800) and runs `launchctl load` on it; to try it once,
    `bash /Users/dave/VSCODE/stockiq/check-tools/daily_review.sh --now`. Never run by a session.
  - **The site check's findings fixed** (the owner: "sure fix the issues"; live 11:52 UTC, 18 Oct 2026, website only, through
    `check-tools/pending-fixes/deploy.sh`): a description for search results on the nine pages without one, and
    `unsubscribe.html` kept out of search (noindex) with its canonical address; **the home page's four index cards drew one fixed
    "up" or "down" shape whatever the market did**, found while fixing their "Loading..." (the check had missed it: it looked
    only for `Math.random`): `live-market.js` version 3 now keeps their figures fresh and draws today's real line, as for the
    side panel (`cards()`, `drawCard`, `sparkPoints(list, prev, width)`), and the page shows a dash until the figures are in;
    the side panel's "Loading..." is the site's spinner; `sidebar.js` emptied (above); the four guides each link to eight
    real stock pages (`<!-- STOCK_EXAMPLES_START/END -->`, written once by hand, all of them indexed pages). Checked:
    `live_market_check.js` (40, one new: the cards' line is the answer's), `mobile_sidebar_check.js`, `header_room_check.js`, every inline
    script parses, the live home page read with real prices (the four cards with Friday's lines, no script error). The site
    check now reads 0 problems and 3 ideas. **Left, with the reason:** `script.js` (loaded by no page) waits for the owner's
    yes to delete it; the notification functions copied in four files (`showLoginModal`, `updateNotificationBell` and the
    rest) need a real signed-in browser to merge safely; the 192 console.log lines; `goToNotifications` (one line in each
    page's header) is in the check's `KNOWN`. **Seen on the way, the owner's to decide:** `contact.html` names "StockIQ Pty
    Ltd" with an ABN, while the terms and these notes say StockIQ is run by an individual with no company; `refunds.html`
    and `privacy-policy.html` say "Last updated: December 2024".
  - **The owner ran the daily review by hand** (11:33 UTC, `daily_review.sh --now`; the schedule is still not installed). It
    worked and found three things the nightly check had missed, with three proposals on the Admin page: **596 of the 958
    indexed stock pages still show 8 or 9 Oct data** although each says "Updated daily" (the snapshot step gets no prices
    from Yahoo on most days: section 9; proposal 1, prices through the price function on AWS); every report's "(REAL-TIME
    DATA)" heading against the FAQ's "no real-time data" (proposal 3); the stock pages' 0-100 score penalises the rise the
    trend score rewards and has never been tested (proposal 2). **Its report could not be saved**: Claude Code counts
    writing a file as an edit, so `Write(...)` never matched and the blocked "Edit" refused it; `daily_review.sh` now allows
    `Edit(check-tools/reviews/daily/**)` only, and the report was saved from `~/stockiq-review.log`
    (`check-tools/reviews/daily/2026-10-18.md`). Done from it the same hour (`pending-fixes2`, 11:58 UTC): the home page's
    index cards no longer show January 2024 figures when the market data fails ("Not available just now", until
    `live-market.js` fills them), and `login.html` is noindex and out of the sitemap. The nightly check learned both new kinds
    of fault (`stale-stock-pages`, fallback figures), and now reads 1 problem (the stale pages) and 3 ideas.
