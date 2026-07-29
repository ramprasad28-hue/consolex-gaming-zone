# Changelog

## [3.0.0] — 2026-07-29

### Added

#### Batch 8 — Production Readiness
- **SEO**: Canonical URLs, JSON-LD structured data, sitemap.xml, robots.txt, `noindex` on auth/staff/admin pages
- **Error Handling**: Custom 403.html template wired via `handler403` in urls.py
- **Accessibility**: Fixed `outline:none` → `:focus-visible` in 6 CSS rules; `aria-hidden="true"` on 25+ decorative SVGs; `scope="col"` on 8 table headers
- **Performance**: `media="all"` on all CSS links; `defer` on JavaScript; `loading="lazy"` on hero/game images
- **Security**: `SECURE_CROSS_ORIGIN_OPENER_POLICY` in production settings
- **Documentation**: README.md, CHANGELOG.md, LICENSE, CONTRIBUTING.md
- **Cleanup**: Removed orphaned `payment_page.css` (278 B, deprecated)

#### Batch 7 — Staff Portal & Analytics
- New `apps/staff/` app with full staff portal
- Staff dashboard with 8 stat widgets, quick actions, pending tasks, recent activity
- Booking management (list with search/filter/sort, detail with payment timeline)
- Customer management (list with avatar, detail with profile/bookings/payments)
- Game management (games + consoles)
- Tournament management (status filter, slot tracking)
- Membership management (plans + subscriptions)
- Analytics dashboard (CSS bar charts for daily bookings/revenue, console/bookings/tournament analytics)
- Reports (revenue, bookings, customers, memberships, tournaments with date filters)
- CSV/XLS Import workflow (5-step drag-and-drop)
- Bulk communication (audience chips, template selector, message compose, history)
- Settings page (business info, theme, account)
- Staff CSS system (`sp-*` class prefix) and staff JS (sidebar, dropzone, chips)

#### Batch 6 — Games, Tournaments & Community
- Games Library (`apps/games/views.py`, `apps/games/urls.py`)
- Games listing with search, category/badge/sort filters, pagination
- Game detail page with hero, metadata, similar games, CTA
- Tournaments (`apps/tournaments/views.py`, `apps/tournaments/urls.py`)
- Tournament listing with search, status filter, sort
- Tournament detail with registration, progress bar, info grid
- Membership widget on dashboard (`dx-membership-card`)
- Community sidebar with leaderboard, gaming progress, achievements
- Unified search JS (`static/js/search.js`)
- Navbar links for Games and Tournaments
- CSS: `games_page.css`, `tournaments_page.css`

#### Batch 5 — CMS & Production Polish
- Django CMS app (`apps/cms/`) with SiteSettings, ContentBlock, Announcement models
- Homepage sections driven by CMS content (hero, features, stats, gallery, testimonials, FAQ, pricing, booking CTA, social CTA)
- Sibling tests for the `apps.cms` app
- Feedback widget (static placeholder)
- Team member rendering on About Me page
- Seeder command (`python manage.py seed_data`) for CMS content, games, consoles, tournaments
- 404 and 500 error pages
- V3 CSS refresh applied to all components

### Changed

- **Performance**: Google Fonts now loaded with `display=swap` query parameter
- **CSS**: All files use `--cx-*` design tokens; no hardcoded colors
- **Security**: Production settings enforce CSRF/SESSION cookie secure, HSTS, nosniff, XSS filter

### Fixed

- **Accessibility**: Skip link targets `#main-content` (exists in base.html); `aria-hidden` on decorative SVGs; `scope="col"` on table headers; `:focus-visible` outline patterns
- **Error Handling**: URL configuration now includes `handler404`, `handler403`, `handler500`
- **SEO**: All templates have unique page titles; auth/staff/admin pages use `noindex`

## [2.0.0] — 2026-06

### Added
- User authentication (login, register, password reset)
- User dashboard with booking history, stats, activity timeline
- Razorpay payment integration
- WhatsApp notification system via Twilio
- Dark/Light theme toggle with system preference detection
- Announcement bar
- Floating WhatsApp support button

## [1.0.0] — 2026-05

### Added
- Initial CONSOLEX platform
- Django project setup with modular app structure
- Booking system with console selection, date/time picker
- Membership plans (Basic, Standard, Pro)
- Responsive design with mobile navigation
- V1 CSS with gaming-themed UI
