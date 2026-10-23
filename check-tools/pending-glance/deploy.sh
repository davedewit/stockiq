#!/bin/bash
# One-off deploy (23 Oct 2026): three plain lines at the top of the Improvements tab: working on next, last session improved, being tested.
ROWS="admin-panel.js:cebd274fa1a98e1232e947522377df4ea61c3c8d78d3f9de95cf85b6ac4c0ec4:b9bb5a7487121e0c7fe65621143ad06b45f32d40317096669464c5278131ab05 dashboard.html:20f889fc1424f8c5a38fa2a8c2f700f3de85d9dd9a912960198c91988e046d28:d31bdad3e59a3d565265cee234e6f6599f85da44cf2e8e3588cdeebcf44b25ad" exec bash /Users/dave/VSCODE/stockiq/check-tools/web_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
