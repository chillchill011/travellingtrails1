/* Travelling Trails: small, accessible homepage featured-stories carousel.
 * Uses the three latest published featured posts from Eleventy.
 * The first story remains available when JS is disabled.
 */
(function () {
  'use strict';

  function initHeroCarousel() {
    const hero = document.querySelector('.tt-home .tt-hero');
    if (!hero) return;

    const slides = Array.from(hero.querySelectorAll('.tt-hero-slides .tt-hero-slide'));
    const featureLink = hero.querySelector('[data-hero-feature]');
    const featureTitle = hero.querySelector('[data-hero-title]');
    const previous = hero.querySelector('[data-hero-previous]');
    const next = hero.querySelector('[data-hero-next]');
    const counter = hero.querySelector('[data-hero-count]');
    const announcement = hero.querySelector('[data-hero-announcement]');
    if (slides.length < 2 || !featureLink || !featureTitle || !previous || !next) return;

    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    let current = 0;
    let timer = null;
    let hovered = false;
    let focused = false;
    let visible = true;

    let requestId = 0;
    let changing = false;
    const pendingImages = new WeakMap();

    // Fetch original, full-quality photos only when requested. Keep the
    // existing slide visible until the next photo is loaded and decoded.
    function prepareSlide(img) {
      if (img.complete && img.naturalWidth > 0) return Promise.resolve(true);
      if (pendingImages.has(img)) return pendingImages.get(img);
      const pending = new Promise(resolve => {
        const finish = ok => {
          img.removeEventListener('load', loaded);
          img.removeEventListener('error', failed);
          if (ok && typeof img.decode === 'function') {
            img.decode().then(() => resolve(true), () => resolve(img.naturalWidth > 0));
          } else resolve(ok);
        };
        const loaded = () => finish(true);
        const failed = () => finish(false);
        img.addEventListener('load', loaded);
        img.addEventListener('error', failed);
        if (img.dataset.src) {
          img.loading = 'eager';
          img.fetchPriority = 'auto';
          img.src = img.dataset.src;
          delete img.dataset.src;
        }
        if (img.complete && img.naturalWidth > 0) finish(true);
      });
      pendingImages.set(img, pending);
      pending.then(() => pendingImages.delete(img));
      return pending;
    }

    async function showSlide(index, announce) {
      const target = (index + slides.length) % slides.length;
      const ticket = ++requestId;
      changing = true;
      if (target !== current && !await prepareSlide(slides[target])) {
        if (ticket === requestId) changing = false;
        return;
      }
      if (ticket !== requestId) return;
      changing = false;
      current = target;
      slides.forEach((slide, i) => slide.classList.toggle('is-active', i === current));

      const active = slides[current];
      const title = active.dataset.storyTitle || 'Featured journey';
      const url = active.dataset.storyUrl || '#';
      featureLink.setAttribute('href', url);
      featureTitle.textContent = title;
      featureLink.setAttribute('aria-label', 'Read featured journey: ' + title);
      if (counter) counter.textContent = String(current + 1).padStart(2, '0');
      if (announcement && announce) {
        announcement.textContent = 'Featured story ' + (current + 1) + ' of ' + slides.length + ': ' + title;
      }
    }

    function stop() {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    function start() {
      stop();
      if (motionQuery.matches || hovered || focused || !visible || document.hidden) return;
      timer = window.setInterval(() => { if (!changing) showSlide(current + 1, false); }, 7000);
    }

    previous.addEventListener('click', () => {
      showSlide(current - 1, true);
      start();
    });

    next.addEventListener('click', () => {
      showSlide(current + 1, true);
      start();
    });

    hero.addEventListener('mouseenter', () => { hovered = true; stop(); });
    hero.addEventListener('mouseleave', () => { hovered = false; start(); });
    hero.addEventListener('focusin', () => { focused = true; stop(); });
    hero.addEventListener('focusout', event => {
      if (!event.relatedTarget || !hero.contains(event.relatedTarget)) {
        focused = false;
        start();
      }
    });

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) stop(); else start();
    });

    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(entries => {
        visible = entries.some(entry => entry.isIntersecting);
        if (visible) start(); else stop();
      }, { threshold: 0.15 });
      observer.observe(hero);
    }

    if (motionQuery.addEventListener) {
      motionQuery.addEventListener('change', start);
    }
    window.addEventListener('pagehide', stop, { once: true });

    showSlide(0, false);
    start();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHeroCarousel, { once: true });
  } else {
    initHeroCarousel();
  }
}());
