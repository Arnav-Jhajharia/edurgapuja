from rest_framework.permissions import BasePermission

from .scope import context_for


class BaseAdminPermission(BasePermission):
    """Attaches the caller's scope to the request, so views never recompute it."""

    def has_permission(self, request, view) -> bool:
        request.admin = context_for(request.user)
        return self.allows(request.admin)

    def allows(self, admin) -> bool:
        raise NotImplementedError


class IsAdmin(BaseAdminPermission):
    def allows(self, admin) -> bool:
        return admin.is_any_admin


class IsPandalAdmin(BaseAdminPermission):
    def allows(self, admin) -> bool:
        return admin.is_super or admin.is_pandal_admin


class IsSponsorAdmin(BaseAdminPermission):
    def allows(self, admin) -> bool:
        return admin.is_super or admin.is_sponsor_admin or admin.is_sub_sponsor_admin


class IsSuperAdmin(BaseAdminPermission):
    def allows(self, admin) -> bool:
        return admin.is_super
