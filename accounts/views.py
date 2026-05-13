from django.shortcuts import render, redirect
from rest_framework import viewsets
from .models import User, UserProfile, Role
from .serializers import UserSerializer, UserProfileSerializer, RoleSerializer
from django.views import View
from django.contrib import messages
from .forms import RegisterForm, LoginForm
from .utils import hash_password_sha256, normalize_phone, get_user_from_jwt, get_user_id_from_jwt
from .jwt_tokens import CustomRefreshToken
from django.core.files.storage import default_storage
from django.utils import timezone
from django.conf import settings
from django.db import connection
import os

# Create your views here.

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

class LogoutView(View):
    def get(self, request):
        response = redirect('home')
        # Удаляем токены из cookie
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        messages.success(request, 'Вы вышли из аккаунта')
        return response

# Frontend UI
class LoginView(View):
    def get(self, request):
        return render(request, 'accounts/login.html', {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if not form.is_valid():
            # Добавляем теги к ошибкам валидации формы
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error, extra_tags='login_page')
            return render(request, 'accounts/login.html', {'form': form})
        login_value = form.cleaned_data['login']
        password = form.cleaned_data['password']
        password_hash = hash_password_sha256(password)
        user = None
        if '@' in login_value:
            # Валидация email формата
            import re
            email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
            if not email_pattern.match(login_value):
                messages.error(request, 'Введите корректный email адрес', extra_tags='login_page')
                return render(request, 'accounts/login.html', {'form': form})
            user = User.objects.filter(email=login_value, password_hash=password_hash).first()
        else:
            phone = normalize_phone(login_value)
            user = User.objects.filter(phone=phone, password_hash=password_hash).first()
        if not user:
            messages.error(request, 'Неверные логин или пароль', extra_tags='login_page')
            return render(request, 'accounts/login.html', {'form': form})
        
        # Генерируем JWT токены
        refresh = CustomRefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Устанавливаем токены в cookie
        response = redirect('home')
        # Используем secure=False для локальной разработки (для production установите secure=True)
        response.set_cookie(
            'access_token', 
            str(access_token), 
            max_age=86400,  # 1 день
            httponly=True, 
            samesite='Lax',
            path='/'
        )
        response.set_cookie(
            'refresh_token', 
            str(refresh), 
            max_age=604800,  # 7 дней
            httponly=True, 
            samesite='Lax',
            path='/'
        )
        
        # Не показываем сообщение об успешном входе
        return response

class RegisterView(View):
    def get(self, request):
        return render(request, 'accounts/register.html', {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if not form.is_valid():
            # Добавляем теги к ошибкам валидации формы
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error, extra_tags='register_page')
            return render(request, 'accounts/register.html', {'form': form})
        data = form.cleaned_data
        
        # Дополнительная валидация имени и фамилии (минимум 3 символа, без цифр и спецсимволов)
        import re
        name_pattern = re.compile(r'^[а-яА-ЯёЁa-zA-Z\s\-\']+$')
        if len(data['first_name'].strip()) < 3:
            messages.error(request, 'Имя должно содержать минимум 3 символа', extra_tags='register_page')
            return render(request, 'accounts/register.html', {'form': form})
        if not name_pattern.match(data['first_name']):
            messages.error(request, 'Имя не должно содержать цифры и спецсимволы', extra_tags='register_page')
            return render(request, 'accounts/register.html', {'form': form})
        if len(data['last_name'].strip()) < 3:
            messages.error(request, 'Фамилия должна содержать минимум 3 символа', extra_tags='register_page')
            return render(request, 'accounts/register.html', {'form': form})
        if not name_pattern.match(data['last_name']):
            messages.error(request, 'Фамилия не должна содержать цифры и спецсимволы', extra_tags='register_page')
            return render(request, 'accounts/register.html', {'form': form})
        
        # Валидация email формата
        email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
        if not email_pattern.match(data['email']):
            messages.error(request, 'Введите корректный email адрес', extra_tags='register_page')
            return render(request, 'accounts/register.html', {'form': form})
        role = Role.objects.filter(role_name='Guest').first()
        phone = normalize_phone(data['phone'])  # Нормализуем телефон при регистрации
        user = User(
            email=data['email'],
            password_hash=hash_password_sha256(data['password']),
            last_name=data['last_name'],
            first_name=data['first_name'],
            middle_name=data.get('middle_name') or None,
            phone=phone,
            role=role if role else None,
        )
        user.save()
        # Профиль (необязательный)
        UserProfile.objects.get_or_create(user=user)
        messages.success(request, 'Регистрация выполнена. Войдите в систему.')
        return redirect('login')


class DataPolicyView(View):
    def get(self, request):
        return render(request, 'accounts/data_policy.html')

class ProfileView(View):
    def get(self, request):
        user = get_user_from_jwt(request)
        if not user:
            return redirect('login')
        user_id = user.user_id
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        # Определяем роль пользователя
        user_role = user.role.role_name if user.role else None
        is_admin_or_manager = user_role in ['Admin', 'Manager']
        is_admin = user_role == 'Admin'
        
        applications = []
        donations = []
        
        # Загружаем заявки и пожертвования только для обычных пользователей
        if not is_admin_or_manager:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT a.ApplicationID, a.ApplicationDate, ast.StatusName, a.Comment, an.AnimalName
                    FROM Applications a
                    JOIN Animals an ON a.AnimalID = an.AnimalID
                    JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                    WHERE a.UserID = %s
                    ORDER BY a.ApplicationDate DESC
                    """,
                    [user_id]
                )
                for r in cur.fetchall():
                    app_id, app_date, status_name, comment, animal_name = r
                    
                    # Определяем статус на основе StatusName
                    if status_name == 'Approved':
                        status = 'Одобрено'
                        status_class = 'success'
                    elif status_name == 'Rejected':
                        status = 'Отклонено'
                        status_class = 'danger'
                    else:  # Pending
                        status = 'В ожидании'
                        status_class = 'warning'
                    applications.append({ 
                        'id': app_id, 
                        'date': app_date, 
                        'status': status,
                        'status_class': status_class,
                        'animal': animal_name 
                    })
                cur.execute(
                    """
                    SELECT d.DonationID, d.DonationDate, d.Amount, an.AnimalName
                    FROM Donations d
                    JOIN Animals an ON d.AnimalID = an.AnimalID
                    WHERE d.UserID = %s
                    ORDER BY d.DonationDate DESC
                    """,
                    [user_id]
                )
                for r in cur.fetchall():
                    donations.append({ 'id': r[0], 'date': r[1], 'amount': r[2], 'animal': r[3] })
        
        ctx = {
            'db_user': user,
            'db_profile': profile,
            'applications': applications,
            'donations': donations,
            'is_admin': is_admin,
            'is_admin_or_manager': is_admin_or_manager,
            'user_role': user_role,
        }
        return render(request, 'accounts/profile.html', ctx)

    def post(self, request):
        user = get_user_from_jwt(request)
        if not user:
            return redirect('login')
        user_id = user.user_id
        profile, _ = UserProfile.objects.get_or_create(user=user)
        # Адрес: ожидаем формат "Город, улица, д. N[, кв. M]"
        home_address = (request.POST.get('home_address') or '').strip()
        if home_address:
            import re
            addr_re = re.compile(r'^[^,]{2,},\s*[^,]{2,},\s*д\.\s*[0-9]{1,6}[0-9A-Za-zА-Яа-яЁё\/-]*?(?:,\s*кв\.\s*[0-9]{1,6})?$', re.IGNORECASE)
            if not addr_re.match(home_address):
                messages.error(request, 'Введите корректный адрес (Город, улица, д. N[, кв. M])')
                return redirect('profile')
        profile.home_address = home_address or None
        profile.date_of_birth = request.POST.get('date_of_birth') or None
        # загрузка файла аватара
        avatar_file = request.FILES.get('avatar_file')
        if avatar_file:
            ext = os.path.splitext(avatar_file.name)[1].lower()
            filename = f"avatars/user_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
            saved_path = default_storage.save(filename, avatar_file)
            url = default_storage.url(saved_path)
            profile.profile_picture = url
        profile.save()
        messages.success(request, 'Профиль обновлён')
        return redirect('profile')

class ApplicationsListView(View):
    def get(self, request):
        return redirect('profile')

class DonationsListView(View):
    def get(self, request):
        return redirect('profile')

class ApplicationDetailView(View):
    def get(self, request, pk):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            return redirect('login')
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT a.ApplicationID, a.ApplicationDate, ast.StatusName, a.Reason, a.Experience, a.HousingConditions, a.Comment,
                       an.AnimalName
                FROM Applications a
                JOIN Animals an ON an.AnimalID = a.AnimalID
                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                WHERE a.ApplicationID = %s AND a.UserID = %s
                """,
                [pk, user_id]
            )
            row = cur.fetchone()
        if not row:
            return redirect('profile')
        app_id, app_date, status_name, reason, experience, housing, comment, animal_name = row
        
        # Определяем статус на основе StatusName
        if status_name == 'Approved':
            status = 'Одобрено'
            status_class = 'success'
        elif status_name == 'Rejected':
            status = 'Отклонено'
            status_class = 'danger'
        else:  # Pending
            status = 'В ожидании'
            status_class = 'warning'
        
        app = {
            'id': app_id, 
            'date': app_date, 
            'status': status,
            'status_class': status_class,
            'reason': reason, 
            'experience': experience, 
            'housing': housing, 
            'comment': comment, 
            'animal': animal_name
        }
        return render(request, 'accounts/application_detail.html', { 'app': app })
