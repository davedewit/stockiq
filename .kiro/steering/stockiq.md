# StockIQ Project Documentation

## Overview
- **Website:** https://stockiq.tech
- **Purpose:** Professional stock analysis platform with AI-powered investment research tools
- **Tech Stack:** Static website (HTML/CSS/JS) + AWS Lambda + DynamoDB + S3
- **Authentication:** AWS Cognito (email/password, Google OAuth, Facebook OAuth)
- **Payment:** Stripe integration, monthly plans billed in **USD**: Starter $4.99 (15 analyses/day), Pro $14.99 (50/day), Elite $49.99 (unlimited). Live price IDs are in `stockiq-payment-handler`; currency lives on the Stripe price, not in the code
- **Business:** "StockIQ", online-only, no physical address, no financial services licence (stated in terms.html and about.html)
- **Email:** AWS Cognito default sender (no-reply@verificationemail.com) - plain text only

## Rules Reference
Start with **`site-overview.md`**: how the whole site works, what is generated vs hand-edited,
**how GitHub pushes work (daily and manual)**, current SEO setup, pitfalls and open ideas
(reviewed 25 Sep 2026).

Detailed docs live in separate files — check these first:
- **`script-reference.md`** — All Python scripts, what they do, how to run them, workflow
- **`stocks-txt-csv-format.md`** — CSV format rules, parsing, sector distribution, workflow
- **`stock-matching-system.md`** — How news matches to stocks (US + non-US)
- **`roadmap-to-9.md`** — Current score (8.7/10), priorities, timeline
- **`backlinks-progress.md`** — Backlink strategy and progress
- **`future-work.md`** — People Also Watch fixes, crypto news integration
- **`add-new-screener.md`** — Full step-by-step for adding a regional screener (India/Korea next); read before starting one

## Key Files
- **`/Users/dave/VSCODE/website/stocks.txt`** — Source of truth (3,467 stocks: SYMBOL, Company Name, Sector)
- **`/Users/dave/VSCODE/website/stocks/*.html`** — Generated stock pages (3,467 files; ~962 large caps indexed, rest noindex)
- **`/Users/dave/VSCODE/website/news.html`** — Recent news (newest 240 stock + 60 general articles, noindex; trimmed by finalize_news_html.py)
- **`/Users/dave/VSCODE/stockiq/indexable_stocks.txt`** — Stock pages that are indexed and in the sitemap (written daily by update_stock_analysis.py)
- **`/Users/dave/VSCODE/website/news.js`** — Sidebar (100-item pool, displays 5)
- **`/Users/dave/VSCODE/stockiq/update_stock_news.py`** — Contains NUMERIC_COMPANY_NAMES (144 non-US stocks)
- **`/Users/dave/VSCODE/stockiq/lambda-sync/`** — Lambda function backups

## Scheduled Task (Automated Daily Deploy)

### Files
- **Bash script:** `/Users/dave/stockiq-daily.sh` (logic: Mon-Sat, 11am-10pm, once/day)
- **Launchd plist:** `~/Library/LaunchAgents/com.stockiq.reminder.plist` (StartInterval 600 = checks every 10 min)
- **Lock file:** `/tmp/stockiq-deploy-YYYYMMDD.lock` (prevents duplicate runs)
- **Log:** `~/stockiq-daily.log`
- **GitHub:** each run ends by committing and pushing both repos (stockiq + website), unless
  the deploy script already pushed within the last 23h. No run on Sunday. Details and timing
  examples: `site-overview.md` section 5b

### Change Schedule
Edit plist: `StartInterval` (seconds) for periodic, or `StartCalendarInterval` for specific time. Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.stockiq.reminder.plist
launchctl load ~/Library/LaunchAgents/com.stockiq.reminder.plist
```

### Quick Commands
```bash
bash ~/stockiq-daily.sh                        # Test now
tail -50 ~/stockiq-daily.log                   # View log
ls -la /tmp/stockiq-deploy-*.lock              # Check if ran today
rm /tmp/stockiq-deploy-$(date +%Y%m%d).lock   # Force retry today
```

## Quick Reference Commands

```bash
# Daily deploy (news update + S3 sync)
cd /Users/dave/VSCODE/stockiq && ./deploy.sh

# Preview what a deploy would upload/push (no S3 or GitHub changes)
DRY_RUN=true ./deploy-to-s3.sh

# Deploy website only (no news update)
./deploy-to-s3.sh

# Update stock news manually
python3 update_stock_news.py

# Generate/regenerate stock pages
python3 generate-stock-pages.py

# Sync news if out of sync
python3 Sync_stock_to_news.py

# Clear all news (start fresh)
python3 clear_stock_news.py

# Check daily cron logs
tail -f /Users/dave/stockiq-daily.log

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id EHXV50CPHY07R --paths "/*" --profile default
```

## Project Structure
- **Scripts:** `/Users/dave/VSCODE/stockiq/`
- **Website:** `/Users/dave/VSCODE/website/`
- **Lambda:** `/Users/dave/VSCODE/stockiq/lambda-sync/`
- **Python:** 3.14 (`/opt/homebrew/bin/python3`)

## AWS Resources

### Account
- **Profile:** `default` | **Account:** `114366766218` | **Region:** `us-east-1`

### S3 Buckets
- `stockiq-final-websitebucket-vqekic7enf9h` — Website hosting
- `stockiq-dashboard-analysis-history` — User analysis reports/CSV (auto-delete 30/90 days)
- `stockiq-option-1-1-custom-analysis` — Custom analysis charts (auto-delete 30/90 days)
- `stockiq-dynamic-stock-lists`, `stockiq-stock-lists`, `stockiq-acp`, `stockiq-prod-1756902871`

### CloudFront
- **Distribution ID:** `EHXV50CPHY07R`
- **Function:** `stockiq-www-redirect` — www→non-www redirect + lowercase symbols→uppercase
- **Backup:** `/Users/dave/VSCODE/stockiq/cloudfront-backup/` (`./restore-cloudfront-function.sh`)

### DynamoDB Tables
- `stockiq-dashboard-analysis-history` — Analysis history
- `stockiq-email-subscribers` — Email list
- `stockiq-usage-tracker` — Usage tracking
- `stockiq-user-tracking` — User activity (key: `user_date`, format: `email#date` or `email#registration`)
- `stockiq-coinspot-prediction-status`, `stockiq-coinspot-predictions` — Crypto predictions
- `stockiq-ai-chat-limits` — AI chat rate limiting (TTL 2h)
- `stockiq-ai-chat-stats` — AI chat usage tracking (TTL 90 days)

### Cognito
- **User Pool ID:** `us-east-1_P4lqPzrlY` | **Client ID:** `6s3i43db9g6jlgjisr0b3blh56`
- **Trigger:** CustomMessage Lambda (`stockiq-cognito-email-sender`)
- **Email:** no-reply@verificationemail.com — plain text only (HTML not supported)

### Key Lambda Functions
- `stockiq-cognito-email-sender` — Verification emails with activation links
- `stockiq-user-trial-manager` — Trial management and registration
- `stockiq-payment-handler` — Stripe payment processing
- `stockiq-validate-symbol`, `stockiq-dashboard`, `stockiq-chart-generator`, `stockiq-screener-coordinator`
- `stockiq-market-data-{us,europe,asia,crypto,commodities,rates,currencies}`
- `stockiq-trial-cleanup` — Daily cron, removes abandoned trials
- `stockiq-auto-delete-scheduler`, `stockiq-auto-delete-cleanup` — S3 data cleanup
- `stockiq-ai-chat` — GPT-4o-mini chat (128MB, 30s timeout, 300 max tokens)
- `stockiq-ai-chat-reporter` — Daily usage email at 5pm UTC
- ~1000 total; `-worker-` functions are parallel processing duplicates

### IAM
- **Lambda Role:** `arn:aws:iam::114366766218:role/acp-lambda-role`

## Lambda Backup & Deployment

### Local Backups
- **Location:** `/Users/dave/VSCODE/stockiq/lambda-sync/`
- **Auto-sync:** Runs during `deploy-to-s3.sh` (1-hour cooldown)
- **Manual sync:** `/Users/dave/VSCODE/stockiq/sync-all-lambdas.sh`

### Deploy Lambda
```bash
# 1. Check AWS version first (compare timestamps)
aws lambda get-function --function-name <function-name> --profile default --query 'Configuration.LastModified' --output text
ls -lh /Users/dave/VSCODE/stockiq/lambda-sync/<function-name>/

# 2. If AWS is newer, download it first
aws lambda get-function --function-name <function-name> --profile default --query 'Code.Location' --output text | xargs curl -s -o /tmp/check.zip && unzip -p /tmp/check.zip *.py | head -20

# 3. Deploy your changes
cd /Users/dave/VSCODE/stockiq/lambda-sync/<function-name>
zip lambda_function.zip *.py
aws lambda update-function-code --function-name <function-name> --zip-file fileb://lambda_function.zip --profile default
rm lambda_function.zip
```

### Notes
- Check AWS version before first edit (steps 1-2) to avoid overwriting newer code
- Skip check if you just deployed - local is already newest
- All functions use `$LATEST` version (no aliases)

## User Authentication

### Email Registration Flow
1. User registers → Cognito triggers `stockiq-cognito-email-sender`
2. Email sent: `"Your verification code is {code}. Verify: https://stockiq.tech/signup.html?activate=true&code={code}&email={email}"`
3. User clicks link → auto-activates → redirects to login.html with email pre-filled

### Known Issues
- **Cognito bug:** Manual code entry unreliable; activation link works 100%
- **CustomMessage trigger:** Only provides `{####}` placeholder — blocks third-party email services
- **AWS SES:** Production access permanently denied by AWS Trust & Safety

### Social Login
- **Google OAuth:** `851713356105-bm61s5e7qf0tkn5ll8jvslhg98ce6pe9.apps.googleusercontent.com`
- **Facebook OAuth:** App ID `1125324569571529`

## Trial System
- **Free Trial:** 15 analyses/screeners, 3 days
- `stockiq-user-trial-manager` handles registration; `stockiq-trial-cleanup` runs daily

## Common AWS Commands
```bash
# List Cognito users
aws cognito-idp list-users --user-pool-id us-east-1_P4lqPzrlY --profile default --region us-east-1

# Delete Cognito user
aws cognito-idp admin-delete-user --user-pool-id us-east-1_P4lqPzrlY --username <username> --profile default --region us-east-1

# Check DynamoDB table
aws dynamodb scan --table-name stockiq-user-tracking --profile default --region us-east-1

# Delete DynamoDB record
aws dynamodb delete-item --table-name stockiq-user-tracking --key '{"user_date":{"S":"email@example.com#registration"}}' --profile default --region us-east-1

# List Lambda functions
aws lambda list-functions --profile default --region us-east-1 --query 'Functions[?contains(FunctionName, `stockiq`)].FunctionName'

# Check Lambda logs
aws logs tail /aws/lambda/<function-name> --since 5m --profile default --region us-east-1

# Delete user S3 data
aws s3 rm s3://stockiq-dashboard-analysis-history/csv/email@example.com/ --recursive --profile default
aws s3 rm s3://stockiq-option-1-1-custom-analysis/charts/email@example.com/ --recursive --profile default
```

## Troubleshooting
- **CloudFront not updating:** `aws cloudfront create-invalidation --distribution-id EHXV50CPHY07R --paths "/*" --profile default`
- **Lambda not updating:** Check directory, function name, zip created, profile is `default`
- **Password not clearing after activation:** login.html clears on `?pwd=clear` (50/100/200ms delays)
- **"Already activated" error:** signup.html detects "already confirmed" → shows message → redirects to login
- **News out of sync:** `python3 Sync_stock_to_news.py` (re-adds old articles to news.html; the next deploy trims them again)
- **Sidebar shows no news:** `node -c /Users/dave/VSCODE/website/news.js`

## AI Chat System (Updated Oct 9, 2026)
- **Lambda:** `stockiq-ai-chat` | **Model:** GPT-4o-mini | **Cost:** ~$0.02/month (Oct 2026)
- **Frontend:** `ai-chat.js` (22.5KB) on all pages
- **Features:** 3-message conversation memory, live stock prices, links to stock pages
- **No advice rule (Oct 9, 2026):** the system prompt tells the model never to give buy/sell/hold calls, price targets, predictions or picks. Asked "should I buy X?" it says it can't make that call, then gives the price, what the score looks at, and links. Suggested questions in `ai-chat.js` are "What does the data say about X?", not "Should I buy X?". Don't loosen this
- **Rate limits:** Anonymous: 3 msg/hr | Trial/free: 10 msg/hr | Paid: 50 msg/hr | @dewit.com.au: unlimited
- **Positioning:** bottom-right, 20px from the edge on every page. Only on pages that have the `#news-panel` sidebar (home page) and only from 1401px wide, it moves to right 370px to clear the panel (`body.has-news-panel`, set in ai-chat.js)
- **UI:** 380x600px desktop, gradient header, message bubbles with tails, input font-size 16px (prevents mobile zoom)
- **Conversation history:** Last 6 messages (3 exchanges) sent as context, stored in sessionStorage
- **Token usage:** ~650 tokens/message average (system prompt + history + current)
- **Cost per message:** ~$0.00015 (0.015 cents) | 100 msgs/month = $0.015
- **Reports:** `stockiq-ai-chat-reporter` emails daily at 5pm UTC to `openai-usage@stockiq.tech`
- **Tables:** `stockiq-ai-chat-limits` (rate limiting, TTL 2h), `stockiq-ai-chat-stats` (usage tracking, TTL 90d)

## Email Signup List (home page, updated Oct 9, 2026)
- **What it is:** the "Get Screener Highlights by Email" block on `index.html` (`<section class="email-capture-section">`,
  input `#email-capture`, button calls `captureEmail()`). **No email is sent to subscribers yet** - it is an
  early-interest list. The owner will send something manually if it passes ~5 real signups.
- **Flow:** `captureEmail()` (the `async` one near the end of `index.html`; an older same-named function
  earlier in the file is overridden and unused) POSTs `{action:'subscribe', email, source:'homepage'}` to the
  Lambda Function URL -> Lambda saves the row -> Lambda emails the owner.
- **Lambda:** `stockiq-email-capture` | URL `https://r5aierjvyfe2kdjoql5p23jmuy0rtisk.lambda-url.us-east-1.on.aws/`
  | handler file `email-capture-with-count.py` (zip that file, not `lambda_function.py`) | Python 3.11
  | role `mylambdafunction-role-haabf70x` (has DynamoDB + `ses:SendEmail`).
- **Actions:** `subscribe` (new, duplicate, or resubscribe) and `get_count` (number with status `subscribed`).
- **Storage:** DynamoDB `stockiq-email-subscribers`, key `email`. Fields: `status`, `source`, `subscribed_at`,
  `ip_address` (real request IP), `user_agent`, `subscriber_id`. No S3.
- **Owner notification:** SES, from `noreply@stockiq.tech` to `noreply@stockiq.tech` (constants
  `NOTIFICATION_EMAIL` / `ADMIN_EMAIL` at the top of the file). Sent on new signup and resubscribe, not on
  duplicates. A failed email never fails the signup. Subject: `StockIQ: New signup (N total) - <email>`.
- **Don't promise what doesn't exist:** the block used to say "daily picks at 6 AM EST" and "5 winners get
  1 YEAR FREE". Both were removed Oct 2026. Only add such wording back if the owner is actually running it.
- **Known gaps:** the Function URL is public (a bot could flood signups and notification emails; no cap yet);
  the Lambda has **no CloudWatch log group**, so errors leave no trace; there is no unsubscribe link or
  sending job.
- **Commands:**
  ```bash
  # List signups
  aws dynamodb scan --table-name stockiq-email-subscribers --profile default --region us-east-1 \
    --query 'Items[].{email:email.S,at:subscribed_at.S,source:source.S,status:status.S}' --output table
  # Deploy after editing lambda-sync/stockiq-email-capture/email-capture-with-count.py
  cd /Users/dave/VSCODE/stockiq/lambda-sync/stockiq-email-capture
  zip -j /tmp/email-capture.zip email-capture-with-count.py
  aws lambda update-function-code --function-name stockiq-email-capture \
    --zip-file fileb:///tmp/email-capture.zip --profile default --region us-east-1
  ```
