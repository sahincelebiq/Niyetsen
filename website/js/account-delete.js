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

  function setStatus(el, type, message) {
    if (!el) return;
    el.hidden = false;
    el.className = 'early-access-status early-access-status--' + type;
    el.textContent = message;
  }

  function buildFormData(formData) {
    var fd = new FormData();
    fd.append('name', (formData.get('name') || '').toString().trim());
    fd.append('email', (formData.get('email') || '').toString().trim());
    var message = (formData.get('message') || '').toString().trim();
    if (message) fd.append('message', message);
    fd.append('confirm_delete', formData.get('confirm_delete') ? 'Evet' : 'Hayır');
    fd.append('kaynak', window.location.pathname || '/hesap-silme');
    fd.append('_subject', 'Niyetsen — Hesap silme talebi');
    fd.append('_captcha', 'false');
    fd.append('_template', 'table');
    fd.append('_replyto', (formData.get('email') || '').toString().trim());
    fd.append('_autoresponse', 'Hesap silme talebin alındı. Kayıtlı e-posta doğrulandıktan sonra işlem yapılır.');
    return fd;
  }

  function postToEndpoint(endpoint, body) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, FETCH_TIMEOUT_MS);
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
        try { data = text ? JSON.parse(text) : {}; } catch (e) { data = {}; }
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
      if (index >= endpoints.length) return Promise.reject(new Error('endpoint'));
      return postToEndpoint(endpoints[index], body).catch(function () {
        return tryNext(index + 1);
      });
    }
    return tryNext(0);
  }

  function handleSubmit(event) {
    var form = event.target;
    if (!form || form.id !== 'account-delete-form') return;
    event.preventDefault();

    var statusEl = document.getElementById('account-delete-status');
    var submitBtn = form.querySelector('[type="submit"]');
    var formData = new FormData(form);

    if (formData.get('_honey')) return;

    var name = (formData.get('name') || '').toString().trim();
    var email = (formData.get('email') || '').toString().trim();
    if (!name || !email) {
      setStatus(statusEl, 'error', 'Lütfen ad ve hesap e-postasını doldur.');
      return;
    }
    if (!formData.get('confirm_delete')) {
      setStatus(statusEl, 'error', 'Silme onay kutusunu işaretle.');
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Gönderiliyor…';
    }
    setStatus(statusEl, 'loading', 'Talebin iletiliyor…');

    submitWithFallback(buildFormData(formData))
      .then(function () {
        form.reset();
        setStatus(statusEl, 'success', 'Talebin alındı. Kayıtlı e-posta doğrulandıktan sonra hesabın silinir.');
      })
      .catch(function () {
        form.removeAttribute('novalidate');
        if (typeof form.requestSubmit === 'function') form.requestSubmit();
        else form.submit();
      })
      .finally(function () {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Silme talebi gönder';
        }
      });
  }

  function showRedirectSuccess() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('silme') !== 'basarili') return;
    setStatus(
      document.getElementById('account-delete-status'),
      'success',
      'Talebin alındı. Kayıtlı e-posta doğrulandıktan sonra hesabın silinir.'
    );
    if (window.history && window.history.replaceState) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }

  document.addEventListener('submit', handleSubmit);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', showRedirectSuccess);
  } else {
    showRedirectSuccess();
  }
})();
