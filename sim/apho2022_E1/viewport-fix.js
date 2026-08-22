/* Viewport fix for the local copy of the official Magnetic Black Box page.
   ---------------------------------------------------------------------------
   basic.js reads window.innerWidth once, while the deferred scripts are being
   evaluated, and derives every length from it:

       canvas_width  = 0.45 * window.innerWidth      (0.9 * on mobile)
       canvas_height = 1.2 * canvas_width
       canvas.width  = canvas_width;  canvas.height = canvas_height

   Nothing ever recomputes those.  If the window has no usable width at that
   instant — a background tab, a restored session, a window opened at zero size,
   or a page opened directly rather than followed from index.html while the
   browser is still laying the document out — canvas_width comes out 0, so
   scaling_factor is 0, every field reads NaN and the canvas stays blank for the
   rest of the session.

   This file changes no physics.  It re-applies the size the original code would
   have chosen had the window been ready, and re-runs the original initParams()
   so all the objects are rebuilt against it.  It runs on load and after a
   resize.  The organisers' own copy in ../../official/ is left untouched. */
(function () {
  function targetWidth() {
    return (typeof mobile !== 'undefined' && mobile ? 0.9 : 0.45) * window.innerWidth;
  }

  function apply() {
    if (typeof canvas === 'undefined' || typeof initParams !== 'function') return;
    var w = targetWidth();
    if (!(w > 0)) return;
    if (typeof canvas_width === 'number' && Math.abs(w - canvas_width) < 1) return;

    canvas_width = w;
    canvas_height = 1.2 * canvas_width;
    canvas.width = canvas_width;
    canvas.height = canvas_height;

    /* initParams() calls initGraph(), which builds a new Chart on the same
       context, so the old one has to go first */
    if (typeof graph !== 'undefined' && graph !== undefined) {
      graph.destroy();
      graph = undefined;
    }
    if (typeof resetMeasurements === 'function') resetMeasurements();

    initParams();

    time = 0;
    updated = false;
    if (typeof updateParams === 'function') updateParams('time');
  }

  window.addEventListener('load', function () { setTimeout(apply, 0); });

  var pending = null;
  window.addEventListener('resize', function () {
    clearTimeout(pending);
    pending = setTimeout(apply, 200);
  });
})();
