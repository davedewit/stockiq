// AI autopilot for the practice portfolio (dashboard). FAKE MONEY ONLY: no real trade is ever placed.
// This file is only the controls and what the autopilot reports. The decisions are made by the stockiq-ai-trader
// Lambda on a schedule (or "Check in now"), which writes its practice buys and sells into the same practice
// portfolio that practice-portfolio.js shows. Shown only to users that Lambda allows.
// How the controls behave: EVERY change is saved by itself (the switch at once, typing after a short pause), so a
// refresh always shows what was last set. There is no save button; a line beside "Check in now" says
// "Saving…", "Saved" or why something could not be saved.
// What it shows keeps itself up to date: while the page is open it asks the Lambda again every minute (not while
// something is being typed or saved), and tells practice-portfolio.js when the autopilot has bought or sold.
(function () {
    const API = 'https://qy6s553i647agmxthtecc24fje0zskms.lambda-url.us-east-1.on.aws/';
    const CSS = `
        #practice-autopilot .ap-imp-sub { color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 4px; }
        #practice-autopilot .ap-imp-head { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; color: var(--text-secondary); margin: 12px 0 4px; }
        #practice-autopilot ul.ap-imp { list-style: none; margin: 0; padding: 0; }
        #practice-autopilot .ap-imp-row { display: flex; gap: 10px; align-items: baseline; padding: 6px 0; border-top: 1px solid var(--border-color); font-size: 0.9rem; color: var(--text-primary); }
        #practice-autopilot .ap-imp-row:first-child { border-top: none; }
        #practice-autopilot .ap-imp-word { flex: none; font-size: 0.72rem; font-weight: 700; padding: 1px 7px; border-radius: 999px; margin-top: 2px; white-space: nowrap; }
        #practice-autopilot .ap-imp-word.ok { background: rgba(22, 163, 74, 0.14); color: #16a34a; } #practice-autopilot .ap-imp-word.no { background: rgba(128, 128, 128, 0.16); color: var(--text-secondary); }
        #practice-autopilot .ap-imp-mark { font-weight: 800; width: 1em; flex: none; text-align: center; }
        #practice-autopilot .ap-imp-mark.ok { color: #16a34a; } #practice-autopilot .ap-imp-mark.no { color: #dc2626; } #practice-autopilot .ap-imp-mark.test { color: #2563eb; } #practice-autopilot .ap-imp-mark.next { color: var(--text-secondary); }
        #practice-autopilot .ap-imp-when { color: var(--text-secondary); font-size: 0.8rem; white-space: nowrap; }
        #practice-autopilot .ap-imp-details summary { cursor: pointer; color: #2563eb; font-size: 0.85rem; margin-top: 12px; }

        #practice-autopilot .ap-wrap { color: var(--text-primary); font-size: 0.9rem; }
        #practice-autopilot .ap-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
        #practice-autopilot .ap-head h3 { margin: 0; font-size: 1.15rem; color: var(--text-primary); }
        #practice-autopilot .ap-beta { display: inline-block; vertical-align: middle; margin-left: 4px; padding: 1px 8px; border-radius: 10px; border: 1px solid #f59e0b; color: #f59e0b; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
        #practice-autopilot .ap-sub { font-size: 0.8rem; font-weight: normal; color: var(--text-secondary); }
        #practice-autopilot .ap-switch { display: inline-flex; align-items: center; gap: 10px; cursor: pointer; font-weight: 600; position: relative; }
        #practice-autopilot .ap-switch input { position: absolute; opacity: 0; width: 46px; height: 26px; margin: 0; cursor: pointer; right: 0; }
        #practice-autopilot .ap-track { width: 46px; height: 26px; border-radius: 13px; background: #9ca3af; position: relative; transition: background 0.15s; flex: none; }
        #practice-autopilot .ap-track::after { content: ''; position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.3); transition: left 0.15s; }
        #practice-autopilot .ap-switch input:checked + .ap-track { background: #22c55e; }
        #practice-autopilot .ap-switch input:checked + .ap-track::after { left: 23px; }
        #practice-autopilot .ap-switch input:focus-visible + .ap-track { outline: 2px solid #007bff; outline-offset: 2px; }
        #practice-autopilot .ap-intro { color: var(--text-secondary); font-size: 0.85rem; line-height: 1.5; margin: 8px 0 0; }
        #practice-autopilot .ap-status { margin-top: 12px; padding: 10px 12px; border-radius: 8px; background: var(--bg-secondary); border-left: 4px solid #9ca3af; color: var(--text-secondary); font-size: 0.85rem; line-height: 1.55; }
        #practice-autopilot .ap-status.on { border-left-color: #22c55e; }
        #practice-autopilot .ap-status strong { color: var(--text-primary); }
        #practice-autopilot .ap-card { border: 1px solid var(--border-color); border-radius: 8px; padding: 14px 16px; margin-top: 12px; }
        #practice-autopilot .ap-label { font-weight: 600; display: block; margin-bottom: 6px; color: var(--text-primary); }
        #practice-autopilot .ap-help { color: var(--text-secondary); font-size: 0.82rem; line-height: 1.45; margin-top: 6px; }
        #practice-autopilot .ap-risk { width: 100%; margin: 0; accent-color: #007bff; }
        #practice-autopilot .ap-levels { display: flex; font-size: 0.78rem; color: var(--text-secondary); margin-top: 2px; }
        #practice-autopilot .ap-levels span { flex: 1; text-align: center; cursor: pointer; padding: 2px 0; }
        #practice-autopilot .ap-levels span:first-child { text-align: left; }
        #practice-autopilot .ap-levels span:last-child { text-align: right; }
        #practice-autopilot .ap-levels span.now { color: var(--text-primary); font-weight: 700; }
        #practice-autopilot .ap-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px 18px; }
        #practice-autopilot .ap-input { display: flex; align-items: center; gap: 8px; color: var(--text-secondary); white-space: nowrap; }
        #practice-autopilot .ap-input input, #practice-autopilot .ap-input select { flex: 1; min-width: 0; width: 100%; box-sizing: border-box; padding: 9px 10px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px; }
        #practice-autopilot .ap-group { display: grid; grid-template-columns: 150px 1fr; gap: 6px 12px; align-items: start; padding: 9px 0; border-top: 1px solid var(--border-color); }
        #practice-autopilot .ap-group.shared { grid-template-columns: 185px minmax(0, 1fr) 370px; gap: 8px 16px; align-items: center; padding: 12px 0; }
        #practice-autopilot .ap-group.shared.off .ap-group-name { opacity: 0.75; }
        #practice-autopilot .ap-group-name .ap-dot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 7px; vertical-align: baseline; }
        #practice-autopilot .ap-splitbar { display: flex; height: 30px; border-radius: 8px; overflow: hidden; margin: 8px 0 12px; border: 1px solid var(--border-color); background: var(--bg-secondary); }
        #practice-autopilot .ap-splitbar span { display: flex; align-items: center; justify-content: center; min-width: 0; padding: 0 8px; color: #fff; font-size: 0.8rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        #practice-autopilot .ap-splitbar span.idle { color: var(--text-secondary); background: none; font-weight: 400; }
        #practice-autopilot .ap-group.first { border-top: none; padding-top: 2px; }
        #practice-autopilot .ap-group-name { color: var(--text-secondary); padding-top: 6px; }
        #practice-autopilot .ap-group-pick { white-space: nowrap; background: none; border: none; padding: 0; margin: 0; font: inherit; color: inherit; cursor: pointer; text-align: left; border-bottom: 1px dashed var(--border-color); }
        #practice-autopilot .ap-group-pick:hover { color: var(--text-primary); border-bottom-color: #3b82f6; }
        #practice-autopilot .ap-chips { display: flex; flex-wrap: wrap; gap: 6px 8px; }
        #practice-autopilot .ap-chip { display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border: 1px solid var(--border-color); border-radius: 16px; cursor: pointer; white-space: nowrap; user-select: none; color: var(--text-primary); }
        #practice-autopilot .ap-chip:has(input:checked) { border-color: #007bff; background: rgba(0, 123, 255, 0.12); }
        #practice-autopilot .ap-chip input { margin: 0; }
        #practice-autopilot .ap-chip small { color: var(--text-secondary); }
        #practice-autopilot .ap-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 14px; }
        #practice-autopilot .ap-btn { border-radius: 6px; padding: 9px 16px; font-size: 0.9rem; cursor: pointer; white-space: nowrap; border: 1px solid var(--border-color); background: none; color: var(--text-primary); }
        #practice-autopilot .ap-btn.primary { background: #007bff; border-color: #007bff; color: #fff; }
        #practice-autopilot .ap-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        #practice-autopilot .ap-btn { transition: background-color 0.12s, border-color 0.12s, box-shadow 0.12s, transform 0.05s; font-family: inherit; }
        #practice-autopilot .ap-btn:hover:not(:disabled) { background: var(--bg-secondary); border-color: var(--text-secondary); }
        #practice-autopilot .ap-btn:active:not(:disabled) { background: var(--border-color); transform: translateY(1px); box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.18); }
        #practice-autopilot .ap-btn.primary:hover:not(:disabled) { background: #0069d9; border-color: #0062cc; }
        #practice-autopilot .ap-btn.primary:active:not(:disabled) { background: #0056b3; border-color: #0056b3; box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3); }
        #practice-autopilot .ap-btn:focus-visible { outline: 2px solid #007bff; outline-offset: 2px; }
        #practice-autopilot .ap-btn.busy::before, #practice-autopilot a.busy::before { content: ''; display: inline-block; width: 0.75em; height: 0.75em; margin-right: 7px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; vertical-align: -1px; animation: ap-spin 0.7s linear infinite; }
        #practice-autopilot a[data-ap="refresh"], #practice-autopilot a[data-ap="mailtest"] { border-radius: 4px; padding: 1px 4px; transition: background-color 0.12s, color 0.12s; }
        #practice-autopilot a[data-ap="refresh"]:hover, #practice-autopilot a[data-ap="mailtest"]:hover { background: rgba(59, 130, 246, 0.14); color: #1d4ed8; text-decoration: underline; }
        [data-theme="dark"] #practice-autopilot a[data-ap="refresh"]:hover, [data-theme="dark"] #practice-autopilot a[data-ap="mailtest"]:hover { color: #93c5fd; }
        #practice-autopilot a[data-ap="refresh"]:active, #practice-autopilot a[data-ap="mailtest"]:active { background: rgba(59, 130, 246, 0.28); }
        #practice-autopilot a.busy { pointer-events: none; opacity: 0.8; }
        #practice-autopilot .ap-flash { animation: ap-flash 2.4s ease-out; }
        @keyframes ap-spin { to { transform: rotate(360deg); } }
        @keyframes ap-flash { 0%, 55% { color: #16a34a; font-weight: 600; } }
        @media (prefers-reduced-motion: reduce) { #practice-autopilot .ap-btn.busy::before, #practice-autopilot a.busy::before { animation-duration: 2.4s; } }
        #practice-autopilot .ap-saved { color: var(--text-secondary); font-size: 0.85rem; }
        #practice-autopilot .ap-saved.bad { color: #d97706; }
        #practice-autopilot .ap-note { margin-top: 10px; padding: 9px 12px; border-radius: 6px; font-size: 0.85rem; color: var(--text-primary); }
        #practice-autopilot .ap-note.good { background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.4); }
        #practice-autopilot .ap-note.bad { background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.4); }
        #practice-autopilot .ap-section { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border-color); font-size: 0.85rem; color: var(--text-secondary); }
        #practice-autopilot .ap-section h4 { margin: 0 0 6px; font-size: 0.95rem; color: var(--text-primary); }
        #practice-autopilot .ap-log { padding: 8px 0; border-bottom: 1px solid var(--border-color); line-height: 1.45; }
        #practice-autopilot .ap-log time { white-space: nowrap; margin-right: 6px; }
        #practice-autopilot .ap-log details, #practice-autopilot .ap-section details { margin-top: 4px; }
        #practice-autopilot .ap-log summary, #practice-autopilot .ap-section summary { cursor: pointer; color: var(--text-primary); font-size: 0.8rem; }
        #practice-autopilot .ap-log ul, #practice-autopilot .ap-section ul { margin: 4px 0 0 18px; padding: 0; }
        #practice-autopilot .ap-fresh { float: right; font-size: 0.8rem; font-weight: normal; color: var(--text-secondary); }
        #practice-autopilot .ap-fresh a { margin-left: 8px; }
        #practice-autopilot .ap-mini { display: inline-flex; align-items: center; gap: 6px; margin-left: 12px; cursor: pointer; position: relative; color: var(--text-primary); }
        #practice-autopilot .ap-mini input { position: absolute; opacity: 0; width: 32px; height: 18px; margin: 0; cursor: pointer; left: 0; }
        #practice-autopilot .ap-mini .ap-dot { width: 32px; height: 18px; border-radius: 9px; background: #9ca3af; position: relative; transition: background 0.15s; flex: none; }
        #practice-autopilot .ap-mini .ap-dot::after { content: ''; position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%; background: #fff; transition: left 0.15s; }
        #practice-autopilot .ap-mini input:checked + .ap-dot { background: #22c55e; }
        #practice-autopilot .ap-mini input:checked + .ap-dot::after { left: 16px; }
        #practice-autopilot .ap-mini input:focus-visible + .ap-dot { outline: 2px solid #3b82f6; outline-offset: 2px; }
        #practice-autopilot a { color: #3b82f6; }
        #practice-autopilot .ap-views { display: flex; gap: 6px; margin-top: 16px; border-bottom: 1px solid var(--border-color); }
        #practice-autopilot .ap-view { padding: 9px 16px; border: 0; border-bottom: 3px solid transparent; margin-bottom: -1px; background: none; color: var(--text-secondary); font-size: 0.95rem; font-weight: 600; cursor: pointer; }
        #practice-autopilot .ap-view:hover { color: var(--text-primary); }
        #practice-autopilot .ap-view.now { color: #007bff; border-bottom-color: #007bff; }
        #practice-autopilot .ap-pane > .ap-section:first-child { border-top: 0; margin-top: 6px; }
        #practice-autopilot .ap-presets { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-top: 12px; font-size: 0.85rem; color: var(--text-secondary); }
        #practice-autopilot .ap-preset { padding: 6px 12px; border: 1px solid var(--border-color); border-radius: 16px; background: var(--bg-secondary); color: var(--text-primary); cursor: pointer; font-size: 0.85rem; }
        #practice-autopilot .ap-preset:hover { border-color: #3b82f6; }
        #practice-autopilot .ap-own { display: flex; gap: 8px 18px; flex-wrap: wrap; align-items: center; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border-color); font-size: 0.85rem; color: var(--text-secondary); }
        #practice-autopilot .ap-own strong { color: var(--text-primary); }
        #practice-autopilot .ap-own input { width: 70px; padding: 6px 8px; margin: 0 4px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px; }
        #practice-autopilot .ap-auto { font-size: 0.75rem; font-weight: normal; color: #22c55e; margin-left: 6px; }
        #practice-autopilot .ap-auto.own { color: var(--text-secondary); }
        #practice-autopilot .ap-may { display: block; padding: 6px 0; cursor: pointer; }
        #practice-autopilot .ap-may input { margin-right: 8px; }
        #practice-autopilot .ap-may small { display: block; margin-left: 24px; color: var(--text-secondary); font-size: 0.8rem; }
        #practice-autopilot .ap-bd { border-collapse: collapse; font-size: 0.85rem; margin-top: 4px; }
        #practice-autopilot .ap-bd th { padding: 6px 14px; text-align: right; white-space: nowrap; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: var(--text-secondary); border-bottom: 2px solid var(--border-color); }
        #practice-autopilot .ap-bd td { padding: 6px 14px; text-align: right; white-space: nowrap; color: var(--text-secondary); border-bottom: 1px solid rgba(128, 128, 128, 0.18); font-variant-numeric: tabular-nums; }
        #practice-autopilot .ap-bd td.ap-bd-name { text-align: left; padding-left: 22px; color: var(--text-primary); white-space: normal; min-width: 240px; }
        #practice-autopilot .ap-bd td.ap-bd-name::first-letter { text-transform: uppercase; }
        #practice-autopilot .ap-bd td.ap-bd-num { font-weight: 600; }
        #practice-autopilot .ap-bd tr.ap-bd-gap td { border: 0; padding: 0; height: 10px; }
        #practice-autopilot .ap-bd tr.ap-bd-head td { text-align: left; padding: 7px 10px; font-weight: 700; font-size: 0.8rem; letter-spacing: 0.02em; color: var(--text-primary); background: var(--bg-secondary); border-bottom: 0; border-left: 3px solid #007bff; border-radius: 4px; }
        #practice-autopilot .ap-share { font-size: 0.8rem; color: var(--text-secondary); padding: 8px 10px; border-radius: 8px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-left-width: 4px; }
        #practice-autopilot .ap-share .ap-share-label { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 5px; }
        #practice-autopilot .ap-share .ap-share-label .ap-auto { margin-left: 0; text-transform: none; letter-spacing: 0; font-size: 0.75rem; }
        #practice-autopilot .ap-share select { width: 100%; box-sizing: border-box; padding: 8px 10px; border: 1px solid #007bff; border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px; font-weight: 500; cursor: pointer; }
        #practice-autopilot .ap-share.none { border: 0; background: none; padding: 0 2px; font-size: 0.8rem; }
        @media (max-width: 980px) { #practice-autopilot .ap-group.shared { grid-template-columns: 185px minmax(0, 1fr); } #practice-autopilot .ap-group.shared > div:last-child { grid-column: 2; } }
        #practice-autopilot .ap-only-phone { display: none; }
        #practice-autopilot .ap-bar { margin: 8px 0; padding: 10px 12px; border: 1px solid var(--border-color); border-left: 3px solid #f59e0b; border-radius: 8px; font-size: 0.85rem; line-height: 1.5; }
        #practice-autopilot .ap-bar strong { color: var(--text-primary); }
        #practice-autopilot .ap-sharedbox { margin: 0 0 8px; padding: 10px 12px; border: 1px solid rgba(124, 58, 237, 0.35); border-left: 3px solid #7c3aed; border-radius: 8px; background: rgba(124, 58, 237, 0.06); font-size: 0.85rem; line-height: 1.5; }
        #practice-autopilot .ap-sharedbox strong { color: var(--text-primary); }
        #practice-autopilot { font-variant-numeric: tabular-nums; }
        @media (max-width: 640px) { #practice-autopilot .ap-only-phone { display: inline; } }
        #practice-autopilot .ap-countline { margin-top: 6px; color: var(--text-primary); }
        #practice-autopilot .ap-count { display: inline-block; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; white-space: nowrap; }
        #practice-autopilot .ap-held { margin-top: 6px; border-bottom: 1px solid var(--border-color); }
        #practice-autopilot .ap-held-row { border-top: 1px solid var(--border-color); }
        #practice-autopilot .ap-held-row > summary { display: grid; grid-template-columns: 104px minmax(0, 1fr) auto; gap: 2px 12px; align-items: baseline; padding: 8px 0; cursor: pointer; list-style: none; }
        #practice-autopilot .ap-held-row > summary::-webkit-details-marker { display: none; }
        #practice-autopilot .ap-held-row > summary:hover .ap-held-open { color: var(--text-primary); }
        #practice-autopilot .ap-held-name { color: var(--text-primary); overflow-wrap: anywhere; }
        #practice-autopilot .ap-held-main { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
        #practice-autopilot .ap-held-what { color: var(--text-secondary); }
        #practice-autopilot .ap-held-chips { display: flex; flex-wrap: wrap; gap: 5px 8px; }
        #practice-autopilot .ap-hchip { font-size: 0.76rem; padding: 1px 8px; border-radius: 10px; border: 1px solid var(--border-color); color: var(--text-secondary); white-space: nowrap; }
        #practice-autopilot .ap-hchip.up { color: #16a34a; border-color: rgba(22, 163, 74, 0.5); }
        #practice-autopilot .ap-hchip.trial { color: #2563eb; border-color: rgba(37, 99, 235, 0.5); }
        #practice-autopilot .ap-held-open { font-size: 0.8rem; color: var(--text-secondary); white-space: nowrap; }
        #practice-autopilot .ap-held-open::after { content: " \\25B8"; }
        #practice-autopilot .ap-held-row[open] > summary .ap-held-open::after { content: " \\25BE"; }
        #practice-autopilot .ap-held-plan { margin: 0 0 10px 116px; padding: 8px 12px; border-left: 2px solid var(--border-color); font-size: 0.84rem; color: var(--text-secondary); line-height: 1.5; }
        #practice-autopilot .ap-held-rest > summary { cursor: pointer; color: var(--text-secondary); padding: 8px 0; border-top: 1px solid var(--border-color); }
        @media (max-width: 640px) { #practice-autopilot .ap-held-row > summary { grid-template-columns: minmax(0, 1fr) auto; } #practice-autopilot .ap-held-main { grid-column: 1 / -1; grid-row: 2; } #practice-autopilot .ap-hchip { white-space: normal; } #practice-autopilot .ap-held-plan { margin-left: 0; } }
        #practice-autopilot .ap-needs { margin-top: 10px; padding: 9px 12px; border-radius: 6px; font-size: 0.85rem; line-height: 1.5; color: var(--text-primary); background: rgba(217, 119, 6, 0.12); border: 1px solid rgba(217, 119, 6, 0.5); }
        #practice-autopilot .ap-needs.none { background: none; border: 0; padding: 0; color: var(--text-secondary); }
        #practice-autopilot .ap-needs ul { margin: 4px 0 0 18px; padding: 0; }
        #practice-autopilot .ap-next { display: grid; grid-template-columns: minmax(150px, max-content) 1fr; gap: 8px 14px; align-items: start; margin-top: 8px; line-height: 1.45; }
        #practice-autopilot .ap-next .ap-count { padding: 2px 9px; border-radius: 12px; background: var(--bg-secondary); border: 1px solid var(--border-color); font-size: 0.82rem; text-align: center; }
        #practice-autopilot .ap-next .ap-count.first { background: rgba(0, 123, 255, 0.14); border-color: #007bff; }
        #practice-autopilot .ap-next time { color: var(--text-primary); font-weight: 600; margin-right: 6px; white-space: nowrap; }
        @media (max-width: 640px) {
            #practice-autopilot table.ap-stack, #practice-autopilot table.ap-stack tbody, #practice-autopilot table.ap-stack tr, #practice-autopilot table.ap-stack td { display: block !important; width: auto !important; box-sizing: border-box; }
            #practice-autopilot table.ap-stack tr.ap-stack-head { display: none !important; }
            #practice-autopilot table.ap-stack tr { border: 1px solid var(--border-color); border-radius: 10px; padding: 10px 12px; margin: 0 0 10px; }
            #practice-autopilot table.ap-stack td { text-align: left !important; white-space: normal !important; padding: 3px 0 !important; }
            #practice-autopilot table.ap-stack td[data-label] { display: flex !important; justify-content: space-between; gap: 12px; }
            #practice-autopilot table.ap-stack td[data-label]::before { content: attr(data-label); color: var(--text-secondary); font-weight: 400; flex: none; }
            #practice-autopilot table.ap-stack td.ap-stack-wide { display: block !important; }
            #practice-autopilot table.ap-stack td.ap-stack-wide::before { display: block; }
            #practice-autopilot table.ap-stack td.ap-stack-title { font-weight: 700; padding-bottom: 6px !important; margin-bottom: 4px; border-bottom: 1px solid var(--border-color); }
            #practice-autopilot .ap-bd { width: 100%; }
            #practice-autopilot .ap-bd th, #practice-autopilot .ap-bd td { padding: 6px 5px; }
            #practice-autopilot .ap-bd td.ap-bd-name { min-width: 0; padding-left: 8px; }
            #practice-autopilot .ap-bd th { white-space: normal; letter-spacing: 0; font-size: 0.66rem; vertical-align: bottom; line-height: 1.2; }
            #practice-autopilot .ap-bd td { font-size: 0.8rem; }
            #practice-autopilot .ap-bd tr.ap-bd-head td { padding: 6px 8px; white-space: normal; }
            #practice-autopilot .ap-own label { flex-basis: 100%; }
            #practice-autopilot .ap-own select { display: block; width: 100% !important; max-width: 100% !important; margin: 6px 0 0 !important; box-sizing: border-box; }
            #practice-autopilot .ap-fresh { float: none; display: block; margin-top: 4px; }
            #practice-autopilot .ap-fresh .ap-mini { margin-left: 0; margin-top: 6px; display: flex; }
            #practice-autopilot .ap-actions .ap-btn { flex: 1 1 100%; padding: 12px 16px; }
            #practice-autopilot .ap-views .ap-view { flex: 1; padding: 11px 8px; }
            #practice-autopilot .ap-card { padding: 12px 12px; }
            #practice-autopilot .ap-splitbar { height: auto; min-height: 30px; }
            #practice-autopilot .ap-splitbar span { white-space: normal; text-align: center; padding: 4px 4px; font-size: 0.72rem; line-height: 1.2; }
        }
        @media (max-width: 640px) { #practice-autopilot .ap-next { grid-template-columns: 1fr; gap: 2px 0; } #practice-autopilot .ap-next .ap-count { justify-self: start; margin-top: 8px; } }
        @media (max-width: 640px) { #practice-autopilot .ap-group, #practice-autopilot .ap-group.shared { grid-template-columns: 1fr; } #practice-autopilot .ap-group.shared > div:last-child { grid-column: 1; } #practice-autopilot .ap-group-name { padding-top: 0; } #practice-autopilot .ap-chip { white-space: normal; } #practice-autopilot .ap-input { white-space: normal; } }
    `;

    let data = null, draft = null, working = '', notice = null, showAll = false;
    let presetUndo = null;                                  // which screeners were ticked before a shortcut or a click on a market's name, for the Undo
    let skew = 0;                                         // the server's clock minus this computer's, in ms: countdowns use the server's
    let saveTimer = null, saving = false, saveError = null, savedOnce = false, breakdownOpen = false;
    // The activity list: everything, or only buys and sells. A way of looking at the list, not a setting of the autopilot:
    // it is remembered in this browser (localStorage), so a refresh keeps it.
    const VIEW_KEY = 'stockiqAutopilotTradesOnly';
    const remembered = () => { try { return localStorage.getItem(VIEW_KEY) === '1'; } catch (e) { return false; } };
    const remember = (on) => { try { localStorage.setItem(VIEW_KEY, on ? '1' : '0'); } catch (e) {} };
    let tradesOnly = remembered();
    // The panel is in two parts so that neither is a long scroll: "Activity" (what it holds, how it is doing, what it has
    // done) and "Settings". Both are always in the page; one is shown. The choice is remembered in this browser.
    const PART_KEY = 'stockiqAutopilotPart';
    let part = null;                                                // 'activity' | 'settings'; decided at the first draw
    const rememberedPart = () => { try { const v = localStorage.getItem(PART_KEY); return v === 'activity' || v === 'settings' ? v : null; } catch (e) { return null; } };
    function showPart(name, keep) {
        part = name === 'settings' ? 'settings' : 'activity';
        if (keep) { try { localStorage.setItem(PART_KEY, part); } catch (e) {} }
        ['activity', 'settings'].forEach(n => {
            const pane = byId('ap-pane-' + n), tab = byId('ap-view-' + n);
            if (pane && pane.style) pane.style.display = n === part ? '' : 'none';
            if (tab && tab.classList) tab.classList.toggle('now', n === part);
        });
    }
    // Shortcuts (13 Oct 2026; they replaced the "quick set-ups", which also changed the pace and the level): they change
    // only which screeners are ticked. MAIN is one index a country, none of them inside another.
    const MAIN = ['3-3', '5-ftse100', '5-dax40', '5-cac40', '5-smi', '5-aex', '5-ftsemib', '5-ibex35', '4-200', '5-nikkei225', '5-hangseng', '5-sensex', '5-kospi200', '5-sti', '5-tsx60', '5-bovespa', '5-omx30', '5-csi300', '5-tw50', '5-nzx50', '5-ipc'];
    let loadedAt = null, refreshing = false, openDetails = {};       // openDetails: which "Details" are unfolded, kept across redraws
    const REFRESH_MS = 5 * 60000;      // every 5 minutes (it was every minute: the most of the database's reads, 17 Oct 2026); it trades only at :10 and :40, and a press of a button refreshes at once
    const userId = () => { const u = localStorage.getItem('userId'); return u && u !== 'anonymous' ? u : null; };
    const box = () => document.getElementById('practice-autopilot');
    const byId = (id) => document.getElementById(id);
    const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const usd0 = (n) => '$' + Math.round(n).toLocaleString('en-US');
    const when = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }); };
    const day = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }); };
    const pc = (n) => (n === null || n === undefined) ? '–' : (n >= 0 ? '+' : '') + n.toFixed(1) + '%';
    const usd2 = (n) => (n < 0 ? '-' : '+') + '$' + Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const clock = (d) => d ? d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
    const fold = (key, title, lines) => lines && lines.length ? `<details data-ap-fold="${esc(key)}" ${openDetails[key] ? 'open' : ''}><summary>${esc(title)}</summary><ul>${lines.map(x => `<li>${esc(x)}</li>`).join('')}</ul></details>` : '';
    // a result as a broker's screen shows it: an arrow and the amount, green up, red down (the words are the screen reader's label)
    const deltaHtml = (amount, percent) => {
        const r = Math.round((amount || 0) * 100) / 100 || 0, p = typeof percent === 'number' ? ' (' + Math.abs(percent).toFixed(1) + '%)' : '';
        const money = '$' + Math.abs(r).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        return `<span class="ap-delta" role="img" aria-label="${r === 0 ? 'level' : (r > 0 ? 'profit of ' : 'loss of ') + money}${p}" style="color: ${r > 0 ? '#16a34a' : r < 0 ? '#ef4444' : 'var(--text-secondary)'}; font-weight: 700; white-space: nowrap;">${r > 0 ? '▲' : r < 0 ? '▼' : '–'} ${money}${p}</span>`;
    };
    // what a sale made or lost in dollars: sent by the function, or read from an older entry's own words
    const gainOf = (e) => {
        if (typeof e.gain === 'number') return e.gain;
        const m = /Put in \$([\d,.]+), got back \$([\d,.]+)/.exec(e.text || '');
        return m ? Math.round((parseFloat(m[2].replace(/,/g, '')) - parseFloat(m[1].replace(/,/g, ''))) * 100) / 100 : null;
    };
    const tint = (n) => (n === null || n === undefined) ? 'var(--text-secondary)' : n >= 0 ? '#22c55e' : '#ef4444';
    const everyText = (v) => v === 24 ? 'once a day' : v === 12 ? 'twice a day' : v === 1 ? 'every hour' : v < 1 ? `every ${Math.round(v * 60)} minutes` : `every ${v} hours`;
    // a holding time given in days: 30 minutes, 3 hours, 5 days
    const holdText = (d) => { const h = d * 24; return h < 0.75 ? `${Math.round(h * 60)} minutes` : h < 23.5 ? `${Math.round(h)} hour${Math.round(h) === 1 ? '' : 's'}` : `${Math.round(d)} day${Math.round(d) === 1 ? '' : 's'}`; };
    let accepted = null;                          // what was last sent and saved (the server may tidy a value, e.g. round the budget)
    const isDirty = () => { if (!data || !draft) return false; const now = JSON.stringify(draft); return now !== JSON.stringify(data.settings) && now !== accepted; };

    function ensureStyle() {
        if (!document.head || !document.createElement || byId('ap-style')) return;
        const style = document.createElement('style');
        style.id = 'ap-style'; style.textContent = CSS;
        document.head.appendChild(style);
    }

    async function api(action, extra, keepalive) {
        const res = await fetch(API, { method: 'POST', keepalive: !!keepalive, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.assign({ action, userId: userId() }, extra || {})) });
        const body = await res.json().catch(() => ({}));
        if (res.status === 402) {                           // not on a paid plan (any more): show what it is, and take them to the plans
            data = { success: true, allowed: false, locked: 'plan' }; draft = null;
            try { window.location.hash = 'upgrade'; } catch (e) {}
        }
        if (!res.ok) throw new Error(body.error || 'The autopilot could not be reached');
        return body;
    }

    // ---------------------------------------------------------------- wording, from the numbers the Lambda sends
    // A level's rules without the user's own limits: the level's own, with what the autopilot has changed itself for the level in use
    function autoRules(level) {
        const r = data.options.risk[String(level)];
        if (!r || !data.rules || String(data.settings.risk) !== String(level)) return r;
        return Object.assign({}, r, { top: data.rules.top, trail: data.rules.trail }, data.rules.level || { stop: data.rules.stop, take: data.rules.take });
    }
    // what an empty "your own limit" field falls back to, shown in grey inside it
    const autoWord = (n) => n ? 'Automatic: ' + n : '';       // what an empty box shows: the level's own value, named as such
    function hint(level, key) { const r = autoRules(level), n = r ? Math.abs(r[key]) : NaN; return isFinite(n) ? String(n) : ''; }
    // ... and with the user's own loss limit and gain mark, as they stand on screen: these come before everything else
    // What the number of holdings means, in words: how big each is, what a larger or smaller number does, and any catch
    // While the themes part (a trial) runs, the share part works with the rest of the budget: the same sum as share_part in the
    // function. Every size and build-up on the panel goes through it.
    function themesShare(d) { const t = data && data.themes; return t && t.on && (!d || d.selfTune !== false) ? (t.share || 0) : 0; }
    // What the market shares are a share of: the whole budget, or, while the themes part runs, the part left for shares
    function ofWhat(d) { return themesShare(d) ? `the ${usd0(sharePart(d).budgetUsd)} for shares` : 'the budget'; }
    function sharePart(d) { const k = themesShare(d); return k && !d.partOfShares ? Object.assign({}, d, { budgetUsd: Math.round(d.budgetUsd * (1 - k) * 100) / 100, partOfShares: true }) : d; }
    function holdingsHint(d) {
        d = sharePart(d);
        const level = (data.options.risk[String(d.risk)] || {}).positions || 0, n = positionsOf(d), bound = data.options.holdings || { min: 2, max: 50 };
        if (!n) return '';
        const size = d.budgetUsd / n, each = `${n} holdings of about ${usd0(size)} each`;
        const what = d.holdings > 0 ? `Set by you: ${each} (the ${autoRules(d.risk) ? autoRules(d.risk).name : ''} level by itself would use ${level}).` : `Left to the risk level: ${each}. Type a number (${bound.min} to ${bound.max}) to choose your own.`;
        const more = d.holdings > level ? ` With more holdings each is smaller and the account moves more like the market as a whole; it buys up to ${buysPerCheck(n)} at a check-in and looks at the top ${Math.max((autoRules(d.risk) || {}).top || 0, Math.min(n, 30))} of each screener to fill them.`
            : d.holdings > 0 && d.holdings < level ? ' With fewer, larger holdings the account swings more: one holding counts for more, up or down.' : ' Fewer, larger holdings swing more; more, smaller ones move more like the market as a whole.';
        const small = size < 25 ? ` Each would be under the $25 smallest buy: it would buy nothing. Use fewer holdings or a larger budget.` : '';
        return what + more + small + ' Empty the box to leave it to the risk level again.'.repeat(d.holdings > 0 ? 1 : 0);
    }
    function levelRules(level) {
        const r = autoRules(level), d = draft || data.settings;
        if (!r) return r;
        // the user's own number of holdings: with more of them than the level looks at, it buys further down each ranking (rules_for in the function)
        const own = d.holdings > 0 ? { positions: d.holdings, top: Math.max(r.top, Math.min(d.holdings, 30)) } : {};
        return Object.assign({}, r, own, d.stopPct > 0 ? { stop: -d.stopPct } : {}, d.takePct > 0 ? { take: d.takePct } : {});
    }
    // How many equal holdings the budget is spread over: the user's own number, or the risk level's. holdings_of() in the
    // stockiq-ai-trader Lambda does the same sum, and buys_per_check() the one below: keep them in step.
    // a level's row of the table with the user's own number of holdings in it, for the texts that describe what will happen
    const withHoldings = (r, d) => r && d && d.holdings > 0 ? Object.assign({}, r, { positions: d.holdings }) : r;
    function positionsOf(d) { return d && d.holdings > 0 ? d.holdings : ((data.options.risk[String(d.risk)] || {}).positions || 0); }
    const buysPerCheck = (positions) => Math.max(3, Math.ceil(positions / 5));
    // The pace a level sets when the three pace fields are left to it ("Automatic"): days to build up, hours between check-ins,
    // days a holding is kept. PACE in the stockiq-ai-trader Lambda, sent as options.pace.
    function paceOf(level) { return (data.options.pace || {})[String(level)] || null; }
    const PACE_FIELDS = ['periodDays', 'everyHours', 'maxHoldDays'];
    const isAuto = (d, key) => Array.isArray(d.auto) && d.auto.includes(key);
    function paceWords(level) {
        const p = paceOf(level);
        return p ? ` Left to the level, it builds the budget up over ${p.periodDays} day${p.periodDays === 1 ? '' : 's'}, checks in ${everyText(p.everyHours)} and keeps a holding at most ${holdText(p.maxHoldDays)}.` : '';
    }
    function riskText(level) {
        const r = levelRules(level);
        if (!r) return '';
        return `${r.name}: spreads the budget over up to ${r.positions} holdings, looks at the top ${r.top} of each screener, sells a holding at ${r.stop}% or +${r.take}%`
            + (r.crypto >= 1 ? ', coins up to the whole budget.' : r.crypto > 0 ? `, up to ${Math.round(r.crypto * 100)}% of the budget in coins (the whole budget if only coin screeners are ticked).` : ', coins only if nothing but coin screeners is ticked.')
            + paceWords(level);
    }
    // How much of the budget is in use, check-in by check-in, when every check-in finds enough to buy and nothing is sold
    // early. The same sums as the stockiq-ai-trader Lambda: allowance() (the budget is released in equal steps over the
    // chosen days, rounded up to whole holdings), the time rule in review_sells() (5 minutes' grace) and, in run_user(),
    // at most 3 buys a check-in (a fifth of the holdings when the user asked for many), no buy under $25 and the coin share. Keep the two in step.
    function buildUp(d, r, limit) {
        const size = d.budgetUsd / r.positions, every = d.everyHours, hold = d.maxHoldDays * 24 - 5 / 60;
        const last = Math.ceil(d.periodDays * 24 / every) + r.positions + 2;    // the budget fully released, then time to settle
        let lots = [], first = 0, peak = 0, count = 0, hours = 0;
        for (let n = 1; n <= last; n++) {
            lots = lots.filter(l => (n - l.n) * every < hold - 1e-9);
            let invested = lots.reduce((s, l) => s + l.usd, 0);
            const pace = d.budgetUsd * Math.min(1, n * every / (d.periodDays * 24));
            const cap = Math.min(d.budgetUsd, Math.ceil(pace / size - 1e-9) * size);
            const buys = Math.min(buysPerCheck(r.positions), Math.floor((cap - invested + 0.005) / size));
            for (let i = 0; i < buys; i++) {
                const usd = Math.min(size, limit - invested);
                if (usd < 25) break;
                lots.push({ n, usd }); invested += usd;
                if (n === 1) first++;
            }
            if (invested > peak + 0.01) { peak = invested; count = lots.length; hours = (n - 1) * every; }
        }
        return { first, peak, count, hours };
    }
    // What the chosen settings mean in practice: every sentence is built from what is selected right now
    function planText(d) {
        const whole = d.budgetUsd, k = themesShare(d);
        d = sharePart(d);
        const r = withHoldings(data.options.risk[String(d.risk)], d);
        if (!r || !(d.budgetUsd > 0) || !(d.periodDays > 0) || !(d.everyHours > 0) || !(d.maxHoldDays > 0)) return '';
        const size = d.budgetUsd / r.positions, start = `It checks in ${everyText(d.everyHours)}.`;
        const up = buildUp(d, r, d.budgetUsd);            // with only coin screeners ticked the whole budget may go into coins (coin_share in the Lambda)
        if (!up.count) return start + ` The ${r.name} level spreads the budget over ${r.positions} holdings, which makes each about ${usd0(size)}: under the $25 smallest buy, so it will buy nothing. Raise the budget.`;
        const quickest = Math.min.apply(null, data.options.everyHours), oftener = d.everyHours > quickest && d.maxHoldDays * 24 > quickest + 1e-9;   // would checking in more often let it hold more?
        const many = up.count === 1 ? '1 holding' : `${up.count} holdings`, full = up.peak >= d.budgetUsd - 0.01;
        const steps = up.hours <= 0 ? ', bought at the first check-in.'
            : `: ${up.first} at the first check-in` + (up.count - up.first === 1 ? ' and one more' : `, then more as the budget is released, all ${up.count}`) + ` after about ${holdText(up.hours / 24)}.`;
        return `${start}${k ? ` ${Math.round(k * 100)}% of the ${usd0(whole)} budget (${usd0(whole * k)}) is the themes part (a trial, under Activity); the shares get the rest.` : ''} Up to ${many} of about ${usd0(size)} each${full ? '' : ' at a time'}${steps}`
            + (full ? ` Then the whole ${usd0(d.budgetUsd)}${k ? ' for shares' : ''} is in use.`
                : ` That is ${usd0(up.peak)} of the ${usd0(d.budgetUsd)}: it buys at most ${buysPerCheck(positionsOf(d))} at a check-in and sells each holding after ${holdText(d.maxHoldDays)}. Keep holdings longer${oftener ? ', or check in more often,' : ''} for it to use more.`)
            + (!sharesOn() && mixed(d) && r.crypto < 1 ? ` Of that, at most ${Math.round(r.crypto * 100)}% (${usd0(d.budgetUsd * r.crypto)}) goes into coins at this level.` : '')
            + (d.everyHours <= 3 && d.screeners.some(k => (data.options.screeners[k] || {}).kind === 'crypto') ? ' A coin is only bought once it has been near the top at two check-ins running (coin rankings change fast and many drop out again within the hour), so coin buying starts one check-in later than this.' : '')
;
    }
    // Under the budget field: how much practice money there is for it, and a plain warning (with the fix) when the budget is more
    function budgetHint(d) {
        const m = data.money;
        if (!m || !(m.reach >= 0)) return '';
        const parts = m.invested > 0 ? `${usd0(m.cash)} of practice cash plus the ${usd0(m.invested)} it has invested` : `the practice cash you have left`;
        if (d.budgetUsd > m.reach) return `<span style="color: #d97706;">⚠ That is more than the practice money there is. Its budget can be at most <strong>${usd0(m.reach)}</strong> (${parts}).</span> <a href="#" data-ap="maxbudget">Set it to ${usd0(m.reach)}</a>`;
        return `Its budget can be up to ${usd0(m.reach)}: ${parts}.`;
    }
    // shares and coins both ticked? Then the level's coin share applies
    function mixed(d) {
        const kinds = d.screeners.map(k => (data.options.screeners[k] || {}).kind);
        return kinds.includes('crypto') && kinds.some(k => k !== 'crypto');
    }
    // The stop that follows a holding: the user's choice (settings.trailMode; TRAIL_MODES in the stockiq-ai-trader Lambda)
    const TRAILS = {
        gains: { name: 'Protects a gain (starts once a holding has risen)', says: 'when a stop that follows a rising holding is hit (a holding that keeps rising is kept: the stop starts once it has risen beyond its own normal wobble and sells only if it then falls back; how far it may fall is set from how much that holding normally moves: more for a jumpy coin, less when its screener figures weaken or time is short)',
                 help: 'The stop only starts once a holding has risen beyond its normal wobble; from then on it follows the price up and sells if it slips back too far. A holding that just drifts down is left to the loss limit, the time limit and its screener figures.' },
        full: { name: 'From the moment it is bought (a full trailing stop loss)', says: 'when its trailing stop is hit (the stop sits under the price from the moment of buying and follows it up, selling only on a fall-back; how far it may fall is set from how much that holding normally moves: more for a jumpy coin, less when its screener figures weaken or time is short)',
                help: 'The stop sits under the price from the moment of buying and follows it up, so a holding that falls is cut early as well. It loses less on a faller, but ordinary dips will shake it out more often.' },
        off: { name: 'Off', says: '', help: 'Nothing follows the price. It sells only at your loss limit and gain mark, at the time limit, and when its screener figures turn.' }
    };
    const trailOf = (d) => TRAILS[d.trailMode] ? d.trailMode : 'gains';
    function paceText(d) {
        const r = levelRules(d.risk);
        if (!r || !(d.maxHoldDays > 0) || !(d.everyHours > 0)) return '';
        const late = d.maxHoldDays * 24 < d.everyHours - 1e-9, quick = d.everyHours < 3 || d.maxHoldDays < 1;
        const shares = d.screeners.some(k => (data.options.screeners[k] || {}).kind !== 'crypto');
        return `It sells a holding once it has had it for ${holdText(d.maxHoldDays)}, whatever the price, and sooner at ${r.stop}% or +${r.take}%${TRAILS[trailOf(d)].says ? ', ' + TRAILS[trailOf(d)].says + ',' : ''} or when its screener signal turns negative or it slips far down the ranking. The money is then free for the next buy.${d.aiSell === true ? ' At every check-in the AI model also reviews each holding against the latest screener figures and recent headlines, and may sell it earlier than these rules.' : ''}`
            + (shares && d.selfTune !== false ? ' One exception, for as long as "Try changes to its own rules" is on: every second pair of shares it buys is a "patient" share in a trial. A patient share is sold only by the limits and the time above, not when its signal turns or it slips down the ranking' + (d.aiSell === true ? ', and the AI model does not review it.' : '.') : '')
            + (late ? ` It only checks in ${everyText(d.everyHours)}, though, so in practice a holding is sold at the next check-in, about ${holdText(d.everyHours / 24)} after it was bought. Check in more often for it to be sold on time.` : '')
            + (quick && shares ? ' Shares are only traded while their market is open and their rankings change little within a day, so quick settings mostly make a difference for coins.' : '')
            + (data.costEachWay ? ` A trading cost of ${data.costEachWay}% is taken off each buy and each sale${quick ? ': trading this often gives up a good part of every result to costs' : ''}.` : '')
            + (shares && d.maxHoldDays <= 2 ? ' In a replay of four years of prices, shares kept only a day or two lost to those costs at every level; kept a week or longer they did not.' : '');
    }
    function statusText() {
        const s = data.settings, last = data.state && data.state.lastRun;
        if (!s.enabled) return 'Off. Nothing is bought or sold automatically.';
        if (!s.screeners.length) return 'On, but no screener is chosen yet. Tick at least one below and it will start at the next check-in.';
        const r = withHoldings(data.options.risk[String(s.risk)] || {}, s);
        const t = data.themes && data.themes.on ? data.themes : null, forShares = t ? s.budgetUsd * (1 - t.share) : s.budgetUsd;
        const holding = data.holding ? ` Holding ${data.holding.count} of up to ${r.positions}: ${usd0(data.holding.investedUsd)} of the ${usd0(forShares)} ${t ? 'for shares' : 'budget'} is invested.`
            + (t ? ` The themes part (trial) holds ${t.held.length} fund${t.held.length === 1 ? '' : 's'} (${usd0(t.invested)} of its ${usd0(t.target)}).` : '') : '';
        const next = data.nextCheck && data.nextCheck.at
            ? ` Next check-in about ${when(data.nextCheck.at)}, when the ${andList(data.nextCheck.markets)} market${data.nextCheck.markets.length > 1 ? 's are' : ' is'} open.`
            : (data.nextCheck === null ? ' No check-in is due in the next ten days.' : '');
        return 'On.' + holding + (last ? ` Last check-in ${when(last)}.` : (next ? '' : ' First check-in at the next hourly check.')) + next;
    }
    // ---------------------------------------------------------------- what happens next: countdowns, and what needs the user
    // How long until a time, in words that tick: "in 1 h 48 min", "in 12 min 05 s", "any moment now"
    function leftText(iso) {
        const ms = Date.parse(iso) - (Date.now() + skew);
        if (!isFinite(ms)) return '';
        if (ms <= 0) return 'any moment now';
        const sec = Math.floor(ms / 1000);
        if (sec < 60) return `in ${sec} s`;
        if (sec < 3600) return `in ${Math.floor(sec / 60)} min ${String(sec % 60).padStart(2, '0')} s`;
        const min = Math.ceil(sec / 60);
        if (min < 1440) return `in ${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')} min`;
        const hours = Math.round(min / 60), days = Math.floor(hours / 24);
        return `in ${days} day${days === 1 ? '' : 's'}${hours % 24 ? ' ' + (hours % 24) + ' h' : ''}`;
    }
    const until = (iso, cls) => `<span class="ap-count ${cls || ''}" data-ap-until="${esc(iso)}">${esc(leftText(iso))}</span>`;
    // Every second: only the countdown texts are touched, nothing is redrawn
    function tick() {
        if (!data || !document.querySelectorAll) return;
        Array.from(document.querySelectorAll('[data-ap-until]')).forEach(x => { const t = leftText(x.getAttribute('data-ap-until')); if (x.textContent !== t) x.textContent = t; });
    }
    // Under the status box: the countdown to the next check-in
    function countLine() {
        const n = data.settings.enabled && data.nextCheck && data.nextCheck.at;
        return n ? `<div class="ap-countline">⏱ Next check-in ${until(n)} <span style="color: var(--text-secondary);">(${esc(when(n))}).</span> <a href="#ap-coming" data-ap-part="activity" data-ap-goto="ap-coming">What happens then</a></div>` : '';
    }
    // What needs the user. Its own reviews and trials do not: they happen by themselves at check-ins
    function needsHtml() {
        if (!Array.isArray(data.needs)) return '';
        if (!data.needs.length) return `<div id="ap-needs" class="ap-needs none">✓ Nothing needs you right now${data.settings.enabled ? ': its settings, cash and screeners are all in order, and it runs by itself' : ''}.</div>`;
        return `<div id="ap-needs" class="ap-needs" role="status"><strong>⚠ Needs you</strong><ul>${data.needs.map(n => `<li>${esc(n.text)}${n.at ? ` <span style="color: var(--text-secondary);">(${esc(when(n.at))})</span>` : ''}</li>`).join('')}</ul></div>`;
    }
    // The dashboard's own tab for this panel carries a mark while something needs the user, so it is seen from any tab
    function markTab() {
        const tab = document.querySelector && document.querySelector('[data-dash-tab="autopilot"]');
        if (!tab || typeof tab.textContent !== 'string') return;
        const n = data && data.allowed && Array.isArray(data.needs) ? data.needs.length : 0;
        const want = '🤖 AI autopilot (Beta)' + (n ? ' ⚠' : data && !data.allowed && data.locked === 'plan' ? ' 🔒' : '');
        if (tab.textContent !== want) { tab.textContent = want; tab.title = !n && want.indexOf('🔒') > 0 ? 'Part of the paid plans' : n ? `${n === 1 ? 'One thing needs' : n + ' things need'} you: see "Needs you" on this tab` : ''; }
    }
    // The first thing under Activity: what is coming, soonest first, each with a countdown; then what goes by the number of trades
    function andList(names) { names = (names || []).slice(); return names.length < 2 ? names.join('') : names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1]; }
    // What happens next (17 Oct 2026, on the owner's real list: 51 rows, 39 of them "X is sold at the latest"): the holdings'
    // last days are one row (the first of them, and how many follow, the list folded under it), and a release of the budget
    // at the same minute as a check-in is left out: that check-in's row already says what it may buy then.
    function comingRows(list) {
        const timed = list.filter(c => c.at), sells = timed.filter(c => c.kind === 'sell'), out = [];
        timed.forEach(c => {
            if (c.kind === 'sell' && sells.length > 2) return;
            if (c.kind === 'release') { const check = timed.find(x => x.kind === 'check' && x.at === c.at); if (check) return; }
            out.push(c);
        });
        if (sells.length > 2) {
            const first = sells[0], last = sells[sells.length - 1], days = (x) => esc(when(x.at).replace(/,? \d\d:\d\d.*$/, ''));
            const at = out.findIndex(c => Date.parse(c.at) > Date.parse(first.at)), row = { at: first.at, kind: 'sells', count: sells.length, list: sells,
                html: `${sells.length} holdings reach the end of their holding time between ${days(first)} and ${days(last)}, and are sold at the latest then (each at a check-in while its market is open). The first: ${esc(first.text.split(' is sold')[0])}.` };
            if (at < 0) out.push(row); else out.splice(at, 0, row);
        }
        return out;
    }
    // The market-risk gauge (18 Oct 2026, the owner's idea): five steps from very low to very high, for information. It holds no
    // cash: a replay found that holding more cash by it made less than staying invested. Each buy records it, so the record can tell.
    function gaugeHtml() {
        const g = data.gauge;
        if (!g || typeof g.level !== 'number') return '';
        const colours = ['#2e9e5b', '#7dbb4a', '#d4a52a', '#e07a2f', '#d0453c'];
        const steps = [0, 1, 2, 3, 4].map(k => `<span style="display: inline-block; width: 22px; height: 8px; margin-right: 2px; border-radius: 2px; background: ${k <= g.level ? colours[g.level] : 'var(--border-color)'};"></span>`).join('');
        const why = [g.spy < g.avg200 ? 'the S&amp;P 500 is below its 200-day average' : 'the S&amp;P 500 is above its 200-day average',
                     g.spy < g.avg50 ? 'below its 50-day average' : 'above its 50-day average',
                     `the VIX (the swings the market expects) is ${g.vix}` + (g.vix > 30 ? ', over 30' : g.vix > 20 ? ', over 20' : ', under 20')];
        return `<div class="ap-section" id="ap-gauge"><div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px;"><strong>Market risk now: ${esc(g.name)}</strong><span aria-label="${esc(g.name)}, ${g.level} of 4">${steps}</span></div>`
            + `<details data-ap-fold="gauge" ${openDetails.gauge ? 'open' : ''} style="margin-top: 4px;"><summary class="ap-sub">What it is, and why it does not hold cash</summary><div class="ap-help" style="margin-top: 4px;">One point each when the S&amp;P 500 is below its 200-day average, below its 50-day average, and when the VIX is over 20 and over 30. Now: ${why.join('; ')}. It is shown for information and recorded with every buy; it does not make the autopilot hold cash. Tested on four years of prices, holding more cash when it was high made less than staying invested (the worst falls were a little smaller). The record will show whether buys made at a high reading do worse.</div></details></div>`;
    }
    function comingHtml() {
        const list = data.coming;
        if (!Array.isArray(list) || !list.length) return '';
        const timed = comingRows(list), counted = list.filter(c => !c.at);
        const row = (c, i) => `${until(c.at, i === 0 ? 'first' : '')}<div><time>${esc(when(c.at))}</time>${c.html || esc(c.text)}${c.list ? `<details data-ap-fold="coming-sells" ${openDetails['coming-sells'] ? 'open' : ''}><summary>Each of the ${c.count}</summary><ul style="margin: 4px 0 0; padding-left: 18px;">${c.list.map(x => `<li>${esc(when(x.at))}: ${esc(x.text.split(':')[0])}</li>`).join('')}</ul></details>` : ''}</div>`;
        const rest = timed.slice(4);
        return `<div class="ap-section" id="ap-coming" style="scroll-margin-top: 120px;"><h4>What happens next <span class="ap-sub">a forecast from its settings: the prices and rankings of the moment decide what is really bought or sold</span></h4>
            <div class="ap-next">${timed.slice(0, 4).map(row).join('')}</div>
            ${rest.length ? `<details data-ap-fold="coming" ${openDetails.coming ? 'open' : ''}><summary>${rest.length} more further ahead</summary><div class="ap-next">${rest.map(c => row(c, 1)).join('')}</div></details>` : ''}
            ${counted.length ? `<div class="ap-next" style="margin-top: 12px;">${counted.map(c => `<span class="ap-count">${typeof c.after === 'number' ? (c.after > 0 ? `after ${c.after} more finished trade${c.after === 1 ? '' : 's'}` : 'at the next check-in') : 'not planned'}</span><div>${esc(c.text)}</div>`).join('')}</div>
            <div style="font-size: 0.8rem; margin-top: 8px;">A finished trade is a holding it bought and has sold. Its reviews and trials happen by themselves at check-ins: you do not have to approve or push anything. It can only adjust its own five trading rules, inside fixed limits; changes to the program itself are made by a person, never by the autopilot.</div>` : ''}
        </div>`;
    }
    // Under "Email me its reviews": what became of the last email, and a way to check that they arrive
    function mailHtml() {
        if (!('mail' in data)) return '';
        const m = data.mail, to = userId() || 'your account address';
        const last = !m ? 'No email has been sent yet.'
            : m.ok ? `Last email: "${esc(m.subject)}", ${esc(when(m.t))}, accepted by the mail service for ${esc(to)}. If it is not in your inbox, look in junk.`
            : `<span style="color: #d97706;">Last email could not be sent (${esc(m.why || 'no reason given')}), ${esc(when(m.t))}.</span>`;
        return `<div id="ap-mail-state" class="ap-help" style="margin-left: 24px;">${last} <a href="#" data-ap="mailtest"${working === 'mailtest' ? ' class="busy"' : ''}>${working === 'mailtest' ? 'Sending…' : 'Send me a test email'}</a></div>`;
    }

    // The line beside the button: whether what is on screen is saved, and what to do next
    function savedState() {
        if (saveError) return { text: 'Not saved: ' + saveError, bad: true };
        if (saving || saveTimer || isDirty()) return { text: 'Saving…', bad: false };
        const s = data.settings;
        const next = !s.enabled ? ' Use the switch at the top right to turn it on.' : !s.screeners.length ? ' Tick at least one screener for it to start.' : '';
        return { text: (savedOnce ? '✓ Saved.' : 'Changes are saved as you make them.') + next, bad: false };
    }
    // ---------------------------------------------------------------- how the budget is spread over the markets ticked
    // The same rules as market_split() and market_slots() in the stockiq-ai-trader Lambda: keep the two in step
    // (autopilot_plan_check.py compares them). A share the user set stands; what is left is spread evenly over the other
    // ticked markets, coins never above the level's share while a share market is ticked too; then whole holdings.
    // MARKET_SPLIT_START
    function marketSplit(d) {
        const all = data.options.groups || [], r = data.options.risk[String(d.risk)] || {};
        // a market whose every ticked screener is resting gets no share (the function's market_split(settings, resting))
        const resting = data.resting || {};
        const groups = all.filter(g => d.screeners.some(k => (data.options.screeners[k] || {}).group === g && !resting[k])), own = {};
        groups.forEach(g => { const v = (d.shares || {})[g]; if (typeof v === 'number' && isFinite(v)) own[g] = v / 100; });
        const left = Math.max(0, 1 - Object.keys(own).reduce((a, g) => a + own[g], 0)), auto = groups.filter(g => !(g in own)), out = Object.assign({}, own);
        let coin = 0;
        if (auto.includes('Coins') && groups.length > 1) coin = out.Coins = Math.min(r.crypto || 0, left / auto.length);
        const rest = auto.filter(g => g !== 'Coins' || groups.length === 1);
        rest.forEach(g => { out[g] = (left - coin) / rest.length; });
        const split = {}; groups.forEach(g => { split[g] = out[g] || 0; });
        return split;
    }
    function marketSlots(d) {
        const all = data.options.groups || [], positions = positionsOf(d), split = marketSplit(d);
        const exact = {}, slots = {}; let sum = 0, used = 0;
        Object.keys(split).forEach(g => { exact[g] = split[g] * positions; slots[g] = Math.floor(exact[g] + 1e-9); sum += exact[g]; used += slots[g]; });
        const spare = Math.min(positions, Math.floor(sum + 0.5 + 1e-9)) - used;
        Object.keys(split).sort((a, b) => (Math.round((exact[b] - slots[b]) * 1e6) - Math.round((exact[a] - slots[a]) * 1e6)) || (all.indexOf(a) - all.indexOf(b)))
            .slice(0, Math.max(0, spare)).forEach(g => { slots[g]++; });
        return slots;
    }
    // MARKET_SPLIT_END
    const sharesOn = () => !!(data && data.options && Array.isArray(data.options.groups) && 'shares' in data.settings);
    const holdingsWord = (n) => n === 1 ? '1 holding' : `${n} holdings`;
    const stepPct = (k, positions) => Math.round(k / positions * 1e6) / 1e4;                // k holdings as a percent of the budget
    const stepLabel = (k, positions, size) => `${Math.round(k / positions * 100)}% (${holdingsWord(k)}, ${usd0(k * size)})`;
    // What a market would get on automatic, the others staying as they are
    function autoSlots(d, group) { const sh = Object.assign({}, d.shares); delete sh[group]; return marketSlots(Object.assign({}, d, { shares: sh }))[group] || 0; }
    // One market's line under its screeners: its share of the budget, automatic unless picked from the steps
    // one colour per market, the same in its share box and in the bar that shows the split
    const MARKET_COLOURS = ['#3b82f6', '#22c55e', '#a855f7', '#ef4444', '#f59e0b', '#14b8a6'];
    const marketColour = (group) => MARKET_COLOURS[Math.max(0, (data.options.groups || []).indexOf(group)) % MARKET_COLOURS.length];
    const isTicked = (d, group) => d.screeners.some(k => (data.options.screeners[k] || {}).group === group);
    // The split at a glance: a bar with one coloured part per market, as wide as its share of the budget
    function splitBar(d) {
        if (!sharesOn()) return '';
        const positions = positionsOf(d), slots = marketSlots(d), groups = Object.keys(slots).filter(g => slots[g] > 0);
        if (!positions) return '';
        if (!groups.length) return '<span class="idle" style="flex: 1;">Tick a screener and its market gets a share of the budget</span>';
        const used = groups.reduce((a, g) => a + slots[g], 0), pctOf = (n) => Math.round(n / positions * 100);
        return groups.map(g => `<span style="flex: ${slots[g]} 1 0; background: ${marketColour(g)};" title="${esc(g)}: ${holdingsWord(slots[g])}">${esc(g)} ${pctOf(slots[g])}%</span>`).join('')
            + (used < positions ? `<span class="idle" style="flex: ${positions - used} 1 0;" title="Not given to any market: it stays in cash">cash ${pctOf(positions - used)}%</span>` : '');
    }
    function shareRow(d, group, index) {
        if (!sharesOn()) return '';
        d = sharePart(d);
        const r = data.options.risk[String(d.risk)] || {}, positions = positionsOf(d), size = d.budgetUsd / (positions || 1);
        const ticked = isTicked(d, group);
        if (!positions) return '';
        // nothing ticked in this market: say so, where its share would be (an empty space looked like something missing)
        if (!ticked) return `<div class="ap-share none">No share of the budget: nothing is ticked in this market.</div>`;
        const rested = restedUntil(d, group);
        if (rested !== null) return `<div class="ap-share none">No share of the budget for now: ${rested ? 'resting until ' + esc(rested) : 'resting'}. Its part goes to the other markets until then.</div>`;
        const mine = typeof (d.shares || {})[group] === 'number', chosen = mine ? Math.min(positions, Math.max(0, Math.round(d.shares[group] / 100 * positions))) : -1;
        // With many holdings a step for each made a menu of 51 lines (the owner's 50): steps of about a tenth then, and always the
        // value that is set. Any whole number of holdings is still allowed; the menu just offers fewer of them.
        const every = positions > 20 ? Math.ceil(positions / 10) : 1;
        const steps = []; for (let k = 0; k <= positions; k++) if (k % every === 0 || k === positions || k === chosen) steps.push(`<option value="${stepPct(k, positions)}" ${k === chosen ? 'selected' : ''}>${stepLabel(k, positions, size)}</option>`);
        return `<div class="ap-share" style="border-left-color: ${marketColour(group)};"><div class="ap-share-label"><span>Share of ${esc(ofWhat(d))}</span> <span class="ap-auto ${mine ? 'own' : ''}">${mine ? 'set by you' : 'automatic'}</span></div><select id="ap-share-${index}" data-ap-share="${esc(group)}" aria-label="Share of the budget for ${esc(group)}" title="Choose how much of the budget this market may hold, or leave it on Automatic"><option value="auto" ${mine ? '' : 'selected'}>Automatic: ${stepLabel(autoSlots(d, group), positions, size)}</option>${steps.join('')}</select></div>`;
    }
    // A market whose every ticked screener is resting: the day the last rest ends ('' if not known), or null if it is not resting
    function restedUntil(d, group) {
        const resting = data.resting || {}, keys = d.screeners.filter(k => (data.options.screeners[k] || {}).group === group);
        if (!keys.length || !keys.every(k => resting[k])) return null;
        const last = keys.map(k => Date.parse(resting[k]) || 0).reduce((a, b) => Math.max(a, b), 0);
        return last ? day(new Date(last).toISOString()) : '';
    }
    // In words, under the screeners: where the budget goes, and what is left over or left out
    function splitText(d) {
        if (!sharesOn()) return '';
        d = sharePart(d);
        const r = data.options.risk[String(d.risk)] || {}, positions = positionsOf(d), size = d.budgetUsd / (positions || 1), slots = marketSlots(d), groups = Object.keys(slots);
        if (!groups.length || !positions) return '';
        const mine = (g) => typeof (d.shares || {})[g] === 'number';
        const used = groups.reduce((a, g) => a + slots[g], 0), spare = positions - used, none = groups.filter(g => !slots[g]);
        const how = groups.length === 1 && slots[groups[0]] === positions ? `How ${ofWhat(d)} is spread: all of it goes to ${groups[0]}, the one market ticked (${holdingsWord(positions)} of ${usd0(size)}).`
            : `How ${ofWhat(d)} is spread: ` + groups.filter(g => slots[g]).map(g => `${g} ${holdingsWord(slots[g])} (${usd0(slots[g] * size)}, ${Math.round(slots[g] / positions * 100)}%)`).join(' · ') + '.';
        const left = none.map(g => ` Nothing goes to ${g}: ` + (mine(g) ? 'you set its share to 0%.' : g === 'Coins' && !(r.crypto > 0) && groups.length > 1 ? `the ${r.name} level puts nothing into coins while a share market is ticked too (pick a share for coins yourself to change that).`
            : groups.some(mine) ? 'the shares set by hand leave nothing for it.' : `there are more markets ticked than the ${positions} holdings of this level.`)).join('');
        const idle = spare > 0 && groups.some(mine) ? ` ${holdingsWord(spare)} (${usd0(spare * size)}) ${spare === 1 ? 'is' : 'are'} not given to any market and stay${spare === 1 ? 's' : ''} in cash.` : '';
        const rule = groups.length > 1 ? ` On automatic the budget is spread evenly over the markets ticked${groups.includes('Coins') && !(r.crypto >= 1) ? ` (coins at most ${Math.round((r.crypto || 0) * 100)}% at this level)` : ''}; pick a share yourself to change one. A market never takes more than its share, whichever opens first.` : '';
        const rested = (data.options.groups || []).map(g => [g, restedUntil(d, g)]).filter(([, u]) => u !== null)
            .map(([g, u]) => ` ${g} ${g.endsWith('s') ? 'get' : 'gets'} no share for now: ${u ? 'resting until ' + u : 'resting'}, so its part goes to the other markets.`).join('');
        return how + left + idle + rested + rule;
    }

    function screenerGroups(all) {
        const groups = [];
        Object.keys(all).forEach(k => { const g = all[k].group || 'Screeners'; let row = groups.find(x => x[0] === g); if (!row) groups.push(row = [g, []]); row[1].push(k); });
        return groups;
    }

    // ---------------------------------------------------------------- "How it is doing": its own closed trades
    function recordHtml() {
        const c = data.scorecard, need = data.minSample || 8, plans = data.plans || [], on = data.settings.enabled;
        const heldPlan = (p) => `<strong style="color: var(--text-primary);">${esc(p.label)}</strong> (bought ${esc(when(p.boughtAt))}; ${on ? `it sells it at the check-in around ${esc(when(p.sellBy))} at the latest, sooner at ${p.stop}% or +${p.take}%` : 'the autopilot is off, so it stays until you sell it'}${on && p.closed ? `; the ${esc(p.market)} market is closed now, so nothing happens to it until it opens${p.opens ? ` (around ${esc(when(p.opens))})` : ''}` : ''}${on && p.mode === 'full' && typeof p.floor === 'number' && !(p.peak >= p.arm) ? `; its trailing stop is at ${pc(p.floor)} and follows the price up` : on && typeof p.floor === 'number' ? `; it has been up ${pc(p.peak)} at its best and is sold if it slips back to ${pc(p.floor)}` : on && p.mode === 'off' ? '; no stop follows it' : on && typeof p.arm === 'number' ? `; while it rises it is kept, and once it has been up ${p.arm}% a stop follows it up and sells only on a fall-back` : ''}${on && typeof p.move === 'number' ? ` (it normally moves about ${p.move.toFixed(1)}% between check-ins and may slip ${p.room} such moves from its best${p.tight ? '; the AI review asked for a tighter stop' : ''})` : ''}${on && p.view ? `; the AI model's latest review, ${esc(when(p.view.t))}${p.view.larger ? ', by the larger model' : ''}: ${p.view.sell ? 'sell' : p.view.tighten ? 'keep, with a tighter stop' : 'keep'} (${esc(p.view.text)})` : ''})`;
        // one row a holding: what differs from the others at a glance, the full plan folded under it (ten holdings in one paragraph were unreadable, and there can be fifty)
        const chip = (text, tone) => `<span class="ap-hchip${tone ? ' ' + tone : ''}">${text}</span>`;
        // "…volume (Crypto (top coins) rank 1, score +4.0; chosen by the AI model)" → "…volume": the closing bracket and all that belongs to it
        const lastBracketOff = (t) => { t = t.trim(); if (!t.endsWith(')')) return t; let depth = 0; for (let i = t.length - 1; i >= 0; i--) { if (t[i] === ')') depth++; else if (t[i] === '(' && --depth === 0) return t.slice(0, i).trim() || t; } return t; };
        // what it was bought for, from the activity list (the company's name and the reason, without the bracket that repeats the rank)
        const boughtFor = (p) => { const e = (data.log || []).slice().reverse().find(x => x.type === 'buy' && x.symbol === p.label); return e ? { name: e.name || '', why: lastBracketOff(String(e.text || '')) } : null; };
        // A row is the holding at a glance and opens to its plan. In the row: its name, the company and why it was bought, and a tag
        // only for what is particular to it now (the rules every holding shares are in the plan, not repeated on every row).
        const heldRow = (p) => {
            const chips = [], b = boughtFor(p);
            if (on && p.closed) chips.push(chip(`${esc(p.market)} market closed${p.opens ? ' until ' + esc(when(p.opens)) : ''}`, 'quiet'));
            if (on && p.mode === 'full' && typeof p.floor === 'number' && !(p.peak >= p.arm)) chips.push(chip(`trailing stop at ${pc(p.floor)}`));
            else if (on && typeof p.floor === 'number') chips.push(chip(`has been up ${pc(p.peak)}: sold if it falls back to ${pc(p.floor)}`, 'up'));
            if (on && p.patient) chips.push(chip('patient share (trial)', 'trial'));
            if (on && p.view && (p.view.sell || p.view.tighten)) chips.push(chip(`AI review: ${p.view.sell ? 'sell' : 'keep, tighter stop'}`));
            if (!on) chips.push(chip('autopilot off: it stays until you sell it', 'quiet'));
            const what = b ? `${b.name ? esc(b.name) + ' · ' : ''}${esc(b.why)}` : `bought ${esc(when(p.boughtAt))}`;
            return `<details class="ap-held-row"><summary><strong class="ap-held-name">${esc(p.label)}</strong><span class="ap-held-main"><span class="ap-held-what">${what}</span>${chips.length ? `<span class="ap-held-chips">${chips.join('')}</span>` : ''}</span><span class="ap-held-open">its plan</span></summary><div class="ap-held-plan">${heldPlan(p)}.</div></details>`;
        };
        const sorted = plans.filter(p => !p.theme).sort((x, y) => String(y.boughtAt).localeCompare(String(x.boughtAt))), shown = sorted.slice(0, 8), older = sorted.slice(8);
        const held = plans.length
            ? `<div>Holding now: ${plans.length}, newest first. A row opens to its plan: when it is sold at the latest, its limits and its own stop.</div><div class="ap-held">${shown.map(heldRow).join('')}${older.length ? `<details class="ap-held-rest"><summary>and ${older.length} bought earlier</summary>${older.map(heldRow).join('')}</details>` : ''}</div>`
            : `<div>Holding nothing right now.</div>`;
        const m = data.month && data.month.last30, before = data.month && data.month.before30;
        const month = m && m.n ? `<div style="margin-top: 4px;">Last 30 days: <span style="color: ${tint(m.usd)}; font-weight: 600;">${usd2(m.usd)}</span> from ${m.n} finished trade${m.n === 1 ? '' : 's'} (${m.up} up)${m.pct !== null ? `, which is <span style="color: ${tint(m.pct)}; font-weight: 600;">${(m.pct >= 0 ? '+' : '') + m.pct.toFixed(2)}%</span> of the ${usd0(data.settings.budgetUsd)} budget` : ''}.${before && before.n ? ` The 30 days before: ${usd2(before.usd)} from ${before.n}${before.pct !== null ? ' (' + (before.pct >= 0 ? '+' : '') + before.pct.toFixed(2) + '%)' : ''}.` : ''}${typeof m.afterCosts === 'number' && data.costEachWay && Math.abs(m.afterCosts - m.usd) > 0.005 ? ` Trades made before 11 Oct 2026 had no trading cost taken off: with ${data.costEachWay}% on each buy and each sale the figure would be <span style="color: ${tint(m.afterCosts)}; font-weight: 600;">${usd2(m.afterCosts)}</span>.` : data.costEachWay ? ` A trading cost of ${data.costEachWay}% on each buy and each sale is already in these figures.` : ''}</div>` : '';
        if (!c || !c.n) return `<div class="ap-section"><h4>How it is doing</h4>${held}${barHtml()}<div style="margin-top: 4px;">No finished trades yet: nothing it bought has been sold. Each sale will be listed here with its result, and the autopilot uses that record at later check-ins.</div></div>`;
        const g = c.groups || {};
        // the comparison with an index fund is a column of its own only when it says something the average does not
        // (after a weekend of coin trades the fund has not moved, and the column would repeat the average)
        const versus = Object.keys(g).some(k => (g[k] || []).some(x => typeof x.vs === 'number' && Math.abs(x.vs - x.avg) >= 0.05));
        const cols = versus ? 5 : 4;
        const row = (x) => `<tr><td class="ap-bd-name">${esc(x.label)}</td><td>${x.n}</td><td class="ap-bd-num" style="color: ${tint(x.avg)};">${pc(x.avg)}</td><td>${x.up} of ${x.n}</td>${versus ? `<td class="ap-bd-num" style="color: ${tint(x.vs)};">${pc(x.vs)}</td>` : ''}</tr>`;
        const section = (title, list) => list && list.length ? `<tr class="ap-bd-gap"><td colspan="${cols}"></td></tr><tr class="ap-bd-head"><td colspan="${cols}">${title}</td></tr>` + list.map(row).join('') : '';
        // The AI model's notes are not shown here any more (17 Oct 2026): they restated the breakdown above in words, with the
        // counts of the day they were written, so the two disagreed on the page. The model still reads them when it chooses.
        const lessons = '';
        return `<div class="ap-section"><h4>How it is doing</h4>
            ${held}${barHtml()}${month}
            <div style="margin-top: 4px;">${c.n} finished trade${c.n === 1 ? '' : 's'} in all: ${c.up} up, ${c.n - c.up} down or level, average <span style="color: ${tint(c.avg)}; font-weight: 600;">${pc(c.avg)}</span> each.${c.n < need ? ` Fewer than ${need} trades: too few to conclude anything yet.` : ''}</div>
            <details id="ap-breakdown" ${breakdownOpen ? 'open' : ''} style="margin-top: 6px;"><summary>Breakdown</summary><div style="overflow-x: auto;"><table class="ap-bd">
                <tr><th style="text-align: left; padding-left: 0;">Finished trades, grouped</th><th>Trades</th><th>Average</th><th title="How many of the trades finished with a gain">Made money</th>${versus ? '<th title="The average result minus what an S&amp;P 500 index fund did over the same time">Against an index fund</th>' : ''}</tr>
                ${section('By screener', g.screener)}${section('By place in the screener ranking when bought', g.rank)}${section('By RSI when bought', g.rsi)}${section('By how far above its 52-week low when bought (shares)', g.above)}${section('By how long it had stayed near the top when bought', g.stay)}${section('By who chose', g.chosen)}${section('By how it was sold', g.exit)}
            </table></div><div style="font-size: 0.8rem; margin-top: 8px;">Only trades the autopilot made and has finished are counted here. What you buy and sell yourself is on the Practice portfolio tab (its "Sold" list, and "Your own buys" above the graph). ${versus ? '' : 'The comparison with an S&amp;P 500 index fund is left out while it would only repeat the average (the share market has not traded since these trades, or there is nothing to compare yet). '}A group needs ${need} trades before the autopilot acts on it. A screener whose recent trades clearly lag an S&amp;P 500 index fund is rested for two weeks. Past results of fake-money trades; they say nothing certain about the future.</div></details>
            ${lessons}
        </div>`;
    }

    // ---------------------------------------------------------------- "Improving its own rules": what it has changed, is trying, has tried
    function ruleWords(r) {
        return `sells at ${r.stop}% or +${r.take}%; ${r.trailMode === 'off' ? 'no stop follows a holding (switched off)' : r.trailMode === 'full' ? 'a trailing stop follows each holding from the moment it is bought, set from how much that holding normally moves and from its screener figures now' : 'a stop follows a rising holding, set from how much that holding normally moves and from its screener figures now'}; buys from the top ${r.top} of a ranking` + (r.max_rsi >= 100 ? '' : ` with RSI under ${r.max_rsi}`);
    }
    // ---------------------------------------------------------------- progress, a batch of finished trades at a time
    // After every batch (20) the function compares it with the batch before; if it did no better it looks into why and acts
    // within its own rules. This shows each batch, the verdict, and what it did.
    // The themes part (a trial since 18 Oct 2026): what it holds, when it changes, how it is doing, and the AI model's daily calls
    function themesHtml() {
        const t = data.themes;
        if (!t) return '';
        if (!t.on) return data.settings.enabled ? `<div class="ap-section"><h4>Themes part <span class="ap-sub">a trial</span></h4><div style="font-size: 0.85rem;">It runs while "Try changes to its own rules" is on and at least one share screener is ticked: ${Math.round(t.share * 100)}% of the budget is then held in the ${t.count} strongest of 14 sector and theme funds, changed once a month.</div></div>` : '';
        const box = (key, title, inner) => `<details data-ap-fold="${esc(key)}" ${openDetails[key] ? 'open' : ''} style="margin-top: 6px;"><summary>${esc(title)}</summary>${inner}</details>`;
        const names = (t.ranking || []).reduce((o, r) => (o[r.symbol] = r, o), {});
        const held = t.held.length ? t.held.map(h => `<strong style="color: var(--text-primary);">${esc(h.symbol)}</strong> ${esc(h.name)} (${usd0(h.cost)}${names[h.symbol] ? `, ${pc(names[h.symbol].trend)} over the past year` : ''})`).join(' · ') : 'nothing yet: it buys at the first check-in while the US market is open';
        const r = t.trades || {}, done = r.n ? `${r.n} fund${r.n === 1 ? '' : 's'} sold so far, ${usd2(r.usd)} in all, ${pc(r.avg)} each${r.vs !== null && r.vs !== undefined ? `, ${pc(r.vs)} against an S&P 500 fund over the same days` : ''}.` : 'No fund sold yet: its first result comes with the first monthly change.';
        const ai = t.ai || {}, calls = (ai.recent || []).filter(c => c.view);
        const aiLine = ai.at ? `Its last read (${esc(when(ai.at))})${ai.theme ? `: “${esc(String(ai.theme).replace(/[.\s]+$/, ''))}”` : ''}. ${ai.scored ? `${ai.right} of ${ai.scored} of its calls scored so far were right` : 'None of its calls has been scored yet'}${ai.scored < 30 ? ' (too few to read under 30)' : ''}.` : 'It has not read the news yet: it does so every trading day while the US market is open.';
        const table = (t.ranking || []).length ? box('themes-rank', 'The 14 funds by their past year, as last ranked', `<table class="ap-bd" style="width: 100%;"><tr><th style="text-align: left;">Fund</th><th>Past year (less the last month)</th><th>3 months</th></tr>${t.ranking.map((x, i) => `<tr><td style="text-align: left;">${i < t.count ? '<strong>' : ''}${esc(x.symbol)} ${esc(x.name)}${i < t.count ? '</strong>' : ''}</td><td>${pc(x.trend)}</td><td>${pc(x.m3)}</td></tr>`).join('')}</table>`) : '';
        const callList = calls.length ? box('themes-calls', 'Its latest calls', `<ul style="margin: 4px 0 0 18px; padding: 0;">${calls.map(c => `<li>${esc(when(c.at))}: ${esc(c.symbol)} ${c.view === 'better' ? 'better' : 'worse'} than an S&P 500 fund over the week (${esc(c.why)})${typeof c.rel === 'number' ? `: it was ${c.rel >= 0 ? 'ahead' : 'behind'} by ${Math.abs(c.rel).toFixed(1)}%, ${c.right ? 'right' : 'wrong'}` : ', not scored yet'}</li>`).join('')}</ul>`) : '';
        return `<div class="ap-section" id="ap-themes"><h4>Themes part <span class="ap-sub">a trial: ${Math.round(t.share * 100)}% of the budget (${usd0(t.target)})</span></h4>
            <div style="font-size: 0.85rem; margin-bottom: 6px;">A theme in the news (chips and AI, oil, inflation, gold) shows up first as a whole sector moving. So this part holds the ${t.count} strongest of 14 sector and theme funds by their rise over the past year (the last month left out), and changes them once a month. On five years of past prices it was ahead of an S&P 500 fund in both halves, mostly through the chip fund, so it is tested here for over a year before anything is concluded.</div>
            <div>Holds: ${held}.</div>
            ${t.next ? `<div style="margin-top: 4px;">Next monthly change ${until(t.next)} <span class="ap-sub">(${esc(when(t.next))})</span>.</div>` : ''}
            <div style="margin-top: 4px;">${done}</div>
            <div style="margin-top: 8px;"><strong style="color: var(--text-primary); font-size: 0.9rem;">The AI model's daily read of the news</strong> <span class="ap-sub">recorded and scored, not acted on</span><div style="margin-top: 2px;">Every trading day the AI model reads the market's headlines and says which funds it expects to do better or worse than an S&P 500 fund over the next week. A week later each call is scored. Only if its calls prove right far more often than chance (from 30 calls) would it be allowed to act. ${aiLine}</div>${callList}</div>
            ${table}
        </div>`;
    }
    function progressHtml() {
        const p = data.progress;
        if (!p || !Array.isArray(p.batches)) return '';
        const size = p.batch || 20, full = p.batches.filter(b => b.full), reports = {};
        (p.reports || []).forEach(r => { reports[r.no] = r; });
        const finished = p.batches.reduce((a, b) => Math.max(a, b.last || 0), 0);
        const how = `After every ${size} finished trades it compares them with the ${size} before. Better: it carries on as it is. No better: it looks into why, puts back a change of its own if the trades since did clearly worse, and tries the most promising change to one of its rules. All by itself; each report is also emailed.`;
        if (!full.length) return `<div class="ap-section"><h4>Progress, ${size} finished trades at a time</h4><div>Its first progress report comes after ${size} finished trades${p.shared ? ' at your risk level, counting every account' : ''} (${finished} so far). ${how}</div></div>`;
        const cell = 'padding: 4px 8px; text-align: right; white-space: nowrap; vertical-align: top;', left = 'padding: 4px 8px; vertical-align: top;';
        const word = { better: ['better', '#22c55e'], worse: ['worse', '#ef4444'], same: ['about the same', 'var(--text-secondary)'] };
        const row = (b) => {
            const r = reports[b.no], v = word[b.verdict];
            return `<tr><td class="ap-stack-title" style="${left} padding-left: 0; color: var(--text-primary); white-space: nowrap;"><span class="ap-only-phone">Trades </span>${b.first} to ${b.last}${b.full ? '' : ` <span style="color: var(--text-secondary);">(${b.n} of ${size} so far)</span>`}</td>
                <td data-label="When" style="${cell}">${esc(day(b.from))} to ${esc(day(b.to))}</td><td data-label="Made money" style="${cell}">${b.up} of ${b.n}</td><td data-label="Average a trade" style="${cell} color: ${tint(b.avg)}; font-weight: 600;">${(b.avg >= 0 ? '+' : '') + b.avg.toFixed(2)}%</td><td data-label="In dollars" style="${cell} color: ${tint(b.usd)};">${usd2(b.usd)}</td>
                <td class="ap-stack-wide" data-label="Against the ${size} before" style="${left}">${v ? `<span style="color: ${v[1]}; font-weight: 600;">${v[0]}</span> <span style="white-space: nowrap;">(${(b.prev >= 0 ? '+' : '') + b.prev.toFixed(2)}% before)</span>` : b.full ? 'the first batch' : 'still filling'}</td>
                ${r ? `<td class="ap-stack-wide" data-label="What it did" style="${left}">${esc((r.actions || []).join(' '))}</td>` : `<td style="${left}"></td>`}</tr>`;
        };
        const latest = (p.reports || []).slice(-1)[0];
        return `<div class="ap-section"><h4>Progress, ${size} finished trades at a time${p.shared ? ' <span style="font-size: 0.8rem; font-weight: 400; color: var(--text-secondary);">every account at your risk level together: this is what it learns from</span>' : ''}</h4>
            <div style="overflow-x: auto;"><table class="ap-stack" style="border-collapse: collapse; font-size: 0.85rem; width: 100%;">
                <tr class="ap-stack-head" style="color: var(--text-secondary);"><td style="${left} padding-left: 0;">Trades</td><td style="${cell}">When</td><td style="${cell}">Made money</td><td style="${cell}">Average a trade</td><td style="${cell}">In dollars</td><td style="${left}">Against the ${size} before</td><td style="${left}">What it did</td></tr>
                ${p.batches.slice().reverse().map(row).join('')}
            </table></div>
            ${latest && (latest.findings || []).length ? fold('progress-found', `What stood out in trades ${(latest.no - 1) * size + 1} to ${latest.no * size}`, latest.findings) : ''}
            <div style="font-size: 0.8rem; margin-top: 6px;">${how} "About the same" means the difference is inside what chance alone would give with ${size} trades. Past results of fake-money trades; they say nothing certain about the future.</div>
        </div>`;
    }

    // Its own trial of which share to buy: as its screener ranks them, or the one furthest above its 52-week low
    // The patient-shares trial (the function tags every second pair of shares; there is no verdict in its code: the two groups are compared at a review)
    function patientHtml() {
        const s = data.settings, shares = (s.screeners || []).some(k => (data.options.screeners[k] || {}).kind !== 'crypto');
        const live = (data.plans || []).some(p => typeof p.patient === 'boolean');       // an older function does not send it: say nothing then
        if (!live || s.selfTune === false || !shares) return '';
        const n = (data.plans || []).filter(p => p.patient).length;
        return `<div style="margin-top: 10px; padding: 10px 12px; border: 1px dashed var(--border-color); border-radius: 8px; font-size: 0.85rem; color: var(--text-secondary);"><strong style="color: var(--text-primary);">Also trying, for shares:</strong> every second pair of shares it buys is a &ldquo;patient&rdquo; share. A patient share is sold only by its loss limit, its gain mark, the stop that follows a rise, or at the end of its holding time: never because its screener signal turned or it slipped down the ranking, and the AI model does not review it. The other shares are sold as before, so the two groups can be compared. Why: on four years of past prices, selling on the signal cut rising shares short. It holds ${n} patient share${n === 1 ? '' : 's'} now. Nothing is decided by itself here: the two groups are compared when the results are reviewed.</div>`;
    }
    function orderHtml() {
        const o = data.order;
        // not started yet: it starts with the next share it buys (the function sends `progress` from the version that has this trial)
        if (!o) return 'progress' in data && data.settings.selfTune !== false && data.settings.screeners.some(k => (data.options.screeners[k] || {}).kind === 'stock')
            ? `<div style="margin-top: 6px;"><strong style="color: var(--text-primary);">Next, for shares:</strong> starting with the next share it buys, every second one will be the share furthest above its 52-week low on the shortlist, instead of the one its screener ranks highest. A test on four years of prices found that figure linked to what shares did next, and the screener's own ranking not. After 10 finished each way it keeps the new order only if those trades did clearly better.</div>` : '';
        const side = (n, avg) => `${n} finished${n ? ' (average ' + pc(avg) + ')' : ''}`, cap = (x) => x ? x.charAt(0).toUpperCase() + x.slice(1) + '.' : '';
        if (o.mode === 'trial') return `<div style="margin-top: 6px;"><strong style="color: var(--text-primary);">Also trying, for shares</strong> (since ${esc(day(o.since))}): every second share it buys is the one furthest above its 52-week low on the shortlist, instead of the one its screener ranks highest. Why: ${esc(o.why)}. So far: bought that way ${side(o.with, o.avgWith)}, bought as ranked ${side(o.without, o.avgWithout)}. It decides after ${o.group} each way and keeps the new order only if it did clearly better. <a href="#" data-ap="stoporder">Stop this trial</a></div>`;
        if (o.mode === 'low52') return `<div style="margin-top: 6px;"><strong style="color: var(--text-primary);">Changed by itself after a trial</strong> (${esc(day(o.ended))}): every share it buys is now the one furthest above its 52-week low on the shortlist. ${esc(cap(o.result))} ${mayChange() ? '<a href="#" data-ap="restoreorder">put it back</a>' : ''}</div>`;
        return o.ended ? `<div style="margin-top: 6px;">Tried for shares, ${esc(day(o.since))} to ${esc(day(o.ended))}: buying the one furthest above its 52-week low instead of the top-ranked one. Not kept: shares are bought as their screener ranks them. ${esc(cap(o.result))}</div>` : '';
    }
    // The bar its results have to clear before they mean anything, and how far along it is. Set in writing before the results
    // are in, so that nobody can talk a short lucky run into a success afterwards.
    function barHtml() {
        const b = data.bar;
        if (!b) return '';
        const sofar = b.n ? `So far: ${b.n} of ${b.need} finished trades${b.shared ? ', every account together' : ''}; after costs they average <span style="color: ${tint(b.avg)}; font-weight: 600;">${pc(b.avg)}</span> a trade against that yardstick${b.n >= 8 ? ` (the margin of error is ${b.margin.toFixed(1)} points)` : ''}.` : `So far: none of the ${b.need} finished trades.`;
        const verdict = b.met ? ' <strong style="color: #16a34a;">The bar is cleared for now</strong>: it still says nothing certain about the future.' : b.n >= b.need ? ' <strong>Enough trades, and the bar is not cleared</strong>: on this record it has not shown that it beats the yardstick.' : ' Until then a good or a bad week is noise.';
        return `<div class="ap-bar"><strong>The bar it has to clear:</strong> ${b.need} finished trades whose average result, after trading costs, is ahead of the yardstick by more than twice the margin of error. The yardstick: an S&amp;P 500 index fund over the same days for a share, zero for a coin. ${sofar}${verdict}</div>`;
    }
    // Learning is shared: what it changes about itself comes from every account's finished trades and applies to every account
    const mayChange = () => !data.central || !!data.central.canChange;
    function sharedHtml() {
        const c = data.central;
        if (!c) return '';
        const n = (k, one, many) => `${Number(k).toLocaleString('en-US')} ${k === 1 ? one : many}`;
        return `<div class="ap-sharedbox"><strong>🧠 It learns from every account, not only yours.</strong> Each finished trade of every account's autopilot goes into one shared record, with nothing that says whose it was: ${n(c.trades, 'finished trade', 'finished trades')} so far from ${n(c.accounts, 'account', 'accounts')}${c.trades ? ` (${n(c.level, 'is', 'are')} at your risk level)` : ''}. The rules it changes after a trial, the screeners it rests and its notes are worked out from that record and apply to every account, so a new account starts with what the others have already taught it, and every further account makes its trials finish sooner.${c.on ? '' : ' <strong>Yours takes no part at the moment</strong>: "Try changes to its own rules" is switched off under Settings, so it keeps the level\'s plain rules.'}</div>`;
    }
    // In one line: what it has tried on itself, what it kept, what it put back
    function improvedLine() {
        const past = (data.tune && data.tune.past) || [], o = data.order || {};
        const running = (data.tune && data.tune.trial ? 1 : 0) + (o.mode === 'trial' ? 1 : 0);
        const kept = past.filter(p => p.verdict === 'kept' && !p.undone).length + (o.mode === 'low52' ? 1 : 0);
        const back = past.filter(p => p.undone).length + (o.undone ? 1 : 0);
        const tried = past.length + (o.ended ? 1 : 0) + running;
        const n = (k, one, many) => `${k} ${k === 1 ? one : many}`;
        return `<div><strong style="color: var(--text-primary);">Improvements so far:</strong> ${n(running, 'change is', 'changes are')} being tried now, ${n(kept, 'has', 'have')} been kept after a trial, ${n(back, 'was', 'were')} put back, ${tried} tried in all. A change is kept only if the trades made with it did clearly better than those made without it over the same days.</div>`;
    }

    function tuneHtml() {
        const t = data.tune, r = data.rules;
        if (!t || !r) return '';
        const names = { stop: 'loss limit', take: 'gain mark', trail: 'share of a gain it gives back', top: 'how far down a ranking it buys', max_rsi: 'RSI limit' };
        const changed = Object.keys(r.changed || {});
        const trial = t.trial, group = t.group || 10;
        const side = (n, avg) => `${n} finished${n ? ' (average ' + pc(avg) + ')' : ''}`;
        const now = trial
            ? `<div style="margin-top: 6px;"><strong style="color: var(--text-primary);">Trying now</strong> (since ${esc(day(trial.since))}): ${esc(trial.text)}. Why: ${esc(trial.why)}. ${esc(trial.how)} So far: with the change ${side(trial.with, trial.avgWith)}, without it ${side(trial.without, trial.avgWithout)}. It decides after ${group} each way and keeps the change only if that group did clearly better. ${mayChange() ? '<a href="#" data-ap="stoptrial">Stop this trial</a>' : ''}</div>`
            : `<div style="margin-top: 6px;">${t.nextReviewIn === 0 ? 'It reviews its rules at the next sale.' : `Next review of its rules after ${t.nextReviewIn} more finished trade${t.nextReviewIn === 1 ? '' : 's'}`}${t.nextReviewIn === 0 ? '' : ` (it reviews them every ${t.batch}).`} If the record suggests a change worth trying, it tries it beside the current rule over the same days.</div>`;
        const verdicts = { kept: 'kept', dropped: 'not kept', stopped: 'stopped' };
        const past = (t.past || []).slice().reverse(), o = data.order || {};
        // 17 Oct 2026: a lighter view for every user (the owner: "one is for everyone the other is just for me so perhaps the one
        // for everyone a lighter version showing improvements only"): what is being tested now and what has been improved, with dates;
        // the explanations, the rules in force and the trials in full are folded under "The details".
        const site = Array.isArray(data.improvements) ? data.improvements : [];
        const testing = [];
        if (trial) testing.push({ text: `A change to one of its rules: ${trial.text}. So far with the change ${side(trial.with, trial.avgWith)}, without it ${side(trial.without, trial.avgWithout)}.`, since: trial.since });
        if (o.mode === 'trial') testing.push({ text: `Every second share bought is the one furthest above its 52-week low. So far that way ${side(o.with, o.avgWith)}, as ranked ${side(o.without, o.avgWithout)}.`, since: o.since });
        site.filter(e => e.status === 'running').forEach(e => testing.push({ text: e.publicText, since: e.started, until: e.decide }));
        const made = [];
        past.forEach(x => made.push({ ok: x.verdict === 'kept' && !x.undone, word: x.verdict === 'kept' && !x.undone ? 'Kept' : 'Not kept', when: x.ended, text: `${x.text}: ${x.undone ? 'kept, then put back' : verdicts[x.verdict] || x.verdict}.` }));
        if (o.ended) made.push({ ok: o.mode === 'low52', word: o.mode === 'low52' ? 'Kept' : 'Not kept', when: o.ended, text: o.mode === 'low52' ? 'Every share is now bought furthest above its 52-week low (kept after a trial).' : 'Buying the share furthest above its 52-week low, tried beside the usual order: shares are bought as their screener ranks them.' });
        site.filter(e => e.status === 'kept' || e.status === 'removed').forEach(e => made.push({ ok: e.status === 'kept', word: e.status === 'kept' ? 'Kept' : 'Taken out', when: e.decided, text: e.publicText }));
        made.sort((a, b) => String(b.when || '').localeCompare(String(a.when || '')));
        const next = site.filter(e => e.status === 'idea');
        const dated = (w) => w ? esc(day(w)) : '';
        const testRow = (x) => `<li class="ap-imp-row"><span class="ap-imp-mark test">●</span><div>${esc(x.text)} <span class="ap-imp-when">since ${dated(x.since)}${x.until ? ' · decided by ' + dated(x.until) : ''}</span></div></li>`;
        const madeRow = (x) => `<li class="ap-imp-row"><span class="ap-imp-word ${x.ok ? 'ok' : 'no'}">${x.word}</span><div>${esc(x.text)} <span class="ap-imp-when">${dated(x.when)}</span></div></li>`;
        const details = `${sharedHtml()}
            ${improvedLine()}
            <div style="margin-top: 6px;">Its rules now (${esc(r.name)} level): ${esc(ruleWords(r))}.${(r.yours || []).length ? ` Set by you: ${esc(r.yours.map(k => names[k]).join(' and '))}; its trials leave ${r.yours.length === 1 ? 'that' : 'those'} alone.` : ''}${changed.length ? ` Changed by itself after a trial: ${changed.map(k => esc(names[k] + ' (the level starts at ' + r.changed[k] + ')') + (mayChange() ? ` <a href="#" data-ap="restore" data-param="${esc(k)}">put it back</a>` : '')).join(', ')}.` : ''}</div>
            ${now}
            ${orderHtml()}
            ${patientHtml()}
            ${past.length ? fold('past-trials', `Earlier trials of its rules (${past.length})`, past.map(p => `${day(p.since)} to ${day(p.ended)}: ${p.text}: ${verdicts[p.verdict] || p.verdict}. ${p.result ? p.result.charAt(0).toUpperCase() + p.result.slice(1) + '.' : ''}`)) : ''}
            <div style="font-size: 0.8rem; margin-top: 6px;">By itself it can only change five of its own rules, inside fixed limits, and the order it buys shares in, for its own fake-money trades; a change is kept only if the trades made with it did clearly better. It never changes your settings, the budget or anything else on the site. Bigger changes (the screeners' score, what it may do) are tested on past prices first and then measured the same way.</div>`;
        return `<div class="ap-section"><h4>How it is improving</h4>
            <div class="ap-imp-sub">Every change is tested beside what it replaces and kept only if the figures show it helps. ${testing.length} being tested now · ${made.filter(x => x.ok).length} kept · ${made.filter(x => !x.ok).length} not kept or taken out</div>
            ${testing.length ? `<div class="ap-imp-head">Being tested now</div><ul class="ap-imp">${testing.map(testRow).join('')}</ul>` : ''}
            ${made.length ? `<div class="ap-imp-head">Improvements made</div><ul class="ap-imp">${made.slice(0, 5).map(madeRow).join('')}</ul>${made.length > 5 ? fold('imp-more', `${made.length - 5} earlier`, made.slice(5).map(x => `${x.word}: ${x.text} (${day(x.when)})`)) : ''}` : ''}
            ${next.length ? `<div class="ap-imp-head">Coming next</div><ul class="ap-imp">${next.map(x => `<li class="ap-imp-row"><span class="ap-imp-mark next">→</span><div>${esc(x.publicText)}</div></li>`).join('')}</ul>` : ''}
            <details class="ap-more ap-imp-details"><summary>The details: its rules now, how it learns from every account, the trials in full</summary><div style="margin-top: 8px;">${details}</div></details>
        </div>`;
    }

    // ---------------------------------------------------------------- for an account that is not on a paid plan
    // The autopilot is part of the paid plans. Everyone can see what it is; only the practice portfolio by hand is free.
    function lockedHtml() {
        if (data.locked !== 'plan') return `<div class="ap-wrap"><div class="ap-head"><h3>🤖 AI autopilot <span class="ap-beta" title="Beta: new, still being tested and changed">Beta</span></h3></div><div class="ap-status">Your plan could not be checked just now. Refresh the page in a moment.</div></div>`;
        return `<div class="ap-wrap">
            <div class="ap-head"><h3>🤖 AI autopilot <span class="ap-beta" title="Beta: new, still being tested and changed">Beta</span> <span class="ap-sub">fake money · part of the paid plans</span></h3></div>
            <p class="ap-intro">The AI autopilot runs a practice portfolio for you. At times you choose, it makes practice buys and sells with fake money from the latest results of the screeners you tick, inside a budget and limits you set, and shows what it did, why, and what it will do next. No real trade is ever placed and nothing here is advice; past screener results have not shown a reliable edge. It is in beta: new, and still being tested and changed.</p>
            <div id="ap-locked" class="ap-status"><strong>It is included in every paid plan (Starter, Pro and Elite).</strong> This account is not on a paid plan at the moment, so the autopilot is not available to it. Buying and selling by hand with the fake money stays free: that is the <a href="#practice">Practice portfolio</a> tab.</div>
            <div class="ap-actions"><a id="ap-upgrade" class="ap-btn primary" href="#upgrade" style="text-decoration: none; color: #fff;">See the plans</a></div>
            <div class="ap-section"><h4>What it does</h4>
                <ul style="margin: 4px 0 0 18px; padding: 0; line-height: 1.6;">
                    <li>Buys from the screeners you choose (shares in the US, Europe, Asia-Pacific and the Americas, and coins), spreading the budget over the markets as you set it.</li>
                    <li>Sells by rules you can see: a loss limit, a gain mark, a stop that follows a rising holding, and a longest holding time. An AI model chooses what to buy from the screeners' shortlist.</li>
                    <li>Shows a countdown to its next check-in, what it plans to do, and every buy and sale with the reason.</li>
                    <li>Keeps a record of its results, compares each 20 finished trades with the 20 before, and tests changes to its own rules, keeping one only if it did clearly better.</li>
                </ul>
                <div style="font-size: 0.8rem; margin-top: 8px;">A practice tool with fake money. General information only, not financial advice.</div>
            </div>
        </div>`;
    }

    // ---------------------------------------------------------------- the panel
    function render() {
        const el = box();
        if (!el) return;
        markTab();
        bellRefresh();
        if (!data || (!data.allowed && !data.locked)) { el.innerHTML = ''; return; }
        ensureStyle();
        if (!data.allowed) { el.innerHTML = lockedHtml(); return; }
        if (!part) part = rememberedPart() || (data.settings.enabled && data.settings.screeners.length ? 'activity' : 'settings');
        const breakdown = byId('ap-breakdown');
        if (breakdown && typeof breakdown.open === 'boolean') breakdownOpen = breakdown.open;
        if (document.querySelectorAll) Array.from(document.querySelectorAll('[data-ap-fold]')).forEach(x => { if (typeof x.open === 'boolean') openDetails[x.getAttribute('data-ap-fold')] = x.open; });
        const d = draft, o = data.options, on = data.settings.enabled, ready = on && data.settings.screeners.length > 0, state = savedState();
        const lvl = paceOf(d.risk);                        // what the level would set; null if the function does not send it
        const select = (id, key, list, value, label) => `<select id="${id}">${lvl ? `<option value="auto" ${isAuto(d, key) ? 'selected' : ''}>Automatic: ${label(lvl[key])}</option>` : ''}${list.map(v => `<option value="${v}" ${!isAuto(d, key) && v === value ? 'selected' : ''}>${label(v)}</option>`).join('')}</select>`;
        const tag = (key) => lvl ? `<span id="ap-tag-${key}" class="ap-auto ${isAuto(d, key) ? '' : 'own'}">${isAuto(d, key) ? 'automatic' : 'set by you'}</span>` : '';
        const icons = { buy: '🟢', sell: '🔴', note: 'ℹ️' };
        const all = (data.log || []).slice().reverse(), log = tradesOnly ? all.filter(e => e.type !== 'note') : all;
        const shown = showAll ? log : log.slice(0, 8);
        const holds = (data.plans || []).length;
        // with "Buys and sells only" on, the latest check-in's own line is still shown if it is newer than the last trade: it says why nothing happened
        const latest = tradesOnly && all.length && all[0].type === 'note' && all[0].key ? all[0] : null;
        const mayRow = (id, key, title, text) => `<label class="ap-may"><input id="${id}" type="checkbox" ${d[key] !== false ? 'checked' : ''}> <strong>${title}</strong><small>${text}</small></label>`;
        const levels = Object.keys(o.risk).sort();
        const chosen = d.screeners.length;
        el.innerHTML = `
            <div class="ap-wrap">
                <div class="ap-head">
                    <h3>🤖 AI autopilot <span class="ap-beta" title="Beta: new, still being tested and changed">Beta</span> <span class="ap-sub">fake money, an experiment to watch</span></h3>
                    <label class="ap-switch" title="Switch the autopilot on or off. This is saved straight away."><span id="ap-switch-text">${d.enabled ? 'On' : 'Off'}</span><input id="ap-enabled" type="checkbox" ${d.enabled ? 'checked' : ''} ${working ? 'disabled' : ''}><span class="ap-track"></span></label>
                </div>
                <p class="ap-intro">An AI model makes practice buys and sells for you from the latest results of the screeners you choose, inside the limits you set here. It uses the fake money of your <a href="#practice">practice portfolio</a>, where its holdings are listed with your own. Nothing here is advice, and past screener results have not shown a reliable edge. It is in beta: new, and still being tested and changed.</p>
                <div id="ap-status" class="ap-status ${on ? 'on' : ''}">${esc(statusText())}${countLine()}</div>
                ${needsHtml()}

                <div class="ap-actions">
                    <button id="ap-run" data-ap="run" class="ap-btn ${ready ? 'primary' : ''}${working === 'run' ? ' busy' : ''}" ${working || !ready || state.text === 'Saving…' ? 'disabled' : ''} title="${!on ? 'Switch the autopilot on first' : !ready ? 'Tick at least one screener first' : 'Runs one check-in now instead of waiting for the next one. If the budget is still being built up, pressing this releases the next part of it early. Only markets that are open are traded; coins at any time'}">${working === 'run' ? 'Checking in… this can take up to a minute' : 'Check in now'}</button>
                    <button id="ap-sellall" data-ap="sellall" class="ap-btn${working === 'sellall' ? ' busy' : ''}" ${working || !holds ? 'disabled' : ''} title="${holds ? 'Sells every holding the autopilot bought, now, at the latest prices. Holdings you bought yourself are not touched' : 'It holds nothing right now'}">${working === 'sellall' ? 'Selling…' : 'Sell everything it holds' + (holds ? ' (' + holds + ')' : '')}</button>
                    <span id="ap-saved" class="ap-saved ${state.bad ? 'bad' : ''}">${esc(state.text)}</span>
                </div>
                <div id="ap-notice" class="${notice ? 'ap-note ' + (notice.bad ? 'bad' : 'good') : ''}" role="status">${notice ? esc(notice.text) + (notice.undo && presetUndo ? ' <a href="#" data-ap="undopreset" style="font-weight: 700; white-space: nowrap;">Undo</a>' : '') : ''}</div>

                <div class="ap-views" role="tablist" aria-label="Autopilot">
                    <button type="button" id="ap-view-activity" class="ap-view ${part === 'activity' ? 'now' : ''}" data-ap-part="activity" role="tab">📋 Activity</button>
                    <button type="button" id="ap-view-settings" class="ap-view ${part === 'settings' ? 'now' : ''}" data-ap-part="settings" role="tab">⚙️ Settings</button>
                </div>

                <div id="ap-pane-activity" class="ap-pane" style="${part === 'activity' ? '' : 'display: none;'}">
                ${gaugeHtml()}
                ${comingHtml()}
                ${recordHtml()}
                ${themesHtml()}
                ${progressHtml()}
                ${tuneHtml()}
                <div class="ap-section" id="ap-done"><h4>What it has done <span class="ap-fresh"><span id="ap-fresh">${loadedAt ? 'Up to date at ' + esc(clock(loadedAt)) + '. Refreshes by itself every minute.' : ''}</span><a href="#" data-ap="refresh">↻ Refresh now</a><label class="ap-mini" title="On: only its buys and sells are listed. Off: its check-ins and notes too. Remembered in this browser."><input id="ap-tradesonly" type="checkbox" ${tradesOnly ? 'checked' : ''}><span class="ap-dot"></span>Buys and sells only</label></span></h4>
                    ${latest ? `<div class="ap-log"><time>${icons.note} ${esc(when(latest.t))}</time> Latest check-in: ${esc(latest.text.replace(/^Checked in\. /, ''))}${latest.n > 1 ? ` <span style="font-size: 0.8rem;">(the same at ${latest.n} check-ins in a row)</span>` : ''}</div>` : ''}
                    ${log.length ? shown.map(e => `<div class="ap-log"><time>${icons[e.type] || ''} ${esc(when(e.t))}</time> ${e.type === 'buy' ? `<strong style="color: var(--text-primary);">Bought ${esc(e.symbol)}</strong> with ${usd0(e.usd)}. ` : e.type === 'sell' ? `<strong style="color: var(--text-primary);">Sold ${esc(e.symbol)}</strong>${gainOf(e) !== null ? ' ' + deltaHtml(gainOf(e), e.pct) : typeof e.pct === 'number' ? ` <span style="color: ${tint(e.pct)}; font-weight: 600;">${pc(e.pct)}</span>` : ''}. ` : ''}${esc(e.text)}${e.n > 1 ? ` <span style="font-size: 0.8rem;">(the same at ${e.n} check-ins in a row, since ${esc(when(e.first))})</span>` : ''}${fold(e.type + e.t + e.symbol, e.type === 'sell' ? 'Why, and the details' : 'The plan for it', e.detail)}</div>`).join('') : `<div>${tradesOnly && all.length ? 'No buys or sells yet.' : 'Nothing yet. Its buys, sells and check-ins will be listed here.'}</div>`}
                    ${log.length > shown.length ? `<a href="#" data-ap="more" style="display: inline-block; margin-top: 8px;">Show all ${log.length}</a>` : ''}</div>
                </div>

                <div id="ap-pane-settings" class="ap-pane" style="${part === 'settings' ? '' : 'display: none;'}">
                <div class="ap-help" style="margin-top: 12px;">Every change here saves itself. A change by itself buys or sells nothing: the autopilot acts only at a check-in, and a scheduled check-in waits until the settings have been left alone for 10 minutes.</div>

                <div class="ap-card">
                    <span class="ap-label">Risk level</span>
                    <input id="ap-risk" class="ap-risk" type="range" min="1" max="${levels.length || 5}" step="1" value="${d.risk}" aria-label="Risk level">
                    <div class="ap-levels">${levels.map(n => `<span data-ap-level="${n}" class="${String(d.risk) === n ? 'now' : ''}">${esc(o.risk[n].name)}</span>`).join('')}</div>
                    <div id="ap-risk-text" class="ap-help">${esc(riskText(d.risk))}</div>
                    <div class="ap-own"><strong>Your own limits</strong>
                        <label>Sell at a loss of <input id="ap-stop" type="number" min="1.5" max="30" step="0.5" inputmode="decimal" placeholder="${hint(d.risk, 'stop')}" value="${d.stopPct || ''}" aria-label="Your own loss limit in percent">%</label>
                        <label>Sell at a gain of <input id="ap-take" type="number" min="2" max="80" step="0.5" inputmode="decimal" placeholder="${hint(d.risk, 'take')}" value="${d.takePct || ''}" aria-label="Your own gain mark in percent">%</label>
                        <span>Optional. Leave a field empty to use the level's (shown in grey). What you set here, its own trials leave alone.</span>
                        ${'trailMode' in data.settings ? `<label style="flex-basis: 100%;">Trailing stop <select id="ap-trail" style="padding: 6px 8px; margin: 0 4px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px; max-width: 100%;">${Object.keys(TRAILS).map(k => `<option value="${k}" ${trailOf(d) === k ? 'selected' : ''}>${TRAILS[k].name}</option>`).join('')}</select></label>
                        <span id="ap-trail-text" style="flex-basis: 100%;">${esc(TRAILS[trailOf(d)].help)}</span>` : ''}
                    </div>
                </div>

                <div class="ap-card">
                    <div class="ap-fields">
                        <div><label class="ap-label" for="ap-budget">Budget for the AI</label><div class="ap-input">$ <input id="ap-budget" type="number" min="100" ${data.money ? `max="${data.money.reach}"` : ''} step="500" value="${d.budgetUsd}"></div></div>
                        ${'holdings' in data.settings ? `<div><label class="ap-label" for="ap-holdings">Number of holdings<span id="ap-tag-holdings" class="ap-auto ${d.holdings > 0 ? 'own' : ''}">${d.holdings > 0 ? 'set by you' : 'automatic'}</span></label><div class="ap-input"><input id="ap-holdings" type="number" min="${(o.holdings || {}).min || 2}" max="${(o.holdings || {}).max || 50}" step="1" placeholder="${autoWord((o.risk[String(d.risk)] || {}).positions)}" value="${d.holdings > 0 ? d.holdings : ''}" title="How many equal holdings the budget is spread over. Empty: the risk level's own number"> holdings</div></div>` : ''}
                        <div><label class="ap-label" for="ap-period">Build up to it over${tag('periodDays')}</label><div class="ap-input"><input id="ap-period" type="number" min="1" max="90" step="1" ${lvl ? `placeholder="${autoWord(lvl.periodDays)}"` : ''} value="${isAuto(d, 'periodDays') ? '' : d.periodDays}"> days</div></div>
                        <div><label class="ap-label" for="ap-every">Checks in${tag('everyHours')}</label><div class="ap-input">${select('ap-every', 'everyHours', o.everyHours, d.everyHours, everyText)}</div></div>
                        <div><label class="ap-label" for="ap-hold">Keeps a holding at most${tag('maxHoldDays')}</label><div class="ap-input">${select('ap-hold', 'maxHoldDays', o.holdDays, d.maxHoldDays, holdText)}</div></div>
                    </div>
                    <div id="ap-budget-hint" class="ap-help">${budgetHint(d)}</div>
                    ${'holdings' in data.settings ? `<div id="ap-holdings-hint" class="ap-help">${holdingsHint(d)}</div>` : ''}
                    ${lvl ? `<div class="ap-help">The last three follow the risk level while they are left on automatic (an empty box, or "Automatic" in a menu): move the slider and they move with it. Set one yourself and it stays where you put it.${(d.auto || []).length < 3 ? ' <a href="#" data-ap="autopace">Let the risk level set all three</a>' : ''}</div>` : ''}
                    <div id="ap-plan" class="ap-help">${esc(planText(d))}</div>
                    <div id="ap-pace" class="ap-help">${esc(paceText(d))}</div>
                </div>

                <div class="ap-card">
                    <span class="ap-label">Screeners it buys from <span id="ap-chosen" class="ap-sub">${chosen} chosen</span></span>
                    ${sharesOn() ? `<div class="ap-help" style="margin-top: 2px;">Tick the screeners it may buy from. Each market you tick gets a share of ${esc(ofWhat(d))}, shown in the bar and set in the box on its right.${themesShare(d) ? ` That is the budget less the ${Math.round(themesShare(d) * 100)}% of the themes part, so the shares below add up to 100% of it.` : ''}</div><div id="ap-splitbar" class="ap-splitbar" aria-label="How the budget is spread over the markets">${splitBar(d)}</div>` : ''}
                    <div class="ap-presets" style="margin-top: 8px;"><span>Shortcuts:</span><button type="button" class="ap-preset" data-ap-pick="main" title="One index a country: ${esc(MAIN.filter(k => o.screeners[k]).map(k => o.screeners[k].name).join(', '))}">🌍 Main index of every country</button><button type="button" class="ap-preset" data-ap-pick="none" title="Untick every screener">Clear all</button><span>or click a market's name to tick or clear all of its screeners. These change only what is ticked, never the pace or the budget. The Euro Stoxx 50 is not one country's index, so the first shortcut leaves it out: 47 of its 50 shares are already in the DAX, CAC, AEX, FTSE MIB and IBEX lists (tick it yourself to add the other three: AB InBev, argenx and Nordea).</span></div>
                    ${screenerGroups(o.screeners).map(([group, keys], i) => `<div class="ap-group ${i === 0 ? 'first' : ''} ${sharesOn() ? 'shared' + (isTicked(d, group) ? '' : ' off') : ''}"><div class="ap-group-name">${sharesOn() ? `<span class="ap-dot" style="background: ${isTicked(d, group) ? marketColour(group) : 'var(--border-color)'};"></span>` : ''}<button type="button" class="ap-group-pick" data-ap-group="${esc(group)}" title="Tick every screener in ${esc(group)}, or clear them when all are ticked">${esc(group)}</button></div><div><div class="ap-chips">${keys.map(k => `<label class="ap-chip"><input type="checkbox" data-ap-screener="${esc(k)}" ${d.screeners.includes(k) ? 'checked' : ''}> ${esc(o.screeners[k].name)}${data.resting && data.resting[k] ? ' <small title="Resting after its recent trades lagged the market">(resting until ' + esc(day(data.resting[k])) + ')</small>' : ''}</label>`).join('')}</div></div><div id="ap-sharebox-${i}">${shareRow(d, group, i)}</div></div>`).join('')}
                    <div id="ap-split" class="ap-help">${esc(splitText(d))}</div>
                    ${data.themes && data.themes.on ? `<div class="ap-help ap-themes-note" style="margin-top: 6px; padding: 6px 8px; border-left: 3px solid var(--border-color);">The percentages above are of the ${usd0(sharePart(d).budgetUsd)} for shares. The other ${Math.round(data.themes.share * 100)}% of the ${usd0(d.budgetUsd)} budget (${usd0(data.themes.target)}) is the <strong>themes part</strong>, a trial: the 3 strongest of 14 sector and theme funds, changed once a month. It is not a screener to tick; what it holds and how it is doing are under Activity. <a href="#ap-themes" data-ap-part="activity" data-ap-goto="ap-themes">See the themes part</a></div>` : ''}
                    <div class="ap-help">Each share market is only traded while it is open, also when you press "Check in now"; coins at any time. Bigger lists take a little longer to check. Lists can overlap (the S&amp;P 1500 holds every share of the S&amp;P 500, 400 and 600): that does no harm, a share is never held twice, and it is bought on its best place among the lists ticked.</div>
                </div>

                <div class="ap-card">
                    <span class="ap-label">What it may do by itself</span>
                    ${''/* "Sell early on the AI model's review" was taken out on 17 Oct 2026: its early sales lost money (31 trades, -1.46% a trade, against -0.62% for every other kind of sale). It is off for every account; check-tools/experiments.json "ai-review-off". */}
                    <div class="ap-help" style="margin: -2px 0 10px;">The AI model no longer sells early: those sales lost money (31 trades, -1.46% a trade, against -0.62% for every other kind of sale), so they were taken out on 17 Oct 2026. The fixed rules sell: the loss limit, the gain mark, the stop that follows a rise, the time limit.</div>
                    ${mayRow('ap-tune', 'selfTune', 'Try changes to its own rules', 'Every 20 finished trades it may try one change to a selling or buying rule beside the current one, and keeps it only if it did clearly better. It also runs two standing trials for shares: which share to buy, and "patient" shares that are not sold when their signal turns. Off: its rules stay exactly as they are and no trial runs.')}
                    ${mayRow('ap-mail', 'emails', 'Email me its reviews', 'An email to your account address each time it reviews its rules, starts a trial or finishes one. Nothing needs doing when one arrives.')}
                    ${mailHtml()}
                </div>
                </div>
            </div>`;
    }

    // Under "Sell early on the AI model's review": what its early sales have done so far, from the record, beside the other sales,
    // so that the switch's state is explained by the figures (17 Oct 2026: it was switched off at the owner's yes when they were
    // clearly losing, and he did not remember why it was off).
    function aiSellRecord(d) {
        const exits = ((data.scorecard || {}).groups || {}).exit || [];
        const ai = exits.find(g => /AI model/.test(g.label || ''));
        const rest = exits.filter(g => !/AI model/.test(g.label || ''));
        const n = rest.reduce((a, g) => a + g.n, 0), avg = n ? rest.reduce((a, g) => a + g.avg * g.n, 0) / n : null;
        const pct = (v) => `${v >= 0 ? '+' : ''}${Number(v).toFixed(2)}%`;
        const line = ai ? `Its early sales so far: ${ai.n} trade${ai.n === 1 ? '' : 's'}, ${pct(ai.avg)} a trade on average` + (avg !== null ? `; every other kind of sale together: ${n} trades, ${pct(avg)}.` : '.') : 'It has not sold anything early yet.';
        const state = d.aiSell === false ? ' It is off: the fixed rules still sell (the loss limit, the gain mark, the stop that follows a rise, the time limit).' : '';
        return `<div class="ap-help" style="margin: -4px 0 10px 28px;">${esc(line + state)}${ai && ai.n >= 30 && d.aiSell !== false && ai.avg < (avg || 0) ? ' <strong>It does worse than the other sales.</strong>' : ''}</div>`;
    }

    // one of the "what it may do by itself" switches: what is ticked on screen, or what is saved if it is not on screen
    function may(id, key) { const el = byId(id); return el && typeof el.checked === 'boolean' ? !!el.checked : (data.settings[key] !== false); }
    // the user's own loss limit or gain mark: the number typed, or null when the field is empty (the level's then applies)
    function ownLimit(id, key) { const el = byId(id); if (!el || typeof el.value !== 'string') return data.settings[key] || null; const n = Math.abs(parseFloat(el.value)); return n > 0 ? n : null; }
    function readDraft() {
        if (!byId('ap-risk')) return;
        const risk = parseInt(byId('ap-risk').value, 10) || 3, level = paceOf(risk), left = [];
        // a pace field left empty or on "Automatic" takes the level's own value, and is listed as left to the level
        const pace = (id, key, parse, fallback) => {
            const raw = String(byId(id).value);
            if (level && (raw === '' || raw === 'auto')) { left.push(key); return level[key]; }
            const n = parse(raw); return isFinite(n) ? n : fallback;
        };
        draft = {
            enabled: !!byId('ap-enabled').checked, risk,
            budgetUsd: parseFloat(byId('ap-budget').value) || 0, periodDays: pace('ap-period', 'periodDays', v => parseInt(v, 10), 1) || 1,
            everyHours: pace('ap-every', 'everyHours', parseFloat, NaN), maxHoldDays: pace('ap-hold', 'maxHoldDays', parseFloat, NaN),
            screeners: Array.from(document.querySelectorAll('[data-ap-screener]')).filter(c => c.checked).map(c => c.getAttribute('data-ap-screener')).sort(),
            aiSell: false, selfTune: may('ap-tune', 'selfTune'), emails: may('ap-mail', 'emails'),
            stopPct: ownLimit('ap-stop', 'stopPct'), takePct: ownLimit('ap-take', 'takePct')
        };
        if ('holdings' in data.settings) {                 // the user's own number of holdings; an empty box leaves it to the level
            const box = byId('ap-holdings'), n = box ? parseInt(box.value, 10) : NaN, bound = data.options.holdings || { min: 2, max: 50 };
            draft.holdings = !box ? (data.settings.holdings || null) : isFinite(n) && n > 0 ? Math.min(bound.max, Math.max(bound.min, n)) : null;
        }
        if ('auto' in data.settings) draft.auto = PACE_FIELDS.filter(k => left.includes(k));
        if ('shares' in data.settings) {                   // a market's share: what its menu says, or automatic when it has no menu on the page
            const sh = {}, known = data.options.groups || [];
            Array.from(document.querySelectorAll('[data-ap-share]')).forEach(el => {
                const g = el.getAttribute('data-ap-share'), v = typeof el.value === 'string' ? parseFloat(el.value) : NaN;
                if (known.includes(g) && isFinite(v) && draft.screeners.some(k => (data.options.screeners[k] || {}).group === g)) sh[g] = v;
            });
            draft.shares = sh;
        }
        if ('trailMode' in data.settings) { const pick = byId('ap-trail'); draft.trailMode = pick && TRAILS[pick.value] ? pick.value : trailOf(data.settings); }
    }
    // Bring the button, the "saved" line and the explanatory lines up to date without redrawing (typing keeps its place)
    function syncDraft() {
        readDraft();
        if (!draft || !data) return;
        const on = data.settings.enabled, ready = on && data.settings.screeners.length > 0, state = savedState(), set = (id, fn) => { const el = byId(id); if (el) fn(el); };
        set('ap-run', el => { el.disabled = !!working || !ready || state.text === 'Saving…'; el.title = !on ? 'Switch the autopilot on first' : !ready ? 'Tick at least one screener first' : 'Runs one check-in now instead of waiting for the next one. If the budget is still being built up, pressing this releases the next part of it early. Only markets that are open are traded; coins at any time'; if (el.classList) el.classList.toggle('primary', ready); });
        set('ap-saved', el => { el.textContent = state.text; if (el.classList) el.classList.toggle('bad', state.bad); });
        set('ap-status', el => { el.textContent = statusText(); if (el.classList) el.classList.toggle('on', on); });
        set('ap-switch-text', el => { el.textContent = draft.enabled ? 'On' : 'Off'; });
        set('ap-risk-text', el => { el.textContent = riskText(draft.risk); });
        set('ap-trail-text', el => { el.textContent = TRAILS[trailOf(draft)].help; });
        set('ap-holdings', el => { el.placeholder = autoWord((data.options.risk[String(draft.risk)] || {}).positions); });
        set('ap-holdings-hint', el => { el.textContent = holdingsHint(draft); });
        set('ap-tag-holdings', el => { el.textContent = draft.holdings > 0 ? 'set by you' : 'automatic'; if (el.classList) el.classList.toggle('own', draft.holdings > 0); });
        const lvl = paceOf(draft.risk);
        if (lvl) {
            set('ap-period', el => { el.placeholder = autoWord(lvl.periodDays); });
            [['ap-every', 'everyHours', everyText], ['ap-hold', 'maxHoldDays', holdText]].forEach(([id, key, label]) => set(id, el => { const first = el.options && el.options[0]; if (first && first.value === 'auto') first.textContent = 'Automatic: ' + label(lvl[key]); }));
            PACE_FIELDS.forEach(key => set('ap-tag-' + key, el => { el.textContent = isAuto(draft, key) ? 'automatic' : 'set by you'; if (el.classList) el.classList.toggle('own', !isAuto(draft, key)); }));
        }
        set('ap-stop', el => { el.placeholder = hint(draft.risk, 'stop'); });
        set('ap-take', el => { el.placeholder = hint(draft.risk, 'take'); });
        set('ap-budget-hint', el => { el.innerHTML = budgetHint(draft); });
        set('ap-plan', el => { el.textContent = planText(draft); });
        set('ap-pace', el => { el.textContent = paceText(draft); });
        set('ap-chosen', el => { el.textContent = draft.screeners.length + ' chosen'; });
        set('ap-split', el => { el.textContent = splitText(draft); });
        // the share menus show dollars and holdings, which follow the budget and the level: rebuild them in place (none of them has the cursor)
        if (sharesOn()) { screenerGroups(data.options.screeners).forEach(([group], i) => set('ap-sharebox-' + i, el => { el.innerHTML = shareRow(draft, group, i); })); set('ap-splitbar', el => { el.innerHTML = splitBar(draft); }); }
        if (document.querySelectorAll) Array.from(document.querySelectorAll('[data-ap-level]')).forEach(el => { if (el.classList) el.classList.toggle('now', el.getAttribute('data-ap-level') === String(draft.risk)); });
    }
    function validate(d) {
        const cash = data.practiceCash || 100000;
        if (!(d.budgetUsd >= 100)) throw new Error('the budget must be at least $100.');
        if (d.budgetUsd > cash * 10) throw new Error(`the budget cannot be more than ${usd0(cash * 10)}.`);
        // only when the budget is being changed: other settings must still save while an older, too-large budget is being put right
        if (data.money && d.budgetUsd > data.money.reach && d.budgetUsd !== data.settings.budgetUsd) throw new Error(`the budget can be at most ${usd0(data.money.reach)}: that is all the practice money there is.`);
        if (!(d.periodDays >= 1 && d.periodDays <= 90)) throw new Error('spread the buying over 1 to 90 days.');
        if (sharesOn() && d.shares) {
            const total = Object.keys(d.shares).reduce((a, g) => a + d.shares[g], 0);
            if (total > 100.01) throw new Error(`the shares you picked add up to ${Math.round(total)}% of the budget: together they can be 100% at most. Lower one, or put one back to "Automatic".`);
        }
        if (d.stopPct !== null && d.stopPct !== undefined && !(d.stopPct >= 1.5 && d.stopPct <= 30)) throw new Error('your own loss limit must be between 1.5% and 30% (or empty).');
        if (d.takePct !== null && d.takePct !== undefined && !(d.takePct >= 2 && d.takePct <= 80)) throw new Error('your own gain mark must be between 2% and 80% (or empty).');
    }
    // Is the user in the middle of typing or dragging in the panel? Then the panel is updated in place, not redrawn.
    function editing() {
        const el = document.activeElement;
        return !!el && typeof el.id === 'string' && ['ap-budget', 'ap-period', 'ap-holdings', 'ap-risk', 'ap-stop', 'ap-take'].includes(el.id);
    }
    function queueSave(delay) {
        if (saveTimer) clearTimeout(saveTimer);
        saveTimer = setTimeout(() => { saveTimer = null; flush(); }, delay);
        syncDraft();
    }
    // Save what is on screen now. Each change is saved by itself; if more changes arrive meanwhile they are saved next.
    async function flush(leaving) {
        if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
        if (!data || !data.allowed) return;
        readDraft();
        if (!isDirty()) { syncDraft(); return; }
        if (saving) return;                               // the save in flight will pick the rest up when it lands
        try { validate(draft); } catch (e) { saveError = e.message; syncDraft(); return; }
        saving = true; saveError = null; syncDraft();
        const sent = JSON.stringify(draft), wasOn = data.settings.enabled;
        try {
            const result = await api('save', { settings: draft }, leaving);
            const unchangedSince = JSON.stringify(draft) === sent;
            data = result; loadedAt = new Date(); sharePlans();
            if (unchangedSince) draft = JSON.parse(JSON.stringify(result.settings));
            savedOnce = true; accepted = sent;
            const on = data.settings.enabled;
            if (on !== wasOn) notice = { text: on ? (data.settings.screeners.length ? 'Autopilot switched on. Press "Check in now" to see its first choices, or leave it to check in by itself.' : 'Autopilot switched on. Tick at least one screener below for it to start.')
                : 'Autopilot switched off. What it holds stays in the practice portfolio until you sell it.' };
        } catch (e) { saveError = e.message; }
        saving = false;
        if (!saveError && isDirty()) { queueSave(300); return; }
        if (editing()) syncDraft(); else render();
    }
    function take(result) { data = result; draft = JSON.parse(JSON.stringify(result.settings)); accepted = null; loadedAt = new Date(); const at = Date.parse(result.now); if (isFinite(at)) skew = at - Date.now(); sharePlans(); }
    // practice-portfolio.js marks the autopilot's holdings with when and at what they will be sold
    function sharePlans() { if (data && data.allowed && window.practicePortfolio && window.practicePortfolio.setPlans) window.practicePortfolio.setPlans(data.plans || [], { realizedUsd: data.realizedUsd }); }
    // What changes when the autopilot acts: its activity list and what it holds
    const stamp = (r) => JSON.stringify([r.order, r.progress, r.log && r.log.length, r.log && r.log.slice(-1), r.plans, r.state, r.tune, r.scorecard && r.scorecard.n, r.coming, r.needs, r.mail, r.nextCheck, r.improvements, r.themes, r.gauge && r.gauge.level]);      // improvements: a new one shows at the next refresh (17 Oct 2026)
    // Ask again without disturbing anything: not while a change is being typed, saved or run
    async function refresh(byHand) {
        if (!data || !data.allowed || refreshing || working || saving || saveTimer || isDirty() || (editing() && !byHand)) return;
        if (!byHand && document.visibilityState === 'hidden') return;
        refreshing = true;
        try {
            const r = await api('get');
            if (r.allowed && !working && !saving && !saveTimer && !isDirty()) {
                const traded = JSON.stringify([r.plans, r.scorecard && r.scorecard.n]) !== JSON.stringify([data.plans, data.scorecard && data.scorecard.n]);
                const changed = stamp(r) !== stamp(data) || JSON.stringify(r.settings) !== JSON.stringify(data.settings);
                take(r);
                if (changed || byHand) { if (editing()) syncDraft(); else render(); } else { const f = byId('ap-fresh'); if (f) f.textContent = 'Up to date at ' + clock(loadedAt) + '. Refreshes by itself every minute.'; }
                if (traded && window.practicePortfolio && window.practicePortfolio.reload) window.practicePortfolio.reload();
            }
        } catch (e) { if (byHand) { notice = { text: 'Could not refresh: ' + e.message, bad: true }; render(); } }
        refreshing = false;
    }

    async function load() {
        if (!userId() || !box()) return;
        try { const r = await api('get'); if (r.allowed) take(r); else data = r; } catch (e) { data = null; }
        render();
    }
    async function act(kind, task) {
        if (working) return;
        await flush();                                    // anything just changed is saved first
        if (saveError || isDirty()) { render(); return; }
        working = kind; notice = null; presetUndo = null; render();
        try { await task(); } catch (e) { notice = { text: e.message, bad: true }; }
        working = ''; render();
    }

    document.addEventListener('click', (e) => {
        const level = e.target.closest && e.target.closest('[data-ap-level]');
        if (level && data && byId('ap-risk')) { byId('ap-risk').value = level.getAttribute('data-ap-level'); saveError = null; queueSave(150); return; }
        const view = e.target.closest && e.target.closest('[data-ap-part]');
        if (view && data) {
            // a link that names a place on the panel (not one of the two part buttons): stay on the page and go down to that place.
            // Left to itself a "#" link sent the page back to the top, so "What happens then" seemed to do nothing
            const goto = view.getAttribute('data-ap-goto');
            if (view.tagName === 'A' && e.preventDefault) e.preventDefault();
            showPart(view.getAttribute('data-ap-part'), true);
            const place = goto && byId(goto);
            if (place && place.scrollIntoView) place.scrollIntoView({ block: 'start' });
            return;
        }
        const pick = e.target.closest && (e.target.closest('[data-ap-pick]') || e.target.closest('[data-ap-group]'));
        if (pick && data && data.options) {                 // a shortcut, or a market's name: they change only what is ticked
            const boxes = Array.from(document.querySelectorAll('[data-ap-screener]')), key = c => c.getAttribute('data-ap-screener'), names = data.options.screeners || {};
            const which = pick.getAttribute('data-ap-pick'), group = pick.getAttribute('data-ap-group');
            if (!presetUndo) presetUndo = { screeners: boxes.filter(c => c.checked).map(key) };
            let said = '';
            if (group) {
                const own = boxes.filter(c => names[key(c)] && names[key(c)].group === group), all = own.length > 0 && own.every(c => c.checked);
                own.forEach(c => { c.checked = !all; });
                said = all ? `${group}: cleared.` : `${group}: all ${own.length} ticked.`;
            } else if (which === 'main') {
                boxes.forEach(c => { if (names[key(c)] && names[key(c)].kind !== 'crypto') c.checked = MAIN.includes(key(c)); });
                said = `Ticked the main index of every country (${boxes.filter(c => c.checked && names[key(c)] && names[key(c)].kind !== 'crypto').length} share screeners; the coin screener is as it was).`;
            } else {
                boxes.forEach(c => { c.checked = false; });
                said = 'Every screener is unticked: it buys nothing until one is ticked. What it holds stays until it is sold.';
            }
            saveError = null; notice = { text: said, undo: true };
            queueSave(150); return;
        }
        const t = e.target.closest && e.target.closest('[data-ap]');
        if (!t || !data) return;
        if (t.tagName === 'A') e.preventDefault();
        const action = t.getAttribute('data-ap');
        if (action === 'undopreset' && presetUndo) {        // put back what was ticked before the shortcut
            const u = presetUndo; presetUndo = null;
            Array.from(document.querySelectorAll('[data-ap-screener]')).forEach(c => { c.checked = u.screeners.includes(c.getAttribute('data-ap-screener')); });
            saveError = null; notice = { text: 'Put back: the screeners ticked are as they were.' };
            queueSave(150); return;
        }
        if (action === 'more') { readDraft(); showAll = true; render(); }
        else if (action === 'refresh') {                    // show that the press was taken, and say when it is done
            t.classList.add('busy'); t.textContent = 'Refreshing…';
            Promise.resolve(refresh(true)).catch(() => {}).then(() => {
                const link = document.querySelector('#practice-autopilot [data-ap="refresh"]'), fresh = byId('ap-fresh');
                if (link) { link.classList.remove('busy'); link.textContent = '↻ Refresh now'; }
                if (fresh) { fresh.classList.remove('ap-flash'); void fresh.offsetWidth; fresh.classList.add('ap-flash'); }
            });
        }
        else if (action === 'maxbudget') {                  // the budget was more than the practice money: put it to the most there is
            if (byId('ap-budget') && data.money) byId('ap-budget').value = String(data.money.reach);
            saveError = null; notice = { text: `Budget set to ${usd0(data.money.reach)}: all the practice money there is for it.` };
            queueSave(150);
        }
        else if (action === 'autopace') {                   // hand all three pace settings back to the risk level
            if (byId('ap-period')) byId('ap-period').value = '';
            ['ap-every', 'ap-hold'].forEach(id => { if (byId(id)) byId(id).value = 'auto'; });
            saveError = null; notice = { text: 'The risk level now sets how fast it builds up, how often it checks in and how long it keeps a holding.' };
            queueSave(150);
        }
        else if (action === 'sellall') {
            const n = (data.plans || []).length;
            if (!n || !confirm(`Sell the ${n} holding${n === 1 ? '' : 's'} the autopilot bought, now, at the latest prices?\n\nHoldings you bought yourself are not touched. If the autopilot stays switched on it will buy again at its next check-in.`)) return;
            act('sellall', async () => {
                const r = await api('sellall');
                take(r);
                const s = r.summary || {};
                notice = { text: `Sold ${s.sold || 0} holding${s.sold === 1 ? '' : 's'}.` + (s.skipped && s.skipped.length ? ` No price right now for ${s.skipped.join(', ')}: still held.` : '') + (s.closed && s.closed.length ? ` Still held because its market is closed (a closed market's last price is not one to sell at): ${s.closed.join(', ')}.` : '') + (data.settings.enabled ? ' The autopilot is still on and will buy again at its next check-in.' : '') };
                if (window.practicePortfolio && window.practicePortfolio.reload) window.practicePortfolio.reload();
            });
        }
        else if (action === 'mailtest') {
            act('mailtest', async () => {
                const r = await api('mailtest');
                take(r);
                notice = r.summary && r.summary.sent ? { text: `A test email is on its way to ${userId()}. If it is not in your inbox in a few minutes, look in junk.` }
                    : { text: `The test email could not be sent${r.mail && r.mail.why ? ' (' + r.mail.why + ')' : ''}.`, bad: true };
            });
        }
        else if (action === 'stoporder' || action === 'restoreorder') {
            act('tune', async () => { take(await api('tune', { op: action })); notice = { text: action === 'stoporder' ? 'Trial stopped. Shares are bought as their screener ranks them.' : 'Put back: shares are bought as their screener ranks them.' }; });
        }
        else if (action === 'restore' || action === 'stoptrial') {
            act('tune', async () => { take(await api('tune', action === 'restore' ? { op: 'restore', param: t.getAttribute('data-param') } : { op: 'stop' })); notice = { text: action === 'restore' ? 'Put back to the level\'s own rule.' : 'Trial stopped. The rule stays as it was.' }; });
        }
        else if (action === 'run') {
            act('run', async () => {
                const r = await api('run');
                take(r);
                const s = r.summary || {};
                // when nothing was traded, say why here: the note with the reason may be hidden by "Buys and sells only"
                notice = { text: s.conflict ? 'The portfolio was being changed at the same time, so nothing was traded. Try again.'
                    : !(s.bought || s.sold) && s.why ? `Checked in: nothing bought or sold. ${s.why}`
                    : `Checked in: ${s.bought || 0} bought, ${s.sold || 0} sold. Details are listed below.` };
                if (window.practicePortfolio && window.practicePortfolio.reload) window.practicePortfolio.reload();
            });
        }
    });
    const changed = (e) => {
        if (!e.target || !data || !data.allowed) return;
        const id = e.target.id || '', inPanel = id.indexOf('ap-') === 0 || (e.target.getAttribute && e.target.getAttribute('data-ap-screener'));
        if (!inPanel) return;
        if (id === 'ap-tradesonly') {                                                    // how the list is shown: kept in this browser, not a setting of the autopilot
            if (e.type === 'change') { readDraft(); tradesOnly = !!e.target.checked; remember(tradesOnly); showAll = false; if (editing()) syncDraft(); else render(); }
            return;
        }
        saveError = null;
        if (id === 'ap-enabled') { if (e.type === 'change') flush(); return; }           // the switch saves at once
        queueSave(e.type === 'change' ? 150 : 900);                                      // ticks and menus quickly; typing after a pause
    };
    document.addEventListener('input', changed);
    document.addEventListener('change', changed);

    // Leaving the page with a change still waiting: send it now
    const leaving = () => { if (data && data.allowed && (saveTimer || isDirty())) flush(true); };
    if (typeof window !== 'undefined' && window.addEventListener) window.addEventListener('pagehide', leaving);
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') leaving(); });

    if (typeof setInterval === 'function') { setInterval(() => refresh(false), REFRESH_MS); setInterval(tick, 1000); }
    // A few plain lines on what the autopilot panel shows right now, for the AI chat on the dashboard (ai-chat.js)
    function summary() {
        if (!data) return '';
        if (!data.allowed) return data.locked === 'plan' ? 'AI AUTOPILOT (Beta): not available to this account, which is not on a paid plan. It is included in every paid plan; the plans are under the tabs.' : '';
        const s = data.settings, o = data.options, r = withHoldings((o.risk || {})[String(s.risk)] || {}, s), lines = [], cut = (t, n) => String(t || '').slice(0, n);
        const auto = (k) => Array.isArray(s.auto) && s.auto.includes(k) ? ' (automatic from the risk level)' : ' (set by the user)';
        // the user's own number of holdings is said outright: the chat otherwise answers with the level's number
        const level = ((o.risk || {})[String(s.risk)] || {}).positions, own = s.holdings > 0 ? `, the number the user set in "Number of holdings" (it uses ${s.holdings}, not the level's own ${level})` : '';
        lines.push(`AI AUTOPILOT (Beta, fake money): switched ${s.enabled ? 'ON' : 'OFF'}. Risk level ${r.name || s.risk} (up to ${r.positions} holdings${own}; loss limit ${data.rules ? data.rules.stop : r.stop}%, gain mark +${data.rules ? data.rules.take : r.take}%). Budget ${usd0(s.budgetUsd)}; built up over ${s.periodDays} day${s.periodDays === 1 ? '' : 's'}${auto('periodDays')}; checks in ${everyText(s.everyHours)}${auto('everyHours')}; keeps a holding at most ${holdText(s.maxHoldDays)}${auto('maxHoldDays')}. Trailing stop: ${(TRAILS[trailOf(s)] || {}).name || 'default'}.`);
        lines.push('Screeners ticked: ' + (s.screeners.map(k => (o.screeners[k] || {}).name || k).join(', ') || 'none') + '.' + (sharesOn() ? ' ' + cut(splitText(s).split(' On automatic')[0], 320) : ''));
        lines.push(`May by itself (selling early on the AI review was taken out on 17 Oct 2026): try changes to its own rules ${s.selfTune !== false ? 'yes' : 'no'}; email its reviews ${s.emails !== false ? 'yes' : 'no'}.`);
        if (data.money) lines.push(`Practice money it can use: ${usd0(data.money.reach)} (${usd0(data.money.cash)} cash, ${usd0(data.money.invested)} it has invested).`);
        if (data.nextCheck && data.nextCheck.at) lines.push(`Next check-in: ${when(data.nextCheck.at)} (${leftText(data.nextCheck.at)}), ${andList(data.nextCheck.markets)} market.`);
        (data.coming || []).slice(0, 5).forEach(c => lines.push('Coming: ' + (c.at ? when(c.at) : typeof c.after === 'number' ? `after ${c.after} more finished trades` : 'not planned') + ': ' + cut(c.text, 230)));
        lines.push('Needs the user: ' + ((data.needs || []).map(n => cut(n.text, 200)).join(' | ') || 'nothing') + '.');
        if (data.gauge && typeof data.gauge.level === 'number') lines.push(`Market risk gauge now: ${data.gauge.name} (${data.gauge.level} of 4; S&P 500 ${data.gauge.spy < data.gauge.avg200 ? 'below' : 'above'} its 200-day and ${data.gauge.spy < data.gauge.avg50 ? 'below' : 'above'} its 50-day average, VIX ${data.gauge.vix}). Shown for information and recorded with each buy; it does not make the autopilot hold cash.`);
        if (data.themes && data.themes.on) { const t = data.themes; lines.push(`Themes part (a trial since 18 Oct 2026): ${Math.round(t.share * 100)}% of the budget (${usd0(t.target)}) in the ${t.count} strongest of 14 sector and theme funds by their past year, changed monthly; holds ${t.held.map(h => h.symbol + ' ' + h.name).join(', ') || 'nothing yet'}; next change ${t.next ? when(t.next) : 'at the next US check-in'}; ${t.trades && t.trades.n ? `${t.trades.n} sold, ${usd2(t.trades.usd)}` : 'none sold yet'}. The AI model's daily news calls are recorded and scored a week later, not acted on: ${t.ai && t.ai.scored ? `${t.ai.right} of ${t.ai.scored} right` : 'none scored yet'}.`); }
        (data.plans || []).filter(p => !p.theme).slice(0, 8).forEach(p => lines.push(`Holds ${p.label}: sold at the latest ${when(p.sellBy)}, sooner at ${p.stop}% or +${p.take}%${p.closed ? '; its market is closed now' : ''}.`));
        const c = data.scorecard, m = data.month && data.month.last30;
        if (c && c.n) lines.push(`Finished trades: ${c.n} (${c.up} up), average ${pc(c.avg)} each${m ? `; last 30 days ${usd2(m.usd)}` : ''}. Too few to judge under ${data.minSample || 8}.`);
        else lines.push('Finished trades: none yet.');
        if (data.tune && data.tune.trial) lines.push('Trial of its own rules running: ' + cut(data.tune.trial.text, 160) + '.');
        if (data.order && data.order.mode === 'trial') lines.push(`Trial for shares running: every second share bought is the one furthest above its 52-week low (${data.order.with} finished that way, ${data.order.without} as ranked).`);
        if (data.central) lines.push(`Learning: shared by every account. ${data.central.trades} finished trades from ${data.central.accounts} account${data.central.accounts === 1 ? '' : 's'} are in one record (nothing in it says whose they were); the rules it changes after a trial, the screeners it rests and its notes come from that record and apply to every account.${data.central.on ? '' : ' This account takes no part: "Try changes to its own rules" is off.'}`);
        (data.log || []).slice(-3).forEach(e => lines.push(`Recent (${when(e.t)}): ${e.type === 'buy' ? 'bought ' + e.symbol + '. ' : e.type === 'sell' ? 'sold ' + e.symbol + '. ' : ''}${cut(e.text, 200)}`));
        return lines.join('\n');
    }
    // ---- the bell: the buys and sells it has made are handed to autopilot-bell.js, which shows them in the bell on every page
    const trades = () => ((data && data.log) || []).filter(e => e.type === 'buy' || e.type === 'sell');
    function bellFeed() {
        if (!data || !window.autopilotBell) return false;
        window.autopilotBell.set(data.allowed ? trades().slice(-12).map(e => ({ t: e.t, type: e.type, symbol: e.symbol, name: e.name || '', usd: e.usd, gain: e.type === 'sell' ? gainOf(e) : null, pct: typeof e.pct === 'number' ? e.pct : null })) : [], !!data.allowed);
        return true;
    }
    function bellOpen() {                                   // from the bell to the list of what it has done
        const drop = document.getElementById('notification-dropdown');
        if (drop && drop.remove) drop.remove();
        if (window.dashboardTabs && window.dashboardTabs.show) window.dashboardTabs.show('autopilot');
        showPart('activity');
        const list = document.getElementById('ap-done');
        if (list && list.scrollIntoView) list.scrollIntoView({ block: 'start' });
    }
    let bellMark = null;
    function bellRefresh() {                                // after each load: has it bought or sold since the bell was last told?
        const t = trades(), mark = t.length + '|' + (t.length ? t[t.length - 1].t : '') + '|' + (data && data.allowed ? 1 : 0);
        if (mark !== bellMark && bellFeed()) bellMark = mark;
    }
    window.practiceAutopilot = { reload: load, flush, refresh, tick, leftText, marketSlots, summary, bellFeed, bellOpen, gainOf };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load); else load();
})();
