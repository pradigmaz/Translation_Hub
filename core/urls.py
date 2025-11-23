from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from .views import MainPageView, DocsView
from utils.admin_site import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    # URL-маршруты для управления командами
    path('teams/', include('teams.urls', namespace='teams')),
    # URL-маршруты пользователей (аутентификация)
    path('accounts/', include('users.urls')),
    # URL-маршруты для управления проектами
    path('projects/', include('projects.urls', namespace='projects')),
    # URL-маршруты для базы знаний
    path('glossary/', include('glossary.urls', namespace='glossary')),
    # Обработка favicon
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico', permanent=True)),
    # Главная страница сайта
    path('', MainPageView.as_view(), name='main_page'),
    # Страница документации
    path('docs/', DocsView.as_view(), name='docs'),
]

# Обслуживание медиафайлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)