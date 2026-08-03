---
number: 24
title: Updating Oxos Homepage
type: new-feature
parent: null
status: planned
releases: 1
created: 2026-08-02
---

# Release Plan: Updating Oxos Homepage

## Roadmap description
A public marketing homepage for the Oxos Platform at the root URL, replacing the current authenticated landing page so new visitors can explore the platform before signing in.

## Summary
This feature converts the existing static HTML mockup (`home-option-f.html`) into a proper Jinja2 template served at `/`, making it the public face of the Oxos Platform. The current `/` route renders the authenticated `platform.html` template — this change separates the public homepage from the authenticated application. The work includes template creation, CSS integration, routing updates, auth-flow adjustments, navigation link updates, and SEO metadata. All protected routes (`/platform`, `/profile`, `/roadmap`, `/features`) remain behind authentication.

## Releases

### Release 1 — Public Homepage & Routing (MVP)
- **Scope:**
  - Convert `home-option-f.html` mockup into a Jinja2 template (`home.html`) extending `base.html`
  - Move inline CSS into `static/css/home.css`, removing duplicates with existing styles
  - Replace mockup-only Lucide CDN and Google Fonts links with the existing ones in `base.html`
  - Update `/` route to serve the new homepage publicly (no auth required)
  - Keep `/platform` as the authenticated application route
  - Update redirect-after-login to `/platform`; logout redirect to `/`
  - Update "Get Started" button to link to `/login`
  - Update navigation links (logo, home buttons) to point to `/`
  - Add SEO metadata (title, meta description) to the homepage
  - Add a favicon to `static/` and reference it in `base.html`
  - Remove mockup-only `file://` URLs and unused inline JS
- **Spec slug:** home-page-routing
- **Spec arg:** `24.1 home-page-routing`
- **Depends on:** nothing
- **Risk:** medium

## Deferred / Out of scope
- Performance optimization (code splitting, lazy loading) — no code splitting infrastructure exists yet
- Detailed performance audit of the homepage bundle
- Removing `landing.html` template — kept for `/expense-home` route until explicitly removed

## Open questions
- Should the existing `landing.html` template be cleaned up after the homepage is in place?
- What favicon file format and size should be provided?
