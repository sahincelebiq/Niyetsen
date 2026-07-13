(function () {
  'use strict';

  var cfg = window.NIYETSEN_MARKETING || {};
  var endpoint = (cfg.EARLY_ACCESS_FORM_ENDPOINT || '').trim();
  var emailTo = (cfg.EARLY_ACCESS_EMAIL || 'ai@niyetsen.com').trim();

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

  function handleSubmit(event) {
    var form = event.target;
    if (!form || form.id !== 'early-access-form') return;
    event.preventDefault();

    var statusEl = document.getElementById('early-access-status');
    var submitBtn = form.querySelector('[type="submit"]');
    var formData = new FormData(form);

    formData.append('_subject', 'Niyetsen — Erken erişim talebi');
    formData.append('_captcha', 'false');
    formData.append('_template', 'table');
    formData.append('_autoresponse', 'Talebin alındı. Niyetsen ekibi en kısa sürede ai@niyetsen.com üzerinden dönüş yapacak.');

    if (!endpoint) {
      var name = formData.get('name') || '';
      var email = formData.get('email') || '';
      var platform = formData.get('platform') || '';
      var note = formData.get('message') || '';
      var body = encodeURIComponent(
        'Erken erişim talebi\n\nAd: ' + name + '\nE-posta: ' + email + '\nPlatform: ' + platform + '\nNot: ' + note
      );
      window.location.href = 'mailto:' + encodeURIComponent(emailTo) +
        '?subject=' + encodeURIComponent('Niyetsen — Erken erişim talebi') +
        '&body=' + body;
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Gönderiliyor…';
    }
    setStatus(statusEl, 'loading', 'Talebin iletiliyor…');

    fetch(endpoint, {
      method: 'POST',
      body: formData,
      headers: { Accept: 'application/json' }
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Form gönderilemedi');
        return res.json();
      })
      .then(function () {
        form.reset();
        trackSignup();
        setStatus(statusEl, 'success', 'Talebin alındı. En kısa sürede ' + emailTo + ' üzerinden dönüş yapacağız.');
      })
      .catch(function () {
        setStatus(statusEl, 'error', 'Gönderilemedi. Lütfen tekrar dene veya doğrudan ' + emailTo + ' adresine yaz.');
      })
      .finally(function () {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Erken erişim talep et';
        }
      });
  }

  document.addEventListener('submit', handleSubmit);
})();
