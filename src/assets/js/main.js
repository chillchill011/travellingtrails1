// This script adds dark mode detection immediately
// Note: This part is now moved to head in base.njk for preventing flash
// Here for reference, but it will execute too late if kept only in main.js
(function() {
  // Check for saved theme preference
  if (localStorage.getItem('color-theme') === 'dark' || 
      (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
})();

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
  // Get the mobile menu button and menu elements
  const mobileMenuButton = document.querySelector('.mobile-menu-button');
  const mobileMenu = document.querySelector('.mobile-menu');

  // Add click event listener to mobile menu button
  if (mobileMenuButton && mobileMenu) {
    mobileMenuButton.addEventListener('click', function() {
      // Toggle the 'hidden' class on the mobile menu
      mobileMenu.classList.toggle('hidden');
    });
  }
  
  // Setup theme toggle button after DOM is loaded
  setupThemeToggle();
  
  // Setup logo toggle based on dark mode
  toggleLogoDarkMode();
  
  // Setup load more functionality
  setupLoadMore();
  
  // Setup analytics tracking
  setupAnalyticsTracking();
});

// Function to setup theme toggle
function setupThemeToggle() {
  const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
  const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');
  const themeToggleBtn = document.getElementById('theme-toggle');
  
  if (!themeToggleDarkIcon || !themeToggleLightIcon || !themeToggleBtn) return;
  
  // Set initial icon state based on current theme
  if (document.documentElement.classList.contains('dark')) {
    themeToggleDarkIcon.classList.add('hidden');
    themeToggleLightIcon.classList.remove('hidden');
  } else {
    themeToggleDarkIcon.classList.remove('hidden');
    themeToggleLightIcon.classList.add('hidden');
  }
  
  // Add click handler for the theme toggle
  themeToggleBtn.addEventListener('click', function() {
    // Toggle icons
    themeToggleDarkIcon.classList.toggle('hidden');
    themeToggleLightIcon.classList.toggle('hidden');
    
    // If is set in localStorage
    if (localStorage.getItem('color-theme')) {
      if (localStorage.getItem('color-theme') === 'light') {
        document.documentElement.classList.add('dark');
        localStorage.setItem('color-theme', 'dark');
        // Track dark mode toggle in analytics
        if (typeof gtag === 'function') {
          gtag('event', 'dark_mode_toggle', {
            'user_dark_mode': 'dark'
          });
        }
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('color-theme', 'light');
        // Track light mode toggle in analytics
        if (typeof gtag === 'function') {
          gtag('event', 'dark_mode_toggle', {
            'user_dark_mode': 'light'
          });
        }
      }
    } else {
      if (document.documentElement.classList.contains('dark')) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('color-theme', 'light');
        // Track light mode toggle in analytics
        if (typeof gtag === 'function') {
          gtag('event', 'dark_mode_toggle', {
            'user_dark_mode': 'light'
          });
        }
      } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('color-theme', 'dark');
        // Track dark mode toggle in analytics
        if (typeof gtag === 'function') {
          gtag('event', 'dark_mode_toggle', {
            'user_dark_mode': 'dark'
          });
        }
      }
    }
  });
}

// Function to toggle logo based on dark mode
function toggleLogoDarkMode() {
  const isDark = document.documentElement.classList.contains('dark');
  const logos = document.querySelectorAll('.logo-switchable');
  
  logos.forEach(logo => {
    if (isDark) {
      logo.src = "/assets/images/logo-white.svg";
      logo.onerror = function() { 
        this.onerror = null; 
        this.src = "/assets/images/logo-white.png";
      };
    } else {
      logo.src = "/assets/images/logo.svg";
      logo.onerror = function() { 
        this.onerror = null; 
        this.src = "/assets/images/logo.png";
      };
    }
  });
}

// Function to setup load more functionality
function setupLoadMore() {
  document.querySelectorAll('.load-more-btn').forEach(btn => {
    const section = btn.closest('section');
    const container = section && section.querySelector('.posts-container');
    if (!container) return;
    const cards = Array.from(container.querySelectorAll('.tt-pagination-item[data-page]'));
    if (!cards.length) return;
    let page = 1;
    btn.addEventListener('click', () => {
      page++;
      const nextCards = cards.filter(card => Number(card.dataset.page) === page);
      nextCards.forEach(card => card.classList.remove('hidden'));
      btn.dataset.currentPage = String(page);
      if (!cards.some(card => Number(card.dataset.page) > page)) btn.hidden = true;
      if (typeof gtag === 'function') {
        gtag('event', 'load_more_posts', {event_category: 'engagement', event_label: 'Page ' + page});
      }
    });
  });
}

// Function to setup analytics tracking
function setupAnalyticsTracking() {
  // Only run if gtag is defined (analytics is loaded)
  if (typeof gtag !== 'function') return;
  
  // Track outbound link clicks
  document.querySelectorAll('a[href^="http"]:not([href*="' + window.location.host + '"])').forEach(link => {
    link.addEventListener('click', function(e) {
      gtag('event', 'click', {
        'event_category': 'outbound',
        'event_label': this.href,
        'transport_type': 'beacon'
      });
    });
  });
  
  // Track category clicks
  document.querySelectorAll('a[href^="/categories/"]').forEach(link => {
    link.addEventListener('click', function() {
      const category = this.textContent.trim();
      gtag('event', 'category_click', {
        'event_category': 'engagement',
        'event_label': category
      });
    });
  });
  
  // Track search usage
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    let searchTimeout;
    searchInput.addEventListener('input', function() {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        if (this.value.length > 2) {
          gtag('event', 'search', {
            'search_term': this.value
          });
        }
      }, 1000);
    });
  }

  // Track dark mode usage
  gtag('event', 'page_view', {
    'user_dark_mode': document.documentElement.classList.contains('dark') ? 'dark' : 'light'
  });
  
  // Track post categories on article pages
  const articleCategories = document.querySelectorAll('article .category-tag');
  if (articleCategories.length > 0) {
    const categories = Array.from(articleCategories).map(tag => tag.textContent.trim()).join(',');
    gtag('event', 'page_view', {
      'post_category': categories
    });
  }

  // Track newsletter signups
  const newsletterForms = document.querySelectorAll('form');
  newsletterForms.forEach(form => {
    const emailInput = form.querySelector('input[type="email"]');
    const submitButton = form.querySelector('button[type="submit"]');
    
    if (emailInput && submitButton && submitButton.textContent.includes('Subscribe')) {
      form.addEventListener('submit', function(e) {
        gtag('event', 'newsletter_signup', {
          'event_category': 'conversion'
        });
      });
    }
  });

  // Track scroll depth on article pages
  const articleContent = document.querySelector('article.max-w-4xl');
  if (articleContent) {
    let scrollMarkers = [25, 50, 75, 100];
    let scrollMarkersHit = [];
    
    window.addEventListener('scroll', function() {
      const scrollPercent = Math.round((window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100);
      
      scrollMarkers.forEach(marker => {
        if (scrollPercent >= marker && !scrollMarkersHit.includes(marker)) {
          scrollMarkersHit.push(marker);
          gtag('event', 'scroll_depth', {
            'event_category': 'engagement',
            'event_label': `${marker}%`,
            'non_interaction': true
          });
        }
      });
    });
  }
}

// Watch for changes to dark mode
const observer = new MutationObserver(mutations => {
  mutations.forEach(mutation => {
    if (mutation.attributeName === 'class') {
      toggleLogoDarkMode();
    }
  });
});

observer.observe(document.documentElement, {
  attributes: true,
  attributeFilter: ['class']
});