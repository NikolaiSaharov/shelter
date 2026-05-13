from django.urls import path
from .views import MessagesListView, MessageThreadView, ComposeMessageView, DeleteMessageView

urlpatterns = [
    path('', MessagesListView.as_view(), name='messages_home'),
    path('compose/', ComposeMessageView.as_view(), name='messages_compose'),
    path('delete/<int:pk>/', DeleteMessageView.as_view(), name='messages_delete'),
    path('<int:pk>/', MessageThreadView.as_view(), name='message_thread'),
]
