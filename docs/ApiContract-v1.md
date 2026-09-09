# eDurgaPuja — API Contract, v1

Covers the v1 scope: the pandal landing page, donations, value-added services,
and the identity and payment machinery underneath them. Passes, the gate, pools,
eligibility and groups are absent by design — see `Scope-v1.md`.

Every endpoint traces to a requirement. Where an endpoint exists only so that
passes drop in later without rework, that is said.

---

## 1 · Conventions

**Base.** `https://api.edurgapuja.app/api/v1`. The version is in the path; a
breaking change gets `v2` rather than a flag.

**Hosts.** Each pandal's page lives on its own subdomain (D12) —
`ballygunge-cultural.edurgapuja.app` — and the web tier resolves the pandal from
the `Host` header. The API stays on one origin and still addresses pandals by
slug, so there is exactly one API host to configure, monitor and cache.

Server-rendered reads are server-to-server and never touch CORS. Browser calls
from a pandal page — checkout, live status — are proxied through that page's own
origin at `/api/*`, so they are same-origin too. The API's CORS allowlist is a
pattern over `*.edurgapuja.app` as a backstop, never `*`.

**Cookies.** The admin session is host-only on `admin.edurgapuja.app`, with no
`Domain` attribute. A cookie scoped to `.edurgapuja.app` would be presented to
every pandal subdomain, including pages whose content pandal admins edit.

**Money.** Integer paise, always. Field names end `_paise`. The client formats
rupees; the server never sends a decimal.

**Identifiers.** UUIDv7 as strings. `pass_code`-style human references are
display only and are never accepted as an authenticator.

**Time.** ISO 8601, UTC, `Z`-suffixed. The client renders in Asia/Kolkata.

**Language.** `Accept-Language: en | bn | hi`. Content blocks return the
requested language, falling back to English.

**Authentication.**

| Caller | Mechanism |
|---|---|
| Visitor app | `Authorization: Bearer <JWT>` |
| Landing page, server-rendered | none — public endpoints only |
| Landing page checkout | short-lived checkout token from OTP verification |
| Admin portal | session cookie, `SameSite=Lax`, CSRF token on writes |

**Idempotency.** Every request that can move money requires
`Idempotency-Key: <uuid>`. The same key returns the original response and never
charges twice. Keys are held 24 hours.

**Pagination.** Admin lists take `?page=&page_size=` and return
`{results, count, next, previous}`. Feeds and logs use `?cursor=`.

**Errors.** One envelope, always.

```json
{ "error": { "code": "capacity_unavailable",
             "message": "Only 2 places remain on 12 October.",
             "fields": { "quantity": "Reduce to 2 or fewer." } } }
```

| Code | HTTP | When |
|---|---|---|
| `validation_failed` | 422 | Malformed or missing input |
| `unauthenticated` | 401 | Missing or expired credential |
| `forbidden` | 403 | Authenticated, but not for this pandal |
| `not_found` | 404 | Unknown, or not published |
| `otp_invalid` | 400 | Wrong code |
| `otp_expired` | 400 | Code dead or spent; request another |
| `otp_rate_limited` | 429 | Cooldown or hourly cap; carries `retry_after` |
| `capacity_unavailable` | 409 | Sold out; carries `available` |
| `hold_expired` | 409 | The hold lapsed before payment |
| `payment_failed` | 402 | Gateway declined |
| `provider_unavailable` | 503 | Gateway unreachable; safe to retry |
| `rate_limited` | 429 | Generic throttle |

Every 4xx is actionable by the client. A 5xx is ours.

---

## 2 · Identity

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/auth/otp/request` | none | Send a code. Same endpoint for sign-up and sign-in — the response never reveals whether the number is known (FR-004) |
| `POST` | `/auth/otp/verify` | none | Verify; creates the account if new. Returns tokens and `is_new_user` |
| `POST` | `/auth/token/refresh` | refresh | Rotate |
| `POST` | `/auth/logout` | bearer | End this device's session (FR-013) |
| `GET` | `/me` | bearer | Profile, including `profile_completeness` |
| `PATCH` | `/me` | bearer | First name, last name, email, date of birth, gender, city, state, PIN, profile types, language |
| `GET` | `/profile-types` | none | Master data |

`POST /auth/otp/request`

```json
→ { "phone": "9876543210", "purpose": "login" }
← { "resend_after_seconds": 60 }
```

Any number format is accepted and normalised to E.164 (FR-016). Issuing a code
kills every live code for that number (FR-006).

---

## 3 · The landing page

**One request renders the page.** The web tier is server-rendered, so a page is
one round trip, not eight. This is the most performance-sensitive read in v1
because it is the surface Google and WhatsApp previews hit.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/site/resolve?host=` | none | Map an incoming host to a pandal, or to a redirect (D12) |
| `GET` | `/pandals` | none | Browse and filter (FR-030) |
| `GET` | `/pandals/{slug}/page` | none | Everything the landing page renders |
| `GET` | `/pandals/{slug}` | none | Structured record for the app |
| `GET` | `/pandals/{slug}/live-status` | none | Wait time, crowd level, and its age (FR-186) |
| `GET` | `/pandals/{slug}/lost-items` | none | Outstanding items only (FR-189) |

### Resolving the host

Each pandal is served on its own subdomain (D12), so a cold render begins by
turning a host into a pandal. The web tier cannot simply strip the subdomain:
renamed pandals keep their old names alive as permanent redirects (FR-248), and a
committee may later bring its own domain (FR-249). Both are lookups.

```
GET /site/resolve?host=ballygunge-cultural.edurgapuja.app
← { "status": "ok", "slug": "ballygunge-cultural" }

GET /site/resolve?host=ballygunge-cultural-2025.edurgapuja.app
← { "status": "redirect", "permanent": true,
    "redirect_to": "https://ballygunge-cultural.edurgapuja.app" }

GET /site/resolve?host=nonsense.edurgapuja.app
← 404 not_found
```

Tiny, and cacheable for an hour. It is the only lookup a cold render needs before
the page itself.

`GET /pandals/{slug}/page`

```json
{
  "pandal":       { "id": "…", "slug": "ballygunge-cultural", "name": "…",
                    "locality": "Ballygunge", "city": "Kolkata",
                    "canonical_url": "https://ballygunge-cultural.edurgapuja.app",
                    "theme": { "name": "Protha", "name_local": "প্রথা" } },
  "seo":          { "title": "Ballygunge Cultural Pandal · Durga Puja",
                    "description": "…",
                    "og_image_url": "…",
                    "locales": ["en", "bn", "hi"] },
  "capabilities": { "sells_passes": false,
                    "accepts_donations": true,
                    "offers_services": true },
  "brand":        { "primary": "#B45F1E", "accent": "#E0A66A",
                    "surface": "#FBF3E8", "ink": "#3A1D0C",
                    "display_font": "…", "body_font": "…",
                    "logo_url": "…", "mark_url": "…" },
  "blocks": [
    { "kind": "hero",        "sort_order": 1, "content": { … } },
    { "kind": "about",       "sort_order": 2, "content": { "pillars": [ … ] } },
    { "kind": "donate",      "sort_order": 3, "content": { … } },
    { "kind": "services",    "sort_order": 4, "content": { … } },
    { "kind": "visit",       "sort_order": 5, "content": { "facts": [ … ] } },
    { "kind": "closing_cta", "sort_order": 6, "content": { … } }
  ],
  "donation_offerings": [
    { "id": "…", "amount_paise": 50100,  "label": "Support a diya" },
    { "id": "…", "amount_paise": 100100, "label": "Support bhog" },
    { "id": "…", "amount_paise": 200100, "label": "Support the artisans" }
  ],
  "services": [
    { "id": "…", "name": "Donor Darshan", "type": "curated_tour",
      "description": "…", "price_paise": 75000, "available_days": ["2026-10-10"] }
  ],
  "live_status": { "estimated_wait_minutes": 18, "crowd_level": "medium",
                   "updated_at": "…", "age_seconds": 120 }
}
```

**The `donor_pass` block is simply absent while `sells_passes` is false.** The
client already iterates blocks and already reads capabilities, so turning passes
on adds a block and changes no code (FR-050a, Scope §4.4).

**Caching.** 60 seconds at the edge, keyed by host *and* `Accept-Language`, and
purged on publish — including every alias host that redirects to the same pandal,
or a renamed pandal serves stale content from its old name. Live status is
excluded from that cache and fetched separately, because a wait time that is a
minute old is worse than useless.

**`canonical_url` and `seo` are load-bearing, not decoration.** Subdomains are
near-separate sites to a search engine, which is the point — each committee ranks
for its own name — but it means each page must declare its own canonical and its
own preview card. WhatsApp forwards are how a pandal page will actually spread,
and an unset `og_image_url` is a grey box in every one of them.

---

## 4 · Donations

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/d/{pandal_slug}/{token}` | none | Resolve a shared link to its pandal, amount and purpose (FR-142) |
| `POST` | `/donations` | none or bearer | Start a donation; returns a payment intent |
| `GET` | `/orders/{id}` | owner or checkout token | Poll for a terminal state |
| `GET` | `/orders/{id}/receipt` | owner or checkout token | Receipt (FR-146) |

`POST /donations` — `Idempotency-Key` required

```json
→ { "pandal_id": "…",
    "offering_id": "…",            // or "amount_paise": 50100
    "donor_name": "",              // blank means anonymous (FR-144)
    "message": "Jai Maa Durga!",
    "link_token": "8x2k1p",        // optional, records attribution (FR-050d)
    "phone": "9876543210" }        // optional; required only for a receipt by SMS

← { "order_id": "…",
    "status": "pending",
    "amount_paise": 50100,
    "payment": { "provider": "razorpay", "provider_order_id": "order_…",
                 "key_id": "rzp_…" } }
```

**A donation needs no account.** Anonymous giving skips OTP entirely — only a
purchase that has to reach a phone needs to know the phone (FR-046).

---

## 5 · Services

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/pandals/{slug}/services` | none | What this pandal offers (FR-132) |
| `GET` | `/services/{id}/availability?from=&to=` | none | Remaining places per day |
| `POST` | `/service-bookings` | bearer or checkout token | Hold a place and start payment |
| `GET` | `/service-bookings` | bearer | Mine |
| `GET` | `/service-bookings/{id}` | owner | One |

`GET /services/{id}/availability`

```json
← { "days": [ { "date": "2026-10-10", "available": 12, "capacity": 20 },
              { "date": "2026-10-11", "available": 0,  "capacity": 20 } ] }
```

`POST /service-bookings` — `Idempotency-Key` required

```json
→ { "service_id": "…", "date": "2026-10-12", "quantity": 2,
    "details": { "name_for_puja": "…", "gotra": "…", "sankalp": "…" },
    "phone": "9876543210" }

← { "booking_id": "…", "status": "held",
    "hold_expires_at": "2026-10-09T12:15:00Z",
    "amount_paise": 100200,
    "payment": { "provider": "razorpay", "provider_order_id": "order_…" } }
```

`details` is validated against the service's **type** — the platform owns the
form shape, the pandal owns the offering (FR-133). Unknown keys are rejected
rather than stored, because this is where gotra, sankalp and assistance
requirements live and they are sensitive (FR-258).

Sold out returns `409 capacity_unavailable` with `available`, so the client can
offer the next day rather than a dead end.

---

## 6 · The three flows that can break

The happy paths above are the easy part. These are the branches worth building
deliberately, and they are the reason no separate use-case document exists.

### 6.1 One-time code

```
request ─► 429 otp_rate_limited     cooldown or hourly cap; retry_after given
        └► 200 resend_after_seconds

verify  ─► 400 otp_invalid          attempts incremented, attempts_left returned
        ├► 400 otp_expired          dead, spent, or superseded → request a new one
        └► 200 tokens + is_new_user
```

Codes are stored as an HMAC, never in the clear. Wrong attempts are counted
atomically, so a parallel guessing attack exhausts the allowance rather than
racing past it.

### 6.2 Donation payment

```
POST /donations  →  order.pending  →  gateway checkout  →  visitor pays
                                                              │
        ┌─────────────────────────────────────────────────────┤
        ▼                                                     ▼
  webhook arrives                                    visitor closes the tab
  signature verified                                 before the redirect
  event stored (unique per provider event id)                 │
  order → captured, receipt issued                            │
        └──────────────── same outcome ──────────────────────-┘
```

| Branch | Behaviour |
|---|---|
| Webhook redelivered | `UNIQUE (provider, event_id)` makes it a no-op returning 200 |
| Webhook delayed | Client polls `GET /orders/{id}`, showing "confirming" rather than failure |
| Webhook never arrives | A reconciliation job asks the provider about every order pending beyond fifteen minutes and resolves it |
| Client retries the POST | Same `Idempotency-Key` returns the original order; never a second charge |
| Our processing throws | The event is stored before it is interpreted, and retried until it lands |

**The guarantee:** no captured payment ever ends without either a completed
donation or a completed refund. That is the property to test, not the happy path.

### 6.3 Service booking against capacity

```
POST /service-bookings
   └─ lock the (service, date) row
      ├─ available < quantity  →  409 capacity_unavailable { available }
      └─ place hold (15 min)   →  201 held + payment intent
```

| Branch | Behaviour |
|---|---|
| Two visitors race for the last place | The row lock serialises them; one is held, one gets 409 |
| Visitor abandons checkout | The hold lapses; capacity frees the moment it expires, not when a sweeper runs |
| Payment lands after the hold expired | Re-acquire under the same lock. Still available → confirm. Gone → refund automatically and tell them |
| Payment fails | Hold released immediately rather than left to expire |

The hold-and-issue operations here are the same four operations passes will use
against `pandal_day_capacity` (Scope §4.3). Exercising them on services first is
deliberate.

---

## 7 · Webhooks

| Method | Path | Auth |
|---|---|---|
| `POST` | `/payments/webhooks/razorpay` | HMAC signature header |

Verify the signature over the raw body **before parsing**. Store the event, then
return 200. Interpretation happens on a worker, never in the request. An
unverifiable signature is 400 and is stored nowhere.

---

## 8 · Support and operations

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/support-requests` | none or bearer | From the app or the footer's "Talk to our team" (FR-191) |
| `POST` | `/lost-items` | bearer | Report an item (FR-188) |

---

## 9 · Admin

Session cookie, CSRF on writes. Every response is scoped to the caller's own
pandal unless they are a Super Admin (FR-233). Scope is enforced in the query,
never by hiding a button.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/admin/auth/otp/request` · `/verify` | Sign in by mobile and code (FR-230, D11) |
| `GET` | `/admin/me` | Roles and the pandals they cover |
| `GET` `PATCH` | `/admin/pandals/{id}` | The record |
| `PATCH` | `/admin/pandals/{id}/brand` | Colours, type, logo (FR-050b) |
| `GET` `PUT` | `/admin/pandals/{id}/blocks` | Reorder, show, hide |
| `PATCH` | `/admin/pandals/{id}/blocks/{kind}` | Edit one block's content |
| `POST` | `/admin/pandals/{id}/publish` | draft → review → published (FR-037) |
| `GET` | `/admin/pandals/{id}/preview` | The page as a visitor would see it (FR-040) |
| `GET` `POST` `PATCH` `DELETE` | `/admin/donation-offerings` | Presets (FR-050c) |
| `GET` `POST` `PATCH` | `/admin/donation-links` | Shareable links (FR-140, FR-141) |
| `GET` | `/admin/donations` | Filter by pandal, period, offering, link |
| `GET` `POST` `PATCH` `DELETE` | `/admin/services` | The pandal's own catalogue |
| `PUT` | `/admin/services/{id}/capacity` | Places per day |
| `GET` | `/admin/service-bookings` | With their captured details |
| `PUT` | `/admin/pandals/{id}/live-status` | Wait time and crowd level (FR-185) |
| `GET` `PATCH` | `/admin/lost-items` | List, mark found (FR-190) |
| `GET` `PATCH` | `/admin/support-requests` | List, resolve (FR-192) |
| `GET` | `/admin/revenue?from=&to=&pandal=` | Grouped by `order_line.kind` — passes appear here later with no new endpoint (Scope §4.5) |
| `POST` `GET` | `/admin/exports` | Queue a CSV/XLSX/PDF job, then collect it (FR-226) |
| `POST` | `/admin/pandals` | Super Admin only — onboard a committee (FR-238) |
| `GET` | `/admin/users` | Super Admin only (FR-240) |

Exports are asynchronous. A synchronous export of a festival's donations is a
timeout waiting for the week it matters.

---

## 10 · Deliberately not in v1

`/passes`, `/bookings`, `/entry-codes`, `/scan`, `/pools`, `/eligibility`,
`/groups`, `/branding`, `/volunteers`.

Three of those are already reachable without redesign: `sells_passes` is in the
capabilities payload, `pass` is already a value of `order_line.kind`, and
`/admin/revenue` already groups by that field. Turning passes on adds endpoints;
it does not change these.

---

## 11 · What this contract assumes, still unanswered

| | |
|---|---|
| **L2** | Whether a pass is eventually bought on the web as donations are, or only in the app. It decides whether `POST /passes` is a public checkout endpoint or a visitor-only one |
| **Q8** | Whether the platform settles money or the gateway splits it. Route adds a `transfers` block to the payment intent and a sub-merchant id to every pandal |
| **Q10** | Whether a platform fee applies to a donation. If it does, `POST /donations` returns a fee line and the visitor must see it before paying |
