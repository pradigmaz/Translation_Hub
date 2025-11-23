"""
Middleware для дополнительной безопасности TranslationHub
"""

from django.http import HttpResponseForbidden
from django.core.exceptions import SuspiciousOperation
from django.utils.deprecation import MiddlewareMixin


class SecurityMiddleware(MiddlewareMixin):
    """
    Middleware для логирования подозрительной активности и дополнительной защиты
    """
    
    def process_request(self, request):
        """Обработка входящих запросов"""
        
        # Проверка на слишком длинные URL (возможная атака)
        if len(request.path) > 2000:
            raise SuspiciousOperation("URL too long")
        
        return None
    
    def process_exception(self, request, exception):
        """Обработка исключений"""
        return None


class RateLimitMiddleware(MiddlewareMixin):
    """
    Ограничение частоты запросов (100/мин с IP).
    ВНИМАНИЕ: In-memory, только для dev. Production: Redis или django-ratelimit.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}  # ТОЛЬКО ДЛЯ DEV! В production используйте Redis
        super().__init__(get_response)
    
    def process_request(self, request):
        """Проверка лимита запросов"""
        
        import time
        current_time = int(time.time())
        
        # Простой IP из request (без утилиты)
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        minute_key = f"{ip}:{current_time // 60}"
        
        if minute_key not in self.request_counts:
            self.request_counts[minute_key] = 0
        
        self.request_counts[minute_key] += 1
        
        # Лимит: 100 запросов в минуту с одного IP
        if self.request_counts[minute_key] > 100:
            return HttpResponseForbidden("Rate limit exceeded")
        
        # Очистка старых записей
        keys_to_remove = [key for key in self.request_counts.keys() 
                         if int(key.split(':')[1]) < current_time // 60 - 5]
        for key in keys_to_remove:
            del self.request_counts[key]
        
        return None