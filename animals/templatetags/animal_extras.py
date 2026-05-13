from __future__ import annotations

from datetime import date

from django import template

register = template.Library()


def _plural_ru(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if 11 <= (n % 100) <= 14:
        return many
    last = n % 10
    if last == 1:
        return one
    if 2 <= last <= 4:
        return few
    return many


@register.filter
def age_display(animal) -> str:
    """
    Показывает возраст:
    - age >= 1: в годах (1 год / 2 года / 5 лет)
    - age == 0: в месяцах, если можно прикинуть по admission_date, иначе "до 1 года"
    """
    if not animal:
        return ''

    try:
        years = int(getattr(animal, 'age', 0) or 0)
    except Exception:
        years = 0

    if years >= 1:
        return f'{years} {_plural_ru(years, "год", "года", "лет")}'

    # age == 0 → пробуем оценить месяцы по дате поступления (часто для малышей она близка к возрасту)
    admission = getattr(animal, 'admission_date', None)
    if admission:
        try:
            days = (date.today() - admission).days
            if days >= 0:
                months = max(1, min(11, days // 30))
                return f'{months} {_plural_ru(months, "месяц", "месяца", "месяцев")}'
        except Exception:
            pass

    return 'до 1 года'

