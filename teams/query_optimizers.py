"""
Утилиты для оптимизации запросов в приложении teams.
Содержит функции для предотвращения N+1 запросов.
"""

from django.db.models import Prefetch, Count, Q
from .models import Team, TeamMembership, Role
import logging

logger = logging.getLogger(__name__)


def optimize_team_detail_context(team, user):
    """
    Оптимизированное получение контекста для детальной страницы команды.
    Предотвращает N+1 запросы для всех связанных объектов.
    """
    from projects.models import Project
    
    # Получаем проекты с оптимизированным запросом и подсчетом глав
    projects = Project.objects.filter(team=team)\
        .select_related('team')\
        .annotate(chapters_count=Count('chapters'))\
        .order_by('-created_at')
    
    # Получаем участников с ролями одним запросом
    memberships_queryset = TeamMembership.objects.filter(team=team)\
        .select_related('user')\
        .prefetch_related(
            Prefetch('roles', queryset=Role.objects.only('id', 'name'))
        )\
        .order_by('user__username')
    
    if team.is_active():
        memberships_queryset = memberships_queryset.filter(is_active=True)
    
    # Выполняем запрос один раз
    memberships = list(memberships_queryset)
    
    # История статусов хранится в логах, не в БД
    recent_status_changes = []
    
    # Получаем роли для JavaScript одним запросом
    roles = list(Role.objects.exclude(name__in=['Пользователь', 'Руководитель'])\
        .only('id', 'name', 'description')\
        .order_by('name'))
    
    # Находим участие текущего пользователя в уже загруженных данных
    user_membership = None
    for membership in memberships:
        if membership.user == user:
            user_membership = membership
            break
    
    return {
        'projects': projects,
        'memberships': memberships,
        'recent_status_changes': recent_status_changes,
        'roles': roles,
        'user_membership': user_membership,
        'is_creator': team.creator == user,
        'can_manage_team': team.can_be_managed_by(user)
    }


def optimize_team_list_context(user):
    """
    Оптимизированное получение контекста для списка команд.
    """
    from django.db.models import Q, Count
    
    # Получаем команды пользователя с оптимизированными запросами
    # Команды где пользователь создатель или активный участник
    teams = Team.objects.filter(
        Q(creator=user) | Q(teammembership__user=user, teammembership__is_active=True)
    ).distinct().select_related('creator').prefetch_related('teammembership_set__user')
    
    # Получаем статистику по статусам
    status_counts = {
        'active': teams.filter(status='active').count(),
        'inactive': teams.filter(status='inactive').count(),
        'disbanded': teams.filter(status='disbanded').count(),
    }
    
    return {
        'teams': teams,
        'status_counts': status_counts
    }