# PujaPass — Scalability

**Written:** 8 September 2026, after the pilot figures came back (2,000 passes, 200 in
the busiest hour).

Those figures describe **year one**. Durga Puja in Kolkata is a festival of millions;
a platform that works is a platform that grows. This document exists so that the
pilot's numbers size the *servers* without shaping the *system*.

---

## 1. The principle

> **Scale is bought with one-way doors, not with servers.**

Almost everything people call "scaling" — more containers, a read replica, a cache, a
connection pooler — is a configuration change made in an afternoon when a graph says
to. Deferring those is not under-engineering; buying them early is waste.

A small number of decisions are different. Get them wrong and no amount of hardware
recovers them, because fixing them means changing a contract someone else already
depends on, or migrating data that already exists.

**Those are the ones we design for the festival we want, not the one we have.**

This project has an unusually hard one-way door: **the API is consumed by Flutter apps
distributed through app stores.** A visitor who installs the app in October 2026 may
still be running that build in October 2027. We cannot make a breaking API change and
we cannot force an upgrade. The API contract is less reversible than the database.

---

## 2. What is already right

Credit where it is due — the existing design has most of the irreversible decisions
correct, and none of them should change:

| Decision | Why it scales |
|---|---|
| Capacity invariant in a **database check constraint**, not only in code | The guarantee survives every future rewrite, cache, and service split above it. |
| **Holds as rows, not a counter** (`models.py:134`) | A counter drifts under concurrency and needs a repair job. Rows do not. Availability excludes expired holds by timestamp, so a late sweeper cannot oversell — that property is worth more at scale, not less. |
| **`select_for_update` with deterministic lock ordering** (`operations.py:53`) | Deadlock-free at any depth and any contention. |
| **Pools with an optional parent** (ADR-003) | Depth is data, not schema. A third sponsorship tier is a row. |
| **UUID primary keys** | No sequence bottleneck, no cross-shard collision, safe to expose. |
| **Denormalised `root_slot`** (`models.py:85`) | The gate resolves a pass to its slot without walking the tree — an O(1) read on the hottest path. |
| **Idempotency by unique index** on `PaymentEvent.event_id` | Correct under concurrent duplicate webhooks, not merely under retries. |
| **Domain logic isolated in `operations.py`** | The seam that lets the implementation change without the callers changing. |
| **Money as integer paise** | No float drift, ever. |
| **Cursor-based gate sync** (`BuildPlan` §6) | Incremental by construction. |

Nothing in the pilot sizing touches any of these.

---

## 3. The one-way doors we must get right now

These cost days now and months later. All of them are in scope regardless of which
schedule option is chosen.

### 3.1 The API contract

Because old app builds persist, **v1 must already look like the API of a system 100×
larger.** Specifically:

- **Every list endpoint is paginated from the first release.** Cursor pagination, not
  offset — offset pagination degrades on large tables and gives inconsistent pages
  under concurrent writes. A client written against an unpaginated list breaks the day
  the list grows; that is a forced app update during a festival.
- **Every list endpoint is filterable server-side.** A client that fetches everything
  and filters locally is a client that stops working at scale.
- **A stable error envelope**, with a machine-readable `code` alongside the human
  message. Clients branch on codes; adding one later means the old build has no branch
  for it.
- **`Idempotency-Key` accepted on every client-initiated write**, not only on webhooks.
  A visitor on a saturated network at a pandal double-taps *Pay*. That is the normal
  case here (`N-42`), not the edge case.
- **Responses carry a `server_time`.** Offline clients, expiring holds and 3-minute
  entry codes all need a clock they can trust more than the handset's.
- **Explicit API versioning** already exists as `/api/v1/`. Keep the discipline that v1
  is additive-only for its whole life.

### 3.2 Media goes to object storage on day one

`PandalPhoto.image` and, later, sponsor `Creative` uploads must go to S3-compatible
object storage, never local disk. Local disk means **you can never run a second
container** — the second one cannot see the first one's uploads.

This is a one-line settings choice now and a migration plus a deploy rewrite later.

### 3.3 The application stays stateless

No in-process caches, no local files, no per-worker state. Sessions in the database or
Redis. This is what makes "add another container" the answer to a load problem, and it
is nearly free if it is never violated.

### 3.4 Measure from the first deploy

Every deferral in §5 has a **numeric trigger**, and a trigger you cannot measure is a
wish. So from the first deploy:

- Request latency p50/p95/p99, per endpoint
- Database query count and duration per request
- **Lock wait time on pool rows** — the one metric unique to this system
- Celery queue depth and task latency
- Payment gateway latency and error rate, per dependency (this is also `NFR-1`'s
  circuit-breaker input)

`NFR-1` requires per-dependency timeouts and circuit breakers. Those need a timeout
budget per external call, set now — an unbounded outbound call is how one slow
gateway takes down gate validation.

---

## 4. Where this design would actually break

Two places. Both are cheap to fix now and neither is fixed by adding servers.

### 4.1 The hot pool row is the throughput ceiling

Every booking for a slot serialises on one `Pool` row. That is correct and it is what
makes NFR-5 hold — but it means the ceiling for a single slot is
`1 / (time the lock is held)`.

At a few milliseconds' hold, that is a few hundred bookings per second per slot —
comfortably past 100× the pilot. It stops being comfortable if the lock is held
longer, and there is one thing in the current code that could do that:

```python
def available(self, now=None):
    return self.capacity_granted - self.transferred_out - self.issued - self.held(now)
    #                                                                    ^^^^^^^^^^^
    # held() runs a SUM aggregate over the holds table — inside the lock.
```

`place_hold` and `issue` take the row lock, then run an aggregate. The existing index
on `(pool, state, expires_at)` keeps that bounded to a pool's *live* holds, which is
small — so this is not broken today. It is worth making explicitly safe:

- **A partial index** on active holds (`WHERE state = 'ACTIVE'`) keeps the aggregate
  proportional to live holds rather than to the index's history, and keeps the index
  itself small as the holds table accumulates a festival's worth of rows.
- **Nothing slow ever goes inside the lock.** No external call, no gateway round trip,
  no email, no signing. The rule to hold: *between `select_for_update` and `COMMIT`,
  only arithmetic and local writes.* `on_commit` exists for everything else.
- **Archive holds after the festival**, so the table does not grow without bound
  across years.

**Beyond ~1,000× the pilot**, the fix is to stop serialising on one row — splitting a
slot's capacity across N sibling pools and picking one at random spreads the lock, at
the cost of a slightly pessimistic availability read. The current model already
supports this without a schema change, because a pool can have children. That is worth
knowing and not worth building.

### 4.2 Availability listing is an N+1 by construction

`GET /pandals/{id}/slots/` returns each slot with its remaining availability. Done the
obvious way, that is one aggregate query per slot — 50 slots, 50 queries, on the
endpoint every visitor hits before booking.

Fix it in the first implementation, not later, because the serializer's shape depends
on it:

```python
Slot.objects.select_related("pool").annotate(
    live_held=Sum("pool__holds__quantity",
                  filter=Q(pool__holds__state="ACTIVE", pool__holds__expires_at__gt=now)),
)
```

One query for the page. This is the single most-requested endpoint in the system and
the one whose cost is most visible to a visitor.

---

## 5. What we defer, and the trigger that un-defers it

Deferred means **designed for and not built**. Each has a number attached, so the
decision to build it is a measurement rather than an argument.

| Deferred | Trigger | Effort when triggered |
|---|---|---|
| Cached availability (`SYS-09`) | `GET /pandals/{id}/slots/` p95 > 300 ms | ~1 day. Short-TTL cache; the pool stays the source of truth. |
| Read replica for browse traffic | Primary CPU > 60% sustained, or read p95 > 200 ms | ~half a day, given `DATABASE_ROUTERS` planned for. |
| pgBouncer | Postgres connections > 60% of `max_connections` | Hours. Transaction-mode pooling; requires no server-side prepared statements, which is a settings flag to set **now**. |
| Horizontal app scaling | Container CPU > 70% sustained | Minutes — **if** §3.2 and §3.3 were honoured. Weeks if they were not. |
| CDN for media and static | Image p95 > 500 ms, or egress cost is visible | Hours, given object storage. |
| Pool splitting for hot slots (§4.1) | Pool lock wait p95 > 50 ms | ~3 days. No schema change. |
| Asynchronous webhook issuance | Gateway webhook timeouts appear, or issuance p95 > 2 s | ~2 days. Webhook writes `PaymentEvent` and returns 200; a task issues. Adds latency to pass delivery, so not free. |
| Rate limiting beyond OTP | Any endpoint shows abusive traffic | Hours. OTP limiting (`N-18`) ships regardless — that is abuse control, not capacity. |

---

## 6. The design target: 10× the pilot

**Revised 8 September 2026.** The pilot figures size year one; the system is designed
and verified against **ten times** them:

| | Pilot | **Design target** |
|---|---|---|
| Passes per festival | 2,000 | **20,000** |
| Sold in the busiest hour | 200 | **2,000** |
| Through the largest pandal's gates, busiest hour | 200 | **2,000** |

**One clarification needed.** "20,000 passes" is ambiguous between *purchases* and
*admissions*, and the difference is threefold. An Individual Pass covering three pandals
is one purchase and three admissions, and it consumes three units of capacity. This
document assumes **20,000 pass artifacts averaging three legs each — 60,000 capacity
units.** If the client meant 20,000 admissions, every figure below is conservative by 3×,
which is the safe direction to be wrong in.

### What the arithmetic says

Peak hour of 2,000 bookings is **0.56 bookings/second** as a mean — but means are the
wrong unit here. Bookings arrive in a spike when a popular slot opens, so the number that
matters is the burst against the **single hottest pool row**:

| Burst vs. peak mean | Bookings/s | Leg-holds/s | Hottest pool, 40% concentration |
|---|---|---|---|
| ×5 | 2.8 | 8.3 | 3.3 /s |
| ×10 | 5.6 | 16.7 | 6.7 /s |
| ×20 | 11.1 | 33.3 | **13.3 /s** |

Against the lock budget for one row, which is `1 / lock hold time`:

| Lock held for | Row supports | Hottest pool at ×20 burst uses |
|---|---|---|
| 2 ms | 500 /s | 2.7% |
| 5 ms | 200 /s | 6.7% |
| 10 ms | 100 /s | 13.3% |
| 25 ms | 40 /s | 33.3% |
| **50 ms** | 20 /s | **66.5%** |

**The conclusion is worth stating plainly: at 10× the pilot, with a twentyfold arrival
burst and 40% of demand on one slot, the hottest row in the system runs at under 7% of
capacity — provided the lock is held for single-digit milliseconds.**

The design does not need sharding, a queue, a virtual waiting room, or a cache to reach
10×. It needs the lock held briefly. That is a discipline, not an architecture, and §4.1
already states it: *between `select_for_update` and `COMMIT`, only arithmetic and local
writes.*

The gate is even less stressed. 2,000 admissions/hour at the largest pandal is 0.56
scans/second; even with 40% of a 1,000-person slot arriving in the first five minutes it
is **1.3 scans/second**, against an NFR-2 budget of 500 ms per decision.

**So we do not add architecture. We add verification, discipline and headroom** — which
is what the rest of this document is about.

---

## 7. What actually becomes the constraint at 10×

The database is not the limit. Four other things are, in rough order of how likely they
are to bite.

### 7.1 External dependencies, which have their own limits

At 20,000 passes the system makes far more outbound calls than inbound ones, and every
one of them is somebody else's rate limit:

| Dependency | Volume at 10× | The risk |
|---|---|---|
| **SMS / OTP** | 20,000+ registrations and logins, concentrated in the days before Panchami | Provider throughput caps and DLT template throttling. A queue of undelivered OTPs is a queue of people who cannot log in. |
| **Payment gateway** | 20,000 orders plus webhooks and refunds | Per-second API rate limits; webhook delivery retries amplifying under load. |
| **Ad network (FR-71)** | One rewarded video per entry-code mint — potentially 300,000 | An external dependency **on the critical path to physical entry**. It will be the least reliable thing in the system. |
| **Push notifications** | 20,000 × several | Batch limits. |

`NFR-1` exists for exactly this: *"failure of any external dependency degrades only what
depends on it… a payment gateway timeout must not slow gate validation."* At 10× that
stops being theoretical. Every outbound call gets a **timeout, a retry budget and a
circuit breaker**, and none of them shares a connection pool with another.

**Agree provider quotas in advance.** SMS throughput and gateway rate limits are
commercial terms, and asking for them in October is asking too late.

### 7.2 Data volume, and one table that grows without bound

| Table | Rows at 10× | Note |
|---|---|---|
| `PassLeg` | 60,000 | Fine. |
| `Hold` | ~180,000 | Includes abandoned checkouts. Keeps the `available()` aggregate honest — hence the partial index in §4.1. |
| `ScanLog` | ~96,000 | Every scan, admitted or refused (`FR-12`). |
| **`EntryCode`** | **~300,000** | **`FR-70` makes minting unlimited.** Five mints per leg is a conservative estimate; a visitor waiting in a queue will mint repeatedly. |

`EntryCode` is the one to watch: it is the largest table, it grows with *user
frustration* rather than with sales, and it is on the hot path for the partial unique
index that enforces NFR-6 (one live code per leg). It needs the index, and it needs an
archival policy — codes older than the festival move out.

### 7.3 Background work

20,000 issuances each fanning out to an SMS, a receipt and a push is ~60,000 tasks,
bunched into the same hours as the bookings. Queue depth and worker count need sizing,
and `expire_holds` running every minute must stay a cheap indexed `UPDATE` as the table
grows.

### 7.4 The one query everyone runs

`GET /pandals/{id}/slots/` is hit by every visitor before every booking — the highest-QPS
endpoint by a wide margin, and the N+1 described in §4.2. At 10× that is the endpoint
that will show up first in the latency graphs. It ships annotated, not naive.

---

## 8. How we ensure it works

Everything above is arithmetic, and arithmetic is a hypothesis. **The system is not
"scalable" because this document says so; it is scalable when a load test says so.**

### 8.1 Load tests, with pass/fail criteria

Written in **Locust** (Python, so it shares the project's language and can import the
same factories). Run against a database **seeded to festival volume** — 60,000 legs,
180,000 holds, 300,000 entry codes — because query plans on empty tables prove nothing.

| ID | Scenario | Pass criteria |
|---|---|---|
| **LT-1** | Sustained mixed booking, 10/s for 15 min (18× peak mean) | Zero oversell. p95 < 500 ms. No 5xx. No deadlock. |
| **LT-2** | **Thundering herd** — 1,000 virtual visitors onto one slot of capacity 200 within 10 s | **Exactly 200 succeed**, 800 receive a clean refusal, zero oversell, p95 < 1 s, no deadlock, no lock timeout. |
| **LT-3** | Overlapping multi-leg bookings whose leg sets share pandals in **different orders** | No deadlock. This is the gap `BuildPlan` §7 flags in the current suite, which only covers pairs. |
| **LT-4** | Gate burst, 20 scans/s at one pandal, half of them queued offline then reconciled | p95 < 500 ms online (**NFR-2**). Zero wrong admit/refuse. Reconciliation within 2 min. Cross-gate duplicates surfaced. |
| **LT-5** | Webhook storm — every payment webhook replayed 3× concurrently | Exactly one pass issued per booking. No double-issue, no double-refund (**NFR-3**). |
| **LT-6** | Dependency failure injection — gateway timing out at 30 s, SMS provider 500ing, ad network dead | Unrelated operations degrade **< 10%** against baseline (**NFR-1's own acceptance criterion**). Gate validation unaffected. |
| **LT-7** | Six-hour soak at 2× peak mean | Flat memory. No connection leak. Query times do not drift as tables grow. |

**LT-2 is the one that matters most.** It is the only test that reproduces the actual
failure mode — everyone wanting the same slot at the same instant — and it is the direct
verification of NFR-5 under the conditions that will occur.

### 8.2 When they run

- **In CI, weekly**, on a schedule — a load test that runs only before launch tells you
  about the code you can no longer change.
- **A full run before 2 October**, the bookings-open date. Gate: no ship without a green
  LT-1, LT-2, LT-3, LT-5.
- **A full run before 16 October.** Gate: LT-4 and LT-6 green.
- **The adversarial suite (NFR-4, NFR-6) runs on every deploy** and any success blocks
  it, as `CLAUDE.md` already requires. That is separate from load testing and not
  negotiable against a deadline.

### 8.3 Headroom, not just correctness

Provision so that measured peak sits at **under 30% of tested capacity**. The gap absorbs
the difference between a modelled festival and a real one — and given the modelling
ambiguity in §6, that gap is doing real work.

---

## 9. Operating a festival that cannot be postponed

`N-41` makes this different from ordinary software: there is no rollback to next
Tuesday. Six days, immovable. So capacity planning is only half of it — the other half
is what happens when something is wrong at 8pm on Ashtami.

### 9.1 Degradation switches

Every one of these is a **runtime flag, not a deploy**, and each is decided in advance so
nobody is designing under pressure:

| Switch | Effect | When |
|---|---|---|
| Disable rewarded video (`FR-71`) | Codes mint without an ad | Ad network slow or failing — it is on the path to physical entry |
| Force gates to offline mode | Local validation, batch reconcile | Network saturation at the pandal (`N-42`) |
| Extend hold TTL | More time to complete payment | Gateway latency climbing |
| Disable coupon validation | Checkout proceeds without discounts | Coupon service degraded |
| Pause live status publishing | Sheds write load | Never needed, cheap to have |
| Browse-only mode | Reads served, bookings refused with an honest message | Database in trouble — degrade deliberately rather than time out |

### 9.2 A dress rehearsal

A full game day before 2 October: seed a real pandal, book through the real app, pay with
real (small) money, mint a code, scan it at a real gate, cut the network mid-scan, and
reconcile. Then do it again before 16 October with volunteers who have never seen the
system — `N-43` says committee volunteers operate these tools, not trained staff.

### 9.3 On-call and a runbook

Six days, evenings weighted. One page per failure mode: gateway down, SMS backed up, a
gate device lost, a pandal oversold, a visitor charged without a pass. Each with the
query to confirm it and the switch to pull.

---

## 10. What this changes in the other documents

- `docs/ClientQuestions.md` — Q1's consequences are staged with triggers, not closed.
- `docs/BuildPlan.md` §8 — `recompute_availability` is deferred with a trigger, not
  deleted.
- `docs/BuildPlan.md` §11.6 — "availability is computed, not cached" stands, and now has
  the measurement that would overturn it.
- `docs/ADR-002.md` — "pgBouncer if connection count becomes real" now has a number: 60%
  of `max_connections`.
- `docs/Schedule.md` — the load-test suite and the two game days are schedule items, not
  spare-time work. Roughly **three days**, and they belong inside whichever scope option
  is chosen rather than after it.
- **New in first-release scope**, none of it large: cursor pagination, the error
  envelope, `Idempotency-Key` on writes, `server_time`, object storage, the partial index
  on active holds, the annotated availability query, per-dependency timeouts and circuit
  breakers, the degradation switches, and instrumentation.

---

## 11. The short version

At 10× the pilot the database design holds with **93% headroom on its hottest row**, and
needs no sharding, queue or cache to do it. What it needs is:

1. **The lock held for milliseconds** — nothing slow between `select_for_update` and
   `COMMIT`, ever.
2. **Every external dependency isolated** behind a timeout and a circuit breaker, with
   provider quotas agreed in advance — because at this size they fail before we do.
3. **One index and one annotation** — the partial index on active holds, and the
   annotated availability query.
4. **A load test that reproduces the thundering herd**, run weekly and gating both
   go-live dates.
5. **Switches to degrade deliberately**, because the festival does not move.

Points 1–3 are about two days of work. Points 4–5 are about three. That is the whole cost
of building for 10× instead of for 1×, and it is why it is worth doing now rather than
discovering the difference in October.
