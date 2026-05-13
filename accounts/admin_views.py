from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import connection
from .models import User, UserProfile, Role
from animals.models import Shelter
from .utils import hash_password_sha256, normalize_phone, get_user_id_from_jwt
from .audit_utils import log_audit
from animals.mixins import AdminRequiredMixin


class UserAdminListView(AdminRequiredMixin, View):
    """Список всех пользователей для админа"""
    def get(self, request):
        # Фильтры
        q = request.GET.get('q', '').strip()
        role_filter = request.GET.get('role', '')
        
        users = User.objects.select_related('role').all()
        
        if q:
            users = users.filter(
                email__icontains=q
            ) | users.filter(
                first_name__icontains=q
            ) | users.filter(
                last_name__icontains=q
            ) | users.filter(
                phone__icontains=q
            )
        
        if role_filter:
            users = users.filter(role_id=role_filter)
        
        users = users.order_by('-registration_date')
        roles = Role.objects.all()
        
        return render(request, 'accounts/admin/list.html', {
            'users': users,
            'roles': roles,
            'q': q,
            'role_filter': role_filter,
        })


class UserAdminCreateView(AdminRequiredMixin, View):
    """Создание пользователя (админ)"""
    def get(self, request):
        roles = Role.objects.all()
        shelters = Shelter.objects.filter(is_active=True).order_by('shelter_name')
        return render(request, 'accounts/admin/create.html', {
            'roles': roles,
            'shelters': shelters,
        })
    
    def post(self, request):
        email = (request.POST.get('email') or '').strip()
        password = (request.POST.get('password') or '').strip()
        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        middle_name = (request.POST.get('middle_name') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        role_id = request.POST.get('role_id')
        shelter_id = request.POST.get('shelter_id') or None
        
        errors = []
        if not email:
            errors.append('Укажите email')
        elif User.objects.filter(email=email).exists():
            errors.append('Пользователь с таким email уже существует')
        
        if not password:
            errors.append('Укажите пароль')
        elif len(password) < 6:
            errors.append('Пароль должен содержать не менее 6 символов')
        
        if not first_name:
            errors.append('Укажите имя')
        elif any(char.isdigit() for char in first_name):
            errors.append('Имя не должно содержать цифры')
        if not last_name:
            errors.append('Укажите фамилию')
        elif any(char.isdigit() for char in last_name):
            errors.append('Фамилия не должна содержать цифры')
        if not phone:
            errors.append('Укажите телефон')
        
        if not role_id:
            errors.append('Выберите роль')
        else:
            # Если назначаем роль менеджера — приют обязателен
            try:
                role_for_validation = Role.objects.get(pk=role_id)
                if role_for_validation.role_name == 'Manager' and not shelter_id:
                    errors.append('Для роли "Менеджер" необходимо выбрать приют')
            except Role.DoesNotExist:
                errors.append('Выбранная роль не найдена')
        
        if errors:
            # Разделяем ошибки по полям для отображения на полях
            error_dict = {}
            for error in errors:
                if 'имя' in error.lower() and 'не должно' in error.lower():
                    error_dict['error_first_name'] = error
                elif 'фамилия' in error.lower() and 'не должна' in error.lower():
                    error_dict['error_last_name'] = error
                elif 'отчество' in error.lower():
                    error_dict['error_middle_name'] = error
                elif 'email' in error.lower():
                    error_dict['error_email'] = error
                elif 'пароль' in error.lower():
                    error_dict['error_password'] = error
                elif 'телефон' in error.lower():
                    error_dict['error_phone'] = error
                elif 'роль' in error.lower():
                    error_dict['error_role_id'] = error
                elif 'приют' in error.lower():
                    error_dict['error_shelter_id'] = error
                else:
                    messages.error(request, error)
            
            roles = Role.objects.all()
            shelters = Shelter.objects.filter(is_active=True).order_by('shelter_name')
            return render(request, 'accounts/admin/create.html', {
                'roles': roles,
                'shelters': shelters,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'phone': phone,
                'role_id': role_id,
                'shelter_id': shelter_id,
                **error_dict
            })
        
        try:
            role = Role.objects.get(pk=role_id)
            normalized_phone = normalize_phone(phone)
            
            user = User.objects.create(
                email=email,
                password_hash=hash_password_sha256(password),
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name if middle_name else None,
                phone=normalized_phone,
                role=role,
                shelter_id=int(shelter_id) if (role.role_name == 'Manager' and shelter_id) else None,
            )
            
            # Создаём профиль пользователя
            UserProfile.objects.get_or_create(user=user)
            
            # Логируем в аудитлог
            log_audit(
                table_name='Users',
                record_id=user.user_id,
                action='Create',
                changed_by=get_user_id_from_jwt(request),
                new_value=f"Email: {email}, Name: {first_name} {last_name}, Role: {role.role_name}"
            )
            
            messages.success(request, f'Пользователь "{email}" успешно создан')
            return redirect('user_admin_list')
        except Role.DoesNotExist:
            messages.error(request, 'Выбранная роль не найдена')
            roles = Role.objects.all()
            shelters = Shelter.objects.filter(is_active=True).order_by('shelter_name')
            return render(request, 'accounts/admin/create.html', {
                'roles': roles,
                'shelters': shelters,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'phone': phone,
            })
        except Exception as e:
            messages.error(request, f'Ошибка при создании: {str(e)}')
            roles = Role.objects.all()
            shelters = Shelter.objects.filter(is_active=True).order_by('shelter_name')
            return render(request, 'accounts/admin/create.html', {
                'roles': roles,
                'shelters': shelters,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'phone': phone,
                'role_id': role_id,
                'shelter_id': shelter_id,
            })


class UserAdminUpdateView(AdminRequiredMixin, View):
    """Редактирование пользователя (админ)"""
    def get(self, request, pk):
        user = get_object_or_404(User.objects.select_related('role'), pk=pk)
        roles = Role.objects.all()
        shelters = Shelter.objects.filter(is_active=True).order_by('shelter_name')
        return render(request, 'accounts/admin/update.html', {
            'user': user,
            'roles': roles,
            'shelters': shelters,
        })
    
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password', '').strip()
        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        middle_name = (request.POST.get('middle_name') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        role_id = request.POST.get('role_id')
        shelter_id = request.POST.get('shelter_id') or None
        
        errors = []
        if not email:
            errors.append('Укажите email')
        elif email != user.email and User.objects.filter(email=email).exists():
            errors.append('Пользователь с таким email уже существует')
        
        if password and len(password) < 6:
            errors.append('Пароль должен содержать не менее 6 символов')
        
        import re
        name_pattern = re.compile(r'^[а-яА-ЯёЁa-zA-Z\s\-\']+$')
        
        # Валидация email формата
        if email:
            email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
            if not email_pattern.match(email):
                errors.append('Введите корректный email адрес')
        
        if not first_name:
            errors.append('Укажите имя')
        elif len(first_name.strip()) < 3:
            errors.append('Имя должно содержать минимум 3 символа')
        elif not name_pattern.match(first_name):
            errors.append('Имя не должно содержать цифры и спецсимволы')
        if not last_name:
            errors.append('Укажите фамилию')
        elif len(last_name.strip()) < 3:
            errors.append('Фамилия должна содержать минимум 3 символа')
        elif not name_pattern.match(last_name):
            errors.append('Фамилия не должна содержать цифры и спецсимволы')
        if not phone:
            errors.append('Укажите телефон')
        
        if not role_id:
            errors.append('Выберите роль')
        else:
            try:
                role_for_validation = Role.objects.get(pk=role_id)
                if role_for_validation.role_name == 'Manager' and not shelter_id:
                    errors.append('Для роли "Менеджер" необходимо выбрать приют')
            except Role.DoesNotExist:
                errors.append('Выбранная роль не найдена')
        
        if errors:
            # Разделяем ошибки по полям для отображения на полях
            error_dict = {}
            for error in errors:
                if 'имя' in error.lower() and 'не должно' in error.lower():
                    error_dict['error_first_name'] = error
                elif 'фамилия' in error.lower() and 'не должна' in error.lower():
                    error_dict['error_last_name'] = error
                elif 'отчество' in error.lower():
                    error_dict['error_middle_name'] = error
                elif 'приют' in error.lower():
                    error_dict['error_shelter_id'] = error
                else:
                    messages.error(request, error)
            
            roles = Role.objects.all()
            shelters = Shelter.objects.filter(is_active=True).order_by('shelter_name')
            return render(request, 'accounts/admin/update.html', {
                'user': user,
                'roles': roles,
                'shelters': shelters,
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'email': email,
                'phone': phone,
                'role_id': role_id,
                'shelter_id': shelter_id,
                **error_dict
            })
        
        try:
            role = Role.objects.get(pk=role_id)
            normalized_phone = normalize_phone(phone)
            
            # Сохраняем старые значения для логирования ДО изменений
            old_email = user.email
            old_name = f"{user.first_name} {user.last_name}"
            old_role = user.role.role_name if user.role else None
            old_shelter_id = user.shelter_id
            
            user.email = email
            if password:
                user.password_hash = hash_password_sha256(password)
            user.first_name = first_name
            user.last_name = last_name
            user.middle_name = middle_name if middle_name else None
            user.phone = normalized_phone
            user.role = role
            user.shelter_id = int(shelter_id) if (role.role_name == 'Manager' and shelter_id) else None
            user.save()
            
            # Формируем описание изменений
            changes = []
            if old_email != email:
                changes.append(f"Email: {old_email} → {email}")
            if old_name != f"{first_name} {last_name}":
                changes.append(f"Name: {old_name} → {first_name} {last_name}")
            if old_role != role.role_name:
                changes.append(f"Role: {old_role} → {role.role_name}")
            if (old_role == 'Manager' or role.role_name == 'Manager') and old_shelter_id != user.shelter_id:
                changes.append("Shelter: изменён")
            if password:
                changes.append("Password: изменен")
            
            change_desc = "; ".join(changes) if changes else "Обновление данных"
            
            # Логируем в аудитлог
            log_audit(
                table_name='Users',
                record_id=user.user_id,
                action='Update',
                changed_by=get_user_id_from_jwt(request),
                old_value=f"Email: {old_email}, Name: {old_name}, Role: {old_role}, ShelterID: {old_shelter_id}",
                new_value=f"Email: {email}, Name: {first_name} {last_name}, Role: {role.role_name}, ShelterID: {user.shelter_id}"
            )
            
            messages.success(request, f'Пользователь "{email}" успешно обновлён')
            return redirect('user_admin_list')
        except Role.DoesNotExist:
            messages.error(request, 'Выбранная роль не найдена')
            roles = Role.objects.all()
            return render(request, 'accounts/admin/update.html', {
                'user': user,
                'roles': roles,
            })
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
            roles = Role.objects.all()
            return render(request, 'accounts/admin/update.html', {
                'user': user,
                'roles': roles,
            })


class UserAdminDeleteView(AdminRequiredMixin, View):
    """Удаление пользователя (админ)"""
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user_email = user.email
        
        # Проверяем, не пытается ли админ удалить сам себя
        if user.user_id == get_user_id_from_jwt(request):
            messages.error(request, 'Нельзя удалить свой собственный аккаунт')
            return redirect('user_admin_list')
        
        try:
            # Сохраняем данные перед удалением для логирования
            user_data = f"Email: {user.email}, Name: {user.first_name} {user.last_name}, Role: {user.role.role_name if user.role else 'None'}"
            user_id_for_log = user.user_id
            
            # Удаляем связанные записи перед удалением пользователя
            from django.db import connection
            with connection.cursor() as cursor:
                try:
                    cursor.execute("DELETE FROM ManagerNotifications WHERE UserID = %s", [user.user_id])
                except:
                    pass  # Таблица может не существовать или записей нет
            
            user.delete()
            
            # Логируем в аудитлог
            log_audit(
                table_name='Users',
                record_id=user_id_for_log,
                action='Delete',
                changed_by=get_user_id_from_jwt(request),
                old_value=user_data
            )
            
            messages.success(request, f'Пользователь "{user_email}" успешно удалён')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении: {str(e)}')
        return redirect('user_admin_list')

