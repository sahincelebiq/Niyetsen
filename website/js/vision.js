(function () {
  "use strict";

  var canvas = document.getElementById("vision-canvas");
  var centerWord = document.getElementById("vision-center-word");
  var listEl = document.getElementById("vision-list");
  var listItems = [
    "Bu yıl daha cesur olacağım",
    "Her gün küçük bir adım",
    "Hayalim gerçek bir plan",
    "Zincirimi koruyacağım",
    "Kendime söz verdim"
  ];
  var centerWords = ["Vizyon", "Misyon", "Niyetsen"];
  var wordIndex = 0;
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var saveData = !!(navigator.connection && navigator.connection.saveData);
  var isNarrow = window.matchMedia("(max-width: 900px)").matches;
  var coarse = window.matchMedia("(pointer: coarse)").matches;
  // Mobil / tasarruf / düşük güç: canvas YOK — asıl yavaşlık buradaydı
  var skipCanvas = !canvas || reducedMotion || saveData || isNarrow || coarse;

  function fillList() {
    if (!listEl) return;
    listItems.forEach(function (text, i) {
      var el = document.createElement("span");
      el.className = "vision-list-item";
      el.textContent = text;
      if (!reducedMotion) el.style.animationDelay = i * 0.12 + "s";
      listEl.appendChild(el);
    });
  }

  if (centerWord) centerWord.textContent = centerWords[0];
  fillList();

  if (!skipCanvas && centerWord && !reducedMotion) {
    setInterval(function () {
      centerWord.classList.add("fade");
      setTimeout(function () {
        wordIndex = (wordIndex + 1) % centerWords.length;
        centerWord.textContent = centerWords[wordIndex];
        centerWord.classList.remove("fade");
      }, 500);
    }, 4800);
  }

  if (skipCanvas) {
    if (canvas) {
      canvas.style.display = "none";
      canvas.setAttribute("aria-hidden", "true");
    }
  } else {
    var ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });
    var particles = [];
    var dpr = Math.min(window.devicePixelRatio || 1, 1.25);
    var w = 0;
    var h = 0;
    var rafId = 0;
    var running = false;
    var heroVisible = true;
    var pageVisible = !document.hidden;
    var last = 0;
    var frameMs = 1000 / 28;

    function resize() {
      var rect = canvas.parentElement.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      particles = [];
      var count = Math.min(18, Math.floor((w * h) / 28000));
      for (var i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * w,
          y: Math.random() * h,
          r: Math.random() * 1.6 + 0.5,
          vy: -(Math.random() * 0.2 + 0.05),
          vx: (Math.random() - 0.5) * 0.08,
          color: ["155,140,245", "245,221,208", "212,232,220"][i % 3],
          alpha: Math.random() * 0.22 + 0.08
        });
      }
    }

    function tick(ts) {
      rafId = 0;
      if (!running || !heroVisible || !pageVisible) return;
      if (ts - last < frameMs) {
        rafId = requestAnimationFrame(tick);
        return;
      }
      last = ts;
      ctx.clearRect(0, 0, w, h);
      for (var i = 0; i < particles.length; i++) {
        var p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        if (p.y < -8) {
          p.y = h + 8;
          p.x = Math.random() * w;
        }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(" + p.color + "," + p.alpha + ")";
        ctx.fill();
      }
      rafId = requestAnimationFrame(tick);
    }

    function start() {
      if (running) return;
      running = true;
      if (!rafId) rafId = requestAnimationFrame(tick);
    }

    function stop() {
      running = false;
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      }
    }

    resize();
    start();
    window.addEventListener("resize", resize, { passive: true });
    document.addEventListener("visibilitychange", function () {
      pageVisible = !document.hidden;
      if (pageVisible && heroVisible) start();
      else stop();
    });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        heroVisible = entries[0].isIntersecting;
        if (heroVisible && pageVisible) start();
        else stop();
      }, { threshold: 0.08 }).observe(canvas.parentElement);
    }
  }

  var showcase = document.getElementById("app-showcase");
  if (!showcase) return;

  var slides = Array.prototype.slice.call(showcase.querySelectorAll(".showcase-slide"));
  var dots = Array.prototype.slice.call(showcase.querySelectorAll(".showcase-dot"));
  var title = document.getElementById("showcase-title");
  var activeSlide = 0;
  var isPaused = false;

  function showSlide(index) {
    activeSlide = (index + slides.length) % slides.length;
    slides.forEach(function (slide, i) {
      slide.classList.toggle("is-active", i === activeSlide);
    });
    dots.forEach(function (dot, i) {
      dot.classList.toggle("is-active", i === activeSlide);
      dot.setAttribute("aria-current", i === activeSlide ? "true" : "false");
    });
    if (title) title.textContent = slides[activeSlide].getAttribute("data-title");
  }

  dots.forEach(function (dot, index) {
    dot.addEventListener("click", function () {
      showSlide(index);
    });
  });

  showcase.addEventListener("mouseenter", function () { isPaused = true; });
  showcase.addEventListener("mouseleave", function () { isPaused = false; });
  showcase.addEventListener("focusin", function () { isPaused = true; });
  showcase.addEventListener("focusout", function () { isPaused = false; });

  if (!reducedMotion && !saveData) {
    setInterval(function () {
      if (!isPaused && !document.hidden) showSlide(activeSlide + 1);
    }, isNarrow ? 5600 : 4500);
  }
})();
