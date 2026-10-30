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
    // A practice buy or sale by hand is made only at a price that has traded in the last FRESH_HOURS, as the autopilot's are
    // (FRESH_HOURS in stockiq-ai-trader: keep the two the same). An older price means the share's market is closed (a night, a
    // weekend, a public holiday): on 17 Oct 2026, a Saturday, the owner sold TLS.AX at Friday's closing price. Coins trade
    // round the clock and are never held back.
    const FRESH_HOURS = 3;
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
    // Whose holdings a list shows: 'own' the ones bought by hand, 'ai' the autopilot's, 'g:<market>' the autopilot's from one
    // market, 's:<screener>' from one screener (23 Oct 2026), anything else all of them. info: the screeners, as the autopilot
    // sends them ({key: {name, group}}).
    const THEMES_INFO = { name: 'Sector funds (a trial)', group: 'Sector funds' };
    // Each screener's own index (23 Oct 2026, the owner: "should i do it against the actual market, eg asx200"): the S&P 500 says
    // whether a market was worth the money, its own index whether the picks were good in it. The symbols are the dashboard's Top 10
    // ones (TOP10_BENCHMARKS), where the price source has their daily prices: the TSX 60 and the Taiwan 50 have no index there, so the
    // TSX Composite and the TAIEX; the S&P 1000 and 1500, the KOSPI 200 and the CSI 300 have only today's price (23 Oct 2026), so the
    // S&P 400, the S&P 500, the KOSPI and the CSI 300's index fund (510300.SS).
    const HOME_INDEX = { '3-8': ['^DJI', 'Dow Jones'], '3-100': ['^OEX', 'S&P 100'], '3-7': ['^NDX', 'NASDAQ 100'], '3-3': ['^GSPC', 'S&P 500 index'],
        '3-2': ['^SP400', 'S&P 400'], '3-4': ['^GSPC', 'S&P 500 index'], '3-5': ['^RUI', 'Russell 1000'], '3-6': ['^RUT', 'Russell 2000'],
        '4-50': ['^AFLI', 'ASX 50'], '4-100': ['^ATOI', 'ASX 100'], '4-200': ['^AXJO', 'ASX 200'], '4-300': ['^AXKO', 'ASX 300'],
        '5-ftse100': ['^FTSE', 'FTSE 100'], '5-nikkei225': ['^N225', 'Nikkei 225'], '5-dax40': ['^GDAXI', 'DAX'], '5-cac40': ['^FCHI', 'CAC 40'],
        '5-aex': ['^AEX', 'AEX'], '5-tsx60': ['^GSPTSE', 'TSX Composite'], '5-ftsemib': ['FTSEMIB.MI', 'FTSE MIB'], '5-ibex35': ['^IBEX', 'IBEX 35'],
        '5-hangseng': ['^HSI', 'Hang Seng'], '5-sti': ['^STI', 'Straits Times'], '5-smi': ['^SSMI', 'SMI'], '5-sensex': ['^BSESN', 'Sensex'],
        '5-kospi200': ['^KS11', 'KOSPI'], '5-bovespa': ['^BVSP', 'Bovespa'], '5-sx5e': ['^STOXX50E', 'Euro Stoxx 50'], '5-omx30': ['^OMX', 'OMX Stockholm 30'],
        '5-csi300': ['510300.SS', 'CSI 300 fund'], '5-tw50': ['^TWII', 'TAIEX'], '5-nzx50': ['^NZ50', 'NZX 50'], '5-ipc': ['^MXX', 'IPC'] };
    // A holding against its own index, in its own currency (a currency's move is not the picks' doing): what it made in local money,
    // after the trading cost, less what the index did between its buying and its sale (or now). The index's price at a moment is read
    // between its daily closes, so this is an approximation. Null without the index's prices or an exchange rate.
    function homeGap(h, quotes) {
        const ix = HOME_INDEX[h.screener], q = ix && quotes[ix[0]];
        if (!q || !(q.price > 0) || !(h.costUsd > 0) || !(h.buyFx > 0)) return null;
        const ms = (x) => typeof x === 'number' ? x : Date.parse(x), sold = !!h.soldAt;
        const knots = ((q.series || []).filter(k => k[1] > 0)).concat([[Math.max(Date.now(), ...((q.series || []).map(k => k[0] + 1))), q.price]]);
        const at = (t) => valueAt(knots, t);
        const i0 = at(ms(h.boughtAt)), i1 = sold ? at(ms(h.soldAt)) : q.price;
        const own = quotes[h.symbol];                                 // in its own currency: what came back, or its worth now, over what was put in
        const endLocal = sold ? (h.sellFx > 0 ? h.proceedsUsd / h.sellFx : null) : (own && own.price > 0 ? h.qty * own.price : null);
        if (!(i0 > 0) || !(i1 > 0) || !(endLocal >= 0)) return null;
        const mine = endLocal / (h.costUsd / h.buyFx) - 1, index = i1 / i0 - 1;
        return { gap: h.costUsd * (mine - index), name: ix[1] };
    }
    function marketOf(h, info) {
        if (!h || h.by !== 'ai') return null;
        const i = h.screener === 'themes' ? THEMES_INFO : (info || {})[h.screener];
        return i ? { group: i.group, name: i.name, key: h.screener } : { group: 'Other', name: h.screener || 'Not known', key: h.screener || '' };
    }
    function partOf(list, key, info) {
        if (key === 'own') return list.filter(h => h.by !== 'ai');
        if (key === 'ai') return list.filter(h => h.by === 'ai');
        if (/^[gs]:/.test(String(key))) return list.filter(h => pickOf(key, info)(h));
        return list;
    }
    function pickOf(key, info) {
        const k = String(key || ''), what = k.slice(2);
        return (h) => { const m = marketOf(h, info); return !!m && (k[0] === 'g' ? m.group === what : m.key === what); };
    }
    // Where the autopilot's results come from (the owner, 23 Oct 2026: "the goal is to understand where the profit or loss is
    // coming from ... my goal is to beat the S&P"): per market and per screener, sold and still held together, against the same
    // dollars put into an S&P 500 fund on the day each was bought and taken out the day it was sold (or now). A holding bought
    // without the fund's price kept is counted in the result but not in the comparison (`compared` says how much was).
    function marketResults(state, quotes, info) {
        const spyNow = (quotes[BENCHMARK] || {}).price, out = {};
        let home = null;
        const add = (key, label, group, h, gain, fund) => {
            const r = out[key] || (out[key] = { key, label, group, trades: 0, sold: 0, held: 0, cost: 0, gainUsd: 0, compared: 0, fundUsd: 0, gainCompared: 0, homeCost: 0, homeGap: 0, homeNames: [], homeable: 0 });
            if (HOME_INDEX[h.screener]) r.homeable += h.costUsd;
            if (home) { r.homeCost += h.costUsd; r.homeGap += home.gap; if (!r.homeNames.includes(home.name)) r.homeNames.push(home.name); }
            r.trades++; r[h.soldAt ? 'sold' : 'held']++; r.cost += h.costUsd; r.gainUsd += gain;
            if (fund !== null) { r.compared += h.costUsd; r.fundUsd += fund; r.gainCompared += gain; }
        };
        const one = (h, sold) => {
            const m = marketOf(h, info);
            const gain = sold ? h.proceedsUsd - h.costUsd : valueOf(h, quotes).gainUsd;
            const end = sold ? h.spyAtSell : spyNow, fund = h.spyAtBuy > 0 && end > 0 ? h.costUsd * (end / h.spyAtBuy - 1) : null;
            home = m ? homeGap(h, quotes) : null;
            if (!m) { add('own', 'Your own buys', '', h, gain, fund); return; }      // bought by hand: in no market, but part of the account's sum
            add('g:' + m.group, m.group, m.group, h, gain, fund);
            add('s:' + m.key, m.name, m.group, h, gain, fund);
        };
        state.holdings.forEach(h => one(h, false));
        state.closed.forEach(h => one(h, true));
        Object.values(out).forEach(r => {
            r.aheadUsd = r.compared > 0 ? r.gainCompared - r.fundUsd : null;
            r.aheadPct = r.compared > 0 ? r.aheadUsd / r.compared * 100 : null;
            r.homePct = r.homeCost > 0 ? r.homeGap / r.homeCost * 100 : null;          // against its own index, in its own currency
            r.homeAll = r.homeCost > 0 && r.homeCost >= r.homeable - 0.01;                   // every holding of the row had its index's prices
        });
        return out;
    }

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

    // What a holding has done "today": since its market's previous close (a coin, which trades round the clock: since
    // 00:00 UTC), or since it was bought when that was later. With its market closed that is its last session, as a
    // broker shows it. From the daily prices that come with every quote: [end of a session, its close], ..., [now, the
    // price now]. A share's session ends are worked out from a session of six and a half hours, so a point less than
    // five hours before the latest price is the session still running (or just over), not the one before.
    function dayMove(h, quotes) {
        const v = valueOf(h, quotes), q = quotes[h.symbol], s = q && q.series;
        if (!v.priced || !s || s.length < 2) return null;
        const last = s[s.length - 1][0], always = /-USD$|=X$/.test(String(h.symbol || ''));
        let base = null;
        for (let i = s.length - 2; i >= 0; i--) if (always || s[i][0] <= last - 5 * 3600000) { base = s[i]; break; }
        if (!base || !(base[1] > 0)) return null;
        if ((Date.parse(h.boughtAt) || 0) > base[0]) return { usd: v.gainUsd, pct: v.changePct, since: 'bought' };   // bought after that close: all of it is today's
        const pct = (q.price / base[1] - 1) * 100;
        return { usd: v.valueUsd - v.valueUsd / (1 + pct / 100), pct, since: 'close' };
    }

    function summarize(state, quotes) {
        const spy = quotes[BENCHMARK] ? quotes[BENCHMARK].price : null;
        let holdingsValue = 0, cost = 0, marketValue = 0, marketCost = 0, unpriced = 0, compared = 0, ahead = 0, level = 0, dayUsd = 0, dayOf = 0, dayCount = 0, dayLive = 0, dayLast = 0;
        state.holdings.forEach(h => {
            const v = valueOf(h, quotes), d = dayMove(h, quotes);
            if (d) { dayUsd += d.usd; dayOf += v.valueUsd - d.usd; dayCount++; const q = quotes[h.symbol]; if (!closedFor(h.symbol, q)) dayLive++; if (q && q.time > dayLast) dayLast = q.time; }
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
            // today, for what is held now: the sum of each holding's own day (dayMove); null when no holding has one
            dayUsd: dayCount ? dayUsd : null, dayPct: dayCount && dayOf > 0 ? dayUsd / dayOf * 100 : null, dayCount,
            // every market it holds is closed (a weekend, a night): the figure is each holding's last session, not today's
            dayClosed: dayCount > 0 && dayLive === 0, dayLast: dayLast ? dayLast * 1000 : null,
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
        const open = summarize(state, quotes).openGainUsd, yours = total - autoSold - autoOpen, yoursOpen = open - autoOpen;
        // yoursSold / yoursOpen: the user's own part split the same way as the autopilot's, so the two rows read alike
        return { total, autoSold, autoOpen, auto: autoSold + autoOpen, yours, yoursOpen, yoursSold: yours - yoursOpen, any: held > 0 || sold > 0 || Math.abs(autoSold) > 0.004 };
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
        if (plan.theme) return `🤖 Autopilot, sector funds (a trial): one of the 3 strongest of 14 sector and theme funds by their past year. It is kept until the monthly change${plan.sellBy ? ` around ${when(plan.sellBy)}` : ''}, and sold then only if it is no longer among the 3.`;
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
            + (plan.patient ? ' A patient share, part of a trial: it is not sold because its screener signal turns or it slips down the ranking.' : ' It is also sold if its screener signal turns negative or it slips far down the ranking.') + shut;
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
    // How far back the fund's daily prices must reach to cover the account's life. The price source answers with a month
    // of them unless it is asked for more ('' = its own month).
    function fundRange(createdAt, now) {
        const days = (now - (typeof createdAt === 'number' ? createdAt : Date.parse(createdAt))) / 86400000;
        return !(days > 24) ? '' : days < 80 ? '3mo' : days < 170 ? '6mo' : days < 350 ? '1y' : days < 700 ? '2y' : '5y';
    }
    // "What if the whole starting amount had simply gone into an S&P 500 fund the moment the account began, and stayed
    // there": that holding's worth over time as [time, dollars], built as a holding's is (the fund's daily closes, then its
    // latest price now). No trading cost is taken off it and no dividends are counted. The fund's price at the start is
    // the last one known then: the last close at or before the start; or, when the US market was open at that moment and
    // something was bought later in the same session, the fund's price kept with that buy (the last close would be a
    // session old). Null when the fund's prices do not reach back to the start: then there is nothing to draw.
    function fundKnots(state, quotes, now) {
        const ms = (x) => typeof x === 'number' ? x : Date.parse(x);
        const q = quotes[BENCHMARK], series = (q && q.series) || [], start = ms(state.createdAt), cash = state.startingCash;
        if (!q || !(q.price > 0) || !(start > 0) || start > now || !(cash > 0)) return null;
        let base = null;
        series.forEach(([t, p]) => { if (t <= start && p > 0) base = p; });
        if (usOpensIn(start) === null) {
            let near = null;
            state.holdings.concat(state.closed).forEach(h => {
                const t = ms(h.boughtAt);
                if (h.spyAtBuy > 0 && t >= start && t - start < 23400000 && usOpensIn(t) === null && (!near || t < near[0])) near = [t, h.spyAtBuy];
            });
            if (near) base = near[1];
        }
        if (!(base > 0)) return null;
        const knots = [[start, cash]];
        series.forEach(([t, p]) => { if (t > start && t < now && p > 0) knots.push([t, cash * p / base]); });
        knots.push([Math.max(now, start + 1), cash * q.price / base]);
        return knots;
    }
    // Day by day, the account against the S&P 500 fund (19 Oct 2026, for the confidence line on the owner's Admin page): at each of
    // the fund's daily closes since the account began, the account's change and the fund's, from the graph's own sums. Returns
    // { days, ahead, avg, se } of the daily gap in percentage points (account less fund), or null without the fund's prices.
    function versusDays(state, quotes, now, autoRealized) {
        const fund = fundKnots(state, quotes, now);
        if (!fund) return null;
        const series = valueSeries(state, quotes, now, autoRealized, 0), at = new Map(series.points.map(p => [p.t, p]));
        // from the start, through each of the fund's closes, to now: the days add up to the whole gap (23 Oct 2026: the first and the
        // latest stretch were left out, so the days added up to +0.39% while the account was 1.13% behind, and the dial leaned the wrong way)
        const closes = fund.map(k => at.get(k[0])).filter(p => p && p.value > 0 && p.fund > 0);
        const gaps = [];
        for (let i = 1; i < closes.length; i++) gaps.push(((closes[i].value / closes[i - 1].value) - (closes[i].fund / closes[i - 1].fund)) * 100);
        const n = gaps.length, avg = n ? gaps.reduce((a, b) => a + b, 0) / n : 0;
        const se = n > 1 ? Math.sqrt(gaps.reduce((a, b) => a + (b - avg) ** 2, 0) / (n - 1) / n) : 0;
        return { days: n, ahead: gaps.filter(g => g > 0).length, avg, se, gaps: gaps.map(g => Math.round(g * 1000) / 1000) };     // gaps: each day's, for the dial's line
    }
    // The fund's own day (26 Oct 2026, the owner: to set beside the account's "Today"): the same rule as dayMove, since the previous
    // close, or its last session while the US market is shut. `value` is what the fund holding is worth now. Null without its prices.
    function fundDay(quotes, value) {
        const q = quotes[BENCHMARK], s = q && q.series;
        if (!q || !(q.price > 0) || !s || s.length < 2 || !(value > 0)) return null;
        const last = s[s.length - 1][0];
        let base = null;
        for (let i = s.length - 2; i >= 0; i--) if (s[i][0] <= last - 5 * 3600000) { base = s[i]; break; }
        if (!base || !(base[1] > 0)) return null;
        const pct = (q.price / base[1] - 1) * 100;
        return { usd: value - value / (1 + pct / 100), pct };
    }
    // The account against that fund right now: what the fund would be worth, and how far the account is ahead of it
    // (gapUsd above zero) or behind it. Null when the fund cannot be worked out.
    function versusStart(state, quotes, now) {
        const knots = fundKnots(state, quotes, now);
        if (!knots) return null;
        const value = knots[knots.length - 1][1];
        return { value, gainUsd: value - state.startingCash, gapUsd: summarize(state, quotes).accountValue - value };
    }
    // The account at every moment from `from` to `now`, worked out from what is in it. A holding still held is valued at
    // its daily prices and at its latest price now. One that was sold is a straight line from what was put in to what came
    // back: exact at both ends, a guess in between. Results of sales no longer in the list (the list was cleared, or is
    // over its limit) have no dates left: they are counted from the beginning, and `undated` says how much that is.
    // Each point: t, value (the account), all (its change since the start), ai (the autopilot's part), own (the user's),
    // fund (the starting amount in an S&P 500 fund since the account began: fundKnots; null when that cannot be worked out).
    function valueSeries(state, quotes, now, autoRealized, from, pick) {
        const ms = (x) => typeof x === 'number' ? x : Date.parse(x);
        const spy = quotes[BENCHMARK], spySeries = (spy && spy.series) || [];
        // one holding's dollars in the S&P 500 fund instead, on its own days: exact at buying and at selling (or now)
        const fundLot = (h, bought, end, endSpy) => {
            if (!(h.spyAtBuy > 0) || !(endSpy > 0)) return null;
            const k = [[bought, h.costUsd]];
            spySeries.forEach(([t, p]) => { if (t > bought && t < end && p > 0) k.push([t, h.costUsd * p / h.spyAtBuy]); });
            k.push([Math.max(end, bought + 1), h.costUsd * endSpy / h.spyAtBuy]);
            return k;
        };
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
            const picked = !!(pick && pick(h));
            lots.push({ ai: h.by === 'ai', cost: h.costUsd, from: bought, knots, picked, fund: picked ? fundLot(h, bought, now, spy && spy.price) : null });
        });
        state.closed.forEach(h => {
            const bought = ms(h.boughtAt);
            const picked = !!(pick && pick(h));
            lots.push({ ai: h.by === 'ai', cost: h.costUsd, from: bought, knots: [[bought, paid(h)], [Math.max(ms(h.soldAt), bought + 1), h.proceedsUsd]],
                        picked, fund: picked ? fundLot(h, bought, ms(h.soldAt), h.spyAtSell) : null });
        });
        const gain = (lot, t) => t < lot.from ? 0 : valueAt(lot.knots, t) - lot.cost;
        const split = splitGain(state, quotes, autoRealized);
        const undated = split.total - lots.reduce((sum, l) => sum + gain(l, now), 0);
        const undatedAi = split.auto - lots.reduce((sum, l) => sum + (l.ai ? gain(l, now) : 0), 0);
        const times = new Set([first, now]);
        lots.forEach(l => l.knots.concat(l.fund || []).forEach(k => { if (k[0] > first && k[0] < now) times.add(k[0]); }));
        const fundGain = (lot, t) => t < lot.from ? 0 : valueAt(lot.fund, Math.min(t, lot.fund[lot.fund.length - 1][0])) - lot.cost;
        const fund = fundKnots(state, quotes, now);
        if (fund) fund.forEach(k => { if (k[0] > first && k[0] < now) times.add(k[0]); });
        for (let i = 1; i < 120; i++) times.add(Math.round(first + (now - first) * i / 120));
        const points = [...times].sort((a, b) => a - b).map(t => {
            let all = undated, ai = undatedAi;
            let part = 0, pfund = 0;
            lots.forEach(l => { const g = gain(l, t); all += g; if (l.ai) ai += g; if (l.picked) { part += g; if (l.fund) pfund += fundGain(l, t); } });
            return Object.assign({ t, value: state.startingCash + all, all, ai, own: all - ai, fund: fund ? valueAt(fund, t) : null }, pick ? { part, pfund } : {});
        });
        // pfundAll: every holding of the part has the fund's price from its buy, so the fund's line is the same money throughout
        const chosen = lots.filter(l => l.picked);
        return { start, from: first, now, points, undated, undatedAi, lots: lots.length, anyAi: split.any, fund: !!fund,
                 parts: pick ? chosen.length : 0, pfundAll: !!pick && chosen.length > 0 && chosen.every(l => l.fund) };
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
        // the S&P 500 fund's line beside the account's; for one market (key 'part') the same dollars in the fund on the same days
        const fk = key === 'part' ? 'pfund' : 'fund';
        const both = key === 'value' ? !!series.fund && pts.every(p => typeof p.fund === 'number') : key === 'part' && !!series.pfundAll;
        const vals = pts.map(p => p[key]).concat([base], both ? pts.map(p => p[fk]) : []);
        let lo = Math.min(...vals), hi = Math.max(...vals);
        const pad = Math.max((hi - lo) * 0.12, Math.abs(base) * 0.0002, 1); lo -= pad; hi += pad;
        const t0 = series.from, t1 = Math.max(series.now, t0 + 1);
        const x = (t) => m.l + w * (t - t0) / (t1 - t0), y = (v) => m.t + h * (1 - (v - lo) / (hi - lo));
        const cents = hi - lo < 20;
        const label = (v) => key === 'value' ? '$' + v.toLocaleString('en-US', { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 })
            : (Math.abs(v) < 0.005 ? '$0' : (v > 0 ? '+$' : '-$') + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 }));
        const days = (t1 - t0) / 86400000;
        const stamp = (t) => { const d = new Date(t); return days <= 3 ? d.toLocaleString(undefined, { weekday: 'short', hour: '2-digit', minute: '2-digit' }) : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }); };
        let out = `<svg id="pp-chart-svg" class="pp-chart-svg" role="img" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-label="${esc(key === 'value' ? 'Account value over time' : key === 'ai' ? 'The autopilot’s result over time' : key === 'part' ? 'The result of one market over time' : 'The result of your own buys over time')}: from ${esc(label(pts[0][key]))} to ${esc(label(pts[pts.length - 1][key]))}${both ? (key === 'part' ? '; the same money in an S&amp;P 500 fund on the same days: ' : '; the same amount in an S&amp;P 500 fund since the start: ') + esc(label(pts[pts.length - 1][fk])) : ''}">`;
        axisTicks(lo, hi, small ? 3 : 4).ticks.forEach(v => {
            out += `<line class="pp-grid" x1="${m.l}" x2="${W - m.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="pp-axis" x="${m.l - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${esc(label(v))}</text>`;
        });
        const n = W < 420 ? 2 : small ? 3 : 5;               // on a phone four date labels ran into each other: three there
        for (let i = 0; i <= n; i++) {
            const t = t0 + (t1 - t0) * i / n;
            out += `<text class="pp-axis" x="${x(t).toFixed(1)}" y="${H - 6}" text-anchor="${i === 0 ? 'start' : i === n ? 'end' : 'middle'}">${esc(stamp(t))}</text>`;
        }
        // where it started: the line everything is measured against
        out += `<line class="pp-base" x1="${m.l}" x2="${W - m.r}" y1="${y(base).toFixed(1)}" y2="${y(base).toFixed(1)}"/>`;
        // f, fy: the fund at that moment and where it sits (only on the account's own picture, and only when it could be worked out)
        const placed = pts.map(p => Object.assign({ t: p.t, v: p[key], all: p.all, x: +x(p.t).toFixed(1), y: +y(p[key]).toFixed(1) }, both ? { f: p[fk], fy: +y(p[fk]).toFixed(1) } : {}));
        // a click and drag across the picture shades the stretch between two moments (26 Oct 2026): drawn by showMeasure
        out += `<rect id="pp-band" class="pp-band" x="${m.l}" y="${m.t}" width="0" height="${h}" style="display:none"/><line id="pp-cross-a" class="pp-cross" x1="${m.l}" x2="${m.l}" y1="${m.t}" y2="${m.t + h}" style="display:none"/>`;
        if (both) out += `<path class="pp-fund" d="${placed.map((p, i) => (i ? 'L' : 'M') + p.x + ' ' + p.fy).join('')}"/>`;      // under the account's line
        out += `<path class="pp-line" d="${placed.map((p, i) => (i ? 'L' : 'M') + p.x + ' ' + p.y).join('')}"/>`;
        const end = placed[placed.length - 1];
        out += `<line id="pp-cross" class="pp-cross" x1="${end.x}" x2="${end.x}" y1="${m.t}" y2="${m.t + h}" style="display:none"/>`;
        if (both) out += `<circle id="pp-dot-fund" class="pp-dot-fund" cx="${end.x}" cy="${end.fy}" r="4"/>`;
        out += `<circle id="pp-dot" class="pp-dot" cx="${end.x}" cy="${end.y}" r="4"/></svg>`;
        return { svg: out, placed, base, width: W, fund: both };
    }

    // How long until the US stock market next opens ("9h 35m"), or null while it is open: 9:30 to 16:00 New York time,
    // Monday to Friday, the rule the dashboard's sidebar counts down by (no public holidays in either).
    function usOpensIn(now) {
        const ny = new Date(new Date(now).toLocaleString('en-US', { timeZone: 'America/New_York' }));
        const day = ny.getDay(), minutes = ny.getHours() * 60 + ny.getMinutes();
        if (day >= 1 && day <= 5 && minutes >= 570 && minutes < 960) return null;
        const next = new Date(ny); next.setHours(9, 30, 0, 0);
        if (minutes >= 960 || day === 0 || day === 6) { do { next.setDate(next.getDate() + 1); } while (next.getDay() === 0 || next.getDay() === 6); }
        const left = Math.max(0, next - ny);
        return Math.floor(left / 3600000) + 'h ' + Math.floor((left % 3600000) / 60000) + 'm';
    }

    // Whether a symbol's market is closed now, by the age of its last traded price: null when it can be traded (a coin, a
    // currency, a fresh price, or a quote that gives no time), else { at: when it last traded (ms), hours: how long ago }
    function closedFor(symbol, q, now) {
        if (/-USD$|=X$/.test(String(symbol || '')) || !q || !(q.time > 0)) return null;
        const at = q.time * 1000, hours = ((now === undefined ? Date.now() : now) - at) / 3600000;
        return hours > FRESH_HOURS ? { at, hours } : null;
    }
    function agoText(hours) { return hours < 48 ? `${Math.round(hours)} hours ago` : `${Math.round(hours / 24)} days ago`; }
    // what is said when a buy or a sale has to wait: verb 'bought' or 'sold'
    function closedText(label, c, verb) {
        return `${label} cannot be ${verb} now: its market is closed. Its last price is from ${when(new Date(c.at).toISOString())} (${agoText(c.hours)}). `
            + `A practice ${verb === 'sold' ? 'sale' : 'buy'} is made only at a price that has traded in the last ${FRESH_HOURS} hours, as the autopilot's are, so that it is a price someone could really have traded at. Try again once its market is open.`;
    }

    const pure = { marketOf, marketResults, homeGap, HOME_INDEX, pickOf, closedFor, closedText, FRESH_HOURS, newState, fxFor, fxRate, versusMarket, applyBuy, applySell, applyClearSold, soldSummary, partOf, valueOf, summarize, splitGain, planLine, moved, movedHtml, usd, pct, money, esc, TRADE_COST_PCT, STARTING_CASH, DEFAULT_AMOUNT, seriesOf, valueAt, dayMove, valueSeries, axisTicks, chartSvg, usOpensIn, fundRange, fundKnots, versusStart, versusDays, fundDay };
    if (typeof module !== 'undefined' && module.exports) module.exports = pure;
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    // ---------------------------------------------------------------- page
    // On a phone a table of seven columns cannot be read: each holding becomes a card, every figure on its own labelled line.
    // (The cells carry inline styles, hence the !important.)
    const PP_CSS = `
        .pp-btn { background: #007bff; color: #fff; border: 1px solid #007bff; border-radius: 6px; padding: 6px 12px; font-size: 0.85rem; cursor: pointer; white-space: nowrap; font-family: inherit;
                  transition: background-color 0.12s, border-color 0.12s, box-shadow 0.12s, transform 0.05s; }
        .pp-btn:hover:not(:disabled) { background: #0069d9; border-color: #0062cc; }
        .pp-btn:active:not(:disabled) { background: #0056b3; border-color: #0056b3; transform: translateY(1px); box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3); }
        .pp-btn:focus-visible { outline: 2px solid #007bff; outline-offset: 2px; }
        .pp-btn:disabled { opacity: 0.6; cursor: default; }
        .pp-btn.big { padding: 10px 18px; font-size: 0.95rem; }
        .pp-btn.ghost { background: transparent; color: var(--text-primary); border-color: var(--border-color); }
        .pp-btn.ghost:hover:not(:disabled) { background: var(--bg-secondary); border-color: var(--text-secondary); }
        .pp-btn.ghost:active:not(:disabled) { background: var(--border-color); border-color: var(--text-secondary); transform: translateY(1px); box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.18); }
        .pp-btn.busy::before { content: ''; display: inline-block; width: 0.75em; height: 0.75em; margin-right: 7px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; vertical-align: -1px; animation: pp-spin 0.7s linear infinite; }
        @keyframes pp-spin { to { transform: rotate(360deg); } }
        @keyframes pp-flash { 0%, 55% { color: #16a34a; font-weight: 600; } }
        @media (prefers-reduced-motion: reduce) { .pp-btn.busy::before { animation-duration: 2.4s; } .pp-btn { transition: none; } }
        .pp-headrow { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px 16px; }
        #pp-tools { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 8px; margin-bottom: 10px; }
        #pp-tools .pp-updated { font-size: 0.78rem; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
        #pp-tools .pp-updated.fresh { animation: pp-flash 2.4s ease-out; }
        @media (max-width: 640px) { #pp-tools { justify-content: flex-start; width: 100%; } #pp-tools .pp-updated { flex: 1 1 100%; order: 3; } #pp-tools .pp-btn { flex: 1 1 0; padding: 9px 10px; } }
        #practice-portfolio { --pp-line: #2563eb; --pp-fund: #c98500; }      /* the pair was checked against the light and the dark background, also for colour-blind readers */
        [data-theme="dark"] #practice-portfolio { --pp-line: #3b82f6; }
        #practice-portfolio .pp-chart { border: 1px solid var(--border-color); border-radius: 10px; padding: 12px 14px 8px; margin-bottom: 14px; background: var(--bg-primary); }
        #practice-portfolio .pp-chart-head { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: baseline; justify-content: space-between; margin-bottom: 4px; }
        #practice-portfolio .pp-chart-title { flex: 0 0 300px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-secondary); }
        #practice-portfolio .pp-chart-read { font-size: 0.9rem; color: var(--text-primary); font-variant-numeric: tabular-nums; min-height: 1.3em; }
        #practice-portfolio .pp-chart-read .pp-chart-when { color: var(--text-secondary); margin-right: 8px; }
        #practice-portfolio .pp-sym { background: none; border: 0; padding: 0; font: inherit; font-weight: 700; color: var(--text-primary); cursor: pointer; text-align: left; }
        #practice-portfolio .pp-sym:hover { text-decoration: underline dotted; }
        #practice-portfolio .pp-sym-go { font-size: 0.75em; opacity: 0.55; }
        #practice-portfolio .pp-chart-tabs { display: flex; flex-wrap: wrap; gap: 6px; }
        #practice-portfolio .pp-mkt { position: relative; flex-basis: 100%; min-width: 0; margin-top: 6px; }
        #practice-portfolio .pp-mkt-btn { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 6px; max-width: 100%; text-align: left; background: none; border: 1px solid var(--border-color); border-radius: 8px; padding: 6px 10px; font-size: 0.85rem; color: var(--text-secondary); cursor: pointer; }
        #practice-portfolio .pp-mkt-btn strong { color: var(--text-primary); }
        #practice-portfolio .pp-mkt-panel { margin-top: 6px; border: 1px solid var(--border-color); border-radius: 10px; background: var(--card-bg, var(--bg-color, #fff)); padding: 8px; max-height: 420px; overflow-y: auto; }
        #practice-portfolio .pp-mkt-sum { font-size: 0.8rem; color: var(--text-secondary); line-height: 1.45; margin: 2px 4px 8px; }
        #practice-portfolio .pp-mkt-tally { margin-top: 8px; border-top: 2px solid var(--border-color); }
        #practice-portfolio .pp-mkt-tally .pp-mkt-row { cursor: default; } #practice-portfolio .pp-mkt-tally button.pp-mkt-row { cursor: pointer; }
        #practice-portfolio .pp-mkt-tally .pp-mkt-row:last-child .pp-mkt-name { font-weight: 700; }
        #practice-portfolio .pp-mkt-how { margin-top: 4px; }
        #practice-portfolio .pp-home { display: block; font-size: 0.72rem; color: var(--text-secondary); margin-top: 2px; white-space: nowrap; } #practice-portfolio .pp-mkt-how summary { cursor: pointer; }
        #practice-portfolio .pp-mkt-head, #practice-portfolio .pp-mkt-row { display: grid; grid-template-columns: minmax(0, 1fr) 90px 150px 170px; gap: 8px; align-items: center; }
        #practice-portfolio .pp-mkt-head { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-secondary); padding: 0 8px 4px; }
        #practice-portfolio .pp-mkt-head span:not(:first-child), #practice-portfolio .pp-mkt-row > span:not(:first-child) { text-align: right; }
        #practice-portfolio .pp-mkt-row { width: 100%; background: none; border: 0; border-top: 1px solid var(--border-color); padding: 7px 8px; font-size: 0.85rem; color: var(--text-primary); cursor: pointer; text-align: left; }
        #practice-portfolio .pp-mkt-row:hover, #practice-portfolio .pp-mkt-row.on { background: rgba(127, 127, 127, 0.1); }
        #practice-portfolio .pp-mkt-row.all { font-weight: 700; font-size: 0.95rem; background: rgba(127, 127, 127, 0.08); }
        #practice-portfolio .pp-mkt-row:not(.sub):not(.all) .pp-mkt-name { font-weight: 700; }
        #practice-portfolio .pp-mkt-row.sub .pp-mkt-name { padding-left: 16px; }
        #practice-portfolio .pp-mkt-name small { display: block; font-weight: 400; font-size: 0.72rem; color: var(--text-secondary); }
        #practice-portfolio .pp-vs { font-weight: 700; white-space: nowrap; color: var(--text-secondary); }
        #practice-portfolio .pp-vs.up { color: #16a34a; } #practice-portfolio .pp-vs.down { color: #ef4444; }
        #practice-portfolio .pp-mkt-row .pp-vs { display: inline-block; padding: 1px 7px; border-radius: 999px; }
        #practice-portfolio .pp-mkt-row .pp-vs.up { background: rgba(22, 163, 74, 0.12); } #practice-portfolio .pp-mkt-row .pp-vs.down { background: rgba(239, 68, 68, 0.12); }
        @media (max-width: 640px) {
            #practice-portfolio .pp-mkt-head { display: none; }
            #practice-portfolio .pp-mkt-row { grid-template-columns: minmax(0, 1fr) auto; row-gap: 2px; }
            #practice-portfolio .pp-mkt-row .pp-mkt-name { grid-column: 1 / -1; }
            #practice-portfolio .pp-mkt-row .pp-mkt-in, #practice-portfolio .pp-mkt-row .pp-mkt-res { text-align: left !important; font-size: 0.8rem; }
            #practice-portfolio .pp-mkt-row .pp-mkt-in::before { content: 'Total bought '; color: var(--text-secondary); }
            #practice-portfolio .pp-mkt-row .pp-mkt-vs { grid-column: 1 / -1; text-align: left !important; }
            #practice-portfolio .pp-mkt-row.sub .pp-mkt-in, #practice-portfolio .pp-mkt-row.sub .pp-mkt-res, #practice-portfolio .pp-mkt-row.sub .pp-mkt-vs { padding-left: 16px; }
        }
        #practice-portfolio .pp-chart-tabs button { background: none; color: var(--text-secondary); border: 1px solid var(--border-color); border-radius: 999px; padding: 3px 11px; font-size: 0.78rem; cursor: pointer; }
        #practice-portfolio .pp-chart-tabs button[aria-pressed="true"] { color: var(--text-primary); border-color: var(--text-secondary); font-weight: 600; }
        #practice-portfolio .pp-chart-svg { display: block; width: 100%; height: auto; touch-action: pan-y; cursor: crosshair; }
        #practice-portfolio .pp-grid { stroke: var(--border-color); stroke-width: 1; }
        #practice-portfolio .pp-base { stroke: var(--text-secondary); stroke-width: 1; stroke-dasharray: 4 4; opacity: 0.7; }
        #practice-portfolio .pp-axis { fill: var(--text-secondary); font-size: 11px; font-variant-numeric: tabular-nums; }
        #practice-portfolio .pp-line { fill: none; stroke: var(--pp-line); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
        #practice-portfolio .pp-cross { stroke: var(--text-secondary); stroke-width: 1; }
        #practice-portfolio .pp-band { fill: rgba(127, 127, 127, 0.12); } #practice-portfolio .pp-band.up { fill: rgba(22, 163, 74, 0.13); } #practice-portfolio .pp-band.down { fill: rgba(239, 68, 68, 0.13); }
        #practice-portfolio .pp-chart-svg { -webkit-user-select: none; user-select: none; }
        #practice-portfolio .pp-dot { fill: var(--pp-line); stroke: var(--bg-primary); stroke-width: 2; }
        #practice-portfolio .pp-fund { fill: none; stroke: var(--pp-fund); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
        #practice-portfolio .pp-dot-fund { fill: var(--pp-fund); stroke: var(--bg-primary); stroke-width: 2; }
        #practice-portfolio .pp-chart-row { display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 8px; line-height: 1.5; }
        #practice-portfolio .pp-chart-who { color: var(--text-secondary); }
        #practice-portfolio .pp-key { display: inline-block; width: 16px; height: 4px; border-radius: 2px; background: var(--pp-line); vertical-align: middle; margin: 0 8px 2px 0; }
        #practice-portfolio .pp-key.fund { background: var(--pp-fund); }
        #practice-portfolio .pp-chart-note { font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px; }
        #practice-portfolio .pp-top { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
        #practice-portfolio .pp-top .pp-card-value { font-size: 1.7rem; }
        #practice-portfolio .pp-top .pp-card-value .pp-delta { font-weight: 700 !important; }
        #practice-portfolio .pp-facts { font-size: 0.88rem; color: var(--text-secondary); margin: 0 2px 8px; line-height: 1.6; }
        #practice-portfolio .pp-facts strong { color: var(--text-primary); }
        #practice-portfolio #pp-more { margin-bottom: 14px; }
        #practice-portfolio #pp-more > summary { cursor: pointer; font-size: 0.82rem; color: var(--text-secondary); margin: 0 2px 10px; }
        #practice-portfolio #pp-more > summary:hover { color: var(--text-primary); }
        #practice-portfolio .pp-plan { font-size: 0.75rem; color: var(--text-secondary); white-space: normal; max-width: 420px; margin-top: 2px; }
        #practice-portfolio .pp-plan > summary { cursor: pointer; list-style: none; }
        #practice-portfolio .pp-tags { display: flex; flex-wrap: wrap; gap: 4px 6px; margin-top: 3px; max-width: 420px; }
        #practice-portfolio .pp-tags > span { font-size: 0.72rem; color: var(--text-secondary); border: 1px solid var(--border-color); border-radius: 10px; padding: 1px 7px; white-space: normal; }
        #practice-portfolio .pp-plan > summary::-webkit-details-marker { display: none; }
        #practice-portfolio .pp-plan > summary::after { content: " \\25B8"; }
        #practice-portfolio .pp-plan[open] > summary::after { content: " \\25BE"; }
        #practice-portfolio .pp-plan > summary:hover { color: var(--text-primary); }
        #practice-portfolio .pp-plan > div { margin-top: 4px; padding-left: 10px; border-left: 2px solid var(--border-color); line-height: 1.45; }
        #practice-portfolio .pp-chart details { font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px; }
        #practice-portfolio .pp-chart table { border-collapse: collapse; margin-top: 6px; font-variant-numeric: tabular-nums; }
        #practice-portfolio .pp-chart td, #practice-portfolio .pp-chart th { padding: 2px 14px 2px 0; text-align: right; font-weight: normal; }
        #practice-portfolio .pp-chart td:first-child, #practice-portfolio .pp-chart th:first-child { text-align: left; }
        @media (max-width: 640px) {
            #practice-portfolio .pp-chart { padding: 10px 10px 6px; }
            #practice-portfolio .pp-chart .pp-fig-part { display: none; }
            #practice-portfolio .pp-chart td, #practice-portfolio .pp-chart th { padding-right: 10px; white-space: nowrap; }
            #practice-portfolio .pp-chart td.pp-fig-vs, #practice-portfolio .pp-chart th.pp-fig-vs { white-space: normal; }
        }
        #practice-portfolio { font-variant-numeric: tabular-nums; }
        #practice-portfolio .pp-card { flex: 1; min-width: 150px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 10px; padding: 12px 14px; border-top: 3px solid transparent; }
        #practice-portfolio .pp-card.up { border-top-color: #16a34a; } #practice-portfolio .pp-card.down { border-top-color: #ef4444; }
        #practice-portfolio .pp-card-label { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: var(--text-secondary); }
        #practice-portfolio .pp-card-value { font-size: 1.45rem; font-weight: 700; color: var(--text-primary); line-height: 1.3; }
        #practice-portfolio .pp-card-word { font-size: 0.7em; font-weight: 600; color: var(--text-secondary); }
        #practice-portfolio .pp-card-sub { font-size: 0.8rem; color: var(--text-secondary); line-height: 1.5; }
        #practice-portfolio .pp-pl { margin-bottom: 8px; }
        #practice-portfolio .pp-pl td { border-bottom: 1px solid var(--border-color); }
        #practice-portfolio .pp-pl tr.pp-pl-total td { border-bottom: 0; border-top: 2px solid var(--border-color); }
        #practice-portfolio .pp-pl tr.pp-pl-total td:not(.pp-name) { font-weight: 700; font-size: 0.95rem; }
        #practice-portfolio .pp-pl-note { font-size: 0.75rem; font-weight: 400; color: var(--text-secondary); }
        #practice-portfolio .pp-pl-line { font-size: 0.85rem; color: var(--text-secondary); margin: 6px 2px; line-height: 1.6; }
        #practice-portfolio .pp-pl-line strong { color: var(--text-primary); }
        #practice-portfolio .pp-pl-line ul { margin: 2px 0 0; padding-left: 20px; }
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
    let state = null, version = 0, quotes = {}, loaded = false, loadError = null, notice = null, working = false, searchTimer = null;
    let busy = null;                              // which button is at work ('refresh', 'buy', 'sell:<id>' ...): it shows a spinner and says so
    let pricesAt = 0, flash = false;              // when the prices on show were fetched; flash: say "updated" once, after a refresh by hand
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
        ppQuote = { symbol: typed, price: t.q.price, fx: t.fx, currency: t.q.currency, name: t.q.name, kind: t.q.kind };
        fillOther();
        return ppQuote;
    }
    // A code can be both a share or fund and a coin (24 Oct 2026: the owner typed BTC meaning Bitcoin and got the Grayscale Bitcoin
    // Mini Trust, a fund that does not trade at weekends). coinTwin('BTC') is the quote of BTC-USD when that is a coin, else null.
    const twins = {};
    async function coinTwin(code) {
        const c = String(code || '').trim().toUpperCase();
        if (!/^[A-Z0-9]{2,10}$/.test(c)) return null;
        if (!(c in twins)) twins[c] = fetchQuote(c + '-USD').then(q => (q && q.kind === 'CRYPTOCURRENCY' ? q : null)).catch(() => null);
        return twins[c];
    }
    const KIND_WORDS = { ETF: 'a fund', MUTUALFUND: 'a fund', EQUITY: 'a share', CRYPTOCURRENCY: 'a coin, trades every day', INDEX: 'an index', CURRENCY: 'a currency' };
    const kindWord = (q) => KIND_WORDS[(q && q.kind) || ''] || '';
    const coinName = (q, code) => String((q && q.name) || code).replace(/\s+USD$/i, '');
    let pickedSymbol = '';                          // the code last chosen from the suggestions (a typed code that is also a coin asks which)
    const openPlans = new Set();                  // the holdings whose plan is unfolded (kept across redraws)
    // The holdings table shows the latest 10, the rest behind a link (17 Oct 2026, the owner: 39 holdings were one long list;
    // as "What it has done" on the autopilot tab). Kept while the page is open, not remembered.
    const HELD_SHOWN = 10;
    let allHeld = false, heldOpenOnly = false;       // "Can be sold now": only the holdings whose market is open (19 Oct 2026, the owner)
    let moreOpen = false;                         // whether the breakdown under the three figures is unfolded (kept across redraws)
    let soldOpen = false;                         // whether the Sold list is unfolded (kept across redraws)
    let figsAll = false;                          // "Show all" days of the graph's figures (kept while the page is open)
    // Every fold with an id stays as the viewer left it when the tab is drawn again (24 Oct 2026, the owner: "Show the figures" closed
    // at the minute's refresh). A new fold needs only an id to be kept: no flag of its own.
    const openFolds = new Set();
    if (typeof document !== 'undefined' && document.addEventListener) document.addEventListener('toggle', (e) => {
        const d = e.target; if (!d || d.tagName !== 'DETAILS' || !d.id || !d.closest || !d.closest('#practice-portfolio')) return;
        if (d.open) openFolds.add(d.id); else openFolds.delete(d.id);
    }, true);
    function restoreFolds(el) {
        if (el && el.querySelectorAll) el.querySelectorAll('details[id]').forEach(d => { if (openFolds.has(d.id) && !d.open) d.open = true; });
    }
    const userId = () => { const u = localStorage.getItem('userId'); return u && u !== 'anonymous' ? u : null; };
    const box = () => document.getElementById('practice-portfolio');

    async function api(action, extra) {
        const res = await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.assign({ action, userId: userId() }, extra || {})) });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) { const e = new Error(body.error || 'The practice portfolio could not be reached'); e.conflict = !!body.conflict; throw e; }
        return body;
    }

    // range: how far back the daily prices should reach ('3mo', '1y', ...); without it the price source sends a month.
    // Only the S&P 500 fund is asked for more, and only once the account is older than that month (fundRange).
    function quoteOf(answer, symbol, range) {
        const result = answer?.chart?.result?.[0], meta = result && result.meta;
        if (!meta || !(meta.regularMarketPrice > 0)) return null;
        // series: the month of daily prices that comes with every quote, for the graph of the account over time
        return { price: meta.regularMarketPrice, currency: meta.currency || 'USD', name: meta.longName || meta.shortName || '', kind: meta.instrumentType || '', time: meta.regularMarketTime || 0, series: seriesOf(result, symbol), range: range || '' };
    }
    async function fetchQuote(symbol, range) {
        try {
            const res = await fetch(PRICE_API + encodeURIComponent(symbol) + (range ? '&range=' + range : ''));
            return quoteOf(await res.json(), symbol, range);
        } catch (e) { return null; }
    }
    // Many prices at once (23 Oct 2026; the owner: "Prices as of" took about 15 seconds). A browser sends only six requests at a
    // time to one address, and an account can need 60 prices, so they are asked for 20 a request (?symbols=A,B,C). A request
    // that fails (an older price function, a hiccup) falls back to one request a symbol. Returns [symbol, quote or null] pairs.
    // The function takes about a second longer for every ten symbols it fetches at once, while separate requests run side by
    // side, so the list is split into six requests (the six a browser sends together), at least 4 and at most 20 symbols each.
    async function fetchQuotes(symbols, rangeOf) {
        const plain = symbols.filter(sym => !rangeOf(sym)), own = symbols.filter(sym => rangeOf(sym));   // a longer range is asked for alone
        const parts = [], size = Math.min(20, Math.max(4, Math.ceil(plain.length / 6)));
        for (let i = 0; i < plain.length; i += size) parts.push(plain.slice(i, i + size));
        const many = async (part) => {
            try {
                const res = await fetch(PRICE_API.replace('?symbol=', '?symbols=') + encodeURIComponent(part.join(',')));
                const got = res.ok ? (await res.json())?.results : null;
                if (got && typeof got === 'object') return part.map(sym => [sym, quoteOf(got[sym], sym, '')]);
            } catch (e) {}
            return Promise.all(part.map(sym => fetchQuote(sym).then(q => [sym, q])));
        };
        const done = await Promise.all(parts.map(many).concat(own.map(sym => fetchQuote(sym, rangeOf(sym)).then(q => [[sym, q]]))));
        return [].concat(...done);
    }
    // A quote plus what is needed to turn it into dollars and compare it with the market
    async function quoteForTrade(symbol) {
        const q = await fetchQuote(symbol);
        if (!q) return null;
        const fx = fxFor(q.currency);
        const [rateQuote, spy] = await Promise.all([fx.symbol ? fetchQuote(fx.symbol) : null, fetchQuote(BENCHMARK, (quotes[BENCHMARK] || {}).range)]);      // as far back as the graph has it
        if (fx.symbol && !rateQuote) return null;
        quotes[symbol] = q; if (rateQuote) quotes[fx.symbol] = rateQuote; if (spy) quotes[BENCHMARK] = spy;
        return { q, fx: fxRate(fx, rateQuote ? rateQuote.price : 0), spy: spy ? spy.price : null };
    }
    // The symbols whose prices the page needed last time, kept in the browser: on the next visit their prices are asked for at
    // once, together with the portfolio, instead of only after it has arrived (one wait in place of two).
    const symbolsKey = () => 'stockiqPracticeSymbols_' + userId();
    const rangeKey = () => 'stockiqPracticeFundRange_' + userId();
    function knownRange() { try { const r = localStorage.getItem(rangeKey()) || ''; return /^(3mo|6mo|1y|2y|5y)$/.test(r) ? r : ''; } catch (e) { return ''; } }
    function knownSymbols() { try { const k = JSON.parse(localStorage.getItem(symbolsKey()) || '[]'); return Array.isArray(k) ? k.filter(x => typeof x === 'string').slice(0, 80) : []; } catch (e) { return []; } }
    const askedAt = {};                                    // when each symbol's price was last asked for (the refresh by itself, below)
    async function refreshQuotes(have, only) {
        if (!state) return;
        const wanted = new Set([BENCHMARK]);
        state.holdings.forEach(h => { wanted.add(h.symbol); const fx = fxFor(h.currency); if (fx.symbol) wanted.add(fx.symbol); });
        const span = fundRange(state.createdAt, Date.now());                         // the fund's prices have to reach back to the account's start
        try { localStorage.setItem(symbolsKey(), JSON.stringify([...wanted])); localStorage.setItem(rangeKey(), span); } catch (e) {}
        // those just fetched ahead are not asked for twice (the fund is, if what came does not reach back far enough)
        const list = [...wanted].filter(sym => !(have && have.has(sym)) || (sym === BENCHMARK && ((quotes[sym] || {}).range || '') !== span)).filter(sym => !only || only(sym));
        list.forEach(sym => { askedAt[sym] = Date.now(); });
        (await fetchQuotes(list, sym => sym === BENCHMARK ? span : '')).forEach(([s, q]) => { if (q) quotes[s] = q; });
        pricesAt = Date.now();
    }

    async function load() {
        if (!userId()) { loaded = true; render(); return; }
        if (!loaded) render();                             // the spinner until the portfolio and its prices are in
        // on the first load, the prices of what it held last time are asked for while the portfolio itself is on its way
        const ahead = loaded ? null : fetchQuotes(knownSymbols(), sym => sym === BENCHMARK ? knownRange() : '').catch(() => []);
        try {
            const r = await api('get');
            state = r.portfolio || newState(new Date().toISOString());
            version = r.version || 0; loadError = null;
        } catch (e) { loadError = e.message; }
        const have = new Set();
        if (ahead) (await ahead).forEach(([sym, q]) => { if (q) { quotes[sym] = q; have.add(sym); } });
        // Nothing is shown before the latest prices are in: holdings valued at what was paid looked, for a moment, like a
        // different account value. If the prices are slow, it is shown after 4 seconds anyway and again when they arrive.
        const prices = state ? refreshQuotes(have) : Promise.resolve();
        await Promise.race([prices, new Promise(done => setTimeout(done, 4000))]);
        loaded = true; redraw();
        await prices; redraw();
    }
    // Redraw without losing what is being typed in the buy row (the autopilot can change the portfolio in the background)
    function redraw() {
        const ids = ['pp-symbol', 'pp-amount', 'pp-qty', 'pp-note'], active = document.activeElement && document.activeElement.id;
        const keep = ids.map(id => [id, document.getElementById(id) ? document.getElementById(id).value : null]);
        // keep where the page and the market list were scrolled to (23 Oct 2026, the owner: "it occasionally jumps up to the top")
        const panel = () => document.querySelector && document.querySelector('#pp-mkt .pp-mkt-panel'), listAt = panel() ? panel().scrollTop : 0;
        const pageAt = typeof window !== 'undefined' && typeof window.scrollY === 'number' ? window.scrollY : null;
        render();
        reMeasure();
        if (panel() && listAt) panel().scrollTop = listAt;
        if (pageAt !== null && window.scrollY !== pageAt && window.scrollTo) window.scrollTo(0, pageAt);
        keep.forEach(([id, v]) => { const el = document.getElementById(id); if (el && v) el.value = v; });
        const clear = document.getElementById('pp-clear'), search = document.getElementById('pp-symbol');
        if (clear && search) clear.style.display = search.value ? 'block' : 'none';
        if (ids.includes(active)) { const el = document.getElementById(active); if (el && el.focus) el.focus(); }
    }
    // From practice-autopilot.js: for each holding the autopilot bought, when and at what it will sell it
    let plans = {}, autoRealized = null;
    function setPlans(list, extra) {
        const next = {}, made = extra && typeof extra.realizedUsd === 'number' ? extra.realizedUsd : null;
        const info = extra && extra.screeners && typeof extra.screeners === 'object' ? extra.screeners : screenerInfo;
        (list || []).forEach(p => { next[p.id] = p; });
        if (JSON.stringify(next) === JSON.stringify(plans) && made === autoRealized && JSON.stringify(info) === JSON.stringify(screenerInfo)) return;
        plans = next; autoRealized = made; screenerInfo = info;
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
        const closed = closedFor(symbol, trade.q);
        if (closed) throw new Error(closedText(label || symbol, closed, 'bought'));
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
        const closed = closedFor(h.symbol, trade.q);
        if (closed) throw new Error(closedText(h.label, closed, 'sold'));
        return change(s => applySell(s, id, { price: trade.q.price, fx: trade.fx, spy: trade.spy, now: new Date().toISOString() }));
    }

    function render() {
        ensureStyle();
        const el = box();
        if (!el) return;
        // the page's own place for the two buttons, beside the heading (an older page has none: they are then drawn at the bottom, as before)
        const tools = document.getElementById('pp-tools'), beside = tools && tools.parentNode && tools.parentNode !== el ? tools : null;
        if (beside) beside.innerHTML = '';
        const soldBox = document.getElementById('pp-sold');
        if (soldBox && typeof soldBox.open === 'boolean') soldOpen = soldBox.open;
        if (el && el.querySelectorAll) el.querySelectorAll('details.pp-plan').forEach(d => { const id = d.getAttribute('data-id'); if (d.open) openPlans.add(id); else openPlans.delete(id); });
        if (!userId()) { el.innerHTML = '<p style="color: var(--text-secondary);">Sign in to use the practice portfolio.</p>'; return; }
        if (!loaded) { el.innerHTML = '<div class="pp-wait" role="status" aria-label="Loading" style="padding: 26px 0 18px;"><div class="spinner"></div></div>'; return; }     // the site's own spinner (styles.css), as a screener shows while it runs
        if (!state) { el.innerHTML = `<p style="color: #ef4444;">${esc(loadError || 'The practice portfolio could not be loaded.')}</p><button data-pp="reload" class="pp-btn">Try again</button>`; return; }

        const s = summarize(state, quotes);
        try { document.dispatchEvent(new CustomEvent('practice-portfolio:figures')); } catch (e) {}     // the Admin page takes the same figure
        const card = (label, value, sub, way) => `<div class="pp-card${way > 0.004 ? ' up' : way < -0.004 ? ' down' : ''}"><div class="pp-card-label">${label}</div><div class="pp-card-value">${value}</div><div class="pp-card-sub">${sub || '&nbsp;'}</div></div>`;
        const cell = 'padding: 8px 6px; border-bottom: 1px solid var(--border-color); text-align: right; white-space: nowrap;';
        const left = cell.replace('text-align: right', 'text-align: left');

        // The graph's choice (Account, Your own buys, AI autopilot) is also whose holdings the two lists show
        if (chartKey !== 'value' && !splitGain(state, quotes, autoRealized).any) chartKey = 'value';
        if (isMarket(chartKey) && !screenerInfo) chartKey = 'ai';
        const held = partOf(state.holdings, chartKey, screenerInfo), soldOnes = partOf(state.closed, chartKey, screenerInfo), part = chartKey !== 'value';
        const count = (shown, all) => part ? `${shown} of ${all}` : String(all);
        const whose = chartKey === 'ai' ? 'the 🤖 AI autopilot’s' : isMarket(chartKey) ? `the 🤖 AI autopilot’s from ${esc(marketLabel(chartKey))}` : 'your own buys';
        const showAll = `<a href="#" data-pp="chart-key" data-id="value" style="color: #007bff; white-space: nowrap;">Show all</a>`;
        const partLine = part && state.holdings.length ? `<div id="pp-part" style="margin: 0 0 8px; font-size: 0.85rem; color: var(--text-secondary);">${held.length ? `Showing <strong style="color: var(--text-primary);">${whose}</strong>: ${held.length} of ${state.holdings.length} holdings.` : `None of the ${state.holdings.length} holdings ${state.holdings.length === 1 ? 'is' : 'are'} ${whose}.`} ${showAll}</div>` : '';

        // what is particular to an autopilot holding now, visible without opening its plan (moved here from the autopilot tab's
        // "Holding now", which listed the same holdings a second time: 19 Oct 2026)
        const tags = (p) => {
            if (!p || !p.auto || p.theme) return '';
            const t = [];
            if (p.closed) t.push(`${esc(p.market)} market closed${p.opens ? ' until ' + esc(when(p.opens)) : ''}`);
            if (p.mode === 'full' && typeof p.floor === 'number' && !(p.peak >= p.arm)) t.push(`trailing stop at ${(p.floor >= 0 ? '+' : '') + p.floor}%`);
            else if (typeof p.floor === 'number') t.push(`has been up ${(p.peak >= 0 ? '+' : '') + p.peak}%: sold if it falls back to ${(p.floor >= 0 ? '+' : '') + p.floor}%`);
            if (p.patient) t.push('patient share (trial)');
            return t.length ? `<div class="pp-tags">${t.map(x => `<span>${x}</span>`).join('')}</div>` : '';
        };
        const openNow = held.filter(h => !closedFor(h.symbol, quotes[h.symbol]));
        if (heldOpenOnly && (!openNow.length || openNow.length === held.length)) heldOpenOnly = false;
        const listed = heldOpenOnly ? openNow : held;
        const filterLine = held.length > 1 && openNow.length && openNow.length < held.length
            ? `<div id="pp-held-filter" style="margin: 0 0 8px; font-size: 0.85rem; color: var(--text-secondary);">Show: <a href="#" data-pp="held-filter" data-id="all" style="color: ${heldOpenOnly ? '#007bff' : 'var(--text-primary)'}; font-weight: ${heldOpenOnly ? 400 : 600};">All ${held.length}</a> · <a href="#" data-pp="held-filter" data-id="open" style="color: ${heldOpenOnly ? 'var(--text-primary)' : '#007bff'}; font-weight: ${heldOpenOnly ? 600 : 400};">Can be sold now ${openNow.length}</a> <span style="opacity: 0.8;">(their market is open)</span></div>` : '';
        const rowList = listed.slice().reverse().map(h => {
            const v = valueOf(h, quotes), today = dayMove(h, quotes), shut = closedFor(h.symbol, quotes[h.symbol]);
            return `<tr>
                <td class="pp-name" style="${left}">${h.by === 'ai' ? '<span title="Bought by the AI autopilot">🤖</span> ' : ''}<button type="button" class="pp-sym" data-pp="analyse" data-symbol="${esc(h.symbol)}" title="Run its full analysis in the background: it goes to your Reports">${esc(h.label)} <span class="pp-sym-go" aria-hidden="true">🔍</span></button><div style="font-size: 0.75rem; color: var(--text-secondary); white-space: normal;">${esc(h.name)}</div>${h.note ? `<div class="pp-note" style="font-size: 0.75rem; color: var(--text-secondary); white-space: normal; max-width: 420px;">${h.by === 'ai' ? '' : 'Note: '}${esc(h.note)}</div>` : ''}${h.by === 'ai' && plans[h.id] && plans[h.id].auto
                    ? `${tags(plans[h.id])}<details class="pp-plan" data-id="${esc(h.id)}"${openPlans.has(h.id) ? ' open' : ''}><summary>🤖 Autopilot: its plan for this</summary><div>${esc(planLine(h, plans[h.id]))}</div></details>`
                    : `<div style="font-size: 0.75rem; color: var(--text-secondary); white-space: normal; max-width: 420px;">${esc(planLine(h, plans[h.id]))}</div>`}</td>
                <td data-label="Bought" style="${cell}">${esc(when(h.boughtAt))}</td>
                <td data-label="Price then" style="${cell}">${money(h.buyPrice, h.currency)}</td>
                <td data-label="Price now" style="${cell}">${v.priced ? money(v.price, h.currency) : '<span title="No price available right now">–</span>'}</td>
                <td data-label="Value" style="${cell}">${usd(h.costUsd)} → ${usd(v.valueUsd)}</td>
                <td data-label="Today" style="${cell}">${today ? pctHtml(today.pct, today.usd) : '<span style="color: var(--text-secondary);">–</span>'}</td>
                <td data-label="Since bought" style="${cell}">${v.priced ? pctHtml(v.changePct, v.gainUsd) : '<span style="color: var(--text-secondary);">no price</span>'}</td>
                <td class="pp-act" style="${cell}">${shut ? `<button class="pp-btn ghost" disabled title="${esc(closedText(h.label, shut, 'sold'))}">Market closed</button>` : `<button data-pp="sell" data-id="${esc(h.id)}" class="pp-btn${busy === 'sell:' + h.id ? ' busy' : ''}" ${working ? 'disabled' : ''}>${busy === 'sell:' + h.id ? 'Selling…' : 'Sell'}</button>`}</td>
            </tr>`;
        });
        const rows = (allHeld ? rowList : rowList.slice(0, HELD_SHOWN)).join('');
        const heldMore = rowList.length > HELD_SHOWN ? `<div id="pp-held-more" style="margin: 8px 0 0; font-size: 0.85rem;"><a href="#" data-pp="held-all" style="color: #007bff;">${allHeld ? `Show only the latest ${HELD_SHOWN}` : `Show all ${rowList.length} (${rowList.length - HELD_SHOWN} more)`}</a></div>` : '';

        const closed = soldOnes.slice().reverse().map(h => {
            const change = (h.proceedsUsd / h.costUsd - 1) * 100;
            return `<tr><td class="pp-name" style="${left}">${h.by === 'ai' ? '<span title="Bought by the AI autopilot">🤖</span> ' : ''}<button type="button" class="pp-sym" data-pp="analyse" data-symbol="${esc(h.symbol)}" title="Run its full analysis in the background: it goes to your Reports">${esc(h.label)} <span class="pp-sym-go" aria-hidden="true">🔍</span></button></td><td data-label="Held" style="${cell}">${esc(when(h.boughtAt))} → ${esc(when(h.soldAt))}</td><td data-label="Price" style="${cell}">${money(h.buyPrice, h.currency)} → ${money(h.sellPrice, h.currency)}</td><td data-label="Value" style="${cell}">${usd(h.costUsd)} → ${usd(h.proceedsUsd)}</td><td data-label="Result" style="${cell}">${pctHtml(change, h.proceedsUsd - h.costUsd)}</td><td class="pp-act" style="${cell}"><span data-pp="unsold" data-id="${esc(h.id)}" title="Remove this line from the sold list" style="cursor: pointer; font-size: 16px; padding: 0 4px;">×</span></td></tr>`;
        }).join('');
        const sold = soldSummary({ closed: soldOnes });
        const soldLine = sold.count ? `${sold.count} sold: put in ${usd(sold.cost)}, got back ${usd(sold.proceeds)}: ${movedHtml(sold.gainUsd, sold.gainPct)}.` : '';
        // one total mixes the user's own buys with the autopilot's: say which part is whose
        const split = splitGain(state, quotes, autoRealized);
        const th = (t, align) => `<th style="padding: 6px; text-align: ${align || 'right'}; font-weight: 600; white-space: nowrap;">${t}</th>`;
        // The top answers three questions at a glance: what is it worth, how is today, how is it since the start. Everything else
        // (cash, what is in holdings, the index fund, sold and still held, whose result is whose) was on show at once, about
        // seventeen figures with several of them twice: it is one line now, and the full breakdown one click away.
        const big = (n) => movedHtml(n, null), share = (p) => (p === null || p === undefined || !isFinite(p)) ? '' : Math.abs(p).toFixed(2) + '%';
        const dayOfAccount = s.dayUsd !== null && s.accountValue - s.dayUsd > 0 ? s.dayUsd / (s.accountValue - s.dayUsd) * 100 : null;
        const gap = s.openGainPct !== null && s.marketPct !== null ? s.openGainPct - s.marketPct : null;
        // The one line says what the graph says: the whole account against the starting amount left in an S&P 500 fund since
        // the account began, in dollars. (The breakdown's card is another sum, and says so: only what is still held, against
        // the same dollars in the fund on the days they were put in.) Without the fund's prices back to the start, that card's
        // figure stands here as before.
        const vs = state.holdings.length || state.closed.length ? versusStart(state, quotes, Date.now()) : null, behind = vs ? Math.round(vs.gapUsd * 100) / 100 : 0;
        // The third figure (17 Oct 2026, the owner's idea: "since the start" moved under the account value, which freed the
        // box): how the account stands against the same starting money in an S&P 500 fund, as the graph shows it. Without the
        // fund's prices back to the start it falls back to what is still held against the fund over the same days.
        const start = usd(state.startingCash).replace(/\.00$/, '');
        const fd = vs ? fundDay(quotes, vs.value) : null, usShut = typeof usOpensIn === 'function' && usOpensIn(Date.now()) !== null;
        const fundToday = fd ? `<span class="pp-fund-day">${usShut ? 'Last trading day' : 'Today'} ${movedHtml(fd.usd, fd.pct)}</span><br>` : '';
        // Every big number is about the user's own account (30 Oct 2026, the owner: "everytime i look it i have to think for a minute
        // what is up or down"): the gap to the fund is the big figure, said in words; the fund's own value is the small print.
        const fundCard = vs ? card('Against the S&amp;P 500', behind === 0 ? 'level' : `${big(behind)} <span class="pp-card-word">${behind > 0 ? 'ahead' : 'behind'}</span>`,
            `${behind === 0 ? 'level with' : Math.abs(behind / state.startingCash * 100).toFixed(2) + '% ' + (behind > 0 ? 'ahead of' : 'behind')} the same ${start} put in an S&amp;P 500 fund at the start, which would be ${usd(vs.value)} now${fd ? ` (${usShut ? 'its last trading day' : 'today'} ${movedHtml(fd.usd, fd.pct)})` : ''}`, behind)
            : s.marketPct === null ? card('Against the S&amp;P 500', '–', 'nothing to compare with yet', 0)
            : s.marketFlat ? card('Against the S&amp;P 500', '–', 'no change yet to compare with: the US market has not traded since the buys', 0)
            : card('Against the S&amp;P 500', gap === null ? pctHtml(s.marketPct) : Math.abs(gap) < 0.005 ? 'level' : `${gap > 0 ? '▲' : '▼'} ${Math.abs(gap).toFixed(2)}%`, 'what is still held, against an S&amp;P 500 fund over the same days', gap === null ? 0 : gap);
        const breakdown = document.getElementById('pp-more');
        if (breakdown && typeof breakdown.open === 'boolean') moreOpen = breakdown.open;
        el.innerHTML = `
            <div class="pp-top">
                ${card('Account value', usd(s.accountValue), `${movedHtml(s.gainUsd, s.gainPct)} since it started with ${usd(state.startingCash).replace(/\.00$/, '')} · fake money`, s.gainUsd)}
                ${card(s.dayClosed ? 'Last trading day' : 'Today', s.dayUsd === null ? '–' : big(s.dayUsd), s.dayUsd === null ? 'nothing held' : share(dayOfAccount) + ' of the account · ' + (s.dayClosed ? `its markets are closed now: each holding's last session${s.dayLast ? ' (latest prices ' + esc(when(new Date(s.dayLast).toISOString())) + ')' : ''}` : 'what it holds now'), s.dayUsd === null ? 0 : s.dayUsd)}
                ${fundCard}
            </div>
            <div class="pp-facts">Cash <strong>${usd(s.cash)}</strong> · In holdings <strong>${usd(s.holdingsValue)}</strong></div>
            <details id="pp-more"${moreOpen ? ' open' : ''}><summary>The breakdown: profit and loss, yours and the autopilot’s, and the index fund</summary>
            ${breakdownHtml(s, split)}
            </details>
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
                <button data-pp="buy" class="pp-btn big${busy === 'buy' ? ' busy' : ''}" ${working ? 'disabled' : ''}>${busy === 'buy' ? 'Buying…' : 'Practice buy'}</button>
            </div>
            <div id="pp-notice" style="min-height: 1.2em; font-size: 0.85rem; margin-bottom: 10px; color: ${notice && notice.bad ? '#ef4444' : 'var(--text-secondary)'};">${notice ? esc(notice.text) : 'Enter practice US dollars or a quantity: the other is worked out from the latest price. A buy is recorded at the latest traded price.'}</div>
            ${partLine}${held.length ? `${filterLine}<div style="overflow-x: auto;"><table class="pp-stack" style="width: 100%; border-collapse: collapse; font-size: 0.85rem; color: var(--text-secondary);"><tr class="pp-head">${th(`Holding (${count(held.length, state.holdings.length)})`, 'left')}${th('Bought')}${th('Price then')}${th('Price now')}${th('Value')}${th('Today')}${th('Since bought')}${th('')}</tr>${rows}</table></div>${heldMore}` : state.holdings.length ? '' : '<p style="color: var(--text-secondary); margin: 6px 0 10px;">Nothing held yet. Enter a stock above, or use “Practice buy” on a line of a screener’s Top 10 Performance (🎯).</p>'}
            ${state.closed.length ? `<details id="pp-sold" ${soldOpen ? 'open' : ''} style="margin-top: 12px;"><summary style="cursor: pointer; color: var(--text-primary);">Sold (${count(soldOnes.length, state.closed.length)})</summary>${soldOnes.length ? `<div style="overflow-x: auto;"><table class="pp-stack" style="width: 100%; border-collapse: collapse; font-size: 0.85rem; color: var(--text-secondary);"><tr class="pp-head">${th('Holding', 'left')}${th('Held')}${th('Price')}${th('Value')}${th('Result')}${th('')}</tr>${closed}</table></div>` : `<p style="margin: 8px 0 0; font-size: 0.85rem; color: var(--text-secondary);">None of the ${state.closed.length} sold ${state.closed.length === 1 ? 'is' : 'are'} ${whose}. ${showAll}</p>`}<div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 8px; font-size: 0.8rem; color: var(--text-secondary);"><span>${soldLine}</span>${part ? '' : `<button data-pp="clearsold" class="pp-btn ghost${busy === 'clearsold' ? ' busy' : ''}" title="Empties the sold list. Your practice cash and account value stay as they are" ${working ? 'disabled' : ''}>${busy === 'clearsold' ? 'Clearing…' : 'Clear sold list'}</button>`}</div></details>` : ''}
            ${beside ? '' : `<div id="pp-tools" style="margin-top: 12px;">${toolsHtml()}</div>`}
            <div style="margin-top: 10px; font-size: 0.75rem; color: var(--text-secondary);">
                <span>Fake money for practice: no real trades are placed. ${TRADE_COST_PCT ? `A trading cost of ${TRADE_COST_PCT}% is taken off each practice buy and each sale (a typical figure; real costs vary), so a holding starts a little below what was put in. ` : ''}Prices can be delayed${s.unpriced ? '; ' + s.unpriced + ' holding(s) have no price right now and are shown at cost' : ''}. Other currencies are converted to US dollars. “Today” is what is held now, each holding since its market’s previous close (a coin: since 00:00 UTC) or since it was bought if that was later; while its market is closed it is the last session. A sale made today is not in it. General information only, not financial advice.</span>
            </div>`;
        if (beside) beside.innerHTML = toolsHtml();
        restoreFolds(el);
        keepReadHeight();
    }

    function say(text, bad) { notice = text ? { text, bad: !!bad } : null; }
    // The breakdown, as a broker's statement reads: one table of profit and loss (what was sold is made or lost for good; what
    // is still held is on paper, at the latest prices), whose it is in columns, the total in the last row; then where the
    // money is now, and the index fund in words. Until 17 Oct 2026 this was four cards and a row: the same figure appeared
    // twice with two different percentages (today on the account and on the holdings), which the owner read as a fault.
    function breakdownHtml(s, split) {
        const cols = split.any ? [['Your own buys', 'yours'], ['🤖 AI autopilot', 'auto'], ['Together', 'all']] : [['', 'all']];
        const part = { sold: { yours: split.yoursSold, auto: split.autoSold, all: s.gainUsd - s.openGainUsd },
                       held: { yours: split.yoursOpen, auto: split.autoOpen, all: s.openGainUsd },
                       total: { yours: split.yours, auto: split.auto, all: s.gainUsd } };
        const head = (t, align) => `<th style="padding: 6px; text-align: ${align || 'right'}; font-weight: 600; white-space: nowrap;">${t}</th>`;
        const row = (key, name, note) => `<tr class="pp-pl-${key}"><td class="pp-name" style="padding: 7px 6px; text-align: left;"><strong style="color: var(--text-primary);">${name}</strong><div class="pp-pl-note">${note}</div></td>${cols.map(([label, k]) => `<td data-label="${label || 'Result'}" style="padding: 7px 6px; text-align: right; white-space: nowrap;">${movedHtml(part[key][k])}</td>`).join('')}</tr>`;
        const table = `<div style="overflow-x: auto;"><table class="pp-stack pp-pl" style="width: 100%; border-collapse: collapse; font-size: 0.88rem; color: var(--text-secondary);"><tr class="pp-head">${head('Profit and loss', 'left')}${cols.map(([label]) => head(label || 'Result')).join('')}</tr>
            ${row('sold', 'Sold', 'made or lost for good')}${row('held', 'Still held', 'on paper, at the latest prices')}${row('total', 'Since the start', 'the two together')}</table></div>`;
        const where = `<div class="pp-pl-line">Where the money is: cash <strong>${usd(s.cash)}</strong> · in holdings <strong>${usd(s.holdingsValue)}</strong>${s.openGainPct === null ? '' : ` (${usd(s.cost)} was put in)`} · together <strong>${usd(s.accountValue)}</strong>, the account value.</div>`;
        const vs = state.holdings.length || state.closed.length ? versusStart(state, quotes, Date.now()) : null;
        // two sums, said apart: the whole account since the start (as the graph), and only what is still held (it can point the other way)
        const whole = vs ? `<li><strong>The whole account:</strong> the same ${usd(state.startingCash)} put into the fund when the account began would be ${usd(vs.value)} now (${movedHtml(vs.gainUsd)}), so the account is <strong>${Math.abs(vs.gapUsd) < 0.005 ? 'level with it' : (vs.gapUsd > 0 ? 'ahead of it' : 'behind it') + ' by ' + usd(Math.abs(vs.gapUsd)) + ' (' + Math.abs(vs.gapUsd / state.startingCash * 100).toFixed(2) + '%)'}</strong>.</li>` : '';
        const held = s.marketPct === null ? '' : s.marketFlat ? `<li><strong>What is still held:</strong> nothing to compare yet, <span id="pp-us-opens">${esc(marketWait())}</span>.</li>`
            : `<li><strong>What is still held:</strong> ${pctHtml(s.openGainPct)} since it was bought; the same dollars in the fund on the same days ${pctHtml(s.marketPct)}${versusFund(s)}</li>`;
        const fund = whole || held ? `<div class="pp-pl-line" id="pp-pl-fund">Against an S&amp;P 500 index fund:<ul>${whole}${held}</ul></div>` : '';
        return table + where + fund;
    }
    // The card shows what the fund did; said beside it, in words, is how the holdings did against that. Without this the fund's
    // "▲ 0.06%" was read as the account being ahead of the fund (the owner, 12 Oct 2026).
    function versusFund(s) {
        if (s.openGainPct === null || s.marketPct === null) return '';
        const d = s.openGainPct - s.marketPct;
        // Only what is still held, against the same dollars in the fund on the days they were put in: it can point the other way
        // from the sentence before it (the whole account since the start), so it says which it is.
        return `, so it is ${Math.abs(d) < 0.005 ? 'level with the fund' : `<strong>${d > 0 ? 'ahead of' : 'behind'} the fund by ${Math.abs(d).toFixed(2)}%</strong>`}. What was sold is not in this one.`;
    }
    // Why the "For comparison" card has nothing to show yet, with when that changes. The dashboard's sidebar counts down to
    // the US opening: its own figure is used when it is on the page, so the card and the sidebar can never disagree.
    function marketWait() {
        const status = document.getElementById('market-status-sidebar'), count = document.getElementById('market-countdown-sidebar');
        const shown = status && count && /\d/.test(count.textContent || '') ? (/open in/i.test(status.textContent || '') ? count.textContent.trim() : null) : usOpensIn(Date.now());
        return shown ? `the US stock market has not traded since you bought (it opens in ${shown})` : 'the US stock market has not moved since you bought';
    }
    // "Refresh prices" and "Reset fake money", with the time of the prices on show. They sit beside the section's heading
    // (the page has a place for them, #pp-tools) so that nobody has to scroll down to them; on a phone, under the heading.
    function toolsHtml() {
        const time = pricesAt ? new Date(pricesAt).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
        const line = busy === 'refresh' ? 'Getting the latest prices…' : !time ? '' : flash ? '✓ Prices updated ' + time : 'Prices as of ' + time;
        return `<span class="pp-updated${flash && busy !== 'refresh' ? ' fresh' : ''}" id="pp-updated" role="status">${esc(line)}</span>
                <button data-pp="refresh" class="pp-btn ghost${busy === 'refresh' ? ' busy' : ''}" ${working ? 'disabled' : ''}>${busy === 'refresh' ? 'Refreshing…' : '↻ Refresh prices'}</button>
                <button data-pp="reset" class="pp-btn ghost${busy === 'reset' ? ' busy' : ''}" title="Clears every practice holding and the sold list and puts the fake money back to ${usd(STARTING_CASH)}" ${working ? 'disabled' : ''}>${busy === 'reset' ? 'Resetting…' : 'Reset fake money'}</button>`;
    }
    // ---------------------------------------------------------------- the graph of the account over time
    const DAYMS = 86400000;
    const CHART_RANGES = { day: ['1d', DAYMS], week: ['1w', 7 * DAYMS], month: ['1m', 30 * DAYMS], m3: ['3m', 91 * DAYMS], m6: ['6m', 182 * DAYMS],
                           y1: ['1y', 365 * DAYMS], y2: ['2y', 730 * DAYMS], y5: ['5y', 1826 * DAYMS], y10: ['10y', 3652 * DAYMS], all: ['All', 0] };
    // chartKey: which line (the account, the user's own buys, the autopilot's). The same choice says whose holdings the two
    // lists under the graph show (partOf). It is kept while the page is open (a refresh of prices leaves it) and is not
    // remembered: a page opened afresh shows the whole account. chartRange (how far back) is remembered in the browser.
    let chartKey = 'value', chartRange = 'all';
    let readTallest = 0;
    // The read-out above the picture keeps the tallest height it has had (three lines for the whole account), so pressing
    // "Your own buys" or "AI autopilot" does not move the picture up (24 Oct 2026, the owner: "things move alot")
    function keepReadHeight() {
        const read = document.getElementById('pp-chart-read');
        // rounded up: offsetHeight rounds 66.3 down to 66, so the taller read-out still moved the picture by a fraction (26 Oct 2026)
        if (read && read.offsetHeight) { readTallest = Math.max(readTallest, Math.ceil(read.getBoundingClientRect().height)); read.style.minHeight = readTallest + 'px'; }
    }
    // 'g:<market>' / 's:<screener>': one market's part of the autopilot (the menu beside the buttons, 23 Oct 2026). screenerInfo:
    // the screeners' names and markets, handed over by the autopilot panel (setPlans); without it there is no menu.
    let screenerInfo = null, mktOpen = false, indexWait = false, indexAt = 0;
    // the screeners' own indexes: asked for only when the market list is opened, then at most every 15 minutes
    function ensureIndexes() {
        if (!state || indexWait || Date.now() - indexAt < 15 * 60000) return;
        const want = new Set();
        state.holdings.concat(state.closed).forEach(h => { if (h.by === 'ai' && HOME_INDEX[h.screener]) want.add(HOME_INDEX[h.screener][0]); });
        if (!want.size) return;
        indexWait = true; indexAt = Date.now();
        const span = fundRange(state.createdAt, Date.now());
        Promise.all([...want].map(sym => fetchQuote(sym, span).then(q => { if (q) quotes[sym] = q; }).catch(() => {})))
            .then(() => { indexWait = false; if (!working) redraw(); });
    }
    const isMarket = (k) => /^[gs]:/.test(String(k || ''));
    const marketLabel = (k) => { const r = state ? marketResults(state, quotes, screenerInfo)[k] : null; return r ? r.label : String(k).slice(2); };
    let drag = null, measured = null;              // a click and drag across the graph, and the stretch it measured (showMeasure)
    let chartNow = null;                             // where each point sits in the picture on show: the pointer reads values off it
    try {
        localStorage.removeItem('stockiqPracticeChartRange');    // remembered until 24 Oct 2026: a page opened afresh shows All, as it shows All markets
        localStorage.removeItem('stockiqPracticeChartKey');      // remembered until 13 Oct 2026
    } catch (e) { /* a private window: the choice is simply not remembered */ }
    // The line above the picture: a moment, the figure then, and the change
    function chartRead(point) {
        const moment = `<span class="pp-chart-when">${esc(new Date(point.t).toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }))}</span>`;
        if (chartKey !== 'value' && typeof point.f === 'number') {
            // one market: its result, and the same dollars in an S&P 500 fund on the same days
            const gap = Math.round((point.v - point.f) * 100) / 100;
            const verdict = gap === 0 ? 'level with it' : `<strong style="color: ${tone(gap)}; white-space: nowrap;">${gap > 0 ? 'ahead of' : 'behind'} it by ${usd(Math.abs(gap))}</strong>`;
            return `<div>${moment}</div>
            <div class="pp-chart-row"><span class="pp-chart-who"><span class="pp-key" aria-hidden="true"></span>${chartKey === 'ai' ? '🤖 The autopilot’s buys, every market' : chartKey === 'own' ? 'Your own buys' : /^s:/.test(chartKey) ? `🤖 The autopilot’s buys from the ${esc(marketLabel(chartKey))} screener` : `🤖 The autopilot’s buys in ${esc(marketLabel(chartKey))}`}</span><span>${movedHtml(point.v)}</span></div>
            <div class="pp-chart-row"><span class="pp-chart-who"><span class="pp-key fund" aria-hidden="true"></span>The same money in an S&amp;P 500 fund, same days</span><span>${movedHtml(point.f)} · ${verdict}</span></div>`;
        }
        if (chartKey !== 'value') return `${moment}${movedHtml(point.v)}`;
        const cash = state ? state.startingCash : STARTING_CASH, share = (n) => n / cash * 100;
        const account = `<strong>${usd(point.v)}</strong> ${movedHtml(point.all, share(point.all))} since the start`;
        if (typeof point.f !== 'number') return moment + account;
        // Two lines, each led by its colour: they are the graph's key as well. Who is ahead is said in words, in dollars.
        const gap = Math.round((point.v - point.f) * 100) / 100;
        const verdict = gap === 0 ? 'your account is level with it' : `your account is <strong style="color: ${tone(gap)}; white-space: nowrap;">${gap > 0 ? 'ahead of' : 'behind'} it by ${usd(Math.abs(gap))} (${Math.abs(share(gap)).toFixed(2)}%)</strong>`;
        return `<div>${moment}</div>
            <div class="pp-chart-row"><span class="pp-chart-who"><span class="pp-key" aria-hidden="true"></span>Your account</span><span>${account}</span></div>
            <div class="pp-chart-row"><span class="pp-chart-who"><span class="pp-key fund" aria-hidden="true"></span>The same ${usd(cash).replace(/\.00$/, '')} in an S&amp;P 500 fund</span><span><strong>${usd(point.f)}</strong> ${movedHtml(point.f - cash, share(point.f - cash))} · ${verdict}</span></div>`;
    }
    function chartHtml() {
        if (!state || !(state.holdings.length || state.closed.length)) return '';
        const now = Date.now(), age = now - (Date.parse(state.createdAt) || now);
        const ranges = Object.keys(CHART_RANGES), longer = (r) => r !== 'all' && age < CHART_RANGES[r][1];   // longer than the account's life: greyed
        if (!CHART_RANGES[chartRange] || longer(chartRange)) chartRange = 'all';
        const series = valueSeries(state, quotes, now, autoRealized, chartRange === 'all' ? 0 : now - CHART_RANGES[chartRange][1], isMarket(chartKey) ? pickOf(chartKey, screenerInfo) : chartKey === 'ai' ? (h) => h.by === 'ai' : chartKey === 'own' ? (h) => h.by !== 'ai' : null);      // 'ai' / 'own': each part's buys, with the fund's line beside them (26 Oct 2026)
        if (!series.anyAi) chartKey = 'value';
        const el = box(), width = Math.min(1100, Math.max(260, ((el && el.clientWidth) || 750) - 30));
        const picture = chartSvg(series, chartKey !== 'value' ? 'part' : chartKey, width, width < 480 ? 180 : 220);
        chartNow = { placed: picture.placed, width: picture.width };
        const tab = (kind, id, text, on) => `<button type="button" data-pp="chart-${kind}" data-id="${id}" aria-pressed="${on}">${text}</button>`;
        const kinds = series.anyAi ? [['value', 'All markets'], ['own', 'Your own buys'], ['ai', '🤖 AI autopilot']] : [];
        const title = chartKey === 'value' ? 'Account value over time' : chartKey === 'ai' ? 'The autopilot’s result over time' : isMarket(chartKey) ? esc(marketLabel(chartKey)) + ': result over time' : 'Your own buys: result over time';
        // The menu of markets and their screeners, each with its result against the same dollars in an S&P 500 fund on the same days
        const results = series.anyAi && screenerInfo ? marketResults(state, quotes, screenerInfo) : null;
        // Its own list, not a plain menu: a plain one cannot colour part of a line, and phones and Macs show it without colour. Each row:
        // what was put in, the result since then, and against the same money in an S&P 500 fund on the same days, the last coloured
        // (green ahead, red behind: the owner's goal is to beat the S&P 500). Ahead first, the largest lead at the top (23 Oct 2026).
        const vsHtml = (r) => {
            if (r.aheadUsd === null) return '<span class="pp-vs">–</span>';
            const a = Math.round(r.aheadUsd);
            return a === 0 ? '<span class="pp-vs">level</span>' : `<span class="pp-vs ${a > 0 ? 'up' : 'down'}">${a > 0 ? '▲' : '▼'} ${usd(Math.abs(a)).replace(/\.00$/, '')} (${Math.abs(r.aheadPct).toFixed(1)}%) ${a > 0 ? 'ahead' : 'behind'}</span>`;
        };
        const row = (r, sub) => `<button type="button" class="pp-mkt-row${sub ? ' sub' : ''}${chartKey === r.key ? ' on' : ''}" data-pp="market" data-id="${esc(r.key)}" aria-pressed="${chartKey === r.key}">`
            + `<span class="pp-mkt-name">${esc(r.label)}<small>${r.trades} ${r.trades === 1 ? 'holding' : 'holdings'}${r.held ? `, ${r.held} still held` : ''}</small></span>`
            + `<span class="pp-mkt-in" data-label="Total bought">${usd(r.cost).replace(/\.\d\d$/, '')}</span><span class="pp-mkt-res" data-label="Result">${movedHtml(r.gainUsd, r.cost ? r.gainUsd / r.cost * 100 : null)}</span>`
            + `<span class="pp-mkt-vs" data-label="Against the S&amp;P 500">${vsHtml(r)}${homeHtml(r)}</span></button>`;
        // its own index, in its own currency: smaller and grey under the S&P 500's badge (the S&P stays the figure to decide by)
        const homeHtml = (r) => {
            if (!r.homeable) return '';                                   // coins and the sector funds have no home index
            if (r.homePct === null) return indexWait ? '<small class="pp-home">its own index: …</small>' : '';
            const p = Math.round(r.homePct * 10) / 10, who = r.homeNames.length === 1 ? 'the ' + esc(r.homeNames[0]) : 'their own indexes';
            return `<small class="pp-home">against ${who}: ${p > 0 ? '▲ ' : p < 0 ? '▼ ' : ''}${Math.abs(p).toFixed(1)}%${r.homeAll ? '' : ' (part)'}</small>`;
        };
        if (mktOpen) ensureIndexes();
        const order = (a, b) => (b.aheadUsd === null ? -1e12 : b.aheadUsd) - (a.aheadUsd === null ? -1e12 : a.aheadUsd);
        const menu = !results ? '' : (() => {
            const groups = Object.values(results).filter(r => r.key[0] === 'g').sort(order);
            // How the rows add up to the account's own gap to the fund (the owner checked the sum, 23 Oct 2026): the markets, the
            // user's own buys, and money not invested while the fund moved (cash, and the time before a buy) make the account's gap.
            const vs = versusStart(state, quotes, Date.now()), own = results.own;
            const parts = groups.concat(own ? [own] : []);
            const covered = parts.every(r => r.aheadUsd !== null && r.compared >= r.cost - 0.01);
            const idle = vs && covered ? vs.gapUsd - parts.reduce((n, r) => n + r.aheadUsd, 0) : null;
            const sumRow = (label, sub, amount, key) => `<${key !== undefined ? `button type="button" data-pp="market" data-id="${key}"` : 'div'} class="pp-mkt-row sumrow${key === 'value' && !isMarket(chartKey) && chartKey === 'value' ? ' on' : ''}"><span class="pp-mkt-name">${label}<small>${sub}</small></span><span class="pp-mkt-in"></span><span class="pp-mkt-res"></span><span class="pp-mkt-vs">${vsHtml({ aheadUsd: amount, aheadPct: Math.abs(amount) / (state.startingCash || STARTING_CASH) * 100 })}</span></${key !== undefined ? 'button' : 'div'}>`;
            // the totals, on the first row (23 Oct 2026, the owner: "this will be the main thing i always look at"): every buy, the account's
            // result since the start, and the account against the same money in an S&P 500 fund since the start
            const bought = state.holdings.concat(state.closed).reduce((n, h) => n + (h.costUsd || 0), 0), start = state.startingCash || STARTING_CASH;
            const gainAll = summarize(state, quotes).accountValue - start;
            // Every market's holdings together, on the same holdings both ways (30 Oct 2026, the owner: "so i can see overall if ... the s&p
            // beats holding vs holding in all indicies"): against an S&P 500 fund on the same days, and against each holding's own index
            const sumOf = (k) => groups.reduce((n, r) => n + (r[k] || 0), 0), spPct = sumOf('compared') > 0 ? (sumOf('gainCompared') - sumOf('fundUsd')) / sumOf('compared') * 100 : null;
            const hmPct = sumOf('homeCost') > 0 ? sumOf('homeGap') / sumOf('homeCost') * 100 : null, sign = (p) => `${p > 0.05 ? '▲ ' : p < -0.05 ? '▼ ' : ''}${Math.abs(p).toFixed(1)}%`;
            const bothHtml = spPct === null ? '' : `<small class="pp-home">the autopilot’s holdings: against the S&amp;P 500 ${sign(spPct)}${hmPct === null ? (indexWait ? ' · their own indexes: …' : '') : ` · against their own indexes ${sign(hmPct)}${sumOf('homeCost') >= sumOf('homeable') - 0.01 ? '' : ' (part)'}`}</small>`;
            const allRow = `<button type="button" class="pp-mkt-row all total${isMarket(chartKey) ? '' : ' on'}" data-pp="market" data-id="" aria-pressed="${!isMarket(chartKey)}"><span class="pp-mkt-name">All markets<small>the whole account since the start, against the same ${usd(start).replace(/\.00$/, '')} in an S&amp;P 500 fund</small></span>`
                + `<span class="pp-mkt-in" data-label="Total bought">${usd(bought).replace(/\.\d\d$/, '')}</span><span class="pp-mkt-res" data-label="Result">${movedHtml(gainAll, gainAll / start * 100)}</span>`
                + `<span class="pp-mkt-vs" data-label="Against the S&amp;P 500">${vs ? vsHtml({ aheadUsd: vs.gapUsd, aheadPct: Math.abs(vs.gapUsd) / start * 100 }) : '–'}${bothHtml}</span></button>`;
            const tally = vs && idle !== null ? `<div class="pp-mkt-tally"><div class="pp-mkt-sum" style="margin-top: 6px;"><strong>How they add up</strong> (the percentages against the S&amp;P 500 here are of the ${usd(state.startingCash).replace(/\.00$/, '')} it started with)</div>`
                + sumRow('The autopilot’s markets', 'the rows above, added up', groups.reduce((n, r) => n + r.aheadUsd, 0))
                + (own ? row(Object.assign({}, own, { label: 'Your own buys', aheadPct: own.aheadUsd / (state.startingCash || STARTING_CASH) * 100 }), false) : '')
                + sumRow('Money kept as cash', `cash does not move; ${(versusStart(state, quotes, Date.now()) || {}).gainUsd < 0 ? 'the fund fell while this money waited, so this part is ahead of it' : 'the fund rose while this money waited, so this part is behind it'} (the time before each buy, and money not yet put back in after a sale)`, idle)
                + sumRow('All markets together', `the whole account, against the same ${usd(state.startingCash).replace(/\.00$/, '')} in an S&amp;P 500 fund since the start: the three lines above added up`, vs.gapUsd, 'value')
                + `</div>` : '';
            const subs = (g) => Object.values(results).filter(r => r.key[0] === 's' && r.group === g.group).sort(order);
            const all = Object.values(results).filter(r => r.key[0] === 's' && r.aheadUsd !== null), up = all.filter(r => Math.round(r.aheadUsd) > 0), down = all.filter(r => Math.round(r.aheadUsd) < 0);
            const total = (list) => usd(Math.abs(list.reduce((n, r) => n + r.aheadUsd, 0))).replace(/\.\d\d$/, '');
            const few = Object.values(results).filter(r => r.trades < 30).length;
            const now = isMarket(chartKey) && results[chartKey] ? results[chartKey] : null;
            return `<div class="pp-mkt${mktOpen ? ' open' : ''}" id="pp-mkt">
                <button type="button" class="pp-mkt-btn" data-pp="mkt-toggle" aria-expanded="${mktOpen}">By market: <strong>${now ? esc(now.label) : chartKey === 'own' ? 'Your own buys' : 'All markets'}</strong>${now ? ' ' + vsHtml(now) : ''} <span aria-hidden="true">▾</span></button>
                <div class="pp-mkt-panel"${mktOpen ? '' : ' hidden'}>
                    <div class="pp-mkt-sum">Against the S&amp;P 500, screener by screener: <span class="pp-vs up">${up.length} ahead, by ${total(up)} together</span> · <span class="pp-vs down">${down.length} behind, by ${total(down)}</span>.${few ? ` <strong>Under 30 holdings is too few to tell skill from luck.</strong>` : ''} <details class="pp-mkt-how"><summary>How it is worked out</summary>Each holding is set against the same money put into an S&amp;P 500 fund the day it was bought and taken out the day it was sold (or now), with no trading cost taken off the fund; sold and still held together, ahead first. "Total bought" adds up every buy: the money from a sale is used again for the next buy, so it keeps growing whether the trades win or lose (it is not money lost or at risk). The result's percent is of it: what each dollar traded made on average. The grey line is each holding against its own market's index (an ASX share against the ASX 200), in that market's own currency, so a currency's move is left out: it says whether the picks did better than their market, while the S&amp;P 500 figure says whether the market was worth the money. The index's price at the moment of a buy or a sale is read between its daily closes, so that line is an approximation.</details></div>
                    <div class="pp-mkt-head" aria-hidden="true"><span>Market and screener</span><span>Total bought</span><span>Result</span><span>Against the S&amp;P 500</span></div>
                    ${allRow}
                    ${groups.map(g => row(g, false) + (subs(g).length > 1 ? subs(g).map(r => row(r, true)).join('') : '')).join('')}
                    ${tally}
                </div></div>`;
        })();
        const chosen = isMarket(chartKey) && results ? results[chartKey] : null;
        const partNote = !chosen ? '' : ` This market: ${chosen.sold} sold and ${chosen.held} still held, ${usd(chosen.cost).replace(/\.\d\d$/, '')} bought in total, ${moved(chosen.gainUsd)} in all${chosen.aheadUsd === null ? '' : `; the same dollars in an S&amp;P 500 fund, bought and sold on the same days, would have ${chosen.fundUsd >= 0 ? 'made' : 'lost'} ${usd(Math.abs(chosen.fundUsd))}`}. The gold line is that fund money.${chosen.trades < 30 ? ` <strong>${chosen.trades} ${chosen.trades === 1 ? 'holding is' : 'holdings are'} too few to tell skill from luck</strong> (about 30 are needed).` : ''}`;
        // the figures behind the picture, a line a day (the last moment of each day)
        const perDay = {};
        series.points.forEach(point => { perDay[new Date(point.t).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })] = point; });
        const against = (point) => { const gap = Math.round((point.value - point.fund) * 100) / 100; return gap === 0 ? 'level' : `<span style="color: ${tone(gap)}; font-weight: 600;">${gap > 0 ? 'ahead' : 'behind'} by <span style="white-space: nowrap;">${usd(Math.abs(gap))}</span></span>`; };
        const allRows = Object.entries(perDay).slice(-60).reverse().map(([day, point]) => `<tr><td>${esc(day)}</td><td>${usd(point.value)}</td><td${picture.fund ? ' class="pp-fig-part"' : ''}>${movedHtml(point.all)}</td>${picture.fund ? `<td class="pp-fig-part">${usd(point.fund)}</td><td class="pp-fig-vs">${against(point)}</td>` : ''}${series.anyAi ? `<td class="pp-fig-part">${movedHtml(point.own)}</td><td class="pp-fig-part">${movedHtml(point.ai)}</td>` : ''}</tr>`);
        // the newest 14 days (7 on a phone), then a button for the rest (24 Oct 2026, the owner: a long list should have a "show more")
        const figsShown = (typeof window !== 'undefined' && window.innerWidth < 640) ? 7 : 14;
        const hiddenRows = Math.max(0, allRows.length - figsShown);
        const rows = (figsAll ? allRows : allRows.slice(0, figsShown)).join('');
        const undated = Math.abs(series.undated) > 0.5 ? ` The result of sold holdings that are no longer in the list (${moved(series.undated)}) has no dates left, so it is counted from the start.` : '';
        return `<div class="pp-chart">
            <div class="pp-chart-head"><span class="pp-chart-title">${title}</span><span class="pp-chart-tabs">${kinds.map(([id, text]) => tab('key', id, text, chartKey === id)).join('')}${ranges.filter(r => !longer(r)).map(r => tab('range', r, CHART_RANGES[r][0], chartRange === r)).join('')}</span>${menu}</div>
            <div class="pp-chart-read" id="pp-chart-read"${readTallest ? ` style="min-height: ${readTallest}px"` : ''}>${chartRead(picture.placed[picture.placed.length - 1])}</div>
            ${picture.svg}
            <div class="pp-chart-note">Fake money. Dashed line: ${chartKey === 'value' ? 'the ' + usd(state.startingCash) + ' it started with' : 'no gain or loss'}. A holding still held is valued at its daily prices and its latest price now; one that was sold is drawn as a straight line from buying to selling.${(chartKey === 'ai' || chartKey === 'own') && picture.fund ? ` The gold line is the same money put into an S&amp;P 500 fund on the day each ${chartKey === 'ai' ? 'of the autopilot’s holdings' : 'of your own buys'} was bought and taken out the day it was sold (or now), with no trading cost taken off the fund and no dividends counted. ${chartKey === 'ai' ? 'Your own buys are not in this view.' : 'The autopilot’s buys are not in this view.'}` : ''}${picture.fund && chartKey === 'value' ? ` The S&amp;P 500 line is the same ${usd(state.startingCash).replace(/\.00$/, '')} put into an S&amp;P 500 index fund (SPY) at the moment this account began and left there, at the fund’s daily closing prices, with no trading cost taken off and no dividends counted.` : ''}${isMarket(chartKey) ? partNote : undated}</div>
            <details id="pp-figs"><summary style="cursor: pointer;">Show the figures</summary><div style="overflow-x: auto;"><table><tr><th>End of</th><th>Account</th><th${picture.fund ? ' class="pp-fig-part"' : ''}>Since the start</th>${picture.fund ? '<th class="pp-fig-part">S&amp;P 500 fund</th><th class="pp-fig-vs">Against the fund</th>' : ''}${series.anyAi ? '<th class="pp-fig-part">Your own buys</th><th class="pp-fig-part">AI autopilot</th>' : ''}</tr>${rows}</table>${hiddenRows ? `<button type="button" class="pp-btn ghost" data-pp="figs-all" style="margin-top: 6px;">${figsAll ? 'Show only the latest ' + figsShown : 'Show all ' + allRows.length + ' days (' + hiddenRows + ' more)'}</button>` : ''}</div></details>
        </div>`;
    }
    // The market list opens on the row that is chosen, not at its top (26 Oct 2026, the owner): it stands a third of the way down
    function showChosen() {
        const panel = document.querySelector && document.querySelector('#pp-mkt .pp-mkt-panel'), on = panel && panel.querySelector('.pp-mkt-row.on');
        if (!panel || !on || !on.getBoundingClientRect) return;
        const at = on.getBoundingClientRect().top - panel.getBoundingClientRect().top + panel.scrollTop;
        panel.scrollTop = Math.max(0, at - panel.clientHeight / 3);
    }
    function drawChart() {
        const slot = document.getElementById('pp-chart');
        if (!slot || !state || !loaded) return;
        const p0 = document.querySelector && document.querySelector('#pp-mkt .pp-mkt-panel'), listAt = p0 ? p0.scrollTop : 0;
        const pageAt = typeof window !== 'undefined' && typeof window.scrollY === 'number' ? window.scrollY : null;
        slot.style.minHeight = slot.offsetHeight ? slot.offsetHeight + 'px' : '';      // no collapse while it is drawn again
        slot.innerHTML = chartHtml();
        restoreFolds(slot);
        slot.style.minHeight = '';
        keepReadHeight();
        const p1 = document.querySelector && document.querySelector('#pp-mkt .pp-mkt-panel'); if (p1 && listAt) p1.scrollTop = listAt;
        reMeasure();
        if (pageAt !== null && window.scrollY !== pageAt && window.scrollTo) window.scrollTo(0, pageAt);
    }
    // The pointer over the picture: a line at that moment, and its figures above
    function chartShow(point, crossed) {
        const cross = document.getElementById('pp-cross'), dot = document.getElementById('pp-dot'), read = document.getElementById('pp-chart-read');
        if (cross) { cross.setAttribute('x1', point.x); cross.setAttribute('x2', point.x); cross.style.display = crossed ? '' : 'none'; }
        if (dot) { dot.setAttribute('cx', point.x); dot.setAttribute('cy', point.y); }
        const fundDot = document.getElementById('pp-dot-fund');
        if (fundDot && typeof point.fy === 'number') { fundDot.setAttribute('cx', point.x); fundDot.setAttribute('cy', point.fy); }
        if (read) read.innerHTML = chartRead(point);
    }
    function chartPoint(e) {
        const svg = e.target && e.target.closest && e.target.closest('#pp-chart-svg');
        if (!svg || !chartNow) return;
        const rect = svg.getBoundingClientRect(), touch = e.touches && e.touches[0];
        const at = ((touch ? touch.clientX : e.clientX) - rect.left) * chartNow.width / (rect.width || chartNow.width);
        let best = chartNow.placed[0];
        chartNow.placed.forEach(point => { if (Math.abs(point.x - at) < Math.abs(best.x - at)) best = point; });
        if (measured) return;                 // a stretch measured stays until the graph is clicked again
        hideMeasure();
        chartShow(best, true);
    }
    // Hold and drag across the graph (a finger on a phone): while held, the change between the two moments, for the line on show and for the
    // S&P 500 fund over the same stretch (26 Oct 2026, the owner: "click and drag across, to show the % change between")
    function nearestAt(e) {
        const svg = document.getElementById('pp-chart-svg');
        if (!svg || !chartNow) return null;
        const rect = svg.getBoundingClientRect(), touch = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0]);
        const at = ((touch ? touch.clientX : e.clientX) - rect.left) * chartNow.width / (rect.width || chartNow.width);
        let best = chartNow.placed[0];
        chartNow.placed.forEach(point => { if (Math.abs(point.x - at) < Math.abs(best.x - at)) best = point; });
        return best;
    }
    function measureRead(a, b) {
        if (b.t < a.t) [a, b] = [b, a];
        const when = (t) => new Date(t).toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
        const days = (b.t - a.t) / 864e5, span = days >= 1.5 ? Math.round(days) + ' days' : Math.max(1, Math.round(days * 24)) + ' hours';
        const isValue = chartKey === 'value', share = (d, base) => isValue && base > 0 ? d / base * 100 : null;
        const who = isValue ? 'Your account' : isMarket(chartKey) ? (/^s:/.test(chartKey) ? `🤖 The autopilot’s buys from the ${esc(marketLabel(chartKey))} screener` : `🤖 The autopilot’s buys in ${esc(marketLabel(chartKey))}`) : chartKey === 'ai' ? '🤖 AI autopilot' : 'Your own buys';
        const dv = b.v - a.v;
        let out = `<div><span class="pp-chart-when">${esc(when(a.t))} → ${esc(when(b.t))} (${span})</span></div>
            <div class="pp-chart-row"><span class="pp-chart-who"><span class="pp-key" aria-hidden="true"></span>${who}</span><span>${movedHtml(dv, share(dv, a.v))} over this stretch</span></div>`;
        if (typeof a.f === 'number' && typeof b.f === 'number') {
            const df = b.f - a.f, gap = Math.round((dv - df) * 100) / 100;
            const fund = isValue ? `The same ${usd(state ? state.startingCash : STARTING_CASH).replace(/\.00$/, '')} in an S&amp;P 500 fund` : 'The same money in an S&amp;P 500 fund, same days';
            const verdict = gap === 0 ? 'level with it' : `<strong style="color: ${tone(gap)}; white-space: nowrap;">${gap > 0 ? 'ahead of' : 'behind'} it by ${usd(Math.abs(gap))}${isValue && a.v > 0 ? ' (' + Math.abs(gap / a.v * 100).toFixed(2) + '%)' : ''}</strong>`;
            out += `<div class="pp-chart-row"><span class="pp-chart-who"><span class="pp-key fund" aria-hidden="true"></span>${fund}</span><span>${movedHtml(df, share(df, a.f))} · ${verdict}</span></div>`;
        }
        return out;
    }
    function showMeasure(a, b) {
        const band = document.getElementById('pp-band'), start = document.getElementById('pp-cross-a'), read = document.getElementById('pp-chart-read');
        if (!band || !read) return;
        const [p, q] = a.t <= b.t ? [a, b] : [b, a], up = q.v - p.v;
        band.setAttribute('x', Math.min(a.x, b.x)); band.setAttribute('width', Math.max(1, Math.abs(b.x - a.x)));
        band.setAttribute('class', 'pp-band' + (up > 0.004 ? ' up' : up < -0.004 ? ' down' : '')); band.style.display = '';
        if (start) { start.setAttribute('x1', a.x); start.setAttribute('x2', a.x); start.style.display = ''; }
        chartShow(b, true);
        read.innerHTML = measureRead(a, b);
        keepReadHeight();
    }
    function hideMeasure() {
        ['pp-band', 'pp-cross-a'].forEach(id => { const el = document.getElementById(id); if (el) el.style.display = 'none'; });
    }
    // the graph is drawn again every minute with fresh prices: a stretch measured is put back on the same two moments
    function reMeasure() {
        if (!measured || !chartNow) return;
        const find = (t) => chartNow.placed.find(p => p.t === t);
        const a = find(measured.a.t), b = find(measured.b.t);
        if (a && b) { measured = { a, b }; showMeasure(a, b); } else measured = null;
    }
    function dragStart(e) {
        if (e.button > 0 || !(e.target && e.target.closest && e.target.closest('#pp-chart-svg'))) return;
        const a = nearestAt(e);
        if (!a) return;
        const touch = e.touches && e.touches[0];
        drag = { a, b: a, x0: touch ? touch.clientX : e.clientX, moved: false };
        if (measured) { measured = null; hideMeasure(); }
        if (!touch) e.preventDefault();       // no text selected while dragging
        chartShow(a, true);
    }
    function dragMove(e) {
        if (!drag) return false;
        const touch = e.touches && e.touches[0], x = touch ? touch.clientX : e.clientX;
        if (!drag.moved && Math.abs(x - drag.x0) < (touch ? 10 : 5)) return true;
        drag.moved = true;
        const b = nearestAt(e);
        if (b) { drag.b = b; showMeasure(drag.a, b); }
        return true;
    }
    // let go and it clears, as broker apps do (26 Oct 2026, the owner): the read-out goes back to the moment under the pointer
    function dragEnd() {
        if (!drag) return;
        const b = drag.b;
        drag = null; measured = null;
        hideMeasure();
        chartShow(b, true);
    }

    async function run(task, key) {
        if (working) return;
        // keep what is typed while the section is redrawn
        const keep = ['pp-symbol', 'pp-amount', 'pp-qty', 'pp-note'].map(id => [id, document.getElementById(id) ? document.getElementById(id).value : null]);
        const restore = () => keep.forEach(([id, v]) => { const el = document.getElementById(id); if (el && v !== null) el.value = v; });
        const showClear = () => { const c = document.getElementById('pp-clear'), b = document.getElementById('pp-symbol'); if (c && b) c.style.display = b.value ? 'block' : 'none'; };
        working = true; busy = key || null; render(); restore(); showClear();
        let ok = false;
        try { await task(); ok = true; } catch (e) { say(e.message, true); }
        working = false; busy = null; render(); flash = false;
        // what is typed in the buy row stays, unless the buy went through or the account was reset (a refresh of prices used to wipe it)
        if (!ok || (key !== 'buy' && key !== 'reset')) { restore(); showClear(); }
    }

    document.addEventListener('mousedown', dragStart);
    document.addEventListener('mousemove', (e) => { if (!dragMove(e)) chartPoint(e); });
    document.addEventListener('mouseup', dragEnd);
    document.addEventListener('touchstart', (e) => { dragStart(e); if (!drag) chartPoint(e); }, { passive: true });
    document.addEventListener('touchmove', (e) => { if (!dragMove(e)) chartPoint(e); }, { passive: true });
    document.addEventListener('touchend', dragEnd, { passive: true });
    document.addEventListener('mouseout', (e) => {
        if (drag || measured) return;         // a drag may leave the picture for a moment; a measured stretch stays
        const from = e.target && e.target.closest && e.target.closest('#pp-chart-svg'), to = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('#pp-chart-svg');
        if (from && !to && chartNow) chartShow(chartNow.placed[chartNow.placed.length - 1], false);
    });
    // The prices refresh by themselves every minute while the tab is on screen and someone has used the page in the last 10
    // minutes (23 Oct 2026, the owner: "i have to click Refresh prices often"). A price that has not traded for half an hour (its
    // market is shut) is asked for again only every 15 minutes: one call a symbol, so this keeps it to the markets that move.
    const AUTO_MS = 60000, IDLE_MS = 10 * 60000, SHUT_EVERY_MS = 15 * 60000;
    let lastUse = Date.now(), autoBusy = false;
    if (typeof window !== 'undefined' && window.addEventListener)
        ['pointermove', 'keydown', 'scroll', 'touchstart', 'click'].forEach(ev => window.addEventListener(ev, () => { lastUse = Date.now(); }, { passive: true }));
    const trading = sym => { const q = quotes[sym]; return !!(q && q.time && Date.now() / 1000 - q.time < 1800); };
    async function autoRefresh() {
        const el = box();
        if (autoBusy || working || !state || !loaded || !el || el.offsetParent === null || (typeof document !== 'undefined' && document.hidden)
            || Date.now() - lastUse > IDLE_MS || document.querySelector('#pp-chart-svg:hover')) return false;
        autoBusy = true;
        try { await refreshQuotes(null, sym => !quotes[sym] || trading(sym) || Date.now() - (askedAt[sym] || 0) > SHUT_EVERY_MS); if (!working) redraw(); }
        finally { autoBusy = false; }
        return true;
    }
    // Checked every 5 seconds, asked only when due: at once when the tab comes back into view (another dashboard tab, another browser
    // tab: 23 Oct 2026, the owner waited up to a minute for "Prices as of" after switching back), otherwise once a minute. Nothing is
    // asked after 10 minutes without a touch, a click or a key, even with the page in front (IDLE_MS, in autoRefresh).
    let wasShown = false;
    if (typeof setInterval === 'function') setInterval(() => {
        const el = box(), shown = !!el && el.offsetParent !== null && !(typeof document !== 'undefined' && document.hidden);
        if (shown && (!wasShown || Date.now() - (pricesAt || 0) >= AUTO_MS)) autoRefresh();
        wasShown = shown;
    }, 5000);
    // the time until the US opening, kept current between redraws
    if (typeof setInterval === 'function') setInterval(() => { const line = document.getElementById('pp-us-opens'); if (line && line.textContent !== undefined) line.textContent = marketWait(); }, 30000);
    // The picture is drawn to the width it has: draw it again when that changes (a tab opened, a window resized, a phone turned)
    let chartTimer = null, chartWidth = 0;
    const chartFit = () => { const el = box(), w = el ? el.clientWidth : 0; if (w && Math.abs(w - chartWidth) > 8) { chartWidth = w; clearTimeout(chartTimer); chartTimer = setTimeout(drawChart, 120); } };
    if (typeof ResizeObserver !== 'undefined' && box()) new ResizeObserver(chartFit).observe(box()); else if (window.addEventListener) window.addEventListener('resize', chartFit);

    document.addEventListener('click', (e) => {
        const t = e.target.closest && e.target.closest('[data-pp]');
        if (mktOpen && !(e.target.closest && e.target.closest('#pp-mkt'))) { mktOpen = false; drawChart(); if (!t) return; }
        if (!t) { const sug = document.getElementById('pp-suggest'); if (sug && !e.target.closest('#pp-suggest, #pp-symbol')) sug.style.display = 'none'; return; }
        const action = t.getAttribute('data-pp');
        if (action === 'mkt-toggle') { mktOpen = !mktOpen; drawChart(); if (mktOpen) showChosen(); return; }      // only the graph is redrawn: the page does not move (23 Oct 2026)
        if (action === 'market') { chartKey = t.getAttribute('data-id') || 'value'; mktOpen = false; redraw(); return; }      // '', 'value', 'own' or a market
        if (t.tagName === 'A') e.preventDefault();
        // a holding or a sale clicked: its full analysis, in the background (23 Oct 2026, the owner: "make it so my holdings and sold can
        // be clicked ... run in background"): the dashboard's own runSidebarAnalysis, as the market panel's rows do (the same daily
        // allowance, the same "running" note, the report goes to Reports); elsewhere the analysis page, run straight away
        if (action === 'analyse') {
            const sym = t.getAttribute('data-symbol');
            if (sym && typeof window.runSidebarAnalysis === 'function') window.runSidebarAnalysis(sym);      // it shows its own "Running analysis" note
            else if (sym) location.href = 'analysis.html?symbol=' + encodeURIComponent(sym) + '&option=1&subOption=custom&autorun=true';   // subOption is what makes it run (24 Oct 2026)
            return;
        }
        if (action === 'held-all') { allHeld = !allHeld; redraw(); return; }
        if (action === 'held-filter') { heldOpenOnly = t.getAttribute('data-id') === 'open'; redraw(); return; }
        if (action === 'figs-all') { figsAll = !figsAll; openFolds.add('pp-figs'); drawChart(); return; }
        if (action === 'chart-key' || action === 'chart-range') {
            if (action === 'chart-key') { chartKey = t.getAttribute('data-id'); mktOpen = false; redraw(); return; }      // the lists follow the graph
            chartRange = t.getAttribute('data-id');
            drawChart();
            return;
        }
        if (action === 'pick') {
            const picked = t.getAttribute('data-symbol');
            pickedSymbol = picked;
            document.getElementById('pp-symbol').value = picked;
            document.getElementById('pp-suggest').style.display = 'none';
            // show which company and price that code is, before anything is bought
            const line = document.getElementById('pp-notice');
            if (line) { line.style.color = 'var(--text-secondary)'; line.textContent = 'Looking up ' + picked + '…'; }
            priceFor(picked).then(q => {
                if (!line || document.getElementById('pp-symbol').value !== picked) return;
                const c = q && closedFor(picked, quotes[picked]);
                if (c) line.style.color = '#ef4444';
                line.textContent = !q ? `No price found for ${picked}` : `${picked}: ${q.name || 'no name available'}${kindWord(q) ? ' (' + kindWord(q) + ')' : ''}, latest price ${money(q.price, q.currency)}` + (c ? `. Its market is closed (last traded ${when(new Date(c.at).toISOString())}): it can be bought once it opens.` : '');
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
                const code = text.trim().toUpperCase();
                if (code !== pickedSymbol) {
                    const coin = await coinTwin(code);
                    if (coin) {
                        const other = await fetchQuote(code);
                        if (other) throw new Error(`${code} is two different things. ${code} on its own is ${other.name || 'a share or fund'}${kindWord(other) ? ' (' + kindWord(other) + ')' : ''}; ${coinName(coin, code)} the coin is ${code}-USD. Type ${code}-USD for the coin, or pick ${code} from the list for the other.`);
                    }
                }
                const r = await buy(text, byQty ? 0 : amount, note, undefined, byQty ? qty : 0);
                ppBasis = 'usd'; ppQuote = null;
                say(`Practice buy recorded: ${usd(r.holding.costUsd)} of ${r.holding.label} at ${money(r.holding.buyPrice, r.holding.currency)}.`);
            }, 'buy');
        } else if (action === 'sell') {
            const id = t.getAttribute('data-id'), h = state.holdings.find(x => x.id === id);
            if (!h || !confirm(`Sell ${h.label} at the latest price? This closes the practice holding.`)) return;
            run(async () => { const proceeds = await sell(id); say(`Sold ${h.label} for ${usd(proceeds)} (put in ${usd(h.costUsd)}).`); }, 'sell:' + id);
        } else if (action === 'clearsold') {
            const n = state.closed.length;
            if (!n || !confirm(`Clear all ${n} line${n === 1 ? '' : 's'} from the sold list? Your practice cash and account value stay as they are; only the list is emptied.`)) return;
            run(async () => { await change(st => applyClearSold(st, null)); say('Sold list cleared. Practice cash and account value are unchanged.'); }, 'clearsold');
        } else if (action === 'unsold') {
            const id = t.getAttribute('data-id'), h = state.closed.find(x => x.id === id);
            if (!h) return;
            soldOpen = true;
            run(async () => { await change(st => applyClearSold(st, id)); say(`${h.label} removed from the sold list. Practice cash and account value are unchanged.`); });
        } else if (action === 'refresh') {
            run(async () => { await refreshQuotes(); flash = true; say('Prices updated at ' + new Date(pricesAt).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.'); }, 'refresh');
        } else if (action === 'reset') {
            if (!confirm(`Reset the fake money to ${usd(STARTING_CASH)}? This clears every practice holding and the sold list.`)) return;
            run(async () => { await api('reset'); state = newState(new Date().toISOString()); version = 0; quotes = {}; say(`Practice portfolio reset: ${usd(STARTING_CASH)} of fake money to start again.`); }, 'reset');
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
    // the market list: open and shut by its button, shut by a click elsewhere or Escape; a row chooses (the graph and both lists follow)
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && mktOpen) { mktOpen = false; drawChart(); } });
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
                const [res, coin] = await Promise.all([fetch(SEARCH_API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol: value }) }), coinTwin(value)]);
                let list = ((await res.json()).suggestions || []).filter(x => /^[A-Z0-9^=.\-]{1,24}$/.test(x.symbol || ''));
                if (coin) {                                  // the coin first, and the same code's other meaning named for what it is
                    const own = list.find(x => x.symbol === value), q = own ? await fetchQuote(value) : null;
                    if (own && q) own.name = (q.name || own.name) + (kindWord(q) ? ', ' + kindWord(q) : '') + ' (' + own.name + ')';
                    list = [{ symbol: value + '-USD', name: coinName(coin, value) + ', the coin (trades every day)' }].concat(list.filter(x => x.symbol !== value + '-USD'));
                }
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
        const vs = state.holdings.length || state.closed.length ? versusStart(state, quotes, Date.now()) : null;
        return ['PRACTICE PORTFOLIO (fake money): ' + (s.dayUsd === null ? '' : (s.dayClosed ? 'last trading day (its markets are closed now; each holding\'s last session) ' : 'today (what it holds now, each holding since its market\'s previous close) ') + moved(s.dayUsd) + '; ') + 'account value ' + usd(s.accountValue) + ', ' + moved(s.gainUsd) + ' since the start of ' + usd(STARTING_CASH) + '; practice cash left ' + usd(state.cash) + '.',
            'Bought by the user (' + mine.length + '): ' + (mine.slice(0, 12).map(one).join('; ') || 'none') + '.',
            'Bought by the autopilot and still held (' + its.length + '): ' + (its.slice(0, 12).map(one).join('; ') || 'none') + '.',
            'Sold so far: ' + state.closed.length + '.']
            .concat(vs ? ['Against an S&P 500 fund (the second line on the graph): the same ' + usd(STARTING_CASH) + ' put into the fund when the account began and left there would be ' + usd(vs.value) + ' now (' + moved(vs.gainUsd) + '); the account is ' + (Math.abs(vs.gapUsd) < 0.005 ? 'level with that' : (vs.gapUsd > 0 ? 'ahead of' : 'behind') + ' that by ' + usd(Math.abs(vs.gapUsd))) + '.'] : []).join('\n');
    }
    // The account's figures as this tab shows them, at the latest prices, for the Admin page on the same dashboard (17 Oct 2026:
    // the Admin page had its own estimate from the last check-in, which differed by about $230). null until prices are in.
    function figures() {
        if (!state || !loaded) return null;
        const s = summarize(state, quotes);
        let versus = null;
        try { versus = versusDays(state, quotes, Date.now(), autoRealized); } catch (e) { versus = null; }
        // for the real-money decision on the Admin page: the same money in the S&P 500 fund now, when the account began, and the
        // three largest gains among its sales (is the lead carried by a few lucky trades?)
        let fundValue = null;
        try { const vs = versusStart(state, quotes, Date.now()); fundValue = vs ? vs.value : null; } catch (e) { fundValue = null; }
        const topGains = (state.closed || []).map(h => (h.proceedsUsd || 0) - (h.costUsd || 0)).filter(g => g > 0).sort((a, b) => b - a).slice(0, 3).reduce((a, b) => a + b, 0);
        return { accountValue: s.accountValue, gainUsd: s.gainUsd, gainPct: s.gainPct, startingCash: state.startingCash, at: Date.now(), versus, fundValue, createdAt: state.createdAt, topGains };
    }
    window.practicePortfolio = { reload: load, setPlans, summary, figures, autoRefresh };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load); else load();
})();
