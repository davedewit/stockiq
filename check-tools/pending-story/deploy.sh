#!/bin/bash
# One-off deploy (23 Oct 2026): the Improvements tab opens with the story: the score, what testing has proven, what is tested now, next.
ROWS="admin-panel.js:b9bb5a7487121e0c7fe65621143ad06b45f32d40317096669464c5278131ab05:11145feebfca6b21ad606cf08b99af55588ccaa2a078674f37d48313da46b3e8 dashboard.html:d31bdad3e59a3d565265cee234e6f6599f85da44cf2e8e3588cdeebcf44b25ad:c8f36f2ed116fa64245c9b12c698e13d610cd84ac2755f41048456b1febf3e73" exec bash /Users/dave/VSCODE/stockiq/check-tools/web_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
