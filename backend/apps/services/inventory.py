"""Service capacity, bound to the shared primitive.

When passes arrive, `apps/passes/inventory.py` is this file with two different
model names and no new algorithm (Scope §4.3).
"""

from functools import partial

from apps.inventory import operations

from .models import ServiceCapacityHold, ServiceDayCapacity

available = partial(operations.available, ServiceCapacityHold)
live_holds = partial(operations.live_holds, ServiceCapacityHold)
place_hold = partial(operations.place_hold, ServiceDayCapacity, ServiceCapacityHold)
issue = partial(operations.issue, ServiceDayCapacity, ServiceCapacityHold)
give_back = partial(operations.give_back, ServiceDayCapacity)
release_hold = partial(operations.release_hold, ServiceCapacityHold)
expire_holds = partial(operations.expire_holds, ServiceCapacityHold)
