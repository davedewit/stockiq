"""Puts a test page made by dashboard_page.py inside a frame as wide as a phone, so that headless Chrome (whose own window
cannot be made that narrow) lays it out as a phone would. The framed page reports back when its steps are done.

   python3 check-tools/dashboard_page.py <portfolio.js> <autopilot.js> /tmp/m.html light "mobile" <dashboard.html>
   python3 check-tools/mobile_frame.py /tmp/m.html /tmp/m-frame.html [width, default 390]
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=420,3000 \\
       --virtual-time-budget=30000 --dump-dom file:///tmp/m-frame.html      (and --screenshot=... for the look)"""
import sys, os
inner, outp, width = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 390
open(outp, 'w').write('''<!doctype html><html><head><meta charset="utf-8"><title>running</title><style>body { margin: 0; background: #888; } iframe { display: block; border: 0; background: #fff; }</style></head>
<body><iframe id="f" src="%s" style="width: %dpx; height: 900px;"></iframe><pre id="out" style="white-space: pre-wrap; font: 11px monospace; background: #fff; margin: 0; padding: 6px;"></pre>
<script>window.addEventListener('message', (e) => { if (!e.data || !e.data.out) return; document.getElementById('out').textContent = e.data.out; document.getElementById('f').style.height = Math.min(6000, e.data.height + 20) + 'px'; document.title = 'done'; });</script></body></html>''' % ('file://' + os.path.abspath(inner), width))
