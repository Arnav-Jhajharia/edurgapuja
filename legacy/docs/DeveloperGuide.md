# PujaPass — Core Functional Requirements, User Stories and Use Cases

Scope narrowed to the path from booking to gate. A requirement is in this document only if its failure would break the product during the festival.

Actors: Visitor, Gate Staff, Committee Admin, Superadmin.

---

## 1. Functional requirements

**Visitor**

- **FR-01** Register an account with a mobile number, verified by OTP.
- **FR-02** Log in to an existing account, verified by OTP.
- **FR-03** Browse pandals, filtered by city or locality.
- **FR-04** View the slots offered by a pandal, each showing current availability.
- **FR-05** Select a slot and initiate a booking, which holds capacity for a bounded period.
- **FR-06** Pay for a held booking through the payment gateway.
- **FR-07** Receive a pass with a QR code on successful payment.
- **FR-08** View all passes held, with the QR available without a network connection.
- **FR-09** Cancel a booking within the configured cancellation window and receive the refund due under the refund rule.

**Gate Staff**

- **FR-10** Scan a pass QR code at a gate and receive an admitted or refused decision.
- **FR-11** Be prevented from admitting a pass that has already been consumed.
- **FR-12** Record an entry log for every scan, whether admitted or refused.
- **FR-13** Admit a visitor by manual exception where authorised, with the reason recorded.

**Committee Admin**

- **FR-14** Create and configure a pandal profile.
- **FR-15** Define slots for the pandal, each with a time window, capacity and price.
- **FR-16** Open and close bookings for a pandal or an individual slot.
- **FR-17** Issue complimentary passes against capacity without payment.
- **FR-18** View live occupancy against capacity, per slot.

**Superadmin**

- **FR-19** Onboard a committee, creating the pandal record and its first Committee Admin account.
- **FR-20** Manage master data the above depend on: pass types, slot types, and cancellation and refund rules.

---

## 2. User stories

Prioritised as Essential, Typical or Novel. Essential stories must be in the first release.

**Booking**

- As a visitor, I can register with my mobile number, so that I can book passes without creating a password. *Essential*
- As a visitor, I can see which slots still have space, so that I do not waste time on a full one. *Essential*
- As a visitor, I can hold a slot while I pay, so that it is not taken from under me mid-payment. *Essential*
- As a visitor, I can pay and immediately receive a pass, so that I know the booking is confirmed. *Essential*
- As a visitor, I can open my pass QR without signal, so that a dead network at the gate does not keep me out. *Essential*
- As a visitor, I can cancel and see what refund I am owed, so that I am not guessing at the rule. *Typical*

**Entry**

- As gate staff, I can scan a pass and get an immediate decision, so that the queue keeps moving. *Essential*
- As gate staff, I am stopped from admitting a pass twice, so that one pass cannot be shared around a group. *Essential*
- As gate staff, I can admit someone by exception and record why, so that a genuine edge case does not become an argument at the gate. *Typical*
- As a committee admin, I can see every scan afterwards, so that a disputed entry can be checked. *Typical*

**Configuration**

- As a committee admin, I can set capacity and price per slot, so that crowd size matches what the pandal can hold. *Essential*
- As a committee admin, I can close bookings immediately, so that I can stop intake when the pandal is over capacity. *Essential*
- As a committee admin, I can issue complimentary passes, so that guests and local dignitaries are handled without a payment workaround. *Typical*
- As a committee admin, I can see live occupancy, so that I know whether to close a slot early. *Typical*
- As a superadmin, I can onboard a committee and hand over an admin account, so that a new pandal can run itself. *Essential*

---

## 3. Use cases

Preconditions and guarantees are stated only where they matter.

### UC01 Book a Pass

**Actor.** Visitor.
**Precondition.** Visitor is logged in. Bookings are open for the chosen slot.
**Guarantee.** Either a pass is issued and capacity is decremented, or no capacity is consumed and no payment is retained.

**MSS**

1. Visitor selects a pandal.
2. System shows its slots with current availability.
3. Visitor selects a slot and a pass quantity.
4. System places a hold on the requested capacity and shows the amount due.
5. Visitor pays.
6. System confirms payment, converts the hold into an issued pass, and returns the pass with its QR code.

Use case ends.

**Extensions**

- 3a. Requested quantity exceeds remaining capacity. System shows the remaining figure and returns to step 3.
- 4a. Capacity is exhausted between display and request. System reports the slot as full and returns to step 2.
- 5a. Visitor abandons payment, or the hold expires before payment completes. System releases the hold. Use case ends without a pass.
- 6a. Payment succeeds but pass issuance fails. System retains the payment in a pending state and resolves it to either an issued pass or a refund without operator intervention.
- 6b. Payment gateway result is unknown. System treats the booking as pending and reconciles against the gateway before either issuing or refunding.

### UC02 Validate a Pass at the Gate

**Actor.** Gate Staff.
**Precondition.** Gate device is registered to a gate.
**Guarantee.** A pass is consumed at most once. Every scan is logged.

**MSS**

1. Gate staff scans the visitor's QR code.
2. System verifies the pass signature, its pandal, its slot window and its consumption state.
3. System marks the pass consumed and displays an admitted decision.
4. System records the scan in the entry log.

Use case ends.

**Extensions**

- 2a. Pass is already consumed. System displays refused with the reason and the time of prior admission, and logs the attempt.
- 2b. Pass signature fails verification. System displays refused as invalid and logs the attempt.
- 2c. Pass is for a different pandal or outside its slot window. System displays refused with the reason and logs the attempt.
- 2d. Gate device has no network connection. System decides from local state, marks the scan for reconciliation, and continues.
- 3a. The same pass was admitted at another gate while both were offline. System flags the conflict at reconciliation for the committee admin to review.
- 4a. Gate staff overrides a refusal under authorisation. System admits the visitor and records the override with its reason and the staff identity.

### UC03 Configure Slots and Capacity

**Actor.** Committee Admin.
**Precondition.** Committee admin is authenticated against their pandal.

**MSS**

1. Committee admin opens the pandal's slot configuration.
2. Committee admin defines a slot with a time window, capacity and price.
3. System validates the slot against existing slots and saves it.

Use case ends.

**Extensions**

- 2a. The new slot overlaps an existing one. System reports the conflict and returns to step 2.
- 3a. Capacity is reduced below the number of passes already issued for that slot. System rejects the change and reports the issued count.

### UC04 Cancel a Booking

**Actor.** Visitor.
**Precondition.** The pass is issued and not yet consumed.
**Guarantee.** Capacity is returned to the slot if and only if the cancellation is accepted.

**MSS**

1. Visitor selects an issued pass and requests cancellation.
2. System applies the cancellation rule and shows the refund due.
3. Visitor confirms.
4. System voids the pass, returns capacity to the slot, and initiates the refund.

Use case ends.

**Extensions**

- 2a. The cancellation window has closed. System reports that the pass is non-refundable and offers to void without refund.
- 4a. Refund initiation fails. System voids the pass, returns capacity, and retries the refund until it succeeds or is escalated.

### UC05 Issue Complimentary Passes

**Actor.** Committee Admin.

**MSS**

1. Committee admin selects a slot and a quantity.
2. System checks remaining capacity and issues passes without payment.
3. System returns the passes for distribution.

Use case ends.

**Extensions**

- 2a. Remaining capacity is insufficient. System reports the shortfall and returns to step 1.

### Held at summary level

- **UC06 Register** *(Visitor)* — mobile number, OTP verification, account creation.
- **UC07 Log In** *(Visitor)* — OTP against an existing account.
- **UC08 Browse Pandals and Slots** *(Visitor)*.
- **UC09 View Held Passes** *(Visitor)* — including offline QR display.
- **UC10 Open or Close Bookings** *(Committee Admin)*.
- **UC11 View Live Occupancy** *(Committee Admin)*.
- **UC12 Onboard a Committee** *(Superadmin)*.
- **UC13 Manage Master Data** *(Superadmin)*.

---

## 4. Not written as use cases

No external actor initiates these, so they belong in supplementary requirements rather than the use case model. They also contain most of the engineering risk.

- Expiry of unpaid holds and release of the capacity they held.
- Automatic closing of a slot at its cut-off time.
- Reconciliation of offline validations on reconnection, including the same pass admitted at two gates.
- The capacity invariant holding under concurrent booking.
- Peak load behaviour, given months of near-flat traffic followed by a few extreme days.