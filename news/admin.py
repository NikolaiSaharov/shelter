from django.contrib import admin
from .models import News

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('news_id', 'title', 'user', 'post_date', 'is_published')
    search_fields = ('title', 'content')
    list_filter = ('is_published', 'post_date', 'user')
