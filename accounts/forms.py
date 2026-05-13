from django import forms
from .models import User
from .utils import normalize_phone

class RegisterForm(forms.Form):
    first_name = forms.CharField(label='Имя', max_length=50)
    last_name = forms.CharField(label='Фамилия', max_length=50)
    middle_name = forms.CharField(label='Отчество', max_length=50, required=False)
    phone = forms.CharField(label='Телефон', max_length=20)
    email = forms.EmailField(label='Почта')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    agree_personal_data = forms.BooleanField(
        label='Согласие на обработку персональных данных',
        required=True,
        error_messages={
            'required': 'Необходимо согласиться на обработку персональных данных',
        },
    )

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get('phone'))
        if not phone.startswith('+'):
            raise forms.ValidationError('Некорректный телефон')
        return phone

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Почта уже зарегистрирована')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            return password
        
        if len(password) < 6:
            raise forms.ValidationError('Пароль должен содержать минимум 6 символов')
        
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError('Пароль должен содержать хотя бы одну цифру')
        
        if not any(char.isupper() for char in password):
            raise forms.ValidationError('Пароль должен содержать хотя бы одну заглавную букву')
        
        return password

class LoginForm(forms.Form):
    login = forms.CharField(label='Почта или телефон')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)


class ForgotPasswordForm(forms.Form):
    login = forms.CharField(label='Почта или телефон', required=True)

    def clean_login(self):
        login = self.cleaned_data.get('login', '').strip()
        if not login:
            raise forms.ValidationError('Поле не может быть пустым')
        
        # Проверяем, это email или телефон
        if '@' in login:
            # Валидация email
            import re
            email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
            if not email_pattern.match(login):
                raise forms.ValidationError('Введите корректный email адрес')
        else:
            # Валидация телефона
            phone = normalize_phone(login)
            if not phone or not phone.startswith('+'):
                raise forms.ValidationError('Введите корректный номер телефона')
            # Проверяем минимальную длину номера (должен быть +7 и минимум 10 цифр)
            digits = ''.join(filter(str.isdigit, phone))
            if len(digits) < 11:
                raise forms.ValidationError('Номер телефона должен содержать минимум 11 цифр')
        
        return login


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(label='Новый пароль', widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(label='Подтвердите пароль', widget=forms.PasswordInput, required=True)

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password', '').strip()
        if not password:
            raise forms.ValidationError('Пароль не может быть пустым')
        
        if len(password) < 6:
            raise forms.ValidationError('Пароль должен содержать минимум 6 символов')
        
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError('Пароль должен содержать хотя бы одну цифру')
        
        if not any(char.isupper() for char in password):
            raise forms.ValidationError('Пароль должен содержать хотя бы одну заглавную букву')
        
        return password

    def clean_confirm_password(self):
        confirm_password = self.cleaned_data.get('confirm_password', '').strip()
        if not confirm_password:
            raise forms.ValidationError('Подтверждение пароля не может быть пустым')
        return confirm_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError({'confirm_password': 'Пароли не совпадают'})
        
        return cleaned_data