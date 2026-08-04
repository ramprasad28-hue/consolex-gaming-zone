def site_context(request):
    """Inject cached CMS content into every template (Ch15)."""
    from apps.cms.cache import get_site_context_data

    return get_site_context_data()
