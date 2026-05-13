from django.urls import path
from .views import (
    CareScheduleListView,
    CareScheduleCreateView,
    CareScheduleUpdateView,
    CareScheduleDeleteView,
)

urlpatterns = [
    path('<int:animal_id>/', CareScheduleListView.as_view(), name='care_schedule_list'),
    path('<int:animal_id>/create/', CareScheduleCreateView.as_view(), name='care_schedule_create'),
    path('<int:animal_id>/<int:schedule_id>/update/', CareScheduleUpdateView.as_view(), name='care_schedule_update'),
    path('<int:animal_id>/<int:schedule_id>/delete/', CareScheduleDeleteView.as_view(), name='care_schedule_delete'),
]

