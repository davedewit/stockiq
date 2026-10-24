#!/bin/bash
# The whole header on every page (24 Oct 2026): site-header.js (new) and the switch for it in theme.js.
ROWS="site-header.js:none:204a7efe5dda0dfb75b0e1e5e77dcc8066413acacb9b446c809b8ac772431423 theme.js:2c37dab4e23a2737e520e1c1140768e93bb216bc7daa38162968968e19c988a6:e054bb09b55c6e2fc9b3f6eac043fb09e09e3bad4f4a9aaf8ce70239c1d2ccc3" exec bash /Users/dave/VSCODE/stockiq/check-tools/web_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
