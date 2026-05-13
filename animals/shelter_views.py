from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.db import connection
from .models import Shelter
from .mixins import AdminRequiredMixin
from accounts.audit_utils import log_audit
from accounts.utils import get_user_id_from_jwt, parse_shelter_phone, clean_optional_email


def _posted_from_request(request):
    return {
        'shelter_name': (request.POST.get('shelter_name') or '').strip(),
        'address': (request.POST.get('address') or '').strip(),
        'phone': (request.POST.get('phone') or '').strip(),
        'email': (request.POST.get('email') or '').strip(),
        'description': (request.POST.get('description') or '').strip(),
        'is_active': request.POST.get('is_active') == 'on',
    }


# ============= Shelter CRUD =============

class ShelterListView(AdminRequiredMixin, View):
    """Список приютов"""
    def get(self, request):
        shelters = Shelter.objects.all().order_by('shelter_name')
        return render(request, 'animals/references/shelter_list.html', {
            'shelters': shelters,
        })


class ShelterCreateView(AdminRequiredMixin, View):
    """Создание приюта"""
    def get(self, request):
        return render(request, 'animals/references/shelter_create.html', {'is_active': True})
    
    def post(self, request):
        posted = _posted_from_request(request)
        shelter_name = posted['shelter_name']
        address = posted['address'] or None
        description = posted['description'] or None
        is_active = posted['is_active']

        phone, phone_err = parse_shelter_phone(posted['phone'])
        email, email_err = clean_optional_email(posted['email'])

        if phone_err:
            messages.error(request, phone_err)
            return render(request, 'animals/references/shelter_create.html', posted)
        if email_err:
            messages.error(request, email_err)
            return render(request, 'animals/references/shelter_create.html', posted)

        if not shelter_name:
            messages.error(request, 'Укажите название приюта')
            return render(request, 'animals/references/shelter_create.html', posted)
        
        if Shelter.objects.filter(shelter_name=shelter_name).exists():
            messages.error(request, 'Приют с таким названием уже существует')
            return render(request, 'animals/references/shelter_create.html', posted)
        
        try:
            shelter = Shelter.objects.create(
                shelter_name=shelter_name,
                address=address,
                phone=phone,
                email=email,
                description=description,
                is_active=is_active
            )
            
            # Логируем в аудитлог
            log_audit(
                table_name='Shelters',
                record_id=shelter.shelter_id,
                action='Create',
                changed_by=get_user_id_from_jwt(request),
                new_value=f"ShelterName: {shelter_name}, Address: {address or ''}, Phone: {phone or ''}, Email: {email or ''}"
            )
            
            messages.success(request, f'Приют "{shelter_name}" успешно создан')
            return redirect('shelter_list')
        except Exception as e:
            messages.error(request, f'Ошибка при создании: {str(e)}')
            return render(request, 'animals/references/shelter_create.html', posted)


class ShelterUpdateView(AdminRequiredMixin, View):
    """Редактирование приюта"""
    def get(self, request, pk):
        shelter = get_object_or_404(Shelter, pk=pk)
        return render(request, 'animals/references/shelter_update.html', {
            'shelter': shelter,
        })
    
    def post(self, request, pk):
        shelter = get_object_or_404(Shelter, pk=pk)
        posted = _posted_from_request(request)
        shelter_name = posted['shelter_name']
        address = posted['address'] or None
        description = posted['description'] or None
        is_active = posted['is_active']

        phone, phone_err = parse_shelter_phone(posted['phone'])
        email, email_err = clean_optional_email(posted['email'])

        if phone_err:
            messages.error(request, phone_err)
            return render(request, 'animals/references/shelter_update.html', {
                'shelter': shelter,
                'posted': posted,
            })
        if email_err:
            messages.error(request, email_err)
            return render(request, 'animals/references/shelter_update.html', {
                'shelter': shelter,
                'posted': posted,
            })
        
        if not shelter_name:
            messages.error(request, 'Укажите название приюта')
            return render(request, 'animals/references/shelter_update.html', {
                'shelter': shelter,
                'posted': posted,
            })
        
        if Shelter.objects.filter(shelter_name=shelter_name).exclude(pk=pk).exists():
            messages.error(request, 'Приют с таким названием уже существует')
            return render(request, 'animals/references/shelter_update.html', {
                'shelter': shelter,
                'posted': posted,
            })
        
        try:
            old_name = shelter.shelter_name
            old_address = shelter.address
            old_phone = shelter.phone
            old_email = shelter.email
            old_is_active = shelter.is_active
            
            shelter.shelter_name = shelter_name
            shelter.address = address
            shelter.phone = phone
            shelter.email = email
            shelter.description = description
            shelter.is_active = is_active
            shelter.save()
            
            # Логируем в аудитлог
            log_audit(
                table_name='Shelters',
                record_id=shelter.shelter_id,
                action='Update',
                changed_by=get_user_id_from_jwt(request),
                old_value=f"ShelterName: {old_name}, Address: {old_address or ''}, Phone: {old_phone or ''}, Email: {old_email or ''}, IsActive: {old_is_active}",
                new_value=f"ShelterName: {shelter_name}, Address: {address or ''}, Phone: {phone or ''}, Email: {email or ''}, IsActive: {is_active}"
            )
            
            messages.success(request, f'Приют успешно обновлён')
            return redirect('shelter_list')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
            return render(request, 'animals/references/shelter_update.html', {
                'shelter': shelter,
                'posted': posted,
            })


class ShelterDeleteView(AdminRequiredMixin, View):
    """Удаление приюта"""
    def post(self, request, pk):
        shelter = get_object_or_404(Shelter, pk=pk)
        shelter_name = shelter.shelter_name
        shelter_id = shelter.shelter_id
        
        # Проверяем, есть ли животные в этом приюте
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM Animals WHERE ShelterID = %s", [shelter_id])
            animals_count = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM News WHERE ShelterID = %s", [shelter_id])
            news_count = cursor.fetchone()[0] or 0
        
        if animals_count > 0 or news_count > 0:
            messages.error(request, f'Невозможно удалить приют "{shelter_name}", так как с ним связано {animals_count} животное(ых) и {news_count} новость(ей)')
            return redirect('shelter_list')
        
        try:
            shelter.delete()
            
            # Логируем в аудитлог
            log_audit(
                table_name='Shelters',
                record_id=shelter_id,
                action='Delete',
                changed_by=get_user_id_from_jwt(request),
                old_value=f"ShelterName: {shelter_name}"
            )
            
            messages.success(request, f'Приют "{shelter_name}" успешно удалён')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении: {str(e)}')
        
        return redirect('shelter_list')



