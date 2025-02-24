// src/assets/js/navigation.js
document.addEventListener('DOMContentLoaded', function() {
    const backToTopButton = document.getElementById('back-to-top');
    const progressBar = document.getElementById('progress-bar');
    
    if (!backToTopButton || !progressBar) return;
  
    // Back to Top functionality
    window.addEventListener('scroll', () => {
      // Show button when user scrolls down 200px
      if (window.scrollY > 200) {
        backToTopButton.classList.remove('translate-y-24', 'opacity-0');
        backToTopButton.classList.add('translate-y-0', 'opacity-100');
      } else {
        backToTopButton.classList.add('translate-y-24', 'opacity-0');
        backToTopButton.classList.remove('translate-y-0', 'opacity-100');
      }
      
      // Update progress bar
      const windowHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrolled = (window.scrollY / windowHeight) * 100;
      progressBar.style.width = `${scrolled}%`;
    });
  
    // Smooth scroll to top when button is clicked
    backToTopButton.addEventListener('click', () => {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  
    // Initial progress bar width
    progressBar.style.width = '0%';
  });