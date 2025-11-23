"""
Представление дашборда для приложения users.

Содержит главную страницу личного кабинета пользователя.
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from projects.models import Chapter, Project
from ..mixins import PerformanceMonitoringMixin


class DashboardView(LoginRequiredMixin, PerformanceMonitoringMixin, TemplateView):
    """
    Отображение личного кабинета пользователя с командами и задачами
    """

    template_name = "users/dashboard.html"

    def get_context_data(self, **kwargs):
        """
        Подготовка и передача данных в шаблон с оптимизированными запросами
        """
        context = super().get_context_data(**kwargs)
        current_user = self.request.user

        # Добавление аватарки пользователя в контекст
        context["user_avatar"] = current_user.avatar if current_user.avatar else None

        # Добавление списка команд пользователя в контекст с оптимизацией
        from teams.models import Team
        from django.db.models import Q
        
        user_teams = Team.objects.filter(
            Q(teammembership__user=current_user, teammembership__is_active=True) | Q(creator=current_user)
        ).select_related('creator').distinct().order_by("name")
        context["user_teams"] = user_teams
        context["teams_count"] = user_teams.count()

        # Добавление списка назначенных пользователю глав в контекст (исключая завершённые)
        user_tasks = Chapter.objects.filter(
            assignee=current_user
        ).exclude(status='done').select_related('project', 'project__team').order_by("-created_at")
        
        context["user_tasks"] = user_tasks
        context["tasks_count"] = user_tasks.count()
        context["recent_tasks"] = user_tasks[:5]
        
        # Подсчет проектов пользователя с оптимизацией
        user_projects = Project.objects.filter(
            Q(team__teammembership__user=current_user, team__teammembership__is_active=True) | Q(team__creator=current_user)
        ).select_related('team').distinct()
        context["projects_count"] = user_projects.count()

        return context