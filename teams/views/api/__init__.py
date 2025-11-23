"""
AJAX API представления для приложения teams.

Этот модуль содержит API представления для асинхронных операций
с командами, участниками и статусами. Все API возвращают JSON ответы
и используют стандартизированный формат ошибок.
"""

# Импорты будут добавлены по мере создания API представлений
from .members import TeamMemberListAPI, TeamMemberAddAPI, TeamMemberRemoveAPI, TeamMemberRoleUpdateAPI, TeamMemberBulkUpdateAPI, TeamRoleListAPI, TeamTransferLeadershipAPI
from .status import TeamStatusChangeAPI, TeamStatusInfoAPI, TeamStatusValidationAPI
from .search import TeamMemberSearchAPI, GlobalUserSearchAPI, TeamSearchAPI, QuickSearchAPI

__all__ = [
    # API управления участниками
    'TeamMemberListAPI',
    'TeamMemberAddAPI',
    'TeamMemberRemoveAPI',
    'TeamMemberRoleUpdateAPI',
    'TeamMemberBulkUpdateAPI',
    'TeamRoleListAPI',
    'TeamTransferLeadershipAPI',
    
    # API управления статусом
    'TeamStatusChangeAPI',

    'TeamStatusInfoAPI',
    'TeamStatusValidationAPI',
    
    # API поиска
    'TeamMemberSearchAPI',
    'GlobalUserSearchAPI',
    'TeamSearchAPI',
    'QuickSearchAPI',
]