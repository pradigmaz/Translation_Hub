"""
Утилитные функции для управления жизненным циклом команд
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import Team, TeamMembership, TeamStatus, TeamStatusChangeType

User = get_user_model()
logger = logging.getLogger('role_audit')


@transaction.atomic
def deactivate_team(team, user, reason=""):
    """Приостановка работы команды."""
    if not team.can_be_managed_by(user):
        raise PermissionError("Недостаточно прав для управления командой")
    
    if team.status != TeamStatus.ACTIVE:
        raise ValueError("Можно приостановить только активную команду")
    
    old_status = team.status
    team.status = TeamStatus.INACTIVE
    team.save()
    
    # Логируем в файл
    logger.info(
        f"Team deactivated | Team: {team.name} (ID: {team.id}) | "
        f"Changed by: {user.username} | Old status: {old_status} | "
        f"New status: {team.status} | Reason: {reason}"
    )
    
    return True


@transaction.atomic
def reactivate_team(team, user, reason=""):
    """Возобновление работы команды."""
    if not team.can_be_managed_by(user):
        raise PermissionError("Недостаточно прав для управления командой")
    
    if team.status != TeamStatus.INACTIVE:
        raise ValueError("Можно возобновить только приостановленную команду")
    
    old_status = team.status
    team.status = TeamStatus.ACTIVE
    team.save()
    
    # Реактивируем всех участников
    reactivated_count = TeamMembership.objects.filter(team=team).update(is_active=True)
    
    # Логируем в файл
    logger.info(
        f"Team reactivated | Team: {team.name} (ID: {team.id}) | "
        f"Changed by: {user.username} | Old status: {old_status} | "
        f"New status: {team.status} | Reactivated members: {reactivated_count} | "
        f"Reason: {reason}"
    )
    
    return True


@transaction.atomic
def disband_team(team, user, reason=""):
    """Роспуск команды."""
    if not team.can_be_managed_by(user):
        raise PermissionError("Недостаточно прав для управления командой")
    
    if team.status == TeamStatus.DISBANDED:
        raise ValueError("Команда уже распущена")
    
    old_status = team.status
    team.status = TeamStatus.DISBANDED
    team.save()
    
    # Деактивируем всех участников
    deactivated_count = TeamMembership.objects.filter(team=team).update(is_active=False)
    
    # Логируем в файл
    logger.info(
        f"Team disbanded | Team: {team.name} (ID: {team.id}) | "
        f"Changed by: {user.username} | Old status: {old_status} | "
        f"New status: {team.status} | Deactivated members: {deactivated_count} | "
        f"Reason: {reason}"
    )
    
    return True


def get_team_status_statistics(user=None):
    """Статистика по статусам команд."""
    from django.db.models import Q
    
    queryset = Team.objects.all()
    
    if user:
        queryset = Team.objects.for_user(user)
    
    statistics = {
        'active': queryset.filter(status=TeamStatus.ACTIVE).count(),
        'inactive': queryset.filter(status=TeamStatus.INACTIVE).count(),
        'disbanded': queryset.filter(status=TeamStatus.DISBANDED).count(),
        'total': queryset.count()
    }
    return statistics


def can_perform_team_action(team, user, action):
    """Проверка возможности выполнения действия с командой."""
    if not team.can_be_managed_by(user):
        return False, "Недостаточно прав для управления командой"
    
    if action == 'deactivate':
        if team.status != TeamStatus.ACTIVE:
            return False, "Можно приостановить только активную команду"
    elif action == 'reactivate':
        if team.status != TeamStatus.INACTIVE:
            return False, "Можно возобновить только приостановленную команду"
    elif action == 'disband':
        if team.status == TeamStatus.DISBANDED:
            return False, "Команда уже распущена"
    else:
        return False, "Неизвестное действие"
    
    return True, ""