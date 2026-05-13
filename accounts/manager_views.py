from django.shortcuts import render
from django.views import View
from django.contrib import messages
from django.db import connection
from .models import User, Role
from news.mixins import AdminOrManagerRequiredMixin


class UserManagerListView(AdminOrManagerRequiredMixin, View):
    """Список всех пользователей для менеджера (только просмотр)"""
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
        
        return render(request, 'accounts/manager/list.html', {
            'users': users,
            'roles': roles,
            'q': q,
            'role_filter': role_filter,
        })

