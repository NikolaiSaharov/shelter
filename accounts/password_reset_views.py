from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .forms import ForgotPasswordForm, ResetPasswordForm
from .models import User
from .utils import normalize_phone, hash_password_sha256


class ForgotPasswordView(View):
    """Первый шаг восстановления пароля - ввод email/телефона"""
    def get(self, request):
        return render(request, 'accounts/forgot_password.html', {'form': ForgotPasswordForm()})

    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, 'accounts/forgot_password.html', {'form': form})
        
        login_value = form.cleaned_data['login']
        user = None
        
        if '@' in login_value:
            user = User.objects.filter(email=login_value).first()
        else:
            phone = normalize_phone(login_value)
            user = User.objects.filter(phone=phone).first()
        
        if not user:
            messages.error(request, 'Пользователь с такими данными не найден', extra_tags='forgot_password_page')
            return render(request, 'accounts/forgot_password.html', {'form': form})
        
        # Сохраняем user_id в сессии для следующего шага
        request.session['password_reset_user_id'] = user.user_id
        return redirect('reset_password')


class ResetPasswordView(View):
    """Второй шаг восстановления пароля - ввод нового пароля"""
    def get(self, request):
        # Проверяем, что пользователь прошел первый шаг
        user_id = request.session.get('password_reset_user_id')
        if not user_id:
            messages.error(request, 'Сессия истекла. Начните восстановление пароля заново.')
            return redirect('forgot_password')
        
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'Пользователь не найден')
            request.session.pop('password_reset_user_id', None)
            return redirect('forgot_password')
        
        return render(request, 'accounts/reset_password.html', {
            'form': ResetPasswordForm(),
            'user_email': user.email,
        })

    def post(self, request):
        # Проверяем, что пользователь прошел первый шаг
        user_id = request.session.get('password_reset_user_id')
        if not user_id:
            messages.error(request, 'Сессия истекла. Начните восстановление пароля заново.')
            return redirect('forgot_password')
        
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'Пользователь не найден')
            request.session.pop('password_reset_user_id', None)
            return redirect('forgot_password')
        
        form = ResetPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, 'accounts/reset_password.html', {
                'form': form,
                'user_email': user.email,
            })
        
        # Обновляем пароль
        new_password = form.cleaned_data['new_password']
        user.password_hash = hash_password_sha256(new_password)
        user.save()
        
        # Очищаем сессию
        request.session.pop('password_reset_user_id', None)
        
        messages.success(request, 'Пароль успешно изменен. Теперь вы можете войти с новым паролем.')
        return redirect('login')

