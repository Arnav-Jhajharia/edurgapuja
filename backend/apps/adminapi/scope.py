"""Who is this administrator, and what may they see?

Every admin response is scoped to the caller's own entity unless they are a
Super Admin (FR-233). That scoping happens **in the queryset**, never by hiding a
button — the four panels differ in what they render, but authority comes from
these rows and is checked server-side (FR-231).
"""

from dataclasses import dataclass, field

from apps.accounts.models import AdminMembership, Role


@dataclass(frozen=True)
class AdminContext:
    roles: set[str] = field(default_factory=set)
    pandal_ids: set = field(default_factory=set)
    organisation_ids: set = field(default_factory=set)

    @property
    def is_super(self) -> bool:
        return Role.SUPER_ADMIN in self.roles

    @property
    def is_pandal_admin(self) -> bool:
        return Role.PANDAL_ADMIN in self.roles

    @property
    def is_sponsor_admin(self) -> bool:
        return Role.SPONSOR_ADMIN in self.roles

    @property
    def is_sub_sponsor_admin(self) -> bool:
        return Role.SUB_SPONSOR_ADMIN in self.roles

    @property
    def is_any_admin(self) -> bool:
        return bool(self.roles)

    def pandals(self, queryset, *, field: str = "pandal"):
        """Narrow a queryset of pandals, or of anything that reaches one.

        `field` is the path from this model to the pandal — "pandal" for the
        common case, "gate__pandal" for a scan event, which belongs to a gate
        which belongs to a pandal.
        """
        if self.is_super:
            return queryset
        if queryset.model.__name__ == "Pandal":
            return queryset.filter(id__in=self.pandal_ids)
        return queryset.filter(**{f"{field}_id__in": self.pandal_ids})

    def owns_pandal(self, pandal_id) -> bool:
        return self.is_super or pandal_id in self.pandal_ids

    def owns_organisation(self, organisation_id) -> bool:
        return self.is_super or organisation_id in self.organisation_ids


def context_for(user) -> AdminContext:
    if not user or not user.is_authenticated:
        return AdminContext()

    memberships = AdminMembership.objects.filter(user=user, is_active=True)
    return AdminContext(
        roles={m.role for m in memberships},
        pandal_ids={m.pandal_id for m in memberships if m.pandal_id},
        organisation_ids={m.organisation_id for m in memberships if m.organisation_id},
    )
