from django.db.models.signals import post_delete, post_save

from apps.cms.cache import CMS_MODELS, invalidate_site_context_cache


def connect_cms_signals():
    """Wire cache invalidation to every CMS model's save/delete."""
    for idx, model in enumerate(CMS_MODELS):
        post_save.connect(
            invalidate_site_context_cache,
            sender=model,
            dispatch_uid=f"cms_cache_invalidate_save_{idx}",
        )
        post_delete.connect(
            invalidate_site_context_cache,
            sender=model,
            dispatch_uid=f"cms_cache_invalidate_delete_{idx}",
        )
