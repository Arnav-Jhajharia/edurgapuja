# eDurgaPuja — Scope v1

**Ships now:** the pandal landing page, donations, and value-added services.
**Deferred:** passes and everything that hangs off them.

**The constraint that shapes this document:** a pandal owner must be able to turn
passes on *themselves*, whenever they want, without a migration, a deploy or
anyone from the platform being involved. That is a design requirement for v1, not
a promise about v2.

---

## 1 · What ships

| Area | In v1 |
|---|---|
| Identity | Mobile + OTP sign-in, profile (first name, last name, email, date of birth, city, state, gender, profile types), web-checkout verification |
| Pandal | The public landing page — indexable, shareable, transactional. Committee details, theme, story, media, guidelines, accessibility, parking, sponsor logos |
| Donations | Donation links with optional amount and purpose, donate on web or in app, anonymous giving, receipts |
| Services | Platform-defined form shapes, pandal-defined offerings and prices, booking, payment, confirmation |
| Payments | One order machinery, Razorpay, idempotency, verified webhooks, refunds |
| Operations | Live status, lost & found, support requests |
| Admin | Pandal management, donation links, services, revenue views, support queue, live status |
| Reporting | Donation and service revenue, by pandal and by period |

## 2 · What is deferred

Passes, pass categories, capacity, the configuration grid, booking, legs, entry
codes, the gate app, scanning, eligibility, groups, sponsorship pools, the
branding module, volunteers.

**Every open contradiction and every open assumption was a pass question.** With
passes out, v1 has none: C7 is a gate question, A4 and A6 are pass questions, and
Q1, Q3 and Q11 are capacity and eligibility questions. Nothing in v1 is waiting on
an answer.

Sponsor logos still appear on a landing page in v1 — uploaded by the pandal admin
as page content. The sponsorship *module* — packages, pools, sub-sponsors,
approval workflow, priced placements — arrives with passes, because a sponsorship
package is mostly an allocation of passes.

---

## 3 · The switch

`pandal.sells_passes` is a boolean the Pandal Admin controls. In v1 it exists, it
is always false, and **every surface already branches on it**. That is the whole
trick: the branches are written now while they are trivial, so that turning the
flag on later is data rather than code.

```
sells_passes = false          sells_passes = true  (later)
─────────────────────         ──────────────────────────────
landing page: donate,         landing page: donate, services,
services                        AND a passes block
admin nav: no Passes          admin nav: Passes, Capacity appear
discovery: no book action     discovery: book action appears
City Pass: cannot cover it    City Pass: may cover it
```

If v1 instead assumes "no pandal sells passes", the assumption spreads into
templates, serialisers, navigation and queries, and adding passes means finding
all of it again.

---

## 4 · The seams

Six decisions that cost little now and are expensive to retrofit. Everything else
is deliberately *not* abstracted.

### 4.1 One order, many lines

The single most important one. If donations and services each get a bespoke
checkout, passes become a third bespoke checkout, and receipts, refunds and
revenue reporting get written three times.

```
order        — user, status, subtotal, fee, discount, total, payment
order_line   — order, kind, target_id, quantity, unit_amount_paise
                 kind ∈ { donation, service_booking }        v1
                 kind ∈ { …, pass }                          later
```

A donation is an order with one line. A service booking is an order with one line.
A pass purchase will be an order with one line per pass. Checkout, receipt, refund
and reporting are written once, over lines.

It also absorbs A7 for free: if a donation later yields a Donor pass, that is one
order with two lines, not a new concept.

### 4.2 Payment is purpose-agnostic

`payment_order.purpose` already carries `pass_booking` and `pool_purchase` as
values, unused. Adding an enum value later is a migration; having it there is
free. More importantly there is **one** payment path, not one per product.

### 4.3 The inventory primitive is built in v1 — for services

Services need capacity already. An aarti slot has a finite number of seats, and a
curated tour is described as "small groups". So v1 builds:

```
service_day_capacity (service, date, capacity, issued_count)
    CHECK (issued_count <= capacity)
capacity_hold        (rows, not counters; expiry is not a sweeper's job)
place_hold / issue / release_hold / expire_holds
```

`pandal_day_capacity` for passes is then **the same table shape and the same four
operations against a different owner** — a module already written, already property
tested, already proven under concurrent load, on something lower-stakes than the
festival's entire admission system.

This is the deliberate one. It is a little more than v1 strictly needs, and it
retires the single largest risk in the pass work.

### 4.4 The landing page is composed of blocks

The page renders an ordered list of blocks — About, Media, Events, Services,
Donate, Sponsors, and later Passes — each shown according to the pandal's
capabilities. Adding passes adds a block. It does not redesign a page.

### 4.5 Reporting groups by line kind

Revenue is reported over `order_line.kind`. Passes appear as a new kind in the
existing reports rather than as a new set of reports.

### 4.6 Pandal-scoped configuration is one admin pattern

A pandal defines its own services today and will define its own pass categories
later — same shape, same permissions, same screens. Building the services admin
generically means the categories admin is a copy, not an invention.

### What is *not* abstracted

No plugin system. No generic product table. No polymorphic capacity across owner
types. No pass tables built "ready". Speculative generality is how a month-long
project loses a week.

---

## 5 · Still blocking in this slice

Only two, and the first is not a code problem.

**Q8 — how does a committee get its money?** Donations are the sharpest form of
this question: the platform collects money that belongs to a puja committee. If we
hold it and pay it on, we are a payment aggregator and need the licence. If the
gateway splits it at source — Razorpay Route, each committee a sub-merchant — we
never touch it.

Route is the right answer, and it has a consequence that belongs on the schedule
rather than in the code: **every committee must be onboarded as a sub-merchant,
with KYC and bank details, before it can take a single rupee.** That has a lead
time measured in weeks and it runs in parallel with nothing. With the festival
about a month out, committee onboarding is more likely to be the critical path
than any of the software.

**Q12 — retention.** Services capture gotra, sankalp and assistance requirements.
That is religious affiliation and disability. v1 collects it, so v1 needs a
retention period and an access rule, even if both are provisional.

Two smaller ones, answerable late: is there a platform fee on a donation as there
is on a pass, and whose cost is a coupon.

---

## 6 · Build order

Each slice ships only when its tests are green.

1. **Identity** — mobile, OTP, profile, sessions, web-checkout verification.
2. **Payments** — order, lines, Razorpay, idempotency, verified webhooks, refunds. Before anything that takes money.
3. **Pandal and landing page** — public, server-rendered, block-composed, capability-driven.
4. **Donations** — links, donate on web and in app, anonymous giving, receipts.
5. **Services** — types, pandal offerings, booking forms, capacity, payment, confirmation.
6. **Admin** — pandal management, services, donation links, revenue, support.
7. **Operations** — live status, lost & found, support.
8. **Reporting** — revenue by pandal, by kind, by period; exports.

Payments before donations is deliberate: the money path has no symmetric reversal
and its edges are expensive to discover late.
