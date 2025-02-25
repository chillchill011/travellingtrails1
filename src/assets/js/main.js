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
});

// Check for saved theme preference, otherwise use system preference
if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
} else {
    document.documentElement.classList.remove('dark');
}

const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');
const themeToggleBtn = document.getElementById('theme-toggle');

// Change the icons inside the button based on previous settings
if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    themeToggleLightIcon.classList.remove('hidden');
} else {
    themeToggleDarkIcon.classList.remove('hidden');
}

themeToggleBtn.addEventListener('click', function() {
    // Toggle icons
    themeToggleDarkIcon.classList.toggle('hidden');
    themeToggleLightIcon.classList.toggle('hidden');

    // If is set in localStorage
    if (localStorage.getItem('color-theme')) {
        if (localStorage.getItem('color-theme') === 'light') {
            document.documentElement.classList.add('dark');
            localStorage.setItem('color-theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('color-theme', 'light');
        }
    } else {
        if (document.documentElement.classList.contains('dark')) {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('color-theme', 'light');
        } else {
            document.documentElement.classList.add('dark');
            localStorage.setItem('color-theme', 'dark');
        }
    }
});

themeToggleBtn.addEventListener('click', function() {
    // Add console logs
    console.log('Button clicked');
    console.log('Current theme:', localStorage.getItem('color-theme'));
    console.log('Dark class present:', document.documentElement.classList.contains('dark'));

    // Rest of your code...
    
    // Add another console log after changes
    console.log('New theme:', localStorage.getItem('color-theme'));
    console.log('Dark class after change:', document.documentElement.classList.contains('dark'));
});

// Load More functionality
document.addEventListener('DOMContentLoaded', function() {
    const loadMoreBtns = document.querySelectorAll('.load-more-btn');
    
    loadMoreBtns.forEach(btn => {
        let currentPage = 1;
        btn.addEventListener('click', function() {
            currentPage++;
            const container = this.closest('section').querySelector('.posts-container .grid');
            const postsGrid = container.querySelector('.grid');
            
            // Get all posts that are currently hidden
            const allPosts = Array.from(document.querySelectorAll('.blog-card[data-page="' + currentPage + '"]'));
            
            if (allPosts.length === 0) {
                // No more posts to show
                this.style.display = 'none';
                return;
            }
            
            // Show next set of posts
            allPosts.slice(0, 9).forEach(post => {
                post.classList.remove('hidden');
                container.appendChild(post);
            });
            
            // Hide button if no more posts
            if (allPosts.length <= 9) {
                this.style.display = 'none';
            }
        });
    });
});


// Lightbox
document.addEventListener('DOMContentLoaded', function() {
    const lightbox = document.getElementById('gallery-lightbox');
    const lightboxImage = document.getElementById('lightbox-image');
    const lightboxClose = document.getElementById('lightbox-close');
  
    if (!lightbox || !lightboxImage || !lightboxClose) return;
  
    // Open lightbox
    document.addEventListener('click', function(e) {
      const trigger = e.target.closest('[data-lightbox-trigger]');
      if (trigger) {
        e.preventDefault();
        // Set image source before showing lightbox
        lightboxImage.src = trigger.src;
        lightboxImage.alt = trigger.alt;
        
        // Show lightbox after a brief delay to ensure image is loaded
        requestAnimationFrame(() => {
          lightbox.classList.add('active');
          document.body.style.overflow = 'hidden';
        });
      }
    });
  
    // Close lightbox
    function closeLightbox() {
      lightbox.classList.remove('active');
      document.body.style.overflow = '';
      
      // Don't clear src until transition is complete
      lightbox.addEventListener('transitionend', function handler() {
        lightboxImage.src = '';
        lightbox.removeEventListener('transitionend', handler);
      }, { once: true });
    }
  
    // Close button click
    lightboxClose.addEventListener('click', function(e) {
      e.stopPropagation();
      closeLightbox();
    });
  
    // Background click
    lightbox.addEventListener('click', function(e) {
      if (e.target === lightbox) {
        closeLightbox();
      }
    });
  
    // Escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && lightbox.classList.contains('active')) {
        closeLightbox();
      }
    });
  
    // Prevent 404 errors
    lightboxImage.addEventListener('error', function() {
      this.src = '';
    });
  });

  // Google Analytics Event Tracking
document.addEventListener('DOMContentLoaded', function() {
  // Only run if gtag is defined (analytics is loaded)
  if (typeof gtag === 'function') {
    
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
  }
});