#!/bin/bash
# Admin #12: the chat's dashboard guide says the free trial includes the autopilot; a holding's sell-by is never a past date.
FUNCS="stockiq-ai-chat:chat:lambda_function.py:x0K1sllVSm6sTjGf0XC/Yl7tIlxz67eU2o1RtvMnPTM=:ba7b7b8dab73199bed257ac5ccfb3fa7f70cb5cf4fc5c4cfeb995f95f9d73e91:a408f6e11cdde82861eb903629463850cce9b973131f6a499c1d8a768bd62922:before_trialwords_20261030 stockiq-ai-trader:lambda:lambda_function.py:lVwV715IPTZ060NpZTv6cGX8PNsuvqMEOtViHMgElVw=:45d060b9636a09d8eb080284b4371ee1aea66aa8d0ddebcee096801ef8675b89:2c9e84f0b5cbc98933c683a69f21dc6d00ab71e7b01e4630e3c362acfe93cb43:before_autopilot_pastdate_20261030" \
  exec bash /Users/dave/VSCODE/stockiq/check-tools/lambda_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
