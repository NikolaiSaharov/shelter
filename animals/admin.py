from django.contrib import admin
from .models import Animal, AnimalType, Breed, AnimalStatus, AnimalCharacter

@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ('animal_id', 'animal_name', 'age', 'gender', 'vaccinated', 'status', 'breed', 'height', 'animal_weight', 'admission_date')
    search_fields = ('animal_name',)
    list_filter = ('status', 'breed', 'gender', 'vaccinated')

@admin.register(AnimalType)
class AnimalTypeAdmin(admin.ModelAdmin):
    list_display = ('type_id', 'type_name')
    search_fields = ('type_name',)

@admin.register(Breed)
class BreedAdmin(admin.ModelAdmin):
    list_display = ('breed_id', 'breed_name', 'type')
    search_fields = ('breed_name',)
    list_filter = ('type',)

@admin.register(AnimalStatus)
class AnimalStatusAdmin(admin.ModelAdmin):
    list_display = ('status_id', 'status_name')
    search_fields = ('status_name',)
    list_filter = ('status_name',)

@admin.register(AnimalCharacter)
class AnimalCharacterAdmin(admin.ModelAdmin):
    list_display = ('character_id', 'character_name', 'description')
    search_fields = ('character_name',)
