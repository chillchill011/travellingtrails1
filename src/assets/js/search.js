// Remove the import since we'll use the global lunr variable
let searchIndex;
let searchData;
let currentFilters = {
    category: '',
    dateRange: ''
};

// Get the path prefix based on environment
const pathPrefix = '';  // Empty for production

console.log('Search script loaded');

async function initializeSearch() {
    // Check if we're on a page that has search functionality
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) {
        console.log('Search input not found, skipping search initialization');
        return; // Exit if search input doesn't exist on this page
    }
    
    try {
        console.log('Initializing search...');
        const response = await fetch('/search-data.json');
        console.log('Search response:', response);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch search data: ${response.status} ${response.statusText}`);
        }
        
        searchData = await response.json();
        console.log('Search data loaded:', searchData);

        // Create Lunr index
        searchIndex = lunr(function() {
            this.field('title', { boost: 10 });
            this.field('content');
            this.field('description', { boost: 5 });
            this.field('categories', { boost: 5 });
            this.ref('url');

            searchData.posts.forEach(post => {
                console.log('Indexing post:', post.title);
                this.add({
                    title: post.title || '',
                    content: post.content || '',
                    description: post.description || '',
                    categories: post.categories ? post.categories.join(' ') : '',
                    url: post.url
                });
            });
        });
        console.log('Search index created');

        setupEventListeners();
    } catch (error) {
        console.error('Error initializing search:', error);
    }
}

function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    const categoryFilter = document.getElementById('categoryFilter');
    const dateFilter = document.getElementById('dateFilter');
    const searchSuggestions = document.getElementById('searchSuggestions');

    if (!searchInput || !searchSuggestions) {
        console.error('Required search elements not found');
        return;
    }

    let debounceTimeout;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            const query = e.target.value;
            if (query.length >= 2) {
                performSearch(query);
                showSuggestions(query);
            } else {
                clearResults();
                hideSuggestions();
            }
        }, 300);
    });

    if (categoryFilter) {
        categoryFilter.addEventListener('change', (e) => {
            currentFilters.category = e.target.value;
            const searchQuery = searchInput.value;
            if (searchQuery.length >= 2) {
                performSearch(searchQuery);
            }
        });
    }

    if (dateFilter) {
        dateFilter.addEventListener('change', (e) => {
            currentFilters.dateRange = e.target.value;
            const searchQuery = searchInput.value;
            if (searchQuery.length >= 2) {
                performSearch(searchQuery);
            }
        });
    }

    document.addEventListener('click', (e) => {
        if (searchSuggestions && !searchSuggestions.contains(e.target) && e.target !== searchInput) {
            hideSuggestions();
        }
    });
}

function performSearch(query) {
    if (!searchIndex) {
        console.error('Search index not initialized');
        return;
    }
    
    const resultsContainer = document.getElementById('searchResults');
    const noResults = document.getElementById('noResults');
    
    if (!resultsContainer || !noResults) {
        console.error('Search results containers not found');
        return;
    }
    
    try {
        console.log('Performing search for:', query);
        const results = searchIndex.search(query);
        console.log('Search results:', results);
        const filteredResults = filterResults(results);
        console.log('Filtered results:', filteredResults);
        displayResults(filteredResults);
    } catch (error) {
        console.error('Error performing search:', error);
    }
}

function filterResults(results) {
    return results.filter(result => {
        const post = searchData.posts.find(p => p.url === result.ref);
        if (!post) return false;
        
        if (currentFilters.category && (!post.categories || 
            !post.categories.includes(currentFilters.category))) {
            return false;
        }

        if (currentFilters.dateRange) {
            const postDate = new Date(post.date);
            const daysAgo = (new Date() - postDate) / (1000 * 60 * 60 * 24);
            if (daysAgo > parseInt(currentFilters.dateRange)) {
                return false;
            }
        }

        return true;
    });
}

function displayResults(results) {
    const resultsContainer = document.getElementById('searchResults');
    const noResults = document.getElementById('noResults');
    
    if (!resultsContainer || !noResults) return;
    
    resultsContainer.innerHTML = '';

    if (results.length === 0) {
        noResults.classList.remove('hidden');
        return;
    }

    noResults.classList.add('hidden');

    results.forEach(result => {
        const post = searchData.posts.find(p => p.url === result.ref);
        if (post) {
            const article = createResultCard(post);
            resultsContainer.appendChild(article);
        }
    });
}

function createResultCard(post) {
    const article = document.createElement('article');
    article.className = 'bg-white dark:bg-gray-800 rounded-lg shadow-md p-6';
    
    // Determine the image source - use thumbnail if available, otherwise featured image
    const imageUrl = post.thumbnailImage || post.featuredImage;
    
    // Fix the URL construction - don't add pathPrefix as we're in production
    let cardHTML = '';
    
    // Add image section if an image is available
    if (imageUrl) {
        cardHTML += `
        <div class="relative h-48 mb-4">
            <img 
                src="${imageUrl}" 
                alt="${post.title}" 
                class="w-full h-full object-cover rounded-lg"
                loading="lazy"
                onerror="if (!this.src.includes('placeholder.jpg')) { this.src = '/assets/images/placeholder.jpg'; this.alt = 'Image not available'; this.onerror = null; }"
            >
        </div>`;
    }
    
    // Add the rest of the card content
    cardHTML += `
        <h2 class="text-xl font-semibold mb-2">
            <a href="${post.url}" class="text-gray-900 dark:text-white hover:text-travel-700 
                                       dark:hover:text-travel-500">
                ${post.title}
            </a>
        </h2>
        <p class="text-gray-600 dark:text-gray-300 mb-4">${post.description || ''}</p>
        <div class="flex items-center justify-between">
            <span class="text-sm text-gray-600 dark:text-gray-400">
                By ${post.author || 'Anonymous'}
            </span>
            <time class="text-sm text-gray-500 dark:text-gray-400">
                ${new Date(post.date).toLocaleDateString()}
            </time>
        </div>
        ${post.categories ? `
        <div class="mt-4 flex flex-wrap gap-2">
            ${post.categories.map(category => `
                <a href="/categories/${category.toLowerCase().replace(/\s+/g, '-')}/"
                   class="inline-block px-3 py-1 text-sm bg-travel-100 text-travel-700 
                          dark:bg-travel-900 dark:text-travel-100 rounded-full">
                    ${category}
                </a>
            `).join('')}
        </div>
        ` : ''}
    `;
    
    article.innerHTML = cardHTML;
    return article;
}

function showSuggestions(query) {
    if (!searchIndex) return;
    
    const suggestionsContainer = document.getElementById('searchSuggestions');
    if (!suggestionsContainer) return;
    
    const results = searchIndex.search(query).slice(0, 5);
    
    if (results.length === 0) {
        hideSuggestions();
        return;
    }

    suggestionsContainer.innerHTML = '';
    results.forEach(result => {
        const post = searchData.posts.find(p => p.url === result.ref);
        if (!post) return;
        
        const div = document.createElement('div');
        div.className = 'p-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer';
        
        // Use thumbnail if available, otherwise use featured image
        const imageUrl = post.thumbnailImage || post.featuredImage;
        
        let suggestionHTML = '';
        if (imageUrl) {
            suggestionHTML += `
            <div class="flex items-center">
                <div class="flex-shrink-0 w-12 h-12 mr-3">
                    <img src="${imageUrl}" alt="${post.title}" class="w-full h-full object-cover rounded-sm">
                </div>
            `;
        }
        
        suggestionHTML += `
            <div>
                <div class="font-medium">${post.title}</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">${post.description || ''}</div>
            </div>
        `;
        
        if (imageUrl) {
            suggestionHTML += `</div>`;
        }
        
        div.innerHTML = suggestionHTML;
        
        div.addEventListener('click', () => {
            window.location.href = post.url;
        });
        suggestionsContainer.appendChild(div);
    });
    
    suggestionsContainer.classList.remove('hidden');
}

function hideSuggestions() {
    const suggestionsContainer = document.getElementById('searchSuggestions');
    if (suggestionsContainer) {
        suggestionsContainer.classList.add('hidden');
    }
}

function clearResults() {
    const resultsContainer = document.getElementById('searchResults');
    const noResults = document.getElementById('noResults');
    
    if (resultsContainer) {
        resultsContainer.innerHTML = '';
    }
    
    if (noResults) {
        noResults.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', initializeSearch);