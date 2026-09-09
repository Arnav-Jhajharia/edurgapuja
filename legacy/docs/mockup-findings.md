# Mockup walkthrough — findings

Source: the client's clickable prototype, walked end to end on 2026-09-07.
`https://e-durga-puja-screen-system.replit.app/__mockup/preview/edurgapuja/OnboardingClickFlow`

The prototype covers the **visitor app only**. There is no gate screen and no admin
screen in it, so everything below is evidence about FR-01 to FR-09 and the visitor
side of donations, services and support. The gate and the admin portals remain
specified only by the written requirements.

This document records what the prototype shows and what it changes. New requirement
IDs live in `CLAUDE.md`; this file is the evidence behind them.

---

## 1. What the prototype shows

### Onboarding

Language first — English, বাংলা, हिन्दी — then sign-up. Sign-up takes a full name and
a ten-digit mobile behind a fixed `+91`, then a six-digit OTP with a sixty-second
resend timer. Terms and Privacy are accepted by continuing, not by a checkbox.

The sign-up screen is headed *"Sign up to check your pandal-hopping eligibility"*.

### Home

A profile-completeness card — *"Profile 30% complete · Add a few details to check
eligibility"* — a Puja countdown, and four quick actions: My Pass, Book Pass,
Explore Pandals and Nearby Pandals. The last two open a "coming soon" dialog.

### Choosing a pass

Three products, and they are not three prices for one shape. They differ structurally.

| Product | Pandals | Date and slot | Covers |
|---|---|---|---|
| Individual | One or more, chosen | **One date and one slot per pandal** | 1 visitor |
| Group | Fixed — the group's enlisted list | **One date and one slot for the whole set** | "Up to 4 members" |
| City | One or more, chosen | **None — "visit them in any order"** | 1 visitor |

The Individual Pass screen says *"Pick one or more pandals to visit. We'll keep them
together on your pass."* Its next screen renders one date picker and one slot picker
**per selected pandal**, independently set.

The Group Pass screen lists pre-existing named groups — "Shib Mandir Squad · 18 Pujas
· South Kolkata", "Ananya's Puja Circle · 6 Pujas · South Kolkata" — with a locality
and a puja count each. The visitor picks a group; the group's six enlisted pandals
are then shown read-only under a single date and slot.

Slots are thirty minutes wide.

### Checkout

One screen for all three products. Order summary with the pass line, a "Visitors
covered" or "Members covered" line, a **Marketplace fee of ₹5**, and a total. A
**coupon code** field. Payment by **UPI, Card or Wallet**.

The heading says *"Your Individual Pass is reserved. Review the details before you
pay."* — capacity is held before payment, as FR-05 requires.

On success: *"Pass issued"*, with a human-readable **Pass ID — `EDP-2026-1842`**.

### My Pass

One card per booking, then a list headed **"Pandals in your pass"** — six rows, each
with its own state, `Visited` or `Pending`.

Below it: *"Your Pass is Almost Ready! Watch a short video to unlock your Pass QR
code."* and a **Generate QR** button.

Generating explains the rule, then shows the code:

> 1. Open "My Pass" and tap Generate QR
> 2. Show the code at the pandal gate
> 3. **Enter within 3 mins — one scan only**
>
> Each code works once. If it expires unused, simply generate a new one from "My Pass".

The code screen is headed **"One-time entry"**, scoped to a single pandal
(*"Pandal 1 · Shib Mandir"*), with a live countdown from `03:00`.

### History

The same six pandals with admission timestamps — "Shibmandir · Oct 12, 7:45 PM ·
Visited", "66 palli · Oct 13, 6:30 PM · Upcoming" — and a progress bar reading
"3 of 6 pandals visited".

### Profile

Name, mobile (shown verified), city, state, gender, and a multi-select
**profile type**: Senior Citizens, Families with Young Children, Specially Abled,
Press, Social Media Influencer.

### Menu

- **Support & Feedback** — name, mobile, subject, message.
- **Value-Added Services** — Curated Tours ₹750 (pandal, date, time, small groups),
  Puja By Your Name ₹501 (name, contact, name the Puja is performed in, **gotra**,
  date, time, **sankalp**), Special Assistance ₹350, Aarti Slot Booking ₹251.
- **Pandal Live Status** — pandal picker, then two tabs. *Live status*: estimated
  wait time ("18 min · from the main entry gate") and crowd level (Low/Medium/High)
  with "last updated 2 minutes ago". *Lost & found*: a per-pandal list, readable by
  the visitor.
- **Donate** — pandal picker, preset amounts ₹101 / ₹501 / ₹1001 or a custom amount,
  name *"optional for receipt — leave blank to donate anonymously"*, a message, UPI
  or Card, and "Receipt sent instantly".

---

## 2. What this changes

### 2.1 The QR is not the pass — it is a short-lived, single-use token

This is the largest finding and it contradicts two things we have written down.

**FR-08** says the QR must be available without a network connection. The prototype
mints a fresh code on demand, after a rewarded video, valid for three minutes and one
scan. A code that must be minted cannot be minted offline, and a code that expires in
three minutes cannot be cached before the visit.

**ADR-004** says the pass is a signed Ed25519 token over pass id, pandal, slot window
and issue time, so a gate can verify authenticity offline. That still works — but the
thing being signed is now the *entry token*, not the pass, and it carries a nonce and
a three-minute expiry. Authenticity stays offline-verifiable; minting does not.

Consequence for **ADR-001** (open question 9): the gate can still validate offline,
but the *visitor* now needs connectivity at the gate. Whether the gate is offline and
whether the visitor is offline are separate problems, and the prototype only solves
one of them.

**NFR-2**'s acceptance criteria stand for the gate. FR-08's offline promise does not.

### 2.2 A pass covers many pandals, each consumed independently

"Pandals in your pass", each `Visited` or `Pending`, with its own admission time, and
a QR scoped to one pandal at a time.

Our `Pass` model is terminal against one root slot with one `state`. It cannot hold
six independent admission states. This is a real schema consequence, not a labelling
one — see §3.

### 2.3 The three pass types are three shapes

FR-40 treats type as a column on a configuration row alongside price and cap. The
prototype shows they differ in what they even require: Individual needs a date and
slot *per pandal*, Group needs one for the *set*, City needs none at all.

### 2.4 A City Pass has no slot

*"Pick the pandals you want covered this Puja. You can visit them in any order."* No
date, no time, no capacity shown.

This partly answers **open question 7**. A City Pass does not book a slot. Whether it
consumes any capacity at all — a pandal-level cap rather than a slot-level one — is
still open, and it is now the sharper question: an uncapped City Pass is an
uncapped admission right, which is exactly what NFR-5 exists to prevent.

### 2.5 "Eligibility" is the profile type

**Open question 6** asked what the eligibility check is. The prototype answers it:
Senior Citizens, Families with Young Children, Specially Abled, Press, Social Media
Influencer, set on the profile and prompted for from sign-up onward.

What eligibility *grants* is still unstated. Priority lanes, discounted or free
passes, and press access are all consistent with the screens, and they have different
consequences — a discount touches money, a lane touches the gate. Still open.

### 2.6 The platform takes a fee

A ₹5 "Marketplace fee" per order, collected in the same transaction as the pass price.

This bears directly on **open question 1**. A platform that collects a fee out of the
same payment as the committee's money is intermediating that payment, which is the
definition that matters for payment-aggregator status. The question is no longer
hypothetical for donations alone; it applies to every pass sale.

### 2.7 Things with no requirement at all

Each of these is in the prototype and nowhere in the requirement set.

- **Coupons.** A code field at checkout, applied against the total.
- **Rewarded video advertising.** Watching one is a precondition for entry.
- **Wallet.** A payment method distinct from UPI and card, which implies stored value
  and therefore a balance, a top-up path, and refunds into it.
- **Language.** Three languages chosen before sign-up.
- **Groups as durable entities.** Named, with a locality, a member count and an
  enlisted pandal list — existing before any booking. FR-43 describes creating or
  joining a group *while booking*; the prototype selects one that already exists.
- **Lost and found as a visitor-readable list**, per pandal. FR-50 and FR-51 only
  cover reporting an item and marking it found.

### 2.8 Data we did not plan to hold

"Puja By Your Name" captures **gotra** and a **sankalp** — religious affiliation and a
personal prayer. "Special Assistance" and the "Specially Abled" profile type capture
disability. Under the DPDP Act this is ordinary personal data, but it is the kind
whose breach is least forgivable, and we have no retention period for any of it
(§7 of `CLAUDE.md`, "unspecified and blocking").

### 2.9 A human-readable Pass ID

`EDP-2026-1842` is shown to the visitor and, by implication, to gate staff. Sequential
and guessable. It must be a *reference*, never an authenticator — the entry token is
the authenticator. Worth stating so nobody builds a "look up by pass ID and admit"
path at a gate.

---

## 3. Schema consequences

The pool and pass core survives. `Pool`, `Hold`, `transfer` and `issue` are unchanged,
and the invariant they enforce is unchanged. What changes is above them.

A booking is not one pass. It is **one order over several legs**, where a leg is one
pandal on one date in one slot. Each leg draws its own capacity from that slot's root
pool, by the existing `place_hold` and `issue`. The visitor sees one card; the
inventory sees one hold and one issue per pandal.

That keeps the invariant exactly where it is. A six-pandal City Pass for four people
is twenty-four passes against six pools, not one pass against nothing.

```
Booking  (order: visitor, product, party size, money, state)
  └─ BookingLeg  (pandal, slot?, visit date?, hold, state)
        ├─ Pass × party_size          from passes.issue(root pool)
        └─ EntryToken × n             one live at a time, 3 min, single use
```

`EntryToken` is minted from a leg, not from a pass. Minting supersedes any live token
for that leg, so "generate a new one" cannot leave two valid codes in the world.

---

## 4. Questions this raises

Blocking, in the same sense as §8 of `CLAUDE.md`.

1. What does an eligibility category actually grant — price, priority, or access?
2. Does the platform fee make us a payment aggregator, and is it refundable on
   cancellation?
3. What is the Wallet? Stored value we hold, or a pass-through to a third party?
4. Does a City Pass consume capacity at each pandal, and if not, what stops a pandal
   filling with City Pass holders?
5. What happens if the rewarded video fails to load at the gate? Ad availability is
   now on the critical path to entry, and it is an external dependency under NFR-1.
6. Is a coupon a pandal's discount or the platform's? It determines who absorbs it.
7. Groups exist before booking — who creates one, who may join, and does a group's
   enlisted pandal list belong to the group or to the pass?
