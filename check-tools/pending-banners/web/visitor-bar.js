// The visitor's usage count, shown as a small chip inside the header bar on every page ("1 free today", "3/5 today",
// "Unlimited", "Trial ended"); a click on it says the same in a sentence, with the one thing to do next (start a free
// trial, see the plans).
//
// It replaces how the count is SHOWN, not how it is worked out. The pages still work the count out as they always did
// (auth.js getStockAnalysisStatus, and the copies in index.html, analysis-functions.js and dashboard.html) and still
// write it into their floating badge, #trial-status-display. theme.js hides that badge and loads this script, which
// reads the badge's text whenever it changes and shows it in the header instead. So nothing about trials, limits or
// plans is decided here, and taking this script away (theme.js without its loader) puts every page back as it was.
//
// The texts the badge can hold (all of them are read below; an unknown one is shown as it is):
//   "1/1 Analyses remaining today"                              an anonymous visitor
//   "3/5 today (resets 00:00 UTC) • Trial: 2d 4h"               signed in, on the free trial
//   "12/15 today (resets 00:00 UTC) • Subscription: 20d 3h"     a paid plan with a daily count
//   "Unlimited", "Unlimited • Subscription: 20d 3h", "Unlimited • Trial: 2d 4h"
//   "Trial expired - Upgrade"                                   signed in, the trial is over
//   "Status unavailable"                                        the count could not be fetched: nothing is shown
(function () {
    'use strict';
    if (window.visitorBar) return;

    var here = (document.currentScript && document.currentScript.src) || '';
    var SITE = /visitor-bar\.js/.test(here) ? here.replace(/visitor-bar\.js.*$/, '') : '';     // links are built from where this script was loaded
    var PHONE = 768;
    var chip = null, card = null, state = null, source = null, watching = null, fitted = null;

    // ---------------------------------------------------------------- reading the badge's text
    function read(html) {
        var text = String(html || '').replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim(), m;
        if (!text || /^Status unavailable/i.test(text)) return { kind: 'none' };
        if ((m = text.match(/^(\d+)\/1 Analyses remaining today$/i))) return { kind: 'anon', left: +m[1], limit: 1 };
        if ((m = text.match(/^Unlimited(?: • (Subscription|Trial): (.+))?$/i))) return { kind: 'unlimited', plan: m[1] || '', time: m[2] || '' };
        if ((m = text.match(/^(\d+)\/(\d+) today(?: \(resets [^)]*\))?(?: • (Subscription|Trial): (.+))?$/i))) return { kind: /trial/i.test(m[3] || '') ? 'trial' : 'paid', left: +m[1], limit: +m[2], plan: m[3] || '', time: m[4] || '' };
        if (/^Trial expired/i.test(text)) return { kind: 'expired' };
        return { kind: 'unknown', text: text };
    }

    // What the chip says (long, and short for a narrow header) and whether it is a warning
    function words(s) {
        if (s.kind === 'anon') return { long: s.left + ' free today', short: s.left + ' free', bad: s.left <= 0 };
        if (s.kind === 'trial' || s.kind === 'paid') return { long: s.left + '/' + s.limit + ' today', short: s.left + '/' + s.limit, bad: s.left <= 0 };
        if (s.kind === 'unlimited') return { long: 'Unlimited', short: '∞', bad: false };
        if (s.kind === 'expired') return { long: 'Trial ended', short: 'Expired', bad: true };
        return { long: 'Usage', short: 'Usage', bad: false };
    }

    function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function count(n, of, free) { return '<strong>' + n + ' of ' + of + '</strong> ' + (free ? 'free ' : '') + (n === 1 ? 'analysis' : 'analyses') + ' left today'; }

    // The sentence behind the chip, and the one thing to do next
    function detail(s) {
        var plans = SITE + 'dashboard.html?redirect=upgrade#upgrade', lines = [], act = null, more = null;
        if (s.kind === 'anon') {
            lines.push(s.left > 0 ? count(s.left, s.limit, true) + '.' : 'Today’s free analysis is used. It comes back at 00:00 UTC.');
            lines.push('A free account gives 15 analyses: 5 a day for 3 days. No credit card.');
            act = ['Start free trial', SITE + 'signup.html']; more = ['Sign in', SITE + 'login.html'];
        } else if (s.kind === 'trial' || s.kind === 'paid') {
            lines.push(count(s.left, s.limit, false) + '. The count starts again at 00:00 UTC.');
            if (s.time) lines.push((s.kind === 'trial' ? 'Free trial: ' : 'Subscription: ') + esc(s.time) + ' left.');
            if (s.kind === 'trial') act = ['See the plans', plans]; else more = ['Your plan', plans];
        } else if (s.kind === 'unlimited') {
            lines.push('<strong>Unlimited</strong> analyses.');
            if (s.time) lines.push((/trial/i.test(s.plan) ? 'Free trial: ' : 'Subscription: ') + esc(s.time) + ' left.');
            more = ['Your plan', plans];
        } else if (s.kind === 'expired') {
            lines.push('Your free trial has ended.');
            act = ['See the plans', plans];
        } else {
            lines.push(esc(s.text || ''));
        }
        return { lines: lines, act: act, more: more };
    }

    // ---------------------------------------------------------------- the chip and its card
    function style() {
        if (document.getElementById('vb-style')) return;
        var st = document.createElement('style');
        st.id = 'vb-style';
        st.textContent = [
            '#vb-chip { font: inherit; font-size: 0.78rem; font-weight: 600; line-height: 1; white-space: nowrap; cursor: pointer; padding: 6px 10px; border-radius: 999px; border: 1px solid currentColor; background: transparent; color: #16a34a; flex: 0 0 auto; -webkit-tap-highlight-color: transparent; }',
            '#vb-chip.vb-bad { color: #ef4444; }',
            '#vb-chip.vb-tight { padding: 6px 8px; }',                                                              // a crowded bar: the short wording, a little narrower
            '#vb-chip:hover, #vb-chip[aria-expanded="true"] { background: rgba(128, 128, 128, 0.12); }',
            '#vb-chip:focus-visible { outline: 2px solid #007bff; outline-offset: 2px; }',
            '#vb-chip.vb-mid { position: absolute; top: 50%; transform: translate(-50%, -50%); }',                  // a phone: between the menu button and the name
            '#vb-chip.vb-under { position: fixed; right: 12px; background: var(--card-bg, #fff); box-shadow: 0 1px 6px rgba(0, 0, 0, 0.15); z-index: 9997; }',   // no room in the bar at all
            '#vb-card { position: fixed; z-index: 10002; width: 280px; max-width: calc(100vw - 16px); box-sizing: border-box; background: var(--card-bg, #fff); color: var(--text-primary, #111); border: 1px solid var(--border-color, #ddd); border-radius: 10px; box-shadow: 0 8px 28px rgba(0, 0, 0, 0.22); padding: 14px 16px; font-size: 0.88rem; line-height: 1.45; text-align: left; }',
            '#vb-card p { margin: 0 0 8px; color: var(--text-secondary, #555); }',
            '#vb-card p:first-child { color: var(--text-primary, #111); }',
            '#vb-card .vb-row { display: flex; align-items: center; gap: 14px; margin-top: 12px; flex-wrap: wrap; }',
            '#vb-card a.vb-act { background: #007bff; color: #fff; text-decoration: none; font-weight: 600; padding: 8px 14px; border-radius: 8px; }',
            '#vb-card a.vb-act:hover { background: #0069d9; }',
            '#vb-card a.vb-more { color: #007bff; text-decoration: none; font-weight: 500; }',
            '#vb-card a.vb-more:hover { text-decoration: underline; }'
        ].join('\n');
        document.head.appendChild(st);
    }

    function bar() { return document.querySelector('.top-nav .nav-container'); }

    function mount() {
        if (chip && chip.isConnected) return true;
        var holder = bar();
        if (!holder) return false;
        style();
        chip = document.createElement('button');
        chip.type = 'button';
        chip.id = 'vb-chip';
        chip.setAttribute('aria-expanded', 'false');
        chip.setAttribute('aria-haspopup', 'dialog');
        chip.style.display = 'none';
        chip.addEventListener('click', function (e) { e.stopPropagation(); if (card) closeCard(); else openCard(); });
        holder.appendChild(chip);
        return true;
    }

    function seen(el) { if (!el) return null; var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden' ? r : null; }

    // Where the chip sits and how much it says, by the room there is in the bar
    function fit() {
        if (!chip || !state || state.kind === 'none') return;
        var w = words(state), nav = document.querySelector('.top-nav'), phone = window.innerWidth <= PHONE;
        chip.className = w.bad ? 'vb-bad' : '';
        chip.style.left = ''; chip.style.top = '';
        chip.textContent = w.long;
        if (phone) {
            // between what is on the left of the bar (the menu button, the bell) and the name on the right.
            // Taken out of the bar's own row first: while it is in the row it pushes the others aside.
            chip.classList.add('vb-mid');
            var edge = 0, brand = seen(document.querySelector('.nav-brand'));
            ['.hamburger-btn', '#mobile-notification-bell'].forEach(function (q) { var r = seen(document.querySelector(q)); if (r && (!brand || r.right <= brand.left)) edge = Math.max(edge, r.right); });
            var end = brand ? brand.left : window.innerWidth, room = end - edge - 20;
            fitted = { edge: Math.round(edge), end: Math.round(end), room: Math.round(room), chip: chip.offsetWidth };
            if (chip.offsetWidth > room) { chip.textContent = w.short; chip.classList.add('vb-tight'); }
            if (chip.offsetWidth > room) { under(nav); return; }
            chip.style.left = Math.round((edge + end) / 2) + 'px';
        } else {
            // the right-hand end of the bar, clear of the menu in the middle
            var menu = seen(document.querySelector('.top-nav .desktop-nav'));
            var clear = function () { var r = chip.getBoundingClientRect(); return !menu || r.left >= menu.right + 8; };
            if (!clear()) { chip.textContent = w.short; chip.classList.add('vb-tight'); }
            if (!clear()) under(nav);
        }
    }

    function under(nav) {
        var r = nav ? nav.getBoundingClientRect() : { bottom: 64 };
        chip.className = (chip.classList.contains('vb-bad') ? 'vb-bad ' : '') + 'vb-under';
        chip.textContent = words(state).long;
        chip.style.left = '';
        chip.style.top = Math.round(r.bottom + 6) + 'px';
    }

    function show() {
        if (!state || state.kind === 'none') { if (chip) chip.style.display = 'none'; closeCard(); return; }
        if (!mount()) return;
        var w = words(state), d = detail(state);
        chip.style.display = '';
        chip.setAttribute('aria-label', d.lines.join(' ').replace(/<[^>]*>/g, ''));
        chip.title = w.long;
        fit();
        if (card) openCard();
    }

    function openCard() {
        closeCard();
        if (!chip || !state) return;
        var d = detail(state);
        card = document.createElement('div');
        card.id = 'vb-card';
        card.setAttribute('role', 'dialog');
        card.setAttribute('aria-label', 'Your usage');
        card.innerHTML = d.lines.map(function (l) { return '<p>' + l + '</p>'; }).join('') +
            (d.act || d.more ? '<div class="vb-row">' + (d.act ? '<a class="vb-act" href="' + esc(d.act[1]) + '">' + esc(d.act[0]) + '</a>' : '') + (d.more ? '<a class="vb-more" href="' + esc(d.more[1]) + '">' + esc(d.more[0]) + '</a>' : '') + '</div>' : '');
        document.body.appendChild(card);
        var r = chip.getBoundingClientRect(), width = card.offsetWidth;
        card.style.top = Math.round(r.bottom + 8) + 'px';
        card.style.left = Math.round(Math.max(8, Math.min(window.innerWidth - width - 8, r.right - width))) + 'px';
        chip.setAttribute('aria-expanded', 'true');
    }

    function closeCard() {
        if (card) { card.remove(); card = null; }
        if (chip) chip.setAttribute('aria-expanded', 'false');
    }

    // ---------------------------------------------------------------- following the pages' own badge
    function take() {
        var badge = document.getElementById('trial-status-display');
        if (!badge) return;
        if (badge !== source) {
            source = badge;
            if (watching) watching.disconnect();
            watching = new MutationObserver(take);
            watching.observe(badge, { childList: true, characterData: true, subtree: true });
        }
        var html = badge.innerHTML;
        if (state && state.from === html) return;
        state = read(html);
        state.from = html;
        show();
    }

    function start() {
        take();
        // the badge is made by the page some time after it loads, and some pages make it again
        new MutationObserver(function (list) {
            for (var i = 0; i < list.length; i++) for (var j = 0; j < list[i].addedNodes.length; j++) if (list[i].addedNodes[j].id === 'trial-status-display') { take(); return; }
            if (source && !source.isConnected) take();
        }).observe(document.body, { childList: true });
        var again;
        window.addEventListener('resize', function () { clearTimeout(again); again = setTimeout(function () { closeCard(); fit(); }, 120); });
        document.addEventListener('click', function (e) { if (card && !card.contains(e.target)) closeCard(); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeCard(); });
        // the bell and the web font arrive late and move things in the bar
        [400, 1500, 4000].forEach(function (ms) { setTimeout(fit, ms); });
    }

    window.visitorBar = {
        version: 1,
        read: read,
        state: function () { return state ? { kind: state.kind, left: state.left, limit: state.limit, time: state.time, text: chip && chip.style.display !== 'none' ? chip.textContent : '', fitted: fitted } : null; },
        refresh: function () { state = null; take(); }
    };
    if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);
})();
