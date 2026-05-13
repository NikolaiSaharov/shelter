from django.shortcuts import redirect
from django.contrib import messages
from django.db import connection
from accounts.utils import get_user_id_from_jwt


class AdminRequiredMixin:
    """Миксин для проверки роли администратора"""
    
    def dispatch(self, request, *args, **kwargs):
        user_id = get_user_id_from_jwt(request)
        if not user_id:
            messages.error(request, 'Необходима авторизация')
            return redirect('login')
        
        role = self._get_user_role(user_id)
        if role != 'Admin':
            messages.error(request, 'Доступ запрещён. Требуется роль администратора')
            return redirect('home')
        
        return super().dispatch(request, *args, **kwargs)
    
    @staticmethod
    def _get_user_role(user_id: int):
        """Получает роль пользователя из базы данных"""
        with connection.cursor() as cur:
            cur.execute(
                "SELECT r.RoleName FROM Users u JOIN Roles r ON u.RoleID=r.RoleID WHERE u.UserID=%s",
                [user_id]
            )
            row = cur.fetchone()
            return row[0] if row else None

