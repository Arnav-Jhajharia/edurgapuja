"""Seed a few complete pandal landing pages.

Content for Ballygunge Cultural is taken from the client's reference build; the
others are written in the same shape with their own palettes, so the page can be
seen doing what it is for — being *that committee's* site rather than a template.
"""

import datetime as dt

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.donations.models import DonationOffering
from apps.geo.models import City, Locality, State
from apps.ops.models import PandalLiveStatus
from apps.pandals.models import PageBlock, Pandal, PandalBrand, VisitFact
from apps.services.models import Service, ServiceDayCapacity
from apps.services.templates import apply_template

PUJA_DAYS = [dt.date(2026, 10, d) for d in range(10, 15)]

PANDALS = [
    {
        "name": "Ballygunge Cultural",
        "slug": "ballygunge-cultural",
        "locality": "Ballygunge",
        "committee": "Ballygunge Cultural Association",
        "theme": ("Protha", "প্রথা"),
        "jubilee": "Platinum Jubilee 2026",
        "brand": {"primary_colour": "#B45F1E", "accent_colour": "#E0A66A",
                  "surface_colour": "#FBF3E8", "ink_colour": "#3A1D0C"},
        "hero": {
            "eyebrow": "Ballygunge · Kolkata · Durga Puja",
            "headline": "Experience the Spirit of Durga Puja at Ballygunge Cultural",
            "standfirst": "A celebration of devotion, culture and community — crafted for an "
                          "unforgettable Puja experience.",
            "primary_cta": "Donate Now",
            "secondary_cta": "Explore Services",
        },
        "marquee": {"items": ["Darshan", "Curated Experiences", "Accessible Visit"]},
        "about": {
            "headline": "Where devotion becomes belonging.",
            "body": "Our 75th-year Platinum Jubilee celebrates Protha — the customs we inherit, "
                    "the stories we carry forward and the warm, welcoming experience we create "
                    "for every visitor.",
            "link_label": "Discover Our Story",
            "pillars": [
                {"title": "Culture & Tradition",
                 "body": "A living celebration shaped by Bengali memory and shared rituals."},
                {"title": "Art & Craft",
                 "body": "A thoughtful pandal experience where craft and imagination meet."},
                {"title": "Community & Celebration",
                 "body": "A generous gathering made for families, friends and every visitor."},
            ],
        },
        "donate": {
            "headline": "Support the Celebration.",
            "body": "Your contribution helps us continue the tradition, creativity and community "
                    "spirit that make Ballygunge Cultural a celebration for everyone.",
            "card_title": "Keep the light burning.",
            "card_eyebrow": "Choose your offering",
        },
        "services_block": {
            "headline": "Thoughtful extras for your visit.",
            "standfirst": "Curated experiences designed to make your Puja visit more "
                          "comfortable, meaningful and memorable.",
        },
        "closing": {
            "headline": "Come. Celebrate. Experience Durga Puja Differently.",
            "body": "Be a part of the devotion, artistry and community spirit of "
                    "Ballygunge Cultural.",
        },
        "footer": {"blurb": "A premium cultural experience shaped by devotion, artistry "
                            "and community."},
        "offerings": [(50_100, "Support a diya"), (100_100, "Support bhog"),
                      (200_100, "Support the artisans")],
        "services": [
            ("blank", "Donor Darshan",
             "Enjoy a more convenient and thoughtfully planned Darshan experience with "
             "dedicated donor access.", 75_000, 40),
            ("curated-tour", "Get Curated Tour",
             "Discover the story, artistry and cultural details of the Puja through a "
             "curated visitor experience.", 75_000, 20),
            ("special-assistance", "Accessible Visit",
             "Experience the Puja with thoughtfully planned accessibility support for a "
             "more comfortable visit.", 35_000, 25),
        ],
        "wait": 18,
        "crowd": PandalLiveStatus.CrowdLevel.MEDIUM,
    },
    {
        "name": "Mudiali Club",
        "slug": "mudiali-club",
        "locality": "Mudiali",
        "committee": "Mudiali Club Sarbojanin",
        "theme": ("Shikor", "শিকড়"),
        "jubilee": "88 Years",
        "brand": {"primary_colour": "#1F5F4B", "accent_colour": "#C9A227",
                  "surface_colour": "#F5F3EA", "ink_colour": "#12241E"},
        "hero": {
            "eyebrow": "Mudiali · Kolkata · Durga Puja",
            "headline": "Come Home to Mudiali This Puja",
            "standfirst": "Eighty-eight years of craft, light and neighbourhood — told again, "
                          "every autumn.",
            "primary_cta": "Donate Now",
            "secondary_cta": "Explore Services",
        },
        "marquee": {"items": ["Darshan", "Heritage Walk", "Prasad"]},
        "about": {
            "headline": "Roots, and what grows from them.",
            "body": "Shikor is about what holds a neighbourhood together — the hands that build, "
                    "the families that return, and the light we keep for anyone who walks in.",
            "link_label": "Discover Our Story",
            "pillars": [
                {"title": "Craft",
                 "body": "Bamboo, clay and light, worked by hands from Kumartuli."},
                {"title": "Neighbourhood", "body": "A para that becomes a city for five days."},
                {"title": "Welcome", "body": "Everyone who arrives is a guest of the club."},
            ],
        },
        "donate": {
            "headline": "Give to the Puja.",
            "body": "Every contribution goes to the artisans, the lighting and the prasad that "
                    "make Mudiali what it is.",
            "card_title": "Add your share.",
            "card_eyebrow": "Choose your offering",
        },
        "services_block": {
            "headline": "Make the visit easier.",
            "standfirst": "A few thoughtful additions for families, elders and first-time "
                          "visitors.",
        },
        "closing": {
            "headline": "Five Days. One Neighbourhood. Everyone Welcome.",
            "body": "Be part of Mudiali's eighty-eighth year.",
        },
        "footer": {"blurb": "A neighbourhood Puja, kept by the people who live here."},
        "offerings": [(25_100, "Light a lamp"), (51_00 * 10, "Feed a family"),
                      (150_100, "Support the artisans")],
        "services": [
            ("curated-tour", "Heritage Pandal Walk",
             "A guided walk through the pandal's art and craft, with the makers.", 30_000, 15),
            ("aarti-slot", "Aarti Slot Booking",
             "Reserve a place at the morning or evening aarti.", 25_100, 30),
        ],
        "wait": 32,
        "crowd": PandalLiveStatus.CrowdLevel.HIGH,
    },
    {
        "name": "Kumartuli Park",
        "slug": "kumartuli-park",
        "locality": "Kumartuli",
        "committee": "Kumartuli Park Sarbojanin Durgotsab",
        "theme": ("Matir Katha", "মাটির কথা"),
        "jubilee": "Since 1996",
        "brand": {"primary_colour": "#7B2D26", "accent_colour": "#D9A566",
                  "surface_colour": "#FAF4EC", "ink_colour": "#2A1512"},
        "hero": {
            "eyebrow": "Kumartuli · Kolkata · Durga Puja",
            "headline": "Where the Idols Are Born",
            "standfirst": "A Puja in the potters' quarter, told in the material it is made from.",
            "primary_cta": "Donate Now",
            "secondary_cta": "Read Our Story",
        },
        "marquee": {"items": ["Darshan", "Studio Visits", "Clay & Craft"]},
        "about": {
            "headline": "The clay speaks first.",
            "body": "Matir Katha is a conversation with the earth our idols come from, and with "
                    "the families who have shaped them here for generations.",
            "link_label": "Discover Our Story",
            "pillars": [
                {"title": "The Potters",
                 "body": "Studios that have worked this lane for a century."},
                {"title": "The Material",
                 "body": "River clay, straw and pigment, and nothing hidden."},
                {"title": "The City", "body": "Where every pandal in Kolkata begins."},
            ],
        },
        "donate": {
            "headline": "Support the Makers.",
            "body": "Contributions here reach the studios and families who build the Puja that "
                    "the rest of the city comes to see.",
            "card_title": "Give to the quarter.",
            "card_eyebrow": "Choose your offering",
        },
        "services_block": {
            "headline": "See how it is made.",
            "standfirst": "Small-group visits into the studios, arranged with the artisans "
                          "themselves.",
        },
        "closing": {
            "headline": "Begin Where the Puja Begins.",
            "body": "Walk the lane the idols come from.",
        },
        "footer": {"blurb": "The potters' quarter, and the Puja it makes possible."},
        "offerings": [(50_100, "Support a studio"), (100_100, "Buy clay and straw"),
                      (250_100, "Sponsor an idol")],
        "services": [
            ("curated-tour", "Studio Visit",
             "A small-group walk into the working studios with an artisan guide.", 60_000, 12),
        ],
        "wait": 12,
        "crowd": PandalLiveStatus.CrowdLevel.LOW,
    },
]


class Command(BaseCommand):
    help = "Seed complete landing pages for a few pandals."

    @transaction.atomic
    def handle(self, *args, **options):
        state, _ = State.objects.get_or_create(code="WB", defaults={"name": "West Bengal"})
        kolkata, _ = City.objects.get_or_create(state=state, name="Kolkata")

        for spec in PANDALS:
            locality, _ = Locality.objects.get_or_create(city=kolkata, name=spec["locality"])
            pandal, _ = Pandal.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "name": spec["name"],
                    "committee_name": spec["committee"],
                    "city": kolkata,
                    "locality": locality,
                    "theme_name": spec["theme"][0],
                    "theme_name_local": spec["theme"][1],
                    "accepts_donations": True,
                    "offers_services": True,
                    "sells_passes": False,
                    "publication_status": Pandal.PublicationStatus.PUBLISHED,
                    "opens_on": PUJA_DAYS[0],
                    "closes_on": PUJA_DAYS[-1],
                    "seo_title": f"{spec['name']} · Durga Puja 2026",
                    "seo_description": spec["hero"]["standfirst"],
                },
            )
            PandalBrand.objects.update_or_create(pandal=pandal, defaults=spec["brand"])

            blocks = [
                (PageBlock.Kind.HERO, {**spec["hero"], "jubilee": spec["jubilee"]}),
                (PageBlock.Kind.MARQUEE, spec["marquee"]),
                (PageBlock.Kind.ABOUT, spec["about"]),
                (PageBlock.Kind.DONATE, spec["donate"]),
                (PageBlock.Kind.SERVICES, spec["services_block"]),
                (PageBlock.Kind.VISIT, {"headline": "Plan Your Visit.",
                                        "standfirst": "Everything you need for a comfortable, "
                                                      "memorable and meaningful Puja."}),
                (PageBlock.Kind.CLOSING_CTA, spec["closing"]),
                (PageBlock.Kind.FOOTER, spec["footer"]),
            ]
            for order, (kind, content) in enumerate(blocks, start=1):
                PageBlock.objects.update_or_create(
                    pandal=pandal, kind=kind, language="en",
                    defaults={"sort_order": order, "content": content, "is_visible": True},
                )

            pandal.visit_facts.all().delete()
            for order, (label, value) in enumerate([
                ("Pandal Location", f"{spec['name']}, {spec['locality']}, Kolkata"),
                ("Puja Dates", "10 – 14 October 2026"),
                ("Darshan Timings", "Open daily · Morning to late evening"),
                ("Visitor Information", "Families, seniors and accessible visits welcome"),
            ], start=1):
                VisitFact.objects.create(pandal=pandal, label=label, value=value,
                                         sort_order=order)

            pandal.donation_offerings.all().delete()
            for order, (amount, label) in enumerate(spec["offerings"], start=1):
                DonationOffering.objects.create(pandal=pandal, amount_paise=amount,
                                                label=label, sort_order=order)

            for order, (template, name, description, price, capacity) in enumerate(
                    spec["services"], start=1):
                service, _ = Service.objects.update_or_create(
                    pandal=pandal, slug=name.lower().replace(" ", "-"),
                    defaults={"name": name, "description": description,
                              "price_paise": price, "sort_order": order, "is_active": True},
                )
                # A template is a starting point for the form, not a type the
                # service keeps — nothing reads it back.
                apply_template(service, template)
                for day in PUJA_DAYS:
                    ServiceDayCapacity.objects.update_or_create(
                        service=service, date=day, defaults={"capacity": capacity},
                    )

            PandalLiveStatus.objects.update_or_create(
                pandal=pandal,
                defaults={"estimated_wait_minutes": spec["wait"], "crowd_level": spec["crowd"]},
            )

            self.stdout.write(f"  {pandal.slug:<22} {pandal.canonical_host}")

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(PANDALS)} landing pages."))
