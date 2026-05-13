from rest_framework.routers import SimpleRouter
from .views import (
    NewsViewSet, NewsListView, NewsDetailView, NewsCreateView, NewsUpdateView, NewsDeleteView,
    NewsAdminListView, NewsAdminCreateView, NewsAdminUpdateView, NewsAdminDeleteView
)
from django.urls import path

urlpatterns = [
    # Публичные страницы
    path('', NewsListView.as_view(), name='news_list'),
    path('<int:pk>/', NewsDetailView.as_view(), name='news_detail'),
    # Старые routes для обратной совместимости (теперь требуют прав админа/менеджера)
    path('create/', NewsCreateView.as_view(), name='news_create'),
    path('<int:pk>/edit/', NewsUpdateView.as_view(), name='news_edit'),
    path('<int:pk>/delete/', NewsDeleteView.as_view(), name='news_delete'),
    # Админ-панель
    path('admin/', NewsAdminListView.as_view(), name='news_admin_list'),
    path('admin/create/', NewsAdminCreateView.as_view(), name='news_admin_create'),
    path('admin/<int:pk>/update/', NewsAdminUpdateView.as_view(), name='news_admin_update'),
    path('admin/<int:pk>/delete/', NewsAdminDeleteView.as_view(), name='news_admin_delete'),
]

router = SimpleRouter()
router.register(r'news', NewsViewSet)
urlpatterns += router.urls
