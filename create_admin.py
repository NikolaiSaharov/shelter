#!/usr/bin/env python
"""Скрипт для создания администратора"""
import os
import sys
import time
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shelter_project.settings')
django.setup()

from django.db.utils import ProgrammingError
from accounts.models import User, Role, UserProfile
from accounts.utils import hash_password_sha256, normalize_phone

EMAIL = "admin@test.com"
PASSWORD = "admin123"
FIRST_NAME = "Админ"
LAST_NAME = "Тестовый"
PHONE = "+79999999999"

def create_admin_with_retry(max_retries=30, delay=3):
    """Создаёт админа с повторными попытками"""
    print("Запуск скрипта создания администратора...")
    
    for attempt in range(max_retries):
        try:
            # Пробуем получить или создать роль
            admin_role, created = Role.objects.get_or_create(
                role_name='Admin',
                defaults={'role_name': 'Admin'}
            )
            
            if created:
                print(f'[OK] Роль "Admin" создана')
            else:
                print(f'[OK] Роль "Admin" найдена')
            
            # Пробуем создать пользователя
            if User.objects.filter(email=EMAIL).exists():
                print(f'[OK] Пользователь {EMAIL} уже существует')
                return
            
            normalized_phone = normalize_phone(PHONE)
            
            user = User.objects.create(
                email=EMAIL,
                password_hash=hash_password_sha256(PASSWORD),
                first_name=FIRST_NAME,
                last_name=LAST_NAME,
                phone=normalized_phone,
                role=admin_role,
            )
            
            UserProfile.objects.get_or_create(user=user)
            
            print('\n' + '='*60)
            print('[SUCCESS] АДМИНИСТРАТОР УСПЕШНО СОЗДАН!')
            print('='*60)
            print(f'   Email: {user.email}')
            print(f'   Пароль: {PASSWORD}')
            print('\n' + '='*60)
            return
            
        except ProgrammingError as e:
            if 'relation' in str(e).lower():
                print(f"Попытка {attempt + 1}/{max_retries}: Таблицы ещё не готовы, ждём {delay} секунд...")
                time.sleep(delay)
            else:
                print(f"Ошибка: {e}")
                break
        except Exception as e:
            print(f"Попытка {attempt + 1}/{max_retries}: Ошибка - {e}, ждём {delay} секунд...")
            time.sleep(delay)
    
    print("[ERROR] Не удалось создать администратора")

if __name__ == '__main__':
    create_admin_with_retry()
