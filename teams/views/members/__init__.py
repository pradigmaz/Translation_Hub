"""
Представления для управления участниками команды.

Этот модуль содержит представления для поиска, добавления и управления
участниками команды с использованием серверного рендеринга.
"""

from .member_search import TeamMemberSearchView
from .member_add import TeamMemberAddView
from .member_list import TeamMemberListView
from .member_role_manage import TeamMemberRoleManageView
from .member_remove_confirm import TeamMemberRemoveConfirmView
from .leadership_transfer import LeadershipTransferView

__all__ = [
    'TeamMemberSearchView',
    'TeamMemberAddView',
    'TeamMemberListView',
    'TeamMemberRoleManageView',
    'TeamMemberRemoveConfirmView',
    'LeadershipTransferView',
]
