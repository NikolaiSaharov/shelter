from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from rest_framework import viewsets
from .models import Animal, AnimalType, Breed, AnimalStatus, AnimalCharacter
from news.models import News
from accounts.utils import get_user_id_from_jwt
from .serializers import (
    AnimalSerializer, AnimalTypeSerializer, BreedSerializer,
    AnimalStatusSerializer, AnimalCharacterSerializer
)

# DRF viewsets (API)
class AnimalViewSet(viewsets.ModelViewSet):
    queryset = Animal.objects.all()
    serializer_class = AnimalSerializer

class AnimalTypeViewSet(viewsets.ModelViewSet):
    queryset = AnimalType.objects.all()
    serializer_class = AnimalTypeSerializer

class BreedViewSet(viewsets.ModelViewSet):
    queryset = Breed.objects.all()
    serializer_class = BreedSerializer

class AnimalStatusViewSet(viewsets.ModelViewSet):
    queryset = AnimalStatus.objects.all()
    serializer_class = AnimalStatusSerializer

class AnimalCharacterViewSet(viewsets.ModelViewSet):
    queryset = AnimalCharacter.objects.all()
    serializer_class = AnimalCharacterSerializer

# Django frontend CBV
from django.views import View
class AnimalCatalogView(View):
    def get(self, request):
        from .models import Shelter
        animals = Animal.objects.select_related('status', 'breed', 'breed__type', 'character', 'shelter').all()
        all_breeds = Breed.objects.select_related('type').all()
        breeds = all_breeds
        statuses = AnimalStatus.objects.all()
        types = AnimalType.objects.all()
        characters = AnimalCharacter.objects.all()
        shelters = Shelter.objects.filter(is_active=True).order_by('shelter_name')

        q = request.GET.get('q')
        breed = request.GET.get('breed')
        status = request.GET.get('status')
        type_id = request.GET.get('type')
        gender = request.GET.get('gender')
        vaccinated = request.GET.get('vaccinated')
        character = request.GET.get('character')
        age_min = request.GET.get('age_min')
        age_max = request.GET.get('age_max')
        weight_min = request.GET.get('weight_min')
        weight_max = request.GET.get('weight_max')
        shelter_id = request.GET.get('shelter')

        if type_id:
            breeds = all_breeds.filter(type_id=type_id)

        if q:
            if any(char.isdigit() for char in q):
                from django.contrib import messages
                messages.warning(request, 'Поиск по имени не должен содержать цифры. Результаты могут быть неполными.')
            animals = animals.filter(animal_name__icontains=q)
        if breed:
            animals = animals.filter(breed_id=breed)
        if status:
            animals = animals.filter(status_id=status)
        if type_id:
            animals = animals.filter(breed__type_id=type_id)
        if gender:
            animals = animals.filter(gender=gender)
        if vaccinated in ['0', '1']:
            animals = animals.filter(vaccinated=(vaccinated == '1'))
        if character:
            animals = animals.filter(character_id=character)
        if age_min:
            animals = animals.filter(age__gte=age_min)
        if age_max:
            animals = animals.filter(age__lte=age_max)
        if weight_min:
            animals = animals.filter(animal_weight__gte=weight_min)
        if weight_max:
            animals = animals.filter(animal_weight__lte=weight_max)
        if shelter_id:
            animals = animals.filter(shelter_id=shelter_id)

        from datetime import date
        from django.db import connection
        today = date.today()
        animals_with_days = []
        for animal in animals:
            days_in_shelter = None
            if animal.admission_date:
                days_in_shelter = (today - animal.admission_date).days
            
            has_approved_application = False
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM Applications a
                    JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                    WHERE a.AnimalID = %s AND ast.StatusName = 'Approved'
                """, [animal.animal_id])
                result = cursor.fetchone()
                has_approved_application = result[0] > 0 if result else False
            
            animals_with_days.append({
                'animal': animal,
                'days_in_shelter': days_in_shelter,
                'has_approved_application': has_approved_application,
            })
        
        return render(request, 'animals/catalog.html', {
            'animals_data': animals_with_days,
            'breeds': breeds,
            'all_breeds': all_breeds,
            'statuses': statuses,
            'types': types,
            'characters': characters,
            'shelters': shelters,
        })

class AnimalDetailView(View):
    def get(self, request, pk):
        from datetime import date
        from django.db import connection
        
        animal = get_object_or_404(Animal.objects.select_related('breed', 'status', 'character', 'shelter'), pk=pk)
        
        is_admin_or_manager = False
        user_id = get_user_id_from_jwt(request)
        if user_id:
            try:
                from accounts.models import User
                user = User.objects.select_related('role').get(pk=user_id)
                user_role = user.role.role_name if user.role else None
                is_admin_or_manager = user_role in ['Admin', 'Manager']
            except:
                pass
        
        days_in_shelter = None
        if animal.admission_date:
            today = date.today()
            days_in_shelter = (today - animal.admission_date).days
        
        has_approved_application = False
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM Applications a
                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                WHERE a.AnimalID = %s AND ast.StatusName = 'Approved'
            """, [pk])
            result = cursor.fetchone()
            has_approved_application = result[0] > 0 if result else False
        
        from animals.models import AnimalMedia
        media_files = AnimalMedia.objects.filter(animal=animal).order_by('display_order', 'media_id')
        photos = [m for m in media_files if m.media_type == 'Photo']
        videos = [m for m in media_files if m.media_type == 'Video']
        
        height_cm = None
        if animal.height is not None:
            height_cm = float(animal.height) * 100
        
        return render(request, 'animals/detail.html', {
            'animal': animal,
            'days_in_shelter': days_in_shelter,
            'height_cm': height_cm,
            'has_approved_application': has_approved_application,
            'is_admin_or_manager': is_admin_or_manager,
            'photos': photos,
            'videos': videos,
            'all_media': list(photos) + list(videos),
        })

from django.db import connection
from django.contrib import messages
from django.core.files.storage import default_storage
from accounts.models import UserProfile, User
import urllib.request
import re

IMAGE_EXT_RE = re.compile(r"\.(png|jpe?g|gif|webp|bmp|svg)(\?.*)?$", re.IGNORECASE)

def _save_image_from_url(url: str, user_id: int) -> str | None:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                return None
            data = resp.read()
            ext = '.jpg'
            if 'png' in content_type:
                ext = '.png'
            elif 'webp' in content_type:
                ext = '.webp'
            elif 'gif' in content_type:
                ext = '.gif'
            from django.utils import timezone
            filename = f"animals/media/photo_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
            saved_path = default_storage.save(filename, data)
            return default_storage.url(saved_path)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'Не удалось скачать изображение по URL {url}: {e}')
        return None

from .mixins import AdminRequiredMixin
from django.utils import timezone
import os

class AnimalListView(AdminRequiredMixin, View):
    def get(self, request):
        from django.core.paginator import Paginator
        
        animals = Animal.objects.select_related('status', 'breed', 'breed__type', 'character').all().order_by('-animal_id')
        
        q = request.GET.get('q')
        if q:
            animals = animals.filter(animal_name__icontains=q)
        
        status_filter = request.GET.get('status')
        if status_filter:
            animals = animals.filter(status_id=status_filter)
        
        paginator = Paginator(animals, 20)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'animals/admin/list.html', {
            'page_obj': page_obj,
            'animals': page_obj,
            'statuses': AnimalStatus.objects.all(),
        })

class AnimalCreateView(AdminRequiredMixin, View):
    def get(self, request):
        from .models import Shelter
        return render(request, 'animals/admin/create.html', {
            'breeds': Breed.objects.select_related('type').all(),
            'statuses': AnimalStatus.objects.all(),
            'characters': AnimalCharacter.objects.all(),
            'types': AnimalType.objects.all(),
            'shelters': Shelter.objects.filter(is_active=True).order_by('shelter_name'),
        })
    
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        animal_name = (request.POST.get('animal_name') or '').strip()
        age = request.POST.get('age')
        gender = request.POST.get('gender', '').strip()
        vaccinated = request.POST.get('vaccinated') == 'on'
        description = (request.POST.get('description') or '').strip() or None
        image_file = request.FILES.get('image') or request.FILES.get('image_file')
        breed_id = request.POST.get('breed_id')
        status_id = request.POST.get('status_id')
        if not status_id:
            default_status = AnimalStatus.objects.filter(status_name__in=['Доступен', 'Available']).order_by('status_id').first()
            status_id = str(default_status.status_id) if default_status else '1'
        character_id = request.POST.get('character_id') or None
        shelter_id = request.POST.get('shelter_id') or None
        height = request.POST.get('height') or None
        height_unit = request.POST.get('height_unit', 'cm')
        animal_weight = request.POST.get('animal_weight') or None
        admission_date = request.POST.get('admission_date') or None
        
        errors = []
        if not animal_name:
            errors.append('Укажите имя животного')
        elif any(char.isdigit() for char in animal_name):
            errors.append('Имя животного не должно содержать цифры')
        
        if not age or not age.isdigit():
            errors.append('Укажите корректный возраст')
        if gender not in ['Male', 'Female', 'Unknown', 'Мужской', 'Женский', 'М', 'Ж']:
            errors.append('Укажите пол')
        if not breed_id:
            errors.append('Выберите породу')
        
        height_float = None
        if not height or not height.strip():
            errors.append('Укажите рост (обязательное поле)')
        else:
            height_normalized = height.strip().replace(',', '.')
            try:
                height_value = float(height_normalized)
                if height_value <= 0:
                    errors.append('Рост должен быть больше 0')
                else:
                    if height_unit == 'cm':
                        height_float = height_value / 100.0
                    else:
                        height_float = height_value
            except ValueError:
                errors.append('Укажите корректный рост (число)')
        
        weight_float = None
        if not animal_weight or not animal_weight.strip():
            errors.append('Укажите вес (обязательное поле)')
        else:
            weight_normalized = animal_weight.strip().replace(',', '.')
            try:
                weight_float = float(weight_normalized)
                if weight_float < 0:
                    errors.append('Вес не может быть отрицательным')
            except ValueError:
                errors.append('Укажите корректный вес (число)')
        
        if errors:
            from .models import Shelter
            for error in errors:
                messages.error(request, error, extra_tags='animal_create_page')
            return render(request, 'animals/admin/create.html', {
                'breeds': Breed.objects.select_related('type').all(),
                'statuses': AnimalStatus.objects.all(),
                'characters': AnimalCharacter.objects.all(),
                'types': AnimalType.objects.all(),
                'shelters': Shelter.objects.filter(is_active=True).order_by('shelter_name'),
                'animal_name': animal_name,
                'age': age,
                'gender': gender,
                'vaccinated': vaccinated,
                'description': description,
                'breed_id': breed_id,
                'status_id': status_id,
                'character_id': character_id,
                'shelter_id': shelter_id,
                'height': height,
                'height_unit': height_unit,
                'animal_weight': animal_weight,
                'admission_date': admission_date,
            })
        
        if gender in ['М', 'Мужской']:
            gender = 'Male'
        elif gender in ['Ж', 'Женский']:
            gender = 'Female'
        elif gender not in ['Male', 'Female', 'Unknown']:
            gender = 'Unknown'
        
        admission_date_obj = None
        if admission_date:
            try:
                admission_date_obj = timezone.datetime.strptime(admission_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append('Укажите корректную дату поступления')
        
        try:
            animal = Animal.objects.create(
                animal_name=animal_name,
                age=int(age),
                gender=gender,
                vaccinated=vaccinated,
                description=description,
                breed_id=int(breed_id),
                status_id=int(status_id),
                character_id=int(character_id) if character_id else None,
                shelter_id=int(shelter_id) if shelter_id else None,
                height=height_float,
                animal_weight=weight_float,
                admission_date=admission_date_obj,
            )
            
            # Сохраняем изображение через ImageField
            if image_file:
                animal.image = image_file
                animal.save()
            
            from animals.models import AnimalMedia
            user_id = get_user_id_from_jwt(request) or 0
            
            # Обработка загруженных фото
            photo_files_list = request.FILES.getlist('photo_files')
            photo_order = 0
            for photo_file in photo_files_list:
                if photo_file:
                    ext = os.path.splitext(photo_file.name)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        filename = f"animals/media/{animal.animal_id}/photo_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{photo_order}{ext}"
                        saved_path = default_storage.save(filename, photo_file)
                        media_path = default_storage.url(saved_path)
                        AnimalMedia.objects.create(
                            animal=animal,
                            media_type='Photo',
                            media_path=media_path[:500],
                            display_order=photo_order,
                            is_primary=(photo_order == 0)
                        )
                        photo_order += 1
            
            # Обработка URL фото
            photo_urls_text = request.POST.get('photo_urls', '').strip()
            if photo_urls_text:
                photo_urls = [url.strip() for url in photo_urls_text.split('\n') if url.strip()]
                for photo_url in photo_urls:
                    if photo_url:
                        final_photo_url = photo_url[:500]
                        if not IMAGE_EXT_RE.search(photo_url):
                            stored = _save_image_from_url(photo_url, user_id)
                            if stored:
                                final_photo_url = stored
                        
                        AnimalMedia.objects.create(
                            animal=animal,
                            media_type='Photo',
                            media_path=final_photo_url,
                            display_order=photo_order,
                            is_primary=(photo_order == 0 and not photo_files_list)
                        )
                        photo_order += 1
            
            # Если нет медиа, но есть image, создаем
            if animal.image and photo_order == 0 and not photo_files_list:
                AnimalMedia.objects.create(
                    animal=animal,
                    media_type='Photo',
                    media_path=animal.image.url[:500],
                    display_order=0,
                    is_primary=True
                )
            
            # Обработка видео
            video_files_list = request.FILES.getlist('video_files')
            video_order = photo_order
            for video_file in video_files_list:
                if video_file:
                    ext = os.path.splitext(video_file.name)[1].lower()
                    if ext in ['.mp4', '.webm', '.ogg', '.mov']:
                        filename = f"animals/media/{animal.animal_id}/video_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{video_order}{ext}"
                        saved_path = default_storage.save(filename, video_file)
                        media_path = default_storage.url(saved_path)
                        AnimalMedia.objects.create(
                            animal=animal,
                            media_type='Video',
                            media_path=media_path[:500],
                            display_order=video_order
                        )
                        video_order += 1
            
            video_urls_text = request.POST.get('video_urls', '').strip()
            if video_urls_text:
                video_urls = [url.strip() for url in video_urls_text.split('\n') if url.strip()]
                for video_url in video_urls:
                    if video_url:
                        AnimalMedia.objects.create(
                            animal=animal,
                            media_type='Video',
                            media_path=video_url[:500],
                            display_order=video_order
                        )
                        video_order += 1

            # Синхронизация главного фото
            try:
                primary_photo = AnimalMedia.objects.filter(animal=animal, media_type='Photo').order_by('display_order', 'media_id').first()
                if primary_photo and primary_photo.media_path:
                    if not animal.image:
                        # Загружаем изображение в Cloudinary из URL
                        import requests
                        from django.core.files.base import ContentFile
                        response = requests.get(primary_photo.media_path)
                        if response.status_code == 200:
                            animal.image.save(f'animal_{animal.animal_id}.jpg', ContentFile(response.content), save=True)
            except Exception:
                logger.exception('Failed to sync primary photo')

            try:
                author_user_id = get_user_id_from_jwt(request)
                news_title = f"Новый питомец: {animal.animal_name}"
                news_content = f"У нас новый питомец \"{animal.animal_name}\""
                news_image_path = animal.image.url if animal.image else None
                if not news_image_path:
                    primary_photo = AnimalMedia.objects.filter(animal=animal, media_type='Photo').order_by('-is_primary', 'display_order').first()
                    if primary_photo:
                        news_image_path = primary_photo.media_path

                News.objects.create(
                    user_id=author_user_id,
                    title=news_title,
                    content=news_content,
                    is_published=True,
                    image_path=(news_image_path[:255] if news_image_path else None),
                )
            except Exception as news_err:
                logger.warning(f'Не удалось автоматически создать новость: {news_err}')
            
            messages.success(request, f'Животное "{animal_name}" успешно создано.')
            return redirect('animal_admin_list')
        except Exception as e:
            import traceback
            messages.error(request, f'Ошибка при создании: {str(e)}')
            return render(request, 'animals/admin/create.html', {
                'breeds': Breed.objects.select_related('type').all(),
                'statuses': AnimalStatus.objects.all(),
                'characters': AnimalCharacter.objects.all(),
                'types': AnimalType.objects.all(),
                'animal_name': animal_name,
                'age': age,
                'gender': gender,
                'vaccinated': vaccinated,
                'description': description,
                'breed_id': breed_id,
                'status_id': status_id,
                'character_id': character_id,
                'height': height,
                'height_unit': height_unit,
                'animal_weight': animal_weight,
                'admission_date': admission_date,
            })

class AnimalUpdateView(AdminRequiredMixin, View):
    def get(self, request, pk):
        from animals.models import AnimalMedia
        from .models import Shelter
        animal = get_object_or_404(Animal.objects.select_related('breed', 'status', 'character'), pk=pk)
        media_files = AnimalMedia.objects.filter(animal=animal).order_by('display_order', 'media_id')
        height_cm = animal.height * 100 if animal.height else None
        return render(request, 'animals/admin/update.html', {
            'animal': animal,
            'breeds': Breed.objects.select_related('type').all(),
            'statuses': AnimalStatus.objects.all(),
            'characters': AnimalCharacter.objects.all(),
            'types': AnimalType.objects.all(),
            'shelters': Shelter.objects.filter(is_active=True).order_by('shelter_name'),
            'media_files': media_files,
            'height_cm': height_cm,
        })
    
    def post(self, request, pk):
        import logging
        logger = logging.getLogger(__name__)
        
        animal = get_object_or_404(Animal, pk=pk)
        user_id = get_user_id_from_jwt(request) or 0
        animal_name = (request.POST.get('animal_name') or '').strip()
        age = request.POST.get('age')
        gender = request.POST.get('gender', '').strip()
        vaccinated = request.POST.get('vaccinated') == 'on'
        description = (request.POST.get('description') or '').strip() or None
        image_file = request.FILES.get('image')
        breed_id = request.POST.get('breed_id')
        status_id = request.POST.get('status_id')
        if not status_id:
            default_status = AnimalStatus.objects.filter(status_name__in=['Доступен', 'Available']).order_by('status_id').first()
            status_id = str(default_status.status_id) if default_status else '1'
        character_id = request.POST.get('character_id') or None
        shelter_id = request.POST.get('shelter_id') or None
        height = request.POST.get('height') or None
        height_unit = request.POST.get('height_unit', 'cm')
        animal_weight = request.POST.get('animal_weight') or None
        admission_date = request.POST.get('admission_date') or None
        
        errors = []
        if not animal_name:
            errors.append('Укажите имя животного')
        elif any(char.isdigit() for char in animal_name):
            errors.append('Имя животного не должно содержать цифры')
        
        if not age or not age.isdigit():
            errors.append('Укажите корректный возраст')
        if gender not in ['Male', 'Female', 'Unknown', 'Мужской', 'Женский', 'М', 'Ж']:
            errors.append('Укажите пол')
        if not breed_id:
            errors.append('Выберите породу')
        
        height_float = None
        if not height or not height.strip():
            errors.append('Укажите рост (обязательное поле)')
        else:
            height_normalized = height.strip().replace(',', '.')
            try:
                height_value = float(height_normalized)
                if height_value <= 0:
                    errors.append('Рост должен быть больше 0')
                else:
                    if height_unit == 'cm':
                        height_float = height_value / 100.0
                    else:
                        height_float = height_value
            except ValueError:
                errors.append('Укажите корректный рост (число)')
        
        weight_float = None
        if not animal_weight or not animal_weight.strip():
            errors.append('Укажите вес (обязательное поле)')
        else:
            weight_normalized = animal_weight.strip().replace(',', '.')
            try:
                weight_float = float(weight_normalized)
                if weight_float < 0:
                    errors.append('Вес не может быть отрицательным')
            except ValueError:
                errors.append('Укажите корректный вес (число)')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'animals/admin/update.html', {
                'animal': animal,
                'breeds': Breed.objects.select_related('type').all(),
                'statuses': AnimalStatus.objects.all(),
                'characters': AnimalCharacter.objects.all(),
                'types': AnimalType.objects.all(),
            })
        
        if gender in ['М', 'Мужской']:
            gender = 'Male'
        elif gender in ['Ж', 'Женский']:
            gender = 'Female'
        elif gender not in ['Male', 'Female', 'Unknown']:
            gender = 'Unknown'
        
        admission_date_obj = None
        if admission_date:
            try:
                admission_date_obj = timezone.datetime.strptime(admission_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append('Укажите корректную дату поступления')
        
        try:
            animal.animal_name = animal_name
            animal.age = int(age)
            animal.gender = gender
            animal.vaccinated = vaccinated
            animal.description = description
            animal.breed_id = int(breed_id)
            animal.status_id = int(status_id)
            animal.character_id = int(character_id) if character_id else None
            animal.shelter_id = int(shelter_id) if shelter_id else None
            animal.height = height_float
            animal.animal_weight = weight_float
            animal.admission_date = admission_date_obj
            
            if image_file:
                animal.image = image_file
            
            animal.save()
            
            from animals.models import AnimalMedia
            
            # Удаление медиа-файлов
            deleted_media_ids = request.POST.get('deleted_media_ids', '').strip()
            if deleted_media_ids:
                try:
                    media_ids = [int(id.strip()) for id in deleted_media_ids.split(',') if id.strip()]
                    for media_id in media_ids:
                        try:
                            media = AnimalMedia.objects.get(media_id=media_id, animal=animal)
                            media.delete()
                        except AnimalMedia.DoesNotExist:
                            pass
                except (ValueError, Exception):
                    pass
            
            # Сохранение новых медиа-файлов
            existing_media = AnimalMedia.objects.filter(animal=animal)
            max_order = existing_media.aggregate(models.Max('display_order'))['display_order__max'] or -1
            photo_order = max_order + 1
            
            photo_files_list = request.FILES.getlist('photo_files')
            for photo_file in photo_files_list:
                if photo_file:
                    ext = os.path.splitext(photo_file.name)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        filename = f"animals/media/{animal.animal_id}/photo_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{photo_order}{ext}"
                        saved_path = default_storage.save(filename, photo_file)
                        media_path = default_storage.url(saved_path)
                        AnimalMedia.objects.create(
                            animal=animal,
                            media_type='Photo',
                            media_path=media_path[:500],
                            display_order=photo_order,
                            is_primary=False
                        )
                        photo_order += 1
            
            photo_urls_text = request.POST.get('photo_urls', '').strip()
            if photo_urls_text:
                photo_urls = [url.strip() for url in photo_urls_text.split('\n') if url.strip()]
                for photo_url in photo_urls:
                    if photo_url:
                        final_photo_url = photo_url[:500]
                        if not IMAGE_EXT_RE.search(photo_url):
                            stored = _save_image_from_url(photo_url, user_id)
                            if stored:
                                final_photo_url = stored
                        
                        AnimalMedia.objects.create(
                            animal=animal,
                            media_type='Photo',
                            media_path=final_photo_url,
                            display_order=photo_order,
                            is_primary=False
                        )
                        photo_order += 1
            
            video_files_list = request.FILES.getlist('video_files')
            video_order = photo_order
            for video_file in video_files_list:
                if video_file:
                    ext = os.path.splitext(video_file.name)[1].lower()
                    if ext in ['.mp4', '.webm', '.ogg', '.mov']:
                        filename = f"animals/media/{animal.animal_id}/video_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{video_order}{ext}"
                        saved_path = default_storage.save(filename, video_file)
                        media_path = default_storage.url(saved_path)
                        AnimalMedia.objects.create(
                            animal=animal,
                            media_type='Video',
                            media_path=media_path[:500],
                            display_order=video_order
                        )
                        video_order += 1
            
            video_urls_text = request.POST.get('video_urls', '').strip()
            if video_urls_text:
                video_urls = [url.strip() for url in video_urls_text.split('\n') if url.strip()]
                for video_url in video_urls:
                    if video_url:
                        AnimalMedia.objects.create(
                            animal=animal,
                            media_type='Video',
                            media_path=video_url[:500],
                            display_order=video_order
                        )
                        video_order += 1

            # Синхронизация главного фото
            try:
                primary_photo = AnimalMedia.objects.filter(animal=animal, media_type='Photo').order_by('display_order', 'media_id').first()
                if primary_photo and primary_photo.media_path:
                    if not animal.image:
                        import requests
                        from django.core.files.base import ContentFile
                        response = requests.get(primary_photo.media_path)
                        if response.status_code == 200:
                            animal.image.save(f'animal_{animal.animal_id}.jpg', ContentFile(response.content), save=True)
            except Exception:
                logger.exception('Failed to sync primary photo')
            
            messages.success(request, f'Животное "{animal_name}" успешно обновлено.')
            return redirect('animal_admin_list')
        except Exception as e:
            import traceback
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
            return render(request, 'animals/admin/update.html', {
                'animal': animal,
                'breeds': Breed.objects.select_related('type').all(),
                'statuses': AnimalStatus.objects.all(),
                'characters': AnimalCharacter.objects.all(),
                'types': AnimalType.objects.all(),
            })

class AnimalDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        animal = get_object_or_404(Animal, pk=pk)
        animal_name = animal.animal_name
        try:
            animal.delete()
            messages.success(request, f'Животное "{animal_name}" успешно удалено')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении: {str(e)}')
        return redirect('animal_admin_list')

class ApplicationCreateView(View):
    def post(self, request):
        user_id = get_user_id_from_jwt(request)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if not user_id:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Требуется авторизация'}, status=401)
            return redirect('login')
        try:
            user = User.objects.select_related('role').get(pk=user_id)
            profile, _ = UserProfile.objects.get_or_create(user=user)
        except Exception:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Заполните профиль перед подачей заявки'}, status=400)
            messages.error(request, 'Заполните профиль перед подачей заявки')
            return redirect('profile')
        
        user_role = user.role.role_name if user.role else None
        if user_role in ['Admin', 'Manager']:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Менеджеры и администраторы не могут подавать заявки на усыновление'}, status=403)
            messages.error(request, 'Менеджеры и администраторы не могут подавать заявки на усыновление')
            animal_id = request.POST.get('animal_id')
            return redirect(f"/animals/{animal_id or ''}/")
        
        if not profile.home_address or not profile.date_of_birth:
            if is_ajax:
                missing = []
                if not profile.home_address:
                    missing.append('home_address')
                if not profile.date_of_birth:
                    missing.append('date_of_birth')
                return JsonResponse(
                    {
                        'success': False,
                        'error': 'Заполните адрес и дату рождения в профиле',
                        'error_code': 'profile_incomplete',
                        'missing_fields': missing,
                    },
                    status=400,
                )
            messages.error(request, 'Заполните адрес и дату рождения в профиле')
            return redirect('profile')

        animal_id = request.POST.get('animal_id')
        reason = (request.POST.get('reason') or '').strip()
        experience = (request.POST.get('experience') or '').strip() or None
        housing = (request.POST.get('housing') or '').strip() or None
        comment = (request.POST.get('comment') or '').strip() or None
        
        if not animal_id or not reason:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Укажите причину и выберите питомца'}, status=400)
            messages.error(request, 'Укажите причину и выберите питомца')
            return redirect(f"/animals/{animal_id or ''}/")
        
        with connection.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM Applications a
                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                WHERE a.UserID = %s 
                AND a.AnimalID = %s 
                AND ast.StatusName = 'Pending'
            """, [user_id, int(animal_id)])
            existing_pending = cur.fetchone()[0]
            
            if existing_pending > 0:
                if is_ajax:
                    return JsonResponse({
                        'success': False, 
                        'error': 'У вас уже есть заявка на это животное, которая находится в ожидании.'
                    }, status=400)
                messages.error(request, 'У вас уже есть заявка на это животное, которая находится в ожидании.')
                return redirect(f"/animals/{animal_id or ''}/")
            
            cur.execute("SELECT StatusID FROM ApplicationStatuses WHERE StatusName = 'Pending'")
            pending_status_row = cur.fetchone()
            if not pending_status_row:
                if is_ajax:
                    return JsonResponse({'success': False, 'error': 'Ошибка базы данных: статус не найден'}, status=500)
                messages.error(request, 'Ошибка базы данных: статус не найден')
                return redirect(f"/animals/{animal_id or ''}/")
            
            pending_status_id = pending_status_row[0]
            
            cur.execute(
                """
                INSERT INTO Applications (UserID, AnimalID, StatusID, Reason, Experience, HousingConditions, Comment)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [user_id, int(animal_id), pending_status_id, reason, experience, housing, comment]
            )
        
        if is_ajax:
            return JsonResponse({'success': True, 'message': 'Заявка отправлена в обработку'})
        
        messages.success(request, 'Заявка отправлена')
        return redirect('/accounts/profile/?tab=applications')
