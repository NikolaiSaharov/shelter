from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from django.urls import path, include
from .views import (
    APIRootView,
    UserViewSet,
    UserProfileViewSet,
    RoleViewSet,
    AnimalViewSet,
    AnimalTypeViewSet,
    BreedViewSet,
    AnimalStatusViewSet,
    AnimalCharacterViewSet,
    NewsViewSet,
    ActivityTypeViewSet,
    FrequencyTypeViewSet,
    AnimalCareScheduleViewSet,
    ApplicationViewSet,
    DonationViewSet,
)

# Создаем роутер и регистрируем все ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'animals', AnimalViewSet, basename='animal')
router.register(r'animal-types', AnimalTypeViewSet, basename='animal-type')
router.register(r'breeds', BreedViewSet, basename='breed')
router.register(r'animal-statuses', AnimalStatusViewSet, basename='animal-status')
router.register(r'animal-characters', AnimalCharacterViewSet, basename='animal-character')
router.register(r'news', NewsViewSet, basename='news')
router.register(r'activity-types', ActivityTypeViewSet, basename='activity-type')
router.register(r'frequency-types', FrequencyTypeViewSet, basename='frequency-type')
router.register(r'care-schedules', AnimalCareScheduleViewSet, basename='care-schedule')
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'donations', DonationViewSet, basename='donation')

urlpatterns = [
    # Корневой эндпоинт API - список всех эндпоинтов
    path('', APIRootView.as_view(), name='api-root'),
    
    # API endpoints через роутер
    path('', include(router.urls)),
    
    # Swagger документация
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

