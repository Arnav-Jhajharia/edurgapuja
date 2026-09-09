# Endpoints

Everything the backend serves today. Base URL `/api/v1`.

Sponsorship is reachable only through the admin API, below.

**Who can call what:** *public* needs nothing, *signed in* needs a bearer token
from `/auth/otp/verify`, *provider* is called by Razorpay and authenticated by
signature.

---

## Accounts

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` | `/auth/methods` | public | Which sign-in options this deployment offers, so the client does not hard-code them. Also says when a shared development password is in play, so a demo build can say out loud that it is one. |
| `POST` | `/auth/otp/request` | public | Sends a one-time code to a mobile number. The same endpoint for sign-up and sign-in, and the reply is identical either way so it never reveals whether a number is registered. |
| `POST` | `/auth/otp/verify` | public | Checks the code and returns an access and refresh token. Creates the account if the number is new. |
| `POST` | `/auth/password/login` | public | The second door: phone and password. Every failure — wrong password, no password set, no such account, deactivated — answers identically, so this cannot be used to discover which numbers hold accounts. Rate-limited like OTP. |
| `POST` | `/auth/password/set` | signed in | Gives this account a password, or changes it. Needs a live session, so a phone number alone cannot claim an account by giving it one. |
| `POST` | `/auth/token/refresh` | public | Exchanges a refresh token for a fresh access token. |
| `POST` | `/auth/logout` | signed in | Ends this device's session by blacklisting its refresh token. |
| `GET` | `/me` | signed in | The signed-in visitor's profile, including how complete it is. |
| `PATCH` | `/me` | signed in | Updates name, email, date of birth, gender, city, state, PIN, profile types and language. |
| `GET` | `/profile-types` | public | The list of profile types — Senior Citizens, Press and so on. |

### Signing in

OTP is the primary route (D11) — nothing to remember, nothing to reuse. A
password is offered alongside it, for people who would rather type one than wait
for an SMS.

**The shared development password.** `DEV_LOGIN_PASSWORD` opens any active
account, so a demo does not need six SMS codes. It is fenced twice: the
authenticator ignores it unless `DEBUG` is on, and a Django system check
(`accounts.E001`) **refuses to start the server** if it is set while `DEBUG` is
off. In this repo's `.env` it is `password`.

It is a convenience for development and must never be set on a deployed
environment — the check exists so that one forgotten environment variable is a
failed boot rather than every account on the platform.

---

## Pandals and the landing page

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` | `/site/resolve?host=` | public | Turns an incoming host into a pandal slug, or into a permanent redirect if the pandal was renamed or uses its own domain. |
| `GET` | `/pandals` | public | Browses published pandals. Filter by `city` or `locality`, search with `?search=`. |
| `GET` | `/pandals/{slug}` | public | One pandal's structured record, for the app. |
| `GET` | `/pandals/{slug}/page` | public | **Everything the landing page renders, in one request** — brand colours, content blocks, donation presets, services, visit facts and live status. |
| `GET` | `/pandals/{slug}/live-status` | public | Wait time and crowd level, with how old the reading is. Fetched separately so it is never served from the page cache. |
| `GET` | `/pandals/{slug}/lost-items` | public | Items still unclaimed at that pandal. |

---

## Donations

| | Endpoint | Who | What it does |
|---|---|---|---|
| `POST` | `/donations` | public | Starts a donation and returns a payment intent. No account needed; leaving the name blank donates anonymously. Send an `Idempotency-Key` header so a retry never charges twice. |
| `GET` | `/d/{pandal_slug}/{token}` | public | Resolves a shared donation link to its pandal, suggested amount and purpose. |

---

## Services

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` | `/pandals/{slug}/services` | public | What that pandal offers, with prices and **the questions each booking form asks**. There is no service type — a service is whatever the committee decided to offer, and its form is data the client renders. |
| `GET` | `/services/{id}/availability` | public | Places left per day. Takes `?from=` and `?to=` dates. |
| `POST` | `/service-bookings` | signed in | Holds a place for fifteen minutes and returns a payment intent. Returns `409 capacity_unavailable` with the number left if it is sold out. A service with `requires_capacity: false` takes no `date` and holds nothing — there is nothing that could run out. `details` may carry **only** the keys that service declares; anything else is refused rather than stored. |
| `GET` | `/service-bookings` | signed in | The caller's own bookings. |
| `GET` | `/service-bookings/{id}` | signed in | One booking. |

---

## Orders and receipts

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` | `/orders/{id}` | public | The state of an order — poll this while a payment settles. Open to anyone holding the id, because a donation may have no account behind it. |
| `GET` | `/orders/{id}/receipt` | public | The receipt. Exists only once the money has actually arrived. |

---

## Payments

| | Endpoint | Who | What it does |
|---|---|---|---|
| `POST` | `/payments/webhooks/razorpay` | provider | Receives payment callbacks. Verifies the signature, stores the event, then pays the order and fulfils it. A redelivered event is a no-op. |

---

## Support and lost property

| | Endpoint | Who | What it does |
|---|---|---|---|
| `POST` | `/support-requests` | public | Submits a support request or feedback. Also serves the landing page's "Talk to our team". |
| `POST` | `/lost-items` | signed in | Reports a lost item. Reading a pandal's list is public and lives under `/pandals/{slug}/lost-items`. |

---

## Service

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` | `/healthz` | public | Liveness, plus whether the database and Redis are reachable. Not under `/api/v1`. |
| `GET` | `/api/schema/` | public | The OpenAPI schema. |
| `GET` | `/api/docs/` | public | Browsable API documentation. |

---

## Passes

A pandal sells passes only once it has switched them on; until then every route
here answers 404 for it and the landing page carries an empty `passes` block.

**Product then category.** The platform fixes three products — Individual, Group,
City — and each pandal defines its own categories (Sponsor, VIP, Para Pass,
Senior Citizen, Donor, anything it invents), which carry the price.

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` | `/pandals/{slug}/passes` | public | What that pandal is selling: product, category, price, dates and, except for a City Pass, the entry window. |
| `GET` | `/pandals/{slug}/pass-availability` | public | Places left per day, so a client greys out what is gone instead of letting somebody reach checkout and be refused. Takes `?from=` and `?to=`. |
| `GET` | `/pass-configs/{id}/coverage` | public | Which pandals a City Pass would cover, before buying it. |
| `POST` | `/passes` | signed in | Buys one. Holds a place at **every** pandal the pass covers, then bills once; a single sold-out pandal rolls the whole purchase back. Returns a payment intent. Send an `Idempotency-Key`. |
| `GET` | `/passes` | signed in | The caller's own passes, each with its legs. |
| `GET` | `/passes/{id}` | signed in | One pass, and where each leg stands. |
| `GET` | `/passes/{id}/legs/{leg_id}/secret` | holder | Provisions the device to generate entry codes **offline**. Refused until the pass is paid for, because the secret is the whole of what a phone needs to produce a code. |

### What a service may ask

A service declares its own questions, so a committee can offer a bhog coupon, a
pushpanjali slot or a dhunuchi-naach registration without waiting for anybody.
The kinds are `text`, `textarea`, `phone`, `email`, `number`, `date`, `time`,
`select` and `checkbox` — they describe how to render an input and how to check
what comes back, not what the question means.

Two rules survive from when the platform owned the forms, and they are the ones
that mattered:

* **A booking may submit only what its service asks.** Gotra, a disability, a
  name to be chanted — these exist only because a service asked, and a service
  that did not ask cannot hold them (FR-258).
* **A required question must be answered**, or the form is decoration and the
  volunteer finds out at the gate.

A question marked `is_sensitive` is personal rather than logistical. It changes
no validation; it is what an export or a retention sweep filters on.

### The entry code

A pass authorises; a short-lived code admits. The code is *derived*, not minted:
at purchase each leg gets a secret, the visitor's phone keeps it, and both sides
compute the same value from that secret and the clock — three-minute step,
eight digits, one neighbouring step accepted for clock drift. Nothing is
transmitted at the gate, which is the point: in a crowd of fifty thousand there
is no mobile data on either phone.

The QR payload is `EDP1:<leg_id>:<counter>:<code>`.

### The gate

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` | `/gate/manifest?pandal=&date=` | gate staff | Everything a device needs to admit people for one pandal on one day, downloaded while it still has signal. Carries leg secrets, so it is restricted to volunteers posted at that pandal and scoped to a single pandal-date. |
| `POST` | `/gate/scan` | gate staff | Reports one scan. **A refusal is a 201 carrying the reason**, not an HTTP error — the gate app needs it back to show the volunteer. `scanned_at` is the device's own clock, because a device that was offline reports an hour later. |

A leg is admitted **once, ever**. That is a partial unique index over scans whose
result is `admitted` or `manual_override`, so two gates scanning the same phone
in the same second both write and exactly one wins — and it stays true when a
device syncs a scan from an hour ago. A manual override (a dead phone battery,
an ID checked by hand) is an admission like any other and consumes the same one.

---

## Admin

Base URL `/api/v1/admin`. One API behind all four panels: which panel a person
sees is decided by the roles in `/admin/me`, but **every queryset is narrowed by
the caller's own memberships regardless**, so choosing a different tab in the
client shows a different screen, never somebody else's data.

*pandal admin* is scoped to their own pandals, *sponsor admin* to their own
organisations, *super admin* to everything. Where a row below says *pandal
admin*, a super admin may call it too.

### Signing in

| | Endpoint | Who | What it does |
|---|---|---|---|
| `POST` | `/admin/auth/otp/request` | public | Sends an admin login code. Same machinery as a visitor's, a different purpose, so a visitor's code will not open the admin. |
| `POST` | `/admin/auth/otp/verify` | public | Returns an access and refresh token plus the caller's roles. A verified number with no admin membership is refused in words indistinguishable from a wrong code, so this cannot be used to discover who the admins are. |
| `POST` | `/admin/auth/password/login` | public | Phone and password into the console. A number that is not an administrator's is refused in words indistinguishable from a wrong password. |
| `GET` | `/admin/auth/methods` | public | As `/auth/methods`, for the console's sign-in screen. |
| `GET` | `/admin/me` | any admin | Which panels to render, and the pandals and organisations each is scoped to. |

### Pandal admin — money and visitors

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` | `/admin/revenue` | pandal admin | Donations and bookings totalled, grouped by what was bought. |
| `GET` `POST` `PATCH` | `/admin/donation-offerings` | pandal admin | The preset amounts on the pandal's page. |
| `GET` `POST` `PATCH` | `/admin/donation-links` | pandal admin | Shareable donation links, each reporting how many donations it produced. |
| `GET` | `/admin/donations` | pandal admin | Every donation to this pandal, newest first. |
| `GET` `POST` `PATCH` | `/admin/services` | pandal admin | The value-added services offered. `type` is a free-text grouping label, not a category to pick from. On create, `template` fills the form with a starting set of questions. |
| `GET` | `/admin/services/templates` | pandal admin | Starting points for a form — suggestions, not a catalogue. A service may end up asking nothing any of them ask. |
| `POST` | `/admin/services/{id}/apply-template` | pandal admin | Adds a template's questions to an existing service. Only ever adds: a question already written is never overwritten. |
| `PUT` | `/admin/services/{id}/reorder` | pandal admin | The order the questions are asked, by key. |
| `GET` `POST` `PATCH` `DELETE` | `/admin/service-fields` | pandal admin | The questions one service asks: label, kind, required, help text, choices, and whether the answer is personal. The **key cannot change** once it exists — bookings are stored under it. |
| `GET` `PUT` | `/admin/services/{id}/capacity` | pandal admin | Places per day, set for a whole date range at once. A service with no day rows cannot be booked. |
| `GET` | `/admin/service-bookings` | pandal admin | Who booked what, and for when. |
| `GET` `PUT` | `/admin/pandals/{id}/live-status` | pandal admin | The wait time and crowd level visitors see, stamped with how old the reading is. |
| `GET` `POST` | `/admin/lost-items` | pandal admin | The digital lost & found. |
| `POST` | `/admin/lost-items/{id}/mark-found` | pandal admin | Marks an item reunited. |
| `GET` | `/admin/support-requests` | pandal admin | Visitor messages. |
| `POST` | `/admin/support-requests/{id}/resolve` | pandal admin | Closes one, stamping who and when. |
| `GET` `POST` `PATCH` | `/admin/gates`, `/admin/volunteers` | pandal admin | The people and entrances at the pandal. |
| `GET` `POST` `PATCH` | `/admin/visit-facts` | pandal admin | The timings and directions shown on the page. |

### Pandal admin — the site

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` `PATCH` | `/admin/pandals` | pandal admin | The committee's own record — name, contact, theme, dates, SEO, and which capabilities its page offers. `PUT` is refused; it would blank every field not sent. The `slug` is settable once and frozen after: it is a subdomain people have already been given, so moving it is a rename with a redirect (FR-248), not a field edit. |
| `POST` | `/admin/pandals` | super admin | Onboards a committee. Creates the pandal **and scaffolds it** — a palette plus all nine page blocks with starter copy in the committee's own name. A blank subdomain is not an onboarded committee. If `slug` is omitted it is derived from the name and made unique. |
| `POST` | `/admin/pandals/{id}/scaffold` | pandal admin | Fills in any block the page is missing, leaving written ones alone. |
| `GET` | `/admin/pandals/page-schema` | pandal admin | What every block is made of, so the editor builds itself rather than hard-coding a shape that drifts from what the page renders. |
| `GET` | `/admin/cities` | any admin | Cities with their localities, so onboarding is a picker rather than a request to go and find two UUIDs. |
| `GET` `POST` | `/admin/localities` | read: any admin · write: super admin | Adding a para nobody has entered yet should not be a database ticket. |
| `GET` `POST` `DELETE` | `/admin/staff` | pandal admin | Who can sign in to which console. Sign-in is by mobile and code, so granting access **is** naming a phone number — there is no credential to generate, send or display (FR-237), and the account is created if it does not exist. A committee may add pandal admins to its own pandals and nothing else; nobody may remove their own access. |
| `GET` `PATCH` | `/admin/pandals/{id}/brand` | pandal admin | The committee's palette and fonts. Colours must be hex — they land in the page as CSS custom properties, and a typo is not a bad field but a page with no colour, which the committee sees before anybody tells them. |
| `GET` | `/admin/pandals/{id}/blocks` | pandal admin | The page's content blocks. |
| `PATCH` | `/admin/pandals/{id}/blocks/{kind}` | pandal admin | Edits one block, **creating it if the page has none** — asking a committee to add a block before they can write in it would be our storage leaking into their afternoon. Content is checked against the block's schema: a key nothing renders is refused rather than stored. |
| `POST` | `/admin/pandals/{id}/publish` | super admin | Publishing is a platform decision, not a committee's. |

### Sponsorship

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` `POST` `PATCH` | `/admin/packages` | pandal admin | What a pandal offers a sponsor: passes, placements, benefits. |
| `GET` `POST` | `/admin/allocations` | pandal admin | Offers a package to a sponsor. Passes are unusable until accepted. |
| `POST` | `/admin/allocations/{id}/accept`, `/decline` | sponsor admin | The sponsor's answer. Accepting credits their pool. |
| `GET` | `/admin/sponsor/overview` | sponsor admin | Everything the sponsor panel renders: pools, packages, allocations, issuances and a rollup. |
| `GET` | `/admin/pools` | sponsor admin | One row per organisation per pandal — a sponsor at five pandals holds five pools. |
| `POST` | `/admin/pools/{id}/transfer` | sponsor admin | Sells passes down to a sub-sponsor at a stated price. Refused beyond the pool, with the number left. |
| `POST` | `/admin/pools/{id}/issue` | sponsor admin | Hands passes to a named recipient and records the handover. |
| `POST` | `/admin/sponsor/buy` | sub-sponsor admin | Buys from **its own sponsor**, never from a pandal, at the price that sponsor set. Refused if the caller is a sponsor rather than a sub-sponsor. |
| `GET` | `/admin/issuances` | sponsor admin | Where the passes went. |
| `GET` `POST` `PATCH` | `/admin/organisations` | sponsor admin | Sub-sponsors. A sponsor may edit its own children's terms, never its own and never re-parent one. |
| `GET` `POST` | `/admin/creatives` | sponsor admin | Branding uploads. Refused beyond the package's placement entitlement rather than queued. |
| `POST` | `/admin/creatives/{id}/review` | super admin | Approving a creative is a platform decision. |

### Passes

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` `POST` `PATCH` | `/admin/pass-categories` | pandal admin | The pandal's own names for who a holder is. No migration to add one. |
| `GET` `POST` `PATCH` | `/admin/pass-configs` | pandal admin | The configuration grid: product, category, price, dates, entry window. A City Pass carrying a time is refused with the field named. |
| `GET` | `/admin/pass-configs/{id}/changes` | pandal admin | Every edit to that row, with the counts at the moment it was made — the question after the Puja is always what it was selling for on Ashtami. |
| `GET` `PUT` | `/admin/pandals/{id}/day-capacity` | pandal admin | How many the pandal will admit each day. Set as a range. Cannot be cut below what is already issued. |
| `GET` | `/admin/passes` | pandal admin | Passes covering the caller's pandals, scoped through the leg — a City Pass shows to each pandal on it, and each sees only its own leg's state. Filter with `?status=` or `?q=` on the pass code. |
| `GET` | `/admin/scans` | pandal admin | The entry log, scoped through the gate. Read-only: a scan is a fact, and editing it would be editing whether somebody came in. Filter with `?result=`. |
| `GET` | `/admin/pass-summary` | pandal admin | The Passes & Payments screen in one call: capacity, issued, revenue, admitted, refused, and a breakdown by category. |
| `POST` | `/admin/pools/{id}/issue` | sponsor admin | Hands passes out of a pool. **With** a `visit_date` it mints real passes and consumes the pandal's capacity — a sponsor's guest occupies a place at the gate exactly like a paying visitor. **Without** one it moves the pool's counter only, for a sponsor distributing off-platform. |

### Super admin

| | Endpoint | Who | What it does |
|---|---|---|---|
| `GET` | `/admin/dashboard` | super admin | Platform totals, plus every queue waiting on somebody. |
| `GET` | `/admin/users` | super admin | The people directory. `?q=` searches mobile, name and email; `?admins_only=true` narrows to accounts holding a role. Read-only — an account is opened by verifying a number and closed by its owner. |
| `GET` | `/admin/users/{id}` | super admin | One person, and what authority they hold. |

---

## Errors

Every error looks the same:

```json
{ "error": { "code": "capacity_unavailable",
             "message": "Only 2 places remain.",
             "fields": { } } }
```

| Code | Status | Means |
|---|---|---|
| `validation_failed` | 422 | Something in the request was unacceptable; `fields` says what. |
| `otp_invalid` | 400 | Wrong code. Carries `attempts_left`. |
| `otp_expired` | 400 | The code is spent, expired or superseded. Ask for a new one. |
| `otp_rate_limited` | 429 | Too soon, or too many. Carries `retry_after`. |
| `capacity_unavailable` | 409 | Sold out. Carries `available`. |
| `hold_expired` | 409 | The reservation lapsed before payment landed. |
| `not_authenticated` | 401 | No credential. |
| `permission_denied` | 403 | Signed in, but not for this. |
| `not_found` | 404 | Unknown, or not published. |
