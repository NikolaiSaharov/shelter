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
            # Валидация поиска - не должно содержать цифры
            if any(char.isdigit() for char in q):
                # Если поиск содержит цифры, показываем предупреждение через messages
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

        # Добавляем счетчик дней и проверку одобренных заявок для каждого животного
        from datetime import date
        from django.db import connection
        today = date.today()
        animals_with_days = []
        for animal in animals:
            days_in_shelter = None
            if animal.admission_date:
                days_in_shelter = (today - animal.admission_date).days
            
            # Проверяем, есть ли одобренная заявка
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
        from django.utils import timezone
        from datetime import date
        from django.db import connection
        
        animal = get_object_or_404(Animal.objects.select_related('breed', 'status', 'character', 'shelter'), pk=pk)
        
        # Проверяем роль пользователя
        is_admin_or_manager = False
        user_id = get_user_id_from_jwt(request)
        if user_id:
            try:
                user = User.objects.select_related('role').get(pk=user_id)
                user_role = user.role.role_name if user.role else None
                is_admin_or_manager = user_role in ['Admin', 'Manager']
            except:
                pass
        
        # Считаем дни в приюте
        days_in_shelter = None
        if animal.admission_date:
            today = date.today()
            days_in_shelter = (today - animal.admission_date).days
        
        # Проверяем, есть ли одобренная заявка для этого животного
        has_approved_application = False
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM Applications a
                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                WHERE a.AnimalID = %s AND ast.StatusName = 'Approved'
            """, [pk])
            result = cursor.fetchone()
            has_approved_application = result[0] > 0 if result else False
        
        # Получаем медиа-файлы животного (фото и видео)
        from animals.models import AnimalMedia
        media_files = AnimalMedia.objects.filter(animal=animal).order_by('display_order', 'media_id')
        photos = [m for m in media_files if m.media_type == 'Photo']
        videos = [m for m in media_files if m.media_type == 'Video']
        
        # Если нет медиа-файлов, но есть старое изображение, используем его
        if not photos and animal.image_path:
            # Создаем временный объект для обратной совместимости
            pass
        
        # Конвертируем рост из метров в сантиметры для отображения
        height_cm = None
        if animal.height is not None:
            height_cm = float(animal.height) * 100
        
        return render(request, 'animals/detail.html', {
            'animal': animal,
            'days_in_shelter': days_in_shelter,
            'height_cm': height_cm,  # Рост в сантиметрах для отображения
            'has_approved_application': has_approved_application,
            'is_admin_or_manager': is_admin_or_manager,
            'photos': photos,
            'videos': videos,
            'all_media': list(photos) + list(videos),  # Все медиа в порядке отображения
        })

from django.db import connection
from django.contrib import messages
from django.core.files.storage import default_storage
from accounts.models import UserProfile, User
import urllib.request
import re

IMAGE_EXT_RE = re.compile(r"\.(png|jpe?g|gif|webp|bmp|svg)(\?.*)?$", re.IGNORECASE)

def _save_image_from_url(url: str, user_id: int) -> str | None:
    """Скачивает изображение по URL и сохраняет локально"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
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
            filename = f"animals/media/photo_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
            saved_path = default_storage.save(filename, bytes(data))
            return default_storage.url(saved_path)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'Не удалось скачать изображение по URL {url}: {e}')
        return None
from .mixins import AdminRequiredMixin
from django.utils import timezone
import os

# Admin CRUD views for animals
class AnimalListView(AdminRequiredMixin, View):
    """Список животных для админа"""
    def get(self, request):
        from django.core.paginator import Paginator
        
        animals = Animal.objects.select_related('status', 'breed', 'breed__type', 'character').all().order_by('-animal_id')
        
        # Поиск и фильтры
        q = request.GET.get('q')
        if q:
            animals = animals.filter(animal_name__icontains=q)
        
        status_filter = request.GET.get('status')
        if status_filter:
            animals = animals.filter(status_id=status_filter)
        
        # Пагинация - по 20 записей на страницу
        paginator = Paginator(animals, 20)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'animals/admin/list.html', {
            'page_obj': page_obj,
            'animals': page_obj,  # Для обратной совместимости
            'statuses': AnimalStatus.objects.all(),
        })

class AnimalCreateView(AdminRequiredMixin, View):
    """Создание нового животного"""
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
        logger.info(f'POST request received for creating animal')
        logger.info(f'POST data: {dict(request.POST)}')
        
        animal_name = (request.POST.get('animal_name') or '').strip()
        age = request.POST.get('age')
        gender = request.POST.get('gender', '').strip()
        vaccinated = request.POST.get('vaccinated') == 'on'
        description = (request.POST.get('description') or '').strip() or None
        image_path = (request.POST.get('image_path') or '').strip() or None
        image_file = request.FILES.get('image_file')  # Получаем загруженный файл
        breed_id = request.POST.get('breed_id')
        # Не полагаемся на "1": в БД ID могли поменяться. Берём дефолт по имени статуса.
        status_id = request.POST.get('status_id')
        if not status_id:
            default_status = AnimalStatus.objects.filter(status_name__in=['Доступен', 'Available']).order_by('status_id').first()
            status_id = str(default_status.status_id) if default_status else '1'
        character_id = request.POST.get('character_id') or None
        shelter_id = request.POST.get('shelter_id') or None
        height = request.POST.get('height') or None
        height_unit = request.POST.get('height_unit', 'cm')  # По умолчанию сантиметры
        animal_weight = request.POST.get('animal_weight') or None
        admission_date = request.POST.get('admission_date') or None
        
        errors = []
        # Валидация имени животного
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
        
        # Рост обязателен с проверкой на 0
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
                    # Конвертируем в метры для сохранения в БД
                    if height_unit == 'cm':
                        # Если введено в сантиметрах, конвертируем в метры
                        height_float = height_value / 100.0
                    else:
                        # Если введено в метрах, сохраняем как есть
                        height_float = height_value
            except ValueError:
                errors.append('Укажите корректный рост (число)')
        
        # Вес обязателен
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
                'image_path': image_path,
                'breed_id': breed_id,
                'status_id': status_id,
                'character_id': character_id,
                'shelter_id': shelter_id,
                'height': height,
                'height_unit': height_unit,
                'animal_weight': animal_weight,
                'admission_date': admission_date,
            })
        
        # Обработка загруженного изображения
        final_image_path = image_path
        if image_file:
            # Сохраняем загруженный файл
            ext = os.path.splitext(image_file.name)[1].lower()
            user_id = get_user_id_from_jwt(request) or 0
            filename = f"animals/animal_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
            saved_path = default_storage.save(filename, image_file)
            final_image_path = default_storage.url(saved_path)
        elif image_path:
            final_image_path = image_path[:255] if len(image_path) <= 255 else image_path[:255]
        
        # Нормализация пола - конвертируем русские значения в английские для БД
        if gender in ['М', 'Мужской']:
            gender = 'Male'
        elif gender in ['Ж', 'Женский']:
            gender = 'Female'
        elif gender not in ['Male', 'Female', 'Unknown']:
            gender = 'Unknown'
        
        # Обработка даты
        admission_date_obj = None
        if admission_date:
            try:
                admission_date_obj = timezone.datetime.strptime(admission_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append('Укажите корректную дату поступления')
        
        if errors:
            for error in errors:
                messages.error(request, error, extra_tags='animal_create_page')
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
                'image_path': image_path,
                'breed_id': breed_id,
                'status_id': status_id,
                'character_id': character_id,
                'height': height,
                'height_unit': height_unit,
                'animal_weight': animal_weight,
                'admission_date': admission_date,
            })
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'Creating animal with: height={height_float}, weight={weight_float}')
            
            animal = Animal.objects.create(
                animal_name=animal_name,
                age=int(age),
                gender=gender,
                vaccinated=vaccinated,
                description=description,
                image_path=final_image_path,
                breed_id=int(breed_id),
                status_id=int(status_id),
                character_id=int(character_id) if character_id else None,
                shelter_id=int(shelter_id) if shelter_id else None,
                height=height_float,
                animal_weight=weight_float,
                admission_date=admission_date_obj,
            )
            logger.info(f'Animal created successfully with ID: {animal.animal_id}')
            logger.info(f'Saved values: height={animal.height}, weight={animal.animal_weight}')
            
            # Сохранение медиа-файлов (фото и видео)
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
            
            # Обработка URL фото (разбиваем по строкам)
            photo_urls_text = request.POST.get('photo_urls', '').strip()
            if photo_urls_text:
                photo_urls = [url.strip() for url in photo_urls_text.split('\n') if url.strip()]
                for photo_url in photo_urls:
                    if photo_url:
                        final_photo_url = photo_url[:500]
                        # Если это прямая ссылка на изображение (с расширением), используем URL напрямую
                        # Только для URL без расширения пытаемся скачать
                        if IMAGE_EXT_RE.search(photo_url):
                            # Прямая ссылка на изображение - используем как есть
                            pass
                        else:
                            # Пытаемся скачать и сохранить локально
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
            
            # Если есть старое изображение и нет медиа-файлов, создаем его как первое фото
            if final_image_path and photo_order == 0 and not photo_files_list:
                AnimalMedia.objects.create(
                    animal=animal,
                    media_type='Photo',
                    media_path=final_image_path[:500],
                    display_order=0,
                    is_primary=True
                )
                photo_order += 1
            
            # Обработка загруженных видео
            video_files = request.FILES.getlist('video_files')
            video_order = 0
            for video_file in video_files:
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
                            display_order=photo_order + video_order  # Видео всегда после фото
                        )
                        video_order += 1
            
            # Обработка URL видео (разбиваем по строкам)
            # Поддерживаем любые URL: YouTube, VK, прямые ссылки на видео файлы и т.д.
            video_urls_text = request.POST.get('video_urls', '').strip()
            if video_urls_text:
                video_urls = [url.strip() for url in video_urls_text.split('\n') if url.strip()]
                for video_url in video_urls:
                    if video_url:
                        video_url = video_url[:500]
                        # Принимаем любой URL - YouTube, VK, прямые ссылки и т.д.
                        AnimalMedia.objects.create(
                            animal=animal,
                            media_type='Video',
                            media_path=video_url,
                            display_order=photo_order + video_order  # Видео всегда после фото
                        )
                        video_order += 1

            # Синхронизация: главное фото и Animals.ImagePath
            try:
                primary_photo = (
                    AnimalMedia.objects.filter(animal=animal, media_type='Photo')
                    .order_by('display_order', 'media_id')
                    .first()
                )
                if primary_photo:
                    AnimalMedia.objects.filter(animal=animal, media_type='Photo').exclude(media_id=primary_photo.media_id).update(is_primary=False)
                    if not primary_photo.is_primary:
                        AnimalMedia.objects.filter(media_id=primary_photo.media_id).update(is_primary=True)
                    new_image_path = (primary_photo.media_path or '')[:255]
                    if new_image_path and animal.image_path != new_image_path:
                        Animal.objects.filter(pk=animal.pk).update(image_path=new_image_path)
                        animal.image_path = new_image_path
            except Exception:
                logger.exception('Failed to sync primary photo and image_path on create')

            # Автоматически создаём новость о новом животном
            try:
                author_user_id = get_user_id_from_jwt(request)
                news_title = f"Новый питомец: {animal.animal_name}"
                news_content = f"У нас новый питомец \"{animal.animal_name}\""
                # Для новости берём фото максимально надёжно:
                # 1) Animals.image_path после синхронизации
                # 2) primary/первое фото из AnimalMedia
                animal.refresh_from_db(fields=['image_path'])
                news_image_path = (animal.image_path or '').strip() or None
                if not news_image_path:
                    primary_photo = (
                        AnimalMedia.objects.filter(animal=animal, media_type='Photo')
                        .order_by('-is_primary', 'display_order', 'media_id')
                        .first()
                    )
                    if primary_photo and primary_photo.media_path:
                        news_image_path = primary_photo.media_path.strip()

                News.objects.create(
                    user_id=author_user_id,
                    title=news_title,
                    content=news_content,
                    is_published=True,
                    image_path=(news_image_path[:255] if news_image_path else None),
                )
            except Exception as news_err:
                logger.warning(f'Не удалось автоматически создать новость: {news_err}')
            messages.success(request, f'Животное "{animal_name}" успешно создано. Рост: {animal.height or "не указан"}, Вес: {animal.animal_weight or "не указан"}')
            return redirect('animal_admin_list')
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            messages.error(request, f'Ошибка при создании: {str(e)}')
            # Логируем детали ошибки для отладки
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Ошибка создания животного: {error_detail}')
            messages.error(request, f'Детали ошибки сохранены в лог. Проверьте консоль сервера.')
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
                'image_path': image_path,
                'breed_id': breed_id,
                'status_id': status_id,
                'character_id': character_id,
                'height': height,
                'height_unit': height_unit,
                'animal_weight': animal_weight,
                'admission_date': admission_date,
            })

class AnimalUpdateView(AdminRequiredMixin, View):
    """Редактирование животного"""
    def get(self, request, pk):
        from animals.models import AnimalMedia
        animal = get_object_or_404(Animal.objects.select_related('breed', 'status', 'character'), pk=pk)
        # Загружаем медиа-файлы для отображения в форме
        media_files = AnimalMedia.objects.filter(animal=animal).order_by('display_order', 'media_id')
        # Конвертируем рост из метров в сантиметры для отображения в форме
        height_cm = animal.height * 100 if animal.height else None
        from .models import Shelter
        return render(request, 'animals/admin/update.html', {
            'animal': animal,
            'breeds': Breed.objects.select_related('type').all(),
            'statuses': AnimalStatus.objects.all(),
            'characters': AnimalCharacter.objects.all(),
            'types': AnimalType.objects.all(),
            'shelters': Shelter.objects.filter(is_active=True).order_by('shelter_name'),
            'media_files': media_files,
            'height_cm': height_cm,  # Рост в сантиметрах для формы
        })
    
    def post(self, request, pk):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'POST request received for animal {pk}')
        logger.info(f'POST data: {dict(request.POST)}')
        
        animal = get_object_or_404(Animal, pk=pk)
        user_id = get_user_id_from_jwt(request) or 0
        animal_name = (request.POST.get('animal_name') or '').strip()
        age = request.POST.get('age')
        gender = request.POST.get('gender', '').strip()
        vaccinated = request.POST.get('vaccinated') == 'on'
        description = (request.POST.get('description') or '').strip() or None
        image_path = (request.POST.get('image_path') or '').strip() or None
        image_file = request.FILES.get('image_file')
        breed_id = request.POST.get('breed_id')
        status_id = request.POST.get('status_id')
        if not status_id:
            default_status = AnimalStatus.objects.filter(status_name__in=['Доступен', 'Available']).order_by('status_id').first()
            status_id = str(default_status.status_id) if default_status else '1'
        character_id = request.POST.get('character_id') or None
        shelter_id = request.POST.get('shelter_id') or None
        height = request.POST.get('height') or None
        height_unit = request.POST.get('height_unit', 'cm')  # По умолчанию сантиметры
        animal_weight = request.POST.get('animal_weight') or None
        admission_date = request.POST.get('admission_date') or None
        
        logger.info(f'Parsed values: height={height}, height_unit={height_unit}, weight={animal_weight}, age={age}')
        
        errors = []
        # Валидация имени животного
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
        
        # Рост обязателен с проверкой на 0
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
                    # Конвертируем в метры для сохранения в БД
                    if height_unit == 'cm':
                        # Если введено в сантиметрах, конвертируем в метры
                        height_float = height_value / 100.0
                    else:
                        # Если введено в метрах, сохраняем как есть
                        height_float = height_value
            except ValueError:
                errors.append('Укажите корректный рост (число)')
        
        # Вес обязателен
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
            # Обновляем объект animal для отображения текущих значений
            animal.refresh_from_db()
            return render(request, 'animals/admin/update.html', {
                'animal': animal,
                'breeds': Breed.objects.select_related('type').all(),
                'statuses': AnimalStatus.objects.all(),
                'characters': AnimalCharacter.objects.all(),
                'types': AnimalType.objects.all(),
            })
        
        # Обработка загруженного изображения
        final_image_path = animal.image_path  # Сохраняем старое значение по умолчанию
        if image_file:
            # Сохраняем загруженный файл
            ext = os.path.splitext(image_file.name)[1].lower()
            user_id = get_user_id_from_jwt(request) or 0
            filename = f"animals/animal_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
            saved_path = default_storage.save(filename, image_file)
            final_image_path = default_storage.url(saved_path)
        elif image_path:
            final_image_path = image_path[:255] if len(image_path) <= 255 else image_path[:255]
        
        # Нормализация пола - конвертируем русские значения в английские для БД
        if gender in ['М', 'Мужской']:
            gender = 'Male'
        elif gender in ['Ж', 'Женский']:
            gender = 'Female'
        elif gender not in ['Male', 'Female', 'Unknown']:
            gender = 'Unknown'
        
        # Обработка даты
        admission_date_obj = None
        if admission_date:
            try:
                admission_date_obj = timezone.datetime.strptime(admission_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append('Укажите корректную дату поступления')
        
        if errors:
            for error in errors:
                messages.error(request, error, extra_tags='animal_update_page')
            animal.refresh_from_db()
            return render(request, 'animals/admin/update.html', {
                'animal': animal,
                'breeds': Breed.objects.select_related('type').all(),
                'statuses': AnimalStatus.objects.all(),
                'characters': AnimalCharacter.objects.all(),
                'types': AnimalType.objects.all(),
            })
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Сохраняем старые значения для логирования
            old_height = animal.height
            old_weight = animal.animal_weight
            
            animal.animal_name = animal_name
            animal.age = int(age)
            animal.gender = gender
            animal.vaccinated = vaccinated
            animal.description = description
            animal.image_path = final_image_path
            animal.breed_id = int(breed_id)
            animal.status_id = int(status_id)
            animal.character_id = int(character_id) if character_id else None
            animal.shelter_id = int(shelter_id) if shelter_id else None
            animal.height = height_float
            animal.animal_weight = weight_float
            animal.admission_date = admission_date_obj
            
            logger.info(f'Before save: height={height_float}, weight={weight_float}')
            logger.info(f'Old values: height={old_height}, weight={old_weight}')
            
            animal.save()
            
            # Проверяем сохраненные значения
            animal.refresh_from_db()
            logger.info(f'After save: height={animal.height}, weight={animal.animal_weight}')
            
            # Удаление медиа-файлов, отмеченных для удаления
            from animals.models import AnimalMedia
            deleted_media_ids = request.POST.get('deleted_media_ids', '').strip()
            logger.info(f'Получены ID медиа-файлов для удаления: {deleted_media_ids}')
            if deleted_media_ids:
                try:
                    media_ids = [int(id.strip()) for id in deleted_media_ids.split(',') if id.strip()]
                    logger.info(f'Обработка {len(media_ids)} медиа-файлов для удаления')
                    for media_id in media_ids:
                        try:
                            media = AnimalMedia.objects.get(media_id=media_id, animal=animal)
                            logger.info(f'Удаление медиа-файла {media_id}: {media.media_path}')
                            media.delete()
                        except AnimalMedia.DoesNotExist:
                            logger.warning(f'Медиа-файл {media_id} не найден')
                        except Exception as e:
                            logger.error(f'Ошибка при удалении медиа-файла {media_id}: {e}')
                except (ValueError, Exception) as e:
                    logger.error(f'Ошибка при обработке списка удаления медиа-файлов: {e}')
            
            # Сохранение медиа-файлов (фото и видео)
            from django.db.models import Max
            
            # Получаем текущие медиа-файлы для определения следующего порядка
            existing_media = AnimalMedia.objects.filter(animal=animal)
            max_order = existing_media.aggregate(Max('display_order'))['display_order__max'] or -1
            photo_order = max_order + 1
            
            # Обработка загруженных фото
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
            
            # Обработка URL фото (разбиваем по строкам)
            photo_urls_text = request.POST.get('photo_urls', '').strip()
            if photo_urls_text:
                photo_urls = [url.strip() for url in photo_urls_text.split('\n') if url.strip()]
                for photo_url in photo_urls:
                    if photo_url:
                        final_photo_url = photo_url[:500]
                        # Если это прямая ссылка на изображение (с расширением), используем URL напрямую
                        # Только для URL без расширения пытаемся скачать
                        if IMAGE_EXT_RE.search(photo_url):
                            # Прямая ссылка на изображение - используем как есть
                            pass
                        else:
                            # Пытаемся скачать и сохранить локально
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
            
            # Обработка загруженных видео
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
            
            # Обработка URL видео (разбиваем по строкам)
            # Поддерживаем любые URL: YouTube, VK, прямые ссылки на видео файлы и т.д.
            video_urls_text = request.POST.get('video_urls', '').strip()
            if video_urls_text:
                video_urls = [url.strip() for url in video_urls_text.split('\n') if url.strip()]
                for video_url in video_urls:
                    if video_url:
                        video_url = video_url[:500]
                        # Принимаем любой URL - YouTube, VK, прямые ссылки и т.д.
                        AnimalMedia.objects.create(
                            animal=animal,
                            media_type='Video',
                            media_path=video_url,
                            display_order=video_order
                        )
                        video_order += 1

            # Синхронизация: главное фото и Animals.ImagePath
            try:
                primary_photo = (
                    AnimalMedia.objects.filter(animal=animal, media_type='Photo')
                    .order_by('display_order', 'media_id')
                    .first()
                )
                if primary_photo:
                    AnimalMedia.objects.filter(animal=animal, media_type='Photo').exclude(media_id=primary_photo.media_id).update(is_primary=False)
                    if not primary_photo.is_primary:
                        AnimalMedia.objects.filter(media_id=primary_photo.media_id).update(is_primary=True)
                    new_image_path = (primary_photo.media_path or '')[:255]
                    if new_image_path and animal.image_path != new_image_path:
                        Animal.objects.filter(pk=animal.pk).update(image_path=new_image_path)
                        animal.image_path = new_image_path
            except Exception:
                logger.exception('Failed to sync primary photo and image_path')
            
            messages.success(request, f'Животное "{animal_name}" успешно обновлено. Рост: {animal.height or "не указан"}, Вес: {animal.animal_weight or "не указан"}')
            return redirect('animal_admin_list')
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
            
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Ошибка обновления животного: {error_detail}')
            
            animal.refresh_from_db()
            return render(request, 'animals/admin/update.html', {
                'animal': animal,
                'breeds': Breed.objects.select_related('type').all(),
                'statuses': AnimalStatus.objects.all(),
                'characters': AnimalCharacter.objects.all(),
                'types': AnimalType.objects.all(),
            })

class AnimalDeleteView(AdminRequiredMixin, View):
    """Удаление животного"""
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
        
        # Проверка роли - менеджеры и админы не могут подавать заявки
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
        
        if not experience:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Укажите опыт ухода за животными'}, status=400)
            messages.error(request, 'Укажите опыт ухода за животными')
            return redirect(f"/animals/{animal_id or ''}/")
        
        if not housing:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Укажите жилищные условия'}, status=400)
            messages.error(request, 'Укажите жилищные условия')
            return redirect(f"/animals/{animal_id or ''}/")
        
        with connection.cursor() as cur:
            # Проверяем, есть ли уже заявка со статусом 'Pending' на это животное
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
                        'error': 'У вас уже есть заявка на это животное, которая находится в ожидании. Дождитесь ответа на существующую заявку.'
                    }, status=400)
                messages.error(request, 'У вас уже есть заявка на это животное, которая находится в ожидании. Дождитесь ответа на существующую заявку.')
                return redirect(f"/animals/{animal_id or ''}/")
            
            # Получаем StatusID для 'Pending'
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
