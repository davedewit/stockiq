# Nikkei 225 Screener — Build Summary

**Date:** 2026-10-05  
**Status:** ✅ Complete

---

## Step 1: 21 Worker Lambda Functions

All created fresh (none pre-existed). Runtime: python3.12, 256MB, 60s timeout.
Code: identical to `stockiq-asia-5-1-worker-1` (handles any Yahoo Finance symbol including .T suffix).

| Worker | Function Name | Function URL |
|--------|--------------|--------------|
| 1  | stockiq-asia-5-5-worker-1  | https://2g3hj5stpbtprg63efqstjrboy0mwpog.lambda-url.us-east-1.on.aws/ |
| 2  | stockiq-asia-5-5-worker-2  | https://5yzugqqawscfvx5kyqict6x7ha0samau.lambda-url.us-east-1.on.aws/ |
| 3  | stockiq-asia-5-5-worker-3  | https://wfeof7dr5inqc4xhohtdu6n6bi0epuqg.lambda-url.us-east-1.on.aws/ |
| 4  | stockiq-asia-5-5-worker-4  | https://itrpfcyqqn6yzjqn6ky7dynnoe0ixzfk.lambda-url.us-east-1.on.aws/ |
| 5  | stockiq-asia-5-5-worker-5  | https://s6kwr3a6j7u4x2a6gbqnrjj6s40nunos.lambda-url.us-east-1.on.aws/ |
| 6  | stockiq-asia-5-5-worker-6  | https://t4uvfpm7ewvvdfn7xpu7hhj6ua0edjse.lambda-url.us-east-1.on.aws/ |
| 7  | stockiq-asia-5-5-worker-7  | https://76pscw2vi3chb2dxjqtuqrha740gvxwu.lambda-url.us-east-1.on.aws/ |
| 8  | stockiq-asia-5-5-worker-8  | https://4bjpk7ivpav7hoalmiphib4twm0vuwmr.lambda-url.us-east-1.on.aws/ |
| 9  | stockiq-asia-5-5-worker-9  | https://knvjsgs77qj6k7zlpe2jqo2vle0sdtju.lambda-url.us-east-1.on.aws/ |
| 10 | stockiq-asia-5-5-worker-10 | https://hx6hgfuntjvk5tmhqsrywvy5a40wtuyq.lambda-url.us-east-1.on.aws/ |
| 11 | stockiq-asia-5-5-worker-11 | https://uullmljyan3vuybanguja2h5py0jevfr.lambda-url.us-east-1.on.aws/ |
| 12 | stockiq-asia-5-5-worker-12 | https://td2j3copshrmq4vehgpujezsvy0mcwtm.lambda-url.us-east-1.on.aws/ |
| 13 | stockiq-asia-5-5-worker-13 | https://6utz7752pa3l54lujtsnq4gh240oepjs.lambda-url.us-east-1.on.aws/ |
| 14 | stockiq-asia-5-5-worker-14 | https://7fqznbw7547jehwmg5har3zh4q0pdzcq.lambda-url.us-east-1.on.aws/ |
| 15 | stockiq-asia-5-5-worker-15 | https://xxjl5khbatuobsoxwe4csx6bgy0tmkse.lambda-url.us-east-1.on.aws/ |
| 16 | stockiq-asia-5-5-worker-16 | https://ueqire27pt3nzwkgzlal5nnlau0mxnxr.lambda-url.us-east-1.on.aws/ |
| 17 | stockiq-asia-5-5-worker-17 | https://sla4c77w4je62je2p7igbsm76i0tgafz.lambda-url.us-east-1.on.aws/ |
| 18 | stockiq-asia-5-5-worker-18 | https://76vbcb5lp4yp5hgwy3xn72nbm40oofqx.lambda-url.us-east-1.on.aws/ |
| 19 | stockiq-asia-5-5-worker-19 | https://i5vrx42zdwq7yt777ii4nqqgem0ngayb.lambda-url.us-east-1.on.aws/ |
| 20 | stockiq-asia-5-5-worker-20 | https://g3vxxlz4p6s7dum3c6cwwguawe0jladz.lambda-url.us-east-1.on.aws/ |
| 21 | stockiq-asia-5-5-worker-21 | https://3dmddgt36bvz2hqsqj3mghd2540drkom.lambda-url.us-east-1.on.aws/ |

**Note on CORS:** First attempt used `["POST","OPTIONS"]` which AWS rejected (method values must be ≤6 chars). Fixed to `["POST"]` matching all other existing workers.

---

## Step 2: Coordinator Lambda

**No changes made.** Per the plan, the frontend (analysis-functions.js) calls workers directly — the coordinator is bypassed entirely for option 4/5 screeners. Adding a coordinator key would be dead code.

---

## Step 3: analysis-functions.js Changes (5 locations)

File: `/Users/dave/VSCODE/website/analysis-functions.js`

### 2a. Handler block (inserted after ASX 300 block, before FTSE 100 block)
- `else if (option === 5 && subOption === 'nikkei225')` block with full 210-stock universe and 21 worker URLs

### 2b. screenerMappings entry (line ~639)
- Added: `'Japan Nikkei 225 Screener': 'analysis.html?option=5&subOption=nikkei225&autorun=true'`

### 2c. companyName subNames (option 5 block ~line 3201)
- Added: `'nikkei225': 'Japan Nikkei 225 Screener'`

### 2d. uniqueSymbolsCount (option 5 block ~line 3136)
- Added: `else if (subOption === 'nikkei225') { symbols = ['JAPAN_SCREENER']; uniqueSymbolsCount = 210; }`

### 2e. formatNikkeiResult() function (inserted before formatUKResult)
- New function at ~line 4849, formats JPY prices with ¥ and toFixed(0)

---

## Step 4: analysis.html Change

File: `/Users/dave/VSCODE/website/analysis.html`

- **Before:** `<button class="screener-btn coming-soon" onclick="showComingSoonPopup()">🇯🇵 Japan (Nikkei 225) - Coming Soon</button>`
- **After:** `<button class="screener-btn" onclick="runAnalysis(5, 'nikkei225', event)">🇯🇵 Japan (Nikkei 225) (210 stocks)</button>`

---

## Issues / Notes

- CORS AllowMethods: `["POST","OPTIONS"]` fails AWS validation (6-char limit). Used `["POST"]` to match all other workers — OPTIONS preflight is handled at the Function URL level automatically.
- No coordinator changes needed (plan confirmed this; frontend bypasses coordinator for option 4/5).
- Deploy required: `cd /Users/dave/VSCODE/stockiq && ./deploy-to-s3.sh` to push analysis-functions.js and analysis.html to S3.
