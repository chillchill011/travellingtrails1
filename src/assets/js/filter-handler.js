/**
 * Filter handler for destination filtering functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get filter elements
    var categoryFilter = document.getElementById('categoryFilter');
    var activityFilter = document.getElementById('activityFilter');
    var dateFilter = document.getElementById('dateFilter');
    var searchInput = document.getElementById('searchInput');
    var resetButton = document.getElementById('resetFilters');
    var destinationsMap = document.getElementById('destinations-map');
    
    // Get destination container and cards
    var destinationSection = document.getElementById('destinationsSection');
    var searchResultsSection = document.getElementById('searchResultsSection');
    var noResults = document.getElementById('noResults');
    var destinationCards = document.querySelectorAll('.destination-card');
    
    // Store original map data
    var originalMapData = null;
    if (destinationsMap) {
      try {
        originalMapData = JSON.parse(destinationsMap.dataset.destinations);
      } catch (error) {
        console.error('Error parsing map data:', error);
      }
    }
    
    // Filter state object
    var filterState = {
      destination: '',
      activity: '',
      dateRange: '',
      searchQuery: ''
    };
    
    /**
     * Initialize filters
     */
    function initFilters() {
      console.log('Initializing filters');
      
      // Add event listeners
      if (categoryFilter) {
        categoryFilter.addEventListener('change', handleFilterChange);
      }
      
      if (activityFilter) {
        activityFilter.addEventListener('change', handleFilterChange);
      }
      
      if (dateFilter) {
        dateFilter.addEventListener('change', handleFilterChange);
      }
      
      if (searchInput) {
        console.log('Adding search listener');
        searchInput.addEventListener('input', handleSearchInput);
        
        // Check for URL query parameter
        var urlParams = new URLSearchParams(window.location.search);
        var initialQuery = urlParams.get('q');
        if (initialQuery) {
          searchInput.value = initialQuery;
          // Trigger search
          var inputEvent = new Event('input');
          searchInput.dispatchEvent(inputEvent);
        }
      }
      
      if (resetButton) {
        resetButton.addEventListener('click', resetFilters);
      } else {
        createResetButton();
      }
      
      // Apply initial filters
      applyFilters();
    }
    
    /**
     * Create reset button
     */
    function createResetButton() {
      var filterSection = document.querySelector('.bg-white.dark\\:bg-gray-800.rounded-lg.shadow-md.p-6.mb-8');
      
      if (filterSection) {
        var buttonContainer = document.createElement('div');
        buttonContainer.className = 'md:col-span-3 flex justify-center mt-4';
        
        var button = document.createElement('button');
        button.id = 'resetFilters';
        button.className = 'px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors duration-200';
        button.textContent = 'Reset Filters';
        button.addEventListener('click', resetFilters);
        
        buttonContainer.appendChild(button);
        filterSection.appendChild(buttonContainer);
      }
    }
    
    /**
     * Handle filter changes
     */
    function handleFilterChange(event) {
      if (event.target === categoryFilter) {
        filterState.destination = event.target.value;
      } else if (event.target === activityFilter) {
        filterState.activity = event.target.value;
      } else if (event.target === dateFilter) {
        filterState.dateRange = event.target.value;
      }
      
      applyFilters();
    }
    
    /**
     * Handle search input
     */
    function handleSearchInput(event) {
      console.log('Search input triggered');
      filterState.searchQuery = event.target.value.toLowerCase().trim();
      console.log('Search query:', filterState.searchQuery);
      
      // If empty query, show destinations
      if (filterState.searchQuery === '') {
        console.log('Empty query, showing destinations');
        if (destinationSection) destinationSection.classList.remove('hidden');
        if (searchResultsSection) searchResultsSection.classList.add('hidden');
        applyFilters();
        return;
      }
      
      // Show search results section
      console.log('Showing search results');
      if (destinationSection) destinationSection.classList.add('hidden');
      if (searchResultsSection) searchResultsSection.classList.remove('hidden');
      
      // Simple search
      try {
        var searchResults = document.getElementById('searchResults');
        console.log('Search results container:', searchResults);
        
        if (searchResults) {
          searchResults.innerHTML = '';
          var foundResults = false;
          
          // Find all content
          var allContent = document.querySelectorAll('.blog-card, .destination-card, article, [class*="card"], .post');
          console.log('Content items:', allContent.length);
          
          for (var i = 0; i < allContent.length; i++) {
            var item = allContent[i];
            
            // Skip if already in results
            if (item.closest('#searchResults')) {
              console.log('Item already in results, skipping');
              continue;
            }
            
            var content = item.textContent || '';
            
            // Check if content matches search
            if (content.toLowerCase().indexOf(filterState.searchQuery) !== -1) {
              console.log('Match found, creating card');
              foundResults = true;
              
              // Create card
              var card = document.createElement('div');
              card.className = 'bg-white dark:bg-gray-800 rounded-lg shadow-md p-6';
              
              // Get title
              var title = '';
              var titleElem = item.querySelector('h1, h2, h3, a');
              if (titleElem) {
                title = titleElem.textContent.trim();
                console.log('Title found:', title);
              } else {
                title = content.substring(0, 50) + '...';
                console.log('Using content excerpt as title');
              }
              
              // Get URL
              var url = '#';
              var linkElem = item.querySelector('a');
              if (linkElem && linkElem.href) {
                url = linkElem.href;
                console.log('URL found:', url);
              }
              
              // Create title element
              var titleEl = document.createElement('h3');
              titleEl.className = 'text-xl font-semibold text-gray-900 dark:text-white mb-4';
              
              var titleLink = document.createElement('a');
              titleLink.href = url;
              titleLink.textContent = title;
              titleLink.className = 'hover:text-travel-700 dark:hover:text-travel-500';
              
              titleEl.appendChild(titleLink);
              card.appendChild(titleEl);
              
              // Create footer
              var footer = document.createElement('div');
              footer.className = 'flex justify-between text-sm text-gray-600 dark:text-gray-400';
              
              // Get author
              var author = '';
              var authorElem = item.querySelector('a[href^="/authors/"]');
              if (authorElem) {
                author = authorElem.textContent.trim();
                console.log('Author found:', author);
              }
              
              // Get date
              var date = '';
              var dateElem = item.querySelector('time') || item.querySelector('.text-gray-500');
              if (dateElem) {
                date = dateElem.textContent.trim();
                console.log('Date found:', date);
              }
              
              // Add author to footer
              if (author) {
                var authorEl = document.createElement('span');
                authorEl.textContent = 'By ' + author;
                footer.appendChild(authorEl);
              }
              
              // Add date to footer
              if (date) {
                var dateEl = document.createElement('span');
                dateEl.textContent = date;
                footer.appendChild(dateEl);
              }
              
              // Add footer if it has content
              if (author || date) {
                card.appendChild(footer);
              }
              
              // Add card to results
              searchResults.appendChild(card);
              console.log('Card added to results');
            }
          }
          
          // Show/hide no results message
          if (noResults) {
            if (!foundResults) {
              noResults.classList.remove('hidden');
              console.log('No results found');
            } else {
              noResults.classList.add('hidden');
              console.log('Results found');
            }
          }
        }
      } catch (error) {
        console.error('Error in search:', error);
      }
    }
    
    /**
     * Apply filters to cards and map
     */
    function applyFilters() {
      var visibleCount = 0;
      
      // Filter destination cards
      for (var i = 0; i < destinationCards.length; i++) {
        var card = destinationCards[i];
        var cardData = parseCardData(card);
        var isVisible = shouldShowCard(cardData);
        
        if (isVisible) {
          card.classList.remove('hidden');
          visibleCount++;
        } else {
          card.classList.add('hidden');
        }
      }
      
      // Handle search results if visible
      if (searchResultsSection && !searchResultsSection.classList.contains('hidden')) {
        var searchResultCards = searchResultsSection.querySelectorAll('.destination-card');
        var searchVisibleCount = 0;
        
        for (var j = 0; j < searchResultCards.length; j++) {
          var searchCard = searchResultCards[j];
          var searchCardData = parseCardData(searchCard);
          var isSearchVisible = shouldShowCard(searchCardData);
          
          if (isSearchVisible) {
            searchCard.classList.remove('hidden');
            searchVisibleCount++;
          } else {
            searchCard.classList.add('hidden');
          }
        }
        
        // Show no results message if needed
        if (noResults) {
          if (searchVisibleCount === 0) {
            noResults.classList.remove('hidden');
          } else {
            noResults.classList.add('hidden');
          }
        }
      }
      
      // Update map
      updateMap();
    }
    
    /**
     * Parse data from card
     */
    function parseCardData(card) {
      return {
        destination: card.dataset.destination || '',
        title: card.querySelector('h3') ? card.querySelector('h3').textContent.trim() : '',
        activities: card.dataset.activities ? card.dataset.activities.split(',') : [],
        date: card.dataset.date ? new Date(card.dataset.date) : null
      };
    }
    
    /**
     * Check if card should be visible
     */
    function shouldShowCard(cardData) {
      // Check destination filter
      if (filterState.destination && 
          cardData.destination.toLowerCase() !== filterState.destination.toLowerCase() && 
          cardData.title.toLowerCase() !== filterState.destination.toLowerCase()) {
        return false;
      }
      
      // Check activity filter
      if (filterState.activity && 
          (!cardData.activities || !cardData.activities.includes(filterState.activity))) {
        return false;
      }
      
      // Check date filter
      if (filterState.dateRange && cardData.date) {
        var daysAgo = Math.floor((new Date() - cardData.date) / (1000 * 60 * 60 * 24));
        if (daysAgo > parseInt(filterState.dateRange)) {
          return false;
        }
      }
      
      // Passed all filters
      return true;
    }
    
    /**
     * Update map with filtered data
     */
    function updateMap() {
      if (!destinationsMap || !originalMapData) return;
      
      try {
        // If no filters active, restore original map
        if (!filterState.destination && !filterState.activity && !filterState.dateRange) {
          destinationsMap.dataset.destinations = JSON.stringify(originalMapData);
          refreshMap();
          return;
        }
        
        // Filter map data
        var filteredMapData = [];
        for (var i = 0; i < originalMapData.length; i++) {
          var marker = originalMapData[i];
          
          // Check destination filter
          if (filterState.destination && 
              marker.title.toLowerCase() !== filterState.destination.toLowerCase()) {
            continue;
          }
          
          // Find matching card for activity/date filters
          var matchingCard = findMatchingCard(marker.title);
          if (!matchingCard) {
            filteredMapData.push(marker); // Keep marker if no matching card (can't filter it)
            continue;
          }
          
          var cardData = parseCardData(matchingCard);
          
          // Check activity filter
          if (filterState.activity && 
              (!cardData.activities || !cardData.activities.includes(filterState.activity))) {
            continue;
          }
          
          // Check date filter
          if (filterState.dateRange && cardData.date) {
            var daysAgo = Math.floor((new Date() - cardData.date) / (1000 * 60 * 60 * 24));
            if (daysAgo > parseInt(filterState.dateRange)) {
              continue;
            }
          }
          
          // Passed all filters
          filteredMapData.push(marker);
        }
        
        // Update map data
        destinationsMap.dataset.destinations = JSON.stringify(filteredMapData);
        
        // Refresh map
        refreshMap();
      } catch (error) {
        console.error('Error updating map:', error);
      }
    }
    
    /**
     * Find card matching marker title
     */
    function findMatchingCard(markerTitle) {
      for (var i = 0; i < destinationCards.length; i++) {
        var card = destinationCards[i];
        var title = '';
        
        var titleElem = card.querySelector('h3');
        if (titleElem) {
          title = titleElem.textContent.trim();
        }
        
        if (!title && card.dataset.destination) {
          title = card.dataset.destination;
        }
        
        if (title.toLowerCase() === markerTitle.toLowerCase()) {
          return card;
        }
      }
      return null;
    }
    
    /**
     * Refresh map after data update
     */
    function refreshMap() {
      var mapInstance = null;
      try {
        mapInstance = L.DomUtil.get('destinations-map')._leaflet_map;
      } catch (error) {
        console.error('Error getting map instance:', error);
        return;
      }
      
      if (mapInstance) {
        // Clear existing markers
        mapInstance.eachLayer(function(layer) {
          if (layer instanceof L.Marker) {
            mapInstance.removeLayer(layer);
          }
        });
        
        // Parse destinations data
        var destinationsData = [];
        try {
          destinationsData = JSON.parse(destinationsMap.dataset.destinations);
        } catch (error) {
          console.error('Error parsing destinations data:', error);
          return;
        }
        
        // Add new markers
        var bounds = [];
        for (var i = 0; i < destinationsData.length; i++) {
          var destination = destinationsData[i];
          if (destination.lat && destination.lng) {
            L.marker([destination.lat, destination.lng])
              .addTo(mapInstance)
              .bindPopup('<strong><a href="' + destination.url + '">' + destination.title + '</a></strong>' +
                       '<p>' + destination.count + ' adventures</p>');
            
            bounds.push([destination.lat, destination.lng]);
          }
        }
        
        // Fit map to show all markers
        if (bounds.length > 0) {
          mapInstance.fitBounds(bounds, { padding: [50, 50] });
        }
      }
    }
    
    /**
     * Reset all filters
     */
    function resetFilters() {
      // Reset filter elements
      if (categoryFilter) categoryFilter.value = '';
      if (activityFilter) activityFilter.value = '';
      if (dateFilter) dateFilter.value = '';
      if (searchInput) searchInput.value = '';
      
      // Reset filter state
      filterState.destination = '';
      filterState.activity = '';
      filterState.dateRange = '';
      filterState.searchQuery = '';
      
      // Show all cards
      for (var i = 0; i < destinationCards.length; i++) {
        destinationCards[i].classList.remove('hidden');
      }
      
      // Clear search results
      var searchResults = document.getElementById('searchResults');
      if (searchResults) {
        searchResults.innerHTML = '';
      }
      
      if (searchResultsSection) {
        searchResultsSection.classList.add('hidden');
      }
      
      // Show destination section
      if (destinationSection) {
        destinationSection.classList.remove('hidden');
      }
      
      // Hide no results message
      if (noResults) {
        noResults.classList.add('hidden');
      }
      
      // Reset map
      if (destinationsMap && originalMapData) {
        destinationsMap.dataset.destinations = JSON.stringify(originalMapData);
        refreshMap();
      }
    }
    
    // Initialize filters on page load
    initFilters();
  });