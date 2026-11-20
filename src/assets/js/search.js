/* Travelling Trails — journal search, one UI owner per page.
   Categories are normalized as complete names (never per-character tags). */
(function () {
  'use strict';
  const input = document.getElementById('searchInput');
  const resultsEl = document.getElementById('searchResults');
  const categoryEl = document.getElementById('categoryFilter');
  const dateEl = document.getElementById('dateFilter');
  const clearBtn = document.getElementById('clearSearch');
  const countEl = document.getElementById('searchStatus');
  const headingEl = document.getElementById('searchResultsHeading');
  const emptyEl = document.getElementById('noResults');
  const liveEl = document.getElementById('searchLive');
  const quickEl = document.getElementById('searchQuickResults');
  const quickTitle = document.getElementById('searchQuickTitle');
  const jumpBtn = document.getElementById('jumpToResults');
  const allResults = document.getElementById('allSearchResults');
  if (!input || !resultsEl || !categoryEl || !dateEl || !countEl) return;
  let posts = [];
  let index = null;
  let debounceId;

  function categories(post) {
    const raw = post.categories;
    if (Array.isArray(raw)) return raw.filter(x => typeof x === 'string' && x.trim()).map(x => x.trim());
    return typeof raw === 'string' && raw.trim() ? [raw.trim()] : [];
  }

  function element(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined && text !== null) el.textContent = String(text);
    return el;
  }

  function createCard(post) {
    const card = element('article', 'tt-search-card');
    const imgSrc = post.thumbnailImage || post.featuredImage;
    if (imgSrc) {
      const imageLink = element('a', 'tt-search-card-photo');
      imageLink.href = post.url;
      imageLink.setAttribute('aria-label', 'Read ' + (post.title || 'travel story'));
      const img = element('img');
      img.src = imgSrc;
      img.alt = post.title || 'Travel photograph';
      img.loading = 'lazy';
      img.decoding = 'async';
      imageLink.appendChild(img);
      card.appendChild(imageLink);
    }
    const body = element('div', 'tt-search-card-body');
    const cats = categories(post);
    if (cats.length) {
      const category = element('span', 'tt-search-category', cats[0]);
      body.appendChild(category);
    }
    const title = element('h3');
    const titleLink = element('a', '', post.title || 'Travel story');
    titleLink.href = post.url;
    title.appendChild(titleLink);
    body.appendChild(title);
    if (post.description) body.appendChild(element('p', 'tt-search-card-description', post.description));
    const footer = element('div', 'tt-search-card-meta');
    if (post.author) footer.appendChild(element('span', '', 'By ' + post.author));
    if (post.date) {
      const date = new Date(post.date);
      if (!Number.isNaN(date.getTime())) {
        const time = element('time', '', date.toLocaleDateString('en-IN', {day:'numeric', month:'short', year:'numeric'}));
        time.dateTime = date.toISOString().slice(0, 10);
        footer.appendChild(time);
      }
    }
    if (footer.children.length) body.appendChild(footer);
    const more = element('a', 'tt-search-read', 'Read the story');
    more.href = post.url;
    const icon = element('span', 'tt-search-read-icon');
    icon.innerHTML = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 19 19 5M7 5h12v12"/></svg>';
    more.appendChild(icon);
    body.appendChild(more);
    card.appendChild(body);
    return card;
  }

  function createQuickResult(post) {
    const link = element('a', 'tt-search-quick-card');
    link.href = post.url;
    const src = post.thumbnailImage || post.featuredImage;
    if (src) {
      const image = element('img');
      image.src = src;
      image.alt = '';
      image.loading = 'lazy';
      image.decoding = 'async';
      link.appendChild(image);
    }
    const copy = element('span', 'tt-search-quick-copy');
    copy.appendChild(element('strong', '', post.title || 'Travel story'));
    const firstCategory = categories(post)[0];
    if (firstCategory) copy.appendChild(element('small', '', firstCategory));
    link.appendChild(copy);
    const arrow = element('span', 'tt-search-quick-arrow');
    arrow.setAttribute('aria-hidden', 'true');
    arrow.textContent = '›';
    link.appendChild(arrow);
    return link;
  }

  function goToResults() {
    if (!allResults) return;
    allResults.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      block: 'start'
    });
  }

  function queryMatches(query) {
    if (!query) return posts.slice();
    const terms = query.toLowerCase().match(/[\p{L}\p{N}]+/gu) || [];
    if (terms.length === 0) return posts.slice();
    if (index && typeof window.lunr === 'function') {
      try {
        const refs = index.search(terms.map(t => t + '*').join(' ')).map(x => x.ref);
        const lookup = new Map(posts.map(p => [p.url, p]));
        return refs.map(ref => lookup.get(ref)).filter(Boolean);
      } catch (err) {
        // A plain-text fallback works for punctuation and malformed searches.
      }
    }
    return posts.filter(post => {
      const body = [post.title, post.description, post.content, post.destination, ...categories(post)]
        .filter(Boolean).join(' ').toLowerCase();
      return terms.every(term => body.includes(term));
    });
  }

  function update() {
    const query = input.value.trim();
    const chosenCategory = categoryEl.value.trim().toLowerCase();
    const dayLimit = Number(dateEl.value);
    const now = Date.now();
    let matches = queryMatches(query);
    if (chosenCategory) matches = matches.filter(post => categories(post).some(cat => cat.toLowerCase() === chosenCategory));
    if (dayLimit) matches = matches.filter(post => {
      const date = new Date(post.date).getTime();
      return Number.isFinite(date) && date <= now && now - date <= dayLimit * 86400000;
    });
    const browsing = !query && !chosenCategory && !dayLimit;
    if (browsing) matches = matches.slice(0, 6);
    resultsEl.replaceChildren(...matches.map(createCard));
    // Keep a short, visibly updated preview beside the input so visitors do
    // not need to scroll just to discover whether their search matched.
    if (liveEl && quickEl && quickTitle) {
      liveEl.hidden = browsing;
      if (!browsing) {
        quickTitle.textContent = matches.length
          ? matches.length + (matches.length === 1 ? ' matching story' : ' matching stories')
          : 'No matching stories';
        if (jumpBtn) jumpBtn.hidden = matches.length === 0;
        quickEl.replaceChildren(...matches.slice(0, 2).map(createQuickResult));
        if (!matches.length) {
          quickEl.appendChild(element('p', 'tt-search-quick-empty', 'Try a different place, route or category.'));
        }
      }
    }
    if (emptyEl) emptyEl.classList.toggle('hidden', matches.length > 0);
    // Notify the editorial analytics listener only; it debounces user queries
    // and will never transmit a form field or other personal information.
    if (query.length >= 2) {
      window.dispatchEvent(new CustomEvent('tt:journal-search', {
        detail: {query: query, resultCount: matches.length}
      }));
    }
    if (headingEl) headingEl.textContent = browsing ? 'Recent adventures' : 'Search results';
    countEl.textContent = browsing
      ? 'Explore the latest stories or search for a particular destination.'
      : matches.length + (matches.length === 1 ? ' story found' : ' stories found');
  }

  async function initialize() {
    try {
      countEl.textContent = 'Loading travel stories…';
      const response = await fetch('/search-data.json');
      if (!response.ok) throw new Error('Search index unavailable');
      const data = await response.json();
      posts = (Array.isArray(data.posts) ? data.posts : []).filter(p => p && p.url && p.title);
      posts.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
      if (typeof window.lunr === 'function') {
        index = window.lunr(function () {
          this.ref('url');
          this.field('title', {boost: 10});
          this.field('description', {boost: 5});
          this.field('categories', {boost: 4});
          this.field('destination', {boost: 3});
          this.field('content');
          posts.forEach(post => this.add({
            url: post.url, title: post.title || '', description: post.description || '',
            destination: post.destination || '', categories: categories(post).join(' '),
            content: post.content || ''
          }));
        });
      }
      const params = new URLSearchParams(window.location.search);
      if (params.has('q')) input.value = params.get('q') || '';
      update();
    } catch (err) {
      countEl.textContent = 'Search is temporarily unavailable. Please try again later.';
    }
  }

  input.addEventListener('input', () => {
    clearTimeout(debounceId);
    debounceId = setTimeout(update, 180);
  });
  categoryEl.addEventListener('change', update);
  dateEl.addEventListener('change', update);
  if (clearBtn) clearBtn.addEventListener('click', () => {
    input.value = '';
    categoryEl.value = '';
    dateEl.value = '';
    update();
    input.focus();
  });
  input.addEventListener('keydown', e => {
    if (e.key === 'Escape') { input.value = ''; update(); }
    if (e.key === 'Enter') {
      e.preventDefault();
      clearTimeout(debounceId);
      update();
      if (resultsEl.children.length > 0) goToResults();
    }
  });
  if (jumpBtn) jumpBtn.addEventListener('click', goToResults);
  initialize();
}());
