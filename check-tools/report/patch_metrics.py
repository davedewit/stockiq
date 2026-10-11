"""stock_metrics.py (the stock pages' scoring) is an exact copy of the report function's scoring code: this copies the
functions across, and stops if the two are not the same afterwards. Run it whenever the report function's scoring changes.
    python3 check-tools/report/patch_metrics.py <report lambda_function2.py> <stock_metrics.py> <out stock_metrics.py>
(the report's code is in lambda-sync/stockiq-option-1-1-custom-analysis/; out may be the same file as the second)"""
import sys, ast
COPIED = ('calculate_rsi', 'calculate_macd', 'calculate_bollinger_bands', 'calculate_support_resistance_enhanced', 'trend_points', 'calculate_unified_investment_score')
lam = open(sys.argv[1]).read(); sm = open(sys.argv[2]).read()
def source_of(text, name):
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return '\n'.join(text.split('\n')[node.lineno - 1:node.end_lineno])
    return None
for name in COPIED:
    new = source_of(lam, name); assert new, name + ' is not in the report function'
    old = source_of(sm, name)
    if old:
        assert sm.count(old) == 1, name
        sm = sm.replace(old, new)
    else:                                         # a function the pages' copy does not have yet: before the score
        anchor = 'def calculate_unified_investment_score('; assert sm.count(anchor) == 1
        sm = sm.replace(anchor, new + '\n\n\n' + anchor)
constant = 'TREND_FULL_AT = 2.0      # percent apart at which each half of the trend factor counts in full\n'
if 'TREND_FULL_AT =' not in sm:
    anchor = 'def trend_points('; assert sm.count(anchor) == 1
    sm = sm.replace(anchor, constant + '\n' + anchor)
old_doc = 'If the Lambda\'s scoring changes, copy the updated functions here too.'
if old_doc in sm:
    sm = sm.replace(old_doc, 'If the Lambda\'s scoring changes, copy the updated functions here too\n(check-tools/report/patch_metrics.py does it, and stops if the two differ afterwards).')
compile(sm, 'stock_metrics.py', 'exec')
f = lambda text: {n.name: ast.dump(n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
a, b = f(lam), f(sm)
differ = [n for n in COPIED if a.get(n) != b.get(n)]
assert not differ, differ
open(sys.argv[3], 'w').write(sm)
print('the same as the report function, statement for statement:', ', '.join(COPIED))
