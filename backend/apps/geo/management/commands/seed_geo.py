"""Reference data: the places pandals are in.

Not demo data — a deployment with an empty city table cannot onboard anybody,
because the onboarding form has nothing to choose from. This is the same
category as a currency list, so it runs on every deploy and is idempotent.

Kolkata's paras are listed because that is where the platform starts. Adding a
city is a row, not a release: a Super Admin can create localities through the
admin, and this only guarantees there is somewhere to begin.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.geo.models import City, Locality, State

PLACES = {
    "West Bengal": {
        "code": "WB",
        "cities": {
            "Kolkata": [
                "Ballygunge", "Bhowanipore", "Kumartuli", "Maniktala", "Mudiali",
                "Salt Lake", "Shobhabazar", "Shyambazar", "Tollygunge",
                "Behala", "Jodhpur Park", "Lake Town", "New Alipore", "Park Circus",
            ],
            "Howrah": ["Shibpur", "Salkia", "Bally"],
        },
    },
}


class Command(BaseCommand):
    help = "Ensure the states, cities and localities pandals can be placed in."

    @transaction.atomic
    def handle(self, *args, **options):
        made = 0
        for state_name, spec in PLACES.items():
            state, _ = State.objects.get_or_create(
                name=state_name, defaults={"code": spec["code"]}
            )
            for city_name, localities in spec["cities"].items():
                city, created = City.objects.get_or_create(state=state, name=city_name)
                made += created
                for locality in localities:
                    _, new = Locality.objects.get_or_create(city=city, name=locality)
                    made += new

        self.stdout.write(self.style.SUCCESS(
            f"Places ready ({made} added, {Locality.objects.count()} localities total)."
        ))
