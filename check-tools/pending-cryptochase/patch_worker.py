"""The crypto screener stops rewarding a coin that has just jumped (23 Oct 2026). Built from the live worker's code:
    python3 patch_worker.py <live lambda_function.py> <out lambda_function.py>
Why, from the coin entry study (check-tools/crypto/entry_study.py, 733 entries into the top 10 from 10 to 22 Oct 2026, every day
the same way): coins that entered after rising 10% or more the day before fell 12% on average afterwards (199), after rising 20% or
more in the week 8% (262); those that had risen under 5% or fallen rose 2.4% (161). The score gave +2 for a day's rise over 10% and
+1 over 5%. Now: over 10% in a day -2, 5 to 10% nothing, over 20% in a week -1 more. Falls keep their points; nothing else changes."""
import sys
src = open(sys.argv[1]).read()
old = """        if change_24h > 10:
            score += 2
            score_breakdown.append(f"24h Change {change_24h:.1f}%: +2")
        elif change_24h > 5:
            score += 1
            score_breakdown.append(f"24h Change {change_24h:.1f}%: +1")
        elif change_24h < -10:"""
new = """        # A jump is not a reason to buy (23 Oct 2026): coins that entered the top 10 after a day's rise of 10% or more fell 12% on
        # average afterwards, after a week's rise of 20% or more 8% (check-tools/crypto/entry_study.py, 733 entries)
        if change_24h > 10:
            score -= 2
            score_breakdown.append(f"24h Change {change_24h:.1f}%: -2 (a jump: coins tend to fall back after one)")
        elif change_24h > 5:
            score_breakdown.append(f"24h Change {change_24h:.1f}%: 0 (a fast rise earns no points)")
        elif change_24h < -10:"""
assert src.count(old) == 1, 'the daily-change rule is not where it was'
src = src.replace(old, new)
anchor = """        # PROFIT PROBABILITY ENHANCEMENTS
"""
assert src.count(anchor) == 1, 'anchor'
src = src.replace(anchor, """        if change_7d > 20:
            score -= 1
            score_breakdown.append(f"7d Change {change_7d:.1f}%: -1 (a fast week: coins tend to fall back after one)")

""" + anchor)
open(sys.argv[2], 'w').write(src)
print('ok')
