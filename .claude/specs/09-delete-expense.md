# Spec: Delete Expense

## Overview
Step 9 lets a logged-in user permanently delete any of their own expenses directly
from the profile page. A POST-based delete route at `/expenses/<id>/delete` handles
the deletion with ownership enforcement — a user can only delete their own rows.
A small `delete_expense` query helper is added to `database/queries.py`. The
transactions table in `profile.html` gains a "Delete" button per row rendered as
a minimal inline form (to avoid GET-based deletions). No separate confirmation page
is required; deletion happens in one click with a success flash message.

## Depends on
- Step 1: Database setup (`expenses` table exists)
- Step 3: Login / Logout (`session["user_id"]` is set and enforced)
- Step 5: Profile page renders transactions (the delete button lives there)
- Step 8: Edit Expense (establishes the Actions column this step adds to)

## Routes
- `POST /expenses/<int:id>/delete` — delete the expense if it belongs to the
  current user, then redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. The existing `expenses` table is used as-is.

## Templates
- **Modify**: `templates/profile.html`
  - Add a "Delete" button alongside the existing "Edit" link in the Actions cell
    of each transaction row
  - The delete button must be a `<form method="POST">` pointing to
    `/expenses/{{ tx.id }}/delete` — never a plain `<a>` link

## Files to change
- `database/queries.py`
  - Add `delete_expense(expense_id, user_id)` — issues a parameterised
    `DELETE FROM expenses WHERE id = ? AND user_id = ?` to enforce ownership
- `app.py`
  - Import `delete_expense` from `database.queries`
  - Replace the GET placeholder at `/expenses/<int:id>/delete` with a
    POST-only handler:
    - Redirect unauthenticated requests to `/login`
    - Call `delete_expense(id, session["user_id"])`
    - Flash "Expense deleted." and redirect to `url_for("profile")`
  - Change the route decorator to `methods=["POST"]`
- `templates/profile.html`
  - Add a delete form button in the `<td>` that already contains the Edit link,
    after it

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- `delete_expense` must scope its `DELETE` to `id = ? AND user_id = ?` to prevent
  one user deleting another user's expense
- The route must only accept `POST` — visiting via GET should return 405
- Unauthenticated access must redirect to `/login`
- No separate confirmation page — delete on first POST, flash success
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ — never £ or $
- The delete form in the template must carry `method="POST"` and have no extra
  hidden fields (no CSRF token required at this stage)

## Definition of done
- [ ] Visiting `POST /expenses/<id>/delete` while logged out redirects to `/login`
- [ ] Posting to `/expenses/<id>/delete` for an expense that belongs to the current
  user deletes it from the database and redirects to `/profile` with a flash message
- [ ] Posting to `/expenses/<id>/delete` for another user's expense does not delete
  it and redirects to `/profile` (no error, silent no-op due to WHERE clause scoping)
- [ ] The deleted expense no longer appears in the transaction list after deletion
- [ ] Each row in the profile transaction table has a "Delete" button next to the
  "Edit" link
- [ ] Sending a GET request to `/expenses/<id>/delete` returns 405 Method Not Allowed
