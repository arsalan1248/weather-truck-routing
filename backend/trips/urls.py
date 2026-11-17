from django.urls import path

from .views import HealthView, TripCreateView

urlpatterns = [
    path('health/', HealthView.as_view()),
    path('trips/', TripCreateView.as_view()),
]
