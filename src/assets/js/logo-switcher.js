document.addEventListener('DOMContentLoaded', function() {
    function switchLogos() {
      const isDarkMode = document.documentElement.classList.contains('dark');
      const headerLogo = document.getElementById('header-logo');
      const footerLogo = document.getElementById('footer-logo');
      
      if (headerLogo) {
        headerLogo.src = isDarkMode 
          ? '/travellingtrails1/assets/images/logo-white.png' 
          : '/travellingtrails1/assets/images/logo.png';
      }
      
      if (footerLogo) {
        footerLogo.src = isDarkMode 
          ? '/travellingtrails1/assets/images/logo-white.png' 
          : '/travellingtrails1/assets/images/logo.png';
      }
    }
    
    // Run on initial page load
    switchLogos();
    
    // Watch for dark mode changes
    const observer = new MutationObserver(function() {
      switchLogos();
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