from django.contrib import admin
from .models import ActivityType, FrequencyType, AnimalCareSchedule


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('activity_type_id', 'activity_name', 'description')
    search_fields = ('activity_name', 'description')
    list_filter = ('activity_name',)


@admin.register(FrequencyType)
class FrequencyTypeAdmin(admin.ModelAdmin):
    list_display = ('frequency_id', 'frequency_name')
    search_fields = ('frequency_name',)


@admin.register(AnimalCareSchedule)
class AnimalCareScheduleAdmin(admin.ModelAdmin):
    list_display = ('care_schedule_id', 'animal', 'activity_type', 'frequency', 'schedule_time', 'is_active')
    search_fields = ('animal__animal_name', 'activity_type__activity_name', 'notes')
    list_filter = ('is_active', 'frequency', 'activity_type')
    readonly_fields = ('care_schedule_id',)
