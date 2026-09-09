"""The capacity primitive.

v1 uses it for services. Passes will use the same two abstractions and the same
four operations against `PandalDayCapacity` (Scope §4.3) — which is the point of
building it here first, on something lower-stakes than the festival's entire
admission system.
"""

from django.db import models

from apps.common.models import BaseModel


class DayCapacity(BaseModel):
    """Capacity for one owner on one day.

    `issued_count` is only ever written under this row's lock. The CHECK is the
    floor: no race, no bug and no bad migration can put more through a day than
    was allowed, because the database refuses the write.
    """

    date = models.DateField()
    capacity = models.PositiveIntegerField()
    issued_count = models.PositiveIntegerField(default=0)
    is_open = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"{self.date}: {self.issued_count}/{self.capacity}"


class Hold(BaseModel):
    """A claim on capacity while a visitor is paying.

    Holds are rows, not a counter, so an expired hold stops occupying capacity
    the instant it expires — whether or not a sweeper has run.
    """

    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField()
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"hold ×{self.quantity} until {self.expires_at:%H:%M}"
