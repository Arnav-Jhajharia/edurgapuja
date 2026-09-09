"""Pandal capacity, bound to the shared primitive.

Compare with `apps/services/inventory.py`: the same six lines with two different
model names. No new algorithm, and the property test already proved it.
"""

from functools import partial

from apps.inventory import operations

from .models import PandalCapacityHold, PandalDayCapacity

available = partial(operations.available, PandalCapacityHold)
live_holds = partial(operations.live_holds, PandalCapacityHold)
place_hold = partial(operations.place_hold, PandalDayCapacity, PandalCapacityHold)
issue = partial(operations.issue, PandalDayCapacity, PandalCapacityHold)
give_back = partial(operations.give_back, PandalDayCapacity)
release_hold = partial(operations.release_hold, PandalCapacityHold)
expire_holds = partial(operations.expire_holds, PandalCapacityHold)
