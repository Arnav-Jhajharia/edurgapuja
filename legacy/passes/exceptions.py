"""Errors raised by pool operations.

Every one of these means the operation did not happen. Operations raise rather
than returning a boolean, so a caller that ignores the result cannot silently
proceed as if capacity had moved.
"""


class PoolError(Exception):
    """Base for everything in this module."""


class InsufficientCapacity(PoolError):
    def __init__(self, pool_id, requested, available):
        self.pool_id = pool_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"pool {pool_id}: requested {requested}, available {available}"
        )


class HoldNotLive(PoolError):
    """The hold was already consumed, released, or has expired."""


class HoldMismatch(PoolError):
    """The hold belongs to a different pool, or covers fewer passes than asked."""


class NotAChildPool(PoolError):
    """Transfer attempted between pools that are not parent and child."""


class MaxDepthExceeded(PoolError):
    """Creating this pool would exceed the configured hierarchy depth."""


class PassNotVoidable(PoolError):
    """The pass has already been consumed at a gate, or is already void."""