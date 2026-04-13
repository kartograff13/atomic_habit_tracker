import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from telegram import Bot

from habits.models import Habit

logger = logging.getLogger(__name__)


@shared_task
def send_habit_reminders():
    """Рассылает уведомления о привычках, которые нужно выполнить"""
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    now = timezone.localtime(timezone.now())
    current_time = now.time()
    time_window_start = (now - timedelta(minutes=1)).time()
    time_window_end = (now + timedelta(minutes=1)).time()

    habits_to_notify = Habit.objects.select_related("user__telegram_profile").filter(
        time__gte=time_window_start,
        time__lte=time_window_end,
        is_pleasant=False,
        user__telegram_profile__isnull=False,
    )

    for habit in habits_to_notify:
        chat_id = habit.user.telegram_profile.telegram_chat_id
        time_str = habit.time.strftime("%H:%M")
        message = (
            f"Напоминание о привычке!\n"
            f"Действие: {habit.action}\n"
            f"Место: {habit.place}\n"
            f"Время: {time_str}\n"
            f"Вознаграждение: {habit.reward if habit.reward else 'Приятная привычка'}"
        )

        try:
            bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Отправлено уведомление пользователю {habit.user.username} (chat_id: {chat_id})")
        except Exception as e:
            logging.error(f"Ошибка отправки уведомления пользователю {habit.user.username}: {e}")
