# Lambda Reference

## Overview
- ~50 named functions + ~630 parallel screener worker functions (total ~680)
- All use **Function URLs** (no API Gateway) called directly from frontend JS
- All in `us-east-1`, IAM role: `arn:aws:iam::114366766218:role/acp-lambda-role`
- Runtime: Python 3.x, `$LATEST` version (no aliases)
- Local mirror: `/Users/dave/VSCODE/stockiq/lambda-sync/` (refreshed hourly by deploy)
- URL map: `/Users/dave/VSCODE/stockiq/lambda-url-mapping.json`

---

## Function Groups

### Market Data (index.html widgets, sidebar)
| Function | Purpose |
|---|---|
| `stockiq-market-data-us` | US market overview (indices, movers) |
| `stockiq-market-data-europe` | European market data |
| `stockiq-market-data-asia` | Asian market data |
| `stockiq-market-data-crypto` | Crypto prices |
| `stockiq-market-data-commodities` | Commodities |
| `stockiq-market-data-rates` | Interest rates |
| `stockiq-market-data-currencies` | FX rates |
| `gainers-scraper` | Top gainers |
| `losers-scraper` | Top losers |
| `most-active-scraper` | Most active stocks |
| `trending-scraper` | Trending stocks |
| `stockiq-price-proxy` | Live price proxy for stock pages (refreshes every 5s) |
| `ticker-data-fetcher` | Ticker data for sidebar |

### Analysis (analysis.html)
| Function | Purpose |
|---|---|
| `stockiq-option-1-1-custom-analysis` | Single stock report + 0-100 score (Option 1) |
| `stockiq-option-2-trading-signals` | Trading signals (Option 2) |
| `stockiq-option-2-2-auto-signals` | Auto trading signals |
| `stockiq-option-3-1-us-screener` | US stock screener coordinator (Option 3) |
| `stockiq-option-3-dynamic-coordinator` | Dynamic screener coordinator |
| `stockiq-option-3-1-sp100` | S&P 100 screener |
| `stockiq-option-7-1-orchestrator` | Crypto screener (Option 7) |
| `stockiq-screener-coordinator` | Main screener coordinator |
| `stockiq-chart-generator` | Chart generation |
| `stockiq-validate-symbol` | Validates stock symbols across exchanges |
| `StockIQ-StockUpdater` | Stock data updater |

### Screener Workers (~651 functions)
Parallel workers called by `stockiq-screener-coordinator`. Each worker receives a `stock_batch`
of 10 symbols and returns scored results. All run in parallel, coordinator aggregates.

| Group | Functions | Screener | Stocks |
|---|---|---|---|
| `stockiq-asia-5-1-worker-1..5` | 5 | ASX 50 | 50 |
| `stockiq-asia-5-2-worker-1..10` | 10 | ASX 100 | 100 |
| `stockiq-asia-5-3-worker-1..20` | 20 | ASX 200 | 196 |
| `stockiq-asia-5-4-worker-1..30` | 30 | ASX 300 | 231 |
| `stockiq-asia-5-5-worker-1..21` | 21 | **Japan Nikkei 225** | 210 |
| `europe-4-1-worker-1..10` | 10 | UK FTSE 100 | 100 |
| Various `stockiq-option-3-*` | ~560 | US screeners (S&P, Russell, NASDAQ, Dow) | varies |

**Coordinator key format:** `{option}-{subOption}` e.g. `4-200` (ASX 200), `5-nikkei225` (Japan), `5-ftse100` (UK).
New screeners: use `5-<subOption>`.

**Worker code source for new non-US screeners:** copy from `stockiq-asia-5-5-worker-1` (Nikkei; see `add-new-screener.md`) — it handles
`.T`, `.AX`, `.L` suffixes correctly via Yahoo Finance. US workers use a different base.

### Auth & Users
| Function | Purpose |
|---|---|
| `stockiq-user-trial-manager` | Registration, trial status, usage tracking |
| `stockiq-cognito-email-sender` | Verification emails via Cognito |
| `stockiq-payment-handler` | Stripe payment processing |
| `stockiq-acp-checkout` | Checkout flow |
| `stockiq-ip-blocking-service` | Registration abuse prevention (5/hr, 1 per IP per 4 days) |
| `stockiq-trial-cleanup` | Daily cron, removes abandoned trials |

### Usage Tracking
| Function | Purpose |
|---|---|
| `stockiq-daily-usage-tracker` | Per-user daily usage |
| `stockiq-daily-usage-tracker-anonymous` | Anonymous usage + bot/subnet blocking |
| `stockiq-usage-counter` | Usage counting |
| `stockiq-usage-report-emailed` | Daily usage email at 03:00 AEST |

### Dashboard
| Function | Purpose |
|---|---|
| `stockiq-dashboard` | Dashboard data (history, favourites) |
| `stockiq-csv-export-proxy` | CSV export of analysis history |
| `stockiq-auto-delete-scheduler` | Schedules S3 data deletion |
| `stockiq-auto-delete-cleanup` | Cleans up S3 user data |

### Other
| Function | Purpose |
|---|---|
| `stockiq-dynamic-stock-lists` | Dynamic stock list API |
| `stockiq-stock-list-api` | Stock list API |
| `stockiq-email-capture` | Home page email list: saves to `stockiq-email-subscribers`, emails the owner (SES, from and to `noreply@stockiq.tech`) on each new signup. Handler file is `email-capture-with-count.py`; role `mylambdafunction-role-haabf70x`; **no CloudWatch log group exists**, so errors are not logged |
| `stockiq-ai-chat` | GPT-4o-mini chat (128MB, 30s, 300 tokens) |
| `stockiq-ai-chat-reporter` | Daily AI usage email at 5pm UTC |
| `stockiq-market-data-sidebar` | Sidebar market data |

### NO_URL (event-driven, no public URL)
`stockiq-acp-webhook`, `stockiq-auto-delete-scheduler`, `stockiq-coinspot-predictions-updater`,
`stockiq-daily-user-notification`, `stockiq-lambda-usage-reporter`, `stockiq-lambda-version-manager`,
`stockiq-payment-notification`, `stockiq-usage-report-emailed`, `stockiq-stock-analysis`,
`PostReader_*` (unused old functions)

---

## Code Patterns

### Standard Lambda handler structure
```python
import json
import boto3

def lambda_handler(event, context):
    try:
        # Parse body (Function URL sends body as string)
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        # ... logic ...

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, f'Internal server error: {str(e)}')

def error_response(status_code, message):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': message})
    }
```

### Bot blocking (used in public-facing functions)
```python
headers = event.get('headers', {})
user_agent = headers.get('User-Agent', '') or headers.get('user-agent', '')
bot_patterns = ['bot', 'crawler', 'spider', 'google', 'bing', 'yahoo', 'baidu']
if any(pattern in user_agent.lower() for pattern in bot_patterns):
    return {'statusCode': 403, 'body': json.dumps({'error': 'Bot access denied'})}
```

### DynamoDB access
```python
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('stockiq-user-tracking')

# Read
response = table.get_item(Key={'user_date': f'{email}#registration'})
item = response.get('Item')

# Write
table.put_item(Item={'user_date': f'{email}#registration', 'email': email, ...})

# Update
table.update_item(
    Key={'user_date': key},
    UpdateExpression='SET #field = :val',
    ExpressionAttributeNames={'#field': 'fieldName'},
    ExpressionAttributeValues={':val': value}
)
```

### Multi-action pattern (single function handles multiple actions)
```python
action = body.get('action')
if action == 'register':
    return register_user(body)
elif action == 'check_trial_status':
    return check_trial_status(body)
```

---

## Frontend Wiring

Lambda URLs are **hardcoded** in these JS/HTML files:
- `analysis-functions.js` — all analysis, screener, signal calls (310KB, main logic)
- `js/analysis-core.js` — core analysis helpers
- `auth.js` — usage tracking, trial checks, Cognito auth
- `ai-chat.js` — AI chat
- `stock-prices.js` — live price proxy
- `sidebar.js` — sidebar market data
- `script.js` — homepage widgets
- `dashboard.html` — dashboard data, CSV export, payment
- `login.html` / `signup.html` — auth flow
- `index.html` / `market-data-sidebar.html` / `market-data-widget.html` — market data widgets

To find which JS calls a specific function: `grep -r "lambda-url-fragment" /Users/dave/VSCODE/website/`

---

## Deploy Workflow for a New Lambda

### 1. Write the function
```bash
mkdir /Users/dave/VSCODE/stockiq/lambda-sync/my-new-function
# create lambda_function.py following the standard pattern above
```

### 2. Create on AWS
```bash
cd /Users/dave/VSCODE/stockiq/lambda-sync/my-new-function
zip lambda_function.zip lambda_function.py

aws lambda create-function \
  --function-name stockiq-my-new-function \
  --runtime python3.12 \
  --role arn:aws:iam::114366766218:role/acp-lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --timeout 30 \
  --memory-size 128 \
  --profile default --region us-east-1
```

### 3. Add a Function URL
```bash
aws lambda create-function-url-config \
  --function-name stockiq-my-new-function \
  --auth-type NONE \
  --cors '{"AllowOrigins":["*"],"AllowMethods":["*"],"AllowHeaders":["*"]}' \
  --profile default --region us-east-1
```

### 4. Update an existing function
```bash
cd /Users/dave/VSCODE/stockiq/lambda-sync/my-function
zip lambda_function.zip *.py
aws lambda update-function-code \
  --function-name stockiq-my-function \
  --zip-file fileb://lambda_function.zip \
  --profile default --region us-east-1
rm lambda_function.zip
```

### 5. Wire to frontend
- Add the Function URL to the relevant JS file
- Update `lambda-url-mapping.json`: `python3 /Users/dave/VSCODE/stockiq/generate-lambda-url-mappings.sh`

### 6. Check logs
```bash
aws logs tail /aws/lambda/stockiq-my-function --since 5m --profile default --region us-east-1
```

---

## Key DynamoDB Tables Used by Lambdas

| Table | Key format | Used by |
|---|---|---|
| `stockiq-user-tracking` | `user_date`: `email#registration` or `email#date` | trial-manager, usage-tracker |
| `stockiq-usage-tracker` | varies | usage-counter, daily-usage-tracker |
| `stockiq-dashboard-analysis-history` | userId + analysisId | dashboard, option-1 |
| `stockiq-email-subscribers` | email | email-capture |
| `stockiq-ai-chat-limits` | userId (TTL 2h) | ai-chat |
| `stockiq-ai-chat-stats` | userId+date (TTL 90d) | ai-chat, ai-chat-reporter |

---

## Before Editing Any Lambda

Always check AWS version vs local before editing:
```bash
# Check AWS last modified
aws lambda get-function --function-name <name> --profile default --region us-east-1 \
  --query 'Configuration.LastModified' --output text

# Compare to local
ls -lh /Users/dave/VSCODE/stockiq/lambda-sync/<name>/
```
If AWS is newer, download it first before editing.
