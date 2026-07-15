(function () {
  'use strict';

  var cfg = window.NIYETSEN_MARKETING || {};
  var emailTo = (cfg.EARLY_ACCESS_EMAIL || 'ai@niyetsen.com').trim();
  var hashEndpoint = (cfg.EARLY_ACCESS_FORM_ENDPOINT || '').trim();
  if (!hashEndpoint && cfg.FORMSUBMIT_FORM_HASH) {
    hashEndpoint = 'https://formsubmit.co/ajax/' + cfg.FORMSUBMIT_FORM_HASH;
  }
  var emailEndpoint = 'https://formsubmit.co/ajax/' + encodeURIComponent(emailTo);
  var FETCH_TIMEOUT_MS = 15000;

  function trackSignup() {
    if (typeof window.gtag !== 'function') return;
    try {
      window.gtag('event', 'early_access_signup', {
        event_category: 'engagement',
        event_label: 'Erken erişim formu'
      });
      if (cfg.GOOGLE_ADS_ID) {
        window.gtag('event', 'conversion', {
          send_to: cfg.GOOGLE_ADS_ID
        });
      }
    } catch (e) {}
  }

  function setStatus(el, type, message) {
    if (!el) return;
    el.hidden = false;
    el.className = 'early-access-status early-access-status--' + type;
    el.textContent = message;
  }

  function getStatusEl(form) {
    return form.querySelector('.early-access-status') ||
      document.getElementById('early-access-status');
  }

  function buildFormData(formData) {
    var fd = new FormData();
    fd.append('name', (formData.get('name') || '').toString().trim());
    fd.append('email', (formData.get('email') || '').toString().trim());
    fd.append('platform', (formData.get('platform') || '').toString().trim());
    var message = (formData.get('message') || '').toString().trim();
    if (message) fd.append('message', message);
    fd.append('_subject', 'Niyetsen — Erken erişim talebi');
    fd.append('_captcha', 'false');
    fd.append('_template', 'table');
    fd.append('_replyto', (formData.get('email') || '').toString().trim());
    fd.append('_autoresponse', 'Talebin alındı. Niyetsen ekibi en kısa sürede ai@niyetsen.com üzerinden dönüş yapacak.');
    return fd;
  }

  function postToEndpoint(endpoint, body) {
    var controller = new AbortController();
    var timer = setTimeout(function () {
      controller.abort();
    }, FETCH_TIMEOUT_MS);

    return fetch(endpoint, {
      method: 'POST',
      headers: { Accept: 'application/json' },
      body: body,
      mode: 'cors',
      credentials: 'omit',
      signal: controller.signal
    }).then(function (res) {
      clearTimeout(timer);
      return res.text().then(function (text) {
        var data = {};
        try {
          data = text ? JSON.parse(text) : {};
        } catch (e) {
          data = { raw: text };
        }
        if (data.success === 'false' || data.success === false) {
          throw new Error(data.message || 'FormSubmit reddetti');
        }
        if (!res.ok && data.success !== true && data.success !== 'true') {
          throw new Error(data.message || 'HTTP ' + res.status);
        }
        return data;
      });
    }).catch(function (err) {
      clearTimeout(timer);
      throw err;
    });
  }

  function submitWithFallback(body) {
    var endpoints = [hashEndpoint, emailEndpoint];
    function tryNext(index) {
      if (index >= endpoints.length) {
        return Promise.reject(new Error('Tüm endpointler başarısız'));
      }
      return postToEndpoint(endpoints[index], body).catch(function () {
        return tryNext(index + 1);
      });
    }
    return tryNext(0);
  }

  function nativeSubmit(form) {
    form.removeAttribute('novalidate');
    if (typeof form.requestSubmit === 'function') {
      form.requestSubmit();
    } else {
      form.submit();
    }
  }

  function handleSubmit(event) {
    var form = event.target;
    if (!form || form.id !== 'early-access-form') return;
    event.preventDefault();

    var statusEl = getStatusEl(form);
    var submitBtn = form.querySelector('[type="submit"]');
    var formData = new FormData(form);

    if (formData.get('_honey')) return;

    var name = (formData.get('name') || '').toString().trim();
    var email = (formData.get('email') || '').toString().trim();
    var platform = (formData.get('platform') || '').toString().trim();

    if (!email) {
      setStatus(statusEl, 'error', 'Lütfen geçerli bir e-posta adresi gir.');
      return;
    }
    if (!name || !platform) {
      setStatus(statusEl, 'error', 'Lütfen ad ve platform alanlarını doldur.');
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Gönderiliyor…';
    }
    setStatus(statusEl, 'loading', 'Talebin iletiliyor…');

    var body = buildFormData(formData);

    submitWithFallback(body)
      .then(function () {
        form.reset();
        trackSignup();
        setStatus(statusEl, 'success', 'Talebin alındı. En kısa sürede ' + emailTo + ' üzerinden dönüş yapacağız.');
      })
      .catch(function () {
        setStatus(statusEl, 'loading', 'Alternatif yöntemle iletiliyor…');
        nativeSubmit(form);
      })
      .finally(function () {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Erken erişim talep et';
        }
      });
  }

  function showRedirectSuccess() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('erken-erisim') !== 'basarili') return;

    var form = document.getElementById('early-access-form');
    var statusEl = form ? getStatusEl(form) : document.getElementById('early-access-status');
    setStatus(statusEl, 'success', 'Talebin alındı. En kısa sürede ' + emailTo + ' üzerinden dönüş yapacağız.');
    trackSignup();

    if (window.history && window.history.replaceState) {
      var clean = window.location.pathname + window.location.hash;
      window.history.replaceState({}, document.title, clean);
    }
  }

  document.addEventListener('submit', handleSubmit);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', showRedirectSuccess);
  } else {
    showRedirectSuccess();
  }
})();
