# Questions asked about making the autopilot better, and what became of each

The owner, 12 Oct 2026: "see how i asked you something earlier and you thought hmm that could be useful to improve, what
i'm after is for you to ask these questions and actively gather more ways to improve."

So every weekly check **adds at least five new questions of the session's own**, drawn from what the review shows (a group
that lost, a sale that came too early, something odd in the diary) and from plain curiosity, and tests the ones that can
be tested. Shares first. A question is only closed with evidence; "tried, no difference" is an answer worth keeping,
so that nobody asks it again. How an idea is tested and what counts as passing: `site-overview.md` section 8c, "THE MANDATE".

Status: **open** (not tested yet), **waiting** (needs trades or data that are not there yet), **answered**, **on trial** (live).

| # | Asked | Question | How to test it | Status and answer |
|---|---|---|---|---|
| 1 | 12 Oct, owner | Are the shares at the top of a screener there because they just rose fast, and do they then drop? | Four years of prices, S&P 100: what the top 10 and the fastest risers did next | **Answered: no.** The top 10 did about what the whole list did a day, a week and a month later; a fast rise over 1 to 30 days was followed by neither a clear fall nor a clear rise (`paper-test/results-*-one-worker.txt`) |
| 2 | 12 Oct, owner | The same for coins | The entry log against prices now: `crypto/entry_study.py` | **Waiting** (one day of data says yes: entries fell 4%, the fastest risers 5 to 7%). Needs five separate days. Low priority: his interest is shares |
| 3 | 12 Oct, owner | Do headlines add anything to a choice? | `heads` on each buy; the review's split | **Waiting** for 30 buys with and 30 without |
| 4 | 11 Oct | Is the share furthest above its 52-week low a better buy than the top of the ranking? | Replay: yes in both parts (+2 points a trade against the fund). Live: every second share buy | **On trial** (verdict at 10 finished each way) |
| 5 | 11 Oct | Does selling a share when the screener's signal turns cut winners short? | Replay: yes (holdings kept 4 to 7 days whatever the limit) | **On trial** since 12 Oct 2026 (the patient-shares trial: every second pair of shares is not sold on the signal nor by the AI review) |
| 6 | 11 Oct | Is a longer holding time better for shares? | Replay: 1 day -4%, 5 days +92%, 20 days and more +103% to +106% | **Open**: first in the trial queue |
| 7 | 12 Oct | Would a loss limit and gain mark set from each share's own movement do better than the same two numbers for all? | Replay, `--limits` | **Answered: no real difference** for large shares (`replay/results-limits-2026-10-12.txt`) |
| 8 | 12 Oct | Does the number of holdings change the profit? | Replay with 2 to 50 holdings | **Answered: no**, it changes how bumpy the account is |
| 9 | 12 Oct, session | Does the ranking work better when the whole market is rising (the index above its 50- or 200-day average) than when it is falling? Should it hold fewer shares, or none, in a falling market? | Replay with the buys switched off, or halved, on days the index is below its average | **Open** |
| 10 | 12 Oct, session | Do winners get sold too soon? Would no gain mark at all, only the stop that follows a rise, have made more? | Replay with the gain mark removed; live: `after` for sales at the gain mark | **Open** |
| 11 | 12 Oct, session | Do shares sold at the loss limit bounce back? Is the limit protecting money or locking in dips? | Replay: what a stopped-out share did over the next 5 and 20 days; live: `after` for those sales | **Open** |
| 12 | 12 Oct, session | Does a share that is near the top of several screeners at once (S&P 500, NASDAQ 100 and Russell 1000 together) do better than one that tops a single list? | Live: tag the buy with how many ticked screeners rank it in their top 30; needs the wider price data to replay | **Open** |
| 13 | 12 Oct, session | Are the rankings worth more among smaller companies (Russell 2000, S&P 400 and 600), where fewer people are watching, than among the 100 largest? | Needs prices for those lists (to download slowly); then the factor study and the replay on them | **Waiting** for the prices |
| 14 | 12 Oct, session | Does the AI model's pick from the shortlist beat simply taking the top by rank? | Live record: `chosen` (the model's pick, by rank, by the trial) once each has 30 trades. If it does not: drop the call and save the cost | **Waiting** for trades |
| 15 | 12 Oct, session | Is the money lost on a few bad days when everything it holds falls together (all from one sector, or all high-flyers)? Would a limit per sector steady it? | The diary: losses by day; replay with at most N holdings a sector (needs a sector for each share) | **Open** |
| 16 | 12 Oct, session | Do calm shares that have risen steadily do better, for the swings they bring, than jumpy ones that rose the same amount? | Factor study: rise over 90 days divided by how jumpy the share is, against what it did next | **Open** |
| 17 | 12 Oct, session | Does it matter when in the session a share is bought (the first check-in after the open, when prices jump about, against later)? | Live: the hour of each buy against its result; needs 30 trades a group | **Waiting** for trades |
| 18 | 12 Oct, session | Do real company figures (profit margin, debt, growth) separate the shares that went on rising from those that did not? | No history here: record them with each buy from now, split the record later | **Waiting**: needs the recording built |
| 19 | 12 Oct, owner | When the AI review sells a share early (HPE, three hours after it was bought), was that right: did the share go on falling or come back? | Live: `after` on each such sale (the same length of time again), and a look five trading days later once that is recorded (`after5`, to build); the review's part 4 | **Waiting** for sales; the five-day look is not built yet |
