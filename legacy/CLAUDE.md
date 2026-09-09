# PujaPass — Specification

Client-branded **eDurgaPuja**. A Durga Puja pandal pass-booking platform: a visitor mobile app, a gate scanning app, and a role-based web admin portal.

This is the single source of requirement IDs. Everything else — code comments, commit messages, the developer guide — references these IDs rather than restating the requirement.

---

## 1. Actors

| Actor | Description |
|---|---|
| **Visitor** | Books passes, donates, books services, reports lost items. Mobile app. |
| **Gate Staff** | Volunteer scanning passes at a gate. Gate app. |
| **Pandal Admin** | Runs one pandal: configuration, sponsors, volunteers, services, donations. |
| **Sponsor Admin** | Holds a pass pool allocated by a pandal. May sell onward to sub-sponsors. |
| **Sub-Sponsor Admin** | Buys passes from a sponsor and issues them to its own customers. |
| **Superadmin** | Platform-wide. Onboards committees, approves branding, sees everything. |

Four admin roles, three pool tiers. Superadmin holds no pool; a guest holds a pass but no pool. Roles and tiers do not map one-to-one — see ADR-003.

---

## 2. Core functional requirements

### Visitor — booking

- **FR-01** Register with a mobile number, verified by OTP.
- **FR-02** Log in to an existing account, verified by OTP.
- **FR-03** Browse pandals, filtered by city or locality.
- **FR-04** View a pandal's slots with current availability.
- **FR-05** Select a slot and initiate a booking, holding capacity for a bounded period.
- **FR-06** Pay for a held booking.
- **FR-07** Receive a pass with a QR code on successful payment.
- **FR-08** View passes held, with the QR available without a network connection.
- **FR-09** Cancel within the configured window and receive the refund due.
- **FR-61** Choose an interface language — English, Bengali or Hindi — before sign-up, and change it afterwards.
- **FR-62** Hold a profile of name, city, state, gender and zero or more profile types: Senior Citizen, Family with Young Children, Specially Abled, Press, Social Media Influencer. The profile type is the eligibility category.
- **FR-66** See, before paying, the pass price, the number of people covered, the platform fee and the total.
- **FR-67** Apply a coupon code at checkout.
- **FR-68** Pay by UPI, card or wallet.
- **FR-69** See, on a held pass, every pandal it covers and each one's own visited or pending state.
- **FR-70** Mint an entry code for one pandal on a held pass. The code admits once, expires after a short fixed interval, and may be replaced once expired. Minting is unlimited; admission is not.
- **FR-71** Watch a rewarded video before an entry code is minted.
- **FR-72** See a per-pandal visit history with admission times and a count of pandals visited against pandals covered.

### Gate Staff — entry

- **FR-10** Scan a pass QR and receive an admitted or refused decision.
- **FR-11** Be prevented from admitting a pass that has already been consumed.
- **FR-12** Record an entry log for every scan, admitted or refused.
- **FR-13** Admit by manual exception where authorised, with the reason recorded.

### Pandal Admin — configuration

- **FR-14** Create and configure a pandal profile.
- **FR-15** Define slots with a time window, capacity and price.
- **FR-16** Open and close bookings for a pandal or an individual slot.
- **FR-17** Issue complimentary passes against capacity without payment.
- **FR-18** View live occupancy against capacity, per slot.

### Superadmin — platform

- **FR-19** Onboard a committee, creating the pandal record and its first Pandal Admin account.
- **FR-20** Manage master data: pass types, slot types, cancellation and refund rules.

---

## 3. Donations

- **FR-21** A Pandal Admin generates a shareable donation link with an optional suggested amount and purpose.
- **FR-22** A Pandal Admin views every link created for their pandal and copies it.
- **FR-23** Opening a link takes a visitor to the donate screen for that pandal, pre-filled where applicable.
- **FR-24** A donor gives any amount where none was fixed, without holding a pass.
- **FR-25** The system issues a receipt on successful payment.
- **FR-26** A Pandal Admin views donations separately from pass revenue.
- **FR-75** Donate anonymously by leaving the donor name blank; the receipt then carries no name.

Donations are a distinct money path. A pass payment is against inventory and reverses by returning capacity; a donation is against nothing and has no symmetric reversal.

---

## 4. Sponsorship hierarchy

- **FR-27** A Pandal Admin defines sponsorship packages: pass count, value, banner slots, benefits, validity.
- **FR-28** A Pandal Admin adds a sponsor and allocates a package.
- **FR-29** An allocation is pending until accepted; passes are unusable before acceptance.
- **FR-30** A Pandal Admin views full allocation history, newest first.
- **FR-31** A Sponsor Admin views their package, entitlements and pool.
- **FR-32** A Sponsor Admin accepts or declines an allocation.
- **FR-33** A Sponsor Admin distributes passes directly to named guests.
- **FR-34** A Sponsor Admin creates sub-sponsors and sells pool passes at a price they set.
- **FR-35** A Sub-Sponsor Admin views passes held, issued, total pool and amount paid to their sponsor.
- **FR-36** A Sub-Sponsor Admin buys **only** from their parent sponsor, never directly from a pandal.
- **FR-37** A Sub-Sponsor Admin issues in bulk or assigns a single pass to a named recipient, and views issuance history.
- **FR-38** A Sponsor Admin uploads branding creatives and tracks approval state.
- **FR-39** A Superadmin approves or rejects branding creatives.

---

## 5. Pass configuration, groups, services

- **FR-40** A Pandal Admin configures passes as rows: type (Individual, Group, City), optional group, date range, time range, price, cap.
- **FR-41** A row can be activated or deactivated without deletion.
- **FR-42** Every configuration change is recorded with resulting issued and remaining counts.
- **FR-43** A visitor creates or joins a group and books a Group Pass against it.
- **FR-44** A visitor buys a City Pass covering multiple pandals over a date range.
- **FR-45** A Pandal Admin defines value-added services with price and available days.
- **FR-46** A visitor books a service for a specific day.
- **FR-47** A Pandal Admin views service bookings.
- **FR-63** An Individual Pass covers one or more pandals, each with its own visit date and time slot, chosen independently.
- **FR-64** A Group Pass is booked against an existing group and covers that group's enlisted pandals for a single date and time slot, up to the pass's member limit.
- **FR-65** A City Pass covers a chosen set of pandals with no date and no slot; the holder visits them in any order.
- **FR-76** Each value-added service carries its own booking form. Puja By Your Name captures the name the Puja is performed in, the gotra and the sankalp.

---

## 6. Operations and support

- **FR-48** A Pandal Admin adds volunteers with name, mobile, assigned gate and active status.
- **FR-49** A Pandal Admin publishes estimated wait time and crowd level, shown live to visitors.
- **FR-50** A visitor reports a lost item with location and contact.
- **FR-51** A Pandal Admin views lost item reports and marks an item found.
- **FR-52** A visitor submits a support request or feedback.
- **FR-53** A Pandal Admin views support requests and marks them resolved.
- **FR-54** A Superadmin views a platform dashboard across all pandals.
- **FR-55** A Superadmin views passes and payments across all pandals.
- **FR-56** A Superadmin views entry and QR logs across all pandals.
- **FR-57** A Superadmin manages groups platform-wide.
- **FR-58** A Superadmin accesses pandal and sponsor operations for any pandal.
- **FR-59** Admin users log in with email and password, selecting a role portal.
- **FR-60** Every admin view is scoped to the acting user's own entity, except Superadmin.
- **FR-73** A visitor sees a pandal's estimated wait time and crowd level, each stamped with when it was last updated.
- **FR-74** A visitor sees the lost item reports held for a pandal.

The role tab at login selects which portal renders. It does not grant the role. Authorisation comes from the account's own role and owned entity, checked server-side.

---

## 7. Non-functional requirements

- **NFR-1 Dependency isolation.** Failure of any external dependency degrades only what depends on it. A payment gateway timeout must not slow gate validation. Per-dependency timeouts and circuit breakers; no shared outbound path. Acceptance: unrelated operations degrade no more than 10% against baseline under injected failure.

- **NFR-2 Gate validation under network loss.** A gate device validates offline from local state and reconciles on reconnection. Acceptance: scan-to-decision under 500 ms offline, zero wrongly accepted or rejected, reconciliation within 2 minutes of reconnection, cross-gate duplicates surfaced.

- **NFR-3 Payment and issuance atomicity.** A failure between payment capture and issuance resolves automatically to an issued artifact or a completed refund. Acceptance: 100% of injected failures reach a terminal state within 15 minutes; zero captured payments with neither pass nor refund.

- **NFR-4 Forgery and reuse resistance.** No pass may be reused, replayed, forged, or admitted at two gates simultaneously. Zero tolerance, not a threshold. Adversarial suite on every deploy; any success blocks the deploy.

- **NFR-5 Pool integrity.** The sum of held and issued passes at every tier never exceeds the tier above it, under concurrent operation at any depth. Enforced in code, in the database as a check constraint, and by property tests.

- **NFR-6 Entry code integrity.** An entry code admits once, at one pandal, within its lifetime. Minting a replacement invalidates every earlier live code for that leg, so two valid codes for one admission never coexist. Codes are verifiable offline by signature; consumption stays server-authoritative and reconciles on reconnect (NFR-2). Adversarial suite on every deploy, as NFR-4.

**Unspecified and blocking.** The client spec gives no peak concurrency figure, no response time target, no uptime expectation and no data retention period. Capacity planning is unanswerable without the peak load figure; it is the one to chase hardest.

---

## 8. Open questions

Blocking. Do not resolve these silently in code.

1. Does donation money settle directly to committee accounts or through the platform? This decides whether the platform is a payment aggregator.
2. Are tax-deductible receipts expected? 80G eligibility depends on each committee's own registration and changes donor identity requirements.
3. What happens to donations already received if a pandal withdraws?
4. Can a sub-sponsor create its own sub-sponsors, or is the hierarchy fixed at two levels?
5. When a sponsor sells to a sub-sponsor, does money move through the platform?
6. What is the "eligibility check" shown in the superadmin activity feed? Referenced but never specified.
7. Does a City Pass consume capacity at every participating pandal, or admit without a per-pandal cap?
8. Are sponsor allocations against pandal-wide capacity or against a specific slot? The current model roots pools at the slot; the mockups suggest pandal-level.
9. **Offline validation.** The client spec says validation is server-side, and separately that offline queueing "may be considered". FR-08 and NFR-2 assume offline. Unresolved — this is ADR-001 and it blocks nothing else in the schema, but it must be settled before the gate app is built.

---

## 9. Data model

### Ownership

`Pool` is the unit of capacity. It has an optional parent, so depth is not encoded in the schema.

```
Slot (capacity)  →  root Pool (depth 0)
                      ├─ Pool (sponsor, depth 1)
                      │    └─ Pool (sub-sponsor, depth 2)
                      └─ Pool (sponsor, depth 1)
```

`Organisation` covers both sponsor and sub-sponsor; they differ only by parent.

Counters on `Pool`: `capacity_granted` (everything in), `transferred_out` and `issued` (everything out). Holds are **rows**, not a counter, so an expired hold stops counting whether or not anything swept it.

Two operations, both in `passes/operations.py`:

- `transfer(parent, child, qty)` — recursive, any depth
- `issue(pool, qty, ...)` — terminal, produces `Pass`

Supporting: `place_hold`, `release_hold`, `expire_holds`, `void_pass`, `create_child_pool`.

Constraints in the database, not only in code:

- `pool_outflow_within_capacity` — the invariant
- `pool_is_root_or_child` — a pool is a slot root or an organisation node, never both

`MAX_POOL_DEPTH` is a settings value. Set it to 2 if question 4 resolves to a fixed hierarchy.

### Pass

A pass is terminal — it holds no capacity. It records the pool it came from and the root slot it admits to. States: `ISSUED`, `CONSUMED`, `VOID`.

Per ADR-004 the pass is a signed token (Ed25519), so a gate can verify authenticity offline. Consumption remains server-authoritative, enforced locally when offline and reconciled on reconnect. Authenticity and consumption are separate concerns.

---

## 10. Decisions on record

| ADR | Decision |
|---|---|
| ADR-001 | Gate offline validation — **unresolved**, see question 9 |
| ADR-002 | Django + DRF backend; React admin portal, not Django Admin |
| ADR-003 | Four roles from day one, two portals rendered; pools at arbitrary depth |
| ADR-004 | JWT for Flutter clients, session cookies for the browser admin |

---

## 11. Build order

Each slice ships only when its tests are green.

1. **Pool and Pass models, `transfer` and `issue`, property and concurrency tests.** Nothing else is worth building until the invariant holds under contention. (NFR-5)
2. **Visitor auth and booking.** (FR-01 – FR-09)
3. **Gate validation.** (FR-10 – FR-13) — needs ADR-001 settled first.
4. **Pandal configuration**, including row-based pass config. (FR-14 – FR-18, FR-40 – FR-42)
5. **Superadmin onboarding and master data.** (FR-19, FR-20)
6. **Donations.** (FR-21 – FR-26) — early, because its money path has no symmetric reversal and its edges are expensive to discover late.
7. **Sponsorship and the sponsor hierarchy.** (FR-27 – FR-39) — the model exists from slice 1; this adds the workflows and portals.
8. **Groups, City Pass, services.** (FR-43 – FR-47)
9. **Operations, live status, support, dashboards.** (FR-48 – FR-58)