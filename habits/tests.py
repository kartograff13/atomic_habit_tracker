from datetime import time
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from habits.models import Habit, TelegramProfile
from habits.serializers import HabitSerializer
from habits.tasks import send_habit_reminders

User = get_user_model()


class HabitModelTest(TestCase):
    """Тесты для модели Habit (валидация, создание, связи)"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.pleasant_habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Выпить стакан воды",
            is_pleasant=True,
            periodicity=1,
            duration=30,
            is_public=False,
        )

    def test_create_valid_habit(self):
        """Проверка создания корректной полезной привычки с вознаграждением"""
        habit = Habit(
            user=self.user,
            place="Офис",
            time=time(12, 0),
            action="Прогулка",
            is_pleasant=False,
            periodicity=1,
            duration=60,
            reward="Кофе",
        )
        habit.full_clean()
        habit.save()
        self.assertEqual(Habit.objects.count(), 2)

    def test_create_habit_with_related_pleasant_habit(self):
        """Полезная привычка может быть связана с приятной"""
        habit = Habit(
            user=self.user,
            place="Улица",
            time=time(18, 0),
            action="Пробежка",
            is_pleasant=False,
            related_habit=self.pleasant_habit,
            periodicity=1,
            duration=90,
        )
        habit.full_clean()
        habit.save()
        self.assertEqual(habit.related_habit, self.pleasant_habit)

    def test_cannot_have_both_reward_and_related_habit(self):
        """Нельзя одновременно указать вознаграждение и связанную привычку"""
        habit = Habit(
            user=self.user,
            place="Дом",
            time=time(20, 0),
            action="Чтение",
            is_pleasant=False,
            related_habit=self.pleasant_habit,
            reward="Печенье",
            periodicity=1,
            duration=60,
        )
        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_duration_cannot_exceed_120_seconds(self):
        """Время выполнения не должно превышать 120 секунд"""
        habit = Habit(user=self.user, place="Дом", time=time(8, 0), action="Зарядка", duration=121)
        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_related_habit_must_be_pleasant(self):
        """Связанная привычка должна быть приятной"""
        another_useful = Habit.objects.create(
            user=self.user,
            place="Работа",
            time=time(15, 0),
            action="Сделать отчёт",
            is_pleasant=False,
            periodicity=1,
            duration=100,
        )
        habit = Habit(
            user=self.user,
            place="Дом",
            time=time(17, 0),
            action="Отдых",
            is_pleasant=False,
            related_habit=another_useful,
            periodicity=1,
            duration=50,
        )
        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_pleasant_habit_cannot_have_reward_or_related(self):
        """Приятная привычка не может иметь вознаграждения или связанной привычки"""
        habit = Habit(
            user=self.user,
            place="Дом",
            time=time(22, 0),
            action="Ванна",
            is_pleasant=True,
            reward="Свеча",
            periodicity=1,
            duration=60,
        )
        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_periodicity_between_1_and_7(self):
        """Периодичность должна быть от 1 до 7 дней"""
        habit = Habit(user=self.user, place="Дом", time=time(7, 0), action="Медитация", periodicity=8, duration=30)
        with self.assertRaises(ValidationError):
            habit.full_clean()

        habit.periodicity = 0
        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_str_method(self):
        """Проверка строкового представления привычки"""
        habit = Habit.objects.create(
            user=self.user, place="Парк", time=time(10, 30), action="Йога", duration=60, periodicity=1
        )
        expected_str = f"{self.user}: Йога в 10:30:00 - Парк"
        self.assertEqual(str(habit), expected_str)


class TelegramProfileModelTest(TestCase):
    """Тесты для модели TelegramProfile"""

    def setUp(self):
        self.user = User.objects.create_user(username="tguser", password="pass")

    def test_create_telegram_profile(self):
        """Успешное создание профиля с уникальным chat_id"""
        profile = TelegramProfile.objects.create(user=self.user, telegram_chat_id="123456789")
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.telegram_chat_id, "123456789")
        self.assertEqual(str(profile), "tguser's Telegram Profile")

    def test_telegram_chat_id_unique(self):
        """Поле telegram_chat_id должно быть уникальным"""
        TelegramProfile.objects.create(user=self.user, telegram_chat_id="123")
        user2 = User.objects.create_user(username="user2", password="pass")
        profile2 = TelegramProfile(user=user2, telegram_chat_id="123")
        with self.assertRaises(Exception):
            profile2.save()


class HabitAPITestCase(APITestCase):
    """Тесты API для привычек (CRUD, права доступа, пагинация)"""

    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="alicepass")
        self.other_user = User.objects.create_user(username="bob", password="bobpass")
        self.client = APIClient()

        response = self.client.post(reverse("jwt-create"), {"username": "alice", "password": "alicepass"})
        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.pleasant = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(21, 0),
            action="Чтение",
            is_pleasant=True,
            duration=60,
            periodicity=1,
        )

        self.habit = Habit.objects.create(
            user=self.user,
            place="Офис",
            time=time(14, 0),
            action="Разминка",
            duration=90,
            periodicity=2,
            is_public=False,
            reward="Смузи",
        )

        self.public_habit = Habit.objects.create(
            user=self.other_user,
            place="Парк",
            time=time(8, 0),
            action="Бег",
            duration=100,
            periodicity=1,
            is_public=True,
        )

        self.other_private = Habit.objects.create(
            user=self.other_user,
            place="Дом",
            time=time(19, 0),
            action="Ужин",
            duration=30,
            periodicity=1,
            is_public=False,
        )

    def test_list_habits_authenticated(self):
        """Аутентифицированный пользователь видит только свои привычки"""
        url = reverse("habit-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        habits = response.data["results"]
        self.assertEqual(len(habits), 2)
        habit_ids = [h["id"] for h in habits]
        self.assertIn(self.pleasant.id, habit_ids)
        self.assertIn(self.habit.id, habit_ids)
        self.assertNotIn(self.public_habit.id, habit_ids)

    def test_list_habits_unauthenticated(self):
        """Неаутентифицированный пользователь получает 401"""
        self.client.credentials()
        url = reverse("habit-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_habits_list(self):
        """Список публичных привычек доступен аутентифицированным пользователям"""
        url = reverse("public-habit-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        habits = response.data["results"]
        self.assertEqual(len(habits), 1)
        self.assertEqual(habits[0]["id"], self.public_habit.id)

    def test_public_habits_unauthenticated(self):
        """Неаутентифицированный пользователь не может видеть публичные привычки (permission IsAuthenticated)"""
        self.client.credentials()
        url = reverse("public-habit-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_habit(self):
        """Успешное создание полезной привычки с вознаграждением"""
        url = reverse("habit-list")
        data = {
            "place": "Кухня",
            "time": "08:00:00",
            "action": "Завтрак",
            "is_pleasant": False,
            "periodicity": 1,
            "duration": 60,
            "reward": "Вкусный кофе",
            "is_public": True,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Habit.objects.count(), 5)
        new_habit = Habit.objects.get(id=response.data["id"])
        self.assertEqual(new_habit.user, self.user)
        self.assertEqual(new_habit.action, "Завтрак")

    def test_create_habit_with_related_pleasant(self):
        """Создание полезной привычки, связанной с приятной"""
        url = reverse("habit-list")
        data = {
            "place": "Спальня",
            "time": "22:00:00",
            "action": "Планирование дня",
            "is_pleasant": False,
            "related_habit": self.pleasant.id,
            "periodicity": 1,
            "duration": 45,
            "is_public": False,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        habit = Habit.objects.get(id=response.data["id"])
        self.assertEqual(habit.related_habit, self.pleasant)

    def test_create_habit_validation_error(self):
        """Попытка создать привычку с нарушением валидации (reward + related_habit)"""
        url = reverse("habit-list")
        data = {
            "place": "Ванная",
            "time": "20:00:00",
            "action": "Уход за кожей",
            "is_pleasant": False,
            "related_habit": self.pleasant.id,
            "reward": "Маска",
            "periodicity": 1,
            "duration": 50,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_retrieve_own_habit(self):
        """Пользователь может получить свою привычку"""
        url = reverse("habit-detail", args=[self.habit.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.habit.id)

    def test_retrieve_other_user_habit_forbidden(self):
        """Пользователь не может получить чужую приватную привычку"""
        url = reverse("habit-detail", args=[self.other_private.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_own_habit(self):
        """Пользователь может обновить свою привычку"""
        url = reverse("habit-detail", args=[self.habit.id])
        data = {"action": "Интенсивная разминка", "duration": 70}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.habit.refresh_from_db()
        self.assertEqual(self.habit.action, "Интенсивная разминка")

    def test_update_other_user_habit_forbidden(self):
        """Пользователь не может редактировать чужую привычку"""
        url = reverse("habit-detail", args=[self.other_private.id])
        data = {"action": "Хакнул"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_habit(self):
        """Пользователь может удалить свою привычку"""
        url = reverse("habit-detail", args=[self.habit.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Habit.objects.filter(id=self.habit.id).exists())

    def test_delete_other_user_habit_forbidden(self):
        """Пользователь не может удалить чужую привычку"""
        url = reverse("habit-detail", args=[self.other_private.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pagination(self):
        """Проверка, что пагинация возвращает по 5 объектов на страницу"""

        for i in range(4):
            Habit.objects.create(
                user=self.user, place=f"Place {i}", time=time(12, 0), action=f"Action {i}", duration=60, periodicity=1
            )

        url = reverse("habit-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIsNotNone(response.data["next"])

        response = self.client.get(url, {"page": 2})
        self.assertEqual(len(response.data["results"]), 1)


class JWTAuthenticationTest(APITestCase):
    """Тесты аутентификации через JWT (регистрация, получение токена)"""

    def test_user_registration(self):
        """Успешная регистрация нового пользователя"""
        url = reverse("user-list")
        data = {"username": "newuser", "password": "Str0ngP@ssw0rd"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_jwt_token_obtain(self):
        """Получение JWT токена по логину/паролю"""
        User.objects.create_user(username="test", password="testpass")
        url = reverse("jwt-create")
        data = {"username": "test", "password": "testpass"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_jwt_token_refresh(self):
        """Обновление токена по refresh"""
        user = User.objects.create_user(username="test", password="testpass")

        url_create = reverse("jwt-create")
        response = self.client.post(url_create, {"username": "test", "password": "testpass"})
        refresh = response.data["refresh"]

        url_refresh = reverse("jwt-refresh")
        response = self.client.post(url_refresh, {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_access_protected_endpoint_without_token(self):
        """Доступ к защищённому эндпоинту без токена возвращает 401"""
        url = reverse("habit-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HabitSerializerTest(APITestCase):
    """Тесты сериализатора HabitSerializer (валидация, создание)"""

    def setUp(self):
        self.user = User.objects.create_user(username="serializer_test", password="pass")
        self.pleasant = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Пить воду",
            is_pleasant=True,
            periodicity=1,
            duration=10,
        )
        self.valid_data = {
            "place": "Парк",
            "time": "08:00:00",
            "action": "Бег",
            "is_pleasant": False,
            "periodicity": 1,
            "duration": 90,
            "reward": "Смузи",
            "is_public": False,
        }

    def test_serializer_valid_data(self):
        """Сериализатор принимает корректные данные"""
        serializer = HabitSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["action"], "Бег")

    def test_serializer_reward_and_related_habit_mutually_exclusive(self):
        """Ошибка при одновременном указании reward и related_habit"""
        data = self.valid_data.copy()
        data["related_habit"] = self.pleasant.id
        serializer = HabitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
        self.assertIn("Нельзя одновременно указать вознаграждение", str(serializer.errors))

    def test_serializer_duration_exceeds_120(self):
        """Ошибка, если duration > 120"""
        data = self.valid_data.copy()
        data["duration"] = 150
        serializer = HabitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Время выполнения должно быть не более 120 секунд", str(serializer.errors))

    def test_serializer_related_habit_must_be_pleasant(self):
        """Ошибка, если связанная привычка не является приятной"""
        non_pleasant = Habit.objects.create(
            user=self.user,
            place="Работа",
            time=time(12, 0),
            action="Совещание",
            is_pleasant=False,
            periodicity=1,
            duration=30,
        )
        data = self.valid_data.copy()
        data.pop("reward")
        data["related_habit"] = non_pleasant.id
        serializer = HabitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Связанная привычка должна быть приятной", str(serializer.errors))

    def test_serializer_pleasant_habit_cannot_have_reward_or_related(self):
        """Приятная привычка не может иметь reward или related_habit"""
        data = {
            "place": "Ванная",
            "time": "21:00:00",
            "action": "Ванна",
            "is_pleasant": True,
            "periodicity": 1,
            "duration": 60,
            "reward": "Пена",
        }
        serializer = HabitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("У приятной привычки не может быть вознаграждения", str(serializer.errors))

        data.pop("reward")
        data["related_habit"] = self.pleasant.id
        serializer = HabitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("У приятной привычки не может быть вознаграждения", str(serializer.errors))

    def test_serializer_periodicity_out_of_range(self):
        """Периодичность должна быть 1-7"""
        data = self.valid_data.copy()
        data["periodicity"] = 8
        serializer = HabitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Периодичность должна быть от 1 до 7 дней", str(serializer.errors))

        data["periodicity"] = 0
        serializer = HabitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Периодичность должна быть от 1 до 7 дней", str(serializer.errors))


class CeleryTaskTest(TestCase):
    """Тесты для Celery-задачи send_habit_reminders"""

    def setUp(self):
        self.user = User.objects.create_user(username="celeryuser", password="pass")
        self.profile = TelegramProfile.objects.create(user=self.user, telegram_chat_id="123456")
        now = timezone.localtime(timezone.now())
        self.habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=now.time(),
            action="Сделать зарядку",
            is_pleasant=False,
            periodicity=1,
            duration=60,
            reward="Кофе",
        )
        self.pleasant = Habit.objects.create(
            user=self.user, place="Дом", time=now.time(), action="Чтение", is_pleasant=True, periodicity=1, duration=30
        )
        self.user2 = User.objects.create_user(username="noprofile", password="pass")
        self.habit_no_profile = Habit.objects.create(
            user=self.user2,
            place="Улица",
            time=now.time(),
            action="Пробежка",
            is_pleasant=False,
            periodicity=1,
            duration=50,
        )

    @patch("habits.tasks.Bot")
    def test_send_habit_reminders_sends_message(self, mock_bot_class):
        """Задача отправляет сообщение пользователю с привязанным Telegram"""
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot

        send_habit_reminders()

        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        self.assertEqual(kwargs["chat_id"], "123456")
        self.assertIn("Сделать зарядку", kwargs["text"])
        self.assertIn("Кофе", kwargs["text"])

    @patch("habits.tasks.Bot")
    def test_send_habit_reminders_no_habits_in_window(self, mock_bot_class):
        """Если привычек с нужным временем нет, сообщения не отправляются"""
        past_time = (timezone.localtime(timezone.now()) - timezone.timedelta(minutes=10)).time()
        self.habit.time = past_time
        self.habit.save()

        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot

        send_habit_reminders()

        mock_bot.send_message.assert_not_called()

    @patch("habits.tasks.Bot")
    def test_send_habit_reminders_handles_bot_exception(self, mock_bot_class):
        """Исключение при отправке не прерывает задачу, ошибка логируется"""
        mock_bot = MagicMock()
        mock_bot.send_message.side_effect = Exception("Telegram API error")
        mock_bot_class.return_value = mock_bot

        try:
            send_habit_reminders()
        except Exception:
            self.fail("send_habit_reminders raised Exception unexpectedly")

        mock_bot.send_message.assert_called_once()

    @patch("habits.tasks.Bot")
    def test_send_habit_reminders_no_reward_fallback(self, mock_bot_class):
        """Если reward отсутствует, в сообщении пишется 'Приятная привычка'."""
        self.habit.reward = None
        self.habit.save()

        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot

        send_habit_reminders()

        mock_bot.send_message.assert_called_once()
        _, kwargs = mock_bot.send_message.call_args
        self.assertIn("Приятная привычка", kwargs["text"])
