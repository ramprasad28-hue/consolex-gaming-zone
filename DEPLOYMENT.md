# ConsoleX Production Deployment Guide

## 1. Architecture

ConsoleX is a Django-based gaming lounge management platform designed to run on containerized or cloud hosting platforms like Railway, Render, or AWS.

### Deployment Stack

\\\
┌─────────────────────────────────────────────────────────┐
│ Browser (HTTPS)                                         │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ HTTPS Reverse Proxy / Load Balancer                     │
│ (Platform-provided, Nginx, or Cloudflare)              │
└────────────────┬────────────────────────────────────────┘
                 │ (HTTP, local network)
┌────────────────▼────────────────────────────────────────┐
│ Gunicorn WSGI Application Server                        │
│ (3-4 worker processes recommended)                      │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────┴────────┬──────────────┐
        │                 │              │
┌───────▼────────┐ ┌─────▼─────┐ ┌─────▼──────┐
│  PostgreSQL    │ │   Redis   │ │ Razorpay   │
│  Database      │ │   Cache   │ │ API        │
└────────────────┘ └───────────┘ │            │
                                  │ Twilio     │
                                  │ WhatsApp   │
                                  │            │
                                  │ SMTP Email │
                                  └────────────┘
\\\

### Key Components

- **Django 6.0.6** — Web framework
- **Gunicorn 26.0.0** — WSGI application server
- **PostgreSQL** — Primary production database
- **Redis 8.1.0** — Shared cache for rate limiting, DRF throttles, CMS
- **WhiteNoise 6.12.0** — Serves static files (CSS, JS, images)
- **Razorpay** — Payment processing
- **Twilio** — WhatsApp notifications
- **SMTP** — Email delivery

### Static Files

- WhiteNoise handles static file serving directly from Django
- 213 static assets are collected and served with Gzip compression
- For high-traffic production, place a CDN (Cloudflare, CloudFront) in front

### Media Files (User Uploads)

**IMPORTANT:** Media files are currently stored on the filesystem at \MEDIA_ROOT\.

On platforms with **ephemeral filesystems** (Railway, Render), newly uploaded images may be lost after redeploy or pod restart.

**Production Decision Required:** Before launch, verify with your hosting platform:
- [ ] Does the platform provide persistent storage for uploaded files?
- [ ] If not, implement S3/Cloudinary storage backend

See Section 15 for more details.

---

## 2. Prerequisites

Before deploying ConsoleX to production, ensure:

- [ ] **Git** — To clone the repository
- [ ] **Python 3.12** — Must match project requirements
- [ ] **PostgreSQL 12+** — Database server (or hosted PostgreSQL service)
- [ ] **Redis 6.0+** — Cache server (or hosted Redis service)
- [ ] **Hosting Platform Account** — Railway, Render, AWS, Heroku, or similar
- [ ] **Domain & DNS** — For ALLOWED_HOSTS configuration
- [ ] **HTTPS/TLS Certificate** — (Usually provided by platform or Let's Encrypt)
- [ ] **Credentials** — Razorpay (live), Twilio, SMTP email provider
- [ ] **Environment Variable Management** — Platform-specific (secrets manager, env file, dashboard)

---

## 3. Environment Variables

Every production deployment requires the following environment variables. Copy and customize \.env.example\ for your environment.

| Variable | Required | Secret | Purpose |
|----------|----------|--------|---------|
| \DJANGO_ENV\ | Yes | No | Set to \production\ for production deployments |
| \SECRET_KEY\ | Yes | **YES** | Django session/CSRF secret; must be 50+ random characters |
| \DEBUG\ | No | No | Must be \False\ in production (hardcoded; for reference only) |
| \ALLOWED_HOSTS\ | Yes | No | Comma-separated domains (e.g., \consolex.in,www.consolex.in\) |
| \DB_NAME\ | Yes | No | PostgreSQL database name |
| \DB_USER\ | Yes | No | PostgreSQL username |
| \DB_PASSWORD\ | Yes | **YES** | PostgreSQL password |
| \DB_HOST\ | Yes | No | PostgreSQL hostname (e.g., RDS endpoint) |
| \DB_PORT\ | No | No | PostgreSQL port (default: 5432) |
| \REDIS_URL\ | Yes | **YES** | Redis connection URL with credentials (e.g., \ediss://default:password@host:6379\) |
| \RAZORPAY_KEY_ID\ | Yes | **YES** | Razorpay API public key (\zp_live_*\ for production) |
| \RAZORPAY_KEY_SECRET\ | Yes | **YES** | Razorpay API secret key |
| \RAZORPAY_WEBHOOK_SECRET\ | Yes | **YES** | Razorpay webhook signature secret |
| \TWILIO_ACCOUNT_SID\ | Yes | **YES** | Twilio account SID |
| \TWILIO_AUTH_TOKEN\ | Yes | **YES** | Twilio authentication token |
| \TWILIO_WHATSAPP_FROM\ | Yes | No | Twilio WhatsApp sender number (e.g., \whatsapp:+14155238886\) |
| \OWNER_WHATSAPP_TO\ | Yes | No | Owner's WhatsApp recipient number |
| \EMAIL_HOST\ | No | No | SMTP server hostname (default: \smtp.gmail.com\) |
| \EMAIL_PORT\ | No | No | SMTP server port (default: 587) |
| \EMAIL_HOST_USER\ | No | No | SMTP username or email address |
| \EMAIL_HOST_PASSWORD\ | No | **YES** | SMTP password (app-specific password if using Gmail) |
| \DEFAULT_FROM_EMAIL\ | No | No | Sender email address for outgoing emails |
| \CORS_ALLOWED_ORIGINS\ | No | No | Comma-separated CORS origins (e.g., \https://admin.consolex.in\) |
| \CSRF_TRUSTED_ORIGINS\ | No | No | Comma-separated CSRF-trusted origins (must be HTTPS) |

**Notes:**
- **Email variables are optional** — If not configured, email features will not send, but the application will remain functional.
- **CORS/CSRF variables are optional** — Apply only if you need cross-origin API requests or CSRF exemptions.
- **SECRET_KEY must be unique and cryptographically random** — Never reuse keys between environments.
- **Razorpay TEST credentials** should be used for staging; LIVE credentials only for production.

---

## 4. Generate SECRET_KEY

To generate a cryptographically secure \SECRET_KEY\:

### Python (Recommended)

\\\ash
python -c "import secrets; print(secrets.token_urlsafe(50))"
\\\

Output:
\\\
LbVz3pLzK8vX9mJ2n4oQ5rS6tU7vW8xY9zAbCdEfGhIjKlMnOpQrStUvWxYzAb
\\\

### Django (Alternative)

\\\ash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
\\\

**Copy the generated string and set it in your platform's environment variables.**

Never share the SECRET_KEY. Treat it like a password.

---

## 5. PostgreSQL Setup

### Managed Service (Recommended for Production)

Most production deployments use a managed PostgreSQL service (AWS RDS, Railway, Render, Heroku Postgres, etc.).

**Typical Setup:**
1. Create a managed PostgreSQL instance through your platform's dashboard
2. Obtain connection credentials:
   - **Host** (e.g., \consolex-prod.xxxxx.us-east-1.rds.amazonaws.com\)
   - **Port** (typically 5432)
   - **Database name** (e.g., \consolex_prod\)
   - **User** (e.g., \consolex_admin\)
   - **Password** (generated during setup)

3. Set environment variables:

\\\ash
DB_HOST=consolex-prod.xxxxx.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=consolex_prod
DB_USER=consolex_admin
DB_PASSWORD=your-generated-password
\\\

### Self-Hosted PostgreSQL (Advanced)

If hosting PostgreSQL yourself:

\\\ash
# Create database
createdb -U postgres consolex_prod

# Create application user
createuser -U postgres -P consolex_admin
# (You will be prompted for a password)

# Grant privileges
psql -U postgres -d consolex_prod -c "GRANT ALL PRIVILEGES ON DATABASE consolex_prod TO consolex_admin;"

# Verify connection
psql -h localhost -U consolex_admin -d consolex_prod -c "SELECT 1;"
\\\

---

## 6. Redis Setup

### Managed Service (Recommended)

Most platforms provide managed Redis (Railway Redis, Render Redis, AWS ElastiCache, Redis Cloud, etc.).

**Typical Setup:**
1. Create a managed Redis instance
2. Obtain connection URL (often provided directly):

\\\
rediss://default:your-password@your-redis-host.c12345.ng.0001.use1.cache.amazonaws.com:6379/0
\\\

3. Set environment variable:

\\\ash
REDIS_URL=rediss://default:your-password@your-redis-host.c12345.ng.0001.use1.cache.amazonaws.com:6379/0
\\\

**Note:** \ediss://\ (with double-s) uses TLS encryption.

### Self-Hosted Redis (Advanced)

\\\ash
# Install Redis
apt-get install redis-server  # Ubuntu/Debian
brew install redis             # macOS

# Start Redis
redis-server

# Test connection
redis-cli ping
# Output: PONG

# For external access, configure redis.conf and set REDIS_URL:
REDIS_URL=redis://your-redis-host:6379/0
\\\

### Health Check

ConsoleX includes a health-check page at \/staff/settings/\ that verifies Redis connectivity. After deployment, visit this page and confirm the Redis cache shows as operational.

---

## 7. Razorpay Configuration

### Create Razorpay Account

1. Sign up at [Razorpay Dashboard](https://dashboard.razorpay.com/)
2. Complete identity verification
3. In **Settings → API Keys**, obtain:
   - **Key ID** (public key)
   - **Key Secret** (private key)

### Test vs Live Credentials

- **Testing:** Use \zp_test_*\ credentials
  - Test payments do not charge real cards
  - Useful for staging/CI environments

- **Production:** Use \zp_live_*\ credentials
  - Real payments are processed
  - Only set in production environment

### Configuration

Set environment variables:

\\\ash
RAZORPAY_KEY_ID=rzp_live_your_actual_key_id
RAZORPAY_KEY_SECRET=your_actual_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
\\\

### Webhook Setup

1. In Razorpay Dashboard → Settings → Webhooks, add:
   - **URL:** \https://your-domain.com/payments/webhook/\
   - **Events:** \payment.captured\, \payment.failed\

2. Copy the webhook secret and set \RAZORPAY_WEBHOOK_SECRET\

3. Verify webhook signature is validated in \pps/payments/views.py\

---

## 8. Twilio Configuration

### Create Twilio Account

1. Sign up at [Twilio Console](https://www.twilio.com/console)
2. Verify your phone number
3. Create a WhatsApp-enabled Twilio number or use an existing one

### Get Credentials

In **Account → API Keys & Tokens**, obtain:
- **Account SID**
- **Auth Token**
- **WhatsApp Number** (sender)

### Configuration

Set environment variables:

\\\ash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
OWNER_WHATSAPP_TO=whatsapp:+91xxxxxxxxxx
\\\

Replace:
- \+14155238886\ with your Twilio WhatsApp number
- \+91xxxxxxxxxx\ with the owner's WhatsApp number (recipient)

**Note:** WhatsApp notifications are sent when a booking is confirmed. If credentials are missing, notifications are silently skipped.

---

## 9. Email Configuration

### Gmail (Recommended for Testing/Small Deployments)

1. Enable 2FA on your Gmail account
2. Create an [App Password](https://myaccount.google.com/apppasswords)
3. Copy the generated 16-character password

Set environment variables:

\\\ash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=CONSOLEX <noreply@your-domain.com>
\\\

### SendGrid / Mailgun / Other SMTP Providers

Follow your provider's documentation to obtain:
- SMTP hostname
- SMTP port (usually 587 or 465)
- Username / API key
- Password

Example (SendGrid):

\\\ash
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.your_sendgrid_api_key
DEFAULT_FROM_EMAIL=noreply@your-domain.com
\\\

**Note:** Email is optional. If not configured, the application remains functional; email features simply won't send.

---

## 10. Build Process

The build process is defined in \uild.sh\ and executed by your deployment platform (Railway, Render, etc.).

### Build Steps

\\\ash
#!/usr/bin/env bash
set -e

# Force production settings
export DJANGO_ENV=""

echo "▶ Installing dependencies..."
pip install -r requirements/base.txt
pip install -r requirements/production.txt

echo "▶ Collecting static files..."
python manage.py collectstatic --noinput

echo "▶ Running migrations..."
python manage.py migrate --noinput

echo "✅ Build complete."
\\\

### What Happens

1. **Dependency Installation**
   - \equirements/base.txt\ — Core packages (Django, DRF, etc.)
   - \equirements/production.txt\ — Production-only packages (psycopg2, redis)

2. **Static Files**
   - Collects 213 static assets from \static/\ → \staticfiles/\
   - WhiteNoise compresses and serves them

3. **Database Migrations**
   - Runs \python manage.py migrate\ against the production PostgreSQL database
   - Creates/updates required tables

### Platform Integration

Most platforms auto-detect and run \uild.sh\:

- **Railway:** Runs \uild.sh\ during build phase
- **Render:** Runs build command if specified in \ender.yaml\ or \Procfile\
- **Heroku:** Uses \Procfile\ (can invoke \uild.sh\)

---

## 11. Gunicorn

### WSGI Application Entry Point

ConsoleX's WSGI application is defined in \config/wsgi.py\:

\\\python
application = get_wsgi_application()
\\\

### Start Gunicorn

`ash
gunicorn config.wsgi:application
`

### Production Configuration

For production, use multiple workers and bind to port 8000:

`ash
gunicorn \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --worker-class sync \
  --max-requests 1000 \
  --timeout 60 \
  config.wsgi:application
`

### Platform-Specific

- **Railway:** Detects Gunicorn automatically; specify start command in dashboard or \Procfile\
- **Render:** Specify build command and start command in \ender.yaml\ or dashboard
- **Heroku:** Specify in \Procfile\

Example \Procfile\:

`
web: gunicorn config.wsgi:application
`

---

## 12. Database Migrations

### Before Deployment

Verify no pending migrations:

`ash
python manage.py makemigrations --check --dry-run
# Output: No changes detected
`

### During Deployment

The build process automatically runs:

`ash
python manage.py migrate --noinput
`

This:
- Connects to the production PostgreSQL database
- Applies all pending migrations
- Creates/updates database schema
- Runs only once (idempotent)

### Manual Migration (If Needed)

To manually run migrations:

`ash
# After SSH-ing into production environment
python manage.py migrate --settings=config.settings.production

# Check migration status
python manage.py showmigrations --settings=config.settings.production
`

---

## 13. Static Files

### Collection

The build process automatically collects static files:

`ash
python manage.py collectstatic --noinput
`

This:
- Gathers CSS, JS, images from \static/\ directory
- Minifies/compresses with WhiteNoise
- Outputs to \staticfiles/\ directory

### Serving

WhiteNoise middleware serves static files directly:

- **In development:** Django serves from \STATICFILES_DIRS\
- **In production:** WhiteNoise serves compressed assets from \STATIC_ROOT\

### Performance

- **Gzip compression** — Enabled automatically
- **Cache headers** — Set by WhiteNoise (1 year)
- **CDN** — Optional; place in front of Gunicorn for further optimization

---

## 14. Health Checks

### Admin Health Check Page

ConsoleX includes a built-in health check accessible at:

`
https://your-domain.com/staff/settings/
`

(Requires staff login)

This page verifies:
- ✓ Database connectivity
- ✓ Redis cache connectivity
- ✓ Static files present
- ✓ Media storage accessible
- ✓ Razorpay configuration
- ✓ Email backend
- ✓ WhatsApp (Twilio) configuration
- ✓ Debug mode (must be OFF)
- ✓ Runtime (Python version, Django version, timezone)

### Application Health Check

Before each deploy, verify:

`ash
python manage.py check
# Output: System check identified no issues (0 silenced).

python manage.py check --deploy --settings=config.settings.production
# Output: System check identified no issues (0 silenced).
`

### Basic HTTP Health

Add a simple health endpoint for load balancers:

`ash
curl https://your-domain.com/
# Should return 200 OK with homepage HTML
`

---

## 15. Media Storage Warning ⚠️

**IMPORTANT:** Media uploads are currently stored on the filesystem.

### Current Behavior

- User uploads (game images, console photos, etc.) saved to \MEDIA_ROOT\ on disk
- Served by WhiteNoise at \/media/\ URL path

### Platform Compatibility

**Ephemeral Filesystems** (Railway, Render, AWS Lambda):
- ❌ Uploaded files may be lost after pod restart/redeploy
- ❌ Not suitable for production without workaround

**Persistent Filesystems** (AWS ECS with EBS, self-hosted):
- ✓ Files persist across restarts
- ✓ Safe for production

### Production Decision

**Before launch, determine:**

1. **Does your platform persist the application filesystem?**
   - Contact support or check documentation
   - Test by uploading a file and restarting the app

2. **If NO persistent filesystem:**
   - Implement S3/Cloudinary storage backend (recommended for future roadmap)
   - Contact us for guidance

3. **If YES persistent filesystem:**
   - Document the persistence guarantee
   - Current setup is production-safe

### Future: S3/Cloudinary Integration

To migrate to cloud storage:

1. Install \django-storages\
2. Configure AWS S3 or Cloudinary credentials
3. Update \MEDIA_ROOT\ and \MEDIA_STORAGE\ settings
4. Migrate existing media to cloud storage

This is outside the scope of current deployment but available if needed.

---

## 16. Deployment Checklist

### PRE-DEPLOYMENT

#### Code & Tests

- [ ] Latest code pushed to production branch
- [ ] All tests pass: \python manage.py test --parallel 4\
- [ ] Django check passes: \python manage.py check\
- [ ] Migrations check passes: \python manage.py makemigrations --check --dry-run\
- [ ] Static files collect successfully: \python manage.py collectstatic --noinput\

#### Environment Variables

- [ ] \DJANGO_ENV=production\
- [ ] \SECRET_KEY\ set to secure 50+ character random string
- [ ] \ALLOWED_HOSTS\ set to your production domains
- [ ] \DB_NAME\, \DB_USER\, \DB_PASSWORD\, \DB_HOST\, \DB_PORT\ configured
- [ ] \REDIS_URL\ configured and verified
- [ ] \RAZORPAY_KEY_ID\, \RAZORPAY_KEY_SECRET\, \RAZORPAY_WEBHOOK_SECRET\ set (LIVE keys)
- [ ] \TWILIO_ACCOUNT_SID\, \TWILIO_AUTH_TOKEN\ set
- [ ] \TWILIO_WHATSAPP_FROM\, \OWNER_WHATSAPP_TO\ configured
- [ ] \EMAIL_HOST_USER\, \EMAIL_HOST_PASSWORD\ set (if email enabled)
- [ ] \CORS_ALLOWED_ORIGINS\, \CSRF_TRUSTED_ORIGINS\ configured if needed

#### Infrastructure

- [ ] PostgreSQL instance created and accessible
- [ ] Redis instance created and accessible
- [ ] Domain DNS configured to platform
- [ ] HTTPS/SSL certificate provisioned
- [ ] Platform configured to run build.sh

### DEPLOYMENT

- [ ] Trigger deployment on platform
- [ ] Build phase completes successfully (logs visible)
- [ ] Dependencies install
- [ ] Static files collect
- [ ] Migrations run
- [ ] Application starts (Gunicorn listening on port 8000)

### POST-DEPLOYMENT

#### Immediate Verification (5 minutes after deploy)

- [ ] Homepage loads: \curl https://your-domain.com/\
- [ ] Login page accessible
- [ ] Staff login works
- [ ] Health check page accessible and passing

#### Functional Testing (30 minutes after deploy)

- [ ] User registration works
- [ ] User login works
- [ ] Booking creation works
- [ ] Availability check works
- [ ] Payment page loads
- [ ] Test payment flow (using Razorpay TEST credentials if still available)
- [ ] Admin panel accessible

#### Integration Testing

- [ ] Razorpay webhook configured and tested
- [ ] Twilio WhatsApp notification sent (manually trigger booking)
- [ ] Email notification sent (check SMTP)
- [ ] Static assets load (CSS, JS, images visible)
- [ ] Media uploads work (upload game image, verify in UI)

#### Logging & Monitoring

- [ ] Platform logs show no errors
- [ ] Database queries executing normally
- [ ] Redis cache working (check admin health page)
- [ ] No SECRET_KEY or credentials in logs

#### Security Verification

- [ ] HTTPS enforced (http://domain redirects to https://)
- [ ] Security headers present (check with browser dev tools):
  - Strict-Transport-Security
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
- [ ] DEBUG=False confirmed
- [ ] Admin panel not exposed publicly

---

## 17. Rollback Procedure

If deployment fails or causes issues:

### Quick Rollback (Within Minutes)

1. **Identify the problem:**
   - Check platform logs for errors
   - Check application health endpoint
   - Check database connectivity

2. **Immediate rollback:**

   `ash
   # Revert to previous deployment on your platform
   # (Platform-specific; e.g., Railway: Use "Rollback" button in dashboard)
   `

3. **Verify previous version:**

   `ash
   curl https://your-domain.com/
   # Should load (from previous deployment)
   `

### Rollback Considerations

**DO NOT blindly reverse database migrations.**

- Migrations move forward, not backward
- Incompatible reversal can corrupt data
- If migration caused issues:
  1. Inspect the migration file
  2. Determine if it's reversible (\def reverse(apps, schema_editor):\)
  3. Contact support if unsure

### Safe Rollback Approach

1. Identify the deployment that broke production
2. Revert to the previous application version (via platform's deployment history)
3. Keep the new database schema (do NOT reverse migrations)
4. After rollback, investigate the issue offline
5. Once fixed, redeploy

### Prevention

- Always deploy to staging/testing first
- Verify all checks pass before production deployment
- Maintain database backups before major deployments

---

## 18. Staging vs Production

### Credential Separation

**CRITICAL:** Never mix Razorpay TEST and LIVE credentials.

| Environment | Razorpay Keys | Twilio Keys | Email | Database |
|---|---|---|---|---|
| **Staging** | \zp_test_*\ | Test account | Sandbox SMTP | Staging DB |
| **Production** | \zp_live_*\ | Production account | Real SMTP | Production DB |

### Test Payment Flow

**Staging:**
1. Use Razorpay TEST credentials
2. Test cards: \4111 1111 1111 1111\ (Visa), etc.
3. Payments do not charge
4. Useful for QA before go-live

**Production:**
1. Set Razorpay LIVE credentials
2. Real cards accepted
3. Real charges processed
4. Monitor webhook for payment confirmations

---

## 19. Troubleshooting

### Common Issues

#### Database Connection Refused

`
django.db.utils.OperationalError: could not connect to server
`

**Solution:**
- Verify \DB_HOST\, \DB_PORT\ are correct
- Confirm database credentials
- Check firewall/security groups allow inbound connections
- Test with: \psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME>\

#### Redis Connection Failed

`
redis.exceptions.ConnectionError: Error 111 connecting to host
`

**Solution:**
- Verify \REDIS_URL\ is correct
- Confirm Redis instance is running
- Check firewall/security groups allow inbound connections
- Test with: \edis-cli -u <REDIS_URL> ping\

#### SECRET_KEY Missing

`
RuntimeError: SECRET_KEY environment variable is required
`

**Solution:**
- Set \SECRET_KEY\ in environment variables
- Verify it's not empty
- Ensure it's 50+ characters long

#### ALLOWED_HOSTS Error

`
DisallowedHost: Invalid HTTP_HOST header
`

**Solution:**
- Add your domain to \ALLOWED_HOSTS\ environment variable
- Example: \ALLOWED_HOSTS=consolex.in,www.consolex.in\

#### Static Files Not Loading

`
404 errors for CSS/JS/images
`

**Solution:**
- Verify \python manage.py collectstatic --noinput\ ran successfully during build
- Check that \staticfiles/\ directory exists and contains files
- Verify \STATIC_ROOT\ and \STATIC_URL\ are configured correctly

#### Migrations Fail

`
django.db.utils.ProgrammingError: relation does not exist
`

**Solution:**
- Run migrations: \python manage.py migrate\
- Verify database connection
- Check migration files for errors

---

## 20. Support & Resources

- **Project Repo:** [ConsoleX GitHub]
- **Django Docs:** https://docs.djangoproject.com/
- **Gunicorn Docs:** https://gunicorn.org/
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **Redis Docs:** https://redis.io/documentation
- **Razorpay Docs:** https://razorpay.com/docs/
- **Twilio Docs:** https://www.twilio.com/docs/

---

**Version:** 1.0  
**Last Updated:** August 2026  
**For Questions:** Contact deployment team

