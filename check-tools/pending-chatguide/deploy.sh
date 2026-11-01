#!/bin/bash
# The AI chat's dashboard guide brought up to date with 1 Nov 2026 (the Practice tab's top, the Reports tab's deletion, the daily summary, the gauge, the two models).
FUNCS="stockiq-ai-chat:chat:lambda_function.py:r1ZRJyCSWqmF+y9Hh7czbju1VWXNbPvAK420pC70cP4=:1d874afb6705d2b05890869c4995ff8fd5397dbedfd9a3cfb8b36d5d0426e0b6:21bf16dc43a9ecbe62c837f19e2dd550e084fa5ad91b88d10e5ed52d6106f9dc:before_guide_20261101" \
  exec bash /Users/dave/VSCODE/stockiq/check-tools/lambda_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
