# StockIQ Project Documentation

## Overview
- **Website:** https://stockiq.tech
- **Purpose:** Professional stock analysis platform with AI-powered investment research tools
- **Tech Stack:** Static website (HTML/CSS/JS) + AWS Lambda + DynamoDB + S3
- **Authentication:** AWS Cognito (email/password, Google OAuth, Facebook OAuth)
- **Payment:** Stripe integration
- **Email:** AWS Cognito default sender (no-reply@verificationemail.com) - plain text only

## Rules Reference
Detailed docs live in separate files — check these first:
- **`script-reference.md`** — All Python scripts, what they do, how to run them, workflow
- **`stocks-txt-csv-format.md`** — CSV format rules, parsing, sector distribution, workflow
- **`stock-matching-system.md`** — How news matches to stocks (US + non-US)
- **`roadmap-to-9.md`** — Current score (8.7/10), priorities, timeline
- **`backlinks-progress.md`** — Backlink strategy and progress
- **`future-work.md`** — People Also Watch fixes, crypto news integration

## Key Files
- **`/Users/ddewit/VSCODE/website/stocks.txt`** — Source of truth (3,469 stocks: SYMBOL, Company Name, Sector)
- **`/Users/ddewit/VSCODE/website/stocks/*.html`** — Generated stock pages (3,469 files)
- **`/Users/ddewit/VSCODE/website/news.html`** — News archive (all stock + general articles)
- **`/Users/ddewit/VSCODE/website/news.js`** — Sidebar (100-item pool, displays 5)
- **`/Users/ddewit/VSCODE/stockiq/update_stock_news.py`** — Contains NUMERIC_COMPANY_NAMES (144 non-US stocks)
- **`/Users/ddewit/VSCODE/stockiq/lambda-sync/`** — Lambda function backups

## Quick Reference Commands

```bash
# Daily deploy (news update + S3 sync)
cd /Users/ddewit/VSCODE/stockiq && ./deploy.sh

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
tail -f /Users/ddewit/stockiq-daily.log

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id EHXV50CPHY07R --paths "/*" --profile default
```

## Project Structure
- **Scripts:** `/Users/ddewit/VSCODE/stockiq/`
- **Website:** `/Users/ddewit/VSCODE/website/`
- **Lambda:** `/Users/ddewit/VSCODE/stockiq/lambda-sync/`
- **Python:** 3.9.6

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
- **Backup:** `/Users/ddewit/VSCODE/stockiq/cloudfront-backup/` (`./restore-cloudfront-function.sh`)

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

## Lambda Deployment
```bash
cd /Users/ddewit/VSCODE/stockiq/lambda-sync/<function-name>
zip lambda_function.zip lambda_function.py
aws lambda update-function-code --function-name <function-name> --zip-file fileb://lambda_function.zip --profile default
rm lambda_function.zip
```

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
- **News out of sync:** `python3 Sync_stock_to_news.py`
- **Sidebar shows no news:** `node -c /Users/ddewit/VSCODE/website/news.js`

## AI Chat System
- **Lambda:** `stockiq-ai-chat` | **Model:** GPT-4o-mini | **Cost:** ~$10-20/month
- **Frontend:** `ai-chat.js` on all pages
- **Rate limits:** Anonymous/trial: 10 msg/hr | Paid: 50 msg/hr | @dewit.com.au: unlimited
- **Positioning:** index.html right 370px (avoids sidebar) | stock pages right 20px
- **Reports:** `stockiq-ai-chat-reporter` emails daily at 5pm UTC to `openai-usage@stockiq.tech`
