from django.shortcuts import render
from django.views import View
from .utils import get_user_from_jwt

class TestJWTView(View):
    """Тестовая страница для проверки JWT токенов"""
    def get(self, request):
        user = get_user_from_jwt(request)
        has_access_token = 'access_token' in request.COOKIES
        has_refresh_token = 'refresh_token' in request.COOKIES
        
        context = {
            'user': user,
            'user_id': user.user_id if user else None,
            'has_access_token': has_access_token,
            'has_refresh_token': has_refresh_token,
            'access_token_preview': request.COOKIES.get('access_token', '')[:50] + '...' if has_access_token else None,
            'all_cookies': list(request.COOKIES.keys()),
        }
        return render(request, 'accounts/test_jwt.html', context)

