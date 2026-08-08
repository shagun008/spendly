---
number: 24
title: Updating Oxos Homepage
type: new-feature
parent: null
status: captured
created: 2026-08-02 23:20 EST
source_folder: .claude/features/user-thoughts/Updating Oxos Homepage/
---

# Processed Thought: Updating Oxos Homepage

## Problem / Goal
Create a public-facing marketing/landing page for the Oxos Platform at `/`, replacing the current `/platform` default route so unauthenticated visitors see a showcase of platform capabilities before being prompted to log in.

## Who benefits
New visitors who haven't signed up yet — they get a clear entry point into the platform without needing to authenticate first.

## Success looks like
A public homepage at `/` that renders the existing mockup (`home-option-h.html`) as a proper Jinja2 template, with a "Get Started" button linking to `/login`, while all other routes (`/platform`, `/profile`, `/roadmap`, etc.) remain behind authentication.

## Constraints, risks, dependencies
- Must preserve existing auth flow and protected routes
- Must reuse existing layout/components (no isolated static serving)
- Must remove unused JS/CSS from the mockup
- Must update navigation links (logo, home buttons, logout redirect) that currently point to `/platform`
- The mockup file `static/mockups/home-option-h.html` must exist and be verified

## Implementation ideas / open questions
- Convert the static mockup HTML into a Jinja2 template extending `base.html`, integrating CSS/JS into the existing asset pipeline
- Update Flask routing so `/` serves the homepage publicly and `/platform` serves the authenticated app
- Update redirect-after-login and logout logic to point to the new homepage where appropriate
- Consider separating public vs. authenticated layouts for cleaner routing
- Remove duplicate CSS/JS already present in the project from the mockup

## Release pressure / deadlines
Not specified
