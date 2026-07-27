from django.db import models


class SiteSettingsManager(models.Manager):
    def get_solo(self):
        obj, _ = self.get_or_create(pk=1)
        return obj


class SiteSettings(models.Model):
    """Singleton — business info, social links, meta tags."""

    brand_name = models.CharField(max_length=100, default="CONSOLEX")
    tagline = models.CharField(max_length=200, default="Play Beyond")
    phone = models.CharField(max_length=20, default="+91 98765 43210")
    address = models.CharField(max_length=300, default="Erode, Tamil Nadu, India")
    operating_hours = models.CharField(max_length=100, default="10:00 AM – 11:00 PM Daily")
    whatsapp_number = models.CharField(max_length=20, default="919876543210")
    instagram_handle = models.CharField(max_length=100, default="@consolexerode")
    instagram_url = models.URLField(default="https://instagram.com/consolexerode")
    google_review_url = models.URLField(blank=True, default="")
    google_rating = models.DecimalField(max_digits=2, decimal_places=1, default=4.9)
    google_review_count = models.PositiveIntegerField(default=87)
    instagram_follower_count = models.CharField(max_length=20, default="2.1K")

    meta_description = models.TextField(
        default="CONSOLEX — Premium PS5 gaming zone in Erode. Book sessions, join memberships, compete in tournaments. Walk-ins welcome.",
    )
    og_title = models.CharField(max_length=200, default="CONSOLEX Gaming Zone — Play Beyond")
    og_description = models.TextField(
        default="Premium PS5 gaming zone in Erode. Book sessions, join memberships, compete in tournaments.",
    )
    theme_color = models.CharField(max_length=10, default="#050036")
    theme_color_light = models.CharField(max_length=10, default="#00e5ff")

    objects = SiteSettingsManager()

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.brand_name


class ContentBlock(models.Model):
    """Generic key-value store for section copy."""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key


class Announcement(models.Model):
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=10, default="🏆")
    text = models.CharField(max_length=300, default="Next Tournament: Jul 20 — ₹5,000 Prize Pool")
    cta_text = models.CharField(max_length=100, default="Register Now →")
    cta_url = models.URLField(blank=True, default="/bookings/new/")

    class Meta:
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"

    def __str__(self):
        return f"{'[Active] ' if self.is_active else ''}{self.text[:60]}"


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=200, help_text="e.g. College Student, PSG Tech")
    quote = models.TextField()
    game_tag = models.CharField(max_length=200, blank=True, help_text="e.g. Playing: God of War Ragnarök")
    rating = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} — {self.role}"


class SiteStat(models.Model):
    number = models.PositiveIntegerField()
    suffix = models.CharField(max_length=10, default="+")
    label = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.number}{self.suffix} {self.label}"


class Feature(models.Model):
    SECTION_CHOICES = [
        ("features", "Features Section"),
        ("why_choose", "Why Choose Us"),
        ("booking_steps", "Booking Steps"),
    ]
    section = models.CharField(max_length=20, choices=SECTION_CHOICES, default="features")
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji or SVG name")
    title = models.CharField(max_length=200)
    description = models.TextField()
    stat_value = models.CharField(max_length=50, blank=True, help_text="e.g. 120")
    stat_label = models.CharField(max_length=100, blank=True, help_text="e.g. Hz refresh rate")
    tag = models.CharField(max_length=100, blank=True, help_text="e.g. Weekly Events")
    tag_url = models.URLField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Feature"
        verbose_name_plural = "Features"

    def __str__(self):
        return f"[{self.section}] {self.title}"


class FAQItem(models.Model):
    CATEGORY_CHOICES = [
        ("all", "All"),
        ("booking", "Booking"),
        ("membership", "Membership"),
        ("payments", "Payments"),
        ("refunds", "Refunds"),
        ("rules", "Rules"),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="all")
    question = models.CharField(max_length=300)
    answer = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "FAQ Item"
        verbose_name_plural = "FAQ Items"

    def __str__(self):
        return self.question[:80]


class GalleryItem(models.Model):
    image = models.ImageField(upload_to="gallery/")
    caption = models.CharField(max_length=200)
    alt_text = models.CharField(max_length=200)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Gallery Item"
        verbose_name_plural = "Gallery Items"

    def __str__(self):
        return self.caption
