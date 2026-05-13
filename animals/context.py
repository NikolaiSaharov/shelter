from __future__ import annotations

from animals.models import Shelter


def active_shelters(request):
    try:
        shelters = Shelter.objects.filter(is_active=True).order_by('shelter_name')
    except Exception:
        shelters = []
    return {'active_shelters': shelters}

