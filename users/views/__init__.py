"""
Модульные представления для приложения users.

Этот модуль содержит импорты всех представлений пользователей,
организованных по функциональным модулям для улучшения
поддерживаемости и тестируемости кода.
"""

# Представления аутентификации
from .auth import RegisterView

# Представления профиля
from .profile import ProfileView

# Представление дашборда
from .dashboard import DashboardView

# Представления настроек
from .settings import TeamsView, TasksView, SettingsView

__all__ = [
    # Аутентификация
    'RegisterView',
    
    # Профиль
    'ProfileView',
    
    # Дашборд
    'DashboardView',
    
    # Настройки
    'TeamsView',
    'TasksView',
    'SettingsView',
]