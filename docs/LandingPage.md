# eDurgaPuja — The Pandal Landing Page

Specified from the reference build at `ballygunge-cultural.replit.app`, walked
9 September 2026. This is no longer inferred from a content list; every block
below exists on that page.

**Shape.** One route per pandal, one long page, anchor navigation. Sections are
`#about`, `#donor-pass`, `#donate`, `#services`, `#visit`. That is good for
indexing and for sharing a single link, and it means "deep link to the donate
section" is an anchor rather than a route.

**Each pandal page carries its own visual identity.** The reference page is
terracotta and cream with its own display serif — not the eDurgaPuja palette. A
pandal page is not one template with the words swapped; it is that committee's
brand. This is the thing that was meant by tenancy, and it belongs on the pandal.

---

## The blocks

Rendered in order, each shown or hidden by the pandal's capabilities and by
whether it has content. Adding passes later adds a block; it does not redesign
the page.

### Header — always
Pandal mark and name · tagline (`theme name · jubilee line`) · anchor nav ·
two calls to action, the primary of which is the pandal's own choice.

### Hero — always
Eyebrow (`locality · city · festival`), headline, standfirst, two calls to
action, a soft link ("Know More About Us"), the theme name including its Bengali
form (*Protha · প্রথা*), and a hero image.

### Marquee — optional
A short scrolling strip of the pandal's own words: *Darshan · Curated
Experiences · Accessible Visit*.

### 01 · About — always
Headline, body, a "Discover Our Story" link, an image with a caption, and
**three pillars** — each a number, a title and a line (*Culture & Tradition · Art
& Craft · Community & Celebration*).

### 02 · Donor Pass — only when `sells_passes`
Headline, body, a meta row of three labelled facts (**Visit Information ·
Validity · Availability**), and a pass card carrying a title, up to three benefit
chips (*Dedicated access · Comfortable arrival · Made for community*), a primary
action and a "Know More" link.

**In v1 this block is absent.** It is fully specified here so that turning
`sells_passes` on is content plus a flag, not a design exercise.

### 03 · Donate — when `accepts_donations`
Headline, body, a "Why Donate?" link, and an offering card containing **preset
offerings**. This is the finding that changes the model: a preset is not just an
amount, it is an amount *with a purpose*.

| Amount | Label |
|---|---|
| ₹501 | Support a diya |
| ₹1,001 | Support bhog |
| ₹2,001 | Support the artisans |

Plus a custom amount, a reassurance line, and the donate action.

### 04 · Value-Added Services — when `offers_services`
Headline, standfirst, and numbered service cards — name, description, action
link. The reference pandal offers three: **Donor Darshan · Get Curated Tour ·
Accessible Visit**.

These names match neither earlier list. Each pandal names and chooses its own,
which settles C6 from a third independent direction.

### 05 · Plan Your Visit — always
Four labelled cards — **Pandal Location · Puja Dates · Darshan Timings · Visitor
Information** — and a "View Visit Details" link. Where live status exists, wait
time and crowd level belong in this block.

### Closing call to action — always
Full-width headline, one line of body, up to three actions.

### Footer — always
Pandal name, a short blurb, a navigation column, and contact — location and a
"Talk to our team" action, which is the web entry point to support.

---

## What this adds to the model

### `pandal_brand`
Per-pandal design tokens: primary, accent, surface and ink colours, display and
body typeface, logo, mark. One row per pandal; the page reads it. Without this,
every pandal page looks like every other, which the reference page shows is not
the intent.

### `page_block`
| Column | Notes |
|---|---|
| `pandal_id` | |
| `kind` | `hero` · `marquee` · `about` · `donor_pass` · `donate` · `services` · `visit` · `closing_cta` · `footer` |
| `sort_order`, `is_visible` | |
| `content` | JSON, shaped by `kind` |

Blocks are content, not code. A pandal admin edits copy and imagery without a
release, which is what FR-037's draft-review-publish workflow governs.

### `donation_offering`
| Column | Notes |
|---|---|
| `pandal_id`, `amount_paise`, `label`, `description`, `sort_order`, `is_active` | |

Distinct from `donation_link`. An **offering** is a preset shown on the page
("₹501 · Support a diya"). A **link** is a shareable URL an admin generates for a
campaign. A donation records which of either it came from, so a pandal can see
what its donors actually respond to.

### `visit_fact`
The four Plan Your Visit cards, as label-and-value rows rather than four fixed
columns, so a pandal can say something we did not anticipate.

---

## Questions this raises

| | Question |
|---|---|
| **L1** | *Donor Darshan* is a service and *Donor Pass* is a pass. Are they the same entitlement reached two ways, or two products? The page sells both. |
| **L2** | Does the Donor Pass action open the app, or does a pass get bought on the web as donations and services are? The reference page's button is inert. |
| **L3** | Who writes this content? Every block is bespoke prose — headline, standfirst, three pillars, benefit chips. A pandal admin typing it into a form is a very different product from us producing it per committee, and with fourteen pandals and a month, it is a scheduling question as much as a design one. |
| **L4** | Does each pandal get its own domain or a path on ours? `ballygunge-cultural.replit.app` is a subdomain. That decides certificates, SEO and how the admin creates a page. |
