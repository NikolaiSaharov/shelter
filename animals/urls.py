from rest_framework.routers import SimpleRouter
from .views import (
    AnimalViewSet, AnimalTypeViewSet, BreedViewSet, AnimalStatusViewSet, AnimalCharacterViewSet,
    AnimalCatalogView, AnimalDetailView, ApplicationCreateView,
    AnimalListView, AnimalCreateView, AnimalUpdateView, AnimalDeleteView
)
from .reference_views import (
    AnimalTypeListView, AnimalTypeCreateView, AnimalTypeUpdateView, AnimalTypeDeleteView,
    BreedListView, BreedCreateView, BreedUpdateView, BreedDeleteView,
    AnimalCharacterListView, AnimalCharacterCreateView, AnimalCharacterUpdateView, AnimalCharacterDeleteView
)
from .shelter_views import ShelterListView, ShelterCreateView, ShelterUpdateView, ShelterDeleteView
from .manager_views import (
    AnimalCardCatalogView, AnimalCardDetailView,
    AnimalCardCatalogAllSheltersView, AnimalCardDetailAllSheltersView,
)
from .calendar_views import VaccinationCalendarView, VaccinationCalendarIcsView
from .medical_views import (
    MedicalRecordsListView, MedicalRecordCreateView, 
    MedicalRecordUpdateView, MedicalRecordDeleteView
)
from .vaccination_views import (
    VaccinationsListView, VaccinationDetailView, VaccinationCreateView,
    VaccinationAddRecordView, VaccinationDeleteView, VaccinationRecordDeleteView
)
from django.urls import path

urlpatterns = [
    path('catalog/', AnimalCatalogView.as_view(), name='animal_catalog'),
    path('<int:pk>/', AnimalDetailView.as_view(), name='animal_detail'),
    path('apply/', ApplicationCreateView.as_view(), name='animal_apply'),
    # Manager Card Catalog
    path('manager/cards/', AnimalCardCatalogView.as_view(), name='animal_card_catalog'),
    path('manager/cards/<int:pk>/', AnimalCardDetailView.as_view(), name='animal_card_detail'),
    path('manager/cards/all/', AnimalCardCatalogAllSheltersView.as_view(), name='animal_card_catalog_all_shelters'),
    path('manager/cards/all/<int:pk>/', AnimalCardDetailAllSheltersView.as_view(), name='animal_card_detail_all_shelters'),
    # Admin CRUD
    path('admin/', AnimalListView.as_view(), name='animal_admin_list'),
    path('admin/create/', AnimalCreateView.as_view(), name='animal_admin_create'),
    path('admin/<int:pk>/update/', AnimalUpdateView.as_view(), name='animal_admin_update'),
    path('admin/<int:pk>/delete/', AnimalDeleteView.as_view(), name='animal_admin_delete'),
    # Admin Reference CRUD
    # Types
    path('admin/types/', AnimalTypeListView.as_view(), name='animal_type_list'),
    path('admin/types/create/', AnimalTypeCreateView.as_view(), name='animal_type_create'),
    path('admin/types/<int:pk>/update/', AnimalTypeUpdateView.as_view(), name='animal_type_update'),
    path('admin/types/<int:pk>/delete/', AnimalTypeDeleteView.as_view(), name='animal_type_delete'),
    # Breeds
    path('admin/breeds/', BreedListView.as_view(), name='breed_list'),
    path('admin/breeds/create/', BreedCreateView.as_view(), name='breed_create'),
    path('admin/breeds/<int:pk>/update/', BreedUpdateView.as_view(), name='breed_update'),
    path('admin/breeds/<int:pk>/delete/', BreedDeleteView.as_view(), name='breed_delete'),
    # Characters
    path('admin/characters/', AnimalCharacterListView.as_view(), name='character_list'),
    path('admin/characters/create/', AnimalCharacterCreateView.as_view(), name='character_create'),
    path('admin/characters/<int:pk>/update/', AnimalCharacterUpdateView.as_view(), name='character_update'),
    path('admin/characters/<int:pk>/delete/', AnimalCharacterDeleteView.as_view(), name='character_delete'),
    # Shelters
    path('admin/shelters/', ShelterListView.as_view(), name='shelter_list'),
    path('admin/shelters/create/', ShelterCreateView.as_view(), name='shelter_create'),
    path('admin/shelters/<int:pk>/update/', ShelterUpdateView.as_view(), name='shelter_update'),
    path('admin/shelters/<int:pk>/delete/', ShelterDeleteView.as_view(), name='shelter_delete'),
    # Medical Records
    path('medical/records/', MedicalRecordsListView.as_view(), name='medical_records_list'),
    path('medical/records/create/', MedicalRecordCreateView.as_view(), name='medical_record_create'),
    path('medical/records/<int:pk>/update/', MedicalRecordUpdateView.as_view(), name='medical_record_update'),
    path('medical/records/<int:pk>/delete/', MedicalRecordDeleteView.as_view(), name='medical_record_delete'),
    # Vaccinations
    path('vaccinations/', VaccinationsListView.as_view(), name='vaccinations_list'),
    path('vaccinations/create/', VaccinationCreateView.as_view(), name='vaccination_create'),
    path('vaccinations/<int:pk>/', VaccinationDetailView.as_view(), name='vaccination_detail'),
    path('vaccinations/<int:pk>/add-record/', VaccinationAddRecordView.as_view(), name='vaccination_add_record'),
    path('vaccinations/<int:pk>/delete/', VaccinationDeleteView.as_view(), name='vaccination_delete'),
    path('vaccinations/records/<int:record_id>/delete/', VaccinationRecordDeleteView.as_view(), name='vaccination_record_delete'),
    # Calendar
    path('calendar/', VaccinationCalendarView.as_view(), name='vaccination_calendar'),
    path('calendar/feed.ics', VaccinationCalendarIcsView.as_view(), name='vaccination_calendar_ics'),
]

router = SimpleRouter()
router.register(r'animals', AnimalViewSet)
router.register(r'types', AnimalTypeViewSet)
router.register(r'breeds', BreedViewSet)
router.register(r'statuses', AnimalStatusViewSet)
router.register(r'characters', AnimalCharacterViewSet)

urlpatterns += router.urls
