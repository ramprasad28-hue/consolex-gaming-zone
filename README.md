# CONSOLEX V4

A premium gaming lounge management system built with Django. Manage bookings, memberships, tournaments, and staff operations — all from a single platform.

## Features

- **Booking System** — Book gaming consoles (PS5, Xbox) by the hour with real-time slot availability
- **Customer Portal** — Profile, settings, notifications, and booking history for logged-in users
- **Staff Live Sessions** — Real-time check-in/check-out with a live "sessions in progress" board (30s polling)
- **Owner Executive Dashboard** — Revenue, MRR, ARPU, retention, utilization, and trend KPIs (superuser only)
- **Membership Plans** — Tiered subscriptions (Basic, Standard, Pro) with hourly discounts
- **Games Library** — Browse and filter games by category, rating, and popularity
- **Tournaments** — Create, register, and manage competitive gaming events
- **User Dashboard** — View booking history, stats, achievements, and membership status
- **Staff Portal** — Manage bookings, customers, games, memberships, and tournaments
- **Staff Notification Center** — Category/status-filtered inbox with unread badge and mark-read/read-all (staff bell)
- **Staff Management** — Search, activate/deactivate, and change roles for staff (owner-only toggles)
- **Staff Profile & Settings Hub** — Edit profile/password and manage site-wide settings with health checks
- **Analytics & Reports** — Visual dashboards with daily/weekly/monthly trends
- **Bulk Communication** — Send targeted messages to customer segments
- **CSV/XLS Import** — Import customer data via drag-and-drop
- **WhatsApp Integration** — Booking confirmations and customer support via Twilio
- **Razorpay Payments** — Secure online payments with demo mode for testing
- **Dark/Light Theme** — System-aware theme toggle with persistent preference
- **CMS with Caching** — Admin-editable site content served through a short-TTL cache with signal-based invalidation

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, Django 5.2.4 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | HTML, CSS (custom design system), JavaScript (vanilla) |
| Payments | Razorpay API |
| Messaging | Twilio WhatsApp API |
| Storage | WhiteNoise (static files), Django FileSystem (media) |

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/consolex.git
cd consolex

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed initial data (games, consoles, tournaments, CMS content)
python manage.py seed_data

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## Environment Variables

Create a `.env` file in the `config/` directory:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True

# Razorpay
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=
OWNER_WHATSAPP_TO=

# Redis (production only — shared cache across Gunicorn workers)
REDIS_URL=redis://127.0.0.1:6379/0
```

## Project Structure

```
consolex/
├── apps/
│   ├── api/            # REST API (DRF)
│   ├── bookings/       # Booking logic and views
│   ├── cms/            # Content management (hero, features, gallery, etc.)
│   ├── core/           # Homepage and shared views
│   ├── games/          # Games library
│   ├── memberships/    # Subscription plans
│   ├── notifications/  # User notifications
│   ├── payments/       # Razorpay integration
│   ├── staff/          # Staff/admin portal
│   ├── tournaments/    # Tournament management
│   └── users/          # Authentication, dashboard, and customer portal
├── config/
│   ├── settings/       # Django settings (base, dev, production)
│   ├── urls.py         # Root URL configuration
│   └── wsgi.py         # WSGI entry point
├── media/              # User-uploaded media
├── requirements/       # base.txt + production.txt (root requirements.txt is a flattened reference)
├── static/             # Static assets (CSS, JS, images)
│   ├── css/            # Design system and page styles
│   └── js/             # Client-side scripts
├── templates/          # Django templates
│   ├── components/     # Reusable UI components
│   ├── bookings/       # Booking pages
│   ├── games/          # Games library pages
│   ├── memberships/    # Membership pages
│   ├── pages/          # Homepage
│   ├── payments/       # Payment pages
│   ├── staff/          # Staff portal pages
│   ├── tournaments/    # Tournament pages
│   └── users/          # Auth and dashboard pages
├── manage.py
└── requirements.txt
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in environment
- [ ] Set a strong `SECRET_KEY` via environment variable
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up PostgreSQL database
- [ ] Provision Redis and set `REDIS_URL` (required: shared rate limiting + CMS cache across workers; startup fails fast without it)
- [ ] Configure WhiteNoise or CDN for static files
- [ ] Set up HTTPS (SSL certificate)
- [ ] Configure Razorpay and Twilio credentials
- [ ] Run `python manage.py collectstatic`
- [ ] Run `python manage.py migrate`
- [ ] Configure webhook endpoints for Razorpay

### Security Settings

Production settings include:
- HSTS (Strict-Transport-Security)
- Secure cookies (CSRF, Session)
- Content-Type nosniff
- XSS filter
- X-Frame-Options DENY
- Referrer-Policy same-origin
- SECURE_SSL_REDIRECT

## Tests

```bash
python manage.py test
```

253 tests covering API endpoints, services, models, and views. Run `python manage.py makemigrations --check --dry-run` to catch missing migrations.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Credits

- **Design**: Custom V3 design system with CSS custom properties
- **Icons**: Feather Icons
- **Fonts**: Inter (UI), Orbitron (display)
