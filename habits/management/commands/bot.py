import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from habits.models import TelegramProfile

User = get_user_model()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды '/start' для связывания Telegram с аккаунтом на сайте"""
    user = update.effective_user
    chat_id = str(update.effective_chat.id)
    username = user.username

    django_user = User.objects.filter(username=username).first()
    if django_user:
        profile, created = TelegramProfile.objects.get_or_create(user=django_user)
        profile.telegram_chat_id = chat_id
        profile.save()
        await update.message.reply_text(
            f"Привет, {django_user.username}! Ваш Telegram успешно привязан."
            f"Теперь Вы будете получать уведомления о привычках."
        )
    else:
        await update.message.reply_text(
            f"Пользователь с именем @{username} не найден на сайте."
            f"Пожалуйста, сначала зарегистрируйтесь на нашем сайте с тем же username."
        )


class Command(BaseCommand):
    """Запуск Telegram-бота"""

    def handle(self, *args, **options):
        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        self.stdout.write(self.style.SUCCESS("Бот запущен..."))
        application.run_polling(allowed_updates=Update.ALL_TYPES)
