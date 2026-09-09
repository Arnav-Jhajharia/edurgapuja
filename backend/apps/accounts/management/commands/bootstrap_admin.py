"""Create the platform's first Super Admin.

Every other administrator is granted by somebody who is already one. That
leaves the first one with nowhere to come from, and the usual answers are both
bad: seed a well-known account into production, or SSH into a container and
type at a shell.

So it is configuration. The command runs on every deploy, does nothing unless
told to, and does nothing twice — which means it can sit in the start command
and be forgotten about.
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import AdminMembership, Role, User


class Command(BaseCommand):
    help = "Ensure a Super Admin exists, from BOOTSTRAP_ADMIN_PHONE / _PASSWORD."

    def add_arguments(self, parser):
        parser.add_argument("--phone", default=None)
        parser.add_argument("--password", default=None)

    @transaction.atomic
    def handle(self, *args, **options):
        phone = options["phone"] or getattr(settings, "BOOTSTRAP_ADMIN_PHONE", "")
        password = options["password"] or getattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", "")

        if not phone:
            self.stdout.write("No BOOTSTRAP_ADMIN_PHONE set; nothing to do.")
            return

        from apps.accounts.phone import normalise
        phone = normalise(phone)

        user, created = User.objects.get_or_create(phone=phone)
        if password:
            # Set every time on purpose: rotating the platform's first password
            # should be a variable change and a redeploy, not a shell session.
            user.set_password(password)
            user.save(update_fields=["password", "updated_at"])

        _, granted = AdminMembership.objects.get_or_create(
            user=user, role=Role.SUPER_ADMIN, pandal=None, organisation=None,
            defaults={"is_active": True},
        )

        what = []
        if created:
            what.append("account created")
        if granted:
            what.append("super admin granted")
        if password:
            what.append("password set")
        self.stdout.write(self.style.SUCCESS(
            f"{phone}: {', '.join(what) or 'already in place'}"
        ))
