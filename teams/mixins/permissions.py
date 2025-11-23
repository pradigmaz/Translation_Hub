"""Миксины для проверки разрешений в представлениях команд."""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin

from ..models import Team
from ..permission_checker import RolePermissionChecker
from ..exceptions import TeamPermissionDenied, TeamNotFoundError



class TeamPermissionMixin:
    """Базовый миксин для проверки прав доступа к команде."""
    
    team_permission_required = None
    team_url_kwarg = 'pk'
    
    def get_team_or_404(self, team_id=None):
        """Получить команду с проверкой доступа."""
        if team_id is None:
            team_id = self.kwargs.get(self.team_url_kwarg)
        
        if not team_id:
            raise Http404("Команда не найдена")
        
        try:
            # Получаем команду с базовой проверкой существования
            team = get_object_or_404(Team, pk=team_id)
            
            # Проверяем базовый доступ к команде (участник или создатель)
            if not self._has_team_access(team):
                raise Http404("Команда не найдена")
            
            # Сохраняем команду в self.team для использования в других методах
            self.team = team
            
            return team
            
        except Team.DoesNotExist:
            raise TeamNotFoundError(f"Команда с ID {team_id} не найдена")
    
    def check_team_permission(self, permission, team=None):
        """Проверить конкретное разрешение для команды."""
        if team is None:
            # Сначала проверяем, есть ли уже сохраненная команда в self.team
            if hasattr(self, 'team') and self.team:
                team = self.team
            else:
                team = self.get_team_or_404()
        
        if not hasattr(self.request, 'user') or not self.request.user.is_authenticated:
            raise PermissionDenied("Необходима аутентификация")
        
        # Используем существующий RolePermissionChecker для проверки разрешений
        has_permission = RolePermissionChecker.user_has_team_permission(
            self.request.user, team, permission
        )
        
        if not has_permission:
            raise TeamPermissionDenied(f"У вас нет разрешения '{permission}' для этой команды")
        
        return True
    
    def handle_permission_denied(self, exception=None):
        """Обработать отказ в доступе."""
        if isinstance(exception, TeamPermissionDenied):
            error_message = str(exception)
        elif isinstance(exception, TeamNotFoundError):
            error_message = str(exception)
        else:
            error_message = "У вас нет прав для выполнения этого действия"
        
        # Если это AJAX запрос, возвращаем JSON ответ
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'error': error_message
            }, status=403)
        
        # Для обычных запросов поднимаем PermissionDenied
        raise PermissionDenied(error_message)
    
    def dispatch(self, request, *args, **kwargs):
        try:
            # Если установлено требуемое разрешение, проверяем его перед вызовом родительского dispatch
            if self.team_permission_required:
                self.check_team_permission(self.team_permission_required)
            
            # Вызываем родительский dispatch
            return super().dispatch(request, *args, **kwargs)
            
        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_permission_denied(e)
        except PermissionDenied as e:
            return self.handle_permission_denied(e)
    
    def _has_team_access(self, team):
        """Проверить базовый доступ к команде."""
        user = self.request.user
        
        if not user.is_authenticated:
            return False
        
        # Суперпользователи имеют доступ ко всем командам
        if user.is_superuser:
            return True
        
        # Создатель команды имеет доступ
        if team.creator == user:
            return True
        
        # Активные участники команды имеют доступ
        try:
            from ..models import TeamMembership
            return TeamMembership.objects.filter(
                team=team,
                user=user,
                is_active=True
            ).exists()
        except Exception as e:
            return False
    
    def get_user_teams_queryset(self):
        """Получить QuerySet команд, доступных текущему пользователю."""
        user = self.request.user
        
        if not user.is_authenticated:
            return Team.objects.none()
        
        if user.is_superuser:
            return Team.objects.all()
        
        # Команды где пользователь является создателем или активным участником
        return Team.objects.for_user(user)


class TeamOwnerRequiredMixin(TeamPermissionMixin):
    """Миксин, требующий права владельца команды."""
    
    def dispatch(self, request, *args, **kwargs):
        try:
            team = self.get_team_or_404()
            
            if not team.can_be_managed_by(request.user):
                raise TeamPermissionDenied(
                )
            
            return super().dispatch(request, *args, **kwargs)
            
        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_permission_denied(e)


class TeamMemberRequiredMixin(TeamPermissionMixin):
    """Миксин, требующий участия в команде."""
    
    def dispatch(self, request, *args, **kwargs):
        try:
            team = self.get_team_or_404()
            
            if not self._has_team_access(team):
                raise TeamPermissionDenied(
                )
            
            return super().dispatch(request, *args, **kwargs)
            
        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_permission_denied(e)