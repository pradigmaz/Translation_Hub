"""Утилиты для кастомизации админ-панели Django."""

from django.contrib import admin
from django.contrib import messages


class NoMessagesAdminMixin:
    """Mixin для админ-классов, убирает системные уведомления."""
    
    def message_user(self, request, message, level=messages.INFO, extra_tags='', fail_silently=False):
        """Показывает только ERROR+."""
        if level >= messages.ERROR:
            super().message_user(request, message, level, extra_tags, fail_silently)


def disable_admin_messages():
    """Глобально отключает стандартные уведомления Django админки."""
    original_message_user = admin.ModelAdmin.message_user
    
    def silent_message_user(self, request, message, level=messages.INFO, extra_tags='', fail_silently=False):
        if level >= messages.ERROR:
            original_message_user(self, request, message, level, extra_tags, fail_silently)
    
    admin.ModelAdmin.message_user = silent_message_user