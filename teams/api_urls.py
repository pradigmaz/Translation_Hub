"""
URL маршруты для AJAX API команд.

Этот модуль содержит все URL маршруты для API представлений команд,
организованные по функциональным группам для лучшей читаемости.
"""

from django.urls import path

from .views.api import (
    TeamMemberListAPI,
    TeamMemberAddAPI,
    TeamMemberRemoveAPI,
    TeamMemberRoleUpdateAPI,
    TeamMemberBulkUpdateAPI,
    TeamRoleListAPI,
    TeamTransferLeadershipAPI,
    TeamStatusChangeAPI,

    TeamStatusInfoAPI,
    TeamStatusValidationAPI,
)
from .views.api.search import (
    TeamMemberSearchAPI,
    GlobalUserSearchAPI,
    TeamSearchAPI,
    QuickSearchAPI,
)

app_name = 'teams_api'

urlpatterns = [
    # API управления участниками команды
    path('<int:team_id>/members/', TeamMemberListAPI.as_view(), name='member_list'),
    path('<int:team_id>/members/add/', TeamMemberAddAPI.as_view(), name='member_add'),
    path('<int:team_id>/members/remove/', TeamMemberRemoveAPI.as_view(), name='member_remove'),
    path('<int:team_id>/members/roles/', TeamMemberRoleUpdateAPI.as_view(), name='member_role_update'),
    path('<int:team_id>/members/bulk/', TeamMemberBulkUpdateAPI.as_view(), name='member_bulk_update'),
    path('<int:team_id>/roles/', TeamRoleListAPI.as_view(), name='role_list'),
    path('<int:team_id>/transfer-leadership/', TeamTransferLeadershipAPI.as_view(), name='transfer_leadership'),
    # API управления статусом команды
    path('<int:team_id>/status/change/', TeamStatusChangeAPI.as_view(), name='status_change'),
    # status_history удалена - история в logs/role_audit.log
    path('<int:team_id>/status/info/', TeamStatusInfoAPI.as_view(), name='status_info'),
    path('<int:team_id>/status/validate/', TeamStatusValidationAPI.as_view(), name='status_validate'),
    # API поиска
    path('<int:team_id>/search/members/', TeamMemberSearchAPI.as_view(), name='search_members'),
    path('search/users/', GlobalUserSearchAPI.as_view(), name='search_users'),
    path('search/teams/', TeamSearchAPI.as_view(), name='search_teams'),
    path('search/quick/', QuickSearchAPI.as_view(), name='search_quick'),
]