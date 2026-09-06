(function () {
  'use strict';

  var prefetched = Object.create(null);
  var sameOrigin = location.origin;
  var coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;

  function pathKey(href) {
    try {
      var u = new URL(href, sameOrigin + '/');
      if (u.origin !== sameOrigin) return null;
      if (u.pathname === location.pathname && !u.search) return null;
      return u.pathname + u.search;
    } catch (e) {
      return null;
    }
  }

  function prefetch(href) {
    var key = pathKey(href);
    if (!key || prefetched[key]) return;
    prefetched[key] = 1;
    var link = document.createElement('link');
    link.rel = 'prefetch';
    link.as = 'document';
    link.href = key;
    document.head.appendChild(link);
  }

  function findAnchor(t) {
    if (!t) return null;
    if (t.closest) return t.closest('a[href]');
    while (t && t !== document.body) {
      if (t.tagName === 'A' && t.getAttribute('href')) return t;
      t = t.parentNode;
    }
    return null;
  }

  function onIntent(e) {
    var a = findAnchor(e.target);
    if (!a) return;
    var href = a.getAttribute('href');
    if (!href || href.charAt(0) !== '/' || href.indexOf('mailto:') === 0) return;
    prefetch(href);
  }

  // Mobilde touchstart spam'i yavaşlatıyordu — yalnız hover/focus
  if (!coarse) {
    document.addEventListener('mouseover', onIntent, true);
  }
  document.addEventListener('focusin', onIntent, true);

  // Mobil menü toggle (tüm sayfalar)
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    links.addEventListener('click', function (e) {
      if (e.target && e.target.tagName === 'A') {
        links.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }
})();
