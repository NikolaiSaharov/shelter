from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def role_display(value: str | None) -> str:
    """
    Отображение ролей на русском, при этом в БД могут храниться английские значения.
    """
    if not value:
        return ""
    mapping = {
        "Admin": "Админ",
        "Manager": "Менеджер",
        "Guest": "Пользователь",
        "User": "Пользователь",
    }
    return mapping.get(str(value), str(value))


@register.filter
def role_badge_class(value: str | None) -> str:
    if not value:
        return "text-bg-secondary"
    value = str(value)
    if value == "Admin":
        return "text-bg-danger"
    if value == "Manager":
        return "text-bg-warning"
    return "text-bg-secondary"


@register.filter
def audit_action_display(value: str | None) -> str:
    if not value:
        return ""
    mapping = {
        "Create": "Создание",
        "Update": "Изменение",
        "Delete": "Удаление",
        "Login": "Вход",
        "Logout": "Выход",
    }
    return mapping.get(str(value), str(value))

