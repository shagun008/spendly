# Spec: Mobile Navigation

## Overview
Step 10 fixes the mobile header so all navigation links are accessible on small
screens (≤ 600px). Previously, a CSS rule hid every nav link that wasn't a CTA
button on mobile — meaning "Sign in" was invisible to logged-out users, and
"Add Expense", "Analytics", and the username were invisible to logged-in users.
The fix introduces a hamburger button that reveals a dropdown menu containing all
the same links that appear in the desktop nav. No new routes or database changes
are required — this is a pure front-end change across `base.html`, `style.css`,
and `main.js`.

## Depends on
- Step 3: Login / Logout (`session["user_id"]` used to conditionally render links)
- Step 5: Backend routes for profile page (nav links reference `add_expense`,
  `analytics`, `profile`, `logout` endpoints)

## Routes
No new routes.

## Database changes
No database changes.

## Templates
- **Modify**: `templates/base.html`
  - Add a `<button class="nav-hamburger" id="nav-hamburger">` with three
    `<span>` children inside `.nav-inner`, after `.nav-links`
  - Add a `<div class="nav-mobile-menu" id="nav-mobile-menu">` inside `<nav>`,
    after `.nav-inner`
  - The mobile menu must mirror the desktop links:
    - Logged-out: "Sign in" link + "Get started" CTA
    - Logged-in: "Add Expense", "Analytics", username (links to profile), "Logout" CTA
  - Active-page highlighting (`nav-link--active`) must be applied in the mobile
    menu using the same `request.endpoint` checks as the desktop nav

## Files to change
- `templates/base.html`
  - Add hamburger `<button>` inside `.nav-inner`
  - Add `.nav-mobile-menu` dropdown inside `<nav>` (sibling of `.nav-inner`)
    containing the same conditional link structure as `.nav-links`
- `static/css/style.css`
  - Remove the old rule `.nav-links a:not(.nav-cta) { display: none; }` from the
    `@media (max-width: 600px)` block
  - In its place, at ≤ 600px: hide `.nav-links` entirely and show
    `.nav-hamburger` as a flex element
  - Add styles for `.nav-hamburger` (hidden on desktop, flex column of three
    `<span>` bars, animated to an ✕ when `aria-expanded="true"`)
  - Add styles for `.nav-mobile-menu` (hidden by default via `display: none`,
    revealed with `display: flex` when `.is-open` is added, `position: absolute`
    anchored to the sticky navbar, full-width dropdown with per-link borders)
  - Add `.nav-mobile-link`, `.nav-mobile-username`, `.nav-mobile-cta` classes
- `static/js/main.js`
  - Add a self-invoking function that:
    - Toggles `.is-open` on `#nav-mobile-menu` when `#nav-hamburger` is clicked
    - Updates `aria-expanded` on the button and `aria-hidden` on the menu
    - Closes the menu when any `<a>` inside it is clicked

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- The hamburger button must only be visible at ≤ 600px; `.nav-links` must only
  be visible above 600px — never both at the same time
- The mobile menu must contain ALL links (logged-out: Sign in + Get started;
  logged-in: Add Expense + Analytics + username + Logout)
- "Sign in" must be visible to logged-out users on mobile
- "Add Expense", "Analytics", and the username must be visible to logged-in users
  on mobile
- Active-page state (`nav-link--active`) must work in the mobile menu
- The hamburger must animate to an ✕ when the menu is open
- The menu must close when a link inside it is clicked
- Use CSS variables — never hardcode hex values
- No inline styles
- All templates extend `base.html`
- No new JavaScript libraries

## Definition of done
- [ ] On screens ≤ 600px, the desktop `.nav-links` is hidden and a hamburger
  button is visible in its place
- [ ] Clicking the hamburger opens the mobile menu (`.is-open` class added,
  `aria-expanded="true"` set on button)
- [ ] Logged-out users can see "Sign in" and "Get started" in the mobile menu
- [ ] Logged-in users can see "Add Expense", "Analytics", username, and "Logout"
  in the mobile menu
- [ ] Clicking a link inside the mobile menu closes the menu
- [ ] The hamburger icon animates to an ✕ when the menu is open
- [ ] On screens > 600px, the hamburger button is hidden and `.nav-links` is
  visible (desktop nav unchanged)
- [ ] Active-page link is highlighted in the mobile menu on the correct page
