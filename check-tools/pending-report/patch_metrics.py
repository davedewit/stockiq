"""stock_metrics.py is an exact copy of the report function's scoring code: this copies the changed functions across.
    python3 patch_metrics.py <new lambda_function2.py> <live stock_metrics.py> <out stock_metrics.py>"""
import sys, ast
lam = open(sys.argv[1]).read(); sm = open(sys.argv[2]).read()
def source_of(text, name):
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return '\n'.join(text.split('\n')[node.lineno - 1:node.end_lineno])
    raise SystemExit(name + ' not found')
for name in ('calculate_rsi', 'calculate_unified_investment_score'):
    old = source_of(sm, name); assert sm.count(old) == 1, name
    sm = sm.replace(old, source_of(lam, name))
anchor = 'def calculate_unified_investment_score('; assert sm.count(anchor) == 1
sm = sm.replace(anchor, 'TREND_FULL_AT = 2.0      # percent apart at which each half of the trend factor counts in full\n\n' + source_of(lam, 'trend_points') + '\n\n\n' + anchor)
old_doc = 'If the Lambda\'s scoring changes, copy the updated functions here too.'; assert sm.count(old_doc) == 1
sm = sm.replace(old_doc, 'If the Lambda\'s scoring changes, copy the updated functions here too\n(check-tools/report/patch_metrics.py does it, and report_test.py fails when the two differ).')
compile(sm, 'stock_metrics.py', 'exec'); open(sys.argv[3], 'w').write(sm)
f = lambda text: {n.name: ast.dump(n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
a, b = f(lam), f(sm)
same = [n for n in b if a.get(n) == b[n]]; print('the same as the report function, statement for statement:', ', '.join(same))
assert set(same) == {'calculate_rsi', 'calculate_macd', 'calculate_bollinger_bands', 'calculate_support_resistance_enhanced', 'trend_points', 'calculate_unified_investment_score'}, same
