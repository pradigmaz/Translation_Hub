"""
Модульные представления для приложения teams.

Этот модуль содержит импорты всех представлений команд,
организованных по функциональным модулям для улучшения
поддерживаемости и тестируемости кода.
"""

# Импорты будут добавлены по мере создания модульных представлений

# Основные CRUD операции с командами
from .team_crud import TeamDetailView, TeamUpdateView, TeamDeleteView
from .team_list import TeamListView, TeamSearchView, MyTeamsView, JoinedTeamsView
from .team_create import TeamCreateView, TeamCreateWizardView
from .team_leave import TeamLeaveView

# Управление статусом команды
from .status import TeamStatusChangeView, TeamStatusInfoView, TeamStatusValidateView

# Утилитарные представления
from .utils import TeamCountsView, team_permission_denied_view

# Управление участниками команды (серверный рендеринг)
from .members import TeamMemberSearchView

# Управление участниками команды (legacy представления)
# from .team_members import TeamMemberManagementView

# AJAX API для команд
# from .api.members import TeamMemberListAPI, TeamMemberAddAPI, TeamMemberRemoveAPI, TeamMemberRoleUpdateAPI
# from .api.status import TeamStatusChangeAPI, TeamStatusHistoryAPI
# from .api.search import TeamMemberSearchAPI

# Переходные представления для обратной совместимости
# from .legacy import TeamMemberManagementView as LegacyTeamMemberManagementView

__all__ = [
    # Основные представления
    'TeamListView',
    'TeamDetailView', 
    'TeamCreateView',
    'TeamUpdateView',
    'TeamDeleteView',
    'TeamLeaveView',
    
    # Специализированные списки
    'TeamSearchView',
    'MyTeamsView',
    'JoinedTeamsView',
    'TeamCreateWizardView',
    
    # Управление статусом
    'TeamStatusChangeView',
    'TeamStatusHistoryView',
    'TeamStatusInfoView',
    'TeamStatusValidateView',
    
    # Утилитарные представления
    'TeamCountsView',
    'team_permission_denied_view',
    
    # Управление участниками
    'TeamMemberSearchView',
    # 'TeamMemberManagementView',
    
    # AJAX API
    # 'TeamMemberListAPI',
    # 'TeamMemberAddAPI',
    # 'TeamMemberRemoveAPI', 
    # 'TeamMemberRoleUpdateAPI',
    # 'TeamStatusChangeAPI',
    # 'TeamStatusHistoryAPI',
    # 'TeamMemberSearchAPI',
    
    # Legacy представления
    # 'LegacyTeamMemberManagementView',
]