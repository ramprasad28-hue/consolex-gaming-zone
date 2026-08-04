# apps/cms/tests.py
from io import StringIO
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite

from apps.cms.models import (
    SiteSettings, ContentBlock, Announcement,
    Testimonial, SiteStat, Feature, FAQItem, GalleryItem,
)
from apps.cms.context_processors import site_context
from apps.cms.admin import (
    SiteSettingsAdmin, ContentBlockAdmin, AnnouncementAdmin,
    TestimonialAdmin, SiteStatAdmin, FeatureAdmin,
    FAQItemAdmin, GalleryItemAdmin,
)


class SiteSettingsTests(TestCase):
    def test_get_solo_creates_on_first_call(self):
        self.assertEqual(SiteSettings.objects.count(), 0)
        site = SiteSettings.objects.get_solo()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(site.brand_name, "CONSOLEX")

    def test_get_solo_returns_existing(self):
        s = SiteSettings.objects.get_solo()
        s.brand_name = "TEST"
        s.save()
        s2 = SiteSettings.objects.get_solo()
        self.assertEqual(s2.brand_name, "TEST")
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_str(self):
        site = SiteSettings.objects.get_solo()
        self.assertEqual(str(site), "CONSOLEX")

    def test_default_values(self):
        site = SiteSettings.objects.get_solo()
        self.assertEqual(site.tagline, "Play Beyond")
        self.assertEqual(site.google_rating, 4.9)
        self.assertEqual(site.google_review_count, 87)


class ContentBlockTests(TestCase):
    def test_create_and_str(self):
        cb = ContentBlock.objects.create(key="hero_title", value="Game On")
        self.assertEqual(str(cb), "hero_title")
        self.assertEqual(cb.value, "Game On")

    def test_unique_key(self):
        ContentBlock.objects.create(key="test", value="a")
        with self.assertRaises(Exception):
            ContentBlock.objects.create(key="test", value="b")

    def test_ordering(self):
        ContentBlock.objects.create(key="z_block", value="z")
        ContentBlock.objects.create(key="a_block", value="a")
        keys = list(ContentBlock.objects.values_list("key", flat=True))
        self.assertEqual(keys, ["a_block", "z_block"])


class AnnouncementTests(TestCase):
    def test_str_active(self):
        a = Announcement.objects.create(is_active=True, text="Tournament coming!")
        self.assertIn("[Active]", str(a))

    def test_str_inactive(self):
        a = Announcement.objects.create(is_active=False, text="Something")
        self.assertNotIn("[Active]", str(a))

    def test_str_truncation(self):
        a = Announcement.objects.create(text="x" * 100)
        self.assertEqual(len(str(a)), 69)  # "[Active] " (9) + 60 chars = 69


class TestimonialTests(TestCase):
    def test_str(self):
        t = Testimonial.objects.create(name="Ram", role="Student", quote="Great!")
        self.assertEqual(str(t), "Ram — Student")

    def test_ordering(self):
        Testimonial.objects.create(name="B", role="", quote="", sort_order=2)
        Testimonial.objects.create(name="A", role="", quote="", sort_order=1)
        names = list(Testimonial.objects.values_list("name", flat=True))
        self.assertEqual(names, ["A", "B"])


class SiteStatTests(TestCase):
    def test_str(self):
        s = SiteStat.objects.create(number=500, suffix="+", label="Gamers")
        self.assertEqual(str(s), "500+ Gamers")


class FeatureTests(TestCase):
    def test_str(self):
        f = Feature.objects.create(
            section="features", title="Fast WiFi", description="Blazing"
        )
        self.assertEqual(str(f), "[features] Fast WiFi")

    def test_section_choices(self):
        f = Feature.objects.create(section="booking_steps", title="Step 1", description="Go")
        self.assertEqual(f.section, "booking_steps")


class FAQItemTests(TestCase):
    def test_str(self):
        f = FAQItem.objects.create(
            category="booking", question="How do I book?", answer="Online."
        )
        self.assertEqual(str(f), "How do I book?")

    def test_category_choices(self):
        self.assertEqual(
            dict(FAQItem.CATEGORY_CHOICES)["membership"], "Membership"
        )


class GalleryItemTests(TestCase):
    def test_str(self):
        g = GalleryItem.objects.create(
            caption="Lounge View", alt_text="Lounge"
        )
        self.assertEqual(str(g), "Lounge View")


class ContextProcessorTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.factory = RequestFactory()
        self.site = SiteSettings.objects.get_solo()
        ContentBlock.objects.create(key="hero_title", value="Test Hero")
        Testimonial.objects.create(name="T1", role="R", quote="Q", is_active=True)
        Testimonial.objects.create(name="T2", role="R", quote="Q", is_active=False)
        SiteStat.objects.create(number=100, label="Players")
        Feature.objects.create(section="features", title="F1", description="D1")
        Feature.objects.create(section="why_choose", title="W1", description="WD1")
        Feature.objects.create(section="booking_steps", title="S1", description="SD1")
        Announcement.objects.create(is_active=True, text="Announcement!")
        FAQItem.objects.create(category="booking", question="Q1", answer="A1")
        GalleryItem.objects.create(caption="Pic", alt_text="Pic")

    def test_site_context_returns_all_keys(self):
        request = self.factory.get("/")
        ctx = site_context(request)
        self.assertIn("site", ctx)
        self.assertIn("cb", ctx)
        self.assertIn("cms_announcement", ctx)
        self.assertIn("cms_testimonials", ctx)
        self.assertIn("cms_stats", ctx)
        self.assertIn("cms_features", ctx)
        self.assertIn("cms_why_choose", ctx)
        self.assertIn("cms_booking_steps", ctx)
        self.assertIn("cms_faqs", ctx)
        self.assertIn("faq_categories", ctx)
        self.assertIn("cms_gallery", ctx)

    def test_cb_is_dict(self):
        request = self.factory.get("/")
        ctx = site_context(request)
        self.assertIsInstance(ctx["cb"], dict)
        self.assertEqual(ctx["cb"]["hero_title"], "Test Hero")

    def test_only_active_testimonials(self):
        request = self.factory.get("/")
        ctx = site_context(request)
        self.assertEqual(len(ctx["cms_testimonials"]), 1)
        self.assertEqual(ctx["cms_testimonials"][0].name, "T1")

    def test_only_active_announcement(self):
        request = self.factory.get("/")
        ctx = site_context(request)
        self.assertEqual(ctx["cms_announcement"].text, "Announcement!")

    def test_faq_categories(self):
        request = self.factory.get("/")
        ctx = site_context(request)
        self.assertIsInstance(ctx["faq_categories"], list)
        self.assertTrue(len(ctx["faq_categories"]) > 0)


class CacheTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.factory = RequestFactory()

    def test_second_call_hits_cache(self):
        first = site_context(self.factory.get("/"))
        with self.assertNumQueries(0):
            second = site_context(self.factory.get("/"))
        self.assertEqual(second, first)

    def test_save_invalidates_cache(self):
        site_context(self.factory.get("/"))
        block = ContentBlock.objects.create(key="hero_title", value="Old")
        block.value = "New"
        block.save()
        ctx = site_context(self.factory.get("/"))
        self.assertEqual(ctx["cb"]["hero_title"], "New")

    def test_delete_invalidates_cache(self):
        block = ContentBlock.objects.create(key="hero_title", value="Gone")
        site_context(self.factory.get("/"))
        block.delete()
        ctx = site_context(self.factory.get("/"))
        self.assertNotIn("hero_title", ctx["cb"])


class AdminTests(TestCase):
    def test_admin_registered(self):
        from django.contrib.admin.sites import site as admin_site
        self.assertIn(SiteSettings, admin_site._registry)
        self.assertIn(ContentBlock, admin_site._registry)
        self.assertIn(Announcement, admin_site._registry)
        self.assertIn(Testimonial, admin_site._registry)
        self.assertIn(SiteStat, admin_site._registry)
        self.assertIn(Feature, admin_site._registry)
        self.assertIn(FAQItem, admin_site._registry)
        self.assertIn(GalleryItem, admin_site._registry)


class SeedContentCommandTests(TestCase):
    def test_seed_content_creates_blocks(self):
        from django.core.management import call_command, CommandError
        out = StringIO()
        call_command("seed_content", stdout=out)
        output = out.getvalue()
        self.assertIn("CMS content seeded successfully", output)
        self.assertTrue(ContentBlock.objects.count() >= 10)
        self.assertTrue(Testimonial.objects.count() >= 1)
        self.assertTrue(SiteStat.objects.count() >= 1)
        self.assertTrue(Feature.objects.count() >= 1)
        self.assertTrue(FAQItem.objects.count() >= 1)

    def test_seed_content_idempotent(self):
        from django.core.management import call_command
        call_command("seed_content")
        count1 = ContentBlock.objects.count()
        call_command("seed_content")
        count2 = ContentBlock.objects.count()
        self.assertEqual(count1, count2)
