# Visitor requirement coverage — prototype walkthrough

Source: the client's clickable prototype, walked end to end on 2026-09-08.
`https://e-durga-puja-screen-system.replit.app/__mockup/preview/edurgapuja/OnboardingClickFlow`

Every visitor-facing screen in the prototype was opened. Requirement IDs are
`CLAUDE.md`'s `FR-nn`; sweep IDs are `docs/FR.md`'s `V-nn`.

**Answer to the question asked: no.** Twelve visitor requirements are absent, five of
them *Essential*, and two of the ones that are present contradict each other.

---

## 1. What the prototype covers

Screens reached: language → sign-up → OTP → home → my pass → entry code → visit
history → profile → menu → donate → pandal live status (+ lost & found tab) →
value-added services → Puja By Your Name form → support → book pass → choose product
→ choose pandals → per-pandal date and slot → checkout → pass issued.

| Req | Requirement | Evidence |
|---|---|---|
| FR-61 | Language before sign-up | English / বাংলা / हिन्दी on the first screen |
| FR-01 | Register, mobile + OTP | Full name, fixed `+91`, 10 digits, 6-digit OTP, 60 s resend |
| FR-62 | Profile and profile types | Name, city, state, gender, and all five types as chips |
| FR-63 | Individual Pass over several pandals | One date picker and one slot picker **per selected pandal** |
| FR-05 | Capacity held before payment | "Your Individual Pass is reserved. Review the details before you pay." |
| FR-66 | Price breakdown before paying | Pass line, "Visitors covered", "Marketplace fee ₹5", Total |
| FR-67 | Coupon at checkout | "Have a coupon?" + Apply |
| FR-68 | UPI, card or wallet | Three payment tiles |
| FR-07 | Pass issued on payment | "Pass issued", Pass ID `EDP-2026-1842` |
| FR-69 | Every pandal on the pass, with its own state | "PANDALS IN YOUR PASS" — 3 Visited, 3 Pending |
| FR-70 | Entry code for one pandal, one admission, short life | "Pandal 1 · Shib Mandir", countdown `02:36`, "Valid once. Expires in 3 mins" |
| FR-72 | Per-pandal visit history and a count | Times per pandal, "3 of 6 pandals visited" |
| FR-73 | Wait time and crowd level with a timestamp | "18 min", "Medium", "Last updated 2 minutes ago" |
| FR-74 | Lost item reports for a pandal | Lost & found tab (empty state) |
| FR-24 FR-43 | Donate any amount, or a suggested one | ₹101 / ₹501 / ₹1001 + custom amount |
| FR-75 | Anonymous donation | "Your name · optional for receipt — Leave blank to donate anonymously" |
| FR-25 | Receipt | "Secure payment · Receipt sent instantly" |
| FR-45 FR-46 | Services with price, booked for a day | Curated Tours ₹750, Puja By Your Name ₹501, Special Assistance ₹350, Aarti Slot ₹251 |
| FR-76 | Puja By Your Name form | Name in which the Puja is performed, Gotra, Sankalp |
| FR-52 | Support request | Name, mobile, subject, message |

**FR-71 (rewarded video) is stated, not shown.** "Watch a short video to unlock your
Pass QR code" appears on My Pass, but Generate QR goes straight to a how-to screen
and then the code. No video plays.

---

## 2. What is missing

### Essential

- **FR-02 / V-02 — log in to an existing account.** The prototype has one entry
  point, "Create your account", and no login path anywhere. A returning visitor, or
  one on a new phone, cannot get back to their passes. FR-02 is Essential and it is
  simply not there.
- **FR-03 / V-07 – V-10 — browse pandals, filter by city or locality, view a
  pandal.** Both discovery entry points on Home — "Explore Pandals" and "Nearby
  Pandals" — open a **"Coming soon"** dialog. The only pandal list in the product is
  the six-tile picker inside the booking flow, with no search, no filter, no detail
  page, and no photos or timings. A visitor cannot find out what a pandal *is* before
  buying a pass to it.
- **FR-04 / V-15 — slots with current availability.** The per-pandal slot dropdown
  offers three fixed windows and shows **no remaining capacity anywhere in the
  product**. This is the requirement that makes the capacity model visible to a
  visitor; without it, "the slot is full" can only ever be a failure at checkout.
- **FR-09 / V-29, V-30 — cancel within the window and see the refund due.** No cancel
  action on any pass, no refund rule shown, no mention of cancellation at checkout.
- **FR-08 / V-27 — QR available without a network.** Nothing in the prototype offers
  or implies offline access. See §3 — this one is not merely missing, it is
  contradicted.

### Typical and Novel

- **FR-50 / V-50 — report a lost item.** Explicitly declined by the product: the
  Lost & found tab says *"Ask a volunteer at the help desk if you need assistance."*
  The visitor can read the list but cannot add to it, so nothing ever populates it.
- **V-53 — see the status of a support request.** The support form submits and ends.
- **V-03 — log out.** Absent. **V-05 — delete account.** Absent.
- **FR-61, second half — change language after sign-up.** The profile screen carries
  no language field. Language is chosen once, before the account exists.
- **V-46 — donation history.** "History" is visit history only.
- **V-44 — the purpose of a donation appeal.** The donate screen has pandal, amount,
  name and message. No appeal, no purpose, no target.
- **FR-23 / V-40 — opening a shared donation link.** Not demonstrated. Only the
  in-app donate screen exists, so FR-21's link is never exercised from the receiving
  end.
- **FR-43 / V-34 – V-38 — create or join a group.** The Group Pass picks from
  pre-existing named groups. Nothing creates one, invites to one, or joins one.
- **V-12 directions, V-13 favourites, V-14 sponsors, V-25 SMS confirmation,
  V-31 transfer, V-32 device wallet, V-33 slot reminders** — none present.

---

## 3. The contradiction worth resolving first

**FR-08 and FR-70 cannot both be true as the prototype implements them.**

- FR-08 / V-27 / NFR-2: the visitor's QR must open **without a network**, because
  Kolkata pandal crowds saturate mobile networks (N-42).
- FR-70, as built: the code is **minted on demand** and dies in **3 minutes**.

A code that must be requested from the server at the gate, and expires three minutes
later, requires connectivity at exactly the moment the requirement says there will be
none. The prototype has silently chosen the online path and dropped FR-08.

There are two coherent readings and the client has to pick one:

1. **The pass QR is the offline artifact**, verifiable by signature at the gate, and
   the entry code is an additional online anti-screenshot measure. FR-08 survives;
   FR-70 becomes best-effort.
2. **The entry code is the only artifact.** FR-08 is wrong and should be struck, and
   NFR-2's offline gate requirement narrows to "the gate validates offline", not "the
   visitor works offline".

This is ADR-001 territory and it now blocks more than the gate app: it decides
whether `Pass` needs an offline-cacheable payload at all.

---

## 4. Inconsistencies inside the prototype

Six, found by walking one path end to end. Each is a place where two screens disagree
about the same fact, so each needs an answer before it becomes a schema.

1. **The product changes between checkout and confirmation.** Chose *Individual
   Pass*; checkout said "Individual Pass · Rs 1500 · 1 visitor"; the confirmation
   screen issued a **City Pass, "South Kolkata Region", "Valid for up to 4 members"**.
2. **A Group Pass has four different sizes.** "Includes 18 members" on My Pass, "six
   pandals included" on the chooser, "up to 4 members" on the confirmation, and
   `docs/mockup-findings.md` recorded "Up to 4 members" earlier. Since a Group Pass's
   member count is what it consumes at every pandal it covers, this number is a
   capacity figure, not a label.
3. **A Group Pass has six different date-times.** Visit History shows the six legs of
   one Group Pass at 7:45, 8:20 and 9:05 PM on Oct 12 and 6:30, 7:15 and 8:00 PM on
   Oct 13. FR-64 says a Group Pass is "a single date and time slot" for the whole
   set. Either FR-64 is wrong or the history screen is.
4. **The entry code's pandal is assigned, not chosen.** The screen reads "Pandal 1 ·
   Shib Mandir" and there is no per-pandal action on the pass. A visitor whose night
   starts at the fourth pandal on their list cannot mint a code for it. FR-70 says
   "mint an entry code **for one pandal**", which implies choosing which.
5. **Payment methods differ between paths.** Pass checkout offers UPI, Card and
   Wallet; the donate screen offers UPI and Card.
6. **Slot times are 1:00 AM, 2:00 AM and 3:00 AM.** Placeholder data, but it means no
   real slot geometry has been reviewed by anyone.

---

## 5. In the mockup, absent from the requirements

The reverse direction. Fourteen things the prototype shows that carry no requirement
ID in `CLAUDE.md` or `docs/FR.md`. Two of them change the data model.

### 5.1 Eligibility is a visitor-facing gate, not an admin curiosity

The word appears three times in the visitor app, in the most prominent positions the
product has:

- the sign-up screen is headed **"Sign up to check your pandal-hopping eligibility"**;
- the first card on Home reads **"Profile 30% complete · Add a few details to check
  eligibility"**;
- FR-62's profile types are, per `CLAUDE.md`, "the eligibility category".

In the requirements, eligibility exists only as `SA-07` ("manage users and their
eligibility state") and as **open question 6** — *"What is the 'eligibility check'
shown in the superadmin activity feed? Referenced but never specified."*

That question is filed as a superadmin mystery. The prototype shows it is the first
sentence a new user reads and the reason the app asks for a profile at all. The
question to put to the client is therefore not "what is that row in the admin feed"
but **"does eligibility restrict what a visitor may buy, and on what rule?"** If it
does, it gates `POST /bookings/` and belongs in slice 3; if it is only a label on a
concession price, it is a `PassProduct` row and costs nothing. Nobody has said which.

**Profile completeness ("30%")** is the same gap in miniature: a scoring rule over
profile fields, shown as a number, with no requirement defining what counts.

### 5.2 Two "value-added services" consume pandal capacity

`FR-45` models a service as *price and available days*. Nothing about slots, nothing
about capacity. Two of the four services in the prototype break that model:

| Service | What it actually does |
|---|---|
| **Curated Tours ₹750** | "A handpicked pandal trail … with **reserved time slots**" — *Choose pandals · Pick a date · Select a time · Small groups* |
| **Aarti Slot Booking ₹251** | "**Reserve** a peaceful Aarti moment at **your chosen pandal**" |

Curated Tours selects pandals, a date and a time, and reserves slots. That is not a
value-added service — **it is a fourth pass product sold through a different door**,
structurally an Individual Pass with a guide attached. Aarti Slot Booking reserves
something at a pandal at a time.

The consequence is concrete: if these do not draw from the same `Pool` as a pass, a
pandal can be sold out on passes and still admit a tour group and an Aarti party. A
slot's capacity is a crowd-safety constraint, so a second uncounted door into the
same pandal is the failure NFR-5 exists to prevent, arriving through the services
model rather than the pass model.

`docs/BuildPlan.md` §6 already asks "does a value-added service have a capacity?"
This is the answer: at least two do, and one of them is a pass.

### 5.3 The rest

| # | In the prototype | No requirement covers |
|---|---|---|
| 1 | Notification bell on every screen | An in-app notification inbox. `V-25` and `V-33` are *outbound* SMS and reminders — a different thing from a read/unread centre. |
| 2 | "By continuing you agree to our **Terms** & **Privacy Policy**" | Consent capture. Which version was accepted, when, by whom. Legally load-bearing, and `N-22` (retention period) is already an open gap. |
| 3 | "Sorted by pandals **near you**"; "Nearby Pandals — find one close by" | Device location. `FR-03` is "filtered by city or locality" — an address filter, not GPS. No permission flow, no fallback when it is denied. |
| 4 | Pass ID **`EDP-2026-1842`** | A short, human-readable, quotable pass identifier distinct from a UUID. Support cannot ask a caller to read out a UUID. |
| 5 | Donation **Message** field, "e.g. Jai Maa Durga" | Donor-supplied free text attached to a donation. `FR-21` has an admin-set *purpose*; this is the donor's own words, shown to a committee. |
| 6 | **Puja countdown**, "20 days to go" | A festival calendar. Which date is the Puja is master data, and `SA-03` does not list it. |
| 7 | **"How to use your pass"** instructional screen | In-app help as a first-class screen. `N-25` says a first-time visitor completes a booking *without documentation*; the prototype has added documentation. |
| 8 | Support: "we usually reply **within 24 hours**" | A support response target. `V-53` and `PA-16` imply none, and this is a public promise. |
| 9 | **Gotra** as a fixed list — Kashyapa, Bharadwaja, Vashishtha, Other | A controlled vocabulary. `FR-76` says capture gotra; a four-item dropdown is master data and a substantive decision about a religious identifier. |
| 10 | Group shown as "**Shib Mandir Squad · 18 Pujas · South Kolkata**" | Group metadata: a locality and an enlisted-pandal count. `FR-43` says a visitor creates or joins a group; it does not say a group has a locality or a fixed list. |
| 11 | "**Tour booked!**" with no checkout in between | The service money path. Whether a service booking is a `Booking` with a `Payment` like a pass, or something else, is unstated. |
| 12 | **Special Assistance ₹350** — "Plan a comfortable, supported visit for every member of your group" | Accessibility as a paid service, alongside "Specially Abled" as an FR-62 eligibility category. Whether assistance is a concession or a product is a policy question for the client, and in India it is one the RPwD Act has a view on. Worth asking before it is built either way. |

---

## 6. Effect on `docs/BuildPlan.md`

Four changes, none structural.

- **Entry code lifetime is 3 minutes, not the 5 I assumed** (BuildPlan §11.2). The
  prototype states it twice. Take 3 minutes as the client's number.
- **V0 must include login (FR-02), not just registration.** The plan already has
  `POST /auth/otp/verify/` handling both, so this costs nothing — but it means the
  prototype cannot be the acceptance reference for auth.
- **Slot availability has no prototype design.** BuildPlan's
  `GET /pandals/{id}/slots/` returns remaining capacity and price together; no screen
  consumes it yet. Worth flagging to whoever designs the booking screen, because it
  is the one number the whole inventory model exists to produce.
- **Group Pass `admits` is unconfirmed and the prototype makes it worse**, not
  better — four different figures. BuildPlan §3.6 assumed members × pandals; the
  assumption stands, and question 2 above is now the concrete way to ask it.

- **`services` gains capacity, and possibly a pool.** §5.2. If Curated Tours and
  Aarti Slot Booking reserve real slots, the `services` app cannot be the thin V1 app
  the plan sketches — it either draws from `inventory` like a pass, or it is a pass
  and belongs in `passes`. Settle this before slice 8.
- **`Pass` needs a short public reference** alongside its UUID. §5.3 item 4. Cheap
  now, a migration later.

`docs/mockup-findings.md` remains accurate on what it covered; this document extends
it in both directions — to the requirements the prototype does *not* reach (§2), and
to the prototype features no requirement claims (§5).
