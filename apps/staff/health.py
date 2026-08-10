"""
System health checks for the staff Settings → System page.

Only verifiable, real checks. Nothing here is decorative — each entry
exercises the actual subsystem (DB connection, cache round-trip, config
presence) and reports the true result.
"""
import os
import platform
import sys

import django
from django.conf import settings
from django.core.cache import cache
from django.db import connection


def _check(key, label, status, tone, detail=""):
    return {
        "key": key,
        "label": label,
        "status": status,
        "tone": tone,  # ok | warn | info
        "detail": detail,
    }


def _db_check():
    try:
        connection.ensure_connection()
        engine = settings.DATABASES["default"]["ENGINE"].rsplit(".", 1)[-1]
        return _check("database", "Database", "Connected", "ok", engine)
    except Exception:
        return _check("database", "Database", "Unreachable", "warn")


def _cache_check():
    try:
        cache.set("cx_health_check", "ok", 5)
        ok = cache.get("cx_health_check") == "ok"
        backend = settings.CACHES["default"]["BACKEND"].rsplit(".", 1)[-1]
        return _check(
            "cache", "Cache",
            "Operational" if ok else "Error",
            "ok" if ok else "warn",
            backend,
        )
    except Exception:
        return _check("cache", "Cache", "Error", "warn")


def _media_check():
    root = settings.MEDIA_ROOT
    exists = os.path.isdir(str(root))
    return _check(
        "media", "Media storage",
        "Present" if exists else "Missing",
        "ok" if exists else "warn",
        str(root),
    )


def _static_check():
    dirs = getattr(settings, "STATICFILES_DIRS", [])
    ok = all(os.path.isdir(str(d)) for d in dirs)
    return _check(
        "static", "Static assets",
        "Present" if ok else "Missing",
        "ok" if ok else "warn",
        "static/",
    )


def _payments_check():
    configured = bool(
        getattr(settings, "RAZORPAY_KEY_ID", "")
        and getattr(settings, "RAZORPAY_KEY_SECRET", "")
    )
    return _check(
        "payments", "Payment gateway",
        "Live" if configured else "Demo mode",
        "info",
        "Razorpay keys set" if configured
        else "Razorpay keys not configured — payments use demo mode.",
    )


def _email_check():
    backend = settings.EMAIL_BACKEND.rsplit(".", 1)[-1]
    return _check(
        "email", "Email backend",
        backend, "info",
        "Console backend logs emails in development; SMTP is configured via the environment.",
    )


def _whatsapp_check():
    configured = bool(
        getattr(settings, "TWILIO_ACCOUNT_SID", "")
        and getattr(settings, "TWILIO_AUTH_TOKEN", "")
    )
    return _check(
        "whatsapp", "WhatsApp (Twilio)",
        "Configured" if configured else "Not configured",
        "info",
        "WhatsApp notifications are disabled until Twilio keys are set.",
    )


def _debug_check():
    if settings.DEBUG:
        return _check(
            "debug", "Debug mode",
            "ON", "warn",
            "DEBUG is enabled — never run production with debug mode on.",
        )
    return _check("debug", "Debug mode", "OFF", "ok")


def _runtime_check():
    return _check(
        "runtime", "Runtime",
        f"Python {platform.python_version()} · Django {django.get_version()}",
        "info",
        f"{platform.system()} {platform.release()} · {settings.TIME_ZONE}",
    )


def run_health_checks():
    return [
        _db_check(),
        _cache_check(),
        _media_check(),
        _static_check(),
        _payments_check(),
        _email_check(),
        _whatsapp_check(),
        _debug_check(),
        _runtime_check(),
    ]
