from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.cms.models import (
    SiteSettings, ContentBlock, Announcement, Testimonial,
    SiteStat, Feature, FAQItem, GalleryItem,
)


class Command(BaseCommand):
    help = "Seed CMS content with all current hardcoded values"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing CMS data first")

    def handle(self, *args, **options):
        if options["clear"]:
            for model in [ContentBlock, Announcement, Testimonial, SiteStat, Feature, FAQItem, GalleryItem]:
                model.objects.all().delete()
            SiteSettings.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared all CMS data."))

        self._seed_site_settings()
        self._seed_content_blocks()
        self._seed_announcement()
        self._seed_testimonials()
        self._seed_stats()
        self._seed_features()
        self._seed_faq()
        self._seed_gallery()

        self.stdout.write(self.style.SUCCESS("CMS content seeded successfully."))

    def _seed_site_settings(self):
        SiteSettings.objects.get_or_create(pk=1, defaults={
            "brand_name": "CONSOLEX",
            "tagline": "Play Beyond",
            "phone": "+91 98765 43210",
            "address": "Erode, Tamil Nadu, India",
            "operating_hours": "10:00 AM – 11:00 PM Daily",
            "whatsapp_number": "919876543210",
            "instagram_handle": "@consolexerode",
            "instagram_url": "https://instagram.com/consolexerode",
            "google_review_url": "https://search.google.com/local/writereview?placeid=ChIJPlaceholder",
            "google_rating": Decimal("4.9"),
            "google_review_count": 87,
            "instagram_follower_count": "2.1K",
            "meta_description": "CONSOLEX — Premium PS5 gaming zone in Erode. Book sessions, join memberships, compete in tournaments. Walk-ins welcome.",
            "og_title": "CONSOLEX Gaming Zone — Play Beyond",
            "og_description": "Premium PS5 gaming zone in Erode. Book sessions, join memberships, compete in tournaments.",
            "theme_color": "#050036",
            "theme_color_light": "#00e5ff",
        })
        self.stdout.write("  SiteSettings: OK")

    def _seed_content_blocks(self):
        blocks = {
            "hero_pill_1": "Now Open in Erode",
            "hero_pill_2": "PS5 Gaming Lounge",
            "hero_headline_1": "PLAY",
            "hero_headline_2": "BEYOND",
            "hero_subtitle": "Experience premium console gaming with high-end PlayStation 5 setups, online booking, memberships, tournaments, and immersive multiplayer experiences.",
            "hero_cta_primary": "Book Now",
            "hero_cta_ghost": "Explore Memberships",
            "hero_stat_1_value": "10+",
            "hero_stat_1_label": "PS5 Consoles",
            "hero_stat_2_value": "4K",
            "hero_stat_2_label": "HDR Displays",
            "hero_stat_3_value": "100+",
            "hero_stat_3_label": "PS5 Games",
            "hero_stat_4_value": "₹130",
            "hero_stat_4_label": "Starting /hr",
            "hero_floating_tournament": "Next Tournament",
            "hero_floating_pool": "Prize Pool: ₹5,000",
            "hero_floating_badge": "Registrations Open",
            "hero_floating_players": "+24 Playing Now",

            "features_pill": "The Experience",
            "features_title": "Everything You Need to Game Like a Pro",
            "features_subtitle": "Not your average cyber café. Every detail is designed for the ultimate PlayStation experience.",

            "games_pill": "Game Library",
            "games_title": "100+ PS5 Titles",
            "games_subtitle": "From AAA blockbusters to indie gems. All included in every session.",
            "games_cta_text": "And 80+ more titles available at the lounge",
            "games_cta_btn": "View Full Library",
            "games_empty": "Game library coming soon. Check back soon for our full PS5 collection!",

            "tournament_pill": "Tournaments",
            "tournament_title": "Compete. Win. Dominate.",
            "tournament_subtitle": "Weekly tournaments with real cash prizes. Open to all members and walk-ins.",
            "tournament_expired": "Event Started",

            "pricing_pill": "Pricing",
            "pricing_title": "Transparent, Fair Pricing",
            "pricing_subtitle": "Pay per hour or go unlimited with a membership. No hidden charges.",
            "pricing_subsection": "Hourly Rates",
            "pricing_footnote": "Mon–Fri: Weekday rates · Sat–Sun: Weekend rates · Minimum 1 hour per booking",

            "testimonials_pill": "Reviews",
            "testimonials_title": "Gamers Love CONSOLEX",

            "faq_pill": "FAQ",
            "faq_title": "Got Questions?",
            "faq_subtitle": "Everything you need to know before you play.",
            "faq_cta_title": "Still have questions?",
            "faq_cta_subtitle": "Chat with us on WhatsApp — we reply fast.",
            "faq_cta_btn": "WhatsApp Us",

            "gallery_pill": "Our Space",
            "gallery_title": "Inside CONSOLEX",
            "gallery_subtitle": "Take a peek at the lounge — premium setups, epic vibes, and the games waiting for you.",

            "membership_pill": "Membership Plans",
            "membership_title": "Level Up with a Membership",
            "membership_subtitle": "Unlock exclusive hours, priority booking and member-only perks every month. The more you play, the more you save.",
            "membership_perk": "Access to full game library",
            "membership_compare": "View All Plans & Compare",
            "membership_rules_title": "Plan Rules",
            "membership_empty": "Membership plans coming soon.",

            "booking_cta_title": "Ready to Play?",
            "booking_cta_subtitle": "Book your PS5 session in 60 seconds. No queue, no wait.",
            "booking_cta_primary": "Book Now",
            "booking_cta_ghost": "View Games",

            "social_instagram_title": "Follow the Chaos",
            "social_instagram_subtitle": "Behind-the-scenes gaming sessions, tournament clips, weekend highlights, and exclusive offers — all on Instagram.",
            "social_instagram_btn": "Follow @consolexerode",
            "social_review_title": "Loved your session?",
            "social_review_subtitle": "Drop a Google review — it takes 30 seconds and helps more gamers discover CONSOLEX.",
            "social_review_btn": "Write a Google Review",

            "footer_tagline": "Premium PS5 gaming lounge in Erode. Book your session, join tournaments, and play beyond limits.",
            "footer_copyright": "© 2026 CONSOLEX. All rights reserved.",

            "booking_form_title": "Book Your PS5 Slot",
            "booking_form_subtitle": "Select your console, date, time and number of players.",

            "payment_title": "Confirm Your Booking",
            "payment_subtitle": "Complete your advance payment securely using Razorpay.",

            "plans_title": "Level Up with a Membership",
            "plans_subtitle": "Unlock exclusive hours, priority booking and member-only perks every month. The more you play, the more you save.",
            "plans_compare_title": "Compare Plans",
            "plans_compare_subtitle": "Everything included in each CONSOLEX membership.",
            "plans_calculator_title": "Gaming Hour Calculator",
            "plans_calculator_subtitle": "See how many sessions your membership hours cover.",
            "plans_savings_title": "Membership Savings",
            "plans_savings_subtitle": "Pay per hour vs. pay with a membership — see the difference.",

            "auth_login_title": "Welcome Back",
            "auth_login_subtitle": "Sign in to your CONSOLEX account",
            "auth_register_title": "Create Account",
            "auth_register_subtitle": "Join CONSOLEX and start booking your PS5 sessions.",

            "error_404_msg": "This level doesn't exist. The page you're looking for has been moved or doesn't exist.",
            "error_500_msg": "System Error — our server hit a glitch. Our team has been notified. Please try again shortly.",
        }
        created = 0
        for key, value in blocks.items():
            _, was_created = ContentBlock.objects.get_or_create(key=key, defaults={"value": value})
            if was_created:
                created += 1
        self.stdout.write(f"  ContentBlocks: {created} created, {len(blocks) - created} already existed.")

    def _seed_announcement(self):
        Announcement.objects.get_or_create(
            pk=1,
            defaults={
                "is_active": True,
                "icon": "🏆",
                "text": "Next Tournament: Jul 20 — ₹5,000 Prize Pool",
                "cta_text": "Register Now →",
                "cta_url": "/bookings/new/",
            },
        )
        self.stdout.write("  Announcement: OK")

    def _seed_testimonials(self):
        testimonials = [
            {
                "name": "Aditya Subramanian",
                "role": "College Student, PSG Tech",
                "quote": "CONSOLEX is unreal. The PS5 setups are top-tier, the screens are huge, and the vibe is like playing at home but way better. I've been coming every weekend with my squad.",
                "game_tag": "Playing: God of War Ragnarök",
                "rating": 5,
                "sort_order": 1,
            },
            {
                "name": "Meenakshi Palaniswamy",
                "role": "Graphic Designer, Erode",
                "quote": "Came here for a date night and we ended up staying for 3 hours! The online booking was so easy, the ambience is incredible, and the staff is super friendly.",
                "game_tag": "Playing: It Takes Two",
                "rating": 5,
                "sort_order": 2,
            },
            {
                "name": "Karthikeyan Rajan",
                "role": "Esports Player, Erode",
                "quote": "Won my first tournament here and walked away with ₹3,000. The setups are lag-free, the controllers are pristine, and the tournament format is super competitive.",
                "game_tag": "Playing: Warzone",
                "rating": 5,
                "sort_order": 3,
            },
            {
                "name": "Divya Annamalai",
                "role": "IT Professional, Erode",
                "quote": "The Pro membership is insane value. 45 hours a month for ₹3,999? I come here after work to decompress and it's honestly the best part of my day.",
                "game_tag": "Playing: Spider-Man 2",
                "rating": 5,
                "sort_order": 4,
            },
            {
                "name": "Surya Narayanan",
                "role": "Engineering Student",
                "quote": "Brought my whole friend group for a birthday session. 4-player mode on the big screen — we couldn't stop laughing. The staff even set up a special arrangement for us.",
                "game_tag": "Playing: Mortal Kombat 1",
                "rating": 5,
                "sort_order": 5,
            },
        ]
        created = 0
        for data in testimonials:
            _, was_created = Testimonial.objects.get_or_create(
                name=data["name"], defaults=data,
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Testimonials: {created} created, {len(testimonials) - created} already existed.")

    def _seed_stats(self):
        stats = [
            {"number": 5000, "suffix": "+", "label": "Players Served", "sort_order": 1},
            {"number": 15000, "suffix": "+", "label": "Hours Played", "sort_order": 2},
            {"number": 2000, "suffix": "+", "label": "Bookings Completed", "sort_order": 3},
            {"number": 200, "suffix": "+", "label": "Active Members", "sort_order": 4},
            {"number": 50, "suffix": "+", "label": "Tournaments Hosted", "sort_order": 5},
        ]
        created = 0
        for data in stats:
            _, was_created = SiteStat.objects.get_or_create(
                label=data["label"], defaults=data,
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Stats: {created} created, {len(stats) - created} already existed.")

    def _seed_features(self):
        features = [
            {
                "section": "features", "icon": "🎮", "sort_order": 1,
                "title": "Premium PS5 Consoles",
                "description": "Latest PlayStation 5 consoles with DualSense haptic controllers. Zero lag, maximum immersion.",
                "image": "consoles/plan.jpeg",
            },
            {
                "section": "features", "icon": "📺", "sort_order": 2,
                "title": "4K HDR Displays",
                "description": '55" OLED screens, 120Hz, HDR10+.',
                "stat_value": "120", "stat_label": "Hz refresh rate",
                "image": "cxdesign/Center.jpeg",
            },
            {
                "section": "features", "icon": "🌐", "sort_order": 3,
                "title": "High-Speed Internet",
                "description": "1Gbps fiber for zero-lag online play.",
                "stat_value": "1Gbps", "stat_label": "fiber optic",
                "image": "cxdesign/first.jpeg",
            },
            {
                "section": "features", "icon": "🛋️", "sort_order": 4,
                "title": "Comfortable Lounge",
                "description": "Premium gaming chairs, AC, snacks. Built for long sessions.",
                "image": "cxdesign/Whole.jpeg",
            },
            {
                "section": "features", "icon": "📱", "sort_order": 5,
                "title": "Online Booking",
                "description": "Reserve your spot in 60 seconds. No queue, no wait.",
                "tag": "Book in 60 seconds →",
                "image": "cxdesign/first.jpeg",
            },
            {
                "section": "features", "icon": "🏆", "sort_order": 6,
                "title": "Competitive Tournaments",
                "description": "Weekly esports events with real cash prizes. Prove your skill.",
                "tag": "Weekly Events",
                "tag_url": "/tournaments/",
                "image": "tournaments/EA_Sports_FC_26.jpg",
            },
            {
                "section": "features", "icon": "👥", "sort_order": 7,
                "title": "Friends & Group Gaming",
                "description": "Side-by-side setups. Bring your squad for the ultimate co-op experience.",
                "tag": "Up to 4 Players",
                "image": "games/spiderman.jpg",
            },
            {
                "section": "features", "icon": "💎", "sort_order": 8,
                "title": "Membership Plans",
                "description": "Monthly plans from ₹1,199. Hours that roll over, weekend access, bonus sessions.",
                "stat_value": "₹1,199", "stat_label": "/month starting",
                "image": "consoles/plan.jpeg",
            },
        ]
        why_choose = [
            {
                "section": "why_choose", "icon": "🎮", "sort_order": 1,
                "title": "Premium Controllers",
                "description": "Genuine DualSense controllers with haptic feedback, fully charged and drift-free.",
            },
            {
                "section": "why_choose", "icon": "🌐", "sort_order": 2,
                "title": "High-Speed Internet",
                "description": "Fibre backbone with zero-lag local play — online matches stay smooth under load.",
            },
            {
                "section": "why_choose", "icon": "💺", "sort_order": 3,
                "title": "Comfortable Seating",
                "description": "Ergonomic gaming chairs built for long sessions — no aches after a 3-hour raid.",
            },
            {
                "section": "why_choose", "icon": "📺", "sort_order": 4,
                "title": '55" 4K Displays',
                "description": "Large 4K panels with HDR and low input lag, tuned specifically for console gaming.",
            },
            {
                "section": "why_choose", "icon": "❄️", "sort_order": 5,
                "title": "Air Conditioned",
                "description": "A cool, climate-controlled room year-round, even during peak weekend sessions.",
            },
            {
                "section": "why_choose", "icon": "🍿", "sort_order": 6,
                "title": "Snacks & Drinks",
                "description": "A stocked snack bar right in the lounge, so no one has to leave mid-match.",
            },
        ]
        booking_steps = [
            {
                "section": "booking_steps", "icon": "1", "sort_order": 1,
                "title": "Choose Console",
                "description": "Pick a PS5 setup and how many players are joining you.",
            },
            {
                "section": "booking_steps", "icon": "2", "sort_order": 2,
                "title": "Choose Time",
                "description": "Select a date and slot that fits your schedule — see availability live.",
            },
            {
                "section": "booking_steps", "icon": "3", "sort_order": 3,
                "title": "Pay Advance",
                "description": "Secure your slot with a small advance via Razorpay. Balance is paid at the lounge.",
            },
            {
                "section": "booking_steps", "icon": "4", "sort_order": 4,
                "title": "Play",
                "description": "Walk in, sit down, and start playing. Your setup is ready and waiting.",
            },
        ]
        all_features = features + why_choose + booking_steps
        created = 0
        for data in all_features:
            image = data.pop("image", "")
            obj, was_created = Feature.objects.get_or_create(
                section=data["section"], title=data["title"], defaults=data,
            )
            if not was_created and image and not obj.image:
                obj.image = image
                obj.save(update_fields=["image"])
            if was_created:
                created += 1
        self.stdout.write(f"  Features: {created} created, {len(all_features) - created} already existed.")

    def _seed_faq(self):
        faqs = [
            {"category": "booking", "sort_order": 1,
             "question": "How do I book a session at CONSOLEX?",
             "answer": "You can book online through our website in under 60 seconds — just select your date, time, number of players, and duration. You'll receive a confirmation via WhatsApp. Walk-ins are also welcome subject to availability."},
            {"category": "booking", "sort_order": 2,
             "question": "What is the minimum booking duration?",
             "answer": "The minimum booking duration is 1 hour. You can book in 30-minute increments after the first hour. Maximum single-session booking is 4 hours."},
            {"category": "membership", "sort_order": 3,
             "question": "What is included in a membership?",
             "answer": "Memberships include pre-paid gaming hours valid for 30 days. Basic (10 hrs weekdays), Standard (25+5 weekend hrs), and Pro (45 total hrs, all days). Members also get priority booking and exclusive discounts."},
            {"category": "membership", "sort_order": 4,
             "question": "Do unused membership hours roll over?",
             "answer": "Membership hours do not roll over to the next month. We recommend choosing a plan that matches your expected usage. You can upgrade your plan at any time."},
            {"category": "payments", "sort_order": 5,
             "question": "What payment methods do you accept?",
             "answer": "We accept UPI (GPay, PhonePe, Paytm), cash, and all major credit/debit cards. Online bookings can be paid via UPI or card. Memberships can also be purchased in-store."},
            {"category": "refunds", "sort_order": 6,
             "question": "What is the refund policy for bookings?",
             "answer": "Cancellations made 2+ hours before the session start time receive a full refund. Cancellations within 2 hours receive a 50% refund. No-shows are non-refundable. Membership fees are non-refundable after activation."},
            {"category": "rules", "sort_order": 7,
             "question": "Are there any age restrictions?",
             "answer": "Players below 16 years old must be accompanied by a parent or guardian. Some games are age-rated and we follow PEGI/ESRB guidelines. ID may be requested for age-restricted titles."},
            {"category": "rules", "sort_order": 8,
             "question": "Can I bring food and drinks to the lounge?",
             "answer": "Outside food and drinks are not permitted inside the gaming zone. We have snacks, beverages, and refreshments available at the lounge counter. No smoking or alcohol is allowed on the premises."},
        ]
        created = 0
        for data in faqs:
            _, was_created = FAQItem.objects.get_or_create(
                question=data["question"], defaults=data,
            )
            if was_created:
                created += 1
        self.stdout.write(f"  FAQ: {created} created, {len(faqs) - created} already existed.")

    def _seed_gallery(self):
        items = [
            {"image": "cxdesign/first.jpeg", "caption": "Our Gaming Lounge", "alt_text": "CONSOLEX Gaming Lounge", "sort_order": 1},
            {"image": "games/cod.jpg", "caption": "Call of Duty", "alt_text": "Call of Duty", "sort_order": 2},
            {"image": "consoles/plan.jpeg", "caption": "Premium PS5 Setup", "alt_text": "CONSOLEX Setup", "sort_order": 3},
            {"image": "png for web/spiderman.png", "caption": "Spider-Man 2", "alt_text": "Spider-Man", "sort_order": 4},
            {"image": "cxdesign/Center.jpeg", "caption": "4K Gaming Zone", "alt_text": "CONSOLEX Interior", "sort_order": 5},
            {"image": "games/kratos.png", "caption": "God of War", "alt_text": "God of War", "sort_order": 6},
            {"image": "png for web/gtav.png", "caption": "GTA V", "alt_text": "GTA V", "sort_order": 7},
            {"image": "png for web/arthur.png", "caption": "Red Dead Redemption 2", "alt_text": "Red Dead Redemption", "sort_order": 8},
            {"image": "png for web/ronald.png", "caption": "FC 26", "alt_text": "FC 26", "sort_order": 9},
            {"image": "cxdesign/Whole.jpeg", "caption": "Walk-In Gaming", "alt_text": "CONSOLEX Lounge", "sort_order": 10},
            {"image": "png for web/ghost.png", "caption": "Tactical Warfare", "alt_text": "COD", "sort_order": 11},
            {"image": "consoles/plan.jpeg", "caption": "Squad Setup", "alt_text": "CONSOLEX", "sort_order": 12},
        ]
        created = 0
        for data in items:
            _, was_created = GalleryItem.objects.get_or_create(
                caption=data["caption"], defaults=data,
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Gallery: {created} created, {len(items) - created} already existed.")
