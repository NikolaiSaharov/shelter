"""
URL configuration for shelter_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from animals.models import Animal
from news.models import News
from django.conf import settings
from django.conf.urls.static import static


def home_view(request):
    from django.db import connection
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    latest_animals_query = Animal.objects.select_related('breed').order_by('-animal_id')[:6]
    latest_news = News.objects.filter(is_published=True).order_by('-post_date')[:6]
    
    latest_animals = []
    for animal in latest_animals_query:
        has_approved_application = False
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM Applications a
                JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
                WHERE a.AnimalID = %s AND ast.StatusName = 'Approved'
            """, [animal.animal_id])
            result = cursor.fetchone()
            has_approved_application = result[0] > 0 if result else False
        
        latest_animals.append({
            'animal': animal,
            'has_approved_application': has_approved_application,
        })
    
    stats = {}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM Animals a
            JOIN AnimalStatuses s ON a.StatusID = s.StatusID
            WHERE s.StatusName = 'Available'
        """)
        stats['animals_available'] = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT COUNT(*) FROM Applications a
            JOIN ApplicationStatuses ast ON a.StatusID = ast.StatusID
            WHERE ast.StatusName = 'Approved'
        """)
        stats['adoptions_success'] = cursor.fetchone()[0] or 0
        
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(Amount), 0) FROM Donations
            WHERE DonationDate >= %s
        """, [today_start])
        row = cursor.fetchone()
        stats['donations_today_count'] = row[0] or 0
        stats['donations_today_sum'] = float(row[1] or 0)
        
        cursor.execute("SELECT COUNT(*) FROM Animals")
        stats['animals_total'] = cursor.fetchone()[0] or 0
    
    return render(request, 'home.html', {
        'latest_animals': latest_animals,
        'latest_news': latest_news,
        'stats': stats,
    })

def help_view(request):
    return render(request, 'help/index.html')

urlpatterns = [
    path('', home_view, name='home'),
    path('help/', help_view, name='help'),
    path('admin/', admin.site.urls),

    path('animals/', include('animals.urls')),
    path('news/', include('news.urls')),
    path('accounts/', include('accounts.urls')),
    path('meetings/', include('meetings.urls')),
    path('messages/', include('messages.urls')),
    path('donations/', include('donations.urls')),
    path('care/', include('care.urls')),

    # API приложение со Swagger
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
