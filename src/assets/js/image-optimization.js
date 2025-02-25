/**
 * Image optimization and lazy loading script
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get all images on the page
    const images = document.querySelectorAll('img:not(.no-optimize)');
    
    // Apply lazy loading and async decoding to all images
    images.forEach(img => {
      // Add lazy loading if not already set
      if (!img.hasAttribute('loading')) {
        img.setAttribute('loading', 'lazy');
      }
      
      // Add async decoding if not already set
      if (!img.hasAttribute('decoding')) {
        img.setAttribute('decoding', 'async');
      }
      
      // Add default error handling
      img.addEventListener('error', function() {
        // Only replace if not already a placeholder
        if (!this.src.includes('placeholder.jpg') && !this.classList.contains('error-handled')) {
          this.src = '/travellingtrails1/assets/images/placeholder.jpg';
          this.alt = this.alt || 'Image not available';
          this.classList.add('error-handled');
        }
      });
      
      // Add srcset for responsive images if available
      if (img.hasAttribute('data-srcset')) {
        img.setAttribute('srcset', img.getAttribute('data-srcset'));
      }
      
      // Add sizes for responsive images if available
      if (img.hasAttribute('data-sizes')) {
        img.setAttribute('sizes', img.getAttribute('data-sizes'));
      }
    });
    
    // Adjust image brightness in dark mode
    function adjustImageBrightness() {
      if (document.documentElement.classList.contains('dark')) {
        document.querySelectorAll('img:not(.no-dark-adjust)').forEach(img => {
          img.style.filter = 'brightness(0.8)';
        });
      } else {
        document.querySelectorAll('img').forEach(img => {
          if (img.style.filter === 'brightness(0.8)') {
            img.style.filter = '';
          }
        });
      }
    }
    
    // Run on page load
    adjustImageBrightness();
    
    // Observe for dark mode changes
    const observer = new MutationObserver(adjustImageBrightness);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });
  });