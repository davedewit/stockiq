// Practice portfolio (dashboard): practice buys with fake money, then monitored against live prices.
// No real trades are placed anywhere. Each buy is one line; selling closes that line at the current price.
// Stored per user by the stockiq-paper-portfolio Lambda; the sums are done here.
(function () {
    const API = 'https://5c7pt7qurshld4cwaqyopfxcei0cuurj.lambda-url.us-east-1.on.aws/';
    const PRICE_API = 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/?symbol=';
    const SEARCH_API = 'https://3oaokynmssanpzz7bwomt7ft6i0qrwhk.lambda-url.us-east-1.on.aws/';
    const STARTING_CASH = 100000;
    const DEFAULT_AMOUNT = 1000;
    const BENCHMARK = 'SPY';                      // an S&P 500 fund: "what if the same money had simply gone into the market"

    // ---------------------------------------------------------------- sums (no page, no network)
    function newState(now) {
        return { v: 1, startingCash: STARTING_CASH, cash: STARTING_CASH, createdAt: now, holdings: [], closed: [] };
    }

    // Which exchange-rate symbol turns a price in `currency` into US dollars. London prices are in pence.
    // Dollars-per-unit quotes are used where they are precise (AUD, GBP, EUR, NZD). Other currencies are quoted per
    // dollar and turned over, because their per-unit quote is rounded too coarsely (JPYUSD=X is 0.0063).
    // The same rule is in the stockiq-ai-trader Lambda (fx_pair): keep them alike.
    function fxFor(currency) {
        if (!currency || currency === 'USD') return { symbol: null, divisor: 1, turn: false };
        const minor = { GBp: 'GBP', GBX: 'GBP', ZAc: 'ZAR', ILA: 'ILS' }[currency];
        const base = (minor || currency).toUpperCase(), direct = ['AUD', 'GBP', 'EUR', 'NZD'].includes(base);
        return { symbol: direct ? base + 'USD=X' : 'USD' + base + '=X', divisor: minor ? 100 : 1, turn: !direct };
    }
    // US dollars for one unit, from that quote's price
    function fxRate(fx, price) { return !fx.symbol ? 1 : price > 0 ? (fx.turn ? 1 / price : price) / fx.divisor : null; }

    function applyBuy(state, b) {
        const amount = Math.round(b.amountUsd * 100) / 100;
        if (!(amount >= 1)) throw new Error('Enter an amount of at least $1');
        if (amount > state.cash + 0.005) throw new Error('Not enough practice cash: ' + usd(state.cash) + ' left');
        if (state.holdings.length >= 100) throw new Error('100 holdings is the limit. Sell one first');
        if (!(b.price > 0) || !(b.fx > 0)) throw new Error('No price available for ' + b.symbol);
        const holding = {
            id: 'h' + Date.parse(b.now).toString(36) + Math.floor(Math.random() * 1e6).toString(36),
            symbol: b.symbol, label: b.label || b.symbol, name: b.name || '', currency: b.currency || 'USD',
            qty: amount / (b.price * b.fx), buyPrice: b.price, buyFx: b.fx, costUsd: amount,
            boughtAt: b.now, spyAtBuy: b.spy > 0 ? b.spy : null, note: b.note || ''
        };
        state.holdings.push(holding);
        state.cash = Math.round((state.cash - amount) * 100) / 100;
        return holding;
    }

    function applySell(state, id, s) {
        const i = state.holdings.findIndex(h => h.id === id);
        if (i < 0) throw new Error('That holding is no longer in the list');
        if (!(s.price > 0) || !(s.fx > 0)) throw new Error('No price available to sell at');
        const h = state.holdings[i];
        const proceeds = Math.round(h.qty * s.price * s.fx * 100) / 100;
        state.holdings.splice(i, 1);
        state.closed.push(Object.assign({}, h, { sellPrice: s.price, sellFx: s.fx, proceedsUsd: proceeds, soldAt: s.now, spyAtSell: s.spy > 0 ? s.spy : null }));
        if (state.closed.length > 200) state.closed = state.closed.slice(-200);
        state.cash = Math.round((state.cash + proceeds) * 100) / 100;
        return proceeds;
    }

    // Tidy the sold list: one line (by id) or all of it. The money is untouched: what a sale brought in
    // went into the practice cash when it was sold, so the account value does not change.
    function applyClearSold(state, id) {
        const before = state.closed.length;
        state.closed = id ? state.closed.filter(h => h.id !== id) : [];
        return before - state.closed.length;
    }

    // How a result compares with the S&P 500 fund over the same days: 'ahead', 'behind' or 'level'.
    // null when neither has moved yet (a holding bought a moment ago is at 0.00% and so is the market: that
    // says nothing, and "0 of 1 ahead" would read as a verdict).
    const MOVED = 0.05;                            // percent: smaller than this is rounding, not a move
    function versusMarket(resultPct, marketPct) {
        if (Math.abs(resultPct) < MOVED && Math.abs(marketPct) < MOVED) return null;
        const gap = resultPct - marketPct;
        return gap > MOVED ? 'ahead' : gap < -MOVED ? 'behind' : 'level';
    }

    // What the sold list adds up to, and how many sales did better than the S&P 500 fund over the same days
    function soldSummary(state) {
        let cost = 0, proceeds = 0, compared = 0, ahead = 0, level = 0;
        state.closed.forEach(h => {
            cost += h.costUsd; proceeds += h.proceedsUsd;
            const verdict = h.spyAtBuy > 0 && h.spyAtSell > 0 ? versusMarket((h.proceedsUsd / h.costUsd - 1) * 100, (h.spyAtSell / h.spyAtBuy - 1) * 100) : null;
            if (verdict) { compared++; if (verdict === 'ahead') ahead++; if (verdict === 'level') level++; }
        });
        return { count: state.closed.length, cost, proceeds, gainUsd: proceeds - cost, gainPct: cost > 0 ? (proceeds / cost - 1) * 100 : null, compared, ahead, level };
    }

    // quotes: { SYMBOL: { price, currency, name } }, including exchange-rate symbols and the benchmark
    function valueOf(h, quotes) {
        const q = quotes[h.symbol];
        const fx = fxFor(h.currency);
        const rate = fx.symbol ? (quotes[fx.symbol] ? fxRate(fx, quotes[fx.symbol].price) : null) : 1;
        if (!q || !(q.price > 0) || !(rate > 0)) return { priced: false, valueUsd: h.costUsd, price: null, changePct: null, gainUsd: 0 };
        const valueUsd = h.qty * q.price * rate;
        return { priced: true, valueUsd, price: q.price, gainUsd: valueUsd - h.costUsd, changePct: (valueUsd / h.costUsd - 1) * 100,
                 pricePct: (q.price / h.buyPrice - 1) * 100 };
    }

    function summarize(state, quotes) {
        const spy = quotes[BENCHMARK] ? quotes[BENCHMARK].price : null;
        let holdingsValue = 0, cost = 0, marketValue = 0, marketCost = 0, unpriced = 0, compared = 0, ahead = 0, level = 0;
        state.holdings.forEach(h => {
            const v = valueOf(h, quotes);
            holdingsValue += v.valueUsd; cost += h.costUsd;
            if (!v.priced) unpriced++;
            if (spy > 0 && h.spyAtBuy > 0) {
                marketValue += h.costUsd * spy / h.spyAtBuy; marketCost += h.costUsd;
                const verdict = v.priced ? versusMarket((v.valueUsd / h.costUsd - 1) * 100, (spy / h.spyAtBuy - 1) * 100) : null;
                if (verdict) { compared++; if (verdict === 'ahead') ahead++; if (verdict === 'level') level++; }
            }
        });
        const accountValue = state.cash + holdingsValue;
        return {
            cash: state.cash, holdingsValue, cost, accountValue, unpriced, compared, ahead, level,
            gainUsd: accountValue - state.startingCash, gainPct: (accountValue / state.startingCash - 1) * 100,
            openGainUsd: holdingsValue - cost, openGainPct: cost > 0 ? (holdingsValue / cost - 1) * 100 : null,
            // the same dollars put into the S&P 500 fund on the same days
            marketPct: marketCost > 0 ? (marketValue / marketCost - 1) * 100 : null,
            // the fund's price is exactly what it was at every buy: the US stock market has not traded since (a weekend, a holiday)
            marketFlat: marketCost > 0 && state.holdings.every(h => !(h.spyAtBuy > 0) || Math.abs(spy / h.spyAtBuy - 1) < 1e-9)
        };
    }

    // Whose result is whose: the account's change since the start, split into the user's own buys and the autopilot's.
    // autoRealized: what the autopilot's finished trades have made in all (from practice-autopilot.js; it survives the
    // sold list being cleared). Without it, the autopilot's lines still in the sold list are added up instead.
    function splitGain(state, quotes, autoRealized) {
        const total = summarize(state, quotes).gainUsd;
        let autoOpen = 0, held = 0, listed = 0, sold = 0;
        state.holdings.forEach(h => { if (h.by === 'ai') { held++; autoOpen += valueOf(h, quotes).gainUsd; } });
        state.closed.forEach(h => { if (h.by === 'ai') { sold++; listed += h.proceedsUsd - h.costUsd; } });
        const autoSold = typeof autoRealized === 'number' && isFinite(autoRealized) ? autoRealized : listed;
        return { total, autoSold, autoOpen, auto: autoSold + autoOpen, yours: total - autoSold - autoOpen, any: held > 0 || sold > 0 || Math.abs(autoSold) > 0.004 };
    }

    // ---------------------------------------------------------------- formatting
    // rounded first, so a value a hair under zero shows as 0.00, not -0.00
    function usd(n) { n = Math.round(n * 100) / 100 || 0; return (n < 0 ? '-' : '') + '$' + Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
    function pct(n) { n = Math.round(n * 100) / 100 || 0; return (n >= 0 ? '+' : '') + n.toFixed(2) + '%'; }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
    function money(price, currency) {
        const digits = price >= 100 ? 2 : price >= 1 ? 3 : price >= 0.01 ? 4 : price >= 0.0001 ? 6 : 10;
        const number = digits === 10 ? price.toFixed(10).replace(/0+$/, '') : price.toFixed(digits);
        if (currency === 'GBp' || currency === 'GBX') return number + 'p';
        const prefix = { USD: '$', AUD: 'A$', CAD: 'C$', HKD: 'HK$', GBP: '£', EUR: '€', JPY: '¥' }[currency];
        return prefix !== undefined ? prefix + number : number + (currency ? ' ' + currency : '');
    }
    function colour(n) { return Math.round(n * 100) / 100 >= 0 ? '#22c55e' : '#ef4444'; }
    function day(iso) { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }); }
    function when(iso) { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }); }
    // Whose holding it is and what will happen to it. `plan` comes from the autopilot (practice-autopilot.js) for the
    // holdings it bought: it sells those by itself. Everything else stays until the user sells it.
    function planLine(h, plan) {
        if (h.by !== 'ai') return 'Bought by you: it stays until you sell it.';
        if (!plan) return '🤖 Bought by the autopilot.';
        if (!plan.auto) return '🤖 Bought by the autopilot, which is switched off: it stays until you sell it or switch the autopilot back on.';
        return `🤖 Autopilot: it sells this by itself, at the check-in around ${when(plan.sellBy)} at the latest, sooner at ${plan.stop}% or +${plan.take}%`
            + (plan.mode === 'off' ? '.' : plan.mode === 'full' && typeof plan.floor === 'number' && !(plan.peak >= plan.arm) ? `, or when its trailing stop is hit: it is at ${plan.floor >= 0 ? '+' : ''}${plan.floor}% now and follows the price up.`
                : `, or to keep part of a gain once it has been up ${plan.arm}%.` + (typeof plan.floor === 'number' ? ` It has been up enough: it is sold if it slips back to ${plan.floor >= 0 ? '+' : ''}${plan.floor}%.` : ''))
            + (plan.trial ? ' Part of a trial of one of its own rules.' : '')
            + ' The AI model also reviews it at every check-in and may sell it earlier.';
    }

    const pure = { newState, fxFor, fxRate, versusMarket, applyBuy, applySell, applyClearSold, soldSummary, valueOf, summarize, splitGain, planLine, usd, pct, money, esc, STARTING_CASH, DEFAULT_AMOUNT };
    if (typeof module !== 'undefined' && module.exports) module.exports = pure;
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    // ---------------------------------------------------------------- page
    const BTN2 = 'background: none; color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 6px 12px; font-size: 0.85rem; cursor: pointer; white-space: nowrap;';
    const BTN = 'background: #007bff; color: #fff; border: none; border-radius: 6px; padding: 6px 12px; font-size: 0.85rem; cursor: pointer; white-space: nowrap;';
    let state = null, version = 0, quotes = {}, loaded = false, loadError = null, notice = null, working = false, searchTimer = null;
    let ppBasis = 'usd';                          // which of dollars / quantity the user typed last
    let ppQuote = null;                           // latest price of the code in the search box: { symbol, price, fx, currency, name }
    // Works out the field the user did not type from the one they did, once the price of the code in the box is known
    function fillOther() {
        const a = document.getElementById('pp-amount'), q = document.getElementById('pp-qty'), b = document.getElementById('pp-symbol');
        if (!a || !q || !b || !ppQuote || ppQuote.symbol !== b.value.trim().toUpperCase()) return;
        const unit = ppQuote.price * ppQuote.fx;
        if (ppBasis === 'qty') { const n = parseFloat(q.value); a.value = n > 0 ? (Math.round(n * unit * 100) / 100).toString() : ''; }
        else { const n = parseFloat(a.value); q.value = n > 0 ? parseFloat((n / unit).toPrecision(6)).toString() : ''; }
    }
    async function priceFor(symbol) {
        const typed = String(symbol || '').trim().toUpperCase();
        if (!/^[A-Z0-9^=.\-]{1,24}$/.test(typed)) return null;
        const t = await quoteForTrade(typed);
        if (!t) return null;
        ppQuote = { symbol: typed, price: t.q.price, fx: t.fx, currency: t.q.currency, name: t.q.name };
        fillOther();
        return ppQuote;
    }
    let soldOpen = false;                         // whether the Sold list is unfolded (kept across redraws)
    const userId = () => { const u = localStorage.getItem('userId'); return u && u !== 'anonymous' ? u : null; };
    const box = () => document.getElementById('practice-portfolio');

    async function api(action, extra) {
        const res = await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.assign({ action, userId: userId() }, extra || {})) });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) { const e = new Error(body.error || 'The practice portfolio could not be reached'); e.conflict = !!body.conflict; throw e; }
        return body;
    }

    async function fetchQuote(symbol) {
        try {
            const res = await fetch(PRICE_API + encodeURIComponent(symbol));
            const meta = (await res.json())?.chart?.result?.[0]?.meta;
            if (!meta || !(meta.regularMarketPrice > 0)) return null;
            return { price: meta.regularMarketPrice, currency: meta.currency || 'USD', name: meta.longName || meta.shortName || '', time: meta.regularMarketTime || 0 };
        } catch (e) { return null; }
    }
    // A quote plus what is needed to turn it into dollars and compare it with the market
    async function quoteForTrade(symbol) {
        const q = await fetchQuote(symbol);
        if (!q) return null;
        const fx = fxFor(q.currency);
        const [rateQuote, spy] = await Promise.all([fx.symbol ? fetchQuote(fx.symbol) : null, fetchQuote(BENCHMARK)]);
        if (fx.symbol && !rateQuote) return null;
        quotes[symbol] = q; if (rateQuote) quotes[fx.symbol] = rateQuote; if (spy) quotes[BENCHMARK] = spy;
        return { q, fx: fxRate(fx, rateQuote ? rateQuote.price : 0), spy: spy ? spy.price : null };
    }
    async function refreshQuotes() {
        if (!state) return;
        const wanted = new Set([BENCHMARK]);
        state.holdings.forEach(h => { wanted.add(h.symbol); const fx = fxFor(h.currency); if (fx.symbol) wanted.add(fx.symbol); });
        const list = [...wanted];
        const got = await Promise.all(list.map(fetchQuote));
        list.forEach((s, i) => { if (got[i]) quotes[s] = got[i]; });
    }

    async function load() {
        if (!userId()) { loaded = true; render(); return; }
        if (!loaded) render();                             // "Loading…" until the portfolio and its prices are in
        try {
            const r = await api('get');
            state = r.portfolio || newState(new Date().toISOString());
            version = r.version || 0; loadError = null;
        } catch (e) { loadError = e.message; }
        // Nothing is shown before the latest prices are in: holdings valued at what was paid looked, for a moment, like a
        // different account value. If the prices are slow, it is shown after 4 seconds anyway and again when they arrive.
        const prices = state ? refreshQuotes() : Promise.resolve();
        await Promise.race([prices, new Promise(done => setTimeout(done, 4000))]);
        loaded = true; redraw();
        await prices; redraw();
    }
    // Redraw without losing what is being typed in the buy row (the autopilot can change the portfolio in the background)
    function redraw() {
        const ids = ['pp-symbol', 'pp-amount', 'pp-qty', 'pp-note'], active = document.activeElement && document.activeElement.id;
        const keep = ids.map(id => [id, document.getElementById(id) ? document.getElementById(id).value : null]);
        render();
        keep.forEach(([id, v]) => { const el = document.getElementById(id); if (el && v) el.value = v; });
        const clear = document.getElementById('pp-clear'), search = document.getElementById('pp-symbol');
        if (clear && search) clear.style.display = search.value ? 'block' : 'none';
        if (ids.includes(active)) { const el = document.getElementById(active); if (el && el.focus) el.focus(); }
    }
    // From practice-autopilot.js: for each holding the autopilot bought, when and at what it will sell it
    let plans = {}, autoRealized = null;
    function setPlans(list, extra) {
        const next = {}, made = extra && typeof extra.realizedUsd === 'number' ? extra.realizedUsd : null;
        (list || []).forEach(p => { next[p.id] = p; });
        if (JSON.stringify(next) === JSON.stringify(plans) && made === autoRealized) return;
        plans = next; autoRealized = made;
        if (loaded && state && !working) redraw();
    }
    // Change a copy, save it, and only then show it: what is on screen is always what is stored
    async function change(mutate) {
        const next = JSON.parse(JSON.stringify(state));
        const result = mutate(next);
        try {
            const r = await api('save', { portfolio: next, expectedVersion: version });
            state = next; version = r.version;
        } catch (e) {
            if (e.conflict) { await load(); throw new Error('This portfolio was changed in another window. It has been reloaded: please try again'); }
            throw e;
        }
        return result;
    }

    async function resolveSymbol(text) {
        const typed = String(text || '').trim().toUpperCase();
        if (!typed) throw new Error('Enter a stock code or name');
        if (/^[A-Z0-9^=.\-]{1,24}$/.test(typed)) { const t = await quoteForTrade(typed); if (t) return { symbol: typed, trade: t }; }
        // not a code the price source knows: look it up as a name
        try {
            const res = await fetch(SEARCH_API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol: typed }) });
            const first = ((await res.json()).suggestions || [])[0];
            if (first && first.symbol) { const t = await quoteForTrade(first.symbol); if (t) return { symbol: first.symbol, trade: t }; }
        } catch (e) {}
        throw new Error('No price found for "' + typed + '". Try the stock code (for example AAPL, BHP.AX, BTC-USD)');
    }

    async function buy(text, amountUsd, note, label, qty) {
        if (!userId()) throw new Error('Sign in to use the practice portfolio');
        if (!loaded || !state) { await load(); if (!state) throw new Error(loadError || 'The practice portfolio could not be loaded'); }
        const { symbol, trade } = await resolveSymbol(text);
        if (qty > 0) amountUsd = qty * trade.q.price * trade.fx;        // bought by quantity: the dollars follow from the latest price
        const holding = await change(s => applyBuy(s, { symbol, label: label || symbol, name: trade.q.name, currency: trade.q.currency, price: trade.q.price,
                                                       fx: trade.fx, spy: trade.spy, amountUsd, note, now: new Date().toISOString() }));
        return { holding, quote: trade.q };
    }
    async function sell(id) {
        const h = state.holdings.find(x => x.id === id);
        if (!h) throw new Error('That holding is no longer in the list');
        const trade = await quoteForTrade(h.symbol);
        if (!trade) throw new Error('No price available for ' + h.label + ' right now, so it cannot be sold');
        return change(s => applySell(s, id, { price: trade.q.price, fx: trade.fx, spy: trade.spy, now: new Date().toISOString() }));
    }

    function render() {
        const el = box();
        if (!el) return;
        const soldBox = document.getElementById('pp-sold');
        if (soldBox && typeof soldBox.open === 'boolean') soldOpen = soldBox.open;
        if (!userId()) { el.innerHTML = '<p style="color: var(--text-secondary);">Sign in to use the practice portfolio.</p>'; return; }
        if (!loaded) { el.innerHTML = '<p style="color: var(--text-secondary);">Loading…</p>'; return; }
        if (!state) { el.innerHTML = `<p style="color: #ef4444;">${esc(loadError || 'The practice portfolio could not be loaded.')}</p><button data-pp="reload" style="${BTN}">Try again</button>`; return; }

        const s = summarize(state, quotes);
        const card = (label, value, sub) => `<div style="flex: 1; min-width: 150px; background: var(--bg-secondary); border-radius: 8px; padding: 12px 14px;"><div style="font-size: 0.8rem; color: var(--text-secondary);">${label}</div><div style="font-size: 1.25rem; font-weight: 700; color: var(--text-primary);">${value}</div><div style="font-size: 0.8rem; color: var(--text-secondary);">${sub || '&nbsp;'}</div></div>`;
        const cell = 'padding: 8px 6px; border-bottom: 1px solid var(--border-color); text-align: right; white-space: nowrap;';
        const left = cell.replace('text-align: right', 'text-align: left');

        const rows = state.holdings.slice().reverse().map(h => {
            const v = valueOf(h, quotes);
            return `<tr>
                <td style="${left}">${h.by === 'ai' ? '<span title="Bought by the AI autopilot">🤖</span> ' : ''}<strong style="color: var(--text-primary);">${esc(h.label)}</strong><div style="font-size: 0.75rem; color: var(--text-secondary); white-space: normal;">${esc(h.name)}${h.note ? ' · ' + esc(h.note) : ''}</div><div style="font-size: 0.75rem; color: var(--text-secondary); white-space: normal; max-width: 420px;">${esc(planLine(h, plans[h.id]))}</div></td>
                <td style="${cell}">${esc(when(h.boughtAt))}</td>
                <td style="${cell}">${money(h.buyPrice, h.currency)}</td>
                <td style="${cell}">${v.priced ? money(v.price, h.currency) : '<span title="No price available right now">–</span>'}</td>
                <td style="${cell}">${usd(h.costUsd)} → ${usd(v.valueUsd)}</td>
                <td style="${cell} font-weight: 600; color: ${v.priced ? colour(v.changePct) : 'var(--text-secondary)'};">${v.priced ? pct(v.changePct) + ' (' + usd(v.gainUsd) + ')' : 'no price'}</td>
                <td style="${cell}"><button data-pp="sell" data-id="${esc(h.id)}" style="${BTN}" ${working ? 'disabled' : ''}>Sell</button></td>
            </tr>`;
        }).join('');

        const closed = state.closed.slice().reverse().map(h => {
            const change = (h.proceedsUsd / h.costUsd - 1) * 100;
            return `<tr><td style="${left}">${h.by === 'ai' ? '<span title="Bought by the AI autopilot">🤖</span> ' : ''}<strong style="color: var(--text-primary);">${esc(h.label)}</strong></td><td style="${cell}">${esc(when(h.boughtAt))} → ${esc(when(h.soldAt))}</td><td style="${cell}">${money(h.buyPrice, h.currency)} → ${money(h.sellPrice, h.currency)}</td><td style="${cell}">${usd(h.costUsd)} → ${usd(h.proceedsUsd)}</td><td style="${cell} font-weight: 600; color: ${colour(change)};">${pct(change)} (${usd(h.proceedsUsd - h.costUsd)})</td><td style="${cell}"><span data-pp="unsold" data-id="${esc(h.id)}" title="Remove this line from the sold list" style="cursor: pointer; font-size: 16px; padding: 0 4px;">×</span></td></tr>`;
        }).join('');
        const sold = soldSummary(state);
        const soldLine = sold.count ? `${sold.count} sold: put in ${usd(sold.cost)}, got back ${usd(sold.proceeds)}, <span style="color: ${colour(sold.gainUsd)}; font-weight: 600;">${pct(sold.gainPct)} (${usd(sold.gainUsd)})</span>.` : '';
        // one total mixes the user's own buys with the autopilot's: say which part is whose
        const split = splitGain(state, quotes, autoRealized), signed = (n) => `<span style="color: ${colour(n)}; font-weight: 600;">${Math.round(n * 100) / 100 >= 0 ? '+' : ''}${usd(n)}</span>`;
        const splitLine = split.any ? `<div style="font-size: 0.85rem; color: var(--text-secondary); margin: -6px 0 14px;">Of the ${signed(split.total)} since the start: your own buys ${signed(split.yours)}; the autopilot ${signed(split.auto)} (${signed(split.autoSold)} on what it has sold, ${signed(split.autoOpen)} on what it still holds). A holding that is not sold yet counts at its latest price.</div>` : '';
        const th = (t, align) => `<th style="padding: 6px; text-align: ${align || 'right'}; font-weight: 600; white-space: nowrap;">${t}</th>`;
        el.innerHTML = `
            <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px;">
                ${card('Account value', usd(s.accountValue), `<span style="color: ${colour(s.gainUsd)}; font-weight: 600;">${pct(s.gainPct)} (${usd(s.gainUsd)})</span> since the start${state.holdings.length || state.closed.length || Math.abs(s.gainUsd) > 0.004 ? `<br>${usd(s.gainUsd - s.openGainUsd)} from what has been sold, ${usd(s.openGainUsd)} on what is still held (at the latest prices)` : ''}`)}
                ${card('Practice cash left', usd(s.cash), 'of ' + usd(state.startingCash))}
                ${card('In holdings', usd(s.holdingsValue), s.openGainPct === null ? 'nothing held yet' : `<span style="color: ${colour(s.openGainPct)}; font-weight: 600;">${pct(s.openGainPct)}</span> on ${usd(s.cost)} put in`)}
                ${card('For comparison', s.marketPct === null ? '–' : s.marketFlat ? 'no change yet' : `<span style="color: ${colour(s.marketPct)};">${pct(s.marketPct)}</span>`, s.marketFlat ? 'the same money in an S&amp;P 500 index fund instead: the US stock market has not traded since you bought (it is closed at weekends), so there is nothing to compare yet' : 'the same money in an S&amp;P 500 index fund instead')}
            </div>
            ${splitLine}
            <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: flex-start; margin-bottom: 6px;">
                <div style="position: relative; flex: 2; min-width: 200px;">
                    <input id="pp-symbol" type="text" autocomplete="off" placeholder="Search for tickers or companies" aria-label="Stock code or company name" style="width: 100%; box-sizing: border-box; padding: 10px 32px 10px 10px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px;">
                    <span id="pp-clear" data-pp="clear" title="Clear" style="display: none; position: absolute; right: 10px; top: 9px; cursor: pointer; color: var(--text-secondary); font-size: 18px; line-height: 1;">×</span>
                    <div id="pp-suggest" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 6px; z-index: 1000; max-height: 240px; overflow-y: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.15);"></div>
                </div>
                <input id="pp-amount" type="number" min="1" step="any" placeholder="Enter $" aria-label="Practice dollars to put in" title="Practice dollars to put in" style="flex: 0 0 110px; padding: 10px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px;">
                <input id="pp-qty" type="number" min="0" step="any" placeholder="or quantity" aria-label="Number of shares or coins" title="Number of shares or coins. Fill in dollars or quantity: the other is worked out from the latest price" style="flex: 0 0 110px; padding: 10px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px;">
                <input id="pp-note" type="text" maxlength="200" placeholder="Why? (optional note)" style="flex: 2; min-width: 160px; padding: 10px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 16px;">
                <button data-pp="buy" style="${BTN} padding: 10px 18px; font-size: 0.95rem;" ${working ? 'disabled' : ''}>${working ? 'Working…' : 'Practice buy'}</button>
            </div>
            <div id="pp-notice" style="min-height: 1.2em; font-size: 0.85rem; margin-bottom: 10px; color: ${notice && notice.bad ? '#ef4444' : 'var(--text-secondary)'};">${notice ? esc(notice.text) : 'Enter practice US dollars or a quantity: the other is worked out from the latest price. A buy is recorded at the latest traded price.'}</div>
            ${state.holdings.length ? `<div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; color: var(--text-secondary);"><tr>${th('Holding', 'left')}${th('Bought')}${th('Price then')}${th('Price now')}${th('Value')}${th('Change')}${th('')}</tr>${rows}</table></div>` : '<p style="color: var(--text-secondary); margin: 6px 0 10px;">Nothing held yet. Enter a stock above, or use “Practice buy” on a line of a screener’s Top 10 Performance (🎯).</p>'}
            ${state.closed.length ? `<details id="pp-sold" ${soldOpen ? 'open' : ''} style="margin-top: 12px;"><summary style="cursor: pointer; color: var(--text-primary);">Sold (${state.closed.length})</summary><div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; color: var(--text-secondary);"><tr>${th('Holding', 'left')}${th('Held')}${th('Price')}${th('Value')}${th('Result')}${th('')}</tr>${closed}</table></div><div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 8px; font-size: 0.8rem; color: var(--text-secondary);"><span>${soldLine}</span><button data-pp="clearsold" style="${BTN2}" title="Empties the sold list. Your practice cash and account value stay as they are" ${working ? 'disabled' : ''}>Clear sold list</button></div></details>` : ''}
            <div style="display: flex; justify-content: flex-end; gap: 8px; flex-wrap: wrap; margin-top: 12px;">
                <button data-pp="refresh" style="${BTN2}" ${working ? 'disabled' : ''}>↻ Refresh prices</button>
                <button data-pp="reset" style="${BTN2}" title="Clears every practice holding and the sold list and puts the fake money back to ${usd(STARTING_CASH)}" ${working ? 'disabled' : ''}>Reset fake money to ${usd(STARTING_CASH)}</button>
            </div>
            <div style="margin-top: 10px; font-size: 0.75rem; color: var(--text-secondary);">
                <span>Fake money for practice: no real trades are placed. Prices can be delayed${s.unpriced ? '; ' + s.unpriced + ' holding(s) have no price right now and are shown at cost' : ''}. Other currencies are converted to US dollars. General information only, not financial advice.</span>
            </div>`;
    }

    function say(text, bad) { notice = text ? { text, bad: !!bad } : null; }
    async function run(task) {
        if (working) return;
        // keep what is typed while the section is redrawn
        const keep = ['pp-symbol', 'pp-amount', 'pp-qty', 'pp-note'].map(id => [id, document.getElementById(id) ? document.getElementById(id).value : null]);
        const restore = () => keep.forEach(([id, v]) => { const el = document.getElementById(id); if (el && v !== null) el.value = v; });
        const showClear = () => { const c = document.getElementById('pp-clear'), b = document.getElementById('pp-symbol'); if (c && b) c.style.display = b.value ? 'block' : 'none'; };
        working = true; render(); restore(); showClear();
        let ok = false;
        try { await task(); ok = true; } catch (e) { say(e.message, true); }
        working = false; render();
        if (!ok) { restore(); showClear(); }
    }

    document.addEventListener('click', (e) => {
        const t = e.target.closest && e.target.closest('[data-pp]');
        if (!t) { const sug = document.getElementById('pp-suggest'); if (sug && !e.target.closest('#pp-suggest, #pp-symbol')) sug.style.display = 'none'; return; }
        const action = t.getAttribute('data-pp');
        if (t.tagName === 'A') e.preventDefault();
        if (action === 'pick') {
            const picked = t.getAttribute('data-symbol');
            document.getElementById('pp-symbol').value = picked;
            document.getElementById('pp-suggest').style.display = 'none';
            // show which company and price that code is, before anything is bought
            const line = document.getElementById('pp-notice');
            if (line) { line.style.color = 'var(--text-secondary)'; line.textContent = 'Looking up ' + picked + '…'; }
            priceFor(picked).then(q => {
                if (!line || document.getElementById('pp-symbol').value !== picked) return;
                line.textContent = q ? `${picked}: ${q.name || 'no name available'}, latest price ${money(q.price, q.currency)}` : `No price found for ${picked}`;
            });
        } else if (action === 'clear') {
            document.getElementById('pp-symbol').value = '';
            document.getElementById('pp-suggest').style.display = 'none';
            t.style.display = 'none';
            document.getElementById('pp-symbol').focus && document.getElementById('pp-symbol').focus();
        } else if (action === 'buy') {
            const text = document.getElementById('pp-symbol').value, note = document.getElementById('pp-note').value.trim();
            const amount = parseFloat(document.getElementById('pp-amount').value), qty = parseFloat((document.getElementById('pp-qty') || {}).value);
            const byQty = qty > 0 && (ppBasis === 'qty' || !(amount > 0));
            if (!byQty && !(amount > 0)) { say('Enter how many practice dollars to put in, or a quantity.', true); render(); document.getElementById('pp-symbol').value = text; return; }
            run(async () => {
                const r = await buy(text, byQty ? 0 : amount, note, undefined, byQty ? qty : 0);
                ppBasis = 'usd'; ppQuote = null;
                say(`Practice buy recorded: ${usd(r.holding.costUsd)} of ${r.holding.label} at ${money(r.holding.buyPrice, r.holding.currency)}.`);
            });
        } else if (action === 'sell') {
            const id = t.getAttribute('data-id'), h = state.holdings.find(x => x.id === id);
            if (!h || !confirm(`Sell ${h.label} at the latest price? This closes the practice holding.`)) return;
            run(async () => { const proceeds = await sell(id); say(`Sold ${h.label} for ${usd(proceeds)} (put in ${usd(h.costUsd)}).`); });
        } else if (action === 'clearsold') {
            const n = state.closed.length;
            if (!n || !confirm(`Clear all ${n} line${n === 1 ? '' : 's'} from the sold list? Your practice cash and account value stay as they are; only the list is emptied.`)) return;
            run(async () => { await change(st => applyClearSold(st, null)); say('Sold list cleared. Practice cash and account value are unchanged.'); });
        } else if (action === 'unsold') {
            const id = t.getAttribute('data-id'), h = state.closed.find(x => x.id === id);
            if (!h) return;
            soldOpen = true;
            run(async () => { await change(st => applyClearSold(st, id)); say(`${h.label} removed from the sold list. Practice cash and account value are unchanged.`); });
        } else if (action === 'refresh') {
            run(async () => { await refreshQuotes(); say('Prices refreshed.'); });
        } else if (action === 'reset') {
            if (!confirm(`Reset the fake money to ${usd(STARTING_CASH)}? This clears every practice holding and the sold list.`)) return;
            run(async () => { await api('reset'); state = newState(new Date().toISOString()); version = 0; quotes = {}; say(`Practice portfolio reset: ${usd(STARTING_CASH)} of fake money to start again.`); });
        } else if (action === 'reload') {
            load();
        }
    });
    // Dollars or quantity: whichever is typed, the other follows from the latest price
    document.addEventListener('input', (e) => {
        if (!e.target || (e.target.id !== 'pp-amount' && e.target.id !== 'pp-qty')) return;
        ppBasis = e.target.id === 'pp-qty' ? 'qty' : 'usd';
        const box = document.getElementById('pp-symbol'), code = box ? box.value.trim().toUpperCase() : '';
        if (ppQuote && ppQuote.symbol === code) fillOther(); else if (code) priceFor(code);
    });
    document.addEventListener('change', (e) => { if (e.target && e.target.id === 'pp-symbol' && e.target.value.trim()) priceFor(e.target.value); });
    // Company-name / ticker lookup, the same service and behaviour as the search box on the home page
    document.addEventListener('input', (e) => {
        if (!e.target || e.target.id !== 'pp-symbol') return;
        clearTimeout(searchTimer);
        const value = e.target.value.trim().toUpperCase(), sug = document.getElementById('pp-suggest'), clear = document.getElementById('pp-clear');
        if (clear) clear.style.display = e.target.value ? 'block' : 'none';
        if (!value || value.includes(',')) { sug.style.display = 'none'; return; }
        searchTimer = setTimeout(async () => {
            if (value.includes('.')) { sug.style.display = 'none'; return; }       // a full code such as BHP.AX needs no lookup
            const still = () => { const box = document.getElementById('pp-symbol'); return box && box.value.trim().toUpperCase() === value; };
            const row = 'padding: 10px; border-bottom: 1px solid var(--border-color); color: var(--text-primary);';
            sug.innerHTML = `<div style="${row} color: var(--text-secondary);">Checking exchanges...</div>`;
            sug.style.display = 'block';
            try {
                const res = await fetch(SEARCH_API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol: value }) });
                const list = ((await res.json()).suggestions || []).filter(x => /^[A-Z0-9^=.\-]{1,24}$/.test(x.symbol || ''));
                if (!still()) return;
                sug.innerHTML = list.length
                    ? list.map(x => `<div data-pp="pick" data-symbol="${esc(x.symbol)}" style="${row} cursor: pointer;" onmouseover="this.style.background='rgba(0, 123, 255, 0.25)'" onmouseout="this.style.background='transparent'"><strong>${esc(x.symbol)}</strong> - ${esc(x.name)}</div>`).join('')
                    : `<div style="${row} color: var(--text-secondary);">No matches found</div>`;
            } catch (err) {
                if (still()) sug.innerHTML = `<div style="${row} color: var(--text-secondary);">Error checking symbol</div>`;
            }
        }, 500);
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.target && ['pp-symbol', 'pp-amount', 'pp-qty', 'pp-note'].includes(e.target.id)) { const b = document.querySelector('[data-pp="buy"]'); if (b) b.click(); }
    });

    // "Practice buy" on a line of the Top 10 Performance popup
    window.practiceBuyFromTop10 = async function (button, lookup, label) {
        if (button.disabled) return;
        button.disabled = true; const before = button.textContent; button.textContent = 'Adding…';
        try {
            const r = await buy(lookup, DEFAULT_AMOUNT, 'From a screener top 10', label);
            button.textContent = '✓ Added ' + usd(r.holding.costUsd);
            say(`Practice buy recorded: ${usd(r.holding.costUsd)} of ${r.holding.label} at ${money(r.holding.buyPrice, r.holding.currency)}.`);
            render();
        } catch (e) {
            button.disabled = false; button.textContent = before; alert(e.message);
        }
    };

    // for practice-autopilot.js: show what the autopilot has just bought or sold
    window.practicePortfolio = { reload: load, setPlans };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load); else load();
})();
