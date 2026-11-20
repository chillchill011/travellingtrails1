// Travelling Trails — accessible modern navigation
document.addEventListener('DOMContentLoaded', () => {
  const header = document.getElementById('tt-site-header');
  const menuButton = document.querySelector('.mobile-menu-button');
  const mobileMenu = document.querySelector('.mobile-menu');
  const toTop = document.getElementById('back-to-top');

  function syncScrollUI() {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    if (header) header.classList.toggle('is-scrolled', scrollTop > 45);
    if (toTop) {
      toTop.classList.toggle('translate-y-24', scrollTop <= 200);
      toTop.classList.toggle('opacity-0', scrollTop <= 200);
      toTop.classList.toggle('translate-y-0', scrollTop > 200);
      toTop.classList.toggle('opacity-100', scrollTop > 200);
    }

  }

  function setMenu(open) {
    if (!mobileMenu || !menuButton) return;
    mobileMenu.hidden = !open;
    mobileMenu.classList.toggle('open', open);
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Close navigation menu' : 'Open navigation menu');
  }

  if (menuButton && mobileMenu) {
    setMenu(false);
    menuButton.addEventListener('click', () => setMenu(mobileMenu.hidden));
    mobileMenu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenu(false)));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !mobileMenu.hidden) {
        setMenu(false);
        menuButton.focus();
      }
    });
    document.addEventListener('click', event => {
      if (!mobileMenu.hidden && !mobileMenu.contains(event.target) && !menuButton.contains(event.target)) setMenu(false);
    });
    window.addEventListener('resize', () => {
      if (window.innerWidth > 800 && !mobileMenu.hidden) setMenu(false);
    });
  }

  if (toTop) {
    toTop.addEventListener('click', () => {
      window.scrollTo({top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
    });
  }
  window.addEventListener('scroll', syncScrollUI, {passive: true});
  syncScrollUI();
});
