from django.urls import path

from .views import HealthView, TripCreateView, TripHeatmapView

urlpatterns = [
    path('health/', HealthView.as_view()),
    path('trips/', TripCreateView.as_view()),
    path('trips/<str:trip_id>/heatmap/', TripHeatmapView.as_view()),
]
