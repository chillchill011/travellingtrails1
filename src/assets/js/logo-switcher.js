document.addEventListener('DOMContentLoaded', function() {
    // In production, this will be empty string
    const basePathPrefix = window.siteBasePathPrefix || '';
    
    function switchLogos() {
      const isDarkMode = document.documentElement.classList.contains('dark');
      const headerLogo = document.getElementById('header-logo');
      const footerLogo = document.getElementById('footer-logo');
      
      if (headerLogo) {
        headerLogo.src = isDarkMode 
          ? basePathPrefix + 'assets/images/logo-white.png' 
          : basePathPrefix + 'assets/images/logo.png';
      }
      
      if (footerLogo) {
        footerLogo.src = isDarkMode 
          ? basePathPrefix + 'assets/images/logo-white.png' 
          : basePathPrefix + 'assets/images/logo.png';
      }
    }
    
    // Run on initial page load
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