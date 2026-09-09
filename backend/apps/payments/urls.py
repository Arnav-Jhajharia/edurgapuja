from django.urls import path

from .views import CashfreeWebhookView, PaymentMethodsView, RazorpayWebhookView

urlpatterns = [
    path("payments/providers", PaymentMethodsView.as_view(), name="payment-providers"),
    path("payments/webhooks/razorpay", RazorpayWebhookView.as_view(), name="razorpay-webhook"),
    path("payments/webhooks/cashfree", CashfreeWebhookView.as_view(), name="cashfree-webhook"),
]
