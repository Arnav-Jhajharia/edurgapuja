# PujaPass — Questions for the Client

**Raised:** 8 September 2026
**Answers needed by:** Tier 1 within one week. Tier 2 within three weeks.

Every question here blocks something. None of them is a preference — each one has a
wrong answer that costs either a schema migration, a licence application, or an
oversold pandal.

This document supersedes the scattered question lists in `CLAUDE.md` §7–§8,
`docs/FR.md` §11, `docs/StoriesAndUseCases.md` §6, `docs/mockup-findings.md` §4 and
`docs/visitor-coverage.md` §5. Those remain as the working record; this is the version
to send. Provenance for every question is in the appendix.

---

## How to read this

Each question carries four things:

| Field | Meaning |
|---|---|
| **We need to know** | The question, in terms someone on the client side can answer without reading our schema. |
| **Why it matters** | The consequence. Not "for completeness" — the actual failure. |
| **If we don't hear back** | What we will build. Silence is an answer; this is what it means. |
| **Cost of a wrong guess** | What it takes to undo, if the default turns out wrong. |

**You do not have to answer everything.** If you answer only the six in Tier 1, we can
build. The defaults are chosen to be safe rather than convenient, and every one of them
is reversible at a stated cost.

The constraint behind the deadlines is `N-41`: *the festival date is immovable.*
Anything unanswered becomes a guess we ship, or scope we drop.

---

# Tier 1 — before we write code

Six questions. Each one changes either the database schema or whether a regulator is
involved. All six are cheap to answer and expensive to discover late.

---

### Q1. How many people, and on which days? — ✅ ANSWERED 8 Sep 2026

**Answers received**

| # | Question | Answer |
|---|---|---|
| 1 | Passes sold across all pandals, in total | **2,000** |
| 2 | Sold in the busiest hour | **200** |
| 3 | People through the largest pandal's gates in its busiest hour | **200** |
| 4 | Festival dates 2026 | **16 October (Panchami) – 21 October (Dashami)** |

**What this settles.** See "Consequences of Q1" immediately below. In short: this is a
**pilot-scale launch**, the performance requirements are met by the simplest possible
deployment, and the binding constraint is not load — it is the **38 days** between this
answer and Panchami.

**Original question, for the record**

1. How many passes do you expect to sell across all pandals, in total?
2. What share of those sell on the single busiest day, and in the busiest hour of it?
3. How many people walk through the gates of the largest pandal in its busiest hour?
4. **What are the actual festival dates for 2026?** The prototype shows visit dates of
   12–13 October and a countdown, but nobody has confirmed the calendar, and it is
   master data the whole system schedules against.

**Why it matters**

Every performance number in the requirement set is currently blank —
`CLAUDE.md` §7 says so explicitly: *"The client spec gives no peak concurrency figure,
no response time target, no uptime expectation and no data retention period."*

This one figure decides how long we hold a seat during checkout, whether availability
is computed live or cached, how many servers we run on Ashtami, and how the gate
behaves when the network saturates (`N-42`).

### Consequences of Q1

The figures are roughly **two orders of magnitude smaller** than every planning document
assumed. `docs/ADR-002.md` describes traffic as *"near-flat for months, then extreme for a
few days"*; 200 passes in the busiest hour is **3.3 per minute**, and 200 admissions per
hour is **one scan every 18 seconds**. That is not extreme. It is a pilot.

**What this sizes — and what it does not**

These figures size the **deployment**. They do not shape the **system**: the platform is
built to grow into a festival of millions, and `docs/Scalability.md` records which
decisions are made for that future and which are deferred behind a measured trigger.

| Previously open | Year-one answer | Grows into |
|---|---|---|
| Infrastructure sizing | One container plus managed Postgres. | Horizontal scaling is a configuration change, kept that way by storing media in object storage and holding no state in the application from day one. |
| Availability: computed or cached? | **Computed.** `BuildPlan` §11.6 held this pending a measurement; the measurement arrived. | `recompute_availability` is **deferred, not deleted** — built when the slots endpoint exceeds 300 ms at p95. |
| Hold TTL | **15 minutes.** At 3.3 bookings/minute a held seat blocks nobody. | A settings value, not a constant. Revisit if a single slot's capacity drops under ~20. |
| Response-time budget | Ordinary web latency. **NFR-2's 500 ms scan-to-decision** is the one hard number, and it is a queue-experience requirement rather than a throughput one. | Unchanged by scale. |
| Rate limiting | Required on OTP (`N-18`) regardless. | Abuse control, not capacity control — abuse does not scale with legitimate traffic. |
| pgBouncer | Not yet. | Added at 60% of `max_connections`. Transaction-mode pooling forbids server-side prepared statements, so that flag is set **now** to keep the door open. |

**Explicitly NOT closed by this answer**

**NFR-5, the capacity invariant, is unaffected.** It is a *correctness* requirement, not a
scale requirement. Two visitors can race for the last seat in a 50-capacity slot at 3
bookings per minute exactly as they can at 3,000 — the window is smaller, not absent, and
a pandal oversold by one is still a pandal oversold. Every `select_for_update`, every
check constraint, and the entire property suite stay exactly as planned.

The same holds for NFR-3 (payment atomicity) and NFR-4/NFR-6 (forgery and reuse
resistance). None of them is a load property. Low traffic makes them *less likely to be
noticed*, which is an argument for testing them harder, not less.

**What this answer creates**

A deadline. Panchami is **16 October 2026** — **38 days** from today. Bookings must open
before it, so the real target is earlier still. This is now the binding constraint on the
project, and it is addressed in `docs/Schedule.md`.

**Blocked:** nothing further.

---

### Q2. Does a City Pass take up space?

**We need to know**

A City Pass covers several pandals with no date and no time — the holder visits in any
order (FR-65, and the prototype confirms it: *"visit them in any order"*).

So: when a City Pass holder walks into a pandal, **were they counted?**

Three possible answers, and we need one of them:

- **(a)** They consume a place at each pandal they select, taken at purchase.
- **(b)** They admit outside the pandal's cap — the pandal may exceed its stated capacity by however many City Pass holders turn up.
- **(c)** There is a separate, smaller City Pass quota per pandal, set by the committee.

**Why it matters**

`N-38` states that a slot's capacity is a **crowd-safety constraint, not only a
commercial one**. Answer (b) means a pandal that has sold out its slots can still fill
with City Pass holders, and nobody knows how many are coming. That is the exact failure
the capacity model exists to prevent, arriving through a door the model does not watch.

**If we don't hear back**

We build **(a)** — a City Pass consumes one place per pandal, taken at purchase.

**Cost of a wrong guess**

This is a **schema decision, not a setting.** Every unit of capacity in our system is
currently rooted at a time slot, and a City Pass has no slot — so answer (a) or (c)
requires capacity to also be able to root at a pandal, which changes a database
constraint and every query above it. Discovering this after we build is roughly a week.
Discovering it after launch means either an oversold pandal or a rebuild during the
festival.

**This is why the City Pass is currently out of our first release.** We would rather
ship two of three products than guess at the third.

**Blocks:** the `City Pass` product entirely (FR-65, V-22, UC04).

---

### Q3. What does a group of four consume, and can it be split?

**We need to know**

A Group Pass admits a party — the prototype says *"Up to 4 members"* — across the
group's enlisted pandals for one date and slot (FR-64).

1. When a group of four visits six pandals, how many places are consumed? **24** (four
   people at each of six pandals), or **6** (one booking at each), or something else?
2. If only three of the four turn up, does the gate admit three? Or is it all four or
   nobody?
3. If the group's list has six pandals and **one of them is full**, does the whole
   booking fail, or does it go ahead covering five?

**Why it matters**

Question 1 is a crowd-safety number. If a group consumes one place per pandal, a pandal
that counted six bookings gets twenty-four bodies. Same argument as Q2, but four times
worse, and this time the discrepancy is silent.

Questions 2 and 3 are the difference between a gate that turns away a family because
one member is late, and a pandal whose count is wrong by the same margin.

**If we don't hear back**

- Consumption: **members × pandals** — four people at six pandals consumes 24 places.
- Admission: **partial admission allowed** — three of four are admitted, and the fourth place is not held open.
- Booking: **all-or-nothing** — if one pandal is full, the booking fails whole rather than silently covering less.

**Cost of a wrong guess**

Question 1 is cheap to change in code and catastrophic to get wrong in a crowd — the
model already supports either, but the pandal's real occupancy differs by a factor of
four. Questions 2 and 3 are gate and checkout behaviour, changeable in days.

**Blocks:** Group Pass (FR-64, V-21, UC03, UC08).

---

### Q4. Whose money is it, and who is holding it?

**We need to know**

The prototype charges a **₹5 Marketplace fee** on every order, collected in the same
payment as the pass price. Donations (FR-21–FR-26) also flow through the app.

1. When a visitor pays ₹150 for a pass plus ₹5 fee, does the ₹155 land in **your**
   account and then get paid on to the committee? Or does the committee's ₹150 settle
   directly to them, with only the ₹5 reaching you?
2. Same question for donations — **do donations touch your account at all?**
3. When a sponsor sells passes on to a sub-sponsor at a price it sets (FR-34), does that
   payment run through the platform?
4. Is the ₹5 fee refunded when a visitor cancels?

**Why it matters**

If money for someone else's goods passes through your account before reaching them, that
is payment aggregation, and in India it is a regulated activity requiring RBI
authorisation. This is not a technical detail we can decide — it determines whether you
need a licence, a different settlement architecture, or a partner who already holds one.

`docs/mockup-findings.md` §2.6 puts it directly: *"A platform that collects a fee out of
the same payment as the committee's money is intermediating that payment."* The fee makes
this a question about **every pass sale**, not only about donations.

**If we don't hear back**

We build against a gateway that **settles the committee's share directly to the
committee** and routes only the platform fee to you — the arrangement that avoids
aggregator status. We will not build a flow where committee money rests in a platform
account.

**Cost of a wrong guess**

If you intend to hold and disburse committee money, the settlement design, the
reconciliation, and the compliance obligations are all different, and the gateway
integration is a different product. This is weeks, not days — and the regulatory
exposure sits with you, not with us.

**Blocks:** the entire payment integration, donations, and sponsor-to-sub-sponsor sales.

---

### Q5. What is the "Wallet"?

**We need to know**

The prototype's checkout offers **UPI, Card and Wallet** as three payment methods
(FR-68). UPI and card are clear. Wallet is not.

- Is it a **third-party wallet** — Paytm, PhonePe, Amazon Pay — where we simply pass the
  visitor through to them?
- Or is it **a balance the visitor holds with PujaPass** — money they top up in advance
  and spend on passes?

**Why it matters**

If it is the second, you are holding customer money. In India that is a Prepaid Payment
Instrument, and issuing one requires RBI authorisation, minimum net worth, and an escrow
arrangement. It also implies a top-up path, a balance, refunds *into* the balance, and
what happens to unspent money — none of which appears anywhere in the requirements.

There is currently **no requirement covering the wallet at all.** It exists only as a
button in the prototype.

**If we don't hear back**

We build it as a **pass-through to third-party wallets** via the payment gateway. We
will not build stored value.

**Cost of a wrong guess**

If you meant stored value, that is a separate product with a licensing precondition, and
it does not ship this festival.

**Blocks:** the payment method list (FR-68). Small if the answer is pass-through;
existential if it is not.

---

### Q6. Will the gate have a working internet connection?

**We need to know**

When a volunteer scans a visitor's code at the pandal gate, can we rely on that phone
having a network connection?

1. Is connectivity at the gate **your responsibility to provide** — a dedicated
   connection, a hotspot, a booked line — or ours to work around?
2. If a gate goes offline mid-evening, is it acceptable that a visitor is admitted and
   the record catches up minutes later? Or must every admission be confirmed by the
   server before the person walks in?
3. How long should a gate be able to keep working with no connection at all — minutes,
   or hours?

**Why it matters**

Your own requirements disagree with each other. One says validation is server-side;
another says offline queueing *"may be considered"*; `N-42` says *"Kolkata pandal crowds
saturate mobile networks"* and `N-31` says volunteers use **their own phones**.

Building for offline and building for online are different gate applications. We cannot
build both, and the answer changes what we can promise about duplicate entry: a gate that
cannot reach the server cannot know a code was already used at the gate on the other side
of the pandal.

There is a second half nobody has noticed. The prototype's entry code is minted **on
demand, three minutes before use, after a video** — so even if the *gate* works offline,
the *visitor* needs a connection at the gate to produce a code at all. Those are two
separate problems and the prototype only solves one.

**If we don't hear back**

We build a gate that **works offline for up to four hours**, verifies codes locally, and
reconciles when it reconnects — surfacing any duplicate entry as a conflict for a human
rather than resolving it silently. We plan for the visitor needing connectivity to mint.

**Cost of a wrong guess**

Building offline when online would do is wasted effort — perhaps two weeks. Building
online when the network fails on Ashtami means gates stop admitting people in a crowd.
The asymmetry is why our default is the expensive one.

**Blocks:** the entire gate application. This is the last thing we build, so the answer
can arrive while we build everything else — but not later than that.

---

# Tier 2 — before the money path and the gate

Eight questions. None changes the schema; all change behaviour someone will notice.

---

### Q7. What does an eligibility category actually give someone?

Visitors record a profile type — Senior Citizen, Family with Young Children, Specially
Abled, Press, Social Media Influencer — and the prototype pushes hard on it
(*"Sign up to check your pandal-hopping eligibility"*, *"Profile 30% complete"*).

**What none of the requirements say is what it grants.** A discount? A free pass? A
priority lane at the gate? Press access to areas visitors cannot enter? These have
entirely different consequences — a discount touches money and refunds, a lane touches
the gate and the crowd.

**Default:** the profile type is **recorded and displayed only**, granting nothing, until
someone tells us what it should do.

---

### Q8. Who pays for a coupon?

Checkout has a coupon field (FR-67). When ₹50 comes off a ₹150 pass, does the committee
receive ₹100, or does the committee still receive ₹150 and the platform absorb ₹50?

**Default:** the **platform absorbs it**. The committee is paid the full pass price.

---

### Q9. Is the rewarded video really mandatory?

The prototype requires watching an advert before an entry code can be minted (FR-71) —
so an advert stands between a visitor and the gate they are already queuing at.

If the ad network is slow or down, or the visitor has no signal in a crowd, what should
happen? Admit them without the video, or refuse to mint?

**Default:** if the video fails to load within a few seconds, **the code is minted
anyway**. We will not put an external advertising dependency on the critical path to
physical entry.

---

### Q10. How long do we keep personal data, and are you comfortable with what we collect?

No retention period exists anywhere in the requirements (`CLAUDE.md` §7).

Two of the fields are more sensitive than the rest, and they came from the prototype
rather than the requirements: **Puja By Your Name** captures *gotra* and a *sankalp* — a
religious lineage and a personal prayer — and **Special Assistance** plus the "Specially
Abled" profile type capture disability.

Under the DPDP Act this is ordinary personal data, but it is the kind whose breach is
least forgivable. We need a retention period, and confirmation that you intend to collect
these at all.

**Default:** personal data retained for **24 months** after the festival; payment records
for **8 years** as tax law requires; gotra and sankalp retained only until the service is
performed, then deleted.

---

### Q11. Do donors get a tax-deductible receipt?

80G eligibility depends on each committee's own registration, not on the platform. If
donors expect one, we must capture donor PAN and address, each committee's registration
number, and issue receipts in a prescribed format — and FR-75's anonymous donation
becomes incompatible with it.

**Default:** receipts are **acknowledgements, not 80G certificates**, and anonymous
donation stays available.

---

### Q12. How do sponsor allocations work?

1. When a pandal allocates 500 passes to a sponsor, is that 500 against **the pandal as a
   whole** (the sponsor's guests come whenever), or 500 against **a specific time slot**?
   Our model currently roots everything at a slot; your mockups suggest pandal level.
2. Can a sub-sponsor create **its own** sub-sponsors, or does the chain stop at two levels?

**Default:** allocations are against **a specific slot**, and the chain is **capped at two
levels** (sponsor → sub-sponsor). The second is a one-line setting either way.

---

### Q13. Do the value-added services take up space in the pandal?

**Curated Tours** (₹750, *"small groups"*) and **Aarti Slot Booking** (₹251) both put
people inside a pandal at a specific time. Neither is a pass, so neither is counted
against the pandal's capacity.

That means a pandal can be sold out on passes and still admit a tour group and an aarti
party — a second, uncounted door into the same crowd.

1. Do these services have their own capacity limits?
2. Does a tour or aarti booking also need a pass, or does it admit on its own?
3. **Who performs them, and how many can one committee handle per day?** If Puja By Your
   Name can be booked by four hundred people for Ashtami, somebody performs it four
   hundred times.

**Default:** each service has **its own daily capacity limit**, set by the committee, and
service bookings **do not admit to the pandal** — the holder still needs a pass.

---

### Q14. Can a free pass be cancelled?

Complimentary passes issued by a committee (FR-17) and passes given out by a sponsor
(FR-33) cost the holder nothing. Can they be cancelled, and by whom — the holder, or the
committee that issued them?

**Default:** the **issuer** can cancel an unused complimentary or sponsor pass, returning
the place to the pool. The holder cannot, and no money moves.

---

# Tier 3 — before the second release

Recorded so they are not lost. None blocks the first release; all have a working default.

| # | Question | Our default |
|---|---|---|
| 15 | If a pandal withdraws after taking donations, what happens to the money? | Held; resolved case by case with the committee. Not automated. |
| 16 | Where does a support request about a *payment* or *the app* go? There is no platform-level support queue. | Routes to the platform, not a pandal. |
| 17 | Can a service booking be cancelled, and under whose rules? | Same cancellation window as passes. |
| 18 | The public lost-and-found list shows a pandal's items. Does it show the **reporter's phone number**? | No. Contact is withheld; the committee holds it. |
| 19 | "Transfer a pass to someone else" is in the story set, but forwarding a signed pass is the exact forgery we are required to prevent. | Dropped, unless re-specified as cancel-and-reissue. |
| 20 | A deactivated volunteer's phone keeps working until it reconnects — up to four hours. Acceptable? | Accepted and documented as a known window. |
| 21 | **Special Assistance** is sold at ₹350 while "Specially Abled" is also an eligibility category. Is accessibility a paid product or a concession? | Flagged, not built. The RPwD Act has a view on charging for access. |
| 22 | *Gotra* appears as a four-item dropdown — Kashyapa, Bharadwaja, Vashishtha, Other. Is that the intended list? | Free text with suggestions, not a fixed list. |
| 23 | Support says *"we usually reply within 24 hours"* — is that a commitment? | Removed from the interface until someone owns it. |
| 24 | Terms and Privacy are accepted by continuing, with no record of which version. | We record version, timestamp and user. |
| 25 | Groups exist **before** booking, with a locality and an enlisted pandal list. Who creates one, who may join, and does the pandal list belong to the group or to the pass? | The creator owns the group and its pandal list; joining is by invitation. |
| 26 | The prototype sorts by *"pandals near you"*, which needs device location. The requirements only specify filtering by city and locality. | City and locality filters only. No GPS in release one. |
| 27 | There is a notification bell on every screen — an inbox nobody specified. | Not built. Outbound SMS and reminders only. |
| 28 | Donations have a free-text **message** field from the donor. Is it shown to the committee, and is it moderated? | Stored and shown to the committee. Not public, not moderated. |

---

# What we are deciding ourselves

For completeness — these were open in our own notes and do not need your time. We have
answered them and recorded why:

- **Entry code lifetime: 3 minutes.** Your prototype states it twice. We had assumed 5.
- **Hold during checkout: 15 minutes.** Revisited once Q1 is answered.
- **Platform fee modelled as a flat amount**, per the prototype's ₹5, but stored so a
  percentage is a configuration change rather than a rebuild.
- **A short, human-readable pass reference** (`EDP-2026-1842`) alongside the internal
  identifier, so support can ask a caller to read it out. It is a reference only, never
  something that admits anyone.
- **One payment gateway** in the first release, with a second being configuration rather
  than a migration.

---

# Appendix — where each question came from

| Q | Origin |
|---|---|
| Q1 | `CLAUDE.md` §7 "unspecified and blocking"; `FR.md` §11.1; `visitor-coverage.md` §5.3.6 (festival calendar) |
| Q2 | `CLAUDE.md` §8.7; `FR.md` §11.2; `mockup-findings.md` §2.4, §4.4; `BuildPlan.md` §3.6 |
| Q3 | `FR.md` §11.3; `StoriesAndUseCases.md` §6.1; `BuildPlan.md` §3.6, §11.1 |
| Q4 | `CLAUDE.md` §8.1, §8.5; `FR.md` §11.4; `mockup-findings.md` §2.6, §4.2; `StoriesAndUseCases.md` §6.9 |
| Q5 | `mockup-findings.md` §2.7, §4.3 |
| Q6 | `CLAUDE.md` §8.9 and ADR-001; `FR.md` §11.8; `mockup-findings.md` §2.1 |
| Q7 | `CLAUDE.md` §8.6; `mockup-findings.md` §2.5, §4.1 |
| Q8 | `mockup-findings.md` §2.7, §4.6 |
| Q9 | `mockup-findings.md` §4.5 |
| Q10 | `CLAUDE.md` §7; `mockup-findings.md` §2.8 |
| Q11 | `CLAUDE.md` §8.2; `FR.md` §11.5 |
| Q12 | `CLAUDE.md` §8.4, §8.8; `FR.md` §11.6, §11.7 |
| Q13 | `StoriesAndUseCases.md` §6.2; `visitor-coverage.md` §5.2 |
| Q14 | `StoriesAndUseCases.md` §6.5 |
| Q15–Q28 | `CLAUDE.md` §8.3; `StoriesAndUseCases.md` §6.3, §6.4, §6.6, §6.7, §6.8; `visitor-coverage.md` §5.3 |
