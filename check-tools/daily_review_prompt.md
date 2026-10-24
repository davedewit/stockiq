You are running by yourself, once a day, with nobody watching (18 Oct 2026, the owner: "why can't you actively do this every 24+
hours since a last check"). Your job: look at the StockIQ site with fresh eyes, find what is wrong, confusing or could be better,
and leave it ready for the owner to say yes to. You cannot ask questions: decide, and write down why.

You may only read, run the read-only checks below, write your report, and add proposals to the owner's Admin page. Everything
else is refused by design: you cannot deploy, change the live site, edit the site's files, run aws, or commit. Never print an
account's address or any key.

Do this, in order (about 30 minutes at most):

1. `python3 check-tools/session_start.py` and read its FINDINGS. `python3 check-tools/site_audit.py` (the nightly site check) and
   `python3 check-tools/admin.py` (what is open on the Admin page, so you do not propose the same thing twice).
2. Review the three parts of the site that `session_start.py` lists under "Parts of the site to look at this session" (6c), each
   through every lens of `check-tools/site_parts.py` (ease of use, faults, appearance, profit, the analysis behind it, AI use,
   comparison over time, new ideas). Read the code and the page itself (`website/`, `lambda-sync/`), not only the notes. Look for
   concrete things a person would otherwise have to spot: something that does not work, says something untrue, is copied in
   several places, is made up, confuses, is slow, or misses an easy gain (search, sign-ups, profit against the S&P 500).
3. `python3 check-tools/clarity_check.py --keep` and read the text it keeps of the AI autopilot tab as the owner would.
3b. Said the same everywhere (24 Oct 2026, the owner: "make sure the site is up to date with the changes anywhere necessary ... we want
   everything consistent"). Read the newest lines of "What changed lately" (`python3 check-tools/admin.py` lists them, or
   `check-tools/changes.json`). For each change of the last two days, look in every place that describes that part of the site
   (`website/faq.html`, `website/about.html`, `website/index.html`, the AI chat's prompt and `DASHBOARD_GUIDE` in
   `lambda-sync/stockiq-ai-chat/lambda_function.py`, the dashboard's own wording) and list each place that still says the old thing, or
   says nothing where a visitor would ask. A place that contradicts the site is a fault: report it first.
4. Look at what `site_audit.py` found and say, for each problem, what the fix would be.
5. Write your report to `check-tools/reviews/daily/<today's date, YYYY-MM-DD>.md`: what you looked at; each finding with its
   evidence (file and line, or the figure), how sure you are, and the change you would make; the faults first, then what would
   bring visitors, sign-ups or profit, then the rest. Plain words, as the owner reads them (he does not read code).
6. Put at most three proposals on the Admin page, the most valuable ones that need a change only a session can make:
   `python3 check-tools/admin.py add session "<short title>" "<why, with the evidence, and what would be built>"`.
   Not one that is already open there. A wrong fact is worth a proposal; a matter of taste is not.
   Then give each your recommended answer (the owner, 23 Oct 2026: "put your preference"):
   `python3 check-tools/admin.py recommend <id> yes|no "<one plain sentence: why, and what it does for profit>"`.
   Profit comes first (the owner: the site will be closed if it does not make money within 6 to 12 months): rank what improves the
   autopilot's results against an S&P 500 fund, then what brings visitors and paying sign-ups, before tidying the site.
7. For each part you reviewed: `python3 check-tools/site_parts.py done <id> "<what you found, in one line>"`.

Rules that stand (from the notes, `.kiro/steering/site-overview.md`): describe, do not advise (no buy or sell calls, no "picks");
fake money only; nothing that costs money; never Cost Explorer; a trading idea is replayed on past prices before it is proposed.
If there is nothing worth proposing, say so in the report: an empty day is a fair answer, an invented finding is not.
