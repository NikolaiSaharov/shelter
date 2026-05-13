from rest_framework import viewsets
from .models import News
from .serializers import NewsSerializer
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.core.files.storage import default_storage
from django.utils import timezone
from django.conf import settings
from django.db import connection
from .mixins import AdminOrManagerRequiredMixin
from accounts.models import User
from accounts.audit_utils import log_audit
from accounts.utils import get_user_id_from_jwt
import os
import re
import urllib.request
import urllib.parse

IMAGE_EXT_RE = re.compile(r"\.(png|jpe?g|gif|webp|bmp|svg)(\?.*)?$", re.IGNORECASE)

def _save_image_from_url(url: str, user_id: int) -> str | None:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
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
            filename = f"news/news_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
            saved_path = default_storage.save(filename, bytes(data))
            return default_storage.url(saved_path)
    except Exception:
        return None

# Create your views here.

class NewsViewSet(viewsets.ModelViewSet):
    queryset = News.objects.all()
    serializer_class = NewsSerializer

class NewsListView(View):
    def get(self, request):
        from animals.models import Shelter
        news_list = News.objects.select_related('shelter').filter(is_published=True)
        shelters = Shelter.objects.filter(is_active=True).order_by('shelter_name')
        
        shelter_id = request.GET.get('shelter')
        if shelter_id:
            news_list = news_list.filter(shelter_id=shelter_id)
        
        # Применяем срез после всех фильтров
        news_list = news_list.order_by('-post_date')[:10]
        
        return render(request, 'news/list.html', {
            'news_list': news_list,
            'shelters': shelters,
        })

class NewsDetailView(View):
    def get(self, request, pk):
        from animals.models import Animal
        item = get_object_or_404(News, pk=pk)
        
        # Пытаемся найти связанное животное по заголовку новости
        related_animal = None
        if item.title.startswith('Новый питомец:'):
            # Извлекаем имя животного из заголовка
            animal_name = item.title.replace('Новый питомец:', '').strip()
            try:
                related_animal = Animal.objects.filter(animal_name=animal_name).first()
            except:
                pass
        
        return render(request, 'news/detail.html', {
            'news': item,
            'related_animal': related_animal
        })

class NewsCreateView(AdminOrManagerRequiredMixin, View):
    def get(self, request):
        return render(request, 'news/create.html')

    def post(self, request):
        user_id = get_user_id_from_jwt(request)
        title = request.POST.get('title','').strip()
        content = request.POST.get('content','').strip()
        author_user_id = user_id
        if not title or not content:
            messages.error(request, 'Заполните заголовок и содержимое', extra_tags='news_create_page')
            return render(request, 'news/create.html', {'title': title, 'content': content})
        image_url = request.POST.get('image_url','').strip()
        image_file = request.FILES.get('image_file')
        final_image_url = ''
        if image_file:
            ext = os.path.splitext(image_file.name)[1].lower()
            filename = f"news/news_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
            saved_path = default_storage.save(filename, image_file)
            final_image_url = default_storage.url(saved_path)
        elif image_url:
            # если не прямая ссылка на картинку — пробуем скачать и сохранить в MEDIA
            if IMAGE_EXT_RE.search(image_url):
                final_image_url = image_url[:255]
            else:
                stored = _save_image_from_url(image_url, user_id)
                if stored:
                    final_image_url = stored
        n = News(user_id=author_user_id, title=title, content=content, is_published=True)
        if final_image_url:
            n.image_path = final_image_url[:255]
        n.save()
        messages.success(request, 'Новость создана')
        return redirect('news_detail', pk=n.news_id)

class NewsUpdateView(AdminOrManagerRequiredMixin, View):
    def get(self, request, pk):
        item = get_object_or_404(News, pk=pk)
        return render(request, 'news/edit.html', {'news': item})

    def post(self, request, pk):
        item = get_object_or_404(News, pk=pk)
        title = request.POST.get('title','').strip()
        content = request.POST.get('content','').strip()
        if not title or not content:
            messages.error(request, 'Заполните заголовок и содержимое', extra_tags='news_update_page')
            return render(request, 'news/edit.html', {'news': item, 'title': title, 'content': content})
        image_url = request.POST.get('image_url','').strip()
        image_file = request.FILES.get('image_file')
        final_image_url = ''
        if image_file:
            ext = os.path.splitext(image_file.name)[1].lower()
            filename = f"news/news_{item.user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
            saved_path = default_storage.save(filename, image_file)
            final_image_url = default_storage.url(saved_path)
        elif image_url:
            if IMAGE_EXT_RE.search(image_url):
                final_image_url = image_url[:255]
            else:
                stored = _save_image_from_url(image_url, item.user_id)
                if stored:
                    final_image_url = stored
        item.title = title
        item.content = content
        if final_image_url:
            item.image_path = final_image_url[:255]
        item.save()
        messages.success(request, 'Новость обновлена')
        return redirect('news_detail', pk=item.news_id)

class NewsDeleteView(AdminOrManagerRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(News, pk=pk)
        item.delete()
        messages.success(request, 'Новость удалена')
        return redirect('news_list')

# Admin panel views for news
class NewsAdminListView(AdminOrManagerRequiredMixin, View):
    """Список всех новостей для админа/менеджера"""
    def get(self, request):
        news_list = News.objects.select_related('user').all().order_by('-post_date')
        
        # Фильтры
        q = request.GET.get('q')
        if q:
            news_list = news_list.filter(title__icontains=q)
        
        published_filter = request.GET.get('published')
        if published_filter == '1':
            news_list = news_list.filter(is_published=True)
        elif published_filter == '0':
            news_list = news_list.filter(is_published=False)
        
        return render(request, 'news/admin/list.html', {
            'news_list': news_list,
        })

class NewsAdminCreateView(AdminOrManagerRequiredMixin, View):
    """Создание новости (админ/менеджер)"""
    def get(self, request):
        from animals.models import Shelter
        return render(request, 'news/admin/create.html', {
            'shelters': Shelter.objects.filter(is_active=True).order_by('shelter_name'),
        })
    
    def post(self, request):
        user_id = get_user_id_from_jwt(request)
        title = (request.POST.get('title') or '').strip()
        content = (request.POST.get('content') or '').strip()
        is_published = request.POST.get('is_published') == 'on'
        shelter_id = request.POST.get('shelter_id') or None
        image_url = request.POST.get('image_url', '').strip()
        image_file = request.FILES.get('image_file')
        
        errors = []
        if not title:
            errors.append('Укажите заголовок')
        if not content:
            errors.append('Укажите содержимое')
        
        if errors:
            from animals.models import Shelter
            for error in errors:
                messages.error(request, error, extra_tags='news_admin_create_page')
            return render(request, 'news/admin/create.html', {
                'title': title,
                'content': content,
                'is_published': is_published,
                'shelter_id': shelter_id,
                'image_url': image_url,
                'shelters': Shelter.objects.filter(is_active=True).order_by('shelter_name'),
            })
        
        final_image_url = ''
        if image_file:
            ext = os.path.splitext(image_file.name)[1].lower()
            filename = f"news/news_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
            saved_path = default_storage.save(filename, image_file)
            final_image_url = default_storage.url(saved_path)
        elif image_url:
            if IMAGE_EXT_RE.search(image_url):
                final_image_url = image_url[:255]
            else:
                stored = _save_image_from_url(image_url, user_id)
                if stored:
                    final_image_url = stored
        
        try:
            news = News.objects.create(
                user_id=user_id,
                title=title,
                content=content,
                is_published=is_published,
                shelter_id=int(shelter_id) if shelter_id else None,
                image_path=final_image_url[:255] if final_image_url else None,
            )
            
            # Логируем в аудитлог
            log_audit(
                table_name='News',
                record_id=news.news_id,
                action='Create',
                changed_by=user_id,
                new_value=f"Title: {title}, Published: {is_published}"
            )
            
            messages.success(request, f'Новость "{title}" успешно создана')
            return redirect('news_admin_list')
        except Exception as e:
            from animals.models import Shelter
            messages.error(request, f'Ошибка при создании: {str(e)}', extra_tags='news_admin_create_page')
            return render(request, 'news/admin/create.html', {
                'title': title,
                'content': content,
                'is_published': is_published,
                'shelter_id': shelter_id,
                'image_url': image_url,
                'shelters': Shelter.objects.filter(is_active=True).order_by('shelter_name'),
            })

class NewsAdminUpdateView(AdminOrManagerRequiredMixin, View):
    """Редактирование новости (админ/менеджер)"""
    def get(self, request, pk):
        from animals.models import Shelter
        news = get_object_or_404(News.objects.select_related('user', 'shelter'), pk=pk)
        return render(request, 'news/admin/update.html', {
            'news': news,
            'shelters': Shelter.objects.filter(is_active=True).order_by('shelter_name'),
        })
    
    def post(self, request, pk):
        news = get_object_or_404(News, pk=pk)
        title = (request.POST.get('title') or '').strip()
        content = (request.POST.get('content') or '').strip()
        is_published = request.POST.get('is_published') == 'on'
        shelter_id = request.POST.get('shelter_id') or None
        image_url = request.POST.get('image_url', '').strip()
        image_file = request.FILES.get('image_file')
        
        errors = []
        if not title:
            errors.append('Укажите заголовок')
        if not content:
            errors.append('Укажите содержимое')
        
        if errors:
            for error in errors:
                messages.error(request, error, extra_tags='news_admin_update_page')
            return render(request, 'news/admin/update.html', {
                'news': news,
            })
        
        # Обработка изображения
        final_image_url = news.image_path  # Сохраняем текущее изображение
        if image_file:
            ext = os.path.splitext(image_file.name)[1].lower()
            filename = f"news/news_{news.user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"
            saved_path = default_storage.save(filename, image_file)
            final_image_url = default_storage.url(saved_path)
        elif image_url:
            if IMAGE_EXT_RE.search(image_url):
                final_image_url = image_url[:255]
            else:
                stored = _save_image_from_url(image_url, news.user_id)
                if stored:
                    final_image_url = stored
                elif image_url != news.image_path:
                    final_image_url = image_url[:255] if len(image_url) <= 255 else image_url[:255]
        
        try:
            # Сохраняем старые значения для логирования
            old_title = news.title
            old_published = news.is_published
            
            news.title = title
            news.content = content
            news.is_published = is_published
            news.shelter_id = int(shelter_id) if shelter_id else None
            if final_image_url:
                news.image_path = final_image_url[:255]
            news.save()
            
            # Логируем в аудитлог
            log_audit(
                table_name='News',
                record_id=news.news_id,
                action='Update',
                changed_by=get_user_id_from_jwt(request),
                old_value=f"Title: {old_title}, Published: {old_published}",
                new_value=f"Title: {title}, Published: {is_published}"
            )
            
            messages.success(request, f'Новость "{title}" успешно обновлена')
            return redirect('news_admin_list')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}', extra_tags='news_admin_update_page')
            return render(request, 'news/admin/update.html', {
                'news': news,
            })

class NewsAdminDeleteView(AdminOrManagerRequiredMixin, View):
    """Удаление новости (админ/менеджер)"""
    def post(self, request, pk):
        news = get_object_or_404(News, pk=pk)
        news_title = news.title
        news_id_for_log = news.news_id
        try:
            # Сохраняем данные перед удалением
            news_data = f"Title: {news.title}, Published: {news.is_published}"
            
            news.delete()
            
            # Логируем в аудитлог
            log_audit(
                table_name='News',
                record_id=news_id_for_log,
                action='Delete',
                changed_by=get_user_id_from_jwt(request),
                old_value=news_data
            )
            
            messages.success(request, f'Новость "{news_title}" успешно удалена')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении: {str(e)}')
        return redirect('news_admin_list')
