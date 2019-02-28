from django.urls import path
from ktkart.api.views import RegisterView, LoginView, GetBalanceView, UpdateBalanceView
from ktkart.api.views import GetAvailableKartsView, BookingView, GetNearKartsView, PopulateView, MultipleBookingView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name="auth-register"),
    path('auth/login/', LoginView.as_view(), name="auth-login"),
    path('balance/get/', GetBalanceView.as_view(), name="balance-get"),
    path('balance/update/', UpdateBalanceView.as_view(), name="balance-update"),
    path('available_karts/', GetAvailableKartsView.as_view(), name="available_karts"),
    path('booking/', BookingView.as_view(), name="booking"),
    path('near_karts/', GetNearKartsView.as_view(), name="near_karts"),
    path('multiple_booking/', MultipleBookingView.as_view(), name="multiple_booking"),
    path('populate/', PopulateView.as_view(), name="populate")
]
