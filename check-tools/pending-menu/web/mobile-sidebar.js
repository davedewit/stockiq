// The two panels that slide in on a phone, handled in one place for every page that loads this script:
//   - the market-data sidebar on the right (home page and dashboard): a swipe to the left brings it out;
//   - the menu on the left (the ☰ button's): a swipe to the right brings it out.
// Either follows the finger (a quarter of a swipe shows a quarter of it, and it can be pushed back in the same touch),
// and the page behind stays exactly where it was.
//
// What the pages supply and what other code relies on:
//   - Sidebar: the markup (#mobile-sidebar-overlay, #mobile-sidebar-modal) and two functions, fillMobileSidebar() (moves
//     the page's panels into it) and emptyMobileSidebar() (moves them back). This script replaces the page's
//     toggleMobileSidebar() and closeMobileSidebar(), which the buttons call. The sidebar counts as open while
//     #mobile-sidebar-modal has style.display === 'block' (sidebar.js and the pages draw into it then).
//   - Menu: the markup (#mobile-menu, #mobile-menu-overlay, .hamburger-btn) and the pages' own toggleMobileMenu() and
//     closeMobileMenu(), which stay as they are. The menu is open while #mobile-menu has the class "open"; this script
//     only drags it and then sets the same classes the pages set.
//   - The page behind is never given position: fixed. That was the old way of stopping it scrolling, and it threw the
//     page to the top. For the sidebar this script sets overflow: hidden on the body; for the menu, styles.css does it
//     (body.menu-open), and overrides the position: fixed that older page code still writes.
(function () {
    'use strict';
    if (window.mobileSidebar) return;

    var PHONE = 768;        // both panels are a phone thing: the pages show their buttons up to this width
    var SLOP = 10;          // px a finger moves before it is read as a swipe or a scroll
    var SHARE = 1 / 3;      // let go with at least this much dragged out (or back) and it carries on that way
    var FLICK = 0.3;        // px per ms: a quick flick decides whatever the distance
    var EDGE = 30;          // px from the left edge left alone when pushing the sidebar back: the browser's "back" swipe starts there
    var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var MS = still ? 1 : 260;
    var EASE = 'ms cubic-bezier(0.2, 0.8, 0.2, 1)';

    var timer = null;       // a panel is gliding to rest
    var drag = null;        // the touch in progress
    var lastDrag = 0;
    var lastEnd = null;     // how the last drag was decided, for check-tools/mobile_sidebar_check.js

    // A panel: parts() its elements (null when the page has none), out(p) fully out and at rest, width(p),
    // begin(p) before it moves, place(p, hidden, glide) with hidden = px of it still off the screen, rest(p, out) once
    // it has stopped, scroller(p, target) what scrolls up and down inside it, pull = which way a finger pulls it out.

    // ---------------------------------------------------------------- the sidebar on the right
    var sidebar = {
        name: 'sidebar', pull: -1, shown: false, isOut: false, bodyOverflow: '',
        parts: function () {
            var overlay = document.getElementById('mobile-sidebar-overlay'), panel = document.getElementById('mobile-sidebar-modal');
            return overlay && panel ? { overlay: overlay, panel: panel } : null;
        },
        out: function () { return this.shown && this.isOut; },
        width: function (p) { return p.panel.getBoundingClientRect().width || Math.min(window.innerWidth * 0.9, 400); },
        begin: function (p) {
            if (this.shown) return;
            if (typeof window.fillMobileSidebar === 'function') window.fillMobileSidebar();
            p.panel.style.transition = 'none';
            p.overlay.style.transition = 'none';
            p.overlay.style.opacity = '0';
            p.overlay.style.touchAction = 'none';
            p.panel.style.overscrollBehavior = 'contain';
            p.panel.style.willChange = 'transform';
            p.panel.style.transform = 'translate3d(100%, 0, 0)';
            p.panel.style.right = '0';
            p.overlay.style.display = 'block';
            p.panel.style.display = 'block';
            // The page behind stops scrolling but is not moved: overflow only, never position: fixed.
            this.bodyOverflow = document.body.style.overflow;
            document.body.style.overflow = 'hidden';
            this.shown = true;
            void p.panel.offsetWidth;
        },
        place: function (p, hidden, glide) {
            p.panel.style.transition = glide ? 'transform ' + MS + EASE : 'none';
            p.overlay.style.transition = glide ? 'opacity ' + MS + 'ms ease' : 'none';
            p.panel.style.transform = 'translate3d(' + Math.round(hidden) + 'px, 0, 0)';
            p.overlay.style.opacity = String(Math.max(0, Math.min(1, 1 - hidden / this.width(p))));
        },
        rest: function (p, out) {
            this.isOut = out;
            if (out) return;
            p.overlay.style.display = 'none';
            p.panel.style.display = 'none';
            p.panel.style.willChange = '';
            if (typeof window.emptyMobileSidebar === 'function') window.emptyMobileSidebar();
            document.body.style.overflow = this.bodyOverflow;
            this.shown = false;
        },
        scroller: function (p) { return p.panel; }
    };

    // ---------------------------------------------------------------- the menu on the left
    var menu = {
        name: 'menu', pull: 1,
        parts: function () {
            var panel = document.getElementById('mobile-menu');
            return panel ? { panel: panel, overlay: document.getElementById('mobile-menu-overlay'), button: document.querySelector('.hamburger-btn') } : null;
        },
        out: function (p) { p = p || this.parts(); return !!p && p.panel.classList.contains('open'); },
        width: function (p) { return p.panel.getBoundingClientRect().width || Math.min(window.innerWidth * 0.85, 320); },
        begin: function (p) {
            if (!this.out(p)) {
                var nav = document.querySelector('.top-nav'), content = p.panel.querySelector('.mobile-menu-content');
                if (nav) nav.style.transform = 'translateY(0)';
                if (content) content.scrollTop = 0;
            }
            // From here to rest() the menu is placed by inline styles; the classes are set once it has stopped.
            this.place(p, this.out(p) ? 0 : this.width(p), false);
            if (p.overlay) { p.overlay.style.visibility = 'visible'; p.overlay.style.touchAction = 'none'; }
            p.panel.style.overscrollBehavior = 'contain';
            void p.panel.offsetWidth;
        },
        place: function (p, hidden, glide) {
            p.panel.style.transition = glide ? 'left ' + MS + EASE : 'none';
            p.panel.style.left = (-Math.round(hidden)) + 'px';
            if (p.overlay) {
                p.overlay.style.transition = glide ? 'opacity ' + MS + 'ms ease' : 'none';
                p.overlay.style.opacity = String(Math.max(0, Math.min(1, 1 - hidden / this.width(p))));
            }
        },
        rest: function (p, out) {
            p.panel.style.transition = 'none';
            if (p.overlay) p.overlay.style.transition = 'none';
            if (out) {
                p.panel.classList.add('open');
                if (p.overlay) p.overlay.classList.add('show');
                if (p.button) p.button.classList.add('active');
                document.body.classList.add('menu-open');
            } else if (typeof window.closeMobileMenu === 'function') {
                window.closeMobileMenu();        // the page's own: it also clears what its ☰ button set
            } else {
                p.panel.classList.remove('open');
                if (p.overlay) p.overlay.classList.remove('show');
                if (p.button) p.button.classList.remove('active');
                document.body.classList.remove('menu-open');
            }
            p.panel.style.left = '';
            if (p.overlay) { p.overlay.style.opacity = ''; p.overlay.style.visibility = ''; }
            void p.panel.offsetWidth;
            p.panel.style.transition = '';
            if (p.overlay) p.overlay.style.transition = '';
        },
        scroller: function (p, target) { return (target && target.closest && target.closest('.mobile-menu-content')) || p.panel.querySelector('.mobile-menu-content') || p.panel; }
    };

    // ---------------------------------------------------------------- moving either of them
    function settle(d, p, out) {
        clearTimeout(timer);
        d.place(p, out ? 0 : d.width(p), true);
        timer = setTimeout(function () { timer = null; d.rest(p, out); }, MS + 40);
    }

    function openSidebar() {
        var p = sidebar.parts();
        if (!p || timer) return;
        sidebar.begin(p);
        requestAnimationFrame(function () { settle(sidebar, p, true); });
    }

    function closeSidebar() {
        var p = sidebar.parts();
        if (!p || !sidebar.shown) return;
        settle(sidebar, p, false);
    }

    function toggleSidebar() { if (sidebar.out()) closeSidebar(); else openSidebar(); }

    // Something under the finger that scrolls sideways and still has room to go that way keeps the swipe for itself.
    function scrollsSideways(target, dx, stop) {
        for (var el = target; el && el !== stop && el !== document.body && el.nodeType === 1; el = el.parentElement) {
            if (el.scrollWidth > el.clientWidth + 1) {
                var flow = getComputedStyle(el).overflowX;
                if (flow === 'auto' || flow === 'scroll') {
                    if (dx < 0 && el.scrollLeft + el.clientWidth < el.scrollWidth - 1) return true;
                    if (dx > 0 && el.scrollLeft > 0) return true;
                }
            }
        }
        return false;
    }

    function keepsItsTouch(target) {
        return !!(target && target.closest && target.closest('input, textarea, select, [contenteditable="true"], #pp-chart-svg, #threshold-slider-track, #crypto-slider-track, [data-no-swipe]'));
    }

    // Which panel a sideways finger moves, if any: one that is out is pushed back; with both in, the one on that side is pulled out.
    function choose(dx, target, startX) {
        var s = sidebar.parts(), m = menu.parts(), way = dx > 0 ? 1 : -1;
        if (s && sidebar.shown) return sidebar.out() && way === 1 && startX >= EDGE && !scrollsSideways(target, dx, s.panel) ? sidebar : null;
        if (m && menu.out(m)) return way === -1 && !scrollsSideways(target, dx, m.panel) ? menu : null;
        if (document.body.classList.contains('menu-open')) return null;       // a pop-up of the page has the screen
        if (keepsItsTouch(target) || scrollsSideways(target, dx, null)) return null;
        if (way === -1) return s ? sidebar : null;
        return m ? menu : null;
    }

    function onStart(e) {
        drag = null;
        if (e.touches.length !== 1 || window.innerWidth > PHONE || timer) return;
        var t = e.touches[0];
        drag = { x: t.clientX, y: t.clientY, target: e.target, mode: '', panel: null, from: 0, grab: 0, wasOut: false, trail: [{ x: t.clientX, at: e.timeStamp }] };
    }

    function onMove(e) {
        if (!drag || e.touches.length !== 1) return;
        var t = e.touches[0], dx = t.clientX - drag.x, dy = t.clientY - drag.y, d, p;

        if (!drag.mode) {
            if (Math.abs(dx) < SLOP && Math.abs(dy) < SLOP) return;
            var sideways = Math.abs(dx) > Math.abs(dy) * 1.5;   // clearly across, not a slanted scroll
            d = sideways ? choose(dx, drag.target, drag.x) : null;
            drag.mode = d ? 'drag' : sideways ? 'other' : 'scroll';
            if (d) {
                p = d.parts();
                drag.panel = d;
                drag.wasOut = d.out(p);
                d.begin(p);
                drag.from = drag.wasOut ? 0 : d.width(p);
                drag.grab = t.clientX;
            }
        }

        if (drag.mode === 'drag') {
            d = drag.panel; p = d.parts();
            if (e.cancelable) e.preventDefault();
            var w = d.width(p), hidden = Math.max(0, Math.min(w, drag.from - d.pull * (t.clientX - drag.grab)));
            d.place(p, hidden, false);
            drag.hidden = hidden;
            drag.trail.push({ x: t.clientX, at: e.timeStamp });
            if (drag.trail.length > 8) drag.trail.shift();
            return;
        }

        // While a panel is out, a finger moving up or down must never reach the page behind: on the dark part nothing
        // scrolls, and the panel's own list stops at its ends instead of handing the movement on.
        if (drag.mode === 'scroll' && e.cancelable) {
            var s = sidebar.parts(), m = menu.parts();
            d = s && sidebar.shown ? sidebar : m && menu.out(m) ? menu : null;
            if (!d) return;
            p = d === sidebar ? s : m;
            var inside = p.panel.contains(drag.target), box = d.scroller(p, drag.target), room = box.scrollHeight - box.clientHeight;
            if (!inside || room <= 0 || (dy > 0 && box.scrollTop <= 0) || (dy < 0 && box.scrollTop >= room - 1)) e.preventDefault();
        }
    }

    function onEnd(e) {
        var g = drag;
        drag = null;
        if (!g || g.mode !== 'drag') return;
        var d = g.panel, p = d.parts();
        if (!p) return;
        lastDrag = Date.now();
        var w = d.width(p), hidden = g.hidden === undefined ? g.from : g.hidden, trail = g.trail, speed = 0;
        // How fast the finger was going when it left: over its last 60ms or so, and nothing if it had stopped first.
        var last = trail[trail.length - 1], first = trail[0];
        for (var i = trail.length - 2; i >= 0; i--) { first = trail[i]; if (last.at - trail[i].at >= 60) break; }
        if (last.at > first.at && e.timeStamp - last.at < 90) speed = (last.x - first.x) / (last.at - first.at);
        var out;
        if (e.type === 'touchcancel') out = g.wasOut;
        else if (Math.abs(speed) > FLICK) out = speed * d.pull > 0;
        else out = g.wasOut ? hidden < w * SHARE : (w - hidden) >= w * SHARE;
        lastEnd = { panel: d.name, speed: Math.round(speed * 100) / 100, hidden: Math.round(hidden), width: Math.round(w), points: trail.length, out: out };
        settle(d, p, out);
    }

    document.addEventListener('touchstart', onStart, { passive: true });
    document.addEventListener('touchmove', onMove, { passive: false });
    document.addEventListener('touchend', onEnd, { passive: true });
    document.addEventListener('touchcancel', onEnd, { passive: true });

    window.mobileSidebar = {
        version: 2,
        open: openSidebar,
        close: closeSidebar,
        toggle: toggleSidebar,
        isOpen: function () { return sidebar.shown; },
        // true while a finger is dragging a panel and just after
        busy: function () { return !!(drag && drag.mode === 'drag') || Date.now() - lastDrag < 80; },
        last: function () { return lastEnd; }
    };
    window.toggleMobileSidebar = toggleSidebar;
    window.closeMobileSidebar = closeSidebar;
})();
