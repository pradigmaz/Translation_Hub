"""
Представления профиля для приложения users.

Содержит представления для просмотра и редактирования профиля пользователя.
"""

from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from projects.models import Chapter
from utils.network import get_client_ip
from ..models import User
from ..forms import ProfileForm
from ..mixins import PerformanceMonitoringMixin

# Настройка логгера безопасности


class ProfileView(LoginRequiredMixin, PerformanceMonitoringMixin, TemplateView):
    """
    Отображение профиля пользователя
    """
    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        """
        Подготовка данных профиля для шаблона
        """
        context = super().get_context_data(**kwargs)
        current_user = self.request.user
        
        # Статистика пользователя с оптимизированными запросами
        from teams.models import TeamMembership
        
        context["user_teams_count"] = current_user.teams.count()
        context["user_tasks_count"] = Chapter.objects.filter(assignee=current_user).count()
        context["completed_tasks_count"] = Chapter.objects.filter(
            assignee=current_user, 
            status='done'
        ).count()
        
        # Список команд с ролями
        memberships = TeamMembership.objects.filter(
            user=current_user,
            is_active=True
        ).select_related('team').prefetch_related('roles')
        
        context["user_memberships"] = memberships
        
        return context


