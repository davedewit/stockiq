// Practice portfolio (dashboard): practice buys with fake money, then monitored against live prices.
// No real trades are placed anywhere. Each buy is one line; selling closes that line at the current price.
// Stored per user by the stockiq-paper-portfolio Lambda; the sums are done here.
(function () {
    const API = 'https://5c7pt7qurshld4cwaqyopfxcei0cuurj.lambda-url.us-east-1.on.aws/';
    const PRICE_API = 'https://dohdeb4vpu67fa2tq3ax56ls4i0rshvm.lambda-url.us-east-1.on.aws/?symbol=';
    const SEARCH_API = 'https://3oaokynmssanpzz7bwomt7ft6i0qrwhk.lambda-url.us-east-1.on.aws/';
    const STARTING_CASH = 100000;
    // A trading cost is taken off every practice buy and every sale, so that a result is not flattered: real trading pays fees
    // and the gap between buying and selling prices. 0.1% each way is a typical figure for large shares; small coins cost more.
    // The same figure is in the autopilot function (TRADE_COST): keep the two in step.
    const TRADE_COST_PCT = (typeof practiceTradeCostPct === 'number') ? practiceTradeCostPct : 0.1;      // eslint-disable-line no-undef
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
            qty: amount * (1 - TRADE_COST_PCT / 100) / (b.price * b.fx), buyPrice: b.price, buyFx: b.fx, costUsd: amount,      // the cost of buying comes out of what is put in
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
        const proceeds = Math.round(h.qty * s.price * s.fx * (1 - TRADE_COST_PCT / 100) * 100) / 100;      // less the cost of selling
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
    // A result in words, so that a mix of gains and losses cannot be misread: "up $144.12", "down $202.60", "level"
    function moved(n) { n = Math.round(n * 100) / 100 || 0; return n === 0 ? 'level' : (n > 0 ? 'up ' : 'down ') + usd(Math.abs(n)); }
    // On the page a result is an arrow and an amount, green up and red down, as a broker's screen shows it; the words stay as
    // the label a screen reader says (and in `moved`, which the AI chat's summary uses).
    function tone(n) { const r = Math.round(n * 100) / 100 || 0; return r > 0 ? '#16a34a' : r < 0 ? '#ef4444' : 'var(--text-secondary)'; }
    function arrow(n) { const r = Math.round(n * 100) / 100 || 0; return r > 0 ? '▲' : r < 0 ? '▼' : '–'; }
    function movedHtml(n, percent) {
        const r = Math.round(n * 100) / 100 || 0, p = (percent === null || percent === undefined || !isFinite(percent)) ? '' : ' (' + Math.abs(percent).toFixed(2) + '%)';
        return `<span class="pp-delta" role="img" aria-label="${moved(r)}${p}" style="color: ${tone(r)}; font-weight: 600; white-space: nowrap;">${arrow(r)} ${usd(Math.abs(r))}${p}</span>`;
    }
    function pctHtml(percent, amount) {      // a change in percent first, the dollars in brackets
        const r = Math.round(percent * 100) / 100 || 0, a = (amount === null || amount === undefined) ? '' : ' (' + usd(Math.abs(amount)) + ')';
        return `<span class="pp-delta" role="img" aria-label="${r === 0 ? 'level' : (r > 0 ? 'up ' : 'down ') + Math.abs(r).toFixed(2) + '%'}${a}" style="color: ${tone(r)}; font-weight: 600; white-space: nowrap;">${arrow(r)} ${Math.abs(r).toFixed(2)}%${a}</span>`;
    }
    function day(iso) { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }); }
    function when(iso) { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }); }
    // Whose holding it is and what will happen to it. `plan` comes from the autopilot (practice-autopilot.js) for the
    // holdings it bought: it sells those by itself. Everything else stays until the user sells it.
    function planLine(h, plan) {
        if (h.by !== 'ai') return 'Bought by you: it stays until you sell it.';
        if (!plan) return '🤖 Bought by the autopilot.';
        if (!plan.auto) return '🤖 Bought by the autopilot, which is switched off: it stays until you sell it or switch the autopilot back on.';
        const up = (n) => (n >= 0 ? '+' : '') + n;
        // Written so that the point where the stop starts cannot be read as a selling price: rising is never a reason to sell
        const stop = plan.mode === 'off' ? ''
            : plan.mode === 'full' && typeof plan.floor === 'number' && !(plan.peak >= plan.arm) ? ` Its trailing stop is at ${up(plan.floor)}% now and follows the price up.`
            : typeof plan.floor === 'number' ? ` It has been up enough for a stop to follow it: it is sold if it falls back to ${up(plan.floor)}%.`
            : ` While it rises it is kept; once it has been up ${plan.arm}% a stop follows it up, and it is sold only if it then falls back.`;
        // Nothing is bought or sold in a closed market (a weekend, a night): say so, and when it opens
        const shut = plan.closed ? ` The ${plan.market} market is closed now, so nothing happens to it until it opens${plan.opens ? ` (around ${when(plan.opens)})` : ''}.` : '';
        return `🤖 Autopilot: it sells this by itself, at the check-in around ${when(plan.sellBy)} at the latest, sooner if it falls to ${plan.stop}% or reaches +${plan.take}%.` + stop
            + (plan.trial ? ' Part of a trial of one of its own rules.' : '')
            + ' The AI model also reviews it at every check-in and may sell it earlier.' + shut;
    }

    // ---------------------------------------------------------------- the account over time (no page, no network)
    // The daily prices that come with a quote (the price source answers with a month of them) as [time in ms, price] at each
    // session's close, ending with the latest price. A market that trades every day (coins, exchange rates) closes a day
    // after its bar starts, a stock exchange about six and a half hours after. The bar of a session still running, or one
    // sent a second time after the close, is left out: the latest price stands for it.
    function seriesOf(result, symbol) {
        const ts = (result && result.timestamp) || [], meta = (result && result.meta) || {};
        const close = ((((result || {}).indicators || {}).quote || [])[0] || {}).close || [];
        const always = /-USD$|=X$/.test(String(symbol || '')), last = (meta.regularMarketTime || 0) * 1000, out = [];
        for (let i = 0; i < ts.length; i++) {
            if (!(close[i] > 0)) continue;
            const end = Math.min(ts[i] * 1000 + (always ? 86400000 : 23400000), i + 1 < ts.length ? ts[i + 1] * 1000 : Infinity);
            if (last && end >= last) break;
            out.push([end, close[i]]);
        }
        if (last && meta.regularMarketPrice > 0) out.push([last, meta.regularMarketPrice]);
        return out;
    }
    // A value at time t from known points [time, value], along straight lines between them; null before the first
    function valueAt(knots, t) {
        if (!knots.length || t < knots[0][0]) return null;
        let lo = 0, hi = knots.length - 1;
        if (t >= knots[hi][0]) return knots[hi][1];
        while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (knots[mid][0] <= t) lo = mid; else hi = mid; }
        return knots[lo][1] + (knots[hi][1] - knots[lo][1]) * (t - knots[lo][0]) / ((knots[hi][0] - knots[lo][0]) || 1);
    }
    // The account at every moment from `from` to `now`, worked out from what is in it. A holding still held is valued at
    // its daily prices and at its latest price now. One that was sold is a straight line from what was put in to what came
    // back: exact at both ends, a guess in between. Results of sales no longer in the list (the list was cleared, or is
    // over its limit) have no dates left: they are counted from the beginning, and `undated` says how much that is.
    // Each point: t, value (the account), all (its change since the start), ai (the autopilot's part), own (the user's).
    function valueSeries(state, quotes, now, autoRealized, from) {
        const ms = (x) => typeof x === 'number' ? x : Date.parse(x);
        const start = ms(state.createdAt) || now, first = Math.min(now, Math.max(start, from || start)), lots = [];
        const rates = (currency) => { const fx = fxFor(currency), q = fx.symbol && quotes[fx.symbol]; return !fx.symbol ? null : ((q && q.series) || []).map(([t, p]) => [t, fxRate(fx, p)]).filter(k => k[1] > 0); };
        const paid = (h) => h.qty > 0 && h.buyPrice > 0 && h.buyFx > 0 ? h.qty * h.buyPrice * h.buyFx : h.costUsd;      // its worth the moment after buying: what was put in less the cost of buying
        state.holdings.forEach(h => {
            const bought = ms(h.boughtAt), q = quotes[h.symbol], fx = rates(h.currency), knots = [[bought, paid(h)]];
            ((q && q.series) || []).forEach(([t, p]) => {
                if (t <= bought || t >= now) return;
                const rate = fx === null ? 1 : (valueAt(fx, t) || h.buyFx);
                if (rate > 0) knots.push([t, h.qty * p * rate]);
            });
            knots.push([Math.max(now, bought + 1), valueOf(h, quotes).valueUsd]);
            lots.push({ ai: h.by === 'ai', cost: h.costUsd, from: bought, knots });
        });
        state.closed.forEach(h => {
            const bought = ms(h.boughtAt);
            lots.push({ ai: h.by === 'ai', cost: h.costUsd, from: bought, knots: [[bought, paid(h)], [Math.max(ms(h.soldAt), bought + 1), h.proceedsUsd]] });
        });
        const gain = (lot, t) => t < lot.from ? 0 : valueAt(lot.knots, t) - lot.cost;
        const split = splitGain(state, quotes, autoRealized);
        const undated = split.total - lots.reduce((sum, l) => sum + gain(l, now), 0);
        const undatedAi = split.auto - lots.reduce((sum, l) => sum + (l.ai ? gain(l, now) : 0), 0);
        const times = new Set([first, now]);
        lots.forEach(l => l.knots.forEach(k => { if (k[0] > first && k[0] < now) times.add(k[0]); }));
        for (let i = 1; i < 120; i++) times.add(Math.round(first + (now - first) * i / 120));
        const points = [...times].sort((a, b) => a - b).map(t => {
            let all = undated, ai = undatedAi;
            lots.forEach(l => { const g = gain(l, t); all += g; if (l.ai) ai += g; });
            return { t, value: state.startingCash + all, all, ai, own: all - ai };
        });
        return { start, from: first, now, points, undated, undatedAi, lots: lots.length, anyAi: split.any };
    }
    // Round numbers for an axis that covers lo..hi in about `count` steps
    function axisTicks(lo, hi, count) {
        const span = (hi - lo) || 1, raw = span / Math.max(1, count), mag = Math.pow(10, Math.floor(Math.log10(raw))), unit = raw / mag;
        const step = (unit <= 1 ? 1 : unit <= 2 ? 2 : unit <= 5 ? 5 : 10) * mag, out = [];
        for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(Math.round(v / step) * step);
        return { step, ticks: out };
    }
    // The graph as an SVG picture. key: 'value' (the account, against the amount it started with), 'own' or 'ai' (that part's
    // gain or loss, against zero). Returns the picture and where each point sits, for the pointer to read values off.
    function chartSvg(series, key, width, height) {
        const pts = series.points, base = key === 'value' ? pts.length ? pts[0].value - pts[0].all : 0 : 0;
        const W = Math.max(260, Math.round(width || 720)), H = Math.round(height || 220), small = W < 480;
        const m = { l: small ? 54 : 70, r: 14, t: 12, b: 24 }, w = W - m.l - m.r, h = H - m.t - m.b;
        const vals = pts.map(p => p[key]).concat([base]);
        let lo = Math.min(...vals), hi = Math.max(...vals);
        const pad = Math.max((hi - lo) * 0.12, Math.abs(base) * 0.0002, 1); lo -= pad; hi += pad;
        const t0 = series.from, t1 = Math.max(series.now, t0 + 1);
        const x = (t) => m.l + w * (t - t0) / (t1 - t0), y = (v) => m.t + h * (1 - (v - lo) / (hi - lo));
        const cents = hi - lo < 20;
        const label = (v) => key === 'value' ? '$' + v.toLocaleString('en-US', { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 })
            : (Math.abs(v) < 0.005 ? '$0' : (v > 0 ? '+$' : '-$') + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 }));
        const days = (t1 - t0) / 86400000;
        const stamp = (t) => { const d = new Date(t); return days <= 3 ? d.toLocaleString(undefined, { weekday: 'short', hour: '2-digit', minute: '2-digit' }) : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }); };
        let out = `<svg id="pp-chart-svg" class="pp-chart-svg" role="img" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-label="${esc(key === 'value' ? 'Account value over time' : key === 'ai' ? 'The autopilot’s result over time' : 'The result of your own buys over time')}: from ${esc(label(pts[0][key]))} to ${esc(label(pts[pts.length - 1][key]))}">`;
        axisTicks(lo, hi, small ? 3 : 4).ticks.forEach(v => {
            out += `<line class="pp-grid" x1="${m.l}" x2="${W - m.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="pp-axis" x="${m.l - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${esc(label(v))}</text>`;
        });
        const n = small ? 3 : 5;
        for (let i = 0; i <= n; i++) {
            const t = t0 + (t1 - t0) * i / n;
            out += `<text class="pp-axis" x="${x(t).toFixed(1)}" y="${H - 6}" text-anchor="${i === 0 ? 'start' : i === n ? 'end' : 'middle'}">${esc(stamp(t))}</text>`;
        }
        // where it started: the line everything is measured against
        out += `<line class="pp-base" x1="${m.l}" x2="${W - m.r}" y1="${y(base).toFixed(1)}" y2="${y(base).toFixed(1)}"/>`;
        const placed = pts.map(p => ({ t: p.t, v: p[key], all: p.all, x: +x(p.t).toFixed(1), y: +y(p[key]).toFixed(1) }));
        out += `<path class="pp-line" d="${placed.map((p, i) => (i ? 'L' : 'M') + p.x + ' ' + p.y).join('')}"/>`;
        const end = placed[placed.length - 1];
        out += `<line id="pp-cross" class="pp-cross" x1="${end.x}" x2="${end.x}" y1="${m.t}" y2="${m.t + h}" style="display:none"/>`;
        out += `<circle id="pp-dot" class="pp-dot" cx="${end.x}" cy="${end.y}" r="4"/></svg>`;
        return { svg: out, placed, base, width: W };
    }

    const pure = { newState, fxFor, fxRate, versusMarket, applyBuy, applySell, applyClearSold, soldSummary, valueOf, summarize, splitGain, planLine, moved, movedHtml, usd, pct, money, esc, TRADE_COST_PCT, STARTING_CASH, DEFAULT_AMOUNT, seriesOf, valueAt, valueSeries, axisTicks, chartSvg };
    if (typeof module !== 'undefined' && module.exports) module.exports = pure;
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    // ---------------------------------------------------------------- page
    // On a phone a table of seven columns cannot be read: each holding becomes a card, every figure on its own labelled line.
    // (The cells carry inline styles, hence the !important.)
    const PP_CSS = `
        #practice-portfolio { --pp-line: #2563eb; }
        [data-theme="dark"] #practice-portfolio { --pp-line: #3b82f6; }
        #practice-portfolio .pp-chart { border: 1px solid var(--border-color); border-radius: 10px; padding: 12px 14px 8px; margin-bottom: 14px; background: var(--bg-primary); }
        #practice-portfolio .pp-chart-head { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: baseline; justify-content: space-between; margin-bottom: 4px; }
        #practice-portfolio .pp-chart-title { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-secondary); }
        #practice-portfolio .pp-chart-read { font-size: 0.9rem; color: var(--text-primary); font-variant-numeric: tabular-nums; min-height: 1.3em; }
        #practice-portfolio .pp-chart-read .pp-chart-when { color: var(--text-secondary); margin-right: 8px; }
        #practice-portfolio .pp-chart-tabs { display: flex; flex-wrap: wrap; gap: 6px; }
        #practice-portfolio .pp-chart-tabs button { background: none; color: var(--text-secondary); border: 1px solid var(--border-color); border-radius: 999px; padding: 3px 11px; font-size: 0.78rem; cursor: pointer; }
        #practice-portfolio .pp-chart-tabs button[aria-pressed="true"] { color: var(--text-primary); border-color: var(--text-secondary); font-weight: 600; }
        #practice-portfolio .pp-chart-svg { display: block; width: 100%; height: auto; touch-action: pan-y; cursor: crosshair; }
        #practice-portfolio .pp-grid { stroke: var(--border-color); stroke-width: 1; }
        #practice-portfolio .pp-base { stroke: var(--text-secondary); stroke-width: 1; stroke-dasharray: 4 4; opacity: 0.7; }
        #practice-portfolio .pp-axis { fill: var(--text-secondary); font-size: 11px; font-variant-numeric: tabular-nums; }
        #practice-portfolio .pp-line { fill: none; stroke: var(--pp-line); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
        #practice-portfolio .pp-cross { stroke: var(--text-secondary); stroke-width: 1; }
        #practice-portfolio .pp-dot { fill: var(--pp-line); stroke: var(--bg-primary); stroke-width: 2; }
        #practice-portfolio .pp-chart-note { font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px; }
        #practice-portfolio .pp-chart details { font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px; }
        #practice-portfolio .pp-chart table { border-collapse: collapse; margin-top: 6px; font-variant-numeric: tabular-nums; }
        #practice-portfolio .pp-chart td, #practice-portfolio .pp-chart th { padding: 2px 14px 2px 0; text-align: right; font-weight: normal; }
        #practice-portfolio .pp-chart td:first-child, #practice-portfolio .pp-chart th:first-child { text-align: left; }
        @media (max-width: 640px) {
            #practice-portfolio .pp-chart { padding: 10px 10px 6px; }
            #practice-portfolio .pp-chart .pp-fig-part { display: none; }
            #practice-portfolio .pp-chart td, #practice-portfolio .pp-chart th { padding-right: 10px; white-space: nowrap; }
        }
        #practice-portfolio { font-variant-numeric: tabular-nums; }
        #practice-portfolio .pp-card { flex: 1; min-width: 150px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 10px; padding: 12px 14px; border-top: 3px solid transparent; }
        #practice-portfolio .pp-card.up { border-top-color: #16a34a; } #practice-portfolio .pp-card.down { border-top-color: #ef4444; }
        #practice-portfolio .pp-card-label { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: var(--text-secondary); }
        #practice-portfolio .pp-card-value { font-size: 1.45rem; font-weight: 700; color: var(--text-primary); line-height: 1.3; }
        #practice-portfolio .pp-card-sub { font-size: 0.8rem; color: var(--text-secondary); line-height: 1.5; }
        #practice-portfolio .pp-split { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 18px; font-size: 0.85rem; color: var(--text-secondary); margin: -4px 0 14px; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 8px; }
        #practice-portfolio .pp-split-head { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
        #practice-portfolio .pp-split-item > span:first-child { color: var(--text-primary); font-weight: 600; margin-right: 4px; }
        #practice-portfolio .pp-split-sub { font-size: 0.8rem; margin-left: 4px; }
        #practice-portfolio table.pp-stack tr.pp-head th { font-size: 0.72rem; letter-spacing: 0.05em; text-transform: uppercase; color: var(--text-secondary); border-bottom: 2px solid var(--border-color); }
        @media (min-width: 641px) { #practice-portfolio table.pp-stack tr:not(.pp-head):hover td { background: rgba(128, 128, 128, 0.07); } }
        @media (max-width: 640px) {
            #practice-portfolio table.pp-stack, #practice-portfolio table.pp-stack tbody, #practice-portfolio table.pp-stack tr, #practice-portfolio table.pp-stack td { display: block !important; width: auto !important; box-sizing: border-box; }
            #practice-portfolio table.pp-stack tr.pp-head { display: none !important; }
            #practice-portfolio table.pp-stack tr { border: 1px solid var(--border-color) !important; border-radius: 10px; padding: 10px 12px; margin: 0 0 10px; }
            #practice-portfolio table.pp-stack td { text-align: left !important; white-space: normal !important; padding: 3px 0 !important; border: 0 !important; }
            #practice-portfolio table.pp-stack td[data-label] { display: flex !important; justify-content: space-between; gap: 12px; }
            #practice-portfolio table.pp-stack td[data-label]::before { content: attr(data-label); color: var(--text-secondary); font-weight: 400; flex: none; }
            #practice-portfolio table.pp-stack td.pp-name { padding-bottom: 6px !important; margin-bottom: 4px; border-bottom: 1px solid var(--border-color) !important; }
            #practice-portfolio table.pp-stack td.pp-act { text-align: right !important; padding-top: 8px !important; }
            #practice-portfolio table.pp-stack td.pp-act button { width: 100%; padding: 10px 12px !important; font-size: 0.95rem !important; }
            #practice-portfolio .pp-find { flex: 1 1 100% !important; }
            #practice-portfolio #pp-amount, #practice-portfolio #pp-qty { flex: 1 1 0 !important; min-width: 0; box-sizing: border-box; }
            #practice-portfolio #pp-note { flex: 1 1 100% !important; min-width: 0 !important; box-sizing: border-box; }
            #practice-portfolio [data-pp="buy"] { flex: 1 1 100%; padding: 12px 18px !important; }
        }`;
    function ensureStyle() {
        if (!document.head || !document.createElement || document.getElementById('pp-style')) return;
        const style = document.createElement('style'); style.id = 'pp-style'; style.textContent = PP_CSS; document.head.appendChild(style);
    }
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
            const result = (await res.json())?.chart?.result?.[0], meta = result && result.meta;
            if (!meta || !(meta.regularMarketPrice > 0)) return null;
            // series: the month of daily prices that comes with every quote, for the graph of the account over time
            return { price: meta.regularMarketPrice, currency: meta.currency || 'USD', name: meta.longName || meta.shortName || '', time: meta.regularMarketTime || 0, series: seriesOf(result, symbol) };
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
        ensureStyle();
        const el = box();
        if (!el) return;
        const soldBox = document.getElementById('pp-sold');
        if (soldBox && typeof soldBox.open === 'boolean') soldOpen = soldBox.open;
        if (!userId()) { el.innerHTML = '<p style="color: var(--text-secondary);">Sign in to use the practice portfolio.</p>'; return; }
        if (!loaded) { el.innerHTML = '<p style="color: var(--text-secondary);">Loading…</p>'; return; }
        if (!state) { el.innerHTML = `<p style="color: #ef4444;">${esc(loadError || 'The practice portfolio could not be loaded.')}</p><button data-pp="reload" style="${BTN}">Try again</button>`; return; }

        const s = summarize(state, quotes);
        const card = (label, value, sub, way) => `<div class="pp-card${way > 0.004 ? ' up' : way < -0.004 ? ' down' : ''}"><div class="pp-card-label">${label}</div><div class="pp-card-value">${value}</div><div class="pp-card-sub">${sub || '&nbsp;'}</div></div>`;
        const cell = 'padding: 8px 6px; border-bottom: 1px solid var(--border-color); text-align: right; white-space: nowrap;';
        const left = cell.replace('text-align: right', 'text-align: left');

        const rows = state.holdings.slice().reverse().map(h => {
            const v = valueOf(h, quotes);
            return `<tr>
                <td class="pp-name" style="${left}">${h.by === 'ai' ? '<span title="Bought by the AI autopilot">🤖</span> ' : ''}<strong style="color: var(--text-primary);">${esc(h.label)}</strong><div style="font-size: 0.75rem; color: var(--text-secondary); white-space: normal;">${esc(h.name)}${h.note ? ' · ' + esc(h.note) : ''}</div><div style="font-size: 0.75rem; color: var(--text-secondary); white-space: normal; max-width: 420px;">${esc(planLine(h, plans[h.id]))}</div></td>
                <td data-label="Bought" style="${cell}">${esc(when(h.boughtAt))}</td>
                <td data-label="Price then" style="${cell}">${money(h.buyPrice, h.currency)}</td>
                <td data-label="Price now" style="${cell}">${v.priced ? money(v.price, h.currency) : '<span title="No price available right now">–</span>'}</td>
                <td data-label="Value" style="${cell}">${usd(h.costUsd)} → ${usd(v.valueUsd)}</td>
                <td data-label="Change" style="${cell}">${v.priced ? pctHtml(v.changePct, v.gainUsd) : '<span style="color: var(--text-secondary);">no price</span>'}</td>
                <td class="pp-act" style="${cell}"><button data-pp="sell" data-id="${esc(h.id)}" style="${BTN}" ${working ? 'disabled' : ''}>Sell</button></td>
            </tr>`;
        }).join('');

        const closed = state.closed.slice().reverse().map(h => {
            const change = (h.proceedsUsd / h.costUsd - 1) * 100;
            return `<tr><td class="pp-name" style="${left}">${h.by === 'ai' ? '<span title="Bought by the AI autopilot">🤖</span> ' : ''}<strong style="color: var(--text-primary);">${esc(h.label)}</strong></td><td data-label="Held" style="${cell}">${esc(when(h.boughtAt))} → ${esc(when(h.soldAt))}</td><td data-label="Price" style="${cell}">${money(h.buyPrice, h.currency)} → ${money(h.sellPrice, h.currency)}</td><td data-label="Value" style="${cell}">${usd(h.costUsd)} → ${usd(h.proceedsUsd)}</td><td data-label="Result" style="${cell}">${pctHtml(change, h.proceedsUsd - h.costUsd)}</td><td class="pp-act" style="${cell}"><span data-pp="unsold" data-id="${esc(h.id)}" title="Remove this line from the sold list" style="cursor: pointer; font-size: 16px; padding: 0 4px;">×</span></td></tr>`;
        }).join('');
        const sold = soldSummary(state);
        const soldLine = sold.count ? `${sold.count} sold: put in ${usd(sold.cost)}, got back ${usd(sold.proceeds)}: ${movedHtml(sold.gainUsd, sold.gainPct)}.` : '';
        // one total mixes the user's own buys with the autopilot's: say which part is whose
        const split = splitGain(state, quotes, autoRealized);
        const splitLine = split.any ? `<div class="pp-split" title="The two add up to the account's change since the start. A holding that is not sold yet counts at its latest price."><span class="pp-split-head">Whose result is whose</span><span class="pp-split-item"><span>Your own buys</span> ${movedHtml(split.yours)}</span><span class="pp-split-item"><span>🤖 AI autopilot</span> ${movedHtml(split.auto)} <span class="pp-split-sub">sold ${movedHtml(split.autoSold)} · still held ${movedHtml(split.autoOpen)}</span></span></div>` : '';
        const th = (t, align) => `<th style="padding: 6px; text-align: ${align || 'right'}; font-weight: 600; white-space: nowrap;">${t}</th>`;
        el.innerHTML = `
            <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px;">
                ${card('Account value', usd(s.accountValue), `${movedHtml(s.gainUsd, s.gainPct)} since the start${state.holdings.length || state.closed.length || Math.abs(s.gainUsd) > 0.004 ? `<br>Sold ${movedHtml(s.gainUsd - s.openGainUsd)} · Still held ${movedHtml(s.openGainUsd)}` : ''}`, s.gainUsd)}
                ${card('Practice cash left', usd(s.cash), 'of ' + usd(state.startingCash))}
                ${card('In holdings', usd(s.holdingsValue), s.openGainPct === null ? 'nothing held yet' : `${movedHtml(s.openGainUsd, s.openGainPct)} on ${usd(s.cost)} put in`)}
                ${card('For comparison', s.marketPct === null ? '–' : s.marketFlat ? 'no change yet' : pctHtml(s.marketPct), s.marketFlat ? 'the same money in an S&amp;P 500 index fund instead: the US stock market has not traded since you bought (it is closed at weekends), so there is nothing to compare yet' : 'the same money in an S&amp;P 500 index fund instead')}
            </div>
            ${splitLine}
            <div id="pp-chart">${chartHtml()}</div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: flex-start; margin-bottom: 6px;">
                <div class="pp-find" style="position: relative; flex: 2; min-width: 200px;">
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
            ${state.holdings.length ? `<div style="overflow-x: auto;"><table class="pp-stack" style="width: 100%; border-collapse: collapse; font-size: 0.85rem; color: var(--text-secondary);"><tr class="pp-head">${th('Holding', 'left')}${th('Bought')}${th('Price then')}${th('Price now')}${th('Value')}${th('Change')}${th('')}</tr>${rows}</table></div>` : '<p style="color: var(--text-secondary); margin: 6px 0 10px;">Nothing held yet. Enter a stock above, or use “Practice buy” on a line of a screener’s Top 10 Performance (🎯).</p>'}
            ${state.closed.length ? `<details id="pp-sold" ${soldOpen ? 'open' : ''} style="margin-top: 12px;"><summary style="cursor: pointer; color: var(--text-primary);">Sold (${state.closed.length})</summary><div style="overflow-x: auto;"><table class="pp-stack" style="width: 100%; border-collapse: collapse; font-size: 0.85rem; color: var(--text-secondary);"><tr class="pp-head">${th('Holding', 'left')}${th('Held')}${th('Price')}${th('Value')}${th('Result')}${th('')}</tr>${closed}</table></div><div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 8px; font-size: 0.8rem; color: var(--text-secondary);"><span>${soldLine}</span><button data-pp="clearsold" style="${BTN2}" title="Empties the sold list. Your practice cash and account value stay as they are" ${working ? 'disabled' : ''}>Clear sold list</button></div></details>` : ''}
            <div style="display: flex; justify-content: flex-end; gap: 8px; flex-wrap: wrap; margin-top: 12px;">
                <button data-pp="refresh" style="${BTN2}" ${working ? 'disabled' : ''}>↻ Refresh prices</button>
                <button data-pp="reset" style="${BTN2}" title="Clears every practice holding and the sold list and puts the fake money back to ${usd(STARTING_CASH)}" ${working ? 'disabled' : ''}>Reset fake money to ${usd(STARTING_CASH)}</button>
            </div>
            <div style="margin-top: 10px; font-size: 0.75rem; color: var(--text-secondary);">
                <span>Fake money for practice: no real trades are placed. ${TRADE_COST_PCT ? `A trading cost of ${TRADE_COST_PCT}% is taken off each practice buy and each sale (a typical figure; real costs vary), so a holding starts a little below what was put in. ` : ''}Prices can be delayed${s.unpriced ? '; ' + s.unpriced + ' holding(s) have no price right now and are shown at cost' : ''}. Other currencies are converted to US dollars. General information only, not financial advice.</span>
            </div>`;
    }

    function say(text, bad) { notice = text ? { text, bad: !!bad } : null; }
    // ---------------------------------------------------------------- the graph of the account over time
    const CHART_RANGES = { all: ['All', 0], month: ['1 month', 30 * 86400000], week: ['1 week', 7 * 86400000] };
    let chartKey = 'value', chartRange = 'all';      // which line (the account, the user's own buys, the autopilot's) and how far back
    let chartNow = null;                             // where each point sits in the picture on show: the pointer reads values off it
    try {
        const k = localStorage.getItem('stockiqPracticeChartKey'), r = localStorage.getItem('stockiqPracticeChartRange');
        if (['value', 'own', 'ai'].includes(k)) chartKey = k;
        if (CHART_RANGES[r]) chartRange = r;
    } catch (e) { /* a private window: the choice is simply not remembered */ }
    // The line above the picture: a moment, the figure then, and the change
    function chartRead(point) {
        const moment = `<span class="pp-chart-when">${esc(new Date(point.t).toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }))}</span>`;
        return chartKey === 'value' ? `${moment}<strong>${usd(point.v)}</strong> &nbsp;${movedHtml(point.all, state ? point.all / state.startingCash * 100 : null)} since the start` : `${moment}${movedHtml(point.v)}`;
    }
    function chartHtml() {
        if (!state || !(state.holdings.length || state.closed.length)) return '';
        const now = Date.now(), age = now - (Date.parse(state.createdAt) || now);
        const ranges = Object.keys(CHART_RANGES).filter(r => r === 'all' || age > CHART_RANGES[r][1] * 1.15);
        if (!ranges.includes(chartRange)) chartRange = 'all';
        const series = valueSeries(state, quotes, now, autoRealized, chartRange === 'all' ? 0 : now - CHART_RANGES[chartRange][1]);
        if (!series.anyAi) chartKey = 'value';
        const el = box(), width = Math.min(1100, Math.max(260, ((el && el.clientWidth) || 750) - 30));
        const picture = chartSvg(series, chartKey, width, width < 480 ? 180 : 220);
        chartNow = { placed: picture.placed, width: picture.width };
        const tab = (kind, id, text, on) => `<button type="button" data-pp="chart-${kind}" data-id="${id}" aria-pressed="${on}">${text}</button>`;
        const kinds = series.anyAi ? [['value', 'Account'], ['own', 'Your own buys'], ['ai', '🤖 AI autopilot']] : [];
        const title = chartKey === 'value' ? 'Account value over time' : chartKey === 'ai' ? 'The autopilot’s result over time' : 'Your own buys: result over time';
        // the figures behind the picture, a line a day (the last moment of each day)
        const perDay = {};
        series.points.forEach(point => { perDay[new Date(point.t).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })] = point; });
        const rows = Object.entries(perDay).slice(-60).reverse().map(([day, point]) => `<tr><td>${esc(day)}</td><td>${usd(point.value)}</td><td>${movedHtml(point.all)}</td>${series.anyAi ? `<td class="pp-fig-part">${movedHtml(point.own)}</td><td class="pp-fig-part">${movedHtml(point.ai)}</td>` : ''}</tr>`).join('');
        const undated = Math.abs(series.undated) > 0.5 ? ` The result of sold holdings that are no longer in the list (${moved(series.undated)}) has no dates left, so it is counted from the start.` : '';
        return `<div class="pp-chart">
            <div class="pp-chart-head"><span class="pp-chart-title">${title}</span><span class="pp-chart-tabs">${kinds.map(([id, text]) => tab('key', id, text, chartKey === id)).join('')}${ranges.length > 1 ? ranges.map(r => tab('range', r, CHART_RANGES[r][0], chartRange === r)).join('') : ''}</span></div>
            <div class="pp-chart-read" id="pp-chart-read">${chartRead(picture.placed[picture.placed.length - 1])}</div>
            ${picture.svg}
            <div class="pp-chart-note">Fake money. Dashed line: ${chartKey === 'value' ? 'the ' + usd(state.startingCash) + ' it started with' : 'no gain or loss'}. A holding still held is valued at its daily prices and its latest price now; one that was sold is drawn as a straight line from buying to selling.${undated}</div>
            <details><summary style="cursor: pointer;">Show the figures</summary><div style="overflow-x: auto;"><table><tr><th>End of</th><th>Account</th><th>Since the start</th>${series.anyAi ? '<th class="pp-fig-part">Your own buys</th><th class="pp-fig-part">AI autopilot</th>' : ''}</tr>${rows}</table></div></details>
        </div>`;
    }
    function drawChart() { const slot = document.getElementById('pp-chart'); if (slot && state && loaded) slot.innerHTML = chartHtml(); }
    // The pointer over the picture: a line at that moment, and its figures above
    function chartShow(point, crossed) {
        const cross = document.getElementById('pp-cross'), dot = document.getElementById('pp-dot'), read = document.getElementById('pp-chart-read');
        if (cross) { cross.setAttribute('x1', point.x); cross.setAttribute('x2', point.x); cross.style.display = crossed ? '' : 'none'; }
        if (dot) { dot.setAttribute('cx', point.x); dot.setAttribute('cy', point.y); }
        if (read) read.innerHTML = chartRead(point);
    }
    function chartPoint(e) {
        const svg = e.target && e.target.closest && e.target.closest('#pp-chart-svg');
        if (!svg || !chartNow) return;
        const rect = svg.getBoundingClientRect(), touch = e.touches && e.touches[0];
        const at = ((touch ? touch.clientX : e.clientX) - rect.left) * chartNow.width / (rect.width || chartNow.width);
        let best = chartNow.placed[0];
        chartNow.placed.forEach(point => { if (Math.abs(point.x - at) < Math.abs(best.x - at)) best = point; });
        chartShow(best, true);
    }

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

    document.addEventListener('mousemove', chartPoint);
    document.addEventListener('touchstart', chartPoint, { passive: true });
    document.addEventListener('touchmove', chartPoint, { passive: true });
    document.addEventListener('mouseout', (e) => {
        const from = e.target && e.target.closest && e.target.closest('#pp-chart-svg'), to = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('#pp-chart-svg');
        if (from && !to && chartNow) chartShow(chartNow.placed[chartNow.placed.length - 1], false);
    });
    // The picture is drawn to the width it has: draw it again when that changes (a tab opened, a window resized, a phone turned)
    let chartTimer = null, chartWidth = 0;
    const chartFit = () => { const el = box(), w = el ? el.clientWidth : 0; if (w && Math.abs(w - chartWidth) > 8) { chartWidth = w; clearTimeout(chartTimer); chartTimer = setTimeout(drawChart, 120); } };
    if (typeof ResizeObserver !== 'undefined' && box()) new ResizeObserver(chartFit).observe(box()); else if (window.addEventListener) window.addEventListener('resize', chartFit);

    document.addEventListener('click', (e) => {
        const t = e.target.closest && e.target.closest('[data-pp]');
        if (!t) { const sug = document.getElementById('pp-suggest'); if (sug && !e.target.closest('#pp-suggest, #pp-symbol')) sug.style.display = 'none'; return; }
        const action = t.getAttribute('data-pp');
        if (t.tagName === 'A') e.preventDefault();
        if (action === 'chart-key' || action === 'chart-range') {
            if (action === 'chart-key') chartKey = t.getAttribute('data-id'); else chartRange = t.getAttribute('data-id');
            try { localStorage.setItem(action === 'chart-key' ? 'stockiqPracticeChartKey' : 'stockiqPracticeChartRange', t.getAttribute('data-id')); } catch (err) { /* not remembered */ }
            drawChart();
            return;
        }
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
    // A few plain lines on what the practice portfolio shows right now, for the AI chat on the dashboard (ai-chat.js)
    function summary() {
        if (!state || !loaded) return '';
        const s = summarize(state, quotes), mine = state.holdings.filter(h => h.by !== 'ai'), its = state.holdings.filter(h => h.by === 'ai');
        const one = (h) => { const v = valueOf(h, quotes); return `${h.label || h.symbol} ${usd(v.valueUsd)} (${v.priced ? moved(v.gainUsd) : 'no price now'})`; };
        return ['PRACTICE PORTFOLIO (fake money): account value ' + usd(s.accountValue) + ', ' + moved(s.gainUsd) + ' since the start of ' + usd(STARTING_CASH) + '; practice cash left ' + usd(state.cash) + '.',
            'Bought by the user (' + mine.length + '): ' + (mine.slice(0, 12).map(one).join('; ') || 'none') + '.',
            'Bought by the autopilot and still held (' + its.length + '): ' + (its.slice(0, 12).map(one).join('; ') || 'none') + '.',
            'Sold so far: ' + state.closed.length + '.'].join('\n');
    }
    window.practicePortfolio = { reload: load, setPlans, summary };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load); else load();
})();
