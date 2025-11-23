"""
Представление для самостоятельного выхода из команды.

Этот модуль содержит простое представление для обработки выхода участников
из команды без участия руководителя команды.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404

from ..models import Team, TeamMembership, TeamStatus



class TeamLeaveView(LoginRequiredMixin, View):
    """Представление для выхода участника из команды."""
    
    def _validate_can_leave(self, team, user):
        """Проверяет возможность выхода из команды."""
        if team.creator == user:
            return False, "Создатель команды не может покинуть команду. Передайте права руководства другому участнику."
        if team.status == TeamStatus.DISBANDED:
            return False, "Нельзя покинуть распущенную команду."
        return True, None
    
    def _get_membership(self, team, user):
        """Получает активное участие пользователя в команде."""
        return TeamMembership.objects.select_related('user', 'team')\
            .prefetch_related('roles')\
            .get(user=user, team=team, is_active=True)
    
    def _handle_leave(self, membership, team, user):
        """Выполняет выход из команды."""
        user_roles = list(membership.roles.values_list('name', flat=True))
        membership.deactivate()
        return user_roles
    
    def post(self, request, team_id):
        """Обрабатывает выход участника из команды."""
        try:
            team = get_object_or_404(Team, pk=team_id)
            
            # Валидация
            can_leave, error_msg = self._validate_can_leave(team, request.user)
            if not can_leave:
                messages.error(request, error_msg)
                return redirect('teams:team_detail', pk=team_id)
            
            # Получение участия
            try:
                membership = self._get_membership(team, request.user)
            except TeamMembership.DoesNotExist:
                messages.error(request, "Вы не являетесь активным участником этой команды.")
                return redirect('teams:team_detail', pk=team_id)
            
            # Выход из команды
            self._handle_leave(membership, team, request.user)
            
            messages.success(
                request,
                f"Вы успешно покинули команду \"{team.name}\". "
                f"Руководитель команды может пригласить вас обратно при необходимости."
            )
            return redirect('teams:team_list')
            
        except Http404:
            raise
        except Exception as e:
            messages.error(request, "Произошла ошибка при выходе из команды. Попробуйте еще раз.")
            return redirect('teams:team_detail', pk=team_id)
    
    def get(self, request, team_id):
        """
        Обрабатывает GET запросы (не поддерживается).
        
        Args:
            request: HTTP запрос
            team_id: ID команды
            
        Returns:
            HttpResponse: Редирект на страницу команды
        """
        messages.warning(
            request,
            "Выход из команды возможен только через подтверждение."
        )
        return redirect('teams:team_detail', pk=team_id)