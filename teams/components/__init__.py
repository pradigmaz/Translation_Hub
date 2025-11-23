"""
Компоненты управления для приложения teams.

Этот модуль содержит бизнес-логику для управления командами,
участниками и статусами. Компоненты инкапсулируют сложную логику
и предоставляют простые интерфейсы для представлений.
"""

# Импорты будут добавлены по мере создания компонентов
from .member_manager import TeamMemberManager
from .status_manager import TeamStatusManager
from .context_builder import TeamContextBuilder

__all__ = [
    'TeamMemberManager',
    'TeamStatusManager', 
    'TeamContextBuilder',
]