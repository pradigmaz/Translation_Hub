"""Список участников команды с фильтрацией и сортировкой."""

from typing import Optional
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.shortcuts import get_object_or_404
from django.db.models import QuerySet, Prefetch, Q

from ...models import Team, TeamMembership, Role
from ...mixins import TeamPermissionMixin



class TeamMemberListView(LoginRequiredMixin, TeamPermissionMixin, ListView):
    """
    Список участников команды с фильтрацией (роль, статус, поиск) и сортировкой.
    Оптимизация: select_related('user'), prefetch_related('roles').
    """
    
    model = TeamMembership
    template_name = 'teams/members/member_list.html'
    context_object_name = 'members'
    paginate_by = 20
    team_permission_required = 'can_view_members'
    team_url_kwarg = 'team_id'
    
    def dispatch(self, request, *args, **kwargs):
        """Переопределяем dispatch для кэширования объекта команды."""
        # Сохраняем команду как атрибут экземпляра для использования в других методах
        self.team = self.get_team_or_404()
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self) -> QuerySet:
        """
        QuerySet с фильтрацией (role, is_active, search) и сортировкой (whitelist).
        """
        # Базовый QuerySet с оптимизацией
        queryset = TeamMembership.objects.filter(
            team=self.team,
            is_active=True
        ).select_related(
            'user'
        ).prefetch_related(
            Prefetch('roles', queryset=Role.objects.all())
        )
        
        # Фильтрация по роли (Strategy Pattern)
        role_filter = self.request.GET.get('role', '').strip()
        if role_filter:
            queryset = queryset.filter(roles__name=role_filter)
        
        # Фильтрация по статусу активности
        is_active = self.request.GET.get('is_active', '').strip()
        if is_active in ['true', 'false']:
            queryset = queryset.filter(is_active=(is_active == 'true'))
        
        # Поиск по имени пользователя или email
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search)
            )
        
        # Сортировка с валидацией (whitelist полей)
        sort_by = self.request.GET.get('sort', 'user__username').strip()
        valid_sort_fields = [
            'user__username', '-user__username',
            'joined_at', '-joined_at',
            'is_active', '-is_active'
        ]
        
        if sort_by in valid_sort_fields:
            queryset = queryset.order_by(sort_by)
        else:
            # Сортировка по умолчанию
            queryset = queryset.order_by('user__username')
        
        return queryset
    
    def get_context_data(self, **kwargs) -> dict:
        """Контекст: team, current_filters, available_roles, permissions."""
        context = super().get_context_data(**kwargs)
        
        # Добавляем команду в контекст
        context['team'] = self.team
        
        # Добавляем текущие фильтры для отображения в шаблоне
        context['current_filters'] = {
            'role': self.request.GET.get('role', ''),
            'is_active': self.request.GET.get('is_active', ''),
            'search': self.request.GET.get('search', ''),
            'sort': self.request.GET.get('sort', 'user__username')
        }
        
        # Добавляем список доступных ролей для фильтрации
        context['available_roles'] = Role.objects.all().order_by('name')
        
        # Добавляем разрешения пользователя для отображения кнопок управления
        from ...permission_checker import RolePermissionChecker
        context['can_invite_members'] = RolePermissionChecker.user_has_team_permission(
            self.request.user, self.team, 'can_invite_members'
        )
        context['can_assign_roles'] = RolePermissionChecker.user_has_team_permission(
            self.request.user, self.team, 'can_assign_roles'
        )
        context['can_remove_members'] = RolePermissionChecker.user_has_team_permission(
            self.request.user, self.team, 'can_remove_members'
        )
        
        return context
