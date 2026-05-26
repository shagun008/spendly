# Spec: Feature Requests Voting

## Overview
Feature 11.1 built the community feature requests page with submission, browsing, edit/delete, and view tracking — but the upvote UI was intentionally deferred. This release activates voting. Users can upvote any feature request they didn't submit themselves, and toggle their vote off by clicking again. A new "Trending" sort order ranks requests by a weighted score of votes, views, and recency, surfacing the most engaged ideas. This completes the core social signal loop: users can now express preference, not just submit ideas.

## Release context
Release 2 of 3.

**In scope for this release:**
- `POST /features/<id>/vote` — toggle upvote on/off, returns JSON
- Upvote button on each card in the listing and inside the detail modal
- Self-vote prevention: disabled button with tooltip on the user's own requests
- Unauthenticated users clicking upvote are redirected to `/login`
- 1-vote-per-user enforced via the existing `UNIQUE(feature_id, user_id)` constraint on `feature_votes`
- Trending score = `(vote_count × 5) + (views × 1) + MAX(0, 7 − days_since_created)`
- "Trending" option added to the sort dropdown on `/features`

**Deferred to Release 3:**
- Home page "Latest Features" section showing the latest 6 feature request cards

**Open questions:** None remaining.

## Depends on
- Feature 11.1 (DB, Submission, and /features Page — Core) — must be shipped

## Routes
- `POST /features/<id>/vote` — toggle upvote for the current user; returns `{"voted": bool, "upvotes": int}` — logged-in only (401 if unauthenticated, 403 if own request, 404 if not found)

## Database changes
No database changes. The `feature_votes` table with `UNIQUE(feature_id, user_id)` constraint was created in Release 1 and is already in place.

## Templates
- **Create:** none
- **Modify:**
  - `templates/_features_listing.html` — replace the static 👍 vote count span with an interactive upvote button; add `data-voted` and `data-is-own` attributes to `.fr-card`; add "Trending" option to the sort dropdown
  - `templates/features.html` — add `fr-vote-base` URL anchor for JS; update `openModal` to render a live vote button in the modal; add `handleVote` JS function

## Files to change
- `database/queries.py` — add `toggle_feature_vote(feature_id, user_id)`; add `"trending"` sort case to `get_feature_requests()`
- `app.py` — add `VALID_SORTS` constant; add `voted_ids` set build in `features()` route; add `vote_feature_request` route; import `toggle_feature_vote`
- `templates/_features_listing.html` — upvote button, card data attributes, Trending sort option
- `templates/features.html` — vote base URL, modal vote button, `handleVote` JS
- `static/css/features.css` — upvote button styles

## Files to create
None.

## New dependencies
No new dependencies.

## Error handling
- **Not logged in:** `POST /features/<id>/vote` returns 401; JS intercepts and redirects to `/login`
- **Own request:** backend returns 403; button is `disabled` in template (defense in depth)
- **Feature not found:** `get_feature_request_by_id` returns None → `abort(404)`
- **Double-vote:** `INSERT OR IGNORE` silently skips on duplicate; `rowcount == 0` triggers the DELETE branch — net effect is a clean toggle-off, never a double-count
- **Invalid sort param:** `VALID_SORTS` whitelist check in `features()` route falls back to `"latest"`

## UI/UX notes
- **Vote button states:**
  - Default (not voted): pill-shaped button, muted border, muted text — `👍 N`
  - Voted: accent background, accent border, accent text, bold — `👍 N`
  - Disabled (own request): 45% opacity, `cursor: not-allowed`, native `title` tooltip "You can't vote for your own request"
  - Hover (votable): accent-light background, accent border
- **Vote toggle feedback:** Button class and count update in-place via JS — no page reload, no flash message (visual state change is the feedback for an AJAX toggle)
- **Unauthenticated flow:** Clicking any vote button when logged out triggers fetch → 401 → `window.location.href = '/login'`
- **Modal sync:** Both the card button and the modal button share `data-feature-id`; `querySelectorAll` updates both in one pass so they always stay in sync
- **Accessibility:** Vote buttons have `aria-label="Upvote this feature request"` and `aria-pressed` (true/false, updated on toggle); disabled button has `aria-label="You can't vote for your own request"`
- **Click propagation:** Vote button `onclick` calls `event.stopPropagation()` to prevent the card's modal-open handler from firing
- **Responsive:** Vote button is inline-flex and fits within the existing `.fr-card-meta` row at all breakpoints; no new breakpoints needed

## Rules for implementation
See `CLAUDE.md`. Key constraints for this feature:
- No ORMs — raw `sqlite3` only
- Parameterised queries only
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard: check `session.get("user_id")` and return 401 (not redirect) for AJAX endpoints

## Definition of done
- [ ] `POST /features/<id>/vote` returns `{"voted": true, "upvotes": N}` on first vote
- [ ] Second `POST /features/<id>/vote` by same user returns `{"voted": false, "upvotes": N-1}` (toggle off)
- [ ] Vote button on card turns green and count increments without page reload
- [ ] Clicking the voted button again turns it back to default and decrements count
- [ ] Voting on own request: button is disabled; `POST /features/<id>/vote` returns 403
- [ ] Logged-out user clicking upvote is redirected to `/login`
- [ ] `POST /features/<id>/vote` on non-existent ID returns 404
- [ ] Modal vote button stays in sync with card vote button after toggling
- [ ] "Trending" option appears in the sort dropdown
- [ ] Trending sort returns 200 and orders results by `(votes × 5) + views + recency_bonus`
- [ ] All of the above covered by `tests/test_11.2-feature-requests-voting.py`
