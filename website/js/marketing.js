(function () {
  var cfg = window.NIYETSEN_MARKETING || {};
  var adsId = (cfg.GOOGLE_ADS_ID || '').trim();
  var gaId = (cfg.GA4_MEASUREMENT_ID || '').trim();
  var gsc = (cfg.GSC_VERIFICATION || '').trim();
  var storageKey = 'niyetsen_cookie_consent';

  if (gsc) {
    var meta = document.createElement('meta');
    meta.name = 'google-site-verification';
    meta.content = gsc;
    document.head.appendChild(meta);
  }

  function hasMarketingIds() {
    return Boolean(adsId || gaId);
  }

  function readConsent() {
    try {
      var stored = localStorage.getItem(storageKey);
      if (stored) return stored;
    } catch (e) {}
    var match = document.cookie.match(new RegExp('(?:^|; )' + storageKey + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : null;
  }

  function writeConsent(value) {
    try { localStorage.setItem(storageKey, value); } catch (e) {}
    document.cookie = storageKey + '=' + encodeURIComponent(value) + ';path=/;max-age=31536000;SameSite=Lax';
  }

  function grantConsent() {
    if (typeof window.gtag !== 'function') return;
    try {
      window.gtag('consent', 'update', {
        ad_storage: 'granted',
        analytics_storage: 'granted',
        ad_user_data: 'granted',
        ad_personalization: 'granted'
      });
    } catch (e) {}
  }

  function loadGtag() {
    if (!hasMarketingIds() || window.__niyetsenGtagLoaded) return;
    window.__niyetsenGtagLoaded = true;

    var primaryId = gaId || adsId;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };

    window.gtag('consent', 'default', {
      ad_storage: 'denied',
      analytics_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied',
      wait_for_update: 500
    });

    window.gtag('js', new Date());

    var script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(primaryId);
    document.head.appendChild(script);

    if (gaId) {
      window.gtag('config', gaId, { anonymize_ip: true, send_page_view: true });
    }
    if (adsId) {
      window.gtag('config', adsId);
    }
  }

  function dismissBar() {
    var bar = document.getElementById('cookie-consent');
    if (!bar) return;
    bar.classList.add('is-hidden');
    bar.setAttribute('hidden', '');
    bar.setAttribute('aria-hidden', 'true');
    window.setTimeout(function () {
      if (bar.parentNode) bar.parentNode.removeChild(bar);
    }, 280);
  }

  function acceptConsent() {
    writeConsent('granted');
    dismissBar();
    if (!window.__niyetsenGtagLoaded) loadGtag();
    grantConsent();
  }

  function rejectConsent() {
    writeConsent('denied');
    dismissBar();
  }

  function handleConsentAction(action) {
    if (action === 'accept') acceptConsent();
    if (action === 'reject') rejectConsent();
  }

  function bindConsentBar(bar) {
    var buttons = bar.querySelectorAll('[data-consent]');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        var action = event.currentTarget.getAttribute('data-consent');
        handleConsentAction(action);
      });
    }

    bar.addEventListener('click', function (event) {
      var trigger = event.target && event.target.closest
        ? event.target.closest('[data-consent]')
        : null;
      if (!trigger) return;
      event.preventDefault();
      handleConsentAction(trigger.getAttribute('data-consent'));
    });
  }

  function renderConsentBar() {
    if (!hasMarketingIds() || document.getElementById('cookie-consent')) return;

    var bar = document.createElement('div');
    bar.id = 'cookie-consent';
    bar.className = 'cookie-consent';
    bar.setAttribute('role', 'dialog');
    bar.setAttribute('aria-modal', 'false');
    bar.setAttribute('aria-label', 'Çerez tercihi');
    bar.innerHTML =
      '<p>Bu site, reklam ve trafik ölçümü için Google etiketlerini kullanır. ' +
      '<a href="/gizlilik.html">Gizlilik politikası</a></p>' +
      '<div class="cookie-consent-actions">' +
      '<button type="button" class="button secondary cookie-consent-btn" data-consent="reject">Reddet</button>' +
      '<button type="button" class="button cookie-consent-btn" data-consent="accept">Kabul et</button>' +
      '</div>';

    document.body.appendChild(bar);
    bindConsentBar(bar);
  }

  function init() {
    if (!hasMarketingIds()) return;

    loadGtag();

    var consent = readConsent();
    if (consent === 'granted') {
      grantConsent();
      return;
    }
    if (consent === 'denied') return;

    renderConsentBar();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
