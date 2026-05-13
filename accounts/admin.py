from django.contrib import admin
from .models import User, UserProfile, Role

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'email', 'first_name', 'last_name', 'phone', 'role', 'registration_date')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    list_filter = ('role',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('profile_id', 'user', 'home_address', 'date_of_birth', 'created_date', 'updated_date')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('role_id', 'role_name')
    search_fields = ('role_name',)
