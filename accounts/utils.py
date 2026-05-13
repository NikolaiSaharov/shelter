import hashlib
import re
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from .models import User

def hash_password_sha256(plain: str) -> str:
    if plain is None:
        return ''
    return hashlib.sha256(plain.encode('utf-8')).hexdigest()

def normalize_phone(raw: str) -> str:
    if not raw:
        return ''
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ''
    if digits.startswith('8'):
        digits = '7' + digits[1:]
    if not digits.startswith('7'):
        if len(digits) == 10:
            digits = '7' + digits
    return '+' + digits


def ru_phone_digits_from_input(raw: str | None) -> str:
    """Только цифры, нормализация 8→7, ведущая 7, не более 11 цифр (как у мобильного РФ)."""
    if not raw:
        return ''
    digits = re.sub(r'\D', '', str(raw))
    if not digits:
        return ''
    if digits.startswith('8'):
        digits = '7' + digits[1:]
    if not digits.startswith('7'):
        digits = '7' + digits
    return digits[:11]


def format_ru_phone_display(digits_11: str) -> str:
    """+7 (XXX) XXX-XX-XX из ровно 11 цифр, начинающихся с 7."""
    if len(digits_11) != 11 or not digits_11.startswith('7'):
        return ''
    d = digits_11
    return f'+7 ({d[1:4]}) {d[4:7]}-{d[7:9]}-{d[9:11]}'


def parse_shelter_phone(raw: str | None) -> tuple[str | None, str | None]:
    """
    Пустой ввод -> (None, None).
    Неполный/неверный номер -> (None, текст ошибки).
    Иначе -> (строка для сохранения в БД, None).
    """
    s = (raw or '').strip()
    if not s:
        return None, None
    d = ru_phone_digits_from_input(s)
    if len(d) != 11:
        return None, 'Укажите полный номер телефона: +7 (XXX) XXX-XX-XX (10 цифр после кода 7).'
    return format_ru_phone_display(d), None


_email_validator = EmailValidator(message='Некорректный адрес электронной почты.')


def clean_optional_email(value: str | None) -> tuple[str | None, str | None]:
    """Пусто -> (None, None). Невалидный email -> (None, сообщение). Иначе (email, None)."""
    v = (value or '').strip()
    if not v:
        return None, None
    try:
        _email_validator(v)
    except ValidationError:
        return None, 'Укажите корректный адрес электронной почты (например, shelter@example.com).'
    return v, None

def get_user_from_jwt(request):
    """
    Извлекает пользователя из JWT токена в запросе.
    Проверяет заголовок Authorization и cookie.
    Возвращает объект User или None.
    """
    token = None
    
    # Проверяем заголовок Authorization
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    
    # Если токена нет в заголовке, проверяем cookie
    if not token:
        token = request.COOKIES.get('access_token')
    
    if not token:
        return None
    
    try:
        # Валидируем токен
        untyped_token = UntypedToken(token)
        user_id = untyped_token.get('user_id')
        
        if user_id:
            try:
                return User.objects.select_related('role', 'shelter').get(pk=user_id)
            except User.DoesNotExist:
                return None
    except (InvalidToken, TokenError, KeyError):
        return None
    
    return None

def get_user_id_from_jwt(request):
    """
    Извлекает user_id из JWT токена в запросе.
    Возвращает user_id или None.
    """
    user = get_user_from_jwt(request)
    return user.user_id if user else None
