# Atomic Habit Tracker

Бэкенд-часть SPA-приложения для отслеживания полезных привычек, вдохновлённая книгой Джеймса Клира «Атомные привычки». Проект предоставляет REST API для создания, редактирования и отслеживания привычек с интеграцией Telegram для напоминаний.

## Технологический стек

- **Python 3.14**
- **Django 6.0.4** + Django REST Framework
- **PostgreSQL / SQLite** (по умолчанию SQLite)
- **Celery** + **Redis** (брокер)
- **django-celery-beat** (периодические задачи)
- **python-telegram-bot** (интеграция с Telegram)
- **djoser + Simple JWT** (аутентификация)
- **drf-spectacular** (автодокументация OpenAPI)
- **django-cors-headers** (CORS)
- **pytest / coverage** (тестирование)

## Функциональные возможности

- Регистрация и аутентификация пользователей по JWT
- Создание, редактирование, удаление привычек
- Валидация в соответствии с концепцией «Атомных привычек»:
  - нельзя одновременно указать вознаграждение и связанную привычку
  - время выполнения ≤ 120 секунд
  - связанная привычка должна быть приятной
  - у приятной привычки нет вознаграждения и связанной привычки
  - периодичность от 1 до 7 дней
- Список личных привычек с пагинацией (5 на страницу)
- Просмотр публичных привычек других пользователей
- Интеграция с Telegram: привязка аккаунта и ежедневные напоминания
- Отложенная рассылка уведомлений через Celery
- Автоматическая документация API (Swagger/ReDoc)
- CORS для взаимодействия с фронтендом

## Установка и запуск

### 1. Клонирование репозитория

```
git clone <repository-url>
cd atomic_habit_tracker
```

### 2. Создание виртуального окружения и установка зависимостей
```
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 3. Настройка переменных окружения
#### Создайте файл .env в корне проекта по образцу .env.sample
*```TELEGRAM_BOT_TOKEN``` получите у @BotFather.*

### 4. Применение миграций
```commandline
python manage.py migrate
```

### 5.  Создание суперпользователя
```commandline
python manage.py createsuperuser
```

### 6. Запуск сервера разработки
```commandline
python manage.py runserver
```

### *Запуск дополнительных сервисов*
*Для работы напоминаний необходимы Redis, Celery Worker, Celery Beat и Telegram-бот.*

- Redis (Windows)

Скачайте и установите Redis для Windows с Microsoft Archive. После установки Redis работает как служба. Проверьте:
```commandline
redis-cli ping
# PONG
```
- Celery Worker
```commandline
celery -A config worker -l info --pool=solo
```
- Telegram-бот
```commandline
python manage.py bot
```

## Настройка периодической задачи
1. Войдите в админ-панель Django (```/admin```).
2. Перейдите в раздел Periodic Tasks (```django_celery_beat```).
3. Создайте новую задачу:
- Name: Рассылка уведомлений о привычках
- Task: ```habits.tasks.send_habit_reminders```
- Interval: every 1 minute (или создайте свой интервал)
4. Сохраните.

***Теперь каждую минуту Celery Beat будет запускать проверку привычек и отправлять уведомления в Telegram.***

## Документация API
### После запуска сервера доступны:

- Swagger UI: http://127.0.0.1:8000/api/schema/swagger/
- ReDoc: http://127.0.0.1:8000/api/schema/redoc/
- Схема OpenAPI JSON: http://127.0.0.1:8000/api/schema/

***Для авторизации в Swagger UI используйте кнопку Authorize и введите Bearer ```<access_token>```.***

## Тестирование
#### Проект покрыт юнит-тестами с использованием ```pytest``` и ```coverage```. Для запуска тестов выполните:
```
coverage run --source='.' manage.py test habits
coverage report -m
```

#### Текущее покрытие составляет 93%. Подробный HTML‑отчёт:

```commandline
coverage html
```

###### Проект выполнен в рамках курсовой работы. Все права защищены 😊
