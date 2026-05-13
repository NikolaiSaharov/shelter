"""
API views - импортируем все ViewSets из других приложений и добавляем теги для Swagger
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema_view, extend_schema
from accounts.views import UserViewSet as BaseUserViewSet
from accounts.views import UserProfileViewSet as BaseUserProfileViewSet
from accounts.views import RoleViewSet as BaseRoleViewSet
from animals.views import AnimalViewSet as BaseAnimalViewSet
from animals.views import AnimalTypeViewSet as BaseAnimalTypeViewSet
from animals.views import BreedViewSet as BaseBreedViewSet
from animals.views import AnimalStatusViewSet as BaseAnimalStatusViewSet
from animals.views import AnimalCharacterViewSet as BaseAnimalCharacterViewSet
from news.views import NewsViewSet as BaseNewsViewSet
from care.views import ActivityTypeViewSet as BaseActivityTypeViewSet
from care.views import FrequencyTypeViewSet as BaseFrequencyTypeViewSet
from care.views import AnimalCareScheduleViewSet as BaseAnimalCareScheduleViewSet
from applications.views import ApplicationViewSet as BaseApplicationViewSet
from donations.views import DonationViewSet as BaseDonationViewSet


class APIRootView(APIView):
    """
    Корневой эндпоинт API - показывает все доступные эндпоинты
    """
    def get(self, request, format=None):
        base_url = request.build_absolute_uri('/api/')
        
        return Response({
            'message': 'Анималити API - Список всех доступных эндпоинтов',
            'documentation': {
                'swagger': base_url + 'swagger/',
                'redoc': base_url + 'redoc/',
                'schema': base_url + 'schema/',
            },
            'endpoints': {
                'accounts': {
                    'users': base_url + 'users/',
                    'profiles': base_url + 'profiles/',
                    'roles': base_url + 'roles/',
                },
                'animals': {
                    'animals': base_url + 'animals/',
                    'animal_types': base_url + 'animal-types/',
                    'breeds': base_url + 'breeds/',
                    'animal_statuses': base_url + 'animal-statuses/',
                    'animal_characters': base_url + 'animal-characters/',
                },
                'news': {
                    'news': base_url + 'news/',
                },
                'care': {
                    'activity_types': base_url + 'activity-types/',
                    'frequency_types': base_url + 'frequency-types/',
                    'care_schedules': base_url + 'care-schedules/',
                },
                'applications': {
                    'applications': base_url + 'applications/',
                },
                'donations': {
                    'donations': base_url + 'donations/',
                },
            }
        })


# Обертки ViewSets с тегами для правильной группировки в Swagger
@extend_schema_view(
    list=extend_schema(tags=['Accounts']),
    retrieve=extend_schema(tags=['Accounts']),
    create=extend_schema(tags=['Accounts']),
    update=extend_schema(tags=['Accounts']),
    partial_update=extend_schema(tags=['Accounts']),
    destroy=extend_schema(tags=['Accounts']),
)
class UserViewSet(BaseUserViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Accounts']),
    retrieve=extend_schema(tags=['Accounts']),
    create=extend_schema(tags=['Accounts']),
    update=extend_schema(tags=['Accounts']),
    partial_update=extend_schema(tags=['Accounts']),
    destroy=extend_schema(tags=['Accounts']),
)
class UserProfileViewSet(BaseUserProfileViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Accounts']),
    retrieve=extend_schema(tags=['Accounts']),
    create=extend_schema(tags=['Accounts']),
    update=extend_schema(tags=['Accounts']),
    partial_update=extend_schema(tags=['Accounts']),
    destroy=extend_schema(tags=['Accounts']),
)
class RoleViewSet(BaseRoleViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Animals']),
    retrieve=extend_schema(tags=['Animals']),
    create=extend_schema(tags=['Animals']),
    update=extend_schema(tags=['Animals']),
    partial_update=extend_schema(tags=['Animals']),
    destroy=extend_schema(tags=['Animals']),
)
class AnimalViewSet(BaseAnimalViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Animals']),
    retrieve=extend_schema(tags=['Animals']),
    create=extend_schema(tags=['Animals']),
    update=extend_schema(tags=['Animals']),
    partial_update=extend_schema(tags=['Animals']),
    destroy=extend_schema(tags=['Animals']),
)
class AnimalTypeViewSet(BaseAnimalTypeViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Animals']),
    retrieve=extend_schema(tags=['Animals']),
    create=extend_schema(tags=['Animals']),
    update=extend_schema(tags=['Animals']),
    partial_update=extend_schema(tags=['Animals']),
    destroy=extend_schema(tags=['Animals']),
)
class BreedViewSet(BaseBreedViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Animals']),
    retrieve=extend_schema(tags=['Animals']),
    create=extend_schema(tags=['Animals']),
    update=extend_schema(tags=['Animals']),
    partial_update=extend_schema(tags=['Animals']),
    destroy=extend_schema(tags=['Animals']),
)
class AnimalStatusViewSet(BaseAnimalStatusViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Animals']),
    retrieve=extend_schema(tags=['Animals']),
    create=extend_schema(tags=['Animals']),
    update=extend_schema(tags=['Animals']),
    partial_update=extend_schema(tags=['Animals']),
    destroy=extend_schema(tags=['Animals']),
)
class AnimalCharacterViewSet(BaseAnimalCharacterViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['News']),
    retrieve=extend_schema(tags=['News']),
    create=extend_schema(tags=['News']),
    update=extend_schema(tags=['News']),
    partial_update=extend_schema(tags=['News']),
    destroy=extend_schema(tags=['News']),
)
class NewsViewSet(BaseNewsViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Care']),
    retrieve=extend_schema(tags=['Care']),
    create=extend_schema(tags=['Care']),
    update=extend_schema(tags=['Care']),
    partial_update=extend_schema(tags=['Care']),
    destroy=extend_schema(tags=['Care']),
)
class ActivityTypeViewSet(BaseActivityTypeViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Care']),
    retrieve=extend_schema(tags=['Care']),
    create=extend_schema(tags=['Care']),
    update=extend_schema(tags=['Care']),
    partial_update=extend_schema(tags=['Care']),
    destroy=extend_schema(tags=['Care']),
)
class FrequencyTypeViewSet(BaseFrequencyTypeViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Care']),
    retrieve=extend_schema(tags=['Care']),
    create=extend_schema(tags=['Care']),
    update=extend_schema(tags=['Care']),
    partial_update=extend_schema(tags=['Care']),
    destroy=extend_schema(tags=['Care']),
)
class AnimalCareScheduleViewSet(BaseAnimalCareScheduleViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Applications']),
    retrieve=extend_schema(tags=['Applications']),
    create=extend_schema(tags=['Applications']),
    update=extend_schema(tags=['Applications']),
    partial_update=extend_schema(tags=['Applications']),
    destroy=extend_schema(tags=['Applications']),
)
class ApplicationViewSet(BaseApplicationViewSet):
    pass


@extend_schema_view(
    list=extend_schema(tags=['Donations']),
    retrieve=extend_schema(tags=['Donations']),
    create=extend_schema(tags=['Donations']),
    update=extend_schema(tags=['Donations']),
    partial_update=extend_schema(tags=['Donations']),
    destroy=extend_schema(tags=['Donations']),
)
class DonationViewSet(BaseDonationViewSet):
    pass


__all__ = [
    'APIRootView',
    'UserViewSet',
    'UserProfileViewSet',
    'RoleViewSet',
    'AnimalViewSet',
    'AnimalTypeViewSet',
    'BreedViewSet',
    'AnimalStatusViewSet',
    'AnimalCharacterViewSet',
    'NewsViewSet',
    'ActivityTypeViewSet',
    'FrequencyTypeViewSet',
    'AnimalCareScheduleViewSet',
    'ApplicationViewSet',
    'DonationViewSet',
]
