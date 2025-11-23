"""Сетевые утилиты для получения IP-адресов клиентов."""

from typing import Optional


def get_client_ip(request) -> Optional[str]:
    """Получение IP-адреса клиента из HTTP запроса."""
    # Проверка валидности объекта request
    if not request:
        return None
        
    # Проверка наличия META атрибута
    if not hasattr(request, 'META') or not request.META:
        return None
    
    try:
        # Получение заголовка HTTP_X_FORWARDED_FOR
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        
        if x_forwarded_for:
            # Извлечение первого IP-адреса из списка и удаление пробелов
            ip = x_forwarded_for.split(',')[0].strip()
            # Возврат IP только если он не пустой
            return ip if ip else None
        else:
            # Fallback на REMOTE_ADDR
            remote_addr = request.META.get('REMOTE_ADDR')
            return remote_addr.strip() if remote_addr else None
            
    except (AttributeError, IndexError, TypeError):
        # Graceful обработка любых ошибок при работе с заголовками
        return None


# Экспорт функций модуля
__all__ = ['get_client_ip']