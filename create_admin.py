#!/usr/bin/env python
"""Скрипт для заполнения базы данных начальными данными"""
import os
import sys
import time
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shelter_project.settings')
django.setup()

from django.db import connection
from accounts.models import User, Role, UserProfile
from accounts.utils import hash_password_sha256, normalize_phone

# =========================================================
# ДАННЫЕ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
# =========================================================

USERS_DATA = [
    {
        'email': 'admin@test.com',
        'password': 'admin123',
        'first_name': 'Админ',
        'last_name': 'Тестовый',
        'phone': '+79999999999',
        'role': 'Admin'
    },
    {
        'email': 'manager@test.com',
        'password': 'manager123',
        'first_name': 'Иван',
        'last_name': 'Менеджеров',
        'phone': '+79999999998',
        'role': 'Manager'
    },
    {
        'email': 'guest@test.com',
        'password': 'guest123',
        'first_name': 'Петр',
        'last_name': 'Гостевой',
        'phone': '+79999999997',
        'role': 'Guest'
    }
]

# =========================================================
# ДАННЫЕ ДЛЯ СПРАВОЧНИКОВ (RAW SQL)
# =========================================================

def execute_raw_sql(sql):
    """Выполняет сырой SQL-запрос"""
    with connection.cursor() as cursor:
        cursor.execute(sql)

def seed_dictionaries():
    """Заполняет справочные таблицы начальными данными"""
    
    # 1. Статусы животных
    execute_raw_sql("""
        INSERT INTO animalstatuses (statusname) VALUES 
        ('Доступен'), ('Пристроен'), ('На рассмотрении')
        ON CONFLICT (statusname) DO NOTHING;
    """)
    print('[OK] Статусы животных добавлены')
    
    # 2. Статусы заявок
    execute_raw_sql("""
        INSERT INTO applicationstatuses (statusname) VALUES 
        ('Pending'), ('Approved'), ('Rejected')
        ON CONFLICT (statusname) DO NOTHING;
    """)
    print('[OK] Статусы заявок добавлены')
    
    # 3. Статусы встреч
    execute_raw_sql("""
        INSERT INTO meetingstatuses (statusname) VALUES 
        ('Scheduled'), ('InProgress'), ('Completed'), ('Cancelled'), ('NoShow')
        ON CONFLICT (statusname) DO NOTHING;
    """)
    print('[OK] Статусы встреч добавлены')
    
    # 4. Типы животных
    execute_raw_sql("""
        INSERT INTO animaltypes (typename) VALUES 
        ('Собака'), ('Кошка'), ('Птица'), ('Грызун'), ('Кролик'), ('Рептилия')
        ON CONFLICT (typename) DO NOTHING;
    """)
    print('[OK] Типы животных добавлены')
    
    # 5. Характеры животных
    execute_raw_sql("""
        INSERT INTO animalcharacters (charactername, description) VALUES 
        ('Дружелюбный', 'Ладит с людьми и другими животными'),
        ('Активный', 'Любит гулять и играть'),
        ('Спокойный', 'Предпочитает тишину и покой'),
        ('Ласковый', 'Обожает внимание и ласку'),
        ('Осторожный', 'Присматривается к новым людям'),
        ('Игривый', 'Любит игрушки и развлечения'),
        ('Умный', 'Быстро обучается командам')
        ON CONFLICT (charactername) DO NOTHING;
    """)
    print('[OK] Характеры животных добавлены')
    
    # 6. Типы активностей (уход)
    execute_raw_sql("""
        INSERT INTO activitytypes (activityname, description) VALUES 
        ('Кормление', 'Регулярное кормление животного'),
        ('Выгул', 'Прогулка на свежем воздухе'),
        ('Осмотр', 'Ветеринарный осмотр'),
        ('Купание', 'Гигиенические процедуры'),
        ('Прививка', 'Плановая вакцинация'),
        ('Дрессировка', 'Занятия с кинологом')
        ON CONFLICT (activityname) DO NOTHING;
    """)
    print('[OK] Типы активностей добавлены')
    
    # 7. Типы частоты (уход)
    execute_raw_sql("""
        INSERT INTO frequencytypes (frequencyname, description) VALUES 
        ('Ежедневно', 'Каждый день'),
        ('Раз в неделю', 'Один раз в неделю'),
        ('Два раза в неделю', 'Дважды в неделю'),
        ('Ежемесячно', 'Раз в месяц'),
        ('По требованию', 'По необходимости')
        ON CONFLICT (frequencyname) DO NOTHING;
    """)
    print('[OK] Типы частоты добавлены')
    
    # 8. Типы вакцинаций
    execute_raw_sql("""
        INSERT INTO vaccinationtypes (vaccinationname, description) VALUES 
        ('Бешенство', 'Вакцинация от бешенства'),
        ('Чума плотоядных', 'Вакцинация от чумы'),
        ('Парвовирус', 'Вакцинация от парвовирусного энтерита'),
        ('Лептоспироз', 'Вакцинация от лептоспироза'),
        ('Калицивироз', 'Вакцинация от калицивироза (кошки)'),
        ('Панлейкопения', 'Вакцинация от панлейкопении (кошки)')
        ON CONFLICT (vaccinationname) DO NOTHING;
    """)
    print('[OK] Типы вакцинаций добавлены')
    
    # 9. Породы животных (примеры)
    execute_raw_sql("""
        INSERT INTO breeds (breedname, typeid) 
        SELECT breedname, typeid FROM (VALUES 
            ('Лабрадор', (SELECT typeid FROM animaltypes WHERE typename = 'Собака')),
            ('Немецкая овчарка', (SELECT typeid FROM animaltypes WHERE typename = 'Собака')),
            ('Дворняга', (SELECT typeid FROM animaltypes WHERE typename = 'Собака')),
            ('Британская', (SELECT typeid FROM animaltypes WHERE typename = 'Кошка')),
            ('Сиамская', (SELECT typeid FROM animaltypes WHERE typename = 'Кошка')),
            ('Дворовая', (SELECT typeid FROM animaltypes WHERE typename = 'Кошка'))
        ) AS b(breedname, typeid)
        WHERE NOT EXISTS (SELECT 1 FROM breeds WHERE breedname = b.breedname);
    """)
    print('[OK] Породы животных добавлены')
    
    # 10. Приюты
    execute_raw_sql("""
        INSERT INTO shelters (sheltername, address, phone, email, description, isactive) VALUES 
        ('Центральный приют', 'г. Москва, ул. Приютская, д. 1', '+74951234567', 'central@shelter.ru', 'Главный приют города', true),
        ('Приют "Доброе сердце"', 'г. Санкт-Петербург, ул. Заботливая, д. 15', '+78121234567', 'dobroe@shelter.ru', 'Приют для кошек и собак', true),
        ('Приют "Верный друг"', 'г. Новосибирск, ул. Сибирская, д. 10', '+73831234567', 'verniy@shelter.ru', 'Работаем с 2010 года', true)
        ON CONFLICT (sheltername) DO NOTHING;
    """)
    print('[OK] Приюты добавлены')

def create_users():
    """Создаёт пользователей с соответствующими ролями"""
    for user_data in USERS_DATA:
        try:
            role = Role.objects.get(role_name=user_data['role'])
        except Role.DoesNotExist:
            print(f'[ERROR] Роль {user_data["role"]} не найдена!')
            continue
        
        if User.objects.filter(email=user_data['email']).exists():
            print(f'[OK] Пользователь {user_data["email"]} уже существует')
            continue
        
        normalized_phone = normalize_phone(user_data['phone'])
        
        user = User.objects.create(
            email=user_data['email'],
            password_hash=hash_password_sha256(user_data['password']),
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            phone=normalized_phone,
            role=role,
        )
        
        UserProfile.objects.get_or_create(user=user)
        print(f'[OK] Создан пользователь: {user_data["email"]} (роль: {user_data["role"]})')

def add_test_animals():
    """Добавляет тестовых животных для демонстрации"""
    execute_raw_sql("""
        INSERT INTO animals (animalname, age, gender, vaccinated, description, statusid, breedid, characterid, shelterid)
        SELECT 
            'Бобик', 3, 'Male', true, 'Дружелюбный пёс, ищет дом', 
            (SELECT statusid FROM animalstatuses WHERE statusname = 'Доступен'),
            (SELECT breedid FROM breeds WHERE breedname = 'Лабрадор' LIMIT 1),
            (SELECT characterid FROM animalcharacters WHERE charactername = 'Дружелюбный' LIMIT 1),
            (SELECT shelterid FROM shelters LIMIT 1)
        WHERE NOT EXISTS (SELECT 1 FROM animals WHERE animalname = 'Бобик');
    """)
    
    execute_raw_sql("""
        INSERT INTO animals (animalname, age, gender, vaccinated, description, statusid, breedid, characterid, shelterid)
        SELECT 
            'Мурка', 2, 'Female', true, 'Ласковая кошечка, любит внимание',
            (SELECT statusid FROM animalstatuses WHERE statusname = 'Доступен'),
            (SELECT breedid FROM breeds WHERE breedname = 'Британская' LIMIT 1),
            (SELECT characterid FROM animalcharacters WHERE charactername = 'Ласковый' LIMIT 1),
            (SELECT shelterid FROM shelters LIMIT 1)
        WHERE NOT EXISTS (SELECT 1 FROM animals WHERE animalname = 'Мурка');
    """)
    
    execute_raw_sql("""
        INSERT INTO animals (animalname, age, gender, vaccinated, description, statusid, breedid, characterid, shelterid)
        SELECT 
            'Шарик', 5, 'Male', true, 'Верный друг, спокойный характер',
            (SELECT statusid FROM animalstatuses WHERE statusname = 'На рассмотрении'),
            (SELECT breedid FROM breeds WHERE breedname = 'Немецкая овчарка' LIMIT 1),
            (SELECT characterid FROM animalcharacters WHERE charactername = 'Спокойный' LIMIT 1),
            (SELECT shelterid FROM shelters LIMIT 1)
        WHERE NOT EXISTS (SELECT 1 FROM animals WHERE animalname = 'Шарик');
    """)
    
    print('[OK] Добавлены тестовые животные')

def main():
    print("="*60)
    print("ЗАПУСК СКРИПТА НАСТРОЙКИ БАЗЫ ДАННЫХ")
    print("="*60)
    
    # Ждём готовности базы данных
    print("\nОжидание 5 секунд...")
    time.sleep(5)
    
    # Заполняем справочники
    print("\n--- ЗАПОЛНЕНИЕ СПРАВОЧНИКОВ ---")
    seed_dictionaries()
    
    # Создаём пользователей
    print("\n--- СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ---")
    create_users()
    
    # Добавляем тестовых животных
    print("\n--- ДОБАВЛЕНИЕ ТЕСТОВЫХ ЖИВОТНЫХ ---")
    add_test_animals()
    
    # Итоговая информация
    print("\n" + "="*60)
    print("ГОТОВО! База данных заполнена:")
    print("="*60)
    print("\n👥 ПОЛЬЗОВАТЕЛИ:")
    for user in USERS_DATA:
        print(f"   {user['role']}: {user['email']} / {user['password']}")
    
    print("\n📋 СПРАВОЧНИКИ:")
    print("   ✓ Статусы животных (Доступен, Пристроен, На рассмотрении)")
    print("   ✓ Типы и породы животных")
    print("   ✓ Характеры животных")
    print("   ✓ Приюты (3 шт.)")
    print("   ✓ Типы активностей и частот")
    print("   ✓ Типы вакцинаций")
    
    print("\n🐕 ТЕСТОВЫЕ ЖИВОТНЫЕ:")
    print("   ✓ Бобик (Лабрадор, Доступен)")
    print("   ✓ Мурка (Британская, Доступен)")
    print("   ✓ Шарик (Немецкая овчарка, На рассмотрении)")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    main()
