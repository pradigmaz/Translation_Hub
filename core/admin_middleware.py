"""Middleware для фильтрации уведомлений в админ-панели Django."""

from django.urls import resolve


class AdminMessagesFilterMiddleware:
    """Убирает messages в админке, кроме ERROR+."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path.startswith('/admin/'):
            pass  # Фильтрация отключена
        return self.get_response(request)