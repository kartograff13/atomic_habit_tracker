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
- **Docker + Docker Compose** (контейнеризация)
- **GitHub Actions** (CI/CD)

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

## 1. Локальный запуск (для разработки)

### 1.1 Клонирование репозитория

```
git clone <repository-url>
cd atomic_habit_tracker
```

### 1.2 Виртуальное окружение и установка зависимостей
```
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### 1.3 Настройка переменных окружения
#### Создайте файл .env в корне проекта по образцу .env.sample
```commandline
SECRET_KEY=ваш_секретный_ключ
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

TELEGRAM_BOT_TOKEN=токен_вашего_бота

POSTGRES_DB=atomic_tracker
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```
*Для локальной разработки с ```SQLite``` (без ```PostgreSQL```) достаточно заполнить ```SECRET_KEY```, ```DEBUG```, ```TELEGRAM_BOT_TOKEN```. База данных по умолчанию ```SQLite```.*
*```TELEGRAM_BOT_TOKEN``` получите у @BotFather.*

### 1.4 Применение миграций и создание суперпользователя
```
python manage.py migrate
python manage.py createsuperuser
```

### 1.5 Запуск необходимых сервисов
Для полноценной работы (напоминания через ```Celery```) потребуются ```Redis```, ```Celery Worker```, ```Celery Beat``` и Telegram-бот.
Проверка Redis:
```commandline
redis-cli ping
# PONG
```
Celery Worker:
```commandline
celery -A config worker -l info --pool=solo   # для Windows
```
Celery Beat:
```commandline
celery -A config beat -l info
```
Telegram-бот:
```commandline
python manage.py bot
```

### 6. Запуск сервера разработки
```commandline
python manage.py runserver
```
Приложение будет доступно по адресу http://127.0.0.1:8000/.

## 2. Локальный запуск через Docker Compose (полная сборка)
Для запуска со всеми сервисами (Django, PostgreSQL, Redis, Celery, Nginx) можно использовать Docker Compose.
#### 2.1 Предварительные требования
**Установите ```Docker``` и ```Docker Compose```.**

#### 2.2 Настройка окружения
Создайте файл ```.env``` в корне проекта, аналогично разделу 1.3, но с настройками для контейнеров (```PostgreSQL``` и ```Redis``` будут использоваться из контейнеров). Убедитесь, что там присутствуют переменные:
```commandline
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```
#### 2.3 Сборка и запуск
```commandline
docker compose up -d --build
```

#### 2.4 Миграции и суперпользователь
```commandline
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```
****Сайт будет доступен через Nginx на порту 80: http://localhost/.****

## 3. Настройка периодической задачи
1. Войдите в админ-панель Django (```/admin```).
2. Перейдите в раздел Periodic Tasks (```django_celery_beat```).
3. Создайте новую задачу:
- Name: Рассылка уведомлений о привычках
- Task: ```habits.tasks.send_habit_reminders```
- Interval: создайте новый интервал every 1 minute (или настройте подходящую периодичность)
4. Сохраните.

***Теперь каждую минуту Celery Beat будет запускать проверку привычек и отправлять уведомления в Telegram.***

## 4. Документация API
### После запуска сервера доступны:

- Swagger UI: http://127.0.0.1:8000/api/schema/swagger/
- ReDoc: http://127.0.0.1:8000/api/schema/redoc/
- Схема OpenAPI JSON: http://127.0.0.1:8000/api/schema/

***Для авторизации в Swagger UI используйте кнопку Authorize и введите Bearer ```<access_token>```.***

## 5. Тестирование
#### Проект покрыт юнит-тестами с использованием ```pytest``` и ```coverage```. Для запуска тестов выполните:
```
coverage run --source='.' manage.py test habits
coverage report -m
```

#### Текущее покрытие составляет 93%. Подробный HTML‑отчёт:

```commandline
coverage html
```

## 6. CI/CD и деплой на сервер
В репозитории настроен **GitHub Actions** для автоматического тестирования, сборки Docker-образа и деплоя на VPS.
Pipeline определён в ```.github/workflows/ci-cd.yml```.

#### 6.1 Структура пайплайна
- ***test-and-lint***: запуск тестов и проверка стиля кода (flake8).
- ***build-docker***: сборка Docker-образа и пуш в GitHub Container Registry (ghcr.io).
- ***deploy***: подключение по SSH к серверу, обновление кода и перезапуск контейнеров.

#### 6.2 Настройка секретов
Для работы деплоя необходимо добавить следующие секреты в репозиторий → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Проверьте подключение:
```commandline
ssh -i ~/.ssh/deploy_key user@your-server
```

#### 6.3 Автоматический деплой
После настройки секретов и сервера, пуш в ветку ```main``` (или мерж PR в ```main```) автоматически запустит пайплайн.
В случае успеха ваше приложение станет доступно по адресу http://ваш_сервер/.


###### Проект выполнен в рамках курсовой работы. Все права защищены 😊
