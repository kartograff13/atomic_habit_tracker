from django.urls import path

from . import views

urlpatterns = [
    path("habits/", views.HabitListCreateView.as_view(), name="habit-list"),
    path("habits/<int:pk>/", views.HabitRetrieveUpdateDestroyView.as_view(), name="habit-detail"),
    path("habits/public/", views.PublicHabitListView.as_view(), name="public-habit-list"),
]
