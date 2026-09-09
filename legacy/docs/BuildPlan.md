# PujaPass — Build Plan

What gets built, in what order, and why the models look the way they do.

Two milestones. **V0** is one vertical slice: a visitor buys an Individual Pass
covering several pandals, pays, holds it offline, mints an entry code, and walks
through a gate. **V1** adds everything else in the Essential set — Group and City
passes, the sponsor chain, donations, groups, services, support, and the admin
portals.

Requirement IDs are `CLAUDE.md`'s. Story and use case IDs are
`docs/StoriesAndUseCases.md`'s.

---

## 0. Where the code actually is

Six findings from reading what exists. Four of them change what this plan can say,
so they come first.

**The pool model is good and it stays.** `passes/models.py` and
`passes/operations.py` are the strongest part of the codebase: an optional-parent
pool tree with the invariant enforced as a database `CheckConstraint`, holds as
rows rather than a counter, and deterministic lock ordering on transfers. Slice 1
of the build order in `CLAUDE.md` is essentially done. Nothing below asks to
rewrite it.

**But nothing has ever run.** `hypothesis`, `pytest` and `pytest-django` are used by
both test modules and appear in neither `pyproject.toml` nor `uv.lock`. There are no
migrations, no commits, and no database. The invariant is *asserted*, not *verified*.
First job.

**The database is SQLite.** `config/settings.py` still has the `startproject`
default. SQLite serialises writers, so `test_concurrency.py` passes for a reason
that has nothing to do with `select_for_update`. Every concurrency guarantee in
NFR-5 is currently untested. Postgres 16 before anything else is built on top.

**There is no custom user model, and no migrations exist yet.** This is the last
moment it is free. After the first `migrate`, swapping `AUTH_USER_MODEL` is a
multi-hour data migration. Do it in the first commit.

**`operations.issue()` creates `Pass` rows.** That makes the capacity module depend
on the artifact module, and it hard-codes one pass to one pool. Every multi-pandal
requirement — FR-63, FR-69, FR-70, FR-72 — needs one pass drawing from several
pools. §3 works this through; it is the central change in this plan.

**`src/pujapass/` is `uv init` residue.** A `uv_build` src-layout package with a
`main()` that prints "Hello from pujapass!", while the actual Django apps sit at the
repository root. Delete the package and the `[project.scripts]` and
`[build-system]` blocks; this is an application, not a distribution.

---

## 1. Stack

Answers, not options. Where this contradicts `docs/ADR-002.md`, that document is
stale — see §10.

| Question | Answer | Why |
|---|---|---|
| Framework | Django 6.1 | Already chosen and installed. The admin, the ORM's `select_for_update`, and constraint support are the reasons. |
| API layer | **Yes, DRF** — with a rule, see below | Already a dependency. `drf-spectacular` generates the OpenAPI the Dart client is built from (N-34). |
| Database | **Postgres 16 only.** No SQLite, not even for tests. | Partial unique indexes, `CheckConstraint` over `F()` expressions, and real row locks. Concurrency is not observable on SQLite. |
| Auth — mobile clients | JWT via `djangorestframework-simplejwt` | ADR-004. Visitor app and gate app. |
| Auth — admin portal | Session cookies | ADR-004. Same-origin React portal in V1; Django Admin in V0. |
| Background work | Celery + beat, Redis broker | Hold expiry, payment reconciliation, refund retries, gate reconciliation. Redis over a Postgres queue: the single-datastore property is worth less than not writing a broker. |
| Pass authenticity | Ed25519 via PyNaCl | ADR-002. Offline verification at the gate; consumption stays server-authoritative. |
| Testing | pytest + pytest-django + Hypothesis, against real Postgres | Already written this way. Just needs declaring and running. |
| Money | Integer paise, never float. A `Money` value object or plain `PositiveIntegerField` named `_paise`. | Non-negotiable and cheap to get right on day one. |

### The DRF rule

**No `ModelViewSet` on anything that moves capacity or money.**

`ModelViewSet` gives you `create`, `update` and `destroy` that write through the ORM
directly. That is exactly the bypass NFR-33 forbids — "domain logic that moves
capacity is isolated in one module and never bypassed". A `PassViewSet` with a
default `create` would issue a pass without touching `operations.py`, and the
database `CheckConstraint` would be the only thing left standing between us and an
oversold pandal.

So:

- **Read-only catalogue** (pandals, slots, availability) — `ReadOnlyModelViewSet`. Fine.
- **Everything else** — `APIView` or `GenericAPIView` with an explicit serializer for
  input, an explicit call into a domain function, and an explicit serializer for
  output. The view validates and delegates. It does not write.

Serializers validate shape. They do not enforce invariants — those live in
`inventory/operations.py` and in the database, where a serializer cannot be
forgotten.

---

## 2. The app map

Twelve apps. Six in V0.

```
                    accounts          (User, OTP, VisitorProfile)
                       │
        ┌──────────────┼───────────────┐
        │              │               │
   catalogue        groups           orgs            ← V1 for groups, orgs
   (Pandal, Gate,   (Group,          (Organisation,
    Slot, Product)   Membership)      Allocation)
        │              │               │
        └──────────────┴───────┬───────┘
                               │
                          inventory          ← the invariant lives here, alone
                          (Pool, Hold, operations)
                               │
                ┌──────────────┴──────────────┐
                │                             │
             passes                       donations        ← V1
             (Pass, PassLeg,              (Link, Donation,
              EntryCode)                   Receipt)
                │
        ┌───────┼────────┐
        │       │        │
     booking   gate   services         ← services V1
     (Booking, (Device,
      Payment)  ScanLog)
                               support, platform          ← V1
```

Dependencies point **down and never up**. `inventory` knows about `catalogue.Slot`
and `orgs.Organisation` and nothing else. It does not know what a `Pass` is. That is
the correction described in §3.3, and it is what lets one pass draw capacity from
six pools.

| App | V0? | Owns | Serves |
|---|---|---|---|
| `accounts` | ✅ | User, OtpChallenge, VisitorProfile, ProfileType | V-01 – V-06, FR-59 – FR-62 |
| `catalogue` | ✅ | Pandal, Gate, Slot, PassProduct, LiveStatus | V-07 – V-15, PA-01 – PA-10, FR-73 |
| `inventory` | ✅ | Pool, Hold, `operations.py` | NFR-5, the whole capacity chain |
| `passes` | ✅ | Pass, PassLeg, EntryCode | V-19, V-26 – V-28, FR-63 – FR-72 |
| `booking` | ✅ | Booking, BookingLeg, Payment, Refund, Coupon | V-16 – V-25, FR-66 – FR-68, NFR-3 |
| `gate` | ✅ | Device, ScanLog, ScanConflict | G-01 – G-10, NFR-2, NFR-4 |
| `orgs` | ⬜ V1 | Organisation, Package, Allocation, Creative | SP-*, SS-*, PA-24 – PA-29 |
| `groups` | ⬜ V1 | Group, GroupMembership, GroupPandal | V-34 – V-38, FR-64 |
| `donations` | ⬜ V1 | DonationLink, Donation, Receipt | V-39 – V-46, PA-19 – PA-21 |
| `services` | ⬜ V1 | Service, ServiceForm, ServiceBooking | V-47 – V-49, PA-30 – PA-32, FR-76 |
| `support` | ⬜ V1 | LostItem, SupportRequest | V-50 – V-53, PA-15, PA-16 |
| `platform` | ⬜ V1 | MasterData, AuditEntry, Suspension | SA-03, SA-11, SA-12, NFR-15 |

`inventory` is the existing `passes` app renamed and split. `Pandal`, `Slot` and
`Organisation` move out of it to `catalogue` and `orgs`; `Pool` and `Hold` stay;
`Pass` moves to the new `passes` app. No migrations exist, so this costs nothing
now and would cost a day in a month.

---

## 3. The pass model, worked through

This is the part worth arguing about. Everything else follows from it.

### 3.1 A pass is not one admission

Today's model says it is:

```python
class Pass(models.Model):
    pool = models.ForeignKey(Pool, ...)
    slot = models.ForeignKey(Slot, ...)     # one slot. one pandal. one entry.
    state = ...                              # ISSUED | CONSUMED | VOID
```

That was correct for FR-01 – FR-20, where a pass admitted one person to one pandal
at one time. It cannot express what the client's own prototype shows:

| Product | Pandals | Date and slot | People |
|---|---|---|---|
| Individual (FR-63) | one or more, chosen | **one date and slot per pandal, set independently** | 1 |
| Group (FR-64) | the group's enlisted list | one date and slot for the whole set | up to the member limit |
| City (FR-65) | one or more, chosen | **none** | 1 |

And three requirements are unimplementable against a single `slot` foreign key:

- **FR-69** — "see every pandal it covers and each one's own visited or pending state"
- **FR-70** — "mint an entry code **for one pandal** on a held pass"
- **FR-72** — "a per-pandal visit history … a count of pandals visited against pandals covered"

All three are per-pandal state on a pass that covers many. The pass needs legs.

### 3.2 Pass, leg, entry code

Three models where there was one.

```python
class Pass(models.Model):
    """The artifact a visitor holds. Holds no capacity and no slot of its own."""
    id          = UUIDField(pk)
    booking     = FK("booking.Booking", PROTECT, related_name="passes")
    holder      = FK("accounts.User", PROTECT, related_name="passes")
    product_type = CharField(choices=INDIVIDUAL | GROUP | CITY)
    group       = FK("groups.Group", null=True)          # GROUP only, V1
    admits      = PositiveSmallIntegerField(default=1)   # people this pass covers
    state       = CharField(choices=ACTIVE | VOID)
    issued_at   = DateTimeField()


class PassLeg(models.Model):
    """One pandal on a pass. The unit of capacity and the unit of admission."""
    id          = UUIDField(pk)
    pass_       = FK(Pass, CASCADE, related_name="legs")
    pandal      = FK("catalogue.Pandal", PROTECT)
    slot        = FK("catalogue.Slot", PROTECT, null=True)   # null for City Pass
    pool        = FK("inventory.Pool", PROTECT)              # where the capacity came from
    admits          = PositiveSmallIntegerField(default=1)   # copies Pass.admits
    admitted_count  = PositiveSmallIntegerField(default=0)
    state       = CharField(choices=PENDING | PARTIAL | ADMITTED | VOID)
    first_admitted_at = DateTimeField(null=True)
    last_admitted_at  = DateTimeField(null=True)

    class Meta:
        constraints = [
            UniqueConstraint("pass_", "pandal", name="one_leg_per_pandal_per_pass"),
            CheckConstraint(Q(admitted_count__lte=F("admits")),
                            name="leg_admissions_within_size"),
        ]


class EntryCode(models.Model):
    """A short-lived, single-use code minted against one leg (FR-70, NFR-6)."""
    id          = UUIDField(pk)
    leg         = FK(PassLeg, PROTECT, related_name="entry_codes")
    mint_seq    = PositiveIntegerField()      # monotonic per leg — see 3.5
    token       = TextField()                 # Ed25519-signed payload
    state       = CharField(choices=LIVE | CONSUMED | SUPERSEDED | EXPIRED)
    minted_at   = DateTimeField()
    expires_at  = DateTimeField()
    consumed_at = DateTimeField(null=True)
    consumed_by = FK("gate.Device", null=True)

    class Meta:
        constraints = [
            UniqueConstraint("leg", "mint_seq", name="entry_code_seq_per_leg"),
            # NFR-6: two valid codes for one admission never coexist.
            UniqueConstraint("leg", condition=Q(state="LIVE"),
                             name="one_live_code_per_leg"),
        ]
```

The shape reads as: **a booking buys a pass; a pass covers legs; a leg is admitted
through a code.** Capacity attaches to the leg, not the pass. Admission attaches to
the leg, not the pass. The pass is the wrapper the visitor recognises.

`Pass.admits` and `PassLeg.admits` are deliberately duplicated. The leg is the row a
gate reads and the row the invariant counts; making it self-sufficient means neither
the gate nor the invariant test needs a join to answer "how many people does this
admit". It is copied at issuance and never changes.

`FR-72`'s "pandals visited against pandals covered" is then
`legs.filter(state=ADMITTED).count()` over `legs.count()` — no new state anywhere.

### 3.3 What this does to the invariant

Today, `operations.issue()` increments `Pool.issued` **and** creates `Pass` rows, and
the property test asserts they match:

```python
live_passes  = Pass.objects.exclude(state=Pass.State.VOID).count()
issued_total = sum(p.issued for p in Pool.objects.all())
test.assertEqual(issued_total, live_passes)     # passes/tests/test_invariant.py:46
```

One pass, one pool, one unit. Once a pass has six legs across six pandals, that
identity is false and the coupling is backwards: `inventory` would have to know how
to build a `Pass`, and a `Pass` would have to belong to a single pool.

**The fix is to split the operation in two.**

```python
# inventory/operations.py — knows nothing about passes
def consume(pool_id, quantity, hold_id=None) -> None:
    """Move capacity out of a pool permanently. Terminal."""

def restore(pool_id, quantity) -> None:
    """Return consumed capacity — a cancellation."""
```

```python
# passes/issuance.py — knows about both
@transaction.atomic
def issue_pass(booking) -> Pass:
    """Consume one unit per leg from that leg's pool, then build the artifact."""
```

`inventory` becomes ignorant of what its capacity is spent on. That is what allows a
single pass to draw from six pools, and it is what makes NFR-33 checkable: nothing
outside `inventory/operations.py` writes to a pool counter, and `inventory` imports
nothing from `passes`.

**The invariant restates.** `Pool.issued` stops counting passes and starts counting
**admissions granted**:

```
per pool:   transferred_out + issued + live_held  <=  capacity_granted
per tree:   sum(pool.issued)  ==  sum(leg.admits for live legs drawn from that tree)
```

`test_invariant.py` line 46 changes from a count of passes to a sum of `admits` over
live legs. The database `CheckConstraint` is untouched — it never knew about passes.

### 3.4 Where the price lives

`FR-15` says a slot has "a time window, capacity and price". `FR-40` says a pass
configuration row has "type, optional group, date range, time range, price, cap".
Both cannot own the price, and if both do, the two will disagree during Ashtami.

**Decision: price lives on the configuration row. The slot carries window and
capacity only.**

- A row is `(pandal, type, date range, time range) -> price, cap`, which is what an
  admin actually thinks in — "Individual passes are ₹150 on Ashtami evening".
- A slot is a *capacity* object. It already has no price field in the current model,
  and its capacity already lives on the root pool rather than on the slot itself.
- `V-23` — "the price applicable to the chosen date and time window" — is then a
  lookup, not a denormalisation that can drift.

Pricing becomes a resolver with its own tests:

```python
def resolve_price(pandal, product_type, visit_date, slot) -> int:   # paise
    """The active row covering this date and window. Exactly one must match."""
```

Two rows matching is a configuration error and must be rejected at write time
(UC12 extension 2a), not disambiguated at read time. Zero rows matching means the
product is not on sale for that window, which is a legitimate answer.

### 3.5 The offline hole in entry codes, and how it closes

NFR-6 requires that minting a replacement invalidates every earlier live code, so
two valid codes for one admission never coexist. The partial unique index in §3.2
enforces that in the database.

It does not enforce it **at an offline gate**. A superseded code's Ed25519 signature
still verifies perfectly — the signature attests authenticity, and supersession is a
server-side fact the device has not heard. A visitor could mint, screenshot, mint
again, and walk two people through two offline gates.

Two mechanisms close it, and both are cheap:

1. **`mint_seq` in the signed payload.** Each code carries a monotonic sequence
   number for its leg. A device caches the highest `mint_seq` it has *seen* per leg
   and refuses anything lower. Two codes for one leg reaching two gates are still a
   race, but a code re-presented at the *same* gate after a re-mint is dead
   immediately, and reconciliation catches the rest as a duplicate (SYS-06).
2. **A short lifetime.** FR-70's "short fixed interval" is what actually bounds
   this. The exposure window is one code lifetime, not one festival. Start at
   **5 minutes** and treat it as a tunable, not a constant.

The signed payload is therefore:

```
{ code_id, leg_id, pandal_id, slot_start, slot_end, admits, mint_seq, expires_at }
```

Everything a gate needs to decide, with no round trip. Consumption stays
server-authoritative, exactly as ADR-004 says.

### 3.6 Group and City capacity — where the plan stops

Two products cannot be finished, and both stop for the same reason: nobody has said
what they consume.

**Group Pass.** A group of four visiting six pandals. Four people physically walk
into each pandal, so the honest reading is `admits = 4` on each of six legs — 24
units of capacity, not 6 and not 1. Capacity per slot is a crowd-safety constraint
(N-38 in the sweep), and a group that consumes one unit per pandal puts twenty-four bodies
through a pandal that counted six. **This plan assumes members × pandals** and the
model above supports it directly through `PassLeg.admits`. It needs confirming.

**City Pass.** Open question 7 in `CLAUDE.md`. A City Pass has no slot, and every
pool in the system is rooted at a slot — so there is *no pool to draw from*, and
`PassLeg.pool` cannot be filled. The two readings need different schemas:

- *Consumes per pandal* → pools must be able to root at a `Pandal` as well as a
  `Slot`, which means relaxing the `pool_is_root_or_child` check constraint and
  giving `Pool` a nullable `pandal` alongside its nullable `slot`.
- *Admits outside the cap* → `PassLeg.pool` becomes nullable, the leg draws nothing,
  and a pandal's real occupancy is no longer bounded by its configured capacity.

**City Pass is therefore not in V0**, despite being an Essential story (V-22,
FR-65). Building it against a guess means either a schema migration or an oversold
pandal, and both are more expensive than asking. This is the single question worth
chasing before V1 starts.

---

## 4. V0 models, app by app

Fields that carry a decision are annotated. Timestamps, UUID primary keys and
`created_at` are assumed everywhere and not listed.

### 4.1 `accounts`

| Model | Fields | Notes |
|---|---|---|
| `User` | `mobile` (unique), `email` (unique, null), `password`, `role`, `is_active` | `AbstractBaseUser` + `PermissionsMixin`. `USERNAME_FIELD = "mobile"` — see below. |
| `OtpChallenge` | `mobile`, `code_hash`, `purpose`, `attempts`, `expires_at`, `consumed_at`, `sent_at` | The raw code is **never stored**. Hash it. |
| `VisitorProfile` | `user` (1:1), `name`, `city`, `state`, `gender`, `language` | `language` ∈ en/bn/hi (FR-61). |
| `ProfileType` | `code`, `label` | Senior Citizen, Family with Young Children, Specially Abled, Press, Influencer (FR-62). M2M to `VisitorProfile`. |

**`USERNAME_FIELD = "mobile"`, for everyone including admins.** Visitors have no
email (FR-01 is mobile + OTP) and admins log in with email and password (FR-59), so
something has to give. Making mobile the identity for both keeps one row per human —
which UC25 extension 3a explicitly wants, when a person administers two pandals —
and costs an admin one extra field at onboarding. Two authentication backends sit on
top: `MobileOTPBackend` and the stock `ModelBackend` matching on email.

`role` is a single field, not a set. Four admin roles and three pool tiers do not map
one-to-one (ADR-003); authorisation reads `role` **and** the entity the account owns,
server-side, on every request (FR-60). The role tab at login selects a portal and
grants nothing.

**Rate limiting on `OtpChallenge` is a requirement, not a hardening pass.** N-18
exists because SMS pumping turns an unthrottled OTP endpoint into someone else's
revenue. Count challenges per mobile per window, in the same transaction that
creates one.

### 4.2 `catalogue`

| Model | Fields | Notes |
|---|---|---|
| `Pandal` | `name`, `slug`, `city`, `locality`, `address`, `lat`, `lng`, `theme`, `description`, `bookings_open` | Moves out of `passes`. `bookings_open` serves FR-16 at pandal level. |
| `PandalPhoto` | `pandal`, `image`, `ordering` | V-10. |
| `Gate` | `pandal`, `name`, `is_active` | PA-02. Needed in V0 because a scan is attributed to a gate. |
| `Slot` | `pandal`, `starts_at`, `ends_at`, `is_open` | **No capacity field and no price field.** Capacity is the root pool's `capacity_granted`; price is on `PassProduct`. |
| `PassProduct` | `pandal`, `product_type`, `group` (null), `valid_from`, `valid_to`, `time_from`, `time_to`, `price_paise`, `cap`, `is_active` | FR-40. The row-based configuration. |
| `PassProductChange` | `product`, `changed_by`, `field_diff`, `issued_at_change`, `remaining_at_change` | FR-42 — a change is recorded with the counts *at the moment it was made*, which is the only version anyone can audit later. |
| `LiveStatus` | `pandal`, `wait_minutes`, `crowd_level`, `updated_at`, `updated_by` | FR-49/FR-73. The `updated_at` is shown to visitors, not hidden — UC15 extension 3a. |

`Slot` having neither price nor capacity is the point. Both were pulled out for
reasons that survive scrutiny: capacity must be a pool so the invariant can hold it,
and price must be a row so it can vary by date without duplicating slots.

### 4.3 `inventory`

Unchanged from today's `passes/models.py`, minus what moves out, plus one field.

| Model | Change |
|---|---|
| `Pool` | Unchanged. Keeps both check constraints and the denormalised `root_slot`. |
| `Hold` | Gains `booking` FK (null) so the several holds of one multi-leg booking are findable and releasable together. |

`operations.py` changes are in §7.

### 4.4 `passes`

`Pass`, `PassLeg`, `EntryCode` exactly as §3.2. Plus `issuance.py`, which is the only
module allowed to create a `Pass`.

### 4.5 `booking`

| Model | Fields | Notes |
|---|---|---|
| `Booking` | `user`, `product_type`, `state`, `subtotal_paise`, `discount_paise`, `platform_fee_paise`, `total_paise`, `coupon`, `expires_at` | `CLAUDE.md`'s glossary calls this an *Entitlement*. Same thing; `Booking` is what the code will call it. FR-66's four lines are four fields, so the checkout screen cannot invent a total. |
| `BookingLeg` | `booking`, `pandal`, `slot` (null), `hold`, `price_paise` | One per intended `PassLeg`. Carries the hold, so releasing a booking releases exactly its holds. |
| `Payment` | `booking`, `gateway`, `gateway_ref`, `method`, `amount_paise`, `state`, `raw` | `method` ∈ UPI/CARD/WALLET (FR-68). |
| `PaymentEvent` | `gateway`, `event_id` (**unique**), `payload`, `received_at`, `processed_at` | The idempotency key. A replayed webhook is a no-op because the insert fails, not because a handler remembered. |
| `Refund` | `payment`, `amount_paise`, `state`, `attempts`, `last_error` | SYS-04 retries against this. |
| `Coupon` | `code` (unique), `kind`, `value`, `valid_from`, `valid_to`, `max_uses`, `uses` | FR-67. |

`Booking.state` ∈ `PENDING | PAID | ISSUED | FAILED | EXPIRED | REFUNDED`. `PAID` and
`ISSUED` are separate on purpose: the gap between them is the failure NFR-3 exists to
close, and a state machine that cannot name the gap cannot resolve it.

### 4.6 `gate`

| Model | Fields | Notes |
|---|---|---|
| `Device` | `pandal`, `gate`, `user`, `token_hash`, `is_active`, `revoked_at`, `last_sync_at` | G-01, G-10. Revocation lands on next sync (N-20) — a known window, see UC09 ext 4c. |
| `ScanLog` | `device`, `gate`, `entry_code` (null), `leg` (null), `decision`, `reason`, `scanned_at`, `recorded_at`, `was_offline`, `reconciled_at`, `override_by`, `override_reason` | FR-12 — every scan, admitted **or** refused. |
| `ScanConflict` | `leg`, `scans` (M2M), `detected_at`, `resolved_by`, `note` | SYS-06. Surfaced, never auto-resolved — the person is already inside. |

**`scanned_at` and `recorded_at` are both required.** `scanned_at` is the device's
clock; `recorded_at` is the server's. Offline scans arrive minutes or hours late, so
ordering must use the device clock while trust uses the server clock. Collapsing them
into one field makes the reconciliation in UC09 unwritable, and it is the sort of
thing that looks like duplication right up until the first offline gate.

`entry_code` and `leg` are both nullable because a refused scan may reference
nothing that exists — a forged QR has no code and no leg, and it still has to be
logged (UC07 extension 2b).

---

## 5. What V1 adds

Sketched only. These get their own planning pass when V0 is green.

- **`orgs`** — `Organisation` (moves out of today's `passes`), `Package`,
  `Allocation` (state PENDING/ACCEPTED/DECLINED/WITHDRAWN/LAPSED), `Creative`.
  The pool machinery already supports the whole chain at any depth; V1 adds the
  workflow and the two portals, not the model. `Allocation` state gates usability —
  a pass from an unaccepted pool is refused at the gate (UC07 ext 2e).
- **`groups`** — `Group`, `GroupMembership`, `GroupPandal` (the enlisted list),
  `GroupInvite`. Unblocks the Group Pass, subject to §3.6.
- **`donations`** — `DonationLink`, `Donation`, `Receipt`. A separate money path with
  no symmetric reversal; `CLAUDE.md` puts it early in the build order for that reason
  and this plan agrees.
- **`services`** — `Service`, `ServiceFormSchema`, `ServiceBooking`. FR-76's
  per-service form is a schema per service, not a table per service.
- **`support`** — `LostItem`, `SupportRequest`.
- **`platform`** — `MasterData`, `AuditEntry` (NFR-15), `Suspension`.
- **React admin portal** — the surface for PA-*, SP-*, SS-*, SA-*.

---

## 6. V0 endpoints — Essential stories only

Sixteen endpoints. Every one traces to an *Essential* story; nothing Typical or
Novel is in V0 except `PATCH /me/`, which is there because a pass has to carry a
name.

All under `/api/v1/`. JWT unless marked.

### Accounts

| Method | Path | Serves | Notes |
|---|---|---|---|
| `POST` | `/auth/otp/request/` | V-01, V-02 | Public. `{mobile, purpose}`. Rate-limited per mobile (N-18). Returns resend-after, never the code. |
| `POST` | `/auth/otp/verify/` | V-01, V-02 | Public. `{mobile, code}` → access + refresh. Registers if the number is new, logs in if not — UC01 extension 2a means one endpoint, not two. |
| `POST` | `/auth/refresh/` | — | simplejwt. |
| `POST` | `/auth/logout/` | V-03 | Blacklists the refresh token. |
| `GET` `PATCH` | `/me/` | V-04 | Profile and language. |

### Discovery

| Method | Path | Serves | Notes |
|---|---|---|---|
| `GET` | `/pandals/` | V-07, V-08 | `?city=&locality=&date=`. Read-only viewset. |
| `GET` | `/pandals/{id}/` | V-10 | Detail with photos and live status. |
| `GET` | `/pandals/{id}/slots/` | V-15 | `?date=&product_type=`. Returns each slot with **remaining availability** (`pool.available()`) and **resolved price** for that window. Availability and price in one response, because a client that has to make two calls will show a price for a slot that just filled. |

### Booking

| Method | Path | Serves | Notes |
|---|---|---|---|
| `POST` | `/bookings/` | V-16, V-17, V-23 | `{product_type, legs:[{pandal, slot}], coupon?}`. Prices, places **all** holds atomically, returns the FR-66 breakdown and the hold expiry. All-or-nothing: one unavailable leg holds nothing anywhere. |
| `GET` | `/bookings/{id}/` | V-17 | State and remaining hold time. |
| `POST` | `/bookings/{id}/pay/` | V-18 | Creates `Payment`, returns the gateway order. |
| `POST` | `/bookings/{id}/release/` | — | Explicit abandonment (UC02 ext 5a). Cheaper than waiting for expiry and it frees a seat during a peak. |
| `POST` | `/webhooks/payments/{gateway}/` | V-19 | **Public, signature-verified.** Idempotent on `PaymentEvent.event_id`. Captures, then issues. |

### Passes

| Method | Path | Serves | Notes |
|---|---|---|---|
| `GET` | `/passes/` | V-26, V-28, FR-69 | Legs inline with per-leg state. One call, because this is the screen a visitor opens in a queue. |
| `GET` | `/passes/{id}/` | V-27 | The full offline payload, cache-and-forget. Includes the signing public key so the client can be verified against the same key the gate uses. |
| `POST` | `/passes/{id}/legs/{leg_id}/entry-code/` | FR-70, FR-71 | Mints. Supersedes any live code for the leg in the same transaction. Body carries the rewarded-video acknowledgement. |

### Gate

| Method | Path | Serves | Notes |
|---|---|---|---|
| `POST` | `/gate/auth/` | G-01 | Device binds to a gate; returns a device token and the Ed25519 public key. |
| `GET` | `/gate/sync/` | G-06 | Down-sync: this pandal's legs, consumption state, revocations, since a cursor. What makes offline validation possible at all. |
| `POST` | `/gate/scans/` | G-02, G-03, G-04 | Online decision. One scan in, one decision out. |
| `POST` | `/gate/scans/batch/` | G-07 | Up-sync of queued offline scans. Returns per-scan reconciliation outcomes and any conflicts (SYS-06). |

### Deliberately not in V0

`POST /passes/{id}/cancel/` (V-29, *Typical*), donations, services, groups, sponsor
and admin APIs. **Admin configuration in V0 runs on Django Admin** — enough to
create a pandal, its gates, its slots with capacity, and its pass rows, so the
visitor path has something to book against. That is a seeding tool, not the product's
admin surface; the React portal is V1 per ADR-003.

---

## 7. `inventory/operations.py` — the changes

Four changes. The existing `transfer`, `place_hold`, `release_hold` and
`expire_holds` are unchanged.

**1. Split `issue` into `consume` and `restore`.** Per §3.3. `consume` moves the
counter; it does not create a `Pass`. `void_pass` leaves this module entirely and
becomes `passes.issuance.void_pass`, which calls `restore`.

**2. Add `place_holds(specs, ttl)` — atomic across pools.** This is the highest-risk
new code in V0 and the reason UC02 and UC03 can promise all-or-nothing:

```python
@transaction.atomic
def place_holds(specs, ttl_seconds=DEFAULT_HOLD_TTL_SECONDS) -> list[Hold]:
    """Hold capacity across several pools, or none of them.

    specs: [(pool_id, quantity), ...]

    Locks every pool in primary-key order in one query, exactly as _lock_pair
    does for two, so a three-leg booking and a two-leg booking touching the same
    pandals cannot deadlock against each other.
    """
```

The single-pool `place_hold` stays as the trivial case. Both must be exercised by
the concurrency suite, and the deadlock test needs a version with **overlapping,
differently-ordered** leg sets — the current `test_concurrent_transfers_do_not_deadlock`
only covers pairs.

**3. Add `set_root_capacity(pool_id, new_capacity)`.** PA-03 lets an admin change a
slot's capacity. There is no operation for it today, so it would be a direct write to
`Pool.capacity_granted` from a view or the admin — precisely the bypass NFR-33
forbids, and the one that oversells a pandal:

```python
@transaction.atomic
def set_root_capacity(pool_id, new_capacity) -> Pool:
    """Raise or lower a slot's capacity. Refuses to cut below commitments.

    new_capacity must be >= transferred_out + issued + live_held, which is
    UC11 extensions 3a and 3b in one condition.
    """
```

**4. `Hold` gains `booking`.** So `release_hold` has a sibling
`release_holds_for(booking)` and an abandoned checkout frees every leg it touched.

### Test changes this forces

- `test_invariant.py:46` — count `sum(leg.admits)` over live legs, not `Pass.objects.count()`.
- `test_concurrency.py` — add multi-pool contention and an interleaved-order deadlock case.
- Both files gain their dependencies and actually run, against Postgres.

---

## 8. Background work (Celery beat)

| Task | Cadence | Requirement | Note |
|---|---|---|---|
| `expire_holds` | 1 min | SYS-01 | Housekeeping only. `Pool.available()` already excludes expired holds by timestamp, so a late run cannot oversell. This property is worth keeping — do not "optimise" it into a counter. |
| `reconcile_pending_payments` | 2 min | SYS-03, NFR-3 | Any `Booking` in `PENDING` past its hold, or `PAID` and not `ISSUED`, is resolved against the gateway to issuance or refund. This is the task that makes NFR-3's "15 minutes to terminal state" true. |
| `retry_refunds` | 5 min, backing off | SYS-04 | |
| `expire_entry_codes` | 1 min | FR-70 | Housekeeping, same argument as holds — expiry is by timestamp in the query. |
| `close_slots_at_cutoff` | 1 min | SYS-02 | |
| `recompute_availability` | — | SYS-09 | **Not a task in V0.** Availability is computed from the pool on read. Cache it when a measurement says to, not before. |

---

## 9. Build order

Each slice ships when its tests are green. Slices 1 – 3 are strictly ordered; nothing
after them is worth writing if the invariant does not hold under contention.

**Slice 0 — make it run.** Declare `pytest`, `pytest-django`, `hypothesis`, `pynacl`,
`redis`, `celery`. Postgres 16 in `settings.py` and in a compose file. Delete
`src/pujapass/` and the build-backend blocks. Custom `User` model. First migration.
*Done when:* the two existing test modules run against Postgres and pass — and one
of them is a concurrency test that has never actually been exercised.

**Slice 1 — inventory.** Rename the app, move `Pandal`/`Slot`/`Organisation` out,
split `issue` into `consume`/`restore`, add `place_holds` and `set_root_capacity`.
*Done when:* the property suite passes with the restated invariant, and the deadlock
test covers overlapping multi-pool holds.

**Slice 2 — catalogue and accounts.** Pandal, Gate, Slot, `PassProduct`,
`resolve_price`. User, OTP, profile. Django Admin for seeding.
*Done when:* a pandal with slots, capacity and priced rows can be created, and
`resolve_price` rejects overlapping rows at write time.

**Slice 3 — the money path.** Booking, holds across legs, Payment, webhook
idempotency, `issue_pass`, `Pass`/`PassLeg`.
*Done when:* injected failures between capture and issuance always reach a terminal
state — a pass or a full refund — with zero captured payments in neither. That is
NFR-3, and it is tested by injecting the failure, not by reading the code.

**Slice 4 — entry codes.** Minting, supersession, the signed payload, `mint_seq`.
*Done when:* an adversarial suite covering replay, re-mint, expired-code reuse and
cross-pandal presentation fails every attempt. Per NFR-4 and NFR-6, any success
blocks the deploy.

**Slice 5 — the gate.** Device auth, sync, online scan, offline queue, batch
reconciliation, conflict surfacing.
*Done when:* a device with the network cut decides in under 500 ms, and a pass
admitted at two offline gates surfaces as a conflict rather than being silently
resolved.

**Blocked before slice 5 starts:** ADR-001. `CLAUDE.md` open question 9 and
`docs/ADR-001.md` is an empty file. The client spec says validation is server-side
and separately that offline queueing "may be considered"; FR-08 and NFR-2 assume
offline. The gate app cannot be built against both readings, and slices 0 – 4 do not
depend on the answer — so the question can be chased in parallel, but not past
slice 4.

---

## 10. Decisions this plan needs recorded

Six ADRs. `docs/ADR-001.md` is empty and `docs/ADR-002.md` contradicts `CLAUDE.md`.

| ADR | Decision | Status |
|---|---|---|
| ADR-001 | Gate offline validation | **Empty file. Unresolved and blocking slice 5.** |
| ADR-002 | Backend stack | **Stale.** Says "Admin surface: Django Admin" and "four roles removed from scope"; `CLAUDE.md` ADR-002/003 say React portal and four roles from day one. Correct it or supersede it. |
| ADR-005 | A pass has legs; capacity attaches to the leg | New — §3.2, §3.3 |
| ADR-006 | Price lives on the configuration row, not the slot | New — §3.4 |
| ADR-007 | Entry-code integrity offline: `mint_seq` plus a short lifetime | New — §3.5 |
| ADR-008 | `USERNAME_FIELD = "mobile"` for every account, two auth backends | New — §4.1 |

---

## 11. Assumptions this plan makes

Stated so they can be overturned cheaply rather than discovered late.

1. **A Group Pass consumes `members × pandals`.** §3.6. The model supports it; the
   client has not confirmed it. If it consumes one unit per pandal instead, only a
   default changes — but a pandal's crowd figure changes by a factor of four.
2. **An entry code lives 5 minutes.** FR-70 says "a short fixed interval" and gives
   no number. Tunable from settings, not a constant in code.
3. **A hold lives 15 minutes.** Today's `DEFAULT_HOLD_TTL_SECONDS`. Unstated in the
   requirements. Long enough for a UPI round trip, short enough not to strangle a
   slot during Ashtami — but it is a guess, and it is the first number to revisit
   under real peak load.
4. **The platform fee is a flat amount, not a percentage.** The prototype shows
   "Marketplace fee ₹5" (FR-66). Modelled as `platform_fee_paise` on the booking,
   which supports either.
5. **One gateway in V0.** `Payment.gateway` exists so a second is a row, not a
   migration, but only one adapter is written.
6. **Availability is computed, not cached.** §8. Correct until a measurement says
   otherwise; NFR-4's missing peak-load figure is what that measurement needs.

And the three unanswered questions that actually bite this plan, in the order worth
chasing them:

1. **Peak concurrency** (`CLAUDE.md` §7, "unspecified and blocking"). Decides hold
   TTL, whether availability stays computed, and every capacity number in NFR-1.
2. **City Pass capacity** (Q7). Decides whether `Pool` can root at a pandal. A schema
   question, and the reason V-22 is not in V0.
3. **Offline validation** (Q9 / ADR-001). Decides slice 5 entirely.
