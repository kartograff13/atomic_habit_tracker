from rest_framework import generics, permissions

from habits.models import Habit
from habits.permissions import IsOwner
from habits.serializers import HabitSerializer


class HabitListCreateView(generics.ListCreateAPIView):
    """
    Представление для получения списка привычек пользователя и создание новой.

    Доступно только аутентифицированным пользователям. При создании привычки
    текущий пользователь автоматически становится её владельцем. При получении
    списка возвращаются только привычки, принадлежащие текущему пользователю.
    """

    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class HabitRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Представление для получения, обновления и удаления конкретной привычки.

    Доступно только аутентифицированным пользователям, которые являются владельцем
    привычки (проверка через кастомное разрешение IsOwner).
    """

    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = Habit.objects.all()


class PublicHabitListView(generics.ListAPIView):
    """
    Представление для получения списка публичных привычек.

    Доступно только аутентифицированным пользователям. Возвращает все привычки,
    у которых флаг `is_public` установлен в True. Не требует проверки владельца.
    """

    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Habit.objects.filter(is_public=True)
