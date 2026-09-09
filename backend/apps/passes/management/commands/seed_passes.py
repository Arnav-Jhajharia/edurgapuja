"""Switch passes on for the seeded pandals.

A separate command on purpose: turning passes on is what a committee does when
it decides to sell them, and doing it here rather than in `seed_pandals` keeps
the "a pandal may have passes or may not" case honestly represented in dev.
"""

import datetime as dt

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.pandals.models import Gate, Pandal
from apps.passes.models import PandalDayCapacity, PassCategory, PassConfig, PassProduct

PUJA_DAYS = [dt.date(2026, 10, d) for d in range(10, 15)]

CATEGORIES = [
    ("Donor", "donor", "For those who have given to the puja"),
    ("Sponsor", "sponsor", "Issued from a sponsor's allocation"),
    ("VIP", "vip", "Guests of the committee"),
    ("Para Pass", "para-pass", "For the neighbourhood"),
    ("Senior Citizen", "senior-citizen", "Step-free entry, shorter queue"),
]


class Command(BaseCommand):
    help = "Turn passes on for the seeded pandals and configure what they sell."

    def add_arguments(self, parser):
        parser.add_argument("--slug", action="append",
                            help="Limit to these pandals (repeatable).")
        parser.add_argument("--capacity", type=int, default=2000,
                            help="Places per pandal per day.")

    @transaction.atomic
    def handle(self, *args, **options):
        pandals = Pandal.objects.filter(is_active=True)
        if options["slug"]:
            pandals = pandals.filter(slug__in=options["slug"])

        for pandal in pandals:
            pandal.sells_passes = True
            pandal.save(update_fields=["sells_passes"])

            categories = {}
            for order, (name, slug, description) in enumerate(CATEGORIES, start=1):
                category, _ = PassCategory.objects.update_or_create(
                    pandal=pandal, slug=slug,
                    defaults={"name": name, "description": description, "sort_order": order},
                )
                categories[slug] = category

            for day in PUJA_DAYS:
                PandalDayCapacity.objects.update_or_create(
                    pandal=pandal, date=day,
                    defaults={"capacity": options["capacity"], "is_open": True},
                )

            grid = [
                (PassProduct.INDIVIDUAL, "donor", 30_000, 1, dt.time(18, 0), dt.time(21, 0)),
                (PassProduct.INDIVIDUAL, "senior-citizen", 15_000, 1,
                 dt.time(10, 0), dt.time(13, 0)),
                (PassProduct.GROUP, "donor", 25_000, 6, dt.time(18, 0), dt.time(21, 0)),
                # A City Pass has a date and no time (D3), so the two are null.
                (PassProduct.CITY, "donor", 100_000, 1, None, None),
            ]
            for product, category_slug, price, party, start, end in grid:
                PassConfig.objects.update_or_create(
                    pandal=pandal, category=categories[category_slug], product=product,
                    defaults={
                        "from_date": PUJA_DAYS[0], "to_date": PUJA_DAYS[-1],
                        "from_time": start, "to_time": end, "price_paise": price,
                        "max_party_size": party, "is_active": True,
                    },
                )

            for name in ("Gate 1", "Gate 2"):
                Gate.objects.get_or_create(pandal=pandal, name=name)

            self.stdout.write(f"  {pandal.slug:<22} "
                              f"{len(categories)} categories, {len(grid)} on sale")

        self.stdout.write(self.style.SUCCESS(
            f"Passes switched on for {pandals.count()} pandal(s)."
        ))
