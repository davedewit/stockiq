#!/bin/bash
# Experiment 'headlines' decided 12 Nov 2026: the shortlist's per-share headlines are no longer fetched or shown to the model (CANDIDATE_HEADLINES = False).
FUNCS="stockiq-ai-trader:lambda:lambda_function.py:r+MK5wY5GL2X1CMuMn0qrFtLMiDQH319TNtt4Jai6ck=:986c6280de4730dd5a572f06465493bd0bc3258d64309fb8cb32af5fd4283fb3:b6ca918e66e0be9f0fabd08eb020526e93e59ffbdd64a6081d764279a7f874e7:before_autopilot_noheads_20261112" \
  exec bash /Users/dave/VSCODE/stockiq/check-tools/lambda_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
