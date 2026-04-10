from django.contrib import admin
from .models import UserProfile, ApiToken, FavoriteRepository, RecentRepository, RepositoryViewMode


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'sso_provider', 'created_at']
    list_filter = ['role', 'sso_provider']
    search_fields = ['user__username', 'user__email']


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'last_used_at', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'name']
    readonly_fields = ['token', 'created_at']


@admin.register(FavoriteRepository)
class FavoriteRepositoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'repository_id', 'created_at']
    search_fields = ['user__username', 'repository_id']


@admin.register(RecentRepository)
class RecentRepositoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'repository_id', 'last_viewed_at']
    search_fields = ['user__username', 'repository_id']


@admin.register(RepositoryViewMode)
class RepositoryViewModeAdmin(admin.ModelAdmin):
    list_display = ['user', 'repository_id', 'view_mode', 'updated_at']
    list_filter = ['view_mode']
    search_fields = ['user__username', 'repository_id']
