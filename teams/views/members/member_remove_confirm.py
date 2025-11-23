"""Удаление участника из команды с подтверждением (GET/POST)."""

from typing import Optional
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from ...models import Team, TeamMembership
from ...mixins import TeamPermissionMixin

User = get_user_model()


class TeamMemberRemoveConfirmView(LoginRequiredMixin, TeamPermissionMixin, TemplateView):
    """Подтверждение удаления участника. GET: форма, POST: деактивация членства."""
    
    template_name = 'teams/members/member_remove_confirm.html'
    team_permission_required = 'can_remove_members'
    team_url_kwarg = 'team_id'
    
    def dispatch(self, request, *args, **kwargs):
        """Переопределяем dispatch для кэширования объектов."""
        # Получаем команду через миксин
        self.team = self.get_team_or_404()
        
        # Получаем участника
        user_id = self.kwargs.get('user_id')
        self.member_user = get_object_or_404(User, pk=user_id)
        
        # Получаем членство
        self.membership = get_object_or_404(
            TeamMembership,
            team=self.team,
            user=self.member_user,
            is_active=True
        )
        
        # Проверяем, что пользователь не пытается удалить сам себя
        if self.member_user == request.user:
            messages.error(request, 'Вы не можете удалить сами себя из команды. Используйте функцию "Покинуть команду".')
            return redirect('teams:team_member_list', team_id=self.team.id)
        
        # Проверяем, что пользователь не пытается удалить создателя команды
        if self.member_user == self.team.creator:
            messages.error(request, 'Нельзя удалить создателя команды.')
            return redirect('teams:team_member_list', team_id=self.team.id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Деактивация членства и редирект."""
        try:
            # Деактивируем членство
            self.membership.is_active = False
            self.membership.save()
            
            # Успешное уведомление
            messages.success(
                request,
                f'Пользователь {self.member_user.username} успешно удален из команды'
            )
            
            return redirect('teams:team_member_list', team_id=self.team.id)
            
        except Exception as e:
            messages.error(
                request,
                'Произошла ошибка при удалении участника. Пожалуйста, попробуйте позже.'
            )
            return redirect('teams:team_member_list', team_id=self.team.id)
    
    def get_context_data(self, **kwargs):
        """Контекст: team, member_user, membership."""
        context = super().get_context_data(**kwargs)
        context['team'] = self.team
        context['member_user'] = self.member_user
        context['membership'] = self.membership
        
        return context
