document.addEventListener('DOMContentLoaded', function() {
    // Get the base path prefix from the global variable or default to "/travellingtrails1/"
    const basePathPrefix = window.siteBasePathPrefix || "/travellingtrails1/";
    
    // Function to switch logos based on dark mode
    function switchLogos() {
      const isDarkMode = document.documentElement.classList.contains('dark');
      const headerLogo = document.getElementById('header-logo');
      const footerLogo = document.getElementById('footer-logo');
      
      function updateLogoSrc(logoElement) {
        if (!logoElement) return;
        
        if (isDarkMode) {
          // Use the white logo in dark mode
          logoElement.src = basePathPrefix + 'assets/images/logo-white.svg';
          logoElement.onerror = function() {
            this.onerror = null;
            this.src = basePathPrefix + 'assets/images/logo-white.png';
          };
        } else {
          // Use the regular logo in light mode
          logoElement.src = basePathPrefix + 'assets/images/logo.svg';
          logoElement.onerror = function() {
            this.onerror = null;
            this.src = basePathPrefix + 'assets/images/logo.png';
          };
        }
      }
      
      updateLogoSrc(headerLogo);
      updateLogoSrc(footerLogo);
    }
    
    // Run on initial page load
    switchLogos();
    
    // Watch for dark mode changes
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.attributeName === 'class') {
          switchLogos();
        }
      });
    });
    
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });
    
    // Also hook into the theme toggle button
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener('click', function() {
        setTimeout(switchLogos, 50);
      });
    }
  });