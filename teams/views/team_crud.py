"""
CRUD представления для команд.

Этот модуль содержит основные представления для создания, чтения,
обновления и удаления команд с использованием модульной архитектуры.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect

from ..models import Team, TeamMembership, ensure_leader_role_exists
from ..mixins import TeamPermissionMixin, TeamContextMixin, PerformanceMonitoringMixin
from ..components import TeamContextBuilder
from ..forms import TeamForm



class TeamDetailView(LoginRequiredMixin, PerformanceMonitoringMixin, TeamPermissionMixin, TeamContextMixin, DetailView):
    """
    Детальное представление команды.
    
    Отображает полную информацию о команде, включая участников, проекты,
    историю статусов и разрешения текущего пользователя.
    """
    
    model = Team
    template_name = "teams/team_detail.html"
    context_object_name = "team"
    
    def get_queryset(self):
        """QuerySet с оптимизацией: select_related('creator'), prefetch_related(members, roles, projects)."""
        return Team.objects.select_related(
            'creator'
        ).prefetch_related(
            'teammembership_set__user',
            'teammembership_set__roles',
            'projects'
        )
    
    def get_context_data(self, **kwargs):
        """Контекст через TeamContextBuilder.build_detail_context()."""
        context = super().get_context_data(**kwargs)
        
        try:
            # Используем TeamContextBuilder для построения контекста
            team = self.get_object()
            context_builder = TeamContextBuilder(team, self.request.user)
            
            # Получаем полный контекст для детальной страницы
            team_context = context_builder.build_detail_context()
            context.update(team_context)
            
        except Exception as e:
            context['error'] = 'Ошибка при загрузке данных команды'
        
        return context


class TeamCreateView(LoginRequiredMixin, PerformanceMonitoringMixin, CreateView):
    """
    Представление для создания новых команд.
    
    Создает команду с текущим пользователем как создателем и автоматически
    назначает ему роль руководителя команды.
    """
    
    model = Team
    form_class = TeamForm
    template_name = "teams/team_form.html"
    
    def get_form(self, form_class=None):
        """Передача user в форму."""
        form = super().get_form(form_class)
        form.user = self.request.user
        return form
    
    @transaction.atomic
    def form_valid(self, form):
        """Создание команды + TeamMembership + роль "Руководитель" для creator."""
        try:
            # Проверка уникальности названия команды для пользователя
            if Team.objects.filter(
                name=form.cleaned_data["name"], 
                creator=self.request.user
            ).exists():
                form.add_error("name", "У вас уже есть команда с таким названием")
                return self.form_invalid(form)
            
            # Установка текущего пользователя как создателя команды
            form.instance.creator = self.request.user
            
            # Создание команды
            response = super().form_valid(form)
            
            # Создание роли "Руководитель" если она не существует
            leader_role = ensure_leader_role_exists()
            
            # Создание TeamMembership для создателя команды
            membership, created = TeamMembership.objects.get_or_create(
                user=self.request.user,
                team=self.object
            )
            
            # Назначение роли "Руководитель" создателю команды
            membership.roles.add(leader_role)
            
            # Логирование успешного создания команды
            
            # Добавление сообщения об успехе для пользователя
            messages.success(
                self.request,
                f'Команда "{self.object.name}" успешно создана! '
                f'Вы назначены руководителем команды.'
            )
            
            return response
            
        except Exception as e:
            messages.error(
                self.request,
                'Произошла ошибка при создании команды. Попробуйте еще раз.'
            )
            return self.form_invalid(form)
    
    def get_success_url(self):
        """Редирект на team_detail."""
        return reverse_lazy('teams:team_detail', kwargs={'pk': self.object.pk})


class TeamUpdateView(LoginRequiredMixin, PerformanceMonitoringMixin, TeamPermissionMixin, UpdateView):
    """
    Представление для редактирования команды.
    
    Позволяет изменять основную информацию о команде.
    Доступно только создателю команды или суперпользователю.
    """
    
    model = Team
    form_class = TeamForm
    template_name = "teams/team_form.html"
    team_permission_required = 'can_manage_team'
    
    def get_queryset(self):
        """Получить QuerySet команд, доступных для редактирования."""
        return Team.objects.filter(creator=self.request.user)
    
    def form_valid(self, form):
        """Проверка уникальности названия и обновление."""
        try:
            # Проверка уникальности названия команды для пользователя (исключая текущую команду)
            if Team.objects.filter(
                name=form.cleaned_data["name"],
                creator=self.request.user
            ).exclude(pk=self.object.pk).exists():
                form.add_error("name", "У вас уже есть команда с таким названием")
                return self.form_invalid(form)
            
            response = super().form_valid(form)
            
            messages.success(
                self.request,
                f'Команда "{self.object.name}" успешно обновлена!'
            )
            
            return response
            
        except Exception as e:
            messages.error(
                self.request,
                'Произошла ошибка при обновлении команды. Попробуйте еще раз.'
            )
            return self.form_invalid(form)
    
    def get_success_url(self):
        """Получить URL для редиректа после успешного обновления."""
        return reverse_lazy('teams:team_detail', kwargs={'pk': self.object.pk})


class TeamDeleteView(LoginRequiredMixin, PerformanceMonitoringMixin, TeamPermissionMixin, DeleteView):
    """
    Представление для удаления команды.
    
    Фактически не удаляет команду, а переводит ее в статус "Распущена"
    для сохранения истории и целостности данных.
    """
    
    model = Team
    template_name = "teams/team_confirm_delete.html"
    success_url = reverse_lazy('teams:team_list')
    team_permission_required = 'can_manage_team'
    
    def get_queryset(self):
        """Получить QuerySet команд, доступных для удаления."""
        return Team.objects.filter(creator=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """Soft delete: перевод в статус DISBANDED через TeamStatusManager."""
        try:
            self.object = self.get_object()
            
            # Используем компонент для изменения статуса
            from ..components import TeamStatusManager
            from ..models import TeamStatus
            
            status_manager = TeamStatusManager(self.object, request.user)
            
            # Проверяем возможность роспуска команды
            can_disband = status_manager.can_change_status(TeamStatus.DISBANDED)
            
            if not can_disband['can_change']:
                messages.error(request, can_disband['reason'])
                return redirect('teams:team_detail', pk=self.object.pk)
            
            # Распускаем команду
            result = status_manager.change_status(
                TeamStatus.DISBANDED,
                reason="Команда удалена через интерфейс"
            )
            
            if result['success']:
                
                messages.success(
                    request,
                    f'Команда "{self.object.name}" была распущена.'
                )
            else:
                messages.error(
                    request,
                    'Не удалось распустить команду. Попробуйте еще раз.'
                )
                return redirect('teams:team_detail', pk=self.object.pk)
            
            return redirect(self.success_url)
            
        except Exception as e:
            messages.error(
                request,
                'Произошла ошибка при роспуске команды. Попробуйте еще раз.'
            )
            return redirect('teams:team_detail', pk=self.object.pk)