"""What each block on the landing page is made of.

One description, three consumers: the seed writes blocks against it, the admin
API serves it so the editor builds itself, and the renderer reads the same keys.
Before this, the shape of a hero block lived in three places — the seed command,
a React component and an admin table — and only one of them was ever right.

The same principle as a service's form: the *shape* is data, so adding a field
to a block is one entry here rather than an edit in three files.
"""

TEXT, AREA, LIST, PILLARS = "text", "textarea", "list", "pillars"


def f(key, label, kind=TEXT, help_text=""):
    return {"key": key, "label": label, "kind": kind, "help_text": help_text}


#: Ordered as they appear down the page.
BLOCKS: list[dict] = [
    {
        "kind": "hero",
        "name": "Hero",
        "description": "The first thing a visitor sees.",
        "fields": [
            f("eyebrow", "Small line above the headline",
              help_text="e.g. Ballygunge · Kolkata · Durga Puja"),
            f("headline", "Headline"),
            f("standfirst", "Opening paragraph", AREA),
            f("jubilee", "Badge", help_text="e.g. Platinum Jubilee 2026. Leave blank for none."),
            f("primary_cta", "Donate button text", help_text="Defaults to “Donate Now”."),
            f("secondary_cta", "Services button text",
              help_text="Defaults to “Explore Services”."),
        ],
    },
    {
        "kind": "marquee",
        "name": "Scrolling strip",
        "description": "The line of phrases that scrolls under the hero.",
        "fields": [f("items", "Phrases", LIST, "One per line.")],
    },
    {
        "kind": "about",
        "name": "About",
        "description": "Who the committee is and what this year's puja is about.",
        "fields": [
            f("headline", "Headline"),
            f("body", "Body", AREA),
            f("pillars", "Three points", PILLARS, "Each has a title and a sentence."),
            f("link_label", "Link text", help_text="Optional."),
        ],
    },
    {
        "kind": "services",
        "name": "Services section",
        "description": "The heading above your value-added services.",
        "fields": [f("headline", "Headline"), f("standfirst", "Sub-heading", AREA)],
    },
    {
        "kind": "passes",
        "name": "Passes section",
        "description": "The heading above your entry passes. Only shown when passes are on.",
        "fields": [f("headline", "Headline"), f("standfirst", "Sub-heading", AREA)],
    },
    {
        "kind": "donate",
        "name": "Donate",
        "description": "The donation panel.",
        "fields": [
            f("headline", "Headline"),
            f("body", "Body", AREA),
            f("card_eyebrow", "Small line on the card"),
            f("card_title", "Card title"),
        ],
    },
    {
        "kind": "visit",
        "name": "Plan your visit",
        "description": "The heading above your timings and directions.",
        "fields": [f("headline", "Headline"), f("standfirst", "Sub-heading", AREA)],
    },
    {
        "kind": "closing_cta",
        "name": "Closing call to action",
        "description": "The last word before the footer.",
        "fields": [f("headline", "Headline"), f("body", "Body", AREA)],
    },
    {
        "kind": "footer",
        "name": "Footer",
        "description": "The line under everything.",
        "fields": [f("blurb", "Footer text", AREA)],
    },
]

BY_KIND = {block["kind"]: block for block in BLOCKS}
ORDER = {block["kind"]: index * 10 for index, block in enumerate(BLOCKS)}


def allowed_keys(kind: str) -> set[str]:
    """What a block of this kind may store. Anything else is refused.

    Same reasoning as a service's form: content nobody renders is content
    nobody maintains, and it silently rots until somebody debugs a page that
    looks fine in the database.
    """
    return {field["key"] for field in BY_KIND.get(kind, {}).get("fields", [])}
