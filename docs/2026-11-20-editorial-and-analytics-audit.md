# Travelling Trails — Older Article Editorial and GA4 Review
**Date:** 20 November 2026  
**Working branch:** `design/modern-explorer-2026` (draft PR #24)  
**Editorial basis:** `Travelling Trails Writing Style.md` and `Travelling Trails Publishing Playbook.md` supplied by the owner  
**Scope:** the 12 existing published posts under `src/blog/`; no URLs, titles, trip metadata, dates, images or publication flags changed.

## 1. Work completed

All 12 older stories received an experience-first edit of their openings and/or closing reflections, with selected chapter headings, awkward sentences and clichéd phrases polished. Their existing article bodies remain substantially intact: this was a controlled narrative refresh, not a recreation of trips from new notes. The site's SEO summary descriptions were independently improved in the previous audit.

| Story | Narrative focus of this edit | Further owner/verification review |
|---|---|---|
| Raigad Fort solo ride | Childhood connection, actual late start, sunset on the return | Check current ropeway timings, seasonal closures and trekking advice before presenting as up-to-date |
| Tamhini Ghat to Tiger Point | Six-rider group, change from smooth roads to rougher tracks, desire to return to Savlya | Recheck old road-surface and riding-condition claims |
| Savlya Ghat first visit | Unexpected viewpoint after a detour before office outing | Verify parking charge, trail access, connectivity and seasonal safety if used as visitor advice |
| Ellora Caves and Devgiri Fort | Kailasa Temple remembered from a school textbook; travel with two riders | Verify attraction/temple hours, historical assertions and any current entry conditions; keep trip observations dated |
| Diveagar Beach | Ganpati Visarjan, unusually quiet roads, cattle and the short beach stop | A festival is not guaranteed to produce low traffic; avoid treating one day's conditions as a universal suggestion |
| Night Rides Through Pune | Familiar streets after dark, warm night and unexpectedly busy roads | Safety review: narrative mentions removing jacket armour; don't interpret as advice to do so |
| Wagheshwar Temple | Seeing the normally submerged shrine while water levels permitted | Verify historical attribution, changing access, and soft lakebed risks before suggesting a route |
| Kadve Ghat | Seeing Torna, Rajgad and Gunjavne Dam in one frame | Recheck present road hazards, signal/network coverage, route difficulty and seasonal conditions |
| Kolhapur and Khidrapur | First longer ride as a couple, the long-held temple plan and navigation mistakes | Keep real disagreements and road fatigue; review high-speed and service-related references for safety context |
| Tamhini–Lavasa off-road trail | Curiosity about a new track, friends helping each other, three-fort viewpoint | A malformed Aahar Vatika link was replaced with plain text (not an invented URL); verify current trail access and monsoon safety |
| Mahabaleshwar / Mapro Garden | First TRP group ride, long breakfast delay, fatigue/dehydration after missing a stop | Emphasize that skipping water was a mistake, not a riding recommendation; recheck operating details if referenced |
| Savlya Ghat office camping | Return to Savlya, group effort, stargazing hopes versus conditions | Check campsite permissions, overnight safety and any current visitor restrictions |

### Editorial principles followed

- Preserve actual memories, people, stops, route information, images, notes and dates.
- Keep the owner's `I` and `we` perspective; avoid inventing sensory details, dialogue, emotions or events.
- Replace marketing phrases with concrete motivations, surprises, disappointments and observations.
- Keep original SEO title/slug compatibility and internal link destinations.
- Do not silently "correct" time-sensitive road safety, fort opening hours or historical claims; identify them for verification.
- Standardize new prose toward Indian/British English, without globally rewriting place names or older direct quotations.

## 2. GA4 findings and implementation

### Found in the previous scripts
- Duplicate manual `page_view` events in addition to the standard Google tag page view.
- Manual outbound `click` duplicated enhanced measurement; extra scroll-depth tracking overlapped with a second analytics script.
- Old newsletter measurement was based on a submit interaction, not a confirmed successful Netlify response.
- The cookie banner's accept/reject choice was evaluated after the Google tag configuration.

### Implemented on the draft branch
- The tag now reads the existing cookie choice before configuration and defaults optional analytics-cookie storage to denied until accepted.
- `analytics-events.js` is loaded only on production, not Netlify deploy previews.
- GA4's built-in page views, outbound clicks, downloads and 90%-scroll event are not manually duplicated.
- Custom editorial events: `select_content`, `search`, `filter_apply`, `share`, `article_read_progress` at 50/75%, `hero_navigation`, `trip_details_interaction`, `contact_email_click`.
- `generate_lead` records contact and newsletter forms only after returning to the Netlify `/success/` page with a recent same-tab submission marker; the marker contains only the form name and time, not form data.
- GA4 event parameters avoid email addresses and form contents; site-search queries matching common email/long-number patterns are discarded.
- Legacy theme and load-more events use the central consent guard.

### Account actions after publishing
1. GA4 **Admin → Product links → Search Console links → Link**. Select the verified `https://travellingtrails.in/` Search Console property and the correct GA4 web stream. This account-level action cannot be performed in GitHub.
2. In the GA4 web stream, verify Enhanced Measurement (page views, outbound clicks, site search, scroll, file download) and avoid creating parallel duplicate custom tags.
3. Accept optional analytics cookies in a test browser, then check GA4 **Realtime** or **DebugView** on the live published domain for `select_content`, `search` and `generate_lead`. Preview builds intentionally do not send GA4 hits.
4. Decide whether `generate_lead` should be marked as a **key event**. If contact and newsletter should be distinguished in standard reports, register `lead_source` and `form_name` as event-scoped custom dimensions.
5. Review how many events your consent banner actually permits; Google tag consent settings may change observable traffic counts compared to the old setup.

## 3. Search Console status supplied by owner screenshots

- XML sitemap `/sitemap.xml`: **Success**, last read **16 November 2026**, **27 discovered pages** (not synonymous with indexed pages).
- Old submission `/sitemap`: **1 error**, zero discovered pages. Remove obsolete *Search Console submission*; keep the human-readable `/sitemap/` website page.
- Search Console overview: **69 clicks** over the displayed report period, with a positive impressions alert for the night-rides article.
- The repo's redesigned sitemap is on the draft branch; Google has not read this future production version yet.

## 4. Contact email and forms

- Public email source: `site.contactEmail = "hello@travellingtrails.in"`.
- The Contact page, footer, Privacy Policy, confirmation page, and every currently identified Netlify form (Contact, homepage Journal newsletter, Blog newsletter, Gear newsletter) display the same public reply-to address.
- **Mailbox/DNS must actually exist**; editing site HTML does not create or configure an inbox.
- **Netlify notification recipient is an account setting:** Site → Forms → Submission notifications. Assign and, where required, confirm `hello@travellingtrails.in` there. The forms' visitor `name="email"` field remains unchanged.
- **Newsletter delivery is separate** from Netlify collecting signup forms. An email-marketing service or workflow still needs connecting before subscribers receive newsletters.

## 5. Release gate

- This document and all code/text changes are on draft PR #24, not live `main`.
- Run Eleventy/Netlify preview build; check desktop/mobile/dark-mode pages and all forms.
- Manually inspect any long paragraphs or photo captions that still use repeated promotional adjectives.
- Verify date-sensitive travel facts, schema and Search Console indexing only against the live site after deployment.
- Merge only after explicit owner visual and publishing approval.
