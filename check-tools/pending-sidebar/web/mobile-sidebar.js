// The market-data sidebar on a phone (the panel that comes in from the right): one script for every page that has it
// (the home page and the dashboard). It shows and hides the panel, lets a finger drag it in and out, and keeps the page
// behind it exactly where it was.
//
// The page supplies the markup (#mobile-sidebar-overlay, #mobile-sidebar-modal) and two functions of its own:
// fillMobileSidebar() moves its panels into the sidebar, emptyMobileSidebar() moves them back. This script replaces the
// page's toggleMobileSidebar() and closeMobileSidebar(), which the buttons call.
//
// Two things other code relies on and must stay true: the sidebar counts as open while #mobile-sidebar-modal has
// style.display === 'block' (sidebar.js and the pages draw into it then), and the page behind is never given
// position: fixed. That was the old way of stopping it scrolling, and it threw the page to the top.
(function () {
    'use strict';
    if (window.mobileSidebar) return;

    var PHONE = 768;        // the sidebar is a phone thing: the pages show its button up to this width
    var SLOP = 10;          // px a finger moves before it is read as a swipe or a scroll
    var SHARE = 1 / 3;      // let go with at least this much dragged out (or back) and it carries on that way
    var FLICK = 0.3;        // px per ms: a quick flick decides whatever the distance
    var EDGE = 30;          // px from the left edge left alone: the browser's own "back" swipe starts there
    var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var MS = still ? 1 : 260;

    var shown = false;      // on the page (display: block), fully out or part way
    var isOut = false;      // fully out and at rest
    var timer = null;
    var drag = null;        // the touch in progress
    var lastDrag = 0;
    var lastEnd = null;     // how the last drag was decided, for check-tools/mobile_sidebar_check.js
    var bodyOverflow = '';

    function parts() {
        var overlay = document.getElementById('mobile-sidebar-overlay'), modal = document.getElementById('mobile-sidebar-modal');
        return overlay && modal ? { overlay: overlay, modal: modal } : null;
    }

    function width(p) { return p.modal.getBoundingClientRect().width || Math.min(window.innerWidth * 0.9, 400); }

    // hidden: how many px of the sidebar are still off the screen (0 = fully out)
    function place(p, hidden, glide) {
        var w = width(p);
        p.modal.style.transition = glide ? 'transform ' + MS + 'ms cubic-bezier(0.2, 0.8, 0.2, 1)' : 'none';
        p.overlay.style.transition = glide ? 'opacity ' + MS + 'ms ease' : 'none';
        p.modal.style.transform = 'translate3d(' + Math.round(hidden) + 'px, 0, 0)';
        p.overlay.style.opacity = String(Math.max(0, Math.min(1, 1 - hidden / w)));
        p.modal.dataset.hidden = String(Math.round(hidden));
    }

    function show(p) {
        if (shown) return;
        if (typeof window.fillMobileSidebar === 'function') window.fillMobileSidebar();
        p.modal.style.transition = 'none';
        p.overlay.style.transition = 'none';
        p.overlay.style.opacity = '0';
        p.overlay.style.touchAction = 'none';
        p.modal.style.overscrollBehavior = 'contain';
        p.modal.style.willChange = 'transform';
        p.modal.style.transform = 'translate3d(100%, 0, 0)';
        p.modal.style.right = '0';
        p.overlay.style.display = 'block';
        p.modal.style.display = 'block';
        // The page behind stops scrolling but is not moved: overflow only, never position: fixed.
        bodyOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        shown = true;
        void p.modal.offsetWidth;
    }

    function hide(p) {
        p.overlay.style.display = 'none';
        p.modal.style.display = 'none';
        p.modal.style.willChange = '';
        if (typeof window.emptyMobileSidebar === 'function') window.emptyMobileSidebar();
        document.body.style.overflow = bodyOverflow;
        shown = false;
        isOut = false;
    }

    function settle(p, out) {
        clearTimeout(timer);
        place(p, out ? 0 : width(p), true);
        isOut = out;
        timer = setTimeout(function () { timer = null; if (!out) hide(p); }, MS + 40);
    }

    function open() {
        var p = parts();
        if (!p) return;
        show(p);
        requestAnimationFrame(function () { settle(p, true); });
    }

    function close() {
        var p = parts();
        if (!p || !shown) return;
        settle(p, false);
    }

    function toggle() { if (shown && isOut) close(); else open(); }

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
        return !!(target && target.closest && target.closest('input, textarea, select, [contenteditable="true"], #pp-chart-svg, [data-no-swipe]'));
    }

    function menuOpen() {
        var menu = document.getElementById('mobile-menu');
        return (menu && menu.classList.contains('open')) || document.body.classList.contains('menu-open');
    }

    function onStart(e) {
        drag = null;
        if (e.touches.length !== 1 || window.innerWidth > PHONE || timer || !parts()) return;
        var t = e.touches[0];
        drag = { x: t.clientX, y: t.clientY, target: e.target, mode: '', from: 0, grab: 0, wasOut: shown && isOut, trail: [{ x: t.clientX, at: e.timeStamp }] };
    }

    function onMove(e) {
        if (!drag || e.touches.length !== 1) return;
        var p = parts(), t = e.touches[0], dx = t.clientX - drag.x, dy = t.clientY - drag.y;
        if (!p) return;

        if (!drag.mode) {
            if (Math.abs(dx) < SLOP && Math.abs(dy) < SLOP) return;
            var sideways = Math.abs(dx) > Math.abs(dy) * 1.2;
            if (!sideways) {
                drag.mode = 'scroll';
            } else if (drag.wasOut) {
                drag.mode = dx > 0 && drag.x >= EDGE && !scrollsSideways(drag.target, dx, p.modal) ? 'drag' : 'other';
            } else {
                drag.mode = dx < 0 && !shown && !menuOpen() && !keepsItsTouch(drag.target) && !scrollsSideways(drag.target, dx, null) ? 'drag' : 'other';
            }
            if (drag.mode === 'drag') {
                show(p);
                drag.from = drag.wasOut ? 0 : width(p);
                drag.grab = t.clientX;
            }
        }

        if (drag.mode === 'drag') {
            if (e.cancelable) e.preventDefault();
            var w = width(p), hidden = Math.max(0, Math.min(w, drag.from + (t.clientX - drag.grab)));
            place(p, hidden, false);
            drag.hidden = hidden;
            drag.trail.push({ x: t.clientX, at: e.timeStamp });
            if (drag.trail.length > 8) drag.trail.shift();
            return;
        }

        // While the sidebar is out, a finger moving up or down must never reach the page behind: on the dark part
        // nothing scrolls, and the sidebar's own list stops at its ends instead of handing the movement on.
        if (shown && drag.mode === 'scroll' && e.cancelable) {
            var inside = p.modal.contains(drag.target), room = p.modal.scrollHeight - p.modal.clientHeight;
            if (!inside || room <= 0 || (dy > 0 && p.modal.scrollTop <= 0) || (dy < 0 && p.modal.scrollTop >= room - 1)) e.preventDefault();
        }
    }

    function onEnd(e) {
        var d = drag, p = parts();
        drag = null;
        if (!d || d.mode !== 'drag' || !p) return;
        lastDrag = Date.now();
        var w = width(p), hidden = d.hidden === undefined ? d.from : d.hidden, trail = d.trail, speed = 0;
        // How fast the finger was going when it left: over its last 60ms or so, and nothing if it had stopped first.
        var last = trail[trail.length - 1], first = trail[0];
        for (var i = trail.length - 2; i >= 0; i--) { first = trail[i]; if (last.at - trail[i].at >= 60) break; }
        if (last.at > first.at && e.timeStamp - last.at < 90) speed = (last.x - first.x) / (last.at - first.at);
        var out;
        if (e.type === 'touchcancel') out = d.wasOut;
        else if (Math.abs(speed) > FLICK) out = speed < 0;
        else out = d.wasOut ? hidden < w * SHARE : (w - hidden) >= w * SHARE;
        lastEnd = { speed: Math.round(speed * 100) / 100, hidden: Math.round(hidden), width: Math.round(w), points: trail.length, out: out };
        settle(p, out);
    }

    document.addEventListener('touchstart', onStart, { passive: true });
    document.addEventListener('touchmove', onMove, { passive: false });
    document.addEventListener('touchend', onEnd, { passive: true });
    document.addEventListener('touchcancel', onEnd, { passive: true });

    window.mobileSidebar = {
        open: open,
        close: close,
        toggle: toggle,
        isOpen: function () { return shown; },
        // true while a finger is dragging the sidebar and just after: the page's own swipe code leaves that touch alone
        busy: function () { return !!(drag && drag.mode === 'drag') || Date.now() - lastDrag < 80; },
        last: function () { return lastEnd; }
    };
    window.toggleMobileSidebar = toggle;
    window.closeMobileSidebar = close;
})();
