(function () {
  'use strict';

  var TARGET = 'erken-erisim';
  var STORAGE_KEY = 'niyetsenScrollTarget';

  function scrollToTarget() {
    var el = document.getElementById(TARGET);
    if (!el) return false;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return true;
  }

  function cleanUrl() {
    if (window.location.hash) {
      history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  }

  function isErkenErisimLink(href) {
    return href === '#' + TARGET || href === '/#' + TARGET;
  }

  document.addEventListener('click', function (e) {
    // Yalnız gerçek link düğümünde yakala; nav'ı bozma
    var link = e.target.closest('a');
    if (!link || !link.getAttribute) return;

    var scrollTo = link.getAttribute('data-scroll-to');
    var href = link.getAttribute('href') || '';

    // Erken erişim dışındaki tüm linkler (Blog, Geliştirme, #felsefe…) doğal aksiyon
    var isEarly = scrollTo === TARGET || isErkenErisimLink(href);
    if (!isEarly) return;

    e.preventDefault();

    if (window.location.pathname !== '/' && window.location.pathname !== '/index.html') {
      try { sessionStorage.setItem(STORAGE_KEY, TARGET); } catch (err) {}
      window.location.href = '/#' + TARGET;
      return;
    }

    scrollToTarget();
    cleanUrl();
  });

  function onReady() {
    var pending = null;
    try { pending = sessionStorage.getItem(STORAGE_KEY); } catch (err) {}
    if (pending === TARGET) {
      try { sessionStorage.removeItem(STORAGE_KEY); } catch (err) {}
      setTimeout(function () {
        scrollToTarget();
        cleanUrl();
      }, 150);
      return;
    }
    if (window.location.hash === '#' + TARGET) {
      setTimeout(function () {
        scrollToTarget();
        cleanUrl();
      }, 150);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onReady);
  } else {
    onReady();
  }
})();
