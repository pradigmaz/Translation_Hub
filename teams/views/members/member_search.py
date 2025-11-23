"""Поиск пользователей для добавления в команду."""

from typing import Optional
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView
from django.db.models import Q, QuerySet
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from ...models import Team, TeamMembership
from ...forms import UserSearchForm
from ...mixins import TeamPermissionMixin

User = get_user_model()


class TeamMemberSearchView(LoginRequiredMixin, TeamPermissionMixin, FormView):
    """Поиск пользователей (username/email), исключая существующих участников. Лимит 20."""
    
    template_name = 'teams/members/member_search.html'
    form_class = UserSearchForm
    team_permission_required = 'can_invite_members'
    team_url_kwarg = 'team_id'
    
    def dispatch(self, request, *args, **kwargs):
        """Кэширование команды."""
        # Получаем команду один раз и сохраняем для использования в методах
        self.team = self.get_team_or_404()
        
        # Вызываем родительский dispatch, который проверит разрешения
        # через TeamPermissionMixin.dispatch() -> check_team_permission()
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        """Рендер формы поиска."""
        # Создаем пустую форму (не валидируем GET параметры)
        form = self.form_class()
        
        # Возвращаем контекст с формой и результатами поиска
        return self.render_to_response(self.get_context_data(form=form))
    
    def get_queryset(self) -> QuerySet:
        """Поиск по username/email, исключая существующих участников. Лимит 20."""
        query = self.request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return User.objects.none()
        
        # Исключаем пользователей, уже состоящих в команде
        existing_members = TeamMembership.objects.filter(
            team=self.team,
            is_active=True
        ).values_list('user_id', flat=True)
        
        # Поиск по username и email
        queryset = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        ).exclude(
            id__in=existing_members
        )[:20]
        
        return queryset
    
    def get_context_data(self, **kwargs) -> dict:
        """Контекст: team, search_query, users, has_results."""
        context = super().get_context_data(**kwargs)
        context['team'] = self.team
        context['search_query'] = self.request.GET.get('q', '')
        
        if context['search_query']:
            context['users'] = self.get_queryset()
            context['has_results'] = context['users'].exists()
        else:
            context['users'] = User.objects.none()
            context['has_results'] = False
        
        return context
