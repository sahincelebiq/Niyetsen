(function () {
  'use strict';

  // Progressive enhancement: CSS defaults visible; hide only when JS runs
  try { document.documentElement.classList.add('js'); } catch (e) {}

  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var nodes = document.querySelectorAll('.reveal');
  if (!nodes.length) return;

  function showAll() {
    for (var i = 0; i < nodes.length; i++) nodes[i].classList.add('is-visible');
  }

  if (reduced || !('IntersectionObserver' in window)) {
    showAll();
    return;
  }

  // Above-fold: hemen görünür (IO bekleme = kaymış/boş hissi)
  var vh = window.innerHeight || 800;
  for (var j = 0; j < nodes.length; j++) {
    var r = nodes[j].getBoundingClientRect();
    if (r.top < vh * 0.92) nodes[j].classList.add('is-visible');
  }

  var io = new IntersectionObserver(function (entries) {
    for (var k = 0; k < entries.length; k++) {
      if (entries[k].isIntersecting) {
        entries[k].target.classList.add('is-visible');
        io.unobserve(entries[k].target);
      }
    }
  }, { rootMargin: '0px 0px -4% 0px', threshold: 0.06 });

  for (var n = 0; n < nodes.length; n++) {
    if (!nodes[n].classList.contains('is-visible')) io.observe(nodes[n]);
  }
})();
