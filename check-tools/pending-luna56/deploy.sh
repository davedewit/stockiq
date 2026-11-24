#!/bin/bash
# Back to GPT-5.6 Luna (24 Nov 2026): the chat and the autopilot's usual model. OpenAI's data-sharing page puts it in the 2.5M-a-day small-model group.
FUNCS="stockiq-ai-trader:lambda:lambda_function.py:AODf+rE0xHPZlpBQ1U5phvuLtkk0OdGJvsSM/mmKlAs=:e9f596f27e64bb4972c204931698513945b210864d7c7716766c8ecb8f251b40:e5948906f6ae4efaebca3a48840af5ea274ac49fcc60c216da9fb4be95f43bf6:before_luna56_20261124 stockiq-ai-chat:chat:lambda_function.py:hMG2MsorMoVG+5iyjqO9wkAsiOnI9toA6mP9h9w1e1c=:1e156c2f6b1a032cb135a08d418ea92409a270305cec7b3872b28ef6f46fb5f4:46bda96497ad1024a8410111e823c58b0228a246c0526d539cb2efc77e3d7d15:before_luna56_20261124" \
  exec bash /Users/dave/VSCODE/stockiq/check-tools/lambda_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
