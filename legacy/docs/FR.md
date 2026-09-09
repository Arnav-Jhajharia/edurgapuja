# PujaPass — Full Requirements Sweep

Everything that could plausibly be a requirement, gathered before narrowing. Sources: the client feature spec, the eDurgaPuja mockups, and the domain itself.

This is deliberately over-inclusive. Nothing here is committed to. Requirements are identified by actor prefix (V, G, PA, SP, SS, SA, SYS) so that the narrowed set can take clean `FR-nn` numbers without collision.

Priority uses the se-edu scale: **Essential** (no user acceptance without it), **Typical** (most similar systems have it), **Novel** (could differentiate the product).

---

## 1. Stakeholders

| Stakeholder | Interest |
|---|---|
| Visitor | Wants entry without queueing, and to find pandals worth visiting |
| Puja committee | Wants crowd control, revenue, and sponsor money |
| Gate volunteer | Wants a scan that works, fast, in a crowd, at night |
| Sponsor | Wants visibility and passes to distribute |
| Sub-sponsor | Wants passes to give its own customers |
| Platform operator (client) | Wants many committees onboarded, and a cut |
| Payment gateway | External system |
| Police / civic authority | Crowd safety; not a system user, but a constraint on capacity |

---

## 2. Functional requirements — Visitor

### Account

- **V-01** Register with a mobile number verified by OTP. *Essential*
- **V-02** Log in with a mobile number verified by OTP. *Essential*
- **V-03** Log out. *Essential*
- **V-04** View and edit a profile: name, contact, city. *Typical*
- **V-05** Delete the account and associated data. *Typical*
- **V-06** Use the app in Bengali or English. *Typical*

### Discovery

- **V-07** Browse a list of participating pandals. *Essential*
- **V-08** Filter pandals by city, locality or date. *Essential*
- **V-09** Search pandals by name. *Typical*
- **V-10** View a pandal's detail page: photos, theme, address, timings. *Essential*
- **V-11** See a pandal's live crowd level and estimated wait time. *Novel*
- **V-12** See directions to a pandal. *Typical*
- **V-13** Save a pandal as a favourite. *Typical*
- **V-14** View a pandal's sponsors. *Typical*

### Booking

- **V-15** View a pandal's slots with current availability. *Essential*
- **V-16** Select a slot and a quantity, and initiate a booking. *Essential*
- **V-17** Have capacity held while payment completes. *Essential*
- **V-18** Pay through the payment gateway. *Essential*
- **V-19** Receive a pass with a QR code on successful payment. *Essential*
- **V-20** Buy an Individual Pass. *Essential*
- **V-21** Buy a Group Pass admitting a party. *Essential*
- **V-22** Buy a City Pass covering multiple pandals over a date range. *Essential*
- **V-23** See the price applicable to the chosen date and time window. *Essential*
- **V-24** Retry a failed payment without losing the booking. *Typical*
- **V-25** Receive a booking confirmation by SMS or WhatsApp. *Typical*

### Passes held

- **V-26** View all passes held. *Essential*
- **V-27** Open a pass QR without a network connection. *Essential*
- **V-28** See a pass's state: valid, used, cancelled, expired. *Essential*
- **V-29** Cancel a pass within the cancellation window. *Typical*
- **V-30** See the refund due before confirming a cancellation. *Typical*
- **V-31** Transfer or share a pass with another person. *Novel*
- **V-32** Add a pass to Apple Wallet or Google Wallet. *Novel*
- **V-33** Receive a reminder before a booked slot. *Typical*

### Groups

- **V-34** Create a group. *Typical*
- **V-35** Invite others to join a group. *Typical*
- **V-36** Join a group by invitation or code. *Typical*
- **V-37** Book a Group Pass against a group. *Essential*
- **V-38** View group members and who holds passes. *Typical*

### Donations

- **V-39** Donate to a pandal from within the app. *Essential*
- **V-40** Open a shared donation link and land on that pandal's donate screen. *Essential*
- **V-41** Donate without holding a pass. *Essential*
- **V-42** Donate without creating an account. *Essential*
- **V-43** Choose an amount, or accept a suggested amount. *Essential*
- **V-44** See the purpose of a donation appeal. *Typical*
- **V-45** Receive a donation receipt. *Typical*
- **V-46** View a history of donations made. *Typical*

### Services

- **V-47** View value-added services offered by a pandal. *Typical*
- **V-48** Book a service for a specific day. *Typical*
- **V-49** View and cancel service bookings. *Typical*

### Support

- **V-50** Report a lost item with a location and contact. *Novel*
- **V-51** View lost and found items for a pandal. *Novel*
- **V-52** Submit a support request or feedback with a subject and message. *Typical*
- **V-53** View the status of a submitted request. *Typical*

---

## 3. Functional requirements — Gate Staff

- **G-01** Log in to a gate device and be bound to an assigned gate. *Essential*
- **G-02** Scan a pass QR and receive an admitted or refused decision. *Essential*
- **G-03** Be prevented from admitting an already-consumed pass. *Essential*
- **G-04** See the reason for a refusal, including prior admission time. *Essential*
- **G-05** Admit a party of N against a Group Pass, tracking partial admission. *Essential*
- **G-06** Continue validating with no network connection. *Essential*
- **G-07** Reconcile offline scans automatically on reconnection. *Essential*
- **G-08** Admit by manual exception where authorised, recording the reason. *Typical*
- **G-09** See a running count of admissions at this gate. *Typical*
- **G-10** Have the device revoked remotely if lost. *Typical*

---

## 4. Functional requirements — Pandal Admin

### Setup

- **PA-01** Create and edit the pandal profile: name, address, theme, photos. *Essential*
- **PA-02** Define gates. *Typical*
- **PA-03** Define slots with a time window and capacity. *Essential*
- **PA-04** Configure passes as rows: type, group, date range, time range, price, cap. *Essential*
- **PA-05** Activate or deactivate a configuration row without deleting it. *Typical*
- **PA-06** View the history of configuration changes with issued and remaining counts. *Typical*
- **PA-07** Open and close bookings for a pandal or an individual slot. *Essential*
- **PA-08** Set cancellation and refund rules within platform limits. *Typical*

### Operations

- **PA-09** View live occupancy against capacity, per slot. *Essential*
- **PA-10** Publish an estimated wait time and crowd level. *Novel*
- **PA-11** Add volunteers with name, mobile, assigned gate and status. *Essential*
- **PA-12** Deactivate a volunteer. *Essential*
- **PA-13** View entry and scan logs for the pandal. *Typical*
- **PA-14** Issue complimentary passes without payment. *Typical*
- **PA-15** View and resolve lost and found reports. *Novel*
- **PA-16** View and resolve support requests. *Typical*

### Money

- **PA-17** View passes sold and pass revenue. *Essential*
- **PA-18** View donations received, separately from pass revenue. *Essential*
- **PA-19** Generate a shareable donation link with optional amount and purpose. *Essential*
- **PA-20** View all donation links created, and copy them. *Typical*
- **PA-21** Revoke a donation link. *Typical*
- **PA-22** View settlement status of money owed to the committee. *Typical*
- **PA-23** Export sales, donations and entry logs. *Typical*

### Sponsorship

- **PA-24** Define sponsorship packages: pass count, value, banner slots, benefits, validity. *Essential*
- **PA-25** Add a sponsor with contact details. *Essential*
- **PA-26** Allocate a package to a sponsor. *Essential*
- **PA-27** View allocation status: pending, accepted, declined. *Essential*
- **PA-28** View the full allocation history. *Typical*
- **PA-29** Withdraw a pending allocation. *Typical*

### Services

- **PA-30** Define value-added services with price and available days. *Typical*
- **PA-31** View service bookings. *Typical*
- **PA-32** Mark a service booking fulfilled. *Typical*

---

## 5. Functional requirements — Sponsor Admin

- **SP-01** Log in to the sponsor portal. *Essential*
- **SP-02** View allocated packages and their entitlements. *Essential*
- **SP-03** Accept or decline an allocation. *Essential*
- **SP-04** View the pass pool held: total, distributed, remaining. *Essential*
- **SP-05** Distribute passes directly to named guests. *Essential*
- **SP-06** Create sub-sponsors under the sponsor account. *Essential*
- **SP-07** Set a per-pass price for sub-sponsors. *Essential*
- **SP-08** Sell pool passes to a sub-sponsor. *Essential*
- **SP-09** View sub-sponsor activity: bought, issued, paid. *Typical*
- **SP-10** Upload branding creatives. *Typical*
- **SP-11** View the approval state of creatives. *Typical*
- **SP-12** View where and how often branding appeared. *Novel*

---

## 6. Functional requirements — Sub-Sponsor Admin

- **SS-01** Log in to the sub-sponsor portal. *Essential*
- **SS-02** View the pool: held, issued, total, paid to sponsor. *Essential*
- **SS-03** View passes available from the parent sponsor and the per-pass price. *Essential*
- **SS-04** Buy passes from the parent sponsor. *Essential*
- **SS-05** Be prevented from buying directly from a pandal. *Essential*
- **SS-06** Issue passes in bulk to a named audience. *Essential*
- **SS-07** Assign a single pass to a named recipient. *Essential*
- **SS-08** View issuance history. *Typical*

---

## 7. Functional requirements — Superadmin

- **SA-01** Log in to the platform portal. *Essential*
- **SA-02** Onboard a committee: create the pandal and its first admin account. *Essential*
- **SA-03** Manage master data: pass types, slot types, cancellation and refund rules. *Essential*
- **SA-04** View a platform dashboard: users, passes sold, revenue, groups, live check-ins. *Essential*
- **SA-05** View passes and payments across all pandals. *Essential*
- **SA-06** View entry and QR logs across all pandals. *Typical*
- **SA-07** Manage users and their eligibility state. *Typical*
- **SA-08** Manage groups platform-wide. *Typical*
- **SA-09** Approve or reject branding creatives. *Typical*
- **SA-10** Access pandal and sponsor operations views for any pandal. *Essential*
- **SA-11** Suspend a pandal, sponsor or user account. *Typical*
- **SA-12** View an audit trail of administrative actions. *Typical*
- **SA-13** Issue a refund manually where automated resolution failed. *Typical*

---

## 8. Functional requirements — System-initiated

No external actor initiates these, so they are not use cases, but they are requirements.

- **SYS-01** Expire unpaid holds and release their capacity.
- **SYS-02** Close a slot automatically at its cut-off time.
- **SYS-03** Resolve a payment captured but not issued, to either issuance or refund.
- **SYS-04** Retry failed refunds until success or escalation.
- **SYS-05** Reconcile offline gate scans on device reconnection.
- **SYS-06** Detect and surface the same pass admitted at two gates.
- **SYS-07** Send booking reminders before a slot begins.
- **SYS-08** Notify a sponsor of a pending allocation and escalate if unacted.
- **SYS-09** Recompute live occupancy figures.
- **SYS-10** Issue receipts for donations and pass purchases.

---

## 9. Non-functional requirements

Organised by the se-edu categories. Each is stated with a number and a measurement method where one is possible; where the client has not supplied a figure, that is recorded as a gap rather than invented.

### Performance and response time

- **N-01** Gate scan-to-decision under 500 ms at p95, including offline operation.
- **N-02** Pandal list and slot availability load under 2 s at p95 on a 4G connection.
- **N-03** Booking confirmation returned within 5 s of payment success at p95.
- **N-04** **Gap.** No peak load figure has been supplied. Capacity planning is unanswerable without it; this is the single most important number to obtain from the client.

### Capacity and scalability

- **N-05** Sustain concurrent booking load at festival peak without degradation of the gate path. Target figure pending N-04.
- **N-06** Traffic is near-flat for months then extreme for roughly five days. The architecture must tolerate a cold-to-peak transition, not just steady state.
- **N-07** Support at least 100 pandals and their slots without query plan changes.

### Availability and reliability

- **N-08** Gate validation continues through a total network outage for at least 4 hours.
- **N-09** Offline scans reconcile within 2 minutes of reconnection.
- **N-10** Recovery point objective 15 minutes; recovery time objective 1 hour.
- **N-11** Failure of any single external dependency degrades only what depends on it. Unrelated operations degrade no more than 10% against baseline.

### Data integrity

- **N-12** The pool invariant holds at every tier under concurrent operation: held plus issued never exceeds capacity granted. Enforced in code, in the database, and by property tests.
- **N-13** Payment and issuance are atomic. 100% of injected failures reach a terminal state within 15 minutes. Zero captured payments with neither pass nor refund.
- **N-14** No pass may be reused, replayed, forged, or admitted at two gates. Zero tolerance, verified by an adversarial suite on every deploy.
- **N-15** Every administrative action affecting money or inventory is auditable to an actor and a timestamp.

### Security

- **N-16** All traffic over TLS 1.3.
- **N-17** Admin sessions expire after a defined period of inactivity.
- **N-18** OTP requests rate-limited per number to resist enumeration and SMS-pumping fraud.
- **N-19** Row-level scoping enforced server-side for every admin view; a role selected at login never grants that role.
- **N-20** Gate device credentials are revocable, and revocation reaches the device on next reconnection.
- **N-21** No card data touches application storage.

### Privacy and compliance

- **N-22** Personal data retained for a defined period after last activity, then deleted. **Gap** — period not specified by the client.
- **N-23** Donor identity requirements depend on whether tax-deductible receipts are offered. **Gap** — unresolved, see open questions.
- **N-24** Whether the platform is a payment aggregator under RBI rules depends on whether donation and pass money settles through it. **Gap** — unresolved, and it is a regulatory question, not a design preference.

### Usability and accessibility

- **N-25** A first-time visitor completes a booking without documentation.
- **N-26** The visitor app is usable one-handed, at night, in a crowd.
- **N-27** Bengali and English throughout the visitor app.
- **N-28** The gate app is operable by a volunteer with under five minutes of training.
- **N-29** Text contrast and target sizes meet WCAG 2.1 AA on visitor-facing screens.

### Environment and portability

- **N-30** Visitor app on Android and iOS; Android is the priority platform for this market.
- **N-31** Gate app must run on low-end Android devices, since volunteers use their own phones.
- **N-32** Backend runs in a container against Postgres 16.

### Maintainability and process

- **N-33** Domain logic that moves capacity is isolated in one module and never bypassed.
- **N-34** The API schema is generated, and generated clients are committed; drift fails CI.
- **N-35** Every architectural decision is recorded as an ADR before implementation.

### Business and domain rules

- **N-36** A sub-sponsor may buy only from its parent sponsor, never from a pandal directly.
- **N-37** Sponsor passes are unusable until the allocation is accepted.
- **N-38** Capacity per slot is a safety constraint, not only a commercial one; overselling has physical consequences in a crowd.
- **N-39** Pass prices vary by date and time window, and the applicable price is the one active at booking time.
- **N-40** A pass consumed at a gate cannot be cancelled or refunded.

### Constraints

- **N-41** The festival date is immovable. Anything not shipped before Mahalaya is shipped next year.
- **N-42** Gate connectivity cannot be assumed. Kolkata pandal crowds saturate mobile networks.
- **N-43** Committee volunteers, not trained staff, operate the admin and gate tools.

### Scope notes

- Out of scope: ticket resale marketplace, transport booking, food ordering, in-app chat.
- Out of scope for release one: sponsor branding impression analytics, multi-city expansion beyond Kolkata.

---

## 10. Glossary

| Term | Meaning |
|---|---|
| **Pandal** | A temporary structure housing the Durga idol; the venue being booked |
| **Slot** | A bookable time window at a pandal, with its own capacity |
| **Pass** | A single admission artifact, scanned at a gate |
| **Entitlement** | What a visitor purchased, which may produce several passes |
| **Pool** | Capacity held by one owner at one point in the ownership chain |
| **Transfer** | Movement of capacity from a parent pool to a child pool |
| **Issue** | Conversion of capacity into a pass held by a person |
| **Hold** | A time-limited reservation of capacity during payment |
| **City Pass** | A pass covering multiple participating pandals |
| **Group Pass** | A pass admitting a party rather than an individual |
| **Sponsor** | An organisation allocated a pass pool by a pandal |
| **Sub-sponsor** | An organisation buying passes from a sponsor |
| **Committee** | The organisation running a pandal |
| **Ashtami** | The peak day of Durga Puja; the load spike this system must survive |

---

## 11. Open questions blocking specification

1. Peak concurrent load. Everything in section 9 marked *Gap* depends on it.
2. Does a City Pass consume capacity at each participating pandal, or admit outside the cap?
3. Does a Group Pass admit a fixed party size, and is partial admission allowed?
4. Does donation money settle to committees directly or through the platform?
5. Are tax-deductible receipts expected?
6. Is the sponsor hierarchy fixed at two levels?
7. Are sponsor allocations against pandal-wide capacity or a specific slot?
8. Is gate connectivity guaranteed by the client, or is offline our problem?
9. What is the "eligibility check" shown in the superadmin activity feed?