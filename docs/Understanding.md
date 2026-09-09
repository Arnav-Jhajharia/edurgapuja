# eDurgaPuja — Understanding

Built from three primary sources, and nothing else.

| Tag | Source | What it is |
|---|---|---|
| **[D]** | `Application Features (3).docx` | The client's written feature list. 11 mobile sections, 15 web modules. Prose, no screens. |
| **[R]** | `Screen Recording 2026-09-08 at 3.29.22 PM.mov` (89s, 2284×1414) | A walkthrough of the **web admin portal**, all four role portals. |
| **[P]** | `e-durga-puja-screen-system.replit.app` | A clickable prototype: **54 screens** under the `edurgapuja` namespace, covering the visitor app and the gate app. |

Where the three disagree, that is recorded rather than resolved. §11 is the list of decisions the client still owes us.

---

## 1. What the product is

A pass-booking platform for Durga Puja pandal-hopping in Kolkata. A visitor books a pass that covers **several pandals at once**, and at each pandal gate mints a **short-lived one-time QR code** to be admitted. Committees sell passes and take donations; sponsors buy pass pools and advertising space; a platform operator sits above all of it.

Three surfaces:

1. **Visitor mobile app** — sign-up, eligibility check, pass purchase, entry code, visit history, services, donations, live pandal status, support.
2. **Gate app** — a volunteer logs in, scans a code at a named gate, gets an admit/refuse verdict, sees their recent scans.
3. **Web admin portal** — one login screen, four role portals behind it.

The product is being built **white-label**: the volunteer login field placeholder reads `you@utsavpro.app` while everything else is branded eDurgaPuja [P]. Treat "eDurgaPuja" as one tenant of a platform, not as the platform.

---

## 2. Actors

| Actor | Where they work | What they own |
|---|---|---|
| **Visitor** | Mobile app | A profile, an eligibility verdict, one or more passes, service bookings, donations |
| **Volunteer / Gate staff** | Gate app | A gate assignment at one pandal; a scan history |
| **Pandal Admin** | Web | One pandal: its passes, prices, capacity, services, volunteers, sponsors, donations, live status, support queue |
| **Sponsor Admin** | Web | A pass pool bought from one or more pandals, a branding entitlement, a set of sub-sponsors |
| **Sub-Sponsor Admin** | Web | A pass pool bought from **its sponsor only**, and the passes it issues onward |
| **Super Admin** | Web | Everything, across all pandals and all sponsors; plus the eligibility questionnaire and the pandal master |

Login is one screen with four tabs — Pandal Admin, Sponsor Admin, Sub-Sponsor, Super Admin — email and password, no MFA shown [R]. [D] asks for optional MFA on privileged roles, plus session timeout, password reset, login history and an admin audit trail; none of that appears in [R].

---

## 3. The visitor journey, as prototyped [P]

```
Language (English / বাংলা / हिन्दी)
  → Sign up: full name + mobile (+91), "Sign up to check your pandal-hopping eligibility"
  → OTP: 6 digits, resend timer ~60s
  → Home: profile completeness ("Profile 30% complete"), Puja countdown ("20 days to go"),
          quick actions: My Pass · Book Pass · Explore Pandals · Nearby Pandals
  → Eligibility check: 6 questions ("PASS APPLICATION")
  → Result: "You are eligible" → Choose a pass
  → Choose pass: Individual | Group | City
  → Select pandals (or a group)
  → Visit date & time
  → Payment: order summary + marketplace fee + coupon + UPI/Card/Wallet
  → Pass issued (Pass ID EDP-2026-1842)
  → My Pass: pandals in your pass, each Visited or Pending → Generate QR
  → Entry Pass: one-time QR, 3-minute countdown, scoped to one pandal
  → Visit history: admission timestamps, "3 of 6 pandals visited"
```

Bottom navigation across the app: **Home · Pass · History · Profile · Menu**. The Menu holds Support & Feedback, Value-Added Services, Pandal Live Status, and Donate.

### Profile
Name, mobile, city, state, gender, and a **multi-select profile type**: Senior Citizens, Families with Young Children, Specially Abled, Press, Social Media Influencer [P, D].

### Eligibility — a gate, not a label
Six questions, headed *PASS APPLICATION · Eligibility check*, with a progress bar and *"Your answers are used only to check pass eligibility and are kept private."* Question 1 is **"Are you a resident of West Bengal?"** — *Yes, I live in West Bengal* / *No, I'm visiting* [P].

The Super Admin's *Users & Eligibility* screen shows the other side: every user carries **Approved / Pending / Not Eligible**, there is an **Eligibility Funnel** listing all six questions with the number of users surviving each (Q1 Resident of West Bengal 4,812 → Q2 Age group confirmed 4,390 → Q3 ID verification 3,960 → Q4 Address proof 3,512 → Q5 Profile type selected 3,105 → Q6 Final review 2,840), each question editable, plus **+ Add Question** [R].

In the sample data the only out-of-state user (Delhi) is **Not Eligible**. So eligibility is a configurable questionnaire that **gates the ability to buy a pass**, it has a *Pending* state implying human review, and it can refuse people on residency. This appears nowhere in [D].

### The three pass products
| Product | Pandals | Date & slot | Party |
|---|---|---|---|
| **Individual** | "One person, any pandal you pick" — multi-select from a list sorted by proximity | One date + one 30-minute slot **per pandal**, set independently | 1 |
| **Group** | Fixed — the pandals enlisted to the chosen group (shown read-only, "6 pandals enlisted for this group") | **One** date and **one** slot for the whole set | "Up to 4 members" at checkout |
| **City** | "Pick pandals near you" — multi-select, capped ("0 of 6 selected"), grouped by region | Two conflicting versions — see §10.1 | "Valid for up to 4 members" on the issued pass |

**Groups exist before booking.** The Group Pass screen lists named, pre-existing groups with a locality and a pandal count: *Shib Mandir Squad · 18 Pujas · South Kolkata*, *Ananya's Puja Circle · 6 Pujas*, *Mudiali Hoppers · 24 Pujas*, *Bagbazar Bandhu · 15 Pujas*, *Kumartuli Collective · 9 Pujas*, *Rohan's Heritage Walk · 5 Pujas* [P]. Nothing in either source says who creates a group, who may join, or who owns its pandal list. The Super Admin dashboard counts "86 active groups · 4 new today" [R].

### Checkout
One screen for all products: order summary (pass line, members/visitors covered), a **Marketplace fee of ₹5**, total, a **coupon code** field, and payment by **UPI, Card or Wallet** [P]. The heading reads *"Your Group Pass is reserved. Review the details before you pay."* — capacity is held before payment.

### The pass and the entry code — these are two different things
**The pass** is durable: a Pass ID (`EDP-2026-1842`), a product type, a party size, and a list of pandals each carrying its own **Visited / Pending** state [P]. A visitor may hold several passes at once — My Pass has a *Your passes* list and an **Add pass** action.

**The entry code** is ephemeral: minted on demand from My Pass with **Generate QR**, scoped to **one pandal** ("Pandal 1 · Shib Mandir"), headed *ONE-TIME ENTRY*, with a live countdown from 03:00 and the text *"Valid once. Expires in 3 mins"* and *"Show this code at the gate. Keep your screen brightness high."* [P]

This is the single most consequential fact in the whole system, and it contradicts [D] §7, which describes the QR as a durable artefact — *"QR code available in-app and optionally as downloadable/shareable pass"*, with pass status *Active, Used, Cancelled, Expired, Blocked*. A code that must be minted at the gate and dies in three minutes cannot be downloaded or shared, and its status is not the pass's status. See §11.

### Value-added services
The Menu offers four **platform services**, each with its own booking form [P]:

| Service | Price | Form fields |
|---|---|---|
| Curated Tours | ₹750 | Pandal, date of visit, time window (e.g. 5:30–7:00 PM) |
| Puja By Your Name | ₹501 | Name, contact number, **name in which the Puja is to be performed**, **gotra**, preferred date, preferred time, **sankalp** |
| Special Assistance | ₹350 | Visitor name, contact, assistance required (e.g. Senior Citizen), **type of assistance** (e.g. Wheelchair), wheelchair required Yes/No, remarks |
| Aarti Slot Booking | ₹251 | Pandal, aarti date, aarti time slot (e.g. 5:00–6:00 AM), **number of attendees**, amount auto-fetched |

A footnote adds *"Also available: parking and VIP darshan passes for selected pandals."*

Separately, the payment and confirmation screens reference a **pandal-configured catalog** — *VIP Darshan Fast-Track at Mudiali Club, Oct 10 2026, ₹500* [P] — which matches what a Pandal Admin maintains in the portal: VIP Darshan Fast-Track ₹500, Prasad Home Delivery ₹150, Guided Photography Session ₹800, Heritage Pandal Walk ₹300, each with a list of available days [R]. **These are two different catalogs.** See §10.4.

### Donations
Pick a pandal, choose ₹101 / ₹501 / ₹1001 or a custom amount, optional name (*"Leave blank to donate anonymously"*), optional message, pay by UPI or Card, receipt on success [P]. No pass required.

### Live status and lost & found
Pick a pandal, then two tabs. *Live status*: estimated wait time ("18 min · From the main entry gate") and crowd level (Low / Medium / High) with *"Last updated 2 minutes ago"*. *Lost & found*: a per-pandal list, visitor-readable — empty state reads *"No items reported nearby · Ask a volunteer at the help desk"* [P].

### Support
Full name, mobile, subject, message. *"We usually reply within 24 hours."* [P]

---

## 4. The gate app [P]

| Screen | Content |
|---|---|
| Volunteer login | Email + password. *"Scan passes at the pandal gate."* |
| Scan Pass | Header shows the posting: **"Shib Mandir · Gate 1"**. Camera viewfinder. |
| Scan result | **Valid Entry** with Pass Holder, Pandal, Pass Type, Time. Actions: *Scan Next*, *View Last 10 Scans*. |
| Scan history | *Last 10 Scans*, Shib Mandir · Gate 1, each row **Valid**, **Expired**, or **Duplicate**. |

Three outcomes, not two — *Expired* and *Duplicate* are distinct refusals, which is exactly what a 3-minute single-use code produces. The Super Admin's *Entry & QR Logs* mirrors it platform-wide: 342 check-ins today, 318 valid (93%), 17 expired codes, 7 duplicate scans, with a live feed of time / pandal / pass holder / group / result [R].

**There is no manual-exception admit control anywhere in [P] or [R]**, although [D] §11 requires "manual exception handling for authorized staff". Nor is there any offline affordance; [D] says only that "offline queueing/cached validation **may be considered** for controlled environments".

---

## 5. The admin portal [R]

### Login
One card, four tabs — Pandal Admin · Sponsor Admin · Sub-Sponsor · Super Admin — email ID and password. The tab chooses which portal renders.

### Pandal Admin — scoped to one pandal ("Shib Mandir")
Nine items in the sidebar:

| Screen | Content |
|---|---|
| **Donations** (the landing page) | Tiles: Passes Sold 284 (+9% wk), Pass Revenue ₹1.62L (+11%), Total Donations ₹1,753, Check-ins Today 128 (live). A **Service Type** filter (All Types / Passes / each service / Donations) that filters the whole page. Tables: Recent Sales (Pass ID, buyer, type, price, date), Recent Service Bookings, Recent Donations. |
| **Generate Donation Link** | Optional suggested amount, optional purpose/note → **Generate Link**. A table of every link created, newest first, with the shareable URL (`https://edurgapuja.app/d/shib-mandir/8x2k1p`) and a Copy button. |
| **Add Volunteer** | Name, mobile, **assigned gate** (Gate 1, Ticket Desk), Active status, edit. |
| **Sponsorship Packages** | *Present in the sidebar but never opened in the recording — content unknown.* |
| **Sponsors** | (Seen in the Super Admin view.) Sponsor, contact, package, passes allocated, value, status Pending/Accepted; plus a **Sponsor Pass Allocation History**. |
| **Pass Configuration** | An editable **row grid**: Is Active · Pass Type (Individual/Group/City) · Group · From Date · To Date · From Time · To Time · Price · (a cap, off-screen right) — plus **+ Add Row**. Below it, **Pass Configuration History**: every change with date, the full row, **No. of Passes Issued**, **Remaining Passes**, action (Created), and a detail note. |
| **Services** | The pandal's own catalog: service, description, price, available days, edit; **+ Add Service**; and Recent Bookings. |
| **Live Status** | Estimated wait time (minutes) and Live Crowd Level (Low/Medium/High), *"Shown live to visitors browsing pandals on the mobile app."* Plus **Digital Lost & Found**: item, location, contact, date, status Lost/Found, **Mark Found**. |
| **Support & Feedback** | Submissions from the app: name, contact, subject (App Issue / Feedback & Suggestion / Pandal · Pass Issue), message, date, status New/Resolved, **Mark Resolved**. |

### Sponsor Admin — "Sponsor One"
| Screen | Content |
|---|---|
| **Overview** | *Your Sponsored Pandals*: pandal, package (Gold/Silver/Community), package value, passes purchased, spend, View. Tiles: Passes Purchased 850, Passes Issued 115, Passes Remaining 735, Active Banners 1, Total Spend ₹73,000, **Received from Sub-sponsors ₹0**. Then *Distribution by Pass Type*: passes issued / passes remaining / amount collected per type. A **Puja Pandal** filter (All Pandals) across every screen. |
| **Pass Management** | My Sponsorship Package (Gold Sponsor ₹50,000 — benefits: priority entry gate, listed on Sponsors page; validity: full festival Oct 10–14). A pending allocation banner: *"Shib Mandir allocated 100 passes to you — accept to add them to your pool"* with **Accept**. *My Pass Allocation History* (package, passes, date, status Pending Acceptance / Accepted). Actions: **Request Additional Passes**, **Assign Single Pass**, **+ Issue Pass**, over a distribution log (pass type, quantity, distributed to, date). |
| **Sub-sponsors** | Sub-sponsor, login email, **password (shown in clear: `eDP@4821`)**, starter grant, price/pass, paid to you, status; **+ Create Sub-sponsor**. |
| **Branding** | Branding Entitlement (*"Your Gold Sponsor package includes 2 banner placement(s) · 2 in use"*), Sponsor Logo upload, **Live Now** (which creative is displayed where), and a creatives table: creative, placement, dates, **price per week**, status Approved / Pending Approval / Rejected (with **Replace**). **+ Add Creative** opens *Add Banner*: creative name, **Puja Pandal(s) checkboxes** (*"Creates one creative entry per selected pandal"*), **Placement · approved options only** (Home Screen / Pass Confirmation / My Pass Screen), image drop zone, start/end date, price. |
| **Donations** | Network distribution activity: passes issued across the network (130), value distributed (₹62,000), passes remaining (735), and recent distributions showing **via** which sponsor or sub-sponsor. |

### Sub-Sponsor Admin — "Kolkata Sweets Corner"
Two screens only.
- **Overview** — Passes in Pool 85, Passes Issued 15, Total Pool 100, Paid to Sponsor One ₹0. A card: *"Buy Passes from Sponsor One — you can only buy passes from your sponsor, not directly from a Puja Pandal"*, price per pass ₹100, 735 available. **Buy Passes** opens a modal: quantity, computed total, payment method **UPI or Card**, UPI ID, **Pay ₹0**.
- **Issue Pass** — "85 of 100 passes remaining in your pool", **Assign Single Pass** / **+ Issue Pass**, and an issuance log (pass type, quantity, distributed to, date).

### Super Admin — "Debraj S.", labelled ADMIN PANEL
A global search box in the header. Three sidebar groups:

**Platform**
- **Dashboard** — Total Users 4,812 (+12%), Passes Sold 1,203 (+8%), Revenue ₹9.84L (+15%), Active Groups 86 (+4 today), Today's Check-ins 342 (live). *Passes Sold by Type* bar chart (Group 612 · Individual 438 · City 153). *Daily Sign-ups* last 7 days. *Puja Countdown* ("MAHA SHASHTHI · 20 days to go · Peak traffic expected at Shib Mandir & Deshapriya Park"). *Recent Activity* feed: pass purchased, checked in, **eligibility check submitted**, new group created.
- **Users & Eligibility** — 4,812 users; filters by pandal, eligibility, profile type; table of name, mobile, city, profile type, eligibility, registered; **+ Add User**; and the Eligibility Funnel described in §3.
- **Passes & Payments** — revenue split by product (Group ₹9.18L / 612 passes, Individual ₹43,800 / 438, City ₹6.12L / 153; 1,203 passes, ₹9,84,500 total) **and the same Pass Configuration grid and history as the Pandal Admin**, platform-wide.
- **Groups** — headed "14 pandals · 86 active groups", but the visible card is a **Pandal master**: pandal, **Capacity** (2,000 / 3,500 / 2,800 / 1,200 …), **Visits Today**, status **Open** or **Opens Oct 12**, edit, **+ Add Pandal**. (A groups table presumably sits below the fold; not seen.)
- **Entry & QR Logs** — as §4.

**Pandal Operations** — Donations, Volunteers, Sponsorship Packages, Sponsors, Services, Live Status, Support & Feedback: the same seven Pandal Admin screens, un-scoped, each with a **Puja Pandal** filter and an extra *Pandal* column. Add buttons appear disabled while the filter is "All Pandals".

**Sponsor Operations** — Sponsor Passes, Sub-sponsors, Branding: the sponsor's screens, read across every sponsor.

---

## 6. The domain, as the evidence actually describes it

### A booking is one order over many legs
A pass covers N pandals; each pandal on that pass carries **its own state** (Visited / Pending) and **its own admission timestamp**; for Individual passes each also carries **its own date and slot**. One purchase therefore produces one visitor-facing pass and N independently-consumable admissions. Any model with a single `state` on a pass cannot represent the My Pass screen.

### Admission is a two-step: mint, then scan
The durable pass authorises; the minted code admits. A code is bound to one pandal, lives ~3 minutes, and works once. Minting again must invalidate any earlier live code for that leg, or two valid codes exist for one admission. Expired and Duplicate are the two failure modes the gate actually reports.

### Capacity appears at three different levels
- **[D]**: "Capacity controls at Pandal/date/slot/pass-type level" — all four.
- **[R] Pass Configuration**: a cap per **row**, where a row is (pass type, group, date range, time range, price).
- **[R] Groups/Pandal master**: a single **Capacity** number per pandal.

These are not the same thing and they are not obviously nested. §11.

### Distribution is a chain of pools with money at each link
```
Pandal  ──allocates a package──▶  Sponsor        (pending until Accepted)
Sponsor ──sells at its own price──▶ Sub-Sponsor  (paid by UPI/Card in-platform)
Sponsor / Sub-Sponsor ──issues──▶  named guests / bulk recipients
```
A sub-sponsor may buy **only** from its parent sponsor. The counters shown are Purchased / Issued / Remaining at every tier, plus "Paid to sponsor" and "Received from sub-sponsors". Nothing in the evidence shows a sub-sub-sponsor, but nothing forbids one either.

### Money moves on four distinct paths
1. **Visitor buys a pass** — pass price + ₹5 marketplace fee, minus any coupon, by UPI/Card/Wallet.
2. **Visitor books a service** — service price, by UPI/Card.
3. **Visitor donates** — any amount, to a named pandal, optionally anonymous, receipt issued.
4. **Sub-sponsor buys pool passes from a sponsor** — quantity × sponsor's price, by UPI/Card, *inside the platform*.

Path 4 is the surprising one: the platform is intermediating a B2B sale between two of its own tenants. Combined with the ₹5 fee taken out of the same transaction as the committee's money in path 1, this is squarely a payment-aggregator question.

### Branding is priced, dated, approved inventory
Placements are a closed list (Home Screen, Pass Confirmation, My Pass Screen), priced per week (₹5,000 / ₹3,500 / ₹2,500), bound to date ranges, per pandal, and each creative is Approved / Pending Approval / Rejected by the Super Admin. Entitlement is a count from the sponsorship package.

---

## 7. What [D] asks for that no screen shows

These are whole modules with zero design behind them. They are the biggest schedule risk in the project, because they are invisible in every demo.

1. **Pandal Promotional Page + CMS** — [D] mobile §4 and web §4. A public page per pandal: hero image/video, theme, story, history, awards, gallery, events and schedules, visitor guidelines, accessibility, parking and transport, sponsor logos, a shareable deep link — managed through a **draft → submit → approve/reject → publish** workflow with media validation, versioning and audit history. Nothing in [P] or [R].
2. **Notifications & Campaign Management** — push on booking/reminder/payment/pass change, announcements, audience segmentation, scheduling, templates, delivery history, approval workflow for promotional sends, deep links, and per-user notification preferences. The app has a bell icon and nothing behind it.
3. **Reports & Analytics** — booking and sales reports, slot utilisation and occupancy, visitor/pass usage, pandal performance, sponsor revenue and entitlement utilisation, branding impressions/clicks, payment reconciliation, workforce utilisation, export to CSV/XLSX/PDF under role permissions.
4. **Configuration & Master Data** — pass types, slot types, pricing/fee configuration, cities/states/localities, profile types, event categories, sponsor packages, branding locations, notification templates, cancellation/refund rules, system parameters.
5. **User Management** — user master, search/filter, account status and access control, booking history for support roles, profile verification, data export under policy.
6. **Auth hardening** — optional MFA, session timeout, password reset, login history, admin audit trail.
7. **Pandal discovery** — search by name or locality; filters by distance, popularity, theme, availability, pass type, special facilities; nearby by location with consent; sorting. In [P] *Explore Pandals* and *Nearby Pandals* exist only as home-screen tiles.
8. **Cancellation and refunds** — [D] wants configurable cancellation/refund rules, refund status tracking and invoice/receipt generation. There is no cancel action on any screen.
9. **Volunteer scan history for admins** — [D] web §12 asks for it; [R] shows only a volunteer roster.
10. **Multiple passes in one booking with individual QR codes** — [D] §7. The prototype issues one pass covering many pandals instead.

---

## 8. What the prototype shows that [D] never mentions

1. **The eligibility questionnaire** — six configurable questions, a Pending review state, a Not-Eligible refusal, and a drop-off funnel. This gates revenue.
2. **The 3-minute one-time entry code**, and with it the whole mint/scan split.
3. **The ₹5 marketplace fee.**
4. **Coupon codes** at checkout.
5. **Wallet** as a payment method alongside UPI and card — which implies stored value, a top-up path and refunds into it.
6. **Language selection** before sign-up (English / Bengali / Hindi).
7. **Groups as durable, named entities** with a locality and an enlisted pandal list, existing before any booking.
8. **Sub-sponsor purchase of passes with real money inside the platform.**
9. **Branding as priced, dated ad inventory** with named placements.
10. **Visitor-readable lost & found**, per pandal.
11. **Pass category Family / Sponsor** as a per-pandal choice inside the City flow.
12. **The pandal master with per-pandal capacity and an Open / Opens-on-date lifecycle.**

---

## 9. Data the system handles that deserves special care

- **Gotra** and **sankalp** (Puja By Your Name) — religious affiliation and a personal prayer.
- **Type of assistance / wheelchair required** (Special Assistance) and the *Specially Abled* profile type — disability.
- **ID verification and address proof** (eligibility questions 3 and 4) — identity documents, for a purpose no source explains.
- Full contact details on every lost-item report and every support request, visible to pandal staff.

No source states a retention period for any of it.

---

## 10. Contradictions inside the evidence

Source tags, used throughout this document:
**[D]** = the client's `Application Features` document · **[R]** = the admin-portal screen recording · **[P]** = the clickable prototype website.

**10.1 Does a City Pass have a date and a slot?**
`CityPass` / `CityPassPuja` go straight from pandal selection to *Continue to payment* — no date, no slot. `CityVisitDateTimeUpdated` gives every selected pandal a **visit date, a time slot, and a Pass Category toggle (Family Pass / Sponsor Pass)**. Two different products wearing the same name.

**10.2 How many people does a Group Pass cover?**
Checkout says *"Up to 4 members"*; My Pass says *"Includes 18 members"*; the group list says *"Shib Mandir Squad · 18 Pujas"* — which is a count of **pandals**, not members. Both strings live in the **same source file** (`OnboardingClickFlow`, which inlines checkout and My Pass), so this is not two screens drifting apart: one screen flow asserts both numbers. Group *size* has been conflated with the group's *pandal list*.

**10.3 There are three incompatible pass taxonomies.**
- [D] §5: General, Preview, VIP, Family, Group, plus "configured special pass types".
- [P]/[R]: Individual, Group, City.
- [P] City flow: Family Pass / Sponsor Pass as a per-pandal **category**.

Product, category and tier are being used interchangeably.

**10.4 There are two service catalogs.**
Platform services with bespoke forms (Curated Tours, Puja By Your Name, Special Assistance, Aarti Slot) live in the app Menu. Pandal-configured services with a price and a list of available days (VIP Darshan Fast-Track, Prasad Home Delivery, Guided Photography Session, Heritage Pandal Walk) live in the Pandal Admin and appear on the service payment screens. [D] §8 lists only the first four. Nothing says how they relate.

**10.5 The QR contradiction**, §3 above: [D] wants a downloadable, shareable pass QR with a durable status; [P] mints a 3-minute single-use code.

**10.6 Sponsor pool arithmetic doesn't close.** Overview shows Purchased 850 / Issued 115 / Remaining 735, yet *Distribution by Pass Type* prints **735 remaining on every row** (Individual, Group, City alike) while issuing 80, 35 and 0 respectively. Either "remaining" is a single shared pool being displayed per row, or the numbers are decorative. The same page shows per-pandal purchases of 500 + 200 + 150 = 850 — so a pool that is scoped per pandal is being reported as one aggregate.

**10.7 Branding entitlement is shown being exceeded.** *"Gold Sponsor package includes 2 banner placement(s) · 3 in use"* — while [D] §8 explicitly requires "prevent unauthorized benefits by enforcing package entitlements".

**10.8 Sub-sponsor credentials are shown in clear text** in a table, to the sponsor and to the Super Admin. The platform is creating accounts and displaying their passwords.

**10.9 Super Admin IA is mislabelled.** *Groups* opens a pandal master. *Donations* opens a combined passes-and-donations report. Naming will have to be fixed before it is coded, or the labels will leak into the API.

**10.10 Registration channel.** [D] §1 says "mobile number/email registration with OTP"; [P] offers mobile only, behind a fixed +91.

---

## 11. Questions the client owes us

Ordered by how much they change the build.

1. **What does eligibility actually decide?** Who reviews a *Pending*? What happens to a *Not Eligible* — refused a pass entirely, or only some pass types? Is residency really a bar to buying? Are ID and address proof documents uploaded, and if so, kept where and for how long?
2. **Is the entry code the product, or is [D]'s downloadable pass?** Everything about the gate, offline behaviour and fraud posture follows from this one answer.
3. **What level does capacity live at** — pandal, date, slot, pass type, or the configuration row? And does a City Pass consume capacity at each pandal it covers? If not, what stops a pandal filling with City Pass holders?
4. **Does the platform touch the money?** The ₹5 fee rides on the committee's payment, and the sponsor→sub-sponsor sale is settled in-platform. If the platform is in the flow, it is a payment aggregator and needs the corresponding licence, settlement and reconciliation design.
5. **Whose coupon is it** — the pandal's discount or the platform's? Who absorbs it? Is the ₹5 fee refundable on cancellation?
6. **What is the Wallet?** Stored value we hold, or a pass-through to a third party? Stored value means balances, top-ups, refunds-into-wallet and a whole compliance surface.
7. **Who owns a group?** Who creates one, who may join, who edits its enlisted pandal list, and does that list belong to the group or to the pass bought against it?
8. **How deep does the sponsor hierarchy go?** Can a sub-sponsor create sub-sponsors?
9. **Cancellation and refunds** — the rules, the window, who initiates, and what happens to an already-consumed leg on a multi-pandal pass.
10. **Manual exception admission** — [D] requires it, no screen has it. Who may override, and what is recorded?
11. **Do gates work offline?** [D] says it "may be considered". A yes changes the code format, the device, and the reconciliation design.
12. **The promotional page / CMS module** — is it in scope for this release? It is roughly a third of the written web requirement and has no design.
13. **Load, uptime, retention.** No source gives a peak-concurrency figure, a response-time target, an uptime expectation or a data-retention period. Peak concurrency is the one to chase hardest: this is a five-day event where a whole city books in the same fortnight and scans in the same evenings.

---

## 12. How this evidence was gathered

So that any claim here can be re-checked.

- **[D]** — `word/document.xml` extracted from the .docx and flattened to text.
- **[R]** — the 89-second recording decomposed into 68 scene-change frames with `ffmpeg` (`select='gt(scene,0.04)'`), each read individually. Every admin screen below is from a specific frame. *Sponsorship Packages* is in the sidebar but is never opened in the recording, so its content is unknown.
- **[P]** — the prototype is a Vite build whose bundle carries a module manifest. `/__mockup/assets/index-CC0aqe35.js` lists all **54** screens as `./components/mockups/edurgapuja/*.tsx`; each was then opened at `/__mockup/preview/edurgapuja/<Name>`.
- **Liveness check.** Not every one of the 54 is reachable. The canonical flow's own chunk, `OnboardingClickFlow-DSKjF9wc.js`, imports 33 of them — including `CityPassPuja` and `CityVisitDateTimeUpdated` — and inlines the rest (language, sign-up, OTP, home, checkout, My Pass, history). Where two variants of a screen exist, the one imported by the click flow is the live one; the plain-named variant (`CityPass`, `Services`, `Donate`, `PandalStatus`, `SpecialAssistance`, the `*Prototype` files) is superseded.
