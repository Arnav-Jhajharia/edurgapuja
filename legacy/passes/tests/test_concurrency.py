"""Concurrent booking against one pool.

None of this behaviour is observable single-threaded. The whole point of
``select_for_update`` is what happens when two transactions want the same row at
the same instant, so these tests use real threads against a real database and
each thread gets its own connection.
"""

import threading
from datetime import timedelta

from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone

from legacy.passes import operations as ops
from legacy.passes.exceptions import PoolError
from legacy.passes.models import Organisation, Pandal, Pass, Pool, Slot

CAPACITY = 50
THREADS = 20
PER_THREAD = 5


def run_concurrently(target, count):
    """Run ``target`` in ``count`` threads, released together, and collect outcomes."""
    barrier = threading.Barrier(count)
    results = []
    lock = threading.Lock()

    def wrapper(index):
        barrier.wait()
        try:
            target(index)
            outcome = ("ok", None)
        except PoolError as exc:
            outcome = ("refused", exc)
        finally:
            connections.close_all()  # each thread holds its own connection
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=wrapper, args=(i,)) for i in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


class ConcurrentBookingTests(TransactionTestCase):
    def setUp(self):
        self.pandal = Pandal.objects.create(name="Deshapriya Park")
        self.slot = Slot.objects.create(
            pandal=self.pandal,
            starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1, hours=1),
        )
        self.root = ops.create_root_pool(self.slot, CAPACITY)

    def test_concurrent_issue_never_oversells(self):
        """20 threads asking for 5 each against a capacity of 50.

        Exactly 10 should succeed. The rest must be refused, not queued and not
        silently trimmed.
        """
        run_concurrently(lambda i: ops.issue(self.root.id, PER_THREAD), THREADS)

        self.root.refresh_from_db()
        self.assertEqual(self.root.issued, CAPACITY)
        self.assertEqual(Pass.objects.count(), CAPACITY)
        self.assertEqual(self.root.available(), 0)

    def test_concurrent_holds_never_oversell(self):
        run_concurrently(lambda i: ops.place_hold(self.root.id, PER_THREAD), THREADS)

        self.root.refresh_from_db()
        self.assertEqual(self.root.held(), CAPACITY)
        self.assertEqual(self.root.available(), 0)

    def test_hold_then_issue_under_contention(self):
        """The full booking path: hold, then issue against that hold.

        A hold that succeeded must always be issuable. If any thread gets a hold
        and is then refused the issue, capacity was double-counted somewhere.
        """
        holds = []
        lock = threading.Lock()

        def book(index):
            hold = ops.place_hold(self.root.id, PER_THREAD)
            with lock:
                holds.append(hold.id)
            ops.issue(self.root.id, PER_THREAD, hold_id=hold.id)

        results = run_concurrently(book, THREADS)
        succeeded = sum(1 for status, _ in results if status == "ok")

        self.assertEqual(succeeded, CAPACITY // PER_THREAD)
        self.root.refresh_from_db()
        self.assertEqual(self.root.issued, CAPACITY)

    def test_concurrent_transfers_do_not_deadlock(self):
        """Two children drawing from one parent at once.

        Pools are locked in primary-key order, so overlapping transfers serialise
        rather than deadlocking.
        """
        sponsor_a = Organisation.objects.create(name="Sponsor A")
        sponsor_b = Organisation.objects.create(name="Sponsor B")
        pool_a = ops.create_child_pool(self.root.id, sponsor_a)
        pool_b = ops.create_child_pool(self.root.id, sponsor_b)
        targets = [pool_a.id, pool_b.id]

        run_concurrently(
            lambda i: ops.transfer(self.root.id, targets[i % 2], PER_THREAD), THREADS
        )

        self.root.refresh_from_db()
        moved = sum(
            p.capacity_granted for p in Pool.objects.filter(parent=self.root)
        )
        self.assertEqual(self.root.transferred_out, moved)
        self.assertLessEqual(self.root.transferred_out, CAPACITY)