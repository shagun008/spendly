# Spec: Home Latest Features Section

## Overview
This feature adds a "Latest Features" section to the public landing page, surfacing the most recent community feature requests to every visitor — logged in or not. It completes the discovery loop introduced in Feature 11: users can now see what the community is building next without navigating away from the home page, and a "View All Features →" CTA drives them to the full `/features` page. The section is read-only — cards display vote and view counts but offer no upvote action. Clicking a card navigates to `/features`.

## Release context
Release 3 of 3. Releases 11.1 (core DB + `/features` page) and 11.2 (upvoting + trending) are shipped. This release is purely frontend/template work — all data is already available via `get_feature_requests()` in `database/queries.py`.

**In scope:**
- New section on the landing page showing up to 6 latest feature request cards
- Cards are read-only: show page badge, status badge, title, description snippet, initials avatar, relative timestamp, vote count, view count
- Clicking a card navigates to `/features`
- "View All Features →" CTA linking to `/features`
- Section hidden entirely when no feature requests exist

**Deferred:** Category filter tabs on the landing page (mentioned in release plan as a nice-to-have but not required for this release).

**Open questions:** None remaining.

## Depends on
- Feature 11.1 — feature_requests, feature_votes, feature_views tables + `get_feature_requests()` helper
- Feature 11.2 — `vote_count` field on feature request rows (via `feature_votes` join)

## Routes
No new routes. Modify the existing `GET /` landing route in `app.py` to fetch and pass `latest_features` to the template.

## Database changes
No database changes. All required data is in `feature_requests`, `feature_votes`, and `feature_views`.

## Templates
- **Modify:** `templates/landing.html` — insert new `.latest-features-section` between the `.features` showcase section and `.cta-section`

## Files to change
- `app.py` — `landing()` function: call `get_feature_requests(sort='latest')` and slice `[:6]`, pass as `latest_features` to `render_template`
- `templates/landing.html` — add the latest features section (guarded by `{% if latest_features %}`)
- `static/css/landing.css` — append styles for the new section

## Files to create
None.

## New dependencies
No new dependencies.

## Error handling
- **Empty DB** — guard with `{% if latest_features %}` so the section renders only when rows exist; no error state needed
- **Description shorter than 100 chars** — truncation logic must check length before appending ellipsis to avoid stray `…` characters
- **`get_feature_requests()` raising an exception** — let Flask's default error handling surface this; no special try/except needed in the landing route since this is a read-only call with no user input

## UI/UX notes
- Section heading: "Shaping Spendly Together" with a short subtitle ("See what the community is building next.") and the "View All Features →" link in the same header row (right-aligned on desktop, below heading on mobile)
- Cards are anchor tags (`<a href="/features">`) — no JS needed for navigation
- Each card displays: page badge, status badge, title, truncated description (~100 chars), initials avatar (circular), relative timestamp, 👍 vote count, 👁 view count
- No upvote button on landing page cards
- Status badge colours match `/features` page convention: `submitted` → muted, `under_review` → amber (`--accent-2`), `planned` → accent green, `completed` → accent green (stronger)
- Cards use `var(--paper-card)` background, `var(--border)` border, `var(--radius-md)` radius, hover: subtle `box-shadow`
- Grid: `repeat(auto-fill, minmax(260px, 1fr))`, gap `1rem`
- `@media (max-width: 900px)` — grid may wrap naturally; no layout change needed
- `@media (max-width: 600px)` — single-column grid; header stacks vertically with "View All" below subtitle
- Accessibility: cards are `<a>` elements with descriptive text content; no icon-only buttons; colour contrast must meet WCAG AA

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only (not applicable here — no new queries)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `get_feature_requests()` is already imported in `app.py` (line 27) — do not re-import

## Definition of done
- [ ] Visiting `/` while logged out shows the "Shaping Spendly Together" section with up to 6 cards
- [ ] Visiting `/` while logged in also shows the section
- [ ] Each card displays page badge, status badge, title, description snippet, initials, time ago, vote count, view count
- [ ] No upvote button appears on any landing page card
- [ ] Clicking a card navigates to `/features`
- [ ] "View All Features →" link navigates to `/features`
- [ ] Section is absent when `feature_requests` table is empty
- [ ] Layout is responsive: single column on mobile (`≤600px`), auto-fill grid on wider screens
- [ ] All existing pytest tests continue to pass
