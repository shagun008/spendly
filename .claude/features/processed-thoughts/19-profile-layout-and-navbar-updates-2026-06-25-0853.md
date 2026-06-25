---
number: 19
title: Profile Layout and Navbar Updates
type: new-feature
parent: null
status: captured
created: 2026-06-25 08:53 EST
source_folder: .claude/features/user-thoughts/User Profile Page Updates/
---

# Processed Thought: Profile Layout and Navbar Updates

## Problem / Goal
The Profile page layout doesn't take advantage of wider screens (Profile Card and Analytics Dashboard are not side-by-side on desktop), and the navbar still shows the user's name as a text link with a separate "Log Out" text item, which clutters the navigation and doesn't follow modern UX patterns. The goal is to make the profile page responsive with a side-by-side layout on desktop, and modernize the navbar by replacing the username with a user icon that adapts to both desktop and mobile contexts.

## Who benefits
All logged-in users — better use of screen real estate on desktop, cleaner and more intuitive navbar navigation, and a consistent user icon across breakpoints.

## Success looks like
**Responsive Profile Layout:** Profile Card and Analytics Dashboard display side-by-side on desktop and stacked on mobile.

**Navbar — Desktop (>600px):**
- Username text link is replaced by a user/person icon
- Clicking the icon opens a dropdown with "My Profile" and "Log Out"
- The standalone "Logout" text link is removed from the desktop nav bar
- All existing routes, permissions, and behaviours are preserved

**Navbar — Mobile (≤600px):**
- When logged in, the hamburger icon (☰) is replaced by a user/person icon
- Tapping the user icon opens the same mobile slide-down menu as the hamburger did
- Inside the mobile menu: the username text link is replaced by "My Profile", and "Logout" is relabelled to "Log Out"
- No structural changes to the mobile menu — it still contains Features, Roadmap, My Profile, Log Out
- When logged out, the hamburger icon remains unchanged

| Element | Desktop (>600px) | Mobile (≤600px) |
|---------|------------------|------------------|
| Hamburger icon (☰) | Not shown | → Replaced by user icon when logged in |
| Username text (in nav) | → Replaced by user icon + dropdown | → Replaced by "My Profile" link (in mobile menu) |
| User icon + dropdown | New — shows "My Profile" / "Log Out" | Not applicable (mobile menu serves this role) |
| Standalone "Logout" text (in desktop nav) | **Removed** | N/A — doesn't exist on mobile today |
| "My Profile" link | Inside the dropdown | Inside the mobile menu |
| "Log Out" link | Inside the dropdown | Inside the mobile menu |

## Constraints, risks, dependencies
Must preserve all existing routes, permissions, and behaviours — no functional regressions. The user icon must be consistent across both breakpoints (Lucide `user` icon) but trigger the appropriate interaction pattern per viewport (dropdown on desktop, mobile menu slide-down on mobile). The responsive layout change must not break the existing Profile Card or Analytics Dashboard content. When logged out, the hamburger icon must remain unchanged on mobile.

## Implementation ideas / open questions
1. **Responsive Layout:** Use CSS flexbox/grid — side-by-side above 900px breakpoint, stacked below.
2. **Desktop User Dropdown:** Lucide `user` icon in the navbar, JS toggle for dropdown visibility, click-outside-to-close.
3. **Mobile User Icon:** Conditionally swap the hamburger icon for a Lucide `user` icon when a user is logged in, keeping all existing mobile menu toggle logic intact.
4. **Label Updates:** Change "Logout" → "Log Out" and username text → "My Profile" in the mobile menu for consistency with the desktop dropdown.
5. **Navbar Cleanup:** Remove the standalone "Logout" nav item from desktop nav; the dropdown's "Log Out" replaces it. On mobile, no structural removal needed — only relabelling.
6. Should the desktop dropdown also include "Change Password" or other profile actions?
7. Should the desktop dropdown be a `<details>/<summary>` for no-JS fallback, or purely JS-driven?

## Release pressure / deadlines
None specified.
