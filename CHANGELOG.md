# Changelog

## [4.2.1] — 2026-08-11

### Fixed

#### Rate limiting (infinite redirect loop)
- `apps/common/rate_limit.py` now counts **POST requests only**; it previously counted every request (including anonymous GETs) and redirected excess to `request.path`, causing an infinite `ERR_TOO_MANY_REDIRECTS` loop on `/users/login/` and `/bookings/book/`
- HTML clients get a redirect with a flash message + accurate retry-after; JSON clients get `429`; GET page loads pass through unlimited

#### Staff portal responsive overflow (verified in-browser)
- ≤768 px: toolbar children full-width, date-group inputs flexible, breadcrumb hidden (old selector referenced a nonexistent class), topbar edges `min-width: 0`
- ≤480 px: "Quick Add" collapses to an icon-only 40 px button
- `.sp-chart-grid > * { min-width: 0 }` (items overflowed ~3 px); `.sp-plan-card { overflow: hidden }` (rotated ribbon was clipped past viewport)

### Added
- `RateLimitTests` (3 tests) covering GET pass-through, POST limiting, and JSON `429`
- Headless-browser smoke verification (Edge/Chromium): 78 page/viewport checks pass at 320–1920 px with zero horizontal overflow, JS errors, or failed requests
- Static/media asset audit: every `{% static %}` resolves via staticfiles finders and every `{{ MEDIA_URL }}` reference resolves — 0 missing files

### Changed
- `CLIENT_READINESS_REPORT.md` updated: avg **9.6/10**, responsiveness / e2e / client-simulation scores raised after in-browser verification
- Test suite re-verified at **362 tests OK**; `manage.py check` clean

## [4.2.0] — 2026-08-11

### Added

#### Ch17 — Phase 7 Final Polish & Client Readiness
- `CLIENT_READINESS_REPORT.md`: final 19-section readiness report with per-area scores (avg 9.2/10) and READY verdict

### Fixed

#### CSS token repair (zero undefined `var()` references remain)
- `--cx-card-bg` → `--card-bg`; `--cx-space-7/9/14/18` → `--cx-space-8/10/16/20`; `--sp-surface-card` → `--sp-surface-2`; `--cx-text-md` → `--cx-text-base`; `--cx-surface-muted` → `--cx-surface-subtle`; `--cx-success-text`/`--cx-warning-text` → `--cx-success`/`--cx-warning`
- `--hero-scrim-*` defined locally with dark-mode overrides (hero overlay was transparent)

#### Booking & live sessions
- `Booking.session_remaining_minutes` now compares local (IST) time instead of UTC (`timezone.localtime()`); new `Booking.session_end_local` handles midnight-crossing sessions
- Staff serializer, live-session widget, and booking detail use `session_end_local`; dead `data-session-countdown` removed
- User dashboard "Sessions Played" no longer double-counts completed bookings

#### Templates & JS
- Cancel booking wired to real `bookings:booking_cancel` endpoint (was a stub) with `form[data-confirm]` dialog
- Hero/media paths use `{{ MEDIA_URL }}`; theme pre-paint handles `system` mode + `localStorage` try/catch
- `sr-only` unread badge text; `prefers-reduced-motion` respected in smooth-scroll; staff sidebar `aria-expanded`
- `search.js` excludes staff toolbar forms from auto-submit (fixes double submission on 7 staff list pages)
- `staff.js` live-sessions render recreates the empty state (fixes stale "No live sessions"); booking link uses server-rendered URL
- Razorpay templates: `amount` is numeric (was string) + `typeof Razorpay` guard; `theme.js`/`dashboard.js` localStorage guards

#### Settings & security
- Invalid `DJANGO_ENV` now raises `ImproperlyConfigured` instead of silently falling back to development
- Env-driven `CSRF_TRUSTED_ORIGINS` and extended `CORS_ALLOWED_ORIGINS`; `build.sh` defaults to `DJANGO_ENV=production`

### Changed
- Test suite re-verified at **359 tests OK** after Phase 7 changes; `manage.py check` clean; all touched templates render via test client *(superseded by the 4.2.1 entry — see above for the final 362-test state)*

## [4.1.0] — 2026-08-10

### Added

#### Ch16 — Staff Portal Phase 6
- **Notification center** (`staff:staff_notifications`): category/status filters, unread count, mark-read, read-all, pagination; `Notification.category` (system/booking/payment/membership/tournament) + migration `0003_notification_category`
- **Notification admin**: `category` added to `list_display` and `list_filter`
- **Staff management** (`staff:staff_staff_list`): staff listing with search, owner-only active/role toggles (HTTP 404 for non-owners), self-toggle protection, guarded redirect back to listing
- **Staff profile** (`staff:staff_profile`): name/phone/email form + password change using `update_session_auth_hash`
- **Settings hub** (`staff:staff_settings`): `SiteSettings`-backed general settings with tabbed sections (general/appearance/bookings/payments/notifications/email/security/system), health checks, WhatsApp/Twilio status, Razorpay status, email backend indicator
- **Topbar notification bell**: context processor (`staff_topbar`) supplying unread count + recent 8 notifications on every staff page
- **Business-event hooks**: membership activation and booking-confirm now emit staff notifications with `membership`/`payment` categories
- **3-mode theme** (dark/light/system) with `data-theme-mode` persistence; settings-nav scrollspy
- Phase 6 tests: notification center, staff management, profile, settings, bell, business-event notifications (incl. membership activation)

## [4.0.0] — 2026-08-04

### Added

#### Ch15 — Performance & Housekeeping
- **CMS context caching** (`apps/cms/cache.py`): the site-wide context processor now caches the fully-evaluated context dict under `cms_site_context` (TTL 300s), turning 8+ DB lookups per page render into a single cache read
- **Cache invalidation signals** (`apps/cms/signals.py`): wired to every CMS model's save/delete via `CmsConfig.ready()`, so admin edits show up immediately
- **Cache tests**: hit-rate (0 queries on 2nd call), save invalidation, delete invalidation (3 tests in `apps/cms/tests.py`)
- **Requirements restructure**: moved `apps/requirements/{base,production}.txt` → root `requirements/`, updated `.github/workflows/ci.yml` install paths

#### Ch13 — Owner Executive Dashboard
- `StaffDashboardService.get_executive_data()`: total/month revenue, MRR, ARPU, active customers, retention, console utilization, live-now count, 12-month revenue trend, top consoles, top customers, booking status breakdown
- `owner_required` decorator, `staff/executive/` route, superuser-only sidebar link
- `templates/staff/executive/dashboard.html` KPI cards + chart primitives
- Executive dashboard tests (owner access, staff forbidden, context keys, zero-safe retention)

#### Ch12 — Staff Live Sessions
- `Booking.checked_in_at` (+ `("checked_in", "Checked In")` status) and migration `0004_booking_checked_in_at_alter_booking_status`
- `Booking.live()` queryset + `session_remaining_minutes` property (midnight-crossing safe)
- `BookingService.check_in()` / `check_out()` / `get()`
- Staff `live_sessions` page + `live_sessions_data` JSON poll endpoint; dashboard live-sessions widget
- `static/js/staff.js` 30s polling with `data-live-*` attributes; live-dot/pulse/badge styling in `static/css/staff.css`
- 8 live-session tests in `apps/staff/tests.py`

#### Ch11 — Customer Portal
- Full customer portal in `apps/users`: profile, settings, notifications, and bookings pages with routes + templates (`users/portal_*`, `users/profile.html`, `users/settings.html`, `users/notifications.html`, `users/bookings.html`)
- Desktop rail + mobile bottom-bar navigation with active-state detection
- Dashboard integrated with the portal grid; real leaderboard rendered
- 12 portal tests in `apps/users/tests.py`

#### Ch10 — V4 Design Refresh
- V4 design system applied across all pages (tokens, typography, components, layouts, motion)
- New `static/css/layouts.css`, `motion.css`, `booking_preview.css`, `why_choose_us.css`; updated `booking.js` flow
- New `templates/layouts/` directory and reworked base/component templates

### Changed

- **Context processor**: `site_context` now delegates to `get_site_context_data()` (cached) instead of hitting the DB on every request
- **Repository layout**: requirements moved to root `requirements/` (`base.txt` + `production.txt`); root `requirements.txt` retained as a flattened dev reference
- **Tests**: suite grew to 253 tests (users 26, staff 20, bookings 22, cms 29, plus API/core/games/payments/etc.)

### Fixed

- Missing `from django.utils import timezone` import in `apps/bookings/models.py`
- Executive revenue trend now uses manual date arithmetic (`timedelta` has no `months=`)
- Executive monthly-revenue bars now scale relative to the peak month instead of a fixed ratio; live-session poll URL is resolved via `data-live-sessions-data-url` instead of a hardcoded path

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
