#!/bin/bash
# One-off deploy (23 Oct 2026): the Admin page's Improvements tab lists every question asked (reviews/questions.md) with its answer.
ROWS="admin-panel.js:7763fa3847ce32984920af3c715dfda28bf029ece3c2587459cef8d39d0aaefb:5023ae7479cd224dfdb6ca9a7c0e9f03bd825cf1f555b94e38841c6a10e6f772 dashboard.html:7cb712f04c3ab482dffce26dc58b64edad43a1dc47ca7a5deb4180ad55c3ea98:a3531bd4e1805d15150aba189f880d0b979d5aad8bb4c807e778a850ef6de446" exec bash /Users/dave/VSCODE/stockiq/check-tools/web_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
