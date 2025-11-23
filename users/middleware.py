from django.contrib.auth import get_user_model
from django.core.cache import cache

User = get_user_model()

class AuthenticationAuditMiddleware:
    """
    Middleware для аудита попыток аутентификации
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Мониторинг попыток входа
        if request.path == '/users/login/' and request.method == 'POST':
            self.log_login_attempt(request)
        
        response = self.get_response(request)
        
        return response
    
    def log_login_attempt(self, request):
        """
        Логирование попыток входа в систему
        """
        pass