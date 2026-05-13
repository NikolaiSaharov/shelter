#!/bin/bash
set -e

echo "Ожидание готовности базы данных..."
python << END
import os
import time
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shelter_project.settings')

import django
django.setup()

from django.db import connection

max_attempts = 30
for i in range(max_attempts):
    try:
        connection.ensure_connection()
        print("База данных готова!")
        break
    except Exception as e:
        if i == max_attempts - 1:
            print(f"Не удалось подключиться к БД: {e}")
            sys.exit(1)
        print(f"Попытка подключения {i+1}/{max_attempts}...")
        time.sleep(2)
END

echo "Применение миграций..."
python manage.py migrate --noinput

echo "Сбор статических файлов..."
python manage.py collectstatic --noinput

echo "Запуск сервера..."
exec "$@"

