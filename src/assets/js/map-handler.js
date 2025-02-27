console.log('Map handler loaded');

// Initialize maps when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check for destination map container
    const destinationMapEl = document.getElementById('destination-map');
    if (destinationMapEl) {
      initDestinationMap(destinationMapEl);
    }
    
    // Check for all destinations map
    const destinationsMapEl = document.getElementById('destinations-map');
    if (destinationsMapEl) {
      initDestinationsMap(destinationsMapEl);
    }
  });
  
  // Lazy load map when it's scrolled into view
  function setupLazyMap(mapElement, initFunction) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          initFunction(mapElement);
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '100px' });
    
    observer.observe(mapElement);
  }
  
  // Initialize a single destination map
  function initDestinationMap(container) {
    // Get coordinates from data attributes
    const lat = parseFloat(container.dataset.latitude || 0);
    const lng = parseFloat(container.dataset.longitude || 0);
    const title = container.dataset.title || 'Destination';
    
    if (!lat || !lng) {
      container.innerHTML = '<p class="text-center text-gray-500 py-8">Map coordinates not available</p>';
      return;
    }
    
    // Create map
    const map = L.map(container).setView([lat, lng], 10);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18
    }).addTo(map);
    
    // Add marker
    L.marker([lat, lng])
      .addTo(map)
      .bindPopup(`<strong>${title}</strong>`)
      .openPopup();
      
    // Refresh map after loading (fixes rendering issues)
    setTimeout(() => { map.invalidateSize(); }, 100);
  }
  
  // Initialize map with multiple destinations
  function initDestinationsMap(container) {
    // Create map centered on a default location (world-centered)
    const map = L.map(container).setView([20, 0], 2);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18
    }).addTo(map);
    
    // Get destination markers data from container
    const destinationsData = JSON.parse(container.dataset.destinations || '[]');
    const bounds = [];
    
    // Add markers for each destination
    destinationsData.forEach(destination => {
      if (destination.lat && destination.lng) {
        L.marker([destination.lat, destination.lng])
          .addTo(map)
          .bindPopup(`<strong><a href="${destination.url}">${destination.title}</a></strong>
                      <p>${destination.count} adventures</p>`);
                      
        bounds.push([destination.lat, destination.lng]);
      }
    });
    
    // If we have destinations, fit the map to show all markers
    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [50, 50] });
    }
    
    // Refresh map after loading
    setTimeout(() => { map.invalidateSize(); }, 100);
  }
  
  // Set up lazy loading for maps when the page loads
  document.addEventListener('DOMContentLoaded', function() {
    const destinationMapEl = document.getElementById('destination-map');
    if (destinationMapEl) {
      setupLazyMap(destinationMapEl, initDestinationMap);
    }
    
    const destinationsMapEl = document.getElementById('destinations-map');
    if (destinationsMapEl) {
      setupLazyMap(destinationsMapEl, initDestinationsMap);
    }
  });