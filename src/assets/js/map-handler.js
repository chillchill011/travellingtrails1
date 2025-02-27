console.log('Map handler loaded');

// Initialize maps when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check for destination map container
    const destinationMapEl = document.getElementById('destination-map');
    if (destinationMapEl) {
      console.log('Found destination map, initializing...');
      initDestinationMap(destinationMapEl);
    }
    
    // Check for all destinations map
    const destinationsMapEl = document.getElementById('destinations-map');
    if (destinationsMapEl) {
      console.log('Found destinations map, initializing...');
      try {
        initDestinationsMap(destinationsMapEl);
      } catch (error) {
        console.error('Error initializing destinations map:', error);
      }
    }
  });
  
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
    container.classList.remove('loading'); // Remove loading indicator
    
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
    // Get destination markers data from container
    let destinationsData = [];
    
    try {
      console.log('Parsing data:', container.dataset.destinations);
      
      // First try to parse the data with JSON.parse
      try {
        destinationsData = JSON.parse(container.dataset.destinations || '[]');
      } catch (jsonError) {
        console.error('JSON parse error:', jsonError);
        
        // If that fails, try to parse it after fixing common HTML entity issues
        const fixedData = container.dataset.destinations
          .replace(/&quot;/g, '"')
          .replace(/&#34;/g, '"')
          .replace(/&apos;/g, "'")
          .replace(/&#39;/g, "'")
          .replace(/&amp;/g, '&')
          .replace(/&#38;/g, '&');
        
        destinationsData = JSON.parse(fixedData || '[]');
      }
      
      console.log('Parsed destinations data:', destinationsData);
      
      if (!destinationsData || destinationsData.length === 0) {
        console.warn('No destination data found or empty array');
        container.innerHTML = '<p class="text-center text-gray-500 py-8">No destinations with map coordinates found</p>';
        return;
      }
      
      // Create map centered on a default location (world-centered)
      const map = L.map(container).setView([20, 0], 2);
      container.classList.remove('loading'); // Remove loading indicator
      
      // Add OpenStreetMap tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18
      }).addTo(map);
      
      const bounds = [];
      
      // Add markers for each destination
      destinationsData.forEach(destination => {
        if (destination.lat && destination.lng) {
          console.log(`Adding marker for ${destination.title} at ${destination.lat},${destination.lng}`);
          
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
      setTimeout(() => { 
        map.invalidateSize(); 
        console.log('Map invalidated and resized');
      }, 100);
    } catch (error) {
      console.error('Error setting up map:', error);
      container.innerHTML = `<p class="text-center text-gray-500 py-8">Error loading map: ${error.message}</p>`;
    }
  }