// Remove the import since we'll use the global lunr variable
let searchIndex;
let searchData;
let currentFilters = {
    category: '',
    dateRange: ''
};

async function initializeSearch() {
    try {
        console.log('Initializing search...');
        const response = await fetch('/travellingtrails1/search-data.json');
        console.log('Search response:', response);
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

    categoryFilter.addEventListener('change', (e) => {
        currentFilters.category = e.target.value;
        const searchQuery = searchInput.value;
        if (searchQuery.length >= 2) {
            performSearch(searchQuery);
        }
    });

    dateFilter.addEventListener('change', (e) => {
        currentFilters.dateRange = e.target.value;
        const searchQuery = searchInput.value;
        if (searchQuery.length >= 2) {
            performSearch(searchQuery);
        }
    });

    document.addEventListener('click', (e) => {
        if (!searchSuggestions.contains(e.target) && e.target !== searchInput) {
            hideSuggestions();
        }
    });
}

function performSearch(query) {
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
    
    resultsContainer.innerHTML = '';

    if (results.length === 0) {
        noResults.classList.remove('hidden');
        return;
    }

    noResults.classList.add('hidden');

    results.forEach(result => {
        const post = searchData.posts.find(p => p.url === result.ref);
        const article = createResultCard(post);
        resultsContainer.appendChild(article);
    });
}

function createResultCard(post) {
    const article = document.createElement('article');
    article.className = 'bg-white dark:bg-gray-800 rounded-lg shadow-md p-6';
    
    article.innerHTML = `
        <h2 class="text-xl font-semibold mb-2">
            <a href="/travellingtrails1${post.url}" class="text-gray-900 dark:text-white hover:text-travel-700 
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
                <a href="/travellingtrails1/categories/${category.toLowerCase().replace(/\s+/g, '-')}/"
                   class="inline-block px-3 py-1 text-sm bg-travel-100 text-travel-700 
                          dark:bg-travel-900 dark:text-travel-100 rounded-full">
                    ${category}
                </a>
            `).join('')}
        </div>
        ` : ''}
    `;
    
    return article;
}

function showSuggestions(query) {
    const results = searchIndex.search(query).slice(0, 5);
    const suggestionsContainer = document.getElementById('searchSuggestions');
    
    if (results.length === 0) {
        hideSuggestions();
        return;
    }

    suggestionsContainer.innerHTML = '';
    results.forEach(result => {
        const post = searchData.posts.find(p => p.url === result.ref);
        const div = document.createElement('div');
        div.className = 'p-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer';
        div.innerHTML = `
            <div class="font-medium">${post.title}</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">${post.description || ''}</div>
        `;
        div.addEventListener('click', () => {
            window.location.href = `/travellingtrails1${post.url}`;
        });
        suggestionsContainer.appendChild(div);
    });
    
    suggestionsContainer.classList.remove('hidden');
}

function hideSuggestions() {
    document.getElementById('searchSuggestions').classList.add('hidden');
}

function clearResults() {
    document.getElementById('searchResults').innerHTML = '';
    document.getElementById('noResults').classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', initializeSearch);