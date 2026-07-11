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
  var words = ["Niyet", "Tutku", "Visyon", "İrade", "Disiplin", "Özgüven"];
  var listItems = [
    "Bu yıl daha cesur olacağım",
    "Her gün küçük bir adım",
    "Hayalim gerçek bir plan",
    "Zincirimi koruyacağım",
    "Kendime söz verdim"
  ];
  var wordIndex = 0;
  var listIndex = 0;
  var dpr = Math.min(window.devicePixelRatio || 1, 2);

  function resize() {
    var rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    initParticles(rect.width, rect.height);
  }

  function initParticles(w, h) {
    particles = [];
    var count = Math.floor((w * h) / 12000);
    for (var i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 2.2 + 0.6,
        vy: -(Math.random() * 0.35 + 0.08),
        vx: (Math.random() - 0.5) * 0.15,
        color: ["155, 140, 245", "245, 221, 208", "212, 232, 220", "196, 184, 255"][Math.floor(Math.random() * 4)],
        alpha: Math.random() * 0.35 + 0.12
      });
    }
  }

  function draw(w, h) {
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
    requestAnimationFrame(function () {
      draw(w, h);
    });
  }

  function cycleWord() {
    if (!centerWord) return;
    centerWord.classList.add("fade");
    setTimeout(function () {
      wordIndex = (wordIndex + 1) % words.length;
      centerWord.textContent = words[wordIndex];
      centerWord.classList.remove("fade");
    }, 500);
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
  var rect = canvas.parentElement.getBoundingClientRect();
  if (!reducedMotion) draw(rect.width, rect.height);

  window.addEventListener("resize", resize);
  if (!reducedMotion) {
    setInterval(cycleWord, 3200);
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
      if (!isPaused) showSlide(activeSlide + 1);
    }, 4200);
  }
})();
