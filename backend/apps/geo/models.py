from django.db import models

from apps.common.models import BaseModel


class State(BaseModel):
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=4, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class City(BaseModel):
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="cities")
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "cities"
        constraints = [models.UniqueConstraint(fields=["state", "name"], name="uniq_city_in_state")]

    def __str__(self) -> str:
        return self.name


class Locality(BaseModel):
    """'South Kolkata', 'Ballygunge' — how pandals are grouped and found."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="localities")
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "localities"
        constraints = [
            models.UniqueConstraint(fields=["city", "name"], name="uniq_locality_in_city")
        ]

    def __str__(self) -> str:
        return f"{self.name}, {self.city.name}"
