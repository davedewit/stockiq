#!/bin/bash
# Show or change how often the site's prices refresh.
#
# The timings live in three shared scripts in website/ (since 18 Oct 2026; before that they were inside
# index.html and dashboard.html, and this script edited those):
#   live-market.js   the figures on show on the home page, dashboard and daily screener pages (side panel,
#                    the four lists, the index cards): a random gap between MIN and MAX seconds, only while
#                    someone is using the page; a quiet market slows itself down to a minute.
#   stock-prices.js  the price at the top of a stock page and its "People also watch" cards.
#   market-panel.js  a full reload of the panel (which shares are on the four lists, every tab).
# A change goes live with the next daily update (it uploads changed scripts), or ask a session to deploy it now.
# Faster costs more Lambda calls: about 6 a minute per person watching at 6-10 s.
set -euo pipefail
WEB="/Users/dave/VSCODE/website"
LM="$WEB/live-market.js"; SP="$WEB/stock-prices.js"; MP="$WEB/market-panel.js"

current() {
    local fast stock panel
    fast=$(grep -oE "T\.fast \|\| \[[0-9]+, [0-9]+\]" "$LM" | grep -oE "[0-9]+" | tr '\n' ' ')
    stock=$(grep -oE "setInterval\(refreshPrices, [0-9]+\)" "$SP" | head -1 | grep -oE "[0-9]+")
    panel=$(grep -oE "var EVERY = [0-9]+ \* 60 \* 1000" "$MP" | grep -oE "[0-9]+" | head -1)
    set -- $fast
    [[ -n "${1:-}" && -n "$stock" && -n "$panel" ]] || { echo "Could not read the settings: the scripts have changed. Ask a session to update this script."; exit 1; }
    echo "Current settings:"
    echo "  1. Market figures (home page, dashboard, daily pages): every $(( $1 / 1000 ))-$(( $2 / 1000 )) s at random, while the page is in use"
    echo "  2. Stock page prices: every $(( stock / 1000 )) s"
    echo "  3. Full reload of the market panel: every $panel min"
}

ask_secs() {   # ask_secs "<question>" <minimum>
    local v; read -r -p "$1: " v
    [[ $v =~ ^[0-9]+$ ]] || { echo "Whole seconds only."; exit 1; }
    (( v >= $2 )) || { echo "At least $2 s, to keep the Lambda calls down."; exit 1; }
    echo "$v"
}

current
echo ""
read -r -p "Change which (1-3, or Enter to leave them): " option
case "${option:-}" in
    "") exit 0 ;;
    1)  lo=$(ask_secs "Shortest gap in seconds (now 6)" 5)
        hi=$(ask_secs "Longest gap in seconds (now 10)" "$lo")
        sed -i '' -E "s/T\.fast \|\| \[[0-9]+, [0-9]+\]/T.fast || [$(( lo * 1000 )), $(( hi * 1000 ))]/" "$LM" ;;
    2)  s=$(ask_secs "Seconds between stock page refreshes (now 5)" 5)
        sed -i '' -E "s/setInterval\(refreshPrices, [0-9]+\)/setInterval(refreshPrices, $(( s * 1000 )))/g" "$SP" ;;
    3)  read -r -p "Minutes between full reloads (now 5): " m
        [[ $m =~ ^[0-9]+$ && $m -ge 1 ]] || { echo "Whole minutes, at least 1."; exit 1; }
        sed -i '' -E "s/var EVERY = [0-9]+ \* 60 \* 1000/var EVERY = $m * 60 * 1000/" "$MP" ;;
    *)  echo "Use 1, 2 or 3."; exit 1 ;;
esac
for f in "$LM" "$SP" "$MP"; do node --check "$f" || { echo "A script no longer parses: undo with git checkout -- $f"; exit 1; }; done
echo ""
current
echo ""
echo "Saved locally. It goes live with the next daily update, or ask a session to deploy it now."
echo "To undo: cd $WEB && git checkout -- live-market.js stock-prices.js market-panel.js"
