# PujaPass — Schedule

**Written:** 8 September 2026, the day the festival dates were confirmed.

Panchami is **Friday 16 October 2026**. Dashami is **Wednesday 21 October**.
That is **38 days** from today, and `N-41` says the date is immovable: *anything not
shipped before Mahalaya is shipped next year.*

Bookings must open before the festival, not on it. At **T-14** that is **Friday 2
October — 24 days from now.** At T-21 it is 25 September, 17 days from now.

This document exists because `docs/BuildPlan.md` §9 orders the work correctly but
against no calendar. With a date, the ordering has to survive arithmetic.

---

## 1. The finding that matters most

**The critical path is not code. It is three external onboarding processes, none of
which has been started, and each of which has a multi-week tail.**

Every one of them blocks a requirement marked *Essential*. Every one of them is
someone else filling in a form and waiting. None of them goes faster because we
write better Python.

### 1a. DLT registration for OTP SMS — blocks all visitor authentication

Sending commercial SMS in India requires registration on a TRAI-mandated DLT
platform: the entity, then the sender ID (header), then every message template. An
unregistered sender's messages are **not delivered at all** — not delayed, not
throttled, dropped.

FR-01 and FR-02 are mobile number plus OTP. They are the first screen of the app. If
DLT registration is not complete, **no visitor can create an account.**

- **Typical turnaround:** several days to two weeks, longer if the entity documents
  need correction.
- **Depends on nothing we are waiting for.** It can start today.
- **Verify immediately:** does the client already have a registered entity and header
  from another product? If so this collapses to template registration, which is days.

### 1b. Payment gateway merchant onboarding — blocks the money path

A live payment gateway account requires business KYC — incorporation documents, bank
account, and in most cases a website or app the provider reviews. Test credentials
arrive immediately; **live credentials do not.**

- **Typical turnaround:** one to two weeks after complete documents.
- **Partially blocked by Q4.** Whether committee money settles directly or through the
  platform changes which product is being onboarded — a plain merchant account, or
  a route/split-settlement arrangement. **The KYC paperwork is the same either way and
  should start now**; only the product selection waits on Q4.
- **This is the single most likely thing to slip**, because it depends on the client's
  documents, not ours.

### 1c. App distribution — blocks the visitor and gate apps reaching anyone

Both mobile apps ship through stores.

- **Apple Developer Program** enrolment takes days, longer for an organisation
  requiring a D-U-N-S number. Review is usually 24–48 hours but a first submission is
  the one most likely to be rejected.
- **Google Play** — if the developer account is a **personal** account created after
  November 2023, production access requires a closed test with at least 12 testers
  running for 14 continuous days. An **organisation** account is exempt. Fourteen days
  is more than a third of the remaining schedule, so **which account type exists is a
  question to answer today, not in October.**

**Mitigation if this slips:** the gate app can ship outside the stores — Android APK
sideloaded onto volunteers' phones, which `N-31` already assumes are their own
devices. The visitor app cannot; it needs the stores.

### The action

These three start **today**, in parallel, before any further planning. They are the
only items on this schedule where waiting costs days we cannot buy back.

---

## 2. The calendar

| Week | Dates | Days remaining at start |
|---|---|---|
| 1 | 8 – 14 Sep | 38 |
| 2 | 15 – 21 Sep | 31 |
| 3 | 22 – 28 Sep | 24 |
| 4 | 29 Sep – 5 Oct | 17 |
| 5 | 6 – 12 Oct | 10 |
| 6 | 13 – 19 Oct | 3 — **Panchami falls on the 16th** |
| — | 20 – 21 Oct | Festival running. Nothing ships. |

Two dates are fixed and everything else negotiates around them:

- **2 October** — bookings open. Committees must have configured their pandals before
  this, so the admin seeding path is needed *earlier still*.
- **16 October** — gates live. No further deploys after the 15th.

The last usable engineering day is **14 October**. That is **36 days**, of which the
final week is stabilisation rather than construction. **Call it 30 building days.**

---

## 3. What has to be true by 2 October

For a visitor to buy a pass, all of this must work:

| Needs to work | BuildPlan slice | External dependency |
|---|---|---|
| A committee's pandal, slots, capacity and prices exist | Slice 2 | — |
| A visitor can register and log in | Slice 2 | **DLT (1a)** |
| A visitor can browse pandals and see availability | Slice 2 | — |
| A visitor can hold, pay, and receive a pass | Slice 3 | **Gateway (1b)** |
| The visitor app is installable | — | **Stores (1c)** |

And by 16 October, additionally:

| Needs to work | Slice | External dependency |
|---|---|---|
| A visitor can mint an entry code | Slice 4 | — |
| A gate can scan and admit | Slice 5 | **Q6 / ADR-001**, gate app distribution |

---

## 4. The arithmetic, honestly

`BuildPlan.md` §9 has six slices. Assigning them the shortest defensible duration for
**one developer already fluent in Django**:

| Slice | Work | Optimistic |
|---|---|---|
| 0 | Postgres, deps, custom user, first migration, CI | 2 days |
| 1 | inventory rename, `consume`/`restore`, `place_holds`, `set_root_capacity`, tests green | 3 days |
| 2 | catalogue, accounts, OTP, `resolve_price`, Django Admin seeding | 5 days |
| 3 | booking, multi-leg holds, payment, webhook idempotency, issuance | 7 days |
| 4 | entry codes, minting, supersession, Ed25519, adversarial suite | 4 days |
| 5 | gate — device auth, sync, offline queue, batch reconciliation | 7 days |
| | **Backend total** | **28 days** |

Against 30 building days, that leaves **two days of slack for the entire project**,
and it counts only the backend. It does not count:

- the **Flutter visitor app**
- the **Flutter gate app**
- the **React admin portal** (V1 by `BuildPlan` §6 — correctly deferred)
- integration, deployment, and a festival dry run

**And the estimate assumes Django fluency that does not yet exist on this project.**
The learning is happening now, in this repository, which is the right call — but it
means the optimistic column is optimistic twice over.

**Conclusion: the full V0 as scoped does not fit, and no amount of sequencing makes it
fit.** Either the scope shrinks or the team grows. That is a decision for the client,
and it should be made this week rather than discovered on 10 October.

---

## 5. Three options

Presented so the choice is explicit. **Option B is the recommendation.**

### Option A — Full V0 as planned

All three pass products, multi-pandal legs, entry codes, full offline gate.
**Requires:** at least two more engineers, one of them on Flutter, starting this week.
**Risk:** high. Onboarding cost eats the first week of anyone joining now.

### Option B — Reduced V0 *(recommended)*

Ship the path that produces a working festival, and cut what a pilot of 2,000 passes
does not need.

**Keep**

- Individual Pass, **multi-pandal legs included** — this is the product's identity and
  the model is already designed for it (`BuildPlan` §3.2)
- OTP registration and login
- Browse, hold, pay, issue
- Entry code minting with supersession
- Gate scan, **online-first with a local queue** for network drops
- Django Admin for committee configuration

**Cut to V1**

- **City Pass** — already out, pending Q2
- **Group Pass** — pending Q3, and groups do not exist as durable entities yet
- **Donations, services, support, lost and found** — none blocks the gate
- **Sponsor and sub-sponsor chain** — the pool model supports it; the portals do not
  exist, and no sponsor is onboarded for a 2,000-pass pilot
- **Coupons, rewarded video, wallet** — the first two are revenue optimisations on a
  pilot, the third may not be legal (Q5)
- **React admin portal** — already V1

**Effect:** backend drops from ~28 days to roughly **18**, which leaves real slack for
the Flutter work and a dry run.

### Option C — Minimum viable festival

Single-pandal Individual Pass, one slot per booking, online-only gate. Roughly 12
backend days. **Only if resourcing does not change and the stores slip.** It abandons
FR-63, which is the requirement the prototype is built around.

---

## 6. What runs in parallel this week, with no code

While the five outstanding Tier-1 questions are open, none of this is blocked:

| Work | Blocked by | Output |
|---|---|---|
| Start DLT, gateway KYC, store accounts | nothing | §1 — **today** |
| ADR-002 superseded; ADR-003, 004, 005, 006, 008 written | nothing | `docs/adr/` |
| ADR-007 entry codes | nothing — lifetime is 3 min, confirmed by the prototype | `docs/adr/` |
| Authorisation model: role × entity × action, and how it is enforced | nothing | new doc |
| API conventions: errors, pagination, idempotency, versioning | nothing | new doc |
| Booking and payment state machine (NFR-3) | Q4 affects settlement, not the state machine | new doc |
| Test strategy and the NFR-4/NFR-6 adversarial suite | nothing | new doc |
| ADR-001 gate offline validation | **Q6** | blocked |

---

## 7. Dates that need a decision this week

1. **Scope — A, B or C.** Everything else follows from it.
2. **Who builds the Flutter apps.** Not answerable by us, and it is the largest gap in
   the plan.
3. **Is the Play Store account personal or organisation?** Fourteen days of forced
   closed testing is the difference between shipping and not.
4. **Confirm bookings open on 2 October**, or name a different date. Committees need
   to configure their pandals before it.
