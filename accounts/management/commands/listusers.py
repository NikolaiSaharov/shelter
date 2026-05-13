from django.core.management.base import BaseCommand
from accounts.models import User, Role


class Command(BaseCommand):
    help = 'Показывает список всех пользователей в системе'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-only',
            action='store_true',
            help='Показать только администраторов',
        )
        parser.add_argument(
            '--role',
            type=str,
            help='Показать пользователей с указанной ролью',
        )

    def handle(self, *args, **options):
        queryset = User.objects.select_related('role').all()
        
        if options['admin_only']:
            admin_role = Role.objects.filter(role_name='Admin').first()
            if admin_role:
                queryset = queryset.filter(role=admin_role)
            else:
                self.stdout.write(self.style.ERROR('Роль "Admin" не найдена в базе данных!'))
                return
        
        if options['role']:
            role = Role.objects.filter(role_name=options['role']).first()
            if role:
                queryset = queryset.filter(role=role)
            else:
                self.stdout.write(self.style.ERROR(f'Роль "{options["role"]}" не найдена!'))
                return
        
        users = queryset.order_by('email')
        
        if not users.exists():
            self.stdout.write(self.style.WARNING('Пользователи не найдены!'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\nНайдено пользователей: {users.count()}\n'))
        self.stdout.write('=' * 80)
        
        for user in users:
            role_name = user.role.role_name if user.role else 'Нет роли'
            self.stdout.write(f'ID: {user.user_id}')
            self.stdout.write(f'  Email: "{user.email}"')
            self.stdout.write(f'  Имя: {user.first_name} {user.last_name}')
            self.stdout.write(f'  Телефон: {user.phone}')
            self.stdout.write(f'  Роль: {role_name}')
            self.stdout.write(f'  Дата регистрации: {user.registration_date}')
            self.stdout.write('-' * 80)
        
        # Показываем всех администраторов отдельно
        admin_role = Role.objects.filter(role_name='Admin').first()
        if admin_role:
            admins = User.objects.filter(role=admin_role)
            if admins.exists():
                self.stdout.write(self.style.SUCCESS(f'\n\nАдминистраторы ({admins.count()}):'))
                for admin in admins:
                    self.stdout.write(f'  - {admin.email} (ID: {admin.user_id})')
        
        # Показываем все роли в системе
        roles = Role.objects.all()
        if roles.exists():
            self.stdout.write(self.style.SUCCESS(f'\n\nРоли в системе:'))
            for role in roles:
                count = User.objects.filter(role=role).count()
                self.stdout.write(f'  - {role.role_name}: {count} пользователей')

