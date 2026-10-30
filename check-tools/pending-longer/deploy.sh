#!/bin/bash
# The longer-holds trial: while the holding time is automatic, shares tagged 0, 1, 1, 0 are kept up to 20 days.
FUNCS="stockiq-ai-trader:lambda:lambda_function.py:fQlGqFfzvAksVWbWKhUSL8WQb95T/4R6jWtnDm0UiqY=:2c9e84f0b5cbc98933c683a69f21dc6d00ab71e7b01e4630e3c362acfe93cb43:e6eeb150076102ddcdfb8f108f1c3b6f27d3e23d7d0c34af0a0e6bd8b7d783f0:before_autopilot_longer_20261030" \
  exec bash /Users/dave/VSCODE/stockiq/check-tools/lambda_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
