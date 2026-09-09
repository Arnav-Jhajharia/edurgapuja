"""Standing a new committee up.

Creating the row is the easy half. A pandal whose page is blank is not onboarded
— the committee opens their subdomain, sees nothing, and has no idea which of
the twenty things they were meant to fill in first.

So a new pandal is given a palette and a full set of blocks with starter copy in
its own name. Every word is meant to be replaced, and every word says so.
"""

from .blocks import BLOCKS, ORDER
from .models import PageBlock, PandalBrand


def starter_content(pandal, kind: str) -> dict:
    """Placeholder prose that names the committee and invites replacement."""
    name = pandal.name
    return {
        "hero": {
            "eyebrow": f"{pandal.locality.name if pandal.locality_id else pandal.city.name}"
                       f" · {pandal.city.name} · Durga Puja",
            "headline": f"Durga Puja at {name}",
            "standfirst": "Write a few lines here about this year's puja — the theme, "
                          "the idol, what makes the pandal worth the queue.",
            "primary_cta": "Donate Now",
            "secondary_cta": "Explore Services",
        },
        "marquee": {"items": [name, "Durga Puja 2026", pandal.city.name]},
        "about": {
            "headline": f"About {name}",
            "body": "Tell visitors who the committee is and how long the puja has run.",
            "pillars": [
                {"title": "The theme", "body": "What this year's pandal is built around."},
                {"title": "The idol", "body": "Who made it, and in what style."},
                {"title": "The neighbourhood", "body": "What the puja means to the para."},
            ],
        },
        "services": {"headline": "Thoughtful extras for your visit.",
                     "standfirst": "Anything your committee offers beyond darshan."},
        "passes": {"headline": "Skip the queue.",
                   "standfirst": "Your pass lives on your phone and works "
                                 "without a signal at the gate."},
        "donate": {"headline": "Support the Celebration.",
                   "body": "Say what a donation pays for — the pandal, the prasad, the lights.",
                   "card_eyebrow": "Choose your offering", "card_title": "Keep the light burning."},
        "visit": {"headline": "Plan your visit.",
                  "standfirst": "Timings, directions and what to expect."},
        "closing_cta": {"headline": "Come and see for yourself.",
                        "body": "One last line before the footer."},
        "footer": {"blurb": f"{name} · {pandal.city.name}"},
    }.get(kind, {})


def scaffold(pandal) -> int:
    """Give a new pandal a palette and a page. Returns how many blocks were made.

    Only ever adds. Running it again on a committee that has started writing
    leaves every word of theirs alone.
    """
    PandalBrand.objects.get_or_create(pandal=pandal)

    existing = set(pandal.blocks.values_list("kind", flat=True))
    made = 0
    for block in BLOCKS:
        kind = block["kind"]
        if kind in existing:
            continue
        PageBlock.objects.create(
            pandal=pandal, kind=kind, language="en", sort_order=ORDER[kind],
            is_visible=True, content=starter_content(pandal, kind),
        )
        made += 1
    return made
