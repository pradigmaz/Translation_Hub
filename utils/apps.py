# Конфигурация приложения utils для управления файловой структурой.

from django.apps import AppConfig


class UtilsConfig(AppConfig):
    """Конфигурация приложения utils"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'utils'
    verbose_name = 'Утилиты'
    
    def ready(self):
        """
        Инициализация приложения.
        
        Импортирует сигналы и создает базовые папки при запуске системы.
        Инициализирует систему мониторинга файлов.
        """
        # Импортируем сигналы для их регистрации
        from . import signals
        
        # Инициализируем базовые папки
        try:
            signals.initialize_base_directories()
        except Exception:
            pass
        
        # Инициализируем систему мониторинга файлов
        try:
            from .file_monitoring import file_metrics
            # Инициализируем кэш метрик
            file_metrics.get_cached_metrics()
        except Exception:
            pass
