document.addEventListener('DOMContentLoaded', function() {
    // Get the absolute base URL from a global variable or construct it
    const baseUrl = window.siteBaseUrl || window.location.origin;
    
    function switchLogos() {
      const isDarkMode = document.documentElement.classList.contains('dark');
      const headerLogo = document.getElementById('header-logo');
      const footerLogo = document.getElementById('footer-logo');
      
      if (headerLogo) {
        headerLogo.src = isDarkMode 
          ? baseUrl + '/assets/images/logo-white.png' 
          : baseUrl + '/assets/images/logo.png';
      }
      
      if (footerLogo) {
        footerLogo.src = isDarkMode 
          ? baseUrl + '/assets/images/logo-white.png' 
          : baseUrl + '/assets/images/logo.png';
      }
    }
    
    // Run once on page load
    switchLogos();
    
    // Watch for dark mode changes
    const logoObserver = new MutationObserver(function() {
      switchLogos();
    });
    
    logoObserver.observe(document.documentElement, {
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