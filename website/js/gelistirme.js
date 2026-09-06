(function () {
  'use strict';

  var root = document.getElementById('dev-explorer');
  if (!root) return;

  var viewBtns = root.querySelectorAll('[data-view]');
  var views = root.querySelectorAll('[data-panel-view]');
  var phaseBtns = root.querySelectorAll('[data-phase]');
  var phasePanels = root.querySelectorAll('[data-phase-panel]');

  function setView(name) {
    for (var i = 0; i < viewBtns.length; i++) {
      var on = viewBtns[i].getAttribute('data-view') === name;
      viewBtns[i].classList.toggle('is-active', on);
      viewBtns[i].setAttribute('aria-selected', on ? 'true' : 'false');
    }
    for (var j = 0; j < views.length; j++) {
      var show = views[j].getAttribute('data-panel-view') === name;
      views[j].hidden = !show;
      views[j].classList.toggle('is-active', show);
    }
    try { history.replaceState(null, '', '#' + name); } catch (e) {}
  }

  function setPhase(id) {
    for (var i = 0; i < phaseBtns.length; i++) {
      var on = phaseBtns[i].getAttribute('data-phase') === id;
      phaseBtns[i].classList.toggle('is-active', on);
      phaseBtns[i].setAttribute('aria-expanded', on ? 'true' : 'false');
    }
    for (var j = 0; j < phasePanels.length; j++) {
      var show = phasePanels[j].getAttribute('data-phase-panel') === id;
      phasePanels[j].hidden = !show;
      phasePanels[j].classList.toggle('is-active', show);
    }
  }

  for (var v = 0; v < viewBtns.length; v++) {
    viewBtns[v].addEventListener('click', function (e) {
      e.preventDefault();
      var name = this.getAttribute('data-view');
      setView(name);
      if (name === 'fazlar') {
        var active = root.querySelector('.phase-tile.is-active');
        if (active) setPhase(active.getAttribute('data-phase'));
      }
    });
  }

  for (var p = 0; p < phaseBtns.length; p++) {
    phaseBtns[p].addEventListener('click', function (e) {
      e.preventDefault();
      setPhase(this.getAttribute('data-phase'));
      setView('fazlar');
    });
  }

  var hash = (location.hash || '').replace('#', '');
  if (hash === 'backend' || hash === 'arayuz' || hash === 'kullanici' || hash === 'fazlar') {
    setView(hash);
  } else {
    setView('fazlar');
  }
  setPhase('7');
})();
