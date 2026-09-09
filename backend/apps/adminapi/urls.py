from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.accounts.views import AuthMethodsView

from . import views

router = SimpleRouter(trailing_slash=False)
router.register("pandals", views.PandalViewSet, basename="admin-pandal")
router.register("cities", views.CityViewSet, basename="admin-city")
router.register("localities", views.LocalityViewSet, basename="admin-locality")
router.register("visit-facts", views.VisitFactViewSet, basename="admin-visit-fact")
router.register("donation-offerings", views.DonationOfferingViewSet, basename="admin-offering")
router.register("donation-links", views.DonationLinkViewSet, basename="admin-donation-link")
router.register("donations", views.DonationViewSet, basename="admin-donation")
router.register("services", views.ServiceViewSet, basename="admin-service")
router.register("service-bookings", views.ServiceBookingViewSet,
                basename="admin-service-booking")
router.register("service-fields", views.ServiceFieldViewSet,
                basename="admin-service-field")
router.register("lost-items", views.LostItemViewSet, basename="admin-lost-item")
router.register("support-requests", views.SupportRequestViewSet, basename="admin-support")
router.register("gates", views.GateViewSet, basename="admin-gate")
router.register("volunteers", views.VolunteerViewSet, basename="admin-volunteer")
router.register("packages", views.PackageViewSet, basename="admin-package")
router.register("organisations", views.OrganisationViewSet, basename="admin-organisation")
router.register("allocations", views.AllocationViewSet, basename="admin-allocation")
router.register("pools", views.PoolViewSet, basename="admin-pool")
router.register("creatives", views.CreativeViewSet, basename="admin-creative")
router.register("issuances", views.IssuanceViewSet, basename="admin-issuance")
router.register("users", views.UserViewSet, basename="admin-user")
router.register("staff", views.StaffViewSet, basename="admin-staff")
router.register("pass-categories", views.PassCategoryViewSet, basename="admin-pass-category")
router.register("pass-configs", views.PassConfigViewSet, basename="admin-pass-config")
router.register("passes", views.AdminPassViewSet, basename="admin-pass")
router.register("scans", views.ScanEventViewSet, basename="admin-scan")

urlpatterns = [
    path("auth/otp/request", views.AdminOtpRequestView.as_view(), name="admin-otp-request"),
    path("auth/otp/verify", views.AdminOtpVerifyView.as_view(), name="admin-otp-verify"),
    path("auth/password/login", views.AdminPasswordLoginView.as_view(),
         name="admin-password-login"),
    path("auth/methods", AuthMethodsView.as_view(), name="admin-auth-methods"),
    path("me", views.AdminMeView.as_view(), name="admin-me"),
    path("revenue", views.RevenueView.as_view(), name="admin-revenue"),
    path("dashboard", views.PlatformDashboardView.as_view(), name="admin-dashboard"),
    path("sponsor/overview", views.SponsorOverviewView.as_view(),
         name="admin-sponsor-overview"),
    path("sponsor/buy", views.BuyPassesView.as_view(), name="admin-sponsor-buy"),
    path("pandals/<uuid:pandal_id>/day-capacity", views.PandalDayCapacityView.as_view(),
         name="admin-pandal-day-capacity"),
    path("pass-summary", views.PassSummaryView.as_view(), name="admin-pass-summary"),
    *router.urls,
]
