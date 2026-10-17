"""Applies this change to a copy of stockiq-ai-trader's lambda_function.py (in place): a market whose every ticked screener
is resting gets no share of the budget, and the check-in note says so. Usage: python3 patch_lambda.py <lambda_function.py>"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, ('not found once', old[:80], s.count(old)); s = s.replace(old, new)
rep('''def market_split(settings):
    """The share of the budget each market with a ticked screener may hold, as fractions: {market: share}.''', '''def market_split(settings, resting=()):
    """The share of the budget each market with a ticked screener may hold, as fractions: {market: share}.
    resting: the screeners that are resting (state['rest']). A market whose every ticked screener is resting gets no share,
    so its part of the budget goes to the markets that can buy (until 17 Oct 2026 it kept its share: the coin screener rested
    for two weeks held a fifth of the budget back as cash). It gets its share again when the rest ends.''')
rep('''    groups = [g for g in GROUPS if any(SCREENERS[k][5] == g for k in settings.get('screeners') or [])]
    own = {g''', '''    groups = [g for g in GROUPS if any(SCREENERS[k][5] == g and k not in resting for k in settings.get('screeners') or [])]
    own = {g''')
rep('def market_slots(settings):', 'def market_slots(settings, resting=()):')
rep('    positions, split = holdings_of(settings), market_split(settings)', '    positions, split = holdings_of(settings), market_split(settings, resting)')
rep('''def coin_share(settings):
    """The share of the budget that may be in coins: the coin market's holdings out of all of the level's (market_slots)."""
    return market_slots(settings).get(COINS, 0) / holdings_of(settings)''', '''def resting_words(settings, resting):
    """A sentence for the markets that get no share of the budget because every screener ticked there is resting, or ''."""
    ticked = settings.get('screeners') or []
    out = []
    for g in GROUPS:
        keys = [k for k in ticked if SCREENERS.get(k, ('',) * 6)[5] == g]
        if keys and all(k in resting for k in keys):
            until = max((parse_time(resting[k]) for k in keys if isinstance(resting, dict) and parse_time(resting.get(k))), default=None)
            out.append(f" {g} {'get' if g.endswith('s') else 'gets'} no share for now: {'its screener is' if len(keys) == 1 else 'its screeners are'} resting"
                       + (f" until {until.strftime('%-d %b')}" if until else '') + ', so that part of the budget goes to the other markets.')
    return ''.join(out)


def coin_share(settings, resting=()):
    """The share of the budget that may be in coins: the coin market's holdings out of all of the level's (market_slots)."""
    return market_slots(settings, resting).get(COINS, 0) / holdings_of(settings)''')
rep("crypto=coin_share(settings)), live_trial(", "crypto=coin_share(settings, state.get('rest') or {})), live_trial(")
rep('''    fit_budget(record, portfolio, now)                      # never work from a budget larger than the practice money there is
    rules = dict(rules_for(settings, state), crypto=coin_share(settings))''', '''    fit_budget(record, portfolio, now)                      # never work from a budget larger than the practice money there is
    rules = dict(rules_for(settings, state), crypto=coin_share(settings, state.get('rest') or {}))''')
rep('''    slots, in_group = market_slots(settings), {}
    for h in ai_holdings(portfolio):''', '''    slots, in_group = market_slots(settings, resting), {}
    for h in ai_holdings(portfolio):''')
rep('''    rules = dict(rules_for(settings, state), crypto=coin_share(settings))
    size, slack = settings['budgetUsd'] / rules['positions'], 0.01 * rules['positions']
    invested = sum(h['costUsd'] for h in mine)
    resting = state.get('rest') or {}''', '''    resting = state.get('rest') or {}
    rules = dict(rules_for(settings, state), crypto=coin_share(settings, resting))
    size, slack = settings['budgetUsd'] / rules['positions'], 0.01 * rules['positions']
    invested = sum(h['costUsd'] for h in mine)''')
rep('''            slots, in_group = market_slots(settings), {}
            for h in mine:''', '''            slots, in_group = market_slots(settings, resting), {}
            for h in mine:''')
rep("    out['coinShare'] = coin_share(settings)", "    out['coinShare'] = coin_share(settings, state.get('rest') or {})")
rep('''    slots, positions = market_slots(settings), holdings_of(settings)
    out['split']''', '''    slots, positions = market_slots(settings, state.get('rest') or {}), holdings_of(settings)
    out['split']''')
rep('''                                 + (f" The rest is for {' and '.join(others)}, bought when {'that market is' if len(others) == 1 else 'those markets are'} open." if others else '')
                                 + ' The shares are set under "Screeners it buys from".')''', '''                                 + (f" The rest is for {' and '.join(others)}, bought when {'that market is' if len(others) == 1 else 'those markets are'} open." if others else '')
                                 + resting_words(settings, resting)
                                 + ' The shares are set under "Screeners it buys from".')''')
open(p, 'w').write(s)
print('patched', p)
