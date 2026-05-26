# Spec: Feature Requests Core

## Overview
Spendly users currently have no way to suggest product improvements, and there is no shared space for the community to discover or discuss feature ideas. This release introduces the core feature request system: three new database tables, a `/features` route visible to all visitors, and a two-state page experience. Logged-out visitors can browse, search, filter, sort, and open feature detail modals. Logged-in users additionally see a two-column layout where their own submitted requests (with edit/delete controls) appear on the left and the submission form appears on the right. View counts increment each time a detail modal is opened, providing the data foundation for trending (implemented in Release 2).

## Release context
Release 1 of 3 — Core infrastructure and page.

**In scope:**
- 3 new DB tables: `feature_requests`, `feature_votes` (schema only, no voting UI yet), `feature_views`
- `/features` nav link visible to all visitors (logged-in and logged-out)
- Logged-out state: public listing with search, filter by page/status, sort (Latest, Most Upvoted, Most Viewed), card detail modal, view count on modal open, initials avatar only
- Logged-in state: two-column layout — left panel = user's own requests with edit/delete controls; right panel = submission form
- Submission form: hardcoded page dropdown, title (max 120 chars), description (min 20, max 1000 chars)
- 5-request-per-user spam limit enforced on submit
- Ownership check on edit and delete
- Privacy: only initials avatar shown, never full name or email

**Deferred to Release 2:** Upvote/remove-vote UI, self-vote prevention, unauthenticated upvote prompt, trending score calculation, Trending sort option.

**Deferred to Release 3:** Home page "Latest Features" section.

**Deferred entirely:** Status management UI, admin/moderation tooling.

## Depends on
- Feature 01 — Database Setup (users table)
- Feature 02 — Registration
- Feature 03 — Login and Logout (session handling)

## Routes
- `GET /features` — Feature requests page (public listing logged-out; two-column logged-in) — public
- `POST /features` — Submit a new feature request — logged-in
- `GET /features/<int:id>/edit` — Edit feature request form — logged-in (owner only)
- `POST /features/<int:id>/edit` — Save edited feature request — logged-in (owner only)
- `POST /features/<int:id>/delete` — Delete a feature request — logged-in (owner only)
- `POST /features/<int:id>/view` — Increment view count when detail modal is opened — public

## Database changes
Three new tables to add to `init_db()` in `database/db.py`:

```sql
CREATE TABLE IF NOT EXISTS feature_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    page        TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'submitted',
    views       INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now')),
    updated_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS feature_votes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id INTEGER NOT NULL REFERENCES feature_requests(id),
    user_id    INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT    DEFAULT (datetime('now')),
    UNIQUE (feature_id, user_id)
);

CREATE TABLE IF NOT EXISTS feature_views (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id INTEGER NOT NULL REFERENCES feature_requests(id),
    viewer_id  INTEGER REFERENCES users(id),
    viewed_at  TEXT    DEFAULT (datetime('now'))
);
```

Note: `feature_votes` schema is created here but the voting UI ships in Release 2. The `UNIQUE(feature_id, user_id)` constraint is essential for duplicate-vote prevention and must be in place from the start.

## Templates
**Create:**
- `templates/features.html` — main /features page (handles both logged-out and logged-in states)
- `templates/edit_feature_request.html` — edit form for an existing feature request

**Modify:**
- `templates/base.html` — add "Features" nav link visible to all visitors (logged-in and logged-out), alongside existing nav items

## Files to change
- `database/db.py` — add the 3 new tables to `init_db()`
- `database/queries.py` — add all feature request query helpers (see below)
- `app.py` — add 6 new routes, import new query helpers, define `VALID_PAGES` constant
- `templates/base.html` — add Features nav link

## Files to create
- `templates/features.html`
- `templates/edit_feature_request.html`
- `static/css/features.css`

## Query helpers to add in `database/queries.py`
- `get_feature_requests(page_filter=None, status_filter=None, sort='latest', exclude_user_id=None)` — returns list with upvote count joined
- `get_own_feature_requests(user_id)` — returns all requests submitted by this user
- `get_feature_request_by_id(feature_id)` — single row
- `insert_feature_request(user_id, page, title, description)` — returns new id
- `update_feature_request(feature_id, user_id, page, title, description)` — ownership enforced via `AND user_id = ?`
- `delete_feature_request(feature_id, user_id)` — ownership enforced via `AND user_id = ?`
- `count_user_feature_requests(user_id)` — for spam limit check
- `increment_feature_view(feature_id, viewer_id)` — inserts into `feature_views` and updates `feature_requests.views`

## New dependencies
No new dependencies.

## Error handling
- **Missing or invalid form fields:** flash error and re-render form with previously entered values
- **Title exceeds 120 characters:** flash "Title must be 120 characters or fewer."
- **Description under 20 characters:** flash "Description must be at least 20 characters."
- **Description exceeds 1000 characters:** flash "Description must be 1000 characters or fewer."
- **Page not in valid list:** flash "Please select a valid page."
- **Spam limit exceeded:** if `count_user_feature_requests(user_id) >= 5`, flash "You have reached the maximum of 5 feature requests." and do not insert
- **Edit/delete by non-owner:** `update_feature_request` and `delete_feature_request` include `AND user_id = ?`; if no row affected, abort(403)
- **Edit/delete unauthenticated:** redirect to `/login`
- **Feature request not found:** abort(404)

## UI/UX notes

**Page states:**
- Logged-out: single-column listing; search bar at top; filter chips for page categories and status; sort dropdown (Latest, Most Upvoted, Most Viewed); feature cards in a grid; clicking a card opens a detail modal and fires `POST /features/<id>/view`
- Logged-in: two-column layout (approx 60/40 split); left = user's own submitted requests (each card has Edit / Delete buttons); right = "Submit a Feature Request" form

**Feature cards** must show:
- Page category label (badge)
- Title
- Description snippet (truncated to ~100 chars)
- Status badge (`submitted` default; display as "Submitted")
- Initials avatar (generated from `name`: first letter of first word + first letter of last word, uppercased; e.g. "John Doe" → "JD", single-name users → first two letters)
- Relative timestamp (e.g. "5 min ago", "2 days ago")
- 👍 vote count (number only in Release 1 — no clickable button until Release 2)
- 👁 view count

**Detail modal:** opens on card click; shows full description, all metadata, same initials avatar; closes on backdrop click or Escape key; view count increments via `POST /features/<id>/view` on open

**Form (right panel, logged-in only):**
- Page dropdown (hardcoded): Home, Profile, Analytics, Add Expense, Edit Expense, Other
- Title text input (max 120)
- Description textarea (min 20, max 1000), character counter recommended
- Submit button; on success flash "Feature request submitted." and refresh list

**Edit form (`/features/<id>/edit`):** same fields as submission form, pre-populated; on success flash "Feature request updated." and redirect to `/features`

**Delete:** POST-only; on success flash "Feature request deleted." and redirect to `/features`

**Nav link:** "Features" added to `base.html` nav; visible to all visitors; active state when on `/features`

**Flash messages:**
- Success: "Feature request submitted.", "Feature request updated.", "Feature request deleted."
- Errors: as listed in Error handling above

**Responsive design:**
- On mobile (`max-width: 600px`): two-column layout collapses to single column; submission form stacks below the listing
- Use existing CSS breakpoints from `static/css/style.css`

**Accessibility:**
- All form inputs must have `<label>` elements
- Modal must trap focus while open and restore focus on close
- Buttons must have descriptive text or `aria-label`

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never interpolate user data into SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard on every protected route — check `session.get("user_id")` and redirect to `/login`
- Ownership check on all feature request mutations — queries must include `AND user_id = ?`
- Flash messages for all user-facing outcomes
- Privacy: never expose full name or email on any page; only initials avatar

## Definition of done
- [ ] `/features` is accessible without login and renders a public listing
- [ ] "Features" link appears in the nav for all visitors (logged-in and logged-out)
- [ ] Logged-in users see the two-column layout with their own requests on the left and the submission form on the right
- [ ] Submitting a feature request saves to DB and appears in the listing
- [ ] Submitting with a missing or invalid field shows the correct flash error
- [ ] A user who has submitted 5 requests cannot submit a 6th (spam limit enforced)
- [ ] Only the submitter can see Edit/Delete on their own cards
- [ ] Editing a feature request updates the record and redirects to `/features`
- [ ] Attempting to edit/delete another user's request returns 403
- [ ] Deleting a feature request removes it and flashes a success message
- [ ] Clicking a feature card opens the detail modal and increments the view count
- [ ] Feature cards show initials avatar only — never full name or email
- [ ] Search filters the listing by title, description, and page
- [ ] Page category filter and status filter work correctly
- [ ] Sort by Latest, Most Upvoted, Most Viewed returns correct ordering
- [ ] All of the above have corresponding pytest test cases in `tests/test_11.1-feature-requests-core.py`
