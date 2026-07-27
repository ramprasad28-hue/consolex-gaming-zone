from django.conf import settings


def site_context(request):
    """Inject CMS content into every template."""
    from apps.cms.models import (
        SiteSettings, ContentBlock, Announcement,
        Testimonial, SiteStat, Feature, FAQItem, GalleryItem,
    )

    site = SiteSettings.objects.get_solo()

    blocks_qs = ContentBlock.objects.all()
    blocks = {b.key: b.value for b in blocks_qs}

    announcement = Announcement.objects.filter(is_active=True).first()
    testimonials = Testimonial.objects.filter(is_active=True)
    stats = SiteStat.objects.all()
    features = Feature.objects.filter(section="features")
    why_choose = Feature.objects.filter(section="why_choose")
    booking_steps = Feature.objects.filter(section="booking_steps")
    faqs = FAQItem.objects.all()
    faq_categories = FAQItem.CATEGORY_CHOICES
    gallery = GalleryItem.objects.all()

    return {
        "site": site,
        "cb": blocks,
        "cms_announcement": announcement,
        "cms_testimonials": testimonials,
        "cms_stats": stats,
        "cms_features": features,
        "cms_why_choose": why_choose,
        "cms_booking_steps": booking_steps,
        "cms_faqs": faqs,
        "faq_categories": faq_categories,
        "cms_gallery": gallery,
    }
