from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from .models import AnimalType, Breed, AnimalCharacter
from .mixins import AdminRequiredMixin
from accounts.audit_utils import log_audit
from accounts.utils import get_user_id_from_jwt


# ============= AnimalType CRUD =============

class AnimalTypeListView(AdminRequiredMixin, View):
    """Список типов животных"""
    def get(self, request):
        types = AnimalType.objects.all().order_by('type_name')
        return render(request, 'animals/references/type_list.html', {
            'types': types,
        })


class AnimalTypeCreateView(AdminRequiredMixin, View):
    """Создание типа животного"""
    def get(self, request):
        return render(request, 'animals/references/type_create.html')
    
    def post(self, request):
        type_name = (request.POST.get('type_name') or '').strip()
        
        import re
        title_pattern = re.compile(r'^[а-яА-ЯёЁa-zA-Z\s\-\']+$')
        
        if not type_name:
            messages.error(request, 'Укажите название типа')
            return render(request, 'animals/references/type_create.html', {
                'type_name': type_name,
            })
        
        if not title_pattern.match(type_name):
            messages.error(request, 'Название типа не должно содержать цифры и спецсимволы (кроме пробелов, дефисов и апострофов)')
            return render(request, 'animals/references/type_create.html', {
                'type_name': type_name,
            })
        
        if AnimalType.objects.filter(type_name=type_name).exists():
            messages.error(request, 'Тип с таким названием уже существует')
            return render(request, 'animals/references/type_create.html', {
                'type_name': type_name,
            })
        
        try:
            animal_type = AnimalType.objects.create(type_name=type_name)
            
            # Логируем в аудитлог
            log_audit(
                table_name='AnimalTypes',
                record_id=animal_type.type_id,
                action='Create',
                changed_by=get_user_id_from_jwt(request),
                new_value=f"TypeName: {type_name}"
            )
            
            messages.success(request, f'Тип "{type_name}" успешно создан')
            return redirect('animal_type_list')
        except Exception as e:
            messages.error(request, f'Ошибка при создании: {str(e)}')
            return render(request, 'animals/references/type_create.html', {
                'type_name': type_name,
            })


class AnimalTypeUpdateView(AdminRequiredMixin, View):
    """Редактирование типа животного"""
    def get(self, request, pk):
        animal_type = get_object_or_404(AnimalType, pk=pk)
        return render(request, 'animals/references/type_update.html', {
            'animal_type': animal_type,
        })
    
    def post(self, request, pk):
        animal_type = get_object_or_404(AnimalType, pk=pk)
        type_name = (request.POST.get('type_name') or '').strip()
        
        import re
        title_pattern = re.compile(r'^[а-яА-ЯёЁa-zA-Z\s\-\']+$')
        
        if not type_name:
            messages.error(request, 'Укажите название типа')
            return render(request, 'animals/references/type_update.html', {
                'animal_type': animal_type,
            })
        
        if not title_pattern.match(type_name):
            messages.error(request, 'Название типа не должно содержать цифры и спецсимволы (кроме пробелов, дефисов и апострофов)')
            return render(request, 'animals/references/type_update.html', {
                'animal_type': animal_type,
            })
        
        if AnimalType.objects.filter(type_name=type_name).exclude(pk=pk).exists():
            messages.error(request, 'Тип с таким названием уже существует')
            return render(request, 'animals/references/type_update.html', {
                'animal_type': animal_type,
            })
        
        try:
            old_name = animal_type.type_name
            animal_type.type_name = type_name
            animal_type.save()
            
            # Логируем в аудитлог
            log_audit(
                table_name='AnimalTypes',
                record_id=animal_type.type_id,
                action='Update',
                changed_by=get_user_id_from_jwt(request),
                old_value=f"TypeName: {old_name}",
                new_value=f"TypeName: {type_name}"
            )
            
            messages.success(request, f'Тип успешно обновлён')
            return redirect('animal_type_list')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
            return render(request, 'animals/references/type_update.html', {
                'animal_type': animal_type,
            })


class AnimalTypeDeleteView(AdminRequiredMixin, View):
    """Удаление типа животного"""
    def post(self, request, pk):
        animal_type = get_object_or_404(AnimalType, pk=pk)
        type_name = animal_type.type_name
        type_id = animal_type.type_id
        
        # Проверяем, есть ли породы с этим типом
        breeds_count = Breed.objects.filter(type=animal_type).count()
        if breeds_count > 0:
            messages.error(request, f'Невозможно удалить тип "{type_name}", так как с ним связано {breeds_count} пород(ы)')
            return redirect('animal_type_list')
        
        try:
            animal_type.delete()
            
            # Логируем в аудитлог
            log_audit(
                table_name='AnimalTypes',
                record_id=type_id,
                action='Delete',
                changed_by=get_user_id_from_jwt(request),
                old_value=f"TypeName: {type_name}"
            )
            
            messages.success(request, f'Тип "{type_name}" успешно удалён')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении: {str(e)}')
        
        return redirect('animal_type_list')


# ============= Breed CRUD =============

class BreedListView(AdminRequiredMixin, View):
    """Список пород"""
    def get(self, request):
        breeds = Breed.objects.select_related('type').all().order_by('type__type_name', 'breed_name')
        return render(request, 'animals/references/breed_list.html', {
            'breeds': breeds,
        })


class BreedCreateView(AdminRequiredMixin, View):
    """Создание породы"""
    def get(self, request):
        types = AnimalType.objects.all().order_by('type_name')
        return render(request, 'animals/references/breed_create.html', {
            'types': types,
        })
    
    def post(self, request):
        breed_name = (request.POST.get('breed_name') or '').strip()
        type_id = request.POST.get('type_id')
        
        import re
        title_pattern = re.compile(r'^[а-яА-ЯёЁa-zA-Z\s\-\']+$')
        
        errors = []
        if not breed_name:
            errors.append('Укажите название породы')
        elif not title_pattern.match(breed_name):
            errors.append('Название породы не должно содержать цифры и спецсимволы (кроме пробелов, дефисов и апострофов)')
        if not type_id:
            errors.append('Выберите тип животного')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            types = AnimalType.objects.all().order_by('type_name')
            return render(request, 'animals/references/breed_create.html', {
                'types': types,
                'breed_name': breed_name,
                'type_id': type_id,
            })
        
        if Breed.objects.filter(breed_name=breed_name).exists():
            messages.error(request, 'Порода с таким названием уже существует')
            types = AnimalType.objects.all().order_by('type_name')
            return render(request, 'animals/references/breed_create.html', {
                'types': types,
                'breed_name': breed_name,
                'type_id': type_id,
            })
        
        try:
            breed = Breed.objects.create(
                breed_name=breed_name,
                type_id=int(type_id)
            )
            
            # Логируем в аудитлог
            log_audit(
                table_name='Breeds',
                record_id=breed.breed_id,
                action='Create',
                changed_by=get_user_id_from_jwt(request),
                new_value=f"BreedName: {breed_name}, TypeID: {type_id}"
            )
            
            messages.success(request, f'Порода "{breed_name}" успешно создана')
            return redirect('breed_list')
        except Exception as e:
            messages.error(request, f'Ошибка при создании: {str(e)}')
            types = AnimalType.objects.all().order_by('type_name')
            return render(request, 'animals/references/breed_create.html', {
                'types': types,
                'breed_name': breed_name,
                'type_id': type_id,
            })


class BreedUpdateView(AdminRequiredMixin, View):
    """Редактирование породы"""
    def get(self, request, pk):
        breed = get_object_or_404(Breed.objects.select_related('type'), pk=pk)
        types = AnimalType.objects.all().order_by('type_name')
        return render(request, 'animals/references/breed_update.html', {
            'breed': breed,
            'types': types,
        })
    
    def post(self, request, pk):
        breed = get_object_or_404(Breed, pk=pk)
        breed_name = (request.POST.get('breed_name') or '').strip()
        type_id = request.POST.get('type_id')
        
        import re
        title_pattern = re.compile(r'^[а-яА-ЯёЁa-zA-Z\s\-\']+$')
        
        errors = []
        if not breed_name:
            errors.append('Укажите название породы')
        elif not title_pattern.match(breed_name):
            errors.append('Название породы не должно содержать цифры и спецсимволы (кроме пробелов, дефисов и апострофов)')
        if not type_id:
            errors.append('Выберите тип животного')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            types = AnimalType.objects.all().order_by('type_name')
            return render(request, 'animals/references/breed_update.html', {
                'breed': breed,
                'types': types,
            })
        
        if Breed.objects.filter(breed_name=breed_name).exclude(pk=pk).exists():
            messages.error(request, 'Порода с таким названием уже существует')
            types = AnimalType.objects.all().order_by('type_name')
            return render(request, 'animals/references/breed_update.html', {
                'breed': breed,
                'types': types,
            })
        
        try:
            old_name = breed.breed_name
            old_type = breed.type_id
            breed.breed_name = breed_name
            breed.type_id = int(type_id)
            breed.save()
            
            # Логируем в аудитлог
            log_audit(
                table_name='Breeds',
                record_id=breed.breed_id,
                action='Update',
                changed_by=get_user_id_from_jwt(request),
                old_value=f"BreedName: {old_name}, TypeID: {old_type}",
                new_value=f"BreedName: {breed_name}, TypeID: {type_id}"
            )
            
            messages.success(request, f'Порода успешно обновлена')
            return redirect('breed_list')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
            types = AnimalType.objects.all().order_by('type_name')
            return render(request, 'animals/references/breed_update.html', {
                'breed': breed,
                'types': types,
            })


class BreedDeleteView(AdminRequiredMixin, View):
    """Удаление породы"""
    def post(self, request, pk):
        breed = get_object_or_404(Breed, pk=pk)
        breed_name = breed.breed_name
        breed_id = breed.breed_id
        
        # Проверяем, есть ли животные с этой породой
        animals_count = breed.animal_set.count()
        if animals_count > 0:
            messages.error(request, f'Невозможно удалить породу "{breed_name}", так как с ней связано {animals_count} животное(ых)')
            return redirect('breed_list')
        
        try:
            breed.delete()
            
            # Логируем в аудитлог
            log_audit(
                table_name='Breeds',
                record_id=breed_id,
                action='Delete',
                changed_by=get_user_id_from_jwt(request),
                old_value=f"BreedName: {breed_name}"
            )
            
            messages.success(request, f'Порода "{breed_name}" успешно удалена')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении: {str(e)}')
        
        return redirect('breed_list')


# ============= AnimalCharacter CRUD =============

class AnimalCharacterListView(AdminRequiredMixin, View):
    """Список характеров животных"""
    def get(self, request):
        characters = AnimalCharacter.objects.all().order_by('character_name')
        return render(request, 'animals/references/character_list.html', {
            'characters': characters,
        })


class AnimalCharacterCreateView(AdminRequiredMixin, View):
    """Создание характера животного"""
    def get(self, request):
        return render(request, 'animals/references/character_create.html')
    
    def post(self, request):
        character_name = (request.POST.get('character_name') or '').strip()
        description = (request.POST.get('description') or '').strip() or None
        
        import re
        title_pattern = re.compile(r'^[а-яА-ЯёЁa-zA-Z\s\-\']+$')
        
        if not character_name:
            messages.error(request, 'Укажите название характера')
            return render(request, 'animals/references/character_create.html', {
                'character_name': character_name,
                'description': description,
            })
        
        if not title_pattern.match(character_name):
            messages.error(request, 'Название характера не должно содержать цифры и спецсимволы (кроме пробелов, дефисов и апострофов)')
            return render(request, 'animals/references/character_create.html', {
                'character_name': character_name,
                'description': description,
            })
        
        if AnimalCharacter.objects.filter(character_name=character_name).exists():
            messages.error(request, 'Характер с таким названием уже существует')
            return render(request, 'animals/references/character_create.html', {
                'character_name': character_name,
                'description': description,
            })
        
        try:
            character = AnimalCharacter.objects.create(
                character_name=character_name,
                description=description
            )
            
            # Логируем в аудитлог
            log_audit(
                table_name='AnimalCharacters',
                record_id=character.character_id,
                action='Create',
                changed_by=get_user_id_from_jwt(request),
                new_value=f"CharacterName: {character_name}, Description: {description or ''}"
            )
            
            messages.success(request, f'Характер "{character_name}" успешно создан')
            return redirect('character_list')
        except Exception as e:
            messages.error(request, f'Ошибка при создании: {str(e)}')
            return render(request, 'animals/references/character_create.html', {
                'character_name': character_name,
                'description': description,
            })


class AnimalCharacterUpdateView(AdminRequiredMixin, View):
    """Редактирование характера животного"""
    def get(self, request, pk):
        character = get_object_or_404(AnimalCharacter, pk=pk)
        return render(request, 'animals/references/character_update.html', {
            'character': character,
        })
    
    def post(self, request, pk):
        character = get_object_or_404(AnimalCharacter, pk=pk)
        character_name = (request.POST.get('character_name') or '').strip()
        description = (request.POST.get('description') or '').strip() or None
        
        import re
        title_pattern = re.compile(r'^[а-яА-ЯёЁa-zA-Z\s\-\']+$')
        
        if not character_name:
            messages.error(request, 'Укажите название характера')
            return render(request, 'animals/references/character_update.html', {
                'character': character,
            })
        
        if not title_pattern.match(character_name):
            messages.error(request, 'Название характера не должно содержать цифры и спецсимволы (кроме пробелов, дефисов и апострофов)')
            return render(request, 'animals/references/character_update.html', {
                'character': character,
            })
        
        if AnimalCharacter.objects.filter(character_name=character_name).exclude(pk=pk).exists():
            messages.error(request, 'Характер с таким названием уже существует')
            return render(request, 'animals/references/character_update.html', {
                'character': character,
            })
        
        try:
            old_name = character.character_name
            old_description = character.description
            character.character_name = character_name
            character.description = description
            character.save()
            
            # Логируем в аудитлог
            log_audit(
                table_name='AnimalCharacters',
                record_id=character.character_id,
                action='Update',
                changed_by=get_user_id_from_jwt(request),
                old_value=f"CharacterName: {old_name}, Description: {old_description or ''}",
                new_value=f"CharacterName: {character_name}, Description: {description or ''}"
            )
            
            messages.success(request, f'Характер успешно обновлён')
            return redirect('character_list')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
            return render(request, 'animals/references/character_update.html', {
                'character': character,
            })


class AnimalCharacterDeleteView(AdminRequiredMixin, View):
    """Удаление характера животного"""
    def post(self, request, pk):
        character = get_object_or_404(AnimalCharacter, pk=pk)
        character_name = character.character_name
        character_id = character.character_id
        
        try:
            character.delete()
            
            # Логируем в аудитлог
            log_audit(
                table_name='AnimalCharacters',
                record_id=character_id,
                action='Delete',
                changed_by=get_user_id_from_jwt(request),
                old_value=f"CharacterName: {character_name}"
            )
            
            messages.success(request, f'Характер "{character_name}" успешно удалён')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении: {str(e)}')
        
        return redirect('character_list')

