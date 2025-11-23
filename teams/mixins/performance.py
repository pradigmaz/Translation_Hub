"""Миксин для мониторинга производительности представлений команд."""

import time
from django.conf import settings
from django.db import connection
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

# Настройка логгера производительности


class PerformanceMonitoringMixin:
    """Миксин для мониторинга производительности представлений."""
    
    # Пороговое значение для медленных запросов (в секундах)
    SLOW_REQUEST_THRESHOLD = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 1.0)
    
    # Пороговое значение для большого количества SQL запросов
    HIGH_QUERY_COUNT_THRESHOLD = getattr(settings, 'HIGH_QUERY_COUNT_THRESHOLD', 20)
    
    def dispatch(self, request, *args, **kwargs):
        # Запоминаем начальные метрики
        start_time = time.time()
        start_queries_count = len(connection.queries)
        
        # Получаем информацию о представлении
        view_name = self.__class__.__name__
        method = request.method
        user = getattr(request, 'user', None)
        user_id = user.id if user and user.is_authenticated else None
        
        try:
            # Выполняем основную логику представления
            response = super().dispatch(request, *args, **kwargs)
            
            # Вычисляем метрики производительности
            end_time = time.time()
            execution_time = end_time - start_time
            end_queries_count = len(connection.queries)
            queries_count = end_queries_count - start_queries_count
            
            # Вычисляем общее время SQL запросов
            sql_time = 0
            if hasattr(settings, 'DEBUG') and settings.DEBUG:
                for query in connection.queries[start_queries_count:]:
                    sql_time += float(query['time'])
            
            # Логируем метрики
            self._log_performance_metrics(
                view_name=view_name,
                method=method,
                user_id=user_id,
                execution_time=execution_time,
                queries_count=queries_count,
                sql_time=sql_time,
                status_code=response.status_code
            )
            
            # Проверяем на медленные запросы
            if execution_time > self.SLOW_REQUEST_THRESHOLD:
                self._log_slow_request(
                    view_name=view_name,
                    method=method,
                    user_id=user_id,
                    execution_time=execution_time,
                    queries_count=queries_count,
                    sql_time=sql_time
                )
            
            # Проверяем на большое количество SQL запросов
            if queries_count > self.HIGH_QUERY_COUNT_THRESHOLD:
                self._log_high_query_count(
                    view_name=view_name,
                    method=method,
                    user_id=user_id,
                    queries_count=queries_count,
                    execution_time=execution_time
                )
            
            return response
            
        except Exception as e:
            # Логируем ошибки с метриками
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Повторно возбуждаем исключение
            raise
    
    def _log_performance_metrics(self, view_name, method, user_id, execution_time, 
                                queries_count, sql_time, status_code):
        pass
    
    def _log_slow_request(self, view_name, method, user_id, execution_time, 
                         queries_count, sql_time):
        
        # В режиме DEBUG также логируем детали SQL запросов
        if hasattr(settings, 'DEBUG') and settings.DEBUG and queries_count > 0:
            start_queries_count = len(connection.queries) - queries_count
            for i, query in enumerate(connection.queries[start_queries_count:], 1):
                pass
    
    def _log_high_query_count(self, view_name, method, user_id, queries_count, execution_time):
        pass


class CacheControlMixin:
    """Миксин для управления кэшированием представлений."""
    
    # Время кэширования по умолчанию (в секундах)
    cache_timeout = getattr(settings, 'DEFAULT_CACHE_TIMEOUT', 300)  # 5 минут
    
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get_cache_key(self, request, *args, **kwargs):
        view_name = self.__class__.__name__
        user_id = request.user.id if request.user.is_authenticated else 'anonymous'
        
        # Создаем базовый ключ
        cache_key = f"{view_name}:{user_id}"
        
        # Добавляем параметры URL
        if kwargs:
            params = ':'.join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key += f":{params}"
        
        # Добавляем GET параметры для списков с фильтрацией
        if request.GET:
            get_params = ':'.join(f"{k}={v}" for k, v in sorted(request.GET.items()))
            cache_key += f":get:{get_params}"
        
        return cache_key
    
    def set_cache_headers(self, response, max_age=None):
        if max_age is None:
            max_age = self.cache_timeout
        
        response['Cache-Control'] = f'max-age={max_age}, private'
        response['Vary'] = 'Cookie, Accept-Language'
        
        return response


class QueryOptimizationMixin:
    """Миксин для оптимизации запросов к базе данных."""
    
    def get_optimized_queryset(self, queryset, select_related_fields=None, 
                              prefetch_related_fields=None):
        if select_related_fields:
            queryset = queryset.select_related(*select_related_fields)
        
        if prefetch_related_fields:
            queryset = queryset.prefetch_related(*prefetch_related_fields)
        
        return queryset
    
    def log_queryset_info(self, queryset, description="QuerySet"):
        if hasattr(settings, 'DEBUG') and settings.DEBUG:
            try:
                # Получаем SQL запрос
                sql_query = str(queryset.query)
            except Exception as e:
                pass