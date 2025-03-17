/**
 * Destination Filters Handler
 * Handles filtering functionality for the Explore page destinations
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get all filter elements
    const categoryFilter = document.getElementById('categoryFilter');
    const activityFilter = document.getElementById('activityFilter');
    const dateFilter = document.getElementById('dateFilter');
    const searchInput = document.getElementById('searchInput');
    const resetButton = document.getElementById('resetFilters');
    const destinationsMap = document.getElementById('destinations-map');
    
    // Get destinations container and all destination cards
    const destinationSection = document.getElementById('destinationsSection');
    const searchResultsSection = document.getElementById('searchResultsSection');
    const noResults = document.getElementById('noResults');
    const destinationCards = document.querySelectorAll('.destination-card');
    
    // Store the original map data to restore when filters are reset
    let originalMapData = null;
    if (destinationsMap) {
        try {
            originalMapData = JSON.parse(destinationsMap.dataset.destinations);
        } catch (error) {
            console.error('Error parsing original map data:', error);
        }
    }
    
    // Store current filter state
    const filterState = {
        destination: '',
        activity: '',
        dateRange: '',
        searchQuery: ''
    };
    
    /**
     * Initialize the filter handlers
     */
    function initFilters() {
        // Add event listeners to all filter elements
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
            // We handle search separately to allow for real-time filtering
            searchInput.addEventListener('input', handleSearchInput);
            
            // Check if there's an initial search query in the URL
            const urlParams = new URLSearchParams(window.location.search);
            const initialQuery = urlParams.get('q');
            if (initialQuery) {
                searchInput.value = initialQuery;
                // Trigger the search
                searchInput.dispatchEvent(new Event('input'));
            }
        }
        
        if (resetButton) {
            resetButton.addEventListener('click', resetFilters);
        } else {
            // Create reset button if it doesn't exist
            createResetButton();
        }
        
        // Apply initial filters
        applyFilters();
    }
    
    /**
     * Create a reset button and add it to the filter section
     */
    function createResetButton() {
        const filterSection = document.querySelector('.bg-white.dark\\:bg-gray-800.rounded-lg.shadow-md.p-6.mb-8');
        
        if (filterSection) {
            // Create a container div for the button
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'md:col-span-3 flex justify-center mt-4';
            
            const button = document.createElement('button');
            button.id = 'resetFilters';
            button.className = 'px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors duration-200';
            button.textContent = 'Reset Filters';
            button.addEventListener('click', resetFilters);
            
            // Append button to container
            buttonContainer.appendChild(button);
            
            // Append container to filter section
            filterSection.appendChild(buttonContainer);
        }
    }
    
    /**
     * Handle changes to any filter
     */
    function handleFilterChange(event) {
        // Update filter state based on which filter changed
        if (event.target === categoryFilter) {
            filterState.destination = event.target.value;
        } else if (event.target === activityFilter) {
            filterState.activity = event.target.value;
        } else if (event.target === dateFilter) {
            filterState.dateRange = event.target.value;
        }
        
        // Apply all filters
        applyFilters();
    }
    
    /**
     * Handle search input events
     */
    function handleSearchInput(event) {
        filterState.searchQuery = event.target.value.toLowerCase().trim();
        
        // If search query is empty, show destination section and hide search results
        if (filterState.searchQuery === '') {
            if (destinationSection) destinationSection.classList.remove('hidden');
            if (searchResultsSection) searchResultsSection.classList.add('hidden');
            // Still apply other filters
            applyFilters();
            return;
        }
        
        // If there's a search query, hide destination section and show search results
        if (destinationSection) destinationSection.classList.add('hidden');
        if (searchResultsSection) searchResultsSection.classList.remove('hidden');
        
        // Simple search implementation (fallback if full search not working)
        try {
            const searchResults = document.getElementById('searchResults');
            if (searchResults) {
                searchResults.innerHTML = ''; // Clear previous results
                
                let foundResults = false;
                
                // Filter through destination cards based on search query
                destinationCards.forEach(card => {
                    const title = card.querySelector('h3')?.textContent || '';
                    const content = card.textContent || '';
                    
                    if (title.toLowerCase().includes(filterState.searchQuery) || 
                        content.toLowerCase().includes(filterState.searchQuery)) {
                        // Clone the card and add to search results
                        const clonedCard = card.cloneNode(true);
                        clonedCard.classList.remove('hidden'); // Ensure it's visible
                        searchResults.appendChild(clonedCard);
                        foundResults = true;
                    }
                });
                
                // Show/hide no results message
                if (noResults) {
                    if (!foundResults) {
                        noResults.classList.remove('hidden');
                    } else {
                        noResults.classList.add('hidden');
                    }
                }
            }
        } catch (error) {
            console.error('Error with simplified search:', error);
        }
    }
    
    /**
     * Apply all active filters to destination cards and map
     */
    function applyFilters() {
        let visibleCount = 0;
        
        // Filter destination cards
        destinationCards.forEach(card => {
            const cardData = parseCardData(card);
            const isVisible = shouldShowCard(cardData);
            
            if (isVisible) {
                card.classList.remove('hidden');
                visibleCount++;
            } else {
                card.classList.add('hidden');
            }
        });
        
        // Also apply filters to search results if they're visible
        if (searchResultsSection && !searchResultsSection.classList.contains('hidden')) {
            const searchResultCards = searchResultsSection.querySelectorAll('.destination-card');
            let searchVisibleCount = 0;
            
            searchResultCards.forEach(card => {
                const cardData = parseCardData(card);
                const isVisible = shouldShowCard(cardData);
                
                if (isVisible) {
                    card.classList.remove('hidden');
                    searchVisibleCount++;
                } else {
                    card.classList.add('hidden');
                }
            });
            
            // Show no results message if needed
            if (noResults) {
                if (searchVisibleCount === 0) {
                    noResults.classList.remove('hidden');
                } else {
                    noResults.classList.add('hidden');
                }
            }
        }
        
        // Show no results message if no destinations are visible
        if (noResults && !searchResultsSection.classList.contains('hidden')) {
            if (visibleCount === 0 && !filterState.searchQuery) {
                noResults.classList.remove('hidden');
            } else {
                noResults.classList.add('hidden');
            }
        }
        
        // Update map to show only filtered destinations
        updateMap();
    }
    
    /**
     * Parse data attributes from a destination card
     */
    function parseCardData(card) {
        return {
            destination: card.dataset.destination || '',
            title: card.querySelector('h3')?.textContent.trim() || '',
            activities: card.dataset.activities ? card.dataset.activities.split(',') : [],
            date: card.dataset.date ? new Date(card.dataset.date) : null
        };
    }
    
    /**
     * Determine if a card should be visible based on current filters
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
            const daysAgo = Math.floor((new Date() - cardData.date) / (1000 * 60 * 60 * 24));
            if (daysAgo > parseInt(filterState.dateRange)) {
                return false;
            }
        }
        
        // If we passed all filters, show the card
        return true;
    }
    
    /**
     * Update the map to show only filtered destinations
     */
    function updateMap() {
        if (!destinationsMap || !originalMapData) return;
        
        try {
            // If no filters are active, restore original map data
            if (!filterState.destination && !filterState.activity && !filterState.dateRange) {
                destinationsMap.dataset.destinations = JSON.stringify(originalMapData);
                refreshMap();
                return;
            }
            
            // Filter the map data based on current filters
            const filteredMapData = originalMapData.filter(marker => {
                // Check destination filter
                if (filterState.destination && 
                    marker.title.toLowerCase() !== filterState.destination.toLowerCase()) {
                    return false;
                }
                
                // For activity and date filters, we need to correlate with destination cards
                // Find matching card for this marker
                const matchingCard = findMatchingCard(marker.title);
                if (!matchingCard) return true; // Keep marker if no matching card is found
                
                const cardData = parseCardData(matchingCard);
                
                // Check activity filter
                if (filterState.activity && 
                    (!cardData.activities || !cardData.activities.includes(filterState.activity))) {
                    return false;
                }
                
                // Check date filter
                if (filterState.dateRange && cardData.date) {
                    const daysAgo = Math.floor((new Date() - cardData.date) / (1000 * 60 * 60 * 24));
                    if (daysAgo > parseInt(filterState.dateRange)) {
                        return false;
                    }
                }
                
                return true;
            });
            
            // Update map data attribute
            destinationsMap.dataset.destinations = JSON.stringify(filteredMapData);
            
            // Refresh the map
            refreshMap();
        } catch (error) {
            console.error('Error updating map with filtered data:', error);
        }
    }
    
    /**
     * Find a destination card that matches a map marker title
     */
    function findMatchingCard(markerTitle) {
        return Array.from(destinationCards).find(card => {
            // Try to get title from h3 tag first
            let title = card.querySelector('h3')?.textContent.trim() || '';
            
            // If no title found or it's empty, check data-destination attribute
            if (!title && card.dataset.destination) {
                title = card.dataset.destination;
            }
            
            return title.toLowerCase() === markerTitle.toLowerCase();
        });
    }
    
    /**
     * Refresh the map after updating data
     */
    function refreshMap() {
        // Get the Leaflet map instance
        const mapInstance = L.DomUtil.get('destinations-map')._leaflet_map;
        
        if (mapInstance) {
            // Clear existing markers
            mapInstance.eachLayer(layer => {
                if (layer instanceof L.Marker) {
                    mapInstance.removeLayer(layer);
                }
            });
            
            // Parse the updated destinations data
            let destinationsData = [];
            try {
                destinationsData = JSON.parse(destinationsMap.dataset.destinations);
            } catch (error) {
                console.error('Error parsing destinations data:', error);
                return;
            }
            
            // Add new markers
            const bounds = [];
            destinationsData.forEach(destination => {
                if (destination.lat && destination.lng) {
                    L.marker([destination.lat, destination.lng])
                        .addTo(mapInstance)
                        .bindPopup(`<strong><a href="${destination.url}">${destination.title}</a></strong>
                                    <p>${destination.count} adventures</p>`);
                    
                    bounds.push([destination.lat, destination.lng]);
                }
            });
            
            // Fit map to show all markers
            if (bounds.length > 0) {
                mapInstance.fitBounds(bounds, { padding: [50, 50] });
            }
        }
    }
    
    /**
     * Reset all filters to their default state
     */
    function resetFilters() {
        // Reset filter elements
        if (categoryFilter) categoryFilter.value = '';
        if (activityFilter) activityFilter.value = '';
        if (dateFilter) dateFilter.value = '';
        
        // Reset filter state
        filterState.destination = '';
        filterState.activity = '';
        filterState.dateRange = '';
        
        // Show all destination cards
        destinationCards.forEach(card => {
            card.classList.remove('hidden');
        });
        
        // Hide no results message
        if (noResults) {
            noResults.classList.add('hidden');
        }
        
        // Show destination section if hidden
        if (destinationSection && destinationSection.classList.contains('hidden')) {
            destinationSection.classList.remove('hidden');
        }
        
        // Reset map to original data
        if (destinationsMap && originalMapData) {
            destinationsMap.dataset.destinations = JSON.stringify(originalMapData);
            refreshMap();
        }
    }
    
    // Initialize filters
    initFilters();
});