"""
Site-wide CMS context caching.

The site context processor hits 8+ tables on every page render. This module
caches the fully-evaluated context dict for a short TTL and exposes a signal
handler that invalidates it whenever any CMS model changes (e.g. admin edits).
"""
from django.core.cache import cache

from apps.cms import models as cms_models

CACHE_KEY = "cms_site_context"
CACHE_TTL = 300  # seconds


def _load_site_context_data():
    """Load + evaluate the CMS context (querysets → lists) for safe caching."""
    site = cms_models.SiteSettings.objects.get_solo()

    blocks = dict(
        cms_models.ContentBlock.objects.values_list("key", "value")
    )
    return {
        "site": site,
        "cb": blocks,
        "cms_announcement": cms_models.Announcement.objects.filter(
            is_active=True
        ).first(),
        "cms_testimonials": list(cms_models.Testimonial.objects.filter(is_active=True)),
        "cms_stats": list(cms_models.SiteStat.objects.all()),
        "cms_features": list(cms_models.Feature.objects.filter(section="features")),
        "cms_why_choose": list(cms_models.Feature.objects.filter(section="why_choose")),
        "cms_booking_steps": list(cms_models.Feature.objects.filter(section="booking_steps")),
        "cms_faqs": list(cms_models.FAQItem.objects.all()),
        "faq_categories": cms_models.FAQItem.CATEGORY_CHOICES,
        "cms_gallery": list(cms_models.GalleryItem.objects.all()),
    }


def get_site_context_data():
    """Return the CMS context dict, using cache when available."""
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    data = _load_site_context_data()
    cache.set(CACHE_KEY, data, CACHE_TTL)
    return data


def invalidate_site_context_cache(sender=None, instance=None, **kwargs):
    """Signal handler — drop the cached context after any CMS change."""
    cache.delete(CACHE_KEY)


CMS_MODELS = [
    cms_models.SiteSettings,
    cms_models.ContentBlock,
    cms_models.Announcement,
    cms_models.Testimonial,
    cms_models.SiteStat,
    cms_models.Feature,
    cms_models.FAQItem,
    cms_models.GalleryItem,
]
