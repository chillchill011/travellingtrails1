// src/assets/js/lightbox.js
document.addEventListener('DOMContentLoaded', function() {
    // Create lightbox if it doesn't exist
    if (!document.getElementById('global-lightbox')) {
      const lightboxHTML = `
        <div class="lightbox" id="global-lightbox">
          <button class="lightbox-close" id="lightbox-close" aria-label="Close">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <div class="lightbox-content">
            <img class="lightbox-image" id="lightbox-image" alt="" />
          </div>
        </div>
      `;
      document.body.insertAdjacentHTML('beforeend', lightboxHTML);
    }
  
    const lightbox = document.getElementById('global-lightbox');
    const lightboxImage = document.getElementById('lightbox-image');
    const lightboxClose = document.getElementById('lightbox-close');
  
    if (!lightbox || !lightboxImage || !lightboxClose) return;
  
    // Track current image
    let currentImageSrc = '';
  
    // Open lightbox
    document.addEventListener('click', function(e) {
      const trigger = e.target.closest('[data-lightbox-trigger]');
      if (trigger) {
        e.preventDefault();
        currentImageSrc = trigger.src;
        lightboxImage.src = currentImageSrc;
        lightboxImage.alt = trigger.alt;
        lightbox.classList.add('active');
        document.body.style.overflow = 'hidden';
      }
    });
  
    // Close lightbox
    function closeLightbox() {
      if (!lightbox.classList.contains('active')) return;
      lightbox.classList.remove('active');
      document.body.style.overflow = '';
    }
  
    // Close button click
    lightboxClose.addEventListener('click', closeLightbox);
  
    // Background click
    lightbox.addEventListener('click', function(e) {
      if (e.target === lightbox) {
        closeLightbox();
      }
    });
  
    // Escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        closeLightbox();
      }
    });
  
    // Handle image errors
    lightboxImage.addEventListener('error', function() {
      this.src = '/assets/images/placeholder.jpg';
      this.alt = 'Image not available';
      // Prevent infinite error loop
      this.onerror = null;
    });
  });