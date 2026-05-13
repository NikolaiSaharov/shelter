from django.core.management.base import BaseCommand
from accounts.models import User
from accounts.utils import hash_password_sha256, normalize_phone


class Command(BaseCommand):
    help = 'Проверяет данные пользователя для диагностики проблем с входом'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email пользователя для проверки',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Пароль для проверки хеширования',
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options.get('password')
        
        users = User.objects.filter(email=email)
        if not users.exists():
            self.stdout.write(self.style.ERROR(f'Пользователь с email "{email}" не найден!'))
            
            similar = User.objects.filter(email__icontains=email[:5])
            if similar.exists():
                self.stdout.write(self.style.WARNING('\nПохожие email:'))
                for u in similar:
                    self.stdout.write(f'  - {u.email}')
            return
        
        user = users.first()
        self.stdout.write(self.style.SUCCESS(f'\nПользователь найден:'))
        self.stdout.write(f'  ID: {user.user_id}')
        self.stdout.write(f'  Email: {user.email}')
        self.stdout.write(f'  Имя: {user.first_name} {user.last_name}')
        self.stdout.write(f'  Телефон: {user.phone}')
        self.stdout.write(f'  Роль: {user.role.role_name if user.role else "Нет роли"}')
        self.stdout.write(f'  Хеш пароля в БД: {user.password_hash[:20]}...')
        
        if password:
            password_hash = hash_password_sha256(password)
            self.stdout.write(f'  Хеш введённого пароля: {password_hash[:20]}...')
            
            if password_hash == user.password_hash:
                self.stdout.write(self.style.SUCCESS('\n✓ Хеши паролей СОВПАДАЮТ!'))
            else:
                self.stdout.write(self.style.ERROR('\n✗ Хеши паролей НЕ СОВПАДАЮТ!'))
                self.stdout.write(self.style.WARNING('\nВозможные причины:'))
                self.stdout.write('  1. Пароль был изменён после создания')
                self.stdout.write('  2. Используется другой алгоритм хеширования')
                self.stdout.write('  3. В пароле есть скрытые символы (пробелы, переносы строк)')
        
        normalized_phone = normalize_phone(user.phone)
        if normalized_phone != user.phone:
            self.stdout.write(self.style.WARNING(f'\n⚠ Телефон в БД: "{user.phone}"'))
            self.stdout.write(self.style.WARNING(f'  Нормализованный: "{normalized_phone}"'))
            self.stdout.write(self.style.WARNING('  При входе по телефону используйте: ' + normalized_phone))
        
        self.stdout.write(f'\nДля входа используйте:')
        self.stdout.write(f'  - Email: {user.email}')
        self.stdout.write(f'  - Телефон: {normalized_phone}')

