from django.contrib import admin
from django.contrib.admin import AdminSite
from .admin_utils import disable_admin_messages


class TranslationHubAdminSite(AdminSite):
    site_header = 'TranslationHub - Административная панель'
    site_title = 'TranslationHub Admin'
    index_title = 'Управление системой переводов'
    
    def __init__(self, name='admin'):
        super().__init__(name)
        disable_admin_messages()


admin_site = TranslationHubAdminSite()

disable_admin_messages()