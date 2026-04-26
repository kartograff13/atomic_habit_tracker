from rest_framework import serializers

from habits.models import Habit


class HabitSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Habit (привычка)"""

    class Meta:
        model = Habit
        fields = "__all__"
        read_only_fields = ("user",)

    def validate(self, data):
        """Выполняет валидацию данных привычки в соответствии с правилами трекера"""
        if data.get("reward") and data.get("related_habit"):
            raise serializers.ValidationError("Нельзя одновременно указать вознаграждение и связанную привычку")

        if data.get("duration", 0) > 120:
            raise serializers.ValidationError("Время выполнения должно быть не более 120 секунд")

        if data.get("related_habit") and not data["related_habit"].is_pleasant:
            raise serializers.ValidationError("Связанная привычка должна быть приятной")

        if data.get("is_pleasant") and (data.get("reward") or data.get("related_habit")):
            raise serializers.ValidationError(
                "У приятной привычки не может быть вознаграждения или связанной привычки"
            )

        periodicity = data.get("periodicity", 1)
        if not (1 <= periodicity <= 7):
            raise serializers.ValidationError("Периодичность должна быть от 1 до 7 дней")

        return data
