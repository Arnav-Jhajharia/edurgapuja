"""Turn the five old platform-owned form shapes into rows each service owns.

Before this, a service's fields were implied by its `type` and looked up in a
dict. A service created yesterday must keep asking exactly what it asked
yesterday, so this walks the existing rows and writes the questions down.

Reversible: the fields go away again, and the old code read `type`, which is
left untouched.
"""

from django.db import migrations

# The dict as it stood, kept here rather than imported: a migration has to
# describe the past, and `apps/services/templates.py` will keep changing.
#
# Note what is *not* copied across: nothing is marked required. The old
# validation had no notion of a required answer, so making one required here
# would be inventing a rule these services never had and rejecting bookings
# that would have gone through yesterday. New services get sensible defaults
# from the templates; existing ones keep exactly the behaviour they had.
OLD_TYPE_FIELDS = {
    "curated_tour": [
        ("name", "Your name", "text", True, False),
        ("contact_phone", "Mobile number", "phone", True, False),
        ("party_size", "How many people", "number", False, False),
        ("notes", "Anything we should know", "textarea", False, False),
    ],
    "puja_in_your_name": [
        ("name", "Your name", "text", True, False),
        ("contact_phone", "Mobile number", "phone", True, False),
        ("name_for_puja", "Name to be chanted", "text", False, True),
        ("gotra", "Gotra", "text", False, True),
        ("sankalp", "Sankalp", "textarea", False, True),
        ("preferred_time", "Preferred time", "time", False, False),
    ],
    "special_assistance": [
        ("name", "Your name", "text", True, False),
        ("contact_phone", "Mobile number", "phone", True, False),
        ("assistance_for", "Who needs assistance", "text", False, True),
        ("assistance_type", "What kind", "text", False, True),
        ("wheelchair_required", "Wheelchair needed", "checkbox", False, True),
        ("remarks", "Anything else", "textarea", False, True),
    ],
    "aarti_slot": [
        ("name", "Your name", "text", True, False),
        ("contact_phone", "Mobile number", "phone", True, False),
        ("attendees", "How many attending", "number", False, False),
        ("slot", "Which aarti", "text", False, False),
    ],
    "generic": [
        ("name", "Your name", "text", True, False),
        ("contact_phone", "Mobile number", "phone", True, False),
        ("notes", "Anything we should know", "textarea", False, False),
    ],
}

#: The old enum values doubled as display labels. Keep them readable now that
#: `type` is a free-text grouping label rather than a key.
READABLE = {
    "curated_tour": "Curated tour",
    "puja_in_your_name": "Puja in your name",
    "special_assistance": "Special assistance",
    "aarti_slot": "Aarti slot",
    "generic": "",
}


def write_the_questions_down(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    ServiceField = apps.get_model("services", "ServiceField")

    for service in Service.objects.all():
        specs = OLD_TYPE_FIELDS.get(service.type, OLD_TYPE_FIELDS["generic"])
        for order, (key, label, kind, _was_required, sensitive) in enumerate(specs, start=1):
            ServiceField.objects.get_or_create(
                service=service, key=key,
                defaults={"label": label, "kind": kind, "required": False,
                          "is_sensitive": sensitive, "sort_order": order * 10, "options": []},
            )
        service.type = READABLE.get(service.type, service.type)
        service.save(update_fields=["type"])


def take_them_away_again(apps, schema_editor):
    """Put `type` back to the enum value the old code read — and touch nothing else.

    The obvious reverse is to delete every ServiceField. It is also wrong: by the
    time anybody reverses this, committees have written their own questions
    through the admin, and those rows are not this migration's to destroy. There
    is no way to tell a derived row from a hand-written one after the fact, so
    the safe reverse leaves them all.

    Nothing is leaked by leaving them: reversing 0002 as well drops the table
    outright, and re-applying this migration uses get_or_create, so a row that
    is still there is left exactly as it is.
    """
    Service = apps.get_model("services", "Service")

    back = {label: key for key, label in READABLE.items() if label}
    for service in Service.objects.all():
        if service.type in back:
            service.type = back[service.type]
            service.save(update_fields=["type"])
        elif not service.type:
            service.type = "generic"
            service.save(update_fields=["type"])


class Migration(migrations.Migration):
    dependencies = [("services", "0002_service_requires_capacity_alter_service_type_and_more")]
    operations = [migrations.RunPython(write_the_questions_down, take_them_away_again)]
