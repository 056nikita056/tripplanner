# TripPlanner (Django MVP)

Сервис для планирования поездок: поездки, активности/расходы, список вещей и аналитика по бюджету.

## Стек
- Django 5
- SQLite (локально)
- requests + Open‑Meteo (погода)
- Chart.js (диаграммы)
- Bootstrap 5

## Функции MVP
- Регистрация/вход
- CRUD поездок (редактирует только автор)
- CRUD активностей (расходы) + теги
- Список вещей: библиотека предметов + добавление в поездку
- Аналитика: сумма расходов, остаток бюджета, диаграммы по дням и тегам

## Запуск локально
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# env
cp .env.example .env

python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

После `seed_demo`:
- user: `demo`
- password: `demo12345`

## Деплой на PythonAnywhere
1. Создать venv и установить зависимости из `requirements.txt`.
2. В разделе Web указать WSGI из проекта Django.
3. Выставить переменные окружения:
   - `DJANGO_SECRET_KEY`
   - `DJANGO_DEBUG=False`
   - `DJANGO_ALLOWED_HOSTS=ваш_домен`
4. Настроить Static files:
   - URL: `/static/` → Directory: `.../staticfiles`
   - выполнить `python manage.py collectstatic`

## Скриншоты
Добавь 2–3 скрина: список поездок, карточка поездки с диаграммами, список вещей.
