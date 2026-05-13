from rest_framework.routers import SimpleRouter
from .views import UserViewSet, UserProfileViewSet, RoleViewSet, LoginView, RegisterView, ProfileView, LogoutView, ApplicationsListView, DonationsListView, ApplicationDetailView, DataPolicyView
from .admin_views import UserAdminListView, UserAdminCreateView, UserAdminUpdateView, UserAdminDeleteView
from .audit_views import AuditLogListView
from .backup_views import BackupCreateView, BackupRestoreView
from .manager_views import UserManagerListView
from .manager_applications_views import ApplicationsManagerListView, ApplicationManagerDetailView, ApplicationManagerApproveView, ApplicationManagerRejectView
from .manager_donations_views import DonationsManagerListView
from .statistics_views import StatisticsView, StatisticsPDFView, StatisticsCSVView
from .test_jwt_view import TestJWTView
from .password_reset_views import ForgotPasswordView, ResetPasswordView
from django.urls import path

router = SimpleRouter()
router.register(r'users', UserViewSet)
router.register(r'profiles', UserProfileViewSet)
router.register(r'roles', RoleViewSet)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('data-policy/', DataPolicyView.as_view(), name='data_policy'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('test-jwt/', TestJWTView.as_view(), name='test_jwt'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('applications/', ApplicationsListView.as_view(), name='user_applications'),
    path('applications/<int:pk>/', ApplicationDetailView.as_view(), name='application_detail'),
    path('donations/', DonationsListView.as_view(), name='user_donations'),
    # Админ-панель пользователей
    path('admin/', UserAdminListView.as_view(), name='user_admin_list'),
    path('admin/create/', UserAdminCreateView.as_view(), name='user_admin_create'),
    path('admin/<int:pk>/update/', UserAdminUpdateView.as_view(), name='user_admin_update'),
    path('admin/<int:pk>/delete/', UserAdminDeleteView.as_view(), name='user_admin_delete'),
    # Аудитлог
    path('audit-log/', AuditLogListView.as_view(), name='audit_log'),
    # Бэкап
    path('backup/create/', BackupCreateView.as_view(), name='backup_create'),
    path('backup/restore/', BackupRestoreView.as_view(), name='backup_restore'),
    # Менеджер
    path('manager/', UserManagerListView.as_view(), name='user_manager_list'),
    path('manager/applications/', ApplicationsManagerListView.as_view(), name='applications_manager_list'),
    path('manager/applications/<int:pk>/', ApplicationManagerDetailView.as_view(), name='application_manager_detail'),
    path('manager/applications/<int:pk>/approve/', ApplicationManagerApproveView.as_view(), name='application_manager_approve'),
    path('manager/applications/<int:pk>/reject/', ApplicationManagerRejectView.as_view(), name='application_manager_reject'),
    path('manager/donations/', DonationsManagerListView.as_view(), name='donations_manager_list'),
    # Статистика
    path('statistics/', StatisticsView.as_view(), name='statistics'),
    path('statistics/pdf/', StatisticsPDFView.as_view(), name='statistics_pdf'),
    path('statistics/csv/', StatisticsCSVView.as_view(), name='statistics_csv'),
]

urlpatterns += router.urls
