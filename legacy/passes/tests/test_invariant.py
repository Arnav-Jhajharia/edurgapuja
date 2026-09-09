"""The invariant, tested against random sequences of operations.

The property under test: for every pool at every depth, at every point in time,

    transferred_out + issued + live_held  <=  capacity_granted

and, across the whole tree, no capacity is created or destroyed -- the sum of
what the root granted equals what its descendants hold plus what has been issued
plus what is still held.
"""

from datetime import timedelta

from django.test import TransactionTestCase
from django.utils import timezone
from hypothesis import HealthCheck, given, settings as hyp_settings, strategies as st

from legacy.passes import operations as ops
from legacy.passes.exceptions import InsufficientCapacity, PoolError
from legacy.passes.models import Hold, Organisation, Pandal, Pass, Pool, Slot

ROOT_CAPACITY = 100


def assert_invariant(test):
    """Every pool respects its own capacity, and the tree conserves capacity."""
    now = timezone.now()
    for pool in Pool.objects.all():
        outflow = pool.transferred_out + pool.issued + pool.held(now)
        test.assertLessEqual(
            outflow,
            pool.capacity_granted,
            f"pool {pool.id} at depth {pool.depth} overspent: "
            f"{outflow} > {pool.capacity_granted}",
        )

    for pool in Pool.objects.all():
        children_granted = sum(c.capacity_granted for c in pool.children.all())
        test.assertEqual(
            pool.transferred_out,
            children_granted,
            f"pool {pool.id} transferred {pool.transferred_out} "
            f"but children received {children_granted}",
        )

    live_passes = Pass.objects.exclude(state=Pass.State.VOID).count()
    issued_total = sum(p.issued for p in Pool.objects.all())
    test.assertEqual(issued_total, live_passes)


operation = st.sampled_from(["hold", "issue", "transfer", "release", "expire", "void"])
quantity = st.integers(min_value=1, max_value=40)


class PoolInvariantTests(TransactionTestCase):
    """Random operation sequences against a real database.

    TransactionTestCase rather than TestCase: these operations take row locks and
    commit, which a wrapping test transaction would hide.
    """

    def setUp(self):
        self.pandal = Pandal.objects.create(name="Shib Mandir")
        self.slot = Slot.objects.create(
            pandal=self.pandal,
            starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1, hours=1),
        )
        self.sponsor = Organisation.objects.create(name="Sponsor One")
        self.sub = Organisation.objects.create(name="Kolkata Sweets", parent=self.sponsor)

        self.root = ops.create_root_pool(self.slot, ROOT_CAPACITY)
        self.sponsor_pool = ops.create_child_pool(self.root.id, self.sponsor)
        self.sub_pool = ops.create_child_pool(self.sponsor_pool.id, self.sub)
        self.pools = [self.root, self.sponsor_pool, self.sub_pool]

    def tearDown(self):
        Pass.objects.all().delete()
        Hold.objects.all().delete()
        Pool.objects.all().delete()
        Organisation.objects.all().delete()
        Slot.objects.all().delete()
        Pandal.objects.all().delete()

    @hyp_settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        script=st.lists(
            st.tuples(operation, st.integers(min_value=0, max_value=2), quantity),
            min_size=1,
            max_size=30,
        )
    )
    def test_invariant_holds_under_random_operations(self, script):
        """No sequence of legal calls can break the invariant.

        Operations that raise are expected -- an over-request should be refused,
        not absorbed. What matters is that a refusal leaves no partial effect.
        """
        for op_name, pool_index, qty in script:
            pool = self.pools[pool_index]
            try:
                if op_name == "hold":
                    ops.place_hold(pool.id, qty)
                elif op_name == "issue":
                    ops.issue(pool.id, qty)
                elif op_name == "transfer":
                    if pool.parent_id is not None:
                        ops.transfer(pool.parent_id, pool.id, qty)
                elif op_name == "release":
                    hold = Hold.objects.filter(
                        pool=pool, state=Hold.State.ACTIVE
                    ).first()
                    if hold:
                        ops.release_hold(hold.id)
                elif op_name == "expire":
                    ops.expire_holds()
                elif op_name == "void":
                    p = Pass.objects.filter(
                        pool=pool, state=Pass.State.ISSUED
                    ).first()
                    if p:
                        ops.void_pass(p.id)
            except (PoolError, ValueError):
                pass  # refusals are correct behaviour

            assert_invariant(self)

    def test_cannot_issue_more_than_granted(self):
        with self.assertRaises(InsufficientCapacity):
            ops.issue(self.root.id, ROOT_CAPACITY + 1)
        assert_invariant(self)

    def test_expired_hold_stops_counting_without_a_sweep(self):
        """Availability is time-based, so a late sweeper cannot oversell."""
        hold = ops.place_hold(self.root.id, 100, ttl_seconds=1)
        self.assertEqual(self.root.available(), 0)

        future = timezone.now() + timedelta(seconds=5)
        self.assertEqual(self.root.available(now=future), 100)
        self.assertEqual(Hold.objects.get(pk=hold.id).state, Hold.State.ACTIVE)

    def test_transfer_conserves_capacity_across_three_tiers(self):
        ops.transfer(self.root.id, self.sponsor_pool.id, 60)
        ops.transfer(self.sponsor_pool.id, self.sub_pool.id, 25)
        ops.issue(self.sub_pool.id, 10)

        self.root.refresh_from_db()
        self.sponsor_pool.refresh_from_db()
        self.sub_pool.refresh_from_db()

        self.assertEqual(self.root.available(), 40)
        self.assertEqual(self.sponsor_pool.available(), 35)
        self.assertEqual(self.sub_pool.available(), 15)
        assert_invariant(self)

    def test_sub_sponsor_cannot_draw_from_the_root(self):
        """A sub-sponsor buys from its sponsor, never from a pandal (FR-36)."""
        from legacy.passes.exceptions import NotAChildPool

        with self.assertRaises(NotAChildPool):
            ops.transfer(self.root.id, self.sub_pool.id, 5)
        assert_invariant(self)

    def test_void_returns_capacity(self):
        issued = ops.issue(self.root.id, 3)
        ops.void_pass(issued[0].id)
        self.root.refresh_from_db()
        self.assertEqual(self.root.available(), ROOT_CAPACITY - 2)
        assert_invariant(self)