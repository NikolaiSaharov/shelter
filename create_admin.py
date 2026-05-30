#!/usr/bin/env python
"""Скрипт для создания администратора"""
import os
import sys
import time
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shelter_project.settings')
django.setup()

from django.db import connection
from django.db.utils import ProgrammingError
from accounts.models import User, Role, UserProfile
from accounts.utils import hash_password_sha256, normalize_phone

EMAIL = "admin@test.com"
PASSWORD = "admin123"
FIRST_NAME = "Админ"
LAST_NAME = "Тестовый"
PHONE = "+79999999999"

def wait_for_database(max_retries=15, delay=2):
    """Ожидание готовности базы данных и таблиц"""
    print("Ожидание готовности базы данных...")
    
    for attempt in range(max_retries):
        try:
            # Проверяем, существует ли таблица roles
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'accounts_role'
                    )
                """)
                exists = cursor.fetchone()[0]
                
                if exists:
                    print(f"[OK] База данных готова (таблица accounts_role найдена)")
                    return True
                else:
                    print(f"Попытка {attempt + 1}/{max_retries}: Таблицы ещё не созданы, ждём {delay} секунд...")
                    time.sleep(delay)
        except ProgrammingError as e:
            print(f"Попытка {attempt + 1}/{max_retries}: Ошибка подключения: {e}")
            time.sleep(delay)
        except Exception as e:
            print(f"Попытка {attempt + 1}/{max_retries}: Неизвестная ошибка: {e}")
            time.sleep(delay)
    
    print("[ERROR] База данных не готова после ожидания")
    return False

def create_admin():
    # Ждём готовности базы данных
    if not wait_for_database():
        print("[ERROR] Прерывание выполнения скрипта")
        return
    
    try:
        admin_role, created = Role.objects.get_or_create(
            role_name='Admin',
            defaults={'role_name': 'Admin'}
        )
        
        if created:
            print(f'[OK] Роль "Admin" создана (ID: {admin_role.role_id})')
        else:
            print(f'[OK] Роль "Admin" найдена (ID: {admin_role.role_id})')
        
        if User.objects.filter(email=EMAIL).exists():
            print(f'[WARNING] Пользователь с email "{EMAIL}" уже существует!')
            user = User.objects.get(email=EMAIL)
            print(f'\nДанные существующего пользователя:')
            print(f'  Email: {user.email}')
            print(f'  Имя: {user.first_name} {user.last_name}')
            print(f'  Роль: {user.role.role_name if user.role else "Нет роли"}')
            print(f'  ID: {user.user_id}')
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
        print('\nДАННЫЕ ДЛЯ ВХОДА:')
        print(f'   Email: {user.email}')
        print(f'   Пароль: {PASSWORD}')
        print(f'   Телефон: {normalized_phone}')
        print('\nИНФОРМАЦИЯ:')
        print(f'   Имя: {user.first_name} {user.last_name}')
        print(f'   Роль: {user.role.role_name}')
        print(f'   ID: {user.user_id}')
        print('\n' + '='*60)
        
    except Exception as e:
        print(f'[ERROR] Ошибка при создании пользователя: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    create_admin()
