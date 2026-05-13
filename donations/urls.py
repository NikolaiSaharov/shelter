from django.urls import path
from .views import DonationCreateView, DonationPayView, DonationConfirmView, DonationReceiptView

urlpatterns = [
    path('create/', DonationCreateView.as_view(), name='donation_create'),
    path('pay/', DonationPayView.as_view(), name='donation_pay'),
    path('confirm/', DonationConfirmView.as_view(), name='donation_confirm'),
    path('receipt/<int:pk>/', DonationReceiptView.as_view(), name='donation_receipt'),
]
