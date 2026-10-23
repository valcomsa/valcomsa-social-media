/* VALCOM — mini motor de animación determinista para Reels.
   Cada reel define window.REEL = {duration, fps} y window.renderAt(t) (t en segundos).
   render_reel.py llama renderAt(t) frame a frame: nada de requestAnimationFrame ni CSS transitions. */
(function () {
  var M = {};
  M.clamp = function (x, a, b) { return Math.max(a, Math.min(b, x)); };
  /* progreso 0..1 de t entre a y b */
  M.seg = function (t, a, b) { return M.clamp((t - a) / (b - a), 0, 1); };
  M.lerp = function (a, b, p) { return a + (b - a) * p; };
  M.ease = {
    linear: function (p) { return p; },
    outCubic: function (p) { return 1 - Math.pow(1 - p, 3); },
    outExpo: function (p) { return p >= 1 ? 1 : 1 - Math.pow(2, -10 * p); },
    inCubic: function (p) { return p * p * p; },
    inOutCubic: function (p) { return p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; },
    outBack: function (p) { var c = 1.70158, c3 = c + 1; return 1 + c3 * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); }
  };
  /* visibilidad de una escena [a,b] con entrada y salida */
  M.window = function (t, a, b, fin, fout) {
    fin = fin == null ? .25 : fin; fout = fout == null ? .2 : fout;
    if (t < a || t > b) return 0;
    return Math.min(M.ease.outCubic(M.seg(t, a, a + fin)), 1 - M.ease.inCubic(M.seg(t, b - fout, b)));
  };
  /* aplica estilo: o = {o: opacity, x, y, s: scale, blur, clip: 0..1 (revela de abajo hacia arriba)} */
  M.set = function (el, o) {
    if (typeof el === 'string') el = document.querySelector(el);
    if (!el) return;
    var tr = 'translate(' + (o.x || 0) + 'px,' + (o.y || 0) + 'px) scale(' + (o.s == null ? 1 : o.s) + ')';
    el.style.transform = tr;
    el.style.opacity = o.o == null ? 1 : o.o;
    el.style.filter = o.blur ? 'blur(' + o.blur + 'px)' : 'none';
    if (o.clip != null) el.style.clipPath = 'inset(' + ((1 - o.clip) * 100) + '% 0 0 0)';
    el.style.visibility = (o.o === 0) ? 'hidden' : 'visible';
  };
  /* revela una línea con máscara: sube desde abajo */
  M.rise = function (el, t, a, dur) {
    var p = M.ease.outExpo(M.seg(t, a, a + (dur || .5)));
    M.set(el, { o: p > 0 ? 1 : 0, y: (1 - p) * 60, clip: p });
  };
  /* pseudo-aleatorio determinista */
  M.rand = function (n) { var x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  /* glitch con separación de color en dorado y azul de marca */
  M.glitch = function (el, t, amount) {
    if (typeof el === 'string') el = document.querySelector(el);
    var k = Math.floor(t * 30);
    var on = amount > 0 && M.rand(k) < amount;
    var dx = on ? (M.rand(k + 7) * 2 - 1) * 14 : 0;
    el.style.textShadow = on ? (dx + 'px 0 rgba(78,128,178,.9), ' + (-dx) + 'px 0 rgba(172,144,106,.9)') : 'none';
    el.style.transform = (el.style.transform || '') + (on ? ' translateX(' + (dx * .4) + 'px)' : '');
  };
  M.count = function (t, a, b, from, to) { return Math.round(M.lerp(from, to, M.ease.outCubic(M.seg(t, a, b)))); };
  M.fmt = function (n) { return n.toLocaleString('es-EC'); };
  /* escribe texto letra a letra */
  M.type = function (el, text, t, a, cps) {
    if (typeof el === 'string') el = document.querySelector(el);
    var n = Math.max(0, Math.floor((t - a) * (cps || 22)));
    el.textContent = text.slice(0, n);
  };
  window.VM = M;
})();
