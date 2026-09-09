from django.urls import path

from .views import OrderDetailView, OrderReceiptView

urlpatterns = [
    path("orders/<uuid:order_id>", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<uuid:order_id>/receipt", OrderReceiptView.as_view(), name="order-receipt"),
]
