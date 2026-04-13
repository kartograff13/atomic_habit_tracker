from rest_framework import generics, permissions

from habits.models import Habit
from habits.permissions import IsOwner
from habits.serializers import HabitSerializer


class HabitListCreateView(generics.ListCreateAPIView):
    """Представление для получения списка привычек пользователя и создание новой"""

    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class HabitRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Представление для получения, обновления и удаления конкретной привычки"""

    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user).order_by("id")


class PublicHabitListView(generics.ListAPIView):
    """Представление для получения списка публичных привычек"""

    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Habit.objects.filter(is_public=True).order_by("id")
