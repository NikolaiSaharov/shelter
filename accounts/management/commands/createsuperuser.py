from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User, Role, UserProfile
from accounts.utils import hash_password_sha256, normalize_phone
import getpass


class Command(BaseCommand):
    help = 'Создаёт суперпользователя (администратора) для системы'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email администратора',
        )
        parser.add_argument(
            '--first-name',
            type=str,
            help='Имя администратора',
        )
        parser.add_argument(
            '--last-name',
            type=str,
            help='Фамилия администратора',
        )
        parser.add_argument(
            '--phone',
            type=str,
            help='Телефон администратора',
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Не запрашивать данные интерактивно (используйте с --email и --password)',
        )

    def handle(self, *args, **options):
        # Получаем или создаём роль Admin
        admin_role, created = Role.objects.get_or_create(
            role_name='Admin',
            defaults={'role_name': 'Admin'}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Роль "Admin" создана (ID: {admin_role.role_id})'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Роль "Admin" найдена (ID: {admin_role.role_id})'))

        # Проверяем, не существует ли уже админ с таким email
        email = options.get('email')
        if not email:
            if options['noinput']:
                self.stdout.write(self.style.ERROR('Не указан email. Используйте --email или запустите без --noinput'))
                return
            email = input('Email: ').strip()
        
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'Пользователь с email "{email}" уже существует!'))
            return

        # Получаем остальные данные
        first_name = options.get('first_name')
        if not first_name:
            if not options['noinput']:
                first_name = input('Имя: ').strip()
            else:
                first_name = 'Admin'

        last_name = options.get('last_name')
        if not last_name:
            if not options['noinput']:
                last_name = input('Фамилия: ').strip()
            else:
                last_name = 'Admin'

        phone = options.get('phone')
        if not phone:
            if not options['noinput']:
                phone = input('Телефон: ').strip()
            else:
                phone = '+79999999999'
        
        phone = normalize_phone(phone)

        # Получаем пароль
        password = None
        if options['noinput']:
            # В режиме noinput нужно передавать пароль через переменную окружения
            import os
            password = os.environ.get('ADMIN_PASSWORD')
            if not password:
                self.stdout.write(self.style.ERROR('Для режима --noinput установите переменную окружения ADMIN_PASSWORD'))
                return
        else:
            password = getpass.getpass('Пароль: ')
            password_confirm = getpass.getpass('Пароль (повтор): ')
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Пароли не совпадают!'))
                return
            if len(password) < 6:
                self.stdout.write(self.style.ERROR('Пароль должен содержать минимум 6 символов!'))
                return

        # Создаём пользователя
        try:
            with transaction.atomic():
                user = User.objects.create(
                    email=email,
                    password_hash=hash_password_sha256(password),
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    role=admin_role,
                )
                
                # Создаём профиль
                UserProfile.objects.get_or_create(user=user)
                
                # Показываем точные данные для входа
                normalized_phone_for_login = normalize_phone(user.phone)
                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ Суперпользователь успешно создан!\n'
                    f'\nДанные для входа:'
                    f'\n  Email: {user.email}'
                    f'\n  Телефон: {normalized_phone_for_login}'
                    f'\n  Пароль: [введённый вами пароль]'
                    f'\n\nИнформация:'
                    f'\n  Имя: {user.first_name} {user.last_name}'
                    f'\n  Роль: {user.role.role_name}'
                    f'\n  ID: {user.user_id}'
                    f'\n  Телефон в БД: {user.phone}'
                    f'\n'
                ))
                self.stdout.write(self.style.WARNING(
                    f'\n⚠ ВАЖНО: Для входа используйте:'
                    f'\n  - Email: "{user.email}" (точно как указано выше)'
                    f'\n  - ИЛИ телефон: "{normalized_phone_for_login}" (если вход по телефону)'
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при создании пользователя: {str(e)}'))

