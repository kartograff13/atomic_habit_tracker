from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

User = get_user_model()


class Habit(models.Model):
    """Модель привычки для трекера полезных привычек"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habits")
    place = models.CharField(max_length=255)
    time = models.TimeField()
    action = models.CharField(max_length=255)
    is_pleasant = models.BooleanField(default=False)
    related_habit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="main_habits",
        help_text="Только для полезных привычек, связанная привычка должна быть приятной",
    )
    periodicity = models.PositiveSmallIntegerField(default=1)
    reward = models.CharField(max_length=255, null=True, blank=True)
    duration = models.PositiveSmallIntegerField()
    is_public = models.BooleanField(default=False)

    def clean(self):
        """Выполняет валидацию модели в соответствии с правилами трекера привычек"""
        if self.reward and self.related_habit:
            raise ValidationError("Нельзя одновременно указать вознаграждение и связанную привычку")

        if self.duration > 120:
            raise ValidationError("Время выполнения должно быть не более 120 секунд")

        if self.related_habit and not self.related_habit.is_pleasant:
            raise ValidationError("Связанная привычка должна быть приятной")

        if self.is_pleasant:
            if self.reward or self.related_habit:
                raise ValidationError("У приятной привычки не может быть вознаграждения или связанной привычки")

        if not (1 <= self.periodicity <= 7):
            raise ValidationError("Периодичность должна быть от 1 до 7 дней")

    def save(self, *args, **kwargs):
        """Сохраняет модель, предварительно выполняя полную валидацию"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Возвращает строковое представление привычки"""
        return f"{self.user}: {self.action} в {self.time} - {self.place}"

    class Meta:
        verbose_name = "Привычка"
        verbose_name_plural = "Привычки"


class TelegramProfile(models.Model):
    """Модель для хранения Telegram-профиля пользователя"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="telegram_profile")
    telegram_chat_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.user.username}'s Telegram Profile"
