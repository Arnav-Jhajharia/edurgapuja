"""Starting a donation.

A donation consumes no inventory and has no symmetric reversal, so there is no
hold and nothing to release — which is why this is much shorter than its
service-booking equivalent.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.common.errors import ValidationFailedError
from apps.orders import services as orders
from apps.orders.models import OrderLine
from apps.pandals.models import Pandal

from .models import Donation, DonationLink, DonationOffering


@transaction.atomic
def start_donation(*, data: dict, user=None) -> tuple[Donation, "orders.Order"]:
    pandal = get_object_or_404(
        Pandal.objects.filter(accepts_donations=True), pk=data["pandal_id"]
    )

    offering = None
    if data.get("offering_id"):
        offering = get_object_or_404(
            DonationOffering.objects.filter(pandal=pandal, is_active=True),
            pk=data["offering_id"],
        )
        amount_paise = offering.amount_paise
    else:
        amount_paise = data["amount_paise"]

    if amount_paise <= 0:
        raise ValidationFailedError("A donation has to be more than nothing.",
                                    fields={"amount_paise": "Enter an amount."})

    link = None
    if data.get("link_token"):
        link = DonationLink.objects.filter(token=data["link_token"], pandal=pandal,
                                           is_active=True).first()

    order = orders.create_order(pandal=pandal, user=user,
                                contact_phone=data.get("phone", ""))
    line = orders.add_line(order, kind=OrderLine.Kind.DONATION,
                           unit_amount_paise=amount_paise,
                           description=offering.label if offering else "Donation")
    orders.finalise(order)

    donation = Donation.objects.create(
        pandal=pandal, order_line=line, offering=offering, link=link,
        donor=user if user and user.is_authenticated else None,
        donor_name=data.get("donor_name", ""),
        message=data.get("message", ""),
        amount_paise=amount_paise,
    )
    return donation, order
