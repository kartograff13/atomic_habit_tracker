from django.contrib import admin

from habits.models import Habit, TelegramProfile


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    """Административная конфигурация для модели Habit"""

    list_display = ("id", "user", "action", "time", "place", "is_pleasant", "is_public")
    list_filter = ("is_pleasant", "is_public", "periodicity")
    search_fields = ("action", "place", "user__username")
    readonly_fields = ("user",)


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    """Административная конфигурация для модели TelegramProfile"""

    list_display = ("id", "user", "telegram_chat_id")
    search_fields = ("user__username", "telegram_chat_id")
