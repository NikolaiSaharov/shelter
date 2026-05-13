from django.urls import path
from .views import MeetingsListView, MeetingCreateView, MeetingRoomView

urlpatterns = [
    path('', MeetingsListView.as_view(), name='meetings_page'),
    path('create/', MeetingCreateView.as_view(), name='meeting_create'),
    path('room/<str:link>/', MeetingRoomView.as_view(), name='meeting_room'),
]
