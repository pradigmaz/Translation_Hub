"""Управление ролями участника команды (GET/POST)."""

from typing import Optional
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import get_user_model

from ...models import Team, TeamMembership, Role
from ...mixins import TeamPermissionMixin
from ...forms import MemberRoleUpdateForm

User = get_user_model()


class TeamMemberRoleManageView(LoginRequiredMixin, TeamPermissionMixin, FormView):
    """Управление ролями участника. GET: форма, POST: обновление roles.set()."""
    
    template_name = 'teams/members/member_role_manage.html'
    form_class = MemberRoleUpdateForm
    team_permission_required = 'can_assign_roles'
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
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        """Возвращает аргументы для инициализации формы."""
        kwargs = super().get_form_kwargs()
        kwargs['membership'] = self.membership
        return kwargs
    
    def form_valid(self, form):
        """Обновление ролей и редирект."""
        try:
            # Получаем выбранные роли
            role_ids = form.cleaned_data['role_ids']
            
            # Обновляем роли
            self.membership.roles.set(role_ids)
            
            # Успешное уведомление
            role_names = ', '.join([role.name for role in role_ids])
            messages.success(
                self.request,
                f'Роли пользователя {self.member_user.username} успешно обновлены: {role_names}'
            )
            
            return redirect('teams:team_member_list', team_id=self.team.id)
            
        except Exception as e:
            messages.error(
                self.request,
                'Произошла ошибка при обновлении ролей. Пожалуйста, попробуйте позже.'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Рендер формы с ошибками."""
        
        messages.error(
            self.request,
            'Пожалуйста, исправьте ошибки в форме'
        )
        
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Контекст: team, member_user, membership."""
        context = super().get_context_data(**kwargs)
        context['team'] = self.team
        context['member_user'] = self.member_user
        context['membership'] = self.membership
        
        return context
