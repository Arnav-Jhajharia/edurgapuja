"""Seed one account per panel, plus enough sponsorship to make them non-empty."""

import datetime as dt

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import AdminMembership, Role, User
from apps.pandals.models import Pandal
from apps.sponsorship import operations
from apps.sponsorship.models import (
    BrandingCreative,
    BrandingPlacement,
    Organisation,
    PoolAllocation,
    SponsorshipPackage,
)

PLACEMENTS = [("Home Screen", 500_000), ("Pass Confirmation", 350_000),
              ("My Pass Screen", 250_000)]


class Command(BaseCommand):
    help = "Seed an account for each of the four admin panels."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="password",
                            help="Password these seeded accounts can sign in with.")

    @transaction.atomic
    def handle(self, *args, **options):
        pandals = list(Pandal.objects.order_by("name"))
        if not pandals:
            self.stderr.write("Run seed_pandals first.")
            return

        def admin(phone, name, role, **scope):
            user, _ = User.objects.update_or_create(
                phone=phone,
                defaults={"first_name": name.split()[0], "last_name": name.split()[-1]},
            )
            # A real hashed password, not a bypass — these accounts can sign in
            # with `password` through the ordinary door. The shared
            # DEV_LOGIN_PASSWORD is a separate thing, fenced to DEBUG.
            user.set_password(options["password"])
            user.save(update_fields=["password", "updated_at"])
            AdminMembership.objects.update_or_create(user=user, role=role, **scope,
                                                     defaults={"is_active": True})
            return user

        admin("+919000000001", "Debraj Sen", Role.SUPER_ADMIN, pandal=None, organisation=None)
        pandal_admin = admin("+919000000002", "Priya Ghosh", Role.PANDAL_ADMIN,
                             pandal=pandals[0], organisation=None)
        # A second pandal for the same admin, so the pandal switcher has work to do.
        if len(pandals) > 1:
            AdminMembership.objects.update_or_create(
                user=pandal_admin, role=Role.PANDAL_ADMIN, pandal=pandals[1],
                organisation=None, defaults={"is_active": True},
            )

        sponsor, _ = Organisation.objects.update_or_create(
            slug="sponsor-one",
            defaults={"name": "Sponsor One", "contact_name": "Priya Sharma",
                      "contact_phone": "+919000022233"},
        )
        admin("+919000000003", "Amit Ghosh", Role.SPONSOR_ADMIN, pandal=None,
              organisation=sponsor)

        sub, _ = Organisation.objects.update_or_create(
            slug="kolkata-sweets",
            defaults={"name": "Kolkata Sweets Corner", "parent": sponsor},
        )
        admin("+919000000004", "Rohan Das", Role.SUB_SPONSOR_ADMIN, pandal=None,
              organisation=sub)

        for order, (name, price) in enumerate(PLACEMENTS):
            BrandingPlacement.objects.update_or_create(
                slug=name.lower().replace(" ", "-"),
                defaults={"name": name, "price_per_week_paise": price, "sort_order": order},
            )

        # Accepted at the first pandal, still pending at the second — so the
        # sponsor panel shows both a live pool and something awaiting an answer.
        for index, pandal in enumerate(pandals[:2]):
            package, _ = SponsorshipPackage.objects.update_or_create(
                pandal=pandal, slug="gold",
                defaults={"name": "Gold Sponsor", "value_paise": 5_000_000,
                          "pass_count": 500, "banner_placements": 2,
                          "benefits": "Priority entry gate, listed on the Sponsors page"},
            )
            allocation, created = PoolAllocation.objects.get_or_create(
                pandal=pandal, organisation=sponsor, package=package,
                defaults={"pass_count": 100 if index == 0 else 60,
                          "value_paise": package.value_paise},
            )
            if created and index == 0:
                pool = operations.accept_allocation(allocation_id=allocation.pk)
                operations.transfer(from_pool_id=pool.pk, to_organisation=sub,
                                    quantity=40, price_per_pass_paise=10_000)
                operations.issue_from_pool(pool_id=pool.pk, quantity=15)
                BrandingCreative.objects.get_or_create(
                    organisation=sponsor, pandal=pandal,
                    placement=BrandingPlacement.objects.get(slug="home-screen"),
                    name="Sponsor One — Puja Special",
                    defaults={"start_date": dt.date(2026, 10, 10),
                              "end_date": dt.date(2026, 10, 20),
                              "price_paise": 500_000},
                )

        self.stdout.write(self.style.SUCCESS(
            "Seeded admins:\n"
            "  +919000000001  Super Admin\n"
            "  +919000000002  Pandal Admin (two pandals)\n"
            "  +919000000003  Sponsor Admin\n"
            "  +919000000004  Sub-Sponsor Admin"
        ))
