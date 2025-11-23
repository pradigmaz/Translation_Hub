# 🌐 TranslationHub

**Система координации переводческих команд для манги, манхвы и маньхуа**

[![Django](https://img.shields.io/badge/Django-5.2.5-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.2-purple.svg)](https://getbootstrap.com/)

## Описание

Django-приложение для координации работы переводческих команд с ролевой системой доступа и аудитом действий.

**Основные возможности:**
- Управление командами с жизненным циклом (Active → Inactive → Disbanded)
- Ролевая система: Leader, Editor, Translator, Cleaner, Typesetter
- Workflow перевода: RAW → Translation/Cleaning → Typesetting → Editing → Done
- Глоссарий с категориями по типам контента
- Автоматическое управление файловой структурой

## Установка

```bash
# Клонирование и настройка окружения
git clone https://github.com/pradigmaz/Translation_Hub.git
cd translationhub
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# Установка зависимостей
pip install -r requirements.txt

# Настройка .env
cp .env.example .env
# Отредактируйте SECRET_KEY, DEBUG, ALLOWED_HOSTS

# Миграции и запуск
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Первоначальная настройка:**
```bash
python manage.py shell
>>> from teams.models import Role
>>> Role.ensure_default_roles_exist()
```

## Структура проекта

```
translationhub/
├── core/          # Django конфигурация, middleware
├── users/         # Пользователи, аутентификация, профили
├── teams/         # Команды, роли, участники, аудит
├── projects/      # Проекты, главы, workflow
├── glossary/      # База знаний (админка)
├── content/       # Аудит контента
├── utils/         # Файловая система, утилиты
├── templates/     # HTML шаблоны (Bootstrap 5.3.2)
└── static/        # CSS, JS, изображения
```

## Технологии

- Django 5.2.5, SQLite/PostgreSQL
- Bootstrap 5.3.2, Vanilla JavaScript
- Pillow, django-background-tasks

## Workflow команды

**Роли и параллельная работа:**
- **Translator** и **Cleaner** начинают работу одновременно после RAW
- **Editor** работает после Translator
- **Typesetter** работает последним (после Translator, Cleaner, Editor)
- **Leader** может выполнять любую роль + управление командой

**Статусы глав:**
```
RAW → Переводчик (параллельно) → Редактор (после Переводчика) → Клиннер → Тайпер → Релиз
```

## Разработка

**Основные команды:**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py collectstatic --noinput
```

**Тестирование:**
- `users` - модели пользователей, аватары, валидация
- `teams` - CRUD команд, роли, статусы, аудит
- `projects` - проекты, workflow, доступ
- `utils` - файловая система

## Продакшн

```bash
# .env для продакшена
SECRET_KEY=your-production-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:pass@localhost/db

# Развертывание
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

**Рекомендации:** Nginx + Gunicorn, PostgreSQL 12+, Redis (опционально)

## Статус разработки

**Реализовано:**
- ✅ Пользователи с аватарами
- ✅ Команды с жизненным циклом и аудитом
- ✅ Ролевая система с правами доступа
- ✅ Проекты (Manga/Manhwa/Manhua) с workflow
- ✅ Глоссарий с категориями (админка)
- ✅ Файловая система с автоуправлением
- ✅ Логирование и middleware безопасности
- ✅ Поиск участников команды
- ✅ Управление ролями участников
- ✅ Модальные окна для удаления участников
- ✅ Компонентная архитектура views
- ✅ Мониторинг файловых операций

**В разработке:**
- 🚧 Kanban-доска для глав
- 🚧 Система назначения задач
- 🚧 Файловый менеджер для RAW
- 🚧 Telegram бот (заглушка готова)

## Лицензия

Проект для внутреннего использования переводческими командами.
