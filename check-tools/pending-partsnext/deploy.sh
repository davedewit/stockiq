#!/bin/bash
# One-off deploy (23 Oct 2026): the parts list on the Improvements tab names the next three as the sessions rank them, with why.
ROWS="admin-panel.js:7258c1c2e6c16f0d8f38f087034751422a24badba1326ac44cf0a914f89c63d4:2e93aab814e068fb99abb300cb166ad642fa773a4d29cc469babb6cdc8b01a46 dashboard.html:66344b3226b71145788cc08c0b09d4ef7ba12c635e22093a6d97a2b6a48cd2d1:50efa61f69215e3f61ce60778a952120924a05e226294729adf61cec73665842" exec bash /Users/dave/VSCODE/stockiq/check-tools/web_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
