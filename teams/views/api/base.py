"""
Базовые классы для API views.

Содержит переиспользуемые компоненты для унификации API представлений.
"""

import json
from functools import wraps
from django.views.generic import View
from django.core.exceptions import ValidationError

from ...mixins import TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, PerformanceMonitoringMixin
from ...exceptions import TeamPermissionDenied, TeamNotFoundError, TeamStatusError



def handle_api_errors(context_name=None):
    """
    Декоратор для унифицированной обработки ошибок в API views.
    
    Args:
        context_name: Имя контекста для логирования (опционально)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            try:
                return func(self, request, *args, **kwargs)
            except (TeamPermissionDenied, TeamNotFoundError) as e:
                return self.handle_ajax_error(e, context=context_name or f"{self.__class__.__name__}.{func.__name__}")
            except TeamStatusError as e:
                return self.ajax_error(message=str(e), status=400)
            except ValidationError as e:
                return self.ajax_error(message=str(e), status=400)
            except json.JSONDecodeError:
                return self.ajax_error(message="Некорректный формат JSON данных", status=400)
            except Exception as e:
                return self.handle_ajax_error(e, context=context_name or f"{self.__class__.__name__}.{func.__name__}")
        return wrapper
    return decorator


class BaseAPIView(PerformanceMonitoringMixin, TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View):
    """Базовый класс для всех API views команд."""
    
    team_url_kwarg = "team_id"
    
    def parse_json_body(self, request):
        """Парсит JSON из тела запроса."""
        return json.loads(request.body)
    
    def validate_required_fields(self, data, *fields):
        """Проверяет наличие обязательных полей."""
        missing = [f for f in fields if not data.get(f)]
        if missing:
            raise ValidationError(f"Отсутствуют обязательные поля: {', '.join(missing)}")


class SearchAPIBase(BaseAPIView):
    """Базовый класс для поисковых API."""
    
    min_query_length = 2
    max_query_length = 100
    default_limit = 10
    max_limit = 50
    
    def validate_search_query(self, query):
        """Валидирует поисковый запрос."""
        if not query:
            raise ValidationError("Параметр поиска 'q' не может быть пустым")
        if len(query) < self.min_query_length:
            raise ValidationError(f"Минимум {self.min_query_length} символа для поиска")
        if len(query) > self.max_query_length:
            raise ValidationError(f"Максимум {self.max_query_length} символов для поиска")
        return query.strip()
    
    def get_search_params(self, request):
        """Извлекает и валидирует параметры поиска."""
        query = self.validate_search_query(request.GET.get('q', '').strip())
        limit = min(int(request.GET.get('limit', self.default_limit)), self.max_limit)
        return query, limit
