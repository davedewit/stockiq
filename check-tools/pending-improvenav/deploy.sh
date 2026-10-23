#!/bin/bash
# One-off deploy (23 Oct 2026): the Improvements tab says how many are being tested, and starts with jump links to each section.
ROWS="admin-panel.js:7242683ed51dfdff56513e37393235422f150f46b4e736592170dca5917ea51b:de27e3c9496c87df2730dc54b5d17f190faacbdcdcf3ecd7591b39c24f37e8f2 dashboard.html:f41741887adcf856d9addd86762b7e7b7d8da36b06f0746aa7608f0ad58d194e:eefad4e1cad98244c0672a90ae55808a25049542cf87971421bb58565863fd41" exec bash /Users/dave/VSCODE/stockiq/check-tools/web_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
