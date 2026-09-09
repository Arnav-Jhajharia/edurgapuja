"""What a paid donation line means. Idempotent, because webhooks redeliver."""

from django.utils import timezone


def confirm_donation(line) -> None:
    donation = getattr(line, "donation", None)
    if donation is None:
        return
    if donation.received_at is None:
        donation.received_at = timezone.now()
        donation.save(update_fields=["received_at", "updated_at"])
