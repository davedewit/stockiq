#!/bin/bash
# One-off deploy (23 Oct 2026): the Improvements tab lists every fix and change with who found the problem behind it.
ROWS="admin-panel.js:5023ae7479cd224dfdb6ca9a7c0e9f03bd825cf1f555b94e38841c6a10e6f772:7242683ed51dfdff56513e37393235422f150f46b4e736592170dca5917ea51b dashboard.html:97bf3d5d69d28e3acc9d399d4d2461a798445f89bd4f9632f9b11b11b9d5b445:f41741887adcf856d9addd86762b7e7b7d8da36b06f0746aa7608f0ad58d194e" exec bash /Users/dave/VSCODE/stockiq/check-tools/web_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
