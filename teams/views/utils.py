"""Утилитарные представления для teams."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Q

from ..models import Team, TeamStatus


class TeamCountsView(LoginRequiredMixin, View):
    """AJAX: счетчики команд пользователя по статусам (JSON)."""
    
    def get(self, request):
        """JSON с количеством команд по статусам."""
        user_teams = Team.objects.filter(
            Q(teammembership__user=request.user, teammembership__is_active=True) | Q(creator=request.user)
        ).distinct()
        
        counts = {
            'active': user_teams.filter(status=TeamStatus.ACTIVE).count(),
            'inactive': user_teams.filter(status=TeamStatus.INACTIVE).count(),
            'disbanded': user_teams.filter(status=TeamStatus.DISBANDED).count(),
        }
        
        return JsonResponse(counts)


def team_permission_denied_view(request, exception=None):
    """Обработка ошибок доступа к командам."""
    
    # Получаем информацию об ошибке
    error_message = str(exception) if exception else "У вас нет прав для выполнения этого действия"
    
    # Определяем тип ошибки и предложения
    suggestions = [
        "Убедитесь, что вы являетесь участником команды",
        "Проверьте, что ваша роль в команде имеет необходимые разрешения",
        "Обратитесь к руководителю команды для назначения соответствующих прав",
        "Свяжитесь с администратором системы, если считаете, что произошла ошибка"
    ]
    
    # Логируем ошибку доступа
    
    context = {
        'error_message': error_message,
        'object_type': 'Команда',
        'error_type': 'permission_denied',
        'suggestions': suggestions,
        'back_url': request.META.get('HTTP_REFERER'),
    }
    
    return render(request, 'teams/errors/403.html', context, status=403)