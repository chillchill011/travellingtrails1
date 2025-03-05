// Enhanced analytics for blog posts
document.addEventListener('DOMContentLoaded', function() {
    if (typeof gtag !== 'function') return;
    
    // Only run on blog posts
    const isArticlePage = document.querySelector('article.max-w-4xl');
    if (!isArticlePage) return;
    
    // Track scroll depth
    let scrollDepthMarkers = [25, 50, 75, 100];
    let scrollDepthMarked = [];
    
    function calculateScrollPercentage() {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (scrollHeight <= 0) return 100;
      return Math.round((window.scrollY / scrollHeight) * 100);
    }
    
    window.addEventListener('scroll', function() {
      const scrollPercentage = calculateScrollPercentage();
      
      scrollDepthMarkers.forEach(marker => {
        if (scrollPercentage >= marker && !scrollDepthMarked.includes(marker)) {
          scrollDepthMarked.push(marker);
          gtag('event', 'scroll_depth', {
            'event_category': 'engagement',
            'event_label': marker + '%'
          });
        }
      });
    });
    
    // Track time on page
    let timeMarkers = [30, 60, 120, 300]; // seconds
    let timeMarked = [];
    let startTime = new Date();
    
    function checkTimeOnPage() {
      const elapsedSeconds = Math.floor((new Date() - startTime) / 1000);
      
      timeMarkers.forEach(marker => {
        if (elapsedSeconds >= marker && !timeMarked.includes(marker)) {
          timeMarked.push(marker);
          gtag('event', 'time_on_page', {
            'event_category': 'engagement',
            'event_label': marker + 's'
          });
        }
      });
      
      if (timeMarked.length < timeMarkers.length) {
        setTimeout(checkTimeOnPage, 10000); // Check every 10 seconds
      }
    }
    
    setTimeout(checkTimeOnPage, 10000); // Start checking after 10 seconds
  });