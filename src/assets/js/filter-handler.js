/* Travelling Trails destination explorer — filter existing cards in place.
   One search handler owns Explore; journal search is loaded on /search/ only. */
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('searchInput');
    const destinationSelect = document.getElementById('categoryFilter');
    const activitySelect = document.getElementById('activityFilter');
    const dateSelect = document.getElementById('dateFilter');
    const reset = document.getElementById('resetFilters');
    const list = document.getElementById('explorePosts');
    const count = document.getElementById('exploreCount');
    const noResults = document.getElementById('noResults');
    const map = document.getElementById('destinations-map');
    if (!input || !destinationSelect || !activitySelect || !dateSelect || !list) return;
    const cards = Array.from(list.querySelectorAll('.tt-destination-collection-card'));

    function filter() {
      const query = input.value.trim().toLowerCase();
      const destination = destinationSelect.value.trim().toLowerCase();
      const activity = activitySelect.value.trim().toLowerCase();
      const days = Number(dateSelect.value);
      const now = Date.now();
      const visibleTitles = [];

      for (const card of cards) {
        const title = (card.dataset.destination || '').toLowerCase();
        const activities = (card.dataset.activities || '').split(',').map(a => a.trim().toLowerCase()).filter(Boolean);
        const date = card.dataset.date ? new Date(card.dataset.date).getTime() : NaN;
        const queryMatches = !query || title.includes(query) || activities.some(a => a.includes(query));
        const destinationMatches = !destination || title === destination;
        const activityMatches = !activity || activities.includes(activity);
        const dateMatches = !days || (Number.isFinite(date) && date <= now && now - date <= days * 86400000);
        const isVisible = queryMatches && destinationMatches && activityMatches && dateMatches;
        card.classList.toggle('hidden', !isVisible);
        if (isVisible) visibleTitles.push(card.dataset.destination || '');
      }
      if (count) count.textContent = visibleTitles.length + (visibleTitles.length === 1 ? ' destination found' : ' destinations found');
      if (noResults) noResults.classList.toggle('hidden', visibleTitles.length > 0);
      if (map) {
        map.dispatchEvent(new CustomEvent('tt:destinations-filtered', {
          detail: {titles: visibleTitles}
        }));
      }
    }

    let timeout;
    input.addEventListener('input', () => {
      clearTimeout(timeout);
      timeout = setTimeout(filter, 150);
    });
    [destinationSelect, activitySelect, dateSelect].forEach(select => select.addEventListener('change', filter));
    if (reset) reset.addEventListener('click', () => {
      input.value = '';
      destinationSelect.value = '';
      activitySelect.value = '';
      dateSelect.value = '';
      filter();
      input.focus();
    });

    const query = new URLSearchParams(window.location.search).get('q');
    if (query) input.value = query;
    filter();
  });
}());
