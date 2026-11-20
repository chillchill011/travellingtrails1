/*
 * Travelling Trails — GA4 editorial measurement.
 * GA4 Enhanced Measurement owns page_view, outbound click, 90%-scroll,
 * file_download and form_start/form_submit: do not duplicate those events.
 *
 * This file loads only on the production site. No email address, message,
 * form contents, or other personally identifiable information is collected.
 */
(function () {
  'use strict';

  function consentGranted() {
    try { return window.localStorage.getItem('cookie-consent') === 'accepted'; }
    catch (error) { return false; }
  }

  function track(name, params) {
    if (!consentGranted() || typeof window.gtag !== 'function') return;
    window.gtag('event', name, params || {});
  }
  window.ttTrack = track;

  // Record only the type of a submitted Netlify form. Do not claim that a
  // button click means the server accepted the submission.
  document.addEventListener('submit', function (event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.matches('form[data-netlify="true"]')) return;
    const formName = form.getAttribute('name');
    if (!['contact', 'newsletter', 'gear-newsletter'].includes(formName)) return;
    if (!form.checkValidity()) return;
    try {
      window.sessionStorage.setItem('tt_pending_form', JSON.stringify({
        type: formName, at: Date.now()
      }));
    } catch (error) { /* storage unavailable */ }
  });

  // A successful redirect to /success/ is the best available client-side
  // signal for accepted Netlify form submissions. Consume it once.
  if (window.location.pathname === '/success/') {
    try {
      const stored = window.sessionStorage.getItem('tt_pending_form');
      window.sessionStorage.removeItem('tt_pending_form');
      const submission = stored ? JSON.parse(stored) : null;
      if (submission && ['contact', 'newsletter', 'gear-newsletter'].includes(submission.type)
          && Date.now() - submission.at < 5 * 60 * 1000) {
        track('generate_lead', {
          lead_source: submission.type === 'contact' ? 'contact_form' : 'newsletter',
          form_name: submission.type,
          method: 'netlify_form'
        });
      }
    } catch (error) { /* unavailable storage, never block the page */ }
  }

  // Meaningful story navigation rather than each automatic slide rotation.
  document.addEventListener('click', function (event) {
    const target = event.target.closest('a, button');
    if (!target) return;
    if (target.matches('[data-hero-feature]')) {
      track('select_content', {content_type: 'featured_story', item_id: target.pathname || '/'});
    } else if (target.matches('.tt-search-card h3 a, .tt-search-read')) {
      track('select_content', {content_type: 'search_result', item_id: target.pathname || '/'});
    } else if (target.matches('.tt-related-card h3 a')) {
      track('select_content', {content_type: 'related_story', item_id: target.pathname || '/'});
    } else if (target.matches('.tt-home .tt-hero-inner .tt-pill')) {
      track('select_content', {content_type: 'homepage_cta', item_id: target.pathname || '/'});
    }

    if (target.matches('.share-button, .copy-link-button')) {
      const label = (target.getAttribute('aria-label') || '').toLowerCase();
      let method = 'other';
      if (label.includes('facebook')) method = 'facebook';
      else if (label.includes('twitter') || label.includes(' x')) method = 'x';
      else if (label.includes('linkedin')) method = 'linkedin';
      else if (label.includes('whatsapp')) method = 'whatsapp';
      else if (label.includes('instagram')) method = 'instagram';
      else if (label.includes('snapchat')) method = 'snapchat';
      else if (label.includes('email')) method = 'email';
      else if (label.includes('copy')) method = 'copy_link';
      track('share', {method: method, content_type: 'article', item_id: window.location.pathname});
    }

    if (target.matches('a[href^="mailto:"]') && !target.matches('.share-button')) {
      track('contact_email_click', {channel: 'email', location: window.location.pathname});
    }
    if (target.matches('[data-hero-next], [data-hero-previous]')) {
      track('hero_navigation', {direction: target.matches('[data-hero-next]') ? 'next' : 'previous'});
    }
    if (target.matches('.trip-details-toggle')) {
      track('trip_details_interaction', {page_path: window.location.pathname});
    }
  });

  // Journal search is client-rendered and does not navigate to a new URL,
  // so it is not fully covered by Enhanced Measurement's URL-based search.
  let searchTimer = null;
  let previousSearch = '';
  window.addEventListener('tt:journal-search', function (event) {
    const details = event.detail || {};
    const searchTerm = String(details.query || '').trim().replace(/\s+/g, ' ');
    // Never transmit likely email addresses, phone numbers or user identifiers.
    if (searchTerm.length < 2 || searchTerm.length > 65 ||
        /@|https?:\/\/|\d{6,}/i.test(searchTerm)) return;
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(function () {
      const key = searchTerm.toLowerCase();
      if (key === previousSearch) return;
      previousSearch = key;
      track('search', {
        search_term: searchTerm,
        result_count: Math.max(0, Number(details.resultCount) || 0)
      });
    }, 950);
  });

  document.addEventListener('change', function (event) {
    if (event.target.matches('#categoryFilter, #activityFilter, #dateFilter')) {
      const kind = event.target.id === 'categoryFilter' ? 'category'
        : event.target.id === 'activityFilter' ? 'activity' : 'date';
      track('filter_apply', {
        filter_type: kind,
        context: window.location.pathname === '/explore/' ? 'explore' : 'journal_search',
        has_selection: !!event.target.value
      });
    }
  });

  // The standard GA4 90%-scroll event remains automatic; these separate
  // milestones help identify where a story retains readers.
  if (document.body.classList.contains('tt-article-page')) {
    const milestones = [50, 75];
    const sent = new Set();
    let scheduled = false;
    const checkDepth = function () {
      scheduled = false;
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (maxScroll <= 0 || document.hidden) return;
      const percent = Math.round(100 * window.scrollY / maxScroll);
      milestones.forEach(function (mark) {
        if (percent >= mark && !sent.has(mark)) {
          sent.add(mark);
          track('article_read_progress', {percent_read: mark, page_path: window.location.pathname});
        }
      });
    };
    window.addEventListener('scroll', function () {
      if (scheduled) return;
      scheduled = true;
      window.requestAnimationFrame(checkDepth);
    }, {passive: true});
  }
}());
