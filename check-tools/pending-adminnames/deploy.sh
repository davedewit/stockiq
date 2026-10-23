#!/bin/bash
# One-off deploy (23 Oct 2026): the Admin page's rows say what each check covers; "Decision due"; every part of the site with its reviews.
ROWS="admin-panel.js:de27e3c9496c87df2730dc54b5d17f190faacbdcdcf3ecd7591b39c24f37e8f2:7258c1c2e6c16f0d8f38f087034751422a24badba1326ac44cf0a914f89c63d4 dashboard.html:eefad4e1cad98244c0672a90ae55808a25049542cf87971421bb58565863fd41:66344b3226b71145788cc08c0b09d4ef7ba12c635e22093a6d97a2b6a48cd2d1" exec bash /Users/dave/VSCODE/stockiq/check-tools/web_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
