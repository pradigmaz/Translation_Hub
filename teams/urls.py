from django.urls import path, include

from .views.team_crud import TeamDetailView, TeamUpdateView, TeamDeleteView
from .views.team_list import TeamListView, TeamSearchView, MyTeamsView, JoinedTeamsView
from .views.team_create import TeamCreateView, TeamCreateWizardView
from .views.team_leave import TeamLeaveView
from .views.status import TeamStatusChangeView, TeamStatusInfoView, TeamStatusValidateView
from .views.utils import TeamCountsView, team_permission_denied_view
from .views.members.member_search import TeamMemberSearchView
from .views.members.member_add import TeamMemberAddView
from .views.members.member_list import TeamMemberListView
from .views.members.member_role_manage import TeamMemberRoleManageView
from .views.members.member_remove_confirm import TeamMemberRemoveConfirmView
from .views.members.leadership_transfer import LeadershipTransferView

app_name = 'teams'

urlpatterns = [
    # CRUD операции
    path('', TeamListView.as_view(), name='team_list'),
    path('create/', TeamCreateView.as_view(), name='team_create'),
    path('create/wizard/', TeamCreateWizardView.as_view(), name='team_create_wizard'),
    path('<int:pk>/', TeamDetailView.as_view(), name='team_detail'),
    path('<int:pk>/edit/', TeamUpdateView.as_view(), name='team_edit'),
    path('<int:pk>/delete/', TeamDeleteView.as_view(), name='team_delete'),
    path('<int:team_id>/leave/', TeamLeaveView.as_view(), name='team_leave'),
    
    # Списки команд
    path('search/', TeamSearchView.as_view(), name='team_search'),
    path('my/', MyTeamsView.as_view(), name='my_teams'),
    path('joined/', JoinedTeamsView.as_view(), name='joined_teams'),
    
    # Управление статусом
    path('<int:team_id>/status/', TeamStatusChangeView.as_view(), name='team_status_change'),
    # team_status_history удалена - история в logs/role_audit.log
    path('<int:team_id>/status/info/', TeamStatusInfoView.as_view(), name='team_status_info'),
    path('<int:team_id>/status/validate/', TeamStatusValidateView.as_view(), name='team_status_validate'),
    
    # Управление участниками
    path('<int:team_id>/members/', TeamMemberListView.as_view(), name='team_member_list'),
    path('<int:team_id>/members/search/', TeamMemberSearchView.as_view(), name='team_member_search'),
    path('<int:team_id>/members/add/', TeamMemberAddView.as_view(), name='team_member_add'),
    path('<int:team_id>/members/<int:user_id>/roles/', TeamMemberRoleManageView.as_view(), name='team_member_role_manage'),
    path('<int:team_id>/members/<int:user_id>/remove/', TeamMemberRemoveConfirmView.as_view(), name='team_member_remove_confirm'),
    path('<int:team_id>/members/<int:user_id>/transfer-leadership/', LeadershipTransferView.as_view(), name='leadership_transfer'),
    
    # Утилиты
    path('api/counts/', TeamCountsView.as_view(), name='team_counts'),
    path('permission-denied/', team_permission_denied_view, name='permission_denied'),
    path('api/', include('teams.api_urls', namespace='api')),
]
