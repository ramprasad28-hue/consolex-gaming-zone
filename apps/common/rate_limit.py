# apps/common/rate_limit.py
"""
Lightweight session-based rate limiting for Django views.
No third-party packages required — uses Django's cache framework.
"""
import time
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse


def rate_limit(key_prefix, max_requests=10, window=60):
    """
    Decorator that limits a view to `max_requests` per `window` seconds
    per unique client (identified by IP + session key).

    Usage:
        @rate_limit("login", max_requests=5, window=60)
        def my_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            ident = request.META.get("REMOTE_ADDR", "unknown")
            session_key = request.session.session_key or ""
            cache_key = f"rl:{key_prefix}:{ident}:{session_key}"

            requests = cache.get(cache_key, [])
            now = time.time()

            # Prune old entries outside the window.
            requests = [t for t in requests if now - t < window]

            if len(requests) >= max_requests:
                retry_after = int(window - (now - requests[0]))
                if request.headers.get("Accept") == "application/json":
                    return JsonResponse(
                        {"success": False, "error": "Too many requests. Please try again later."},
                        status=429,
                    )
                from django.contrib import messages
                from django.shortcuts import redirect
                messages.error(request, f"Too many requests. Please wait {retry_after} seconds.")
                return redirect(request.path)

            requests.append(now)
            cache.set(cache_key, requests, window + 10)

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
