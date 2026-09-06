(function () {
  'use strict';

  var TARGET = 'erken-erisim';
  var PAGE = '/erkenerisim';

  function isLegacyEarlyLink(href, scrollTo) {
    return scrollTo === TARGET ||
      href === '#' + TARGET ||
      href === '/#' + TARGET;
  }

  document.addEventListener('click', function (e) {
    var link = e.target.closest('a');
    if (!link || !link.getAttribute) return;

    var scrollTo = link.getAttribute('data-scroll-to');
    var href = link.getAttribute('href') || '';
    if (!isLegacyEarlyLink(href, scrollTo)) return;

    e.preventDefault();
    window.location.href = PAGE;
  });

  function onReady() {
    if (window.location.hash === '#' + TARGET) {
      window.location.replace(PAGE);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onReady);
  } else {
    onReady();
  }
})();
