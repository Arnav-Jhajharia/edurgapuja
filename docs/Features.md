# eDurgaPuja — Features by Actor

What the system does today, organised by who does it.

Every claim here is checked against the code in this repository. Where the
client's written requirement or the demo screens promise something the code does
not do, that is recorded as a gap rather than quietly omitted — §10 collects
them all in one place.

## How to read it

| Sources | |
|---|---|
| **Code** | `backend/` (Django 5.2 + DRF) and `web/` (Next.js 15). The authority for everything marked *Built*. |
| **[D]** | `info/Application Features (3).docx` — the client's written feature list: 11 mobile sections, 15 web modules. |
| **[R]** | `info/Screen Recording 2026-09-08 at 3.29.22 PM.mov` — 89s walkthrough of the admin portal, all four role panels. Decomposed to scene frames and read. |
| **[P]** | The clickable prototype, as recorded in `docs/Understanding.md`. |
| **Graph** | `graphify-out/` — 168 communities over the corpus. Its god nodes are `Pandal` (65 edges), `BaseModel` (62), `ValidationFailedError` (61), `Pass` (46), `User` (42), `Order` (40), `start_purchase()` (39). That ranking is the shape of the domain: a pandal, a person, an order, and one purchase function that touches everything. |

| Status | Meaning |
|---|---|
| **Built** | Code exists and is exercised by tests. |
| **Built, no client** | The API exists; nothing calls it yet (the mobile app and the gate app are not written). |
| **Model only** | A table exists; no endpoint or behaviour reads or writes it. |
| **Not built** | Specified in [D], [R] or [P]; absent from the code. |

---

## 1 · The system in one page

A pass-booking, donation and services platform for Durga Puja pandal-hopping in
Kolkata, built white-label: eDurgaPuja is one tenant, not the platform.

**Two things are deployed.**

- **`backend/`** — a Django REST API. Postgres, Redis, JWT (SimpleJWT), OpenAPI
  via drf-spectacular. Deployed on Railway (`railway.toml`, `Procfile`), static
  files through WhiteNoise, Sentry optional. Migrations and the Super Admin
  bootstrap run on every deploy, before the first request.
- **`web/`** — a Next.js server-rendered tier serving three surfaces: the public
  pandal landing page (resolved from the `Host` header), the shared donation
  link page at `/d/<slug>/<token>`, and the four-panel admin console at
  `/admin`.

**Two things are not built.** The **visitor mobile app** and the **gate app**.
Both have a complete API behind them — §2 and §3 give the endpoint contracts a
client would call.

### The five load-bearing decisions

Everything below is a consequence of one of these. They are recorded in
`docs/Decisions.md` and `docs/Scope-v1.md`; this is where they show up in code.

1. **One order, many lines.** `orders.Order` + `orders.OrderLine`, `kind ∈
   {donation, service_booking, pass}`. Checkout, receipt, refund and revenue
   reporting are written once, over lines — `apps/orders/services.py`.
2. **One capacity primitive.** `inventory.DayCapacity` and `inventory.Hold` are
   abstract; `ServiceDayCapacity` and `PandalDayCapacity` are the two concrete
   owners, and `apps/inventory/operations.py` holds the only six functions that
   move a count. Holds are rows, not a counter, so an expired hold stops
   occupying capacity the instant it expires. A database `CHECK
   (issued_count <= capacity)` is the floor.
3. **Product, then category.** The platform fixes three products — Individual,
   Group, City. Each pandal defines its own categories (Donor, Sponsor, VIP,
   Para Pass, Senior Citizen, anything it invents), and the category carries the
   price. No migration to add one.
4. **The pass authorises; a short-lived code admits.** A `Pass` is durable and
   covers N pandals as N `PassLeg` rows, each admitted independently. The entry
   code is derived on the visitor's own device from a per-leg secret — HMAC-
   SHA256, 180-second step, 8 digits — so entry needs no mobile data on either
   phone. `apps/passes/codes.py`.
5. **Capability flags, not two versions of the page.** `Pandal.sells_passes`,
   `.accepts_donations`, `.offers_services`. Every surface already branches on
   them, so a committee turning passes on is data, not a deploy.

### Actors

| Actor | Where they work | Authority comes from | Status of their client |
|---|---|---|---|
| **Visitor** | Mobile app; the pandal's public website | A verified phone number, or nothing at all for a donation | Website built; **mobile app not built** |
| **Gate volunteer** | Gate app | `pandals.Volunteer`, active, posted at that pandal | **Not built** |
| **Pandal Admin** | `/admin` | `AdminMembership(role=pandal_admin, pandal=…)` | Built |
| **Sponsor Admin** | `/admin` | `AdminMembership(role=sponsor_admin, organisation=…)` | Built |
| **Sub-Sponsor Admin** | `/admin` | `AdminMembership(role=sub_sponsor_admin, organisation=…)` where the organisation has a `parent` | Built |
| **Super Admin** | `/admin` | `AdminMembership(role=super_admin)`, no scope | Built |
| **The platform** | No UI | The payment provider's webhook signature; deploy-time configuration | Built |

**The tab does not grant the role.** In the demo the login screen has four tabs
[R], and that is presentation only. In the code, `/admin/me` reports which
panels to *render*, and every queryset in `apps/adminapi/views.py` is narrowed by
`request.admin` regardless — choosing a different tab shows a different screen,
never somebody else's data (`apps/adminapi/scope.py`).

---

## 2 · Visitor

The mobile app does not exist. Everything below is the API it would call, in the
order of the journey. The public website already exercises the donation, service
and pass paths.

### 2.1 Identity — Built

Identity is the mobile number (D10). Email and date of birth are profile data,
never credentials.

| Feature | Endpoint | Notes |
|---|---|---|
| What sign-in to offer | `GET /auth/methods` | So the client does not hard-code it. Also reports when a shared development password is in play, so a demo build can say out loud that it is one. |
| Request a code | `POST /auth/otp/request` | One endpoint for sign-up *and* sign-in, and the reply is identical either way — it must not reveal whether a number is registered. Returns `resend_after_seconds`. |
| Verify | `POST /auth/otp/verify` | Creates the account if the number is new; stamps `phone_verified_at`; returns `access`, `refresh`, `user`, `is_new_user`. Accepts `preferred_language`. |
| Password sign-in | `POST /auth/password/login` | The second door (D11). Wrong password, no password set, unknown number and deactivated account all answer identically — and a missing account still spends the time a real check would, so it is not detectable by latency. |
| Set a password | `POST /auth/password/set` | Needs a live session, so a phone number alone cannot claim an account by giving it one. |
| Refresh | `POST /auth/token/refresh` | Access 1 hour, refresh 30 days, rotation on, blacklist after rotation. |
| Sign out | `POST /auth/logout` | Blacklists this device's refresh token. An already-invalid token is not an error: they asked to be signed out, and they are. |
| Profile | `GET` `PATCH /me` | First/last name, email, date of birth, gender, state, city, PIN, profile types, language. `profile_completeness` is computed over six fields and drives the app's "Profile 30% complete" card. |
| Profile types | `GET /profile-types` | Senior Citizens, Families with Young Children, Specially Abled, Press, Social Media Influencer — master data, not a hard-coded list. |

**Limits, as promised by the contract** (`apps/accounts/otp/service.py`,
`config/settings/base.py`): 6-digit code, 300s TTL, 5 attempts, 60s resend
cooldown, 8 sends per hour per destination, plus DRF throttles `otp 8/hour` and
`login 10/hour`. Issuing a new code consumes any live one for that
destination and purpose. Codes are stored as an HMAC of `destination:code` and
compared with `hmac.compare_digest`.

**Phone numbers** are normalised to E.164 through `phonenumbers` with
`DEFAULT_PHONE_REGION = "IN"` before anything stores or compares them.

**Languages**: `en`, `bn`, `hi`.

**The shared development password.** `DEV_LOGIN_PASSWORD` opens any active
account so a demo does not need six SMS codes. It is fenced twice: the
authenticator ignores it unless `DEBUG` is on, and the system check
`accounts.E001` (`apps/accounts/checks.py`) **refuses to start the server** if it
is set while `DEBUG` is off.

### 2.2 Discovery and the pandal page — Built

| Feature | Endpoint | Notes |
|---|---|---|
| Resolve a host | `GET /site/resolve?host=` | `{status: ok, slug}` or `{status: redirect, permanent: true, redirect_to}`. A renamed pandal keeps its old subdomain alive forever (`PandalDomainAlias`), and a committee may bring its own domain. |
| Browse | `GET /pandals` | Published and active only. `?city=`, `?locality=`, `?search=` over name, theme and locality. Paginated, 25 per page. |
| One pandal | `GET /pandals/{slug}` | The structured record. |
| **The whole page** | `GET /pandals/{slug}/page` | One round trip renders everything: pandal, SEO, capabilities, brand palette, ordered content blocks, visit facts, donation presets, services *with their form fields*, pass configurations, live status. Honours `Accept-Language` with an English fallback. `Cache-Control: public, max-age=60`, `Vary: Accept-Language`. |

`donation_offerings`, `services` and `passes` come back **empty when the
capability is off**, so the client iterates and reads capabilities and needs no
change when a committee switches passes on.

**Not built** — [D] mobile §3 asks for filters by distance, popularity, theme,
availability, pass type and special facilities; nearby-by-location with consent;
and sorting. `PandalViewSet` carries only city, locality and text search
(FR-031…034).

### 2.3 Donations — Built

Money given against nothing. It consumes no inventory, has no symmetric
reversal, and needs no account at all.

| Feature | Endpoint | Notes |
|---|---|---|
| Open a shared link | `GET /d/{pandal_slug}/{token}` | Returns the pandal, suggested amount and purpose. Never cached: a link the committee has just switched off must stop collecting now. |
| Donate | `POST /donations` | Public. Either `offering_id` (a preset with a purpose) or `amount_paise` (min 100 paise = ₹1). `donor_name` left blank **is** how a donor stays anonymous, and the receipt then carries no name. Optional `message`, `link_token` for attribution, `phone`. Send an `Idempotency-Key`. Returns `order_id`, `donation_id` and a payment intent. |
| Poll the order | `GET /orders/{id}` | Open to anyone holding the id — a donation may have no account behind it, and the id is an unguessable UUIDv7 carrying nothing sensitive. |
| Receipt | `GET /orders/{id}/receipt` | Exists only once the money has actually arrived. |

Web surfaces: the `Donate` block on the landing page and the dedicated
`/d/<slug>/<token>` page, which leads with the specific ask rather than dropping
the visitor at the top of a marketing page. A switched-off link says so plainly
and offers the pandal's own page instead. Shared links are `noindex`.

### 2.4 Value-added services — Built

C6 resolved in code: **a service belongs to its pandal, and so does the shape of
its form.** There is no service type enum — the five shapes in
`apps/services/templates.py` are starting points, not a closed set.

| Feature | Endpoint | Notes |
|---|---|---|
| What is offered | `GET /pandals/{slug}/services` | Each service carries its own questions, so a client can render a form for a service the platform has never heard of (FR-133). |
| Places left | `GET /services/{id}/availability?from=&to=` | So a client greys out what is gone instead of letting somebody reach checkout and be refused. |
| Book | `POST /service-bookings` | Signed in — a booking has a person attached and has to reach them. **Holds the place first, then creates the order**, for 15 minutes (`CAPACITY_HOLD_TTL_SECONDS`). Returns `409 capacity_unavailable` carrying how many are left. |
| My bookings | `GET /service-bookings`, `GET /service-bookings/{id}` | Scoped to the caller. |

**What a booking may say.** `details` is validated against the questions the
service actually declares (`services.validate_details`): an unknown key is
**refused, never stored**, and a required question must be answered. Gotra, a
disability, a name to be chanted — these exist only because a service asked for
them, and one that did not ask cannot hold them (FR-258). Field kinds are
`text`, `textarea`, `phone`, `email`, `number`, `date`, `time`, `select`,
`checkbox`; each is coerced and range-checked on the way in.

`is_sensitive` marks a field as personal rather than logistical. It changes no
validation — it is what an export or a retention sweep filters on, and what
tells an admin screen to warn before showing a column.

A service with `requires_capacity: false` (prasad posted to your house) takes no
date, holds nothing, and is confirmed the moment it is paid for.

### 2.5 Passes — Built, no client

A pandal appears to sell passes only once `sells_passes` is on; until then every
route here 404s for it.

| Feature | Endpoint | Notes |
|---|---|---|
| What is on sale | `GET /pandals/{slug}/passes` | Product, category, price, date range and — except for a City Pass — the entry window. |
| Places left | `GET /pandals/{slug}/pass-availability?from=&to=` | Per day at that pandal. |
| City coverage | `GET /pass-configs/{id}/coverage` | Which pandals a City Pass would cover, before buying it. |
| Buy | `POST /passes` | `config_id`, `visit_date`, `party_size`, optional `pandal_ids` (the City subset), `contact_phone`. Send an `Idempotency-Key`. |
| My passes | `GET /passes`, `GET /passes/{id}` | Each with its legs and each leg's state. |
| Provision the device | `GET /passes/{id}/legs/{leg_id}/secret` | Holder only, and refused until the pass is paid for — the secret is the whole of what a phone needs to produce a code. |

**What buying does** (`apps/passes/purchase.py`). One purchase can touch several
pandals. A City Pass covers every pandal selling passes in that city, narrowed
to a chosen subset, and **consumes one place at each of them** on its date. The
hold is a hold per leg, and the surrounding transaction makes it all-or-nothing:
a sold-out fourth pandal rolls back the three holds already placed. Then one
order, one line, billed once, however many pandals it covers.

**Rules enforced, with the field named** rather than as an `IntegrityError`:
only a Group Pass may cover more than one person; a City Pass carries no time
(a database `CHECK` says so too); the date must be inside the configuration's
range; a pandal with no `PandalDayCapacity` row for that date is not admitting
visitors that day.

**Late payment is all-or-nothing** (`apps/passes/fulfilment.py`). A City Pass
whose fourth pandal sold out while the payment cleared is not delivered as a
three-quarter pass — the visitor would discover the shortfall at a gate, at
night, in a crowd. Every leg is released, already-issued places are given back,
and the pass is cancelled for refund.

**Pass state**: `active` · `used` · `cancelled` · `expired` · `blocked`.
**Leg state**: `pending` · `visited` · `void`. Admitting the last leg marks the
pass `used`.

### 2.6 The entry code — Built, no client

Two decisions pull in opposite directions: the code is short-lived (D1) and
entry must work offline (D5). A server-minted code satisfies the first and fails
the second, so the code is **derived, not minted**.

- At purchase each leg gets a `LegSecret` — 64 random bytes.
- The phone computes `HMAC-SHA256(secret, counter)`, truncated RFC-4226-style to
  **8 digits**, where `counter = floor(now / 180)`.
- The QR payload is `EDP1:<leg_id>:<counter>:<code>`.
- The gate accepts the neighbouring step in each direction (`DRIFT_STEPS = 1`),
  because a volunteer's tablet drifting ninety seconds must not turn away a
  genuine pass.
- Nothing is transmitted at the gate. Verification is `hmac.compare_digest`.

The code is *not* the authorisation. `Pass.status` and `PassLeg.state` decide
whether somebody may enter; the code only proves the phone at the gate is the
phone that bought the pass.

### 2.7 Payment — Built

One payment path, not one per product (Scope §4.2).

`POST /donations`, `POST /service-bookings` and `POST /passes` all return a
payment intent: `{provider, provider_order_id, key_id, amount_paise, currency}`.
The client hands that to the gateway's checkout widget, then polls
`GET /orders/{id}` while the webhook settles it.

`Idempotency-Key` is honoured on all three; the same key returns the original
attempt rather than charging twice, and a race on one key returns the winner's
row.

Razorpay is the intended provider. Signature verification is real and needs no
SDK; order creation is stubbed until credentials exist (`StubProvider`), so the
whole flow is testable end to end without network.

### 2.8 Operations a visitor sees — Built

| Feature | Endpoint | Notes |
|---|---|---|
| Live status | `GET /pandals/{slug}/live-status` | Estimated wait and crowd level, with `age_seconds` — a stale reading must *look* stale. Deliberately outside the page cache. |
| Lost & found | `GET /pandals/{slug}/lost-items` | Outstanding items only. Public. |
| Report a lost item | `POST /lost-items` | Signed in. |
| Support / feedback | `POST /support-requests` | Public — this is also the landing page's "Talk to our team". Subjects: general, donation, service, feedback. |

### 2.9 The visitor app's endpoint contract, by journey

```
launch          GET  /auth/methods
                GET  /profile-types
sign up / in    POST /auth/otp/request            {phone}
                POST /auth/otp/verify             {phone, code, preferred_language}
                  ↳ access, refresh, user, is_new_user
                POST /auth/password/login         (alternative door)
profile         GET  /me · PATCH /me
discover        GET  /pandals?city=&search=
                GET  /pandals/{slug}
                GET  /pandals/{slug}/page         ← one call renders everything
                GET  /pandals/{slug}/live-status  ← poll separately, never cached
donate          GET  /d/{slug}/{token}            (if opened from a shared link)
                POST /donations                   + Idempotency-Key
                GET  /orders/{id}                 poll until paid
                GET  /orders/{id}/receipt
book a service  GET  /pandals/{slug}/services     ← includes each form's fields
                GET  /services/{id}/availability?from=&to=
                POST /service-bookings            + Idempotency-Key
                GET  /orders/{id} → receipt
                GET  /service-bookings
buy a pass      GET  /pandals/{slug}/passes
                GET  /pandals/{slug}/pass-availability?from=&to=
                GET  /pass-configs/{id}/coverage  (City only)
                POST /passes                      + Idempotency-Key
                GET  /orders/{id} → receipt
my passes       GET  /passes · GET /passes/{id}
at the gate     GET  /passes/{id}/legs/{leg_id}/secret   ← once, while online
                (then compute EDP1:<leg_id>:<counter>:<code> offline, forever)
help            GET  /pandals/{slug}/lost-items
                POST /lost-items
                POST /support-requests
session         POST /auth/token/refresh · POST /auth/logout
```

Errors always arrive in the same envelope — see §9.

### 2.10 Not built for the visitor

Each of these is in [D], [R] or [P] and has no code behind it.

| | Where it was promised |
|---|---|
| The **eligibility questionnaire** — six configurable questions, Approved/Pending/Not Eligible, a drop-off funnel, residency as a bar to buying | [R] Super Admin *Users & Eligibility*, [P]. Not in [D]. Nothing in the code. |
| **Groups** as durable named entities (*Shib Mandir Squad · 18 Pujas*) | [P], [R]. Q2 in `docs/Decisions.md` asks whether they still exist. |
| **Coupons** and the **₹5 marketplace fee** | [P] checkout. `Order` has `platform_fee_paise` and `discount_paise` columns; nothing sets them. |
| **Wallet** as a payment method | [P]. `PaymentOrder.Method` includes `wallet`, but no stored-value machinery exists. |
| **Notifications and push** — booking confirmation, reminders, announcements, deep links, per-user preferences | [D] mobile §9, web §13. Entirely absent. |
| **Cancellation and refunds** by the visitor | [D] §5, §6. `Refund` is a model with no flow. |
| **Pandal promotional CMS** — gallery, events and schedules, awards, parking, transport, accessibility, sponsor logos, versioning and an approval workflow | [D] mobile §4 / web §4. The block system covers hero, marquee, about, services, passes, donate, visit, closing CTA and footer; the media-heavy sections are not there. |
| **Multiple passes in one booking, each with its own QR** | [D] §7. The model issues one pass covering many pandals instead — a deliberate difference, recorded in D1. |
| **Downloadable / shareable pass QR** | [D] §7. Killed by D1: a code that dies in three minutes cannot be shared. |
| **Accessibility guarantees** — screen-reader labels, contrast, tap targets | [D] mobile §10. No client to assess. |
| **FAQ / help centre** | [D] mobile §11. |

---

## 3 · Gate volunteer

The gate app is not built. The API is, and it is designed for a device that is
offline for an hour at a time.

**Who they are.** A `pandals.Volunteer` row — a user, a pandal, optionally a
named `Gate`, and `is_active`. There is no separate volunteer login: they sign
in through the ordinary visitor endpoints. `IsGateStaff`
(`apps/passes/views.py`) checks the posting **on every call**, not once at
sign-in, so deactivating a volunteer ends their ability to scan on the next
request.

| Feature | Endpoint | Status | Notes |
|---|---|---|---|
| Download the day | `GET /gate/manifest?pandal=&date=` | Built, no client | Everything needed to admit people for one pandal on one day, fetched while the device still has signal: `leg_id`, `secret`, `pass_code`, `category`, `product`, `party_size`, `slot_from`, `slot_to`. Only pending legs on active passes. |
| Report a scan | `POST /gate/scan` | Built, no client | `gate_id`, `payload`, `scanned_at` (the *device's* clock), `device_id`, and optionally `override` + `override_reason`. |

**A refusal is a 201 carrying the reason, not an HTTP error** — the gate app
needs it back to show the volunteer. Five outcomes:

| Result | When |
|---|---|
| `admitted` | Code verifies, leg pending, pass active, visit date is today, and no earlier admission exists. |
| `expired` | The code does not verify — either forged, or genuine and older than its three minutes. Both read the same to the volunteer: try again. |
| `duplicate` | The leg is already `visited`, or two devices raced and this one lost the unique index. |
| `invalid` | Not one of our payloads; a genuine code for the pandal next door; an unknown or voided leg; a leg with no secret; a pass that is not active; the wrong date. |
| `manual_override` | An authorised exception, which **must** carry a reason or the request is refused. It consumes the same single admission as a normal one. |

**A leg is admitted once, ever.** That is a partial unique index over scans whose
result is `admitted` or `manual_override` — not a lock and not a read-then-write.
Two gates scanning the same phone in the same second both write and exactly one
wins, and it stays true when a device syncs a scan from an hour ago.

Manual override is present in the code even though no screen in [P] or [R] has
it; [D] web §11 requires it. Q6 in `docs/Decisions.md` asks whether it is still
wanted now that gates work offline.

### Not built for the gate

- **The gate app itself.**
- **A volunteer's own scan history.** [P] shows *Last 10 Scans*; [D] web §12 asks
  for "View Scan History". `GET /admin/scans` exists but is pandal-admin
  authority, not the volunteer's own.
- **Batched scan upload.** `GateScanView`'s docstring says it "accepts a batch,
  because a device that was offline for an hour has an hour of them to send at
  once" — but `ScanSerializer` describes a single scan and the view processes
  one. Either the serializer needs a list form or the docstring is wrong. This
  is the one discrepancy in the offline story.
- **Gate-wise and slot-wise entry reports** ([D] web §11).

---

## 4 · Pandal Admin

Scoped to their own pandals by `AdminMembership`, everywhere, in the queryset.
`PandalScopedViewSet` does the narrowing once so no subclass can forget it.

### 4.1 Signing in

| Endpoint | Notes |
|---|---|
| `POST /admin/auth/otp/request` | A distinct OTP *purpose* (`admin_login`), so a visitor's code will not open the console. |
| `POST /admin/auth/otp/verify` | Returns tokens plus the caller's roles. A verified number with no admin membership is refused in words indistinguishable from a wrong code, so this cannot be used to discover who the administrators are. |
| `POST /admin/auth/password/login` | Same silence, same rate limit. |
| `GET /admin/auth/methods` | As the visitor's. |
| `GET /admin/me` | Which panels to render, and the pandals and organisations each is scoped to. |

### 4.2 The committee's website — Built

| Feature | Endpoint |
|---|---|
| The committee record — name, contact, city, locality, address, theme (English and Bengali), capabilities, opening dates, SEO title and description, active flag | `GET` `PATCH /admin/pandals` |
| Re-fill any missing page block | `POST /admin/pandals/{id}/scaffold` |
| What every block is made of, so the editor builds itself | `GET /admin/pandals/page-schema` |
| Read the page's blocks | `GET /admin/pandals/{id}/blocks` |
| Edit one block, **creating it if the page has none** | `PATCH /admin/pandals/{id}/blocks/{kind}` |
| Palette and fonts | `GET` `PATCH /admin/pandals/{id}/brand` |
| "Plan your visit" facts | `/admin/visit-facts` CRUD |
| Cities and localities, as a picker | `GET /admin/cities`, `GET /admin/localities` |

**Nine block kinds**, ordered down the page: `hero`, `marquee`, `about`,
`services`, `passes`, `donate`, `visit`, `closing_cta`, `footer`. Each declares
its own fields in `apps/pandals/blocks.py` — one description, three consumers
(the seed, the admin API, the renderer). Content is checked against that schema:
**a key nothing renders is refused rather than stored.**

**`PUT` on a pandal is refused with a reason** — it would blank every field not
sent. **The slug is settable once and then frozen**: it is a subdomain people
have already been given, so moving it is a rename with a permanent redirect
(FR-248), not a field edit. Omit it on create and it is derived from the name and
made unique.

**Colours must be hex.** They land in the page as CSS custom properties, and a
typo is not a bad field but a page that renders with no colour at all — which
the committee sees before anybody tells them.

**Publishing is a Super Admin decision** (`POST /admin/pandals/{id}/publish`),
even though the draft → pending_review → published states are the pandal's own.

### 4.3 Donations — Built

| Feature | Endpoint |
|---|---|
| Preset amounts with a purpose ("₹501 · Support a diya") | `/admin/donation-offerings` CRUD |
| Shareable campaign links, each reporting how many donations it produced | `/admin/donation-links` CRUD |
| Every donation, newest first, filterable by `?received=` | `GET /admin/donations` |
| Revenue grouped by what was bought | `GET /admin/revenue?pandal=&from=&to=` |

A donation is **read-only** to an admin: it is a financial record, not something
to edit. Revenue is grouped by `order_line.kind`, so passes appear in the same
report rather than as a new one (Scope §4.5).

### 4.4 Services and the form builder — Built

This is the richest admin surface in the codebase.

| Feature | Endpoint |
|---|---|
| The services offered | `/admin/services` CRUD |
| Starting points for a form | `GET /admin/services/templates` |
| Add a template's questions to an existing service | `POST /admin/services/{id}/apply-template` |
| Reorder the questions | `PUT /admin/services/{id}/reorder` |
| The questions themselves | `/admin/service-fields` CRUD |
| Places per day, set for a whole range at once | `GET` `PUT /admin/services/{id}/capacity` |
| Who booked what | `GET /admin/service-bookings` |

**Six templates** ship: `blank`, `curated-tour`, `puja-in-your-name`,
`special-assistance`, `aarti-slot`, `prasad-delivery`. Nothing in the codebase
branches on which was used — they exist so a committee adding "Puja in your
name" does not have to remember that a sankalp needs a gotra. A template only
ever **adds**, so applying one to a live service cannot rewrite a question
bookings have already answered.

**A question's `key` cannot change once it exists.** The key is the name every
stored booking answered under; renaming it would orphan them all. The label is
what a visitor sees and is free to change.

A new service is created **with a form rather than none** — a service with no
questions cannot be booked usefully, and an admin who has just typed a name and
a price should not have to discover that.

### 4.5 Passes — Built

| Feature | Endpoint |
|---|---|
| The pandal's own categories — Donor, Sponsor, VIP, Para Pass, Senior Citizen, anything | `/admin/pass-categories` CRUD |
| The configuration grid: product, category, price, date range, entry window, max party size | `/admin/pass-configs` CRUD |
| Every edit to one row, with the counts at that moment | `GET /admin/pass-configs/{id}/changes` |
| How many the pandal will admit each day | `GET` `PUT /admin/pandals/{id}/day-capacity` |
| Passes covering this pandal | `GET /admin/passes?status=&q=` |
| The entry log | `GET /admin/scans?result=` |
| The Passes & Payments screen in one call | `GET /admin/pass-summary` |

This is [R]'s *Pass Configuration* grid and its *Pass Configuration History*,
built. Every create and update writes a `PassConfigChange` carrying a JSON
snapshot of the row plus issued and remaining counts at that instant — because
the question asked after the Puja is always "what was it selling for on
Ashtami", and the row itself only knows what it says today.

**Day capacity cannot be cut below what is already issued**, and the message
names the number. The database refuses it too.

`GET /admin/passes` is scoped **through the leg**, not the pass: a City Pass
belongs to no single pandal, so each pandal on it sees it and sees only its own
leg's state.

`GET /admin/scans` is read-only. A scan is a fact, and editing it would be
editing whether somebody came in.

`GET /admin/pass-summary` returns capacity, issued, available, legs pending and
visited, pass revenue, scans admitted and refused, and a breakdown by category.

### 4.6 Sponsorship, from the pandal's side — Built

| Feature | Endpoint |
|---|---|
| What this pandal offers a sponsor: value, pass count, banner placements, benefits, validity | `/admin/packages` CRUD |
| Offer a package to a sponsor | `GET` `POST /admin/allocations` |

An allocation is **pending until the sponsor accepts**, and the passes are
unusable before that — acceptance, not allocation, is what credits a pool
(FR-152).

### 4.7 People — Built

| Feature | Endpoint |
|---|---|
| Named scanning positions — "Gate 1", "Ticket Desk" | `/admin/gates` CRUD |
| Gate staff, with a gate assignment and an active flag | `/admin/volunteers` CRUD |
| Who can sign in to the console | `GET` `POST` `DELETE /admin/staff` |

**Granting access *is* naming a phone number.** Sign-in is by mobile and code,
so there is no credential to generate, send or ever display (FR-237, D7) — which
is the answer to [R]'s sub-sponsor table showing passwords in clear text. The
account is created if it does not exist yet, so the person's first sign-in works
rather than failing at the code screen.

A pandal admin may add **pandal admins to their own pandals and nothing else**,
and **nobody may remove their own access** — cheap to check, and the alternative
is a committee locking itself out of its own console on a Friday night.

### 4.8 Operations — Built

| Feature | Endpoint |
|---|---|
| Wait time and crowd level shown to visitors | `GET` `PUT /admin/pandals/{id}/live-status` |
| Digital lost & found | `GET` `POST /admin/lost-items` |
| Mark an item reunited | `POST /admin/lost-items/{id}/mark-found` |
| Visitor messages, filterable by `?status=` | `GET /admin/support-requests` |
| Close one, stamping who and when | `POST /admin/support-requests/{id}/resolve` |

### 4.9 Not built for the Pandal Admin

- **Sponsor pass-allocation history** as a screen ([R] *Sponsors*) — the data
  exists via `/admin/allocations` and `/admin/issuances`; the pandal-side view is
  not assembled.
- **Bulk / group pass allocation** and **manual pass issuance** to a named
  visitor ([D] web §5). Sponsors can issue from a pool; a pandal cannot issue a
  complimentary pass directly, though `Pass.Source.COMPLIMENTARY` exists.
- **Blackout dates and slot closure** ([D] web §5). `PandalDayCapacity.is_open`
  and `PassConfig.slot_cap` exist; only `is_open` is settable, and `slot_cap` is
  never read.
- **Exports** to CSV/XLSX/PDF ([D] web §14).
- **OG image, latitude and longitude, custom domain** — columns on `Pandal` with
  no field in `AdminPandalSerializer`, so they cannot be set through the API.
- **Volunteer scan history** ([D] web §12).

---

## 5 · Sponsor Admin

A sponsor is an `Organisation` with no `parent`. **A pool belongs to an
(organisation, pandal) pair** (D6): a sponsor holding packages at five pandals
holds five pools, and the console shows them separately and as a rollup. The
single aggregate figure in [R] is the rollup, not a balance.

| Feature | Endpoint | Notes |
|---|---|---|
| The panel's opening figures | `GET /admin/sponsor/overview` | Organisations, packages, allocations, the 50 most recent issuances, every pool, a rollup of granted/transferred/issued/available, and the pending allocations waiting on an answer. |
| The pools themselves | `GET /admin/pools` | One row per organisation per pandal. |
| Accept or decline an offer | `POST /admin/allocations/{id}/accept` · `/decline` | Accepting credits the pool. Answering an allocation offered to somebody else is refused. |
| Sell passes down to a sub-sponsor | `POST /admin/pools/{id}/transfer` | Quantity and price per pass. |
| Hand passes out | `POST /admin/pools/{id}/issue` | See below. |
| Where the passes went | `GET /admin/issuances` | |
| Create and manage sub-sponsors | `/admin/organisations` CRUD | Name, contacts, and `price_per_pass_paise` — what this sponsor charges *that* sub-sponsor. |
| Branding creatives | `GET` `POST` `PATCH /admin/creatives` | |

**Three rules on a transfer**, enforced in `sponsorship/operations.py` and not
trusted to the caller: a sub-sponsor buys only from its own parent (FR-159);
passes stay at the pandal they were granted for; and the hierarchy goes no
deeper than `MAX_POOL_DEPTH` (default 1, because Q-164 is still open).

**The pool invariant is enforced three times over** — a `CHECK` constraint
(`transferred_out <= granted - issued`), a `SELECT … FOR UPDATE` row lock, and
the tests. Outflow never exceeds the grant, at every tier, under concurrent
operation (FR-163).

**Issuing has two modes**, and the difference matters:

- **With a `visit_date`** it mints real `Pass` rows, provisions their leg
  secrets, and **consumes the pandal's capacity for that day** — a sponsor's
  guest occupies a place at the gate exactly like a paying visitor (D2). It is
  refused if the pandal is not admitting visitors that date, or if the day is
  full. `apps/passes/sponsor_issue.py`.
- **Without one** it moves the pool's counter and records the handover only,
  which is what a sponsor doing its own distribution off-platform wants.

**Branding entitlement is enforced at upload, not caught later** (D8). A sponsor
cannot create more live placements than its package grants, and **pending and
approved both occupy one** — otherwise a sponsor could queue unlimited uploads
and exceed its package the moment they were approved. [R]'s "2 placements · 3 in
use" state is unreachable. Selecting several pandals for one upload creates one
row per pandal, so approval and expiry are decided per pandal.

**A sponsor may edit its sub-sponsors' terms, never its own** — its own
`price_per_pass_paise` is what the *pandal* charges *it* — and may never
re-parent a sub-sponsor under someone else's pool.

### Not built for the Sponsor Admin

- **"Request Additional Passes"** ([R]). `sponsorship.PassRequest` is a model
  with no endpoint.
- **Money on a transfer.** `PoolTransfer` carries an `order` foreign key, and
  both `transfer()` and `buy_from_parent()` are called with `order=None` — so a
  sub-sponsor's purchase moves passes without taking payment. The commercial
  half of D6/FR-160 is not wired.
- **Sponsor logo upload** as a distinct artefact ([R] *Sponsor Logo*).
  Creatives carry an image; a logo does not.
- **Branding impressions and clicks** ([D] web §14).
- **Invoices, payment history and receipts** for the sponsor's own spend
  ([D] web §9). `paid_to_parent_paise` is computed from completed transfers;
  there is no invoice.
- **Sponsor communication and supporting documents** ([D] web §7).

---

## 6 · Sub-Sponsor Admin

An `Organisation` **with** a `parent`. It shares the `IsSponsorAdmin` permission
and therefore the same endpoints, narrowed to its own organisation.

| Feature | Endpoint | Notes |
|---|---|---|
| Overview and pools | `GET /admin/sponsor/overview`, `GET /admin/pools` | Passes in pool, issued, total, and what it has paid its sponsor. |
| **Buy from its own sponsor** | `POST /admin/sponsor/buy` | `{pandal, quantity}`. It cannot buy from a pandal, and it cannot choose the price — that is the one its parent set when creating it. Refused outright if the caller is a sponsor rather than a sub-sponsor. |
| Issue passes | `POST /admin/pools/{id}/issue` | Same two modes as a sponsor. |
| Branding | `/admin/creatives` | Same entitlement rule. |

**It cannot create sub-sponsors** while `MAX_POOL_DEPTH = 1`. The schema permits
any depth on purpose — whether a sub-sponsor may itself have sub-sponsors is
Q-164, still open — so the policy limit is a setting, not a migration.

Everything in §5's "Not built" list applies here too, and the missing payment leg
bites hardest: [R] shows a *Buy Passes* modal with UPI, a UPI ID field and a
**Pay ₹0** button, and the code moves the passes with no order behind it.

---

## 7 · Super Admin

Everything the other three panels do, unscoped, plus the platform-only
decisions. `AdminContext.is_super` short-circuits every scoping call.

| Feature | Endpoint | Notes |
|---|---|---|
| Platform totals | `GET /admin/dashboard` | Pandals total / published / selling passes, users, revenue, donations, confirmed service bookings, **and every queue waiting on somebody**: new support requests, open lost items, pending allocations, creatives pending review. |
| Onboard a committee | `POST /admin/pandals` | Creates the pandal **and scaffolds it** — a palette plus all nine blocks with starter copy in the committee's own name. Every word is meant to be replaced and every word says so. A blank subdomain is not an onboarded committee. |
| Publish a page | `POST /admin/pandals/{id}/publish` | draft → pending_review → published. |
| Add a locality | `POST /admin/localities` | Onboarding a committee in a para nobody has entered yet should not be a database ticket. |
| Approve or reject a creative | `POST /admin/creatives/{id}/review` | With a rejection reason, stamped with who and when. |
| The people directory | `GET /admin/users`, `GET /admin/users/{id}` | `?q=` over mobile, name and email; `?admins_only=true`. Read-only and deliberately thin: an operator needs to find a person and see what authority they hold, not to browse donor histories. |
| Grant any role, any scope | `/admin/staff` | |

**Where the first Super Admin comes from.** Every other administrator is granted
by somebody who is already one, which leaves the first with nowhere to come
from. So it is configuration: `BOOTSTRAP_ADMIN_PHONE` and
`BOOTSTRAP_ADMIN_PASSWORD`, applied by `manage.py bootstrap_admin` on **every**
deploy — idempotent, does nothing unless told to, and can sit in the start
command and be forgotten about. Rotating that password is a variable change and
a redeploy, not a shell session.

### Naming, fixed before it reached the routes (D9)

[R]'s Super Admin *Groups* screen is a pandal master and its *Donations* screen
is a combined revenue report. In the code they are `pandals` and `revenue`.

### Not built for the Super Admin

- **Users & Eligibility** — the whole eligibility module (§2.10).
- **Notification and campaign management** ([D] web §13) — templates, audience
  segmentation, scheduling, delivery history, approval workflow, deep links.
- **Reports & analytics** ([D] web §14) — slot utilisation, occupancy, pandal
  performance, sponsor entitlement utilisation, payment reconciliation reports,
  workforce utilisation, exports.
- **Configuration & master data** as screens ([D] web §15) — pass types, slot
  types, fee configuration, event categories, sponsor packages as platform
  master data, branding locations, notification templates, cancellation rules,
  system parameters. `BrandingPlacement` is platform-level master data with no
  admin endpoint at all; it is created only by `seed_admins`.
- **Login history and an administrative audit trail** ([D] web §1) — see §10.
- **`+ Add User`** ([R]). Accounts are opened by verifying a number.
- **MFA for privileged roles.** D11 recommends password **plus** OTP for Super
  Admin specifically, since phone-plus-OTP alone is a single factor and a SIM
  swap would be enough to take the platform. Not implemented.

---

## 8 · The platform itself

No user interface. These run on their own.

| Feature | Where | Notes |
|---|---|---|
| **Payment webhook** | `POST /payments/webhooks/razorpay` | Verify, store, acknowledge — *then* interpret. A plain Django view, not a DRF one: it must not depend on content negotiation, authentication or throttling, and it needs the raw body to check the signature before anything parses it. |
| **Signature verification** | `apps/payments/providers.py` | HMAC-SHA256 over the raw body, compared in constant time. Real even in the stub provider. |
| **Event deduplication** | `PaymentEvent` unique on `(provider, event_id)` | A redelivery is a no-op returning 200, not application logic. Reconciliation reads this table, not the logs. |
| **Fulfilment dispatch** | `payments.services._fulfil` | On capture: mark the order paid, mint a receipt number, then fulfil each line by kind — donation, service booking or pass. Idempotent throughout, because webhooks redeliver. |
| **Release on failure** | `payments.services._release` | A failed payment gives capacity back at once rather than waiting for the hold to lapse. |
| **Health** | `GET /healthz` | Liveness plus its two hard dependencies, database and Redis. Returns 503 degraded rather than raising. Not under `/api/v1`. |
| **API documentation** | `GET /api/schema/`, `GET /api/docs/` | drf-spectacular. Seven models have a field called `status` with entirely different choices; `ENUM_NAME_OVERRIDES` names all twelve of them so every generated SDK gets one readable type per concept. |
| **Deploy sequence** | `Procfile` / `railway.toml` | `migrate → collectstatic → bootstrap_admin → gunicorn`, health-checked at `/healthz`. |
| **Seeds** | `seed_pandals`, `seed_passes`, `seed_admins` | Complete landing pages; passes switched on separately, on purpose, so "a pandal may or may not sell passes" stays honestly represented in development; and one account per panel with enough sponsorship to make them non-empty. |

**Celery is configured and has no tasks.** `config/celery.py` exists, broker and
result backend point at Redis, `acks_late` and `reject_on_worker_lost` are set —
and there is no `tasks.py` anywhere. In particular `expire_holds` is defined for
both owners and never scheduled. That is by design: holds are rows with an
expiry, so an expired hold stops occupying capacity whether or not a sweeper has
run. Housekeeping only; correctness does not depend on it.

---

## 9 · Cross-cutting mechanics

Every actor above depends on these.

### One error envelope

```json
{ "error": { "code": "capacity_unavailable",
             "message": "Only 2 places remain.",
             "fields": { } } }
```

A code is a stable string a client may branch on, not a sentence it has to
parse. DRF field errors are re-reported as **422**, because the contract
reserves 400 for a malformed request and 422 for one that parsed but cannot be
accepted.

| Code | Status | Extra |
|---|---|---|
| `validation_failed` | 422 | `fields` |
| `otp_invalid` | 400 | `attempts_left` |
| `otp_expired` | 400 | |
| `otp_rate_limited` | 429 | `retry_after` |
| `invalid_credentials` | 401 | |
| `capacity_unavailable` | 409 | `available` |
| `hold_expired` | 409 | `available` |
| `pool_exhausted` | 409 | `available` |
| `invalid_transfer` | 400 | |
| `allocation_not_pending` | 409 | |
| `not_authenticated` · `permission_denied` · `not_found` | 401 · 403 · 404 | |

### Identity and session

JWT via SimpleJWT: **access 1 hour, refresh 30 days, rotation on, blacklist
after rotation.** SimpleJWT's five-minute default is right for a phone hitting
an API in bursts and wrong for a console somebody keeps open all evening while
the pandal is running. Rotation with blacklisting means a stolen refresh token
is usable exactly once before the real device's next rotation invalidates it.

Both web clients (`lib/admin.ts`, `lib/visitor.ts`) share **one in-flight
refresh promise**: a dashboard fires six requests that expire together, and six
concurrent refreshes would burn five rotated tokens and sign the admin out.

### Throttling

`otp 8/hour` · `login 10/hour` · `anon 60/min` · `user 600/min`. `login` is
scoped like OTP because it is the same thing — an unauthenticated attempt to
sign in as somebody, and the one endpoint where guessing is possible at all.

### Money

Stored, compared and summed in **paise**, as `BigIntegerField`. `rupees()` is
display only. Non-negativity is a database `CHECK` on every amount column.

### Identifiers

**UUIDv7** primary keys everywhere (`apps/common/uuid7.py` via
`common.BaseModel`) — unguessable, so an order id can be handed to an anonymous
donor, and time-ordered, so inserts do not fragment the index.

### Scoping

`apps/adminapi/scope.py` builds an `AdminContext` from the caller's active
memberships once per request and attaches it in the permission class. Four
permissions — `IsAdmin`, `IsPandalAdmin`, `IsSponsorAdmin`, `IsSuperAdmin` —
and the narrowing happens **in the queryset**, never by hiding a button.

### Pagination

25 per page. Every admin list that annotates or aggregates is explicitly
ordered, because paginating an unordered queryset can show a row on two pages
and miss another entirely.

### Multi-tenancy by subdomain (D12)

`<slug>.edurgapuja.app`, resolved from the `Host` header. One wildcard DNS
record and one wildcard certificate; onboarding a committee stays a database
insert. Reserved names (`www`, `api`, `admin`, `app`, `mail`, `static`, …) are
blocked in settings. In development the same code resolves
`<slug>.localhost:3000`, which Chrome handles with no hosts-file editing.

### Production hardening

`config/settings/prod.py`: HSTS one year with subdomains and preload (every
pandal is a subdomain, so leaving them out would exempt the entire public site),
SSL redirect behind Railway's `X-Forwarded-Proto`, secure and HTTP-only cookies,
nosniff, `X-Frame-Options: DENY`, same-origin referrer policy, Argon2 password
hashing, WhiteNoise with compressed manifest storage.

The API and the web tier are separate origins in production; browser calls are
proxied through the pandal's own host by a Next rewrite, so they are same-origin
and CORS never enters the picture.

### Tests

~280 tests across 18 files, including a **property test** over the capacity
primitive and a real-transaction test for the concurrent-admission index. The
capacity module was built for services first, on purpose — the pass work then
reused a module already property-tested and proven under concurrent load, on
something lower-stakes than the festival's entire admission system (Scope §4.3).

---

## 10 · Written but not wired

Tables and settings that exist with nothing reading or writing them. Each is a
decision that was made and then not finished; none is dead weight, but none does
anything today.

| | What it was for | State |
|---|---|---|
| `common.AuditLog` | "Who did what, to which row" (FR-255). Actions: create, update, delete, login, publish, refund. | **Never written to.** No code creates one. [D] web §1 requires a login history and an administrative audit trail. |
| `accounts.StaffInvitation` | Single-use invitation links with a hashed token, so an invitee sets their own secret (FR-237). | **Unused.** Superseded in practice: `/admin/staff` grants access by naming a phone number, which achieves D7's "no credential is ever displayed" without a link. |
| `sponsorship.PassRequest` | A sponsor asking a pandal for more passes (FR-157). [R] has the button. | **No endpoint.** |
| `payments.Refund` | Refund tracking with a provider refund id and status. | **No flow creates one.** Two paths already *log* that a refund is due — a service booking whose place vanished during payment, and a pass whose leg sold out — and nothing acts on it. |
| `pandals.PandalDomainAlias` | Old subdomains kept alive forever as permanent redirects (FR-248). | **Read** by `/site/resolve`; no endpoint creates one, so a rename cannot actually be performed. |
| `Pandal.custom_domain`, `og_image`, `latitude`, `longitude` | Bring-your-own domain (FR-249), social preview image, map pin. | Columns exist; **absent from `AdminPandalSerializer`**, so unsettable through the API. |
| `PassConfig.slot_cap` | An optional sub-limit under the pandal's day capacity. | **Never read.** The pandal total is the binding ceiling (D2). |
| `Order.platform_fee_paise`, `discount_paise` | The ₹5 marketplace fee and coupons [P]. | Columns exist and are summed; **nothing ever sets them non-zero.** |
| `PaymentOrder.Method.WALLET` | Wallet as a payment method [P]. | Enum value only. Q9 asks what a wallet even is. |
| `Pass.Source.COMPLIMENTARY` | A pass issued without payment. | Enum value only; no path produces one. |
| `SetPasswordView` | Setting or changing a password. | Calls `set_password` directly and **never runs `AUTH_PASSWORD_VALIDATORS`**, so the configured minimum of 10 characters is not enforced — the serializer's own `min_length=8` is the only check. Worth reconciling. |
| `GateScanView` batching | The docstring promises a batch endpoint for a device that was offline. | `ScanSerializer` takes a single scan. See §3. |

---

## 11 · Still open

From `docs/Decisions.md`, unchanged by anything in the code. Ordered by how much
they block.

| # | Question | What it blocks |
|---|---|---|
| **Q8** | Does the platform settle money it collects, or does the gateway split it at source? Razorpay Route with each committee as a sub-merchant is the right answer — and **every committee needs KYC and bank details before it can take a single rupee**, which has a lead time measured in weeks and runs in parallel with nothing. | Payment-aggregator status. The biggest commercial question in the project, and the likeliest critical path. |
| **Q2** | Do the named groups from the prototype still exist? D4 defines a Group Pass as a family buying several passes, which is a different thing entirely. | Nine requirements (FR-120…128). |
| **Q11** | What does an eligibility verdict grant or refuse — access, price or priority? And what happens to the ID and address evidence collected in questions three and four? | The whole eligibility module and its retention rules. |
| **Q12** | Retention periods for personal data, eligibility evidence, scan logs and payment records. v1 already collects gotra, sankalp and assistance requirements — religious affiliation and disability — so it needs a retention period and an access rule even if both are provisional. | Data-protection posture. `is_sensitive` on a service field is the hook that is already in place for it. |
| **Q4** | Can a Group Pass be any category, or only Donor? | Pricing and the category model. |
| **Q5** | At the gate, does a family of four scan once, or four times? Today one leg admits once regardless of `party_size`. | The code-to-admission relationship. |
| **Q6** | Is manual-exception admission still wanted alongside offline gates? It is built either way. | Gate app scope. |
| **Q7** | Are the four bespoke services the same catalogue as the pandal-defined ones? | Answered in code — one catalogue, owned by the pandal — but not confirmed by the client. |
| **Q9** | What is the Wallet: stored value we hold, or a pass-through? | Whether the platform owes anyone a balance. |
| **Q10** | Whose cost is a coupon, and is the marketplace fee refunded on cancellation? | Settlement. |
| **Q-164** | May a sub-sponsor create its own sub-sponsors? | `MAX_POOL_DEPTH`, currently 1. The schema already permits any depth. |
| **—** | Load, uptime and retention targets. No source gives a peak-concurrency figure. This is a five-day event where a whole city books in the same fortnight and scans on the same evenings. | Capacity planning. |

---

## Where to look next

| Document | What it is |
|---|---|
| `docs/Understanding.md` | The evidence, before any code existed. Built from the docx, the recording and the prototype, and nothing else. |
| `docs/Decisions.md` | The client's answers, D1–D12, and what each one kills and forces. |
| `docs/Scope-v1.md` | What ships now, what is deferred, and the six seams that cost little now and are expensive to retrofit. |
| `docs/FunctionalRequirements.md` | FR-001…FR-260. The single source of requirement IDs, referenced by every commit message. |
| `docs/Endpoints.md` | Every route the backend serves today, with who may call it. |
| `docs/ApiContract-v1.md` | Conventions, headers, and the three flows that can break. |
| `docs/DataModel.md` | The target schema, including tables not yet built. |
| `docs/CodeTour.md` | The codebase explained for someone learning Django. |
| `docs/walkthrough/` | Module-by-module reading order: config, common, geo/accounts, pandals, inventory/services. |
| `graphify-out/GRAPH_REPORT.md` | The knowledge graph: god nodes, communities, cohesion scores, and an honest audit trail. |
