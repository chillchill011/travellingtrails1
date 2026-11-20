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

    function showSlide(index, announce) {
      current = (index + slides.length) % slides.length;
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
      timer = window.setInterval(() => showSlide(current + 1, false), 7000);
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
