from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from news.mixins import AdminOrManagerRequiredMixin
from rest_framework import viewsets
from .models import AnimalCareSchedule, ActivityType, FrequencyType
from animals.models import Animal
from .serializers import ActivityTypeSerializer, FrequencyTypeSerializer, AnimalCareScheduleSerializer


# DRF viewsets (API)
class ActivityTypeViewSet(viewsets.ModelViewSet):
    queryset = ActivityType.objects.all()
    serializer_class = ActivityTypeSerializer


class FrequencyTypeViewSet(viewsets.ModelViewSet):
    queryset = FrequencyType.objects.all()
    serializer_class = FrequencyTypeSerializer


class AnimalCareScheduleViewSet(viewsets.ModelViewSet):
    queryset = AnimalCareSchedule.objects.all()
    serializer_class = AnimalCareScheduleSerializer


# Web views (existing)
class CareScheduleListView(AdminOrManagerRequiredMixin, View):
    """Список расписаний ухода для конкретного животного"""
    
    def get(self, request, animal_id):
        animal = get_object_or_404(Animal, pk=animal_id)
        
        # Получаем расписания ухода через ORM
        schedules_qs = AnimalCareSchedule.objects.filter(
            animal_id=animal_id
        ).select_related(
            'activity_type', 'frequency'
        ).order_by('-is_active', 'activity_type__activity_name')
        
        schedules = []
        for schedule in schedules_qs:
            schedules.append({
                'id': schedule.care_schedule_id,
                'activity': schedule.activity_type.activity_name,
                'frequency': schedule.frequency.frequency_name,
                'time': schedule.schedule_time,
                'notes': schedule.notes,
                'is_active': schedule.is_active,
                'description': schedule.activity_type.description
            })
        
        return render(request, 'care/schedule_list.html', {
            'animal': animal,
            'schedules': schedules,
        })


class CareScheduleCreateView(AdminOrManagerRequiredMixin, View):
    """Создание нового расписания ухода"""
    
    def get(self, request, animal_id):
        animal = get_object_or_404(Animal, pk=animal_id)
        
        # Получаем типы активностей и частоты
        activities = ActivityType.objects.all().order_by('activity_name')
        frequencies = FrequencyType.objects.all().order_by('frequency_name')
        
        return render(request, 'care/schedule_create.html', {
            'animal': animal,
            'activities': activities,
            'frequencies': frequencies,
        })
    
    def post(self, request, animal_id):
        animal = get_object_or_404(Animal, pk=animal_id)
        
        activity_type_id = request.POST.get('activity_type_id')
        frequency_id = request.POST.get('frequency_id')
        schedule_time = request.POST.get('schedule_time') or None
        notes = (request.POST.get('notes') or '').strip() or None
        is_active = request.POST.get('is_active') == 'on'
        
        errors = []
        
        if not activity_type_id:
            errors.append('Выберите тип активности')
        if not frequency_id:
            errors.append('Выберите частоту')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            
            activities = ActivityType.objects.all().order_by('activity_name')
            frequencies = FrequencyType.objects.all().order_by('frequency_name')
            
            return render(request, 'care/schedule_create.html', {
                'animal': animal,
                'activities': activities,
                'frequencies': frequencies,
                'activity_type_id': activity_type_id,
                'frequency_id': frequency_id,
                'schedule_time': schedule_time,
                'notes': notes,
                'is_active': is_active,
            })
        
        try:
            schedule = AnimalCareSchedule.objects.create(
                animal=animal,
                activity_type_id=int(activity_type_id),
                frequency_id=int(frequency_id),
                schedule_time=schedule_time,
                notes=notes,
                is_active=is_active,
            )
            
            messages.success(request, f'Расписание ухода успешно создано')
            return redirect('care_schedule_list', animal_id=animal_id)
        except Exception as e:
            messages.error(request, f'Ошибка при создании: {str(e)}')
            
            activities = ActivityType.objects.all().order_by('activity_name')
            frequencies = FrequencyType.objects.all().order_by('frequency_name')
            
            return render(request, 'care/schedule_create.html', {
                'animal': animal,
                'activities': activities,
                'frequencies': frequencies,
                'activity_type_id': activity_type_id,
                'frequency_id': frequency_id,
                'schedule_time': schedule_time,
                'notes': notes,
                'is_active': is_active,
            })


class CareScheduleUpdateView(AdminOrManagerRequiredMixin, View):
    """Редактирование расписания ухода"""
    
    def get(self, request, animal_id, schedule_id):
        animal = get_object_or_404(Animal, pk=animal_id)
        schedule = get_object_or_404(AnimalCareSchedule, pk=schedule_id, animal=animal)
        
        activities = ActivityType.objects.all().order_by('activity_name')
        frequencies = FrequencyType.objects.all().order_by('frequency_name')
        
        return render(request, 'care/schedule_update.html', {
            'animal': animal,
            'schedule': schedule,
            'activities': activities,
            'frequencies': frequencies,
        })
    
    def post(self, request, animal_id, schedule_id):
        animal = get_object_or_404(Animal, pk=animal_id)
        schedule = get_object_or_404(AnimalCareSchedule, pk=schedule_id, animal=animal)
        
        activity_type_id = request.POST.get('activity_type_id')
        frequency_id = request.POST.get('frequency_id')
        schedule_time = request.POST.get('schedule_time') or None
        notes = (request.POST.get('notes') or '').strip() or None
        is_active = request.POST.get('is_active') == 'on'
        
        errors = []
        
        if not activity_type_id:
            errors.append('Выберите тип активности')
        if not frequency_id:
            errors.append('Выберите частоту')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            
            activities = ActivityType.objects.all().order_by('activity_name')
            frequencies = FrequencyType.objects.all().order_by('frequency_name')
            
            return render(request, 'care/schedule_update.html', {
                'animal': animal,
                'schedule': schedule,
                'activities': activities,
                'frequencies': frequencies,
            })
        
        try:
            schedule.activity_type_id = int(activity_type_id)
            schedule.frequency_id = int(frequency_id)
            schedule.schedule_time = schedule_time
            schedule.notes = notes
            schedule.is_active = is_active
            schedule.save()
            
            messages.success(request, 'Расписание ухода успешно обновлено')
            return redirect('care_schedule_list', animal_id=animal_id)
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
            
            activities = ActivityType.objects.all().order_by('activity_name')
            frequencies = FrequencyType.objects.all().order_by('frequency_name')
            
            return render(request, 'care/schedule_update.html', {
                'animal': animal,
                'schedule': schedule,
                'activities': activities,
                'frequencies': frequencies,
            })


class CareScheduleDeleteView(AdminOrManagerRequiredMixin, View):
    """Удаление расписания ухода"""
    
    def post(self, request, animal_id, schedule_id):
        animal = get_object_or_404(Animal, pk=animal_id)
        schedule = get_object_or_404(AnimalCareSchedule, pk=schedule_id, animal=animal)
        
        try:
            schedule.delete()
            messages.success(request, 'Расписание ухода успешно удалено')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении: {str(e)}')
        
        return redirect('care_schedule_list', animal_id=animal_id)
