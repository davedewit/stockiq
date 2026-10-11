"""Third, small step for the single-stock report function: a warm container keeps a share's company figures from one
report to the next, already filled; the second report then named the first source alone ("Finnhub") for figures that
had come from both. The note of where they came from is now kept with them.
    python3 patch_report3.py <live lambda_function2.py> <out lambda_function2.py>"""
import sys
src = open(sys.argv[1]).read()
old = """    had = [k for k in FIGURE_KEYS if fundamentals.get(k) is not None]
    added, as_of = [], ''
"""
assert src.count(old) == 1, src.count(old)
src = src.replace(old, """    if 'figures_source' in fundamentals:          # kept from an earlier report by this container: already filled
        return fundamentals
""" + old)
compile(src, 'lambda_function2.py', 'exec'); open(sys.argv[2], 'w').write(src); print('written:', len(src.split('\n')), 'lines')
