# PujaPass — User Stories and Use Cases

Derived from `docs/FR.md`, the full requirements sweep. Every requirement in that
sweep appears here as a user story; the ones that carry branching worth arguing
about appear again as a use case.

This document does not introduce requirements. Where a use case cannot be written
because an open question blocks its main flow, that is recorded in the use case
rather than resolved silently — see §6.

`docs/DeveloperGuide.md` holds the same material for the **narrowed** release-one
set (FR-01 to FR-20). This document is the wider view behind it. `CLAUDE.md`
remains the single source of committed `FR-nn` IDs; §7 covers the requirements that
live there but have not yet been folded back into the sweep.

---

## 1. Conventions

**Priority** carries the se-edu scale used in the sweep: *Essential* (no user
acceptance without it), *Typical* (most similar systems have it), *Novel* (could
differentiate the product).

**Stories** are identified by the sweep's own requirement ID, so traceability needs
no separate table. Where one requirement yields more than one story the ID is
suffixed.

**Use cases** follow se-edu form: a main success scenario numbered from one,
extensions lettered against the step they branch from. Preconditions and guarantees
are stated only where they carry weight. **System** means PujaPass as a whole —
the backend plus whichever client the actor is holding; in gate use cases it
includes the device's own local state, which is the point of them.

---

## 2. User stories

### 2.1 Visitor — account and language

| Req | Priority | Story |
|---|---|---|
| V-01 | Essential | As a visitor, I can register with my mobile number verified by an OTP, so that I can book without keeping a password. |
| V-02 | Essential | As a visitor, I can log in with the same number and an OTP, so that my passes follow me to a new phone. |
| V-03 | Essential | As a visitor, I can log out, so that a borrowed phone does not leave my passes open. |
| V-04 | Typical | As a visitor, I can view and edit my name, contact and city, so that my pass carries details a gate volunteer can check against me. |
| V-05 | Typical | As a visitor, I can delete my account and its data, so that the platform does not hold me after the festival is over. |
| V-06 | Typical | As a visitor, I can read the app in Bengali or English, so that language is not the thing that stops me booking. |

### 2.2 Visitor — discovery

| Req | Priority | Story |
|---|---|---|
| V-07 | Essential | As a visitor, I can browse the participating pandals, so that I plan a route instead of guessing which ones take bookings. |
| V-08 | Essential | As a visitor, I can filter by city, locality or date, so that I see only pandals I can reach on a day I am free. |
| V-09 | Typical | As a visitor, I can search a pandal by name, so that I go straight to the one I already have in mind. |
| V-10 | Essential | As a visitor, I can open a pandal's page and see photos, theme, address and timings, so that I know what I am booking before I pay. |
| V-11 | Novel | As a visitor, I can see a pandal's crowd level and estimated wait, so that I can choose the shorter queue. |
| V-12 | Typical | As a visitor, I can get directions to a pandal, so that I am not navigating by landmark in a crowd. |
| V-13 | Typical | As a visitor, I can save a pandal as a favourite, so that I find it again without re-searching. |
| V-14 | Typical | As a visitor, I can see a pandal's sponsors, so that I recognise the names behind the pandal I am visiting. |

### 2.3 Visitor — booking

| Req | Priority | Story |
|---|---|---|
| V-15 | Essential | As a visitor, I can see each slot with its current availability, so that I do not waste time on one that is already full. |
| V-16 | Essential | As a visitor, I can select a slot and a quantity and start a booking, so that I hold places for everyone coming with me. |
| V-17 | Essential | As a visitor, I can have my capacity held while I pay, so that the slot is not taken from under me mid-payment. |
| V-18 | Essential | As a visitor, I can pay through the gateway, so that payment is not the step that fails. |
| V-19 | Essential | As a visitor, I can receive a pass with a QR code the moment payment succeeds, so that I know the booking is real. |
| V-20 | Essential | As a visitor, I can buy an Individual Pass, so that I can visit on my own. |
| V-21 | Essential | As a visitor, I can buy a Group Pass admitting a party, so that my family enters on one artifact rather than six. |
| V-22 | Essential | As a visitor, I can buy a City Pass covering several pandals over a date range, so that I can hop without booking each one separately. |
| V-23 | Essential | As a visitor, I can see the price that applies to the date and window I chose, so that a peak-day price is not a surprise at checkout. |
| V-24 | Typical | As a visitor, I can retry a failed payment without losing my booking, so that a bank timeout does not cost me the slot. |
| V-25 | Typical | As a visitor, I can receive confirmation by SMS or WhatsApp, so that I hold proof outside the app. |

### 2.4 Visitor — passes held

| Req | Priority | Story |
|---|---|---|
| V-26 | Essential | As a visitor, I can see every pass I hold in one place, so that I am not searching my messages at the gate. |
| V-27 | Essential | As a visitor, I can open a pass QR with no signal, so that a saturated network at the pandal does not keep me out. |
| V-28 | Essential | As a visitor, I can see whether a pass is valid, used, cancelled or expired, so that I do not queue on one that will be refused. |
| V-29 | Typical | As a visitor, I can cancel inside the cancellation window, so that a change of plan does not mean money lost. |
| V-30 | Typical | As a visitor, I can see the refund due before I confirm, so that I am not guessing at the rule. |
| V-31 | Novel | As a visitor, I can pass a booking I cannot use to someone else, so that the place is not wasted. |
| V-32 | Novel | As a visitor, I can add a pass to Apple Wallet or Google Wallet, so that entry does not depend on this app opening. |
| V-33 | Typical | As a visitor, I can get a reminder before my slot, so that I do not miss a window I paid for. |

### 2.5 Visitor — groups

| Req | Priority | Story |
|---|---|---|
| V-34 | Typical | As a visitor, I can create a group, so that the people I go pandal-hopping with are set up once. |
| V-35 | Typical | As a visitor, I can invite others to my group, so that I am not entering their details myself. |
| V-36 | Typical | As a visitor, I can join a group by invitation or code, so that I appear on its passes. |
| V-37 | Essential | As a visitor, I can book a Group Pass against a group, so that the pass covers the people already enlisted in it. |
| V-38 | Typical | As a visitor, I can see who is in a group and who holds passes, so that I know who still needs one. |

### 2.6 Visitor — donations

| Req | Priority | Story |
|---|---|---|
| V-39 | Essential | As a visitor, I can donate to a pandal from the app, so that giving does not need a bank transfer and a phone call. |
| V-40 | Essential | As a donor, I can open a shared link and land on that pandal's donate screen, so that a link in a family group chat is one tap from a donation. |
| V-41 | Essential | As a donor, I can donate without holding a pass, so that supporting a pandal does not require visiting it. |
| V-42 | Essential | As a donor, I can donate without creating an account, so that sign-up is not what stops the donation. |
| V-43 | Essential | As a donor, I can give any amount, or accept the suggested one, so that I decide what the pandal is worth to me. |
| V-44 | Typical | As a donor, I can see what an appeal is for, so that I know what I am funding. |
| V-45 | Typical | As a donor, I can receive a receipt, so that I hold a record of what I gave. |
| V-46 | Typical | As a donor, I can see my donation history, so that I can look up what I gave and when. |

### 2.7 Visitor — services and support

| Req | Priority | Story |
|---|---|---|
| V-47 | Typical | As a visitor, I can see the services a pandal offers, so that I know what can be arranged beyond entry. |
| V-48 | Typical | As a visitor, I can book a service for a chosen day, so that it is arranged before I arrive. |
| V-49 | Typical | As a visitor, I can view and cancel my service bookings, so that a change of plan is not a phone call to the committee. |
| V-50 | Novel | As a visitor, I can report a lost item with where I lost it and how to reach me, so that whoever finds it can return it. |
| V-51 | Novel | As a visitor, I can see the items a pandal is holding, so that I can check before travelling back across the city. |
| V-52 | Typical | As a visitor, I can submit a support request or feedback, so that a problem reaches someone who can act on it. |
| V-53 | Typical | As a visitor, I can see the status of my request, so that I know whether to wait or to chase. |

### 2.8 Gate staff

| Req | Priority | Story |
|---|---|---|
| G-01 | Essential | As gate staff, I can log in to a device that is bound to my gate, so that my scans are attributed to the right entrance. |
| G-02 | Essential | As gate staff, I can scan a QR and get an immediate admitted or refused decision, so that the queue keeps moving. |
| G-03 | Essential | As gate staff, I am stopped from admitting a pass that has already been used, so that one pass cannot be passed around a group. |
| G-04 | Essential | As gate staff, I can see why a pass was refused and when it was previously admitted, so that I can explain a refusal instead of arguing about it. |
| G-05 | Essential | As gate staff, I can admit a party against a Group Pass and see how many remain, so that a family arriving in twos is handled correctly. |
| G-06 | Essential | As gate staff, I can keep validating with no network, so that a dead signal does not stop entry. |
| G-07 | Essential | As gate staff, I can have my offline scans reconcile by themselves when signal returns, so that I am not re-keying anything by hand. |
| G-08 | Typical | As gate staff, I can admit someone by exception and record why, so that a genuine edge case does not become an argument at the gate. |
| G-09 | Typical | As gate staff, I can see a running count of admissions at my gate, so that I know how full the pandal is getting. |
| G-10 | Typical | As gate staff, I can report a device lost and have it revoked, so that a lost phone stops being a working gate. |

### 2.9 Pandal admin — setup

| Req | Priority | Story |
|---|---|---|
| PA-01 | Essential | As a pandal admin, I can create and edit my pandal's profile, so that visitors see what my pandal actually is. |
| PA-02 | Typical | As a pandal admin, I can define my gates, so that scans and volunteers are attributed to an entrance. |
| PA-03 | Essential | As a pandal admin, I can define slots with a time window and capacity, so that arrivals are spread across the day instead of landing at once. |
| PA-04 | Essential | As a pandal admin, I can configure passes as rows with type, group, date range, time range, price and cap, so that a peak evening prices differently from a weekday afternoon. |
| PA-05 | Typical | As a pandal admin, I can deactivate a row without deleting it, so that last year's configuration is still on record. |
| PA-06 | Typical | As a pandal admin, I can see the history of configuration changes with issued and remaining counts, so that a disputed price or cap is settled by the record. |
| PA-07 | Essential | As a pandal admin, I can open and close bookings for the pandal or one slot, so that I stop intake the moment the pandal is over capacity. |
| PA-08 | Typical | As a pandal admin, I can set cancellation and refund rules within platform limits, so that my committee's terms are the ones applied. |

### 2.10 Pandal admin — operations

| Req | Priority | Story |
|---|---|---|
| PA-09 | Essential | As a pandal admin, I can see live occupancy against capacity per slot, so that I know whether to close a slot early. |
| PA-10 | Novel | As a pandal admin, I can publish an estimated wait and a crowd level, so that visitors spread themselves instead of all arriving at eight. |
| PA-11 | Essential | As a pandal admin, I can add volunteers with a name, mobile, gate and status, so that only people I know are scanning at my gates. |
| PA-12 | Essential | As a pandal admin, I can deactivate a volunteer, so that someone who has stopped turning up cannot still admit people. |
| PA-13 | Typical | As a pandal admin, I can see every scan at my pandal, so that a disputed entry can be checked afterwards. |
| PA-14 | Typical | As a pandal admin, I can issue complimentary passes without payment, so that dignitaries and guests are handled without a payment workaround. |
| PA-15 | Novel | As a pandal admin, I can see lost item reports and mark an item found, so that returns are tracked rather than remembered. |
| PA-16 | Typical | As a pandal admin, I can see support requests and mark them resolved, so that nothing raised during the festival is silently dropped. |

### 2.11 Pandal admin — money

| Req | Priority | Story |
|---|---|---|
| PA-17 | Essential | As a pandal admin, I can see passes sold and the revenue against them, so that I know what the pandal has taken. |
| PA-18 | Essential | As a pandal admin, I can see donations separately from pass revenue, so that money against inventory is not mixed with money against nothing. |
| PA-19 | Essential | As a pandal admin, I can generate a shareable donation link with an amount and a purpose, so that an appeal can be circulated on WhatsApp. |
| PA-20 | Typical | As a pandal admin, I can see every link I have created and copy it, so that I re-share an appeal without recreating it. |
| PA-21 | Typical | As a pandal admin, I can revoke a link, so that a closed appeal stops taking money. |
| PA-22 | Typical | As a pandal admin, I can see the settlement status of money owed to my committee, so that I know what has actually reached the account. |
| PA-23 | Typical | As a pandal admin, I can export sales, donations and entry logs, so that my committee's own accounts can be reconciled. |

### 2.12 Pandal admin — sponsorship and services

| Req | Priority | Story |
|---|---|---|
| PA-24 | Essential | As a pandal admin, I can define packages with pass count, value, banner slots, benefits and validity, so that a sponsor buys a defined thing. |
| PA-25 | Essential | As a pandal admin, I can add a sponsor with contact details, so that an allocation has someone to go to. |
| PA-26 | Essential | As a pandal admin, I can allocate a package to a sponsor, so that their passes come out of my capacity and not from nowhere. |
| PA-27 | Essential | As a pandal admin, I can see whether an allocation is pending, accepted or declined, so that I know what capacity is really committed. |
| PA-28 | Typical | As a pandal admin, I can see the full allocation history newest first, so that a dispute over what was given is settled by the record. |
| PA-29 | Typical | As a pandal admin, I can withdraw a pending allocation, so that capacity is not tied up by a sponsor who has gone quiet. |
| PA-30 | Typical | As a pandal admin, I can define services with a price and available days, so that visitors book what my committee can actually deliver. |
| PA-31 | Typical | As a pandal admin, I can see service bookings, so that the committee knows what has been promised. |
| PA-32 | Typical | As a pandal admin, I can mark a booking fulfilled, so that the day's work is tracked rather than recalled. |

### 2.13 Sponsor admin

| Req | Priority | Story |
|---|---|---|
| SP-01 | Essential | As a sponsor admin, I can log in to the sponsor portal, so that I manage my own allocation and nothing else. |
| SP-02 | Essential | As a sponsor admin, I can see my packages and their entitlements, so that I know what I was given. |
| SP-03 | Essential | As a sponsor admin, I can accept or decline an allocation, so that I am not holding passes I never agreed to. |
| SP-04 | Essential | As a sponsor admin, I can see my pool as total, distributed and remaining, so that I do not promise passes I no longer have. |
| SP-05 | Essential | As a sponsor admin, I can distribute passes to named guests, so that a guest receives a pass in their own name. |
| SP-06 | Essential | As a sponsor admin, I can create sub-sponsors under my account, so that my dealers distribute on my behalf. |
| SP-07 | Essential | As a sponsor admin, I can set a per-pass price for sub-sponsors, so that I decide the terms of onward sale. |
| SP-08 | Essential | As a sponsor admin, I can sell pool passes to a sub-sponsor, so that capacity moves down the chain with the money. |
| SP-09 | Typical | As a sponsor admin, I can see what each sub-sponsor bought, issued and paid, so that I can chase what is owed. |
| SP-10 | Typical | As a sponsor admin, I can upload branding creatives, so that my banners can be printed and placed. |
| SP-11 | Typical | As a sponsor admin, I can see the approval state of each creative, so that I know whether to send artwork to print. |
| SP-12 | Novel | As a sponsor admin, I can see where and how often my branding appeared, so that I can judge what the sponsorship bought. |

### 2.14 Sub-sponsor admin

| Req | Priority | Story |
|---|---|---|
| SS-01 | Essential | As a sub-sponsor admin, I can log in to my own portal, so that I see my pool and not my sponsor's. |
| SS-02 | Essential | As a sub-sponsor admin, I can see held, issued, total and amount paid to my sponsor, so that I know both my stock and my liability. |
| SS-03 | Essential | As a sub-sponsor admin, I can see what my parent sponsor has available and at what price, so that I decide how many to buy. |
| SS-04 | Essential | As a sub-sponsor admin, I can buy passes from my parent sponsor, so that I have stock for my own customers. |
| SS-05 | Essential | As a sponsor admin, I can rely on my sub-sponsors being unable to buy directly from a pandal, so that the chain I paid to sit in is not bypassed. |
| SS-06 | Essential | As a sub-sponsor admin, I can issue passes in bulk to a named audience, so that a customer list is handled in one action. |
| SS-07 | Essential | As a sub-sponsor admin, I can assign a single pass to a named recipient, so that one customer is served without a bulk run. |
| SS-08 | Typical | As a sub-sponsor admin, I can see my issuance history, so that I can tell a customer whether their pass was sent. |

`SS-05` is written from the sponsor's side deliberately. Nobody wants to be
prevented from doing something; the value of the constraint belongs to the actor it
protects.

### 2.15 Superadmin

| Req | Priority | Story |
|---|---|---|
| SA-01 | Essential | As a superadmin, I can log in to the platform portal, so that platform-wide work happens under a distinct account. |
| SA-02 | Essential | As a superadmin, I can onboard a committee and hand over an admin account, so that a new pandal can run itself. |
| SA-03 | Essential | As a superadmin, I can manage pass types, slot types and cancellation and refund rules, so that committees configure within the platform's terms. |
| SA-04 | Essential | As a superadmin, I can see a dashboard across all pandals, so that I see the festival as one picture rather than a hundred. |
| SA-05 | Essential | As a superadmin, I can see passes and payments across all pandals, so that a payment dispute anywhere can be answered. |
| SA-06 | Typical | As a superadmin, I can see entry and QR logs across all pandals, so that abuse patterns spanning pandals are visible at all. |
| SA-07 | Typical | As a superadmin, I can manage users and their eligibility state, so that a wrongly categorised visitor can be corrected. |
| SA-08 | Typical | As a superadmin, I can manage groups platform-wide, so that a group spanning pandals still has an owner. |
| SA-09 | Typical | As a superadmin, I can approve or reject branding creatives, so that nothing unapproved is printed under a pandal's name. |
| SA-10 | Essential | As a superadmin, I can open pandal and sponsor views for any pandal, so that I support a committee without asking for their password. |
| SA-11 | Typical | As a superadmin, I can suspend a pandal, sponsor or user, so that abuse is stopped during the festival and not after it. |
| SA-12 | Typical | As a superadmin, I can see an audit trail of administrative actions, so that every change to money or inventory has an actor and a time. |
| SA-13 | Typical | As a superadmin, I can issue a refund manually where automated resolution failed, so that no captured payment is left stranded. |

---

## 3. Use cases

### UC01 Register

**Actor.** Visitor. *(V-01, V-06, N-18)*
**Guarantee.** An account exists against a mobile number only after that number has been verified.

**MSS**

1. Visitor chooses an interface language.
2. Visitor enters a mobile number.
3. System sends a one-time code to that number.
4. Visitor enters the code.
5. System verifies the code, creates the account and signs the visitor in.

Use case ends.

**Extensions**

- 2a. The number already has an account. System continues as a login rather than creating a second account.
- 3a. The code cannot be delivered. System reports the failure and returns to step 2.
- 4a. The code is wrong. System reports it and allows re-entry up to a bounded number of attempts, after which the code is invalidated and step 3 must be repeated.
- 4b. The code expires before entry. System offers a resend, subject to the per-number rate limit.
- 4c. Visitor requests a resend before the resend timer elapses. System refuses and shows the remaining wait.

### UC02 Book an Individual Pass

**Actor.** Visitor. *(V-15 – V-20, V-23, N-12, N-38)*
**Precondition.** Visitor is signed in. Bookings are open for the chosen slot.
**Guarantee.** Either a pass is issued and capacity is consumed, or no capacity is consumed and no money is retained.

**MSS**

1. Visitor opens a pandal and asks to book.
2. System shows the pandal's slots with remaining availability, and the price applying to each.
3. Visitor selects a slot and a quantity.
4. System holds the requested capacity for a bounded period and shows the amount due.
5. Visitor pays.
6. System confirms payment, converts the hold into issued passes, and returns each with its QR code.

Use case ends.

**Extensions**

- 2a. Bookings are closed for the pandal, or every slot is full. System says so. Use case ends.
- 3a. Quantity exceeds remaining capacity. System shows the remaining figure and returns to step 3.
- 4a. Capacity is exhausted between display and request. System reports the slot full and returns to step 2.
- 5a. Visitor abandons payment. The hold expires and its capacity returns. Use case ends without a pass.
- 5b. Payment fails and the hold is still live. System returns to step 5 with the hold intact and the remaining hold time shown.
- 5c. Payment fails and the hold has expired. System releases the capacity and returns to step 2.
- 6a. Payment is captured but issuance fails. System holds the payment in a pending state and resolves it to an issued pass or a full refund without operator intervention.
- 6b. The gateway result is unknown. System treats the booking as pending and reconciles against the gateway before either issuing or refunding.
- 6c. Issuance would take the slot past its capacity. System refuses issuance and refunds in full. Capacity is a safety constraint, not a commercial target.

### UC03 Book a Group Pass

**Actor.** Visitor. *(V-21, V-34 – V-38)*
**Precondition.** Visitor belongs to a group.

**MSS**

1. Visitor chooses a Group Pass and selects one of their groups.
2. System shows the group's enlisted pandals, its member count and the pass's member limit.
3. Visitor selects a date and a slot for the whole set.
4. System holds capacity for the party and shows the amount due.
5. Visitor pays.
6. System issues a Group Pass against the group and returns it with its QR code.

Use case ends.

**Extensions**

- 1a. Visitor belongs to no group. System offers to create one or to join one by code, then returns to step 1.
- 2a. Group size exceeds the pass's member limit. System reports the limit and the overage, and returns to step 1.
- 3a. One of the group's pandals has no availability for the chosen date and slot. System names the pandal and returns to step 3.
- 4a. Capacity at one pandal is exhausted between display and hold. System holds nothing anywhere and returns to step 3. A Group Pass covering a set is all-or-nothing; a partly held set is not a product.
- 5a – 6c. As UC02.

### UC04 Buy a City Pass

**Actor.** Visitor. *(V-22)*

**MSS**

1. Visitor chooses a City Pass, the pandals to cover, and the date range.
2. System shows the price for that selection.
3. Visitor pays.
4. System issues a City Pass covering the chosen pandals and returns it with its QR code.

Use case ends.

**Extensions**

- 1a. A selected pandal does not participate in City Passes. System excludes it, reprices, and shows what changed.
- 3a – 4a. As UC02 steps 5 – 6.

**Blocked.** Open question 2 decides this use case's shape and it cannot be
committed until it is answered. If a City Pass consumes capacity at each pandal,
steps 1 – 3 need a hold at every one of them and an all-or-nothing failure mode as
in UC03. If it admits outside the cap, there is no hold and no such failure — but
then a City Pass can push a pandal past a capacity that exists for crowd safety.

### UC05 Cancel a Pass and Take the Refund

**Actor.** Visitor. *(V-29, V-30, N-40, SYS-04)*
**Precondition.** The pass is issued and not consumed.
**Guarantee.** Capacity returns to the pool it came from if and only if the cancellation is accepted. A consumed pass is never refunded.

**MSS**

1. Visitor selects an issued pass and requests cancellation.
2. System applies the cancellation rule and shows the refund due.
3. Visitor confirms.
4. System voids the pass, returns capacity to the pool it was issued from, and initiates the refund.

Use case ends.

**Extensions**

- 1a. The pass is already consumed. System refuses. Use case ends.
- 2a. The cancellation window has closed. System reports the pass non-refundable and offers to void it without refund.
- 4a. Refund initiation fails. System still voids the pass and returns capacity, then retries the refund until it succeeds or is escalated. Inventory and money fail independently; holding the seat hostage to a gateway helps nobody.
- 4b. The pass was complimentary or came from a sponsor pool. System returns capacity to the issuing pool and initiates no refund — the visitor paid nothing.

### UC06 Show a Pass at the Gate

**Actor.** Visitor. *(V-26 – V-28)*

**MSS**

1. Visitor opens their passes.
2. System lists each with its pandal, slot and state.
3. Visitor opens one.
4. System renders its QR code from local storage.

Use case ends.

**Extensions**

- 2a. The pass is consumed, cancelled or expired. System shows the state and does not present the QR as admissible.
- 4a. The device has no network. The QR renders regardless; it is held locally, not fetched.
- 4b. The pass has never been synced to this device. System requires one online sync before offline display is possible, and says so rather than showing an empty screen at the gate.

### UC07 Validate a Pass at a Gate

**Actor.** Gate staff. *(G-01 – G-04, N-14, N-37)*
**Precondition.** The device is logged in and bound to a gate.
**Guarantee.** A pass is consumed at most once. Every scan is logged, admitted or refused.

**MSS**

1. Gate staff scans the visitor's QR code.
2. System verifies the signature, the pandal, the slot window and the consumption state.
3. System marks the pass consumed and displays an admitted decision.
4. System records the scan in the entry log.

Use case ends.

**Extensions**

- 2a. The pass is already consumed. System refuses, showing the time and gate of the prior admission, and logs the attempt.
- 2b. The signature fails verification. System refuses as invalid and logs the attempt.
- 2c. The pass is for another pandal, or outside its slot window. System refuses with the reason and logs the attempt.
- 2d. The pass has been voided or cancelled. System refuses and logs the attempt.
- 2e. The pass came from an allocation the sponsor has not yet accepted. System refuses; passes in a pending pool are not usable.
- 3a. The pass is a Group Pass. Continue at UC08.
- 3b. Gate staff overrides the refusal under authorisation. Continue at UC10.

### UC08 Admit a Party against a Group Pass

**Actor.** Gate staff. *(G-05)*

**MSS**

1. Gate staff scans a Group Pass.
2. System shows the party size and how many of it remain unadmitted.
3. Gate staff enters the number entering now.
4. System decrements the remainder, displays admitted, and logs the scan with the count.

Use case ends.

**Extensions**

- 2a. No members remain unadmitted. System refuses, showing when the last admission happened.
- 3a. The number entered exceeds the remainder. System admits nobody and shows the remaining figure.

**Blocked in part.** Open question 3 decides whether step 3 exists. If a Group Pass
admits its full party once and never partially, the use case collapses to UC07 with
a headcount, and the remainder tracking above is dead code.

### UC09 Validate Offline and Reconcile

**Actor.** Gate staff. *(G-06, G-07, SYS-05, SYS-06, N-08, N-09)*
**Precondition.** The device holds a synced local copy of pass state for its pandal.
**Guarantee.** Every offline decision is recorded and reaches the server. Conflicts are surfaced, never silently resolved.

**MSS**

1. The device loses its network connection.
2. Gate staff scans. System verifies the signature locally and checks local consumption state.
3. System decides, records the scan locally, and marks it for reconciliation.
4. The connection returns. System uploads queued scans and downloads consumption recorded elsewhere.
5. System reports the reconciliation outcome to the pandal admin.

Use case ends.

**Extensions**

- 2a. The device has never synced, so it holds no consumption state. It can still verify authenticity by signature but cannot detect prior use. Whether it admits and flags, or refuses outright, is an ADR-001 decision and is not settled.
- 4a. The same pass was admitted at another gate while both devices were offline. System surfaces the conflict to the pandal admin. It does not retract an admission that has already physically happened — the person is inside.
- 4b. Reconciliation does not complete within two minutes of reconnection. System escalates rather than retrying silently.
- 4c. A volunteer was deactivated while the device was offline. Revocation lands at the next sync, so scans made in between stand and are attributable. This window is a consequence of offline operation, not a defect.

**Blocked.** Open question 8 and ADR-001. The client spec says validation is
server-side and separately that offline queueing "may be considered". The gate app
cannot be built against both readings.

### UC10 Admit by Manual Exception

**Actor.** Gate staff. *(G-08, N-15)*

**MSS**

1. Gate staff, holding a refused decision, chooses to override it.
2. System requires a reason and confirms the staff identity.
3. Gate staff supplies the reason.
4. System admits the visitor and records the override with its reason, the staff identity, the gate and the time.

Use case ends.

**Extensions**

- 2a. This staff member is not authorised to override. System refuses and logs the attempt — an unauthorised override attempt is itself worth knowing about.
- 4a. The override was against an already-consumed pass. System records it as a duplicate admission and surfaces it to the pandal admin.

### UC11 Configure Slots and Capacity

**Actor.** Pandal admin. *(PA-03, N-38)*
**Precondition.** Admin is authenticated against their own pandal.

**MSS**

1. Admin opens the pandal's slot configuration.
2. Admin defines a slot with a time window, capacity and price.
3. System validates it against existing slots and saves it.

Use case ends.

**Extensions**

- 2a. The new slot overlaps an existing one. System reports the conflict and returns to step 2.
- 3a. Capacity is reduced below the number of passes already issued for the slot. System rejects the change and reports the issued count.
- 3b. Capacity is reduced below issued plus live holds. System rejects and reports both figures. Holds are commitments to visitors mid-payment, not slack.

### UC12 Configure Pass Rows

**Actor.** Pandal admin. *(PA-04, PA-05, PA-06)*

**MSS**

1. Admin opens pass configuration and adds a row: type, group, date range, time range, price and cap.
2. System validates the row against existing rows, saves it, and records the change together with the issued and remaining counts at that moment.

Use case ends.

**Extensions**

- 1a. The type is Group but no group is named. System rejects the row.
- 2a. The row overlaps another row of the same type and window. System reports the conflict and returns to step 1.
- 2b. The cap is set below what the row has already issued. System rejects and reports the issued figure.
- 2c. Admin deactivates a row instead. System stops it being bookable and leaves passes already issued against it valid.

**Blocked in part.** Open question 7 decides what a row's cap validates against —
the slot's capacity or the pandal's. The current model roots pools at the slot; the
mockups suggest the pandal.

### UC13 Issue Complimentary Passes

**Actor.** Pandal admin. *(PA-14)*

**MSS**

1. Admin selects a slot and a quantity.
2. System checks remaining capacity and issues passes without payment.
3. System returns the passes for distribution.

Use case ends.

**Extensions**

- 2a. Remaining capacity is insufficient. System reports the shortfall and returns to step 1. A complimentary pass consumes real capacity; it is free of charge, not free of cost.
- 3a. A complimentary pass is later cancelled. Capacity returns to the pandal's own pool and no refund is initiated.

### UC14 Open and Close Bookings

**Actor.** Pandal admin. *(PA-07)*

**MSS**

1. Admin selects the pandal or one slot and closes bookings.
2. System stops new holds immediately and reports how many holds are still live.

Use case ends.

**Extensions**

- 2a. Holds are live at the moment of closing. System lets them run to payment or expiry. Closing stops intake; it does not cancel work already in flight.
- 2b. Admin reopens. System resumes intake against whatever capacity remains.

### UC15 Publish Live Crowd Status

**Actors.** Pandal admin, Visitor. *(PA-10, V-11)*

**MSS**

1. Admin sets an estimated wait and a crowd level.
2. System publishes both, stamped with the time they were set.
3. Visitors see both, with that timestamp, on the pandal's page.

Use case ends.

**Extensions**

- 3a. The figure has not been updated for some time. System shows its age rather than hiding it. A visibly old figure is honest; a silently old one sends people to the wrong queue.

### UC16 Create and Share a Donation Link

**Actor.** Pandal admin. *(PA-19, PA-20, PA-21)*

**MSS**

1. Admin creates a link, optionally with a suggested amount and a purpose.
2. System generates a shareable URL and lists it alongside the pandal's other links.
3. Admin copies and shares it.

Use case ends.

**Extensions**

- 3a. Admin revokes a link. System stops it accepting donations and leaves donations already taken untouched.

### UC17 Donate through a Shared Link

**Actor.** Donor — a visitor, not necessarily signed in. *(V-39 – V-46, SYS-10)*
**Guarantee.** Money is either receipted against a pandal or returned. A donation is never held without a receipt.

**MSS**

1. Donor opens the link.
2. System shows the pandal, the purpose, and the suggested amount where one was set.
3. Donor sets an amount and pays.
4. System records the donation and issues a receipt.

Use case ends.

**Extensions**

- 1a. The link has been revoked or has expired. System says the appeal is closed and offers the pandal's own donate screen if it still takes donations.
- 2a. No amount was fixed. Donor enters any amount.
- 3a. Donor is not signed in. System takes a contact for the receipt and creates no account.
- 4a. Payment is captured but the receipt is not issued. System resolves it to a receipt or a refund. A donation buys no inventory, so the only reversal available is money — see §4.

**Blocked in part.** Open questions 4 and 5. Q4 — where the money settles — decides
whether the platform is the merchant of record on this path, and therefore whether it
is a payment aggregator under RBI rules. Q5 — whether tax-deductible receipts are
offered — decides what identity step 3 has to collect from a donor who meant to give
in ten seconds. Both are regulatory answers, not design ones.

### UC18 Allocate a Sponsorship Package

**Actor.** Pandal admin. *(PA-24 – PA-29, N-12, N-37, SYS-08)*
**Guarantee.** Allocated passes exist only against capacity the pandal actually holds.

**MSS**

1. Admin defines or selects a package.
2. Admin adds a sponsor and allocates the package to them.
3. System creates a child pool under the pandal's capacity, transfers the package's pass count into it, and marks the allocation pending.
4. System notifies the sponsor.

Use case ends.

**Extensions**

- 3a. Remaining capacity is insufficient for the package. System refuses and reports the shortfall.
- 4a. The sponsor takes no action. System escalates rather than leaving capacity committed indefinitely.
- 4b. Admin withdraws the pending allocation. System returns the transferred capacity to the pandal's pool.

Passes in a pending pool are unusable at a gate — UC07 extension 2e.

**Blocked in part.** Open question 7 — whether allocations sit against pandal-wide
capacity or against a specific slot.

### UC19 Accept or Decline an Allocation

**Actor.** Sponsor admin. *(SP-02, SP-03, SP-04, N-37)*

**MSS**

1. Sponsor opens the pending allocation and sees its entitlements.
2. Sponsor accepts.
3. System marks the allocation accepted, and the pool's passes become usable.

Use case ends.

**Extensions**

- 2a. Sponsor declines. System returns the capacity to the pandal and records the decline.
- 2b. The package's validity lapses before any action. System lets the allocation expire and returns the capacity.

### UC20 Distribute Passes to Named Guests

**Actor.** Sponsor admin. *(SP-05, N-12)*

**MSS**

1. Sponsor enters the guests to receive passes.
2. System issues one pass per guest from the sponsor's pool, decrementing it.
3. System delivers each pass to its guest.

Use case ends.

**Extensions**

- 1a. There are more guests than the pool has remaining. System issues none and reports the remainder. A partial issue against a named list leaves the sponsor unable to tell who was served.
- 3a. Delivery to a guest fails. The pass stays issued and retrievable, and the sponsor can resend. A delivery failure is not an issuance failure.

### UC21 Create a Sub-Sponsor and Sell Passes

**Actor.** Sponsor admin. *(SP-06 – SP-09, N-12)*

**MSS**

1. Sponsor creates the sub-sponsor.
2. Sponsor sets a per-pass price for them.
3. Sponsor sells a quantity.
4. System creates or locates the sub-sponsor's child pool, transfers the quantity into it, and records the price and the amount owed.

Use case ends.

**Extensions**

- 3a. The quantity exceeds the sponsor's remaining pool. System refuses and reports the remainder.
- 4a. The sub-sponsor already holds a pool under this sponsor. System transfers into the existing pool rather than creating a second.

**Blocked in part.** Whether the money for this sale moves through the platform or
settles between the two organisations off it decides whether step 4 records a payable
or takes a payment. The sweep does not ask this; `CLAUDE.md` §8 question 5 does — see
§6. Open question 6 decides whether a sub-sponsor may in turn create its own; the
model allows arbitrary depth and `MAX_POOL_DEPTH` bounds it, so the answer is a
settings value, not a rewrite.

### UC22 Buy Passes from the Parent Sponsor

**Actor.** Sub-sponsor admin. *(SS-03, SS-04, SS-05, N-36)*
**Guarantee.** Capacity reaching a sub-sponsor came through its parent sponsor and no other route.

**MSS**

1. Sub-sponsor sees what the parent sponsor has available and at what price.
2. Sub-sponsor requests a quantity.
3. System transfers that quantity from the parent's pool to the sub-sponsor's, and records the amount owed.

Use case ends.

**Extensions**

- 1a. No pandal is offered as a source. There is no such path to attempt; the constraint is structural, not a validation message.
- 2a. The quantity exceeds the parent's remaining pool. System refuses and reports the remainder.

### UC23 Issue Passes to Recipients

**Actor.** Sub-sponsor admin. *(SS-06, SS-07, SS-08)*

**MSS**

1. Sub-sponsor supplies a recipient list, or a single name.
2. System issues one pass per recipient from its pool, decrementing it, and records the issuance.

Use case ends.

**Extensions**

- 1a. The list is longer than the pool remaining. System issues none and reports the shortfall.
- 2a. A recipient's contact details are invalid. System issues the pass and flags it undelivered rather than failing the whole batch.

### UC24 Upload and Approve Branding Creatives

**Actors.** Sponsor admin (primary), Superadmin. *(SP-10, SP-11, SA-09)*

**MSS**

1. Sponsor uploads a creative.
2. System stores it pending approval.
3. Superadmin reviews and approves it.
4. System marks it approved, and the sponsor sees the new state.

Use case ends.

**Extensions**

- 2a. The file fails a format or size check. System rejects it at upload, before it reaches a reviewer.
- 3a. Superadmin rejects it with a reason. Sponsor sees the reason and can re-upload.

### UC25 Onboard a Committee

**Actor.** Superadmin. *(SA-02)*

**MSS**

1. Superadmin enters the committee and pandal details.
2. System creates the pandal record.
3. System creates the first Pandal Admin account and issues its credentials.
4. Pandal admin signs in and sets their own password.

Use case ends.

**Extensions**

- 2a. The pandal already exists. System reports it and offers to attach a further admin instead.
- 3a. The email already holds an admin account. System attaches the existing account to the new pandal rather than creating a second identity for one person.

### UC26 Book a Value-Added Service

**Actors.** Visitor, Pandal admin. *(V-47 – V-49, PA-30 – PA-32)*

**MSS**

1. Visitor opens a pandal's services.
2. System shows each with its price and available days.
3. Visitor picks a day, completes the service's form and pays.
4. System records the booking and confirms it.
5. Pandal admin sees the booking and marks it fulfilled on the day.

Use case ends.

**Extensions**

- 2a. The service is not available on the requested day. System refuses and shows the days it is.
- 4a. Payment behaves as UC02 steps 5 – 6.
- 4b. Visitor cancels the booking. Refund follows the service's own rule — which the sweep does not state. See §6.

### UC27 Report a Lost Item

**Actors.** Visitor, Pandal admin. *(V-50, V-51, PA-15)*

**MSS**

1. Visitor reports an item with where it was lost and how to reach them.
2. System records it against the pandal.
3. Pandal admin sees the report.
4. Admin marks the item found, and the reporter sees the change of state.

Use case ends.

**Extensions**

- 2a. The report carries personal contact details visible to the pandal admin. Retention applies, and the retention period is a gap.
- 3a. Another visitor views the pandal's lost-and-found list. The list shows the item, never the reporter's contact details.

### UC28 Submit and Resolve a Support Request

**Actors.** Visitor, Pandal admin. *(V-52, V-53, PA-16)*

**MSS**

1. Visitor submits a subject and a message.
2. System records the request and returns its state.
3. Pandal admin sees it, acts, and marks it resolved.
4. Visitor sees the resolved state.

Use case ends.

**Extensions**

- 1a. The request concerns the platform rather than a pandal — a payment, a refund, the app itself. Where it routes is not specified. See §6.

### UC29 Issue a Manual Refund

**Actor.** Superadmin. *(SA-13, SYS-03, SYS-04, N-13, N-15)*

**MSS**

1. Superadmin finds a payment captured with neither an artifact nor a refund against it.
2. Superadmin requests a refund.
3. System refunds through the gateway and records the action against the superadmin who took it.

Use case ends.

**Extensions**

- 1a. A pass was in fact issued against the payment. System refuses the manual refund and directs the superadmin to cancellation, so that capacity is returned rather than stranded.
- 3a. The gateway rejects the refund. System retries and escalates.

### UC30 Manage Volunteers

**Actor.** Pandal admin. *(PA-11, PA-12, G-01, G-10, N-20)*

**MSS**

1. Admin adds a volunteer with a name, mobile, assigned gate and status.
2. System creates gate credentials for them.
3. Volunteer signs in on a device and is bound to the assigned gate.

Use case ends.

**Extensions**

- 1a. The mobile number is already a volunteer at another pandal. System allows it; volunteers are scoped per pandal.
- 2a. Admin deactivates the volunteer, or the volunteer reports the device lost. Credentials stop working at the next scan, and on an offline device at the next sync. That window is real and bounded by NFR-2's two minutes — see UC09 extension 4c.

### Held at summary level

Real use cases, but with no branching worth writing out. They are listed so that
coverage is visible, not because the flow is interesting.

| Use case | Actor | Requirements |
|---|---|---|
| UC31 Log In | Visitor | V-02 |
| UC32 Log Out | Visitor | V-03 |
| UC33 Edit Profile | Visitor | V-04 |
| UC34 Delete Account | Visitor | V-05 |
| UC35 Change Language | Visitor | V-06 |
| UC36 Browse, Filter and Search Pandals | Visitor | V-07, V-08, V-09, V-10 |
| UC37 Get Directions to a Pandal | Visitor | V-12 |
| UC38 Favourite a Pandal | Visitor | V-13 |
| UC39 View a Pandal's Sponsors | Visitor | V-14 |
| UC40 Add a Pass to a Device Wallet | Visitor | V-32 |
| UC41 Create, Invite to and Join a Group | Visitor | V-34, V-35, V-36, V-38 |
| UC42 View Donation History | Visitor | V-46 |
| UC43 View Admissions at This Gate | Gate staff | G-09 |
| UC44 Create and Edit a Pandal Profile | Pandal admin | PA-01 |
| UC45 Define Gates | Pandal admin | PA-02 |
| UC46 Set Cancellation and Refund Rules | Pandal admin | PA-08 |
| UC47 View Live Occupancy | Pandal admin | PA-09 |
| UC48 View Entry and Scan Logs | Pandal admin | PA-13 |
| UC49 View Pass Revenue and Donations | Pandal admin | PA-17, PA-18 |
| UC50 View Settlement Status | Pandal admin | PA-22 |
| UC51 Export Sales, Donations and Logs | Pandal admin | PA-23 |
| UC52 Log In to a Portal | Sponsor, Sub-sponsor, Superadmin | SP-01, SS-01, SA-01 |
| UC53 View a Pool | Sponsor, Sub-sponsor | SP-04, SS-02 |
| UC54 View Sub-Sponsor Activity | Sponsor | SP-09 |
| UC55 View Branding Impressions | Sponsor | SP-12 |
| UC56 View Issuance History | Sub-sponsor | SS-08 |
| UC57 Manage Master Data | Superadmin | SA-03 |
| UC58 View the Platform Dashboard | Superadmin | SA-04 |
| UC59 View Passes and Payments Platform-Wide | Superadmin | SA-05 |
| UC60 View Entry Logs Platform-Wide | Superadmin | SA-06 |
| UC61 Manage Users and Eligibility | Superadmin | SA-07 |
| UC62 Manage Groups Platform-Wide | Superadmin | SA-08 |
| UC63 Access Any Pandal's Views | Superadmin | SA-10 |
| UC64 Suspend an Account | Superadmin | SA-11 |
| UC65 View the Audit Trail | Superadmin | SA-12 |

### Deliberately not written as a use case

- **V-31 Transfer or share a pass.** A pass is a signed artifact bound to a holder;
  forwarding the artifact is exactly the reuse NFR N-14 exists to prevent. If
  transfer is wanted, it is a void-and-reissue against the same capacity, not a
  forward — and that is a different use case with a different risk profile. It is
  not written until the product decides which one it means.
- **V-24 Retry a failed payment** and **V-25 booking confirmation by SMS.** Both are
  extensions of UC02 rather than use cases a visitor sets out to perform.
- **V-33 Slot reminders** and **V-11 live crowd level.** The visitor receives these;
  they do not initiate them. Reminders are SYS-07; the crowd figure is UC15.

---

## 4. System-initiated behaviour — not use cases

No external actor initiates these, so they are supplementary requirements rather
than use cases. Between them they hold most of the engineering risk in the product,
which is exactly why they are easy to leave out of a use case model and then out of
a build.

| Req | Behaviour | Where it surfaces |
|---|---|---|
| SYS-01 | Expire unpaid holds and release the capacity they held | UC02 ext 5a, UC14 ext 2a |
| SYS-02 | Close a slot automatically at its cut-off time | UC14 |
| SYS-03 | Resolve a payment captured but not issued, to issuance or refund | UC02 ext 6a, UC17 ext 4a, UC29 |
| SYS-04 | Retry failed refunds until success or escalation | UC05 ext 4a, UC29 ext 3a |
| SYS-05 | Reconcile offline gate scans on reconnection | UC09 step 4 |
| SYS-06 | Detect and surface the same pass admitted at two gates | UC09 ext 4a, UC10 ext 4a |
| SYS-07 | Send booking reminders before a slot begins | V-33 |
| SYS-08 | Notify a sponsor of a pending allocation and escalate if unacted | UC18 ext 4a |
| SYS-09 | Recompute live occupancy figures | UC15, UC47 |
| SYS-10 | Issue receipts for donations and pass purchases | UC17 step 4 |

Also not use cases, and worth stating for the same reason: the pool invariant
holding under concurrent booking (N-12), and peak-load behaviour after months of
near-flat traffic (N-05, N-06).

---

## 5. Coverage

Every requirement in `docs/FR.md` §2 – §7 appears in §2 of this document as a story,
identified by its own ID. Every one of them also reaches §3 — through a full use
case, through the summary-level table, or through an explicit note on why it is not
a use case. `SYS-01` to `SYS-10` are covered by §4.

Four use cases cannot be committed as written, because an open question decides
their main flow rather than an extension of it:

| Use case | Blocked by |
|---|---|
| UC04 Buy a City Pass | Q2 — does a City Pass consume capacity at each pandal? |
| UC08 Admit a Party against a Group Pass | Q3 — is partial admission allowed? |
| UC09 Validate Offline and Reconcile | Q8 and ADR-001 — is offline validation in scope? |
| UC17 Donate through a Shared Link | Q4 — where does donation money settle? Q5 — are tax-deductible receipts offered? |

Two more are shaped, but not blocked, by open questions: UC12 (Q7, whether a cap
sits against a slot or a pandal) and UC21 (Q6, hierarchy depth — a `MAX_POOL_DEPTH`
setting, not a redesign).

---

## 6. What writing these surfaced

New gaps, found by trying to write an extension and discovering there was nothing to
write it from. These are additions to the nine open questions in `docs/FR.md` §11,
not restatements of them.

1. **A Group Pass covering several pandals, one of which is full.** Q3 asks about
   partial *admission*. This is partial *booking*: the group's enlisted list is
   fixed, so if one pandal has no room the booking either fails whole or silently
   covers less than the group expects. UC03 assumes all-or-nothing. That assumption
   should be confirmed rather than inherited from this document.
2. **Does a value-added service have a capacity?** PA-30 gives a service a price and
   available days, and nothing else. If Puja By Your Name can be booked by four
   hundred people for Ashtami, somebody has to perform it four hundred times.
3. **What is a service's cancellation rule?** V-49 allows cancellation. PA-08 sets
   cancellation rules for *passes*. Whether services follow the same rule, their own,
   or none is unstated.
4. **Where does a support request route?** V-52 and PA-16 assume a pandal. A request
   about a payment, a refund or the app itself has no pandal to route to, and the
   superadmin has no support queue in the sweep.
5. **Are complimentary and sponsor-issued passes cancellable, and by whom?** UC05
   ext 4b assumes capacity returns to the issuing pool with no refund. Neither
   PA-14 nor SP-05 says so.
6. **Does the public lost-and-found list expose the reporter?** V-51 shows a pandal's
   items to any visitor; V-50 attaches a contact to each. UC27 ext 3a assumes the
   contact is withheld. Confirm it, because the alternative publishes phone numbers.
7. **Pass transfer conflicts with reuse resistance.** V-31 (*Novel*) as written is
   forwarding a signed artifact, which is the attack N-14 forbids. It needs to be a
   void-and-reissue or it needs to be dropped.
8. **Revocation has an offline window.** N-20 says revocation reaches a device on
   reconnection; N-08 says a device operates offline for up to four hours. A
   deactivated volunteer therefore keeps scanning for up to that long. This is a
   consequence of the two requirements together, and it should be an accepted,
   stated window rather than a surprise after the festival.
9. **The sweep does not ask where sponsor-to-sub-sponsor money goes.** `docs/FR.md`
   §11 Q4 covers donation settlement and nothing else. SP-08 and SS-04 move passes
   down the chain against a price the sponsor sets, and whether that payment runs
   through the platform is unasked here — it appears only as `CLAUDE.md` §8 question
   5. It bears on the same aggregator question as Q4 and belongs beside it.

---

## 7. Requirements not yet in the sweep

`CLAUDE.md` carries FR-61 to FR-76, drawn from the client's clickable prototype and
recorded in `docs/mockup-findings.md`. They are committed requirements, and
`docs/FR.md` has not yet been updated to include them. Their stories are below so
that this document is not silently narrower than the committed set. The sweep should
absorb them; until it does, `CLAUDE.md` is the authority.

| Req | Priority | Story |
|---|---|---|
| FR-61 | Typical | As a visitor, I can choose English, Bengali or Hindi before I sign up and change it later, so that I am not reading a second language before I have an account. Widens V-06, which offers only two. |
| FR-62 | Typical | As a visitor, I can record my city, state, gender and profile types — senior citizen, family with young children, specially abled, press, influencer — so that I am offered the passes I am eligible for. |
| FR-63 | Essential | As a visitor, I can put several pandals on one Individual Pass, each with its own date and slot, so that a night of pandal-hopping is one purchase. Refines V-20. |
| FR-64 | Essential | As a visitor, I can book a Group Pass against a group's enlisted pandals for a single date and slot, so that the whole party moves together. Refines V-21. |
| FR-65 | Essential | As a visitor, I can hold a City Pass with no date and no slot, so that I visit its pandals in any order. Refines V-22. |
| FR-66 | Essential | As a visitor, I can see the pass price, the people covered, the platform fee and the total before I pay, so that the total is not the first honest number I see. |
| FR-67 | Typical | As a visitor, I can apply a coupon code at checkout, so that a promotion reaches the price I actually pay. |
| FR-68 | Essential | As a visitor, I can pay by UPI, card or wallet, so that I use what I already have set up. Refines V-18. |
| FR-69 | Essential | As a visitor, I can see every pandal my pass covers and which of them I have visited, so that I know what is left on it. |
| FR-70 | Essential | As a visitor, I can mint a short-lived entry code for one pandal on my pass, so that a screenshot of my pass admits nobody. |
| FR-71 | Typical | As a visitor, I watch a rewarded video before a code is minted, so that the free tier is paid for by something. |
| FR-72 | Typical | As a visitor, I can see when I was admitted at each pandal and how many of my covered pandals I have visited, so that I can pace the night. |
| FR-73 | Novel | As a visitor, I can see a pandal's wait time and crowd level with the time each was last updated, so that I can judge whether to trust the figure. Refines V-11. |
| FR-74 | Novel | As a visitor, I can see a pandal's lost item reports, so that I check before travelling back. Same as V-51. |
| FR-75 | Typical | As a donor, I can leave my name blank and receive a receipt carrying no name, so that I can give anonymously. |
| FR-76 | Typical | As a visitor, I can complete a service's own form — for Puja By Your Name, the name, gotra and sankalp, so that the Puja is performed correctly. Refines V-48. |

### UC66 Mint an Entry Code

**Actor.** Visitor. *(FR-70, FR-71, FR-69, FR-72, NFR-6)*
**Precondition.** The visitor holds a pass covering the pandal, and that leg is not yet admitted.
**Guarantee.** At most one live code exists for a leg. A code admits once, at one pandal, within its lifetime.

**MSS**

1. Visitor opens a held pass and selects a pandal it covers.
2. Visitor requests an entry code.
3. System plays a rewarded video.
4. System mints a code for that leg, invalidating every earlier live code for it, and shows it with its remaining lifetime.
5. Gate staff scans the code. System verifies its signature and consumes it.
6. System marks that leg visited and records the admission time.

Use case ends.

**Extensions**

- 1a. The leg is already visited. System shows the admission time and offers no code.
- 3a. Visitor dismisses the video. No code is minted.
- 4a. Visitor mints again while an earlier code is still live. The earlier code stops working immediately. Minting is unlimited; admission is not, and two live codes for one leg must never coexist.
- 4b. The code expires unused. Visitor mints a replacement from step 2.
- 5a. The gate is offline. It verifies the signature locally and admits, then reconciles consumption on reconnection as UC09.
- 5b. The code was minted for another pandal. System refuses and logs the attempt.

This use case does not replace UC07. UC07 validates the pass; this validates a code
minted against one leg of it. Authenticity is verifiable offline in both; consumption
is server-authoritative in both.
