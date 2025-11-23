"""
Content app admin - аудит перенесен в file-based logging
"""

from django.contrib import admin

# ContentAuditLogAdmin удалена - используется file-based logging в logs/content_audit.log


# Настройка заголовков админки
admin.site.site_header = "TranslationHub - Управление"
admin.site.site_title = "TranslationHub Admin"
admin.site.index_title = "Панель управления"
