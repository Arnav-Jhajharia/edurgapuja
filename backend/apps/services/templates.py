"""Starting points for a service's form.

These were once the platform's five fixed shapes, and a committee that wanted a
sixth had to wait for a migration. They are now suggestions: picking one fills
the form editor with a sensible set of questions, and the pandal renames, adds,
reorders or deletes whatever it likes afterwards.

Nothing in the codebase branches on these. They exist so that a committee adding
'Puja in your name' does not have to remember that a sankalp needs a gotra.
"""

from .models import ServiceField

K = ServiceField.Kind


def _field(key, label, kind=K.TEXT, *, required=False, sensitive=False, help_text="",
           options=None):
    return {"key": key, "label": label, "kind": kind, "required": required,
            "is_sensitive": sensitive, "help_text": help_text, "options": options or []}


WHO = [
    _field("name", "Your name", required=True),
    _field("contact_phone", "Mobile number", K.PHONE, required=True,
           help_text="We will call this number if anything changes."),
]

TEMPLATES: list[dict] = [
    {
        "slug": "blank",
        "name": "Start from scratch",
        "description": "Two questions to identify the visitor. Add whatever else you need.",
        "requires_capacity": True,
        "fields": WHO,
    },
    {
        "slug": "curated-tour",
        "name": "Curated tour",
        "description": "A guided walk of the pandal for a small group.",
        "requires_capacity": True,
        "fields": [
            *WHO,
            _field("party_size", "How many people", K.NUMBER, required=True),
            _field("notes", "Anything we should know", K.TEXTAREA),
        ],
    },
    {
        "slug": "puja-in-your-name",
        "name": "Puja in your name",
        "description": "A sankalp offered on the visitor's behalf.",
        "requires_capacity": True,
        "fields": [
            *WHO,
            _field("name_for_puja", "Name to be chanted", required=True, sensitive=True),
            _field("gotra", "Gotra", sensitive=True,
                   help_text="Leave blank if you would rather not say."),
            _field("sankalp", "Sankalp", K.TEXTAREA, sensitive=True),
            _field("preferred_time", "Preferred time", K.TIME),
        ],
    },
    {
        "slug": "special-assistance",
        "name": "Special assistance",
        "description": "Help for a visitor who needs it to get round the pandal.",
        "requires_capacity": True,
        "fields": [
            *WHO,
            _field("assistance_for", "Who needs assistance", required=True, sensitive=True),
            _field("assistance_type", "What kind", K.SELECT, sensitive=True,
                   options=["Mobility", "Vision", "Hearing", "Other"]),
            _field("wheelchair_required", "Wheelchair needed", K.CHECKBOX, sensitive=True),
            _field("remarks", "Anything else", K.TEXTAREA, sensitive=True),
        ],
    },
    {
        "slug": "aarti-slot",
        "name": "Aarti slot",
        "description": "A reserved place at an aarti.",
        "requires_capacity": True,
        "fields": [
            *WHO,
            _field("attendees", "How many attending", K.NUMBER, required=True),
            _field("slot", "Which aarti", K.SELECT,
                   options=["Morning", "Evening", "Sandhi Puja"]),
        ],
    },
    {
        "slug": "prasad-delivery",
        "name": "Prasad delivery",
        "description": "Posted to an address. No daily limit, so no capacity to set.",
        "requires_capacity": False,
        "fields": [
            *WHO,
            _field("address", "Delivery address", K.TEXTAREA, required=True, sensitive=True),
            _field("pin_code", "PIN code", required=True),
            _field("deliver_after", "Deliver on or after", K.DATE),
        ],
    },
]

BY_SLUG = {template["slug"]: template for template in TEMPLATES}


def apply_template(service, slug: str) -> int:
    """Give a service the template's questions. Returns how many were created.

    Only ever adds: a key the service already declares is left alone, so
    applying a template to a live service cannot silently rewrite a question
    that bookings have already answered.
    """
    template = BY_SLUG.get(slug)
    if template is None:
        return 0

    existing = set(service.fields.values_list("key", flat=True))
    created = 0
    for order, spec in enumerate(template["fields"], start=1):
        if spec["key"] in existing:
            continue
        ServiceField.objects.create(service=service, sort_order=order * 10, **spec)
        created += 1
    return created
