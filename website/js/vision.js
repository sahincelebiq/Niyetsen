(function () {
  "use strict";

  var canvas = document.getElementById("vision-canvas");
  if (!canvas) return;

  var reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  var reducedMotion = reducedMotionQuery.matches;
  var ctx = canvas.getContext("2d");
  var particles = [];
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
  var listIndex = 0;
  var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
  var stageWidth = 0;
  var stageHeight = 0;
  var animating = false;
  var rafId = 0;
  var heroVisible = true;
  var pageVisible = !document.hidden;

  function resize() {
    var rect = canvas.parentElement.getBoundingClientRect();
    stageWidth = rect.width;
    stageHeight = rect.height;
    canvas.width = stageWidth * dpr;
    canvas.height = stageHeight * dpr;
    canvas.style.width = stageWidth + "px";
    canvas.style.height = stageHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    initParticles(stageWidth, stageHeight);
  }

  function initParticles(w, h) {
    particles = [];
    var density = window.innerWidth < 768 ? 18000 : 12000;
    var count = Math.min(Math.floor((w * h) / density), window.innerWidth < 768 ? 32 : 52);
    for (var i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 2 + 0.6,
        vy: -(Math.random() * 0.28 + 0.06),
        vx: (Math.random() - 0.5) * 0.12,
        color: ["155, 140, 245", "245, 221, 208", "212, 232, 220", "196, 184, 255"][Math.floor(Math.random() * 4)],
        alpha: Math.random() * 0.3 + 0.1
      });
    }
  }

  function shouldAnimate() {
    return !reducedMotion && heroVisible && pageVisible;
  }

  function tick() {
    rafId = 0;
    if (!shouldAnimate()) return;

    var w = stageWidth;
    var h = stageHeight;
    ctx.clearRect(0, 0, w, h);
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      if (p.y < -10) {
        p.y = h + 10;
        p.x = Math.random() * w;
      }
      if (p.x < -10) p.x = w + 10;
      if (p.x > w + 10) p.x = -10;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(" + p.color + ", " + p.alpha + ")";
      ctx.fill();
    }
    rafId = requestAnimationFrame(tick);
  }

  function startAnimation() {
    if (animating || !shouldAnimate()) return;
    animating = true;
    if (!rafId) rafId = requestAnimationFrame(tick);
  }

  function stopAnimation() {
    animating = false;
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    }
  }

  function cycleCenterWord() {
    if (!centerWord || !shouldAnimate()) return;
    centerWord.classList.add("fade");
    setTimeout(function () {
      wordIndex = (wordIndex + 1) % centerWords.length;
      centerWord.textContent = centerWords[wordIndex];
      centerWord.classList.remove("fade");
    }, 600);
  }

  function addListItem() {
    if (!listEl || listIndex >= listItems.length) return;
    var el = document.createElement("span");
    el.className = "vision-list-item";
    el.textContent = listItems[listIndex];
    el.style.animationDelay = listIndex * 0.15 + "s";
    listEl.appendChild(el);
    listIndex++;
  }

  resize();
  if (centerWord) centerWord.textContent = centerWords[0];

  window.addEventListener("resize", function () {
    resize();
    if (shouldAnimate()) startAnimation();
  });

  document.addEventListener("visibilitychange", function () {
    pageVisible = !document.hidden;
    if (pageVisible && heroVisible) startAnimation();
    else stopAnimation();
  });

  if ("IntersectionObserver" in window) {
    var heroObserver = new IntersectionObserver(function (entries) {
      heroVisible = entries[0].isIntersecting;
      if (heroVisible && pageVisible) startAnimation();
      else stopAnimation();
    }, { root: null, threshold: 0.05 });
    heroObserver.observe(canvas.parentElement);
  }

  if (!reducedMotion) {
    startAnimation();
    setInterval(cycleCenterWord, 4200);
    listItems.forEach(function (_, i) {
      setTimeout(addListItem, 800 + i * 600);
    });
  } else {
    listItems.forEach(addListItem);
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
    slides.forEach(function (slide, slideIndex) {
      slide.classList.toggle("is-active", slideIndex === activeSlide);
    });
    dots.forEach(function (dot, dotIndex) {
      dot.classList.toggle("is-active", dotIndex === activeSlide);
      dot.setAttribute("aria-current", dotIndex === activeSlide ? "true" : "false");
    });
    if (title) title.textContent = slides[activeSlide].getAttribute("data-title");
  }

  dots.forEach(function (dot, index) {
    dot.addEventListener("click", function () {
      showSlide(index);
    });
  });

  showcase.addEventListener("mouseenter", function () {
    isPaused = true;
  });
  showcase.addEventListener("mouseleave", function () {
    isPaused = false;
  });
  showcase.addEventListener("focusin", function () {
    isPaused = true;
  });
  showcase.addEventListener("focusout", function () {
    isPaused = false;
  });

  if (!reducedMotion) {
    setInterval(function () {
      if (!isPaused && pageVisible) showSlide(activeSlide + 1);
    }, 4200);
  }
})();
