# eDurgaPuja — Functional Requirements

This document is the single source of requirement IDs. Everything downstream —
use cases, user stories, the data model, the endpoints, the tests, the commit
messages — references these IDs rather than restating the requirement.

## How to read it

**Source.** Where the requirement comes from. `D` = the client's *Application
Features* document · `R` = the admin-portal screen recording · `P` = the
clickable prototype · `—` = neither; a decision we made.

**Status.**

| Status | Meaning |
|---|---|
| **Agreed** | The sources concur, or only one source covers it and nothing contradicts it. Build it. |
| **Doc-only** | In the client document, with no design anywhere. Real scope, no picture of it. The largest schedule risk in the project. |
| **Open · Cn** | Blocked on contradiction *n* from `eDurgaPuja-Contradictions.pdf`. The statement below is written so that it holds either way; the bracketed note says what the answer changes. |
| **Decided** | The sources conflict or are silent, and the safe answer is not in doubt. Recorded here so nobody re-opens it. |

**Numbering.** IDs are permanent and are never reused or renumbered. Each area
has spare numbers so later requirements slot in without disturbing the rest.

---

## A · Identity, profile and language — FR-001…019

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-001 | A visitor chooses an interface language — English, Bengali or Hindi — before signing up. | P | Agreed |
| FR-002 | A visitor changes the interface language at any time afterwards. | P D | Agreed |
| FR-003 | A visitor registers with a mobile number, verified by a one-time code. | D P | Agreed |
| FR-004 | A returning visitor signs in with the same mobile number and a one-time code. Registration and sign-in are the same entry point, and the system does not reveal whether a number is already registered. | P | Agreed |
| FR-005 | A one-time code expires after a configured interval, tolerates a configured number of wrong attempts, and cannot be requested again until a cooldown has elapsed. | D | Agreed |
| FR-006 | Issuing a new one-time code invalidates every earlier live code for that destination, so two valid codes never coexist. | — | Decided |
| FR-007 | Sending of one-time codes is rate-limited per destination and per source address. | D | Agreed |
| FR-008 | A visitor accepts the Terms and Privacy Policy by continuing past sign-up; the accepted version is recorded against the account. | P | Agreed |
| FR-009 | A visitor holds a profile of first name, last name, mobile, email, date of birth, city, state, PIN code, gender and zero or more profile types. | D P — | Agreed · D10 |
| FR-010 | Profile types are Senior Citizens, Families with Young Children, Specially Abled, Press and Social Media Influencer, and are maintained as master data rather than hard-coded. | D P | Agreed |
| FR-011 | A visitor sees how complete their profile is, and what completing it unlocks. | P | Agreed |
| FR-012 | A visitor edits their profile; the mobile number is shown as verified and is not editable in place. | D P | Agreed |
| FR-013 | A visitor signs out, ending the session on that device only. | D | Agreed |
| FR-014 | Sessions expire, and a client refreshes its credentials without asking the visitor to sign in again. | D | Agreed |
| FR-015 | Email is profile data and never a sign-in credential; identity is the mobile number alone. | — | Decided · D10 |
| FR-016 | A visitor's mobile number is stored in a single canonical format, so the same number entered in any notation reaches the same account. | — | Decided |
| FR-017 | Sign-up captures the mobile number only. First name, last name, email and date of birth are captured afterwards, on the profile screen. | — | Agreed · D10 |
| FR-018 | Date of birth satisfies any age-based eligibility question, rather than the visitor being asked their age a second time. | — | Decided |
| FR-019 | A purchase made on the web verifies the buyer's mobile number by one-time code, creating the account if it does not exist. Because the mobile number is the identity, the same number signing in to the app sees what was bought, with no account-linking step. | — | Agreed |

---

## B · Eligibility — FR-020…029

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-020 | A visitor answers an eligibility questionnaire before choosing a pass. | P | Agreed |
| FR-021 | The questionnaire is configurable: a Super Admin adds, edits, reorders and retires questions without a release. | R | Agreed |
| FR-022 | Each answer is stored against the visitor and is visible to the platform, never to a pandal or a sponsor. | P R | Agreed |
| FR-023 | A visitor holds one of three eligibility verdicts: Approved, Pending, or Not Eligible. | R | Agreed |
| FR-024 | A Pending verdict is resolved by a human reviewer, who records a reason. | R | Agreed |
| FR-025 | A Super Admin sees, per question, how many visitors reached it and how many continued past it. | R | Agreed |
| FR-026 | An eligibility verdict governs what the visitor may then do. *[Open: whether it gates access, changes price, or grants priority. Residency is question one, so a refusal on residency is possible and must be confirmed as policy.]* | P R | Open |
| FR-027 | Questions that ask for identity or address evidence capture that evidence. *[Open: whether documents are uploaded, who reviews them, where they are stored and for how long. Two of the six questions are ID verification and address proof.]* | R | Open |
| FR-028 | A visitor whose verdict is Not Eligible is told why, and what they may do about it. | — | Decided |

---

## C · Pandal discovery and content — FR-030…049

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-030 | A visitor browses pandals, filtered by city and locality. | D P | Agreed |
| FR-031 | A visitor searches pandals by name or locality. | D | Doc-only |
| FR-032 | A visitor filters pandals by distance, popularity, theme, availability, pass type and special facilities. | D | Doc-only |
| FR-033 | A visitor sees pandals near their current location, only after granting location consent. | D | Doc-only |
| FR-034 | A visitor sorts results by distance, popularity, rating or recommended order. | D | Doc-only |
| FR-035 | A pandal has a public promotional page carrying hero media, name, location, theme, story, organiser information, a gallery, events and schedules, visitor guidelines, accessibility information, parking and transport, and approved sponsor branding. | D | Doc-only |
| FR-036 | A pandal's promotional page has a shareable, deep-linkable URL suitable for campaign distribution. | D | Doc-only |
| FR-037 | Promotional content is authored in the admin portal through a draft → submit → approve or reject → publish workflow. | D | Doc-only |
| FR-038 | Promotional content is versioned, and every change is attributable. | D | Doc-only |
| FR-039 | Uploaded media is validated for file type, size and dimensions before it is accepted. | D | Doc-only |
| FR-040 | An administrator previews a promotional page as a visitor would see it, before publishing. | D | Doc-only |
| FR-041 | A pandal has an opening date and is shown as Open or as opening on that date. | R | Agreed |
| FR-042 | A pandal record holds committee and organiser details, contact information, and a geographic position. | D R | Agreed |
| FR-043 | A visitor sees a personalised home screen with a Puja countdown, quick actions, featured pandals and promotional banners. | D P | Agreed |
| FR-044 | Every pandal has a public landing page. It is the pandal's primary presence — indexable, shareable and reachable at a stable URL — and it works for a visitor who has never installed the app. | — | Agreed |
| FR-045 | A pandal declares which of pass sales, donations and value-added services it offers. A pandal may have a landing page and sell no passes at all. | — | Agreed |
| FR-046 | A visitor donates to a pandal from its landing page and completes the payment on the web, without installing anything. | — | Agreed |
| FR-047 | A visitor books that pandal's value-added services from its landing page and pays on the web. | — | Agreed |
| FR-048 | Pass booking appears on a landing page only for a pandal that sells passes. | — | Agreed |
| FR-049 | A pass bought on the web is delivered to the buyer's app, keyed by the mobile number used at checkout. | — | Agreed |
| FR-050a | A pandal's landing page is composed of ordered, individually hideable blocks, so a capability turning on adds a block rather than redesigning the page. | — | Agreed |
| FR-050b | A pandal's landing page carries that pandal's own colours, typography and mark, not a shared platform skin. | — | Agreed |
| FR-050c | A pandal defines preset donation offerings, each an amount with its own purpose — "₹501 · Support a diya" — shown on its page alongside a custom amount. | — | Agreed |
| FR-050d | A donation records which offering or which shared link it came from, so a pandal can see what its donors respond to. | — | Agreed |

---

## D · Pass products and inventory — FR-050…069

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-050 | A visitor chooses between three pass products: Individual, Group and City. | P R | Agreed |
| FR-051 | A pass covers one or more pandals, and each covered pandal carries its own admission state and its own admission time. | P | Agreed |
| FR-052 | An Individual Pass covers pandals the visitor picks, each with a visit date and time slot chosen independently. | P | Agreed |
| FR-053 | A Group Pass covers the pandals enlisted to a chosen group, under a single date and time slot for the whole set. | P | Agreed |
| FR-054 | A City Pass covers a chosen set of pandals on one chosen date, with no time slot; the holder visits them in any order. | P — | Agreed · D3 |
| FR-055 | A Group Pass covers a head count chosen at purchase. An Individual Pass and a City Pass each cover one person. | — | Agreed · D4 |
| FR-056 | A Pandal Admin configures passes as rows of pass type, optional group, date range, time range, price and a cap on passes issued. | R | Agreed |
| FR-057 | A configuration row is activated or deactivated without being deleted. | R | Agreed |
| FR-058 | Every configuration change is recorded with who changed it, when, and the resulting issued and remaining counts. | R | Agreed |
| FR-059 | Each pandal defines a capacity, and no more passes than that are ever issued for that pandal. Configuration rows carry price, dates and times; the pandal's number is the binding ceiling. | R — | Agreed · D2 |
| FR-060 | The catalogue has two levels: a **product** fixed by the platform — Individual, Group or City — and a **category** defined by each pandal, which carries the price. | — | Agreed · D4 |
| FR-061 | A Pandal Admin issues complimentary passes against capacity without payment. | D | Doc-only |
| FR-062 | An administrator issues passes in bulk to a named recipient group. | D R | Agreed |
| FR-063 | A pass carries a status through its life: active, used, cancelled, expired or blocked. These belong to the pass, not to the admission code. | D — | Agreed · D1 |
| FR-064 | A visitor holds more than one pass at a time, and adds another from the pass screen. | P | Agreed |
| FR-065 | A pass carries a human-readable identifier shown to the visitor and to gate staff. That identifier is a reference only, and is never sufficient to gain admission. | P R | Decided |
| FR-066 | A Pandal Admin defines its own pass categories — Sponsor, VIP, Para Pass, Senior Citizen, Donor and any others it wants — each with its own price. | — | Agreed · D4 |
| FR-067 | A category applies to the Individual product. A Group Pass is that category bought in multiples; a City Pass is available for one person only. | — | Agreed · D4 |
| FR-068 | Passes issued out of a sponsor's pool are issued in the Sponsor category, which is how the sponsorship hierarchy meets the pass catalogue. | — | Decided |
| FR-069 | A City Pass may only cover pandals that sell passes, and consumes one unit of each covered pandal's capacity on the chosen date. | — | Agreed · D2 |

---

## E · Booking and checkout — FR-070…084

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-070 | Selecting a pass holds the inventory it needs for a bounded period, before payment. | D P | Agreed |
| FR-071 | A hold that is not paid for within its window is released, and the inventory becomes available again. | D | Agreed |
| FR-072 | A visitor sees, before paying, the pass price, the number of people covered, the platform fee and the total. | P | Agreed |
| FR-073 | A visitor applies a coupon code at checkout, and sees the discount applied to the total. | P | Agreed |
| FR-074 | A booking is confirmed only after payment succeeds. | D P | Agreed |
| FR-075 | A visitor sees their booking history and the status of each booking. | D | Doc-only |
| FR-076 | A visitor cancels a booking within a configured window and receives the refund the policy allows. | D | Doc-only |
| FR-077 | Cancellation and refund rules are configured as master data, per pass type, not written into code. | D | Doc-only |
| FR-078 | A booking that covers several pandals is cancellable in whole; whether a single covered pandal can be cancelled once others have been visited is undecided. | — | Open |
| FR-079 | Minimum and maximum quantities per booking are configurable. | D | Doc-only |
| FR-080 | Blackout dates, holidays and individual slot closures are configurable and prevent booking. | D | Doc-only |

---

## F · Payments, fees and refunds — FR-085…099

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-085 | A visitor pays through an approved payment gateway, using the methods the gateway exposes. | D | Agreed |
| FR-086 | A visitor pays by UPI, card or wallet. | P | Agreed |
| FR-087 | The application never stores raw card credentials; payment is completed by redirection or by the gateway's own SDK. | D | Agreed |
| FR-088 | Payment success, failure, timeout and retry are each handled, and no combination leaves money taken without a booking, or a booking without money. | D | Agreed |
| FR-089 | A repeated payment request carrying the same idempotency key produces the same order, never a second charge. | — | Decided |
| FR-090 | Every gateway notification is verified for authenticity, stored raw, and processed exactly once however many times it is delivered. | — | Decided |
| FR-091 | Each transaction carries a provider reference that supports reconciliation against the gateway's own records. | D | Agreed |
| FR-092 | An invoice or receipt is generated where required. | D | Doc-only |
| FR-093 | Refund status is tracked from request to completion. | D | Doc-only |
| FR-094 | The platform charges a marketplace fee, shown to the visitor as a separate line, collected in the same transaction as the pass price. | P | Agreed |
| FR-095 | Money collected on behalf of a committee reaches that committee. *[Open: whether the platform settles it or the gateway splits it at source. This decides whether the platform is a payment aggregator, and it is the most consequential commercial question in the project.]* | — | Open |
| FR-096 | A coupon's cost is borne by a defined party. *[Open: pandal discount or platform promotion. It changes settlement, not the checkout screen.]* | P | Open |
| FR-097 | The Wallet payment method behaves as defined. *[Open: stored value the platform holds — which implies balances, top-ups and refunds into it — or a pass-through to a third-party wallet.]* | P | Open |
| FR-098 | Whether the marketplace fee is refunded on cancellation is defined by policy and applied consistently. | — | Open |

---

## G · Entry and admission — FR-100…119

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-100 | A pass holder obtains an admission credential for one covered pandal at a time. | P | Agreed |
| FR-101 | An admission credential admits exactly once, at one pandal. | P | Agreed |
| FR-102 | An admission credential expires a short, fixed interval after it is created, and can be replaced once it has expired. | P | Agreed |
| FR-103 | Creating a replacement credential invalidates every earlier live credential for that pandal on that pass, so two admitting credentials never coexist. | — | Decided |
| FR-104 | Obtaining an admission credential is unlimited; being admitted is not. | P | Agreed |
| FR-105 | The admission credential is a short-lived one-time code generated by the holder at the gate — not a durable, shareable pass QR. | P — | Agreed · D1 |
| FR-106 | Gate staff sign in to a scanning application with their own credentials. | P | Agreed |
| FR-107 | A gate session is bound to one pandal and one named gate. | P | Agreed |
| FR-108 | Scanning a credential returns one of three outcomes: admitted, expired, or already used. | P R | Agreed |
| FR-109 | An admitted scan shows the holder's name, the pandal, the pass type and the time. | P | Agreed |
| FR-110 | Every scan is logged, whatever its outcome, with the gate, the device and the time. | D | Agreed |
| FR-111 | Gate staff review their recent scans on the device. | P | Agreed |
| FR-112 | An authorised person admits by manual exception, and the reason is recorded. *[C7: the document requires it; no screen in any source provides it. Gates will need it on the night.]* | D | Open · C7 |
| FR-113 | A gate validates and admits while disconnected, and reconciles when connectivity returns. | D — | Agreed · D5 |
| FR-114 | No credential is admitted twice, replayed, forged, or accepted at two gates at once. | — | Decided |
| FR-119 | A visitor generates an admission code without network connectivity, so that entry does not depend on mobile data working in a dense crowd. | — | Decided · D5 |
| FR-115 | A visitor sees, per pass, which covered pandals are visited and which are pending, with the admission time of each. | P | Agreed |
| FR-116 | A visitor sees how many of the pandals covered by a pass they have visited. | P | Agreed |
| FR-117 | An administrator defines the gates at a pandal and their active status. | D R | Agreed |
| FR-118 | An administrator sees entry activity by gate and by slot. | D R | Agreed |

---

## H · Groups — FR-120…129

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-120 | A group exists as a named entity with a locality and an enlisted list of pandals, before any pass is bought against it. | P | Agreed |
| FR-121 | A visitor chooses an existing group and books a Group Pass against it. | P | Agreed |
| FR-122 | The pandals covered by a Group Pass are the group's enlisted pandals, shown read-only at booking. | P | Agreed |
| FR-123 | A group has an owner, and a defined rule for who may join it. *[Open: no source says who creates a group, who may join, or whether the enlisted pandal list belongs to the group or to the pass.]* | — | Open |
| FR-124 | An administrator configures group pass types, group size, price, validity, date and slot, and eligibility. | D | Doc-only |
| FR-125 | An administrator sets allocation limits and approval requirements for group passes. | D | Doc-only |
| FR-126 | An administrator tracks group passes issued, assigned, used and remaining. | D | Doc-only |
| FR-127 | An administrator configures what additional information group members must supply. | D | Doc-only |
| FR-128 | A Super Admin manages groups across the platform. | R | Agreed |

---

## I · Value-added services — FR-130…139

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-130 | A visitor books a value-added service for a specific pandal and day, and pays for it. | D P | Agreed |
| FR-131 | Each service captures the information that service needs, not a common form. Puja By Your Name captures the name the Puja is performed in, the gotra and the sankalp; Special Assistance captures the assistance type and any equipment needed; Aarti Slot Booking captures a slot and a number of attendees; Curated Tours captures a pandal, a date and a time window. | P | Agreed |
| FR-132 | A Pandal Admin defines its own services with a description, a price and the days they are available. | R | Agreed |
| FR-133 | Value-added services belong to a pandal. The platform defines the form shapes — curated tour, puja in your name, special assistance, aarti slot, and a plain priced service — and each pandal chooses which of them it offers, names them and prices them. | P R — | Agreed |
| FR-134 | A visitor receives a confirmation for a booked service. | P | Agreed |
| FR-135 | An administrator views service bookings, filtered by service type. | R | Agreed |
| FR-136 | Service revenue is reported separately from pass revenue and from donations. | R | Agreed |

---

## J · Donations — FR-140…149

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-140 | A Pandal Admin generates a shareable donation link with an optional suggested amount and an optional purpose. | R | Agreed |
| FR-141 | A Pandal Admin sees every link created for their pandal, newest first, and copies any of them. | R | Agreed |
| FR-142 | Opening a donation link takes the visitor to the donate screen for that pandal, pre-filled with the link's amount and purpose. | P R | Agreed |
| FR-143 | A donor gives a preset or a custom amount, without holding a pass. | P | Agreed |
| FR-144 | A donor leaves their name blank to give anonymously; the receipt then carries no name. | P | Agreed |
| FR-145 | A donor may attach a short message. | P | Agreed |
| FR-146 | A receipt is issued on successful payment. | P D | Agreed |
| FR-147 | A Pandal Admin views donations separately from pass revenue. | R | Agreed |
| FR-148 | Whether donation receipts must be tax-deductible is defined. *[Open: 80G eligibility depends on each committee's own registration and changes what identity a donor must supply — which conflicts with anonymous giving.]* | — | Open |

---

## K · Sponsorship and pass pools — FR-150…169

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-150 | A Pandal Admin defines sponsorship packages carrying a pass count, a value, banner placements, benefits and a validity period. | D R | Agreed |
| FR-151 | A Pandal Admin adds a sponsor and allocates a package to it. | D R | Agreed |
| FR-152 | An allocation is pending until the sponsor accepts it; the passes are unusable before acceptance. | R | Agreed |
| FR-153 | A Sponsor Admin accepts or declines an allocation. | R | Agreed |
| FR-154 | A Pandal Admin views the full allocation history for their pandal, newest first. | R | Agreed |
| FR-155 | A Sponsor Admin views their packages, entitlements and remaining pool, per pandal and in total. | R | Agreed |
| FR-156 | A Sponsor Admin distributes passes directly to named guests, or in bulk to a named recipient group. | R | Agreed |
| FR-157 | A Sponsor Admin requests additional passes from a pandal. | R | Agreed |
| FR-158 | A Sponsor Admin creates sub-sponsors, each with its own sign-in, and sets the price per pass it charges them. | R | Agreed |
| FR-159 | A Sub-Sponsor Admin buys passes only from its parent sponsor, never directly from a pandal. | R | Agreed |
| FR-160 | A Sub-Sponsor Admin pays its sponsor for passes through the platform, by UPI or card. | R | Agreed |
| FR-161 | A Sub-Sponsor Admin issues passes in bulk or assigns a single pass to a named recipient, and views its issuance history. | R | Agreed |
| FR-162 | A Sponsor Admin sees what its sub-sponsors have issued and what they have paid. | R | Agreed |
| FR-163 | A pool belongs to a sponsor **at one pandal**. The sum of passes outstanding and issued from a pool never exceeds what that pandal allocated to it, and the same holds one tier further down, under concurrent operation. | R — | Agreed · D6 |
| FR-164 | Whether a sub-sponsor may itself create sub-sponsors is defined. | — | Open |
| FR-165 | Sponsor accounts are created by invitation; the invitee sets their own password, and no one else ever sees it. | — | Decided |

---

## L · Sponsor branding — FR-170…179

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-170 | The platform defines the branding placements available, as a closed list. | D R | Agreed |
| FR-171 | A sponsorship package grants a number of branding placements. | D R | Agreed |
| FR-172 | A Sponsor Admin uploads a creative, choosing the pandals it runs at, its placement, and its start and end dates. | R | Agreed |
| FR-173 | Selecting several pandals for one creative produces one creative entry per pandal. | R | Agreed |
| FR-174 | A Super Admin approves or rejects a creative; a rejected creative can be replaced. | D R | Agreed |
| FR-175 | A Sponsor Admin tracks each creative as live, scheduled, pending approval, rejected or expired. | D R | Agreed |
| FR-176 | Branding carries a price per placement per week. | R | Agreed |
| FR-177 | A sponsor cannot create more live placements than its package grants; an attempt to exceed the entitlement is refused at upload, with a reason. | D R — | Decided · D8 |
| FR-178 | A Sponsor Admin previews how a creative will appear in its placement before it goes live. | D | Doc-only |
| FR-179 | Branding impressions and clicks are counted where the instrumentation exists. | D | Doc-only |

---

## M · Volunteers — FR-180…184

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-180 | A Pandal Admin adds a volunteer with a name, a mobile number, an assigned gate and an active status. | D R | Agreed |
| FR-181 | A Pandal Admin deactivates a volunteer, immediately ending their ability to scan. | R | Agreed |
| FR-182 | An administrator views a volunteer's scan history. | D | Doc-only |
| FR-183 | A Super Admin views volunteers across all pandals. | R | Agreed |

---

## N · Live status, lost and found, support — FR-185…199

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-185 | A Pandal Admin publishes an estimated wait time and a crowd level for their pandal. | R | Agreed |
| FR-186 | A visitor sees a pandal's wait time and crowd level, together with how recently it was updated. | P | Agreed |
| FR-187 | A stale reading is visibly stale; the age of the reading is part of what the visitor sees. | P | Decided |
| FR-188 | A visitor reports a lost item with a description, a location and a contact number. | P R | Agreed |
| FR-189 | A visitor sees the outstanding lost items reported at a pandal. | P | Agreed |
| FR-190 | A Pandal Admin marks a lost item found. | R | Agreed |
| FR-191 | A visitor submits a support request or feedback with a name, a contact number, a subject and a message. | P R | Agreed |
| FR-192 | A Pandal Admin views support requests and marks them resolved. | R | Agreed |
| FR-193 | A Super Admin views support requests across all pandals. | R | Agreed |
| FR-194 | An FAQ and help centre is available in the app. | D | Doc-only |

---

## O · Notifications and campaigns — FR-200…214

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-200 | A visitor receives a push notification on booking confirmation, payment status change, and any change to a pass they hold. | D | Doc-only |
| FR-201 | A visitor receives reminders before a booked visit. | D | Doc-only |
| FR-202 | A visitor receives event and pandal announcements. | D | Doc-only |
| FR-203 | An administrator composes a push notification and selects its audience by pandal, location, booking status or a configured segment. | D | Doc-only |
| FR-204 | An administrator schedules a notification for a future time. | D | Doc-only |
| FR-205 | Notification content is composed from managed templates. | D | Doc-only |
| FR-206 | Promotional communication passes an approval workflow before it is sent. | D | Doc-only |
| FR-207 | An administrator sees notification history and per-message delivery status. | D | Doc-only |
| FR-208 | A notification deep-links to the relevant screen in the app. | D | Doc-only |
| FR-209 | A visitor sets their own notification preferences, and promotional messages respect their consent. | D | Doc-only |

---

## P · Reporting and analytics — FR-215…229

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-215 | A Super Admin sees a platform dashboard: users, passes sold, revenue, active groups and today's check-ins, each against the previous period. | R | Agreed |
| FR-216 | A Super Admin sees passes sold broken down by product, and sign-ups over time. | R | Agreed |
| FR-217 | A Super Admin sees a live activity feed of purchases, check-ins, eligibility submissions and group creation. | R | Agreed |
| FR-218 | A Super Admin sees passes and payments across all pandals, with revenue split by product. | R | Agreed |
| FR-219 | A Super Admin sees entry and scan logs across all pandals, with valid, expired and duplicate counts. | R | Agreed |
| FR-220 | An administrator runs booking and pass sales reports. | D | Doc-only |
| FR-221 | An administrator runs slot utilisation and occupancy reports. | D | Doc-only |
| FR-222 | An administrator runs pandal performance reports. | D | Doc-only |
| FR-223 | An administrator runs sponsor revenue and entitlement utilisation reports. | D | Doc-only |
| FR-224 | An administrator runs payment and reconciliation reports. | D | Doc-only |
| FR-225 | An administrator runs workforce attendance and utilisation reports. | D | Doc-only |
| FR-226 | Reports export to CSV, XLSX and PDF, subject to the exporting user's permissions. | D | Doc-only |

---

## Q · Administration, roles and master data — FR-230…254

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-230 | An administrator signs in with a mobile number and a one-time code, choosing a role portal. | R — | Agreed · D11 |
| FR-231 | The role tab at sign-in selects which portal renders. It does not grant the role; authority comes from the account's own role and is enforced server-side. | R | Decided |
| FR-232 | The platform supports four administrative roles — Pandal Admin, Sponsor Admin, Sub-Sponsor Admin and Super Admin — plus Volunteer. | R | Agreed |
| FR-233 | Every administrative view is scoped to the acting user's own entity, except a Super Admin's. | R | Agreed |
| FR-234 | Permissions are enforced per module and per action, not per screen. | D | Agreed |
| FR-235 | Privileged accounts may be required to present a second factor. | D | Doc-only |
| FR-236 | An administrator resets a forgotten password without an operator seeing it. | D | Agreed |
| FR-245 | A Super Admin presents a password in addition to a one-time code, because possession of a SIM alone must not be enough to reach every payment and every visitor on the platform. | — | Decided · D11 |
| FR-246 | Each pandal's landing page is served on its own subdomain — `ballygunge-cultural.edurgapuja.app`. | — | Agreed · D12 |
| FR-247 | A subdomain is claimed when the pandal is created, checked for availability, refused if it collides with a reserved name, and constrained to what DNS allows. | — | Decided |
| FR-248 | A subdomain is fixed once the page is published. Changing it afterwards keeps the old one alive as a permanent redirect, because it will already be printed, shared and messaged. | — | Decided |
| FR-249 | A committee may later serve its page on its own domain, with a certificate issued on demand. | — | Doc-only |
| FR-250 | An administrator's session is confined to the admin host and is never presented to a pandal's subdomain. | — | Decided |
| FR-237 | Administrative accounts for third parties are created by invitation, never by an operator setting and disclosing a password. | — | Decided |
| FR-238 | A Super Admin onboards a committee, creating the pandal record and its first Pandal Admin account. | D | Doc-only |
| FR-239 | A Super Admin maintains master data: pass types, slot types, pricing and fees, states, cities and localities, profile types, event categories, sponsor packages, branding placements, notification templates, cancellation and refund rules, and system parameters. | D | Doc-only |
| FR-240 | A Super Admin searches and filters users, and changes an account's status. | D | Doc-only |
| FR-241 | An authorised support role views a user's booking and pass history. | D | Doc-only |
| FR-242 | User data is exported only under an explicit access policy. | D | Doc-only |
| FR-243 | A Super Admin opens any pandal's or sponsor's operational screens. | R | Agreed |
| FR-244 | Administrative screens use names that describe what they show. | R | Decided |

---

## R · Audit, security and data protection — FR-255…264

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-255 | Every administrative action that changes data is recorded with the actor, the target, the change and the time. | D | Agreed |
| FR-256 | Sign-in history is retained for administrative accounts. | D | Agreed |
| FR-257 | No credential is ever displayed, logged or transmitted in a readable form. | R | Decided |
| FR-258 | Eligibility answers, assistance requirements and religious details captured by services are treated as sensitive: minimum access, no export without policy, and no exposure to pandals or sponsors beyond what they need to serve the visitor. | P | Decided |
| FR-259 | A retention period is defined for personal data, eligibility evidence, scan logs and payment records. *[Open: no source states one.]* | — | Open |
| FR-260 | A visitor may request deletion of their account and personal data, subject to what must be retained for financial records. | — | Open |

---

## Coverage summary

214 requirements, as at 9 September 2026 — after the client's answers, recorded in
`Decisions.md`. A status carrying `· Dn` was settled by that decision.

| Status | Count | What it means for the plan |
|---|---|---|
| **Agreed** | 130 | Specified well enough to build against. |
| **Doc-only** | 49 | Real scope with no design. Each needs a screen drawn before it can be built, and most sit in modules neither prototype touched. |
| **Open · Cn** | 2 | Still blocked on a contradiction: the two service catalogues (C6), and whether manual-exception admission survives offline gates (C7). |
| **Open** | 12 | Blocked on a question no source addresses. Listed as Q1–Q12 in `Decisions.md`. |
| **Decided** | 21 | Answered without the client because the safe answer is not in doubt. |

**What this says about the month.** The Agreed set is buildable now and is roughly the visitor journey, the gate, and the operational screens. The Doc-only set is the promotional CMS, notifications and reporting — about a third of the written requirement, with nothing drawn. If the deadline is Puja 2026, that third is the natural thing to cut, and cutting it is a conversation to have in the first week rather than the last.
