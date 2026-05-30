#!/usr/bin/env python
"""Скрипт для создания всех ролей и администратора"""
import os
import sys
import time
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shelter_project.settings')
django.setup()

from accounts.models import User, Role, UserProfile
from accounts.utils import hash_password_sha256, normalize_phone

# Данные для администратора
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"
ADMIN_FIRST_NAME = "Админ"
ADMIN_LAST_NAME = "Тестовый"
ADMIN_PHONE = "+79999999999"

# Данные для тестового гостя
GUEST_EMAIL = "guest@test.com"
GUEST_PASSWORD = "guest123"
GUEST_FIRST_NAME = "Тестовый"
GUEST_LAST_NAME = "Гость"
GUEST_PHONE = "+79999999998"

def create_roles():
    """Создаёт все необходимые роли"""
    roles_data = [
        {'name': 'Admin', 'description': 'Полный доступ ко всем функциям'},
        {'name': 'Manager', 'description': 'Управление животными и заявками'},
        {'name': 'Guest', 'description': 'Гостевой доступ (ограниченные права)'}
    ]
    
    for role_info in roles_data:
        role, created = Role.objects.get_or_create(
            role_name=role_info['name'],
            defaults={'role_name': role_info['name']}
        )
        if created:
            print(f'[OK] Роль "{role_info["name"]}" создана')
        else:
            print(f'[OK] Роль "{role_info["name"]}" уже существует')

def create_admin():
    """Создаёт администратора"""
    try:
        admin_role = Role.objects.get(role_name='Admin')
    except Role.DoesNotExist:
        print('[ERROR] Роль Admin не найдена!')
        return False
    
    if User.objects.filter(email=ADMIN_EMAIL).exists():
        print(f'[OK] Администратор {ADMIN_EMAIL} уже существует')
        return True
    
    normalized_phone = normalize_phone(ADMIN_PHONE)
    
    user = User.objects.create(
        email=ADMIN_EMAIL,
        password_hash=hash_password_sha256(ADMIN_PASSWORD),
        first_name=ADMIN_FIRST_NAME,
        last_name=ADMIN_LAST_NAME,
        phone=normalized_phone,
        role=admin_role,
    )
    
    UserProfile.objects.get_or_create(user=user)
    
    print(f'[OK] Администратор создан: {ADMIN_EMAIL}')
    return True

def create_guest():
    """Создаёт тестового гостя"""
    try:
        guest_role = Role.objects.get(role_name='Guest')
    except Role.DoesNotExist:
        print('[WARNING] Роль Guest не найдена, тестовый гость не создан')
        return False
    
    if User.objects.filter(email=GUEST_EMAIL).exists():
        print(f'[OK] Гость {GUEST_EMAIL} уже существует')
        return True
    
    normalized_phone = normalize_phone(GUEST_PHONE)
    
    user = User.objects.create(
        email=GUEST_EMAIL,
        password_hash=hash_password_sha256(GUEST_PASSWORD),
        first_name=GUEST_FIRST_NAME,
        last_name=GUEST_LAST_NAME,
        phone=normalized_phone,
        role=guest_role,
    )
    
    UserProfile.objects.get_or_create(user=user)
    
    print(f'[OK] Тестовый гость создан: {GUEST_EMAIL}')
    return True

def main():
    print("="*60)
    print("ЗАПУСК СКРИПТА НАСТРОЙКИ РОЛЕЙ И ПОЛЬЗОВАТЕЛЕЙ")
    print("="*60)
    
    # Ждём готовности базы данных
    print("\nОжидание 5 секунд для гарантии готовности БД...")
    time.sleep(5)
    
    # Создаём роли
    print("\n--- СОЗДАНИЕ РОЛЕЙ ---")
    create_roles()
    
    # Создаём администратора
    print("\n--- СОЗДАНИЕ АДМИНИСТРАТОРА ---")
    create_admin()
    
    # Создаём гостя
    print("\n--- СОЗДАНИЕ ТЕСТОВОГО ГОСТЯ ---")
    create_guest()
    
    # Итоговая информация
    print("\n" + "="*60)
    print("ГОТОВО! Все данные для входа:")
    print("="*60)
    print("\n👑 Администратор (полный доступ):")
    print(f"   Email: {ADMIN_EMAIL}")
    print(f"   Пароль: {ADMIN_PASSWORD}")
    print("\n👤 Гость (ограниченный доступ):")
    print(f"   Email: {GUEST_EMAIL}")
    print(f"   Пароль: {GUEST_PASSWORD}")
    print("\n📋 Роли в системе: Admin, Manager, Guest")
    print("="*60)

if __name__ == '__main__':
    main()
