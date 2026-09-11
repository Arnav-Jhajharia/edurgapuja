from django.urls import path

from .views import (
    CashfreeWebhookView,
    PaymentMethodsView,
    RazorpayWebhookView,
    VerifyPaymentView,
)

urlpatterns = [
    path("payments/providers", PaymentMethodsView.as_view(), name="payment-providers"),
    path("payments/verify", VerifyPaymentView.as_view(), name="payment-verify"),
    path("payments/webhooks/razorpay", RazorpayWebhookView.as_view(), name="razorpay-webhook"),
    path("payments/webhooks/cashfree", CashfreeWebhookView.as_view(), name="cashfree-webhook"),
]
