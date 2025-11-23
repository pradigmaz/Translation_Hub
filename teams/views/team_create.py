"""Представления для создания команд."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib import messages

from ..models import Team, TeamMembership, ensure_leader_role_exists
from ..forms import TeamForm



class TeamCreateView(LoginRequiredMixin, CreateView):
    """Создание команды с автоназначением роли руководителя."""
    
    model = Team
    form_class = TeamForm
    template_name = "teams/team_form.html"
    
    def get_form(self, form_class=None):
        """Передача пользователя в форму."""
        form = super().get_form(form_class)
        form.user = self.request.user
        return form
    
    def _check_duplicate_team(self, team_name, user):
        """Проверка уникальности названия."""
        return Team.objects.filter(name=team_name, creator=user).exists()
    
    @transaction.atomic
    def form_valid(self, form):
        """Обработка валидной формы."""
        try:
            team_name = form.cleaned_data["name"]
            
            # Проверка дубликата
            if self._check_duplicate_team(team_name, self.request.user):
                form.add_error("name", "У вас уже есть команда с таким названием")
                return self.form_invalid(form)
            
            # Создание команды (сигнал автоматически добавит создателя как Leader)
            form.instance.creator = self.request.user
            response = super().form_valid(form)
            
            # Добавляем дополнительные роли если выбраны
            selected_roles = form.cleaned_data.get('role_ids', [])
            if selected_roles:
                membership = TeamMembership.objects.get(user=self.request.user, team=self.object)
                membership.roles.add(*selected_roles)
            
            messages.success(
                self.request,
                f'Команда "{self.object.name}" успешно создана!'
            )
            
            return response
            
        except Exception as e:
            messages.error(self.request, 'Произошла ошибка при создании команды. Попробуйте еще раз.')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Обработка невалидной формы."""
        
        # Добавляем общее сообщение об ошибке
        messages.error(
            self.request,
            'Пожалуйста, исправьте ошибки в форме и попробуйте снова.'
        )
        
        return super().form_invalid(form)
    
    def get_success_url(self):
        """URL редиректа после создания."""
        return reverse_lazy('teams:team_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        """Дополнительный контекст для шаблона."""
        context = super().get_context_data(**kwargs)
        
        # Добавляем информацию для шаблона
        context.update({
            'page_title': 'Создание новой команды',
            'form_action': 'Создать команду',
            'cancel_url': reverse_lazy('teams:team_list'),
            'help_text': {
                'name': 'Введите уникальное название для вашей команды. '
                        'Название должно содержать от 3 до 100 символов и может включать '
                        'буквы, цифры, пробелы, дефисы и подчеркивания.'
            }
        })
        
        return context


class TeamCreateWizardView(LoginRequiredMixin, CreateView):
    """Мастер создания команды с расширенными настройками."""
    
    model = Team
    form_class = TeamForm
    template_name = "teams/team_create_wizard.html"
    
    def get_context_data(self, **kwargs):
        """Контекст для мастера создания."""
        context = super().get_context_data(**kwargs)
        
        # Добавляем информацию о доступных ролях
        from ..models import Role
        available_roles = Role.objects.exclude(
            name__in=['Пользователь', 'Руководитель']
        ).order_by('name')
        
        context.update({
            'page_title': 'Мастер создания команды',
            'available_roles': available_roles,
            'wizard_steps': [
                {'step': 1, 'title': 'Основная информация', 'active': True},
                {'step': 2, 'title': 'Настройки команды', 'active': False},
                {'step': 3, 'title': 'Роли и разрешения', 'active': False},
                {'step': 4, 'title': 'Завершение', 'active': False},
            ]
        })
        
        return context