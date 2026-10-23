#!/bin/bash
# One-off deploy (23 Oct 2026): the Improvements tab as six closed rows, each with its count and the one fact worth knowing.
ROWS="admin-panel.js:2e93aab814e068fb99abb300cb166ad642fa773a4d29cc469babb6cdc8b01a46:cebd274fa1a98e1232e947522377df4ea61c3c8d78d3f9de95cf85b6ac4c0ec4 dashboard.html:50efa61f69215e3f61ce60778a952120924a05e226294729adf61cec73665842:20f889fc1424f8c5a38fa2a8c2f700f3de85d9dd9a912960198c91988e046d28" exec bash /Users/dave/VSCODE/stockiq/check-tools/web_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
