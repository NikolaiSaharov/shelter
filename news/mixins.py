from django.shortcuts import redirect
from django.contrib import messages
from django.db import connection
from accounts.utils import get_user_id_from_jwt, get_user_from_jwt


class AdminOrManagerRequiredMixin:
    """Миксин для проверки роли администратора или менеджера"""
    
    def dispatch(self, request, *args, **kwargs):
        user = get_user_from_jwt(request)
        if not user:
            messages.error(request, 'Необходима авторизация')
            return redirect('login')
        
        role = user.role.role_name if user.role else self._get_user_role(user.user_id)
        if role not in ['Admin', 'Manager']:
            messages.error(request, 'Доступ запрещён. Требуется роль администратора или менеджера')
            return redirect('home')

        # Пробрасываем в request — чтобы менеджерские вьюхи могли фильтровать по приюту
        request.current_user = user
        request.current_user_role = role
        request.manager_shelter_id = user.shelter_id if role == 'Manager' else None

        # Прод-логика: менеджер обязан быть привязан к приюту
        if role == 'Manager' and not request.manager_shelter_id:
            messages.error(request, 'Менеджер не привязан к приюту. Обратитесь к администратору.')
            return redirect('home')
        
        return super().dispatch(request, *args, **kwargs)
    
    @staticmethod
    def _get_user_role(user_id: int):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT r.rolename FROM users u JOIN roles r ON u.roleid=r.roleid WHERE u.userid=%s",
                [user_id]
            )
            row = cur.fetchone()
            return row[0] if row else None

